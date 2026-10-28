"""
Integration test for Phase 2: Simulator -> TelemetryRecord -> Synchronizer -> Digital Twin.
Verifies end-to-end telemetry fidelity, topology shadow synchronization, and determinism.
"""

import pytest
import numpy as np
import pandas as pd
from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import MasterConfig, SimulationConfig, TopologyConfig
from backend.digital_twin import DigitalTwin, DigitalTwinSynchronizer


def test_phase2_simulator_to_twin_pipeline():
    """
    Executes full pipeline:
    1. Initialize simulator with 6 nodes, 50 seconds.
    2. Synchronize topology context into Synchronizer.
    3. Advance simulator step-by-step and feed TelemetryRecord stream to Digital Twin.
    4. Assert Digital Twin node states match simulator node states exactly.
    """
    cfg = MasterConfig(
        simulation=SimulationConfig(nodes=6, duration=50.0, timestep=1.0, seed=42),
        topology=TopologyConfig(type="grid", grid_rows=2, grid_cols=3)
    )

    sim = NetworkSimulator(config=cfg)
    twin = DigitalTwin(history_window_seconds=60.0)
    synchronizer = DigitalTwinSynchronizer(twin)

    # Register topology context
    positions = sim.topology.positions
    neighbors = {i: sim.topology.get_neighbors(i) for i in range(sim.num_nodes)}
    synchronizer.register_topology_context(positions, neighbors)

    all_sim_records = []
    # Step-by-step execution and ingestion
    for _ in range(50):
        step_recs = sim.step()
        all_sim_records.extend(step_recs)
        synchronizer.ingest_batch(step_recs)

    # 1. Total records ingested verification
    sync_metrics = twin.get_synchronization_metrics()
    assert sync_metrics["records_ingested"] == 6 * 50
    assert sync_metrics["mean_sync_latency_ms"] >= 0.0

    # 2. Node State Exact Match Verification at final step
    sim_df = sim.get_telemetry_dataframe()
    final_sim_df = sim_df[sim_df["timestamp"] == 49.0].set_index("node_id")

    for node_id in range(6):
        sim_row = final_sim_df.loc[node_id]
        twin_node = twin.get_node_state(node_id)

        assert twin_node.timestamp == sim_row["timestamp"]
        assert twin_node.packet_rate == pytest.approx(sim_row["packet_rate"], rel=1e-5)
        assert twin_node.forwarding_rate == pytest.approx(sim_row["forwarding_rate"], rel=1e-5)
        assert twin_node.packet_loss == pytest.approx(sim_row["packet_loss"], rel=1e-5)
        assert twin_node.latency == pytest.approx(sim_row["latency"], rel=1e-5)
        assert twin_node.rssi == pytest.approx(sim_row["rssi"], rel=1e-5)
        assert twin_node.energy == pytest.approx(sim_row["energy"], rel=1e-5)
        assert twin_node.cpu == pytest.approx(sim_row["cpu"], rel=1e-5)
        assert twin_node.memory == pytest.approx(sim_row["memory"], rel=1e-5)
        assert twin_node.connection_state == sim_row["connection_state"]

    # 3. Topology Shadow Verification
    twin_topo = twin.get_network_topology()
    assert twin_topo.number_of_nodes() == sim.topology.graph.number_of_nodes()
    assert twin_topo.number_of_edges() == sim.topology.graph.number_of_edges()

    # 4. Network Health Verification
    health = twin.get_network_health()
    assert health.connected_node_ratio == 1.0
    assert health.health_status == "HEALTHY"
    assert health.disconnected_node_count == 0


def test_reproducible_twin_state():
    """Verify that identical simulation seeds yield bit-identical Digital Twin states."""
    def run_pipeline(seed: int):
        sim = NetworkSimulator(seed=seed)
        twin = DigitalTwin(history_window_seconds=60.0)
        synchronizer = DigitalTwinSynchronizer(twin)
        neighbors = {i: sim.topology.get_neighbors(i) for i in range(sim.num_nodes)}
        synchronizer.register_topology_context(sim.topology.positions, neighbors)

        for _ in range(20):
            recs = sim.step()
            synchronizer.ingest_batch(recs)
        return twin

    twin1 = run_pipeline(seed=42)
    twin2 = run_pipeline(seed=42)
    twin3 = run_pipeline(seed=43)

    for nid in range(6):
        s1 = twin1.get_node_state(nid)
        s2 = twin2.get_node_state(nid)
        s3 = twin3.get_node_state(nid)

        assert s1.to_dict() == s2.to_dict()
        assert s1.to_dict() != s3.to_dict()

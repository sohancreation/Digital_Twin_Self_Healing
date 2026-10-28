"""
Integration test for Phase 3: Simulator -> Attack Injector -> TelemetryRecord -> Ground Truth -> Digital Twin.
Verifies full pipeline interoperability, Digital Twin shadow integrity under attack, and reproducibility.
"""

import pytest
import numpy as np
import pandas as pd
from backend.simulation.simulator import NetworkSimulator
from backend.digital_twin import DigitalTwin, DigitalTwinSynchronizer
from backend.attacks import AttackInjector, AttackConfig


def test_phase3_pipeline_with_attacks():
    """
    Executes full pipeline under attack:
    1. Attach AttackInjector with DoS and NodeFailure scenarios.
    2. Step simulator and feed TelemetryRecord stream to Digital Twin.
    3. Verify Digital Twin mirrors the attacked states without error.
    4. Verify ground-truth alignment with telemetry records.
    """
    injector = AttackInjector(attack_seed=1001)
    # DoS on node 2 at [10, 20)
    injector.add_attack(AttackConfig(
        attack_id="DOS_001",
        attack_type="dos",
        target_nodes=[2],
        start_time=10.0,
        end_time=20.0,
        intensity=20.0
    ))
    # Failure on node 4 at [30, 40)
    injector.add_attack(AttackConfig(
        attack_id="FAIL_001",
        attack_type="node_failure",
        target_nodes=[4],
        start_time=30.0,
        end_time=40.0
    ))

    sim = NetworkSimulator(seed=42, attack_injector=injector)
    twin = DigitalTwin(history_window_seconds=60.0)
    synchronizer = DigitalTwinSynchronizer(twin)

    # Register topology context
    neighbors = {i: sim.topology.get_neighbors(i) for i in range(sim.num_nodes)}
    synchronizer.register_topology_context(sim.topology.positions, neighbors)

    for _ in range(50):
        step_recs = sim.step()
        synchronizer.ingest_batch(step_recs)

    # 1. Total records check
    assert len(sim.telemetry_history) == 6 * 50
    gt_df = injector.get_ground_truth_dataframe()
    assert len(gt_df) == 6 * 50

    # 2. Digital Twin Node Failure Reflection (at t=35s)
    # Query node 4 history at t=35s
    node_4_hist = twin.get_node_history(4)
    t35_records = [r for r in node_4_hist if r.timestamp == 35.0]
    assert len(t35_records) == 1
    assert t35_records[0].connection_state == "DISCONNECTED"
    assert t35_records[0].packet_loss == 1.0

    # 3. Final State: node 4 recovered (at t=49s)
    node_4_latest = twin.get_node_state(4)
    assert node_4_latest.timestamp == 49.0
    assert node_4_latest.connection_state == "CONNECTED"


def test_phase3_reproducibility():
    """
    Verify strict reproducibility of attacked simulation and ground truth:
    seed=42, attack_seed=1001 run twice produces exact matching DataFrames.
    """
    def run_simulation(seed: int, attack_seed: int):
        inj = AttackInjector(attack_seed=attack_seed)
        inj.add_attack(AttackConfig(
            attack_id="DOS_001",
            attack_type="dos",
            target_nodes=[1],
            start_time=5.0,
            end_time=15.0,
            intensity=15.0
        ))
        s = NetworkSimulator(seed=seed, attack_injector=inj)
        s.run(duration=20.0)
        return s.get_telemetry_dataframe(), inj.get_ground_truth_dataframe()

    tel1, gt1 = run_simulation(42, 1001)
    tel2, gt2 = run_simulation(42, 1001)
    tel3, gt3 = run_simulation(42, 1002)

    # Identical runs must match bit-for-bit
    pd.testing.assert_frame_equal(tel1, tel2)
    pd.testing.assert_frame_equal(gt1, gt2)

    # Different attack seed produces variation in stochastic flood jitter
    with pytest.raises(AssertionError):
        pd.testing.assert_frame_equal(tel1, tel3)

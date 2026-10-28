"""
Unit tests for Digital Twin components: models, state synchronization,
topology shadow, history management, and health assessments.
"""

import pytest
import time
import numpy as np
import networkx as nx
from backend.simulation.telemetry import TelemetryRecord
from backend.digital_twin import (
    DigitalTwin,
    DigitalTwinSynchronizer,
    TwinNodeState,
    NetworkTwinState,
    NetworkHealthSummary,
    SyncMetadata,
    HistoryManager,
)


def _create_sample_telemetry(node_id: int, timestamp: float, energy: float = 98.0, loss: float = 0.02) -> TelemetryRecord:
    return TelemetryRecord(
        timestamp=timestamp,
        node_id=node_id,
        packet_rate=2.0,
        forwarding_rate=1.0,
        packet_loss=loss,
        latency=25.0,
        rssi=-80.0,
        energy=energy,
        cpu=12.0,
        memory=18.0,
        neighbor_count=2,
        connection_state="CONNECTED" if energy > 0 else "DISCONNECTED",
        routing_state="ROUTING" if energy > 0 else "IDLE",
        threat_level=0.0,
        trust_score=1.0,
    )


def test_twin_initialization():
    """Verify clean initialization of Digital Twin."""
    twin = DigitalTwin(history_window_seconds=60.0)
    assert len(twin.get_all_nodes()) == 0
    assert twin.latest_timestamp == 0.0
    metrics = twin.get_synchronization_metrics()
    assert metrics["records_ingested"] == 0.0


def test_node_state_synchronization():
    """Verify that ingested telemetry accurately updates TwinNodeState."""
    twin = DigitalTwin()
    synchronizer = DigitalTwinSynchronizer(twin)

    rec = _create_sample_telemetry(node_id=1, timestamp=5.0)
    meta = synchronizer.ingest_record(rec)

    assert meta.node_id == 1
    assert meta.telemetry_timestamp == 5.0
    assert meta.sync_latency_ms >= 0.0

    state = twin.get_node_state(1)
    assert isinstance(state, TwinNodeState)
    assert state.node_id == 1
    assert state.timestamp == 5.0
    assert state.packet_rate == 2.0
    assert state.forwarding_rate == 1.0
    assert state.packet_loss == 0.02
    assert state.latency == 25.0
    assert state.rssi == -80.0
    assert state.energy == 98.0
    assert state.cpu == 12.0
    assert state.memory == 18.0
    assert state.connection_state == "CONNECTED"


def test_network_state_synchronization():
    """Verify that network-level metrics are computed accurately across nodes."""
    twin = DigitalTwin()
    synchronizer = DigitalTwinSynchronizer(twin)

    recs = [
        _create_sample_telemetry(node_id=0, timestamp=1.0, energy=90.0, loss=0.02),
        _create_sample_telemetry(node_id=1, timestamp=1.0, energy=80.0, loss=0.04),
    ]
    synchronizer.ingest_batch(recs)

    net_state = twin.get_network_state()
    assert isinstance(net_state, NetworkTwinState)
    assert net_state.node_count == 2
    assert net_state.connected_node_count == 2
    assert net_state.average_packet_loss == pytest.approx(0.03)
    assert net_state.total_energy == pytest.approx(170.0)
    assert net_state.network_availability == 1.0


def test_topology_synchronization():
    """Verify topology shadow creation and neighbor link state tracking."""
    twin = DigitalTwin()
    synchronizer = DigitalTwinSynchronizer(twin)

    positions = {0: (0.0, 0.0), 1: (10.0, 0.0), 2: (0.0, 10.0)}
    neighbors = {0: [1, 2], 1: [0], 2: [0]}
    synchronizer.register_topology_context(positions, neighbors)

    for nid in [0, 1, 2]:
        synchronizer.ingest_record(_create_sample_telemetry(node_id=nid, timestamp=0.0))

    topo = twin.get_network_topology()
    assert topo.number_of_nodes() == 3
    assert topo.number_of_edges() == 2
    assert twin.topology_model.is_connected() is True
    assert set(twin.topology_model.get_neighbors(0)) == {1, 2}

    link = twin.get_link_state(0, 1)
    assert link is not None
    assert link.active is True
    assert link.estimated_rssi == -80.0


def test_history_storage_and_queries():
    """Verify that historical time series are retained and retrievable."""
    twin = DigitalTwin(history_window_seconds=30.0)
    synchronizer = DigitalTwinSynchronizer(twin)

    for t in range(10):
        synchronizer.ingest_record(_create_sample_telemetry(node_id=0, timestamp=float(t)))

    history = twin.get_node_history(0)
    assert len(history) == 10
    assert history[0].timestamp == 0.0
    assert history[-1].timestamp == 9.0

    # Metric query
    cpu_history = twin.history_manager.get_metric_history(0, "cpu")
    assert len(cpu_history) == 10
    assert cpu_history[-1] == (9.0, 12.0)

    # Recent state query
    recent = twin.history_manager.get_recent_state(0, seconds=3.0)
    assert len(recent) == 4  # timestamps 6, 7, 8, 9


def test_history_window_eviction():
    """Verify that records older than history_window_seconds are evicted."""
    twin = DigitalTwin(history_window_seconds=10.0)
    synchronizer = DigitalTwinSynchronizer(twin)

    # Ingest 25 seconds of telemetry
    for t in range(25):
        synchronizer.ingest_record(_create_sample_telemetry(node_id=0, timestamp=float(t)))

    history = twin.get_node_history(0)
    # With window=10s and latest timestamp=24, entries < 14 should be evicted
    assert history[0].timestamp >= 14.0
    assert history[-1].timestamp == 24.0
    assert len(history) <= 11


def test_state_consistency():
    """Verify Digital Twin preserves exact fields from incoming telemetry."""
    twin = DigitalTwin()
    synchronizer = DigitalTwinSynchronizer(twin)

    rec = _create_sample_telemetry(node_id=3, timestamp=42.0, energy=77.5, loss=0.08)
    synchronizer.ingest_record(rec)

    twin_state = twin.get_node_state(3)
    assert twin_state.node_id == rec.node_id
    assert twin_state.timestamp == rec.timestamp
    assert twin_state.energy == rec.energy
    assert twin_state.packet_loss == rec.packet_loss
    assert twin_state.cpu == rec.cpu
    assert twin_state.latency == rec.latency
    assert twin_state.connection_state == rec.connection_state


def test_disconnected_node_state():
    """Verify that disconnected / dead nodes update topology and health status accordingly."""
    twin = DigitalTwin()
    synchronizer = DigitalTwinSynchronizer(twin)

    # Node 0 is normal, Node 1 is disconnected (0 energy)
    rec0 = _create_sample_telemetry(node_id=0, timestamp=1.0, energy=90.0)
    rec1 = _create_sample_telemetry(node_id=1, timestamp=1.0, energy=0.0, loss=1.0)

    synchronizer.ingest_batch([rec0, rec1])

    net_state = twin.get_network_state()
    assert net_state.active_node_count == 1
    assert net_state.connected_node_count == 1
    assert net_state.network_availability == 0.5

    health = twin.get_network_health()
    assert isinstance(health, NetworkHealthSummary)
    assert health.connected_node_ratio == 0.5
    assert health.disconnected_node_count == 1
    assert health.health_status in ("DEGRADED", "CRITICAL")


def test_invalid_node_query():
    """Verify that querying a non-existent node raises KeyError rather than silently failing."""
    twin = DigitalTwin()
    with pytest.raises(KeyError):
        twin.get_node_state(999)

    with pytest.raises(KeyError):
        twin.get_node_history(999)


def test_synchronization_metrics():
    """Verify that synchronization latency metrics are tracked and valid."""
    twin = DigitalTwin()
    synchronizer = DigitalTwinSynchronizer(twin)

    for i in range(10):
        synchronizer.ingest_record(_create_sample_telemetry(node_id=0, timestamp=float(i)))

    metrics = twin.get_synchronization_metrics()
    assert metrics["records_ingested"] == 10.0
    assert metrics["mean_sync_latency_ms"] >= 0.0
    assert metrics["min_sync_latency_ms"] <= metrics["max_sync_latency_ms"]

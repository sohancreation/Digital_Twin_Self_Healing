"""
Unit tests for IoTNode creation, physical/computational dynamics, and bounds verification.
"""

import pytest
import numpy as np
from backend.simulation.node import IoTNode
from backend.simulation.config import TrafficConfig, ChannelConfig, ResourceConfig
from backend.simulation.telemetry import TelemetryRecord


def test_node_creation():
    """Verify node initialization with default and custom configurations."""
    node = IoTNode(node_id=1, position=(10.0, 20.0))
    assert node.node_id == 1
    assert node.position == (10.0, 20.0)
    assert node.is_alive is True
    assert node.energy_percentage == 100.0
    assert node.connection_state == "CONNECTED"
    assert node.trust_score == 1.0
    assert node.threat_level == 0.0


def test_node_state_validation():
    """Verify bounds and internal state calculations over simulation steps."""
    rng = np.random.default_rng(42)
    node = IoTNode(node_id=0, position=(0.0, 0.0))
    node.set_neighbors([1, 2], {1: 30.0, 2: 45.0})

    for step_idx in range(50):
        t = step_idx * 1.0
        rec = node.step(timestamp=t, timestep=1.0, inbound_forward_packets=2, rng=rng)

        assert isinstance(rec, TelemetryRecord)
        assert 0.0 <= rec.packet_loss <= 1.0
        assert 0.0 <= rec.cpu <= 100.0
        assert 0.0 <= rec.memory <= 100.0
        assert 0.0 <= rec.energy <= 100.0
        assert rec.latency >= 0.0
        assert rec.packet_rate >= 0.0
        assert rec.forwarding_rate >= 0.0
        assert -120.0 <= rec.rssi <= -10.0
        assert rec.connection_state in ("CONNECTED", "DEGRADED", "DISCONNECTED")


def test_energy_behavior():
    """Verify that energy decreases over time with transmission, reception, and idle power draw."""
    rng = np.random.default_rng(42)
    resource_cfg = ResourceConfig(
        initial_energy_j=100.0,
        max_energy_j=100.0,
        idle_power_w=0.5,
        tx_energy_per_packet_j=0.1,
        rx_energy_per_packet_j=0.05
    )
    node = IoTNode(node_id=0, position=(0.0, 0.0), resource_config=resource_cfg)

    initial_energy = node.current_energy_j
    energies = [initial_energy]

    for step_idx in range(20):
        node.step(timestamp=float(step_idx), timestep=1.0, inbound_forward_packets=3, rng=rng)
        energies.append(node.current_energy_j)

    # Monotonically strictly decreasing energy
    for i in range(len(energies) - 1):
        assert energies[i + 1] < energies[i], f"Energy did not decrease at step {i}"

    assert node.current_energy_j < initial_energy


def test_node_battery_depletion():
    """Verify that when energy is completely depleted, node transitions to dead/DISCONNECTED state."""
    rng = np.random.default_rng(42)
    # Low energy node
    resource_cfg = ResourceConfig(
        initial_energy_j=0.05,
        max_energy_j=100.0,
        idle_power_w=1.0
    )
    node = IoTNode(node_id=0, position=(0.0, 0.0), resource_config=resource_cfg)

    # First step should deplete energy
    rec = node.step(timestamp=0.0, timestep=1.0, inbound_forward_packets=0, rng=rng)
    assert node.is_alive is False
    assert node.current_energy_j == 0.0
    assert rec.energy == 0.0
    assert rec.connection_state == "DISCONNECTED"
    assert rec.packet_loss == 1.0


def test_cpu_traffic_scaling():
    """Verify internal consistency: higher traffic generates higher CPU utilization."""
    resource_cfg = ResourceConfig(cpu_baseline_pct=5.0, cpu_per_packet_pct=2.0)

    # Node under low traffic (0 forwarded packets)
    rng1 = np.random.default_rng(100)
    traffic_low = TrafficConfig(base_packet_rate=1.0, packet_rate_std=0.0)
    node_low = IoTNode(node_id=1, position=(0.0, 0.0), traffic_config=traffic_low, resource_config=resource_cfg)
    rec_low = node_low.step(timestamp=0.0, timestep=1.0, inbound_forward_packets=0, rng=rng1)

    # Node under high traffic (20 forwarded packets)
    rng2 = np.random.default_rng(100)
    traffic_high = TrafficConfig(base_packet_rate=1.0, packet_rate_std=0.0)
    node_high = IoTNode(node_id=2, position=(0.0, 0.0), traffic_config=traffic_high, resource_config=resource_cfg)
    rec_high = node_high.step(timestamp=0.0, timestep=1.0, inbound_forward_packets=20, rng=rng2)

    assert rec_high.cpu > rec_low.cpu, f"Expected high CPU ({rec_high.cpu}) > low CPU ({rec_low.cpu})"

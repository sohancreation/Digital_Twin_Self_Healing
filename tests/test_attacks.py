"""
Unit and functional tests for the Cyberattack Simulation Framework (Phase 3).
Tests attack models, scheduler boundaries, ground-truth generation, and attack non-interference.
"""

import pytest
import numpy as np
import pandas as pd
from pydantic import ValidationError

from backend.attacks import (
    AttackConfig,
    AttackGroundTruth,
    AttackScheduler,
    GroundTruthRecorder,
    AttackInjector,
    DoSAttack,
    CompromisedNodeAttack,
    NodeFailureAttack,
)
from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import MasterConfig, SimulationConfig, TopologyConfig


# ==============================================================================
# 1. Attack Model Validation Tests
# ==============================================================================

def test_attack_config_valid():
    """Verify creation of valid attack configurations."""
    cfg = AttackConfig(
        attack_id="DOS_001",
        attack_type="dos",
        target_nodes=[2],
        start_time=100.0,
        end_time=150.0,
        intensity=10.0
    )
    assert cfg.attack_id == "DOS_001"
    assert cfg.attack_type == "dos"
    assert cfg.target_nodes == [2]
    assert cfg.start_time == 100.0
    assert cfg.end_time == 150.0
    assert cfg.intensity == 10.0
    assert cfg.enabled is True


@pytest.mark.parametrize("invalid_kwargs", [
    {"attack_id": "A1", "attack_type": "unsupported_attack", "target_nodes": [1], "start_time": 10.0, "end_time": 20.0},
    {"attack_id": "A2", "attack_type": "dos", "target_nodes": [1], "start_time": 50.0, "end_time": 30.0},  # end <= start
    {"attack_id": "A3", "attack_type": "dos", "target_nodes": [1], "start_time": 50.0, "end_time": 50.0},  # end == start
    {"attack_id": "A4", "attack_type": "dos", "target_nodes": [], "start_time": 10.0, "end_time": 20.0},   # empty target_nodes
    {"attack_id": "A5", "attack_type": "dos", "target_nodes": [-1], "start_time": 10.0, "end_time": 20.0}, # negative node ID
    {"attack_id": "A6", "attack_type": "compromised_node", "target_nodes": [2], "start_time": 10.0, "end_time": 20.0, "intensity": 1.5}, # intensity > 1.0 for compromised
    {"attack_id": "A7", "attack_type": "compromised_node", "target_nodes": [2], "start_time": 10.0, "end_time": 20.0, "intensity": -0.1},# negative intensity
    {"attack_id": "A8", "attack_type": "dos", "target_nodes": [1], "start_time": -5.0, "end_time": 20.0}, # negative start_time
])
def test_attack_config_invalid_rejections(invalid_kwargs):
    """Verify that invalid configurations raise ValidationError."""
    with pytest.raises(ValidationError):
        AttackConfig(**invalid_kwargs)


# ==============================================================================
# 2. Attack Scheduler & Boundary Tests
# ==============================================================================

def test_scheduler_boundary_conditions():
    """
    Verify exact temporal boundary semantics:
    start_time <= t < end_time.
    """
    scheduler = AttackScheduler(attack_seed=1001)
    cfg = AttackConfig(
        attack_id="DOS_TEST",
        attack_type="dos",
        target_nodes=[1],
        start_time=100.0,
        end_time=150.0,
        intensity=5.0
    )
    scheduler.add_attack(cfg)

    # Before start
    assert scheduler.has_active_attacks(99.0) is False
    assert scheduler.has_active_attacks(99.9) is False
    assert scheduler.get_attack_for_node(1, 99.0) is None

    # At exact start
    assert scheduler.has_active_attacks(100.0) is True
    atk = scheduler.get_attack_for_node(1, 100.0)
    assert atk is not None
    assert atk.attack_id == "DOS_TEST"

    # Mid interval
    assert scheduler.has_active_attacks(125.0) is True
    assert scheduler.get_attack_for_node(1, 125.0) is not None

    # Just before end
    assert scheduler.has_active_attacks(149.9) is True

    # At exact end (exclusive boundary)
    assert scheduler.has_active_attacks(150.0) is False
    assert scheduler.get_attack_for_node(1, 150.0) is None

    # After end
    assert scheduler.has_active_attacks(151.0) is False


def test_scheduler_multiple_attacks():
    """Verify scheduler manages distinct non-overlapping and overlapping intervals."""
    scheduler = AttackScheduler()
    scheduler.add_attack(AttackConfig(attack_id="A1", attack_type="dos", target_nodes=[1], start_time=10.0, end_time=20.0, intensity=5.0))
    scheduler.add_attack(AttackConfig(attack_id="A2", attack_type="node_failure", target_nodes=[2], start_time=30.0, end_time=40.0))

    assert scheduler.get_attack_for_node(1, 15.0).attack_id == "A1"
    assert scheduler.get_attack_for_node(2, 15.0) is None

    assert scheduler.get_attack_for_node(1, 35.0) is None
    assert scheduler.get_attack_for_node(2, 35.0).attack_id == "A2"


# ==============================================================================
# 3. Attack Non-Interference Test (Crucial for Baseline Integrity)
# ==============================================================================

def test_attack_non_interference():
    """
    Verify that initializing the simulator with an AttackInjector containing NO active attacks
    produces BIT-IDENTICAL telemetry to the pure baseline simulator.
    """
    # 1. Pure baseline
    sim_baseline = NetworkSimulator(seed=42)
    sim_baseline.run(duration=30.0)
    df_baseline = sim_baseline.get_telemetry_dataframe()

    # 2. Simulator with empty AttackInjector
    injector_empty = AttackInjector(attack_seed=1001)
    sim_with_injector = NetworkSimulator(seed=42, attack_injector=injector_empty)
    sim_with_injector.run(duration=30.0)
    df_with_injector = sim_with_injector.get_telemetry_dataframe()

    pd.testing.assert_frame_equal(df_baseline, df_with_injector)

    # 3. Simulator with attack scheduled in the future (t=100s, running only 30s)
    injector_future = AttackInjector(attack_seed=1001)
    injector_future.add_attack(AttackConfig(
        attack_id="FUTURE_DOS",
        attack_type="dos",
        target_nodes=[2],
        start_time=100.0,
        end_time=150.0,
        intensity=10.0
    ))
    sim_future = NetworkSimulator(seed=42, attack_injector=injector_future)
    sim_future.run(duration=30.0)
    df_future = sim_future.get_telemetry_dataframe()

    pd.testing.assert_frame_equal(df_baseline, df_future)


# ==============================================================================
# 4. DoS Flooding Attack Dynamics Tests
# ==============================================================================

def test_dos_attack_observable_effects():
    """Verify that DoS packet flooding drives CPU, buffer loss, and queuing latency up."""
    injector = AttackInjector(attack_seed=1001)
    injector.add_attack(AttackConfig(
        attack_id="DOS_001",
        attack_type="dos",
        target_nodes=[2],
        start_time=10.0,
        end_time=20.0,
        intensity=25.0  # Heavy flood: 25 pkts/sec
    ))

    sim = NetworkSimulator(seed=42, attack_injector=injector)
    sim.run(duration=30.0)
    df = sim.get_telemetry_dataframe()

    # Target node during normal vs attack
    target_normal_pre = df[(df["node_id"] == 2) & (df["timestamp"] < 10.0)]
    target_attack = df[(df["node_id"] == 2) & (df["timestamp"] >= 10.0) & (df["timestamp"] < 20.0)]
    target_normal_post = df[(df["node_id"] == 2) & (df["timestamp"] >= 20.0)]

    # 1. Forwarding rate / incoming packet rate increases significantly during attack
    assert target_attack["forwarding_rate"].mean() > target_normal_pre["forwarding_rate"].mean()

    # 2. CPU load increases significantly
    assert target_attack["cpu"].mean() > target_normal_pre["cpu"].mean()

    # 3. Latency increases
    assert target_attack["latency"].mean() > target_normal_pre["latency"].mean()

    # 4. Non-target nodes (e.g. node 0) do NOT have massive local CPU surge
    node_0_attack = df[(df["node_id"] == 0) & (df["timestamp"] >= 10.0) & (df["timestamp"] < 20.0)]
    assert target_attack["cpu"].mean() > node_0_attack["cpu"].mean()


def test_dos_disabled_flag():
    """Verify that disabled attacks (enabled=False) produce zero effect."""
    injector = AttackInjector()
    injector.add_attack(AttackConfig(
        attack_id="DOS_OFF",
        attack_type="dos",
        target_nodes=[2],
        start_time=5.0,
        end_time=15.0,
        intensity=30.0,
        enabled=False
    ))

    sim = NetworkSimulator(seed=42, attack_injector=injector)
    sim.run(duration=20.0)
    df_disabled = sim.get_telemetry_dataframe()

    sim_baseline = NetworkSimulator(seed=42)
    sim_baseline.run(duration=20.0)
    df_baseline = sim_baseline.get_telemetry_dataframe()

    pd.testing.assert_frame_equal(df_baseline, df_disabled)


# ==============================================================================
# 5. Compromised Node Attack Tests (Selective Dropping)
# ==============================================================================

def test_compromised_node_selective_drop():
    """Verify that a compromised node selectively drops packets and elevates packet loss."""
    injector = AttackInjector(attack_seed=1002)
    injector.add_attack(AttackConfig(
        attack_id="COMP_001",
        attack_type="compromised_node",
        target_nodes=[3],
        start_time=10.0,
        end_time=20.0,
        intensity=0.6  # 60% drop probability
    ))

    sim = NetworkSimulator(seed=42, attack_injector=injector)
    sim.run(duration=30.0)
    df = sim.get_telemetry_dataframe()

    node_3_pre = df[(df["node_id"] == 3) & (df["timestamp"] < 10.0)]
    node_3_attack = df[(df["node_id"] == 3) & (df["timestamp"] >= 10.0) & (df["timestamp"] < 20.0)]

    # Packet loss should be significantly higher during selective drop window
    assert node_3_attack["packet_loss"].mean() > node_3_pre["packet_loss"].mean()
    assert node_3_attack["packet_loss"].mean() >= 0.5


# ==============================================================================
# 6. Node Failure Attack Tests
# ==============================================================================

def test_node_failure_dynamics():
    """Verify that a failed node disconnects, stops forwarding, and recovers post-window."""
    injector = AttackInjector(attack_seed=1003)
    injector.add_attack(AttackConfig(
        attack_id="FAIL_001",
        attack_type="node_failure",
        target_nodes=[4],
        start_time=10.0,
        end_time=20.0
    ))

    sim = NetworkSimulator(seed=42, attack_injector=injector)
    sim.run(duration=30.0)
    df = sim.get_telemetry_dataframe()

    node_4_fail = df[(df["node_id"] == 4) & (df["timestamp"] >= 10.0) & (df["timestamp"] < 20.0)]
    for _, row in node_4_fail.iterrows():
        assert row["connection_state"] == "DISCONNECTED"
        assert row["packet_rate"] == 0.0
        assert row["forwarding_rate"] == 0.0
        assert row["packet_loss"] == 1.0
        assert row["cpu"] == 0.0
        assert row["latency"] == 0.0

    # Post failure recovery (since energy remains)
    node_4_post = df[(df["node_id"] == 4) & (df["timestamp"] >= 20.0)]
    assert node_4_post["connection_state"].iloc[0] == "CONNECTED"
    assert node_4_post["packet_rate"].mean() > 0.0


# ==============================================================================
# 7. Ground Truth Annotation Tests
# ==============================================================================

def test_ground_truth_labeling():
    """Verify ground truth records accurately match attack schedule and target nodes."""
    injector = AttackInjector()
    injector.add_attack(AttackConfig(
        attack_id="DOS_001",
        attack_type="dos",
        target_nodes=[2],
        start_time=10.0,
        end_time=20.0,
        intensity=15.0
    ))

    sim = NetworkSimulator(seed=42, attack_injector=injector)
    sim.run(duration=25.0)

    gt_df = injector.get_ground_truth_dataframe()
    assert len(gt_df) == 6 * 25

    # Check target node 2 during attack
    target_active = gt_df[(gt_df["node_id"] == 2) & (gt_df["timestamp"] >= 10.0) & (gt_df["timestamp"] < 20.0)]
    assert (target_active["attack_active"] == 1).all()
    assert (target_active["attack_type"] == "dos").all()
    assert (target_active["attack_id"] == "DOS_001").all()
    assert (target_active["target_node"] == 2).all()
    assert (target_active["intensity"] == 15.0).all()

    # Check non-target node 0 during same period
    non_target = gt_df[(gt_df["node_id"] == 0) & (gt_df["timestamp"] >= 10.0) & (gt_df["timestamp"] < 20.0)]
    assert (non_target["attack_active"] == 0).all()
    assert (non_target["attack_type"] == "normal").all()

    # Check target node before attack
    pre_attack = gt_df[(gt_df["node_id"] == 2) & (gt_df["timestamp"] < 10.0)]
    assert (pre_attack["attack_active"] == 0).all()
    assert (pre_attack["attack_type"] == "normal").all()

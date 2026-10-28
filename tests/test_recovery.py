"""
Unit and Integration Tests for Phase 7 Candidate Recovery Strategy Generator.
Verifies candidate models, topological feasibility checking, mitigation builders,
partition safeguards, and candidate pool generation across cyberattack vectors.
"""

import pytest
import numpy as np
import networkx as nx

from backend.recovery import (
    RecoveryActionType,
    RecoveryCandidate,
    StrategyPool,
    RecoveryConfig,
    FeasibilityChecker,
    build_no_action_candidate,
    build_isolation_candidate,
    build_reroute_candidate,
    build_rate_limit_candidate,
    build_reboot_candidate,
    build_power_adjustment_candidate,
    build_composite_isolate_and_bridge_candidate,
    build_composite_throttle_and_reroute_candidate,
    CandidateStrategyGenerator,
)
from backend.digital_twin.models import TwinNodeState
from backend.digital_twin.twin import DigitalTwin
from backend.trust.models import TrustConfig
from backend.trust.engine import DynamicTrustEngine
from backend.detection.engine import DetectionResult


@pytest.fixture
def sample_graph():
    # 5-node graph with a cycle and a bridge:
    # 0 - 1 - 2 - 3 - 4
    #     |___|
    # (1-2 is in a cycle with 0? No: 0-1, 1-2, 2-0 is a triangle; 2-3-4 is a tail)
    G = nx.Graph()
    G.add_edges_from([(0, 1), (1, 2), (2, 0), (2, 3), (3, 4)])
    return G


@pytest.fixture
def sample_node_states():
    states = {}
    for i in range(5):
        states[i] = TwinNodeState(
            node_id=i,
            timestamp=10.0,
            position=(float(i * 10), 0.0),
            packet_rate=2.0,
            forwarding_rate=4.0,
            packet_loss=0.01,
            latency=15.0,
            rssi=-65.0,
            energy=85.0,
            cpu=20.0,
            memory=25.0,
            neighbor_count=2,
            connection_state="CONNECTED",
            routing_state="ROUTING",
            threat_level=0.0,
            trust_score=1.0,
        )
    return states


def test_recovery_candidate_model():
    cand = RecoveryCandidate(
        strategy_id="STRAT_TEST",
        action_type="RATE_LIMITING",
        target_nodes=[2],
        affected_nodes=[1, 3],
        parameters={"rate_cap_pkts_sec": 2.5},
        estimated_cost=1.5,
        is_topology_partitioning=False,
        expected_recovery_time_s=1.0,
        rationale="Rate limiting test"
    )
    assert cand.strategy_id == "STRAT_TEST"
    assert cand.action_type == "RATE_LIMITING"
    assert cand.target_nodes == [2]
    d = cand.to_dict()
    assert d["estimated_cost"] == 1.5


def test_strategy_pool_model():
    cand0 = build_no_action_candidate()
    pool = StrategyPool(
        timestamp=10.0,
        candidates=[cand0],
        trigger_context={"quarantined_nodes": [2]},
        generation_latency_us=120.5
    )
    assert len(pool.candidates) == 1
    assert pool.get_candidate("STRAT_NO_ACTION") is not None
    assert pool.get_candidate("NON_EXISTENT") is None


def test_feasibility_partition_detection(sample_graph):
    checker = FeasibilityChecker()

    # Node 3 is an articulation point on the tail (2 - 3 - 4):
    # Removing Node 3 partitions Node 4 from {0, 1, 2}
    is_part, num_comps, comps = checker.check_isolation_partition(sample_graph, target_node=3)
    assert is_part is True
    assert num_comps == 2

    # Node 4 is a leaf node:
    # Removing Node 4 does NOT partition the remaining nodes {0, 1, 2, 3}
    is_part4, num_comps4, _ = checker.check_isolation_partition(sample_graph, target_node=4)
    assert is_part4 is False
    assert num_comps4 == 1

    # Node 1 is in a triangle {0, 1, 2}:
    # Removing Node 1 leaves {0, 2, 3, 4} connected
    is_part1, num_comps1, _ = checker.check_isolation_partition(sample_graph, target_node=1)
    assert is_part1 is False
    assert num_comps1 == 1


def test_feasibility_alternate_routes(sample_graph):
    checker = FeasibilityChecker()

    # In triangle {0, 1, 2}, neighbors of 1 are 0 and 2.
    # If 1 is bypassed, alternate route between 0 and 2 exists directly: [0, 2]
    routes = checker.find_alternate_routes(sample_graph, target_node=1)
    assert (0, 2) in routes
    assert routes[(0, 2)] == [0, 2]

    # For Node 3 (articulation point), neighbors are 2 and 4.
    # If 3 is bypassed, no path exists between 2 and 4!
    routes3 = checker.find_alternate_routes(sample_graph, target_node=3)
    assert (2, 4) in routes3
    assert routes3[(2, 4)] is None


def test_power_boost_feasibility(sample_node_states):
    checker = FeasibilityChecker()

    # All nodes have 85% battery -> feasible
    assert checker.check_power_boost_feasibility(sample_node_states, candidate_nodes=[1, 2]) is True

    # Depleted node with 10% battery -> infeasible
    sample_node_states[1] = sample_node_states[1].model_copy(update={"energy": 10.0})
    assert checker.check_power_boost_feasibility(sample_node_states, candidate_nodes=[1, 2]) is False


def test_candidate_builders(sample_graph, sample_node_states):
    # 1. No Action
    c_none = build_no_action_candidate()
    assert c_none.action_type == "NO_ACTION"
    assert c_none.estimated_cost == 0.0

    # 2. Isolation
    c_iso = build_isolation_candidate(target_node=3, graph=sample_graph)
    assert c_iso.action_type == "NODE_ISOLATION"
    assert c_iso.is_topology_partitioning is True  # 3 is an articulation point
    assert c_iso.estimated_cost > 3.0

    # 3. Reroute
    c_reroute = build_reroute_candidate(target_node=1, graph=sample_graph)
    assert c_reroute is not None
    assert c_reroute.action_type == "DYNAMIC_REROUTING"

    # 4. Rate Limit
    c_rate = build_rate_limit_candidate(target_node=2, current_packet_rate=25.0, rate_cap_pkts_sec=2.0)
    assert c_rate.action_type == "RATE_LIMITING"
    assert c_rate.parameters["ingress_rate_cap_pkts_sec"] == 2.0
    assert c_rate.parameters["rate_reduction_pct"] > 80.0

    # 5. Reboot
    c_boot = build_reboot_candidate(target_node=4, reboot_duration_s=5.0)
    assert c_boot.action_type == "NODE_REBOOT"
    assert c_boot.expected_recovery_time_s == 5.0

    # 6. Power Adjustment
    c_pwr = build_power_adjustment_candidate(target_node=1, graph=sample_graph, node_states=sample_node_states)
    assert c_pwr is not None
    assert c_pwr.action_type == "POWER_ADJUSTMENT"


def test_generator_dos_quarantine_scenario(sample_graph, sample_node_states):
    dt = DigitalTwin()
    for nid, s in sample_node_states.items():
        dt.node_states[nid] = s
    dt.topology_model.graph = sample_graph

    trust_engine = DynamicTrustEngine(config=TrustConfig(), digital_twin=dt)

    # Put Node 2 into QUARANTINED state under DoS attack
    det_dos = DetectionResult(
        timestamp=10.0, node_id=2, is_attack=True, attack_type="dos",
        attack_probability=0.98, confidence=0.98, inference_latency_us=50.0
    )
    dos_node = sample_node_states[2].model_copy(update={"packet_rate": 35.0, "packet_loss": 0.60})
    for _ in range(5):
        trust_engine.update_node(dos_node, det_dos, graph=sample_graph)

    generator = CandidateStrategyGenerator()
    pool = generator.generate_strategy_pool(timestamp=10.0, digital_twin=dt, trust_engine=trust_engine)

    assert len(pool.candidates) >= 3
    action_types = {c.action_type for c in pool.candidates}
    assert "NO_ACTION" in action_types
    assert "RATE_LIMITING" in action_types
    assert "NODE_ISOLATION" in action_types


def test_generator_compromised_node_scenario(sample_graph, sample_node_states):
    dt = DigitalTwin()
    for nid, s in sample_node_states.items():
        dt.node_states[nid] = s
    dt.topology_model.graph = sample_graph

    trust_engine = DynamicTrustEngine(config=TrustConfig(), digital_twin=dt)

    # Put Node 3 into QUARANTINED state under selective drop attack
    det_comp = DetectionResult(
        timestamp=10.0, node_id=3, is_attack=True, attack_type="compromised_node",
        attack_probability=0.99, confidence=1.0, inference_latency_us=50.0
    )
    comp_node = sample_node_states[3].model_copy(update={"packet_loss": 0.85})
    for _ in range(3):
        trust_engine.update_node(comp_node, det_comp, graph=sample_graph)

    generator = CandidateStrategyGenerator()
    pool = generator.generate_strategy_pool(timestamp=10.0, digital_twin=dt, trust_engine=trust_engine)

    action_types = {c.action_type for c in pool.candidates}
    assert "NO_ACTION" in action_types
    assert "NODE_ISOLATION" in action_types
    assert "NODE_REBOOT" in action_types


def test_generator_node_failure_scenario(sample_graph, sample_node_states):
    dt = DigitalTwin()
    for nid, s in sample_node_states.items():
        dt.node_states[nid] = s
    dt.topology_model.graph = sample_graph

    trust_engine = DynamicTrustEngine(config=TrustConfig(), digital_twin=dt)

    # Put Node 4 into QUARANTINED state under failure (disconnected)
    det_fail = DetectionResult(
        timestamp=10.0, node_id=4, is_attack=True, attack_type="node_failure",
        attack_probability=0.95, confidence=0.95, inference_latency_us=50.0
    )
    fail_node = sample_node_states[4].model_copy(update={"connection_state": "DISCONNECTED", "energy": 0.0})
    for _ in range(3):
        trust_engine.update_node(fail_node, det_fail, graph=sample_graph)

    generator = CandidateStrategyGenerator()
    pool = generator.generate_strategy_pool(timestamp=10.0, digital_twin=dt, trust_engine=trust_engine)

    action_types = {c.action_type for c in pool.candidates}
    assert "NODE_REBOOT" in action_types


def test_generator_latency_benchmark(sample_graph, sample_node_states):
    dt = DigitalTwin()
    for nid, s in sample_node_states.items():
        dt.node_states[nid] = s
    dt.topology_model.graph = sample_graph

    trust_engine = DynamicTrustEngine(config=TrustConfig(), digital_twin=dt)
    generator = CandidateStrategyGenerator()

    pool = generator.generate_strategy_pool(timestamp=10.0, digital_twin=dt, trust_engine=trust_engine)
    # Generation latency should be well under 2000 us (2 ms)
    assert pool.generation_latency_us < 2000.0


def test_composite_isolate_and_bridge_builder(sample_graph, sample_node_states):
    """
    Tests that composite builder pairs cut-vertex isolation with neighbor power boosting,
    ensuring is_topology_partitioning is False and action_type is COMPOSITE.
    """
    comp = build_composite_isolate_and_bridge_candidate(
        target_node=3, graph=sample_graph, node_states=sample_node_states, boost_dbm=4.0
    )
    assert comp is not None
    assert comp.action_type == "COMPOSITE"
    assert comp.is_topology_partitioning is False
    assert "NODE_ISOLATION" in comp.parameters["sub_actions"]
    assert "POWER_ADJUSTMENT" in comp.parameters["sub_actions"]
    assert comp.parameters["power_boost_dbm"] == 4.0


def test_composite_throttle_and_reroute_builder(sample_graph):
    """
    Tests composite builder combining ingress rate limiting and loop-free bypass rerouting.
    """
    comp = build_composite_throttle_and_reroute_candidate(
        target_node=1, graph=sample_graph, current_packet_rate=30.0, rate_cap_pkts_sec=2.0
    )
    assert comp is not None
    assert comp.action_type == "COMPOSITE"
    assert comp.is_topology_partitioning is False
    assert comp.parameters["ingress_rate_cap_pkts_sec"] == 2.0
    assert "bypass_routes" in comp.parameters


def test_path_stretch_evaluation(sample_graph):
    """
    Tests path stretch calculation Delta_h = len(P_bypass) - len(P_orig) and excessive stretch flags.
    """
    checker = FeasibilityChecker()
    stretch_map = checker.evaluate_path_stretch(sample_graph, target_node=1, max_stretch_hops=2)

    assert (0, 2) in stretch_map
    res = stretch_map[(0, 2)]
    assert res["bypass_path"] == [0, 2]
    assert res["is_excessive_stretch"] is False


def test_neighbor_congestion_check(sample_node_states):
    """
    Tests validation of neighbor compute/buffer headroom before rerouting traffic.
    """
    checker = FeasibilityChecker()

    # Normal state
    assert checker.check_neighbor_congestion(sample_node_states, neighbor_nodes=[1, 2]) is True

    # Congested neighbor (CPU pinned at 95%)
    congested_states = dict(sample_node_states)
    congested_states[1] = congested_states[1].model_copy(update={"cpu": 95.0})
    assert checker.check_neighbor_congestion(congested_states, neighbor_nodes=[1, 2]) is False


def test_generator_composite_inclusion(sample_graph, sample_node_states):
    """
    Tests that CandidateStrategyGenerator automatically includes COMPOSITE candidates
    when cut vertices (Node 3) or DoS nodes are quarantined.
    """
    dt = DigitalTwin()
    for nid, s in sample_node_states.items():
        dt.node_states[nid] = s
    dt.topology_model.graph = sample_graph

    trust_engine = DynamicTrustEngine(config=TrustConfig(), digital_twin=dt)

    # Quarantine Node 3 (cut vertex) under selective drop
    det_comp = DetectionResult(
        timestamp=10.0, node_id=3, is_attack=True, attack_type="compromised_node",
        attack_probability=0.99, confidence=1.0, inference_latency_us=50.0
    )
    comp_node = sample_node_states[3].model_copy(update={"packet_loss": 0.85})
    for _ in range(3):
        trust_engine.update_node(comp_node, det_comp, graph=sample_graph)

    generator = CandidateStrategyGenerator()
    pool = generator.generate_strategy_pool(timestamp=10.0, digital_twin=dt, trust_engine=trust_engine)

    action_types = {c.action_type for c in pool.candidates}
    assert "COMPOSITE" in action_types


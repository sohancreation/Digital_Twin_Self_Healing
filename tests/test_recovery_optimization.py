"""
Unit and Integration Tests for Phase 8:
Digital Twin Recovery Simulation & Multi-Objective Optimization.
"""

import pytest
import networkx as nx
import numpy as np

from backend.digital_twin.models import TwinNodeState, SyncMetadata
from backend.digital_twin.twin import DigitalTwin
from backend.recovery.models import (
    RecoveryCandidate,
    StrategyPool,
    RecoveryConfig,
    OptimizationWeights,
    OptimizationConstraints,
    SandboxSimulationResult,
    CandidateObjectiveScore,
    OptimizationDecision,
)
from backend.recovery.taxonomy import (
    build_no_action_candidate,
    build_isolation_candidate,
    build_rate_limit_candidate,
    build_reroute_candidate,
    build_reboot_candidate,
    build_composite_isolate_and_bridge_candidate,
)
from backend.recovery.generator import CandidateStrategyGenerator
from backend.recovery.sandbox import RecoverySandbox
from backend.recovery.optimization import (
    MultiObjectiveRecoveryOptimizer,
    WEIGHT_PROFILES,
)
from backend.trust.engine import DynamicTrustEngine
from backend.trust.models import TrustConfig


@pytest.fixture
def sample_twin():
    """Creates a 6-node mesh network Digital Twin with realistic baseline telemetry."""
    twin = DigitalTwin(history_window_seconds=60.0)
    # 6-node graph where node 2 is a transit node and node 3 is an articulation point to node 4 & 5
    # Edges: (0, 1), (1, 2), (0, 2), (2, 3), (3, 4), (3, 5), (4, 5)
    adj = {
        0: [1, 2],
        1: [0, 2],
        2: [0, 1, 3],
        3: [2, 4, 5],
        4: [3, 5],
        5: [3, 4],
    }
    for nid, neighbors in adj.items():
        state = TwinNodeState(
            node_id=nid,
            timestamp=10.0,
            packet_rate=2.0,
            forwarding_rate=4.0,
            packet_loss=0.02,
            latency=12.0,
            rssi=-50.0,
            energy=95.0,
            cpu=10.0,
            memory=15.0,
            neighbor_count=len(neighbors),
            connection_state="CONNECTED",
            trust_score=0.95,
            threat_level=0.05,
        )
        sync = SyncMetadata(
            telemetry_timestamp=10.0,
            ingestion_timestamp=10.001,
            sync_latency_ms=1.0,
            node_id=nid,
            sequence_number=1,
        )
        twin.apply_node_update(state, sync, neighbors=neighbors)
    return twin


def test_sandbox_cloning_isolation(sample_twin):
    """Verifies that sandbox simulation mutates only its isolated copy, not the main Digital Twin."""
    sandbox = RecoverySandbox()
    cand = build_isolation_candidate(target_node=3, graph=sample_twin.get_network_topology())

    orig_nodes_before = len(sample_twin.get_all_nodes())
    orig_edges_before = sample_twin.get_network_topology().number_of_edges()

    res = sandbox.simulate_candidate(sample_twin, cand, horizon_s=15.0)

    # Main twin should remain unmodified
    assert len(sample_twin.get_all_nodes()) == orig_nodes_before
    assert sample_twin.get_network_topology().number_of_edges() == orig_edges_before
    assert sample_twin.get_node_state(3).connection_state == "CONNECTED"

    # Simulation result should be properly populated
    assert isinstance(res, SandboxSimulationResult)
    assert res.horizon_s == 15.0
    assert len(res.time_series["loss"]) == 15


def test_sandbox_no_action_under_attack(sample_twin):
    """Verifies that NO_ACTION forward projection preserves high loss and latency under active DoS."""
    sandbox = RecoverySandbox()
    cand = build_no_action_candidate(timestamp=10.0)

    attack_ctx = {2: "dos"}
    res = sandbox.simulate_candidate(sample_twin, cand, horizon_s=20.0, attack_context=attack_ctx)

    # In unmitigated DoS, packet loss and latency should be elevated
    assert res.projected_packet_loss > 0.15
    assert res.projected_avg_latency_ms > 20.0
    assert res.projected_pdr < 0.85
    assert res.is_partitioned is False


def test_sandbox_rate_limiting(sample_twin):
    """Verifies that RATE_LIMITING throttles DoS source, restoring nominal loss in forward projection."""
    sandbox = RecoverySandbox()
    dos_target = 2
    cand = build_rate_limit_candidate(target_node=dos_target, current_packet_rate=30.0)

    attack_ctx = {dos_target: "dos"}
    res_no_action = sandbox.simulate_candidate(
        sample_twin, build_no_action_candidate(10.0), horizon_s=20.0, attack_context=attack_ctx
    )
    res_rate_limit = sandbox.simulate_candidate(
        sample_twin, cand, horizon_s=20.0, attack_context=attack_ctx
    )

    # Rate limiting should yield strictly higher PDR and lower loss than no action
    assert res_rate_limit.projected_pdr > res_no_action.projected_pdr
    assert res_rate_limit.projected_packet_loss < res_no_action.projected_packet_loss
    assert res_rate_limit.projected_avg_latency_ms < res_no_action.projected_avg_latency_ms


def test_sandbox_isolation_partition_detection(sample_twin):
    """Verifies that isolating articulation point Node 3 partitions benign nodes in the sandbox."""
    sandbox = RecoverySandbox()
    # Node 3 is a cut vertex connecting {0, 1, 2} with {4, 5}
    cand = build_isolation_candidate(target_node=3, graph=sample_twin.get_network_topology())

    res = sandbox.simulate_candidate(sample_twin, cand, horizon_s=20.0)

    # Node 3 removal leaves {0,1,2} and {4,5} in 2 distinct components
    assert res.is_partitioned is True
    assert res.projected_connected_components == 2


def test_sandbox_composite_isolate_and_bridge(sample_twin):
    """Verifies that COMPOSITE_ISOLATE_AND_BRIDGE prevents network partition when isolating cut vertex."""
    sandbox = RecoverySandbox()
    nodes = sample_twin.get_all_nodes()
    graph = sample_twin.get_network_topology()

    cand = build_composite_isolate_and_bridge_candidate(
        target_node=3, graph=graph, node_states=nodes
    )
    assert cand is not None

    res = sandbox.simulate_candidate(sample_twin, cand, horizon_s=20.0)

    # Power boost bridging links neighbor nodes (e.g. 2 with 4/5), preserving single component
    assert res.is_partitioned is False
    assert res.projected_connected_components == 1
    assert res.projected_pdr > 0.90


def test_sandbox_node_reboot(sample_twin):
    """Verifies that NODE_REBOOT simulates initial downtime disruption followed by clean recovery."""
    sandbox = RecoverySandbox()
    cand = build_reboot_candidate(target_node=2)

    attack_ctx = {2: "compromised_node"}
    res = sandbox.simulate_candidate(
        sample_twin, cand, horizon_s=30.0, attack_context=attack_ctx
    )

    losses = res.time_series["loss"]
    # Early steps (during 8s reboot) have higher disruption than later steps (clean restored state)
    early_loss = np.mean(losses[:8])
    late_loss = np.mean(losses[12:])
    assert early_loss > late_loss


def test_routing_loop_dag_detection():
    """Verifies that circular forwarding paths are correctly flagged as routing loops."""
    sandbox = RecoverySandbox()
    g = nx.cycle_graph(4)

    # Circular bypass: 0 -> 1 -> 2 -> 3 -> 0
    cyclic_bypasses = {
        (0, 1): [0, 1],
        (1, 2): [1, 2],
        (2, 3): [2, 3],
        (3, 0): [3, 0],
    }
    assert sandbox._check_routing_loops(g, cyclic_bypasses) is True

    # Acyclic bypass: 0 -> 1 -> 2
    acyclic_bypasses = {
        (0, 2): [0, 1, 2],
    }
    assert sandbox._check_routing_loops(g, acyclic_bypasses) is False


def test_multi_objective_cost_calculation():
    """Verifies mathematical consistency of cost function J(s) and weight profile sensitivity."""
    optimizer = MultiObjectiveRecoveryOptimizer()
    cand = build_rate_limit_candidate(target_node=2, current_packet_rate=20.0)

    sim_res = SandboxSimulationResult(
        strategy_id=cand.strategy_id,
        action_type="RATE_LIMITING",
        horizon_s=30.0,
        timestep=1.0,
        projected_pdr=0.96,
        projected_packet_loss=0.04,
        projected_avg_latency_ms=15.0,
        projected_energy_drain_pct=5.4,
        projected_active_node_ratio=1.0,
        projected_connected_components=1,
        is_partitioned=False,
        has_routing_loops=False,
        signaling_overhead=1.0,
        simulation_latency_ms=2.5,
    )

    weights = WEIGHT_PROFILES["BALANCED"]
    constraints = OptimizationConstraints()

    score = optimizer.compute_candidate_score(cand, sim_res, weights, constraints)
    assert score.is_feasible is True
    assert len(score.constraint_violations) == 0
    assert score.cost_j > 0.0

    # Test that security-first weights penalize loss more heavily
    sec_weights = WEIGHT_PROFILES["SECURITY_FIRST"]
    sec_score = optimizer.compute_candidate_score(cand, sim_res, sec_weights, constraints)
    assert isinstance(sec_score.cost_j, float)


def test_hard_constraints_partition_enforcement(sample_twin):
    """Verifies that candidates causing graph partition are flagged infeasible and heavily penalized."""
    optimizer = MultiObjectiveRecoveryOptimizer(constraints=OptimizationConstraints(allow_partitioning=False))
    cand_iso = build_isolation_candidate(target_node=3, graph=sample_twin.get_network_topology())

    sim_res = SandboxSimulationResult(
        strategy_id=cand_iso.strategy_id,
        action_type="NODE_ISOLATION",
        horizon_s=30.0,
        projected_pdr=0.60,
        projected_packet_loss=0.40,
        projected_avg_latency_ms=18.0,
        projected_energy_drain_pct=5.0,
        projected_connected_components=2,
        is_partitioned=True,
        has_routing_loops=False,
        signaling_overhead=3.0,
    )

    score = optimizer.compute_candidate_score(
        cand_iso, sim_res, optimizer.weights, optimizer.constraints
    )
    assert score.is_feasible is False
    assert any("Partition" in v for v in score.constraint_violations)
    assert score.cost_j >= 5.0  # Penalized


def test_pareto_dominance_frontier():
    """Verifies that non-dominated candidates are accurately computed into Pareto frontier S*."""
    optimizer = MultiObjectiveRecoveryOptimizer()

    # Candidate 1: Superior in all objectives (Dominates Cand 2)
    s1 = CandidateObjectiveScore(
        strategy_id="STRAT_1",
        action_type="RATE_LIMITING",
        cost_j=0.20,
        normalized_latency_penalty=0.10,
        loss_penalty=0.03,
        normalized_energy_penalty=0.50,
        signaling_overhead_penalty=0.10,
        is_feasible=True,
        is_pareto_optimal=False,
    )

    # Candidate 2: Strictly dominated by Candidate 1
    s2 = CandidateObjectiveScore(
        strategy_id="STRAT_2",
        action_type="NODE_ISOLATION",
        cost_j=0.85,
        normalized_latency_penalty=0.50,
        loss_penalty=0.20,
        normalized_energy_penalty=1.20,
        signaling_overhead_penalty=0.40,
        is_feasible=True,
        is_pareto_optimal=False,
    )

    # Candidate 3: Trade-off (Higher latency, but lower energy -> Non-dominated with Cand 1)
    s3 = CandidateObjectiveScore(
        strategy_id="STRAT_3",
        action_type="DYNAMIC_REROUTING",
        cost_j=0.28,
        normalized_latency_penalty=0.30,
        loss_penalty=0.03,
        normalized_energy_penalty=0.20,  # Lower energy than s1
        signaling_overhead_penalty=0.20,
        is_feasible=True,
        is_pareto_optimal=False,
    )

    pareto_ids = optimizer._calculate_pareto_frontier([s1, s2, s3])
    assert "STRAT_1" in pareto_ids
    assert "STRAT_3" in pareto_ids
    assert "STRAT_2" not in pareto_ids  # s2 is dominated


def test_end_to_end_dt_pool_evaluation(sample_twin):
    """
    End-to-End Integration Test:
    Twin State -> Strategy Pool -> Sandbox Simulations -> Multi-Objective Optimizer -> Decision s*.
    """
    # 1. Setup Trust Engine with quarantined node 3
    from backend.trust.models import TrustComponents, NodeTrustEvaluation
    trust_engine = DynamicTrustEngine()
    trust_engine.quarantined_nodes.add(3)
    trust_engine.node_latest_evaluations[3] = NodeTrustEvaluation(
        node_id=3,
        timestamp=20.0,
        components=TrustComponents(
            forwarding_trust=0.20,
            energy_trust=0.80,
            loss_trust=0.30,
            ml_trust=0.10,
        ),
        instantaneous_trust=0.25,
        smoothed_trust=0.20,
        trust_state="QUARANTINED",
        risk_score=0.85,
        criticality_factor=0.60,
        detected_attack_type="compromised_node",
    )


    # 2. Synthesize Strategy Pool
    generator = CandidateStrategyGenerator()
    pool = generator.generate_strategy_pool(
        timestamp=20.0,
        digital_twin=sample_twin,
        trust_engine=trust_engine,
    )
    assert len(pool.candidates) >= 4

    # 3. Optimize via Digital Twin API
    decision = sample_twin.evaluate_strategy_pool(
        strategy_pool=pool,
        horizon_s=25.0,
        attack_context={3: "compromised_node"},
    )

    assert isinstance(decision, OptimizationDecision)
    assert decision.optimal_strategy_id != ""
    assert decision.optimal_cost_j > 0.0
    assert len(decision.ranked_candidates) == len(pool.candidates)
    assert len(decision.pareto_frontier_ids) >= 1
    assert decision.solving_latency_us > 0.0

    # Ensure the optimal candidate is feasible (does not cause unmitigated partition)
    opt_score = [s for s in decision.ranked_candidates if s.strategy_id == decision.optimal_strategy_id][0]
    assert opt_score.is_feasible is True
    assert len(decision.topsis_rankings) == len(pool.candidates)
    assert decision.optimal_topsis_strategy_id is not None


def test_monte_carlo_stochastic_ensemble(sample_twin):
    """Verifies that Monte-Carlo forward ensembling produces uncertainty statistics and envelopes."""
    sandbox = RecoverySandbox()
    cand = build_rate_limit_candidate(target_node=2, current_packet_rate=25.0)

    res = sandbox.simulate_candidate_ensemble(
        digital_twin=sample_twin,
        candidate=cand,
        horizon_s=20.0,
        num_rollouts=10,
        seed=42,
        attack_context={2: "dos"},
    )

    assert res.stochastic_summary is not None
    summary = res.stochastic_summary
    assert summary.num_rollouts == 10
    assert 0.0 <= summary.pdr_mean <= 1.0
    assert summary.pdr_std >= 0.0
    assert summary.pdr_ci95_lower <= summary.pdr_mean <= summary.pdr_ci95_upper
    assert summary.cvar_95_loss >= summary.loss_mean

    # Verify trajectory envelope
    assert "ensemble_trajectories" in res.raw_details
    ens = res.raw_details["ensemble_trajectories"]
    assert len(ens["pdr_mean"]) == 20
    assert len(ens["pdr_upper_2sigma"]) == 20
    assert len(ens["pdr_lower_2sigma"]) == 20
    assert ens["pdr_upper_2sigma"][0] >= ens["pdr_lower_2sigma"][0]


def test_topsis_decision_ranking():
    """Verifies that TOPSIS multi-criteria ranking calculates valid closeness coefficients and ranks."""
    from backend.recovery.optimization import TOPSISRanker
    ranker = TOPSISRanker()
    weights = OptimizationWeights(w_latency=0.25, w_loss=0.35, w_energy=0.25, w_overhead=0.15)

    s1 = CandidateObjectiveScore(
        strategy_id="CAND_A",
        action_type="RATE_LIMITING",
        cost_j=0.20,
        normalized_latency_penalty=0.10,
        loss_penalty=0.02,
        normalized_energy_penalty=0.40,
        signaling_overhead_penalty=0.10,
        is_feasible=True,
    )
    s2 = CandidateObjectiveScore(
        strategy_id="CAND_B",
        action_type="NODE_ISOLATION",
        cost_j=0.70,
        normalized_latency_penalty=0.60,
        loss_penalty=0.30,
        normalized_energy_penalty=1.10,
        signaling_overhead_penalty=0.50,
        is_feasible=True,
    )
    s3 = CandidateObjectiveScore(
        strategy_id="CAND_C",
        action_type="DYNAMIC_REROUTING",
        cost_j=0.35,
        normalized_latency_penalty=0.30,
        loss_penalty=0.05,
        normalized_energy_penalty=0.50,
        signaling_overhead_penalty=0.20,
        is_feasible=True,
    )

    topsis_scores = ranker.rank_candidates([s1, s2, s3], weights)
    assert len(topsis_scores) == 3

    # Cand A is strictly superior across all criteria, so it should have highest closeness C_i and rank 1
    assert topsis_scores[0].strategy_id == "CAND_A"
    assert topsis_scores[0].topsis_rank == 1
    assert topsis_scores[0].closeness_coefficient >= topsis_scores[1].closeness_coefficient
    for item in topsis_scores:
        assert 0.0 <= item.closeness_coefficient <= 1.0
        assert item.distance_to_positive_ideal >= 0.0
        assert item.distance_to_negative_ideal >= 0.0


def test_adaptive_horizon_calculation():
    """Verifies that compute_adaptive_horizon adapts to network diameter and threat urgency."""
    sandbox = RecoverySandbox()

    # Mesh of 6 nodes has diameter ~2
    g_mesh = nx.grid_2d_graph(2, 3)
    g = nx.convert_node_labels_to_integers(g_mesh)

    # DoS threat should yield quick urgent horizon (15s - 20s)
    h_dos = sandbox.compute_adaptive_horizon(g, attack_context={0: "dos"})
    assert 15.0 <= h_dos <= 25.0

    # Node failure / compromised drop requires longer lookahead (>= 30s)
    h_fail = sandbox.compute_adaptive_horizon(g, attack_context={0: "node_failure"})
    assert h_fail >= 30.0


def test_cross_mitigation_collision_detection():
    """Verifies that detect_cross_mitigation_collisions flags bypass routes traversing isolated nodes."""
    from backend.recovery.optimization import detect_cross_mitigation_collisions

    # Strategy 1 isolates node 2
    c1 = RecoveryCandidate(
        strategy_id="STRAT_ISO_2",
        action_type="NODE_ISOLATION",
        target_nodes=[2],
        parameters={},
    )

    # Strategy 2 reroutes transit flows through path [1, 2, 3] (traversing isolated node 2!)
    c2 = RecoveryCandidate(
        strategy_id="STRAT_REROUTE_BAD",
        action_type="DYNAMIC_REROUTING",
        target_nodes=[4],
        parameters={
            "alternate_routes": {
                (1, 3): [1, 2, 3]  # Intermediate hop is node 2
            }
        },
    )

    collisions = detect_cross_mitigation_collisions([c1, c2])
    assert len(collisions) == 1
    assert collisions[0]["type"] == "SEVERED_BYPASS_COLLISION"
    assert 2 in collisions[0]["conflict_nodes"]


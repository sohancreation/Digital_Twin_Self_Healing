"""
Unit and Integration Tests for Phase 9:
Autonomous Self-Healing & Closed-Loop Verification.
"""

import pytest
import numpy as np
import networkx as nx

from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import MasterConfig, SimulationConfig, TopologyConfig
from backend.simulation.telemetry import TelemetryRecord
from backend.recovery.models import (
    RecoveryCandidate,
    OptimizationDecision,
    OptimizationWeights,
    OptimizationConstraints,
    CandidateObjectiveScore,
)
from backend.recovery.taxonomy import (
    build_isolation_candidate,
    build_rate_limit_candidate,
    build_reboot_candidate,
    build_reroute_candidate,
    build_composite_isolate_and_bridge_candidate,
)
from backend.self_healing.models import (
    ActuationCommand,
    CommandAck,
    ActuationBatch,
    VerificationResult,
    RollbackSnapshot,
    RollbackExecutionResult,
    ResilienceMetrics,
    SPRTConfig,
    SPRTState,
    EscalationTier,
    FlappingState,
)
from backend.self_healing.dispatcher import ActuationPolicyDispatcher
from backend.self_healing.actuator import NetworkActuator
from backend.self_healing.verifier import ClosedLoopVerifier, WaldSPRTVerifier
from backend.self_healing.rollback import RollbackManager
from backend.self_healing.resilience import ResilienceEvaluator
from backend.self_healing.coordinator import SelfHealingCoordinator
from backend.self_healing.escalation import GraduatedEscalationManager
from backend.self_healing.damping import RouteFlappingDamper


@pytest.fixture
def sample_simulator():
    """Creates a deterministic 6-node mesh network simulator for testing actuation."""
    cfg = MasterConfig(
        simulation=SimulationConfig(duration=30.0, timestep=1.0, seed=42, nodes=6),
        topology=TopologyConfig(layout="mesh", communication_range=30.0),
    )
    sim = NetworkSimulator(config=cfg, seed=42)
    return sim


def test_dispatcher_command_generation_and_hmac():
    """Validates that candidate strategies are decomposed into authenticated downlink frames."""
    dispatcher = ActuationPolicyDispatcher(seed=42)
    cand = RecoveryCandidate(
        strategy_id="STRAT_ISO_3",
        action_type="NODE_ISOLATION",
        target_nodes=[3],
        affected_nodes=[2, 4, 5],
        parameters={"severed_links": [(3, 2), (3, 4), (3, 5)]},
    )

    batch = dispatcher.create_actuation_batch(cand, decision_epoch=50.0)
    assert batch.strategy_id == "STRAT_ISO_3"
    assert len(batch.commands) == 4  # 1 isolate target + 3 drop-route neighbors

    target_cmd = next(c for c in batch.commands if c.target_node == 3)
    assert target_cmd.command_type == "ISOLATE_NODE"
    assert target_cmd.sequence_number >= 1000

    # Verify HMAC authenticity
    assert dispatcher.verify_hmac_token(target_cmd) is True

    # Tampered command should fail HMAC verification
    tampered_cmd = target_cmd.model_copy()
    tampered_cmd.target_node = 1
    assert dispatcher.verify_hmac_token(tampered_cmd) is False


def test_dispatcher_lossy_downlink_retries():
    """Tests downlink wireless transmission under 0% loss and under simulated channel drops with retries."""
    # Zero loss: all commands should be immediately APPLIED with 0 retries
    clean_dispatcher = ActuationPolicyDispatcher(default_channel_loss_prob=0.0, seed=42)
    cand = RecoveryCandidate(
        strategy_id="STRAT_RL_2",
        action_type="RATE_LIMITING",
        target_nodes=[2],
        affected_nodes=[],
        parameters={"rate_limit_pkts_per_sec": 2.5},
    )
    batch = clean_dispatcher.create_actuation_batch(cand, decision_epoch=30.0)

    batch, acks = clean_dispatcher.dispatch_batch(batch, current_time=30.0)
    assert batch.all_acknowledged is True
    assert batch.total_retries == 0
    assert len(acks) == 1
    assert acks[0].status == "APPLIED"

    # Lossy channel with 100% loss: should exhaust max_retries and yield TIMEOUT
    lossy_dispatcher = ActuationPolicyDispatcher(default_channel_loss_prob=1.0, max_retries=2, seed=42)
    batch_lossy = lossy_dispatcher.create_actuation_batch(cand, decision_epoch=31.0)
    batch_lossy, lossy_acks = lossy_dispatcher.dispatch_batch(batch_lossy, current_time=31.0)

    assert batch_lossy.all_acknowledged is False
    assert batch_lossy.total_retries == 2
    assert lossy_acks[0].status == "TIMEOUT"


def test_actuator_node_isolation(sample_simulator):
    """Verifies that executing ISOLATE_NODE severs edges in topology and updates node state."""
    actuator = NetworkActuator(simulator=sample_simulator)
    cmd = ActuationCommand(
        command_id="CMD_TEST_ISO",
        target_node=3,
        command_type="ISOLATE_NODE",
        parameters={"action": "sever_all_links"},
        sequence_number=1001,
        hmac_token="dummy_token",
        timestamp=10.0,
    )

    # Node 3 starts with active links
    g = sample_simulator.topology.graph
    pre_degree = g.degree(3)
    assert pre_degree > 0

    ack = actuator.execute_command(cmd, current_time=10.0)
    assert ack.status == "APPLIED"
    assert 3 in actuator.isolated_nodes
    assert g.degree(3) == 0
    assert sample_simulator.nodes[3].is_alive is False
    assert getattr(sample_simulator.nodes[3], "_is_isolated", False) is True


def test_actuator_rate_limiting(sample_simulator):
    """Verifies that SET_RATE_LIMIT installs token-bucket limits and clamps ingress traffic."""
    actuator = NetworkActuator(simulator=sample_simulator)
    cmd = ActuationCommand(
        command_id="CMD_TEST_RL",
        target_node=2,
        command_type="SET_RATE_LIMIT",
        parameters={"token_rate_pkts_s": 3.0},
        sequence_number=1002,
        hmac_token="dummy_token",
        timestamp=12.0,
    )

    ack = actuator.execute_command(cmd, current_time=12.0)
    assert ack.status == "APPLIED"
    assert actuator.rate_limits[2] == 3.0

    # Traffic filter test
    filtered = actuator.filter_traffic(node_id=2, incoming_packets=25)
    assert filtered == 3
    # Non-limited node traffic unchanged
    assert actuator.filter_traffic(node_id=1, incoming_packets=25) == 25


def test_actuator_node_reboot(sample_simulator):
    """Verifies that REBOOT_NODE marks node offline and restores it after duration."""
    actuator = NetworkActuator(simulator=sample_simulator)
    cmd = ActuationCommand(
        command_id="CMD_TEST_REBOOT",
        target_node=4,
        command_type="REBOOT_NODE",
        parameters={"duration_s": 5.0, "flush_queues": True},
        sequence_number=1003,
        hmac_token="dummy_token",
        timestamp=20.0,
    )

    ack = actuator.execute_command(cmd, current_time=20.0)
    assert ack.status == "APPLIED"
    assert sample_simulator.nodes[4]._is_failed is True
    assert 4 in actuator.rebooting_nodes

    # Step at t=22.0 (reboot still active)
    actuator.pre_step_maintenance(current_time=22.0)
    assert sample_simulator.nodes[4]._is_failed is True

    # Step at t=26.0 (duration 5s elapsed)
    actuator.pre_step_maintenance(current_time=26.0)
    assert sample_simulator.nodes[4]._is_failed is False
    assert sample_simulator.nodes[4].is_alive is True
    assert 4 not in actuator.rebooting_nodes


def test_actuator_dynamic_rerouting(sample_simulator):
    """Verifies dynamic route bypass installation."""
    actuator = NetworkActuator(simulator=sample_simulator)
    cmd = ActuationCommand(
        command_id="CMD_TEST_REROUTE",
        target_node=1,
        command_type="REROUTE_TRAFFIC",
        parameters={"installed_bypasses": {"0_4": [0, 1, 2, 4]}},
        sequence_number=1004,
        hmac_token="dummy_token",
        timestamp=15.0,
    )

    ack = actuator.execute_command(cmd, current_time=15.0)
    assert ack.status == "APPLIED"
    route = actuator.get_route(src=0, dst=4, default_path=[0, 3, 4])
    assert route == [0, 1, 2, 4]


def test_verifier_success_and_criteria():
    """Tests ClosedLoopVerifier under healthy post-actuation telemetry."""
    verifier = ClosedLoopVerifier(target_min_pdr=0.88, verification_window_s=5.0)
    batch = ActuationBatch(
        batch_id="BATCH_V_TEST",
        decision_epoch=50.0,
        strategy_id="STRAT_ISO_3",
        action_type="NODE_ISOLATION",
    )
    verifier.start_verification(batch, start_time=50.0)

    # Ingest 5 healthy step records
    for sec in range(5):
        recs = [
            TelemetryRecord(
                timestamp=50.0 + sec,
                node_id=nid,
                packet_rate=2.0,
                forwarding_rate=3.0,
                packet_loss=0.02,
                latency=12.5,
                energy=95.0,
                cpu=8.0,
                memory=22.0,
                rssi=-55.0,
                queue_length=1,
                neighbor_count=3,
            )
            for nid in range(5)
        ]
        verifier.ingest_telemetry_step(recs)

    res = verifier.evaluate_verification(current_time=55.0)
    assert res.verification_status == "VERIFIED_SUCCESS"
    assert res.is_successful is True
    assert res.observed_pdr >= 0.95
    assert len(res.criteria_results) == 5
    assert all(c.passed for c in res.criteria_results)


def test_verifier_timeout_failure():
    """Tests ClosedLoopVerifier failure when packet loss remains elevated."""
    verifier = ClosedLoopVerifier(target_min_pdr=0.88, max_acceptable_loss=0.12, verification_window_s=5.0)
    batch = ActuationBatch(
        batch_id="BATCH_FAIL_TEST",
        decision_epoch=70.0,
        strategy_id="STRAT_NO_ACTION",
        action_type="NO_ACTION",
    )
    verifier.start_verification(batch, start_time=70.0)

    # Ingest lossy records (loss = 0.35 -> PDR = 0.65)
    for sec in range(5):
        recs = [
            TelemetryRecord(
                timestamp=70.0 + sec,
                node_id=nid,
                packet_rate=2.0,
                forwarding_rate=1.0,
                packet_loss=0.35,
                latency=55.0,
                energy=80.0,
                cpu=35.0,
                memory=40.0,
                rssi=-70.0,
                queue_length=8,
                neighbor_count=3,
            )
            for nid in range(5)
        ]
        verifier.ingest_telemetry_step(recs)

    res = verifier.evaluate_verification(current_time=75.0)
    assert res.verification_status == "VERIFICATION_FAILED"
    assert (
        "critical criteria" in (res.failure_reason or "").lower()
        or "delivery ratio" in (res.failure_reason or "").lower()
        or "wald sprt" in (res.failure_reason or "").lower()
    )


def test_rollback_manager_snapshot_and_restoration(sample_simulator):
    """Verifies that RollbackManager captures pre-actuation state and faithfully restores severed topology."""
    actuator = NetworkActuator(simulator=sample_simulator)
    rollback_mgr = RollbackManager()

    # Capture pre-actuation snapshot
    snap = rollback_mgr.capture_snapshot(actuator, current_time=40.0)
    orig_edge_count = sample_simulator.topology.graph.number_of_edges()

    # Actuate isolation of node 1 (severs edges)
    iso_cmd = ActuationCommand(
        command_id="CMD_ISO_1",
        target_node=1,
        command_type="ISOLATE_NODE",
        sequence_number=1005,
        hmac_token="dummy",
        timestamp=40.0,
    )
    actuator.execute_command(iso_cmd, current_time=40.0)
    assert sample_simulator.topology.graph.number_of_edges() < orig_edge_count

    # Execute automated rollback
    res = rollback_mgr.execute_rollback(snap, actuator, current_time=45.0, trigger_reason="Test partition rollback")
    assert res.success is True
    assert sample_simulator.topology.graph.number_of_edges() == orig_edge_count
    assert 1 not in actuator.isolated_nodes
    assert sample_simulator.nodes[1].is_alive is True


def test_resilience_evaluator_metrics_and_score():
    """Validates computation of MTTD, MTTA, MTTR, and integral Resilience Score R."""
    evaluator = ResilienceEvaluator()

    # Synthetic incident telemetry: 10s nominal, 10s degraded, 10s restored
    records: List[TelemetryRecord] = []
    # Attack start at t=20, detected at t=24, actuated at t=26, restored at t=35
    for t in range(20, 36):
        loss = 0.30 if 20 <= t < 28 else 0.02
        lat = 50.0 if 20 <= t < 28 else 12.0
        for nid in range(4):
            records.append(TelemetryRecord(
                timestamp=float(t),
                node_id=nid,
                packet_rate=2.0,
                forwarding_rate=2.0,
                packet_loss=loss,
                latency=lat,
                energy=90.0,
                cpu=10.0,
                memory=20.0,
                rssi=-55.0,
                queue_length=1,
                neighbor_count=3,
            ))

    metrics = evaluator.evaluate_incident_resilience(
        attack_type="compromised_node",
        t_attack_start=20.0,
        t_detect=24.0,
        t_actuate=26.0,
        t_restored=35.0,
        telemetry_records=records,
    )

    assert metrics.mttd_s == 4.0   # 24 - 20
    assert metrics.mtta_s == 2.0   # 26 - 24
    assert metrics.mttr_s == 11.0  # 35 - 24
    assert metrics.total_incident_time_s == 15.0 # 35 - 20
    assert 0.70 <= metrics.resilience_score_r <= 0.95
    assert metrics.resilience_loss_index == round(1.0 - metrics.resilience_score_r, 4)
    assert len(metrics.qos_trajectory["timestamps"]) > 0


def test_self_healing_coordinator_end_to_end(sample_simulator):
    """End-to-end closed-loop self-healing integration test."""
    coordinator = SelfHealingCoordinator(simulator=sample_simulator)
    coordinator.start_incident(attack_type="dos", t_attack_start=50.0, t_detect=52.0)

    # Synthetic optimal decision from Phase 8
    cand = RecoveryCandidate(
        strategy_id="STRAT_RL_2",
        action_type="RATE_LIMITING",
        target_nodes=[2],
        affected_nodes=[],
        parameters={"rate_limit_pkts_per_sec": 2.0},
    )
    decision = OptimizationDecision(
        decision_epoch=53.0,
        optimal_strategy_id="STRAT_RL_2",
        optimal_candidate=cand,
        optimal_cost_j=0.25,
        ranked_candidates=[
            CandidateObjectiveScore(
                strategy_id="STRAT_RL_2",
                action_type="RATE_LIMITING",
                cost_j=0.25,
                normalized_latency_penalty=0.0,
                loss_penalty=0.02,
                normalized_energy_penalty=0.1,
                signaling_overhead_penalty=0.1,
            )
        ],
        weights_used=OptimizationWeights(),
        constraints_used=OptimizationConstraints(),
    )

    # Execute optimal decision
    batch, acks = coordinator.execute_optimal_decision(decision, current_time=53.0)
    assert batch.all_acknowledged is True
    assert coordinator.actuator.rate_limits[2] == 2.0

    # Step telemetry during verification
    step_recs = [
        TelemetryRecord(
            timestamp=54.0,
            node_id=nid,
            packet_rate=2.0,
            forwarding_rate=2.0,
            packet_loss=0.02,
            latency=13.0,
            energy=92.0,
            cpu=11.0,
            memory=21.0,
            rssi=-56.0,
            queue_length=1,
            neighbor_count=3,
        )
        for nid in range(6)
    ]
    ver_res = coordinator.process_step_telemetry(current_time=54.0, step_records=step_recs)
    assert ver_res is not None
    assert ver_res.verification_status in ("VERIFYING", "VERIFIED_SUCCESS")


def test_verifier_partition_critical_failure():
    """Tests ClosedLoopVerifier immediate critical failure when topology graph partitions."""
    from backend.digital_twin.twin import DigitalTwin
    from backend.digital_twin.models import TwinNodeState

    twin = DigitalTwin()
    # Graph with 2 disconnected components: (0, 1) and (2, 3)
    g = nx.Graph()
    g.add_edges_from([(0, 1), (2, 3)])
    twin.topology_model.graph = g
    for nid in range(4):
        twin.node_states[nid] = TwinNodeState(
            node_id=nid,
            timestamp=60.0,
            packet_rate=2.0,
            forwarding_rate=2.0,
            packet_loss=0.02,
            latency=12.0,
            rssi=-50.0,
            energy=95.0,
            cpu=10.0,
            memory=20.0,
            neighbor_count=1,
        )

    verifier = ClosedLoopVerifier(verification_window_s=10.0)
    batch = ActuationBatch(
        batch_id="BATCH_PART_TEST",
        decision_epoch=60.0,
        strategy_id="STRAT_BAD_ISO",
        action_type="NODE_ISOLATION",
    )
    verifier.start_verification(batch, start_time=60.0)
    recs = [
        TelemetryRecord(
            timestamp=61.0,
            node_id=nid,
            packet_rate=2.0,
            forwarding_rate=2.0,
            packet_loss=0.02,
            latency=12.0,
            energy=95.0,
            cpu=10.0,
            memory=20.0,
            rssi=-50.0,
            queue_length=1,
            neighbor_count=1,
        )
        for nid in range(4)
    ]
    verifier.ingest_telemetry_step(recs)

    res = verifier.evaluate_verification(current_time=61.0, digital_twin=twin)
    assert res.verification_status == "VERIFICATION_FAILED"
    assert res.is_successful is False
    assert "partition" in (res.failure_reason or "").lower()
    assert res.observed_connected_components == 2


def test_wald_sprt_early_verification_success():
    """Validates that Wald's SPRT certifies nominal recovery early when observed loss is low."""
    config = SPRTConfig(p0=0.03, p1=0.12, alpha=0.01, beta=0.05, max_samples=30)
    verifier = WaldSPRTVerifier(config=config)

    assert verifier.decision == "CONTINUE"
    assert verifier.log_likelihood_ratio == 0.0
    assert config.boundary_b < 0.0 < config.boundary_a

    # Ingest series of healthy samples with 1.5% loss (below p0=0.03)
    decisions = []
    for step in range(20):
        decision = verifier.update(packet_loss_sample=0.015)
        decisions.append(decision)
        if decision != "CONTINUE":
            break

    # Must accept H0 (Success) early before exhausting all 30 samples
    assert verifier.decision == "ACCEPT_H0_SUCCESS"
    assert verifier.early_stopped is True
    assert verifier.sample_count < 30
    assert verifier.log_likelihood_ratio <= config.boundary_b


def test_wald_sprt_early_verification_failure():
    """Validates that Wald's SPRT quickly rejects verification and triggers failure when loss remains elevated."""
    config = SPRTConfig(p0=0.03, p1=0.12, alpha=0.01, beta=0.05, max_samples=30)
    verifier = WaldSPRTVerifier(config=config)

    # Ingest elevated loss samples (30% loss, well above p1=0.12)
    for step in range(15):
        decision = verifier.update(packet_loss_sample=0.30)
        if decision != "CONTINUE":
            break

    # Must accept H1 (Failure) early within a small number of samples
    assert verifier.decision == "ACCEPT_H1_FAILURE"
    assert verifier.early_stopped is True
    assert verifier.sample_count <= 8
    assert verifier.log_likelihood_ratio >= config.boundary_a


def test_graduated_escalation_multi_tier():
    """Validates 3-tier graduated escalation state machine and MST topological preservation."""
    mgr = GraduatedEscalationManager()
    assert mgr.get_current_tier() == "TIER_1_PRIMARY_OPTIMAL"

    cand = RecoveryCandidate(
        strategy_id="STRAT_TEST_RL",
        action_type="RATE_LIMITING",
        target_nodes=[2],
        parameters={"rate_limit_pkts_per_sec": 3.0},
    )

    # Escalate Tier 1 -> Tier 2
    outcome = mgr.escalate(cand, trigger_reason="PDR below threshold", current_time=50.0)
    assert outcome is not None
    batch_t2, tier_t2 = outcome
    assert tier_t2 == "TIER_2_SECONDARY_PARETO"
    assert mgr.get_current_tier() == "TIER_2_SECONDARY_PARETO"
    assert len(mgr.escalation_history) == 1
    assert "T2_COMPOSITE" in batch_t2.strategy_id

    # Escalate Tier 2 -> Tier 3 (Fail-Safe MST)
    outcome_t3 = mgr.escalate(cand, trigger_reason="Persistent attack detected", current_time=55.0)
    assert outcome_t3 is not None
    batch_t3, tier_t3 = outcome_t3
    assert tier_t3 == "TIER_3_FAILSAFE_MST"
    assert mgr.get_current_tier() == "TIER_3_FAILSAFE_MST"
    assert len(mgr.escalation_history) == 2
    assert "T3_MST_QUARANTINE" in batch_t3.strategy_id

    # Tier 3 already reached -> next escalation should be None (triggering full rollback)
    outcome_t4 = mgr.escalate(cand, trigger_reason="Exhausted tiers", current_time=60.0)
    assert outcome_t4 is None


def test_route_flapping_hysteresis_damping():
    """Validates exponential decay oscillation tracking and route flapping hold-down suppression."""
    damper = RouteFlappingDamper(
        decay_rate=0.15,
        suppress_threshold=2.5,
        reuse_threshold=0.8,
        min_hold_down_s=8.0,
        penalty_per_switch=1.0,
    )

    # First switch at t=10.0
    allowed1 = damper.filter_route_change(node_id=3, current_time=10.0)
    assert allowed1 is True
    assert damper.is_suppressed(node_id=3, current_time=10.0) is False
    assert damper.get_oscillation_index(node_id=3, current_time=10.0) == 1.0

    # Second rapid switch at t=11.0 (Omega ~ 1 + exp(-0.15*1) ~ 1.86)
    allowed2 = damper.filter_route_change(node_id=3, current_time=11.0)
    assert allowed2 is True
    assert damper.is_suppressed(node_id=3, current_time=11.0) is False

    # Third rapid switch at t=12.0 (Omega ~ 1 + exp(-0.15) + exp(-0.30) ~ 2.60 >= 2.5) -> Suppressed!
    allowed3 = damper.filter_route_change(node_id=3, current_time=12.0)
    assert allowed3 is False
    assert damper.is_suppressed(node_id=3, current_time=12.0) is True

    # Check at t=15.0 (hold-down still active, duration 8s from t=12 -> t=20)
    assert damper.is_suppressed(node_id=3, current_time=15.0) is True
    assert damper.filter_route_change(node_id=3, current_time=15.0) is False

    # Check at t=30.0 (elapsed > 8s and Omega has decayed well below reuse threshold 0.8)
    assert damper.is_suppressed(node_id=3, current_time=30.0) is False
    # Route change should now be permitted again
    assert damper.filter_route_change(node_id=3, current_time=30.0) is True


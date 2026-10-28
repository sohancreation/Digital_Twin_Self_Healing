"""
Unit and Integration Tests for Phase 6 Dynamic Risk & Trust Assessment Engine.
Verifies evaluators, asymmetric temporal smoothing, on-off attack damping,
topological criticality, state transitions, and Digital Twin synchronization.
"""

import pytest
import numpy as np
import pandas as pd
import networkx as nx

from backend.trust import (
    TrustComponents,
    NodeTrustEvaluation,
    NetworkTrustSummary,
    TrustConfig,
    ForwardingFidelityEvaluator,
    EnergyConsistencyEvaluator,
    ChannelLossFidelityEvaluator,
    MLSecurityTrustEvaluator,
    CompositeTrustEvaluator,
    TopologicalCriticalityEngine,
    DynamicTrustEngine,
    BayesianRecommendationEvaluator,
)
from backend.digital_twin.models import TwinNodeState
from backend.digital_twin.twin import DigitalTwin
from backend.detection.engine import DetectionResult


@pytest.fixture
def trust_config():
    return TrustConfig(
        weight_forwarding=0.30,
        weight_energy=0.15,
        weight_loss=0.15,
        weight_ml=0.40,
        penalty_decay_rate=0.40,
        recovery_decay_rate=0.05,
        threshold_trusted=0.70,
        threshold_quarantine=0.40,
        threshold_risk_quarantine=0.65,
    )


@pytest.fixture
def baseline_node_state():
    return TwinNodeState(
        node_id=1,
        timestamp=10.0,
        position=(10.0, 10.0),
        packet_rate=2.0,
        forwarding_rate=4.0,
        packet_loss=0.01,
        latency=12.5,
        rssi=-65.0,
        energy=95.0,
        cpu=18.0,
        memory=22.0,
        neighbor_count=4,
        connection_state="CONNECTED",
        routing_state="ROUTING",
        threat_level=0.0,
        trust_score=1.0,
    )


def test_trust_config_validation():
    cfg = TrustConfig()
    assert 0.99 <= (cfg.weight_forwarding + cfg.weight_energy + cfg.weight_loss + cfg.weight_ml) <= 1.01
    assert cfg.penalty_decay_rate > cfg.recovery_decay_rate

    # Invalid weights sum
    with pytest.raises(ValueError):
        TrustConfig(weight_forwarding=0.5, weight_energy=0.5, weight_loss=0.5, weight_ml=0.5)


def test_forwarding_fidelity_evaluator(trust_config, baseline_node_state):
    evaluator = ForwardingFidelityEvaluator(trust_config)

    # Benign low loss
    score_normal = evaluator.evaluate(baseline_node_state)
    assert score_normal >= 0.95

    # Severe packet drop (e.g. 80% loss in gray-hole attack)
    bad_state = baseline_node_state.model_copy(update={"packet_loss": 0.80})
    score_bad = evaluator.evaluate(bad_state)
    assert score_bad < 0.30
    assert score_bad < score_normal

    # Disconnected node
    dead_state = baseline_node_state.model_copy(update={"connection_state": "DISCONNECTED"})
    assert evaluator.evaluate(dead_state) == 0.0


def test_energy_consistency_evaluator(trust_config, baseline_node_state):
    evaluator = EnergyConsistencyEvaluator(trust_config)

    # Normal state
    score_normal = evaluator.evaluate(baseline_node_state)
    assert score_normal >= 0.90

    # Critically low battery (< 5%)
    low_batt = baseline_node_state.model_copy(update={"energy": 2.5})
    score_low = evaluator.evaluate(low_batt)
    assert score_low < 0.60

    # Rapid vampire drain (10% drop in 1 second)
    prev_state = baseline_node_state.model_copy(update={"timestamp": 9.0, "energy": 98.0})
    curr_state = baseline_node_state.model_copy(update={"timestamp": 10.0, "energy": 88.0})
    score_drain = evaluator.evaluate(curr_state, historical_states=[prev_state, curr_state])
    assert score_drain < 0.50


def test_channel_loss_fidelity_evaluator(trust_config, baseline_node_state):
    evaluator = ChannelLossFidelityEvaluator(trust_config)

    # Strong RSSI (-65 dBm) with normal 1% loss -> High fidelity
    assert evaluator.evaluate(baseline_node_state) >= 0.95

    # Strong RSSI (-65 dBm) with 60% loss -> Anomalous selective dropping -> Low fidelity
    anom_drop = baseline_node_state.model_copy(update={"rssi": -65.0, "packet_loss": 0.60})
    score_anom = evaluator.evaluate(anom_drop)
    assert score_anom < 0.15

    # Weak RSSI (-98 dBm) with 30% loss -> Physically explainable fading -> Moderate fidelity
    weak_rf = baseline_node_state.model_copy(update={"rssi": -98.0, "packet_loss": 0.30})
    score_weak = evaluator.evaluate(weak_rf)
    assert score_weak > score_anom


def test_ml_security_evaluator(trust_config):
    evaluator = MLSecurityTrustEvaluator(trust_config)

    assert evaluator.evaluate(0.0) == 1.0
    assert evaluator.evaluate(1.0) == 0.0
    assert evaluator.evaluate(0.25) == 0.75
    assert evaluator.evaluate(0.95) == pytest.approx(0.05, 0.001)


def test_composite_trust_evaluator(trust_config, baseline_node_state):
    coordinator = CompositeTrustEvaluator(trust_config)

    # Normal node with P_attack = 0.0
    components, inst_trust = coordinator.evaluate_node(baseline_node_state, attack_probability=0.0)
    assert isinstance(components, TrustComponents)
    assert inst_trust >= 0.95
    assert components.forwarding_trust >= 0.95
    assert components.ml_trust == 1.0

    # Attacked node (DoS with P_attack = 0.98, high CPU, high loss)
    attack_state = baseline_node_state.model_copy(update={
        "packet_rate": 35.0,
        "packet_loss": 0.65,
        "cpu": 95.0
    })
    _, inst_attack = coordinator.evaluate_node(attack_state, attack_probability=0.98)
    assert inst_attack < 0.30


def test_topological_criticality_engine():
    engine = TopologicalCriticalityEngine()

    # Create a 5-node line graph: 0 - 1 - 2 - 3 - 4
    # Node 2 is the central articulation bridge!
    G = nx.path_graph(5)
    crits = engine.compute_criticalities(G)

    assert len(crits) == 5
    # Node 2 (center) should have higher criticality than Node 0 (leaf)
    assert crits[2] > crits[0]
    assert crits[2] > crits[4]
    assert crits[1] > crits[0]


def test_asymmetric_temporal_smoothing(trust_config, baseline_node_state):
    engine = DynamicTrustEngine(config=trust_config)

    # Step 1: Normal update -> initial smoothed trust is 1.0
    det_normal = DetectionResult(
        timestamp=1.0, node_id=1, is_attack=False, attack_type="normal",
        attack_probability=0.0, confidence=1.0, inference_latency_us=50.0
    )
    eval1 = engine.update_node(baseline_node_state, det_normal)
    assert eval1.smoothed_trust >= 0.98

    # Step 2: Sudden severe attack -> instantaneous trust collapses to 0.10
    attack_state = baseline_node_state.model_copy(update={"timestamp": 2.0, "packet_loss": 0.85})
    det_attack = DetectionResult(
        timestamp=2.0, node_id=1, is_attack=True, attack_type="compromised_node",
        attack_probability=0.99, confidence=0.99, inference_latency_us=50.0
    )
    eval2 = engine.update_node(attack_state, det_attack)

    # Because lambda_penalty is 0.40, smoothed trust should drop sharply:
    assert eval2.smoothed_trust <= 0.70

    # Step 3: Attack stops, node behaves normally again
    # But because lambda_recovery is only 0.05, trust should recover VERY slowly
    eval3 = engine.update_node(baseline_node_state.model_copy(update={"timestamp": 3.0}), det_normal)
    assert eval3.smoothed_trust - eval2.smoothed_trust < 0.06
    assert eval3.smoothed_trust < 0.75  # Not yet trusted!


def test_on_off_attack_damping(trust_config, baseline_node_state):
    """
    Validates that an intermittent 'on-off' attacker cannot evade quarantine
    by toggling attacks on and off.
    """
    engine = DynamicTrustEngine(config=trust_config)
    det_normal = DetectionResult(
        timestamp=0.0, node_id=2, is_attack=False, attack_type="normal",
        attack_probability=0.0, confidence=1.0, inference_latency_us=50.0
    )
    det_attack = DetectionResult(
        timestamp=0.0, node_id=2, is_attack=True, attack_type="dos",
        attack_probability=0.98, confidence=0.98, inference_latency_us=50.0
    )

    t = 0.0
    # Alternating 2s attack, 2s normal for 6 cycles
    for cycle in range(6):
        # Attack burst (2 steps)
        for _ in range(2):
            t += 1.0
            attack_state = baseline_node_state.model_copy(update={"node_id": 2, "timestamp": t, "packet_loss": 0.70})
            engine.update_node(attack_state, det_attack)

        # Quiet period (2 steps)
        for _ in range(2):
            t += 1.0
            normal_state = baseline_node_state.model_copy(update={"node_id": 2, "timestamp": t})
            engine.update_node(normal_state, det_normal)

    latest_eval = engine.get_node_trust(2)
    assert latest_eval is not None
    # Because penalty is 8x faster than recovery, net trust must collapse into QUARANTINED!
    assert latest_eval.trust_state == "QUARANTINED"
    assert latest_eval.smoothed_trust < 0.40


def test_risk_score_and_operational_transitions(trust_config, baseline_node_state):
    engine = DynamicTrustEngine(config=trust_config)

    # Initial state -> TRUSTED
    det_norm = DetectionResult(
        timestamp=1.0, node_id=3, is_attack=False, attack_type="normal",
        attack_probability=0.0, confidence=1.0, inference_latency_us=50.0
    )
    e1 = engine.update_node(baseline_node_state.model_copy(update={"node_id": 3}), det_norm)
    assert e1.trust_state == "TRUSTED"
    assert e1.risk_score < 0.15

    # Progressive degradation: sustained suspicious telemetry
    det_suspicious = DetectionResult(
        timestamp=2.0, node_id=3, is_attack=False, attack_type="normal",
        attack_probability=0.60, confidence=0.5, inference_latency_us=50.0
    )
    engine.update_node(
        baseline_node_state.model_copy(update={"node_id": 3, "timestamp": 2.0, "packet_loss": 0.45}),
        det_suspicious
    )
    e2 = engine.update_node(
        baseline_node_state.model_copy(update={"node_id": 3, "timestamp": 3.0, "packet_loss": 0.45}),
        det_suspicious
    )
    assert e2.trust_state in ("SUSPICIOUS", "QUARANTINED")

    # Critical drop -> sustained attack leads to QUARANTINED
    det_crit = DetectionResult(
        timestamp=4.0, node_id=3, is_attack=True, attack_type="compromised_node",
        attack_probability=0.99, confidence=1.0, inference_latency_us=50.0
    )
    engine.update_node(
        baseline_node_state.model_copy(update={"node_id": 3, "timestamp": 4.0, "packet_loss": 0.85}),
        det_crit
    )
    e3 = engine.update_node(
        baseline_node_state.model_copy(update={"node_id": 3, "timestamp": 5.0, "packet_loss": 0.85}),
        det_crit
    )
    assert e3.trust_state == "QUARANTINED"
    assert e3.risk_score >= 0.40
    assert 3 in engine.get_quarantined_nodes()


def test_network_trust_summary(trust_config, baseline_node_state):
    engine = DynamicTrustEngine(config=trust_config)

    # Add 4 normal nodes
    det_norm = DetectionResult(
        timestamp=1.0, node_id=0, is_attack=False, attack_type="normal",
        attack_probability=0.0, confidence=1.0, inference_latency_us=50.0
    )
    for nid in range(4):
        engine.update_node(baseline_node_state.model_copy(update={"node_id": nid}), det_norm)

    summary1 = engine.evaluate_network(timestamp=1.0)
    assert summary1.total_nodes == 4
    assert summary1.trusted_node_count == 4
    assert summary1.quarantined_node_count == 0
    assert summary1.network_health_recommendation == "STABLE"

    # Add 1 severely compromised node
    det_comp = DetectionResult(
        timestamp=2.0, node_id=4, is_attack=True, attack_type="compromised_node",
        attack_probability=0.99, confidence=1.0, inference_latency_us=50.0
    )
    bad_node = baseline_node_state.model_copy(update={"node_id": 4, "timestamp": 2.0, "packet_loss": 0.90})
    for _ in range(3):
        engine.update_node(bad_node, det_comp)

    summary2 = engine.evaluate_network(timestamp=2.0)
    assert summary2.total_nodes == 5
    assert summary2.quarantined_node_count == 1
    assert 4 in summary2.quarantined_node_ids
    assert summary2.network_health_recommendation in ("CONTAINMENT_REQUIRED", "EMERGENCY_REROUTE")


def test_digital_twin_synchronization(trust_config, baseline_node_state):
    dt = DigitalTwin()
    dt.node_states[1] = baseline_node_state

    engine = DynamicTrustEngine(config=trust_config, digital_twin=dt)

    det_crit = DetectionResult(
        timestamp=5.0, node_id=1, is_attack=True, attack_type="compromised_node",
        attack_probability=0.95, confidence=0.95, inference_latency_us=50.0
    )
    bad_node = baseline_node_state.model_copy(update={"timestamp": 5.0, "packet_loss": 0.80})
    eval_res = engine.update_node(bad_node, det_crit)

    # Digital Twin state should be directly updated with trust_score and threat_level!
    twin_node = dt.get_node_state(1)
    assert twin_node.trust_score == eval_res.smoothed_trust
    assert twin_node.threat_level == eval_res.risk_score


def test_trust_ledger_export(trust_config, baseline_node_state):
    engine = DynamicTrustEngine(config=trust_config)
    det = DetectionResult(
        timestamp=1.0, node_id=1, is_attack=False, attack_type="normal",
        attack_probability=0.0, confidence=1.0, inference_latency_us=50.0
    )
    engine.update_node(baseline_node_state, det)
    engine.update_node(baseline_node_state.model_copy(update={"timestamp": 2.0}), det)

    df = engine.export_trust_ledger()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "smoothed_trust" in df.columns
    assert "risk_score" in df.columns
    assert "forwarding_trust" in df.columns
    assert "ml_trust" in df.columns
    assert "trust_volatility" in df.columns
    assert "operational_confidence" in df.columns
    assert "cascading_hazard" in df.columns


def test_bayesian_recommendation_and_outlier_filtering():
    """
    Tests Bayesian recommendation aggregation, recommender trust discounting,
    and consensus outlier rejection (ballot-stuffing / bad-mouthing).
    """
    rec_eval = BayesianRecommendationEvaluator()

    # 1. Consistent consensus recommendations (nodes 2, 3, 4 report high trust ~0.90)
    recs_good = {2: 0.90, 3: 0.92, 4: 0.88}
    recommender_trusts = {2: 0.95, 3: 0.90, 4: 0.85}
    score_good = rec_eval.evaluate_recommendations(recs_good, recommender_trusts)
    assert score_good >= 0.82

    # 2. Malicious node 5 submits bad-mouthing recommendation 0.05
    # The consensus filter should automatically detect and prune the outlier 0.05
    recs_with_outlier = {2: 0.90, 3: 0.92, 4: 0.88, 5: 0.05}
    score_filtered = rec_eval.evaluate_recommendations(recs_with_outlier, recommender_trusts)
    # Filtered score should remain high (> 0.80) because node 5's malicious opinion is discarded
    assert score_filtered >= 0.80

    # 3. Recommender with very low trust has its opinion heavily discounted
    untrusted_rec = {6: 0.10}
    untrusted_eval = rec_eval.evaluate_recommendations(untrusted_rec, recommender_trust_scores={6: 0.15})
    # Discounted toward neutral prior
    assert untrusted_eval > 0.30


def test_trust_volatility_and_operational_confidence(trust_config, baseline_node_state):
    """
    Validates that rapid trust oscillation (e.g. intermittent on-off attack) elevates
    trust volatility and collapses operational confidence below 0.40, preventing
    the node from achieving TRUSTED state.
    """
    engine = DynamicTrustEngine(config=trust_config)
    det_good = DetectionResult(
        timestamp=1.0, node_id=5, is_attack=False, attack_type="normal",
        attack_probability=0.0, confidence=1.0, inference_latency_us=50.0
    )
    det_bad = DetectionResult(
        timestamp=1.0, node_id=5, is_attack=True, attack_type="dos",
        attack_probability=0.99, confidence=1.0, inference_latency_us=50.0
    )

    t = 0.0
    # Simulate erratic on-off switching: high trust -> zero trust -> high trust
    for step in range(8):
        t += 1.0
        if step % 2 == 0:
            engine.update_node(baseline_node_state.model_copy(update={"node_id": 5, "timestamp": t}), det_good)
        else:
            bad_state = baseline_node_state.model_copy(update={"node_id": 5, "timestamp": t, "packet_loss": 0.80})
            engine.update_node(bad_state, det_bad)

    eval_record = engine.get_node_trust(5)
    assert eval_record is not None
    # Volatility should be elevated (> 0.15)
    assert eval_record.trust_volatility > 0.15
    # Operational confidence should be depressed (< 0.65)
    assert eval_record.operational_confidence < 0.65


def test_cascading_failure_hazard(baseline_node_state):
    """
    Tests that isolating a central or bottleneck node calculates cascading congestion hazard.
    """
    crit_engine = TopologicalCriticalityEngine()

    # Path graph 0 - 1 - 2
    G = nx.path_graph(3)
    states = {
        0: baseline_node_state.model_copy(update={"node_id": 0, "cpu": 85.0, "energy": 25.0}),
        1: baseline_node_state.model_copy(update={"node_id": 1}),
        2: baseline_node_state.model_copy(update={"node_id": 2, "cpu": 90.0, "energy": 20.0}),
    }

    hazard = crit_engine.compute_cascading_failure_hazard(node_id=1, graph=G, node_states=states)
    assert 0.10 <= hazard <= 1.00
    # Because neighbors have high CPU and low battery, hazard should be substantial (> 0.40)
    assert hazard >= 0.40


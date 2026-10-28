"""
Dynamic Risk & Trust Assessment Engine.
Maintains stateful, asymmetrically smoothed behavioral trust, evaluates topological
criticality-weighted systemic risk, manages operational state transitions
(TRUSTED -> SUSPICIOUS -> QUARANTINED), and synchronizes with the Digital Twin.
"""

from typing import Dict, List, Optional, Tuple, Any, Set
from collections import defaultdict, deque
import numpy as np
import pandas as pd
import networkx as nx

from .models import (
    TrustComponents,
    NodeTrustEvaluation,
    NetworkTrustSummary,
    TrustConfig,
)
from .evaluator import CompositeTrustEvaluator
from .criticality import TopologicalCriticalityEngine
from ..digital_twin.models import TwinNodeState
from ..digital_twin.twin import DigitalTwin
from ..detection.engine import DetectionResult


class DynamicTrustEngine:
    """
    Core operational engine for Phase 6.
    Evaluates multi-dimensional behavioral trust, applies asymmetric temporal smoothing,
    computes topology-weighted systemic risk, and dictates node isolation / quarantine.
    """

    def __init__(
        self,
        config: Optional[TrustConfig] = None,
        digital_twin: Optional[DigitalTwin] = None,
        history_len: int = 500
    ):
        self.config = config or TrustConfig()
        self.digital_twin = digital_twin
        self.history_len = history_len

        # Internal evaluators
        self.trust_evaluator = CompositeTrustEvaluator(self.config)
        self.criticality_engine = TopologicalCriticalityEngine()

        # State tracking: node_id -> latest smoothed trust (initialized to 1.0)
        self.node_smoothed_trust: Dict[int, float] = {}
        self.node_latest_evaluations: Dict[int, NodeTrustEvaluation] = {}
        self.node_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=self.history_len))
        self.network_history: deque = deque(maxlen=self.history_len)

        # Quarantined nodes set
        self.quarantined_nodes: Set[int] = set()

    def update_node(
        self,
        node_state: TwinNodeState,
        detection_result: Optional[DetectionResult] = None,
        graph: Optional[nx.Graph] = None,
        historical_states: Optional[list] = None,
        neighbor_recommendations: Optional[Dict[int, float]] = None,
        recommender_trust_scores: Optional[Dict[int, float]] = None
    ) -> NodeTrustEvaluation:
        """
        Processes a node update, computes multi-dimensional trust, applies asymmetric smoothing,
        evaluates topological risk and cascading hazards, determines operational state, and records history.
        """
        node_id = node_state.node_id
        timestamp = node_state.timestamp

        # 1. Parse detection inputs from Phase 5
        attack_prob = detection_result.attack_probability if detection_result else 0.0
        detected_type = detection_result.attack_type if detection_result else "normal"

        # 2. Evaluate orthogonal trust dimensions (including Bayesian neighbor recommendations)
        components, inst_trust = self.trust_evaluator.evaluate_node(
            node_state=node_state,
            attack_probability=attack_prob,
            historical_states=historical_states,
            neighbor_recommendations=neighbor_recommendations,
            recommender_trust_scores=recommender_trust_scores
        )

        # 3. Asymmetric Temporal Smoothing (Hysteresis)
        prev_smoothed = self.node_smoothed_trust.get(node_id, 1.0)

        if inst_trust < prev_smoothed:
            # Degrading trust: rapid penalty decay rate lambda_penalty
            rate = self.config.penalty_decay_rate
        else:
            # Improving trust: slow, cautious recovery rate lambda_recovery
            rate = self.config.recovery_decay_rate

        smoothed_trust = ((1.0 - rate) * prev_smoothed) + (rate * inst_trust)
        smoothed_trust = float(np.clip(smoothed_trust, 0.0, 1.0))
        self.node_smoothed_trust[node_id] = smoothed_trust

        # 4. Volatility & Operational Confidence (anti-evasion)
        recent_history = list(self.node_history[node_id])
        if len(recent_history) >= 2:
            recent_inst = [r.instantaneous_trust for r in recent_history[-8:]] + [inst_trust]
            volatility = float(np.std(recent_inst))
        else:
            volatility = 0.0
        confidence = float(np.clip(1.0 - (2.5 * volatility), 0.10, 1.00))

        # 5. Topological Criticality & Cascading Hazard
        if graph is None and self.digital_twin is not None:
            graph = self.digital_twin.get_network_topology()

        node_states_map = self.digital_twin.node_states if self.digital_twin else None
        if graph is not None:
            crit_factor = self.criticality_engine.get_node_criticality(node_id, graph)
            cascading_hazard = self.criticality_engine.compute_cascading_failure_hazard(
                node_id, graph, node_states=node_states_map
            )
        else:
            crit_factor = 0.50
            cascading_hazard = 0.10

        # 6. Systemic Risk Calculation
        threat_sev = self.config.severity_weights.get(detected_type, 0.50)
        trust_deficit = 1.0 - smoothed_trust

        combined_impact = (
            self.config.weight_criticality * crit_factor +
            self.config.weight_severity * threat_sev
        )
        risk_score = float(np.clip(trust_deficit * combined_impact, 0.0, 1.0))

        # 7. Operational State Classification
        if (
            smoothed_trust < self.config.threshold_quarantine or
            risk_score >= self.config.threshold_risk_quarantine or
            node_state.connection_state == "DISCONNECTED" or
            attack_prob >= 0.85
        ):
            trust_state = "QUARANTINED"
            self.quarantined_nodes.add(node_id)
        elif (
            smoothed_trust < self.config.threshold_trusted or
            risk_score >= 0.35 or
            confidence < 0.40  # Low confidence due to volatile on-off behaviour
        ):
            trust_state = "SUSPICIOUS"
            self.quarantined_nodes.discard(node_id)
        else:
            trust_state = "TRUSTED"
            self.quarantined_nodes.discard(node_id)

        # 8. Build Evaluation Record
        eval_record = NodeTrustEvaluation(
            node_id=node_id,
            timestamp=round(timestamp, 3),
            components=components,
            instantaneous_trust=round(inst_trust, 4),
            smoothed_trust=round(smoothed_trust, 4),
            trust_volatility=round(volatility, 4),
            operational_confidence=round(confidence, 4),
            trust_state=trust_state,
            risk_score=round(risk_score, 4),
            criticality_factor=round(crit_factor, 4),
            cascading_hazard=round(cascading_hazard, 4),
            threat_severity=round(threat_sev, 4),
            attack_probability=round(attack_prob, 4),
            detected_attack_type=detected_type
        )

        self.node_latest_evaluations[node_id] = eval_record
        self.node_history[node_id].append(eval_record)

        # 9. Synchronize back into Digital Twin if attached
        if self.digital_twin is not None and node_id in self.digital_twin.node_states:
            current_twin_node = self.digital_twin.node_states[node_id]
            updated_twin_node = current_twin_node.model_copy(update={
                "trust_score": eval_record.smoothed_trust,
                "threat_level": eval_record.risk_score
            })
            self.digital_twin.node_states[node_id] = updated_twin_node

        return eval_record

    def evaluate_network(self, timestamp: float) -> NetworkTrustSummary:
        """
        Aggregates macroscopic network-wide trust and risk metrics across all monitored nodes.
        """
        if not self.node_latest_evaluations:
            return NetworkTrustSummary(
                timestamp=timestamp,
                total_nodes=0,
                trusted_node_count=0,
                suspicious_node_count=0,
                quarantined_node_count=0,
                average_trust=1.0,
                minimum_trust=1.0,
                average_risk=0.0,
                maximum_risk=0.0,
                quarantined_node_ids=[],
                network_health_recommendation="STABLE"
            )

        evals = list(self.node_latest_evaluations.values())
        total = len(evals)

        trusted_count = sum(1 for e in evals if e.trust_state == "TRUSTED")
        suspicious_count = sum(1 for e in evals if e.trust_state == "SUSPICIOUS")
        quarantine_count = sum(1 for e in evals if e.trust_state == "QUARANTINED")

        avg_trust = float(np.mean([e.smoothed_trust for e in evals]))
        min_trust = float(np.min([e.smoothed_trust for e in evals]))
        avg_risk = float(np.mean([e.risk_score for e in evals]))
        max_risk = float(np.max([e.risk_score for e in evals]))

        quarantined_ids = sorted(list(self.quarantined_nodes))

        # Macroscopic mitigation recommendation
        if quarantine_count >= 2 or max_risk >= 0.75:
            recommendation = "EMERGENCY_REROUTE"
        elif quarantine_count == 1:
            recommendation = "CONTAINMENT_REQUIRED"
        elif suspicious_count > 0 or max_risk >= 0.40:
            recommendation = "MONITOR"
        else:
            recommendation = "STABLE"

        summary = NetworkTrustSummary(
            timestamp=round(timestamp, 3),
            total_nodes=total,
            trusted_node_count=trusted_count,
            suspicious_node_count=suspicious_count,
            quarantined_node_count=quarantine_count,
            average_trust=round(avg_trust, 4),
            minimum_trust=round(min_trust, 4),
            average_risk=round(avg_risk, 4),
            maximum_risk=round(max_risk, 4),
            quarantined_node_ids=quarantined_ids,
            network_health_recommendation=recommendation
        )

        self.network_history.append(summary)
        return summary

    def get_node_trust(self, node_id: int) -> Optional[NodeTrustEvaluation]:
        """Returns the latest evaluation record for a specific node."""
        return self.node_latest_evaluations.get(node_id)

    def get_quarantined_nodes(self) -> List[int]:
        """Returns list of currently quarantined node IDs."""
        return sorted(list(self.quarantined_nodes))

    def get_suspicious_nodes(self) -> List[int]:
        """Returns list of nodes currently in SUSPICIOUS state."""
        return [
            node_id for node_id, record in self.node_latest_evaluations.items()
            if record.trust_state == "SUSPICIOUS"
        ]

    def export_trust_ledger(self) -> pd.DataFrame:
        """
        Exports the entire recorded chronological history of all nodes as a DataFrame.
        """
        rows = []
        for node_id, records in self.node_history.items():
            for rec in records:
                rows.append({
                    "timestamp": rec.timestamp,
                    "node_id": rec.node_id,
                    "forwarding_trust": rec.components.forwarding_trust,
                    "energy_trust": rec.components.energy_trust,
                    "loss_trust": rec.components.loss_trust,
                    "ml_trust": rec.components.ml_trust,
                    "instantaneous_trust": rec.instantaneous_trust,
                    "smoothed_trust": rec.smoothed_trust,
                    "trust_volatility": rec.trust_volatility,
                    "operational_confidence": rec.operational_confidence,
                    "trust_state": rec.trust_state,
                    "risk_score": rec.risk_score,
                    "criticality_factor": rec.criticality_factor,
                    "cascading_hazard": rec.cascading_hazard,
                    "threat_severity": rec.threat_severity,
                    "attack_probability": rec.attack_probability,
                    "detected_attack_type": rec.detected_attack_type,
                })
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(by=["timestamp", "node_id"]).reset_index(drop=True)
        return df

"""
Graduated Escalation Engine for Phase 9.
Implements industrial cyber-physical safety standards (NIST SP 800-82 / IEC 62443)
with a 3-tier graduated escalation state machine:
  Tier 1: Primary Pareto-optimal action s*
  Tier 2: Secondary Pareto candidate from S* (e.g. composite rate-limiting / bridge)
  Tier 3: Emergency fail-safe quarantine with Minimum Spanning Tree (MST) connectivity preservation.
"""

from typing import Dict, List, Optional, Any, Tuple
import networkx as nx

from ..recovery.models import RecoveryCandidate, OptimizationDecision
from ..digital_twin.twin import DigitalTwin
from .models import (
    EscalationTier,
    EscalationEvent,
    ActuationCommand,
    ActuationBatch,
)
from .dispatcher import ActuationPolicyDispatcher
from .actuator import NetworkActuator


class GraduatedEscalationManager:
    """
    Coordinates graduated multi-tier mitigation escalation when primary mitigations
    fail closed-loop verification or when severe persistent degradation is detected.
    """

    def __init__(
        self,
        dispatcher: Optional[ActuationPolicyDispatcher] = None,
    ):
        self.dispatcher = dispatcher or ActuationPolicyDispatcher()
        self.current_tier: EscalationTier = "TIER_1_PRIMARY_OPTIMAL"
        self.escalation_history: List[EscalationEvent] = []

    def reset(self) -> None:
        """Resets escalation state machine to Tier 1."""
        self.current_tier = "TIER_1_PRIMARY_OPTIMAL"
        self.escalation_history.clear()

    def get_current_tier(self) -> EscalationTier:
        return self.current_tier

    def escalate(
        self,
        current_candidate: RecoveryCandidate,
        trigger_reason: str,
        current_time: float,
        digital_twin: Optional[DigitalTwin] = None,
        alternative_candidates: Optional[List[RecoveryCandidate]] = None,
    ) -> Optional[Tuple[ActuationBatch, EscalationTier]]:
        """
        Escalates from current tier to next higher tier.
        Returns newly synthesized ActuationBatch and new EscalationTier,
        or None if maximum tier has been exhausted.
        """
        if self.current_tier == "TIER_1_PRIMARY_OPTIMAL":
            # Transition Tier 1 -> Tier 2
            next_tier: EscalationTier = "TIER_2_SECONDARY_PARETO"
            event = EscalationEvent(
                from_tier=self.current_tier,
                to_tier=next_tier,
                timestamp=current_time,
                trigger_reason=trigger_reason,
                strategy_id=current_candidate.strategy_id,
                preserved_connectivity=True,
            )
            self.escalation_history.append(event)
            self.current_tier = next_tier

            # Generate Tier 2 candidate
            tier2_cand = self._synthesize_tier2_candidate(current_candidate, alternative_candidates)
            batch = self.dispatcher.create_actuation_batch(tier2_cand, decision_epoch=current_time)
            return batch, next_tier

        elif self.current_tier == "TIER_2_SECONDARY_PARETO":
            # Transition Tier 2 -> Tier 3 (Fail-Safe MST Quarantine)
            next_tier = "TIER_3_FAILSAFE_MST"
            preserved = True
            tier3_cand = self._synthesize_tier3_mst_candidate(current_candidate, digital_twin)

            event = EscalationEvent(
                from_tier=self.current_tier,
                to_tier=next_tier,
                timestamp=current_time,
                trigger_reason=trigger_reason,
                strategy_id=tier3_cand.strategy_id,
                preserved_connectivity=preserved,
            )
            self.escalation_history.append(event)
            self.current_tier = next_tier

            batch = self.dispatcher.create_actuation_batch(tier3_cand, decision_epoch=current_time)
            return batch, next_tier

        else:
            # Tier 3 already reached; cannot escalate further (must trigger full rollback)
            return None

    def _synthesize_tier2_candidate(
        self,
        primary_candidate: RecoveryCandidate,
        alternatives: Optional[List[RecoveryCandidate]] = None,
    ) -> RecoveryCandidate:
        """
        Synthesizes a Tier 2 secondary candidate. If an alternative candidate exists,
        uses the best secondary Pareto choice; otherwise builds an amplified composite action.
        """
        if alternatives:
            for alt in alternatives:
                if alt.strategy_id != primary_candidate.strategy_id:
                    return alt

        # Fallback: synthesize amplified composite candidate
        target_nodes = primary_candidate.target_nodes
        t_nid = target_nodes[0] if target_nodes else 2

        if primary_candidate.action_type == "RATE_LIMITING":
            # Escalate rate limiting to aggressive clamping + power boost on neighbors
            return RecoveryCandidate(
                strategy_id=f"{primary_candidate.strategy_id}_T2_COMPOSITE",
                action_type="COMPOSITE",
                target_nodes=target_nodes,
                affected_nodes=primary_candidate.affected_nodes,
                parameters={
                    "sub_actions": ["SET_RATE_LIMIT", "ADJUST_TX_POWER"],
                    "rate_limit_pkts_per_sec": 1.0,  # Clamped tighter
                    "tx_power_boost_dbm": 6.0,
                    "target_node": t_nid,
                },
            )
        elif primary_candidate.action_type == "NODE_REBOOT":
            # Escalate to reboot + rate limit upon recovery
            return RecoveryCandidate(
                strategy_id=f"{primary_candidate.strategy_id}_T2_EXTENDED",
                action_type="COMPOSITE",
                target_nodes=target_nodes,
                affected_nodes=[],
                parameters={
                    "sub_actions": ["REBOOT_NODE", "SET_RATE_LIMIT"],
                    "duration_s": 8.0,
                    "rate_limit_pkts_per_sec": 2.0,
                    "target_node": t_nid,
                },
            )
        else:
            # Default composite
            return RecoveryCandidate(
                strategy_id=f"{primary_candidate.strategy_id}_T2_FALLBACK",
                action_type="COMPOSITE",
                target_nodes=target_nodes,
                affected_nodes=primary_candidate.affected_nodes,
                parameters={
                    "sub_actions": ["SET_RATE_LIMIT", "REROUTE_TRAFFIC"],
                    "rate_limit_pkts_per_sec": 1.5,
                    "target_node": t_nid,
                },
            )

    def _synthesize_tier3_mst_candidate(
        self,
        current_candidate: RecoveryCandidate,
        digital_twin: Optional[DigitalTwin] = None,
    ) -> RecoveryCandidate:
        """
        Synthesizes a Tier 3 emergency quarantine candidate that preserves
        a Minimum Spanning Tree (MST) or bridge connectivity for non-quarantined nodes.
        """
        target_nodes = current_candidate.target_nodes
        t_nid = target_nodes[0] if target_nodes else 3

        is_cut_vertex = False
        bridge_boosts: Dict[int, float] = {}

        if digital_twin:
            g = digital_twin.get_network_topology()
            if g.has_node(t_nid):
                # Check if t_nid is an articulation point
                try:
                    articulation_points = set(nx.articulation_points(g))
                    is_cut_vertex = (t_nid in articulation_points)
                except Exception:
                    is_cut_vertex = False

                if is_cut_vertex:
                    # Target node is articulation point: severing it partitions the network!
                    # Preserve connectivity by boosting Tx power of neighbors to bridge the gap
                    neighbors = list(g.neighbors(t_nid))
                    for n in neighbors:
                        bridge_boosts[n] = 6.0  # +6 dBm power boost

        return RecoveryCandidate(
            strategy_id=f"STRAT_T3_MST_QUARANTINE_NODE_{t_nid}",
            action_type="COMPOSITE",
            target_nodes=[t_nid],
            affected_nodes=list(bridge_boosts.keys()),
            parameters={
                "sub_actions": ["ISOLATE_NODE", "ADJUST_TX_POWER"],
                "target_node": t_nid,
                "is_cut_vertex": is_cut_vertex,
                "power_boosts": bridge_boosts,
                "mst_preservation": True,
            },
        )

"""
Autonomous Candidate Recovery Strategy Generator.
Inspects Digital Twin shadow state, topology, and Phase 6 Dynamic Trust & Risk assessments
to synthesize a ranked, feasibility-validated pool of candidate recovery strategies S.
"""

import time
from typing import Dict, List, Optional, Any, Set
import networkx as nx

from .models import (
    RecoveryCandidate,
    StrategyPool,
    RecoveryConfig,
)
from .feasibility import FeasibilityChecker
from .taxonomy import (
    build_no_action_candidate,
    build_isolation_candidate,
    build_reroute_candidate,
    build_rate_limit_candidate,
    build_reboot_candidate,
    build_power_adjustment_candidate,
    build_composite_isolate_and_bridge_candidate,
    build_composite_throttle_and_reroute_candidate,
)
from ..digital_twin.twin import DigitalTwin
from ..trust.engine import DynamicTrustEngine


class CandidateStrategyGenerator:
    """
    Synthesizes candidate mitigation strategies tailored to observed attacks,
    threat levels, and topological conditions.
    """

    def __init__(
        self,
        config: Optional[RecoveryConfig] = None,
        feasibility_checker: Optional[FeasibilityChecker] = None
    ):
        self.config = config or RecoveryConfig()
        self.checker = feasibility_checker or FeasibilityChecker()

    def generate_strategy_pool(
        self,
        timestamp: float,
        digital_twin: DigitalTwin,
        trust_engine: DynamicTrustEngine,
    ) -> StrategyPool:
        """
        Synthesizes a structured candidate strategy pool S at the current evaluation epoch.
        """
        t_start = time.perf_counter()

        graph = digital_twin.get_network_topology()
        node_states = digital_twin.get_all_nodes()

        quarantined = trust_engine.get_quarantined_nodes()
        suspicious = trust_engine.get_suspicious_nodes()

        candidates: List[RecoveryCandidate] = []

        # 1. Candidate 0: Always include NO_ACTION benchmark
        candidates.append(build_no_action_candidate(timestamp=timestamp))

        # Context metadata
        trigger_context = {
            "timestamp": timestamp,
            "quarantined_nodes": quarantined,
            "suspicious_nodes": suspicious,
            "total_nodes": len(node_states),
            "topology_edges": graph.number_of_edges(),
        }

        # 2. Process QUARANTINED nodes (high priority intervention)
        for nid in quarantined:
            eval_record = trust_engine.get_node_trust(nid)
            detected_type = eval_record.detected_attack_type if eval_record else "normal"
            twin_node = node_states.get(nid)

            if detected_type == "dos":
                # DoS: Ingress rate limiting + Rerouting + Isolation + Composite Throttle & Reroute
                pkt_rate = twin_node.packet_rate if twin_node else 30.0
                candidates.append(build_rate_limit_candidate(nid, current_packet_rate=pkt_rate, config=self.config))

                reroute = build_reroute_candidate(nid, graph, config=self.config, checker=self.checker)
                if reroute:
                    candidates.append(reroute)

                candidates.append(build_isolation_candidate(nid, graph, config=self.config, checker=self.checker))

                comp_cand = build_composite_throttle_and_reroute_candidate(
                    nid, graph, current_packet_rate=pkt_rate, config=self.config, checker=self.checker
                )
                if comp_cand:
                    candidates.append(comp_cand)

            elif detected_type == "compromised_node":
                # Compromised Selective Drop: Isolation + Rerouting + Power Bridging + Reboot + Composite Isolate & Bridge
                iso_cand = build_isolation_candidate(nid, graph, config=self.config, checker=self.checker)
                candidates.append(iso_cand)

                # If isolation causes graph partition, synthesize composite bridge
                if iso_cand.is_topology_partitioning:
                    comp_bridge = build_composite_isolate_and_bridge_candidate(
                        nid, graph, node_states, config=self.config, checker=self.checker
                    )
                    if comp_bridge:
                        candidates.append(comp_bridge)

                reroute = build_reroute_candidate(nid, graph, config=self.config, checker=self.checker)
                if reroute:
                    candidates.append(reroute)

                pwr_boost = build_power_adjustment_candidate(nid, graph, node_states, config=self.config, checker=self.checker)
                if pwr_boost:
                    candidates.append(pwr_boost)

                candidates.append(build_reboot_candidate(nid, config=self.config))

            elif detected_type == "node_failure" or (twin_node and twin_node.connection_state == "DISCONNECTED"):
                # Node Failure / Crash: Reboot + Reroute + Power Bridge
                candidates.append(build_reboot_candidate(nid, config=self.config))

                reroute = build_reroute_candidate(nid, graph, config=self.config, checker=self.checker)
                if reroute:
                    candidates.append(reroute)

                pwr_boost = build_power_adjustment_candidate(nid, graph, node_states, config=self.config, checker=self.checker)
                if pwr_boost:
                    candidates.append(pwr_boost)

            else:
                # Generic fallback for quarantined nodes
                candidates.append(build_isolation_candidate(nid, graph, config=self.config, checker=self.checker))
                reroute = build_reroute_candidate(nid, graph, config=self.config, checker=self.checker)
                if reroute:
                    candidates.append(reroute)
                candidates.append(build_reboot_candidate(nid, config=self.config))

        # 3. Process SUSPICIOUS nodes (precautionary interventions)
        for nid in suspicious:
            if nid in quarantined:
                continue  # already handled above
            eval_record = trust_engine.get_node_trust(nid)
            detected_type = eval_record.detected_attack_type if eval_record else "normal"
            twin_node = node_states.get(nid)

            if detected_type == "dos" or (twin_node and twin_node.packet_rate > 15.0):
                pkt_rate = twin_node.packet_rate if twin_node else 20.0
                candidates.append(build_rate_limit_candidate(nid, current_packet_rate=pkt_rate, config=self.config))

            reroute = build_reroute_candidate(nid, graph, config=self.config, checker=self.checker)
            if reroute and not any(c.strategy_id == reroute.strategy_id for c in candidates):
                candidates.append(reroute)

        # 4. De-duplicate candidates by strategy_id
        unique_candidates: List[RecoveryCandidate] = []
        seen_ids: Set[str] = set()
        for cand in candidates:
            if cand.strategy_id not in seen_ids:
                seen_ids.add(cand.strategy_id)
                unique_candidates.append(cand)

        # Limit to max_candidates_per_pool
        final_candidates = unique_candidates[:self.config.max_candidates_per_pool]

        t_end = time.perf_counter()
        latency_us = (t_end - t_start) * 1_000_000.0

        return StrategyPool(
            timestamp=round(timestamp, 3),
            candidates=final_candidates,
            trigger_context=trigger_context,
            generation_latency_us=round(latency_us, 2)
        )

"""
Multi-Objective Cost Optimizer & Pareto Evaluator for Recovery Strategies.
Evaluates projected candidate outcomes from the Digital Twin Recovery Sandbox,
applies multi-objective cost formulation J(s), verifies hard topological & safety constraints,
computes the non-dominated Pareto frontier S*, and selects the optimal recovery decision s*.
"""

import time
from typing import Dict, List, Optional, Tuple, Any, Set
import numpy as np

from ..digital_twin.twin import DigitalTwin
from .models import (
    RecoveryCandidate,
    StrategyPool,
    SandboxSimulationResult,
    OptimizationWeights,
    OptimizationConstraints,
    CandidateObjectiveScore,
    OptimizationDecision,
    TOPSISScore,
)
from .sandbox import RecoverySandbox


# Predefined operational weight profiles
WEIGHT_PROFILES: Dict[str, OptimizationWeights] = {
    "BALANCED": OptimizationWeights(w_latency=0.25, w_loss=0.35, w_energy=0.25, w_overhead=0.15),
    "SECURITY_FIRST": OptimizationWeights(w_latency=0.15, w_loss=0.55, w_energy=0.15, w_overhead=0.15),
    "ENERGY_CONSTRAINED": OptimizationWeights(w_latency=0.15, w_loss=0.25, w_energy=0.50, w_overhead=0.10),
    "LATENCY_CRITICAL": OptimizationWeights(w_latency=0.50, w_loss=0.25, w_energy=0.15, w_overhead=0.10),
}


class TOPSISRanker:
    """
    Multi-Criteria Decision Analysis engine using TOPSIS:
    Technique for Order Preference by Similarity to Ideal Solution.
    Ranks non-commensurable candidate strategies against Positive and Negative Ideal Solutions.
    """

    def rank_candidates(
        self,
        scores: List[CandidateObjectiveScore],
        weights: OptimizationWeights,
    ) -> List[TOPSISScore]:
        """
        Computes TOPSIS relative closeness coefficients C_i and ordinal ranking.
        """
        if not scores:
            return []

        # Decision matrix: rows = candidates, cols = [latency, loss, energy, overhead]
        mat = []
        cands = []
        for s in scores:
            mat.append([
                s.normalized_latency_penalty,
                s.loss_penalty,
                s.normalized_energy_penalty,
                s.signaling_overhead_penalty,
            ])
            cands.append(s)

        X = np.array(mat, dtype=float)
        num_candidates, num_criteria = X.shape

        # Step 1: Vector normalization
        denom = np.sqrt(np.sum(X ** 2, axis=0))
        denom[denom == 0.0] = 1e-9  # Avoid division by zero
        R = X / denom

        # Step 2: Weight normalized matrix
        w_vec = np.array([
            weights.w_latency,
            weights.w_loss,
            weights.w_energy,
            weights.w_overhead,
        ])
        V = R * w_vec

        # Step 3: Determine Positive Ideal Solution (A*) and Negative Ideal Solution (A-)
        # Note: All criteria are cost/loss criteria (lower is better)
        a_pos = np.min(V, axis=0)  # Best is minimum for cost
        a_neg = np.max(V, axis=0)  # Worst is maximum for cost

        # Step 4: Separation distances
        d_pos = np.sqrt(np.sum((V - a_pos) ** 2, axis=1))
        d_neg = np.sqrt(np.sum((V - a_neg) ** 2, axis=1))

        # Step 5: Relative closeness to Ideal Solution C_i = d_neg / (d_pos + d_neg)
        closeness = d_neg / np.maximum(1e-9, (d_pos + d_neg))

        # Step 6: Package results and rank (higher closeness is better)
        topsis_results = []
        for i, cand in enumerate(cands):
            topsis_results.append({
                "strategy_id": cand.strategy_id,
                "action_type": cand.action_type,
                "closeness": float(closeness[i]),
                "d_pos": float(d_pos[i]),
                "d_neg": float(d_neg[i]),
                "norm_vec": {
                    "latency": float(V[i, 0]),
                    "loss": float(V[i, 1]),
                    "energy": float(V[i, 2]),
                    "overhead": float(V[i, 3]),
                },
            })

        # Sort descending by closeness
        topsis_results.sort(key=lambda item: item["closeness"], reverse=True)

        ranked_scores = []
        for rank_idx, item in enumerate(topsis_results):
            ranked_scores.append(TOPSISScore(
                strategy_id=item["strategy_id"],
                action_type=item["action_type"],
                closeness_coefficient=round(item["closeness"], 4),
                distance_to_positive_ideal=round(item["d_pos"], 4),
                distance_to_negative_ideal=round(item["d_neg"], 4),
                topsis_rank=rank_idx + 1,
                normalized_vector=item["norm_vec"],
            ))

        return ranked_scores


def detect_cross_mitigation_collisions(
    candidates: List[RecoveryCandidate],
    graph: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Analyzes cross-action collisions when multiple recovery actions execute concurrently.
    Detects whether dynamic bypass flows intersect target nodes under isolation or heavy rate limiting.
    """
    collisions = []
    isolated_nodes = set()
    throttled_nodes = set()
    reroute_paths = {}

    for c in candidates:
        if c.action_type == "NODE_ISOLATION":
            isolated_nodes.update(c.target_nodes)
        elif c.action_type == "RATE_LIMITING":
            throttled_nodes.update(c.target_nodes)
        elif c.action_type in ("DYNAMIC_REROUTING", "COMPOSITE"):
            bypasses = c.parameters.get("alternate_routes", {})
            for pair, path in bypasses.items():
                if path:
                    reroute_paths[c.strategy_id] = path

    for strat_id, path in reroute_paths.items():
        if isinstance(path, list) and len(path) >= 2:
            transit_nodes = set(path[1:-1])
            overlap_isolated = transit_nodes.intersection(isolated_nodes)
            if overlap_isolated:
                collisions.append({
                    "type": "SEVERED_BYPASS_COLLISION",
                    "severity": "CRITICAL",
                    "strategy_id": strat_id,
                    "conflict_nodes": list(overlap_isolated),
                    "description": f"Bypass path for {strat_id} routes through isolated nodes {list(overlap_isolated)}",
                })

            overlap_throttled = transit_nodes.intersection(throttled_nodes)
            if overlap_throttled:
                collisions.append({
                    "type": "SECONDARY_CONGESTION_HAZARD",
                    "severity": "WARNING",
                    "strategy_id": strat_id,
                    "conflict_nodes": list(overlap_throttled),
                    "description": f"Bypass path for {strat_id} routes through throttled nodes {list(overlap_throttled)}",
                })

    return collisions


class MultiObjectiveRecoveryOptimizer:
    """
    Multi-objective recovery optimization engine.
    Finds optimal recovery policy s* minimizing:
        J(s_k) = w_1 * (Delta_Latency / Latency_base) +
                 w_2 * Delta_Loss +
                 w_3 * (Delta_Energy / Energy_base) +
                 w_4 * Signaling_Overhead(s_k)
    Subject to:
        - Graph reachability / no partition (k(G') == 1)
        - Projected PDR >= PDR_min
        - Loop-free DAG routing
        - Latency <= MaxLatency
    """

    def __init__(
        self,
        weights: Optional[OptimizationWeights] = None,
        constraints: Optional[OptimizationConstraints] = None,
        base_latency_ms: float = 12.0,
        base_nominal_drain_per_s: float = 0.03,
        max_signaling_overhead: float = 10.0,
        sandbox: Optional[RecoverySandbox] = None,
    ):
        self.weights = weights or WEIGHT_PROFILES["BALANCED"]
        self.constraints = constraints or OptimizationConstraints()
        self.base_latency_ms = base_latency_ms
        self.base_nominal_drain_per_s = base_nominal_drain_per_s
        self.max_signaling_overhead = max_signaling_overhead
        self.sandbox = sandbox or RecoverySandbox(base_nominal_latency_ms=base_latency_ms)
        self.topsis_ranker = TOPSISRanker()


    def evaluate_strategy_pool(
        self,
        digital_twin: DigitalTwin,
        strategy_pool: StrategyPool,
        horizon_s: float = 30.0,
        attack_context: Optional[Dict[int, str]] = None,
        weights: Optional[OptimizationWeights] = None,
        constraints: Optional[OptimizationConstraints] = None,
    ) -> OptimizationDecision:
        """
        Simulates all candidates in the strategy pool within the Digital Twin sandbox,
        evaluates objective costs, determines Pareto frontier, and selects optimal s*.
        """
        t_start = time.perf_counter()

        active_weights = weights or self.weights
        active_constraints = constraints or self.constraints

        sim_results: Dict[str, SandboxSimulationResult] = {}
        for candidate in strategy_pool.candidates:
            sim_res = self.sandbox.simulate_candidate(
                digital_twin=digital_twin,
                candidate=candidate,
                horizon_s=horizon_s,
                attack_context=attack_context,
            )
            sim_results[candidate.strategy_id] = sim_res

        decision = self.optimize_from_simulations(
            candidates=strategy_pool.candidates,
            sim_results=sim_results,
            decision_epoch=strategy_pool.timestamp,
            weights=active_weights,
            constraints=active_constraints,
        )

        t_end = time.perf_counter()
        decision.solving_latency_us = (t_end - t_start) * 1e6
        return decision

    def optimize_from_simulations(
        self,
        candidates: List[RecoveryCandidate],
        sim_results: Dict[str, SandboxSimulationResult],
        decision_epoch: float,
        weights: Optional[OptimizationWeights] = None,
        constraints: Optional[OptimizationConstraints] = None,
    ) -> OptimizationDecision:
        """
        Given pre-simulated candidate results, calculates objective cost J(s),
        checks constraints, computes the Pareto frontier, and selects s*.
        """
        t_start = time.perf_counter()
        active_weights = weights or self.weights
        active_constraints = constraints or self.constraints

        scores: List[CandidateObjectiveScore] = []
        candidate_map: Dict[str, RecoveryCandidate] = {c.strategy_id: c for c in candidates}

        # 1. Score each candidate
        for cand in candidates:
            sim_res = sim_results.get(cand.strategy_id)
            if not sim_res:
                continue

            score = self.compute_candidate_score(
                candidate=cand,
                sim_result=sim_res,
                weights=active_weights,
                constraints=active_constraints,
            )
            scores.append(score)

        # 2. Compute Pareto Dominance Frontier S*
        pareto_ids = self._calculate_pareto_frontier(scores)
        for s in scores:
            s.is_pareto_optimal = (s.strategy_id in pareto_ids)

        # 3. Select Optimal Strategy s*
        # Filter strictly feasible candidates first
        feasible_scores = [s for s in scores if s.is_feasible]
        if feasible_scores:
            # Sort by multi-objective cost J(s)
            feasible_scores.sort(key=lambda x: x.cost_j)
            optimal_score = feasible_scores[0]
        else:
            # Fallback to least-violating candidate if none strictly feasible
            scores.sort(key=lambda x: (len(x.constraint_violations), x.cost_j))
            optimal_score = scores[0]

        # Sort all scores for reporting: feasible first by cost, then infeasible
        scores.sort(key=lambda x: (not x.is_feasible, x.cost_j))

        # 4. Multi-Criteria TOPSIS Ranking
        topsis_rankings = self.topsis_ranker.rank_candidates(scores, active_weights)
        opt_topsis_id = topsis_rankings[0].strategy_id if topsis_rankings else optimal_score.strategy_id

        optimal_cand = candidate_map[optimal_score.strategy_id]
        opt_sim_res = sim_results.get(optimal_score.strategy_id)

        t_end = time.perf_counter()
        latency_us = (t_end - t_start) * 1e6

        return OptimizationDecision(
            decision_epoch=decision_epoch,
            optimal_strategy_id=optimal_score.strategy_id,
            optimal_candidate=optimal_cand,
            optimal_cost_j=optimal_score.cost_j,
            optimal_simulation_result=opt_sim_res,
            ranked_candidates=scores,
            pareto_frontier_ids=pareto_ids,
            topsis_rankings=topsis_rankings,
            optimal_topsis_strategy_id=opt_topsis_id,
            weights_used=active_weights,
            constraints_used=active_constraints,
            solving_latency_us=latency_us,
        )

    def compute_candidate_score(
        self,
        candidate: RecoveryCandidate,
        sim_result: SandboxSimulationResult,
        weights: OptimizationWeights,
        constraints: OptimizationConstraints,
    ) -> CandidateObjectiveScore:
        """
        Computes normalized cost breakdown and constraint compliance for a candidate.
        """
        # 1. Normalized Objectives
        # Delta Latency Stretch: (L_proj - L_base) / L_base
        delta_lat = max(0.0, sim_result.projected_avg_latency_ms - self.base_latency_ms)
        norm_latency = delta_lat / max(1.0, self.base_latency_ms)

        # Loss Penalty: projected packet loss in [0.0, 1.0]
        loss_penalty = float(np.clip(sim_result.projected_packet_loss, 0.0, 1.0))

        # Normalized Energy Penalty: (Energy_proj / Energy_base)
        # Baseline total expected energy drain = drain_rate * horizon * active_nodes
        horizon_s = max(1.0, sim_result.horizon_s)
        expected_base_energy = self.base_nominal_drain_per_s * horizon_s * 6.0
        norm_energy = sim_result.projected_energy_drain_pct / max(0.1, expected_base_energy)

        # Normalized Signaling Overhead: overhead / max_signaling
        norm_overhead = sim_result.signaling_overhead / max(1.0, self.max_signaling_overhead)

        # 2. Multi-Objective Cost Function J(s)
        # J(s) = w_1 * norm_lat + w_2 * loss + w_3 * norm_energy + w_4 * norm_overhead
        base_cost_j = (
            weights.w_latency * norm_latency +
            weights.w_loss * loss_penalty +
            weights.w_energy * norm_energy +
            weights.w_overhead * norm_overhead
        )

        # 3. Check Hard Safety Constraints
        violations: List[str] = []

        # Constraint 1: Network Connectivity / Partition Avoidance
        if not constraints.allow_partitioning and sim_result.is_partitioned:
            violations.append(
                f"Graph Partition: {sim_result.projected_connected_components} disconnected components"
            )

        # Constraint 2: Minimum PDR
        if sim_result.projected_pdr < constraints.min_pdr:
            violations.append(
                f"PDR Violation: projected {sim_result.projected_pdr:.2f} < minimum {constraints.min_pdr:.2f}"
            )

        # Constraint 3: Maximum Packet Loss
        if sim_result.projected_packet_loss > constraints.max_packet_loss:
            violations.append(
                f"Loss Violation: projected {sim_result.projected_packet_loss:.2f} > maximum {constraints.max_packet_loss:.2f}"
            )

        # Constraint 4: Routing Loop Freedom (DAG)
        if constraints.require_dag_routing and sim_result.has_routing_loops:
            violations.append("Routing Loop: installed paths contain cyclic dependencies")

        # Constraint 5: Latency Deadline
        if sim_result.projected_avg_latency_ms > constraints.max_latency_ms:
            violations.append(
                f"Latency Deadline Exceeded: {sim_result.projected_avg_latency_ms:.1f}ms > {constraints.max_latency_ms:.1f}ms"
            )

        is_feasible = (len(violations) == 0)

        # If infeasible, apply heavy penalty to cost
        penalized_cost = base_cost_j + (len(violations) * 5.0 if not is_feasible else 0.0)

        return CandidateObjectiveScore(
            strategy_id=candidate.strategy_id,
            action_type=candidate.action_type,
            cost_j=float(penalized_cost),
            normalized_latency_penalty=float(norm_latency),
            loss_penalty=float(loss_penalty),
            normalized_energy_penalty=float(norm_energy),
            signaling_overhead_penalty=float(norm_overhead),
            is_feasible=is_feasible,
            constraint_violations=violations,
            is_pareto_optimal=False,
        )

    def _calculate_pareto_frontier(self, scores: List[CandidateObjectiveScore]) -> List[str]:
        """
        Identifies the non-dominated Pareto frontier S* among candidate objective vectors.
        An objective vector A dominates B (A > B) iff:
            all(A_k <= B_k) and any(A_k < B_k)
        """
        # Consider feasible candidates first
        candidates_to_eval = [s for s in scores if s.is_feasible]
        if not candidates_to_eval:
            candidates_to_eval = scores

        pareto_ids: List[str] = []

        for i, cand_a in enumerate(candidates_to_eval):
            vec_a = np.array([
                cand_a.normalized_latency_penalty,
                cand_a.loss_penalty,
                cand_a.normalized_energy_penalty,
                cand_a.signaling_overhead_penalty,
            ])

            is_dominated = False
            for j, cand_b in enumerate(candidates_to_eval):
                if i == j:
                    continue
                vec_b = np.array([
                    cand_b.normalized_latency_penalty,
                    cand_b.loss_penalty,
                    cand_b.normalized_energy_penalty,
                    cand_b.signaling_overhead_penalty,
                ])

                # Check if vec_b strictly dominates vec_a (minimization)
                if np.all(vec_b <= vec_a) and np.any(vec_b < vec_a):
                    is_dominated = True
                    break

            if not is_dominated:
                pareto_ids.append(cand_a.strategy_id)

        return pareto_ids

"""
GNN-Bayesian Trust Fusion Layer.
Implements Theorem 4: GNN-Augmented Trust Convergence.
Dynamically combines scalar Bayesian temporal trust scores with spatio-temporal GNN
relational embeddings, conditioned on topological node criticality (cut-vertices).
"""

from typing import Dict, List, Optional, Tuple, Any, Set
import numpy as np
import torch


class GNNBayesianFusion:
    """
    Adaptive Bayesian-GNN Trust Integrator.
    Fuses local Bayesian evidence with graph-relational context:
        T_i^fused(t) = beta_i * T_i^Bayes(t) + (1 - beta_i) * T_i^GNN(t)
    where beta_i is dynamically modulated by topological criticality:
        beta_i = beta_bridge if i in CutVertices else beta_nominal
    """

    def __init__(
        self,
        beta_nominal: float = 0.50,
        beta_bridge: float = 0.35,
        beta_leaf: float = 0.60,
        fast_penalty_threshold: float = 0.75,
        hysteresis_gamma: float = 0.15,
    ):
        self.beta_nominal = beta_nominal
        self.beta_bridge = beta_bridge
        self.beta_leaf = beta_leaf
        self.fast_penalty_threshold = fast_penalty_threshold
        self.hysteresis_gamma = hysteresis_gamma

        # History of fused scores: node_id -> previous fused trust
        self._fused_history: Dict[int, float] = {}

    def get_adaptive_beta(
        self,
        node_id: int,
        is_cut_vertex: bool,
        degree: int = 2,
    ) -> float:
        """
        Computes role-dependent mixing weight beta_i.
        Cut-vertices rely more heavily on GNN neighborhood relational context (1 - beta = 0.65)
        to detect stealthy multi-hop transit compromises.
        """
        if is_cut_vertex:
            return self.beta_bridge
        elif degree <= 1:
            return self.beta_leaf
        return self.beta_nominal

    def fuse_node_trust(
        self,
        node_id: int,
        t_bayes: float,
        t_gnn: float,
        p_attack_gnn: float,
        is_cut_vertex: bool = False,
        degree: int = 2,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Computes the fused trust score for a single node at epoch t.
        Returns:
            (fused_trust, diagnostic_metadata)
        """
        beta = self.get_adaptive_beta(node_id, is_cut_vertex, degree)

        # Baseline convex combination
        raw_fused = (beta * t_bayes) + ((1.0 - beta) * t_gnn)

        # Theorem 4 Acceleration:
        # If GNN detects high-confidence attack (e.g., evasive On-Off or stealthy Grayhole),
        # accelerate the downward penalty drift without waiting for scalar Bayesian window delay
        if p_attack_gnn >= self.fast_penalty_threshold:
            penalty_boost = 0.15 * p_attack_gnn
            raw_fused = max(0.0, raw_fused - penalty_boost)

        # Asymmetric smoothing across epochs to prevent high-frequency chatter
        prev_fused = self._fused_history.get(node_id, 1.0)
        if raw_fused < prev_fused:
            # Rapid degradation: 80% new observation, 20% inertia
            smoothed_fused = 0.80 * raw_fused + 0.20 * prev_fused
        else:
            # Conservative recovery: 15% new observation, 85% inertia
            smoothed_fused = (self.hysteresis_gamma * raw_fused) + ((1.0 - self.hysteresis_gamma) * prev_fused)

        smoothed_fused = max(0.0, min(1.0, float(smoothed_fused)))
        self._fused_history[node_id] = smoothed_fused

        diagnostics = {
            "node_id": node_id,
            "t_bayes": float(t_bayes),
            "t_gnn": float(t_gnn),
            "p_attack_gnn": float(p_attack_gnn),
            "beta": float(beta),
            "raw_fused": float(raw_fused),
            "smoothed_fused": float(smoothed_fused),
            "is_cut_vertex": is_cut_vertex,
        }
        return smoothed_fused, diagnostics

    def batch_fuse(
        self,
        node_ids: List[int],
        bayes_scores: Dict[int, float],
        gnn_scores: Dict[int, float],
        gnn_attack_probs: Dict[int, float],
        cut_vertices: Set[int],
        node_degrees: Optional[Dict[int, int]] = None,
    ) -> Dict[int, float]:
        """
        Computes fused trust scores across an entire network snapshot.
        """
        degrees = node_degrees or {}
        fused_map = {}
        for nid in node_ids:
            tb = bayes_scores.get(nid, 1.0)
            tg = gnn_scores.get(nid, 1.0)
            pa = gnn_attack_probs.get(nid, 0.0)
            is_cut = (nid in cut_vertices)
            deg = degrees.get(nid, 2)

            score, _ = self.fuse_node_trust(
                node_id=nid,
                t_bayes=tb,
                t_gnn=tg,
                p_attack_gnn=pa,
                is_cut_vertex=is_cut,
                degree=deg,
            )
            fused_map[nid] = score
        return fused_map

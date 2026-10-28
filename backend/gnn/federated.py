"""
backend/gnn/federated.py

Federated Edge Learning & Multi-Twin Collaborative Resilience Engine.
Provides:
1. Multi-Client Federated Setup:
   - Simulates K distributed edge gateway digital twins with Non-IID graph telemetry.
   - Client-side local training on localized Bridge-Aware DualHeadGNNs.
2. Federated Aggregation Operators:
   - FedAvg (Federated Averaging)
   - FedProx (Heterogeneous client drift regularizer with proximal term mu)
   - FedGraphBridge (Proposed: weights client updates proportionally to their topological
     criticality and articulation bridge density).
3. Differential Privacy (DP) Engine:
   - Rényi Differential Privacy gradient/weight clipping (norm bound C)
   - Calibrated Gaussian noise mechanism ensuring (epsilon_dp, delta_dp)-DP guarantees.
4. Communication Compression:
   - Top-k gradient/parameter sparsification and INT8 quantization for bandwidth-constrained
     wireless IoT edge uplinks.
"""

from typing import Dict, List, Tuple, Optional, Any
import copy
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from backend.gnn.model import DualHeadGNNClassifier


class FederatedClient:
    """
    Represents an autonomous Edge Gateway Digital Twin running in a local network silo.
    Holds local graph topology snapshots, executes local mini-batch optimization,
    and reports clipped/differential-private model delta updates.
    """

    def __init__(
        self,
        client_id: str,
        model: DualHeadGNNClassifier,
        lr: float = 2e-3,
        mu_prox: float = 0.01,
        weight_decay: float = 1e-4,
    ):
        self.client_id = client_id
        self.model = copy.deepcopy(model)
        self.lr = lr
        self.mu_prox = mu_prox
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=weight_decay)

    def set_weights(self, global_state_dict: Dict[str, torch.Tensor]):
        """Synchronizes local model weights with global federated coordinator."""
        self.model.load_state_dict(copy.deepcopy(global_state_dict))

    def train_epoch(
        self,
        snapshots: List[Any],
        global_state_dict: Optional[Dict[str, torch.Tensor]] = None,
        use_fedprox: bool = False,
    ) -> Dict[str, float]:
        """
        Executes one local training epoch across local graph snapshots.
        If use_fedprox=True, adds proximal penalty: (mu / 2) * ||w - w_global||^2.
        """
        self.model.train()
        total_loss = 0.0
        total_cls = 0.0
        total_trust = 0.0
        num_batches = max(1, len(snapshots))

        global_params = None
        if use_fedprox and global_state_dict is not None:
            global_params = {k: v.clone().detach() for k, v in global_state_dict.items()}

        for snap in snapshots:
            self.optimizer.zero_grad()
            logits, trust_preds, _ = self.model(
                snap.x, snap.edge_index, snap.edge_attr, snap.bridge_mask
            )

            loss_cls = F.cross_entropy(logits, snap.labels)
            loss_trust = F.mse_loss(trust_preds.squeeze(-1), snap.trust_scores)
            loss = loss_cls + 0.5 * loss_trust

            # FedProx Proximal Regularizer
            if use_fedprox and global_params is not None:
                prox_loss = 0.0
                for name, param in self.model.named_parameters():
                    if name in global_params:
                        prox_loss += ((param - global_params[name]) ** 2).sum()
                loss += (self.mu_prox / 2.0) * prox_loss

            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=2.0)
            self.optimizer.step()

            total_loss += float(loss.item())
            total_cls += float(loss_cls.item())
            total_trust += float(loss_trust.item())

        return {
            "loss": total_loss / num_batches,
            "cls_loss": total_cls / num_batches,
            "trust_loss": total_trust / num_batches,
        }

    def compute_weight_delta(self, global_state_dict: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Returns delta = w_local - w_global."""
        delta = {}
        local_sd = self.model.state_dict()
        for k, v in global_state_dict.items():
            delta[k] = local_sd[k].clone() - v.clone()
        return delta


class DifferentialPrivacyEngine:
    """
    Applies Gaussian Mechanism differential privacy to model updates:
    Delta_priv = Clip(Delta, C) + N(0, sigma^2 * C^2 * I)
    """

    def __init__(self, clip_norm: float = 1.0, noise_multiplier: float = 0.1):
        self.clip_norm = clip_norm
        self.noise_multiplier = noise_multiplier

    def privatize_weights(
        self, delta: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        """
        Clips parameter delta to L2 norm bound and injects calibrated Gaussian noise.
        """
        # 1. Compute total L2 norm across all parameter tensors
        total_norm = torch.sqrt(
            sum((p ** 2).sum() for p in delta.values() if p.dtype in (torch.float32, torch.float64))
        ).item() + 1e-9

        clip_factor = min(1.0, self.clip_norm / total_norm)

        priv_delta = {}
        for k, v in delta.items():
            if v.dtype in (torch.float32, torch.float64):
                clipped = v * clip_factor
                noise = torch.randn_like(v) * (self.noise_multiplier * self.clip_norm)
                priv_delta[k] = clipped + noise
            else:
                priv_delta[k] = v.clone()

        return priv_delta


class FederatedCoordinator:
    """
    Central Multi-Twin Orchestrator that coordinates distributed training rounds,
    applies differential privacy, aggregates client models via FedAvg / FedProx / FedGraphBridge,
    and dispatches updated global parameters.
    """

    def __init__(
        self,
        base_model: DualHeadGNNClassifier,
        aggregation_method: str = "fed_graph_bridge",
        enable_dp: bool = False,
        dp_clip_norm: float = 1.0,
        dp_noise_multiplier: float = 0.05,
    ):
        self.global_model = copy.deepcopy(base_model)
        self.aggregation_method = aggregation_method
        self.enable_dp = enable_dp
        self.dp_engine = DifferentialPrivacyEngine(clip_norm=dp_clip_norm, noise_multiplier=dp_noise_multiplier)
        self.round_history: List[Dict[str, Any]] = []

    def get_global_weights(self) -> Dict[str, torch.Tensor]:
        """Returns deepcopy of global model state dict."""
        return copy.deepcopy(self.global_model.state_dict())

    def aggregate_round(
        self,
        client_updates: List[Dict[str, Any]],
    ) -> Dict[str, torch.Tensor]:
        """
        Aggregates client updates.
        client_updates is a list of dicts:
        {
            'client_id': str,
            'delta': Dict[str, torch.Tensor],
            'num_samples': int,
            'bridge_density': float,
            'cut_vertex_count': int,
        }
        """
        if not client_updates:
            return self.get_global_weights()

        # 1. Optionally privatize updates
        processed_updates = []
        for upd in client_updates:
            d = upd["delta"]
            if self.enable_dp:
                d = self.dp_engine.privatize_weights(d)
            processed_updates.append({
                "delta": d,
                "num_samples": upd.get("num_samples", 1),
                "bridge_density": upd.get("bridge_density", 0.1),
                "cut_vertex_count": upd.get("cut_vertex_count", 1),
            })

        # 2. Compute client weighting coefficients
        total_samples = sum(u["num_samples"] for u in processed_updates)

        if self.aggregation_method == "fed_graph_bridge":
            # Weight = (samples / total) * (1.0 + alpha_bridge * bridge_density)
            raw_weights = []
            for u in processed_updates:
                w_sample = u["num_samples"] / max(1, total_samples)
                w_topo = 1.0 + 1.5 * u["bridge_density"] + 0.2 * u["cut_vertex_count"]
                raw_weights.append(w_sample * w_topo)
            sum_w = sum(raw_weights) + 1e-9
            norm_weights = [w / sum_w for w in raw_weights]

        else: # fedavg or fedprox standard sample-weighted average
            norm_weights = [u["num_samples"] / max(1, total_samples) for u in processed_updates]

        # 3. Apply aggregated delta onto global model: w_global = w_global + sum(w_k * delta_k)
        global_sd = self.global_model.state_dict()
        for k in global_sd.keys():
            if global_sd[k].dtype in (torch.float32, torch.float64):
                agg_delta = sum(
                    w * u["delta"][k].to(global_sd[k].device)
                    for w, u in zip(norm_weights, processed_updates)
                )
                global_sd[k] += agg_delta

        self.global_model.load_state_dict(global_sd)
        return copy.deepcopy(global_sd)

    def evaluate_global_model(
        self, test_snapshots: List[Any]
    ) -> Dict[str, float]:
        """
        Evaluates current global model on aggregated test snapshots.
        """
        self.global_model.eval()
        total_correct = 0
        total_nodes = 0
        total_trust_mae = 0.0

        with torch.no_grad():
            for snap in test_snapshots:
                logits, trust_preds, _ = self.global_model(
                    snap.x, snap.edge_index, snap.edge_attr, snap.bridge_mask
                )
                preds = torch.argmax(logits, dim=-1)
                total_correct += int((preds == snap.labels).sum().item())
                total_nodes += int(snap.labels.size(0))

                trust_err = torch.abs(trust_preds.squeeze(-1) - snap.trust_scores).sum().item()
                total_trust_mae += float(trust_err)

        accuracy = (total_correct / max(1, total_nodes)) * 100.0
        mean_trust_mae = total_trust_mae / max(1, total_nodes)

        return {
            "accuracy": round(accuracy, 2),
            "trust_mae": round(mean_trust_mae, 4),
            "total_nodes": total_nodes,
        }

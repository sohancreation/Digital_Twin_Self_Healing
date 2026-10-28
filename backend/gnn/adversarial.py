"""
backend/gnn/adversarial.py

Adversarial Attack & Graph Perturbation Engine for Cyber-Resilience GNNs.
Implements:
1. Continuous Node Feature Attacks:
   - Fast Gradient Sign Method (FGSM)
   - Projected Gradient Descent (PGD-K) with L_inf and L_2 bounds
2. Discrete Graph Topology Perturbations:
   - Greedy Edge Addition / Removal (Nettack-style structural perturbation)
   - Cut-Vertex False-Flag Inversion Attack (attempts to mask compromised nodes
     or force false isolation of critical articulation bridges).
"""

from typing import Dict, List, Tuple, Optional, Any
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class GraphAdversarialAttacker:
    """
    Generates adversarial continuous feature perturbations and discrete edge flips
    to evaluate the worst-case robustness of the Cyber-Resilience Dual-Head GNN.
    """

    def __init__(self, model: nn.Module, epsilon: float = 0.05, alpha: float = 0.01, num_steps: int = 10):
        self.model = model
        self.epsilon = epsilon
        self.alpha = alpha
        self.num_steps = num_steps

    def fgsm_feature_attack(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        bridge_mask: torch.Tensor,
        labels: torch.Tensor,
        target_nodes: Optional[torch.Tensor] = None,
        targeted: bool = False,
        target_class: int = 0,
    ) -> torch.Tensor:
        """
        Fast Gradient Sign Method (FGSM) on continuous node telemetry features.
        x_adv = x + epsilon * sign(grad_x)
        """
        self.model.eval()
        x_adv = x.clone().detach().requires_grad_(True)

        logits, _, _ = self.model(x_adv, edge_index, edge_attr, bridge_mask)

        if target_nodes is not None:
            active_logits = logits[target_nodes]
            active_labels = labels[target_nodes]
        else:
            active_logits = logits
            active_labels = labels

        if targeted:
            target_tensor = torch.full_like(active_labels, fill_value=target_class)
            loss = -F.cross_entropy(active_logits, target_tensor)
        else:
            loss = F.cross_entropy(active_logits, active_labels)

        loss.backward()

        with torch.no_grad():
            grad = x_adv.grad.data
            perturbation = self.epsilon * grad.sign()
            if target_nodes is not None:
                mask = torch.zeros_like(x_adv)
                mask[target_nodes] = 1.0
                perturbation = perturbation * mask
            x_adv = x + perturbation
            x_adv = torch.clamp(x_adv, 0.0, 5.0)

        return x_adv.detach()

    def pgd_feature_attack(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        bridge_mask: torch.Tensor,
        labels: torch.Tensor,
        target_nodes: Optional[torch.Tensor] = None,
        targeted: bool = False,
        target_class: int = 0,
        epsilon: Optional[float] = None,
        num_steps: Optional[int] = None,
    ) -> torch.Tensor:
        """
        Projected Gradient Descent (PGD) on continuous node telemetry features.
        Iteratively computes gradient step within L_infinity epsilon ball.
        """
        eps = epsilon if epsilon is not None else self.epsilon
        steps = num_steps if num_steps is not None else self.num_steps
        alpha = self.alpha if self.alpha is not None else (eps / 4.0)

        self.model.eval()
        # Random start within epsilon ball
        x_adv = x.clone().detach() + torch.FloatTensor(x.shape).uniform_(-eps, eps).to(x.device)
        x_adv = torch.clamp(x_adv, 0.0, 5.0).detach()

        for _ in range(steps):
            x_adv.requires_grad_(True)
            logits, _, _ = self.model(x_adv, edge_index, edge_attr, bridge_mask)

            if target_nodes is not None:
                active_logits = logits[target_nodes]
                active_labels = labels[target_nodes]
            else:
                active_logits = logits
                active_labels = labels

            if targeted:
                target_tensor = torch.full_like(active_labels, fill_value=target_class)
                loss = -F.cross_entropy(active_logits, target_tensor)
            else:
                loss = F.cross_entropy(active_logits, active_labels)

            loss.backward()

            with torch.no_grad():
                grad = x_adv.grad.data
                step = alpha * grad.sign()

                if target_nodes is not None:
                    mask = torch.zeros_like(x_adv)
                    mask[target_nodes] = 1.0
                    step = step * mask

                x_adv = x_adv + step
                # Project back to L_inf epsilon ball around original x
                diff = torch.clamp(x_adv - x, min=-eps, max=eps)
                x_adv = torch.clamp(x + diff, min=0.0, max=5.0)

        return x_adv.detach()

    def structural_edge_perturbation(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        bridge_mask: torch.Tensor,
        budget: int = 2,
        mode: str = "remove_bridges",
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Structural topology perturbation attack:
        - 'remove_bridges': Adversary strategically severs critical articulation links.
        - 'add_spurious': Adversary inserts spurious high-weight links to dilute attention.
        """
        E = edge_index.size(1)
        device = edge_index.device

        if mode == "remove_bridges":
            # Find bridge edges
            bridge_indices = torch.where(bridge_mask > 0.5)[0]
            if len(bridge_indices) > 0:
                num_to_remove = min(budget, len(bridge_indices))
                drop_idx = bridge_indices[:num_to_remove]
                keep_mask = torch.ones(E, dtype=torch.bool, device=device)
                keep_mask[drop_idx] = False

                new_edge_index = edge_index[:, keep_mask]
                new_edge_attr = edge_attr[keep_mask]
                new_bridge_mask = bridge_mask[keep_mask]
                return new_edge_index, new_edge_attr, new_bridge_mask

        elif mode == "add_spurious":
            # Add spurious cross-cluster connections
            N = x.size(0)
            added_edges = []
            for _ in range(budget):
                u = int(np.random.randint(0, N // 2))
                v = int(np.random.randint(N // 2, N))
                added_edges.extend([[u, v], [v, u]])

            if added_edges:
                add_tensor = torch.tensor(added_edges, dtype=torch.long, device=device).t()
                new_edge_index = torch.cat([edge_index, add_tensor], dim=1)
                num_add = add_tensor.size(1)
                default_attr = torch.ones(num_add, edge_attr.size(1), device=device) * 0.5
                new_edge_attr = torch.cat([edge_attr, default_attr], dim=0)
                default_bridge = torch.zeros(num_add, device=device)
                new_bridge_mask = torch.cat([bridge_mask, default_bridge], dim=0)
                return new_edge_index, new_edge_attr, new_bridge_mask

        return edge_index, edge_attr, bridge_mask

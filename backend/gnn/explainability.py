"""
GNN Explainability & Attention Interpretability Engine.
Extracts multi-head attention distributions, edge importance attribution,
and input feature sensitivity gradients across IoT cyber-resilience models.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import networkx as nx
import torch
import torch.nn.functional as F

from .model import DualHeadGNNClassifier, BridgeAwareGATLayer


class GNNAttentionExplainer:
    """
    Computes and attributes edge attention weights and feature gradients
    for DualHeadGNNClassifier predictions.
    """

    FEATURE_NAMES = [
        "Packet Delivery Ratio (PDR)",
        "Traffic Load Norm",
        "Latency Norm",
        "Energy Level",
        "Trust Score",
        "Forwarding Ratio",
        "Loss Rolling Std",
        "Cut-Vertex Indicator",
        "Mean Neighbor PDR",
        "Min Neighbor Trust",
        "CPU Utilization",
        "Cycle Signature (On-Off)",
    ]

    CLASS_NAMES = ["Normal", "DoS Flood", "Selective Drop", "Node Failure", "On-Off Evasion"]

    def __init__(self, model: DualHeadGNNClassifier):
        self.model = model
        self.model.eval()

    def extract_edge_attention(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        bridge_mask: torch.Tensor,
    ) -> np.ndarray:
        """
        Computes the multi-head attention weights alpha_ij for layer 1 GAT.
        Returns:
            mean_edge_attention: [E] array of mean attention values averaged across heads.
        """
        layer: BridgeAwareGATLayer = self.model.encoder.gat1
        with torch.no_grad():
            N = x.size(0)
            E = edge_index.size(1)
            src = edge_index[0]
            dst = edge_index[1]

            h = layer.lin_node(x).view(N, layer.num_heads, layer.head_dim)
            e = layer.lin_edge(edge_attr).view(E, layer.num_heads, layer.head_dim)

            h_src = h[src]
            h_dst = h[dst]

            score_src = (h_src * layer.att_src).sum(dim=-1)
            score_dst = (h_dst * layer.att_dst).sum(dim=-1)
            score_edge = (e * layer.att_edge).sum(dim=-1)

            logits = score_src + score_dst + score_edge
            logits = F.leaky_relu(logits, negative_slope=layer.negative_slope)

            attenuation = 1.0 - (layer.bridge_penalty * bridge_mask.unsqueeze(-1))
            logits = logits * attenuation

            max_logits = torch.zeros(N, layer.num_heads, device=x.device).fill_(-1e9)
            max_logits.scatter_reduce_(0, dst.unsqueeze(-1).expand(-1, layer.num_heads), logits, reduce="amax", include_self=True)
            exp_logits = torch.exp(logits - max_logits[dst])

            sum_exp = torch.zeros(N, layer.num_heads, device=x.device)
            sum_exp.scatter_add_(0, dst.unsqueeze(-1).expand(-1, layer.num_heads), exp_logits)
            alpha = exp_logits / (sum_exp[dst] + 1e-9)  # [E, num_heads]

            mean_alpha = alpha.mean(dim=-1).cpu().numpy()
            return mean_alpha

    def compute_attention_matrix(
        self,
        num_nodes: int,
        edge_index: torch.Tensor,
        edge_attention: np.ndarray,
    ) -> np.ndarray:
        """
        Transforms edge attention list into an N x N attention heatmap matrix.
        """
        att_mat = np.zeros((num_nodes, num_nodes), dtype=np.float32)
        src = edge_index[0].cpu().numpy()
        dst = edge_index[1].cpu().numpy()

        for u, v, val in zip(src, dst, edge_attention):
            if u < num_nodes and v < num_nodes:
                att_mat[u, v] += val

        # Normalize row-wise so rows sum to 1.0
        row_sums = att_mat.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        return att_mat / row_sums

    def attribute_feature_importance(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        bridge_mask: torch.Tensor,
        target_node: int,
        target_class: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Computes input feature attribution via Gradient x Input sensitivity analysis:
            S_k = | (d y_c / d x_k) * x_k |
        """
        x_in = x.clone().detach().requires_grad_(True)
        logits, trust_preds, _ = self.model(x_in, edge_index, edge_attr, bridge_mask)

        probs = torch.softmax(logits, dim=-1)
        pred_class = int(torch.argmax(probs[target_node]).item())
        target_c = target_class if target_class is not None else pred_class

        target_score = logits[target_node, target_c]
        target_score.backward()

        grad = x_in.grad[target_node].cpu().numpy()
        val = x_in[target_node].detach().cpu().numpy()
        attribution = np.abs(grad * val)

        total_attr = np.sum(attribution) + 1e-9
        normalized_attr = attribution / total_attr

        ranking = np.argsort(normalized_attr)[::-1]

        features_summary = [
            {
                "feature_name": self.FEATURE_NAMES[idx],
                "feature_index": int(idx),
                "raw_value": round(float(val[idx]), 4),
                "gradient": round(float(grad[idx]), 4),
                "importance_score": round(float(normalized_attr[idx]), 4),
                "importance_percentage": round(float(normalized_attr[idx] * 100), 2),
            }
            for idx in ranking
        ]

        return {
            "target_node": target_node,
            "predicted_class": self.CLASS_NAMES[pred_class],
            "predicted_class_id": pred_class,
            "target_class": self.CLASS_NAMES[target_c],
            "class_probability": round(float(probs[target_node, target_c].item()), 4),
            "features_ranked": features_summary,
            "top_feature": features_summary[0]["feature_name"],
            "top_feature_pct": features_summary[0]["importance_percentage"],
        }

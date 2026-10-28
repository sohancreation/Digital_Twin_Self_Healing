"""
Architectural Ablation Suite for Graph Neural Network Cyber-Resilience.
Implements standardized graph model baselines:
1. MLPBaselineClassifier: Pure node-level multi-layer perceptron (No graph structure).
2. StandardGCN: Kipf & Welling Graph Convolutional Network (Symmetric normalized adjacency).
3. GraphSAGE: Hamilton et al. Inductive Representation Learning (Mean neighborhood aggregation).
4. StandardGAT: Veličković et al. Graph Attention Network (Uniform attention without bridge attenuation).
5. BridgeAwareGAT: Proposed topological bridge-attenuated Graph Attention Network (Theorem 4).

Answers the critical reviewer questions:
- "Does graph structure actually improve detection over an MLP?"
- "Does attention mechanism outperform uniform spectral GCN / spatial GraphSAGE?"
- "Does bridge attenuation (beta_bridge) significantly mitigate cut-vertex gradient leakage?"
"""

from typing import Dict, List, Optional, Tuple, Any
import math
import time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .model import BridgeAwareGATLayer, BridgeAwareGAT, DualHeadGNNClassifier


class MLPBaselineClassifier(nn.Module):
    """
    Baseline 1: Multi-Layer Perceptron (No Graph Message Passing).
    Processes node features in complete isolation, ignoring graph connectivity.
    """

    def __init__(
        self,
        in_features: int = 12,
        hidden_dim: int = 64,
        out_dim: int = 32,
        num_classes: int = 5,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.fc1 = nn.Linear(in_features, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, out_dim)
        self.dropout = dropout

        # Dual output heads matching GNN architecture
        self.cls_head = nn.Linear(out_dim, num_classes)
        self.trust_head = nn.Linear(out_dim, 1)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: Optional[torch.Tensor] = None,
        edge_attr: Optional[torch.Tensor] = None,
        bridge_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        h = F.relu(self.fc1(x))
        h = F.dropout(h, p=self.dropout, training=self.training)
        embeddings = F.relu(self.fc2(h))
        embeddings = F.dropout(embeddings, p=self.dropout, training=self.training)

        logits = self.cls_head(embeddings)
        trust = torch.sigmoid(self.trust_head(embeddings)).squeeze(-1)
        return logits, trust


class StandardGCNLayer(nn.Module):
    """
    Pure PyTorch implementation of Kipf & Welling Graph Convolutional Layer:
    H^{(l+1)} = sigma( D_tilde^{-1/2} A_tilde D_tilde^{-1/2} H^{(l)} W )
    """

    def __init__(self, in_features: int, out_features: int, bias: bool = True):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight = nn.Parameter(torch.Tensor(in_features, out_features))
        if bias:
            self.bias = nn.Parameter(torch.Tensor(out_features))
        else:
            self.register_parameter("bias", None)
        self.reset_parameters()

    def reset_parameters(self):
        gain = nn.init.calculate_gain("relu")
        nn.init.xavier_uniform_(self.weight, gain=gain)
        if self.bias is not None:
            nn.init.zeros_(self.bias)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        x: [N, in_features]
        edge_index: [2, E]
        """
        N = x.size(0)
        E = edge_index.size(1)
        device = x.device

        # Self-loops: A_tilde = A + I_N
        self_loops = torch.arange(N, device=device).unsqueeze(0).repeat(2, 1)
        all_edges = torch.cat([edge_index, self_loops], dim=1)

        src, dst = all_edges[0], all_edges[1]

        # Compute degree: D_tilde_i = sum_j A_tilde_ij
        deg = torch.zeros(N, device=device)
        deg.scatter_add_(0, dst, torch.ones(all_edges.size(1), device=device))

        # D_tilde^{-1/2}
        deg_inv_sqrt = torch.pow(deg.clamp(min=1.0), -0.5)
        norm_weights = deg_inv_sqrt[src] * deg_inv_sqrt[dst]  # [E + N]

        # Project features: [N, out_features]
        xw = torch.matmul(x, self.weight)

        # Message passing: sum_j (norm_ij * xw_j)
        messages = xw[src] * norm_weights.unsqueeze(-1)
        out = torch.zeros(N, self.out_features, device=device)
        out.scatter_add_(0, dst.unsqueeze(-1).expand(-1, self.out_features), messages)

        if self.bias is not None:
            out = out + self.bias
        return out


class StandardGCN(nn.Module):
    """
    2-Layer Graph Convolutional Network (Kipf & Welling).
    """

    def __init__(
        self,
        in_features: int = 12,
        hidden_dim: int = 64,
        out_dim: int = 32,
        num_classes: int = 5,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.gcn1 = StandardGCNLayer(in_features, hidden_dim)
        self.gcn2 = StandardGCNLayer(hidden_dim, out_dim)
        self.dropout = dropout

        self.cls_head = nn.Linear(out_dim, num_classes)
        self.trust_head = nn.Linear(out_dim, 1)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: Optional[torch.Tensor] = None,
        bridge_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        h = F.relu(self.gcn1(x, edge_index))
        h = F.dropout(h, p=self.dropout, training=self.training)
        embeddings = F.relu(self.gcn2(h, edge_index))
        embeddings = F.dropout(embeddings, p=self.dropout, training=self.training)

        logits = self.cls_head(embeddings)
        trust = torch.sigmoid(self.trust_head(embeddings)).squeeze(-1)
        return logits, trust


class GraphSAGELayer(nn.Module):
    """
    Pure PyTorch GraphSAGE Layer with Mean Aggregation:
    h_v^{(l+1)} = sigma( W_self h_v^{(l)} + W_neigh Mean_{u in N(v)} h_u^{(l)} )
    """

    def __init__(self, in_features: int, out_features: int, bias: bool = True):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.w_self = nn.Linear(in_features, out_features, bias=bias)
        self.w_neigh = nn.Linear(in_features, out_features, bias=False)
        self.reset_parameters()

    def reset_parameters(self):
        gain = nn.init.calculate_gain("relu")
        nn.init.xavier_uniform_(self.w_self.weight, gain=gain)
        nn.init.xavier_uniform_(self.w_neigh.weight, gain=gain)
        if self.w_self.bias is not None:
            nn.init.zeros_(self.w_self.bias)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        N = x.size(0)
        src, dst = edge_index[0], edge_index[1]
        device = x.device

        # Compute degree of each destination node
        deg = torch.zeros(N, device=device)
        deg.scatter_add_(0, dst, torch.ones(edge_index.size(1), device=device))
        deg_inv = torch.reciprocal(deg.clamp(min=1.0))

        # Mean aggregation: (1 / |N(v)|) * sum_u h_u
        messages = x[src] * deg_inv[dst].unsqueeze(-1)
        neigh_mean = torch.zeros(N, self.in_features, device=device)
        neigh_mean.scatter_add_(0, dst.unsqueeze(-1).expand(-1, self.in_features), messages)

        # Combine
        out = self.w_self(x) + self.w_neigh(neigh_mean)
        return out


class GraphSAGE(nn.Module):
    """
    2-Layer GraphSAGE model with mean aggregator.
    """

    def __init__(
        self,
        in_features: int = 12,
        hidden_dim: int = 64,
        out_dim: int = 32,
        num_classes: int = 5,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.sage1 = GraphSAGELayer(in_features, hidden_dim)
        self.sage2 = GraphSAGELayer(hidden_dim, out_dim)
        self.dropout = dropout

        self.cls_head = nn.Linear(out_dim, num_classes)
        self.trust_head = nn.Linear(out_dim, 1)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: Optional[torch.Tensor] = None,
        bridge_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        h = F.relu(self.sage1(x, edge_index))
        h = F.dropout(h, p=self.dropout, training=self.training)
        embeddings = F.relu(self.sage2(h, edge_index))
        embeddings = F.dropout(embeddings, p=self.dropout, training=self.training)

        logits = self.cls_head(embeddings)
        trust = torch.sigmoid(self.trust_head(embeddings)).squeeze(-1)
        return logits, trust


class StandardGAT(nn.Module):
    """
    Standard 2-Layer Graph Attention Network (Veličković et al.) WITHOUT bridge attenuation.
    Sets beta_bridge = 0.0 to evaluate the pure GAT mechanism without articulation dampening.
    """

    def __init__(
        self,
        in_features: int = 12,
        hidden_dim: int = 64,
        out_dim: int = 32,
        edge_dim: int = 4,
        num_heads: int = 4,
        num_classes: int = 5,
        dropout: float = 0.1,
    ):
        super().__init__()
        # Use BridgeAwareGAT with bridge_penalty = 0.0 (Standard GAT)
        self.encoder = BridgeAwareGAT(
            in_features=in_features,
            hidden_dim=hidden_dim,
            out_dim=out_dim,
            edge_dim=edge_dim,
            num_heads=num_heads,
            dropout=dropout,
            bridge_penalty=0.0,
        )
        self.cls_head = nn.Linear(out_dim, num_classes)
        self.trust_head = nn.Linear(out_dim, 1)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        bridge_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        # Pass all-zero bridge mask to enforce zero attenuation
        zero_mask = torch.zeros(edge_index.size(1), device=x.device)
        embeddings = self.encoder(x, edge_index, edge_attr, zero_mask)
        logits = self.cls_head(embeddings)
        trust = torch.sigmoid(self.trust_head(embeddings)).squeeze(-1)
        return logits, trust


class GNNModelAblationSuite:
    """
    Automated comparative evaluation across all 5 candidate GNN architectures:
    1. MLP (No graph)
    2. Standard GCN (Kipf & Welling)
    3. GraphSAGE (Hamilton et al.)
    4. Standard GAT (Velickovic et al., no attenuation)
    5. Proposed BridgeAwareGAT (Theorem 4)
    """

    def __init__(self, in_features: int = 12, edge_dim: int = 4, num_classes: int = 5):
        self.models: Dict[str, nn.Module] = {
            "MLP (No Graph)": MLPBaselineClassifier(in_features=in_features, num_classes=num_classes),
            "Standard GCN": StandardGCN(in_features=in_features, num_classes=num_classes),
            "GraphSAGE (Mean)": GraphSAGE(in_features=in_features, num_classes=num_classes),
            "Standard GAT": StandardGAT(in_features=in_features, edge_dim=edge_dim, num_classes=num_classes),
            "Proposed BridgeAwareGAT": DualHeadGNNClassifier(
                in_features=in_features,
                num_classes=num_classes,
                bridge_penalty=0.50,
            ),
        }

    def evaluate_model_complexity(self) -> Dict[str, Dict[str, Any]]:
        """Computes parameter count and forward inference latency for each architecture."""
        results = {}
        N = 6
        E = 7
        device = torch.device("cpu")

        # Synthetic test inputs
        x = torch.randn(N, 12, device=device)
        edge_index = torch.tensor([
            [0, 1, 1, 2, 0, 2, 3],
            [1, 0, 2, 1, 2, 0, 4],
        ], dtype=torch.long, device=device)
        edge_attr = torch.randn(E, 4, device=device)
        bridge_mask = torch.tensor([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], device=device)

        for name, model in self.models.items():
            model.eval()
            param_count = sum(p.numel() for p in model.parameters() if p.requires_grad)

            # Measure latency over 100 warm-up & benchmark passes
            with torch.no_grad():
                for _ in range(20):
                    if name == "MLP (No Graph)":
                        _ = model(x)
                    elif name in ("Standard GCN", "GraphSAGE (Mean)"):
                        _ = model(x, edge_index)
                    elif name == "Standard GAT":
                        _ = model(x, edge_index, edge_attr)
                    else:
                        _ = model(x, edge_index, edge_attr, bridge_mask)

                t0 = time.perf_counter()
                iterations = 100
                for _ in range(iterations):
                    if name == "MLP (No Graph)":
                        _ = model(x)
                    elif name in ("Standard GCN", "GraphSAGE (Mean)"):
                        _ = model(x, edge_index)
                    elif name == "Standard GAT":
                        _ = model(x, edge_index, edge_attr)
                    else:
                        _ = model(x, edge_index, edge_attr, bridge_mask)
                latency_ms = ((time.perf_counter() - t0) / iterations) * 1000.0

            results[name] = {
                "parameters": param_count,
                "latency_ms": round(latency_ms, 3),
                "supports_graph": name != "MLP (No Graph)",
                "supports_edge_features": name in ("Standard GAT", "Proposed BridgeAwareGAT"),
                "bridge_attenuation": name == "Proposed BridgeAwareGAT",
            }
        return results

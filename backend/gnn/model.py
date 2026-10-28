"""
Bridge-Aware Spatio-Temporal Graph Attention Network (ST-GAT) for IoT Networks.
Pure PyTorch implementation of:
1. BridgeAwareGATLayer: Graph attention with bridge-edge attenuation.
2. BridgeAwareGAT: Multi-layer graph attention encoder.
3. TemporalGCN: Sequence aggregation across graph snapshots.
4. DualHeadGNNClassifier: Joint 5-class attack classification and trust score prediction.
"""

from typing import Tuple, List, Optional
import math
import torch
import torch.nn as nn
import torch.nn.functional as F


class BridgeAwareGATLayer(nn.Module):
    """
    Graph Attention Layer with topological bridge-edge attenuation.
    Attenuates attention weights across articulation cut-edges to prevent
    adversarial gradient propagation and catastrophic neighborhood contamination.
    """

    def __init__(
        self,
        in_features: int,
        out_features: int,
        edge_dim: int = 4,
        num_heads: int = 4,
        dropout: float = 0.1,
        negative_slope: float = 0.2,
        bridge_penalty: float = 0.5,
    ):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.edge_dim = edge_dim
        self.num_heads = num_heads
        self.head_dim = out_features // num_heads
        self.dropout = dropout
        self.negative_slope = negative_slope
        self.bridge_penalty = bridge_penalty

        assert (
            out_features % num_heads == 0
        ), f"out_features ({out_features}) must be divisible by num_heads ({num_heads})"

        self.lin_node = nn.Linear(in_features, out_features, bias=False)
        self.lin_edge = nn.Linear(edge_dim, out_features, bias=False)

        # Attention weight vectors per head: [num_heads, head_dim]
        self.att_src = nn.Parameter(torch.Tensor(num_heads, self.head_dim))
        self.att_dst = nn.Parameter(torch.Tensor(num_heads, self.head_dim))
        self.att_edge = nn.Parameter(torch.Tensor(num_heads, self.head_dim))
        self.bias = nn.Parameter(torch.Tensor(out_features))

        self.reset_parameters()

    def reset_parameters(self):
        gain = nn.init.calculate_gain("relu")
        nn.init.xavier_uniform_(self.lin_node.weight, gain=gain)
        nn.init.xavier_uniform_(self.lin_edge.weight, gain=gain)
        nn.init.xavier_uniform_(self.att_src.unsqueeze(0), gain=gain)
        nn.init.xavier_uniform_(self.att_dst.unsqueeze(0), gain=gain)
        nn.init.xavier_uniform_(self.att_edge.unsqueeze(0), gain=gain)
        nn.init.zeros_(self.bias)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        bridge_mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        x: [N, in_features]
        edge_index: [2, E] (src, dst)
        edge_attr: [E, edge_dim]
        bridge_mask: [E] (1.0 if bridge edge, 0.0 otherwise)
        """
        N = x.size(0)
        E = edge_index.size(1)

        # 1. Project node features: [N, num_heads, head_dim]
        h = self.lin_node(x).view(N, self.num_heads, self.head_dim)
        # 2. Project edge features: [E, num_heads, head_dim]
        e = self.lin_edge(edge_attr).view(E, self.num_heads, self.head_dim)

        src, dst = edge_index[0], edge_index[1]

        # Gather source and destination representations: [E, num_heads, head_dim]
        h_src = h[src]
        h_dst = h[dst]

        # 3. Compute attention logits: e_ij = a_s^T h_i + a_d^T h_j + a_e^T e_ij
        score_src = (h_src * self.att_src).sum(dim=-1)   # [E, num_heads]
        score_dst = (h_dst * self.att_dst).sum(dim=-1)   # [E, num_heads]
        score_edge = (e * self.att_edge).sum(dim=-1)      # [E, num_heads]

        logits = score_src + score_dst + score_edge
        logits = F.leaky_relu(logits, negative_slope=self.negative_slope)

        # 4. Bridge-edge attenuation (Theorem 4 foundation):
        # Dampen attention scores across articulation bridges
        attenuation = 1.0 - (self.bridge_penalty * bridge_mask.unsqueeze(-1))
        logits = logits * attenuation

        # 5. Softmax normalization grouped by destination node dst
        # Stable segmented softmax per destination node
        # Compute max per destination for numerical stability
        max_logits = torch.zeros(N, self.num_heads, device=x.device).fill_(-1e9)
        max_logits.scatter_reduce_(0, dst.unsqueeze(-1).expand(-1, self.num_heads), logits, reduce="amax", include_self=True)
        exp_logits = torch.exp(logits - max_logits[dst])

        sum_exp = torch.zeros(N, self.num_heads, device=x.device)
        sum_exp.scatter_add_(0, dst.unsqueeze(-1).expand(-1, self.num_heads), exp_logits)
        alpha = exp_logits / (sum_exp[dst] + 1e-9)  # [E, num_heads]
        alpha = F.dropout(alpha, p=self.dropout, training=self.training)

        # 6. Aggregate messages: out_dst = sum_src alpha_ij * h_src
        # Weighted messages: [E, num_heads, head_dim]
        messages = h_src * alpha.unsqueeze(-1)
        out = torch.zeros(N, self.num_heads, self.head_dim, device=x.device)
        out.scatter_add_(0, dst.view(E, 1, 1).expand(-1, self.num_heads, self.head_dim), messages)

        # Reshape to [N, out_features] and add bias
        out = out.view(N, self.out_features) + self.bias
        return out


class BridgeAwareGAT(nn.Module):
    """
    2-Layer Bridge-Aware Graph Attention Network Encoder.
    Outputs dense node embeddings capturing topology and neighborhood context.
    """

    def __init__(
        self,
        in_features: int = 12,
        hidden_dim: int = 64,
        out_dim: int = 32,
        edge_dim: int = 4,
        num_heads: int = 4,
        dropout: float = 0.1,
        bridge_penalty: float = 0.5,
    ):
        super().__init__()
        self.gat1 = BridgeAwareGATLayer(
            in_features=in_features,
            out_features=hidden_dim,
            edge_dim=edge_dim,
            num_heads=num_heads,
            dropout=dropout,
            bridge_penalty=bridge_penalty,
        )
        self.gat2 = BridgeAwareGATLayer(
            in_features=hidden_dim,
            out_features=out_dim,
            edge_dim=edge_dim,
            num_heads=1,
            dropout=dropout,
            bridge_penalty=bridge_penalty,
        )
        self.dropout = dropout

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        bridge_mask: torch.Tensor,
    ) -> torch.Tensor:
        h1 = self.gat1(x, edge_index, edge_attr, bridge_mask)
        h1 = F.elu(h1)
        h1 = F.dropout(h1, p=self.dropout, training=self.training)
        h2 = self.gat2(h1, edge_index, edge_attr, bridge_mask)
        return h2  # [N, out_dim]


class TemporalGCN(nn.Module):
    """
    Spatio-Temporal Sequence Aggregator.
    Processes a sliding horizon of W graph snapshots through BridgeAwareGAT
    and aggregates temporal dynamics with a GRU.
    """

    def __init__(
        self,
        spatial_encoder: BridgeAwareGAT,
        embed_dim: int = 32,
        hidden_dim: int = 32,
        num_layers: int = 1,
    ):
        super().__init__()
        self.spatial_encoder = spatial_encoder
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.gru = nn.GRU(
            input_size=embed_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
        )

    def forward_snapshots(
        self,
        snapshots: List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]],
    ) -> torch.Tensor:
        """
        snapshots: List of W tuples: (x_t, edge_index_t, edge_attr_t, bridge_mask_t)
        Returns:
            aggregated_embeddings: [N, hidden_dim]
        """
        W = len(snapshots)
        spatial_embeddings = []
        for x, edge_index, edge_attr, bridge_mask in snapshots:
            z_t = self.spatial_encoder(x, edge_index, edge_attr, bridge_mask)  # [N, embed_dim]
            spatial_embeddings.append(z_t)

        # Stack over time: [N, W, embed_dim]
        seq = torch.stack(spatial_embeddings, dim=1)
        out, h_n = self.gru(seq)  # out: [N, W, hidden_dim], h_n: [1, N, hidden_dim]
        return out[:, -1, :]      # Return final step representation [N, hidden_dim]


class DualHeadGNNClassifier(nn.Module):
    """
    Joint multi-task prediction network:
    Head 1: 5-class attack classification (Normal, DoS, Compromised, Node Failure, On-Off)
    Head 2: Calibrated continuous behavioral trust score prediction in [0.0, 1.0].
    """

    def __init__(
        self,
        in_features: int = 12,
        hidden_dim: int = 64,
        embed_dim: int = 32,
        num_classes: int = 5,
        bridge_penalty: float = 0.5,
    ):
        super().__init__()
        self.encoder = BridgeAwareGAT(
            in_features=in_features,
            hidden_dim=hidden_dim,
            out_dim=embed_dim,
            bridge_penalty=bridge_penalty,
        )
        self.temporal_model = TemporalGCN(
            spatial_encoder=self.encoder,
            embed_dim=embed_dim,
            hidden_dim=embed_dim,
        )

        # Classification Head: [embed_dim -> 32 -> num_classes]
        self.attack_head = nn.Sequential(
            nn.Linear(embed_dim, 32),
            nn.ReLU(),
            nn.Linear(32, num_classes),
        )

        # Trust Score Head: [embed_dim -> 32 -> 1]
        self.trust_head = nn.Sequential(
            nn.Linear(embed_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        bridge_mask: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Single-step snapshot forward pass.
        Returns:
            (logits_attack [N, 5], trust_pred [N], embeddings [N, embed_dim])
        """
        embeddings = self.encoder(x, edge_index, edge_attr, bridge_mask)
        logits_attack = self.attack_head(embeddings)
        trust_pred = self.trust_head(embeddings).squeeze(-1)
        return logits_attack, trust_pred, embeddings

    def forward_sequence(
        self,
        snapshots: List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]],
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Temporal sequence forward pass across W snapshots.
        """
        embeddings = self.temporal_model.forward_snapshots(snapshots)
        logits_attack = self.attack_head(embeddings)
        trust_pred = self.trust_head(embeddings).squeeze(-1)
        return logits_attack, trust_pred, embeddings

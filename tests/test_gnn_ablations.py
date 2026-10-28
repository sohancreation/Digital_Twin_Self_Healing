"""
Unit tests for GNN Architectural Ablation Suite.
Verifies MLP, Standard GCN, GraphSAGE, Standard GAT, and BridgeAwareGAT.
"""

import pytest
import torch

from backend.gnn.ablations import (
    MLPBaselineClassifier,
    StandardGCNLayer,
    StandardGCN,
    GraphSAGELayer,
    GraphSAGE,
    StandardGAT,
    GNNModelAblationSuite,
)
from backend.gnn.model import BridgeAwareGAT


@pytest.fixture
def synthetic_graph():
    """Provides a synthetic 6-node graph with 7 edges and bridge edge (2, 3)."""
    N = 6
    E = 7
    x = torch.randn(N, 12)
    edge_index = torch.tensor([
        [0, 1, 1, 2, 0, 2, 3],
        [1, 0, 2, 1, 2, 0, 4],
    ], dtype=torch.long)
    edge_attr = torch.randn(E, 4)
    bridge_mask = torch.tensor([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
    return x, edge_index, edge_attr, bridge_mask


class TestGNNAblations:
    """Tests all ablation architectures."""

    def test_mlp_baseline(self, synthetic_graph):
        x, _, _, _ = synthetic_graph
        model = MLPBaselineClassifier(in_features=12, hidden_dim=32, out_dim=16, num_classes=5)
        logits, trust = model(x)
        assert logits.shape == (6, 5)
        assert trust.shape == (6,)
        assert (trust >= 0.0).all() and (trust <= 1.0).all()

    def test_standard_gcn(self, synthetic_graph):
        x, edge_index, _, _ = synthetic_graph
        model = StandardGCN(in_features=12, hidden_dim=32, out_dim=16, num_classes=5)
        logits, trust = model(x, edge_index)
        assert logits.shape == (6, 5)
        assert trust.shape == (6,)
        assert not torch.isnan(logits).any()

    def test_graphsage(self, synthetic_graph):
        x, edge_index, _, _ = synthetic_graph
        model = GraphSAGE(in_features=12, hidden_dim=32, out_dim=16, num_classes=5)
        logits, trust = model(x, edge_index)
        assert logits.shape == (6, 5)
        assert trust.shape == (6,)
        assert not torch.isnan(logits).any()

    def test_standard_gat(self, synthetic_graph):
        x, edge_index, edge_attr, _ = synthetic_graph
        model = StandardGAT(in_features=12, hidden_dim=32, out_dim=16, edge_dim=4, num_classes=5)
        logits, trust = model(x, edge_index, edge_attr)
        assert logits.shape == (6, 5)
        assert trust.shape == (6,)
        assert not torch.isnan(logits).any()

    def test_ablation_suite_complexity(self):
        suite = GNNModelAblationSuite(in_features=12, edge_dim=4, num_classes=5)
        report = suite.evaluate_model_complexity()

        assert len(report) == 5
        assert "MLP (No Graph)" in report
        assert "Standard GCN" in report
        assert "GraphSAGE (Mean)" in report
        assert "Standard GAT" in report
        assert "Proposed BridgeAwareGAT" in report

        for name, metrics in report.items():
            assert metrics["parameters"] > 0
            assert metrics["latency_ms"] >= 0.0

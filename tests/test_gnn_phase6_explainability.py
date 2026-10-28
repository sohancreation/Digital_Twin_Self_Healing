"""
tests/test_gnn_phase6_explainability.py

Unit and integration tests for GNN Phase 6:
Explainability, Graph Attention Interpretability & Counterfactual Defense Attribution.
"""

import pytest
import torch
import numpy as np
import networkx as nx

from backend.gnn.model import DualHeadGNNClassifier
from backend.gnn.explainability import GNNAttentionExplainer
from backend.gnn.counterfactual import CounterfactualDefenseExplainer, CounterfactualExplanation, CounterfactualWorld


@pytest.fixture
def gnn_model():
    """Instantiate a test DualHeadGNNClassifier."""
    torch.manual_seed(42)
    model = DualHeadGNNClassifier(
        in_features=12,
        hidden_dim=32,
        embed_dim=32,
        num_classes=5,
        bridge_penalty=0.5,
    )
    model.eval()
    return model


@pytest.fixture
def synthetic_graph():
    """Create a 4-node synthetic topology with an articulation bridge edge (0-1)."""
    torch.manual_seed(42)
    num_nodes = 4
    x = torch.randn(num_nodes, 12)
    # Directed edge index for undirected graph: (0-1), (1-2), (2-3)
    edge_index = torch.tensor(
        [
            [0, 1, 1, 2, 2, 3, 1, 0, 2, 1, 3, 2],
            [1, 0, 2, 1, 3, 2, 0, 1, 1, 2, 2, 3],
        ],
        dtype=torch.long,
    )
    num_edges = edge_index.size(1)
    edge_attr = torch.randn(num_edges, 4)
    # Node 1 and 2 are bridge-connected
    bridge_mask = torch.zeros(num_edges, dtype=torch.float32)
    bridge_mask[0] = 1.0
    bridge_mask[1] = 1.0

    return {
        "x": x,
        "edge_index": edge_index,
        "edge_attr": edge_attr,
        "bridge_mask": bridge_mask,
        "num_nodes": num_nodes,
    }


@pytest.fixture
def network_topology():
    """Creates a barbell-like topology where node 2 is an articulation cut-vertex connecting two clusters."""
    g = nx.Graph()
    # Cluster A: nodes 0, 1, 2 (triangle)
    g.add_edges_from([(0, 1), (1, 2), (0, 2)])
    # Cluster B: nodes 2, 3, 4, 5 (2 connects to 3, 3 connects to 4, 5)
    g.add_edges_from([(2, 3), (3, 4), (4, 5), (3, 5)])
    return g


def test_edge_attention_extraction_and_heatmap(gnn_model, synthetic_graph):
    """Verify that multi-head attention weights are extracted and normalized correctly."""
    explainer = GNNAttentionExplainer(gnn_model)

    alpha = explainer.extract_edge_attention(
        x=synthetic_graph["x"],
        edge_index=synthetic_graph["edge_index"],
        edge_attr=synthetic_graph["edge_attr"],
        bridge_mask=synthetic_graph["bridge_mask"],
    )

    assert isinstance(alpha, np.ndarray)
    assert alpha.shape[0] == synthetic_graph["edge_index"].size(1)
    assert np.all(alpha >= 0.0)
    assert np.all(alpha <= 1.0)

    # Test N x N attention matrix
    att_mat = explainer.compute_attention_matrix(
        num_nodes=synthetic_graph["num_nodes"],
        edge_index=synthetic_graph["edge_index"],
        edge_attention=alpha,
    )

    assert att_mat.shape == (synthetic_graph["num_nodes"], synthetic_graph["num_nodes"])
    # Row sums should equal 1.0 for connected nodes
    for r in range(synthetic_graph["num_nodes"]):
        assert np.isclose(np.sum(att_mat[r]), 1.0, atol=1e-4)


def test_gradient_input_feature_attribution(gnn_model, synthetic_graph):
    """Verify Gradient x Input sensitivity ranking computes non-zero normalized scores across 12 features."""
    explainer = GNNAttentionExplainer(gnn_model)

    attribution = explainer.attribute_feature_importance(
        x=synthetic_graph["x"],
        edge_index=synthetic_graph["edge_index"],
        edge_attr=synthetic_graph["edge_attr"],
        bridge_mask=synthetic_graph["bridge_mask"],
        target_node=1,
    )

    assert attribution["target_node"] == 1
    assert "predicted_class" in attribution
    assert "class_probability" in attribution
    assert len(attribution["features_ranked"]) == 12

    # Verify scores sum to ~1.0 (100%)
    total_pct = sum(f["importance_percentage"] for f in attribution["features_ranked"])
    assert np.isclose(total_pct, 100.0, atol=0.1)

    top_feat = attribution["top_feature"]
    assert isinstance(top_feat, str)
    assert len(top_feat) > 0
    assert attribution["top_feature_pct"] > 0.0


def test_counterfactual_world_generation_and_pareto(network_topology):
    """Verify that counterfactual engine computes 4 valid worlds and W* Pareto-dominates alternatives for cut-vertex."""
    cf_engine = CounterfactualDefenseExplainer(topology=network_topology)

    result = cf_engine.explain_recovery_decision(
        compromised_node=2,
        attack_type="dos",
        candidate_detours=[(0, 3)],
    )

    assert isinstance(result, CounterfactualExplanation)
    assert result.compromised_node == 2
    assert result.is_articulation_cut_vertex is True
    assert len(result.worlds_evaluated) == 4

    world_dict = {w.world_id: w for w in result.worlds_evaluated}
    assert "W0_NoAction" in world_dict
    assert "W1_NaiveIsolation" in world_dict
    assert "W2_SuboptimalBypass" in world_dict
    assert "W_star_ProposedDetour" in world_dict

    w0 = world_dict["W0_NoAction"]
    w1 = world_dict["W1_NaiveIsolation"]
    w2 = world_dict["W2_SuboptimalBypass"]
    w_star = world_dict["W_star_ProposedDetour"]

    # W* must be the chosen world
    assert w_star.is_chosen is True
    assert w0.is_chosen is False
    assert w1.is_chosen is False
    assert w2.is_chosen is False

    # Pareto dominance validations:
    # 1. PDR of W* is higher than all alternatives
    assert w_star.predicted_pdr > w0.predicted_pdr
    assert w_star.predicted_pdr > w1.predicted_pdr
    assert w_star.predicted_pdr > w2.predicted_pdr

    # 2. Partition rate of W* is 0% while W1 has severe severance
    assert w_star.partition_rate == 0.0
    assert w1.partition_rate > 50.0

    # 3. Path stretch of W* is lower than W2
    assert w_star.path_stretch_hops < w2.path_stretch_hops

    # 4. Resilience score of W* dominates all
    assert w_star.resilience_score > w0.resilience_score
    assert w_star.resilience_score > w1.resilience_score
    assert w_star.resilience_score > w2.resilience_score

    # 5. Natural-language justification exists
    assert result.justification_summary is not None
    assert "COMPOSITE_ISOLATE_AND_BRIDGE" in result.justification_summary


def test_counterfactual_leaf_node_behavior(network_topology):
    """Verify counterfactual behavior when compromised node is not an articulation cut-vertex (e.g. node 5)."""
    cf_engine = CounterfactualDefenseExplainer(topology=network_topology)

    result = cf_engine.explain_recovery_decision(
        compromised_node=5,
        attack_type="dos",
    )

    assert result.compromised_node == 5
    assert result.is_articulation_cut_vertex is False

    world_dict = {w.world_id: w for w in result.worlds_evaluated}
    w1 = world_dict["W1_NaiveIsolation"]
    w_star = world_dict["W_star_ProposedDetour"]

    # For a leaf/cycle node, isolation does not partition the network
    assert w1.partition_rate == 0.0
    assert w_star.is_chosen is True

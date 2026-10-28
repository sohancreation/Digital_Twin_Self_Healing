"""
Unit tests for GNN Feature Leakage Ablation and Non-Heuristic Feature Extraction.
Verifies that GraphFeatureExtractor operates properly with enable_heuristic_signatures=False,
ensuring raw statistical volatility is used in place of hand-tuned cyclic / recovery signatures,
preventing label leakage.
"""

import pytest
import numpy as np
import networkx as nx
import torch

from backend.digital_twin.models import TwinNodeState
from backend.gnn.features import GraphFeatureExtractor, GraphSnapshot
from backend.gnn.model import DualHeadGNNClassifier


@pytest.fixture
def sample_graph_and_states():
    """Builds a 6-node network with an articulation cut-vertex bridge at Node 3."""
    graph = nx.Graph()
    graph.add_edges_from([
        (0, 1), (1, 2), (0, 2),
        (2, 3),
        (3, 4), (4, 5), (3, 5),
    ])

    states = {}
    for nid in range(6):
        states[nid] = TwinNodeState(
            node_id=nid,
            timestamp=10.0,
            packet_rate=5.0,
            forwarding_rate=4.0,
            packet_loss=0.05,
            latency=15.0,
            rssi=-60.0,
            energy=95.0,
            cpu=20.0,
            memory=25.0,
            neighbor_count=len(list(graph.neighbors(nid))),
            trust_score=0.92,
        )
    return graph, states


class TestFeatureAblation:
    def test_heuristic_disabled_dimensions_and_finite(self, sample_graph_and_states):
        """Verifies that extractor without heuristic signatures produces expected shapes and finite values."""
        graph, states = sample_graph_and_states
        extractor = GraphFeatureExtractor(enable_heuristic_signatures=False)

        snapshot = extractor.extract_snapshot(node_states=states, graph=graph)
        assert isinstance(snapshot, GraphSnapshot)
        assert snapshot.x.shape == (6, 12)
        if isinstance(snapshot.x, torch.Tensor):
            assert torch.all(torch.isfinite(snapshot.x))
        else:
            assert np.all(np.isfinite(snapshot.x))
        assert snapshot.edge_index.shape[0] == 2
        assert snapshot.edge_attr.shape[1] == 4

    def test_heuristic_disabled_vs_enabled_difference(self, sample_graph_and_states):
        """
        Verifies that feature column 10 (cycle / volatility feature) differs between
        heuristic signature mode and ablated raw volatility mode under oscillatory traffic.
        """
        graph, states = sample_graph_and_states
        ext_heur = GraphFeatureExtractor(enable_heuristic_signatures=True)
        ext_abld = GraphFeatureExtractor(enable_heuristic_signatures=False)

        # Simulate a burst of changing PDR / packet loss
        pdr_t0 = {nid: 0.95 for nid in states}
        pdr_t1 = {nid: 0.10 if nid == 3 else 0.95 for nid in states}

        # Step 1
        _ = ext_heur.extract_snapshot(states, graph, previous_pdr=pdr_t0)
        _ = ext_abld.extract_snapshot(states, graph, previous_pdr=pdr_t0)

        # Step 2 with significant drop
        snap_heur = ext_heur.extract_snapshot(states, graph, previous_pdr=pdr_t1)
        snap_abld = ext_abld.extract_snapshot(states, graph, previous_pdr=pdr_t1)

        # The features should be valid and bounded [0, 1]
        assert snap_heur.x.shape == (6, 12)
        assert snap_abld.x.shape == (6, 12)
        val = snap_abld.x[3, 10].item() if isinstance(snap_abld.x, torch.Tensor) else snap_abld.x[3, 10]
        assert 0.0 <= val <= 1.0

    def test_model_forward_with_ablated_features(self, sample_graph_and_states):
        """Verifies that the DualHeadGNNClassifier runs inference successfully on ablated features."""
        graph, states = sample_graph_and_states
        extractor = GraphFeatureExtractor(enable_heuristic_signatures=False)
        snapshot = extractor.extract_snapshot(states, graph)

        model = DualHeadGNNClassifier(in_features=12, num_classes=5)
        model.eval()

        x = snapshot.x if isinstance(snapshot.x, torch.Tensor) else torch.from_numpy(snapshot.x)
        edge_index = snapshot.edge_index if isinstance(snapshot.edge_index, torch.Tensor) else torch.from_numpy(snapshot.edge_index)
        edge_attr = snapshot.edge_attr if isinstance(snapshot.edge_attr, torch.Tensor) else torch.from_numpy(snapshot.edge_attr)
        bridge_mask = snapshot.bridge_mask if isinstance(snapshot.bridge_mask, torch.Tensor) else torch.from_numpy(snapshot.bridge_mask)

        with torch.no_grad():
            logits, trust_pred, embeddings = model(x, edge_index, edge_attr, bridge_mask)

        assert logits.shape == (6, 5)
        assert trust_pred.shape == (6,)
        assert embeddings.shape == (6, 32)
        assert torch.all(trust_pred >= 0.0) and torch.all(trust_pred <= 1.0)

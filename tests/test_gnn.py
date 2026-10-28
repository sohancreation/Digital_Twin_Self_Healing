"""
Unit and integration tests for GNN Cyber-Resilience Pipeline (Phase 2).
Covers GraphFeatureExtractor, BridgeAwareGATLayer, BridgeAwareGAT,
TemporalGCN, DualHeadGNNClassifier, GNNBayesianFusion, GraphSnapshotDataset,
and GNNTrainer.
"""

import pytest
import numpy as np
import networkx as nx
import torch
from torch.utils.data import DataLoader

from backend.digital_twin.models import TwinNodeState
from backend.gnn.features import GraphFeatureExtractor, GraphSnapshot
from backend.gnn.model import (
    BridgeAwareGATLayer,
    BridgeAwareGAT,
    TemporalGCN,
    DualHeadGNNClassifier,
)
from backend.gnn.fusion import GNNBayesianFusion
from backend.gnn.dataset import GraphSnapshotDataset, GraphSnapshotBatch
from backend.gnn.trainer import GNNTrainer


@pytest.fixture
def sample_topology_and_states():
    """Builds a 6-node network with an articulation cut-vertex bridge at Node 3."""
    graph = nx.Graph()
    # Edges: {0,1,2} form a triangle, connected via bridge (2,3) to {3,4,5}
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
            packet_rate=2.0,
            forwarding_rate=4.0,
            packet_loss=0.02,
            latency=12.0,
            rssi=-65.0,
            energy=98.5,
            cpu=18.0,
            memory=22.0,
            neighbor_count=len(list(graph.neighbors(nid))),
            trust_score=0.98,
        )
    return graph, states


class TestGraphFeatureExtractor:
    def test_feature_dimensions_and_topology(self, sample_topology_and_states):
        graph, states = sample_topology_and_states
        extractor = GraphFeatureExtractor()

        snapshot = extractor.extract_snapshot(node_states=states, graph=graph)

        assert isinstance(snapshot, GraphSnapshot)
        assert snapshot.x.shape == (6, GraphFeatureExtractor.NODE_FEATURE_DIM)
        assert snapshot.edge_attr.shape[1] == GraphFeatureExtractor.EDGE_FEATURE_DIM
        assert snapshot.edge_index.shape[0] == 2
        assert snapshot.bridge_mask.shape[0] == snapshot.edge_index.shape[1]

        # Node 3 and Node 2 are articulation points
        assert 3 in snapshot.cut_vertices or 2 in snapshot.cut_vertices
        assert len(snapshot.node_ids) == 6

    def test_feature_bounds(self, sample_topology_and_states):
        graph, states = sample_topology_and_states
        extractor = GraphFeatureExtractor()
        snap = extractor.extract_snapshot(node_states=states, graph=graph)

        # Check normalization bounds for PDR, load, lat, energy, etc.
        assert torch.all(snap.x[:, 0] >= 0.0) and torch.all(snap.x[:, 0] <= 1.0)  # PDR
        assert torch.all(snap.x[:, 1] >= 0.0)  # Load
        assert torch.all(snap.x[:, 3] >= 0.0) and torch.all(snap.x[:, 3] <= 1.0)  # Energy


class TestBridgeAwareGAT:
    def test_layer_bridge_attenuation(self):
        in_feat = 12
        out_feat = 16
        layer = BridgeAwareGATLayer(
            in_features=in_feat,
            out_features=out_feat,
            edge_dim=4,
            num_heads=2,
            bridge_penalty=0.5,
        )

        x = torch.randn(4, in_feat)
        edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 0]], dtype=torch.long)
        edge_attr = torch.randn(4, 4)
        bridge_mask = torch.tensor([0.0, 1.0, 0.0, 1.0])  # edges 1 and 3 are bridges

        out = layer(x, edge_index, edge_attr, bridge_mask)
        assert out.shape == (4, out_feat)
        assert not torch.isnan(out).any()

    def test_full_encoder(self):
        encoder = BridgeAwareGAT(
            in_features=12,
            hidden_dim=32,
            out_dim=16,
            edge_dim=4,
            num_heads=2,
            bridge_penalty=0.5,
        )
        x = torch.randn(6, 12)
        edge_index = torch.tensor([[0, 1, 2], [1, 2, 0]], dtype=torch.long)
        edge_attr = torch.randn(3, 4)
        bridge_mask = torch.tensor([0.0, 1.0, 0.0])

        out = encoder(x, edge_index, edge_attr, bridge_mask)
        assert out.shape == (6, 16)


class TestTemporalGCNAndClassifier:
    def test_temporal_gcn_sequence(self):
        encoder = BridgeAwareGAT(in_features=12, hidden_dim=16, out_dim=8, num_heads=2)
        temporal_model = TemporalGCN(spatial_encoder=encoder, embed_dim=8, hidden_dim=8)

        # 3 timesteps of 4 nodes
        snapshots = []
        for _ in range(3):
            x = torch.randn(4, 12)
            e_idx = torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.long)
            e_attr = torch.randn(3, 4)
            b_mask = torch.zeros(3)
            snapshots.append((x, e_idx, e_attr, b_mask))

        out = temporal_model.forward_snapshots(snapshots)
        assert out.shape == (4, 8)

    def test_dual_head_classifier(self):
        model = DualHeadGNNClassifier(in_features=12, hidden_dim=16, embed_dim=8, num_classes=5)
        x = torch.randn(5, 12)
        edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 4]], dtype=torch.long)
        edge_attr = torch.randn(4, 4)
        bridge_mask = torch.zeros(4)

        logits, trust_pred, embeds = model(x, edge_index, edge_attr, bridge_mask)
        assert logits.shape == (5, 5)
        assert trust_pred.shape == (5,)
        assert embeds.shape == (5, 8)
        assert torch.all(trust_pred >= 0.0) and torch.all(trust_pred <= 1.0)


class TestGNNBayesianFusion:
    def test_theorem4_adaptive_beta(self):
        fusion = GNNBayesianFusion(beta_nominal=0.50, beta_bridge=0.35, beta_leaf=0.60)

        # Cut-vertex uses beta_bridge (more reliance on GNN context: 1 - 0.35 = 0.65)
        assert fusion.get_adaptive_beta(node_id=3, is_cut_vertex=True, degree=3) == 0.35
        # Leaf node uses beta_leaf (relies more on local observations)
        assert fusion.get_adaptive_beta(node_id=4, is_cut_vertex=False, degree=1) == 0.60
        # Normal mesh node uses beta_nominal
        assert fusion.get_adaptive_beta(node_id=1, is_cut_vertex=False, degree=3) == 0.50

    def test_fast_penalty_acceleration(self):
        fusion = GNNBayesianFusion(fast_penalty_threshold=0.70)
        # Normal fused trust
        t_fused_normal, diag_normal = fusion.fuse_node_trust(
            node_id=2, t_bayes=0.90, t_gnn=0.90, p_attack_gnn=0.10, is_cut_vertex=False
        )
        assert t_fused_normal > 0.80

        # Accelerated penalty when GNN detects attack with high confidence
        fusion_atk = GNNBayesianFusion(fast_penalty_threshold=0.70)
        t_fused_atk, diag_atk = fusion_atk.fuse_node_trust(
            node_id=2, t_bayes=0.90, t_gnn=0.20, p_attack_gnn=0.95, is_cut_vertex=False
        )
        # Raw fused: (0.5*0.9 + 0.5*0.2) - 0.15*0.95 = 0.55 - 0.1425 = 0.4075 -> smoothed ~0.52
        assert t_fused_atk < 0.60

    def test_batch_fuse(self):
        fusion = GNNBayesianFusion()
        node_ids = [0, 1, 2, 3]
        bayes_scores = {0: 0.95, 1: 0.90, 2: 0.40, 3: 0.20}
        gnn_scores = {0: 0.98, 1: 0.92, 2: 0.35, 3: 0.15}
        attack_probs = {0: 0.05, 1: 0.08, 2: 0.85, 3: 0.92}
        cut_vertices = {2}

        fused = fusion.batch_fuse(
            node_ids=node_ids,
            bayes_scores=bayes_scores,
            gnn_scores=gnn_scores,
            gnn_attack_probs=attack_probs,
            cut_vertices=cut_vertices,
        )
        assert len(fused) == 4
        assert fused[0] > 0.85
        assert fused[3] < 0.50


class TestDatasetAndTrainer:
    def test_dataset_collation(self):
        # Create 2 small snapshots
        s1 = GraphSnapshot(
            x=torch.randn(3, 12),
            edge_index=torch.tensor([[0, 1], [1, 2]], dtype=torch.long),
            edge_attr=torch.randn(2, 4),
            bridge_mask=torch.zeros(2),
            node_ids=[0, 1, 2],
            cut_vertices={1},
            timestamp=1.0,
        )
        s2 = GraphSnapshot(
            x=torch.randn(4, 12),
            edge_index=torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.long),
            edge_attr=torch.randn(3, 4),
            bridge_mask=torch.zeros(3),
            node_ids=[0, 1, 2, 3],
            cut_vertices=set(),
            timestamp=2.0,
        )

        att1 = torch.tensor([0, 1, 0], dtype=torch.long)
        att2 = torch.tensor([0, 0, 2, 0], dtype=torch.long)
        tr1 = torch.tensor([0.9, 0.2, 0.9], dtype=torch.float32)
        tr2 = torch.tensor([0.95, 0.95, 0.3, 0.95], dtype=torch.float32)

        ds = GraphSnapshotDataset([s1, s2], [att1, att2], [tr1, tr2])
        loader = DataLoader(ds, batch_size=2, collate_fn=GraphSnapshotDataset.collate_snapshots)

        batch = next(iter(loader))
        assert isinstance(batch, GraphSnapshotBatch)
        assert batch.x.shape == (7, 12)
        assert batch.edge_index.shape[1] == 5
        # Node indices for second graph should be offset by 3
        assert batch.edge_index[:, 2:].min() >= 3
        assert batch.labels_attack.shape == (7,)
        assert batch.labels_trust.shape == (7,)

    def test_trainer_step_and_eval(self):
        torch.manual_seed(42)
        s1 = GraphSnapshot(
            x=torch.randn(4, 12),
            edge_index=torch.tensor([[0, 1, 2, 3], [1, 2, 3, 0]], dtype=torch.long),
            edge_attr=torch.randn(4, 4),
            bridge_mask=torch.zeros(4),
            node_ids=[0, 1, 2, 3],
            cut_vertices=set(),
            timestamp=1.0,
        )
        att1 = torch.tensor([0, 1, 0, 0], dtype=torch.long)
        tr1 = torch.tensor([0.9, 0.2, 0.9, 0.9], dtype=torch.float32)

        ds = GraphSnapshotDataset([s1], [att1], [tr1])
        loader = DataLoader(ds, batch_size=1, collate_fn=GraphSnapshotDataset.collate_snapshots)

        model = DualHeadGNNClassifier(in_features=12, hidden_dim=16, embed_dim=8, num_classes=5)
        trainer = GNNTrainer(model=model, lr=1e-3)

        train_res = trainer.train_epoch(loader)
        assert "loss" in train_res
        assert "loss_cls" in train_res
        assert "loss_reg" in train_res

        eval_res = trainer.evaluate(loader, return_raw_outputs=True)
        assert "accuracy" in eval_res
        assert "macro_f1" in eval_res
        assert "macro_auc" in eval_res
        assert "confusion_matrix" in eval_res
        assert len(eval_res["confusion_matrix"]) == 5

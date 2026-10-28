"""
tests/test_gnn_phase8_federated.py

Unit and integration tests for GNN Phase 8:
Federated Edge Learning & Multi-Twin Collaborative Resilience.
"""

from typing import Dict, List, Tuple
import pytest
import torch
import numpy as np

from backend.gnn.model import DualHeadGNNClassifier
from backend.gnn.federated import (
    FederatedClient,
    FederatedCoordinator,
    DifferentialPrivacyEngine,
)


class DummySnapshot:
    """Mock GraphSnapshot container for federated testing."""
    def __init__(self, num_nodes: int = 10):
        self.x = torch.randn(num_nodes, 12).abs()
        # Ring topology
        edges = []
        for i in range(num_nodes):
            j = (i + 1) % num_nodes
            edges.extend([[i, j], [j, i]])
        self.edge_index = torch.tensor(edges, dtype=torch.long).t()
        E = self.edge_index.size(1)
        self.edge_attr = torch.ones(E, 4) * 0.5
        self.bridge_mask = torch.zeros(E)
        self.labels = torch.randint(0, 5, (num_nodes,), dtype=torch.long)
        self.trust_scores = torch.rand(num_nodes, dtype=torch.float32)


@pytest.fixture
def base_model():
    """Instantiate a base DualHeadGNNClassifier."""
    torch.manual_seed(42)
    return DualHeadGNNClassifier(
        in_features=12,
        hidden_dim=16,
        embed_dim=16,
        num_classes=5,
    )


def test_federated_client_local_training(base_model):
    """Verify that FederatedClient executes local epochs and computes weight deltas."""
    client = FederatedClient(client_id="Client_A", model=base_model, lr=1e-3)
    snapshots = [DummySnapshot(12), DummySnapshot(12)]

    global_weights = base_model.state_dict()
    res = client.train_epoch(snapshots)

    assert "loss" in res
    assert "cls_loss" in res
    assert "trust_loss" in res
    assert res["loss"] > 0.0

    delta = client.compute_weight_delta(global_weights)
    assert len(delta) == len(global_weights)
    # At least some parameters must have non-zero delta
    total_delta_norm = sum((d ** 2).sum().item() for d in delta.values())
    assert total_delta_norm > 0.0


def test_fedprox_regularization_penalty(base_model):
    """Verify FedProx adds proximal penalty to prevent local model drift."""
    client = FederatedClient(client_id="Client_B", model=base_model, lr=1e-3, mu_prox=0.1)
    snapshots = [DummySnapshot(12)]
    global_weights = base_model.state_dict()

    res = client.train_epoch(snapshots, global_state_dict=global_weights, use_fedprox=True)
    assert "loss" in res
    assert res["loss"] > 0.0


def test_differential_privacy_engine_clipping_and_noise():
    """Verify that DifferentialPrivacyEngine clips gradient norm and injects Gaussian noise."""
    dp_engine = DifferentialPrivacyEngine(clip_norm=1.0, noise_multiplier=0.1)

    # Large weight delta with norm >> 1.0
    delta = {
        "layer.weight": torch.ones(10, 10) * 5.0, # norm = sqrt(100 * 25) = 50
        "layer.bias": torch.zeros(10),
    }

    priv_delta = dp_engine.privatize_weights(delta)

    assert "layer.weight" in priv_delta
    # Values should no longer be identical to original (noise added)
    assert not torch.allclose(priv_delta["layer.weight"], delta["layer.weight"])
    # Norm after clipping and before noise should be around clip_norm
    # With small noise, norm will be close to clip_norm
    noisy_norm = torch.sqrt((priv_delta["layer.weight"] ** 2).sum()).item()
    assert noisy_norm < 10.0  # severely reduced from initial norm of 50.0


def test_fedavg_and_fedgraphbridge_aggregation(base_model):
    """Verify coordinator aggregates client updates under both FedAvg and FedGraphBridge."""
    for method in ("fedavg", "fed_graph_bridge"):
        coordinator = FederatedCoordinator(
            base_model=base_model,
            aggregation_method=method,
            enable_dp=False,
        )

        global_sd = coordinator.get_global_weights()
        client_updates = [
            {
                "client_id": "GW_1",
                "delta": {k: torch.randn_like(v) * 0.01 for k, v in global_sd.items()},
                "num_samples": 100,
                "bridge_density": 0.35,
                "cut_vertex_count": 3,
            },
            {
                "client_id": "GW_2",
                "delta": {k: torch.randn_like(v) * 0.01 for k, v in global_sd.items()},
                "num_samples": 50,
                "bridge_density": 0.05,
                "cut_vertex_count": 0,
            },
        ]

        updated_weights = coordinator.aggregate_round(client_updates)
        assert len(updated_weights) == len(global_sd)


def test_global_model_evaluation(base_model):
    """Verify that coordinator correctly evaluates the global model across test snapshots."""
    coordinator = FederatedCoordinator(base_model=base_model)
    test_snaps = [DummySnapshot(15), DummySnapshot(15)]

    metrics = coordinator.evaluate_global_model(test_snaps)
    assert "accuracy" in metrics
    assert "trust_mae" in metrics
    assert "total_nodes" in metrics
    assert 0.0 <= metrics["accuracy"] <= 100.0
    assert metrics["trust_mae"] >= 0.0
    assert metrics["total_nodes"] == 30

"""
tests/test_gnn_phase7_adversarial.py

Unit and integration tests for GNN Phase 7:
Adversarial Robustness, Graph Perturbation & Defense Hardening.
"""

import pytest
import torch
import numpy as np

from backend.gnn.model import DualHeadGNNClassifier
from backend.gnn.adversarial import GraphAdversarialAttacker
from backend.gnn.robustness import AdversariallyHardenedTrainer, RobustnessEvaluator


@pytest.fixture
def synthetic_graph():
    """Create a 6-node synthetic graph with 2 articulation bridges."""
    torch.manual_seed(42)
    N = 6
    x = torch.randn(N, 12).abs()  # positive telemetry features
    edge_index = torch.tensor(
        [
            [0, 1, 1, 2, 2, 0, 2, 3, 3, 4, 4, 5, 5, 3],
            [1, 0, 2, 1, 0, 2, 3, 2, 4, 3, 5, 4, 3, 5],
        ],
        dtype=torch.long,
    )
    E = edge_index.size(1)
    edge_attr = torch.ones(E, 4) * 0.8
    bridge_mask = torch.zeros(E)
    # Edge between node 2 and 3 is an articulation bridge
    bridge_mask[6] = 1.0
    bridge_mask[7] = 1.0

    labels = torch.tensor([0, 0, 1, 0, 0, 2], dtype=torch.long)
    trust_scores = torch.tensor([0.98, 0.95, 0.20, 0.96, 0.97, 0.25], dtype=torch.float32)

    return {
        "x": x,
        "edge_index": edge_index,
        "edge_attr": edge_attr,
        "bridge_mask": bridge_mask,
        "labels": labels,
        "trust_scores": trust_scores,
    }


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


def test_fgsm_feature_attack(gnn_model, synthetic_graph):
    """Verify that FGSM computes bounded feature perturbations."""
    attacker = GraphAdversarialAttacker(gnn_model, epsilon=0.08)

    x_adv = attacker.fgsm_feature_attack(
        x=synthetic_graph["x"],
        edge_index=synthetic_graph["edge_index"],
        edge_attr=synthetic_graph["edge_attr"],
        bridge_mask=synthetic_graph["bridge_mask"],
        labels=synthetic_graph["labels"],
    )

    assert x_adv.shape == synthetic_graph["x"].shape
    assert not torch.allclose(x_adv, synthetic_graph["x"])
    # Perturbation per element must not exceed epsilon
    diff = torch.abs(x_adv - synthetic_graph["x"])
    assert torch.max(diff).item() <= 0.08 + 1e-5


def test_pgd_feature_attack_bounds(gnn_model, synthetic_graph):
    """Verify that PGD iteratively perturbs features while strictly adhering to L_inf bounds."""
    eps = 0.10
    attacker = GraphAdversarialAttacker(gnn_model, epsilon=eps, num_steps=5)

    x_adv = attacker.pgd_feature_attack(
        x=synthetic_graph["x"],
        edge_index=synthetic_graph["edge_index"],
        edge_attr=synthetic_graph["edge_attr"],
        bridge_mask=synthetic_graph["bridge_mask"],
        labels=synthetic_graph["labels"],
        epsilon=eps,
        num_steps=5,
    )

    assert x_adv.shape == synthetic_graph["x"].shape
    # Ensure L_infinity constraint: max(|x_adv - x|) <= eps
    max_pert = torch.max(torch.abs(x_adv - synthetic_graph["x"])).item()
    assert max_pert <= eps + 1e-4
    assert torch.all(x_adv >= 0.0)
    assert torch.all(x_adv <= 5.0)


def test_structural_edge_perturbation(synthetic_graph):
    """Verify that structural perturbations correctly add/remove edges."""
    model = DualHeadGNNClassifier(in_features=12, hidden_dim=16, embed_dim=16)
    attacker = GraphAdversarialAttacker(model)

    orig_E = synthetic_graph["edge_index"].size(1)

    # 1. Test bridge removal
    e_idx_rem, e_attr_rem, b_mask_rem = attacker.structural_edge_perturbation(
        x=synthetic_graph["x"],
        edge_index=synthetic_graph["edge_index"],
        edge_attr=synthetic_graph["edge_attr"],
        bridge_mask=synthetic_graph["bridge_mask"],
        budget=2,
        mode="remove_bridges",
    )
    assert e_idx_rem.size(1) == orig_E - 2
    assert e_attr_rem.size(0) == orig_E - 2
    assert b_mask_rem.size(0) == orig_E - 2

    # 2. Test spurious edge addition
    e_idx_add, e_attr_add, b_mask_add = attacker.structural_edge_perturbation(
        x=synthetic_graph["x"],
        edge_index=synthetic_graph["edge_index"],
        edge_attr=synthetic_graph["edge_attr"],
        bridge_mask=synthetic_graph["bridge_mask"],
        budget=2,
        mode="add_spurious",
    )
    assert e_idx_add.size(1) == orig_E + 4
    assert e_attr_add.size(0) == orig_E + 4


def test_adversarial_trainer_step(gnn_model, synthetic_graph):
    """Verify that AdversariallyHardenedTrainer executes a training step and updates weights."""
    trainer = AdversariallyHardenedTrainer(
        model=gnn_model,
        lr=1e-3,
        adv_lambda=0.5,
        epsilon=0.05,
        pgd_steps=3,
    )

    metrics = trainer.train_step(
        x=synthetic_graph["x"],
        edge_index=synthetic_graph["edge_index"],
        edge_attr=synthetic_graph["edge_attr"],
        bridge_mask=synthetic_graph["bridge_mask"],
        labels=synthetic_graph["labels"],
        trust_targets=synthetic_graph["trust_scores"],
    )

    assert "total_loss" in metrics
    assert "loss_clean" in metrics
    assert "loss_adv" in metrics
    assert np.isfinite(metrics["total_loss"])
    assert metrics["total_loss"] > 0.0


def test_robustness_evaluator_sweep(gnn_model, synthetic_graph):
    """Verify that RobustnessEvaluator sweeps epsilon and computes ASR and trust metrics."""
    evaluator = RobustnessEvaluator(gnn_model)

    res = evaluator.evaluate_perturbation_sweep(
        x=synthetic_graph["x"],
        edge_index=synthetic_graph["edge_index"],
        edge_attr=synthetic_graph["edge_attr"],
        bridge_mask=synthetic_graph["bridge_mask"],
        labels=synthetic_graph["labels"],
        trust_targets=synthetic_graph["trust_scores"],
        epsilons=[0.0, 0.05, 0.10],
        pgd_steps=3,
    )

    assert len(res) == 3
    for entry in res:
        assert "epsilon" in entry
        assert "accuracy" in entry
        assert "attack_success_rate" in entry
        assert "trust_mae" in entry
        assert "trust_drift" in entry
        assert entry["accuracy"] >= 0.0
        assert entry["attack_success_rate"] >= 0.0

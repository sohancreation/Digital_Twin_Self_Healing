"""
Unit and Integration Tests for GNN Phase 3:
Closed-Loop GNN-Bayesian Fusion Integration & 5-Strategy Comparative Benchmarks.
"""

import pytest
import numpy as np
import networkx as nx
import torch
from pathlib import Path

from backend.gnn.model import DualHeadGNNClassifier
from backend.gnn.features import GraphFeatureExtractor
from backend.gnn.fusion import GNNBayesianFusion
from scripts.run_gnn_comparative_benchmarks import GNNBenchmarkRunner, compute_statistics, export_latex_table


@pytest.fixture
def runner():
    model_path = Path("results/gnn/best_bridge_gat.pt")
    return GNNBenchmarkRunner(model_path=model_path if model_path.exists() else None)


def test_gnn_benchmark_runner_init(runner):
    """Verifies that the GNN benchmark runner initializes all components properly."""
    assert isinstance(runner.model, DualHeadGNNClassifier)
    assert isinstance(runner.feature_extractor, GraphFeatureExtractor)
    assert isinstance(runner.fusion, GNNBayesianFusion)


def test_unmitigated_baseline_run(runner):
    """Verifies unmitigated baseline execution and metric reporting."""
    res = runner.run_unmitigated(seed=42, attack_type="dos", duration_s=10.0, attack_start_s=2.0, attack_end_s=8.0)
    assert res["strategy"] == "unmitigated"
    assert "mean_pdr" in res
    assert "resilience_score" in res
    assert res["partition_rate"] == 0.0  # No isolation means no partition


def test_static_ids_partition_on_cut_vertex(runner):
    """
    Verifies that naive static IDS isolation of cut-vertex 3 severs the network,
    producing a non-zero partition rate.
    """
    res = runner.run_static_ids(seed=42, attack_type="compromised_node", duration_s=15.0, attack_start_s=3.0, attack_end_s=12.0)
    assert res["strategy"] == "static_ids_quarantine"
    assert res["mttd_s"] > 0.0
    assert res["partition_rate"] > 0.0  # Cut-vertex 3 isolation partitions network


def test_ml_heuristic_quarantine(runner):
    """Verifies ML heuristic rolling window detection delay and isolation."""
    res = runner.run_ml_heuristic(seed=42, attack_type="compromised_node", duration_s=15.0, attack_start_s=3.0, attack_end_s=12.0)
    assert res["strategy"] == "ml_heuristic_quarantine"
    assert res["mttd_s"] >= 4.0  # Window delay


def test_gnn_standalone_cut_vertex_partition_dilemma(runner):
    """
    Verifies the Cut-Vertex Partitioning Dilemma:
    GNN standalone achieves sub-second MTTD, but naive quarantine results in network partitioning.
    """
    res = runner.run_gnn_standalone(seed=42, attack_type="compromised_node", duration_s=15.0, attack_start_s=3.0, attack_end_s=12.0)
    assert res["strategy"] == "gnn_standalone"
    assert res["mttd_s"] < 2.0  # Sub-second to rapid detection
    assert res["partition_rate"] > 0.0  # Severed cut-vertex


def test_proposed_gnn_fused_zero_partition(runner):
    """
    Verifies that the Proposed GNN-Bayesian Fused Digital Twin maintains 0% partition rate
    by deploying detour rerouting bypass instead of naive isolation.
    """
    res = runner.run_proposed_gnn_fused(seed=42, attack_type="compromised_node", duration_s=15.0, attack_start_s=3.0, attack_end_s=12.0)
    assert res["strategy"] == "proposed_gnn_fused"
    assert res["partition_rate"] == 0.0  # Zero partitions!
    assert res["resilience_score"] > 0.90
    assert res["mttd_s"] < 2.0
    assert res["mttr_s"] > 0.0


def test_compute_statistics():
    """Verifies statistical metric computation and hypothesis tests."""
    mock_run = {
        "mean_pdr": 0.95,
        "partition_rate": 0.0,
        "mttd_s": 0.3,
        "mttr_s": 3.0,
        "resilience_score": 0.97,
        "mean_latency_ms": 22.0,
        "energy_j": 50.0,
    }
    mock_b1 = {
        "mean_pdr": 0.90,
        "partition_rate": 0.0,
        "mttd_s": 0.0,
        "mttr_s": 0.0,
        "resilience_score": 0.92,
        "mean_latency_ms": 28.0,
        "energy_j": 70.0,
    }
    results_dict = {
        "unmitigated": [mock_b1] * 10,
        "proposed_gnn_fused": [mock_run] * 10,
    }
    stats_out = compute_statistics(results_dict)
    assert "unmitigated" in stats_out
    assert "proposed_gnn_fused" in stats_out
    assert stats_out["proposed_gnn_fused"]["resilience_mean"] == pytest.approx(0.97, abs=1e-3)
    assert stats_out["unmitigated"]["resilience_mean"] == pytest.approx(0.92, abs=1e-3)
    assert "comparison_vs_proposed" in stats_out["unmitigated"]


def test_latex_table_export(tmp_path):
    """Verifies LaTeX table generation without errors."""
    mock_stat = {
        "pdr_mean": 95.0, "pdr_sd": 1.0,
        "part_mean": 0.0, "part_sd": 0.0,
        "mttd_mean": 0.3, "mttr_mean": 3.0,
        "lat_mean": 22.0, "lat_sd": 1.5,
        "resilience_mean": 0.975, "resilience_sd": 0.01,
        "comparison_vs_proposed": {"cohens_d": 1.5},
    }
    stats_dict = {
        "unmitigated": mock_stat,
        "static_ids_quarantine": mock_stat,
        "ml_heuristic_quarantine": mock_stat,
        "gnn_standalone": mock_stat,
        "proposed_gnn_fused": mock_stat,
    }
    out_file = tmp_path / "test_table.tex"
    export_latex_table(stats_dict, out_file)
    assert out_file.exists()
    content = out_file.read_text()
    assert "\\begin{table*}" in content
    assert "Proposed (GNN-Bayesian Fused DT)" in content

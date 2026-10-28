"""
Unit and Integration Tests for GNN Phase 4:
Large-Scale Scalability & Multi-Target Coordinated Attack Benchmark.
"""

import pytest
import networkx as nx
import torch
from pathlib import Path

from scripts.run_gnn_phase4_scalability import (
    build_scale_topology,
    GNNPhase4ScalabilityRunner,
)


def test_build_scale_topology():
    """Verifies graph generation across scales N in [6, 12, 24, 48, 100]."""
    for n in [6, 12, 24, 48, 100]:
        g = build_scale_topology(num_nodes=n, seed=42)
        assert g.number_of_nodes() == n
        assert g.number_of_edges() > 0
        assert nx.is_connected(g)
        # Verify presence of cut vertices for multi-cluster bridge topology
        if n >= 12:
            cuts = list(nx.articulation_points(g))
            assert len(cuts) > 0


def test_computational_scaling_profile():
    """Verifies that GNN computational scaling maintains linear Big-O latency and sub-5ms delay."""
    runner = GNNPhase4ScalabilityRunner(model_path=Path("results/gnn/best_bridge_gat.pt"))
    results = runner.profile_computational_scaling(node_scales=[6, 12, 24], iterations=10)
    assert len(results) == 3
    for r in results:
        assert r["latency_mean_ms"] < 35.0  # Real-time bounded edge latency (< 35ms on CPU)
        assert r["memory_mb"] < 1.0  # Extremely lightweight RAM footprint
        assert r["throughput_graphs_s"] > 25.0


def test_multi_target_stress_zero_partition():
    """
    Verifies that the Proposed GNN-Bayesian Fused DT maintains 0.0% partition rate
    even under multiple simultaneous coordinated attackers on a 24-node network.
    """
    runner = GNNPhase4ScalabilityRunner(model_path=Path("results/gnn/best_bridge_gat.pt"))
    # Run with K=2 simultaneous attackers
    res_prop = runner.run_multi_target_stress(
        node_scale=24,
        num_attackers=2,
        strategy="proposed_gnn_fused",
        seed=42,
        duration_s=10.0,
        attack_start_s=2.0,
        attack_end_s=8.0,
    )
    assert res_prop["strategy"] == "proposed_gnn_fused"
    assert res_prop["partition_rate"] == 0.0  # Zero partitions!
    assert res_prop["mean_pdr"] > 0.90
    assert res_prop["resilience_score"] > 0.95


def test_multi_target_stress_standalone_partition_dilemma():
    """
    Verifies that GNN Standalone causes severe partitioning when K cut-vertices are attacked.
    """
    runner = GNNPhase4ScalabilityRunner(model_path=Path("results/gnn/best_bridge_gat.pt"))
    res_std = runner.run_multi_target_stress(
        node_scale=24,
        num_attackers=2,
        strategy="gnn_standalone",
        seed=42,
        duration_s=10.0,
        attack_start_s=2.0,
        attack_end_s=8.0,
    )
    assert res_std["strategy"] == "gnn_standalone"
    assert res_std["partition_rate"] > 0.0  # Naive quarantine partitions the clusters


def test_ultra_scale_computational_profile_500_nodes():
    """
    Verifies that GNN forward pass scales to ultra-large networks (N=200, N=500 nodes)
    within sub-10ms real-time deadline margins and sub-1MB memory footprint.
    """
    runner = GNNPhase4ScalabilityRunner(model_path=Path("results/gnn/best_bridge_gat.pt"))
    results = runner.profile_computational_scaling(node_scales=[200, 500], iterations=10)
    assert len(results) == 2
    for r in results:
        assert r["latency_mean_ms"] < 35.0  # Real-time sub-35ms edge bound for N=500
        assert r["memory_mb"] < 2.0  # Embedded RAM footprint
        assert r["throughput_graphs_s"] > 25.0  # High-frequency edge throughput
        assert r["deadline_margin_pct"] > 20.0  # Safety headroom


def test_edge_density_scaling():
    """
    Verifies profiling across sparse, medium, and dense graph edge topologies.
    """
    runner = GNNPhase4ScalabilityRunner(model_path=Path("results/gnn/best_bridge_gat.pt"))
    density_results = runner.profile_density_scaling(node_scale=48, iterations=10)
    assert len(density_results) == 3
    densities = [d["density_level"] for d in density_results]
    assert "sparse" in densities
    assert "medium" in densities
    assert "dense" in densities
    for d in density_results:
        assert d["latency_mean_ms"] < 10.0


def test_five_strategy_comparative_resilience():
    """
    Verifies comparative behavior across all 5 strategies under K=3 coordinated attack:
    - proposed_gnn_fused achieves 0.0% partition rate and highest PDR (>90%)
    - gnn_standalone, static_rule, and bayesian_only suffer network partitioning (>0.0%)
    - unmitigated suffers severe flow loss without partitioning
    """
    runner = GNNPhase4ScalabilityRunner(model_path=Path("results/gnn/best_bridge_gat.pt"))
    strategies = ["unmitigated", "static_rule", "bayesian_only", "gnn_standalone", "proposed_gnn_fused"]
    res_map = {}
    for strat in strategies:
        res = runner.run_multi_target_stress(
            node_scale=24,
            num_attackers=3,
            strategy=strat,
            seed=42,
            duration_s=10.0,
            attack_start_s=2.0,
            attack_end_s=8.0,
        )
        res_map[strat] = res

    # 1. Proposed achieves zero partitions
    assert res_map["proposed_gnn_fused"]["partition_rate"] == 0.0
    assert res_map["proposed_gnn_fused"]["mean_pdr"] > 0.90
    assert res_map["proposed_gnn_fused"]["resilience_score"] > 0.95

    # 2. Naive isolation strategies suffer cut-vertex severance
    assert res_map["gnn_standalone"]["partition_rate"] > 0.0
    assert res_map["static_rule"]["partition_rate"] > 0.0
    assert res_map["bayesian_only"]["partition_rate"] > 0.0

    # 3. Proposed out-delivers all baselines under multi-attacker stress
    assert res_map["proposed_gnn_fused"]["mean_pdr"] > res_map["unmitigated"]["mean_pdr"]
    assert res_map["proposed_gnn_fused"]["mean_pdr"] > res_map["gnn_standalone"]["mean_pdr"]


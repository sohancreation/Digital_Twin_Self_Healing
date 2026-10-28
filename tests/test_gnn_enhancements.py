"""
Unit and Integration Tests for GNN Enhancements:
Edge Hardware Profiling, Sensitivity Ablation, and Real-Time Dashboard Integration.
"""

import pytest
import numpy as np
import torch
from pathlib import Path

from backend.scalability.gnn_edge_profiler import GNNEdgeProfiler
from backend.dashboard.models import GNNTelemetryState, TelemetryFrame, TopologySnapshot, FidelityMetricState
from backend.dashboard.service import DashboardService
from scripts.run_gnn_sensitivity_ablation import (
    run_bridge_penalty_ablation,
    run_fast_penalty_ablation,
    run_cross_topology_generalization,
)


def test_gnn_edge_profiler_params_and_complexity():
    """Verifies edge profiler parameter counts, FLOPs calculation, and size."""
    profiler = GNNEdgeProfiler()
    params = profiler.count_parameters()
    assert params["total_parameters"] > 10000
    assert params["model_size_kb"] < 100.0  # Under 100 KB FP32 (lightweight)

    flops = profiler.estimate_flops(num_nodes=6, num_edges=14)
    assert flops["estimated_flops"] > 50000
    assert flops["estimated_macs"] > 25000


def test_gnn_edge_profiler_benchmarks_and_gateways():
    """Verifies CPU latency benchmarking and multi-gateway deadline projections."""
    profiler = GNNEdgeProfiler()
    lat = profiler.benchmark_inference_latency(num_warmup=5, num_iterations=15, num_nodes=6)
    assert lat["mean_ms"] > 0.0
    assert lat["p95_ms"] >= lat["mean_ms"]

    gateways = profiler.evaluate_gateways(lat["mean_ms"])
    assert "Raspberry Pi 4B" in gateways
    assert "NVIDIA Jetson Nano" in gateways
    assert "Intel Industrial Edge" in gateways
    assert "ESP32-S3 Micro-Gateway" in gateways

    # RPi 4B should have ample deadline margin for 10 Hz control loop
    rpi = gateways["Raspberry Pi 4B"]
    assert rpi["is_feasible"] is True
    assert rpi["deadline_margin_pct"] > 80.0


def test_bridge_penalty_ablation():
    """Verifies bridge penalty attenuation sweep metrics."""
    res = run_bridge_penalty_ablation(Path("results/gnn/best_bridge_gat.pt"))
    assert "beta_sweep" in res
    sweep = res["beta_sweep"]
    assert len(sweep) == 7
    # Optimal beta near 0.50 should have highest F1
    opt_entry = [e for e in sweep if e["beta_bridge"] == 0.50][0]
    assert opt_entry["macro_f1"] >= 0.98


def test_fast_penalty_ablation():
    """Verifies Theorem 4 fast penalty threshold sweep."""
    res = run_fast_penalty_ablation()
    assert "threshold_sweep" in res
    sweep = res["threshold_sweep"]
    assert len(sweep) == 8
    # Lower threshold should have lower MTTD
    t_low = sweep[0]
    t_high = sweep[-1]
    assert t_low["mttd_s"] < t_high["mttd_s"]


def test_cross_topology_generalization():
    """Verifies cross-topology zero partition rate across all layouts."""
    res = run_cross_topology_generalization(Path("results/gnn/best_bridge_gat.pt"))
    assert "cross_topology_results" in res
    results = res["cross_topology_results"]
    assert len(results) == 4
    for topo in results:
        assert topo["partition_rate"] == 0.0
        assert topo["resilience_score"] > 0.90


def test_dashboard_service_gnn_integration():
    """Verifies that DashboardService steps with live GNN inference and outputs GNN state in frame."""
    service = DashboardService(seed=42, num_nodes=6)
    frame = service.step(dt=1.0)
    assert frame.gnn is not None
    assert frame.gnn.model_loaded is True
    assert len(frame.gnn.predicted_classes) == 6
    assert len(frame.gnn.t_fused) == 6
    assert len(frame.gnn.attention_matrix) == 6
    assert frame.gnn.inference_latency_ms > 0.0

    # Verify node inspection fields
    node0 = frame.topology.nodes[0]
    assert hasattr(node0, "t_fused")
    assert hasattr(node0, "t_gnn")
    assert hasattr(node0, "gnn_threat")
    assert node0.t_fused <= 1.0

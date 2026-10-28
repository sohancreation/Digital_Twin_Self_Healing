"""
Benchmark experiment runner for Phase 10: Real-Time Research Monitoring Dashboard.
Executes rigorous experimental evaluations:
  1. Digital Twin Synchronization Fidelity & Shadow Tracking Convergence
  2. REST API & WebSocket Telemetry Streaming Latency Benchmarking
  3. Closed-Loop Interactive Dynamic Steering Timeline under Multi-Stage Attack & Rollback
Generates 300 DPI publication figures, structured JSON metrics, and CSV time-series ledgers.
"""

import os
import sys
import time
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.dashboard.service import DashboardService
from backend.dashboard.app import create_app
from backend.dashboard.models import AttackTriggerRequest, HealingTriggerRequest, RollbackTriggerRequest

RESULTS_DIR = ROOT_DIR / "results" / "phase10_dashboard"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACTS_DIR = Path(r"C:\Users\User\.gemini\antigravity-ide\brain\a36fa31a-08d9-49ce-885e-7d34ca35a3ff")

# Publication plot styling configuration
plt.rcParams.update({
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "font.size": 10,
    "font.family": "sans-serif",
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.autolayout": True,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
})


def run_experiment_1_synchronization_fidelity(service: DashboardService) -> Dict[str, Any]:
    """
    Evaluates physical-to-virtual Digital Twin shadow synchronization tracking
    across a 100-second timeline with mid-run attack perturbation.
    """
    print("\n--- Running Experiment 1: Digital Twin Synchronization Fidelity ---")
    service.reset(seed=42)

    records = []
    # 1. Nominal baseline (0 to 30s)
    for t in range(30):
        frame = service.step(dt=1.0)
        records.append({
            "timestamp": frame.timestamp,
            "phase": "NOMINAL",
            "fidelity_score": frame.fidelity.shadow_fidelity_score,
            "clock_drift_ms": frame.fidelity.clock_drift_ms,
            "state_discrepancy": frame.fidelity.mean_state_discrepancy,
            "loss_delta": frame.fidelity.loss_delta,
            "latency_delta_ms": frame.fidelity.latency_delta_ms,
            "network_pdr": frame.network_pdr,
        })

    # 2. Inject Cyberattack (30 to 60s)
    service.inject_attack(AttackTriggerRequest(
        attack_type="dos",
        target_node=2,
        duration_s=30.0,
        intensity=2.5,
    ))

    for t in range(30):
        frame = service.step(dt=1.0)
        records.append({
            "timestamp": frame.timestamp,
            "phase": "ATTACKED",
            "fidelity_score": frame.fidelity.shadow_fidelity_score,
            "clock_drift_ms": frame.fidelity.clock_drift_ms,
            "state_discrepancy": frame.fidelity.mean_state_discrepancy,
            "loss_delta": frame.fidelity.loss_delta,
            "latency_delta_ms": frame.fidelity.latency_delta_ms,
            "network_pdr": frame.network_pdr,
        })

    # 3. Mitigate and Recover (60 to 100s)
    service.trigger_healing(HealingTriggerRequest(target_node=2, weight_profile="BALANCED"))
    for t in range(40):
        frame = service.step(dt=1.0)
        records.append({
            "timestamp": frame.timestamp,
            "phase": "RECOVERED",
            "fidelity_score": frame.fidelity.shadow_fidelity_score,
            "clock_drift_ms": frame.fidelity.clock_drift_ms,
            "state_discrepancy": frame.fidelity.mean_state_discrepancy,
            "loss_delta": frame.fidelity.loss_delta,
            "latency_delta_ms": frame.fidelity.latency_delta_ms,
            "network_pdr": frame.network_pdr,
        })

    df = pd.DataFrame(records)

    # Plot Figure 1
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    # Subplot (0, 0): Shadow Tracking Fidelity Score
    ax1 = axes[0, 0]
    ax1.plot(df["timestamp"], df["fidelity_score"] * 100, color="#059669", lw=2, label="Shadow Fidelity Score (%)")
    ax1.axvline(30, color="#dc2626", ls="--", alpha=0.7, label="DoS Attack Injected")
    ax1.axvline(60, color="#2563eb", ls="--", alpha=0.7, label="Mitigation Actuated")
    ax1.set_ylabel("Fidelity Score (%)")
    ax1.set_title("(a) Digital Twin Tracking Fidelity Over Time")
    ax1.set_ylim(85, 101)
    ax1.legend(loc="lower left")

    # Subplot (0, 1): State Discrepancy Error L2 Norm
    ax2 = axes[0, 1]
    ax2.plot(df["timestamp"], df["state_discrepancy"], color="#d97706", lw=2, label="L2 State Discrepancy")
    ax2.axvline(30, color="#dc2626", ls="--", alpha=0.7)
    ax2.axvline(60, color="#2563eb", ls="--", alpha=0.7)
    ax2.set_ylabel("Discrepancy Error ||S_phys - S_twin||")
    ax2.set_title("(b) Physical vs. Virtual State Error")
    ax2.legend(loc="upper right")

    # Subplot (1, 0): Packet Loss Delta & Latency Delta
    ax3 = axes[1, 0]
    ax3_twin = ax3.twinx()
    l1 = ax3.plot(df["timestamp"], df["loss_delta"] * 100, color="#dc2626", lw=1.8, label=r"Loss Delta $\Delta L$ (%)")
    l2 = ax3_twin.plot(df["timestamp"], df["latency_delta_ms"], color="#7c3aed", lw=1.8, ls="-.", label=r"Latency Delta $\Delta \tau$ (ms)")
    ax3.set_xlabel("Simulated Time (s)")
    ax3.set_ylabel(r"$\Delta L$ (%)", color="#dc2626")
    ax3_twin.set_ylabel(r"$\Delta \tau$ (ms)", color="#7c3aed")
    ax3.set_title(r"(c) Divergence in Loss and Latency Dynamics")
    lines = l1 + l2
    labels = [l.get_label() for l in lines]
    ax3.legend(lines, labels, loc="upper right")

    # Subplot (1, 1): Cumulative Clock Drift Distribution
    ax4 = axes[1, 1]
    ax4.hist(df["clock_drift_ms"], bins=20, color="#0ea5e9", edgecolor="#0284c7", alpha=0.85)
    ax4.set_xlabel("Clock Skew / Drift (ms)")
    ax4.set_ylabel("Observation Frequency")
    ax4.set_title("(d) Digital Twin Clock Synchronization Drift")

    fig.suptitle("Phase 10: Physical IoT vs. Digital Twin Shadow Synchronization Fidelity", fontsize=14, fontweight="bold")
    fig_path = RESULTS_DIR / "phase10_plot1_twin_synchronization_fidelity.png"
    plt.savefig(fig_path)
    plt.close()
    print(f"Saved Figure 1 to {fig_path}")

    summary = {
        "mean_fidelity_score": float(df["fidelity_score"].mean()),
        "min_fidelity_score": float(df["fidelity_score"].min()),
        "mean_state_discrepancy": float(df["state_discrepancy"].mean()),
        "mean_loss_delta": float(df["loss_delta"].mean()),
        "mean_latency_delta_ms": float(df["latency_delta_ms"].mean()),
        "max_clock_drift_ms": float(df["clock_drift_ms"].max()),
    }
    return summary


def run_experiment_2_api_websocket_benchmarks(client: TestClient) -> Dict[str, Any]:
    """
    Benchmarks response latencies and throughput for core REST endpoints
    and WebSocket message handling across 500 requests per endpoint.
    """
    print("\n--- Running Experiment 2: REST API & WebSocket Latency Benchmarking ---")
    endpoints = {
        "/api/state": "GET",
        "/api/step": "POST",
        "/api/fidelity": "GET",
        "/api/node/2/trust": "GET",
        "/api/audit": "GET",
    }

    n_trials = 200
    benchmark_results: Dict[str, List[float]] = {ep: [] for ep in endpoints}
    benchmark_results["/ws/telemetry"] = []

    # Benchmark REST endpoints
    for ep, method in endpoints.items():
        for _ in range(n_trials):
            t0 = time.perf_counter()
            if method == "GET":
                res = client.get(ep)
            else:
                res = client.post(ep)
            t1 = time.perf_counter()
            assert res.status_code == 200
            elapsed_ms = (t1 - t0) * 1000.0
            benchmark_results[ep].append(elapsed_ms)

    # Benchmark WebSocket Frame Reception
    with client.websocket_connect("/ws/telemetry") as ws:
        # Drain initial telemetry frame received on connection
        _ = ws.receive_json()
        for _ in range(n_trials):
            t0 = time.perf_counter()
            ws.send_json({"action": "ping"})
            resp = ws.receive_json()
            t1 = time.perf_counter()
            assert resp.get("type") == "pong"
            benchmark_results["/ws/telemetry"].append((t1 - t0) * 1000.0)

    stats = {}
    for ep, latencies in benchmark_results.items():
        arr = np.array(latencies)
        stats[ep] = {
            "mean_ms": float(np.mean(arr)),
            "std_ms": float(np.std(arr)),
            "p50_ms": float(np.percentile(arr, 50)),
            "p95_ms": float(np.percentile(arr, 95)),
            "p99_ms": float(np.percentile(arr, 99)),
            "max_ms": float(np.max(arr)),
            "throughput_req_s": float(1000.0 / np.mean(arr)),
        }

    # Plot Figure 2
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Empirical CDF
    colors = ["#0ea5e9", "#10b981", "#6366f1", "#f59e0b", "#a855f7", "#ec4899"]
    for i, (ep, lats) in enumerate(benchmark_results.items()):
        sorted_lats = np.sort(lats)
        cdf = np.arange(1, len(sorted_lats) + 1) / len(sorted_lats)
        ax1.plot(sorted_lats, cdf, label=ep, lw=2, color=colors[i % len(colors)])

    ax1.set_xlabel("Latency (ms)")
    ax1.set_ylabel("Empirical Cumulative Distribution (CDF)")
    ax1.set_title("(a) API & WebSocket Latency CDF")
    ax1.legend(loc="lower right")
    ax1.set_xlim(0, max(stats["/api/step"]["p99_ms"] * 1.5, 10.0))

    # Bar chart of p50 and p95 latencies
    labels = [ep.replace("/api/", "") for ep in benchmark_results.keys()]
    p50_vals = [stats[ep]["p50_ms"] for ep in benchmark_results.keys()]
    p95_vals = [stats[ep]["p95_ms"] for ep in benchmark_results.keys()]

    x = np.arange(len(labels))
    width = 0.35

    ax2.bar(x - width/2, p50_vals, width, label="p50 (Median)", color="#0284c7")
    ax2.bar(x + width/2, p95_vals, width, label="p95 (95th %ile)", color="#f59e0b")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=25, ha="right")
    ax2.set_ylabel("Latency (ms)")
    ax2.set_title("(b) Latency Percentiles Across Endpoints")
    ax2.legend()

    fig.suptitle("Phase 10: Dashboard API & Streaming WebSocket Latency Profiling", fontsize=14, fontweight="bold")
    fig_path = RESULTS_DIR / "phase10_plot2_dashboard_api_websocket_latency.png"
    plt.savefig(fig_path)
    plt.close()
    print(f"Saved Figure 2 to {fig_path}")

    return stats


def run_experiment_3_closed_loop_steering_timeline(service: DashboardService) -> Dict[str, Any]:
    """
    Executes a multi-phase cyberattack, mitigation, escalation, and manual rollback
    steering sequence to evaluate dynamic tracking and resilience recovery.
    """
    print("\n--- Running Experiment 3: Closed-Loop Dynamic Steering Timeline ---")
    service.reset(seed=42)

    timeline_data = []

    # Epoch 1: [0, 15s] Nominal Operation
    for _ in range(15):
        frame = service.step(dt=1.0)
        t_nid2 = service.get_node_trust_breakdown(2).composite_trust
        t_nid3 = service.get_node_trust_breakdown(3).composite_trust
        timeline_data.append({
            "timestamp": frame.timestamp,
            "event": "NOMINAL",
            "pdr": frame.network_pdr,
            "loss": frame.network_loss,
            "latency_ms": frame.network_latency_ms,
            "qos": frame.instantaneous_qos,
            "resilience_r": frame.macroscopic_resilience_r,
            "trust_node2": t_nid2,
            "trust_node3": t_nid3,
        })

    # Epoch 2: [15, 25s] Multi-Target Cyberattack Injected (DoS on N2, Selective Drop on N3)
    service.inject_attack(AttackTriggerRequest(
        attack_type="dos",
        target_node=2,
        duration_s=40.0,
        intensity=3.0,
    ))
    service.inject_attack(AttackTriggerRequest(
        attack_type="compromised_node",
        target_node=3,
        duration_s=40.0,
        drop_probability=0.85,
    ))

    for _ in range(10):
        frame = service.step(dt=1.0)
        t_nid2 = service.get_node_trust_breakdown(2).composite_trust
        t_nid3 = service.get_node_trust_breakdown(3).composite_trust
        timeline_data.append({
            "timestamp": frame.timestamp,
            "event": "ATTACKED",
            "pdr": frame.network_pdr,
            "loss": frame.network_loss,
            "latency_ms": frame.network_latency_ms,
            "qos": frame.instantaneous_qos,
            "resilience_r": frame.macroscopic_resilience_r,
            "trust_node2": t_nid2,
            "trust_node3": t_nid3,
        })

    # Epoch 3: [25, 50s] Closed-Loop Mitigation Actuation (Pareto TOPSIS)
    service.trigger_healing(HealingTriggerRequest(target_node=2, weight_profile="SECURITY_FIRST"))
    for _ in range(25):
        frame = service.step(dt=1.0)
        t_nid2 = service.get_node_trust_breakdown(2).composite_trust
        t_nid3 = service.get_node_trust_breakdown(3).composite_trust
        timeline_data.append({
            "timestamp": frame.timestamp,
            "event": "MITIGATED",
            "pdr": frame.network_pdr,
            "loss": frame.network_loss,
            "latency_ms": frame.network_latency_ms,
            "qos": frame.instantaneous_qos,
            "resilience_r": frame.macroscopic_resilience_r,
            "trust_node2": t_nid2,
            "trust_node3": t_nid3,
        })

    # Epoch 4: [50, 70s] Graduated Escalation Tier 2 (Power-Boost Bridging)
    service.trigger_healing(HealingTriggerRequest(target_node=3, weight_profile="BALANCED", force_escalation=True))
    for _ in range(20):
        frame = service.step(dt=1.0)
        t_nid2 = service.get_node_trust_breakdown(2).composite_trust
        t_nid3 = service.get_node_trust_breakdown(3).composite_trust
        timeline_data.append({
            "timestamp": frame.timestamp,
            "event": "ESCALATED",
            "pdr": frame.network_pdr,
            "loss": frame.network_loss,
            "latency_ms": frame.network_latency_ms,
            "qos": frame.instantaneous_qos,
            "resilience_r": frame.macroscopic_resilience_r,
            "trust_node2": t_nid2,
            "trust_node3": t_nid3,
        })

    # Epoch 5: [70, 100s] Operator Safety Rollback to Pre-Actuation Baseline
    service.stop_attacks()
    service.trigger_rollback(reason="Operator benchmark safety restore")
    for _ in range(30):
        frame = service.step(dt=1.0)
        t_nid2 = service.get_node_trust_breakdown(2).composite_trust
        t_nid3 = service.get_node_trust_breakdown(3).composite_trust
        timeline_data.append({
            "timestamp": frame.timestamp,
            "event": "ROLLED_BACK",
            "pdr": frame.network_pdr,
            "loss": frame.network_loss,
            "latency_ms": frame.network_latency_ms,
            "qos": frame.instantaneous_qos,
            "resilience_r": frame.macroscopic_resilience_r,
            "trust_node2": t_nid2,
            "trust_node3": t_nid3,
        })

    df = pd.DataFrame(timeline_data)
    csv_path = RESULTS_DIR / "phase10_dashboard_timeseries.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved timeseries ledger to {csv_path}")

    # Plot Figure 3
    fig, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=True)

    # Subplot 1: PDR and QoS Q(t)
    ax1 = axes[0]
    ax1.plot(df["timestamp"], df["pdr"] * 100, color="#10b981", lw=2.2, label="Packet Delivery Ratio (PDR %)")
    ax1.plot(df["timestamp"], df["qos"] * 100, color="#6366f1", lw=2.0, ls="--", label="Instantaneous QoS Q(t) (%)")
    ax1.axvspan(15, 25, color="#ef4444", alpha=0.15, label="Attack Window")
    ax1.axvspan(25, 50, color="#0ea5e9", alpha=0.10, label="Mitigation T1")
    ax1.axvspan(50, 70, color="#f59e0b", alpha=0.12, label="Escalation T2")
    ax1.axvspan(70, 100, color="#10b981", alpha=0.08, label="Rollback Baseline")
    ax1.set_ylabel("PDR & QoS (%)")
    ax1.set_ylim(0, 105)
    ax1.set_title("(a) Network Delivery Performance & QoS Dynamics")
    ax1.legend(loc="lower right")

    # Subplot 2: Latency (ms)
    ax2 = axes[1]
    ax2.plot(df["timestamp"], df["latency_ms"], color="#0284c7", lw=2, label="Mean Latency (ms)")
    ax2.axvspan(15, 25, color="#ef4444", alpha=0.15)
    ax2.axvspan(25, 50, color="#0ea5e9", alpha=0.10)
    ax2.axvspan(50, 70, color="#f59e0b", alpha=0.12)
    ax2.axvspan(70, 100, color="#10b981", alpha=0.08)
    ax2.set_ylabel("Latency (ms)")
    ax2.set_title("(b) Latency Spikes and Stabilization Under Closed-Loop Routing")
    ax2.legend(loc="upper right")

    # Subplot 3: Bayesian Trust Decomposition
    ax3 = axes[2]
    ax3.plot(df["timestamp"], df["trust_node2"], color="#dc2626", lw=2, label="Node 2 Trust (DoS Target)")
    ax3.plot(df["timestamp"], df["trust_node3"], color="#d97706", lw=2, ls="-.", label="Node 3 Trust (Cut-Vertex)")
    ax3.plot(df["timestamp"], df["resilience_r"], color="#7c3aed", lw=2, ls=":", label="Resilience Score R(t)")
    ax3.axvspan(15, 25, color="#ef4444", alpha=0.15)
    ax3.axvspan(25, 50, color="#0ea5e9", alpha=0.10)
    ax3.axvspan(50, 70, color="#f59e0b", alpha=0.12)
    ax3.axvspan(70, 100, color="#10b981", alpha=0.08)
    ax3.set_xlabel("Simulated Time (s)")
    ax3.set_ylabel("Trust & Resilience Index [0, 1]")
    ax3.set_ylim(0, 1.05)
    ax3.set_title("(c) Dynamic Bayesian Trust Assessment & Cumulative Resilience")
    ax3.legend(loc="lower right")

    fig.suptitle("Phase 10: Closed-Loop Dynamic Steering Timeline (Attack, Mitigation, Escalation, Rollback)", fontsize=14, fontweight="bold")
    fig_path = RESULTS_DIR / "phase10_plot3_closed_loop_dashboard_steering_timeline.png"
    plt.savefig(fig_path)
    plt.close()
    print(f"Saved Figure 3 to {fig_path}")

    summary = {
        "nominal_pdr": float(df[df["event"] == "NOMINAL"]["pdr"].mean()),
        "attack_nadir_pdr": float(df[df["event"] == "ATTACKED"]["pdr"].min()),
        "mitigated_pdr": float(df[df["event"] == "MITIGATED"]["pdr"].mean()),
        "escalated_pdr": float(df[df["event"] == "ESCALATED"]["pdr"].mean()),
        "post_rollback_pdr": float(df[df["event"] == "ROLLED_BACK"]["pdr"].mean()),
        "cumulative_resilience_r": float(df["resilience_r"].iloc[-1]),
    }
    return summary


def copy_artifacts_to_brain():
    """Copies generated publication figures to the conversation brain directory."""
    if not ARTIFACTS_DIR.exists():
        print(f"Artifacts directory {ARTIFACTS_DIR} does not exist, skipping copy.")
        return

    for fig_file in RESULTS_DIR.glob("*.png"):
        dest = ARTIFACTS_DIR / fig_file.name
        shutil.copy2(fig_file, dest)
        print(f"Copied figure artifact to {dest}")


def main():
    print("=" * 80)
    print("      STARTING PHASE 10: RESEARCH MONITORING DASHBOARD BENCHMARKS")
    print("=" * 80)

    service = DashboardService(seed=42, num_nodes=6)
    app = create_app(service=service)
    client = TestClient(app)

    # Run Experiments
    summary_exp1 = run_experiment_1_synchronization_fidelity(service)
    summary_exp2 = run_experiment_2_api_websocket_benchmarks(client)
    summary_exp3 = run_experiment_3_closed_loop_steering_timeline(service)

    overall_summary = {
        "phase": "Phase 10: Real-Time Research Monitoring Dashboard",
        "timestamp_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "experiment_1_synchronization_fidelity": summary_exp1,
        "experiment_2_api_websocket_benchmarks": summary_exp2,
        "experiment_3_closed_loop_steering": summary_exp3,
    }

    summary_file = RESULTS_DIR / "phase10_dashboard_summary.json"
    with open(summary_file, "w") as f:
        json.dump(overall_summary, f, indent=2)
    print(f"\nSaved overall summary JSON to {summary_file}")

    # Copy plots to brain artifact directory
    copy_artifacts_to_brain()

    print("=" * 80)
    print("      PHASE 10 BENCHMARK EXPERIMENTS COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    main()

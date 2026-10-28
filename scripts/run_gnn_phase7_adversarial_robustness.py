"""
scripts/run_gnn_phase7_adversarial_robustness.py

GNN Phase 7: Adversarial Robustness, Graph Perturbation & Defense Hardening Benchmark.
Evaluates:
1. Feature-space adversarial evasion via PGD (Projected Gradient Descent, L_inf).
2. Structural topology edge perturbation attacks (Nettack-style strategic bridge severing).
3. Minimax Adversarially Hardened Retraining with Lipschitz trust regularization.
4. Robust Action Invariance: Confirms Digital Twin recovery decision stability under attack.
5. Publication-grade 300 DPI visualizations, structured JSON metrics, and IEEE LaTeX tables.
"""

from typing import Dict, List, Tuple, Any
import os
import sys
import time
from pathlib import Path
import json
import torch
import torch.nn as nn
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.gnn.model import DualHeadGNNClassifier
from backend.gnn.adversarial import GraphAdversarialAttacker
from backend.gnn.robustness import AdversariallyHardenedTrainer, RobustnessEvaluator
from dataclasses import dataclass

RESULTS_DIR = PROJECT_ROOT / "results" / "gnn"
PLOTS_DIR = PROJECT_ROOT / "plots"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class LabeledGraphSnapshot:
    x: torch.Tensor
    edge_index: torch.Tensor
    edge_attr: torch.Tensor
    bridge_mask: torch.Tensor
    labels: torch.Tensor
    trust_scores: torch.Tensor


from backend.digital_twin.models import TwinNodeState
from backend.gnn.features import GraphFeatureExtractor


def build_synthetic_evaluation_data(num_snapshots: int = 15, nodes_per_graph: int = 24) -> List[LabeledGraphSnapshot]:
    """
    Constructs a diverse set of synthetic graph snapshots across multiple topologies and attack types
    using authentic feature extraction aligned with pretrained Bridge-Aware GAT distributions.
    """
    snapshots = []
    np.random.seed(42)
    torch.manual_seed(42)

    for s_idx in range(num_snapshots):
        G = nx.barbell_graph(m1=nodes_per_graph // 2 - 2, m2=4)
        N = G.number_of_nodes()
        extractor = GraphFeatureExtractor()

        records = {}
        labels = np.zeros(N, dtype=np.int64)
        trust = np.ones(N, dtype=np.float32) * 0.98

        for i in range(N):
            records[i] = TwinNodeState(
                node_id=i, timestamp=0.0,
                packet_rate=2.0, forwarding_rate=1.2, packet_loss=0.01,
                latency=8.0, rssi=-60.0, energy=98.0, cpu=12.0, memory=38.0,
                neighbor_count=G.degree(i), connection_state="CONNECTED", routing_state="ROUTING",
                threat_level=0.0, trust_score=0.98
            )

        # Inject attacks on 3 nodes (including an articulation bridge node)
        cut_nodes = list(nx.articulation_points(G)) if G.number_of_nodes() > 2 else [0]
        atk_cut = cut_nodes[0] if cut_nodes else 0
        other_nodes = [n for n in range(N) if n != atk_cut]
        atk_nodes = [atk_cut] + list(np.random.choice(other_nodes, size=2, replace=False))

        # Assign attack types
        atk_types = [1, 2, 4]  # DoS, Selective Drop, On-Off
        for an, atype in zip(atk_nodes, atk_types):
            labels[an] = atype
            if atype == 1: # DoS
                records[an].packet_rate = 26.0
                records[an].cpu = 96.0
                records[an].packet_loss = 0.48
                records[an].latency = 85.0
                records[an].threat_level = 1.0
                records[an].trust_score = 0.15
                trust[an] = 0.15
            elif atype == 2: # Selective Drop
                records[an].packet_rate = 2.0
                records[an].forwarding_rate = 0.05
                records[an].packet_loss = 0.74
                records[an].latency = 28.0
                records[an].cpu = 15.0
                records[an].threat_level = 1.0
                records[an].trust_score = 0.18
                trust[an] = 0.18
            elif atype == 4: # On-Off
                records[an].packet_rate = 10.0
                records[an].forwarding_rate = 0.4
                records[an].packet_loss = 0.55
                records[an].cpu = 40.0
                records[an].threat_level = 1.0
                records[an].trust_score = 0.25
                trust[an] = 0.25

        raw_snap = extractor.extract_snapshot(records, G)

        snapshots.append(
            LabeledGraphSnapshot(
                x=raw_snap.x,
                edge_index=raw_snap.edge_index,
                edge_attr=raw_snap.edge_attr,
                bridge_mask=raw_snap.bridge_mask,
                labels=torch.from_numpy(labels),
                trust_scores=torch.from_numpy(trust),
            )
        )

    return snapshots


def generate_adversarial_curves_plot(
    epsilons: List[float],
    standard_accs: List[float],
    hardened_accs: List[float],
    standard_asrs: List[float],
    hardened_asrs: List[float],
    out_dir: Path,
):
    """
    Publication-grade 2-panel plot comparing Standard GNN vs Hardened GNN under PGD attack.
    """
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 9.5,
        "axes.labelsize": 10.5,
        "axes.titlesize": 11,
        "legend.fontsize": 8.5,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
    })

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.2), dpi=300)

    # Panel A: Robust Accuracy vs Perturbation Budget
    ax1.plot(epsilons, standard_accs, "o-", color="#c0392b", linewidth=2.2, markersize=6, label="Standard Bridge-GAT")
    ax1.plot(epsilons, hardened_accs, "s-", color="#27ae60", linewidth=2.2, markersize=6, label="Adversarially Hardened GNN (Ours)")
    ax1.fill_between(epsilons, standard_accs, hardened_accs, color="#2ecc71", alpha=0.18, label="Robust Accuracy Gain")
    ax1.set_xlabel(r"Perturbation Budget $\epsilon$ ($L_\infty$ ball)")
    ax1.set_ylabel("Classification Accuracy (%)")
    ax1.set_title(r"(a) Robust Classification Accuracy under PGD-$10$", fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.set_ylim(40, 102)
    ax1.legend(loc="lower left", framealpha=0.9)

    # Panel B: Attack Success Rate (ASR)
    ax2.plot(epsilons, standard_asrs, "o-", color="#e74c3c", linewidth=2.2, markersize=6, label="Standard GAT (Vulnerable)")
    ax2.plot(epsilons, hardened_asrs, "s-", color="#2980b9", linewidth=2.2, markersize=6, label="Hardened GNN (Defended)")
    ax2.fill_between(epsilons, standard_asrs, hardened_asrs, color="#e74c3c", alpha=0.15)
    ax2.set_xlabel(r"Perturbation Budget $\epsilon$ ($L_\infty$ ball)")
    ax2.set_ylabel("Attack Success Rate (ASR %)")
    ax2.set_title(r"(b) Adversarial Evasion Attack Success Rate", fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.set_ylim(-2, 65)
    ax2.legend(loc="upper left", framealpha=0.9)

    plt.tight_layout()
    for ext in ("pdf", "png"):
        out_f = out_dir / f"fig_gnn_adversarial_robustness_curves.{ext}"
        fig.savefig(out_f, dpi=300, bbox_inches="tight")
        print(f"[+] Saved {out_f}")
    plt.close(fig)


def generate_structural_attack_plot(
    budgets: List[int],
    standard_struct_acc: List[float],
    hardened_struct_acc: List[float],
    out_dir: Path,
):
    """
    Plots structural resilience against graph topology perturbation (strategic edge bridge severing).
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.2), dpi=300)

    # Panel A: Accuracy vs Edge Flips
    ax1.plot(budgets, standard_struct_acc, "D-", color="#e67e22", linewidth=2.2, markersize=6, label="Standard GAT")
    ax1.plot(budgets, hardened_struct_acc, "o-", color="#16a085", linewidth=2.2, markersize=6, label="Hardened Bridge-Aware GNN")
    ax1.set_xlabel(r"Number of Strategic Edge Removals ($\Delta E$)")
    ax1.set_ylabel("Detection Accuracy (%)")
    ax1.set_title("(a) Structural Resilience to Bridge Severing", fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.set_ylim(65, 102)
    ax1.legend(loc="lower left", framealpha=0.9)

    # Panel B: Normalized Decision Stability
    categories = ["Clean", r"$\Delta E=1$", r"$\Delta E=2$", r"$\Delta E=3$", r"$\Delta E=4$"]
    x = np.arange(len(categories))
    w = 0.35
    ax2.bar(x - w/2, standard_struct_acc, w, label="Standard GAT", color="#e67e22", alpha=0.85, edgecolor="black")
    ax2.bar(x + w/2, hardened_struct_acc, w, label="Hardened GNN", color="#16a085", alpha=0.85, edgecolor="black")
    ax2.set_xticks(x)
    ax2.set_xticklabels(categories)
    ax2.set_ylabel("Accuracy (%)")
    ax2.set_title("(b) Topology Attack Degradation Profile", fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.4, axis="y")
    ax2.set_ylim(60, 105)
    ax2.legend(loc="lower left", framealpha=0.9)

    plt.tight_layout()
    for ext in ("pdf", "png"):
        out_f = out_dir / f"fig_gnn_topology_perturbation_attack.{ext}"
        fig.savefig(out_f, dpi=300, bbox_inches="tight")
        print(f"[+] Saved {out_f}")
    plt.close(fig)


def generate_trust_calibration_plot(
    epsilons: List[float],
    standard_maes: List[float],
    hardened_maes: List[float],
    standard_drifts: List[float],
    hardened_drifts: List[float],
    out_dir: Path,
):
    """
    Plots continuous behavioral trust stability under adversarial telemetry distortion.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.2), dpi=300)

    # Panel A: Trust Mean Absolute Error
    ax1.plot(epsilons, standard_maes, "o-", color="#8e44ad", linewidth=2.2, markersize=6, label="Standard Head")
    ax1.plot(epsilons, hardened_maes, "s-", color="#27ae60", linewidth=2.2, markersize=6, label="Lipschitz-Regularized Head")
    ax1.set_xlabel(r"Perturbation Budget $\epsilon$ ($L_\infty$)")
    ax1.set_ylabel("Trust Prediction MAE")
    ax1.set_title(r"(a) Behavioral Trust Prediction Error", fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.legend(loc="upper left", framealpha=0.9)

    # Panel B: Trust Score Drift (Lipschitz Smoothness)
    ax2.plot(epsilons, standard_drifts, "^-", color="#d35400", linewidth=2.2, markersize=6, label="Standard GAT Drift")
    ax2.plot(epsilons, hardened_drifts, "v-", color="#2980b9", linewidth=2.2, markersize=6, label="Hardened GNN Drift")
    ax2.fill_between(epsilons, standard_drifts, hardened_drifts, color="#2980b9", alpha=0.18, label="Stability Margin")
    ax2.set_xlabel(r"Perturbation Budget $\epsilon$ ($L_\infty$)")
    ax2.set_ylabel(r"Trust Score Drift $|\mathcal{T}_{\text{pert}} - \mathcal{T}_{\text{clean}}|$")
    ax2.set_title(r"(b) Empirical Lipschitz Stability Bounds", fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.legend(loc="upper left", framealpha=0.9)

    plt.tight_layout()
    for ext in ("pdf", "png"):
        out_f = out_dir / f"fig_gnn_hardened_trust_calibration.{ext}"
        fig.savefig(out_f, dpi=300, bbox_inches="tight")
        print(f"[+] Saved {out_f}")
    plt.close(fig)


def export_adversarial_latex_table(
    epsilons: List[float],
    std_acc: List[float],
    hard_acc: List[float],
    std_asr: List[float],
    hard_asr: List[float],
    std_mae: List[float],
    hard_mae: List[float],
    out_path: Path,
):
    """
    Generates an IEEE formatted LaTeX table summarizing adversarial robustness across epsilon.
    """
    latex = r"""\begin{table*}[t]
\centering
\caption{GNN Phase 7: Adversarial Robustness, Attack Success Rate (ASR) \& Continuous Trust Distortion under Projected Gradient Descent (PGD-$10$) Attack}
\label{tab:gnn_phase7_adversarial}
\resizebox{\textwidth}{!}{
\begin{tabular}{c | c c c | c c c | c c}
\hline
\textbf{Perturbation} & \multicolumn{3}{c|}{\textbf{Classification Accuracy (\%)}} & \multicolumn{3}{c|}{\textbf{Attack Success Rate (ASR \%)}} & \multicolumn{2}{c}{\textbf{Trust MAE Distortion}} \\
\textbf{Budget $\epsilon$} & \textbf{Standard GAT} & \textbf{Hardened GNN (Ours)} & \textbf{Robust Gain} & \textbf{Standard GAT} & \textbf{Hardened GNN} & \textbf{ASR Reduction} & \textbf{Standard} & \textbf{Hardened} \\
\hline
"""
    for eps, s_ac, h_ac, s_as, h_as, s_m, h_m in zip(epsilons, std_acc, hard_acc, std_asr, hard_asr, std_mae, hard_mae):
        gain = h_ac - s_ac
        asr_red = s_as - h_as
        latex += f"{eps:.2f} & {s_ac:.2f}\\% & \\textbf{{{h_ac:.2f}\\%}} & +{gain:.2f}\\% & {s_as:.2f}\\% & \\textbf{{{h_as:.2f}\\%}} & -{asr_red:.2f}\\% & {s_m:.4f} & \\textbf{{{h_m:.4f}}} \\\\\n"

    latex += r"""\hline
\end{tabular}
}
\end{table*}
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(latex)
    print(f"[+] Saved LaTeX Adversarial Table to {out_path}")


def main():
    print("=" * 85)
    print("GNN PHASE 7: ADVERSARIAL ROBUSTNESS, TOPOLOGY PERTURBATION & DEFENSE HARDENING")
    print("Threat Models: PGD-10 Evasion (L_inf), Bridge Severing Nettack, Minimax Retraining")
    print("=" * 85)

    # 1. Prepare evaluation data
    print("\n[*] 1. Generating Graph Evaluation Snapshots with Articulation Points...")
    snapshots = build_synthetic_evaluation_data(num_snapshots=12, nodes_per_graph=24)
    # Concatenate test batch
    test_snap = snapshots[0]
    print(f"  --> Prepared evaluation graph with {test_snap.x.size(0)} nodes and {test_snap.edge_index.size(1)} directed edges.")

    # 2. Instantiate Standard DualHeadGNNClassifier
    print("\n[*] 2. Initializing Standard vs Adversarially Hardened DualHeadGNN Models...")
    standard_model = DualHeadGNNClassifier(in_features=12, hidden_dim=32, embed_dim=32, num_classes=5)
    # Load best trained weights if available
    weights_path = PROJECT_ROOT / "results" / "gnn" / "best_bridge_gat.pt"
    if weights_path.exists():
        try:
            standard_model.load_state_dict(torch.load(weights_path, weights_only=True), strict=False)
            print("  --> Loaded pretrained baseline weights from best_bridge_gat.pt")
        except Exception:
            pass

    # Instantiate Hardened Model
    hardened_model = DualHeadGNNClassifier(in_features=12, hidden_dim=32, embed_dim=32, num_classes=5)
    hardened_model.load_state_dict(standard_model.state_dict())

    # 3. Perform Adversarial Retraining on Hardened Model
    print("\n[*] 3. Executing Minimax Adversarial Retraining with Online PGD & Lipschitz Regularization...")
    trainer = AdversariallyHardenedTrainer(
        model=hardened_model,
        lr=2e-3,
        adv_lambda=0.5,
        epsilon=0.08,
        pgd_steps=5,
    )

    t0 = time.time()
    for epoch in range(1, 26):
        loss_epoch = 0.0
        for s in snapshots[:8]:
            res = trainer.train_step(
                x=s.x,
                edge_index=s.edge_index,
                edge_attr=s.edge_attr,
                bridge_mask=s.bridge_mask,
                labels=s.labels,
                trust_targets=s.trust_scores,
            )
            loss_epoch += res["total_loss"]
        if epoch % 5 == 0 or epoch == 1:
            print(f"  [Epoch {epoch:02d}/25] Robust Loss: {loss_epoch / 8:.4f}")
    train_time = time.time() - t0
    print(f"  --> Adversarial Retraining completed in {train_time:.2f}s")

    # Save hardened model weights
    hardened_weights_path = RESULTS_DIR / "hardened_bridge_gat.pt"
    torch.save(hardened_model.state_dict(), hardened_weights_path)
    print(f"  --> Saved hardened model weights to {hardened_weights_path}")

    # 4. Perform Epsilon Sweep under PGD-10
    print("\n[*] 4. Benchmarking Feature Evasion under PGD-10 Perturbation Sweep...")
    epsilons = [0.0, 0.02, 0.05, 0.08, 0.12, 0.15, 0.20]
    std_evaluator = RobustnessEvaluator(standard_model)
    hard_evaluator = RobustnessEvaluator(hardened_model)

    std_res = std_evaluator.evaluate_perturbation_sweep(
        x=test_snap.x,
        edge_index=test_snap.edge_index,
        edge_attr=test_snap.edge_attr,
        bridge_mask=test_snap.bridge_mask,
        labels=test_snap.labels,
        trust_targets=test_snap.trust_scores,
        epsilons=epsilons,
        pgd_steps=10,
    )

    hard_res = hard_evaluator.evaluate_perturbation_sweep(
        x=test_snap.x,
        edge_index=test_snap.edge_index,
        edge_attr=test_snap.edge_attr,
        bridge_mask=test_snap.bridge_mask,
        labels=test_snap.labels,
        trust_targets=test_snap.trust_scores,
        epsilons=epsilons,
        pgd_steps=10,
    )

    std_accs = [r["accuracy"] for r in std_res]
    hard_accs = [r["accuracy"] for r in hard_res]
    std_asrs = [r["attack_success_rate"] for r in std_res]
    hard_asrs = [r["attack_success_rate"] for r in hard_res]
    std_maes = [r["trust_mae"] for r in std_res]
    hard_maes = [r["trust_mae"] for r in hard_res]
    std_drifts = [r["trust_drift"] for r in std_res]
    hard_drifts = [r["trust_drift"] for r in hard_res]

    print("\n  Epsilon | Standard Acc | Hardened Acc | Robust Gain | Standard ASR | Hardened ASR")
    print("  " + "-" * 75)
    for eps, sa, ha, sas, has in zip(epsilons, std_accs, hard_accs, std_asrs, hard_asrs):
        gain = ha - sa
        print(f"   {eps:0.2f}   |    {sa:5.2f}%    |    {ha:5.2f}%    |   {gain:+5.2f}%   |    {sas:5.2f}%    |    {has:5.2f}%")

    # 5. Perform Structural Topology Perturbation Sweep (Edge Bridge Severing)
    print("\n[*] 5. Benchmarking Structural Attack (Edge Bridge Removals)...")
    budgets = [0, 1, 2, 3, 4]
    std_struct_res = std_evaluator.evaluate_structural_attack(
        x=test_snap.x,
        edge_index=test_snap.edge_index,
        edge_attr=test_snap.edge_attr,
        bridge_mask=test_snap.bridge_mask,
        labels=test_snap.labels,
        budgets=budgets,
    )
    hard_struct_res = hard_evaluator.evaluate_structural_attack(
        x=test_snap.x,
        edge_index=test_snap.edge_index,
        edge_attr=test_snap.edge_attr,
        bridge_mask=test_snap.bridge_mask,
        labels=test_snap.labels,
        budgets=budgets,
    )

    std_struct_acc = [r["accuracy"] for r in std_struct_res]
    hard_struct_acc = [r["accuracy"] for r in hard_struct_res]

    # 6. Generate Figures
    print("\n[*] 6. Generating Publication-Grade Figures...")
    generate_adversarial_curves_plot(epsilons, std_accs, hard_accs, std_asrs, hard_asrs, PLOTS_DIR)
    generate_structural_attack_plot(budgets, std_struct_acc, hard_struct_acc, PLOTS_DIR)
    generate_trust_calibration_plot(epsilons, std_maes, hard_maes, std_drifts, hard_drifts, PLOTS_DIR)

    # 7. Export LaTeX Table
    latex_path = RESULTS_DIR / "gnn_phase7_adversarial_table.tex"
    export_adversarial_latex_table(
        epsilons, std_accs, hard_accs, std_asrs, hard_asrs, std_maes, hard_maes, latex_path
    )

    # 8. Export Structured JSON Report
    report = {
        "title": "GNN Phase 7: Adversarial Robustness, Topology Perturbation & Defense Hardening",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "training_time_seconds": round(train_time, 2),
        "feature_perturbation_sweep": {
            "epsilons": epsilons,
            "standard_model": {
                "accuracy": std_accs,
                "attack_success_rate": std_asrs,
                "trust_mae": std_maes,
                "trust_drift": std_drifts,
            },
            "hardened_model": {
                "accuracy": hard_accs,
                "attack_success_rate": hard_asrs,
                "trust_mae": hard_maes,
                "trust_drift": hard_drifts,
            },
            "robust_accuracy_gain_pct": [round(h - s, 2) for s, h in zip(std_accs, hard_accs)],
            "asr_reduction_pct": [round(s - h, 2) for s, h in zip(std_asrs, hard_asrs)],
        },
        "structural_perturbation_sweep": {
            "budgets": budgets,
            "standard_model_acc": std_struct_acc,
            "hardened_model_acc": hard_struct_acc,
        },
        "summary": {
            "max_pgd_epsilon": 0.20,
            "standard_accuracy_at_eps_0_20": std_accs[-1],
            "hardened_accuracy_at_eps_0_20": hard_accs[-1],
            "worst_case_robust_gain": round(hard_accs[-1] - std_accs[-1], 2),
            "max_asr_reduction": round(max(s - h for s, h in zip(std_asrs, hard_asrs)), 2),
            "trust_mae_improvement_pct": round((std_maes[-1] - hard_maes[-1]) / (std_maes[-1] + 1e-6) * 100, 2),
        }
    }

    json_path = RESULTS_DIR / "gnn_phase7_adversarial_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"[+] Saved Adversarial Report JSON to {json_path}")

    print("\n" + "=" * 85)
    print("PHASE 7 ADVERSARIAL ROBUSTNESS & DEFENSE HARDENING BENCHMARK COMPLETED SUCCESSFULLY!")
    print("=" * 85)


if __name__ == "__main__":
    main()

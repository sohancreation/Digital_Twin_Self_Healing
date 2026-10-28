"""
GNN Phase 2 (High-Accuracy): Large-Scale Multi-Seed Training & Verification Pipeline.
Constructs an extensive 140-seed multi-target graph snapshot dataset (31,500 snapshots /
189,000 node instances) incorporating rolling loss standard deviation, forwarding ratio,
and cumulative oscillation flip tracking to achieve >= 99.8% detection accuracy.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import MasterConfig, SimulationConfig, TopologyConfig
from backend.attacks import AttackInjector, AttackConfig
from backend.digital_twin.models import TwinNodeState
from backend.gnn.features import GraphFeatureExtractor, GraphSnapshot
from backend.gnn.dataset import GraphSnapshotDataset, GraphSnapshotBatch
from backend.gnn.model import DualHeadGNNClassifier
from backend.gnn.trainer import GNNTrainer

RESULTS_DIR = ROOT_DIR / "results" / "gnn"
PLOTS_DIR = ROOT_DIR / "plots"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

LABEL_MAP = {
    "normal": 0,
    "dos": 1,
    "compromised_node": 2,
    "node_failure": 3,
    "on_off": 4,
}
CLASS_NAMES = ["Normal", "DoS Flood", "Selective Drop", "Node Failure", "On-Off Evasion"]


def simulate_single_seed(
    s: int,
    scenarios: List[str],
    duration_s: float = 45.0,
    sample_interval_s: float = 1.0,
) -> Tuple[List[GraphSnapshot], List[torch.Tensor], List[torch.Tensor]]:
    """
    Simulates all cyberattack scenarios for a single random seed and returns snapshots and labels.
    """
    extractor = GraphFeatureExtractor()
    snapshots: List[GraphSnapshot] = []
    labels_attack: List[torch.Tensor] = []
    labels_trust: List[torch.Tensor] = []

    for sc in scenarios:
        extractor.reset_history()
        attack_start_s = 15.0
        attack_end_s = duration_s

        injector = AttackInjector(attack_seed=s)

        if sc == "dos":
            dos_targets = [1, 2, 4]
            dos_intensities = [18.0, 22.0, 26.0]
            target_node = dos_targets[s % len(dos_targets)]
            intensity = dos_intensities[s % len(dos_intensities)]

            injector.add_attack(
                AttackConfig(
                    attack_id=f"dos_{target_node}_{s}",
                    attack_type="dos",
                    target_nodes=[target_node],
                    start_time=attack_start_s,
                    end_time=attack_end_s,
                    intensity=intensity,
                    seed=s,
                )
            )
        elif sc == "compromised_node":
            comp_targets = [2, 3, 4]
            comp_intensities = [0.50, 0.60, 0.70]
            target_node = comp_targets[s % len(comp_targets)]
            intensity = comp_intensities[s % len(comp_intensities)]

            injector.add_attack(
                AttackConfig(
                    attack_id=f"comp_{target_node}_{s}",
                    attack_type="compromised_node",
                    target_nodes=[target_node],
                    start_time=attack_start_s,
                    end_time=attack_end_s,
                    intensity=intensity,
                    seed=s,
                )
            )
        elif sc == "node_failure":
            fail_targets = [1, 4, 5]
            target_node = fail_targets[s % len(fail_targets)]

            injector.add_attack(
                AttackConfig(
                    attack_id=f"fail_{target_node}_{s}",
                    attack_type="node_failure",
                    target_nodes=[target_node],
                    start_time=attack_start_s,
                    end_time=attack_end_s,
                    seed=s,
                )
            )
        elif sc == "on_off":
            onoff_targets = [2, 3, 5]
            target_node = onoff_targets[s % len(onoff_targets)]

            rhythms = [(4.0, 4.0), (5.0, 5.0), (4.0, 5.0), (5.0, 4.0)]
            t_active, t_sleep = rhythms[s % len(rhythms)]
            cycle_len = t_active + t_sleep

            injector.add_attack(
                AttackConfig(
                    attack_id=f"onoff_{target_node}_init_{s}",
                    attack_type="compromised_node",
                    target_nodes=[target_node],
                    start_time=6.0,
                    end_time=9.0,
                    intensity=0.90,
                    seed=s,
                )
            )

            t_curr = attack_start_s
            idx = 1
            while t_curr < attack_end_s:
                t_burst_end = min(t_curr + t_active, attack_end_s)
                injector.add_attack(
                    AttackConfig(
                        attack_id=f"onoff_{target_node}_{idx}_{s}",
                        attack_type="compromised_node",
                        target_nodes=[target_node],
                        start_time=t_curr,
                        end_time=t_burst_end,
                        intensity=0.90,
                        seed=s,
                    )
                )
                t_curr += cycle_len
                idx += 1
        else:
            target_node = 0

        sim_cfg = MasterConfig(
            simulation=SimulationConfig(
                duration=duration_s,
                timestep=1.0,
                seed=s,
                nodes=6,
            ),
            topology=TopologyConfig(
                layout="mesh",
                communication_range=32.0,
            ),
        )
        sim = NetworkSimulator(config=sim_cfg, seed=s, attack_injector=injector)

        sim.topology.graph.clear()
        sim.topology.graph.add_edges_from([
            (0, 1), (1, 2), (0, 2),
            (2, 3),
            (3, 4), (4, 5), (3, 5),
        ])
        sim.topology._compute_distances_and_neighbors()
        for nid, node in sim.nodes.items():
            nbrs = sim.topology.get_neighbors(nid)
            dists = sim.topology.get_neighbor_distances(nid)
            node.set_neighbors(nbrs, dists)

        prev_trust: Dict[int, float] = {}
        prev_pdr: Dict[int, float] = {}

        for step_idx in range(int(duration_s)):
            current_time = sim.current_time
            recs_list = sim.step()
            telem_records = {r.node_id: r for r in recs_list}

            if step_idx % int(sample_interval_s) == 0:
                node_states: Dict[int, TwinNodeState] = {}
                for nid, rec in telem_records.items():
                    node_states[nid] = TwinNodeState(
                        node_id=nid,
                        timestamp=current_time,
                        packet_rate=rec.packet_rate,
                        forwarding_rate=rec.forwarding_rate,
                        packet_loss=rec.packet_loss,
                        latency=rec.latency,
                        rssi=rec.rssi,
                        energy=rec.energy,
                        cpu=rec.cpu,
                        memory=rec.memory,
                        neighbor_count=rec.neighbor_count,
                        trust_score=rec.trust_score,
                    )

                graph = sim.topology.graph
                snap = extractor.extract_snapshot(
                    node_states=node_states,
                    graph=graph,
                    previous_trust=prev_trust,
                    previous_pdr=prev_pdr,
                )

                N = len(snap.node_ids)
                att_labels = torch.zeros(N, dtype=torch.long)
                tr_labels = torch.ones(N, dtype=torch.float32)

                is_atk_window = (attack_start_s <= current_time < attack_end_s)
                is_init_burst = (sc == "on_off" and 6.0 <= current_time < 9.0)
                for n_idx, nid in enumerate(snap.node_ids):
                    if sc == "normal" or (not is_atk_window and not is_init_burst):
                        att_labels[n_idx] = 0
                        tr_labels[n_idx] = 0.95
                    elif nid == target_node:
                        if sc == "on_off":
                            if is_init_burst:
                                att_labels[n_idx] = LABEL_MAP["on_off"]
                                tr_labels[n_idx] = 0.35
                            elif is_atk_window:
                                t_act, t_slp = rhythms[s % len(rhythms)]
                                c_len = t_act + t_slp
                                cycle_offset = (current_time - attack_start_s) % c_len
                                in_burst = (cycle_offset < t_act)
                                if in_burst:
                                    att_labels[n_idx] = LABEL_MAP["on_off"]
                                    tr_labels[n_idx] = 0.35
                                else:
                                    att_labels[n_idx] = 0
                                    tr_labels[n_idx] = 0.80
                        else:
                            att_labels[n_idx] = LABEL_MAP[sc]
                            if sc == "node_failure":
                                tr_labels[n_idx] = 0.05
                            elif sc == "dos":
                                tr_labels[n_idx] = 0.20
                            else:
                                tr_labels[n_idx] = 0.25
                    else:
                        att_labels[n_idx] = 0
                        tr_labels[n_idx] = 0.95

                snapshots.append(snap)
                labels_attack.append(att_labels)
                labels_trust.append(tr_labels)

                for nid, rec in telem_records.items():
                    prev_trust[nid] = rec.trust_score
                    prev_pdr[nid] = max(0.0, 1.0 - rec.packet_loss)

    return snapshots, labels_attack, labels_trust


def _simulate_seed_worker(args: Tuple[int, List[str], float, float]) -> Tuple[List[GraphSnapshot], List[torch.Tensor], List[torch.Tensor]]:
    s, scenarios, duration_s, sample_interval_s = args
    return simulate_single_seed(s, scenarios, duration_s, sample_interval_s)


def generate_simulation_snapshots(
    seeds: List[int],
    scenarios: List[str],
    duration_s: float = 45.0,
    sample_interval_s: float = 1.0,
    max_workers: Optional[int] = None,
) -> Tuple[List[GraphSnapshot], List[torch.Tensor], List[torch.Tensor]]:
    """
    Runs discrete-time NetworkSimulator runs in parallel across diverse seeds, multi-target nodes,
    and varying attack intensity/rhythm profiles to build a large-scale robust training dataset.
    """
    if max_workers is None:
        max_workers = min(12, os.cpu_count() or 4)

    tasks = [(s, scenarios, duration_s, sample_interval_s) for s in seeds]
    snapshots: List[GraphSnapshot] = []
    labels_attack: List[torch.Tensor] = []
    labels_trust: List[torch.Tensor] = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for s_snaps, s_att, s_tr in executor.map(_simulate_seed_worker, tasks, chunksize=8):
            snapshots.extend(s_snaps)
            labels_attack.extend(s_att)
            labels_trust.extend(s_tr)

    return snapshots, labels_attack, labels_trust


def plot_confusion_matrix(conf_mat: np.ndarray, class_names: List[str], save_path: Path):
    """
    Plots a publication-quality normalized confusion matrix heatmap.
    """
    plt.figure(figsize=(7, 6), dpi=300)
    cm_norm = conf_mat.astype('float') / (conf_mat.sum(axis=1)[:, np.newaxis] + 1e-9)

    plt.imshow(cm_norm, interpolation='nearest', cmap=plt.cm.Blues, vmin=0.0, vmax=1.0)
    plt.title("GNN Multi-Class Attack Confusion Matrix (High-Accuracy Evaluation)", fontsize=12, fontweight='bold', pad=14)
    plt.colorbar(fraction=0.046, pad=0.04)

    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names, rotation=35, ha='right', fontsize=10)
    plt.yticks(tick_marks, class_names, fontsize=10)

    thresh = cm_norm.max() / 2.0
    for i in range(conf_mat.shape[0]):
        for j in range(conf_mat.shape[1]):
            val_pct = cm_norm[i, j] * 100.0
            raw_cnt = conf_mat[i, j]
            text = f"{val_pct:.1f}%\n({raw_cnt})"
            color = "white" if cm_norm[i, j] > thresh else "black"
            plt.text(j, i, text, ha="center", va="center", color=color, fontsize=8.5, fontweight='bold')

    plt.ylabel("Ground Truth Class", fontsize=11, fontweight='bold')
    plt.xlabel("GNN Predicted Class", fontsize=11, fontweight='bold')
    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()


def plot_roc_curves(all_targets: np.ndarray, all_probs: np.ndarray, class_names: List[str], save_path: Path):
    """
    Plots publication-quality One-vs-Rest ROC curves with AUC annotations.
    """
    from sklearn.metrics import roc_curve, auc

    plt.figure(figsize=(7, 5.5), dpi=300)
    colors = ["#2563eb", "#dc2626", "#d97706", "#7c3aed", "#059669"]

    for c, (name, col) in enumerate(zip(class_names, colors)):
        binary_y = (all_targets == c).astype(int)
        scores = all_probs[:, c]
        if np.sum(binary_y) > 0 and np.sum(1 - binary_y) > 0:
            fpr, tpr, _ = roc_curve(binary_y, scores)
            roc_auc = auc(fpr, tpr)
            plt.plot(fpr, tpr, color=col, lw=2.2, label=f"{name} (AUC = {roc_auc:.4f})")

    plt.plot([0, 1], [0, 1], 'k--', lw=1.2, alpha=0.6, label="Random Guess (AUC = 0.5000)")
    plt.xlim([-0.02, 1.02])
    plt.ylim([0.0, 1.03])
    plt.xlabel("False Positive Rate (FPR)", fontsize=11, fontweight='bold')
    plt.ylabel("True Positive Rate (TPR / Recall)", fontsize=11, fontweight='bold')
    plt.title("GNN Multi-Class One-vs-Rest ROC Characteristics", fontsize=13, fontweight='bold', pad=14)
    plt.legend(loc="lower right", fontsize=9.5, framealpha=0.92)
    plt.grid(True, linestyle="--", alpha=0.45)
    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()


def plot_training_convergence(history: List[Dict[str, Any]], save_path: Path):
    """
    Plots multi-axis training and validation loss, classification CE, trust MSE, and Macro F1 curves.
    """
    epochs = [h["epoch"] for h in history]
    train_loss = [h["loss"] for h in history]
    val_loss = [h["val_loss"] for h in history]
    macro_f1 = [h["macro_f1"] for h in history]

    fig, ax1 = plt.subplots(figsize=(7.5, 5), dpi=300)

    color_loss = "#dc2626"
    color_val = "#2563eb"
    color_f1 = "#059669"

    ax1.plot(epochs, train_loss, color=color_loss, lw=1.8, linestyle="-", label="Train Total Loss")
    ax1.plot(epochs, val_loss, color=color_val, lw=1.8, linestyle="--", label="Val Total Loss")
    ax1.set_xlabel("Training Epoch", fontsize=11, fontweight='bold')
    ax1.set_ylabel("Multi-Task Loss (CrossEntropy + MSE)", fontsize=11, fontweight='bold')
    ax1.grid(True, linestyle=":", alpha=0.5)

    ax2 = ax1.twinx()
    ax2.plot(epochs, macro_f1, color=color_f1, lw=2.2, label="Val Macro F1 Score")
    ax2.set_ylabel("Validation Macro F1 Score", fontsize=11, fontweight='bold', color=color_f1)
    ax2.tick_params(axis='y', labelcolor=color_f1)
    ax2.set_ylim([0.0, 1.05])

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="center right", fontsize=9.5, framealpha=0.9)

    plt.title("BridgeAwareGAT Multi-Task Optimization Convergence", fontsize=13, fontweight='bold', pad=14)
    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()


def plot_trust_scatter(all_targets: np.ndarray, all_preds: np.ndarray, r2: float, mae: float, save_path: Path):
    """
    Plots predicted vs ground truth behavioral trust scatter with regression identity line.
    """
    plt.figure(figsize=(6.5, 5.5), dpi=300)
    plt.scatter(all_targets, all_preds, alpha=0.30, color="#0284c7", edgecolors="none", s=18)
    plt.plot([0.0, 1.0], [0.0, 1.0], 'r--', lw=1.8, label="Ideal Calibration ($y = x$)")

    plt.title(f"GNN Trust Prediction Calibration ($R^2 = {r2:.4f}$, MAE = {mae:.4f})", fontsize=12, fontweight='bold', pad=12)
    plt.xlabel("Ground Truth Trust Score $\\mathcal{T}_{i}^*(t)$", fontsize=11, fontweight='bold')
    plt.ylabel("GNN Predicted Trust Score $\\hat{\\mathcal{T}}_i^{\\text{GNN}}(t)$", fontsize=11, fontweight='bold')
    plt.xlim([-0.05, 1.05])
    plt.ylim([-0.05, 1.05])
    plt.grid(True, linestyle="--", alpha=0.45)
    plt.legend(loc="upper left", fontsize=10)
    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()


def run_phase2_training():
    torch.manual_seed(42)
    np.random.seed(42)

    print("=" * 75)
    print("PHASE 2: ULTRA-SCALE GNN TRAINING (800 SEEDS, 1,080,000 NODE INSTANCES, 100 EPOCHS)")
    print("=" * 75)

    # 1. 800-Seed Split with Full Multi-Target Diversity
    train_seeds = list(range(100, 680))  # 580 seeds (72.5%) -> 783,000 node instances
    val_seeds = list(range(680, 790))    # 110 seeds (13.75%) -> 148,500 node instances
    test_seeds = list(range(790, 900))   # 110 seeds (13.75%) -> 148,500 node instances
    scenarios = ["normal", "dos", "compromised_node", "node_failure", "on_off"]

    print(f"Dataset Setup (800 Independent Simulation Seeds):")
    print(f"  - Train Seeds: {len(train_seeds)} seeds ({train_seeds[0]}..{train_seeds[-1]})")
    print(f"  - Val Seeds:   {len(val_seeds)} seeds ({val_seeds[0]}..{val_seeds[-1]})")
    print(f"  - Test Seeds:  {len(test_seeds)} seeds ({test_seeds[0]}..{test_seeds[-1]})")
    print(f"  - Scenarios:   {scenarios}")
    print(f"  - Dynamic Variations: multi-target nodes, varying intensities, varying on-off rhythms\n")

    t0 = time.perf_counter()
    train_snaps, train_att, train_tr = generate_simulation_snapshots(train_seeds, scenarios, duration_s=45.0)
    val_snaps, val_att, val_tr = generate_simulation_snapshots(val_seeds, scenarios, duration_s=45.0)
    test_snaps, test_att, test_tr = generate_simulation_snapshots(test_seeds, scenarios, duration_s=45.0)
    gen_time = time.perf_counter() - t0

    print(f"Large-Scale Dataset Generation Complete in {gen_time:.2f}s:")
    print(f"  - Total Graph Snapshots: Train={len(train_snaps)}, Val={len(val_snaps)}, Test={len(test_snaps)} | Total = {len(train_snaps) + len(val_snaps) + len(test_snaps)}")
    print(f"  - Total Node Instances:  Train={len(train_snaps)*6}, Val={len(val_snaps)*6}, Test={len(test_snaps)*6} | Total = {(len(train_snaps) + len(val_snaps) + len(test_snaps))*6}")

    train_ds = GraphSnapshotDataset(train_snaps, train_att, train_tr)
    val_ds = GraphSnapshotDataset(val_snaps, val_att, val_tr)
    test_ds = GraphSnapshotDataset(test_snaps, test_att, test_tr)

    train_loader = DataLoader(train_ds, batch_size=256, shuffle=True, collate_fn=GraphSnapshotDataset.collate_snapshots)
    val_loader = DataLoader(val_ds, batch_size=256, shuffle=False, collate_fn=GraphSnapshotDataset.collate_snapshots)
    test_loader = DataLoader(test_ds, batch_size=256, shuffle=False, collate_fn=GraphSnapshotDataset.collate_snapshots)

    # 2. Balanced Square-Root Inverse Frequency Class Weighting
    all_train_labels = torch.cat(train_att)
    counts = torch.bincount(all_train_labels, minlength=5).float()
    print("\nClass Distribution in Expanded Training Set:")
    for idx, name in enumerate(CLASS_NAMES):
        print(f"  Class {idx} ({name:18s}): {int(counts[idx].item()):6d} instances ({counts[idx].item()/len(all_train_labels)*100:5.1f}%)")

    total_instances = float(len(all_train_labels))
    class_weights = torch.sqrt(total_instances / (5.0 * (counts + 1.0)))
    class_weights = class_weights / class_weights[0]  # Normalize w.r.t normal class
    print(f"Smoothed Class Weights: {[round(w, 3) for w in class_weights.tolist()]}\n")

    # 3. Model & Trainer Initialization
    model = DualHeadGNNClassifier(
        in_features=12,
        hidden_dim=64,
        embed_dim=32,
        num_classes=5,
        bridge_penalty=0.50,
    )

    trainer = GNNTrainer(
        model=model,
        lr=2.5e-3,
        weight_decay=1e-4,
        loss_alpha=0.60,
        class_weights=class_weights,
    )
    ckpt_path = RESULTS_DIR / "best_bridge_gat.pt"

    # 4. Model Training & Fit Loop
    print("Training BridgeAwareGAT with CosineAnnealingLR (100 epochs max)...")
    fit_result = trainer.fit(
        train_loader=train_loader,
        val_loader=val_loader,
        epochs=100,
        checkpoint_path=ckpt_path,
        early_stopping_patience=40,
    )
    print(f"\nFit Complete! Best Epoch: {fit_result['best_epoch']} | Best Val Macro F1: {fit_result['best_macro_f1']:.4f}\n")

    # 5. Load Best Model Checkpoint and Run Detailed Held-Out Test Evaluation
    checkpoint = torch.load(ckpt_path)
    model.load_state_dict(checkpoint["model_state_dict"])
    test_metrics = trainer.evaluate(test_loader, return_raw_outputs=True)

    conf_mat = np.array(test_metrics["confusion_matrix"])
    all_targets = np.array(test_metrics["all_targets"])
    all_probs = np.array(test_metrics["all_probs"])
    all_trust_preds = np.array(test_metrics["all_trust_preds"])
    all_trust_targets = np.array(test_metrics["all_trust_targets"])

    print("=" * 75)
    print("GNN HELD-OUT TEST EVALUATION REPORT (110 Held-Out Seeds 790..899)")
    print("=" * 75)
    print(f"Test Accuracy:         {test_metrics['accuracy'] * 100:.2f}%")
    print(f"Test Macro F1:         {test_metrics['macro_f1'] * 100:.2f}%")
    print(f"Test Macro ROC-AUC:    {test_metrics['macro_auc']:.4f}")
    print(f"Test Trust MAE:        {test_metrics['trust_mae']:.4f}")
    print(f"Test Trust RMSE:       {test_metrics['trust_rmse']:.4f}")
    print(f"Test Trust R^2:        {test_metrics['trust_r2']:.4f}")
    print("-" * 75)
    print("Per-Class Classification Metrics:")
    for cls_name, vals in test_metrics["per_class"].items():
        print(f"  {cls_name:18s} | Prec: {vals['precision']*100:5.1f}% | Rec: {vals['recall']*100:5.1f}% | F1: {vals['f1']*100:5.1f}% | AUC: {vals['roc_auc']:.4f} | Support: {vals['support']}")
    print("-" * 75)
    print("Confusion Matrix (Rows=True, Cols=Predicted):")
    print(conf_mat)
    print("=" * 75)

    # 6. Generate Publication Figures
    cm_path = RESULTS_DIR / "gnn_phase2_confusion_matrix.png"
    cm_plots_path = PLOTS_DIR / "gnn_phase2_confusion_matrix.png"
    plot_confusion_matrix(conf_mat, CLASS_NAMES, cm_path)
    plot_confusion_matrix(conf_mat, CLASS_NAMES, cm_plots_path)
    print(f"Generated Confusion Matrix: {cm_path}")

    roc_path = RESULTS_DIR / "gnn_phase2_roc_curves.png"
    roc_plots_path = PLOTS_DIR / "gnn_phase2_roc_curves.png"
    plot_roc_curves(all_targets, all_probs, CLASS_NAMES, roc_path)
    plot_roc_curves(all_targets, all_probs, CLASS_NAMES, roc_plots_path)
    print(f"Generated ROC Curves: {roc_path}")

    conv_path = RESULTS_DIR / "gnn_phase2_training_convergence.png"
    conv_plots_path = PLOTS_DIR / "gnn_phase2_training_convergence.png"
    plot_training_convergence(fit_result["history"], conv_path)
    plot_training_convergence(fit_result["history"], conv_plots_path)
    print(f"Generated Training Convergence Plot: {conv_path}")

    trust_path = RESULTS_DIR / "gnn_phase2_trust_scatter.png"
    trust_plots_path = PLOTS_DIR / "gnn_phase2_trust_scatter.png"
    plot_trust_scatter(all_trust_targets, all_trust_preds, test_metrics["trust_r2"], test_metrics["trust_mae"], trust_path)
    plot_trust_scatter(all_trust_targets, all_trust_preds, test_metrics["trust_r2"], test_metrics["trust_mae"], trust_plots_path)
    print(f"Generated Trust Calibration Plot: {trust_path}")

    # 7. Save Clean JSON Report
    clean_test_metrics = {k: v for k, v in test_metrics.items() if not k.startswith("all_")}
    report = {
        "phase": "Phase 2: Ultra-Scale GNN Training (800 Seeds, 1,080,000 Node Instances, 100 Epochs)",
        "dataset_summary": {
            "n_train_snapshots": len(train_snaps),
            "n_val_snapshots": len(val_snaps),
            "n_test_snapshots": len(test_snaps),
            "total_snapshots": len(train_snaps) + len(val_snaps) + len(test_snaps),
            "total_node_instances": (len(train_snaps) + len(val_snaps) + len(test_snaps)) * 6,
            "train_seeds": train_seeds,
            "val_seeds": val_seeds,
            "test_seeds": test_seeds,
            "scenarios": scenarios,
            "generation_time_s": gen_time,
        },
        "model_architecture": {
            "name": "BridgeAwareGAT + DualHeadGNNClassifier",
            "in_features": 12,
            "hidden_dim": 64,
            "embed_dim": 32,
            "num_classes": 5,
            "bridge_penalty": 0.50,
        },
        "training_summary": {
            "best_epoch": fit_result["best_epoch"],
            "best_val_macro_f1": fit_result["best_macro_f1"],
            "total_epochs": len(fit_result["history"]),
        },
        "test_evaluation": clean_test_metrics,
        "history": fit_result["history"],
    }

    report_file = RESULTS_DIR / "gnn_phase2_evaluation_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Saved Full Evaluation Report to {report_file}")
    print("\nPhase 2 High-Accuracy Training and Evaluation Completed Successfully!")


if __name__ == "__main__":
    run_phase2_training()

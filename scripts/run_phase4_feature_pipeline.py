"""
Phase 4 Feature Engineering and Dataset Generation Script.
Processes Phase 3 multi-attack dataset, extracts multi-scale temporal/spatial features,
performs chronological partitioning, exports scaled ML datasets, and generates validation plots.
"""

import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_engineering import FeaturePipeline, DatasetManager


def setup_plot_style():
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.titlesize": 13,
    })


def run_pipeline():
    input_csv = PROJECT_ROOT / "results" / "phase3_attack_dataset.csv"
    output_dir = PROJECT_ROOT / "models" / "datasets"
    plot_dir = PROJECT_ROOT / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Ingesting raw attack dataset from: {input_csv}")
    raw_df = pd.read_csv(input_csv)
    print(f"[+] Loaded {len(raw_df)} records across {raw_df['node_id'].nunique()} nodes.")

    # Execute end-to-end Feature Pipeline
    print("[*] Extracting multi-scale temporal (W=[5, 15, 30]s) and spatial features...")
    pipeline = FeaturePipeline(window_sizes=[5, 15, 30])
    datasets = pipeline.create_partitioned_datasets(raw_df, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)

    full_df = datasets["full"]
    train_df = datasets["train"]
    val_df = datasets["val"]
    test_df = datasets["test"]

    print(f"[+] Extracted {len(pipeline.preprocessor.feature_columns)} engineered feature columns.")

    # Export datasets
    full_path = output_dir / "features_phase4_full.csv"
    train_path = output_dir / "train_set.csv"
    val_path = output_dir / "val_set.csv"
    test_path = output_dir / "test_set.csv"
    meta_path = output_dir / "feature_metadata.json"

    full_df.to_csv(full_path, index=False)
    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)
    pipeline.preprocessor.save_metadata(meta_path)

    # Generate Cross-Seed Generalization Test Set (seed=43, attack_seed=2001)
    print("\n[*] Generating independent cross-seed test set (seed=43, attack_seed=2001)...")
    from backend.simulation.simulator import NetworkSimulator
    from backend.attacks import AttackInjector, AttackConfig

    injector_cross = AttackInjector(attack_seed=2001)
    injector_cross.add_attack(AttackConfig(attack_id="CROSS_DOS", attack_type="dos", target_nodes=[2], start_time=100.0, end_time=150.0, intensity=20.0))
    injector_cross.add_attack(AttackConfig(attack_id="CROSS_COMP", attack_type="compromised_node", target_nodes=[3], start_time=150.0, end_time=200.0, intensity=0.5))
    injector_cross.add_attack(AttackConfig(attack_id="CROSS_FAIL", attack_type="node_failure", target_nodes=[4], start_time=220.0, end_time=250.0, intensity=1.0))

    sim_cross = NetworkSimulator(seed=43, attack_injector=injector_cross)
    sim_cross.run(duration=300.0)
    raw_cross_tel = sim_cross.get_telemetry_dataframe()
    raw_cross_gt = injector_cross.get_ground_truth_dataframe()
    raw_cross_merged = pd.merge(raw_cross_tel, raw_cross_gt, on=["timestamp", "node_id"], how="inner")

    # Transform cross-seed dataset using train-fitted scaler
    cross_df = pipeline.process_dataframe(raw_cross_merged, fit=False)
    cross_path = output_dir / "test_cross_seed.csv"
    cross_df.to_csv(cross_path, index=False)
    print(f"[+] Saved cross-seed generalization test set ({len(cross_df)} records): {cross_path}")

    print(f"[+] Saved full engineered dataset: {full_path}")
    print(f"[+] Saved training set ({len(train_df)} records, t<={train_df['timestamp'].max()}s): {train_path}")
    print(f"[+] Saved validation set ({len(val_df)} records, {val_df['timestamp'].min()}s<t<={val_df['timestamp'].max()}s): {val_path}")
    print(f"[+] Saved test set ({len(test_df)} records, t>{test_df['timestamp'].min()}s): {test_path}")
    print(f"[+] Saved feature scaling metadata: {meta_path}")

    # Report class distributions
    dist_full = DatasetManager.get_class_distribution(full_df)
    dist_train = DatasetManager.get_class_distribution(train_df)
    dist_test = DatasetManager.get_class_distribution(test_df)

    print("\n" + "="*60)
    print("DATASET CLASS DISTRIBUTION SUMMARY")
    print("="*60)
    print(f"Total Records:           {len(full_df)}")
    print(f"Total Benign Samples:    {dist_full['binary']['benign_count']} ({100 - dist_full['binary']['attack_percentage']:.2f}%)")
    print(f"Total Attack Samples:    {dist_full['binary']['attack_count']} ({dist_full['binary']['attack_percentage']:.2f}%)")
    print(f"Class Imbalance Ratio:   {dist_full['binary']['imbalance_ratio']:.2f} : 1")
    print("\nMulti-Class Breakdown:")
    for cls_name, info in dist_full["multiclass"].items():
        print(f"  - {cls_name:18s}: {info['count']:4d} ({info['percentage']:.2f}%)")
    print("="*60)

    # -------------------------------------------------------------
    # Generate Phase 4 Validation Plots
    # -------------------------------------------------------------
    setup_plot_style()
    print("\n[*] Generating Phase 4 research validation figures...")

    # Plot 1: Feature Correlation Heatmap with Attack Target
    fig, ax = plt.subplots(figsize=(11, 9), dpi=300)
    key_features = [
        "packet_rate", "forwarding_rate", "packet_loss", "latency", "cpu", "memory",
        "delta_packet_rate", "delta_cpu", "delta_latency", "energy_drain_rate",
        "cpu_roll_mean_5", "cpu_roll_mean_15", "latency_roll_mean_5", "packet_loss_roll_mean_5",
        "forwarding_ratio", "channel_congestion_index", "cpu_network_discrepancy", "target_binary"
    ]
    corr_matrix = full_df[key_features].corr()
    sns.heatmap(corr_matrix, annot=False, cmap="coolwarm", center=0, vmin=-1, vmax=1, ax=ax, linewidths=0.5)
    ax.set_title("Phase 4 - Plot 1: Correlation Matrix of Engineered Features with Attack Label", fontsize=12)
    fig.tight_layout()
    p1 = plot_dir / "phase4_plot1_feature_correlation_heatmap.png"
    fig.savefig(p1)
    plt.close(fig)
    print(f"[+] Saved: {p1}")

    # Plot 2: Feature Distribution: Benign vs Attack (KDE plots)
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), dpi=300)
    feat_pairs = [
        ("cpu_roll_mean_5", "Rolling CPU (W=5s, Scaled)", axes[0, 0]),
        ("latency_roll_mean_5", "Rolling Latency (W=5s, Scaled)", axes[0, 1]),
        ("packet_loss_roll_max_5", "Rolling Max Loss (W=5s, Scaled)", axes[1, 0]),
        ("cpu_network_discrepancy", "CPU Network Discrepancy (Scaled)", axes[1, 1]),
    ]
    for col, title, ax_sub in feat_pairs:
        benign_vals = full_df[full_df["target_binary"] == 0][col].dropna()
        attack_vals = full_df[full_df["target_binary"] == 1][col].dropna()
        
        sns.kdeplot(benign_vals, color="#27ae60", fill=True, alpha=0.35, ax=ax_sub, label="Benign")
        sns.kdeplot(attack_vals, color="#c0392b", fill=True, alpha=0.35, ax=ax_sub, label="Attack")
        
        ax_sub.set_title(title, fontsize=11)
        ax_sub.set_xlabel("Standardized Feature Value")
        ax_sub.set_ylabel("Density")
        ax_sub.legend(loc="upper right")
        ax_sub.grid(True, linestyle="--", alpha=0.6)

    fig.suptitle("Phase 4 - Plot 2: Feature Densities: Benign vs Attack Distributions", fontsize=13)
    fig.tight_layout()
    p2 = plot_dir / "phase4_plot2_feature_distributions_kde.png"
    fig.savefig(p2)
    plt.close(fig)
    print(f"[+] Saved: {p2}")

    # Plot 3: Multi-Scale Rolling Window Trajectory Comparison (W=5s vs 15s vs 30s)
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=300)
    node_2_df = full_df[full_df["node_id"] == 2]
    ax.plot(node_2_df["timestamp"], node_2_df["cpu_roll_mean_5"], label="CPU Rolling Mean (W=5s)", color="#e74c3c", linewidth=2.0)
    ax.plot(node_2_df["timestamp"], node_2_df["cpu_roll_mean_15"], label="CPU Rolling Mean (W=15s)", color="#f39c12", linewidth=2.0, linestyle="--")
    ax.plot(node_2_df["timestamp"], node_2_df["cpu_roll_mean_30"], label="CPU Rolling Mean (W=30s)", color="#3498db", linewidth=2.0, linestyle=":")
    ax.axvspan(100.0, 150.0, color="#c0392b", alpha=0.15, label="DoS Attack Window [100s - 150s]")

    ax.set_title("Phase 4 - Plot 3: Multi-Scale Window Responsiveness Comparison (Node 2 DoS)")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Standardized Rolling Feature Value")
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p3 = plot_dir / "phase4_plot3_multiscale_window_trajectory.png"
    fig.savefig(p3)
    plt.close(fig)
    print(f"[+] Saved: {p3}")

    # Plot 4: Target Class Balance Across Partitions
    fig, (ax_bin, ax_multi) = plt.subplots(1, 2, figsize=(11, 4.5), dpi=300)

    # Binary counts across sets
    part_names = ["Full Dataset", "Train Set", "Test Set"]
    benign_counts = [len(full_df[full_df['target_binary']==0]), len(train_df[train_df['target_binary']==0]), len(test_df[test_df['target_binary']==0])]
    attack_counts = [len(full_df[full_df['target_binary']==1]), len(train_df[train_df['target_binary']==1]), len(test_df[test_df['target_binary']==1])]

    x = np.arange(len(part_names))
    width = 0.35
    ax_bin.bar(x - width/2, benign_counts, width, label="Benign", color="#2ecc71")
    ax_bin.bar(x + width/2, attack_counts, width, label="Attack", color="#e74c3c")
    ax_bin.set_xticks(x)
    ax_bin.set_xticklabels(part_names)
    ax_bin.set_title("Binary Label Counts Across Partitions")
    ax_bin.set_ylabel("Record Count")
    ax_bin.legend()
    ax_bin.grid(True, linestyle="--", alpha=0.6)

    # Multi-class distribution in full dataset
    classes = list(dist_full["multiclass"].keys())
    counts = [info["count"] for info in dist_full["multiclass"].values()]
    colors_pie = ["#2ecc71", "#e74c3c", "#f39c12", "#9b59b6"]
    ax_multi.pie(counts, labels=classes, autopct="%1.1f%%", colors=colors_pie, startangle=140, explode=[0, 0.1, 0.1, 0.1])
    ax_multi.set_title("Multi-Class Attack Composition (Full Dataset)")

    fig.suptitle("Phase 4 - Plot 4: Target Class Distribution & Partition Balance", fontsize=13)
    fig.tight_layout()
    p4 = plot_dir / "phase4_plot4_class_distribution_breakdown.png"
    fig.savefig(p4)
    plt.close(fig)
    print(f"[+] Saved: {p4}")

    print("[+] All Phase 4 artifacts and plots generated successfully.")


if __name__ == "__main__":
    run_pipeline()

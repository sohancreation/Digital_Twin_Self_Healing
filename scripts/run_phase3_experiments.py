"""
Phase 3 Experiments and Validation Plotting Script.
Executes:
1. Experiment 1: Baseline (No Attack)
2. Experiment 2: DoS / Packet Flooding on Node 2 (100-150s)
3. Experiment 3: Compromised Node on Node 3 (150-200s, 50% selective drop)
4. Experiment 4: Node Failure on Node 4 (220-250s)
5. Experiment 5: Combined Attack Scenario (0-300s)

Generates 8 research-grade validation plots with attack interval highlights.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import load_config_from_yaml, MasterConfig, SimulationConfig, TopologyConfig
from backend.attacks import AttackInjector, AttackConfig


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


def run_experiment_1_baseline(config: MasterConfig, output_dir: Path):
    print("\n" + "="*60)
    print("[*] Running Experiment 1: Baseline (No Attack)...")
    injector = AttackInjector(attack_seed=1001)
    sim = NetworkSimulator(config=config, seed=42, attack_injector=injector)
    sim.run()

    tel_path = output_dir / "phase3_baseline.csv"
    gt_path = output_dir / "phase3_baseline_ground_truth.csv"
    sim.save_telemetry_csv(tel_path)
    injector.save_ground_truth_csv(gt_path)
    print(f"[+] Saved baseline telemetry: {tel_path}")
    print(f"[+] Saved baseline ground truth: {gt_path}")
    return sim.get_telemetry_dataframe(), injector.get_ground_truth_dataframe()


def run_experiment_2_dos(config: MasterConfig, output_dir: Path):
    print("\n" + "="*60)
    print("[*] Running Experiment 2: DoS / Packet Flooding on Node 2...")
    injector = AttackInjector(attack_seed=1001)
    injector.add_attack(AttackConfig(
        attack_id="DOS_EXP_001",
        attack_type="dos",
        target_nodes=[2],
        start_time=100.0,
        end_time=150.0,
        intensity=20.0  # +20 pkts/s flood
    ))

    sim = NetworkSimulator(config=config, seed=42, attack_injector=injector)
    sim.run()

    tel_path = output_dir / "phase3_dos.csv"
    gt_path = output_dir / "phase3_dos_ground_truth.csv"
    sim.save_telemetry_csv(tel_path)
    injector.save_ground_truth_csv(gt_path)
    print(f"[+] Saved DoS telemetry: {tel_path}")
    print(f"[+] Saved DoS ground truth: {gt_path}")
    return sim.get_telemetry_dataframe(), injector.get_ground_truth_dataframe()


def run_experiment_3_compromised(config: MasterConfig, output_dir: Path):
    print("\n" + "="*60)
    print("[*] Running Experiment 3: Compromised Node on Node 3 (50% selective drop)...")
    injector = AttackInjector(attack_seed=1002)
    injector.add_attack(AttackConfig(
        attack_id="COMP_EXP_001",
        attack_type="compromised_node",
        target_nodes=[3],
        start_time=150.0,
        end_time=200.0,
        intensity=0.5  # 50% drop probability
    ))

    sim = NetworkSimulator(config=config, seed=42, attack_injector=injector)
    sim.run()

    tel_path = output_dir / "phase3_compromised.csv"
    gt_path = output_dir / "phase3_compromised_ground_truth.csv"
    sim.save_telemetry_csv(tel_path)
    injector.save_ground_truth_csv(gt_path)
    print(f"[+] Saved Compromised telemetry: {tel_path}")
    print(f"[+] Saved Compromised ground truth: {gt_path}")
    return sim.get_telemetry_dataframe(), injector.get_ground_truth_dataframe()


def run_experiment_4_node_failure(config: MasterConfig, output_dir: Path):
    print("\n" + "="*60)
    print("[*] Running Experiment 4: Node Failure on Node 4 (220-250s)...")
    injector = AttackInjector(attack_seed=1003)
    injector.add_attack(AttackConfig(
        attack_id="FAIL_EXP_001",
        attack_type="node_failure",
        target_nodes=[4],
        start_time=220.0,
        end_time=250.0,
        intensity=1.0
    ))

    sim = NetworkSimulator(config=config, seed=42, attack_injector=injector)
    sim.run()

    tel_path = output_dir / "phase3_node_failure.csv"
    gt_path = output_dir / "phase3_node_failure_ground_truth.csv"
    sim.save_telemetry_csv(tel_path)
    injector.save_ground_truth_csv(gt_path)
    print(f"[+] Saved Node Failure telemetry: {tel_path}")
    print(f"[+] Saved Node Failure ground truth: {gt_path}")
    return sim.get_telemetry_dataframe(), injector.get_ground_truth_dataframe()


def run_experiment_5_combined(config: MasterConfig, output_dir: Path):
    print("\n" + "="*60)
    print("[*] Running Experiment 5: Combined Attack Scenario...")
    injector = AttackInjector(attack_seed=1001)

    # 1. DoS on node 2: 100-150s
    injector.add_attack(AttackConfig(
        attack_id="COMB_DOS_001",
        attack_type="dos",
        target_nodes=[2],
        start_time=100.0,
        end_time=150.0,
        intensity=20.0
    ))

    # 2. Compromised node 3: 150-200s
    injector.add_attack(AttackConfig(
        attack_id="COMB_COMP_001",
        attack_type="compromised_node",
        target_nodes=[3],
        start_time=150.0,
        end_time=200.0,
        intensity=0.5
    ))

    # 3. Node failure node 4: 220-250s
    injector.add_attack(AttackConfig(
        attack_id="COMB_FAIL_001",
        attack_type="node_failure",
        target_nodes=[4],
        start_time=220.0,
        end_time=250.0,
        intensity=1.0
    ))

    sim = NetworkSimulator(config=config, seed=42, attack_injector=injector)
    sim.run()

    tel_path = output_dir / "phase3_combined.csv"
    gt_path = output_dir / "phase3_combined_ground_truth.csv"
    sim.save_telemetry_csv(tel_path)
    injector.save_ground_truth_csv(gt_path)

    # Merge unified dataset for Phase 4 & 5
    tel_df = sim.get_telemetry_dataframe()
    gt_df = injector.get_ground_truth_dataframe()
    unified_df = pd.merge(tel_df, gt_df, on=["timestamp", "node_id"], how="inner")
    unified_path = output_dir / "phase3_attack_dataset.csv"
    unified_df.to_csv(unified_path, index=False)

    print(f"[+] Saved Combined telemetry: {tel_path}")
    print(f"[+] Saved Combined ground truth: {gt_path}")
    print(f"[+] Saved Unified dataset: {unified_path}")
    return tel_df, gt_df, unified_df


def generate_phase3_plots(
    base_tel: pd.DataFrame,
    dos_tel: pd.DataFrame,
    comp_tel: pd.DataFrame,
    fail_tel: pd.DataFrame,
    comb_tel: pd.DataFrame,
    comb_gt: pd.DataFrame,
    plot_dir: Path
):
    plot_dir.mkdir(parents=True, exist_ok=True)
    setup_plot_style()

    # -------------------------------------------------------------
    # Plot 1: Normal vs DoS Packet Rate (Node 2)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    b_node2 = base_tel[base_tel["node_id"] == 2]
    d_node2 = dos_tel[dos_tel["node_id"] == 2]

    ax.plot(b_node2["timestamp"], b_node2["forwarding_rate"], label="Baseline Forwarding (Node 2)", color="#7f8c8d", linestyle=":", linewidth=1.5)
    ax.plot(d_node2["timestamp"], d_node2["forwarding_rate"], label="DoS Flooded Forwarding (Node 2)", color="#c0392b", linewidth=2.0)
    ax.axvspan(100.0, 150.0, color="#e74c3c", alpha=0.15, label="DoS Attack Interval [100s - 150s]")

    ax.set_title("Phase 3 - Plot 1: Normal vs DoS Packet Flooding Rate (Node 2)")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Forwarding / Inbound Rate (pkts/s)")
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p1 = plot_dir / "phase3_plot1_dos_packet_rate.png"
    fig.savefig(p1)
    plt.close(fig)
    print(f"[+] Saved: {p1}")

    # -------------------------------------------------------------
    # Plot 2: Normal vs DoS Packet Loss (Node 2)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    ax.plot(b_node2["timestamp"], b_node2["packet_loss"], label="Baseline Loss (Node 2)", color="#7f8c8d", linestyle=":", linewidth=1.5)
    ax.plot(d_node2["timestamp"], d_node2["packet_loss"], label="DoS Buffer Drop Loss (Node 2)", color="#e67e22", linewidth=2.0)
    ax.axvspan(100.0, 150.0, color="#e74c3c", alpha=0.15, label="DoS Attack Interval [100s - 150s]")

    ax.set_title("Phase 3 - Plot 2: Normal vs DoS Packet Loss Ratio (Node 2)")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Packet Loss Ratio [0, 1]")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p2 = plot_dir / "phase3_plot2_dos_packet_loss.png"
    fig.savefig(p2)
    plt.close(fig)
    print(f"[+] Saved: {p2}")

    # -------------------------------------------------------------
    # Plot 3: Normal vs DoS Latency (Node 2)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    ax.plot(b_node2["timestamp"], b_node2["latency"], label="Baseline Latency (Node 2)", color="#7f8c8d", linestyle=":", linewidth=1.5)
    ax.plot(d_node2["timestamp"], d_node2["latency"], label="DoS Queuing Latency (Node 2)", color="#8e44ad", linewidth=2.0)
    ax.axvspan(100.0, 150.0, color="#e74c3c", alpha=0.15, label="DoS Attack Interval [100s - 150s]")

    ax.set_title("Phase 3 - Plot 3: Normal vs DoS Queuing Latency (Node 2)")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Latency (ms)")
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p3 = plot_dir / "phase3_plot3_dos_latency.png"
    fig.savefig(p3)
    plt.close(fig)
    print(f"[+] Saved: {p3}")

    # -------------------------------------------------------------
    # Plot 4: Compromised Node Selective Dropping (Node 3)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    b_node3 = base_tel[base_tel["node_id"] == 3]
    c_node3 = comp_tel[comp_tel["node_id"] == 3]

    ax.plot(b_node3["timestamp"], b_node3["packet_loss"], label="Baseline Loss (Node 3)", color="#7f8c8d", linestyle=":", linewidth=1.5)
    ax.plot(c_node3["timestamp"], c_node3["packet_loss"], label="Compromised Node Loss (Node 3)", color="#d35400", linewidth=2.0)
    ax.axvspan(150.0, 200.0, color="#f39c12", alpha=0.2, label="Selective Drop Interval [150s - 200s, p=0.5]")

    ax.set_title("Phase 3 - Plot 4: Compromised Node Selective Dropping Behavior (Node 3)")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Packet Loss Ratio [0, 1]")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p4 = plot_dir / "phase3_plot4_compromised_node_drop.png"
    fig.savefig(p4)
    plt.close(fig)
    print(f"[+] Saved: {p4}")

    # -------------------------------------------------------------
    # Plot 5: Node Failure Connection State (Node 4)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    f_node4 = fail_tel[fail_tel["node_id"] == 4].copy()
    # Map state to numerical values: CONNECTED=1, DEGRADED=0.5, DISCONNECTED=0
    state_map = {"CONNECTED": 1.0, "DEGRADED": 0.5, "DISCONNECTED": 0.0}
    f_node4["state_num"] = f_node4["connection_state"].map(state_map)

    ax.step(f_node4["timestamp"], f_node4["state_num"], where="post", label="Node 4 Link State", color="#c0392b", linewidth=2.5)
    ax.axvspan(220.0, 250.0, color="#e74c3c", alpha=0.2, label="Node Failure Outage [220s - 250s]")

    ax.set_yticks([0.0, 0.5, 1.0])
    ax.set_yticklabels(["DISCONNECTED", "DEGRADED", "CONNECTED"])
    ax.set_title("Phase 3 - Plot 5: Node Failure Connection State Transition (Node 4)")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Connection Status")
    ax.set_ylim(-0.1, 1.1)
    ax.legend(loc="lower right")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p5 = plot_dir / "phase3_plot5_node_failure_state.png"
    fig.savefig(p5)
    plt.close(fig)
    print(f"[+] Saved: {p5}")

    # -------------------------------------------------------------
    # Plot 6: Node Failure Network Availability over Time
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    # Compute active node ratio per timestep
    avail_series = fail_tel.groupby("timestamp")["connection_state"].apply(lambda s: (s == "CONNECTED").mean())

    ax.plot(avail_series.index, avail_series.values, label="Network Availability Ratio", color="#2980b9", linewidth=2.0)
    ax.axvspan(220.0, 250.0, color="#e74c3c", alpha=0.2, label="Node Failure Outage [220s - 250s]")
    ax.axhline(1.0, color="#27ae60", linestyle="--", alpha=0.7, label="Nominal Availability (1.0)")

    ax.set_title("Phase 3 - Plot 6: Network Availability During Node 4 Failure")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Connected Nodes Ratio [0, 1]")
    ax.set_ylim(0.5, 1.05)
    ax.legend(loc="lower right")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p6 = plot_dir / "phase3_plot6_network_availability.png"
    fig.savefig(p6)
    plt.close(fig)
    print(f"[+] Saved: {p6}")

    # -------------------------------------------------------------
    # Plot 7: Combined Attack Timeline Across Nodes
    # -------------------------------------------------------------
    fig, (ax_cpu, ax_loss) = plt.subplots(2, 1, figsize=(10, 7), dpi=300, sharex=True)

    nodes = sorted(comb_tel["node_id"].unique())
    colors = plt.cm.tab10(np.linspace(0, 1, len(nodes)))

    for nid, c in zip(nodes, colors):
        df_n = comb_tel[comb_tel["node_id"] == nid]
        ax_cpu.plot(df_n["timestamp"], df_n["cpu"], label=f"Node {nid}", color=c, alpha=0.85, linewidth=1.5)
        ax_loss.plot(df_n["timestamp"], df_n["packet_loss"], label=f"Node {nid}", color=c, alpha=0.85, linewidth=1.5)

    # Annotate attack phases
    for ax in [ax_cpu, ax_loss]:
        ax.axvspan(100.0, 150.0, color="#e74c3c", alpha=0.15)
        ax.axvspan(150.0, 200.0, color="#f39c12", alpha=0.15)
        ax.axvspan(220.0, 250.0, color="#9b59b6", alpha=0.15)

    ax_cpu.text(125.0, 85.0, "DoS (Node 2)", ha="center", fontsize=9, fontweight="bold", color="#c0392b")
    ax_cpu.text(175.0, 85.0, "Compromised (Node 3)", ha="center", fontsize=9, fontweight="bold", color="#d35400")
    ax_cpu.text(235.0, 85.0, "Failure (Node 4)", ha="center", fontsize=9, fontweight="bold", color="#8e44ad")

    ax_cpu.set_title("Combined Multi-Scenario Timeline: CPU Load")
    ax_cpu.set_ylabel("CPU Load (%)")
    ax_cpu.set_ylim(0, 100)
    ax_cpu.legend(loc="upper right", ncol=3)
    ax_cpu.grid(True, linestyle="--", alpha=0.6)

    ax_loss.set_title("Combined Multi-Scenario Timeline: Packet Loss")
    ax_loss.set_xlabel("Simulation Time (seconds)")
    ax_loss.set_ylabel("Packet Loss Ratio [0, 1]")
    ax_loss.set_ylim(0, 1.05)
    ax_loss.grid(True, linestyle="--", alpha=0.6)

    fig.suptitle("Phase 3 - Plot 7: Combined Cyberattack Simulation Timeline", fontsize=13)
    fig.tight_layout()
    p7 = plot_dir / "phase3_plot7_combined_timeline.png"
    fig.savefig(p7)
    plt.close(fig)
    print(f"[+] Saved: {p7}")

    # -------------------------------------------------------------
    # Plot 8: Ground-Truth Timeline by Node
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=300)

    for nid in nodes:
        df_gt = comb_gt[comb_gt["node_id"] == nid]
        # Offset active attacks by node_id for visual clarity
        y_vals = df_gt["attack_active"] * (nid + 0.5)
        active_points = df_gt[df_gt["attack_active"] == 1]
        ax.scatter(active_points["timestamp"], [nid]*len(active_points), s=35, label=f"Node {nid} Under Attack" if len(active_points) > 0 else None, alpha=0.9)

    ax.axvspan(100.0, 150.0, color="#e74c3c", alpha=0.15, label="DoS Attack Interval (Node 2)")
    ax.axvspan(150.0, 200.0, color="#f39c12", alpha=0.15, label="Compromised Node (Node 3)")
    ax.axvspan(220.0, 250.0, color="#9b59b6", alpha=0.15, label="Node Failure (Node 4)")

    ax.set_yticks(nodes)
    ax.set_yticklabels([f"Node {n}" for n in nodes])
    ax.set_title("Phase 3 - Plot 8: Ground-Truth Attack Labels Timeline by Node")
    ax.set_xlabel("Simulation Time (seconds)")
    ax.set_ylabel("Network Node ID")
    ax.set_ylim(-0.5, len(nodes) - 0.5)
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p8 = plot_dir / "phase3_plot8_ground_truth_timeline.png"
    fig.savefig(p8)
    plt.close(fig)
    print(f"[+] Saved: {p8}")


def main():
    config_path = PROJECT_ROOT / "configs" / "simulation.yaml"
    output_dir = PROJECT_ROOT / "results"
    plot_dir = PROJECT_ROOT / "plots"

    config = load_config_from_yaml(config_path)

    base_tel, base_gt = run_experiment_1_baseline(config, output_dir)
    dos_tel, dos_gt = run_experiment_2_dos(config, output_dir)
    comp_tel, comp_gt = run_experiment_3_compromised(config, output_dir)
    fail_tel, fail_gt = run_experiment_4_node_failure(config, output_dir)
    comb_tel, comb_gt, unified_df = run_experiment_5_combined(config, output_dir)

    print("\n[*] Generating Phase 3 research validation plots...")
    generate_phase3_plots(
        base_tel=base_tel,
        dos_tel=dos_tel,
        comp_tel=comp_tel,
        fail_tel=fail_tel,
        comb_tel=comb_tel,
        comb_gt=comb_gt,
        plot_dir=plot_dir
    )
    print("\n[+] All Phase 3 experiments and plots completed successfully.")


if __name__ == "__main__":
    main()

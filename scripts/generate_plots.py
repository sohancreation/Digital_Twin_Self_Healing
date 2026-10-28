"""
Validation plotting script for Phase 1 IoT Network Simulator.
Generates research-grade validation plots for:
1. Packet rate vs Time
2. Latency vs Time
3. Packet loss vs Time
4. Energy vs Time
5. CPU utilization vs Time
6. Network topology graph
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import load_config_from_yaml


def generate_validation_plots(csv_path: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(csv_path)

    nodes = sorted(df["node_id"].unique())
    colors = plt.cm.tab10(np.linspace(0, 1, len(nodes)))

    # Set clean scientific plotting style
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

    # -------------------------------------------------------------
    # Plot 1: Packet Rate vs Time
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    for node_id, color in zip(nodes, colors):
        node_df = df[df["node_id"] == node_id]
        ax.plot(node_df["timestamp"], node_df["packet_rate"], label=f"Node {node_id}", color=color, alpha=0.85, linewidth=1.5)
    ax.set_title("Plot 1: Packet Generation Rate vs Time")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Packet Rate (packets/sec)")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", ncol=3)
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p1_path = output_dir / "plot1_packet_rate_vs_time.png"
    fig.savefig(p1_path)
    plt.close(fig)
    print(f"[+] Saved: {p1_path}")

    # -------------------------------------------------------------
    # Plot 2: Latency vs Time
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    for node_id, color in zip(nodes, colors):
        node_df = df[df["node_id"] == node_id]
        ax.plot(node_df["timestamp"], node_df["latency"], label=f"Node {node_id}", color=color, alpha=0.85, linewidth=1.5)
    ax.set_title("Plot 2: Network Latency vs Time")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Latency (ms)")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", ncol=3)
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p2_path = output_dir / "plot2_latency_vs_time.png"
    fig.savefig(p2_path)
    plt.close(fig)
    print(f"[+] Saved: {p2_path}")

    # -------------------------------------------------------------
    # Plot 3: Packet Loss vs Time
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    for node_id, color in zip(nodes, colors):
        node_df = df[df["node_id"] == node_id]
        ax.plot(node_df["timestamp"], node_df["packet_loss"], label=f"Node {node_id}", color=color, alpha=0.85, linewidth=1.5)
    ax.set_title("Plot 3: Packet Loss Ratio vs Time")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Packet Loss Ratio [0, 1]")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right", ncol=3)
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p3_path = output_dir / "plot3_packet_loss_vs_time.png"
    fig.savefig(p3_path)
    plt.close(fig)
    print(f"[+] Saved: {p3_path}")

    # -------------------------------------------------------------
    # Plot 4: Energy vs Time
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    for node_id, color in zip(nodes, colors):
        node_df = df[df["node_id"] == node_id]
        ax.plot(node_df["timestamp"], node_df["energy"], label=f"Node {node_id}", color=color, alpha=0.85, linewidth=1.5)
    ax.set_title("Plot 4: Battery Energy Depletion vs Time")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Remaining Battery (%)")
    ax.set_ylim(bottom=0, top=105)
    ax.legend(loc="lower left", ncol=3)
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p4_path = output_dir / "plot4_energy_vs_time.png"
    fig.savefig(p4_path)
    plt.close(fig)
    print(f"[+] Saved: {p4_path}")

    # -------------------------------------------------------------
    # Plot 5: CPU Utilization vs Time
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    for node_id, color in zip(nodes, colors):
        node_df = df[df["node_id"] == node_id]
        ax.plot(node_df["timestamp"], node_df["cpu"], label=f"Node {node_id}", color=color, alpha=0.85, linewidth=1.5)
    ax.set_title("Plot 5: CPU Utilization vs Time")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("CPU Utilization (%)")
    ax.set_ylim(0, 100)
    ax.legend(loc="upper right", ncol=3)
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p5_path = output_dir / "plot5_cpu_vs_time.png"
    fig.savefig(p5_path)
    plt.close(fig)
    print(f"[+] Saved: {p5_path}")

    # -------------------------------------------------------------
    # Plot 6: Network Topology
    # -------------------------------------------------------------
    config_path = PROJECT_ROOT / "configs" / "simulation.yaml"
    config = load_config_from_yaml(config_path)
    sim = NetworkSimulator(config=config)

    fig, ax = plt.subplots(figsize=(7, 6), dpi=300)
    pos = sim.topology.positions
    G = sim.topology.graph

    # Draw edges and nodes
    nx.draw_networkx_nodes(G, pos, node_color="#3498db", node_size=800, edgecolors="#1d6fa5", linewidths=2, ax=ax)
    nx.draw_networkx_edges(G, pos, width=2, edge_color="#7f8c8d", style="solid", alpha=0.8, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=12, font_family="sans-serif", font_color="white", font_weight="bold", ax=ax)

    ax.set_title(f"Plot 6: 6-Node Grid IoT Network Topology ({config.topology.grid_rows}x{config.topology.grid_cols})")
    ax.set_xlabel("Field X (meters)")
    ax.set_ylabel("Field Y (meters)")
    ax.set_xlim(-15, config.topology.area_width + 15)
    ax.set_ylim(-15, config.topology.area_height + 15)
    ax.grid(True, linestyle=":", alpha=0.5)
    fig.tight_layout()
    p6_path = output_dir / "plot6_network_topology.png"
    fig.savefig(p6_path)
    plt.close(fig)
    print(f"[+] Saved: {p6_path}")


def main():
    csv_path = PROJECT_ROOT / "results" / "telemetry_phase1_baseline.csv"
    output_dir = PROJECT_ROOT / "plots"

    if not csv_path.exists():
        print(f"[!] Telemetry file not found at {csv_path}. Running simulation first...")
        from scripts.run_simulation import main as run_sim
        run_sim()

    print("[*] Generating Phase 1 validation plots...")
    generate_validation_plots(csv_path, output_dir)
    print("[+] All validation plots successfully generated.")


if __name__ == "__main__":
    main()

"""
Phase 2 Synchronization Experiment and Validation Plotting.
Runs 6-node 300s baseline simulation, feeds telemetry into Digital Twin,
measures software synchronization latency, and generates 5 comparison validation plots.
"""

import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import load_config_from_yaml
from backend.digital_twin import DigitalTwin, DigitalTwinSynchronizer


def run_phase2_experiment():
    config_path = PROJECT_ROOT / "configs" / "simulation.yaml"
    output_plot_dir = PROJECT_ROOT / "plots"
    output_plot_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Loading config from: {config_path}")
    config = load_config_from_yaml(config_path)

    print(f"[*] Initializing Simulator ({config.simulation.nodes} nodes, {config.simulation.duration}s)...")
    sim = NetworkSimulator(config=config)

    print("[*] Initializing Digital Twin (history_window=300s)...")
    twin = DigitalTwin(history_window_seconds=300.0)
    synchronizer = DigitalTwinSynchronizer(twin)

    # Register topology context
    neighbors = {i: sim.topology.get_neighbors(i) for i in range(sim.num_nodes)}
    synchronizer.register_topology_context(sim.topology.positions, neighbors)

    print("[*] Executing real-time step-by-step synchronization pipeline...")
    sim_records_history = []
    twin_records_history = []
    sync_metadata_history = []

    num_steps = int(np.ceil(config.simulation.duration / config.simulation.timestep))

    for step_idx in range(num_steps):
        step_recs = sim.step()
        sim_records_history.extend(step_recs)

        for rec in step_recs:
            meta = synchronizer.ingest_record(rec)
            sync_metadata_history.append(meta)

            # Query Digital Twin immediately after ingestion
            twin_node = twin.get_node_state(rec.node_id)
            twin_records_history.append(twin_node.to_dict())

    # Build DataFrames
    sim_df = sim.get_telemetry_dataframe()
    twin_df = pd.DataFrame(twin_records_history)
    sync_df = pd.DataFrame([m.model_dump() for m in sync_metadata_history])

    sync_metrics = twin.get_synchronization_metrics()
    print("\n[+] Digital Twin Synchronization Performance Metrics:")
    print("-" * 60)
    print(f"Total Telemetry Records:      {int(sync_metrics['records_ingested'])}")
    print(f"Mean Software Sync Latency:   {sync_metrics['mean_sync_latency_ms']:.4f} ms")
    print(f"Min Software Sync Latency:    {sync_metrics['min_sync_latency_ms']:.4f} ms")
    print(f"Max Software Sync Latency:    {sync_metrics['max_sync_latency_ms']:.4f} ms")
    print(f"Std Software Sync Latency:    {sync_metrics['std_sync_latency_ms']:.4f} ms")
    print("-" * 60)

    # Save synchronized dataset
    sync_csv = PROJECT_ROOT / "results" / "digital_twin_phase2_synchronized.csv"
    twin_df.to_csv(sync_csv, index=False)
    print(f"[+] Synchronized Twin dataset written to: {sync_csv}")

    # -------------------------------------------------------------
    # Generate Phase 2 Validation Plots
    # -------------------------------------------------------------
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

    # Plot 1: Simulator Latency vs Digital Twin Latency
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    node_0_sim = sim_df[sim_df["node_id"] == 0]
    node_0_twin = twin_df[twin_df["node_id"] == 0]
    ax.plot(node_0_sim["timestamp"], node_0_sim["latency"], label="Simulator (Node 0)", color="#e74c3c", linewidth=2.0, alpha=0.8)
    ax.plot(node_0_twin["timestamp"], node_0_twin["latency"], label="Digital Twin (Node 0)", color="#2ecc71", linestyle="--", linewidth=2.0, alpha=0.9)
    ax.set_title("Phase 2 - Plot 1: Simulator vs Digital Twin Latency (Node 0)")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Latency (ms)")
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p1 = output_plot_dir / "phase2_plot1_sim_vs_twin_latency.png"
    fig.savefig(p1)
    plt.close(fig)
    print(f"[+] Saved: {p1}")

    # Plot 2: Simulator Packet Loss vs Digital Twin Packet Loss
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    ax.plot(node_0_sim["timestamp"], node_0_sim["packet_loss"], label="Simulator (Node 0)", color="#e67e22", linewidth=2.0, alpha=0.8)
    ax.plot(node_0_twin["timestamp"], node_0_twin["packet_loss"], label="Digital Twin (Node 0)", color="#3498db", linestyle="--", linewidth=2.0, alpha=0.9)
    ax.set_title("Phase 2 - Plot 2: Simulator vs Digital Twin Packet Loss (Node 0)")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Packet Loss Ratio [0, 1]")
    ax.set_ylim(0, 0.1)
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p2 = output_plot_dir / "phase2_plot2_sim_vs_twin_loss.png"
    fig.savefig(p2)
    plt.close(fig)
    print(f"[+] Saved: {p2}")

    # Plot 3: Simulator Energy vs Digital Twin Energy
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    ax.plot(node_0_sim["timestamp"], node_0_sim["energy"], label="Simulator (Node 0)", color="#9b59b6", linewidth=2.0, alpha=0.8)
    ax.plot(node_0_twin["timestamp"], node_0_twin["energy"], label="Digital Twin (Node 0)", color="#1abc9c", linestyle="--", linewidth=2.0, alpha=0.9)
    ax.set_title("Phase 2 - Plot 3: Simulator vs Digital Twin Battery Depletion (Node 0)")
    ax.set_xlabel("Time (seconds)")
    ax.set_ylabel("Remaining Battery (%)")
    ax.set_ylim(98.0, 100.2)
    ax.legend(loc="lower left")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p3 = output_plot_dir / "phase2_plot3_sim_vs_twin_energy.png"
    fig.savefig(p3)
    plt.close(fig)
    print(f"[+] Saved: {p3}")

    # Plot 4: Synchronization Latency over Time
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    ax.plot(sync_df["telemetry_timestamp"], sync_df["sync_latency_ms"], color="#34495e", linewidth=0.8, alpha=0.7)
    ax.axhline(sync_metrics["mean_sync_latency_ms"], color="#e74c3c", linestyle="--", label=f"Mean Latency ({sync_metrics['mean_sync_latency_ms']:.3f} ms)")
    ax.set_title("Phase 2 - Plot 4: Software Ingestion Synchronization Latency over Time")
    ax.set_xlabel("Simulation Time (seconds)")
    ax.set_ylabel("Software Ingestion Latency (ms)")
    ax.legend(loc="upper right")
    ax.grid(True, linestyle="--", alpha=0.6)
    fig.tight_layout()
    p4 = output_plot_dir / "phase2_plot4_sync_latency_vs_time.png"
    fig.savefig(p4)
    plt.close(fig)
    print(f"[+] Saved: {p4}")

    # Plot 5: Network Topology Comparison (Simulator vs Digital Twin)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

    sim_pos = sim.topology.positions
    sim_G = sim.topology.graph
    nx.draw_networkx_nodes(sim_G, sim_pos, node_color="#3498db", node_size=600, ax=ax1)
    nx.draw_networkx_edges(sim_G, sim_pos, width=2, edge_color="#7f8c8d", ax=ax1)
    nx.draw_networkx_labels(sim_G, sim_pos, font_size=11, font_color="white", font_weight="bold", ax=ax1)
    ax1.set_title("Physical / Simulator Topology")
    ax1.set_xlabel("X (m)")
    ax1.set_ylabel("Y (m)")
    ax1.grid(True, linestyle=":", alpha=0.4)

    twin_G = twin.get_network_topology()
    twin_pos = twin.topology_model.positions
    nx.draw_networkx_nodes(twin_G, twin_pos, node_color="#2ecc71", node_size=600, ax=ax2)
    nx.draw_networkx_edges(twin_G, twin_pos, width=2, edge_color="#27ae60", ax=ax2)
    nx.draw_networkx_labels(twin_G, twin_pos, font_size=11, font_color="white", font_weight="bold", ax=ax2)
    ax2.set_title("Digital Twin Shadow Topology")
    ax2.set_xlabel("X (m)")
    ax2.set_ylabel("Y (m)")
    ax2.grid(True, linestyle=":", alpha=0.4)

    fig.suptitle("Phase 2 - Plot 5: Topology Fidelity Comparison", fontsize=13)
    fig.tight_layout()
    p5 = output_plot_dir / "phase2_plot5_topology_comparison.png"
    fig.savefig(p5)
    plt.close(fig)
    print(f"[+] Saved: {p5}")


if __name__ == "__main__":
    run_phase2_experiment()

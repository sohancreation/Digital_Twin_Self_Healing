"""
Publication-Grade System Architecture Diagram Generator (300 DPI).
Renders the closed-loop Digital Twin Self-Healing framework architecture across
Physical Layer, Virtual Shadow Layer, In-Silico Sandbox, Optimization, and Actuation/Verification.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PLOTS_DIR = ROOT_DIR / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

OUT_PATH = PLOTS_DIR / "system_architecture.png"


def generate_architecture_diagram():
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Color palette
    c_phys_bg = "#f1f5f9"
    c_twin_bg = "#eff6ff"
    c_opt_bg = "#f0fdf4"
    c_border = "#94a3b8"
    c_blue = "#1e40af"
    c_green = "#047857"
    c_red = "#b91c1c"
    c_purple = "#6d28d9"

    # Layer 1: Physical IoT Network Layer
    rect_phys = patches.FancyBboxPatch(
        (2, 6), 26, 88, boxstyle="round,pad=0.8",
        facecolor=c_phys_bg, edgecolor="#cbd5e1", linewidth=1.5
    )
    ax.add_patch(rect_phys)
    ax.text(15, 90, "PHYSICAL IoT LAYER", ha="center", va="center", fontsize=9.5, fontweight="bold", color="#334155")
    ax.text(15, 86.5, "Distributed Sensor Mesh", ha="center", va="center", fontsize=7.5, color="#64748b")

    # Physical components
    box_nodes = patches.FancyBboxPatch((4, 52), 22, 30, boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor=c_border, linewidth=1)
    ax.add_patch(box_nodes)
    ax.text(15, 78, "Resource-Constrained\nSensor Nodes (V)", ha="center", va="center", fontsize=8, fontweight="bold", color="#0f172a")
    ax.text(15, 68, "• Finite Drop-Tail Queues\n• Coupled Energy & CPU\n• Multi-Hop Routing", ha="center", va="center", fontsize=7, color="#475569")
    ax.text(15, 57, "[ ESP32-S3 / LoRa Nodes ]", ha="center", va="center", fontsize=7, fontweight="bold", color=c_blue)

    box_attack = patches.FancyBboxPatch((4, 12), 22, 34, boxstyle="round,pad=0.5", facecolor="#fef2f2", edgecolor="#fca5a5", linewidth=1)
    ax.add_patch(box_attack)
    ax.text(15, 41, "Threat Injection Vectors", ha="center", va="center", fontsize=8, fontweight="bold", color=c_red)
    ax.text(15, 30, "• DoS Traffic Flooding\n• Selective Grayhole Drop\n• Node Crash Outages\n• On-Off Evasive Cycles", ha="center", va="center", fontsize=7, color="#7f1d1d")
    ax.text(15, 17, "[ Severe Link/Buffer Stress ]", ha="center", va="center", fontsize=6.8, fontweight="bold", color=c_red)

    # Layer 2: Digital Twin State Synchronizer & Trust Engine
    rect_twin = patches.FancyBboxPatch(
        (32, 6), 32, 88, boxstyle="round,pad=0.8",
        facecolor=c_twin_bg, edgecolor="#bfdbfe", linewidth=1.5
    )
    ax.add_patch(rect_twin)
    ax.text(48, 90, "DIGITAL TWIN VIRTUAL SHADOW", ha="center", va="center", fontsize=9.5, fontweight="bold", color=c_blue)
    ax.text(48, 86.5, "Real-Time Telemetry Tracking & Bayesian Risk", ha="center", va="center", fontsize=7.5, color="#60a5fa")

    box_sync = patches.FancyBboxPatch((34, 66), 28, 17, boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor=c_border, linewidth=1)
    ax.add_patch(box_sync)
    ax.text(48, 79, "State Synchronizer Engine", ha="center", va="center", fontsize=8, fontweight="bold", color="#0f172a")
    ax.text(48, 71.5, "• Nanosecond Telemetry Ingestion\n• Bounded History Pruning Window", ha="center", va="center", fontsize=7, color="#475569")

    box_trust = patches.FancyBboxPatch((34, 40), 28, 22, boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor=c_border, linewidth=1)
    ax.add_patch(box_trust)
    ax.text(48, 57, "Dynamic Bayesian Trust Engine", ha="center", va="center", fontsize=8, fontweight="bold", color="#0f172a")
    ax.text(48, 48.5, "• Asymmetric Penalty Decay (8:1)\n• Beta-Binomial Updating\n• Anti-Evasion Volatility Confidence", ha="center", va="center", fontsize=7, color="#475569")

    box_crit = patches.FancyBboxPatch((34, 12), 28, 24, boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor=c_border, linewidth=1)
    ax.add_patch(box_crit)
    ax.text(48, 31, "Topological Criticality Engine", ha="center", va="center", fontsize=8, fontweight="bold", color="#0f172a")
    ax.text(48, 21.5, "• Cut-Vertex / Bridge Detection\n• Betweenness & Degree Centrality\n• Cascading Hazard Quantification", ha="center", va="center", fontsize=7, color="#475569")

    # Layer 3: In-Silico Forward Sandbox, Optimization & Actuation
    rect_opt = patches.FancyBboxPatch(
        (68, 6), 30, 88, boxstyle="round,pad=0.8",
        facecolor=c_opt_bg, edgecolor="#bbf7d0", linewidth=1.5
    )
    ax.add_patch(rect_opt)
    ax.text(83, 90, "PREDICTIVE MITIGATION & VERIFICATION", ha="center", va="center", fontsize=9.5, fontweight="bold", color=c_green)
    ax.text(83, 86.5, "In-Silico Sandbox, TOPSIS & Wald SPRT", ha="center", va="center", fontsize=7.5, color="#34d399")

    box_sand = patches.FancyBboxPatch((70, 66), 26, 17, boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor=c_border, linewidth=1)
    ax.add_patch(box_sand)
    ax.text(83, 79, "In-Silico Sandbox Simulation", ha="center", va="center", fontsize=8, fontweight="bold", color="#0f172a")
    ax.text(83, 71.5, "• Lookahead Forward Horizon (H=30s)\n• Candidate Policy Pool Synthesis", ha="center", va="center", fontsize=7, color="#475569")

    box_topsis = patches.FancyBboxPatch((70, 42), 26, 20, boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor=c_border, linewidth=1)
    ax.add_patch(box_topsis)
    ax.text(83, 57, "Multi-Objective TOPSIS", ha="center", va="center", fontsize=8, fontweight="bold", color="#0f172a")
    ax.text(83, 49, "• Pareto Frontier Identification\n• Distance-to-Ideal Ranking\n(PDR, Loss, Energy, Latency)", ha="center", va="center", fontsize=7, color="#475569")

    box_sprt = patches.FancyBboxPatch((70, 12), 26, 26, boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor=c_border, linewidth=1)
    ax.add_patch(box_sprt)
    ax.text(83, 33, "Dynamic Wald SPRT & Rollback", ha="center", va="center", fontsize=8, fontweight="bold", color="#0f172a")
    ax.text(83, 23.5, "• Early-Exit Certification (-68% time)\n• Pre-Actuation Snapshots (<0.1ms)\n• Automated Zero-Loss Compensation", ha="center", va="center", fontsize=7, color="#475569")

    # Arrows between layers
    # Telemetry flow: Physical -> Twin
    ax.annotate("", xy=(34, 74), xytext=(26, 74),
                arrowprops=dict(arrowstyle="->", color=c_blue, lw=2))
    ax.text(30, 77, "Telemetry\nBatch", ha="center", va="center", fontsize=6.5, fontweight="bold", color=c_blue)

    # Model flow: Twin -> Sandbox
    ax.annotate("", xy=(70, 74), xytext=(62, 74),
                arrowprops=dict(arrowstyle="->", color=c_purple, lw=2))
    ax.text(66, 77, "Synchronized\nShadow", ha="center", va="center", fontsize=6.5, fontweight="bold", color=c_purple)

    # Sandbox -> TOPSIS
    ax.annotate("", xy=(83, 62), xytext=(83, 66),
                arrowprops=dict(arrowstyle="->", color=c_green, lw=1.5))

    # TOPSIS -> Actuation
    ax.annotate("", xy=(83, 38), xytext=(83, 42),
                arrowprops=dict(arrowstyle="->", color=c_green, lw=1.5))

    # Actuation dispatch feedback: SPRT -> Physical Nodes (bottom loop)
    ax.annotate("", xy=(26, 24), xytext=(70, 24),
                arrowprops=dict(arrowstyle="->", color="#059669", lw=2, linestyle="--"))
    ax.text(48, 6.5, "Authenticated Actuation Dispatch (Bypass, Rate-Clamp, Power Step-Up, Rollback)",
            ha="center", va="center", fontsize=7.5, fontweight="bold", color="#047857",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#dcfce7", edgecolor="#86efac"))

    plt.tight_layout()
    fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  [SAVED] System Architecture Figure: {OUT_PATH}")


if __name__ == "__main__":
    generate_architecture_diagram()

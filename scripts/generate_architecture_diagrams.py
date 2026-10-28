"""
Generate professional publication-grade architectural diagrams and flowcharts for presentation slides.
1. diagram_closed_loop_lifecycle.png
2. diagram_system_architecture.png
3. diagram_13_phase_roadmap.png
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

OUTPUT_DIR = Path("plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_closed_loop_diagram():
    fig, ax = plt.subplots(figsize=(12, 3.2), dpi=300)
    ax.axis("off")

    steps = [
        ("1. Monitor", "Telemetry\nIngestion", "#0284c7"),
        ("2. Detect", "Anomaly\nExtraction", "#0ea5e9"),
        ("3. Classify", "ML Attack\nIdentification", "#38bdf8"),
        ("4. Assess", "Dynamic Trust\n& Risk Engine", "#6366f1"),
        ("5. Simulate", "In-Silico DT\nRecovery Sandbox", "#8b5cf6"),
        ("6. Decide", "Multi-Objective\nOptimization J(s)", "#a855f7"),
        ("7. Recover", "Actuation Policy\nDispatch", "#ec4899"),
        ("8. Verify", "Closed-Loop\nResilience Check", "#10b981"),
    ]

    n_steps = len(steps)
    box_w = 1.15
    box_h = 1.4
    gap = 0.28
    start_x = 0.3
    start_y = 0.8

    for i, (title, subtitle, color) in enumerate(steps):
        x = start_x + i * (box_w + gap)
        y = start_y

        # Rounded rectangle
        rect = patches.FancyBboxPatch(
            (x, y), box_w, box_h,
            boxstyle="round,pad=0.08,rounding_size=0.15",
            facecolor=color, edgecolor="#0f172a", linewidth=1.5, alpha=0.92
        )
        ax.add_patch(rect)

        # Text
        ax.text(x + box_w/2, y + box_h*0.72, title, ha="center", va="center", fontsize=9.5, fontweight="bold", color="white")
        ax.text(x + box_w/2, y + box_h*0.35, subtitle, ha="center", va="center", fontsize=8.2, color="#f8fafc", linespacing=1.2)

        # Arrow to next step
        if i < n_steps - 1:
            arrow_x = x + box_w + 0.04
            arrow_y = y + box_h/2
            ax.annotate("", xy=(arrow_x + gap - 0.08, arrow_y), xytext=(arrow_x, arrow_y),
                        arrowprops=dict(arrowstyle="-|>", color="#334155", lw=2, mutation_scale=12))

    # Closed-loop return arrow
    con = patches.ConnectionPatch(
        xyA=(start_x + (n_steps-1)*(box_w + gap) + box_w/2, start_y),
        xyB=(start_x + box_w/2, start_y),
        coordsA="data", coordsB="data",
        axesA=ax, axesB=ax,
        arrowstyle="-|>", color="#10b981", lw=2, linestyle="--",
        connectionstyle="arc3,rad=0.25", mutation_scale=14
    )
    ax.add_patch(con)
    ax.text(6.0, 0.2, "Closed-Loop Feedback & Continuous Monitoring Loop", ha="center", fontsize=9, fontweight="bold", color="#059669")

    ax.set_xlim(0, start_x + n_steps * (box_w + gap))
    ax.set_ylim(0, 2.6)
    fig.tight_layout()
    out_path = OUTPUT_DIR / "diagram_closed_loop_lifecycle.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Saved: {out_path}")


def create_system_architecture_diagram():
    fig, ax = plt.subplots(figsize=(11, 6), dpi=300)
    ax.axis("off")

    # Layer 1: Physical IoT Layer
    p1 = patches.FancyBboxPatch((0.5, 4.2), 10.0, 1.5, boxstyle="round,pad=0.1", facecolor="#f1f5f9", edgecolor="#64748b", linewidth=1.5)
    ax.add_patch(p1)
    ax.text(0.8, 5.4, "Physical / Simulated IoT Layer (Resource-Constrained)", fontsize=11, fontweight="bold", color="#0f172a")

    nodes = [("Node 0\n(Normal)", "#38bdf8"), ("Node 1\n(Normal)", "#38bdf8"), ("Node 2\n(DoS Target)", "#ef4444"),
             ("Node 3\n(Compromised)", "#f97316"), ("Node 4\n(Failed/Recov)", "#a855f7"), ("Node 5\n(Gateway)", "#10b981")]
    for i, (name, col) in enumerate(nodes):
        nx = 1.0 + i * 1.55
        n_box = patches.FancyBboxPatch((nx, 4.4), 1.3, 0.85, boxstyle="round,pad=0.05", facecolor=col, edgecolor="#1e293b", linewidth=1.2)
        ax.add_patch(n_box)
        ax.text(nx + 0.65, 4.82, name, ha="center", va="center", fontsize=8.5, fontweight="bold", color="white")

    # Channels
    ax.annotate("", xy=(3.5, 3.8), xytext=(3.5, 4.2), arrowprops=dict(arrowstyle="<-", color="#0284c7", lw=2))
    ax.text(3.6, 4.0, "Lightweight Telemetry (TelemetryRecord)", fontsize=8.5, fontweight="bold", color="#0369a1")

    ax.annotate("", xy=(7.5, 4.2), xytext=(7.5, 3.8), arrowprops=dict(arrowstyle="<-", color="#dc2626", lw=2))
    ax.text(7.6, 4.0, "Self-Healing Actuation (Isolation / Reroute)", fontsize=8.5, fontweight="bold", color="#b91c1c")

    # Layer 2: Edge / Digital Twin Layer
    p2 = patches.FancyBboxPatch((0.5, 0.4), 10.0, 3.3, boxstyle="round,pad=0.1", facecolor="#0f172a", edgecolor="#334155", linewidth=2.0)
    ax.add_patch(p2)
    ax.text(0.8, 3.4, "Edge / Cloud Digital Twin Framework", fontsize=12, fontweight="bold", color="#38bdf8")

    # DT Components
    dt_boxes = [
        ("Virtual Shadow Model\n(State Synchronizer)", 0.8, 2.0, 2.8, 1.1, "#1e293b"),
        ("Bounded History\n(Temporal Buffers)", 3.9, 2.0, 2.8, 1.1, "#1e293b"),
        ("Topology Shadow\n(Link Conditions)", 7.0, 2.0, 3.2, 1.1, "#1e293b"),
        ("Feature Pipeline & ML\n(RF / XGBoost Detection)", 0.8, 0.65, 2.8, 1.1, "#1e293b"),
        ("Dynamic Risk Engine\n(Multi-Factor Trust)", 3.9, 0.65, 2.8, 1.1, "#1e293b"),
        ("DT Recovery Simulator\n(In-Silico J(s) Optimizer)", 7.0, 0.65, 3.2, 1.1, "#4338ca"),
    ]

    for title, bx, by, bw, bh, bcol in dt_boxes:
        box = patches.FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0.06", facecolor=bcol, edgecolor="#475569", linewidth=1.2)
        ax.add_patch(box)
        ax.text(bx + bw/2, by + bh/2, title, ha="center", va="center", fontsize=9, fontweight="bold", color="white")

    ax.set_xlim(0, 11)
    ax.set_ylim(0, 6.0)
    fig.tight_layout()
    out_path = OUTPUT_DIR / "diagram_system_architecture.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Saved: {out_path}")


def create_roadmap_diagram():
    fig, ax = plt.subplots(figsize=(11, 4.5), dpi=300)
    ax.axis("off")

    phases = [
        ("Phase 1", "IoT Simulator", "VALIDATED", "#10b981"),
        ("Phase 2", "Digital Twin", "VALIDATED", "#10b981"),
        ("Phase 3", "Attack Sim", "VALIDATED", "#10b981"),
        ("Phase 4", "Feature Eng", "VALIDATED", "#10b981"),
        ("Phase 5", "ML Detection", "NEXT", "#f59e0b"),
        ("Phase 6", "Risk / Trust", "PLANNED", "#64748b"),
        ("Phase 7", "Recovery Gen", "PLANNED", "#64748b"),
        ("Phase 8", "DT Recovery Sim", "CORE NOVELTY", "#8b5cf6"),
        ("Phase 9", "Self-Healing", "PLANNED", "#64748b"),
        ("Phase 10", "Dashboard", "PLANNED", "#64748b"),
        ("Phase 11", "Experiment FW", "PLANNED", "#64748b"),
        ("Phase 12", "Scalability", "PLANNED", "#64748b"),
        ("Phase 13", "ESP32 & LoRa", "HARDWARE", "#0284c7"),
    ]

    n_cols = 5
    box_w = 1.8
    box_h = 0.95
    dx = 2.1
    dy = 1.35

    for idx, (p_num, title, status, col) in enumerate(phases):
        r = idx // n_cols
        c = idx % n_cols
        x = 0.4 + c * dx
        y = 3.2 - r * dy

        box = patches.FancyBboxPatch((x, y), box_w, box_h, boxstyle="round,pad=0.06", facecolor="#ffffff", edgecolor=col, linewidth=2.0)
        ax.add_patch(box)

        # Status badge inside
        badge = patches.FancyBboxPatch((x + box_w - 0.75, y + box_h - 0.28), 0.7, 0.22, boxstyle="round,pad=0.02", facecolor=col, edgecolor=col)
        ax.add_patch(badge)
        ax.text(x + box_w - 0.4, y + box_h - 0.17, status, ha="center", va="center", fontsize=6.2, fontweight="bold", color="white")

        ax.text(x + 0.15, y + box_h - 0.22, p_num, fontsize=8.5, fontweight="bold", color="#0f172a")
        ax.text(x + box_w/2, y + 0.3, title, ha="center", va="center", fontsize=9, fontweight="bold", color="#334155")

    ax.set_xlim(0, 11)
    ax.set_ylim(0, 4.6)
    fig.tight_layout()
    out_path = OUTPUT_DIR / "diagram_13_phase_roadmap.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Saved: {out_path}")


if __name__ == "__main__":
    create_closed_loop_diagram()
    create_system_architecture_diagram()
    create_roadmap_diagram()

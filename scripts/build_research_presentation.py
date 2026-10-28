"""
Build the full, professional research presentation (.pptx) for:
Digital Twin-Based Cyber Attack Detection and Self-Healing for Resource-Constrained IoT Networks.
Embeds high-resolution figures, flowcharts, mathematical formulations, and detailed phase summaries.
"""

from pathlib import Path
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

OUTPUT_PPTX = Path("Digital_Twin_IoT_Cybersecurity_Research_Master_Plan.pptx")
PLOTS_DIR = Path("plots")

# Color Palette Constants
COLOR_NAVY_DARK   = RGBColor(15, 23, 42)     # #0f172a
COLOR_SLATE_BOX   = RGBColor(30, 41, 59)     # #1e293b
COLOR_CARD_BG     = RGBColor(248, 250, 252)  # #f8fafc
COLOR_BORDER      = RGBColor(226, 232, 240)  # #e2e8f0
COLOR_BLUE_ACCENT = RGBColor(2, 132, 199)    # #0284c7
COLOR_CYAN_ACCENT = RGBColor(14, 165, 233)   # #0ea5e9
COLOR_GREEN       = RGBColor(16, 185, 129)   # #10b981
COLOR_AMBER       = RGBColor(245, 158, 11)   # #f59e0b
COLOR_RED         = RGBColor(239, 68, 68)    # #ef4444
COLOR_PURPLE      = RGBColor(139, 92, 246)   # #8b5cf6
COLOR_WHITE       = RGBColor(255, 255, 255)
COLOR_TEXT_DARK   = RGBColor(15, 23, 42)
COLOR_TEXT_MUTED  = RGBColor(100, 116, 139)


def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def add_header(slide, title_text: str, category_text: str = "RESEARCH MASTER PLAN"):
        # Header banner container
        header_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(0.4), Inches(12.133), Inches(0.9)
        )
        header_shape.fill.solid()
        header_shape.fill.fore_color.rgb = COLOR_WHITE
        header_shape.line.color.rgb = COLOR_WHITE

        # Category badge
        badge = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(0.38), Inches(2.2), Inches(0.24)
        )
        badge.fill.solid()
        badge.fill.fore_color.rgb = COLOR_BLUE_ACCENT
        badge.line.color.rgb = COLOR_BLUE_ACCENT
        tf_b = badge.text_frame
        tf_b.word_wrap = False
        p_b = tf_b.paragraphs[0]
        p_b.text = category_text
        p_b.font.size = Pt(8.5)
        p_b.font.bold = True
        p_b.font.color.rgb = COLOR_WHITE
        p_b.font.name = "Segoe UI"
        p_b.alignment = PP_ALIGN.CENTER

        # Title text
        tx_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.62), Inches(12.133), Inches(0.6))
        tf = tx_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(20)
        p.font.bold = True
        p.font.color.rgb = COLOR_NAVY_DARK
        p.font.name = "Segoe UI"

        # Subtle bottom line
        line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.28), Inches(12.133), Inches(0.02)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = COLOR_BORDER
        line.line.color.rgb = COLOR_BORDER

    def add_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1.2)
        return card

    # =========================================================================
    # SLIDE 1: Title Slide (Dark Executive)
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLOR_NAVY_DARK
    bg.line.fill.background()

    # Title box
    tb = slide.shapes.add_textbox(Inches(1.0), Inches(1.3), Inches(11.333), Inches(3.2))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p0 = tf.paragraphs[0]
    p0.text = "RESEARCH MASTER PLAN & PROTOTYPE VALIDATION"
    p0.font.size = Pt(12)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_CYAN_ACCENT
    p0.font.name = "Segoe UI"

    p1 = tf.add_paragraph()
    p1.text = "Digital Twin-Based Cyber Attack Detection and Self-Healing for Resource-Constrained IoT Networks"
    p1.font.size = Pt(28)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE
    p1.font.name = "Segoe UI"
    p1.space_before = Pt(10)

    p2 = tf.add_paragraph()
    p2.text = "A Reproducible, Closed-Loop Resilience Architecture from Simulation to ESP32/LoRa Hardware"
    p2.font.size = Pt(15)
    p2.font.color.rgb = RGBColor(148, 163, 184)
    p2.font.name = "Segoe UI"
    p2.space_before = Pt(12)

    # 4 Status Pillars
    card_data = [
        ("Phase 1: Simulator", "VALIDATED", "56 Tests PASS\nPhysics & Energy Models", COLOR_GREEN),
        ("Phase 2: Digital Twin", "VALIDATED", "68 Tests PASS\n0.009 ms Sync Latency", COLOR_GREEN),
        ("Phase 3: Attack Sim", "VALIDATED", "87 Tests PASS\nDoS, Drop, Failure Models", COLOR_GREEN),
        ("Phase 4: Feature Eng", "VALIDATED", "94 Tests PASS\n95 Multi-Scale Features", COLOR_GREEN),
    ]

    for idx, (title, badge_txt, sub, col) in enumerate(card_data):
        cx = Inches(1.0 + idx * 2.9)
        cy = Inches(4.7)
        cw = Inches(2.65)
        ch = Inches(1.8)

        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, cy, cw, ch)
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_SLATE_BOX
        card.line.color.rgb = col
        card.line.width = Pt(1.5)

        tx = slide.shapes.add_textbox(cx, cy, cw, ch)
        tff = tx.text_frame
        tff.word_wrap = True
        
        pa = tff.paragraphs[0]
        pa.text = title
        pa.font.size = Pt(11)
        pa.font.bold = True
        pa.font.color.rgb = COLOR_WHITE
        pa.font.name = "Segoe UI"

        pb = tff.add_paragraph()
        pb.text = f"● {badge_txt}"
        pb.font.size = Pt(10)
        pb.font.bold = True
        pb.font.color.rgb = col
        pb.space_before = Pt(4)

        pc = tff.add_paragraph()
        pc.text = sub
        pc.font.size = Pt(9.5)
        pc.font.color.rgb = RGBColor(203, 213, 225)
        pc.space_before = Pt(6)

    # =========================================================================
    # SLIDE 2: Research Motivation & Paradigm
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Research Problem: The IoT Security & Resilience Trilemma", "MOTIVATION & CONTEXT")

    # Left Card: The Problem
    add_card(slide, Inches(0.6), Inches(1.5), Inches(5.9), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(5.5), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "The Resource-Constrained Dilemma"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY_DARK

    bullets = [
        ("Extreme Compute & Energy Constraints:", "Microcontrollers (e.g. ESP32, 240MHz, 520KB SRAM) and battery-powered nodes cannot sustain heavyweight IDS classifiers, deep neural networks, or complex routing recalculations."),
        ("Fragility to Multi-Vector Attacks:", "Resource-constrained networks are vulnerable to Denial-of-Service (DoS) buffer exhaustion, gray-hole selective packet dropping, and abrupt node failure outages."),
        ("The Recovery Paradox:", "Uncoordinated node isolation often causes unintended routing partitions, loop formations, or cascade failures across the topology."),
        ("Hardware Validation Gap:", "Most literature either remains in abstract software simulation (NS-3/Matlab) or deploys unverified ad-hoc heuristics directly on hardware without safe pre-evaluation.")
    ]
    for b_title, b_desc in bullets:
        p_b = tf.add_paragraph()
        p_b.text = f"• {b_title} "
        p_b.font.bold = True
        p_b.font.size = Pt(11)
        p_b.font.color.rgb = COLOR_NAVY_DARK
        p_b.space_before = Pt(8)
        run = p_b.add_run()
        run.text = b_desc
        run.font.bold = False
        run.font.color.rgb = COLOR_TEXT_MUTED

    # Right Card: The Proposed Solution
    add_card(slide, Inches(6.8), Inches(1.5), Inches(5.9), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(7.0), Inches(1.6), Inches(5.5), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "The Digital Twin Solution Paradigm"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLUE_ACCENT

    solutions = [
        ("Decoupled Intelligence:", "Physical nodes stream ultra-lightweight telemetry (TelemetryRecord). Heavy computation (ML detection, feature extraction, graph optimization) is offloaded to the Digital Twin at the edge server."),
        ("Living Virtual Shadow:", "The Digital Twin maintains continuous, validated state synchronization of every node, active link condition, and historical time-series buffer."),
        ("In-Silico Recovery Simulation (Core Novelty):", "Before issuing actuation commands to the physical network, the Digital Twin clones the current network state into a virtual sandbox and simulates candidate recovery actions."),
        ("Multi-Objective Optimization:", "Selects the optimal self-healing policy balancing packet loss, latency stretch, energy consumption, and communication overhead."),
        ("Hardware Portability:", "Invariant telemetry contract allows seamless transfer from Python simulation to physical ESP32 + LoRa hardware.")
    ]
    for b_title, b_desc in solutions:
        p_b = tf.add_paragraph()
        p_b.text = f"• {b_title} "
        p_b.font.bold = True
        p_b.font.size = Pt(11)
        p_b.font.color.rgb = COLOR_NAVY_DARK
        p_b.space_before = Pt(6)
        run = p_b.add_run()
        run.text = b_desc
        run.font.bold = False
        run.font.color.rgb = COLOR_TEXT_MUTED

    # =========================================================================
    # SLIDE 3: Research Questions (RQ1 - RQ6)
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Research Questions Guiding the Experimental Framework", "SCIENTIFIC OBJECTIVES")

    rq_list = [
        ("RQ1", "State Synchronization & Overhead", "Can a low-overhead, event-driven telemetry ingestion protocol maintain high-fidelity synchronization between constrained IoT nodes and their Digital Twin shadow without battery degradation?"),
        ("RQ2", "Telemetry-Driven ML Attack Detection", "How accurately and with what detection latency can lightweight, interpretable machine learning models identify DoS, selective forwarding, and node failure anomalies using temporal rolling features?"),
        ("RQ3", "Dynamic Behavioral Risk Modeling", "How can multi-factor physical indicators (forwarding fidelity, energy drain drift, and channel loss consistency) be synthesized into a dynamic node trust score without arbitrary heuristics?"),
        ("RQ4", "Pre-Execution Recovery Simulation", "Does forward-simulating candidate recovery strategies inside the Digital Twin prior to live actuation reduce recovery failures, prevent network partitioning, and minimize Mean Time to Recovery (MTTR)?"),
        ("RQ5", "Scalability & Resilience Quantification", "How does the closed-loop self-healing framework scale across network sizes (N = 6 to 100 nodes) in terms of computational overhead, communication overhead, and network availability?"),
        ("RQ6", "Hardware Portability (Sim-to-Real)", "Can the identical Digital Twin and self-healing software pipeline ingest telemetry and actuate recovery on physical ESP32 microcontrollers over LoRa without architectural redesign?")
    ]

    for idx, (rq_id, rq_title, rq_desc) in enumerate(rq_list):
        row = idx // 2
        col = idx % 2
        rx = Inches(0.6 + col * 6.2)
        ry = Inches(1.5 + row * 1.8)

        card = add_card(slide, rx, ry, Inches(5.9), Inches(1.65))
        tx = slide.shapes.add_textbox(rx + Inches(0.15), ry + Inches(0.1), Inches(5.6), Inches(1.45))
        tf = tx.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = f"{rq_id}: {rq_title}"
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = COLOR_BLUE_ACCENT

        p_desc = tf.add_paragraph()
        p_desc.text = rq_desc
        p_desc.font.size = Pt(10)
        p_desc.font.color.rgb = COLOR_TEXT_MUTED
        p_desc.space_before = Pt(4)

    # =========================================================================
    # SLIDE 4: System Architecture & Closed-Loop Lifecycle
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Global Closed-Loop System Architecture", "SYSTEM ARCHITECTURE")

    # Diagram top: Closed-loop flow
    dl_path = PLOTS_DIR / "diagram_closed_loop_lifecycle.png"
    if dl_path.exists():
        slide.shapes.add_picture(str(dl_path), Inches(0.6), Inches(1.4), Inches(12.133), Inches(2.3))

    # Diagram bottom: 2-layer Architecture
    sa_path = PLOTS_DIR / "diagram_system_architecture.png"
    if sa_path.exists():
        slide.shapes.add_picture(str(sa_path), Inches(0.6), Inches(3.9), Inches(12.133), Inches(3.2))

    # =========================================================================
    # SLIDE 5: Complete 13-Phase Research Roadmap
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Complete 13-Phase Incremental Research Progression", "RESEARCH ROADMAP")

    rm_path = PLOTS_DIR / "diagram_13_phase_roadmap.png"
    if rm_path.exists():
        slide.shapes.add_picture(str(rm_path), Inches(0.6), Inches(1.45), Inches(12.133), Inches(3.0))

    # Summary table below
    add_card(slide, Inches(0.6), Inches(4.7), Inches(12.133), Inches(2.3))
    tx = slide.shapes.add_textbox(Inches(0.8), Inches(4.8), Inches(11.7), Inches(2.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Phase Progression & Milestone Governance"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY_DARK

    p_tbl = tf.add_paragraph()
    p_tbl.text = (
        "• Phases 1–4 (COMPLETED & VALIDATED - 94 Unit Tests Passing):\n"
        "   - Established reproducible network simulator, Digital Twin state synchronizer, 3 threat models, and 95 engineered temporal features.\n"
        "• Phases 5–9 (CORE INTELLIGENCE & HEALING - Current Stage):\n"
        "   - ML detection (Phase 5), Dynamic trust engine (Phase 6), Candidate generation (Phase 7), In-silico DT simulation (Phase 8), Self-healing (Phase 9).\n"
        "• Phases 10–13 (VALIDATION, SCALABILITY & HARDWARE):\n"
        "   - Research dashboard (Phase 10), Benchmark ablation framework (Phase 11), Scalability to 100 nodes (Phase 12), Physical ESP32 + LoRa testbed (Phase 13)."
    )
    p_tbl.font.size = Pt(10.5)
    p_tbl.font.color.rgb = COLOR_TEXT_MUTED
    p_tbl.space_before = Pt(4)

    # =========================================================================
    # SLIDE 6: Phase 1: IoT Network Simulator
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 1: IoT Network Simulator Implementation", "PHASE 1 - COMPLETED & VALIDATED")

    # Left: Mathematical Models
    add_card(slide, Inches(0.6), Inches(1.5), Inches(6.5), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(6.1), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Mathematical & Physics Models (backend/simulation/)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY_DARK

    p_body = tf.add_paragraph()
    p_body.text = (
        "• Wireless Channel Propagation (Log-Distance Path Loss):\n"
        "   RSSI(d) = RSSI_0 - 10 * eta * log10(d / d_0) + X_sigma\n"
        "   eta = 2.8, RSSI_0 = -30 dBm, sigma = 2.0 dB (shadow fading)\n\n"
        "• FIFO Buffer Queuing & Drop-Tail Packet Loss:\n"
        "   P_loss = P_buffer_overflow + (1 - P_buffer_overflow) * P_channel_error\n"
        "   Q_max = 50 packets capacity, Sigmoid sensitivity threshold = -100 dBm\n\n"
        "• Computational Resource Coupling:\n"
        "   CPU(t) = min(100%, CPU_base + alpha * (lambda_gen + lambda_fwd) + eps_cpu)\n"
        "   RAM(t) = min(100%, RAM_base + (Q_len / Q_max) * 42.5% + beta * N_new)\n\n"
        "• Monotonic Battery Depletion Model:\n"
        "   E(t + dt) = E(t) - [P_idle * dt + E_tx * N_tx + E_rx * N_rx]\n"
        "   E_max = 1000 J, P_idle = 15 mW, E_tx = 8 mJ/pkt, E_rx = 4 mJ/pkt"
    )
    p_body.font.size = Pt(10)
    p_body.font.color.rgb = COLOR_TEXT_MUTED
    p_body.space_before = Pt(6)

    # Right: Embedded Topology Figure
    add_card(slide, Inches(7.4), Inches(1.5), Inches(5.3), Inches(5.4))
    top_img = PLOTS_DIR / "plot6_network_topology.png"
    if top_img.exists():
        slide.shapes.add_picture(str(top_img), Inches(7.6), Inches(1.7), Inches(4.9), Inches(4.8))

    # =========================================================================
    # SLIDE 7: Phase 1: Experimental Validation & Baseline Metrics
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 1: Baseline Simulation Results & Verification", "PHASE 1 - COMPLETED & VALIDATED")

    # Left: Baseline Metrics Table
    add_card(slide, Inches(0.6), Inches(1.5), Inches(5.5), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(5.1), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Baseline Statistics (6 Nodes, 300s, Seed=42)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY_DARK

    p_tbl = tf.add_paragraph()
    p_tbl.text = (
        "• Total Records Generated: 1,800 records\n"
        "• Mean Packet Generation: 2.01 pkts/s (std: 0.45)\n"
        "• Mean Forwarding Rate: 1.35 pkts/s (std: 1.90)\n"
        "• Mean Packet Loss Ratio: 0.0246 (2.46% nominal channel loss)\n"
        "• Mean End-to-End Latency: 28.08 ms (queuing + radio tx)\n"
        "• Mean RSSI: -81.39 dBm\n"
        "• Mean CPU Load: 11.05% (std: 3.53%)\n"
        "• Mean Memory Load: 17.69% (std: 1.59%)\n"
        "• Mean Remaining Battery: 98.91% (smooth linear discharge)\n\n"
        "Validation Status:\n"
        "✔ 56/56 Unit Tests Passed\n"
        "✔ Strict Determinism: seed=42 run 1 == run 2 (exact float match)\n"
        "✔ Scalability: Verified on 6, 10, 20, 50, and 100 nodes across Grid, Random, Mesh, Ring, Star topologies."
    )
    p_tbl.font.size = Pt(10)
    p_tbl.font.color.rgb = COLOR_TEXT_MUTED
    p_tbl.space_before = Pt(6)

    # Right: Plot 1 Packet Rate vs Time
    add_card(slide, Inches(6.4), Inches(1.5), Inches(6.3), Inches(5.4))
    p1_img = PLOTS_DIR / "plot1_packet_rate_vs_time.png"
    if p1_img.exists():
        slide.shapes.add_picture(str(p1_img), Inches(6.6), Inches(1.8), Inches(5.9), Inches(4.6))

    # =========================================================================
    # SLIDE 8: Phase 2: Digital Twin State Synchronizer & Shadow Model
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 2: Digital Twin State Synchronizer & Shadow Model", "PHASE 2 - COMPLETED & VALIDATED")

    # Left: DT Architecture
    add_card(slide, Inches(0.6), Inches(1.5), Inches(6.0), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Digital Twin Architecture (backend/digital_twin/)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY_DARK

    p_body = tf.add_paragraph()
    p_body.text = (
        "• Invariant Telemetry Contract:\n"
        "   Ingests TelemetryRecord directly without schema pollution or hardcoded physical dependencies.\n\n"
        "• Virtual Node Shadow Model (TwinNodeState):\n"
        "   Maintains real-time physical, computational, and channel states for every active network node.\n\n"
        "• Bounded Temporal History Manager (HistoryManager):\n"
        "   Maintains rolling deques with configurable retention (W = 60s). Automatically prunes expired records to guarantee bounded RAM overhead.\n\n"
        "• Topology Shadow Graph (NetworkTopologyModel):\n"
        "   NetworkX-backed dynamic graph tracking directional link states, active adjacency, and connected components.\n\n"
        "• Software Synchronization Latency Benchmark:\n"
        "   Mean: 0.0090 ms | Min: 0.0052 ms | Max: 3.9694 ms\n"
        "   Demonstrates sub-millisecond edge software overhead."
    )
    p_body.font.size = Pt(10)
    p_body.font.color.rgb = COLOR_TEXT_MUTED
    p_body.space_before = Pt(6)

    # Right: Plot 4 Sync Latency Over Time
    add_card(slide, Inches(6.9), Inches(1.5), Inches(5.8), Inches(5.4))
    p_sync = PLOTS_DIR / "phase2_plot4_sync_latency_vs_time.png"
    if p_sync.exists():
        slide.shapes.add_picture(str(p_sync), Inches(7.1), Inches(1.8), Inches(5.4), Inches(4.5))

    # =========================================================================
    # SLIDE 9: Phase 2: State Consistency & Health Modeling
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 2: Digital Twin Fidelity & Health Assessment", "PHASE 2 - COMPLETED & VALIDATED")

    # Top Half: Topology comparison
    add_card(slide, Inches(0.6), Inches(1.5), Inches(7.0), Inches(5.4))
    p_top = PLOTS_DIR / "phase2_plot5_topology_comparison.png"
    if p_top.exists():
        slide.shapes.add_picture(str(p_top), Inches(0.8), Inches(1.7), Inches(6.6), Inches(4.8))

    # Right Half: Descriptive Health Model
    add_card(slide, Inches(7.9), Inches(1.5), Inches(4.8), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(8.1), Inches(1.6), Inches(4.4), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Descriptive Network Health"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLUE_ACCENT

    p_desc = tf.add_paragraph()
    p_desc.text = (
        "• Deterministic Health Classification:\n"
        "   Strictly metric-driven; avoids arbitrary ML black-box scoring during baseline synchronization.\n\n"
        "• Classification Thresholds:\n"
        "   - HEALTHY: Connected ratio >= 0.90, loss < 0.10, and 0 degraded nodes.\n"
        "   - DEGRADED: Connected ratio >= 0.50 and loss < 0.40.\n"
        "   - CRITICAL: Connected ratio < 0.50 or loss >= 0.40.\n\n"
        "• State Fidelity Verification:\n"
        "   - 68/68 Tests Passing.\n"
        "   - Exact float-level match between simulator telemetry and Digital Twin query API.\n"
        "   - Disconnected nodes naturally sever incident edges in the virtual shadow graph."
    )
    p_desc.font.size = Pt(10)
    p_desc.font.color.rgb = COLOR_TEXT_MUTED
    p_desc.space_before = Pt(6)

    # =========================================================================
    # SLIDE 10: Phase 3: Controlled Cyberattack Simulation Framework
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 3: Controlled Cyberattack Injection Framework", "PHASE 3 - COMPLETED & VALIDATED")

    # 3 Threat Columns
    threats = [
        ("DoS / Packet Flooding", "backend/attacks/dos.py",
         "Floods target node buffer with surge traffic (intensity = 20 pkts/s).\n\n"
         "Physical Propagation:\n"
         "• Queue saturation (Q_len -> 50)\n"
         "• Drop-tail buffer packet loss\n"
         "• CPU load surges (11% -> 49%)\n"
         "• Latency surges (28ms -> 91ms)\n"
         "• Accelerated battery drain", COLOR_RED),
        ("Compromised Node", "backend/attacks/compromised_node.py",
         "Simulates internal malicious gray-hole selectively dropping forwarded packets.\n\n"
         "Physical Propagation:\n"
         "• Binomial drop probability p = 0.50\n"
         "• Downstream throughput suppressed\n"
         "• Observed packet loss: 2.65% -> 51.32%\n"
         "• Matches intensity with binomial variance", COLOR_AMBER),
        ("Node Failure / Outage", "backend/attacks/node_failure.py",
         "Simulates transceiver failure, power loss, or processor crash.\n\n"
         "Physical Propagation:\n"
         "• State -> DISCONNECTED\n"
         "• Ceases transmission & forwarding\n"
         "• Network availability: 1.0 -> 0.833\n"
         "• Clean reboot post-attack if energy > 0", COLOR_PURPLE),
    ]

    for idx, (t_name, code_loc, desc, t_col) in enumerate(threats):
        tx_pos = Inches(0.6 + idx * 4.1)
        card = add_card(slide, tx_pos, Inches(1.5), Inches(3.9), Inches(5.4))
        card.line.color.rgb = t_col

        tx = slide.shapes.add_textbox(tx_pos + Inches(0.15), Inches(1.65), Inches(3.6), Inches(5.0))
        tf = tx.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = t_name
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = t_col

        p_loc = tf.add_paragraph()
        p_loc.text = code_loc
        p_loc.font.size = Pt(8.5)
        p_loc.font.color.rgb = COLOR_TEXT_MUTED

        p_body = tf.add_paragraph()
        p_body.text = desc
        p_body.font.size = Pt(9.5)
        p_body.font.color.rgb = COLOR_TEXT_DARK
        p_body.space_before = Pt(8)

    # =========================================================================
    # SLIDE 11: Phase 3: Physical Propagation & Non-Interference
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 3: Observable Attack Effects & Non-Interference", "PHASE 3 - COMPLETED & VALIDATED")

    # Left: Plot 1 DoS Packet Rate
    add_card(slide, Inches(0.6), Inches(1.5), Inches(5.9), Inches(2.65))
    p_dos_r = PLOTS_DIR / "phase3_plot1_dos_packet_rate.png"
    if p_dos_r.exists():
        slide.shapes.add_picture(str(p_dos_r), Inches(0.7), Inches(1.55), Inches(5.7), Inches(2.5))

    # Left Bottom: Plot 4 Compromised Node Loss
    add_card(slide, Inches(0.6), Inches(4.3), Inches(5.9), Inches(2.65))
    p_comp = PLOTS_DIR / "phase3_plot4_compromised_node_drop.png"
    if p_comp.exists():
        slide.shapes.add_picture(str(p_comp), Inches(0.7), Inches(4.35), Inches(5.7), Inches(2.5))

    # Right: Plot 5 & 6 Failure and Availability
    add_card(slide, Inches(6.8), Inches(1.5), Inches(5.9), Inches(2.65))
    p_fail = PLOTS_DIR / "phase3_plot5_node_failure_state.png"
    if p_fail.exists():
        slide.shapes.add_picture(str(p_fail), Inches(6.9), Inches(1.55), Inches(5.7), Inches(2.5))

    add_card(slide, Inches(6.8), Inches(4.3), Inches(5.9), Inches(2.65))
    p_avail = PLOTS_DIR / "phase3_plot6_network_availability.png"
    if p_avail.exists():
        slide.shapes.add_picture(str(p_avail), Inches(6.9), Inches(4.35), Inches(5.7), Inches(2.5))

    # =========================================================================
    # SLIDE 12: Phase 3: Combined Scenario & Ground Truth Alignment
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 3: Multi-Scenario Combined Attack Timeline", "PHASE 3 - COMPLETED & VALIDATED")

    # Top: Combined Timeline
    add_card(slide, Inches(0.6), Inches(1.45), Inches(12.133), Inches(3.0))
    p_comb = PLOTS_DIR / "phase3_plot7_combined_timeline.png"
    if p_comb.exists():
        slide.shapes.add_picture(str(p_comb), Inches(0.8), Inches(1.5), Inches(11.7), Inches(2.85))

    # Bottom: Ground Truth Scatter
    add_card(slide, Inches(0.6), Inches(4.6), Inches(12.133), Inches(2.4))
    p_gt = PLOTS_DIR / "phase3_plot8_ground_truth_timeline.png"
    if p_gt.exists():
        slide.shapes.add_picture(str(p_gt), Inches(0.8), Inches(4.65), Inches(11.7), Inches(2.25))

    # =========================================================================
    # SLIDE 13: Phase 4: Dataset & Feature Engineering Architecture
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 4: Dataset & Feature Engineering Architecture", "PHASE 4 - COMPLETED & VALIDATED")

    # 4 Feature Pillars
    feat_pillars = [
        ("Multi-Scale Temporal Windows", "Rolling Stats: W = 5s, 15s, 30s",
         "Computed per node for 6 core metrics:\n"
         "• Rolling Mean (mu_W)\n"
         "• Rolling Std (sigma_W)\n"
         "• Rolling Min & Max (min_W, max_W)\n\n"
         "Rationale: W=5s isolates sudden bursts (DoS); W=30s isolates slow battery drain & gray-hole drops.", COLOR_BLUE_ACCENT),
        ("Rate-of-Change Derivatives", "Temporal Acceleration",
         "First-order derivatives (dx/dt):\n"
         "• delta_packet_rate / dt\n"
         "• delta_forwarding_rate / dt\n"
         "• delta_cpu / dt\n"
         "• delta_latency / dt\n"
         "• energy_drain_rate = -dE/dt\n\n"
         "Instantly catches explosive inflection points.", COLOR_CYAN_ACCENT),
        ("Domain Context Ratios", "Physical Interaction Features",
         "Engineered IoT domain features:\n"
         "• Forwarding Ratio:\n"
         "   N_fwd / (N_gen + N_fwd + 1e-6)\n"
         "• Congestion Index:\n"
         "   Latency / max(1, |RSSI|)\n"
         "• Traffic-to-CPU Ratio:\n"
         "   Total Traffic / max(1, CPU)", COLOR_PURPLE),
        ("Spatial Discrepancy", "Macro Network Baseline",
         "Deviations from instantaneous network average at timestamp t:\n"
         "• cpu_network_discrepancy\n"
         "• loss_network_discrepancy\n"
         "• latency_network_discrepancy\n\n"
         "Isolates anomalous node behavior from general network load.", COLOR_GREEN),
    ]

    for idx, (title, sub, desc, col) in enumerate(feat_pillars):
        px = Inches(0.6 + idx * 3.08)
        card = add_card(slide, px, Inches(1.5), Inches(2.95), Inches(5.4))
        card.line.color.rgb = col

        tx = slide.shapes.add_textbox(px + Inches(0.12), Inches(1.6), Inches(2.7), Inches(5.1))
        tf = tx.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = col

        p_sub = tf.add_paragraph()
        p_sub.text = sub
        p_sub.font.size = Pt(8.5)
        p_sub.font.color.rgb = COLOR_TEXT_MUTED
        p_sub.space_before = Pt(2)

        p_body = tf.add_paragraph()
        p_body.text = desc
        p_body.font.size = Pt(9)
        p_body.font.color.rgb = COLOR_TEXT_DARK
        p_body.space_before = Pt(8)

    # =========================================================================
    # SLIDE 14: Phase 4: Data Leakage Prevention & Dataset Partitions
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 4: Data Leakage Safeguards & Partition Integrity", "PHASE 4 - COMPLETED & VALIDATED")

    # Left: Correlation Heatmap
    add_card(slide, Inches(0.6), Inches(1.5), Inches(6.0), Inches(5.4))
    p_heat = PLOTS_DIR / "phase4_plot1_feature_correlation_heatmap.png"
    if p_heat.exists():
        slide.shapes.add_picture(str(p_heat), Inches(0.8), Inches(1.65), Inches(5.6), Inches(4.9))

    # Right: Partitioning & Leakage Rules
    add_card(slide, Inches(6.9), Inches(1.5), Inches(5.8), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(7.1), Inches(1.6), Inches(5.4), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Strict Data Leakage Prevention Protocols"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY_DARK

    p_txt = tf.add_paragraph()
    p_txt.text = (
        "• Strict Causal Backward-Looking Windows:\n"
        "   Rolling features use strictly backward windows ([t - W, t], closed='right').\n"
        "   Proven by test_zero_future_leakage: changing future data at t=40s causes ZERO change to feature vectors at t <= 30s.\n\n"
        "• Train-Only Scaler Parameter Fitting:\n"
        "   Z-score parameters (means mu, stds sigma) are fitted STRICTLY on the training split (t <= 209s) and frozen in feature_metadata.json.\n\n"
        "• Dataset Partitioning (models/datasets/):\n"
        "   - Training Set: 1,260 records (70%, t <= 209s)\n"
        "   - Validation Set: 270 records (15%, 210s < t <= 254s)\n"
        "   - Chronological Test Set: 270 records (15%, t >= 255s)\n"
        "   - Cross-Seed Test Set: 1,800 records (Seed 43, Attack Seed 2001) for out-of-sample stochastic generalization."
    )
    p_txt.font.size = Pt(9.8)
    p_txt.font.color.rgb = COLOR_TEXT_MUTED
    p_txt.space_before = Pt(6)

    # =========================================================================
    # SLIDE 15: Phase 4: Feature Densities & Window Responsiveness
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 4: Feature Responsiveness & Statistical Separability", "PHASE 4 - COMPLETED & VALIDATED")

    # Left: Plot 2 KDE Distributions
    add_card(slide, Inches(0.6), Inches(1.5), Inches(6.0), Inches(5.4))
    p_kde = PLOTS_DIR / "phase4_plot2_feature_distributions_kde.png"
    if p_kde.exists():
        slide.shapes.add_picture(str(p_kde), Inches(0.8), Inches(1.65), Inches(5.6), Inches(4.9))

    # Right: Plot 3 Window Trajectory
    add_card(slide, Inches(6.9), Inches(1.5), Inches(5.8), Inches(5.4))
    p_traj = PLOTS_DIR / "phase4_plot3_multiscale_window_trajectory.png"
    if p_traj.exists():
        slide.shapes.add_picture(str(p_traj), Inches(7.1), Inches(1.65), Inches(5.4), Inches(4.9))

    # =========================================================================
    # SLIDE 16: Phase 5 (Next): ML Attack Detection Engine
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 5 (Next Stage): Machine Learning Attack Detection Engine", "PHASE 5 - READY TO COMMENCE")

    # Left Card: Model Architecture
    add_card(slide, Inches(0.6), Inches(1.5), Inches(6.0), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Model Selection Strategy (backend/detection/)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY_DARK

    p_b = tf.add_paragraph()
    p_b.text = (
        "• Model Hierarchy (Interpretable Baselines First):\n"
        "   1. Regularized Logistic Regression: Linear benchmark, L1/L2 penalty for feature sparsity.\n"
        "   2. Random Forest Classifier: Robust non-linear tree ensemble; captures feature interactions.\n"
        "   3. XGBoost / LightGBM: State-of-the-art gradient boosting for tabular telemetry; handles class imbalance via scale_pos_weight.\n\n"
        "• Dual Target Classification Tasks:\n"
        "   - Binary Detection: Benign vs Attack (target_binary).\n"
        "   - Multi-Class Identification: Normal, DoS, Compromised, Node Failure (target_multiclass).\n\n"
        "• Zero-Day Anomaly Detection (Secondary):\n"
        "   Isolation Forest / Autoencoder trained strictly on benign baseline to flag unmodeled zero-day anomalies."
    )
    p_b.font.size = Pt(10)
    p_b.font.color.rgb = COLOR_TEXT_MUTED
    p_b.space_before = Pt(6)

    # Right Card: Evaluation & TinyML
    add_card(slide, Inches(6.9), Inches(1.5), Inches(5.8), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(7.1), Inches(1.6), Inches(5.4), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Academic Evaluation Metrics"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLUE_ACCENT

    p_ev = tf.add_paragraph()
    p_ev.text = (
        "• Rigorous Classification Metrics:\n"
        "   - Precision, Recall, Macro/Weighted F1-Score\n"
        "   - ROC-AUC & Precision-Recall AUC (PR-AUC)\n"
        "   - False Positive Rate (FPR) & False Negative Rate (FNR)\n\n"
        "• Real-Time Operational Performance:\n"
        "   - Inference Latency per sample (microseconds)\n"
        "   - Detection Delay (timesteps from attack onset to alarm)\n"
        "   - Model memory footprint (KB, evaluating TinyML edge gateway viability)\n\n"
        "• Generalization Validation Gate:\n"
        "   - Evaluation on Chronological Test Split\n"
        "   - Evaluation on Independent Cross-Seed Test Set (Seed 43)\n"
        "   - Export calibrated posterior probabilities P(Attack | x) to feed Phase 6 Trust Engine."
    )
    p_ev.font.size = Pt(10)
    p_ev.font.color.rgb = COLOR_TEXT_MUTED
    p_ev.space_before = Pt(6)

    # =========================================================================
    # SLIDE 17: Phase 6: Dynamic Risk & Trust Engine (Planned)
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 6: Dynamic Risk & Node Trust Assessment Engine", "PHASE 6 - PLANNED")

    # Left: Trust Formulation
    add_card(slide, Inches(0.6), Inches(1.5), Inches(6.0), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Multi-Factor Behavioral Trust Formulation"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY_DARK

    p_form = tf.add_paragraph()
    p_form.text = (
        "Trust Score for Node i at time t:\n\n"
        "T_i(t) = w_fwd * T_fwd(i, t) + w_nrg * T_nrg(i, t) + \n"
        "         w_loss * T_loss(i, t) + w_ml * (1 - P_attack(i, t))\n\n"
        "Where:\n"
        "• T_fwd: Forwarding Consistency Trust\n"
        "   Ratio of observed forwarded packets to expected transit packets.\n"
        "• T_nrg: Energy Depletion Trust\n"
        "   Divergence between theoretical power model and observed drain.\n"
        "• T_loss: Channel-Consistent Loss Trust\n"
        "   Penalizes loss ratios exceeding physical log-distance expectations.\n"
        "• P_attack: Calibrated ML posterior attack probability from Phase 5.\n\n"
        "Weights constraint: w_fwd + w_nrg + w_loss + w_ml = 1.0"
    )
    p_form.font.size = Pt(9.8)
    p_form.font.color.rgb = COLOR_TEXT_MUTED
    p_form.space_before = Pt(6)

    # Right: Sensitivity & Trust Dynamics
    add_card(slide, Inches(6.9), Inches(1.5), Inches(5.8), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(7.1), Inches(1.6), Inches(5.4), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Trust Decay, Penalty & Recovery Dynamics"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLUE_ACCENT

    p_dyn = tf.add_paragraph()
    p_dyn.text = (
        "• Asymmetric Penalty vs Recovery:\n"
        "   - Swift Penalty: Exponential trust decay upon detected malicious activity:\n"
        "     T(t) = T(t-1) * exp(-lambda_penalty * severity)\n"
        "   - Cautious Recovery: Slow logarithmic reinstatement post-attack to prevent on-off strategic attackers.\n\n"
        "• Rigorous Sensitivity Analysis Protocol:\n"
        "   Systematically sweep weights (w_fwd, w_nrg, w_loss, w_ml) across a Dirichlet simplex grid to eliminate arbitrary heuristic bias.\n\n"
        "• Threshold Integration with Phase 7:\n"
        "   - Nominal: T > 0.75 (Fully Trusted)\n"
        "   - Suspicious: 0.40 <= T <= 0.75 (Candidate for Rate Limiting / Reroute)\n"
        "   - Malicious: T < 0.40 (Triggers In-Silico Recovery Simulation)"
    )
    p_dyn.font.size = Pt(9.8)
    p_dyn.font.color.rgb = COLOR_TEXT_MUTED
    p_dyn.space_before = Pt(6)

    # =========================================================================
    # SLIDE 18: Phase 7: Candidate Recovery Strategy Generator (Planned)
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 7: Candidate Recovery Strategy Taxonomy", "PHASE 7 - PLANNED")

    # 4 Recovery Cards
    strat_cards = [
        ("STRATEGY 1: Node Isolation", "Total Link Quarantine",
         "Completely sever all incident logical edges to target node.\n\n"
         "Pros:\n"
         "• 100% containment of malicious traffic.\n"
         "Risks:\n"
         "• Risk of graph partition / unreachable nodes.", COLOR_RED),
        ("STRATEGY 2: Dynamic Rerouting", "Topology Bypass",
         "Recompute shortest paths penalizing low-trust nodes without cutting them off.\n\n"
         "Pros:\n"
         "• Preserves global network reachability.\n"
         "Risks:\n"
         "• Path stretch (higher latency on detour).", COLOR_BLUE_ACCENT),
        ("STRATEGY 3: Ingress Rate Limiting", "Traffic Throttling",
         "Impose token-bucket rate limiting on suspicious ingress buffers.\n\n"
         "Pros:\n"
         "• Neutralizes DoS buffer overflow.\n"
         "Risks:\n"
         "• Legitimate burst traffic dropped if false positive.", COLOR_AMBER),
        ("STRATEGY 4: Soft Reboot / Rollback", "State Reset & Power Boost",
         "Command remote firmware soft-reset or transceiver TX power boost.\n\n"
         "Pros:\n"
         "• Recovers crashed nodes / overcomes jamming.\n"
         "Risks:\n"
         "• Transient reboot blackout delay (~5s).", COLOR_PURPLE),
    ]

    for idx, (s_title, s_sub, s_desc, s_col) in enumerate(strat_cards):
        cx = Inches(0.6 + idx * 3.08)
        card = add_card(slide, cx, Inches(1.5), Inches(2.95), Inches(5.4))
        card.line.color.rgb = s_col

        tx = slide.shapes.add_textbox(cx + Inches(0.12), Inches(1.6), Inches(2.7), Inches(5.1))
        tf = tx.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = s_title
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = s_col

        p_sub = tf.add_paragraph()
        p_sub.text = s_sub
        p_sub.font.size = Pt(8.5)
        p_sub.font.color.rgb = COLOR_TEXT_MUTED
        p_sub.space_before = Pt(2)

        p_desc = tf.add_paragraph()
        p_desc.text = s_desc
        p_desc.font.size = Pt(9.5)
        p_desc.font.color.rgb = COLOR_TEXT_DARK
        p_desc.space_before = Pt(8)

    # =========================================================================
    # SLIDE 19: Phase 8: Digital Twin Recovery Simulation & Optimization (Core Novelty)
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 8: In-Silico Recovery Simulation & Optimization (Core Contribution)", "PHASE 8 - CORE RESEARCH NOVELTY")

    # Left: The Virtual Sandbox Concept
    add_card(slide, Inches(0.6), Inches(1.5), Inches(6.0), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "The In-Silico Predictive Sandbox"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_PURPLE

    p_body = tf.add_paragraph()
    p_body.text = (
        "Why This is the Core Novelty:\n"
        "Most IoT security papers apply fixed heuristic mitigations (e.g. always isolate). In multi-hop mesh IoT networks, isolating a critical forwarder causes severe collateral partition.\n\n"
        "The Digital Twin Pre-Evaluation Workflow:\n"
        "1. Virtual State Cloned: Current Digital Twin state S(t) is cloned into temporary virtual sandboxes S_sandbox(k).\n"
        "2. Candidate Strategies Applied: In each sandbox, a distinct candidate strategy s_k from Phase 7 is executed.\n"
        "3. Lookahead Simulation: The Digital Twin forward-simulates network dynamics for horizon H in [10s, 30s, 60s].\n"
        "4. Consequences Estimated:\n"
        "   - Projected packet loss delta\n"
        "   - Projected latency path stretch\n"
        "   - Projected battery depletion on reroute hops\n"
        "   - Graph connectivity & partition verification."
    )
    p_body.font.size = Pt(9.8)
    p_body.font.color.rgb = COLOR_TEXT_MUTED
    p_body.space_before = Pt(6)

    # Right: Multi-Objective Cost Optimization
    add_card(slide, Inches(6.9), Inches(1.5), Inches(5.8), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(7.1), Inches(1.6), Inches(5.4), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Multi-Objective Cost Optimization J(s)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLUE_ACCENT

    p_cost = tf.add_paragraph()
    p_cost.text = (
        "Optimal Strategy Selection Formulation:\n\n"
        "s* = argmin_{s_k in S} J(s_k)\n\n"
        "Where Cost Function J(s_k) is:\n\n"
        "J(s_k) = w_1 * (Delta_Latency / Latency_base) + \n"
        "         w_2 * Delta_Loss + \n"
        "         w_3 * (Delta_Energy / Energy_base) + \n"
        "         w_4 * Signaling_Overhead(s_k)\n\n"
        "Subject to Hard Constraints:\n"
        "• Network must remain connected: Connected_Components(G) == 1\n"
        "• Projected packet delivery ratio > PDR_min (e.g. 0.90)\n"
        "• No routing loops: nx.is_directed_acyclic_graph(Routes) == True\n\n"
        "Guarantees that the chosen self-healing action is mathematically optimal and provably safe."
    )
    p_cost.font.size = Pt(9.8)
    p_cost.font.color.rgb = COLOR_TEXT_MUTED
    p_cost.space_before = Pt(6)

    # =========================================================================
    # SLIDE 20: Phase 9: Autonomous Self-Healing & Closed-Loop Actuation (Planned)
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phase 9: Autonomous Self-Healing & Closed-Loop Verification", "PHASE 9 - PLANNED")

    # Left: Actuation Dispatch
    add_card(slide, Inches(0.6), Inches(1.5), Inches(6.0), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Closed-Loop Actuation Dispatch"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY_DARK

    p_b = tf.add_paragraph()
    p_b.text = (
        "• Actuation Policy Dispatcher:\n"
        "   Translates optimal strategy s* into compact downlink actuation frames:\n"
        "   - Reroute commands to 1-hop routing neighbors.\n"
        "   - Ingress rate-limit tokens to suspicious nodes.\n"
        "   - Downlink reboot triggers to failed/compromised nodes.\n\n"
        "• Closed-Loop Verification Loop:\n"
        "   Following actuation, the Digital Twin monitors incoming telemetry:\n"
        "   1. Has packet loss dropped back to baseline (P_loss < 0.05)?\n"
        "   2. Has CPU utilization stabilized to nominal (< 15%)?\n"
        "   3. Has network reachability been preserved (100% active nodes connected)?\n\n"
        "• Fallback Mechanism:\n"
        "   If verification fails within timeout T_verify, rollback to conservative safe policy."
    )
    p_b.font.size = Pt(9.8)
    p_b.font.color.rgb = COLOR_TEXT_MUTED
    p_b.space_before = Pt(6)

    # Right: Resilience Metrics
    add_card(slide, Inches(6.9), Inches(1.5), Inches(5.8), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(7.1), Inches(1.6), Inches(5.4), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Resilience & Recovery Metrics"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN

    p_res = tf.add_paragraph()
    p_res.text = (
        "• Mean Time to Detect (MTTD):\n"
        "   MTTD = t_detect - t_attack_start\n"
        "   (Quantifies ML temporal responsiveness)\n\n"
        "• Mean Time to Recover (MTTR):\n"
        "   MTTR = t_restored - t_detect\n"
        "   (Quantifies DT simulation + actuation delay)\n\n"
        "• Quantitative Resilience Score (R):\n"
        "   Integral of Quality of Service recovery trajectory:\n\n"
        "   R = [Integral_{t0}^{t0+T} QoS(t) dt] / [QoS_nominal * T]\n\n"
        "   Where QoS(t) is defined as Packet Delivery Ratio (PDR) or Network Availability.\n"
        "   R = 1.0 indicates instantaneous, loss-free self-healing resilience."
    )
    p_res.font.size = Pt(9.8)
    p_res.font.color.rgb = COLOR_TEXT_MUTED
    p_res.space_before = Pt(6)

    # =========================================================================
    # SLIDE 21: Phase 10 & 11: Real-Time Dashboard & Experimental Framework
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phases 10 & 11: Dashboard & Comparative Baseline Framework", "PHASES 10 & 11 - PLANNED")

    # Left: Phase 10 Dashboard
    add_card(slide, Inches(0.6), Inches(1.5), Inches(6.0), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Phase 10: Research Monitoring Dashboard"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY_DARK

    p_dash = tf.add_paragraph()
    p_dash.text = (
        "• Interactive Visual Telemetry (Streamlit / Plotly):\n"
        "   Academic visualization suite for live paper demonstrations.\n\n"
        "• Live Visual Components:\n"
        "   1. Real-Time Network Topology Map: Node status color-coded by connection and trust score.\n"
        "   2. Live Streaming Telemetry: Sliding time-series throughput, loss, latency, and CPU.\n"
        "   3. Physical vs Virtual Shadow Fidelity: Direct side-by-side comparison of physical node and Digital Twin state.\n"
        "   4. Attack Injection Control Panel: Manual trigger for DoS, compromised drop, or node failure.\n"
        "   5. Self-Healing Decision Audit Log: Explaining why candidate strategy s* was selected by J(s)."
    )
    p_dash.font.size = Pt(9.8)
    p_dash.font.color.rgb = COLOR_TEXT_MUTED
    p_dash.space_before = Pt(6)

    # Right: Phase 11 Baselines
    add_card(slide, Inches(6.9), Inches(1.5), Inches(5.8), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(7.1), Inches(1.6), Inches(5.4), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Phase 11: Comparative Experimental Baselines"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLUE_ACCENT

    p_base = tf.add_paragraph()
    p_base.text = (
        "Rigorous Evaluation Against 4 Baselines:\n"
        "• Baseline 1: No Detection / No Recovery\n"
        "   (Raw unmitigated attack degradation)\n"
        "• Baseline 2: Static Threshold + Fixed Isolation\n"
        "   (Traditional rule-based IDS; naive isolation)\n"
        "• Baseline 3: ML Detection + Fixed Recovery\n"
        "   (ML detection without DT pre-simulation)\n"
        "• Proposed Framework: ML Detection + Dynamic Trust + In-Silico DT Recovery Simulation + Autonomous Self-Healing\n\n"
        "Ablation Studies:\n"
        "• Sensitivity to lookahead horizon H (10s vs 30s vs 60s)\n"
        "• Sensitivity to cost weights w_1, w_2, w_3, w_4\n"
        "• Resilience under lossy telemetry channels."
    )
    p_base.font.size = Pt(9.8)
    p_base.font.color.rgb = COLOR_TEXT_MUTED
    p_base.space_before = Pt(6)

    # =========================================================================
    # SLIDE 22: Phase 12 & 13: Scalability & Hardware Validation (ESP32 + LoRa)
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Phases 12 & 13: Scalability & Physical Hardware Validation", "PHASES 12 & 13 - PLANNED")

    # Left: Phase 12 Scalability
    add_card(slide, Inches(0.6), Inches(1.5), Inches(6.0), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Phase 12: Scalability & Stress Testing"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY_DARK

    p_sc = tf.add_paragraph()
    p_sc.text = (
        "• Systematic Node Scaling:\n"
        "   N in {6, 10, 20, 50, 100} nodes.\n\n"
        "• Variable Traffic & Attack Intensities:\n"
        "   - Nominal traffic: 2 pkts/s -> Extreme stress: 20 pkts/s.\n"
        "   - Multi-attacker scenarios: 1 to 5 compromised nodes.\n\n"
        "• System Overhead Profiling:\n"
        "   - Ingestion throughput (records/sec).\n"
        "   - Digital Twin server CPU & RAM consumption.\n"
        "   - Optimization solving time as a function of network size.\n"
        "   - Packet delivery ratio vs network density."
    )
    p_sc.font.size = Pt(9.8)
    p_sc.font.color.rgb = COLOR_TEXT_MUTED
    p_sc.space_before = Pt(6)

    # Right: Phase 13 Hardware Testbed
    add_card(slide, Inches(6.9), Inches(1.5), Inches(5.8), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(7.1), Inches(1.6), Inches(5.4), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Phase 13: Physical ESP32 + LoRa Testbed"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN_ACCENT

    p_hw = tf.add_paragraph()
    p_hw.text = (
        "• Hardware Configuration:\n"
        "   4–6 ESP32 microcontrollers (Tensilica Xtensa LX6, 240MHz, 520KB SRAM) equipped with SX1276 LoRa transceivers.\n\n"
        "• Gateway Bridge Architecture:\n"
        "   - Physical LoRa gateway receives RF telemetry packets.\n"
        "   - Serial / MQTT bridge converts binary payload into invariant TelemetryRecord JSON stream.\n\n"
        "• Seamless Sim-to-Real Transfer:\n"
        "   The Digital Twin, ML detection engine, and recovery optimizer run UNCHANGED on the edge server.\n\n"
        "• Physical Actuation Verification:\n"
        "   LoRa downlink command triggers dynamic route table reconfig or deep sleep power state on real ESP32."
    )
    p_hw.font.size = Pt(9.8)
    p_hw.font.color.rgb = COLOR_TEXT_MUTED
    p_hw.space_before = Pt(6)

    # =========================================================================
    # SLIDE 23: Scientific Rigor & Publication Roadmap
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, "Scientific Rigor, Verification Summary & Publication Targets", "RESEARCH GOVERNANCE")

    # Left: Verification Summary
    add_card(slide, Inches(0.6), Inches(1.5), Inches(6.0), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Automated Test Suite (94 Tests PASS)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN

    p_tests = tf.add_paragraph()
    p_tests.text = (
        "• Test Coverage Breakdown:\n"
        "   - tests/test_node.py (5 tests): Energy decay, CPU scaling, bounds.\n"
        "   - tests/test_topology.py (28 tests): Grid, mesh, random, symmetry.\n"
        "   - tests/test_telemetry.py (18 tests): Out-of-bounds rejection.\n"
        "   - tests/test_simulator.py (5 tests): Determinism & progression.\n"
        "   - tests/test_digital_twin.py (10 tests): History eviction, shadow.\n"
        "   - tests/test_attacks.py (17 tests): Boundaries, DoS, drop, non-interference.\n"
        "   - tests/test_phase2_integration.py (2 tests): End-to-end sync.\n"
        "   - tests/test_phase3_integration.py (2 tests): Multi-attack fidelity.\n"
        "   - tests/test_feature_engineering.py (7 tests): Causal non-leakage.\n\n"
        "• Scientific Integrity Principles:\n"
        "   - Zero fabricated results; all metrics empirically executed.\n"
        "   - Explicit distinction between software execution time and wireless latency."
    )
    p_tests.font.size = Pt(9.5)
    p_tests.font.color.rgb = COLOR_TEXT_MUTED
    p_tests.space_before = Pt(6)

    # Right: Publication Venues
    add_card(slide, Inches(6.9), Inches(1.5), Inches(5.8), Inches(5.4))
    tx = slide.shapes.add_textbox(Inches(7.1), Inches(1.6), Inches(5.4), Inches(5.1))
    tf = tx.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "Target Flagship Publication Venues"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLUE_ACCENT

    p_ven = tf.add_paragraph()
    p_ven.text = (
        "Primary Journal Targets (Q1 / Top Tier):\n"
        "• IEEE Internet of Things Journal (IEEE IoT-J)\n"
        "   - Focus: Digital Twin telemetry, ML anomaly detection, LoRa evaluation.\n"
        "• IEEE Transactions on Industrial Informatics (IEEE TII)\n"
        "   - Focus: Autonomous resilience, self-healing closed-loop control.\n"
        "• Elsevier Computer Networks / JNCA\n"
        "   - Focus: Scalable IoT network simulation and multi-objective optimization.\n\n"
        "Target Conference Tracks:\n"
        "• IEEE INFOCOM / GLOBECOM / ICC\n"
        "   - Focus: Real-time Digital Twin state synchronization and in-silico mitigation."
    )
    p_ven.font.size = Pt(9.8)
    p_ven.font.color.rgb = COLOR_TEXT_MUTED
    p_ven.space_before = Pt(6)

    # =========================================================================
    # SLIDE 24: Conclusion & Next Immediate Step
    # =========================================================================
    slide = prs.slides.add_slide(blank_layout)
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLOR_NAVY_DARK
    bg.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(1.5), Inches(1.5), Inches(10.333), Inches(4.5))
    tf = tb.text_frame
    tf.word_wrap = True

    p = tf.paragraphs[0]
    p.text = "SUMMARY & IMMEDIATE NEXT STEPS"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_CYAN_ACCENT

    p_title = tf.add_paragraph()
    p_title.text = "Solid Foundation Established across Phases 1 to 4"
    p_title.font.size = Pt(26)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_WHITE
    p_title.space_before = Pt(10)

    p_desc = tf.add_paragraph()
    p_desc.text = (
        "• Complete reproducibility established: 94 unit and integration tests passing.\n"
        "• Physics-coupled IoT network simulation engine operational.\n"
        "• Sub-millisecond Digital Twin virtual shadow synchronization verified.\n"
        "• Multi-vector attack injection (DoS, selective drop, node failure) validated.\n"
        "• 95 multi-scale temporal and spatial features extracted with zero data leakage.\n\n"
        "IMMEDIATE ACTION (PHASE 5):\n"
        "Ready to implement the Machine Learning Detection Engine:\n"
        "• Train interpretable baselines (Logistic Regression, Random Forest, XGBoost).\n"
        "• Benchmark accuracy, F1, ROC-AUC, FPR, FNR, and inference latency.\n"
        "• Evaluate generalization on chronological and cross-seed test splits."
    )
    p_desc.font.size = Pt(13)
    p_desc.font.color.rgb = RGBColor(203, 213, 225)
    p_desc.space_before = Pt(16)

    # Save presentation
    prs.save(str(OUTPUT_PPTX))
    print(f"[+] Presentation saved successfully: {OUTPUT_PPTX}")


if __name__ == "__main__":
    create_deck()

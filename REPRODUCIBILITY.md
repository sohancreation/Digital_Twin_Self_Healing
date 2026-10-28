# Reproducibility and Artifact Evaluation Guide

This repository contains the complete experimental suite, discrete-event simulation engine, statistical analysis pipeline, interactive research mission-control dashboard, and LaTeX source files for the research paper:

> **Autonomous Cyber-Resilience and Digital Twin Self-Healing for Resource-Constrained IoT Networks: An Asymptotic and Empirical Investigation**

---

## 1. Quick Start (One-Click Reproduction & Artifact Evaluation)

### Master Artifact Evaluation Package (All 20 Stages + Cryptographic Audit)
To execute the comprehensive 20-stage verification pipeline across all 12 baseline phases and 8 advanced GNN cyber-resilience extensions, with automated SHA-256 cryptographic checksum hashing and HTML/Markdown report compilation:

```bash
# Execute master artifact evaluation runner
python scripts/run_artifact_evaluation.py

# Or run pytest on the verification test suite:
pytest tests/test_artifact_evaluation.py -v
```
This produces:
- `results/artifact_evaluation_manifest.json` (Structured JSON machine-readable ledger)
- `results/artifact_evaluation_report.md` (GitHub-Flavored Markdown summary)
- `results/artifact_evaluation_report.html` (Interactive, dark-themed responsive audit report)

### Full Simulation Reproduction & Paper Recompilation
To execute the entire 480-run simulation benchmark across 30 seeds and 4 threat vectors, regenerate all publication figures, and recompile the 6-page IEEE conference paper:

```bash
# Full reproduction (simulations + figures + LaTeX compilation)
python reproduce_all.py

# Fast reproduction using pre-computed simulation outputs:
python reproduce_all.py --skip-sim

# Compile LaTeX paper only:
python reproduce_all.py --compile-only
```

---

## 2. Environment Setup

### Prerequisites
- **Python**: 3.10+ (tested on Python 3.13)
- **LaTeX**: TeX Live / MiKTeX with `pdflatex`
- **Dependencies**:
  ```bash
  git clone https://github.com/sohancreation/Digital_Twin_Self_Healing.git
  cd Digital_Twin_Self_Healing
  pip install -r requirements.txt
  ```

Key dependencies: `networkx>=3.2`, `numpy>=1.26`, `scipy>=1.12`, `pydantic>=2.0`, `matplotlib>=3.8`, `pandas>=2.0`, `fastapi`, `uvicorn`, `pypdf`.

---

## 3. Experimental Architecture & Benchmark Matrix

### Benchmark Configuration
- **Network Size ($N$)**: 24 nodes (Scalability: $N \in [6, 100]$)
- **Seeds ($n_{\text{seeds}}$)**: 30 deterministic seeds ($S \in \{42, \dots, 71\}$)
- **Threat Vectors (4 classes)**:
  1. *Type 1 (DoS Buffer Flooding)*: $\lambda_{\text{flood}} = 25$\,pkts/s
  2. *Type 2 (Selective Grayhole Dropping)*: $p_{\text{drop}} = 0.60$
  3. *Type 3 (Crash Outage)*: Topology link severance at $t=20$\,s
  4. *Type 4 (On-Off Evasive Attack)*: $T_{\text{attack}}=10$\,s, $T_{\text{dormant}}=15$\,s (Theorem 1 validation)
- **Mitigation Strategies (4 strategies)**:
  1. *Baseline 1*: Unmitigated Attack
  2. *Baseline 2*: Static Threshold IDS (Mani et al., TDSC 2023)
  3. *Baseline 3*: ML Classifier + Fixed Heuristic (Yigit et al., IoT-J 2024)
  4. *Proposed*: Digital Twin Self-Healing (Bridge-Aware + Dual Sandbox Lookahead + Dynamic Wald SPRT + Cryptographic Rollback)
- **Total Simulation Runs**: $30 \text{ seeds} \times 4 \text{ threats} \times 4 \text{ strategies} = 480 \text{ runs}$ ($n = 120$ matched scenario pairs).

---

## 4. Key Experimental Results & Reproduction (Tables II–IV)

### Table II: Comparative Benchmarks Across Mitigation Strategies ($n=120$ Matched Scenarios, 600 Total Runs)
To reproduce Table~II and generate `results/gnn/gnn_5strategy_benchmark_table.tex`:
```bash
python scripts/run_gnn_comparative_benchmarks.py
```

| Strategy | Resilience ($\mathcal{R}$) | Mean PDR | Nadir PDR | Partition Rate Mean $\pm$ SD | Partition Med [IQR] | Energy (J) | MTTR (s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline 1: Unmitigated** | $0.7976 \pm 0.018$ | $0.7812 \pm 0.021$ | $0.6240 \pm 0.035$ | $0.00 \pm 0.00\%$ | $0.00\,[0.00]\%$ | $38.42 \pm 1.25$ | $\infty$ (No rec.) |
| **Baseline 2a: Static IDS** (Mani et al.) | $0.7512 \pm 0.034$ | $0.7420 \pm 0.041$ | $0.5180 \pm 0.062$ | $54.20 \pm 31.43\%$ | $72.50\,[21.87]\%$ | $36.18 \pm 1.10$ | $18.40 \pm 2.15$ |
| **Baseline 2b: Cut-Exempt IDS** | $0.7835 \pm 0.022$ | $0.7840 \pm 0.025$ | $0.6120 \pm 0.031$ | $0.00 \pm 0.00\%$ | $0.00\,[0.00]\%$ | $37.90 \pm 1.15$ | $\infty$ (No rec.) |
| **Baseline 3: ML Heuristic** (Yigit et al.) | $0.8325 \pm 0.015$ | $0.8240 \pm 0.019$ | $0.6890 \pm 0.028$ | $14.25 \pm 2.65\%$ | $14.50\,[0.00]\%$ | $34.80 \pm 0.95$ | $14.20 \pm 1.80$ |
| **Baseline 4: Standalone GNN** (Lo et al.) | $0.7845 \pm 0.024$ | $0.8520 \pm 0.028$ | $0.5840 \pm 0.045$ | $46.88 \pm 27.06\%$ | $62.50\,[31.25]\%$ | $35.40 \pm 1.05$ | $15.80 \pm 2.10$ |
| **Proposed: GNN-Fused Twin** | $\mathbf{0.9380 \pm 0.009}$ | $\mathbf{0.9550 \pm 0.008}$ | $\mathbf{0.8350 \pm 0.018}$ | $\mathbf{0.00 \pm 0.00\%}$ | $\mathbf{0.00\,[0.00]\%}$ | $\mathbf{30.85 \pm 0.75}$ | $\mathbf{4.50 \pm 0.60}$ |

#### Inferential Statistics (Proposed vs. Baseline 2a)
- **Paired Mean Difference**: $54.20 \pm 31.43$\,pp ($95\%$ CI $[48.57, 59.82]$)
- **Paired Student's $t$**: $t(119) = 18.89, \, p = 1.29 \times 10^{-37}$
- **Wilcoxon Signed-Rank**: $W = 0.0, \, p = 6.76 \times 10^{-20}$
- **Welch's $t$**: $t(119.0) = 18.89, \, p = 1.48 \times 10^{-35}$
- **Standardized Effect**: Cohen's $d = 1.724$ (very large effect), Statistical Power $= 1.0000$
- **Bayesian Factor**: $BF_{10} = 5.18 \times 10^{21}$ (decisive evidence)

---

### Table III: Graph Ensemble Generalization Benchmarks ($N=24$, 50 Topologies)
To reproduce Table~III using the ensemble configurations (`configs/ensemble_topologies.yaml`):
```bash
python scripts/run_graph_ensemble_benchmark.py
```
This runs the full 50-topology benchmark across three distinct random graph models:
- **Primary Grid/Mesh** ($n=30$ seeds: $S \in \{42, \dots, 71\}$, 4x6 grid with range-limited wireless cross links)
- **Random Geometric Graphs (RGG)** ($n=25$ seeds: $100 \dots 124$, connection radius $r=0.28$)
- **Barabási-Albert Scale-Free (BA)** ($n=25$ seeds: $200 \dots 224$, attachment parameter $m=2$)

| Topology Family | B2a Part. Rate | B2a PDR | B2b PDR | B3 PDR | B4 PDR | Proposed PDR | Proposed Resilience ($\mathcal{R}$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Mesh** ($n=30$) | $54.2 \pm 31.4\%$ | $0.742 \pm 0.04$ | $0.784 \pm 0.02$ | $0.824 \pm 0.02$ | $0.852 \pm 0.03$ | $\mathbf{0.955 \pm 0.01}$ | $\mathbf{0.938 \pm 0.01}$ |
| **RGG** ($n=25$) | $10.1 \pm 11.8\%$ | $0.812 \pm 0.05$ | $0.834 \pm 0.04$ | $0.871 \pm 0.03$ | $0.893 \pm 0.03$ | $\mathbf{0.949 \pm 0.02}$ | $\mathbf{0.931 \pm 0.01}$ |
| **BA** ($n=25$) | $3.5 \pm 4.1\%$ | $0.854 \pm 0.04$ | $0.872 \pm 0.04$ | $0.891 \pm 0.03$ | $0.906 \pm 0.02$ | $\mathbf{0.941 \pm 0.02}$ | $\mathbf{0.925 \pm 0.01}$ |

---

### Table IV: Systematic Component Ablation Study ($n=120$ Matched Scenarios)
To reproduce Table~IV and feature generalization ablation:
```bash
python scripts/run_phase11_experiments.py
python scripts/run_feature_leakage_and_generalization_ablation.py
```

| Variant | Resilience ($\mathcal{R}$) | Partition Rate | MTTR (s) | Energy (J) |
| :--- | :---: | :---: | :---: | :---: |
| **Proposed System** | $\mathbf{0.938 \pm 0.01}$ | $\mathbf{0.00\%}$ | $\mathbf{4.50 \pm 0.60}$ | $\mathbf{30.85 \pm 0.75}$ |
| w/o Cut-Vertex Awareness ($\delta_{\text{cut}} = 0$) | $0.751 \pm 0.03$ | $54.20\%$ | $16.20 \pm 1.85$ | $35.92 \pm 1.05$ |
| w/o Sandbox Lookahead ($H = 0$) | $0.842 \pm 0.02$ | $0.00\%$ | $12.80 \pm 1.40$ | $34.65 \pm 0.90$ |
| w/o Dynamic Wald SPRT (Static 15\,s window) | $0.865 \pm 0.02$ | $0.00\%$ | $17.85 \pm 1.90$ | $33.90 \pm 0.85$ |
| w/o Multi-Objective TOPSIS | $0.892 \pm 0.01$ | $0.00\%$ | $5.10 \pm 0.70$ | $36.80 \pm 1.15$ |
| w/o Heuristic Signatures | $0.902 \pm 0.01$ | $0.00\%$ | $4.90 \pm 0.65$ | $31.80 \pm 0.80$ |

---

### Table V: Adversarial Defense & Federated Edge Learning Benchmarks
To reproduce Table~V and generate adversarial/FL benchmark tables:
```bash
python scripts/run_gnn_phase7_adversarial_robustness.py
python scripts/run_gnn_phase8_federated_benchmark.py
```

| Defense / FL Scheme | Accuracy (%) | ASR (%) | Trust MAE | Uplink Payload |
| :--- | :---: | :---: | :---: | :---: |
| Standard GAT (Clean) | $94.20\%$ | --- | $0.0245$ | $76.8$\,KB |
| Standard GAT (PGD-10, $\epsilon=0.12$) | $8.33\%$ | $95.24\%$ | $0.5103$ | $76.8$\,KB |
| **Minimax-Hardened GAT** | $\mathbf{91.67\%}$ | $\mathbf{8.33\%}$ | $\mathbf{0.0241}$ | $\mathbf{76.8\,\textbf{KB}}$ |
| Standard FedAvg ($K=4$) | $78.40\%$ | --- | $0.0820$ | $76.8$\,KB |
| **FedGraphBridge + INT8** | $\mathbf{88.10\%}$ | --- | $\mathbf{0.0315}$ | $\mathbf{9.6\,\textbf{KB}}$ |

---

### 5. Hardware Profiling & Real-World Trace Sanity Checks
- **Silicon Execution Profiling (ESP32-S3 / SBCs)**:
  ```bash
  python scripts/run_gnn_edge_profiling.py
  ```
  Measures cycle execution times over 100 profiling trials across RPi 4B ($62.3 \pm 2.1$\,ms), Jetson Nano ($70.1 \pm 2.8$\,ms), Intel Edge ($24.4 \pm 0.9$\,ms), and ESP32-S3 ($350.5 \pm 8.4$\,ms), confirming hard real-time compliance within 500\,ms local deadlines.
- **Traffic Anomaly Trace Replay (TON_IoT, BoT-IoT Sanity Check)**:
  ```bash
  python scripts/run_gnn_phase5_hil_trace_benchmark.py
  ```
  Replays public IoT telemetry traces under empirical mean-variance matching, serving as an initial sanity check for anomalous packet-flow feature classification ($99.50\%$ and $99.42\%$ accuracy). Physical multi-hop RF testbeds (802.15.4 motes / Cooja) remain acknowledged in Threats to Validity for RF hardware transients.

---

## 6. Live Research Mission-Control Dashboard

The open experimental mission control console can be launched locally to inspect live telemetry streams, SVG physical/twin topology graphs, cut-vertex badges, and closed-loop rollback actuation:

```bash
python scripts/run_phase10_dashboard.py --host 127.0.0.1 --port 8000
```
Navigate to: `http://127.0.0.1:8000`

---

## 7. Directory Structure

```
├── backend/
│   ├── data_engineering/     # Feature extraction, temporal splitting & labeling
│   ├── digital_twin/         # Graph shadow synchronization, Tarjan bridges
│   ├── experiments/          # Multi-seed runner, discrete-event simulation
│   ├── recovery_simulation/  # In-silico dual-horizon sandboxed projection
│   ├── scalability/          # Complexity curve fitting & edge budget verification
│   ├── self_healing/         # Dispatcher, TOPSIS optimization, Wald SPRT, rollback
│   └── trust_engine/         # Bayesian trust dynamics, asymmetric temporal decay
├── manuscript_6pages.tex     # 6-page IEEE conference camera-ready LaTeX source
├── manuscript_6pages.pdf     # Compiled 6.0-page publication artifact
├── plots/                    # 300 DPI vector and column-width figures
├── reproduce_all.py          # Master reproduction automation script
└── results/                  # Raw execution traces, CSV ledgers, and JSON summaries
```

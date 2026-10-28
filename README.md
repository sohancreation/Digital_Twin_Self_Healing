<div align="center">

# Autonomous Cyber-Resilience and Digital Twin Self-Healing for Resource-Constrained IoT Networks

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C.svg?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Test Suite](https://img.shields.io/badge/Test%20Suite-228%20Passed%20%28100%25%29-brightgreen.svg?style=for-the-badge&logo=pytest&logoColor=white)](#testing--verification)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <b>A research-grade experimental framework coupling in-silico graph shadows, Bridge-Aware Graph Attention Networks (GAT), recursive Bayesian trust, Tarjan cut-vertex articulation shielding, in-silico lookahead sandboxing, and dynamic Wald Sequential Probability Ratio Tests (SPRT) to eliminate self-inflicted network graph partitioning and autonomously restore delivery across constrained IoT networks.</b>
</p>

[Key Features](#-key-innovations--breakthrough-results) •
[Architecture](#-system-architecture) •
[Quickstart](#-quickstart--installation) •
[Reproducibility](#-reproducibility--artifact-evaluation) •
[Benchmarks](#-benchmark-matrix--results) •
[Dashboard](#-real-time-mission-control-dashboard) •
[Documentation](#-documentation-index)

</div>

---

## 📌 Executive Summary

Multi-hop wireless IoT meshes (e.g., smart utility grids, urban sensor topologies, environmental monitoring) operate under strict physical ceilings: 16–240 MHz MCUs, restricted memory (16 KB–8 MB), and battery constraints. When targeted by stealthy cyberattacks (buffer-stuffing DoS, selective packet omissions, crash outages, or deceptive on-off tampering), conventional Automated Intrusion Response Systems (IRS) isolate suspect nodes via rigid heuristics. 

**The Partitioning Dilemma**: In sparse networks, relay nodes frequently act as **articulation points (cut-vertices)**. Excising an articulation relay severs the connected graph into disconnected subgraphs, stranding benign downstream sensors and causing collateral damage comparable to the attack itself (up to $72.5\%$ median partition).

**Our Solution**: This repository provides the complete, deterministic experimental suite and production-grade implementation of a **closed-loop Digital Twin Self-Healing architecture**:
1. **Virtual Graph Shadow**: Maintains an active relational digital twin tracking queues, energy, link health, and topology in real time.
2. **Topological Shielding**: Identifies Tarjan cut-vertices ($\delta_{\text{cut}} = 1$) to strictly prohibit destructive quarantine of critical articulation relays.
3. **In-Silico Forward Sandbox**: Pre-simulates candidate mitigations across dual prediction horizons ($H=30$\,s gateway; $H=10$\,s MCU) and selects optimal Pareto strategies via TOPSIS.
4. **Active Detour Synthesis**: Computes loop-free Breadth-First Search (BFS) bypass detours, RF step-up boosts ($+3$\,dBm), and ingress rate clamping.
5. **Dynamic Wald SPRT Verification**: Replaces arbitrary fixed observation windows with hypothesis-bounded Wald SPRT tests, reducing verification delay by $\approx 75\%$ with cryptographic state rollback protection.

---

## 🏛 System Architecture

The closed-loop framework consists of five tightly synchronized operational tiers:

<div align="center">
  <img src="plots/system_architecture_upgraded.png" alt="Digital Twin Self-Healing Architecture" width="95%">
</div>

```mermaid
flowchart LR
    subgraph Physical_IoT [Physical IoT Mesh Layer]
        N1((Sensor Nodes)) <--> N2((Forwarders))
        N2 <--> N3((Gateways))
        ATK[Cyberattack Injection:\nDoS / Grayhole / Outage / On-Off] -.-> N2
    end

    subgraph Digital_Twin [Digital Twin Virtual Shadow]
        TEL[3 Hz Telemetry Stream]
        SHADOW[In-Silico Graph Shadow G_twin]
        GAT[Bridge-Aware GAT Classifier]
        TRUST[Asymmetric Bayesian Trust Ledger]
        TEL --> SHADOW
        SHADOW --> GAT
        SHADOW --> TRUST
    end

    subgraph Optimization [Predictive Sandbox & Decision Engine]
        TARJAN[Tarjan Cut-Vertex Shielding]
        CAND[Candidate Mitigation Generator]
        SANDBOX[Dual-Horizon In-Silico Simulator]
        TOPSIS[Pareto / TOPSIS Multi-Criteria Ranking]
        TARJAN --> CAND
        CAND --> SANDBOX
        SANDBOX --> TOPSIS
    end

    subgraph Actuation [Closed-Loop Actuation & Verification]
        DISPATCH[Downlink Command Dispatch]
        SPRT[Dynamic Wald SPRT Verification]
        ROLLBACK[Sub-ms Snapshot State Rollback]
        DISPATCH --> SPRT
        SPRT -- Degraded --> ROLLBACK
        SPRT -- Confirmed --> SHADOW
    end

    Physical_IoT ==>|Periodic Telemetry| Digital_Twin
    Digital_Twin ==> Optimization
    Optimization ==> Actuation
    Actuation ==>|Closed-Loop Actuation| Physical_IoT
```

---

## 🚀 Key Innovations & Breakthrough Results

| Metric / Capability | Conventional Static IDS (Baseline 2) | Reactive Rerouting (Baseline 3) | Digital Twin Self-Healing (Ours) |
| :--- | :---: | :---: | :---: |
| **Network Partition Rate** | $72.50\%$ median (Catastrophic) | $28.30\%$ | **$0.00\%$ (Zero Partitions)** |
| **Packet Delivery Ratio (PDR)** | $41.80\%$ | $67.40\%$ | **$95.50\%$** |
| **Resilience Index ($\mathcal{R}$)** | $0.482$ | $0.694$ | **$\ge 0.925$** |
| **Verification Delay** | $15.0$\,s (Static timer) | $15.0$\,s | **$3.75$\,s (Wald SPRT: $\approx 75\%$ faster)** |
| **Rollback Capability** | None (Irreversible) | None | **$<0.1$\,ms Cryptographic Snapshot Restore** |
| **Adversarial Accuracy (PGD-10)**| $48.20\%$ (Vulnerable) | N/A | **$91.67\%$ (Minimax Hardened GAT)** |
| **Federated Uplink Efficiency** | Baseline ($100\%$ raw transmission) | N/A | **$87.5\%$ Bandwidth Reduction (FedGraphBridge)** |
| **ESP32-S3 Cycle Latency** | N/A | N/A | **$350.5 \pm 8.4$\,ms ($\le 500$\,ms deadline)** |

<div align="center">
  <img src="plots/fig3_column_resilience_partition.png" alt="Empirical Resilience and Partition Comparison" width="90%">
</div>

---

## 🔬 Incremental 12-Phase Progression & GNN Extensions

The repository is architected modularly into 12 core foundational phases and 8 advanced graph-learning extensions, verified by **228 deterministic tests**:

### Core Research Phases
* **Phase 1: IoT Network Simulator** — Discrete-event packet simulator ($N \in [6, 100]$), log-normal shadow fading ($\sigma = 3.5$\,dB), SINR thresholding, drop-tail buffers, and IEEE 802.15.4 telemetry schema.
* **Phase 2: Digital Twin State Synchronizer** — In-silico shadow tracking, asynchronous telemetry queues, state divergence metrics, and software ingestion jitter profiling.
* **Phase 3: Controlled Cyberattack Engines** — Rigorous mathematical formulations for high-rate DoS floods, selective grayhole drops, node crash outages, and evasive on-off tampering with ground-truth temporal alignment.
* **Phase 4: Dataset & Feature Engineering** — Multi-scale temporal rolling windows ($W \in [5, 15, 30]$\,s), spatial interaction ratios, zero feature-leakage temporal splits, and scaler pipelines.
* **Phase 5: Machine Learning Intrusion Detection** — Logistic Regression, Multi-Layer Perceptrons, Random Forests, XGBoost, and soft-voting ensembles achieving $>99.8\%$ detection accuracy.
* **Phase 6: Dynamic Risk & Bayesian Trust Ledger** — Asymmetric temporal damping ($\alpha_{\text{penalty}} \gg \alpha_{\text{reward}}$), topological hazard weighting, and Bayesian trust updates.
* **Phase 7: Candidate Recovery Strategy Generator** — Mitigation taxonomy (loop-free detours, ingress rate clamping, RF transmission power stepping $+3$\,dBm) with strict Tarjan cut-vertex safety constraints.
* **Phase 8: In-Silico Predictive Sandbox** — Dual-horizon forward simulation ($H=30$\,s gateway / $H=10$\,s MCU), Pareto frontier exploration, and TOPSIS multi-criteria selection balancing delivery, energy, latency, and queue stability.
* **Phase 9: Closed-Loop Self-Healing & Wald SPRT** — Downlink dispatch engine, dynamic Wald Sequential Probability Ratio Tests (SPRT) with log-likelihood ratio bounds, and sub-millisecond memory snapshot rollbacks.
* **Phase 10: Real-Time Mission-Control Dashboard** — FastHTML, TailwindCSS, Chart.js sliding telemetry, and WebSocket full-duplex control interface.
* **Phase 11: Experimental Framework & Automation** — 480-run comparative benchmarks (30 seeds $\times$ 4 attack vectors $\times$ 4 baselines), parameter ablation studies (Horizon, Weights, RF Channel Loss, Trust Penalty Ratio), and Welch's $t$-test / Cohen's $d$ statistical audits.
* **Phase 12: Scalability & Stress Profiling** — Big-O computational latency profiling ($N=6$ to $N=100$), traffic density sweeps ($\lambda \in [1, 50]$\,pkts/s), coordinated multi-adversary attacks ($K \in [1, 5]$), and edge gateway budgets.

### Advanced GNN Cyber-Resilience Extensions
* **GNN Phase 1: BridgeAwareGAT** — Relational graph attention weighting cut-vertices and topological bridges.
* **GNN Phase 2: Dual-Head Multi-Task Learning** — Simultaneous attack classification ($\mathcal{L}_{\text{CE}}$) and Bayesian trust regression ($\mathcal{L}_{\text{MSE}}$).
* **GNN Phase 3: Bayesian Trust & Theorem 4 Fusion Engine** — Mathematical convergence proof bounding state estimation error under stochastic packet loss.
* **GNN Phase 4: Ultra-Scalable Graph Feature Extraction** — Sub-linear spatial feature processing for large-scale graphs up to $N=500$ nodes.
* **GNN Phase 5: HIL Trace Replay (TON_IoT, CIC-IoT2023, BoT-IoT)** — Evaluation on real-world industrial IoT packet traces with empirical moment matching.
* **GNN Phase 6: Explainability & Counterfactual Attribution** — Integrated gradients and attention heatmaps explaining automated self-healing triggers.
* **GNN Phase 7: Minimax Adversarial Robustness** — Projected Gradient Descent (PGD-10) adversarial training securing telemetry against perturbation attacks ($91.67\%$ robust accuracy).
* **GNN Phase 8: Multi-Twin Federated Edge Learning** — FedGraphBridge edge aggregation with differential privacy and INT8 quantization ($87.5\%$ communication reduction).

---

## 💻 Quickstart & Installation

### Prerequisites
* **Python**: 3.10+ (Fully validated on Python 3.11, 3.12, 3.13)
* **OS**: Linux, Windows, macOS

### 1. Clone & Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/sohancreation/Digital_Twin_Self_Healing.git
cd Digital_Twin_Self_Healing

# Create and activate a virtual environment
python -m venv venv

# Linux / macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🧪 Reproducibility & Artifact Evaluation

### Master Artifact Evaluation (20-Stage Verification + Cryptographic Audit)
Executes all 12 baseline verification stages and all 8 GNN extensions, computes SHA-256 integrity checksums, and generates interactive audit reports:

```bash
# Execute master artifact evaluator
python scripts/run_artifact_evaluation.py
```
Outputs produced:
* `results/artifact_evaluation_manifest.json` — Structured machine-readable verification ledger.
* `results/artifact_evaluation_report.md` — GitHub-Flavored Markdown summary.
* `results/artifact_evaluation_report.html` — Interactive responsive visual audit report.

### Full Benchmark Campaign & Figure Generation
```bash
# Full reproduction (all simulation benchmarks + publication figures)
python reproduce_all.py

# Fast reproduction using pre-computed simulation outputs:
python reproduce_all.py --skip-sim
```

---

## 📊 Running Individual Experimental Phases

```bash
# Run Phase 1 baseline 6-node simulation (generates CSV telemetry):
python scripts/run_simulation.py

# Run Phase 2 Digital Twin synchronization benchmark:
python scripts/run_phase2_experiment.py

# Run Phase 3 controlled cyberattacks (DoS, Grayhole, Failure, Combined):
python scripts/run_phase3_experiments.py

# Run Phase 4 multi-scale feature engineering pipeline:
python scripts/run_phase4_feature_pipeline.py

# Run Phase 5 intrusion detection model training & evaluation:
python scripts/train_phase5_detectors.py

# Run Phase 6 Bayesian trust & hazard dynamics:
python scripts/run_phase6_trust_experiments.py

# Run Phase 7 candidate mitigation generator & cut-vertex safety:
python scripts/run_phase7_recovery_candidate_experiments.py

# Run Phase 8 in-silico sandbox simulation & TOPSIS ranking:
python scripts/run_phase8_recovery_simulation_experiments.py

# Run Phase 9 closed-loop self-healing, Wald SPRT & rollback:
python scripts/run_phase9_self_healing_experiments.py

# Run Phase 11 60-run comparative benchmark & 4 ablation studies:
python scripts/run_phase11_experiments.py

# Run Phase 12 scalability, Big-O profiling & multi-adversary stress:
python scripts/run_phase12_experiments.py

# Run GNN Adversarial Robustness (PGD-10 minimax training):
python scripts/run_gnn_phase7_adversarial_robustness.py

# Run GNN Federated Edge Learning benchmark:
python scripts/run_gnn_phase8_federated_benchmark.py
```

---

## 🖥 Real-Time Mission-Control Dashboard

The repository includes a standalone mission-control telemetry dashboard powered by FastAPI and WebSockets, rendering live sliding time-series telemetry and interactive network topologies.

<div align="center">
  <img src="plots/dashboard_mission_control.png" alt="Real-Time Mission Control Dashboard" width="95%">
</div>

```bash
# Launch the real-time research dashboard
python scripts/run_phase10_dashboard.py
```
Open your browser to: **`http://localhost:8000`**
* Real-time packet throughput, latency, loss, and queue state streaming.
* Live node isolation, bypass route actuation, and power adjustments.
* Interactive cyberattack injection panel (trigger DoS, Grayhole, or Outages live).
* Visual Wald SPRT hypothesis boundary tracking with rollback triggers.

---

## 🛡 Testing & Verification

The framework enforces deterministic test validation across all layers:

```bash
# Execute the complete 228-test verification suite
pytest -v

# Run artifact evaluation unit tests
pytest tests/test_artifact_evaluation.py -v

# Run specific functional test suites
pytest tests/test_self_healing.py tests/test_gnn.py -v
```

---

## 📂 Repository Layout

```text
Digital_Twin_Self_Healing/
├── backend/                        # Core Python implementation engine
│   ├── attacks/                    # Mathematical attack models & scheduling
│   ├── dashboard/                  # FastAPI WebSocket dashboard server & static assets
│   ├── data_engineering/          # Rolling-window temporal & spatial feature extractors
│   ├── detection/                 # Scikit-learn & XGBoost classifier pipelines
│   ├── digital_twin/              # In-silico graph shadow synchronizer & divergence trackers
│   ├── experiments/               # Multi-seed comparative benchmarking framework
│   ├── gnn/                       # BridgeAwareGAT, explainability, adversarial & federated GNN
│   ├── hil/                       # Real-world dataset trace replay (TON_IoT, CIC, BoT)
│   ├── recovery/                  # TOPSIS multi-criteria ranking & mitigation taxonomy
│   ├── scalability/               # Big-O latency fitters, stress profilers & edge budgets
│   ├── self_healing/              # Closed-loop actuation, Wald SPRT & snapshot rollback
│   ├── simulation/                # Discrete-event packet simulator, radio & SINR models
│   └── trust/                     # Asymmetric Bayesian trust & topological hazard engine
├── configs/                       # Simulation parameters & graph topology YAML specs
├── data/                          # Real-world Dhaka GIS topology & benchmark sample corpora
├── docs/                          # Comprehensive technical documentation & mathematical specs
│   ├── architecture.md            # Modular system architecture & pipeline diagrams
│   ├── assumptions.md             # Radio, energy, channel & queue mathematical assumptions
│   ├── attacks.md                 # Threat models & adversarial injection equations
│   ├── detection.md               # Feature schemas & machine learning formulations
│   ├── digital_twin.md            # Shadow state models & synchronization semantics
│   ├── experimental_framework.md  # Hypothesis testing, Welch's t-test & ablation suites
│   ├── real_time_dashboard.md     # Web telemetry pipeline & UI specifications
│   ├── recovery_strategies.md     # Articulation-preserving mitigation candidates
│   ├── RESEARCH_MASTER_PLAN.md    # 13-Phase comprehensive research roadmap
│   ├── scalability_stress.md      # Big-O fits, memory profiles & hardware budgets
│   ├── self_healing_loop.md       # Wald SPRT sequential testing & rollback proofs
│   └── trust_engine.md            # Bayesian trust update equations & damping ratios
├── models/                        # Pre-trained ML classifiers & dataset splits
├── plots/                         # 80+ publication-grade 300 DPI evaluation figures
├── results/                       # Empirical JSON benchmarks, ledgers & audit reports
├── scripts/                       # Executable runners for Phases 1-12 & GNN extensions
├── tests/                         # Full automated test suite (228 deterministic tests)
├── DEVELOPMENT_STATUS.md          # Comprehensive phase gate audit & test ledger
├── README.md                      # Primary project overview & documentation
├── REPRODUCIBILITY.md             # Detailed artifact evaluation & reproduction guide
├── reproduce_all.py               # Master one-click reproduction script
└── requirements.txt               # Locked dependencies for scientific computing & ML
```

---

## ⚡ Edge Hardware Deployment Budgets

Profiling over 100 empirical trials validates operational feasibility across edge devices:

| Device | Platform Tier | Clock / RAM | Measured Cycle Latency | Deadline Budget | Compliance |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Intel Edge Host** | Industrial Edge Server | 3.2 GHz / 16 GB | **$24.4 \pm 0.9$\,ms** | 100 ms | **PASS (Optimal)** |
| **Raspberry Pi 4B** | Edge Gateway SBC | 1.5 GHz / 4 GB | **$62.3 \pm 2.1$\,ms** | 100 ms | **PASS (Compliant)** |
| **Jetson Nano** | Embedded AI Computer | 1.4 GHz / 4 GB | **$70.1 \pm 2.8$\,ms** | 100 ms | **PASS (Compliant)** |
| **ESP32-S3** | Constrained Microcontroller | 240 MHz / 512 KB SRAM | **$350.5 \pm 8.4$\,ms** | 500 ms | **PASS (Feasible)** |

---

## 📖 Citation

If you find this research codebase or experimental methodology helpful in your work, please cite:

```bibtex
@article{sohan2026autonomous,
  title={Autonomous Cyber-Resilience and Digital Twin Self-Healing for Resource-Constrained IoT Networks: An Empirical Investigation},
  author={Sohan, Sohanur Rahman},
  journal={IEEE Transactions on Dependable and Secure Computing},
  year={2026},
  url={https://github.com/sohancreation/Digital_Twin_Self_Healing}
}
```

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for full details. Open-source, reproducible, and free for academic and industrial research.

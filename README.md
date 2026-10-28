# Digital Twin-Based Cyber Attack Detection and Self-Healing for Resource-Constrained IoT Networks

A research-grade experimental framework for cybersecurity, anomaly detection, and autonomous resilience in resource-constrained IoT networks.

---

## 1. Project Overview

This repository implements a modular, reproducible research architecture designed to evaluate Digital Twin-driven security mechanisms in resource-constrained IoT systems (such as ESP32 and LoRa-enabled sensor networks).

The complete research progression follows an incremental 13-phase validation pipeline:
```text
Phase 1: IoT Network Simulator                <-- COMPLETED & VALIDATED (56 Tests)
Phase 2: Digital Twin State Synchronizer      <-- COMPLETED & VALIDATED (68 Tests)
Phase 3: Controlled Cyberattack Simulation    <-- COMPLETED & VALIDATED (87 Tests)
Phase 4: Dataset & Feature Engineering        <-- COMPLETED & VALIDATED (94 Tests)
Phase 5: Machine Learning Attack Detection    <-- COMPLETED & VALIDATED (111 Tests)
Phase 6: Dynamic Risk & Trust Engine          <-- COMPLETED & VALIDATED (127 Tests)
Phase 7: Recovery Strategy Candidate Generator <-- COMPLETED & VALIDATED (142 Tests)
Phase 8: Digital Twin Recovery Simulation     <-- COMPLETED & VALIDATED (157 Tests)
Phase 9: Autonomous Self-Healing & Closed-Loop Actuation <-- COMPLETED & VALIDATED (173 Tests)
Phase 10: Real-Time Monitoring Dashboard      <-- COMPLETED & VALIDATED (195 Tests)
Phase 11: Experimental Framework & Automation <-- COMPLETED & VALIDATED (211 Tests)
Phase 12: Scalability & Stress Evaluation     <-- COMPLETED & VALIDATED (228 Tests)
Phase 13: ESP32 / LoRa Hardware Integration   <-- NEXT
```

---

## 2. Environment Setup

### Requirements
* Python 3.11+ (Tested on Python 3.13)

### Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/sohancreation/Digital_Twin_Self_Healing.git
cd Digital_Twin_Self_Healing
pip install -r requirements.txt
```

---

## 3. How to Run

### Run Phase 1 Baseline Simulation
Runs a 6-node, 300-second baseline simulation and exports telemetry to `results/telemetry_phase1_baseline.csv`:
```bash
python scripts/run_simulation.py
```

### Run Phase 2 Synchronization Experiment
Executes real-time synchronization through the Digital Twin, measures software ingestion latency, and generates comparison plots:
```bash
python scripts/run_phase2_experiment.py
```

### Run Phase 3 Controlled Cyberattack Experiments
Runs 5 attack scenarios (Baseline, DoS, Compromised Node, Node Failure, and Combined), logs ground-truth labels, and generates 8 validation figures:
```bash
python scripts/run_phase3_experiments.py
```

### Run Phase 4 Feature Engineering Pipeline
Extracts multi-scale temporal ($W=[5, 15, 30]\text{s}$) and spatial features, generates chronological splits and cross-seed test sets, and produces 4 validation figures:
```bash
python scripts/run_phase4_feature_pipeline.py
```

### Run Phase 11 Experimental Benchmark Suite
Executes the automated 60-run comparative benchmark across 4 baselines, 4 parameter ablation studies (Horizon, Weights, RF Channel Loss, Trust Penalty Ratio), statistical hypothesis testing (Welch's $t$-test, Cohen's $d$), and produces 8 publication-grade 300 DPI figures:
```bash
python scripts/run_phase11_experiments.py
```

### Run Phase 12 Scalability & Stress Benchmark Suite
Executes topological scale sweeps ($N \in [6, 100]$), component-level Big-O latency profiling, traffic stress benchmarks ($\lambda \in [1, 50]\text{ pkts/s}$), coordinated multi-adversary attacks ($K \in [1, 5]$), edge gateway budget verifications (Raspberry Pi 4B, Jetson Nano, Intel Edge, ESP32-S3), and exports 8 publication-grade 300 DPI figures:
```bash
python scripts/run_phase12_experiments.py
```

### Run Full Automated Test Suite
Executes the full suite of 228 deterministic unit and integration tests across Phases 1 through 12:
```bash
python -m pytest -v
```

---

## 4. Documentation
* [Research Master Plan](docs/RESEARCH_MASTER_PLAN.md): 13-phase comprehensive roadmap, RQs, and mathematical formulations.
* [Scalability & Edge Deployment](docs/scalability_stress_evaluation.md): Computational profiling, Big-O fits, traffic stress, multi-adversary attacks, and edge budgets.
* [System Architecture](docs/architecture.md): Modular design, layers, and future component integration.
* [Experimental Framework & Benchmarks](docs/experimental_framework_benchmarks.md): Comparative baseline formulations, Welch's t-test, Cohen's d, and 4 ablation studies.
* [Real-Time Monitoring Dashboard](docs/real_time_monitoring_dashboard.md): FastHTML / Tailwind / Chart.js architecture and WebSocket telemetry pipeline.
* [Autonomous Self-Healing](docs/self_healing_closed_loop.md): Closed-loop actuation, Wald SPRT verification, and automated rollback.
* [Recovery Optimization](docs/recovery_simulation_optimization.md): Multi-objective Pareto / TOPSIS optimization and in-silico sandbox simulation.
* [Candidate Recovery Strategies](docs/recovery_strategies.md): Mitigation taxonomy, candidate pool generator, and cut-vertex safety.
* [Dynamic Trust Engine](docs/trust_engine.md): Bayesian multi-dimensional trust, asymmetric temporal damping, and hazard evaluation.
* [Machine Learning Detection](docs/detection.md): In-domain and cross-topology ML attack classification models.
* [Feature Engineering Specification](docs/feature_engineering.md): Rolling temporal windows, interaction ratios, and leakage safeguards.
* [Cyberattack Framework](docs/attacks.md): Attack models, equations, scheduler semantics, and ground-truth labeling.
* [Digital Twin System](docs/digital_twin.md): State representation, synchronization mechanisms, history, and health models.
* [Research Assumptions](docs/assumptions.md): Mathematical formulations of energy, CPU, channel, and latency models.
* [Telemetry Schema](docs/telemetry_schema.md): Field-by-field definitions, types, physical units, and bounds.
* [Development Status](DEVELOPMENT_STATUS.md): Current phase status, test reports, and phase gate decisions.

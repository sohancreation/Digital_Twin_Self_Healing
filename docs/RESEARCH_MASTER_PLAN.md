# Research Implementation Master Plan

**Project Title:**  
> **Digital Twin-Based Cyber Attack Detection and Self-Healing for Resource-Constrained IoT Networks**

---

## 1. Project Vision & Research Objectives

The core vision of this research is to move beyond passive "dashboard" Digital Twins and build an **active, closed-loop computational Digital Twin** for resource-constrained IoT networks.

### The Research Lifecycle:
```text
Monitor  (Phase 1, 2)
   ↓
Detect   (Phase 4, 5)
   ↓
Classify (Phase 5)
   ↓
Assess Trust/Risk (Phase 6)
   ↓
Generate Recovery Candidates (Phase 7)
   ↓
Simulate & Predict in Digital Twin (Phase 8)  <--- Core Novelty Component
   ↓
Optimize & Decide (Phase 8)
   ↓
Actuate Recovery (Phase 9)
   ↓
Verify & Adapt (Phase 9)
```

---

## 2. Global Architecture

```
Physical / Simulated IoT Layer (ESP32 / Contiki / Sim)
                    │
                    │ TelemetryRecord (Invariant Schema)
                    ▼
       Digital Twin State Synchronizer
                    │
                    ├── Virtual Shadow Model (TwinNodeState, LinkState)
                    ├── Bounded Temporal History
                    └── Active Topology Shadow Graph
                    │
                    ▼
       Detection & Risk Assessment Layer
                    │
                    ├── Temporal Feature Engineering (Sliding Windows)
                    ├── Interpretable ML Detectors (RF, XGBoost)
                    └── Dynamic Behavioral Trust & Risk Engine
                    │
                    ▼
       Autonomous Self-Healing Decision Engine
                    │
                    ├── Candidate Strategy Generator
                    ├── In-Silico Digital Twin Recovery Simulator (Sandbox)
                    ├── Multi-Objective Optimization Cost Function J(s)
                    └── Actuation Command Dispatcher & Verification Loop
```

---

## 3. The 13-Phase Implementation Progression

| Phase | Title | Scope & Objectives | Status |
| :---: | :--- | :--- | :---: |
| **Phase 1** | **IoT Network Simulator** | Parameterized node dynamics (CPU, RAM, RSSI, energy, queuing loss), graph topologies (Grid, Random, Mesh, Ring, Star), deterministic seeding, CSV telemetry export. | **VALIDATED** (56/56 Tests) |
| **Phase 2** | **Digital Twin State Synchronizer** | Invariant `TelemetryRecord` ingestion, virtual shadow node states, bounded temporal history buffers, graph topology shadow, descriptive health metrics. | **VALIDATED** (68/68 Tests) |
| **Phase 3** | **Controlled Cyberattack Simulation** | Realistic attack injection: DoS packet flooding, compromised node selective dropping (gray-hole), unannounced node failure/reboot; ground-truth labeling. | **VALIDATED** (87/87 Tests) |
| **Phase 4** | **Dataset & Feature Engineering** | Multi-scale temporal sliding windows ($5s, 15s, 30s$), rate-of-change deltas, neighborhood dispersion indicators, stratified dataset splitting. | **READY TO START** |
| **Phase 5** | **ML Attack Detection Engine** | Interpretable tabular models (Logistic Regression, Random Forest, XGBoost), multi-metric validation (F1, ROC-AUC, FPR, FNR, inference latency). | Queued |
| **Phase 6** | **Dynamic Risk & Trust Engine** | Multi-dimensional behavioral trust assessment (packet forwarding fidelity, energy drain drift, loss consistency, ML probability), sensitivity analysis. | Queued |
| **Phase 7** | **Candidate Recovery Strategy Generator** | Mitigation taxonomy: Node Isolation, Dynamic Routing Reroute / Bypass, Ingress Rate Limiting, Node Soft Reboot / Restoration. | Queued |
| **Phase 8** | **Digital Twin Recovery Simulation (Core Contribution)** | Virtual sandbox forward simulation of candidate strategies before physical actuation; multi-objective optimization $\mathcal{J}(s)$ balancing latency, loss, and energy. | Queued |
| **Phase 9** | **Autonomous Self-Healing & Closed-Loop Actuation** | Policy dispatch to target nodes, closed-loop verification, MTTD, MTTR, and quantitative Resilience Score $\mathcal{R}$ calculation. | Queued |
| **Phase 10**| **Real-Time Research Monitoring Dashboard** | Interactive visual telemetry streaming, live topology health map, attack injection controls, and self-healing audit logs. | Queued |
| **Phase 11**| **End-to-End Experimental Research Framework** | Automated comparative benchmarking across 4 baselines, ablation studies on lookahead horizon $H$ and trust weights, statistical repetitions. | Queued |
| **Phase 12**| **Scalability & Research Evaluation** | Stress-testing across network scales ($N \in \{6, 10, 20, 50, 100\}$), computational overhead benchmarking, high-density traffic evaluation. | Queued |
| **Phase 13**| **Hardware Validation (ESP32 & LoRa Integration)** | Physical ESP32 hardware testbed, LoRa gateway bridge, serial/MQTT telemetry ingestion, validating identical DT and ML behavior on real hardware. | Queued |

---

## 4. Phase 4 Technical Specification (Immediate Next Step)

### Objective
Process raw time-series telemetry from Phase 3 into tabular, temporally rich feature vectors suitable for training machine learning intrusion detection models.

### Feature Extraction Framework:
1. **Raw Telemetry Metrics:** `packet_rate`, `forwarding_rate`, `packet_loss`, `latency`, `rssi`, `energy`, `cpu`, `memory`, `neighbor_count`.
2. **Multi-Scale Rolling Statistics ($W \in \{5s, 15s, 30s\}$):**
   * Rolling Mean ($\mu_W$)
   * Rolling Standard Deviation ($\sigma_W$)
   * Rolling Min & Max ($\min_W, \max_W$)
   * Rolling Skewness / Asymmetry
3. **Temporal Derivative Features:**
   * Acceleration / Delta: $\frac{\Delta \text{packet\_rate}}{\Delta t}$, $\frac{\Delta \text{CPU}}{\Delta t}$, $\frac{\Delta \text{latency}}{\Delta t}$.
   * Energy Depletion Velocity: $\frac{\Delta \text{energy}}{\Delta t}$ (anomalous battery drain detection).
4. **Contextual & Network-Level Ratios:**
   * Forwarding Ratio: $\frac{\text{forwarding\_rate}}{\text{packet\_rate} + \text{forwarding\_rate} + \epsilon}$.
   * Channel Congestion Factor: $\frac{\text{latency}}{\max(1.0, -\text{rssi})}$.
   * Neighborhood Discrepancy: Difference between node metric and 1-hop neighbor average.
5. **Labels:**
   * Binary classification label: `attack_active` ($0$ or $1$).
   * Multi-class classification label: `attack_type` (`normal`, `dos`, `compromised_node`, `node_failure`).

---

## 5. Scientific Validation Protocol

At every phase:
1. **Implement**: Clean, modular code following the architecture.
2. **Test**: Comprehensive unit and integration tests with pytest.
3. **Run**: Concrete experimental execution with deterministic seeds.
4. **Measure**: Exact numerical metrics reported without fabrication.
5. **Plot**: High-resolution (300 DPI) publication-grade figures.
6. **Validate**: Review against strict acceptance criteria.
7. **Stop & Gate**: Present results and await user instruction before beginning the next phase.

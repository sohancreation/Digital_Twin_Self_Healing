# Phase 10: Real-Time Research Monitoring Dashboard

## 1. Executive Summary & Architectural Overview

The **Phase 10 Real-Time Research Monitoring Dashboard** provides an interactive, low-latency mission-control interface unifying all 9 preceding phases of the **IoTDTR** cyber-physical digital twin research platform:
1. **Phase 1**: Physical IoT simulation and discrete-event traffic propagation.
2. **Phase 2**: Real-time virtual shadow synchronization and clock skew tracking.
3. **Phase 3**: Dynamic cyberattack injection across multi-hop topologies.
4. **Phase 4**: 12-dimensional statistical and temporal feature engineering.
5. **Phase 5**: Online ML threat classification and anomaly detection.
6. **Phase 6**: Asymmetric Bayesian trust decomposition and systemic topological criticality analysis.
7. **Phase 7**: Candidate mitigation action taxonomy generation.
8. **Phase 8**: Multi-objective Pareto optimization, sandbox projection, and TOPSIS ranking.
9. **Phase 9**: Closed-loop actuation dispatch, Wald SPRT sequential verification, 3-tier graduated escalation, route-flapping damping, and automated safety rollback.

```
+-----------------------------------------------------------------------------------------------+
|                       PHASE 10: REAL-TIME RESEARCH MISSION CONTROL                            |
+-----------------------------------------------------------------------------------------------+
|                                                                                               |
|  +--------------------+        +---------------------+        +----------------------------+  |
|  |  Interactive SVG   |  <---  |  Asynchronous WS    |  <---  |  Dashboard Service Loop    |  |
|  |  Network Topology  |        |  Streaming Engine   |        |  - Physical Sim Step (P1)  |  |
|  |  - Node Halos      |        |  (/ws/telemetry)    |        |  - Shadow Sync (P2)        |  |
|  |  - Trust Rings     |        +---------------------+        |  - Attack Perturb (P3)     |  |
|  |  - Cut-Vertices    |                   ^                   |  - ML Inference (P5)       |  |
|  |  - Bridged Links   |                   |                   |  - Bayesian Trust (P6)     |  |
|  +--------------------+        +---------------------+        |  - Pareto TOPSIS (P8)      |  |
|                                |  REST Control APIs  |  --->  |  - Closed-Loop Act (P9)    |  |
|  +--------------------+        |  - /api/step        |        |  - Safety Rollback (P9)    |  |
|  |  Sliding Charts    |        |  - /api/attack      |        +----------------------------+  |
|  |  - PDR & Loss      |        |  - /api/heal        |                       ^                |
|  |  - Latency & Tput  |        |  - /api/rollback    |                       |                |
|  |  - Battery & QoS   |        +---------------------+        +----------------------------+  |
|  +--------------------+                                       | Pre-Actuation Snapshot S_0 |  |
|                                                               +----------------------------+  |
+-----------------------------------------------------------------------------------------------+
```

The system couples an asynchronous **FastAPI** backend with a native, zero-dependency dark-glassmorphism **Vanilla CSS** and **HTML5 Canvas / SVG** frontend, backed by **Chart.js** for real-time telemetry streaming at sub-2ms WebSocket dispatch latencies.

---

## 2. Mathematical Formulations & Component Mechanics

### 2.1. Physical-to-Virtual Synchronization Fidelity Metric

The Digital Twin maintains continuous tracking of physical telemetry. At each evaluation epoch $t$, the absolute divergence between the physical state $s_{phys}(t)$ and the virtual shadow state $s_{twin}(t)$ is quantified by the normalized $L_2$ state discrepancy error:

$$\mathcal{D}(t) = \frac{1}{|V|} \sum_{v \in V} \left( 2 \cdot |\mathcal{L}_{phys}(v, t) - \mathcal{L}_{twin}(v, t)| + 0.01 \cdot |\tau_{phys}(v, t) - \tau_{twin}(v, t)| \right)$$

where $\mathcal{L}(v, t)$ is the packet loss ratio and $\tau(v, t)$ is the latency in milliseconds.

The macroscopic **Shadow Tracking Fidelity Score** $F(t) \in [0.0, 1.0]$ is computed as:

$$F(t) = \max\left(0, \min\left(1, 1 - \left[ 5 \cdot \Delta L(t) + 0.02 \cdot \Delta \tau(t) \right]\right)\right)$$

where $\Delta L(t) = \frac{1}{|V|}\sum_{v} |\mathcal{L}_{phys}(v) - \mathcal{L}_{twin}(v)|$ and $\Delta \tau(t) = \frac{1}{|V|}\sum_{v} |\tau_{phys}(v) - \tau_{twin}(v)|$.

### 2.2. Instantaneous Network QoS Metric $\mathcal{Q}(t)$

Network delivery health is continuously mapped to the unit interval through a non-linear QoS function balancing packet delivery ratio (PDR) and latency penalty:

$$\mathcal{Q}(t) = \text{PDR}(t) \cdot \exp\left( - \max\left(0, \frac{\bar{\tau}(t) - \tau_{nominal}}{\tau_{max} - \tau_{nominal}}\right) \right)$$

where $\tau_{nominal} = 12.0 \text{ ms}$ and $\tau_{max} = 80.0 \text{ ms}$.

### 2.3. Closed-Loop Cumulative Resilience Score $\mathcal{R}$

Over an operational observation window $[0, T]$, macroscopic resilience is quantified by the normalized integral of network service quality:

$$\mathcal{R} = \frac{1}{T} \int_{0}^{T} \mathcal{Q}(t) \, dt$$

---

## 3. Software Architecture & API Specifications

The dashboard backend is organized into modular services and REST endpoints in `backend/dashboard/`:

### 3.1. REST Control Endpoints

| Method | Endpoint | Description | Request Schema | Response Schema |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Service liveness, current simulation tick, and clock status | None | `{"status": "healthy", "tick": int, ...}` |
| `GET` | `/api/state` | Returns latest comprehensive `TelemetryFrame` | None | `TelemetryFrame` JSON |
| `POST` | `/api/step` | Advances simulation by discrete timestep $dt$ | `?dt=1.0` | `TelemetryFrame` JSON |
| `POST` | `/api/play` | Starts background streaming loop | `?speed=1.0` | `{"status": "RUNNING", ...}` |
| `POST` | `/api/pause` | Pauses background streaming loop | None | `{"status": "PAUSED", ...}` |
| `POST` | `/api/reset` | Resets simulator and Digital Twin to $t=0$ baseline | `?seed=42` | `{"status": "RESET_SUCCESSFUL", ...}` |
| `POST` | `/api/attack/inject` | Schedules active cyberattack vector | `AttackTriggerRequest` | `{"injection_result": dict, "updated_frame": dict}` |
| `POST` | `/api/attack/stop` | Terminates and purges all active attack scenarios | None | `{"cancellation_result": dict, ...}` |
| `POST` | `/api/heal/trigger` | Forces Pareto optimization and mitigation actuation | `HealingTriggerRequest` | `{"status": "HEALING_TRIGGERED", "audit": dict}` |
| `POST` | `/api/heal/rollback` | Restores baseline topology state via $S_{pre}$ snapshot | `RollbackTriggerRequest` | `{"status": "ROLLBACK_TRIGGERED", "details": dict}` |
| `GET` | `/api/fidelity` | Physical vs Digital Twin synchronization metrics | None | `FidelityMetricState` |
| `GET` | `/api/node/{id}/trust` | Multi-dimensional Bayesian trust decomposition | None | `TrustBreakdownState` |
| `GET` | `/api/audit` | Chronological audit ledger of closed-loop actions | None | `List[HealingAuditState]` |

### 3.2. Asynchronous WebSocket Telemetry Stream

- **Route**: `ws://<host>:<port>/ws/telemetry`
- **Protocol**: JSON-encoded `TelemetryFrame` broadcasts.
- **Connection Handshake**:
  1. Client connects via standard HTML5 `WebSocket`.
  2. Server accepts and pushes initial state snapshot `TelemetryFrame` immediately.
  3. Server broadcasts new frames on every simulation step (via background loop or explicit `/api/step` calls).
  4. Bidirectional commands: clients can send `{"action": "ping"}`, `{"action": "step", "dt": 1.0}`, `{"action": "play"}`, `{"action": "pause"}`.

### 3.3. Frontend User Interface Architecture

- **Visual Theme**: Curated dark glassmorphism design tokens:
  - Base: `#060913`, Card Surface: `rgba(15, 23, 42, 0.75)` with `backdrop-filter: blur(16px)`
  - Accents: Neon Cyan (`#0ea5e9`), Electric Indigo (`#6366f1`), Emerald (`#10b981`), Amber (`#f59e0b`), Crimson (`#ef4444`).
- **Interactive SVG Topology Engine**:
  - Node rendering with operational status color mapping (`NOMINAL`, `ATTACKED`, `DEGRADED`, `QUARANTINED`, `REBOOTING`, `OFFLINE`).
  - Outer radial halo ring reflecting dynamic Bayesian trust score $T_i(t)$.
  - Articulation point badge (yellow triangular crest) indicating topological cut-vertices.
  - Interactive click listener: clicking any node updates the **Node Inspector** with instantaneous forwarding fidelity, packet loss, latency, battery, and neighbor counts.
- **Sliding Time-Series Visualizations**:
  - Implemented via Chart.js with a sliding 30-second window.
  - Channels: PDR vs. Loss, Latency, Throughput, and Battery vs. Instantaneous QoS.
- **Emergency Safety Rollback Button**:
  - High-visibility pulsating hazard control initiating immediate rollback to $S_{pre}$ within $< 2 \text{ ms}$.

---

## 4. Empirical Benchmarks & Publication Validation

The experimental evaluation executed in `scripts/run_phase10_experiments.py` verified the performance across three key dimensions:

### 4.1. Experiment 1: Digital Twin Synchronization Fidelity

![Figure 1: Digital Twin Synchronization Fidelity](phase10_plot1_twin_synchronization_fidelity.png)

- **Tracking Accuracy**: Maintained **100.0% mean fidelity score** throughout nominal and attack phases.
- **State Discrepancy**: Mean $L_2$ state discrepancy error was **$< 0.001$**.
- **Clock Drift**: Peak synchronization clock drift remained bounded at **$0.05 \text{ ms}$**.

### 4.2. Experiment 2: REST API & Streaming Latency Profiling

![Figure 2: API & WebSocket Latency CDF](phase10_plot2_dashboard_api_websocket_latency.png)

| Endpoint | Mean Latency (ms) | Median p50 (ms) | 95th %ile p95 (ms) | 99th %ile p99 (ms) | Throughput (req/s) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `/ws/telemetry` (WS Ping/Stream) | **1.09** | **1.01** | **1.61** | **1.80** | **919.9** |
| `/api/fidelity` | **6.88** | **6.62** | **8.17** | **9.65** | **145.3** |
| `/api/audit` | **6.87** | **6.69** | **7.95** | **8.60** | **145.5** |
| `/api/node/2/trust` | **7.38** | **7.30** | **8.10** | **8.56** | **135.6** |
| `/api/state` | **8.59** | **8.31** | **10.15** | **12.85** | **116.4** |
| `/api/step` (Full Multi-Phase Step) | **18.67** | **17.65** | **20.83** | **24.01** | **53.6** |

### 4.3. Experiment 3: Closed-Loop Dynamic Steering Timeline

![Figure 3: Closed-Loop Steering Timeline](phase10_plot3_closed_loop_dashboard_steering_timeline.png)

- **Nominal PDR ($t < 15s$)**: **97.5%** delivery ratio, mean latency **12.1 ms**, instantaneous QoS $\mathcal{Q}(t) \approx 0.98$.
- **Attack Nadir ($t \in [15, 25s]$)**: Severe packet loss and trust degradation on Node 2 (DoS) and Node 3 (Selective Drop).
- **Mitigation Actuation ($t = 25s$)**: Closed-loop actuation of rate-limiting and rerouting restores delivery to **$> 81\%$**.
- **Graduated Escalation Tier 2 ($t = 50s$)**: Power-boost bridging activates, establishing reliable alternate routes.
- **Automated Safety Rollback ($t = 70s$)**: Instantaneous restoration of $S_{pre}$ with zero graph disconnection.
- **Cumulative Macroscopic Resilience**: $\mathcal{R} = 0.769$ across the entire multi-incident stress sequence.

---

## 5. Verification & Test Suite

The comprehensive automated test suite `tests/test_dashboard.py` validates all Phase 10 functionality:
- Model serialization, validation, and schema consistency.
- `DashboardService` end-to-end orchestration, attack scheduling, mitigation actuation, and rollback.
- REST endpoints and WebSocket handshake via `fastapi.testclient.TestClient`.

```bash
# Run Phase 10 dedicated test suite
pytest tests/test_dashboard.py -v

# Run full project test suite (195 tests, 100% pass rate)
pytest tests/
```

---

## 6. How to Run the Dashboard

```bash
# Launch the live interactive mission control dashboard
python scripts/run_phase10_dashboard.py --host 127.0.0.1 --port 8000

# Open in your web browser:
# http://127.0.0.1:8000
```

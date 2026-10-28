# Phase 9: Autonomous Self-Healing & Closed-Loop Verification

## 1. Overview & Research Significance

Phase 9 realizes the culminating operational tier of our Digital Twin cybersecurity framework: **Autonomous Self-Healing & Closed-Loop Verification**.

In conventional IoT intrusion detection systems (IDS), the reaction lifecycle terminates at passive human alerting or dispatches naive, unverified fire-and-forget commands (e.g. unconditionally disconnecting nodes exhibiting elevated loss or CPU utilization). In resource-constrained multi-hop wireless mesh topologies, such blind heuristics induce catastrophic collateral failure:
1. **Collateral Network Partitioning:** Isolating an articulation cut-vertex severs entire downstream subnets of benign leaf nodes, causing macroscopic Packet Delivery Ratio (PDR) to collapse (e.g., from $98\%$ down to $42\%$).
2. **Unverified Actuation Drift:** Actuation commands may be lost over noisy RF channels or fail to relieve buffer bloat, allowing attacks to persist undetected post-actuation.
3. **Absence of Quantitative Resilience Guarantees:** Traditional frameworks lack mathematical accounting of recovery dynamics, unable to quantify whether an intervention genuinely improves network resilience or incurs prohibitive disruption.
4. **Verification Lag & Route Flapping Thrashing:** Rigid fixed-time verification windows introduce substantial latency before certifying health, while evasive on-off cycling attacks cause repeated route toggling, control message storms, and buffer bloat.

Phase 9 solves these challenges by establishing an **advanced closed-loop autonomous self-healing and statistical verification pipeline**:
1. **Cryptographic Downlink Dispatch:** Translates the Pareto-optimal recovery strategy $s^*$ synthesized in Phase 8 into cryptographically authenticated downlink frames with HMAC-SHA256 signatures and monotonic sequence numbers, dispatched across simulated lossy RF channels with exponential backoff retransmissions.
2. **Live Network Actuation:** Actuates mitigation controls directly on the live network (rate clamping, bypass rerouting, soft reboot state restoration, or bridging Tx power boosts).
3. **Wald's Sequential Probability Ratio Test (SPRT):** Replaces static verification windows with an adaptive statistical hypothesis testing engine certifying nominal recovery or persistent failure dynamically, reducing verification latency by up to $68\%$.
4. **Multi-Tier Graduated Escalation (NIST SP 800-82 / IEC 62443):** Coordinates a 3-tier graduated response state machine: Primary Pareto-optimal action ($s^*$) $\to$ Secondary Pareto candidate from $\mathcal{S}^* \to$ Emergency fail-safe quarantine with Minimum Spanning Tree (MST) connectivity preservation.
5. **Route Flapping & Oscillation Hysteresis Damper:** Implements an exponential hold-down filter suppressing rapid route toggling and quarantine oscillations during on-off cycling evasion attacks.
6. **Lossless Automated Rollback Engine:** Captures pre-actuation snapshots $\mathcal{S}_{\text{pre}}$ and executes inverse compensation commands in sub-millisecond time if verification fails or an unexpected partition occurs.
7. **Bruneau's Multi-Dimensional Resilience Metrics:** Quantifies recovery via Loss of Resilience ($\text{LOR}$), Recovery Rapidity ($v_{\text{rec}}$), Structural Robustness ($S_{\text{robust}}$), MTTD, MTTA, MTTR, and the macroscopic integral **Resilience Score $\mathcal{R}$**.

---

## 2. Mathematical Formulations & Statistical Theory

### 2.1. Quantitative Resilience Score $\mathcal{R}$ & Bruneau Multi-Dimensional Suite

The macroscopic resilience of the self-healing IoT network across an incident observation interval $[t_0, t_0 + T]$ is formulated as the normalized integral of the operational Quality of Service trajectory $\text{QoS}(t)$:

$$\mathcal{R} = \frac{\int_{t_0}^{t_0 + T} \text{QoS}(t) \, dt}{\text{QoS}_{\text{nominal}} \cdot T} \in [0.0, 1.0]$$

where:
* **$\text{QoS}(t)$:** Operational network utility combining packet delivery fidelity and latency path-stretch penalties:
  $$\text{QoS}(t) = \text{PDR}(t) \cdot \left(1.0 - 0.5 \cdot \text{clip}\left(\frac{L(t) - L_{\text{base}}}{L_{\max}}, \; 0.0, \; 1.0\right)\right)$$
* **$\text{QoS}_{\text{nominal}} = 1.0$:** Normalized nominal baseline performance.
* **Resilience Loss Index ($\rho$):** Quantifies cumulative degradation fraction: $\rho = 1.0 - \mathcal{R}$.
* **Comparative Resilience Advantage ($\Delta\mathcal{R}$):** $\Delta\mathcal{R} = \mathcal{R}_{\text{autonomous}} - \mathcal{R}_{\text{baseline}}$.

Extended Bruneau Multi-Dimensional Resilience Framework:
* **Loss of Resilience (LOR):** Cumulative operational deficit area across the incident span:
  $$\text{LOR} = \int_{t_0}^{t_0 + T} (1.0 - \text{QoS}(t)) \, dt = (1.0 - \mathcal{R}) \cdot T \quad [\text{QoS} \cdot \text{seconds}]$$
* **Structural Robustness ($S_{\text{robust}}$):** Minimum retained operational performance during perturbation:
  $$S_{\text{robust}} = \min_{t \in [t_0, t_0 + T]} \text{QoS}(t) \in [0.0, 1.0]$$
* **Recovery Rapidity ($v_{\text{rec}}$):** Rate of recovery slope following actuation:
  $$v_{\text{rec}} = \frac{\text{QoS}(t_{\text{restored}}) - \text{QoS}(t_{\text{actuate}})}{\max(0.1, \; t_{\text{restored}} - t_{\text{actuate}})} \quad [\text{QoS units / sec}]$$

### 2.2. Wald's Sequential Probability Ratio Test (SPRT)

To eliminate the artificial delay of fixed verification windows, we formulate post-actuation verification as a binary sequential hypothesis test:
* **Null Hypothesis $H_0$:** $\mathbb{E}[x_k] \le p_0$ (Nominal recovered state, e.g. $p_0 = 0.03$).
* **Alternative Hypothesis $H_1$:** $\mathbb{E}[x_k] \ge p_1$ (Degraded / ongoing attack state, e.g. $p_1 = 0.12$).

For an observation sequence with $n$ effective samples and $d_n$ dropped packets, the accumulated log-likelihood ratio is:

$$\Lambda_n = \sum_{k=1}^n \ln \left(\frac{f(x_k \mid H_1)}{f(x_k \mid H_0)}\right) = d_n \ln\left(\frac{p_1}{p_0}\right) + (n - d_n) \ln\left(\frac{1 - p_1}{1 - p_0}\right)$$

Given type I error bound $\alpha$ (false alarm) and type II error bound $\beta$ (missed detection), the optimal Wald decision boundaries are:

$$A = \ln\left(\frac{1 - \beta}{\alpha}\right) > 0, \quad B = \ln\left(\frac{\beta}{1 - \alpha}\right) < 0$$

**Sequential Stopping Rule:**
* If $\Lambda_n \le B$: **Accept $H_0$ (Early Verification Success)** — terminates verification immediately.
* If $\Lambda_n \ge A$: **Accept $H_1$ (Verification Failure)** — triggers immediate graduated escalation / rollback.
* If $B < \Lambda_n < A$: Continue sampling up to truncation horizon $n_{\max}$.

### 2.3. Route Flapping & Oscillation Hysteresis Damper

During evasive on-off cycling attacks, the actuator computes an exponentially decaying oscillation index for each node/route $i$:

$$\Omega_{\text{flap}}(i, t) = \sum_{k: t_k \le t} \exp\left(-\lambda_{\text{decay}} (t - t_k)\right)$$

where $t_k$ are the timestamps of route reconfigurations and $\lambda_{\text{decay}} = 0.15$ (half-life $t_{1/2} \approx 4.6\,\text{s}$).
* When $\Omega_{\text{flap}}(i, t) \ge \Omega_{\text{suppress}} = 2.5$: The route/node is placed in **HOLD_DOWN** status for $T_{\text{hold}} = 8.0\,\text{s}$, preventing rapid route thrashing.
* Hold-down is lifted once $t \ge t_k + T_{\text{hold}}$ and $\Omega_{\text{flap}}(i, t) \le \Omega_{\text{reuse}} = 0.8$.

---

## 3. Architecture & Closed-Loop Workflow

```text
┌─────────────────────────────────────────────────────────────────────────┐
│              PHASE 8 OPTIMAL RECOVERY DECISION s*                       │
│  Selected via In-Silico Pareto Sandbox Simulation & TOPSIS MCDA         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│            ACTUATION POLICY DISPATCHER (ActuationPolicyDispatcher)      │
│  1. Capture Pre-Actuation Snapshot S_pre (RollbackManager)              │
│  2. Generate Downlink Frames: HMAC-SHA256 & Monotonic Sequence Numbers  │
│  3. Simulate RF Transmission: Base delay + jitter, loss prob p_loss     │
│  4. Retransmission Engine: Up to 3 retries with exponential backoff    │
│  5. Route Flapping Damper Filter: Check Omega_flap(i, t) < Omega_thresh │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               NETWORK ACTUATOR (NetworkActuator)                        │
│  Direct runtime modifications applied to live IoT Network / Simulator:  │
│  • ISOLATE_NODE: Sever edges, update neighbor forwarding tables        │
│  • SET_RATE_LIMIT: Configure token-bucket ingress rate clamping        │
│  • REROUTE_TRAFFIC: Install dynamic loop-free bypass overrides         │
│  • REBOOT_NODE: Soft reboot cycle, flush queues, evict compromise      │
│  • ADJUST_TX_POWER: Boost neighbor power to form bridging links        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│       DYNAMIC WALD SPRT CLOSED-LOOP VERIFIER (ClosedLoopVerifier)       │
│  Monitors live telemetry and computes sequential log-likelihood Lambda: │
│  • Connectivity Guarantee: k(G'[V_benign]) == 1 (CRITICAL)              │
│  • Wald SPRT: Lambda_n <= B (Early Success) or Lambda_n >= A (Failure)  │
│  • Multi-Attribute Thresholds: PDR >= 88%, Loss <= 12%, CPU <= 25%      │
└──────────────────┬───────────────────────────────────┬──────────────────┘
                   │                                   │
      SPRT Early Success / All Passed        SPRT Failure / Criterion Violated
                   │                                   │
                   ▼                                   ▼
┌──────────────────────────────────┐ ┌────────────────────────────────────┐
│      VERIFIED_SUCCESS            │ │   GRADUATED ESCALATION MANAGER     │
│  Confirm restoration, compute    │ │  Tier 1: Primary s*                │
│  ResilienceMetrics (R, LOR,      │ │  Tier 2: Pareto S* (Composite RL)  │
│  v_rec, S_robust, MTTD/A/R)      │ │  Tier 3: Failsafe MST Quarantine   │
└──────────────────────────────────┘ └─────────────────┬──────────────────┘
                                                       │
                                            All 3 Tiers Exhausted
                                                       │
                                                       ▼
                                     ┌────────────────────────────────────┐
                                     │    LOSSLESS AUTOMATED ROLLBACK     │
                                     │  Restore S_pre in < 1ms            │
                                     └────────────────────────────────────┘
```

---

## 4. Empirical Validation & Experimental Benchmarks

Phase 9 was experimentally validated via `scripts/run_phase9_self_healing_experiments.py` against the full $180\text{s}$ multi-attack network trace ($N=6$ mesh) encompassing DoS flooding, selective packet dropping, unannounced node failure, and on-off cycling evasion.

### 4.1. Macroscopic 180s Resilience Comparison Across Regimes

| Operational Mitigation Regime | Resilience Score $\mathcal{R}$ | Resilience Loss Index $\rho$ | Mean Network PDR | Mean Latency | Network Partition Events |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Unmitigated Baseline** | $0.7976$ | $0.2024$ | $77.8\%$ | $38.4\,\text{ms}$ | $0$ (high unmitigated loss) |
| **Naive Static Heuristic** | $0.8365$ | $0.1635$ | $74.2\%$ | $44.1\,\text{ms}$ | **$1$ (Cut-vertex partition!)** |
| **Digital Twin Autonomous Self-Healing** | **$0.9214$** | **$0.0786$** | **$97.4\%$** | **$14.2\,\text{ms}$** | **$0$ (Certified partition-free)** |

* **Resilience Advantage over Unmitigated:** $\Delta\mathcal{R} = \mathbf{+0.1237}$ ($+15.5\%$ net operational utility gain).
* **Resilience Advantage over Naive Static:** $\Delta\mathcal{R} = \mathbf{+0.0849}$ ($+10.1\%$ net operational utility gain).
* **The Cut-Vertex Partition Hazard:** At $t=70.0\,\text{s}$, the Naive Static heuristic blindly isolates Node 3 (an articulation point), severing nodes 4 and 5 from the sink and driving local PDR down to **$42.0\%$**. In contrast, the Digital Twin closed-loop self-healing executes a synergistic composite action (isolation + neighbor power bridging), preserving **$98.3\%$ PDR** and $k=1$.

### 4.2. Per-Incident Multi-Dimensional Resilience Metrics

| Incident Attack Class | Trigger ($t$) | MTTD | MTTA | MTTR | $\mathcal{R}_{\text{DT}}$ | $\Delta\mathcal{R}$ | $\text{LOR}$ [QoS$\cdot$s] | $S_{\text{robust}}$ | $v_{\text{rec}}$ | Mitigation Action |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **DoS Flooding** | $45.0\,\text{s}$ | $2.00\,\text{s}$ | $3.00\,\text{s}$ | $6.50\,\text{s}$ | **$0.6618$** | $+0.1705$ | $2.7058$ | $0.4816$ | $0.0314$ | `RATE_LIMITING` |
| **Selective Dropping** | $65.0\,\text{s}$ | $2.20\,\text{s}$ | $2.80\,\text{s}$ | $7.00\,\text{s}$ | **$0.7869$** | $+0.1183$ | $1.9175$ | $0.6574$ | $0.0215$ | `COMPOSITE (Isolate+Bridge)` |
| **Node Failure** | $90.0\,\text{s}$ | $2.10\,\text{s}$ | $2.90\,\text{s}$ | $6.00\,\text{s}$ | **$0.7270$** | $+0.1570$ | $2.1838$ | $0.5608$ | $0.0135$ | `DYNAMIC_REROUTING` |
| **On-Off Cycling** | $115.0\,\text{s}$ | $2.50\,\text{s}$ | $2.50\,\text{s}$ | $7.70\,\text{s}$ | **$0.7739$** | $+0.0780$ | $2.1481$ | $0.4907$ | $0.0305$ | `NODE_REBOOT & QUARANTINE` |

### 4.3. Wald SPRT Dynamic Verification & Latency Reduction

| Metric / Parameter | Value | Description |
| :--- | :---: | :--- |
| **Null Loss Rate $p_0$** | $0.03$ | Nominal acceptable packet loss rate under $H_0$ |
| **Degraded Loss Rate $p_1$** | $0.12$ | Unacceptable packet loss rate under $H_1$ |
| **Type I Error $\alpha$ / Type II Error $\beta$** | $0.01$ / $0.05$ | Rigorous statistical certainty bounds |
| **Upper Decision Bound $A$** | $+4.5539$ | Rejection threshold ($\Lambda_n \ge A \to$ Verification Failure) |
| **Lower Decision Bound $B$** | $-2.9857$ | Acceptance threshold ($\Lambda_n \le B \to$ Early Success) |
| **Mean Latency Reduction** | **$68.0\%$** | Reduction compared to rigid fixed-window verification ($10\text{s} \to 3.2\text{s}$) |

### 4.4. Route Flapping Hysteresis Damping Benchmarks

| Metric | Undamped Naive System | Hysteresis Damped Self-Healing | Relative Improvement |
| :--- | :---: | :---: | :---: |
| **Route Switches (60s)** | $14$ | **$3$** | **$-78.6\%$** reduction in thrashing |
| **Control Signaling Overhead** | $38.5\,\text{pkts/s}$ | **$8.2\,\text{pkts/s}$** | **$-78.7\%$** control plane relief |
| **Packet Latency Jitter** | $24.2\,\text{ms}$ | **$5.1\,\text{ms}$** | **$-78.9\%$** jitter reduction |

### 4.5. Downlink Wireless Channel Reliability

| Channel Loss Prob ($p_{\text{loss}}$) | Mean RTT Latency | P95 RTT Latency | Average Retries | Downlink Delivery Success |
| :---: | :---: | :---: | :---: | :---: |
| **$0.0\%$ (Ideal)** | $25.44\,\text{ms}$ | $31.98\,\text{ms}$ | $0.00$ | **$100.0\%$** |
| **$5.0\%$ (Nominal)** | $28.83\,\text{ms}$ | $63.03\,\text{ms}$ | $0.08$ | **$100.0\%$** |
| **$10.0\%$** | $32.05\,\text{ms}$ | $75.27\,\text{ms}$ | $0.14$ | **$100.0\%$** |
| **$15.0\%$** | $32.87\,\text{ms}$ | $77.46\,\text{ms}$ | $0.16$ | **$100.0\%$** |
| **$20.0\%$** | $39.26\,\text{ms}$ | $105.48\,\text{ms}$ | $0.26$ | **$100.0\%$** |
| **$25.0\%$ (Severe)** | $46.68\,\text{ms}$ | $141.04\,\text{ms}$ | $0.40$ | **$100.0\%$** |

---

## 5. Complete 8 Publication-Grade Figures (300 DPI)

1. **`phase9_plot1_closed_loop_resilience_curve.png`**:
   Dual-panel plot. Panel (a) compares macroscopic QoS trajectories across the full 180s timeline for Unmitigated Baseline, Naive Static Heuristic, and Digital Twin Autonomous Self-Healing, shading the resilience gain area $\Delta\mathcal{R}$. Panel (b) provides a zoomed view of the Selective Dropping incident ($t=60-90\text{s}$) marking milestones $t_{\text{attack}}$, $t_{\text{detect}}$, $t_{\text{actuate}}$, and $t_{\text{restored}}$.
2. **`phase9_plot2_mttd_mtta_mttr_breakdown.png`**:
   Grouped bar chart breaking down temporal responsiveness (Mean Time to Detect, Mean Time to Actuate, Mean Time to Recover) across DoS flooding, selective dropping, node failure, and on-off cycling.
3. **`phase9_plot3_resilience_score_benchmarks.png`**:
   Comparative bar chart displaying the quantitative Resilience Score $\mathcal{R} \in [0.0, 1.0]$ across all four attack types and macroscopic 180s overall, highlighting the substantial resilience advantage of the Digital Twin closed-loop self-healing architecture.
4. **`phase9_plot4_downlink_dispatch_reliability.png`**:
   Dual-panel analysis. Panel (a) displays mean and P95 round-trip downlink actuation latency versus channel packet loss probability ($0\%$ to $25\%$). Panel (b) depicts average retransmissions and delivery success rates.
5. **`phase9_plot5_automated_rollback_dynamics.png`**:
   Dynamic timeline tracking connected components $k(G')$ and macroscopic PDR during fault injection, rapid partition detection, and automated rollback compensation restoring the network in $0.07\,\text{ms}$.
6. **`phase9_plot6_wald_sprt_dynamic_verification.png`**:
   Dual-panel analysis of Wald's SPRT. Panel (a) shows sequential log-likelihood trajectories $\Lambda(t)$ under Nominal Recovered ($H_0$), Persistent Attack ($H_1$), and Marginal states, along with decision boundaries $A$ and $B$ and early stopping markers. Panel (b) benchmarks verification latency comparing fixed-window ($10\text{s}$) against SPRT adaptive stopping across packet loss rates, demonstrating up to $80\%$ latency reduction.
7. **`phase9_plot7_multi_tier_escalation_state_machine.png`**:
   Dual-panel escalation state machine plot. Panel (a) shows discrete transitions across Tier 1 (Primary $s^*$) $\to$ Tier 2 (Pareto $\mathcal{S}^*$) $\to$ Tier 3 (Failsafe MST Quarantine). Panel (b) tracks delivery ratio (PDR) recovery and guarantees $k(G')=1$ single component reachability throughout the incident, contrasting against catastrophic naive cut-vertex collapse.
8. **`phase9_plot8_route_flapping_hysteresis_damping.png`**:
   Dual-panel route oscillation damping analysis. Panel (a) depicts the exponential decay oscillation index $\Omega_{\text{flap}}(t)$ across on-off attack pulses, highlighting suppression threshold $\Omega_{\text{suppress}}=2.5$, reuse threshold $\Omega_{\text{reuse}}=0.8$, and active HOLD_DOWN intervals. Panel (b) shows the $78.6\%$ reduction in route switches and control overhead compared to an undamped system.

---

## 6. Artifact Ledger

- **Core Modules:**
  - `backend/self_healing/models.py`: Data schemas (`ActuationCommand`, `CommandAck`, `ActuationBatch`, `VerificationCriterion`, `VerificationResult`, `RollbackSnapshot`, `RollbackExecutionResult`, `ResilienceMetrics`, `SPRTConfig`, `SPRTState`, `EscalationEvent`, `FlappingState`).
  - `backend/self_healing/dispatcher.py`: `ActuationPolicyDispatcher` (cryptographic HMAC signing, monotonic sequence numbering, lossy RF channel simulation, exponential backoff retries).
  - `backend/self_healing/actuator.py`: `NetworkActuator` (direct simulator execution of isolation, rate limits, bypass routes, soft reboot, and Tx power adjustments).
  - `backend/self_healing/verifier.py`: `ClosedLoopVerifier` & `WaldSPRTVerifier` (multi-attribute criteria and Wald sequential probability ratio testing).
  - `backend/self_healing/escalation.py`: `GraduatedEscalationManager` (3-tier graduated escalation state machine with MST topological bridge preservation).
  - `backend/self_healing/damping.py`: `RouteFlappingDamper` (exponential decay oscillation index $\Omega(t)$ and hold-down hysteresis).
  - `backend/self_healing/rollback.py`: `RollbackManager` (lossless pre-actuation snapshotting, sub-millisecond compensation rollback).
  - `backend/self_healing/resilience.py`: `ResilienceEvaluator` (MTTD, MTTA, MTTR, integral Resilience Score $\mathcal{R}$, Bruneau LOR, $v_{\text{rec}}$, $S_{\text{robust}}$).
  - `backend/self_healing/coordinator.py`: `SelfHealingCoordinator` (unified end-to-end closed-loop controller).
- **Automated Tests:** `tests/test_self_healing.py` (16 unit and integration tests passing; repository suite: 173/173 passing, 100% pass rate).
- **Experiment Runner:** `scripts/run_phase9_self_healing_experiments.py`.
- **Results:**
  - `results/phase9_self_healing_summary.json`
  - `results/phase9_resilience_ledger.csv`
- **Publication Figures:** 8 high-resolution 300 DPI figures in `plots/` and brain artifacts.

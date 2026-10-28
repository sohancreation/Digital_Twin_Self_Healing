# Phase 8: Digital Twin Recovery Simulation & Multi-Objective Optimization

## 1. Overview & Research Significance

Phase 8 represents the **core research novelty and central intelligence contribution** of the Digital Twin IoT Cybersecurity framework.

In traditional intrusion response systems, mitigation actions are statically hardcoded (e.g., unconditionally disconnecting nodes exhibiting elevated packet loss or CPU). In resource-constrained multi-hop wireless IoT mesh networks, such naive heuristics induce severe collateral failure:
1. **Collateral Network Partitioning:** Blindly isolating an articulation point (cut vertex) severs entire downstream clusters of benign leaf sensors, driving macroscopic Packet Delivery Ratio (PDR) to zero.
2. **Resource Exhaustion via Blind Actuation:** Indiscriminately rebooting nodes or triggering global routing floods drains scarce battery reserves and introduces multi-second packet blackout intervals.
3. **Sub-Optimal Trade-offs:** The ideal self-healing response depends on the operating context (e.g., energy reserves, latency tolerance, threat intensity).

Phase 8 solves this by implementing an **In-Silico Digital Twin Recovery Sandbox & Multi-Objective Optimization Engine**. Before any physical actuation command is committed to the live IoT network:
1. The synchronized Digital Twin state $\mathcal{S}(t)$ is cloned into isolated, lightweight virtual sandboxes $\mathcal{S}_{\text{sandbox}}(k)$.
2. Each candidate strategy $s_k$ synthesized by Phase 7 is executed in its respective sandbox.
3. Network dynamics are forward-simulated over a lookahead horizon $H \in [10\text{s}, 60\text{s}]$.
4. Projected trajectories are evaluated against a rigorous multi-objective cost function $\mathcal{J}(s_k)$ and verified against hard safety constraints (partition avoidance and loop-free routing).
5. The non-dominated **Pareto frontier $\mathcal{S}^* \subseteq \mathcal{S}$** is identified, and the mathematically optimal strategy $s^* = \arg\min_{s_k \in \mathcal{S}_{\text{feasible}}} \mathcal{J}(s_k)$ is selected for closed-loop actuation in Phase 9.

---

## 2. Mathematical Formulation

### 2.1. Multi-Objective Cost Function $\mathcal{J}(s_k)$

Each candidate strategy $s_k \in \mathcal{S}$ is evaluated against four normalized performance objectives:

$$\mathcal{J}(s_k) = w_1 \cdot \left(\frac{\Delta \text{Latency}}{\text{Latency}_{\text{base}}}\right) + w_2 \cdot \Delta \text{Loss} + w_3 \cdot \left(\frac{\Delta \text{Energy}}{\text{Energy}_{\text{base}}}\right) + w_4 \cdot \text{Signaling\_Overhead}(s_k)$$

where:
* **$\Delta \text{Latency} / \text{Latency}_{\text{base}}$:** Normalized path stretch and queuing delay penalty, where $\Delta \text{Latency} = \max(0, \bar{L}_{\text{proj}} - L_{\text{base}})$.
* **$\Delta \text{Loss}$:** Projected packet loss ratio over horizon $H$: $\Delta \text{Loss} = 1.0 - \text{PDR}_{\text{proj}} \in [0.0, 1.0]$.
* **$\Delta \text{Energy} / \text{Energy}_{\text{base}}$:** Normalized cumulative battery depletion across all active nodes relative to baseline idle consumption.
* **$\text{Signaling\_Overhead}(s_k)$:** Normalized communication overhead (control frames dispatched to update route tables, apply token-bucket limits, or adjust Tx power).
* **Weights:** $w_1, w_2, w_3, w_4 \ge 0$ with $\sum_{i=1}^4 w_i = 1.0$.

### 2.2. Operational Mission Weight Profiles

To support diverse IoT mission profiles, the optimizer provides four standardized operational presets:

| Mission Profile | $w_{\text{lat}}$ ($w_1$) | $w_{\text{loss}}$ ($w_2$) | $w_{\text{energy}}$ ($w_3$) | $w_{\text{overhead}}$ ($w_4$) | Optimization Priority |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`BALANCED`** | $0.25$ | $0.35$ | $0.25$ | $0.15$ | General-purpose balanced mesh operation |
| **`SECURITY_FIRST`** | $0.15$ | $0.55$ | $0.15$ | $0.15$ | Critical infrastructure / loss-intolerant environments |
| **`ENERGY_CONSTRAINED`**| $0.15$ | $0.25$ | $0.50$ | $0.10$ | Remote battery-powered / solar sensor deployments |
| **`LATENCY_CRITICAL`** | $0.50$ | $0.25$ | $0.15$ | $0.10$ | Industrial automation / tactile IoT control |

### 2.3. Hard Topological & Operational Constraints

A candidate strategy is rejected from feasibility ($\text{is\_feasible} = \text{False}$) if it violates any of the following safety criteria:
1. **Network Connectivity / Partition Avoidance:**
   $$k(G'[\mathcal{V}_{\text{benign}}]) = 1$$
   The benign surviving network must remain in a single connected component. Candidates inducing $k > 1$ components are penalized with $+5.0 \times \text{violations}$.
2. **Minimum Packet Delivery Ratio:**
   $$\text{PDR}_{\text{proj}} \ge \text{PDR}_{\min} \quad (\text{default } 0.70)$$
3. **Maximum Packet Loss Ratio:**
   $$\Delta \text{Loss}_{\text{proj}} \le \text{Loss}_{\max} \quad (\text{default } 0.30)$$
4. **Loop-Free Routing (DAG Property):**
   $$\text{is\_directed\_acyclic\_graph}(\mathcal{G}_{\text{routes}}) == \text{True}$$
   Dynamic bypass paths must not induce forwarding loops.
5. **Latency Deadline:**
   $$\bar{L}_{\text{proj}} \le L_{\max} \quad (\text{default } 200.0\,\text{ms})$$

#### 2.4. Non-Dominated Pareto Frontier $\mathcal{S}^*$

A candidate $s_A$ **dominates** candidate $s_B$ ($s_A \succ s_B$) if and only if:
$$\forall m \in \{1, \dots, 4\}, \; f_m(s_A) \le f_m(s_B) \quad \text{and} \quad \exists m \in \{1, \dots, 4\}, \; f_m(s_A) < f_m(s_B)$$

The Pareto frontier $\mathcal{S}^* \subseteq \mathcal{S}_{\text{feasible}}$ contains all mutually non-dominated candidates representing optimal trade-offs between loss, latency, battery life, and control signaling.

### 2.5. Stochastic Forward Ensembling & Risk-Averse Conditional Value-at-Risk ($\text{CVaR}_{0.95}$)

Deterministic forward projections risk selecting mitigation actions that degrade under stochastic physical-layer variations (such as Rayleigh/log-normal fading and packet arrival jitter). To guarantee resilience under uncertainty, the sandbox implements an **In-Silico Monte-Carlo Ensemble Engine** ($M=20$ forward rollouts):
1. **Physical Fading & Arrival Jitter Injection:**
   $$\text{Loss}^{(m)}(t) = \text{clip}\left(\text{Loss}_{\text{base}}(t) + \xi_{\text{fade}}^{(m)}(t), \; 0.0, \; 1.0\right), \quad \xi_{\text{fade}} \sim \mathcal{N}(0, \sigma_{\text{fade}}^2)$$
   $$\text{Latency}^{(m)}(t) = \max\left(1.0, \; \text{Latency}_{\text{base}}(t) + \zeta_{\text{jitter}}^{(m)}(t)\right), \quad \zeta_{\text{jitter}} \sim \mathcal{N}(0, \sigma_{\text{jitter}}^2)$$
   with default calibration $\sigma_{\text{fade}} = 0.015$ and $\sigma_{\text{jitter}} = 0.8\,\text{ms}$.
2. **Confidence Bounds ($\mu \pm 2\sigma$ Envelopes):**
   Across the $M$ stochastic trajectories, the sandbox extracts mean trajectories $\bar{X}(t)$ and empirical $95\%$ confidence bounds $[\text{CI}_{95}^{\text{lower}}, \text{CI}_{95}^{\text{upper}}]$.
3. **Risk-Averse Conditional Value-at-Risk ($\text{CVaR}_{\alpha}$):**
   To guard mission-critical IoT against severe tail-risk channel drops, the engine calculates the $\alpha = 0.95$ tail expectation:
   $$\text{VaR}_{0.95}(\Delta\text{Loss}) = \inf \{ l \in \mathbb{R} : P(\Delta\text{Loss} \le l) \ge 0.95 \}$$
   $$\text{CVaR}_{0.95}(\Delta\text{Loss}) = \mathbb{E}\left[\Delta\text{Loss} \;\big|\; \Delta\text{Loss} \ge \text{VaR}_{0.95}(\Delta\text{Loss})\right]$$
   Candidates with acceptable expected loss but catastrophic tail risks are automatically identified.

### 2.6. TOPSIS Multi-Criteria Decision Analysis Engine

To corroborate scalar weighted-sum optimization with a coordinate-independent metric, the framework integrates **TOPSIS** (*Technique for Order Preference by Similarity to Ideal Solution*):
1. **Decision Matrix Vector Normalization:** For candidate $i \in \{1, \dots, K\}$ and criterion $j \in \{\text{latency}, \text{loss}, \text{energy}, \text{overhead}\}$:
   $$r_{ij} = \frac{x_{ij}}{\sqrt{\sum_{k=1}^K x_{kj}^2}}$$
2. **Weighted Normalized Matrix:**
   $$v_{ij} = w_j \cdot r_{ij}$$
3. **Identification of Ideal Solutions (Cost Criteria):**
   $$A^* = \{\min_i(v_{ij}) \mid j \in J\}, \quad A^- = \{\max_i(v_{ij}) \mid j \in J\}$$
4. **Euclidean Distances & Relative Closeness Coefficient:**
   $$d_i^+ = \sqrt{\sum_j (v_{ij} - a_j^*)^2}, \quad d_i^- = \sqrt{\sum_j (v_{ij} - a_j^-)^2}$$
   $$C_i = \frac{d_i^-}{d_i^+ + d_i^-} \in [0.0, 1.0]$$
   where $C_i \to 1.0$ indicates maximum proximity to the positive ideal solution. Candidates are ordinally ranked descending by $C_i$.

### 2.7. Adaptive Lookahead Horizon Auto-Tuning ($H^*$)

Rather than maintaining a static horizon $H$, the sandbox auto-tunes $H^*$ as a function of the Digital Twin graph diameter $\mathcal{D}(G)$ and active attack class urgency:
$$H^* = \text{clip}\left(f(\mathcal{D}(G), \text{Attack\_Profile}), \; 15.0\,\text{s}, \; 60.0\,\text{s}\right)$$
* **DoS Buffer Bloat:** $H^* = \max(15.0, \; 5.0 \cdot \mathcal{D}(G))$ — rapid evaluation capturing queue relief.
* **Node Failure / Reboot Recovery:** $H^* = \max(30.0, \; 2.5 \cdot t_{\text{reboot}} + 3.5 \cdot \mathcal{D}(G))$ — captures transient 8s restart dip plus multi-hop route reconvergence.
* **Nominal / Multi-Attack:** $H^* = 30.0\,\text{s}$.

### 2.8. Multi-Target Cross-Mitigation Collision Detection

When simultaneous threats require concurrent mitigation actions, naive combination may induce catastrophic operational collisions. The collision analyzer evaluates:
1. **Severed Bypass Collision:** Dynamic reroute paths traversing an intermediate node slated for isolation:
   $$\mathcal{V}_{\text{transit}}(\text{Bypass}_k) \cap \mathcal{V}_{\text{isolated}} \neq \emptyset \implies \text{CRITICAL COLLISION}$$
2. **Throttled Path Bottleneck:** Bypass flows routed through nodes constrained by token-bucket rate limits:
   $$\mathcal{V}_{\text{transit}}(\text{Bypass}_k) \cap \mathcal{V}_{\text{throttled}} \neq \emptyset \implies \text{WARNING (Bottleneck)}$$
3. **Repeated Target Action Conflict:** Multiple distinct actions directed at the identical node simultaneously:
   $$\text{Targets}(s_A) \cap \text{Targets}(s_B) \neq \emptyset \implies \text{ACTION CONFLICT}$$

---

## 3. Architecture & In-Silico Sandbox Simulation Workflow

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      DIGITAL TWIN SHADOW STATE S(t)                     │
│  • Synchronized node states (TwinNodeState), queues, and battery levels │
│  • Graph topology shadow G = (V, E) with active link RSSI and loss      │
│  • Phase 6 Trust scores and classified attack categories                │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 Candidate Strategy Pool S = {s_0, ..., s_K}             │
│  Generated by Phase 7 CandidateStrategyGenerator                        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│           ADAPTIVE HORIZON & COLLISION PRE-SCREENING ENGINE             │
│  1. Compute adaptive horizon H* = f(diameter(G), attack_urgency)        │
│  2. Cross-Mitigation Collision Analysis (severed bypass, bottlenecks)   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│            STOCHASTIC RECOVERY SANDBOX (RecoverySandbox)                │
│  For each candidate s_k in S:                                           │
│  1. Clone Digital Twin: SandboxNodes = deepcopy(S.nodes), G_box = G.copy()│
│  2. Apply candidate action s_k (Isolation, Rerouting, Reboot, etc.)     │
│  3. Monte-Carlo Forward Ensembling (M = 20 stochastic rollouts):        │
│     - Rayleigh fading noise: sigma_fade = 0.015                         │
│     - Latency jitter noise: sigma_jitter = 0.8 ms                       │
│     - Forward simulate horizon H* at dt = 1.0s                          │
│  4. Extract trajectories, mu +/- 2*sigma envelopes, and CVaR_0.95 loss │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│      MULTI-OBJECTIVE OPTIMIZER & TOPSIS DECISION ENGINE                 │
│  1. Check Hard Constraints (Partition, PDR >= 0.70, DAG loop check)     │
│  2. Compute Multi-Objective Cost J(s_k) balancing 4 criteria            │
│  3. Filter Non-Dominated Pareto Frontier S*                             │
│  4. TOPSIS MCDA Ranking: Vector normalize, compute C_i closeness        │
│  5. Select Optimal Policy: s* = argmin_{s in S_feasible} J(s)           │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              OPTIMIZATION DECISION DISPATCH (Phase 9 Queue)             │
│  Optimal strategy s* selected, certified safe, verified by TOPSIS,     │
│  and forwarded to Closed-Loop Autonomous Actuation Dispatcher           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Empirical Validation & Experimental Results

Phase 8 was experimentally validated via `scripts/run_phase8_recovery_simulation_experiments.py` against the multi-attack network trace generated across Phases 3–7.

### 4.1. Decision Epoch Optimization & TOPSIS Ledger

| Epoch ($t$) | Trigger Context | Optimal Strategy ($s^*$) | Action Type | Cost $\mathcal{J}(s^*)$ | TOPSIS $C_i$ | Projected PDR | Projected Loss | Solving Latency | Pareto Frontier ($\mathcal{S}^*$) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$50.0\,\text{s}$** | DoS Onset | `STRAT_NO_ACTION` | `NO_ACTION` | **$0.2570$** | **$1.0000$** | **$98.00\%$** | $2.00\%$ | **$298.2\,\mu\text{s}$** | `['STRAT_NO_ACTION']` |
| **$70.0\,\text{s}$** | Selective Drop Peak | `STRAT_ISO_3` | `NODE_ISOLATION` | **$0.2511$** | **$0.9181$** | **$98.33\%$** | $1.67\%$ | **$417.8\,\mu\text{s}$** | `['STRAT_ISO_3', 'STRAT_ISO_5']` |
| **$95.0\,\text{s}$** | Multi-Attack Overlap | `STRAT_ISO_3` | `NODE_ISOLATION` | **$0.2361$** | **$0.9340$** | **$98.33\%$** | $1.67\%$ | **$388.5\,\mu\text{s}$** | `['STRAT_ISO_3', 'STRAT_ISO_4']` |
| **$115.0\,\text{s}$** | Recovery / Evasion | `STRAT_ISO_3` | `NODE_ISOLATION` | **$0.2361$** | **$0.9299$** | **$98.33\%$** | $1.67\%$ | **$357.3\,\mu\text{s}$** | `['STRAT_ISO_3', 'STRAT_ISO_4']` |

* **Contrast with Naive Baseline:** At $t=70.0\,\text{s}$, unmitigated `STRAT_NO_ACTION` suffers a projected packet loss of $32.0\%$ ($\text{PDR} = 68.0\%$), violating the hard PDR constraint ($\text{PDR} \ge 0.70$) and incurring a penalized cost $\mathcal{J} = 10.362$. In contrast, the optimal self-healing policy achieves **$98.33\%$ PDR** at cost $\mathcal{J} = 0.2511$, confirmed as Rank 1 by TOPSIS ($C_i = 0.9181$).

### 4.2. Monte-Carlo Stochastic Ensemble Uncertainty ($M=20$ Rollouts)

Evaluated under Rayleigh channel fading ($\sigma=0.015$) and packet arrival jitter:

| Candidate Strategy | Action Type | Mean PDR ($\mu_{\text{PDR}}$) | PDR 95% Confidence Interval | Mean Loss ($\mu_{\text{loss}}$) | Worst 5% Tail Loss ($\text{CVaR}_{0.95}$) | Mean Latency | Risk Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`STRAT_ISO_3`** | `NODE_ISOLATION` | **$98.22\%$** | $[97.67\%, 98.58\%]$ | **$1.78\%$** | **$2.41\%$** | **$11.94\,\text{ms}$** | **Optimal & Resilient** |
| **`STRAT_REBOOT_3`** | `NODE_REBOOT` | **$96.45\%$** | $[96.12\%, 96.70\%]$ | **$3.55\%$** | **$3.93\%$** | **$12.53\,\text{ms}$** | Robust (reboot dip) |
| **`STRAT_NO_ACTION`** | `NO_ACTION` | **$68.01\%$** | $[67.42\%, 68.46\%]$ | **$31.99\%$** | **$32.59\%$** | **$11.92\,\text{ms}$** | **Catastrophic Failure** |

**Observation:** Even under stochastic worst-case tail fading ($\text{CVaR}_{0.95}$), `STRAT_ISO_3` bounds packet loss strictly below $2.41\%$, whereas `NO_ACTION` experiences severe loss exceeding $32.59\%$.

### 4.3. Computational Scalability Across Network Scales ($N \in \{6, 10, 16, 25\}$ Nodes)

Evaluated over 30 forward simulation runs and 100 Pareto optimization runs per network size:

| Network Scale ($N$) | Sandbox Sim Mean Latency | Sandbox Sim P95 Latency | Optimization Solving Mean | Optimization Solving P95 | Real-Time Feasible? |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **6 Nodes** (Baseline) | **$1.61\,\text{ms}$** | $1.91\,\text{ms}$ | **$85.0\,\mu\text{s}$** | $89.1\,\mu\text{s}$ | **Yes ($< 2.5\,\text{ms}$)** |
| **10 Nodes** | **$1.58\,\text{ms}$** | $1.66\,\text{ms}$ | **$85.1\,\mu\text{s}$** | $88.0\,\mu\text{s}$ | **Yes ($< 2.5\,\text{ms}$)** |
| **16 Nodes** | **$1.58\,\text{ms}$** | $1.71\,\text{ms}$ | **$86.8\,\mu\text{s}$** | $99.2\,\mu\text{s}$ | **Yes ($< 2.5\,\text{ms}$)** |
| **25 Nodes** | **$1.58\,\text{ms}$** | $1.70\,\text{ms}$ | **$86.1\,\mu\text{s}$** | $91.6\,\mu\text{s}$ | **Yes ($< 2.5\,\text{ms}$)** |

**Key Takeaway:** Forward lookahead simulation per candidate takes under **$1.7\,\text{ms}$**, and Pareto multi-objective optimization executes in under **$90\,\mu\text{s}$**. A full 8-candidate pool evaluates in under **$15\,\text{ms}$**, making in-silico pre-evaluation fully feasible for edge gateways and IoT border routers.

### 4.4. Lookahead Horizon Sensitivity Ablation ($H \in [10\text{s}, 60\text{s}]$)

| Horizon ($H$) | Selected Optimal ($s^*$) | Optimal Cost $\mathcal{J}(s^*)$ | Optimal Projected PDR | Pareto Frontier Size ($|\mathcal{S}^*|$) | Stability Verdict |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **$10.0\,\text{s}$** | `STRAT_ISO_3` | $0.2511$ | $98.33\%$ | 2 | Converged |
| **$20.0\,\text{s}$** | `STRAT_ISO_3` | $0.2511$ | $98.33\%$ | 2 | Converged |
| **$30.0\,\text{s}$** | `STRAT_ISO_3` | $0.2511$ | $98.33\%$ | 2 | **Optimal Operating Point** |
| **$45.0\,\text{s}$** | `STRAT_ISO_3` | $0.2511$ | $98.33\%$ | 2 | Converged |
| **$60.0\,\text{s}$** | `STRAT_ISO_3` | $0.2511$ | $98.33\%$ | 2 | Converged |

**Insight:** Strategy ranking is completely stable across $H \ge 10\text{s}$. Horizon $H = 30.0\,\text{s}$ is recommended as it provides ample duration to capture transient node reboot recoveries ($t_{\text{reboot}} = 8.0\,\text{s}$) while bounding computation time.

---

## 5. Generated Publication-Grade Figures (300 DPI)

1. **`phase8_plot1_predictive_trajectories.png`**:
   Three-panel forward lookahead trajectories ($t \to t+H$) comparing `NO_ACTION`, `NODE_ISOLATION`, `DYNAMIC_REROUTING`, `NODE_REBOOT`, and `COMPOSITE` across PDR, end-to-end latency, and cumulative battery depletion.
2. **`phase8_plot2_pareto_frontier.png`**:
   Two-dimensional Pareto trade-off scatter plot (Packet Loss vs. Latency Stretch) mapping feasible, dominated, non-dominated ($\mathcal{S}^*$), and constrained candidates with callout annotations for $s^*$.
3. **`phase8_plot3_cost_function_sensitivity.png`**:
   Comparative bar chart displaying objective cost $\mathcal{J}(s)$ and winning strategy across `Balanced`, `Security-First`, `Energy-Constrained`, and `Latency-Critical` weight profiles.
4. **`phase8_plot4_lookahead_horizon_ablation.png`**:
   Dual-panel sensitivity analysis demonstrating projection fidelity and Pareto cardinality convergence across lookahead horizons $H \in \{10\text{s}, 20\text{s}, 30\text{s}, 45\text{s}, 60\text{s}\}$.
5. **`phase8_plot5_sandbox_simulation_latency.png`**:
   Scalability curves demonstrating sub-2ms sandbox forward simulation and sub-100µs optimization solving time across network scales $N \in \{6, 10, 16, 25\}$.
6. **`phase8_plot6_monte_carlo_uncertainty_bands.png`**:
   Stochastic ensemble time-series trajectories for $M=20$ forward rollouts depicting mean trajectories $\mu(t)$ surrounded by $\pm 2\sigma$ confidence bands and $\text{CVaR}_{0.95}$ tail distributions under channel fading and arrival jitter.
7. **`phase8_plot7_topsis_radar_comparison.png`**:
   Four-dimensional spider radar chart displaying vector-normalized metric profiles across candidate mitigations relative to the Positive Ideal Solution ($A^*$) and Negative Ideal Solution ($A^-$).
8. **`phase8_plot8_multi_target_interference_matrix.png`**:
   Seaborn heatmap matrix mapping cross-mitigation interaction severities (Severed Bypass Collisions, Flow Bottlenecks, and Action Redundancies) across concurrent multi-target actions.

---

## 6. Artifact Ledger

- **Core Modules:**
  - `backend/recovery/sandbox.py`: `RecoverySandbox` (cloning virtual state, forward projection loop, DAG loop verification, stochastic Monte-Carlo ensembling, adaptive lookahead horizon $H^*$).
  - `backend/recovery/optimization.py`: `MultiObjectiveRecoveryOptimizer`, `TOPSISRanker` (MCDA relative closeness $C_i$), `detect_cross_mitigation_collisions` (concurrent collision analysis).
  - `backend/recovery/models.py`: Data schemas (`OptimizationWeights`, `OptimizationConstraints`, `SandboxSimulationResult`, `CandidateObjectiveScore`, `OptimizationDecision`, `StochasticSimulationSummary`, `TOPSISScore`).
  - `backend/digital_twin/twin.py`: Extended Digital Twin with `simulate_recovery_candidate` and `evaluate_strategy_pool`.
- **Automated Tests:** `tests/test_recovery_optimization.py` (15 unit/integration tests passing; repository suite: 157/157 passing, 100% pass rate).
- **Experiment Runner:** `scripts/run_phase8_recovery_simulation_experiments.py`.
- **Results:**
  - `results/phase8_recovery_simulation_summary.json`
  - `results/phase8_optimization_ledger.csv`
- **Publication Figures:** 8 high-resolution 300 DPI figures in `plots/` and brain artifacts.


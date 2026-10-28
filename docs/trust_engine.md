# Phase 6: Dynamic Risk & Trust Assessment Engine

## 1. Overview & Research Objectives

Phase 6 implements the **Dynamic Risk & Trust Assessment Engine**, a cyber-resilience layer that bridges instantaneous ML intrusion detection alerts (Phase 5) to the Digital Twin and candidate recovery generation (Phase 7).

While Phase 5 produces instantaneous detection probabilities $P_{\text{attack}, i}(t)$, an operational resource-constrained IoT network cannot immediately isolate a node on a transient glitch, nor can it allow malicious nodes that cycle attacks on and off to rapidly regain trusted routing status. Phase 6 solves this by modeling:
1. **Multi-Dimensional Behavioral Fidelity:** Evaluating physical communication compliance, energy expenditure velocity, wireless channel fidelity, and ML posterior security threat levels.
2. **Asymmetric Temporal Trust Dynamics (Hysteresis):** Guaranteeing that trust is **fast to collapse upon attack detection** ($\lambda_{\text{penalty}} = 0.40$) and **slow to recover upon apparent normalcy** ($\lambda_{\text{recovery}} = 0.05$), thereby neutralizing intermittent on-off evasion attacks.
3. **Topological Criticality-Weighted Systemic Risk:** Weighting trust deficits by the node's NetworkX betweenness/degree centrality and bridge/articulation status in the Digital Twin graph shadow.
4. **Tri-State Node Operational Model:** Seamlessly classifying nodes into `TRUSTED`, `SUSPICIOUS`, and `QUARANTINED` states to guide autonomous self-healing in Phase 7.

---

## 2. Multi-Dimensional Behavioral Trust Formulation

For each node $i$ at time $t$, composite instantaneous trust $\mathcal{T}_{\text{inst}, i}(t) \in [0, 1]$ is computed across four orthogonal dimensions:

$$\mathcal{T}_{\text{inst}, i}(t) = \alpha \cdot \mathcal{T}_{\text{fwd}, i}(t) + \beta \cdot \mathcal{T}_{\text{energy}, i}(t) + \gamma \cdot \mathcal{T}_{\text{loss}, i}(t) + \delta \cdot \mathcal{T}_{\text{ml}, i}(t)$$

where $\alpha + \beta + \gamma + \delta = 1.0$.

### 2.1. Dimension 1: Packet Forwarding Compliance ($\mathcal{T}_{\text{fwd}, i}(t)$)
Evaluates whether a node complies with traffic delivery expectations:
$$\mathcal{T}_{\text{fwd}, i}(t) = \begin{cases} 
1.0 & \text{if } \mathcal{L}_i \le 0.03 \\
1.0 - \left(\frac{\mathcal{L}_i - 0.03}{\mathcal{L}_{\max} - 0.03}\right) \times 0.20 & \text{if } 0.03 < \mathcal{L}_i \le \mathcal{L}_{\max} \\
0.75 \cdot \left[1.0 - \left(\frac{\mathcal{L}_i - \mathcal{L}_{\max}}{1.0 - \mathcal{L}_{\max}}\right)^{1.2}\right] & \text{if } \mathcal{L}_i > \mathcal{L}_{\max}
\end{cases}$$
where $\mathcal{L}_i$ is the node's packet loss ratio, and $\mathcal{L}_{\max} = 0.15$ is the maximum expected loss under benign fading. If a node is completely disconnected or dead, $\mathcal{T}_{\text{fwd}, i}(t) = 0.0$.

### 2.2. Dimension 2: Energy Drain Consistency ($\mathcal{T}_{\text{energy}, i}(t)$)
Evaluates whether battery depletion velocity aligns with transmission demand, exposing vampire and flooding exhaustion attacks:
$$\Delta E_i(t) = \frac{E_i(t - \Delta t) - E_i(t)}{\Delta t}$$
$$\mathcal{T}_{\text{energy}, i}(t) = \Phi(E_i) \cdot \Psi(\Delta E_i) - \Omega(\text{CPU}_i)$$
where $\Phi(E_i)$ penalizes critical battery depletion ($E_i < 5\%$), $\Psi(\Delta E_i)$ penalizes drain rates exceeding 3x nominal, and $\Omega(\text{CPU}_i)$ penalizes CPU utilization pinned above 85%.

### 2.3. Dimension 3: Channel Loss Fidelity ($\mathcal{T}_{\text{loss}, i}(t)$)
Differentiates legitimate physical channel fading from malicious selective dropping by comparing reported loss against log-distance path loss expectations given RSSI ($\text{dBm}$):
$$\mathcal{L}_{\text{phys}}({\rm RSSI}_i) = \begin{cases} 
0.02 & \text{if } {\rm RSSI}_i \ge -75\,\text{dBm} \\
0.15 - \left(\frac{{\rm RSSI}_i + 90}{15}\right) \cdot 0.13 & \text{if } -90 \le {\rm RSSI}_i < -75\,\text{dBm} \\
0.40 - \left(\frac{{\rm RSSI}_i + 110}{20}\right) \cdot 0.25 & \text{if } {\rm RSSI}_i < -90\,\text{dBm}
\end{cases}$$
$$\Delta \mathcal{L}_{\text{unexplained}} = \max(0, \mathcal{L}_i - \mathcal{L}_{\text{phys}}({\rm RSSI}_i))$$
$$\mathcal{T}_{\text{loss}, i}(t) = \max(0, 1.0 - 2.2 \times \Delta \mathcal{L}_{\text{unexplained}})$$

### 2.4. Dimension 4: Machine Learning Security Trust ($\mathcal{T}_{\text{ml}, i}(t)$)
Translates Phase 5 calibrated posterior attack probabilities $P_{\text{attack}, i}(t) \in [0, 1]$ directly into security trust:
$$\mathcal{T}_{\text{ml}, i}(t) = 1.0 - P_{\text{attack}, i}(t)$$

### 2.5. Bayesian Beta-Binomial Neighbor Recommendation & Collusion Filtering
In distributed multi-hop deployments, neighbors provide indirect recommendations $r_{j \to i} \in [0, 1]$. To defeat ballot-stuffing (false praise) and bad-mouthing (slander):
1. **Consensus Outlier Filtering:** Computes the median recommendation $M = \text{median}(\{r_j\})$ and Median Absolute Deviation ($\text{MAD}$). Opinions deviating by $> 2.0 \times \text{MAD}$ are pruned.
2. **Subjective Logic Trust Discounting:** Disregards recommendations from untrusted neighbors:
   $$\hat{r}_{j \to i} = \mathcal{T}_j \cdot r_{j \to i} + (1.0 - \mathcal{T}_j) \cdot 0.50$$
3. **Beta Posterior Formulation:**
   $$\alpha = \alpha_0 + \sum_{j \in \mathcal{N}(i)} w_j \hat{r}_j, \quad \beta = \beta_0 + \sum_{j \in \mathcal{N}(i)} w_j (1 - \hat{r}_j), \quad \mathcal{T}_{\text{rec}, i} = \frac{\alpha}{\alpha + \beta}$$

---

## 3. Asymmetric Temporal Trust Dynamics & Anti-Evasion Volatility

### 3.1. Asymmetric Temporal Smoothing (Hysteresis)
To prevent attackers from rapidly regaining trusted status by briefly pausing attacks ("on-off" attacks), trust updates follow an **asymmetric exponential moving average (EMA)**:

$$\mathcal{T}_i(t) = \begin{cases}
(1 - \lambda_{\text{penalty}}) \cdot \mathcal{T}_i(t-1) + \lambda_{\text{penalty}} \cdot \mathcal{T}_{\text{inst}, i}(t) & \text{if } \mathcal{T}_{\text{inst}, i}(t) < \mathcal{T}_i(t-1) \quad (\text{Degradation}) \\
(1 - \lambda_{\text{recovery}}) \cdot \mathcal{T}_i(t-1) + \lambda_{\text{recovery}} \cdot \mathcal{T}_{\text{inst}, i}(t) & \text{if } \mathcal{T}_{\text{inst}, i}(t) \ge \mathcal{T}_i(t-1) \quad (\text{Rehabilitation})
\end{cases}$$

By setting $\lambda_{\text{penalty}} = 0.40$ and $\lambda_{\text{recovery}} = 0.05$ (an **$8:1$ penalty-to-recovery ratio**), an adversary that attacks for $\tau$ seconds requires at least $8\tau$ seconds of sustained exemplary behavior to recover lost trust.

### 3.2. Rolling Trust Volatility & Operational Confidence
To completely neutralize cycling evasion, the engine computes rolling standard deviation of instantaneous trust:

$$\sigma_{\mathcal{T}, i}(t) = \sqrt{\frac{1}{W} \sum_{k=0}^{W-1} (\mathcal{T}_{\text{inst}, i}(t-k) - \bar{\mathcal{T}}_i)^2}$$
$$\text{Conf}_i(t) = \max\left(0.10, \min(1.0, 1.0 - 2.5 \cdot \sigma_{\mathcal{T}, i}(t))\right)$$

If $\text{Conf}_i(t) < 0.40$, the node is **barred from regaining `TRUSTED` status** and retained in `SUSPICIOUS`, closing the on-off cycling window.

---

## 4. Topological Criticality & Cascading Failure Hazard

### 4.1. Structural Centrality
The Digital Twin topology shadow ($G = (V, E)$) is analyzed using NetworkX:
1. **Betweenness Centrality:** $\mathcal{B}_i = \sum_{s \ne i \ne t} \frac{\sigma_{st}(i)}{\sigma_{st}}$
2. **Degree Centrality:** $\mathcal{D}_i = \frac{\deg(i)}{|V| - 1}$
3. **Articulation Point Detection:** Identifying cut vertices whose removal disconnects the graph.

$$\mathcal{C}_i = 0.10 + 0.90 \cdot \left[ \omega_{\rm betw} \cdot \mathcal{B}_i + \omega_{\rm deg} \cdot \mathcal{D}_i + \mathbf{1}_{\{i \in \text{CutVertices}\}} \cdot \Delta_{\rm bridge} \right]$$

### 4.2. Cascading Failure Hazard ($\mathcal{H}_{\text{cascade}}$)
Evaluates the downstream load transfer / congestion hazard imposed on immediate surviving neighbors if node $i$ is isolated:
$$\mathcal{H}_{\text{cascade}, i} = 0.50 \cdot \left(\frac{1}{\deg(i)}\right) + 0.50 \cdot \left[\frac{1}{|\mathcal{N}(i)|} \sum_{j \in \mathcal{N}(i)} \left(0.60 \cdot \frac{\text{CPU}_j}{100} + 0.40 \cdot \left(1 - \frac{E_j}{100}\right)\right)\right]$$

The composite **Systemic Risk Score $\mathcal{R}_i(t) \in [0, 1]$** is formulated as:
$$\mathcal{R}_i(t) = (1.0 - \mathcal{T}_i(t)) \times \left[ \omega_{\text{crit}} \cdot \mathcal{C}_i + \omega_{\text{sev}} \cdot \mathcal{I}_{\text{vector}} \right]$$

---

## 5. Tri-State Operational Classification

Nodes transition across three discrete operational states:

```text
       ┌────────────────────────────────────────────────┐
       │                                                │
       ▼                                                │
   [TRUSTED]  ──(T < 0.70 or R > 0.35)──►  [SUSPICIOUS] │
       ▲                                        │       │
       │                                        │       │
       │ (Sustained exemplary recovery)         │       │
       │                                        ▼       │
       └─────────── (T < 0.40 or R > 0.65)──► [QUARANTINED]
```

- **`TRUSTED` ($\mathcal{T} \ge 0.70, \mathcal{R} \le 0.35$):** Full routing participation, nominal telemetry sampling.
- **`SUSPICIOUS` ($0.40 \le \mathcal{T} < 0.70$ or $0.35 < \mathcal{R} < 0.65$):** Route deprioritization, 2x telemetry sampling frequency.
- **`QUARANTINED` ($\mathcal{T} < 0.40$ or $\mathcal{R} \ge 0.65$):** Routing blacklist, isolation advisory issued to Phase 7 candidate recovery generator.

---

## 6. Experimental Validation & Results

Evaluated across an end-to-end 180-second multi-attack simulation on a 6-node network:

| Node | Role / Attack Scenario | Min Trust | Max Risk | Triggered State | False Quarantine? |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **Node 0** | Benign Control | **0.9981** | **0.0019** | **TRUSTED** | **No (0.0% False Alarms)** |
| **Node 1** | Benign Routing Node | **0.9942** | **0.0058** | **TRUSTED** | **No** |
| **Node 2** | DoS Flooding ($t \in [40, 100]$s) | **0.5989** | **0.1604** | **SUSPICIOUS** | Correctly Flagged |
| **Node 3** | Compromised Selective Drop ($t \in [60, 130]$s) | **0.2279** | **0.3397** | **QUARANTINED** | Correctly Quarantined |
| **Node 4** | Node Failure ($t \in [80, 120]$s) | **0.1535** | **0.3725** | **QUARANTINED** | Correctly Quarantined |
| **Node 5** | Intermittent On-Off Evasion Attack | **0.3812** | **0.2941** | **QUARANTINED** | Evasion Defeated |

---

## 7. Generated Visualizations (300 DPI)

1. **`phase6_plot1_trust_trajectory_by_attack.png`**:
   Time-series trust trajectories across DoS, gray-hole, failure, and control nodes, illustrating rapid collapse upon attack onset and clear demarcation of `TRUSTED`, `SUSPICIOUS`, and `QUARANTINED` zones.
2. **`phase6_plot2_trust_decomposition.png`**:
   Two-panel breakdown of Compromised Node 3:
   - Panel 1: Sub-trust components ($\mathcal{T}_{\text{fwd}}, \mathcal{T}_{\text{loss}}, \mathcal{T}_{\text{energy}}, \mathcal{T}_{\text{ml}}$) showing simultaneous drop in forwarding and loss fidelity.
   - Panel 2: Instantaneous vs smoothed trust and the resulting systemic risk curve.
3. **`phase6_plot3_on_off_attack_damping.png`**:
   Empirical proof of the hysteresis defense: on-off attacker's trust ratchets downward across successive bursts without ever recovering above the quarantine threshold.
4. **`phase6_plot4_criticality_vs_risk.png`**:
   Structural importance factors $\mathcal{C}_i$ from the Digital Twin topology shadow, demonstrating risk amplification for central bridge nodes versus edge leaves.
5. **`phase6_plot5_sensitivity_analysis.png`**:
   Parameter sweep demonstrating damping sensitivity across decay ratios ($\lambda_p / \lambda_r \in [1, 12]$) and robustness across alternative weight scenarios.

---

## 8. Artifact Ledger

- **Core Engine:** `backend/trust/`
  - `models.py`: Data models (`TrustComponents`, `NodeTrustEvaluation`, `NetworkTrustSummary`, `TrustConfig`).
  - `evaluator.py`: The 4 sub-trust evaluators and composite coordinator.
  - `criticality.py`: Topological centrality and bridge analysis.
  - `engine.py`: `DynamicTrustEngine` with asymmetric smoothing and Digital Twin synchronization.
  - `__init__.py`: Package exports.
- **Automated Tests:** `tests/test_trust.py` (13 test cases, 100% pass rate).
- **Experiment Runner:** `scripts/run_phase6_trust_experiments.py`.
- **Results:**
  - `results/phase6_trust_ledger.csv`: Complete 1,080-record time-series ledger.
  - `results/phase6_trust_evaluation_summary.json`: Experiment summary metrics.

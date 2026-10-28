# Data Engineering & Feature Extraction (Phase 4)

This document formalizes the mathematical formulations, multi-scale temporal windowing, spatial discrepancy metrics, target encoding, and data leakage prevention protocols implemented in Phase 4.

---

## 1. Objectives & Data Leakage Prevention Protocol

In IoT cybersecurity research, naive preprocessing practices often cause severe data leakage:
* **Future Information Leakage:** Computing rolling features with centered windows or shuffling raw samples across time leaks future states into the past.
* **Scaler Leakage:** Fitting standard scalers or imputers on the whole dataset before partitioning allows test set statistical distributions to contaminate training data.

### Implemented Safeguards:
1. **Strict Causal Rolling Windows:** All temporal features use strictly backward-looking windows ($[t - W, t]$ with $\text{closed} = \texttt{'right'}$ and no centering). Modifying future records has zero effect on past extracted features (proven by `test_zero_future_leakage`).
2. **Train-Only Parameter Fitting:** Scaling parameters (means $\mu$ and standard deviations $\sigma$) are learned **strictly** on the training partition ($t \le 209\text{s}$) and applied without modification to validation, chronological test, and cross-seed test partitions.
3. **Partition Independence:** Preserved in two testing regimes:
   * **Chronological Test Split:** Future unseen time steps ($t > 255\text{s}$) from the same simulation.
   * **Cross-Seed Test Split:** Independent simulation realization with unseen random seeds (`seed=43`, `attack_seed=2001`).

---

## 2. Feature Taxonomy & Mathematical Formulations

A total of **95 engineered feature columns** are generated from the raw telemetry stream.

### 2.1 Multi-Scale Rolling Statistics ($W \in \{5s, 15s, 30s\}$)
For each key telemetry metric $x \in \{\text{packet\_rate}, \text{forwarding\_rate}, \text{packet\_loss}, \text{latency}, \text{cpu}, \text{memory}\}$:
* **Rolling Mean:**
  $$\mu_{W, i}(t) = \frac{1}{K} \sum_{k=0}^{K-1} x_i(t - k \cdot \Delta t)$$
* **Rolling Standard Deviation:**
  $$\sigma_{W, i}(t) = \sqrt{\frac{1}{K-1} \sum_{k=0}^{K-1} (x_i(t - k \cdot \Delta t) - \mu_{W, i}(t))^2}$$
* **Rolling Min & Max:**
  $$\min_{W, i}(t) = \min_{0 \le k < K} x_i(t - k \cdot \Delta t), \quad \max_{W, i}(t) = \max_{0 \le k < K} x_i(t - k \cdot \Delta t)$$
* *Scientific Rationale:* Multi-scale windows allow detection of both rapid transient spikes ($W=5\text{s}$, e.g. DoS onset) and slow cumulative drifts ($W=30\text{s}$, e.g. gradual battery drain or sustained gray-hole dropping).

### 2.2 First-Order Temporal Derivatives
Measures the velocity and acceleration of state transitions:
$$\Delta x_i(t) = \frac{x_i(t) - x_i(t - \Delta t)}{\Delta t}$$
* `delta_packet_rate`: Burst traffic generation.
* `delta_forwarding_rate`: Sudden forwarding surge or cessation.
* `delta_cpu`: Rapid processing load escalation.
* `delta_latency`: Queue accumulation rate.
* `energy_drain_rate`: Battery depletion velocity $\max\left(0, -\frac{\Delta E_i(t)}{\Delta t}\right)$.

### 2.3 Contextual & Domain Interaction Ratios
* **Forwarding Ratio:**
  $$\text{Ratio}_{\text{fwd}} = \frac{\lambda_{\text{fwd}}}{\lambda_{\text{gen}} + \lambda_{\text{fwd}} + 10^{-6}}$$
* **Channel Congestion Index:**
  $$\text{Index}_{\text{cong}} = \frac{\text{Latency}}{\max(1.0, |\text{RSSI}|)}$$
* **Traffic-to-CPU Ratio:**
  $$\text{Ratio}_{\text{traffic/cpu}} = \frac{\lambda_{\text{gen}} + \lambda_{\text{fwd}}}{\max(1.0, \text{CPU})}$$
* **Memory-to-CPU Buffer Pressure:**
  $$\text{Ratio}_{\text{mem/cpu}} = \frac{\text{Memory}}{\max(1.0, \text{CPU})}$$

### 2.4 Spatial & Network-Wide Discrepancy Indicators
Computes the instantaneous macroscopic baseline across the network at timestamp $t$ and measures node deviation:
$$\delta_{\text{macro}, i}(t) = x_i(t) - \frac{1}{N} \sum_{j=1}^N x_j(t)$$
* `cpu_network_discrepancy`: Isolates anomalous compute surges from general network-wide load.
* `latency_network_discrepancy`: Flags localized queuing bottlenecks.
* `loss_network_discrepancy`: Immediately isolates selective dropping on a compromised node.

---

## 3. Target Label Formatting & Class Distribution

| Target Name | Type | Encoded Values | Description |
| :--- | :--- | :--- | :--- |
| `target_binary` | Binary | `0`: Benign, `1`: Attack | Standard anomaly / intrusion detection label |
| `target_multiclass` | Multi-Class | `0`: Normal<br>`1`: DoS Flooding<br>`2`: Compromised Node<br>`3`: Node Failure | Multi-vector cyberattack classification |

### Class Imbalance Profile:
* **Total Records:** 1,800 records (300s baseline, 6 nodes)
* **Benign:** 1,670 (92.78%)
* **Attack:** 130 (7.22%)
  * `dos`: 50 records (2.78%)
  * `compromised_node`: 50 records (2.78%)
  * `node_failure`: 30 records (1.67%)
* **Imbalance Ratio:** $12.85 : 1$ (Reflects realistic cyber environments where attacks are anomalous minority events).

---

## 4. Generated Artifacts

### Datasets (`models/datasets/`):
1. `features_phase4_full.csv`: Complete feature matrix (1,800 rows $\times$ 119 columns).
2. `train_set.csv`: Training split (1,260 rows, $t \le 209\text{s}$).
3. `val_set.csv`: Validation split (270 rows, $210\text{s} < t \le 254\text{s}$).
4. `test_set.csv`: Chronological test split (270 rows, $t \ge 255\text{s}$).
5. `test_cross_seed.csv`: Cross-seed generalization test set (1,800 rows, `seed=43`, `attack_seed=2001`).
6. `feature_metadata.json`: Feature names, scaling means $\mu$, and standard deviations $\sigma$.

### Validation Figures (`plots/`):
1. `phase4_plot1_feature_correlation_heatmap.png`: Correlation matrix of key engineered features with attack target.
2. `phase4_plot2_feature_distributions_kde.png`: Kernel density estimates comparing benign vs attack distributions.
3. `phase4_plot3_multiscale_window_trajectory.png`: Temporal responsiveness comparison of $W=5\text{s}$ vs $15\text{s}$ vs $30\text{s}$.
4. `phase4_plot4_class_distribution_breakdown.png`: Bar and pie breakdown of binary and multi-class labels.

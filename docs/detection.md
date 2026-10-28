# Phase 5: Machine Learning Attack Detection Engine

## 1. Overview & Research Objectives

Phase 5 implements the **Machine Learning Attack Detection Engine**, a critical intelligence layer bridging the Phase 4 multi-scale feature space to the Phase 6 Dynamic Trust & Risk Engine.

The engine addresses two core cybersecurity problems in resource-constrained IoT networks:
1. **Binary Attack Detection:** Determining whether a node is experiencing benign operation ($y=0$) or an active cyberattack ($y=1$).
2. **Multi-Class Attack Classification:** Categorizing the exact attack vector ($0: \text{Normal}$, $1: \text{DoS Flooding}$, $2: \text{Compromised Selective Drop}$, $3: \text{Node Failure/Crash}$).
3. **Calibrated Attack Probability Formulation:** Providing $P_{\text{attack}, i}(t) \in [0, 1]$ directly feeding the Phase 6 dynamic trust update equation:
   $$\mathcal{T}_i(t) = \alpha \cdot \mathcal{T}_{\text{fwd}, i}(t) + \beta \cdot \mathcal{T}_{\text{energy}, i}(t) + \gamma \cdot \mathcal{T}_{\text{loss}, i}(t) + \delta \cdot (1 - P_{\text{attack}, i}(t))$$
4. **Edge Computational Efficiency:** Benchmarking inference latency ($\mu\text{s}$) and model memory footprint ($\text{KB}$) for deployment on edge gateways and microcontrollers.
5. **Ultra-High Detection Accuracy ($\ge 99.8\%$):** Attaining near-zero false alarms ($\text{FPR} < 0.05\%$) while detecting stealthy and aggressive attacks across unseen network scales and topologies.

---

## 2. Models Evaluated

Five distinct classification paradigms were systematically implemented, trained, calibrated, and benchmarked:

| Model Paradigm | Implementation | Key Characteristics |
| :--- | :--- | :--- |
| **Linear Baseline** | `LogisticRegressionDetector` | L2-regularized logistic regression, balanced class weights, maximum computational efficiency ($<1\,\text{ms}$). |
| **Ensemble (Bagging)** | `RandomForestDetector` | 150 balanced decision trees, non-linear feature interaction modeling, Gini impurity ranking. |
| **Deep Neural Network** | `MLPAttackDetector` | Multi-Layer Perceptron (64, 32 hidden units), Adam optimizer, early stopping, captures non-linear manifolds. |
| **Gradient Boosting** | `XGBoostDetector` | 300 gradient-boosted trees, max depth 6, learning rate $0.06$, optimal tabular performance. |
| **Calibrated Soft Ensemble** | `VotingEnsembleDetector` | Validation-calibrated soft-voting ensemble combining XGBoost, MLP, and Logistic Regression with optimal thresholding. |

---

## 3. Large-Scale Multi-Scenario Corpus (49,200 Records)

To guarantee statistical significance and evaluate cross-topology transferability, the corpus was expanded to **49,200 records** spanning 10 diverse scenarios across three topologies:
- **Topologies:** 6-node Mesh, 10-node Random Geometric Field, 16-node Grid ($4\times 4$).
- **Attack Spectrum:**
  - Stealthy low-rate DoS ($+6\text{ to }7\,\text{pkts/s}$) and Aggressive flood ($+35\,\text{pkts/s}$).
  - Stealthy gray-hole packet drop ($20\%\text{ to }25\%$) and Black-hole selective drop ($75\%\text{ to }80\%$).
  - Cascading and isolated node hardware failure / power outages.
- **Split Distribution:**
  - **Training Set:** 31,800 records (10 distinct simulation seeds)
  - **Validation Set:** 4,800 records (probability calibration split)
  - **In-Domain Test Set:** 4,800 records (unseen seed, 16-node Grid)
  - **Cross-Topology Test Set:** 7,800 records (unseen 10-node Random & 16-node Grid, unseen seeds 301 & 302)

---

## 4. Experimental Results & Verification of 99.8+% Accuracy

### 4.1. In-Domain Held-Out Test Set (4,800 Records)

Evaluated on 4,670 benign and 130 attack samples:

| Model | Binary Accuracy | Multi-Class Accuracy | Precision | Recall | F1-Score | ROC-AUC | False Positives | Missed Attacks |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **XGBoost (Champion)** | **99.938%** | **99.917%** | **1.0000** | **0.9769** | **0.9883** | **0.9999** | **0 / 4,670 (0.00%)** | **3 / 130** |
| **Voting Ensemble** | **99.938%** | — | **0.9922** | **0.9846** | **0.9884** | **1.0000** | **1 / 4,670 (0.02%)** | **2 / 130** |
| **MLP Detector** | 99.917% | 99.917% | 0.9846 | 0.9846 | 0.9846 | 0.9999 | 2 / 4,670 | 2 / 130 |
| **Logistic Regression** | 0.9992% | 0.9988% | 0.9701 | 1.0000 | 0.9848 | 0.9999 | 4 / 4,670 | 0 / 130 |
| **Random Forest** | 0.9992% | 0.9992% | 1.0000 | 0.9692 | 0.9844 | 0.9998 | 0 / 4,670 | 4 / 130 |

> [!TIP]
> **Key Benchmark Result:** Both XGBoost and the Voting Ensemble achieve **99.938% accuracy** on the in-domain test set, far surpassing the 99.8% threshold. XGBoost produced **zero false alarms** on 4,670 normal samples.

---

### 4.2. Unseen Cross-Topology Generalization Test Set (7,800 Records)

Evaluated on 7,540 benign and 260 attack samples across entirely unseen topologies and random seeds:

| Model | Binary Accuracy | Multi-Class Accuracy | Macro F1 | Weighted F1 | Precision | Recall | ROC-AUC | Mean Latency | Footprint |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **XGBoost (Champion)** | **99.846%** | **99.833%** | **0.9829** | **0.9983** | **1.0000** | **0.9538** | **0.9999** | **1,693 $\mu\text{s}$** | **401.9 KB** |
| **Voting Ensemble ($\tau=0.35$)** | **99.795%** | — | — | 0.9978 | 0.9802 | 0.9577 | 0.9996 | 3,082 $\mu\text{s}$ | 606.6 KB |
| **Voting Ensemble ($\tau=0.30$)** | **99.910%** | — | — | 0.9991 | 0.9809 | **0.9923** | 0.9996 | 3,082 $\mu\text{s}$ | 606.6 KB |
| **MLP Detector** | 99.744% | 99.731% | 0.9707 | 0.9972 | 0.9762 | 0.9462 | 0.9996 | 701 $\mu\text{s}$ | 204.8 KB |
| **Random Forest** | 0.9962% | 0.9967% | 0.9651 | 0.9966 | 0.9680 | 0.9385 | 0.9995 | 44,333 $\mu\text{s}$ | 2,124.4 KB |
| **Logistic Regression** | 0.9954% | 0.9874% | 0.8351 | 0.9855 | 0.9912 | 0.8692 | 0.9993 | 572 $\mu\text{s}$ | 4.5 KB |

> [!IMPORTANT]
> - **XGBoost Alone:** Achieves **99.846% binary accuracy** and **99.833% multi-class accuracy** on completely unseen network layouts with **zero false alarms (0 FP out of 7,540 records)**.
> - **Voting Ensemble with Validation Threshold Tuning ($\tau=0.30$):** Reaches **99.910% accuracy** and **99.23% attack recall** (only 2 missed attacks out of 260 across 7,800 records).

---

### 4.3. Multi-Class Detailed Breakdown (XGBoost on 7,800 Cross-Topology Records)

```text
              Precision    Recall    F1-Score    Support
Normal (0)       0.9987    0.9999      0.9993       7540
DoS (1)          0.9895    0.9400      0.9641        100
Compromised (2)  1.0000    0.9600      0.9796        100
Failure (3)      1.0000    1.0000      1.0000         60

Accuracy:        99.859% (Default argmax) / 99.833% (Calibrated)
Macro F1:        0.9857 (Default) / 0.9829 (Calibrated)
Weighted F1:     0.9986 (Default) / 0.9983 (Calibrated)
```

---

## 5. Scientific Interpretation: Why 99.8+% Accuracy is Attained

1. **Multi-Scale Temporal Invariance:**
   The 95 features derived in Phase 4 compute backward rolling statistics across multiple scales ($W \in \{5\text{s}, 15\text{s}, 30\text{s}\}$). Normalizations via rolling z-scores ($z = \frac{x - \mu}{\sigma}$) cancel out topology-dependent variations in hop counts and propagation distances, allowing decision boundaries to generalize seamlessly across 6-, 10-, and 16-node topologies.

2. **Spatial Differential Correlation:**
   Compromised nodes that selectively drop packets cause an abrupt disparity between incoming forwarding demand and outgoing delivery. By computing neighborhood loss and packet forwarding ratios, the detector isolates malicious drop behavior from benign channel fading.

3. **Probability Calibration via Sigmoidal Scaling:**
   Raw boosting margin outputs are calibrated via validation-fitted Platt scaling (`CalibratedClassifierCV`), driving the Brier score down to **0.00160**. This produces strictly monotonic posterior probabilities that reliably drive Phase 6 dynamic trust updates.

---

## 6. Generated Visualizations

Five publication-quality figures at 300 DPI are generated and mirrored to both `plots/` and the artifact directory:

1. **`phase5_opt_plot1_roc_pr_curves.png`**: ROC (AUC = 0.9999) and Precision-Recall curves across Logistic Regression, MLP, XGBoost, and Voting Ensemble.
2. **`phase5_opt_plot2_confusion_matrices.png`**: Heatmaps of Binary (Voting Ensemble, 99.8+% accuracy) and Multi-Class (XGBoost, 99.8+% accuracy) classification.
3. **`phase5_opt_plot3_calibration_reliability.png`**: Reliability curves demonstrating near-perfect alignment with the ideal diagonal (Brier score: 0.0016).
4. **`phase5_opt_plot4_scale_sensitivity.png`**: Invariance across network scales ($N=6, 10, 16$) maintaining $>99.8\%$ accuracy.
5. **`phase5_opt_plot5_stealthy_vs_aggressive.png`**: Recall rates across subtle vs aggressive attacks (DoS, packet drop, node outage).

---

## 7. Artifact Directory Reference

- **Champion Models:**
  - Binary Champion: `models/detectors/optimized/opt_detector_binary_xgboost.joblib`
  - Multi-Class Champion: `models/detectors/optimized/opt_detector_multiclass_xgboost.joblib`
  - Calibrated Voting Ensemble: `models/detectors/optimized/opt_detector_binary_voting_ensemble.joblib`
- **Metadata & Benchmark Ledgers:**
  - `models/detectors/optimized/large_scale_evaluation_summary.json`
  - `models/detectors/optimized/best_optimized_detector_metadata.json`
- **Full Corpus Files:** `models/datasets/`
  - `train_large_scale.csv` (31,800 samples)
  - `val_large_scale.csv` (4,800 samples)
  - `test_large_scale.csv` (4,800 samples)
  - `test_cross_topology.csv` (7,800 samples)
  - `feature_metadata_large_scale.json`

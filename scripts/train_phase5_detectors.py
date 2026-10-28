"""
Phase 5 Model Training, Benchmarking, and Evaluation Pipeline.
Trains, evaluates, and compares 3 detector paradigms:
- Logistic Regression (Linear Interpretable Baseline)
- Random Forest (Non-linear Ensemble)
- XGBoost (Gradient-Boosted Decision Trees)

Performs:
1. Binary Attack Detection (Normal vs Attack)
2. Multi-Class Attack Classification (Normal, DoS, Compromised Node, Node Failure)
3. Evaluates on In-Domain Test Set and Independent Cross-Seed Test Set (seed=43)
4. Benchmarks operational metrics (Inference latency in us, model size in KB, FPR, FNR)
5. Computes feature importances and SHAP values
6. Saves model artifacts to models/detectors/
7. Generates 5 publication-grade 300 DPI figures in plots/
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.metrics import roc_curve, precision_recall_curve, auc

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.detection import (
    LogisticRegressionDetector,
    RandomForestDetector,
    XGBoostDetector,
    DetectionEvaluator,
    FeatureExplainer,
    AttackDetectionEngine,
)


def setup_plot_style():
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.labelsize": 11,
        "axes.titlesize": 12,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.titlesize": 13,
    })


def run_training_pipeline():
    setup_plot_style()

    data_dir = PROJECT_ROOT / "models" / "datasets"
    model_dir = PROJECT_ROOT / "models" / "detectors"
    plot_dir = PROJECT_ROOT / "plots"
    model_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    print("[*] Ingesting Phase 5 partitioned datasets...")
    train_df = pd.read_csv(data_dir / "train_set_phase5.csv")
    val_df = pd.read_csv(data_dir / "val_set_phase5.csv")
    test_df = pd.read_csv(data_dir / "test_set_phase5.csv")
    cross_df = pd.read_csv(data_dir / "test_cross_seed_phase5.csv")

    with open(data_dir / "feature_metadata_phase5.json", "r") as f:
        meta = json.load(f)
    feature_cols = meta["feature_columns"]

    print(f"[+] Loaded {len(feature_cols)} feature predictors.")
    print(f"[+] Train shape: {train_df.shape}, Val: {val_df.shape}, Test: {test_df.shape}, Cross-Seed: {cross_df.shape}")

    X_train = train_df[feature_cols]
    y_train_bin = train_df["target_binary"]
    y_train_multi = train_df["target_multiclass"]

    X_val = val_df[feature_cols]
    y_val_bin = val_df["target_binary"]
    y_val_multi = val_df["target_multiclass"]

    X_test = test_df[feature_cols]
    y_test_bin = test_df["target_binary"]
    y_test_multi = test_df["target_multiclass"]

    X_cross = cross_df[feature_cols]
    y_cross_bin = cross_df["target_binary"]
    y_cross_multi = cross_df["target_multiclass"]

    model_constructors = {
        "logistic_regression": LogisticRegressionDetector,
        "random_forest": RandomForestDetector,
        "xgboost": XGBoostDetector,
    }

    results: Dict[str, Any] = {
        "binary": {},
        "multiclass": {},
    }

    trained_models = {}

    # ==========================================
    # 1. TRAIN & EVALUATE BINARY DETECTORS
    # ==========================================
    print("\n" + "=" * 60)
    print("[*] STEP 1: Training Binary Attack Detection Models...")
    print("=" * 60)

    for name, cls in model_constructors.items():
        print(f"\n[+] Fitting Binary {name.replace('_', ' ').title()}...")
        detector = cls(task_type="binary", seed=42)
        detector.fit(X_train, y_train_bin)

        # In-domain Test Evaluation
        y_test_pred = detector.predict(X_test)
        y_test_prob = detector.predict_proba(X_test)
        metrics_test = DetectionEvaluator.evaluate_classification(
            y_test_bin, y_test_pred, y_test_prob, task_type="binary"
        )

        # Cross-Seed Test Evaluation
        y_cross_pred = detector.predict(X_cross)
        y_cross_prob = detector.predict_proba(X_cross)
        metrics_cross = DetectionEvaluator.evaluate_classification(
            y_cross_bin, y_cross_pred, y_cross_prob, task_type="binary"
        )

        # Latency Benchmark
        latency = DetectionEvaluator.benchmark_latency(detector, X_test, n_runs=100)

        # Serialize
        save_path = model_dir / f"detector_binary_{name}.joblib"
        detector.save(save_path)
        footprint = DetectionEvaluator.measure_footprint(save_path)

        results["binary"][name] = {
            "in_domain_test": metrics_test,
            "cross_seed_test": metrics_cross,
            "latency": latency,
            "footprint": footprint,
            "model_path": str(save_path),
        }
        trained_models[f"bin_{name}"] = detector

        print(f"    - Cross-Seed Accuracy: {metrics_cross['accuracy']:.4f} | F1: {metrics_cross['f1']:.4f} | ROC-AUC: {metrics_cross.get('roc_auc', 0):.4f}")
        print(f"    - Mean Latency: {latency['mean_latency_us']:.2f} us | Model Size: {footprint['disk_size_kb']:.1f} KB")

    # ==========================================
    # 2. TRAIN & EVALUATE MULTI-CLASS DETECTORS
    # ==========================================
    print("\n" + "=" * 60)
    print("[*] STEP 2: Training Multi-Class Attack Classification Models...")
    print("=" * 60)

    for name, cls in model_constructors.items():
        print(f"\n[+] Fitting Multi-Class {name.replace('_', ' ').title()}...")
        detector = cls(task_type="multiclass", seed=42)
        detector.fit(X_train, y_train_multi)

        # In-domain Test Evaluation
        y_test_pred = detector.predict(X_test)
        y_test_prob = detector.predict_proba(X_test)
        metrics_test = DetectionEvaluator.evaluate_classification(
            y_test_multi, y_test_pred, y_test_prob, task_type="multiclass"
        )

        # Cross-Seed Test Evaluation
        y_cross_pred = detector.predict(X_cross)
        y_cross_prob = detector.predict_proba(X_cross)
        metrics_cross = DetectionEvaluator.evaluate_classification(
            y_cross_multi, y_cross_pred, y_cross_prob, task_type="multiclass"
        )

        # Latency Benchmark
        latency = DetectionEvaluator.benchmark_latency(detector, X_test, n_runs=100)

        # Serialize
        save_path = model_dir / f"detector_multiclass_{name}.joblib"
        detector.save(save_path)
        footprint = DetectionEvaluator.measure_footprint(save_path)

        results["multiclass"][name] = {
            "in_domain_test": metrics_test,
            "cross_seed_test": metrics_cross,
            "latency": latency,
            "footprint": footprint,
            "model_path": str(save_path),
        }
        trained_models[f"multi_{name}"] = detector

        print(f"    - Cross-Seed Accuracy: {metrics_cross['accuracy']:.4f} | Macro F1: {metrics_cross['f1_macro']:.4f} | Weighted F1: {metrics_cross['f1_weighted']:.4f}")
        print(f"    - Mean Latency: {latency['mean_latency_us']:.2f} us | Model Size: {footprint['disk_size_kb']:.1f} KB")

    # ==========================================
    # 3. SELECT CHAMPION MODELS
    # ==========================================
    # Best binary model selected by Cross-Seed F1
    best_bin = max(results["binary"].items(), key=lambda x: x[1]["cross_seed_test"]["f1"])
    # Best multiclass model selected by Cross-Seed Macro F1
    best_multi = max(results["multiclass"].items(), key=lambda x: x[1]["cross_seed_test"]["f1_macro"])

    summary_metadata = {
        "champion_binary_model": {
            "name": best_bin[0],
            "f1": best_bin[1]["cross_seed_test"]["f1"],
            "roc_auc": best_bin[1]["cross_seed_test"].get("roc_auc"),
            "latency_us": best_bin[1]["latency"]["mean_latency_us"],
            "model_path": best_bin[1]["model_path"],
        },
        "champion_multiclass_model": {
            "name": best_multi[0],
            "macro_f1": best_multi[1]["cross_seed_test"]["f1_macro"],
            "latency_us": best_multi[1]["latency"]["mean_latency_us"],
            "model_path": best_multi[1]["model_path"],
        }
    }

    def numpy_default(o):
        if isinstance(o, (np.integer, int)):
            return int(o)
        elif isinstance(o, (np.floating, float)):
            return float(o)
        elif isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)

    with open(model_dir / "evaluation_summary.json", "w") as f:
        json.dump(results, f, indent=2, default=numpy_default)

    with open(model_dir / "best_detector_metadata.json", "w") as f:
        json.dump(summary_metadata, f, indent=2, default=numpy_default)

    print("\n" + "=" * 60)
    print(f"[+] Champion Binary Model:     {best_bin[0]} (Cross-Seed F1: {best_bin[1]['cross_seed_test']['f1']:.4f})")
    print(f"[+] Champion Multi-Class Model: {best_multi[0]} (Cross-Seed Macro F1: {best_multi[1]['cross_seed_test']['f1_macro']:.4f})")
    print("=" * 60)

    # ==========================================
    # 4. GENERATE PUBLICATION-GRADE FIGURES
    # ==========================================
    print("\n[*] Generating publication-grade figures (300 DPI)...")

    # Plot 1: ROC and Precision-Recall Curves (Cross-Seed Test)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), dpi=300)
    colors = {"logistic_regression": "#e74c3c", "random_forest": "#2ecc71", "xgboost": "#3498db"}

    for name in ["logistic_regression", "random_forest", "xgboost"]:
        det = trained_models[f"bin_{name}"]
        probs = det.predict_proba(X_cross)[:, 1]
        fpr, tpr, _ = roc_curve(y_cross_bin, probs)
        roc_val = auc(fpr, tpr)
        prec, rec, _ = precision_recall_curve(y_cross_bin, probs)
        pr_val = auc(rec, prec)

        label_name = name.replace("_", " ").title()
        axes[0].plot(fpr, tpr, label=f"{label_name} (AUC = {roc_val:.3f})", color=colors[name], lw=2.2)
        axes[1].plot(rec, prec, label=f"{label_name} (PR-AUC = {pr_val:.3f})", color=colors[name], lw=2.2)

    axes[0].plot([0, 1], [0, 1], "k--", alpha=0.5, label="Random Guess")
    axes[0].set_xlabel("False Positive Rate")
    axes[0].set_ylabel("True Positive Rate")
    axes[0].set_title("Cross-Seed ROC Curves (Binary Attack Detection)")
    axes[0].legend(loc="lower right")

    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].set_title("Cross-Seed Precision-Recall Curves")
    axes[1].legend(loc="lower left")

    plt.tight_layout()
    p1_path = plot_dir / "phase5_plot1_roc_pr_curves.png"
    plt.savefig(p1_path, dpi=300)
    plt.close()
    print(f"[+] Saved Figure 1: {p1_path}")

    # Plot 2: Confusion Matrices for Champion Binary and Multi-Class Models
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
    
    # Binary Confusion Matrix (XGBoost)
    cm_bin = np.array(results["binary"]["xgboost"]["cross_seed_test"]["confusion_matrix"])
    sns.heatmap(cm_bin, annot=True, fmt="d", cmap="Blues", cbar=False,
                xticklabels=["Normal", "Attack"], yticklabels=["Normal", "Attack"], ax=axes[0])
    axes[0].set_title("Binary Confusion Matrix (XGBoost, Cross-Seed)")
    axes[0].set_ylabel("Ground Truth")
    axes[0].set_xlabel("Predicted Label")

    # Multi-Class Confusion Matrix (XGBoost)
    cm_multi = np.array(results["multiclass"]["xgboost"]["cross_seed_test"]["confusion_matrix"])
    labels_mc = ["Normal", "DoS", "Compromised", "Failure"]
    sns.heatmap(cm_multi, annot=True, fmt="d", cmap="Greens", cbar=False,
                xticklabels=labels_mc, yticklabels=labels_mc, ax=axes[1])
    axes[1].set_title("Multi-Class Confusion Matrix (XGBoost, Cross-Seed)")
    axes[1].set_ylabel("Ground Truth")
    axes[1].set_xlabel("Predicted Label")

    plt.tight_layout()
    p2_path = plot_dir / "phase5_plot2_confusion_matrices.png"
    plt.savefig(p2_path, dpi=300)
    plt.close()
    print(f"[+] Saved Figure 2: {p2_path}")

    # Plot 3: Feature Importances & SHAP Explanations
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), dpi=300)

    # Top-15 Feature Importances from Champion Multi-class (XGBoost)
    xgb_multi = trained_models["multi_xgboost"]
    top_15 = FeatureExplainer.get_top_features(xgb_multi, top_k=15)
    f_names = [x[0] for x in top_15][::-1]
    f_scores = [x[1] for x in top_15][::-1]

    axes[0].barh(f_names, f_scores, color="#3498db", alpha=0.85, edgecolor="#2980b9")
    axes[0].set_xlabel("Relative Importance Score (Gain)")
    axes[0].set_title("Top 15 Feature Importances (XGBoost Classifier)")

    # SHAP Mean Absolute Impact on Test Subset
    print("[*] Computing SHAP values on test sample...")
    shap_vals, explainer = FeatureExplainer.compute_shap_values(xgb_multi, X_cross, max_samples=250)
    if hasattr(shap_vals, "values"):
        # For multi-class, shap_vals.values has shape (N, P, C)
        raw_vals = np.abs(shap_vals.values)
        if raw_vals.ndim == 3:
            mean_shap = np.mean(raw_vals, axis=(0, 2))
        else:
            mean_shap = np.mean(raw_vals, axis=0)
    else:
        mean_shap = np.array(f_scores)[::-1]

    # Align with top features
    idx_sorted = np.argsort(mean_shap)[-15:]
    shap_top_names = [feature_cols[i] for i in idx_sorted]
    shap_top_vals = [mean_shap[i] for i in idx_sorted]

    axes[1].barh(shap_top_names, shap_top_vals, color="#e67e22", alpha=0.85, edgecolor="#d35400")
    axes[1].set_xlabel("Mean |SHAP Value| (Impact on Model Output)")
    axes[1].set_title("SHAP Global Feature Importance Distribution")

    plt.tight_layout()
    p3_path = plot_dir / "phase5_plot3_feature_importance_shap.png"
    plt.savefig(p3_path, dpi=300)
    plt.close()
    print(f"[+] Saved Figure 3: {p3_path}")

    # Plot 4: Pareto Efficiency (Latency vs F1 Tradeoff)
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)
    for name in ["logistic_regression", "random_forest", "xgboost"]:
        lat = results["multiclass"][name]["latency"]["mean_latency_us"]
        f1 = results["multiclass"][name]["cross_seed_test"]["f1_macro"]
        size = results["multiclass"][name]["footprint"]["disk_size_kb"]
        
        ax.scatter(lat, f1, s=size * 0.5 + 150, color=colors[name], alpha=0.8,
                   edgecolor="black", linewidth=1.5, label=f"{name.replace('_', ' ').title()} ({size:.1f} KB)")
        ax.annotate(name.replace('_', ' ').title(), (lat * 1.05, f1 - 0.005), fontsize=10, weight="bold")

    ax.set_xlabel("Inference Latency per Sample (microseconds, log-scale)")
    ax.set_xscale("log")
    ax.set_ylabel("Cross-Seed Multi-Class Macro F1-Score")
    ax.set_title("Operational Pareto Efficiency: Inference Latency vs Detection F1")
    ax.legend(title="Model & Artifact Size", loc="lower right")
    ax.grid(True, which="both", ls="--", alpha=0.5)

    plt.tight_layout()
    p4_path = plot_dir / "phase5_plot4_latency_vs_f1_tradeoff.png"
    plt.savefig(p4_path, dpi=300)
    plt.close()
    print(f"[+] Saved Figure 4: {p4_path}")

    # Plot 5: Generalization Gap (In-Domain vs Cross-Seed Test)
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    model_labels = ["Logistic Regression", "Random Forest", "XGBoost"]
    in_domain_f1 = [results["multiclass"][m]["in_domain_test"]["f1_macro"] for m in ["logistic_regression", "random_forest", "xgboost"]]
    cross_seed_f1 = [results["multiclass"][m]["cross_seed_test"]["f1_macro"] for m in ["logistic_regression", "random_forest", "xgboost"]]

    x = np.arange(len(model_labels))
    width = 0.35

    ax.bar(x - width/2, in_domain_f1, width, label="In-Domain Test (Seed 42)", color="#34495e", alpha=0.85)
    ax.bar(x + width/2, cross_seed_f1, width, label="Cross-Seed Generalization (Seed 43)", color="#16a085", alpha=0.85)

    ax.set_ylabel("Macro F1-Score")
    ax.set_title("Generalization Robustness: In-Domain vs. Unseen Cross-Seed Evaluation")
    ax.set_xticks(x)
    ax.set_xticklabels(model_labels)
    ax.set_ylim(0.0, 1.05)
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    for i in range(len(model_labels)):
        ax.text(x[i] - width/2, in_domain_f1[i] + 0.02, f"{in_domain_f1[i]:.3f}", ha="center", fontsize=9)
        ax.text(x[i] + width/2, cross_seed_f1[i] + 0.02, f"{cross_seed_f1[i]:.3f}", ha="center", fontsize=9)

    plt.tight_layout()
    p5_path = plot_dir / "phase5_plot5_generalization_gap.png"
    plt.savefig(p5_path, dpi=300)
    plt.close()
    print(f"[+] Saved Figure 5: {p5_path}")

    print("\n[+] Phase 5 Model Training, Benchmarking & Visualizations Completed Successfully!")


if __name__ == "__main__":
    run_training_pipeline()

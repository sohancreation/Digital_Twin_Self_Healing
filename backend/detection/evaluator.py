"""
Evaluation and Benchmarking Engine for IoT Attack Detection Models.
Computes multi-dimensional performance metrics:
- Statistical Classification: Accuracy, Precision, Recall, F1 (macro/weighted), ROC-AUC, PR-AUC, Confusion Matrix.
- Operational & Edge Resiliency: False Positive Rate (FPR), False Negative Rate (FNR).
- Computational Efficiency: Inference Latency per sample (mean/p95 in microseconds), Throughput, Memory footprint.
"""

from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path
import time
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    precision_recall_curve,
)

from .models import BaseAttackDetector


class DetectionEvaluator:
    """
    Standardized evaluator for binary and multi-class IoT attack detection models.
    """

    @staticmethod
    def find_optimal_threshold(y_true: Union[pd.Series, np.ndarray], y_prob: np.ndarray) -> Tuple[float, float]:
        """
        Calculates the optimal classification decision threshold maximizing F1 score.
        Essential for class-imbalanced IoT environments.
        """
        y_true_arr = np.asarray(y_true)
        pos_prob = y_prob[:, 1] if y_prob.ndim == 2 and y_prob.shape[1] > 1 else y_prob.ravel()

        precisions, recalls, thresholds = precision_recall_curve(y_true_arr, pos_prob)
        denom = precisions + recalls
        f1_scores = np.zeros_like(denom)
        valid = denom > 0
        f1_scores[valid] = 2.0 * (precisions[valid] * recalls[valid]) / denom[valid]

        best_idx = int(np.argmax(f1_scores))
        best_threshold = float(thresholds[min(best_idx, len(thresholds) - 1)])
        return best_threshold, float(f1_scores[best_idx])

    @staticmethod
    def evaluate_classification(
        y_true: Union[pd.Series, np.ndarray],
        y_pred: np.ndarray,
        y_prob: Optional[np.ndarray] = None,
        task_type: str = "binary",
        class_labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Computes comprehensive classification metrics.
        """
        y_true_arr = np.asarray(y_true)
        y_pred_arr = np.asarray(y_pred)

        metrics: Dict[str, Any] = {}
        metrics["accuracy"] = float(accuracy_score(y_true_arr, y_pred_arr))

        if task_type == "binary":
            metrics["precision"] = float(precision_score(y_true_arr, y_pred_arr, zero_division=0))
            metrics["recall"] = float(recall_score(y_true_arr, y_pred_arr, zero_division=0))
            metrics["f1"] = float(f1_score(y_true_arr, y_pred_arr, zero_division=0))
            metrics["f1_macro"] = float(f1_score(y_true_arr, y_pred_arr, average="macro", zero_division=0))
            metrics["f1_weighted"] = float(f1_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0))

            # Confusion matrix: TN, FP, FN, TP
            cm = confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1])
            tn, fp, fn, tp = cm.ravel()
            metrics["confusion_matrix"] = cm.tolist()
            metrics["true_negatives"] = int(tn)
            metrics["false_positives"] = int(fp)
            metrics["false_negatives"] = int(fn)
            metrics["true_positives"] = int(tp)
            metrics["false_positive_rate"] = float(fp / max(1, fp + tn))
            metrics["false_negative_rate"] = float(fn / max(1, fn + tp))

            if y_prob is not None:
                # Handle probability column for positive class
                pos_prob = y_prob[:, 1] if y_prob.ndim == 2 and y_prob.shape[1] > 1 else y_prob.ravel()
                try:
                    if len(np.unique(y_true_arr)) > 1:
                        metrics["roc_auc"] = float(roc_auc_score(y_true_arr, pos_prob))
                        metrics["pr_auc"] = float(average_precision_score(y_true_arr, pos_prob))
                    else:
                        metrics["roc_auc"] = 1.0
                        metrics["pr_auc"] = 1.0
                except Exception:
                    metrics["roc_auc"] = None
                    metrics["pr_auc"] = None
        else:
            # Multi-class
            metrics["precision_macro"] = float(precision_score(y_true_arr, y_pred_arr, average="macro", zero_division=0))
            metrics["precision_weighted"] = float(precision_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0))
            metrics["recall_macro"] = float(recall_score(y_true_arr, y_pred_arr, average="macro", zero_division=0))
            metrics["recall_weighted"] = float(recall_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0))
            metrics["f1_macro"] = float(f1_score(y_true_arr, y_pred_arr, average="macro", zero_division=0))
            metrics["f1_weighted"] = float(f1_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0))

            # Multi-class confusion matrix
            unique_labels = sorted(list(set(y_true_arr).union(set(y_pred_arr))))
            cm = confusion_matrix(y_true_arr, y_pred_arr, labels=unique_labels)
            metrics["confusion_matrix"] = cm.tolist()
            metrics["labels"] = [int(x) for x in unique_labels]

            # Macro FPR across classes
            fp_list, fn_list = [], []
            for idx, label in enumerate(unique_labels):
                tp_i = cm[idx, idx]
                fn_i = cm[idx, :].sum() - tp_i
                fp_i = cm[:, idx].sum() - tp_i
                tn_i = cm.sum() - (tp_i + fn_i + fp_i)
                fp_rate = fp_i / max(1, fp_i + tn_i)
                fn_rate = fn_i / max(1, fn_i + tp_i)
                fp_list.append(fp_rate)
                fn_list.append(fn_rate)

            metrics["false_positive_rate"] = float(np.mean(fp_list))
            metrics["false_negative_rate"] = float(np.mean(fn_list))

            if y_prob is not None:
                try:
                    present_classes = np.unique(y_true_arr)
                    if len(present_classes) > 1 and y_prob.shape[1] >= len(present_classes):
                        metrics["roc_auc"] = float(roc_auc_score(
                            y_true_arr,
                            y_prob[:, present_classes] if y_prob.shape[1] > len(present_classes) else y_prob,
                            multi_class="ovr",
                            average="macro"
                        ))
                    else:
                        metrics["roc_auc"] = 1.0
                except Exception:
                    metrics["roc_auc"] = None

        return metrics

    @staticmethod
    def benchmark_latency(
        detector: BaseAttackDetector,
        X_sample: Union[pd.DataFrame, np.ndarray],
        n_runs: int = 500
    ) -> Dict[str, float]:
        """
        Benchmarks single-sample inference latency in microseconds (us).
        Essential for evaluating resource-constrained edge gateways.
        """
        if isinstance(X_sample, pd.DataFrame):
            sample = X_sample.iloc[[0]].values
        elif isinstance(X_sample, np.ndarray):
            sample = X_sample[[0]]
        else:
            raise TypeError("X_sample must be DataFrame or ndarray")

        # Warmup
        for _ in range(20):
            _ = detector.predict(sample)

        durations_us = []
        for _ in range(n_runs):
            t_start = time.perf_counter()
            _ = detector.predict(sample)
            t_end = time.perf_counter()
            durations_us.append((t_end - t_start) * 1e6)

        arr = np.array(durations_us)
        return {
            "mean_latency_us": float(np.mean(arr)),
            "median_latency_us": float(np.median(arr)),
            "p95_latency_us": float(np.percentile(arr, 95)),
            "p99_latency_us": float(np.percentile(arr, 99)),
            "throughput_samples_sec": float(1e6 / max(1e-3, np.mean(arr))),
        }

    @staticmethod
    def measure_footprint(filepath: Union[str, Path]) -> Dict[str, float]:
        """Measures disk footprint of serialized model artifact in KB."""
        p = Path(filepath)
        if not p.exists():
            return {"disk_size_kb": 0.0}
        return {"disk_size_kb": float(p.stat().st_size / 1024.0)}

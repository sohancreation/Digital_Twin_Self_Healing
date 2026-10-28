"""
Unit and Integration Tests for Phase 5 Machine Learning Attack Detection Engine.
Verifies models, evaluators, explainers, detection engine, and serialization.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from backend.detection import (
    BaseAttackDetector,
    LogisticRegressionDetector,
    RandomForestDetector,
    XGBoostDetector,
    MLPAttackDetector,
    VotingEnsembleDetector,
    DetectionEvaluator,
    FeatureExplainer,
    AttackDetectionEngine,
    DetectionResult,
)


@pytest.fixture
def synthetic_binary_data():
    np.random.seed(42)
    n = 100
    p = 10
    X = pd.DataFrame(np.random.randn(n, p), columns=[f"feat_{i}" for i in range(p)])
    # Linear combination with noise
    score = X["feat_0"] * 2.0 - X["feat_1"] * 1.5 + np.random.randn(n) * 0.5
    y = (score > 0).astype(int)
    return X, y


@pytest.fixture
def synthetic_multiclass_data():
    np.random.seed(42)
    n = 120
    p = 10
    X = pd.DataFrame(np.random.randn(n, p), columns=[f"feat_{i}" for i in range(p)])
    y = np.random.choice([0, 1, 2, 3], size=n, p=[0.7, 0.1, 0.1, 0.1])
    return X, y


def test_detector_initialization():
    lr = LogisticRegressionDetector(task_type="binary", seed=42)
    rf = RandomForestDetector(task_type="multiclass", seed=42)
    xgb = XGBoostDetector(task_type="multiclass", seed=42)

    assert lr.task_type == "binary"
    assert rf.task_type == "multiclass"
    assert xgb.task_type == "multiclass"
    assert not lr.is_fitted
    assert not rf.is_fitted
    assert not xgb.is_fitted

    with pytest.raises(ValueError):
        LogisticRegressionDetector(task_type="unsupported")


@pytest.mark.parametrize("detector_cls", [
    LogisticRegressionDetector,
    RandomForestDetector,
    XGBoostDetector,
])
def test_binary_fitting_and_prediction(detector_cls, synthetic_binary_data):
    X, y = synthetic_binary_data
    detector = detector_cls(task_type="binary", seed=42)
    detector.fit(X, y)

    assert detector.is_fitted
    assert len(detector.feature_names) == X.shape[1]

    preds = detector.predict(X)
    assert len(preds) == len(y)
    assert set(np.unique(preds)).issubset({0, 1})

    probas = detector.predict_proba(X)
    assert probas.shape == (len(y), 2)
    np.testing.assert_allclose(probas.sum(axis=1), np.ones(len(y)), atol=1e-5)

    p_attack = detector.get_attack_probability(X)
    assert len(p_attack) == len(y)
    assert np.all((p_attack >= 0.0) & (p_attack <= 1.0))


@pytest.mark.parametrize("detector_cls", [
    LogisticRegressionDetector,
    RandomForestDetector,
    XGBoostDetector,
])
def test_multiclass_fitting_and_prediction(detector_cls, synthetic_multiclass_data):
    X, y = synthetic_multiclass_data
    detector = detector_cls(task_type="multiclass", seed=42)
    detector.fit(X, y)

    assert detector.is_fitted
    preds = detector.predict(X)
    assert len(preds) == len(y)
    assert set(np.unique(preds)).issubset({0, 1, 2, 3})

    probas = detector.predict_proba(X)
    assert probas.shape[0] == len(y)
    assert probas.shape[1] == 4
    np.testing.assert_allclose(probas.sum(axis=1), np.ones(len(y)), atol=1e-4)

    p_attack = detector.get_attack_probability(X)
    assert len(p_attack) == len(y)
    assert np.all((p_attack >= 0.0) & (p_attack <= 1.0))


def test_feature_importances(synthetic_binary_data):
    X, y = synthetic_binary_data
    rf = RandomForestDetector(task_type="binary", seed=42)
    rf.fit(X, y)

    importances = rf.get_feature_importances()
    assert len(importances) == X.shape[1]
    # Check sorted descending
    vals = list(importances.values())
    assert all(vals[i] >= vals[i+1] for i in range(len(vals) - 1))


def test_model_serialization(tmp_path, synthetic_binary_data):
    X, y = synthetic_binary_data
    rf = RandomForestDetector(task_type="binary", seed=42)
    rf.fit(X, y)

    model_path = tmp_path / "detector_rf.joblib"
    rf.save(model_path)
    assert model_path.exists()

    loaded = RandomForestDetector.load(model_path)
    assert loaded.is_fitted
    np.testing.assert_array_equal(rf.predict(X), loaded.predict(X))
    np.testing.assert_allclose(rf.predict_proba(X), loaded.predict_proba(X))


def test_evaluator_binary_metrics():
    y_true = np.array([0, 0, 0, 1, 1, 1, 0, 1])
    y_pred = np.array([0, 0, 0, 1, 1, 0, 1, 1])
    y_prob = np.array([
        [0.9, 0.1],
        [0.8, 0.2],
        [0.7, 0.3],
        [0.2, 0.8],
        [0.1, 0.9],
        [0.6, 0.4],
        [0.4, 0.6],
        [0.3, 0.7],
    ])

    metrics = DetectionEvaluator.evaluate_classification(
        y_true=y_true, y_pred=y_pred, y_prob=y_prob, task_type="binary"
    )

    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert "roc_auc" in metrics
    assert "false_positive_rate" in metrics
    assert "false_negative_rate" in metrics
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert 0.0 <= metrics["false_positive_rate"] <= 1.0


def test_latency_benchmarking(synthetic_binary_data):
    X, y = synthetic_binary_data
    lr = LogisticRegressionDetector(task_type="binary", seed=42)
    lr.fit(X, y)

    bench = DetectionEvaluator.benchmark_latency(lr, X, n_runs=100)
    assert "mean_latency_us" in bench
    assert "p95_latency_us" in bench
    assert "throughput_samples_sec" in bench
    assert bench["mean_latency_us"] > 0
    assert bench["throughput_samples_sec"] > 0


def test_feature_explainer(synthetic_binary_data):
    X, y = synthetic_binary_data
    rf = RandomForestDetector(task_type="binary", seed=42)
    rf.fit(X, y)

    top_feats = FeatureExplainer.get_top_features(rf, top_k=5)
    assert len(top_feats) == 5

    alert_exp = FeatureExplainer.explain_alert(rf, X.iloc[0], top_k=3)
    assert "predicted_class" in alert_exp
    assert "attack_probability" in alert_exp
    assert "top_contributing_features" in alert_exp


def test_attack_detection_engine(synthetic_binary_data):
    X, y = synthetic_binary_data
    bin_detector = RandomForestDetector(task_type="binary", seed=42).fit(X, y)
    engine = AttackDetectionEngine(binary_detector=bin_detector)

    sample = X.iloc[0]
    res = engine.detect_vector(sample, timestamp=10.0, node_id=2)

    assert isinstance(res, DetectionResult)
    assert res.timestamp == 10.0
    assert res.node_id == 2
    assert isinstance(res.is_attack, bool)
    assert 0.0 <= res.attack_probability <= 1.0
    assert res.inference_latency_us > 0

    batch_res = engine.detect_batch(X.iloc[:5])
    assert len(batch_res) == 5

    hist_df = engine.get_detection_dataframe()
    assert len(hist_df) == 6  # 1 individual + 5 batch


def test_detector_calibration(synthetic_binary_data):
    X, y = synthetic_binary_data
    lr = LogisticRegressionDetector(task_type="binary", seed=42)
    lr.fit(X.iloc[:60], y.iloc[:60])
    assert not lr.is_calibrated

    lr.calibrate(X.iloc[60:], y.iloc[60:])
    assert lr.is_calibrated
    probs = lr.predict_proba(X)
    assert probs.shape == (len(X), 2)
    assert np.all((probs >= 0.0) & (probs <= 1.0))


def test_saved_detector_artifacts():
    model_dir = Path("models/detectors")
    if not (model_dir / "best_detector_metadata.json").exists():
        pytest.skip("Models not yet trained.")

    import json
    with open(model_dir / "best_detector_metadata.json", "r") as f:
        meta = json.load(f)

    bin_path = meta["champion_binary_model"]["model_path"]
    multi_path = meta["champion_multiclass_model"]["model_path"]

    bin_det = LogisticRegressionDetector.load(bin_path)
    multi_det = LogisticRegressionDetector.load(multi_path)

    assert bin_det.is_fitted
    assert multi_det.is_fitted
    assert bin_det.task_type == "binary"
    assert multi_det.task_type == "multiclass"


def test_mlp_detector(synthetic_binary_data, tmp_path):
    X, y = synthetic_binary_data
    mlp = MLPAttackDetector(task_type="binary", seed=42, model_params={"max_iter": 50})
    mlp.fit(X, y)
    assert mlp.is_fitted

    preds = mlp.predict(X)
    probs = mlp.predict_proba(X)
    assert len(preds) == len(X)
    assert probs.shape == (len(X), 2)
    assert np.all((probs >= 0.0) & (probs <= 1.0))

    importances = mlp.get_feature_importances()
    assert len(importances) == X.shape[1]

    mlp.calibrate(X, y)
    assert mlp.is_calibrated

    # Serialization test
    save_path = tmp_path / "mlp.joblib"
    mlp.save(save_path)
    loaded = MLPAttackDetector.load(save_path)
    assert loaded.is_fitted
    assert loaded.task_type == "binary"


def test_voting_ensemble_detector(synthetic_binary_data, tmp_path):
    X, y = synthetic_binary_data
    lr = LogisticRegressionDetector(task_type="binary", seed=42, model_params={"max_iter": 50})
    mlp = MLPAttackDetector(task_type="binary", seed=42, model_params={"max_iter": 50})
    ensemble = VotingEnsembleDetector(
        task_type="binary",
        seed=42,
        detectors=[lr, mlp],
        weights=[0.5, 0.5],
        decision_threshold=0.40,
    )
    ensemble.fit(X, y)
    assert ensemble.is_fitted

    preds = ensemble.predict(X)
    probs = ensemble.predict_proba(X)
    assert len(preds) == len(X)
    assert probs.shape == (len(X), 2)
    assert np.allclose(probs.sum(axis=1), 1.0)

    importances = ensemble.get_feature_importances()
    assert len(importances) == X.shape[1]

    # Threshold behavior check
    prob_1 = probs[:, 1]
    expected_pred = (prob_1 >= 0.40).astype(int)
    assert np.array_equal(preds, expected_pred)

    # Calibration test
    ensemble.calibrate(X, y)
    assert ensemble.is_calibrated

    # Serialization test
    save_path = tmp_path / "ensemble.joblib"
    ensemble.save(save_path)
    loaded = VotingEnsembleDetector.load(save_path)
    assert loaded.is_fitted
    assert loaded.decision_threshold == 0.40

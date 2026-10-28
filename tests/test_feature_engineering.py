"""
Unit and integration tests for Phase 4: Data Engineering and Feature Extraction.
Verifies temporal causality, zero future leakage, multi-scale statistics, and chronological partitioning.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from backend.data_engineering import (
    TemporalFeatureExtractor,
    FeaturePreprocessor,
    DatasetManager,
    FeaturePipeline,
)


def _generate_synthetic_telemetry(n_steps: int = 50, n_nodes: int = 3) -> pd.DataFrame:
    """Generates synthetic multi-node telemetry DataFrame for testing."""
    records = []
    for t in range(n_steps):
        for nid in range(n_nodes):
            records.append({
                "timestamp": float(t),
                "node_id": nid,
                "packet_rate": 2.0 + (10.0 if (nid == 1 and 20 <= t < 30) else 0.0),
                "forwarding_rate": 1.0,
                "packet_loss": 0.02 + (0.5 if (nid == 2 and 35 <= t < 45) else 0.0),
                "latency": 25.0 + (50.0 if (nid == 1 and 20 <= t < 30) else 0.0),
                "rssi": -80.0,
                "energy": max(0.0, 100.0 - (0.1 * t)),
                "cpu": 10.0 + (30.0 if (nid == 1 and 20 <= t < 30) else 0.0),
                "memory": 15.0,
                "neighbor_count": 2,
                "connection_state": "CONNECTED" if not (nid == 0 and 40 <= t < 45) else "DISCONNECTED",
                "routing_state": "ROUTING",
                "attack_active": 1 if (nid == 1 and 20 <= t < 30) else 0,
                "attack_type": "dos" if (nid == 1 and 20 <= t < 30) else "normal",
            })
    return pd.DataFrame(records)


def test_feature_extraction_structure():
    """Verify that TemporalFeatureExtractor produces all expected rolling, delta, and spatial features."""
    df = _generate_synthetic_telemetry(n_steps=40, n_nodes=2)
    extractor = TemporalFeatureExtractor(window_sizes=[5, 15])
    features_df = extractor.extract_features(df)

    # Check that original columns are preserved
    assert "timestamp" in features_df.columns
    assert "node_id" in features_df.columns
    assert "cpu" in features_df.columns

    # Check derivative deltas
    assert "delta_packet_rate" in features_df.columns
    assert "delta_cpu" in features_df.columns
    assert "energy_drain_rate" in features_df.columns

    # Check rolling statistics for window sizes 5 and 15
    for w in [5, 15]:
        assert f"cpu_roll_mean_{w}" in features_df.columns
        assert f"cpu_roll_std_{w}" in features_df.columns
        assert f"latency_roll_mean_{w}" in features_df.columns
        assert f"packet_loss_roll_max_{w}" in features_df.columns

    # Check interaction & spatial discrepancy features
    assert "forwarding_ratio" in features_df.columns
    assert "channel_congestion_index" in features_df.columns
    assert "cpu_network_discrepancy" in features_df.columns
    assert "loss_network_discrepancy" in features_df.columns

    # Ensure no NaN values propagate
    assert features_df.isnull().sum().sum() == 0


def test_zero_future_leakage():
    """
    Critical causal test: Modifying future data at t=40 must NOT alter
    extracted feature values at t=20.
    """
    df1 = _generate_synthetic_telemetry(n_steps=50, n_nodes=2)
    df2 = df1.copy()

    # Modify record at t=40 in df2
    mask = (df2["timestamp"] == 40.0) & (df2["node_id"] == 1)
    df2.loc[mask, "packet_rate"] = 999.0
    df2.loc[mask, "cpu"] = 99.0

    extractor = TemporalFeatureExtractor(window_sizes=[5, 15])
    feat1 = extractor.extract_features(df1)
    feat2 = extractor.extract_features(df2)

    # Inspect features at t <= 30: must be EXACTLY identical
    past1 = feat1[feat1["timestamp"] <= 30.0].reset_index(drop=True)
    past2 = feat2[feat2["timestamp"] <= 30.0].reset_index(drop=True)

    pd.testing.assert_frame_equal(past1, past2)


def test_multi_scale_window_responsiveness():
    """
    Verify that smaller window (W=5) reacts faster to a sudden surge than larger window (W=30).
    """
    df = _generate_synthetic_telemetry(n_steps=50, n_nodes=2)
    extractor = TemporalFeatureExtractor(window_sizes=[5, 30])
    feat = extractor.extract_features(df)

    # Surge starts at t=20 on node 1
    # At t=22 (2 steps into attack): W=5 should show much higher mean than W=30
    node1_t22 = feat[(feat["node_id"] == 1) & (feat["timestamp"] == 22.0)].iloc[0]
    assert node1_t22["cpu_roll_mean_5"] > node1_t22["cpu_roll_mean_30"]


def test_target_formatting():
    """Verify target column formatting for binary and multiclass labels."""
    df = pd.DataFrame([
        {"timestamp": 0.0, "node_id": 0, "attack_active": 0, "attack_type": "normal"},
        {"timestamp": 1.0, "node_id": 1, "attack_active": 1, "attack_type": "dos"},
        {"timestamp": 2.0, "node_id": 2, "attack_active": 1, "attack_type": "compromised_node"},
        {"timestamp": 3.0, "node_id": 3, "attack_active": 1, "attack_type": "node_failure"},
    ])

    formatted = DatasetManager.format_targets(df)
    assert list(formatted["target_binary"]) == [0, 1, 1, 1]
    assert list(formatted["target_multiclass"]) == [0, 1, 2, 3]


def test_chronological_splitting():
    """Verify strict chronological boundaries in train, validation, and test partitions."""
    df = _generate_synthetic_telemetry(n_steps=100, n_nodes=2)
    train_df, val_df, test_df = DatasetManager.split_chronological(df, 0.7, 0.15, 0.15)

    assert len(train_df) + len(val_df) + len(test_df) == len(df)
    assert train_df["timestamp"].max() < val_df["timestamp"].min()
    assert val_df["timestamp"].max() < test_df["timestamp"].min()


def test_preprocessor_scaling_and_persistence(tmp_path):
    """Verify z-score standardization and metadata JSON export/import."""
    df = _generate_synthetic_telemetry(n_steps=30, n_nodes=2)
    extractor = TemporalFeatureExtractor(window_sizes=[5])
    feat_df = extractor.extract_features(df)

    preprocessor = FeaturePreprocessor()
    scaled_df = preprocessor.fit_transform(feat_df)

    # Scaled continuous feature should have mean near 0 and std near 1 on training data
    assert pytest.approx(scaled_df["cpu"].mean(), abs=1e-5) == 0.0
    assert pytest.approx(scaled_df["cpu"].std(), abs=1e-2) == 1.0

    # Save and reload metadata
    meta_file = tmp_path / "metadata.json"
    preprocessor.save_metadata(meta_file)
    assert meta_file.exists()

    reloaded = FeaturePreprocessor().load_metadata(meta_file)
    assert reloaded.means["cpu"] == preprocessor.means["cpu"]
    assert reloaded.stds["cpu"] == preprocessor.stds["cpu"]


def test_feature_pipeline_end_to_end():
    """Verify complete pipeline creates full, train, val, and test datasets without error."""
    df = _generate_synthetic_telemetry(n_steps=60, n_nodes=2)
    pipeline = FeaturePipeline(window_sizes=[5, 15])
    datasets = pipeline.create_partitioned_datasets(df, 0.70, 0.15, 0.15)

    assert "full" in datasets
    assert "train" in datasets
    assert "val" in datasets
    assert "test" in datasets

    assert len(datasets["train"]) == int(len(df) * 0.70)
    assert "target_binary" in datasets["train"].columns
    assert "target_multiclass" in datasets["train"].columns
    assert datasets["train"].isnull().sum().sum() == 0

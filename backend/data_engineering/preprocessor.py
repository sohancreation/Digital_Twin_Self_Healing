"""
Feature Preprocessing and Normalization Engine.
Handles missing value imputation, categorical encoding, and feature scaling with parameter persistence.
"""

from typing import List, Dict, Optional, Union
import json
from pathlib import Path
import numpy as np
import pandas as pd


class FeaturePreprocessor:
    """
    Standardizes feature distributions, encodes discrete states, and persists scaling parameters.
    """

    # Columns excluded from model input features
    NON_FEATURE_COLUMNS = {
        "timestamp",
        "node_id",
        "attack_active",
        "attack_type",
        "attack_id",
        "target_node",
        "intensity",
        "is_indirectly_affected",
        "threat_level",
        "trust_score",
        "target_binary",
        "target_multiclass",
        "scenario_id",
        "topology",
        "num_nodes",
    }

    # Categorical columns to encode
    CATEGORICAL_COLUMNS = ["connection_state", "routing_state"]

    def __init__(self):
        self.feature_columns: List[str] = []
        self.means: Dict[str, float] = {}
        self.stds: Dict[str, float] = {}
        self.is_fitted: bool = False

    def fit(self, df: pd.DataFrame) -> "FeaturePreprocessor":
        """
        Learns feature means and standard deviations from training data.
        """
        # Determine numeric feature columns
        candidate_cols = [
            c for c in df.columns 
            if c not in self.NON_FEATURE_COLUMNS 
            and c not in self.CATEGORICAL_COLUMNS 
            and pd.api.types.is_numeric_dtype(df[c])
        ]
        self.feature_columns = candidate_cols

        for col in self.feature_columns:
            mean_val = float(df[col].mean())
            std_val = float(df[col].std())
            # Guard against zero variance
            if np.isnan(std_val) or std_val < 1e-8:
                std_val = 1.0
            self.means[col] = mean_val
            self.stds[col] = std_val

        self.is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies learned scaling and encoding to the dataset.
        """
        if not self.is_fitted:
            raise RuntimeError("FeaturePreprocessor must be fitted before calling transform().")

        out_df = df.copy()

        # One-hot encode categorical connection and routing states
        if "connection_state" in out_df.columns:
            out_df["is_connected"] = (out_df["connection_state"] == "CONNECTED").astype(float)
            out_df["is_degraded"] = (out_df["connection_state"] == "DEGRADED").astype(float)
            out_df["is_disconnected"] = (out_df["connection_state"] == "DISCONNECTED").astype(float)

        if "routing_state" in out_df.columns:
            out_df["is_routing"] = (out_df["routing_state"] == "ROUTING").astype(float)
            out_df["is_congested"] = (out_df["routing_state"] == "CONGESTED").astype(float)

        # Scale continuous features
        for col in self.feature_columns:
            if col in out_df.columns:
                mean_val = self.means[col]
                std_val = self.stds[col]
                out_df[col] = (out_df[col] - mean_val) / std_val

        return out_df

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fits preprocessor and transforms dataframe in a single step."""
        return self.fit(df).transform(df)

    def save_metadata(self, filepath: Union[str, Path]) -> Path:
        """Saves learned preprocessing metadata to JSON."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "feature_columns": self.feature_columns,
            "means": self.means,
            "stds": self.stds,
            "is_fitted": self.is_fitted,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path

    def load_metadata(self, filepath: Union[str, Path]) -> "FeaturePreprocessor":
        """Loads preprocessing parameters from JSON."""
        path = Path(filepath)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.feature_columns = data["feature_columns"]
        self.means = data["means"]
        self.stds = data["stds"]
        self.is_fitted = data["is_fitted"]
        return self

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "FeaturePreprocessor":
        """Factory method to load FeaturePreprocessor from metadata JSON."""
        instance = cls()
        return instance.load_metadata(filepath)

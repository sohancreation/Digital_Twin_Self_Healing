"""
Dataset partitioning, class balance analysis, and target label formatting for ML.
Ensures rigorous temporal-aware splitting without data leakage.
"""

from typing import Tuple, Dict, Any, Union
from pathlib import Path
import pandas as pd


class DatasetManager:
    """
    Handles target label encoding, chronological train/validation/test partitioning,
    and class imbalance reporting.
    """

    LABEL_MAPPING = {
        "normal": 0,
        "dos": 1,
        "compromised_node": 2,
        "node_failure": 3,
        "on_off": 4,
    }

    INV_LABEL_MAPPING = {v: k for k, v in LABEL_MAPPING.items()}

    @classmethod
    def format_targets(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds standardized target columns:
        - `target_binary`: 0 (Benign), 1 (Attack)
        - `target_multiclass`: 0 (Normal), 1 (DoS), 2 (Compromised), 3 (Node Failure)
        """
        out_df = df.copy()

        if "attack_active" in out_df.columns:
            out_df["target_binary"] = out_df["attack_active"].astype(int)
        else:
            out_df["target_binary"] = 0

        if "attack_type" in out_df.columns:
            out_df["target_multiclass"] = out_df["attack_type"].map(cls.LABEL_MAPPING).fillna(0).astype(int)
        else:
            out_df["target_multiclass"] = 0

        return out_df

    @classmethod
    def split_chronological(
        cls,
        df: pd.DataFrame,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Splits dataset chronologically based on timestamps.
        Guarantees zero future data leakage across train, validation, and test sets.
        """
        if abs((train_ratio + val_ratio + test_ratio) - 1.0) > 1e-5:
            raise ValueError("train_ratio + val_ratio + test_ratio must sum to 1.0")

        sorted_df = df.sort_values(by="timestamp").reset_index(drop=True)
        timestamps = sorted_df["timestamp"].unique()
        n_timestamps = len(timestamps)

        idx_train_end = int(n_timestamps * train_ratio)
        idx_val_end = int(n_timestamps * (train_ratio + val_ratio))

        t_train_max = timestamps[idx_train_end - 1]
        t_val_max = timestamps[idx_val_end - 1]

        train_df = sorted_df[sorted_df["timestamp"] <= t_train_max].copy().reset_index(drop=True)
        val_df = sorted_df[(sorted_df["timestamp"] > t_train_max) & (sorted_df["timestamp"] <= t_val_max)].copy().reset_index(drop=True)
        test_df = sorted_df[sorted_df["timestamp"] > t_val_max].copy().reset_index(drop=True)

        return train_df, val_df, test_df

    @classmethod
    def get_class_distribution(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Computes class frequencies and balance metrics for binary and multi-class targets.
        """
        dist = {}

        if "target_binary" in df.columns:
            counts_bin = df["target_binary"].value_counts().to_dict()
            total = len(df)
            dist["binary"] = {
                "benign_count": counts_bin.get(0, 0),
                "attack_count": counts_bin.get(1, 0),
                "attack_percentage": float((counts_bin.get(1, 0) / max(1, total)) * 100.0),
                "imbalance_ratio": float(counts_bin.get(0, 0) / max(1, counts_bin.get(1, 0))),
            }

        if "target_multiclass" in df.columns:
            counts_multi = df["target_multiclass"].value_counts().to_dict()
            total = len(df)
            dist["multiclass"] = {
                cls.INV_LABEL_MAPPING.get(k, str(k)): {
                    "count": int(v),
                    "percentage": float((v / max(1, total)) * 100.0)
                }
                for k, v in sorted(counts_multi.items())
            }

        return dist

"""
Temporal and Spatial Feature Extraction Engine for IoT Security.
Transforms raw telemetry streams into high-dimensional feature vectors using
multi-scale rolling temporal windows, first-order derivatives, and spatial discrepancies.
"""

from typing import List, Optional
import numpy as np
import pandas as pd


class TemporalFeatureExtractor:
    """
    Extracts multi-scale temporal and spatial features per node and timestep.
    Ensures zero future data leakage (backward-only causal rolling windows).
    """

    def __init__(self, window_sizes: Optional[List[int]] = None):
        # Default temporal windows in seconds/timesteps: 5s (burst), 15s (queuing), 30s (macro trend)
        self.window_sizes = window_sizes if window_sizes is not None else [5, 15, 30]

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Processes raw telemetry DataFrame and returns an enriched feature DataFrame.
        """
        # Ensure chronological ordering per node
        work_df = df.copy().sort_values(by=["node_id", "timestamp"]).reset_index(drop=True)

        feature_frames = []

        # 1. Per-Node Temporal Rolling Windows and Derivatives
        for node_id, node_group in work_df.groupby("node_id"):
            node_df = node_group.copy()

            # Time delta for derivative calculations
            dt = node_df["timestamp"].diff().fillna(1.0)
            dt = dt.replace(0, 1.0)

            # First-order rate-of-change derivatives
            node_df["delta_packet_rate"] = node_df["packet_rate"].diff().fillna(0.0) / dt
            node_df["delta_forwarding_rate"] = node_df["forwarding_rate"].diff().fillna(0.0) / dt
            node_df["delta_cpu"] = node_df["cpu"].diff().fillna(0.0) / dt
            node_df["delta_latency"] = node_df["latency"].diff().fillna(0.0) / dt
            node_df["delta_packet_loss"] = node_df["packet_loss"].diff().fillna(0.0) / dt
            # Energy depletion rate: positive rate indicates battery draining
            node_df["energy_drain_rate"] = (-node_df["energy"].diff().fillna(0.0) / dt).clip(lower=0.0)

            # Multi-scale rolling window statistics
            metrics_for_rolling = ["packet_rate", "forwarding_rate", "packet_loss", "latency", "cpu", "memory"]
            for w in self.window_sizes:
                for metric in metrics_for_rolling:
                    roll = node_df[metric].rolling(window=w, min_periods=1)
                    node_df[f"{metric}_roll_mean_{w}"] = roll.mean().bfill().fillna(0.0)
                    node_df[f"{metric}_roll_std_{w}"] = roll.std().fillna(0.0)
                    node_df[f"{metric}_roll_min_{w}"] = roll.min().bfill().fillna(0.0)
                    node_df[f"{metric}_roll_max_{w}"] = roll.max().bfill().fillna(0.0)

            # Domain interaction ratios
            total_traffic = node_df["packet_rate"] + node_df["forwarding_rate"]
            node_df["forwarding_ratio"] = node_df["forwarding_rate"] / (total_traffic + 1e-6)
            node_df["channel_congestion_index"] = node_df["latency"] / np.maximum(1.0, np.abs(node_df["rssi"]))
            node_df["traffic_to_cpu_ratio"] = total_traffic / np.maximum(1.0, node_df["cpu"])
            node_df["memory_to_cpu_ratio"] = node_df["memory"] / np.maximum(1.0, node_df["cpu"])

            feature_frames.append(node_df)

        combined_df = pd.concat(feature_frames, ignore_index=True)

        # 2. Spatial / Network-Wide Discrepancy Features (Macro Comparison)
        # For each timestamp, compute network-wide average and subtract node metric
        net_stats = combined_df.groupby("timestamp")[["cpu", "latency", "packet_loss", "forwarding_rate"]].transform("mean")
        combined_df["cpu_network_discrepancy"] = combined_df["cpu"] - net_stats["cpu"]
        combined_df["latency_network_discrepancy"] = combined_df["latency"] - net_stats["latency"]
        combined_df["loss_network_discrepancy"] = combined_df["packet_loss"] - net_stats["packet_loss"]
        combined_df["fwd_network_discrepancy"] = combined_df["forwarding_rate"] - net_stats["forwarding_rate"]

        # Sort back chronologically
        combined_df = combined_df.sort_values(by=["timestamp", "node_id"]).reset_index(drop=True)
        return combined_df

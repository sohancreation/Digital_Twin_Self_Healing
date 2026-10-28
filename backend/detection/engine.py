"""
Runtime Cyber Attack Detection Engine.
Integrates trained binary and multi-class ML models with the Digital Twin.
Processes engineered feature vectors, performs real-time inference,
produces calibrated attack probabilities P_attack(t) for Phase 6 Trust Modeling,
and packages structured DetectionResult alerts.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import time
import numpy as np
import pandas as pd

from .models import BaseAttackDetector
from ..data_engineering.preprocessor import FeaturePreprocessor


@dataclass
class DetectionResult:
    """Structured detection alert emitted by the AttackDetectionEngine."""
    timestamp: float
    node_id: int
    is_attack: bool
    attack_type: str
    attack_probability: float
    confidence: float
    inference_latency_us: float
    multiclass_label: int = 0
    top_features: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "is_attack": self.is_attack,
            "attack_type": self.attack_type,
            "attack_probability": self.attack_probability,
            "confidence": self.confidence,
            "inference_latency_us": self.inference_latency_us,
            "multiclass_label": self.multiclass_label,
            "top_features": self.top_features,
        }


class AttackDetectionEngine:
    """
    Operational detection engine bridging ML classifiers to the Digital Twin.
    """

    ATTACK_TYPE_MAP = {
        0: "normal",
        1: "dos",
        2: "compromised_node",
        3: "node_failure",
    }

    def __init__(
        self,
        binary_detector: Optional[BaseAttackDetector] = None,
        multiclass_detector: Optional[BaseAttackDetector] = None,
        preprocessor: Optional[FeaturePreprocessor] = None,
        detection_threshold: float = 0.50
    ):
        self.binary_detector = binary_detector
        self.multiclass_detector = multiclass_detector
        self.preprocessor = preprocessor
        self.detection_threshold = detection_threshold
        self.detection_history: List[DetectionResult] = []

    def detect_vector(
        self,
        features: Union[pd.Series, pd.DataFrame, np.ndarray],
        timestamp: float = 0.0,
        node_id: int = 0
    ) -> DetectionResult:
        """
        Performs real-time inference on a single feature vector.
        """
        t_start = time.perf_counter()

        if isinstance(features, pd.Series):
            feat_df = features.to_frame().T
        elif isinstance(features, pd.DataFrame):
            feat_df = features.iloc[[0]] if len(features) > 1 else features
        else:
            feat_df = features.reshape(1, -1)

        # 1. Binary Detection
        if self.binary_detector is not None:
            p_attack = float(self.binary_detector.get_attack_probability(feat_df)[0])
            is_attack = bool(p_attack >= self.detection_threshold)
            bin_conf = float(abs(p_attack - 0.5) * 2.0)
        else:
            p_attack = 0.0
            is_attack = False
            bin_conf = 0.0

        # 2. Multi-Class Classification
        if self.multiclass_detector is not None:
            multi_class = int(self.multiclass_detector.predict(feat_df)[0])
            multi_proba = self.multiclass_detector.predict_proba(feat_df)[0]
            multi_conf = float(np.max(multi_proba))
            attack_type = self.ATTACK_TYPE_MAP.get(multi_class, "unknown")

            # Cross-check with binary: if binary flags attack but multiclass says normal,
            # or if multiclass predicts attack > 0
            if multi_class > 0:
                is_attack = True
                p_attack = max(p_attack, float(1.0 - multi_proba[0]) if len(multi_proba) > 0 else 0.8)
            elif is_attack and attack_type == "normal":
                # Binary says attack, multiclass pick highest non-zero class
                if len(multi_proba) > 1:
                    non_zero_idx = np.argmax(multi_proba[1:]) + 1
                    attack_type = self.ATTACK_TYPE_MAP.get(non_zero_idx, "dos")
        else:
            multi_class = 1 if is_attack else 0
            attack_type = "dos" if is_attack else "normal"
            multi_conf = bin_conf

        t_end = time.perf_counter()
        latency_us = (t_end - t_start) * 1e6

        # Top feature attribution
        top_feats = {}
        if is_attack and self.multiclass_detector is not None:
            ranking = self.multiclass_detector.get_feature_importances()
            top_feats = dict(list(ranking.items())[:3])

        result = DetectionResult(
            timestamp=timestamp,
            node_id=node_id,
            is_attack=is_attack,
            attack_type=attack_type,
            attack_probability=p_attack,
            confidence=float(max(bin_conf, multi_conf)),
            inference_latency_us=float(latency_us),
            multiclass_label=multi_class,
            top_features=top_feats,
        )

        self.detection_history.append(result)
        return result

    def detect_batch(
        self,
        features_df: pd.DataFrame,
        feature_columns: Optional[List[str]] = None
    ) -> List[DetectionResult]:
        """
        Executes batched inference over an engineered dataset.
        """
        cols = feature_columns
        if cols is None and self.preprocessor is not None:
            cols = self.preprocessor.feature_columns

        results = []
        for _, row in features_df.iterrows():
            ts = float(row.get("timestamp", 0.0))
            nid = int(row.get("node_id", 0))
            feat_subset = row[cols] if cols is not None else row
            res = self.detect_vector(feat_subset, timestamp=ts, node_id=nid)
            results.append(res)
        return results

    def get_detection_dataframe(self) -> pd.DataFrame:
        """Returns recorded detection history as a DataFrame."""
        return pd.DataFrame([r.to_dict() for r in self.detection_history])

    def clear_history(self):
        """Resets the detection alert history buffer."""
        self.detection_history.clear()

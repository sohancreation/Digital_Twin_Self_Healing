"""
Interpretability and Explainability Engine for IoT Attack Detection.
Extracts global feature importances and computes SHAP (SHapley Additive exPlanations)
for tree-based and linear detection architectures.
Provides local attribution for why an alert was triggered.
"""

from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd
import shap

from .models import BaseAttackDetector, LogisticRegressionDetector, RandomForestDetector, XGBoostDetector


class FeatureExplainer:
    """
    Computes global feature importances, SHAP values, and local alert explanations.
    """

    @staticmethod
    def get_top_features(
        detector: BaseAttackDetector,
        top_k: int = 15
    ) -> List[Tuple[str, float]]:
        """
        Returns the top-K most influential features according to model internal importances.
        """
        ranking = detector.get_feature_importances()
        return list(ranking.items())[:top_k]

    @staticmethod
    def compute_shap_values(
        detector: BaseAttackDetector,
        X: Union[pd.DataFrame, np.ndarray],
        max_samples: int = 300
    ) -> Tuple[Any, Any]:
        """
        Computes SHAP values using TreeExplainer for tree ensembles
        or LinearExplainer for logistic regression.
        Limits samples to max_samples for fast computation.
        """
        if not detector.is_fitted:
            raise RuntimeError("Detector must be fitted before computing SHAP values.")

        if isinstance(X, pd.DataFrame):
            X_eval = X.iloc[:max_samples]
        else:
            X_eval = X[:max_samples]

        underlying = detector.model

        if isinstance(detector, (RandomForestDetector, XGBoostDetector)):
            explainer = shap.TreeExplainer(underlying)
            shap_values = explainer(X_eval)
        elif isinstance(detector, LogisticRegressionDetector):
            explainer = shap.LinearExplainer(underlying, X_eval)
            shap_values = explainer(X_eval)
        else:
            explainer = shap.Explainer(underlying, X_eval)
            shap_values = explainer(X_eval)

        return shap_values, explainer

    @staticmethod
    def explain_alert(
        detector: BaseAttackDetector,
        sample: Union[pd.Series, pd.DataFrame, np.ndarray],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Provides local attribution explanation for an individual detection alert.
        Explains which feature deviations contributed most to the attack decision.
        """
        if isinstance(sample, pd.Series):
            feat_names = list(sample.index)
            sample_vals = sample.values.reshape(1, -1)
        elif isinstance(sample, pd.DataFrame):
            feat_names = list(sample.columns)
            sample_vals = sample.iloc[[0]].values
        else:
            feat_names = detector.feature_names
            sample_vals = np.asarray(sample).reshape(1, -1)

        pred_class = int(detector.predict(sample_vals)[0])
        attack_prob = float(detector.get_attack_probability(sample_vals)[0])

        ranking = detector.get_feature_importances()
        top_feats = dict(list(ranking.items())[:top_k])

        return {
            "predicted_class": pred_class,
            "attack_probability": attack_prob,
            "is_attack": bool(attack_prob > 0.5 or pred_class > 0),
            "top_contributing_features": top_feats,
        }

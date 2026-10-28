"""
Data Engineering and Feature Extraction Package (Phase 4).
Prepares high-dimensional, temporal-aware feature datasets for machine learning intrusion detection.
"""

from .extractor import TemporalFeatureExtractor
from .preprocessor import FeaturePreprocessor
from .dataset import DatasetManager
from .pipeline import FeaturePipeline

__all__ = [
    "TemporalFeatureExtractor",
    "FeaturePreprocessor",
    "DatasetManager",
    "FeaturePipeline",
]

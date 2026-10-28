"""
Graph Neural Network (GNN) module for IoT cyber-resilience and digital twin self-healing.
Provides:
- GraphFeatureExtractor: Extracts topological and physical features into graph tensors.
- BridgeAwareGAT: Graph Attention Network with bridge-edge attenuation.
- TemporalGCN: Spatio-temporal graph representation over sliding horizons.
- DualHeadGNNClassifier: Joint 5-class attack classification and trust score prediction.
- GNNBayesianFusion: Dynamic fusion of GNN predictions and Bayesian trust.
"""

from .features import GraphFeatureExtractor, GraphSnapshot
from .model import BridgeAwareGATLayer, BridgeAwareGAT, TemporalGCN, DualHeadGNNClassifier
from .dataset import GraphSnapshotDataset, GraphSnapshotBatch
from .fusion import GNNBayesianFusion
from .ablations import (
    MLPBaselineClassifier,
    StandardGCN,
    GraphSAGE,
    StandardGAT,
    GNNModelAblationSuite,
)

__all__ = [
    "GraphFeatureExtractor",
    "GraphSnapshot",
    "BridgeAwareGATLayer",
    "BridgeAwareGAT",
    "TemporalGCN",
    "DualHeadGNNClassifier",
    "GraphSnapshotDataset",
    "GraphSnapshotBatch",
    "GNNBayesianFusion",
    "MLPBaselineClassifier",
    "StandardGCN",
    "GraphSAGE",
    "StandardGAT",
    "GNNModelAblationSuite",
]

"""
Phase 11: End-to-End Experimental Research Framework & Automated Comparative Benchmarking.
"""

from .models import (
    BaselineType,
    ExperimentMetricRecord,
    ExperimentRunResult,
    BenchmarkConfig,
    StatisticalComparison,
    HorizonAblationRecord,
    WeightSensitivityRecord,
    ChannelLossAblationRecord,
    TrustPenaltyAblationRecord,
)
from .baselines import (
    BaseBaselineController,
    UnmitigatedBaseline,
    StaticThresholdIDSBaseline,
    MLFixedRecoveryBaseline,
    ProposedDigitalTwinBaseline,
)
from .runner import ExperimentRunner
from .ablation import AblationStudyEngine
from .statistics import StatisticalEvaluator

__all__ = [
    "BaselineType",
    "ExperimentMetricRecord",
    "ExperimentRunResult",
    "BenchmarkConfig",
    "StatisticalComparison",
    "HorizonAblationRecord",
    "WeightSensitivityRecord",
    "ChannelLossAblationRecord",
    "TrustPenaltyAblationRecord",
    "BaseBaselineController",
    "UnmitigatedBaseline",
    "StaticThresholdIDSBaseline",
    "MLFixedRecoveryBaseline",
    "ProposedDigitalTwinBaseline",
    "ExperimentRunner",
    "AblationStudyEngine",
    "StatisticalEvaluator",
]

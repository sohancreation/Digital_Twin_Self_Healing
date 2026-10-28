"""
Candidate Recovery Strategy Generation Package.
Provides mitigation action taxonomies, topological feasibility checkers,
and autonomous recovery candidate pool synthesis for resource-constrained IoT networks.
"""

from .models import (
    RecoveryActionType,
    RecoveryCandidate,
    StrategyPool,
    RecoveryConfig,
    OptimizationWeights,
    OptimizationConstraints,
    SandboxSimulationResult,
    CandidateObjectiveScore,
    OptimizationDecision,
    StochasticSimulationSummary,
    TOPSISScore,
)
from .feasibility import FeasibilityChecker
from .taxonomy import (
    build_no_action_candidate,
    build_isolation_candidate,
    build_reroute_candidate,
    build_rate_limit_candidate,
    build_reboot_candidate,
    build_power_adjustment_candidate,
    build_composite_isolate_and_bridge_candidate,
    build_composite_throttle_and_reroute_candidate,
)
from .generator import CandidateStrategyGenerator
from .sandbox import RecoverySandbox
from .optimization import (
    MultiObjectiveRecoveryOptimizer,
    WEIGHT_PROFILES,
    TOPSISRanker,
    detect_cross_mitigation_collisions,
)

__all__ = [
    "RecoveryActionType",
    "RecoveryCandidate",
    "StrategyPool",
    "RecoveryConfig",
    "OptimizationWeights",
    "OptimizationConstraints",
    "SandboxSimulationResult",
    "CandidateObjectiveScore",
    "OptimizationDecision",
    "StochasticSimulationSummary",
    "TOPSISScore",
    "FeasibilityChecker",
    "build_no_action_candidate",
    "build_isolation_candidate",
    "build_reroute_candidate",
    "build_rate_limit_candidate",
    "build_reboot_candidate",
    "build_power_adjustment_candidate",
    "build_composite_isolate_and_bridge_candidate",
    "build_composite_throttle_and_reroute_candidate",
    "CandidateStrategyGenerator",
    "RecoverySandbox",
    "MultiObjectiveRecoveryOptimizer",
    "WEIGHT_PROFILES",
    "TOPSISRanker",
    "detect_cross_mitigation_collisions",
]



"""
Phase 9: Autonomous Self-Healing & Closed-Loop Verification.
Public exports for actuation dispatch, network execution, closed-loop verification,
automated rollback management, resilience metrics, and closed-loop coordination.
"""

from .models import (
    ActuationCommandType,
    CommandStatus,
    VerificationStatus,
    SPRTDecision,
    EscalationTier,
    ActuationCommand,
    CommandAck,
    ActuationBatch,
    VerificationCriterion,
    VerificationResult,
    RollbackSnapshot,
    RollbackExecutionResult,
    ResilienceMetrics,
    SPRTConfig,
    SPRTState,
    EscalationEvent,
    FlappingState,
)
from .dispatcher import ActuationPolicyDispatcher
from .actuator import NetworkActuator
from .verifier import ClosedLoopVerifier, WaldSPRTVerifier
from .rollback import RollbackManager
from .resilience import ResilienceEvaluator
from .coordinator import SelfHealingCoordinator
from .escalation import GraduatedEscalationManager
from .damping import RouteFlappingDamper

__all__ = [
    "ActuationCommandType",
    "CommandStatus",
    "VerificationStatus",
    "SPRTDecision",
    "EscalationTier",
    "ActuationCommand",
    "CommandAck",
    "ActuationBatch",
    "VerificationCriterion",
    "VerificationResult",
    "RollbackSnapshot",
    "RollbackExecutionResult",
    "ResilienceMetrics",
    "SPRTConfig",
    "SPRTState",
    "EscalationEvent",
    "FlappingState",
    "ActuationPolicyDispatcher",
    "NetworkActuator",
    "ClosedLoopVerifier",
    "WaldSPRTVerifier",
    "RollbackManager",
    "ResilienceEvaluator",
    "SelfHealingCoordinator",
    "GraduatedEscalationManager",
    "RouteFlappingDamper",
]

"""
Self-Healing Coordinator for Phase 9.
Unified orchestrator coordinating the complete closed-loop self-healing cycle:
decision ingestion -> state snapshot -> dispatch -> live actuation ->
closed-loop verification -> automated rollback (if failed) -> resilience metrics computation.
"""

from typing import Dict, List, Optional, Any, Tuple

from ..digital_twin.twin import DigitalTwin
from ..recovery.models import OptimizationDecision, RecoveryCandidate
from ..simulation.simulator import NetworkSimulator
from ..simulation.telemetry import TelemetryRecord
from .models import (
    ActuationBatch,
    CommandAck,
    VerificationResult,
    RollbackSnapshot,
    RollbackExecutionResult,
    ResilienceMetrics,
    EscalationTier,
)
from .dispatcher import ActuationPolicyDispatcher
from .actuator import NetworkActuator
from .verifier import ClosedLoopVerifier
from .rollback import RollbackManager
from .resilience import ResilienceEvaluator
from .escalation import GraduatedEscalationManager
from .damping import RouteFlappingDamper


class SelfHealingCoordinator:
    """
    Autonomous closed-loop controller coordinating execution, verification,
    safety rollback, graduated escalation, and resilience accounting across the IoT network.
    """

    def __init__(
        self,
        digital_twin: Optional[DigitalTwin] = None,
        simulator: Optional[NetworkSimulator] = None,
        dispatcher: Optional[ActuationPolicyDispatcher] = None,
        actuator: Optional[NetworkActuator] = None,
        verifier: Optional[ClosedLoopVerifier] = None,
        rollback_manager: Optional[RollbackManager] = None,
        resilience_evaluator: Optional[ResilienceEvaluator] = None,
        escalation_manager: Optional[GraduatedEscalationManager] = None,
        flapping_damper: Optional[RouteFlappingDamper] = None,
        enable_graduated_escalation: bool = True,
    ):
        self.digital_twin = digital_twin
        self.simulator = simulator
        self.dispatcher = dispatcher or ActuationPolicyDispatcher()
        self.actuator = actuator or NetworkActuator(simulator=simulator)
        self.verifier = verifier or ClosedLoopVerifier()
        self.rollback_manager = rollback_manager or RollbackManager()
        self.resilience_evaluator = resilience_evaluator or ResilienceEvaluator()
        self.escalation_manager = escalation_manager or GraduatedEscalationManager(dispatcher=self.dispatcher)
        self.flapping_damper = flapping_damper or RouteFlappingDamper()
        self.enable_graduated_escalation = enable_graduated_escalation

        if self.simulator and not self.actuator.simulator:
            self.actuator.bind_simulator(self.simulator)

        # Active incident tracking
        self.active_snapshot: Optional[RollbackSnapshot] = None
        self.active_batch: Optional[ActuationBatch] = None
        self.active_candidate: Optional[RecoveryCandidate] = None
        self.alternative_candidates: List[RecoveryCandidate] = []
        self.active_incident: Optional[Dict[str, Any]] = None
        self.completed_incidents: List[ResilienceMetrics] = []
        self.verification_history: List[VerificationResult] = []

    def start_incident(
        self,
        attack_type: str,
        t_attack_start: float,
        t_detect: float,
    ) -> None:
        """Registers the onset and detection of an active security incident."""
        self.active_incident = {
            "attack_type": attack_type,
            "t_attack_start": t_attack_start,
            "t_detect": t_detect,
            "t_actuate": None,
            "t_restored": None,
            "telemetry_records": [],
        }

    def execute_optimal_decision(
        self,
        decision: OptimizationDecision,
        current_time: float,
    ) -> Tuple[ActuationBatch, List[CommandAck]]:
        """
        Takes an OptimizationDecision s*, snapshots system state, dispatches downlink
        commands, and executes actuation on the live simulator.
        """
        self.active_candidate = decision.optimal_candidate
        self.escalation_manager.reset()

        # 1. Capture lossless rollback snapshot before applying any changes
        self.active_snapshot = self.rollback_manager.capture_snapshot(self.actuator, current_time)

        # 2. Decompose candidate into downlink actuation batch
        batch = self.dispatcher.create_actuation_batch(decision.optimal_candidate, current_time)

        # 3. Dispatch batch over wireless channel with loss modeling & retries
        batch, acks = self.dispatcher.dispatch_batch(batch, current_time)
        self.active_batch = batch

        # 4. Actuate acknowledged commands in the live simulation network
        for cmd in batch.commands:
            if cmd.status == "APPLIED":
                self.actuator.execute_command(cmd, current_time)

        # 5. Initialize Closed-Loop Verification loop
        self.verifier.start_verification(batch, current_time)

        if self.active_incident:
            self.active_incident["t_actuate"] = current_time

        return batch, acks

    def process_step_telemetry(
        self,
        current_time: float,
        step_records: List[TelemetryRecord],
        unmitigated_records: Optional[List[TelemetryRecord]] = None,
    ) -> Optional[VerificationResult]:
        """
        Step-by-step hook: ingests live telemetry, manages reboot recoveries,
        checks verification criteria, executes graduated escalation or automated rollback on failure,
        or computes multi-dimensional resilience metrics on successful recovery.
        """
        # 1. Simulator step maintenance (reboot completions)
        self.actuator.pre_step_maintenance(current_time)

        if self.active_incident:
            self.active_incident["telemetry_records"].extend(step_records)

        # 2. If verification is ongoing, evaluate criteria
        if self.active_batch and self.verifier._window_start_time is not None:
            self.verifier.ingest_telemetry_step(step_records)
            ver_res = self.verifier.evaluate_verification(current_time, self.digital_twin)
            self.verification_history.append(ver_res)

            # Check verification failure -> Graduated Escalation or Safety Rollback!
            if ver_res.verification_status == "VERIFICATION_FAILED":
                if self.enable_graduated_escalation and self.active_candidate:
                    escalation_outcome = self.escalation_manager.escalate(
                        current_candidate=self.active_candidate,
                        trigger_reason=ver_res.failure_reason or "Verification failed",
                        current_time=current_time,
                        digital_twin=self.digital_twin,
                        alternative_candidates=self.alternative_candidates,
                    )
                    if escalation_outcome is not None:
                        new_batch, new_tier = escalation_outcome
                        new_batch, acks = self.dispatcher.dispatch_batch(new_batch, current_time)
                        self.active_batch = new_batch
                        for cmd in new_batch.commands:
                            if cmd.status == "APPLIED":
                                self.actuator.execute_command(cmd, current_time)
                        self.verifier.start_verification(new_batch, current_time)
                        return ver_res

                # Maximum escalation tier exhausted or escalation disabled -> execute lossless rollback!
                if self.active_snapshot:
                    self.rollback_manager.execute_rollback(
                        self.active_snapshot,
                        self.actuator,
                        current_time,
                        trigger_reason=ver_res.failure_reason or "Verification failed",
                    )
                self.active_batch = None
                return ver_res

            # Check verification success -> Finalize Incident Resilience!
            elif ver_res.verification_status == "VERIFIED_SUCCESS":
                if self.active_incident:
                    self.active_incident["t_restored"] = current_time
                    metrics = self.resilience_evaluator.evaluate_incident_resilience(
                        attack_type=self.active_incident["attack_type"],
                        t_attack_start=self.active_incident["t_attack_start"],
                        t_detect=self.active_incident["t_detect"],
                        t_actuate=self.active_incident.get("t_actuate") or current_time,
                        t_restored=current_time,
                        telemetry_records=self.active_incident["telemetry_records"],
                        unmitigated_records=unmitigated_records,
                        sprt_verified=(ver_res.sprt_early_stopped or (ver_res.sprt_decision == "ACCEPT_H0_SUCCESS")),
                        escalation_tier=self.escalation_manager.get_current_tier(),
                    )
                    self.completed_incidents.append(metrics)
                    self.active_incident = None

                self.active_batch = None
                return ver_res

            return ver_res

        return None

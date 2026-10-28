"""
Data models and typed schemas for Phase 9:
Autonomous Self-Healing & Closed-Loop Verification.
Defines downlink actuation commands, acknowledgments, verification criteria,
rollback snapshots, and quantitative resilience metrics.
"""

from typing import Literal, Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field


ActuationCommandType = Literal[
    "ISOLATE_NODE",
    "REROUTE_TRAFFIC",
    "SET_RATE_LIMIT",
    "REBOOT_NODE",
    "ADJUST_TX_POWER",
    "COMPOSITE_ACTION",
    "ROLLBACK_ACTION",
]

CommandStatus = Literal[
    "PENDING",
    "DISPATCHED",
    "ACKNOWLEDGED",
    "APPLIED",
    "REJECTED",
    "TIMEOUT",
    "FAILED",
]

VerificationStatus = Literal[
    "PENDING",
    "DISPATCHED",
    "ACKNOWLEDGED",
    "VERIFYING",
    "VERIFIED_SUCCESS",
    "VERIFICATION_FAILED",
    "ROLLED_BACK",
]

SPRTDecision = Literal[
    "CONTINUE",
    "ACCEPT_H0_SUCCESS",
    "ACCEPT_H1_FAILURE",
]

EscalationTier = Literal[
    "TIER_1_PRIMARY_OPTIMAL",
    "TIER_2_SECONDARY_PARETO",
    "TIER_3_FAILSAFE_MST",
]


class SPRTConfig(BaseModel):
    """
    Configuration parameters for Wald's Sequential Probability Ratio Test (SPRT).
    Certifies nominal recovery (H0: loss <= p0) or persistent failure (H1: loss >= p1)
    with bounded type I error alpha and type II error beta.
    """
    p0: float = Field(default=0.03, ge=0.0, le=1.0, description="Nominal acceptable packet loss rate under H0")
    p1: float = Field(default=0.12, ge=0.0, le=1.0, description="Degraded/attack packet loss rate under H1")
    alpha: float = Field(default=0.01, gt=0.0, lt=1.0, description="Type I error bound (false alarm)")
    beta: float = Field(default=0.05, gt=0.0, lt=1.0, description="Type II error bound (missed detection)")
    max_samples: int = Field(default=30, ge=1, description="Truncation sample horizon")
    packets_per_step: int = Field(default=5, ge=1, description="Effective packet weight per telemetry sample step")

    @property
    def boundary_a(self) -> float:
        """Upper decision boundary A = ln((1 - beta) / alpha) > 0."""
        import math
        return math.log((1.0 - self.beta) / self.alpha)

    @property
    def boundary_b(self) -> float:
        """Lower decision boundary B = ln(beta / (1 - alpha)) < 0."""
        import math
        return math.log(self.beta / (1.0 - self.alpha))


class SPRTState(BaseModel):
    """
    Runtime tracking state of Wald's SPRT accumulator.
    """
    sample_count: int = Field(default=0, ge=0)
    dropped_count: int = Field(default=0, ge=0)
    log_likelihood_ratio: float = Field(default=0.0)
    boundary_a: float = Field(..., description="Upper boundary A")
    boundary_b: float = Field(..., description="Lower boundary B")
    decision: SPRTDecision = Field(default="CONTINUE")
    early_stopped: bool = Field(default=False)
    trajectory: List[float] = Field(default_factory=list, description="Historical sequence of Lambda_n")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class EscalationEvent(BaseModel):
    """
    Records a graduated escalation transition between mitigation tiers.
    """
    from_tier: str
    to_tier: str
    timestamp: float
    trigger_reason: str
    strategy_id: str
    preserved_connectivity: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class FlappingState(BaseModel):
    """
    Route and node flapping oscillation tracking state.
    Computes Omega_flap(t) = sum e^(-lambda * (t - t_k)).
    """
    node_id: int
    oscillation_index: float = Field(default=0.0, ge=0.0)
    last_switch_timestamp: float = Field(default=0.0, ge=0.0)
    switch_count: int = Field(default=0, ge=0)
    is_held_down: bool = Field(default=False)
    hold_down_until: float = Field(default=0.0, ge=0.0)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()



class ActuationCommand(BaseModel):
    """
    Individual downlink control command dispatched to an IoT node or gateway.
    Includes sequence ordering, cryptographic HMAC authentication, and TTL.
    """
    command_id: str = Field(..., description="Unique alphanumeric command identifier")
    target_node: int = Field(..., description="Target node ID receiving actuation instruction")
    command_type: ActuationCommandType = Field(..., description="Categorical actuation action")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Command parameters (e.g. rate_limit, bypass_routes, reboot_duration, tx_power_boost_dbm)"
    )
    sequence_number: int = Field(..., ge=0, description="Monotonically increasing sequence number for anti-replay")
    hmac_token: str = Field(..., description="Cryptographic HMAC-SHA256 authorization signature")
    timestamp: float = Field(..., ge=0.0, description="Dispatch timestamp in simulated seconds")
    ttl_seconds: float = Field(default=30.0, ge=1.0, description="Time-to-live validity window in seconds")
    status: CommandStatus = Field(default="PENDING", description="Current execution lifecycle status")
    retry_count: int = Field(default=0, ge=0, description="Number of retransmission attempts")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class CommandAck(BaseModel):
    """
    Uplink acknowledgment emitted by an actuated node back to the Digital Twin gateway.
    """
    command_id: str
    node_id: int
    status: CommandStatus
    round_trip_ms: float = Field(..., ge=0.0, description="Round-trip transmission latency in ms")
    timestamp: float = Field(..., ge=0.0, description="Timestamp of acknowledgment reception")
    message: str = Field(default="", description="Operational detail or error diagnosis")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ActuationBatch(BaseModel):
    """
    Bundle of atomic actuation commands synthesized from an optimal RecoveryDecision s*.
    """
    batch_id: str = Field(..., description="Unique identifier for the actuation batch")
    decision_epoch: float = Field(..., ge=0.0, description="Timestamp of triggering decision epoch")
    strategy_id: str = Field(..., description="Originating Phase 8 candidate strategy ID")
    action_type: str = Field(..., description="Phase 7 recovery action category")
    commands: List[ActuationCommand] = Field(default_factory=list, description="Downlink commands in batch")
    dispatch_timestamp: float = Field(default=0.0, ge=0.0, description="Timestamp batch was dispatched")
    all_acknowledged: bool = Field(default=False, description="True when all commands have received valid ACKs")
    total_retries: int = Field(default=0, ge=0, description="Total retransmission attempts across all commands")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class VerificationCriterion(BaseModel):
    """
    Individual health or performance condition evaluated during closed-loop verification.
    """
    criterion_name: str = Field(..., description="Descriptive criterion name (e.g. 'Network Connectivity')")
    metric_name: str = Field(..., description="Target telemetry metric evaluated")
    threshold: float = Field(..., description="Acceptable threshold boundary")
    operator: Literal[">=", "<=", "==", "!="] = Field(..., description="Comparison operator")
    actual_value: float = Field(..., description="Empirically observed value from post-actuation telemetry")
    passed: bool = Field(..., description="Whether observed value meets condition")
    severity: Literal["CRITICAL", "WARNING", "INFO"] = Field(default="CRITICAL")
    message: str = Field(default="", description="Verification outcome explanation")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class VerificationResult(BaseModel):
    """
    Aggregated result of the Closed-Loop Verification loop over verification window T_verify.
    """
    batch_id: str
    strategy_id: str
    verification_status: VerificationStatus
    is_successful: bool = Field(..., description="True if all critical criteria are satisfied")
    criteria_results: List[VerificationCriterion] = Field(default_factory=list)
    verification_duration_s: float = Field(..., ge=0.0, description="Elapsed verification window in seconds")
    observed_pdr: float = Field(..., ge=0.0, le=1.0, description="Observed Packet Delivery Ratio")
    observed_packet_loss: float = Field(..., ge=0.0, le=1.0, description="Observed Packet Loss Ratio")
    observed_latency_ms: float = Field(..., ge=0.0, description="Observed average latency in ms")
    observed_connected_components: int = Field(default=1, ge=1, description="Surviving connected graph components")
    failure_reason: Optional[str] = Field(default=None, description="Reason for verification failure if applicable")
    sprt_decision: Optional[str] = Field(default=None, description="Wald SPRT decision if enabled")
    sprt_log_likelihood: Optional[float] = Field(default=None, description="Current SPRT log-likelihood ratio Lambda_n")
    sprt_early_stopped: bool = Field(default=False, description="True if SPRT triggered early boundary termination")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class RollbackSnapshot(BaseModel):
    """
    Pre-actuation system snapshot capturing routing, rate limits, power, and connectivity
    prior to executing any actuation command, ensuring lossless automated rollback capability.
    """
    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    timestamp: float = Field(..., ge=0.0, description="Timestamp snapshot was recorded")
    isolated_nodes: List[int] = Field(default_factory=list, description="Currently isolated node IDs")
    rate_limits: Dict[int, float] = Field(default_factory=dict, description="Active rate limits per node")
    installed_routes: Dict[str, List[int]] = Field(default_factory=dict, description="Active route overrides")
    power_boosts: Dict[int, float] = Field(default_factory=dict, description="Active Tx power adjustments")
    topology_edges: List[Tuple[int, int]] = Field(default_factory=list, description="Active topology graph edges")
    node_states_summary: Dict[int, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Summary of node CPU, queue, and operational state"
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class RollbackExecutionResult(BaseModel):
    """
    Telemetry and status returned upon executing an automated rollback plan.
    """
    snapshot_id: str
    timestamp: float
    success: bool
    restored_components: List[str] = Field(default_factory=list)
    rollback_commands_dispatched: int = Field(default=0, ge=0)
    elapsed_ms: float = Field(default=0.0, ge=0.0)
    message: str = Field(default="")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ResilienceMetrics(BaseModel):
    """
    Quantitative resilience and self-healing performance metrics.
    Includes temporal responsiveness (MTTD, MTTA, MTTR) and the macroscopic
    QoS trajectory integral Resilience Score R.
    """
    attack_type: str = Field(..., description="Classified attack category (e.g., 'dos', 'compromised_node')")
    t_attack_start: float = Field(..., ge=0.0, description="Onset timestamp of attack")
    t_detect: float = Field(..., ge=0.0, description="Timestamp attack was detected by Phase 5/6")
    t_actuate: float = Field(..., ge=0.0, description="Timestamp optimal mitigation was actuated")
    t_restored: float = Field(..., ge=0.0, description="Timestamp closed-loop verification confirmed restoration")

    # Temporal responsiveness
    mttd_s: float = Field(..., ge=0.0, description="Mean Time to Detect: t_detect - t_attack_start")
    mtta_s: float = Field(..., ge=0.0, description="Mean Time to Actuate: t_actuate - t_detect")
    mttr_s: float = Field(..., ge=0.0, description="Mean Time to Recover: t_restored - t_detect")
    total_incident_time_s: float = Field(..., ge=0.0, description="Total incident span: t_restored - t_attack_start")

    # Macroscopic resilience integral: R = \int QoS(t) dt / (QoS_nominal * T)
    resilience_score_r: float = Field(..., ge=0.0, le=1.0, description="Resilience Score R [0.0, 1.0]")
    resilience_loss_index: float = Field(..., ge=0.0, le=1.0, description="Resilience degradation index: 1.0 - R")
    unmitigated_resilience_score: float = Field(..., ge=0.0, le=1.0, description="Resilience score if no action taken")
    resilience_advantage_delta: float = Field(
        ..., description="Comparative resilience advantage: R_autonomous - R_unmitigated"
    )

    # Bruneau Multi-Dimensional Resilience Metrics
    loss_of_resilience_lor: float = Field(default=0.0, ge=0.0, description=r"Loss of Resilience (LOR) deficit area in QoS-seconds: \int (1 - QoS(t)) dt")
    recovery_rapidity_v_rec: float = Field(default=0.0, ge=0.0, description="Recovery rapidity slope [QoS units / sec]")
    structural_robustness_s_robust: float = Field(default=0.0, ge=0.0, le=1.0, description="Structural robustness minimum retained QoS: min QoS(t)")
    sprt_verified: bool = Field(default=False, description="Whether Wald SPRT was utilized during verification")
    escalation_tier: str = Field(default="TIER_1_PRIMARY_OPTIMAL", description="Escalation tier reached during mitigation")

    # Dynamic trajectory: 'timestamps', 'pdr', 'latency', 'qos'
    qos_trajectory: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Temporal time series of QoS dynamics throughout the incident"
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

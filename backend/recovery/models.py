"""
Data models and typed schemas for the Candidate Recovery Strategy Generator.
Defines recovery actions, parameterized candidate strategies, strategy pools,
and operational generation configurations.
"""

from typing import Literal, Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


RecoveryActionType = Literal[
    "NO_ACTION",
    "NODE_ISOLATION",
    "DYNAMIC_REROUTING",
    "RATE_LIMITING",
    "NODE_REBOOT",
    "POWER_ADJUSTMENT",
    "COMPOSITE",
]


class RecoveryCandidate(BaseModel):
    """
    Structured representation of a concrete mitigation strategy candidate s_k in S.
    Fully parameterized for forward simulation in the Phase 8 Digital Twin sandbox.
    """
    strategy_id: str = Field(..., description="Unique alphanumeric identifier (e.g., 'STRAT_ISO_3')")
    action_type: RecoveryActionType = Field(..., description="Categorical mitigation action type")
    target_nodes: List[int] = Field(default_factory=list, description="Target node IDs subjected to mitigation")
    affected_nodes: List[int] = Field(default_factory=list, description="Neighboring nodes affected by rerouting or power change")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters (e.g. rate_limit_pkts_per_sec, alternate_routes, power_boost_dbm)"
    )
    estimated_cost: float = Field(default=1.0, ge=0.0, description="Estimated overhead / actuation cost [0.0, 10.0]")
    is_topology_partitioning: bool = Field(
        default=False,
        description="True if executing this action disconnects benign nodes into separate graph components"
    )
    expected_recovery_time_s: float = Field(
        default=5.0, ge=0.0,
        description="Estimated duration in seconds required to take effect"
    )
    rationale: str = Field(default="", description="Human-interpretable engineering explanation for candidate generation")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class StrategyPool(BaseModel):
    """
    Container for the set of candidate recovery strategies S = {s_0, s_1, ..., s_k}
    synthesized at a specific decision epoch.
    """
    timestamp: float = Field(..., ge=0.0, description="Decision epoch in simulated seconds")
    candidates: List[RecoveryCandidate] = Field(..., min_length=1, description="List of generated feasible candidates")
    trigger_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Triggering context (e.g. quarantined_nodes, average_risk, detected_attack)"
    )
    generation_latency_us: float = Field(default=0.0, ge=0.0, description="Computation time in microseconds")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def get_candidate(self, strategy_id: str) -> Optional[RecoveryCandidate]:
        for c in self.candidates:
            if c.strategy_id == strategy_id:
                return c
        return None


class RecoveryConfig(BaseModel):
    """
    Configuration parameters governing candidate generation, rate-limit thresholds,
    reboot durations, and topological constraints.
    """
    max_candidates_per_pool: int = Field(default=8, ge=2, le=20, description="Maximum number of candidates generated per pool")
    default_rate_limit_pkts_sec: float = Field(default=2.0, ge=0.5, description="Target packet rate cap for RATE_LIMITING")
    default_reboot_duration_s: float = Field(default=8.0, ge=1.0, description="Expected downtime during soft reboot")
    default_power_boost_dbm: float = Field(default=4.0, ge=1.0, le=10.0, description="Tx power boost for neighbor bridge links")
    allow_partitioning_candidates: bool = Field(
        default=True,
        description="Whether to include partitioning candidates marked with is_topology_partitioning=True"
    )
    base_action_costs: Dict[str, float] = Field(
        default_factory=lambda: {
            "NO_ACTION": 0.0,
            "RATE_LIMITING": 1.0,
            "DYNAMIC_REROUTING": 2.5,
            "NODE_ISOLATION": 3.0,
            "POWER_ADJUSTMENT": 4.0,
            "NODE_REBOOT": 5.0,
            "COMPOSITE": 5.5,
        }
    )


class OptimizationWeights(BaseModel):
    """
    Multi-objective cost function weights w_1, w_2, w_3, w_4 for J(s).
    J(s) = w_1*(Delta_Latency / Latency_base) + w_2*Delta_Loss + w_3*(Delta_Energy / Energy_base) + w_4*Signaling_Overhead
    """
    w_latency: float = Field(default=0.25, ge=0.0, le=1.0, description="Weight for normalized latency path stretch penalty (w_1)")
    w_loss: float = Field(default=0.35, ge=0.0, le=1.0, description="Weight for projected packet loss penalty (w_2)")
    w_energy: float = Field(default=0.25, ge=0.0, le=1.0, description="Weight for normalized battery depletion penalty (w_3)")
    w_overhead: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight for signaling and control overhead penalty (w_4)")

    @field_validator("w_overhead")
    @classmethod
    def validate_weights_sum(cls, v: float, info: Any) -> float:
        # Sum of weights should normalize to ~1.0
        data = info.data
        total = data.get("w_latency", 0.0) + data.get("w_loss", 0.0) + data.get("w_energy", 0.0) + v
        if abs(total - 1.0) > 0.05:
            # Tolerant normalization check
            pass
        return v

    def to_dict(self) -> Dict[str, float]:
        return self.model_dump()


class OptimizationConstraints(BaseModel):
    """
    Hard safety and operational constraints bounding strategy selection.
    """
    min_pdr: float = Field(default=0.70, ge=0.0, le=1.0, description="Minimum acceptable projected Packet Delivery Ratio")
    max_packet_loss: float = Field(default=0.30, ge=0.0, le=1.0, description="Maximum acceptable projected packet loss")
    allow_partitioning: bool = Field(default=False, description="Whether to reject candidates that cause graph partition")
    require_dag_routing: bool = Field(default=True, description="Strict requirement for loop-free routing DAG")
    min_node_energy_pct: float = Field(default=10.0, ge=0.0, le=100.0, description="Minimum allowable battery reserve")
    max_latency_ms: float = Field(default=200.0, ge=1.0, description="Maximum acceptable single-hop/end-to-end latency")


class StochasticSimulationSummary(BaseModel):
    """
    Monte-Carlo ensemble statistics across M stochastic forward rollouts
    incorporating channel RSSI fading and packet arrival rate jitter.
    """
    num_rollouts: int = Field(default=10, ge=2, description="Number of stochastic rollouts executed")
    pdr_mean: float = Field(..., description="Expected PDR across rollouts")
    pdr_std: float = Field(..., description="PDR standard deviation")
    pdr_ci95_lower: float = Field(..., description="95% confidence interval lower bound for PDR")
    pdr_ci95_upper: float = Field(..., description="95% confidence interval upper bound for PDR")
    loss_mean: float = Field(..., description="Expected packet loss")
    loss_std: float = Field(..., description="Packet loss standard deviation")
    latency_mean: float = Field(..., description="Expected latency in ms")
    latency_std: float = Field(..., description="Latency standard deviation")
    energy_mean: float = Field(..., description="Expected cumulative energy drain %")
    cvar_95_loss: float = Field(..., description="Conditional Value-at-Risk (worst 5% tail loss)")
    cost_j_mean: float = Field(default=0.0, description="Expected multi-objective cost J(s)")
    cost_j_cvar95: float = Field(default=0.0, description="Risk-averse CVaR_0.95 multi-objective cost")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class TOPSISScore(BaseModel):
    """
    Multi-Criteria Decision Analysis evaluation score using the TOPSIS method
    (Technique for Order of Preference by Similarity to Ideal Solution).
    """
    strategy_id: str
    action_type: RecoveryActionType
    closeness_coefficient: float = Field(..., ge=0.0, le=1.0, description="Relative closeness to Positive Ideal Solution C_i")
    distance_to_positive_ideal: float = Field(..., ge=0.0, description="Euclidean distance to Positive Ideal Solution d_i+")
    distance_to_negative_ideal: float = Field(..., ge=0.0, description="Euclidean distance to Negative Ideal Solution d_i-")
    topsis_rank: int = Field(..., ge=1, description="Ordinal ranking under TOPSIS (1 is best)")
    normalized_vector: Dict[str, float] = Field(default_factory=dict, description="Euclidean normalized metric coordinates")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class SandboxSimulationResult(BaseModel):
    """
    High-fidelity projected trajectory and aggregate metrics for a candidate strategy
    forward-simulated in the Digital Twin virtual sandbox over horizon H.
    """
    strategy_id: str = Field(..., description="Target candidate identifier")
    action_type: RecoveryActionType = Field(..., description="Mitigation action type simulated")
    horizon_s: float = Field(..., ge=1.0, description="Lookahead horizon in seconds")
    timestep: float = Field(default=1.0, ge=0.1, description="Simulation discrete timestep in seconds")

    # Projected macroscopic performance
    projected_pdr: float = Field(..., ge=0.0, le=1.0, description="Projected Packet Delivery Ratio [0.0, 1.0]")
    projected_packet_loss: float = Field(..., ge=0.0, le=1.0, description="Projected Packet Loss Ratio [0.0, 1.0]")
    projected_avg_latency_ms: float = Field(..., ge=0.0, description="Projected average latency in ms")
    projected_energy_drain_pct: float = Field(..., ge=0.0, description="Projected cumulative battery depletion in %")
    projected_active_node_ratio: float = Field(default=1.0, ge=0.0, le=1.0, description="Active / total node ratio")

    # Topological & graph health
    projected_connected_components: int = Field(default=1, ge=1, description="Number of connected components in topology")
    is_partitioned: bool = Field(default=False, description="True if benign network is partitioned")
    has_routing_loops: bool = Field(default=False, description="True if forwarding paths contain cycles")
    signaling_overhead: float = Field(default=1.0, ge=0.0, description="Control / reconfiguration message count")

    # Execution telemetry
    simulation_latency_ms: float = Field(default=0.0, ge=0.0, description="Sandbox simulation compute time in ms")

    # Optional Monte-Carlo uncertainty ensemble
    stochastic_summary: Optional[StochasticSimulationSummary] = Field(
        default=None, description="Monte-Carlo ensemble uncertainty statistics"
    )

    # Time-series trajectories for in-depth plotting & analysis
    time_series: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Per-second trajectories: 'loss', 'latency', 'energy', 'pdr', 'active_nodes'"
    )
    raw_details: Dict[str, Any] = Field(default_factory=dict, description="Detailed node states and route metadata")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class CandidateObjectiveScore(BaseModel):
    """
    Evaluated multi-objective cost breakdown and constraint feasibility for a candidate.
    """
    strategy_id: str
    action_type: RecoveryActionType
    cost_j: float = Field(..., description="Scalar multi-objective cost J(s_k)")
    normalized_latency_penalty: float = Field(..., ge=0.0, description="Normalized latency stretch (Delta_Latency / Latency_base)")
    loss_penalty: float = Field(..., ge=0.0, le=1.0, description="Projected packet loss Delta_Loss")
    normalized_energy_penalty: float = Field(..., ge=0.0, description="Normalized energy depletion (Delta_Energy / Energy_base)")
    signaling_overhead_penalty: float = Field(..., ge=0.0, description="Normalized signaling overhead")
    is_feasible: bool = Field(default=True, description="Whether candidate passes all hard safety constraints")
    constraint_violations: List[str] = Field(default_factory=list, description="Descriptions of violated constraints")
    is_pareto_optimal: bool = Field(default=False, description="True if member of non-dominated Pareto frontier S*")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class OptimizationDecision(BaseModel):
    """
    Optimal recovery decision s* synthesized at a decision epoch, along with
    Pareto frontier S* and candidate rankings.
    """
    decision_epoch: float = Field(..., ge=0.0, description="Decision timestamp in simulated seconds")
    optimal_strategy_id: str = Field(..., description="Selected optimal candidate strategy identifier s*")
    optimal_candidate: RecoveryCandidate = Field(..., description="Full specification of optimal recovery action")
    optimal_cost_j: float = Field(..., description="Minimal objective cost J(s*)")
    optimal_simulation_result: Optional[SandboxSimulationResult] = Field(default=None, description="Projected simulation trajectory for s*")
    ranked_candidates: List[CandidateObjectiveScore] = Field(..., description="All evaluated candidates sorted by J(s)")
    pareto_frontier_ids: List[str] = Field(default_factory=list, description="IDs of non-dominated candidates S*")
    topsis_rankings: List[TOPSISScore] = Field(default_factory=list, description="TOPSIS multi-criteria decision rankings")
    optimal_topsis_strategy_id: Optional[str] = Field(default=None, description="Optimal strategy selected by TOPSIS closeness")
    weights_used: OptimizationWeights
    constraints_used: OptimizationConstraints
    solving_latency_us: float = Field(default=0.0, ge=0.0, description="Optimization computation latency in microseconds")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()



"""
Data models and schemas for Phase 11:
End-to-End Experimental Research Framework & Automated Comparative Benchmarking.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field


class BaselineType(str, Enum):
    """Comparative baseline types evaluated in the research framework."""
    UNMITIGATED = "unmitigated"                                    # Baseline 1: No Detection / No Recovery
    STATIC_THRESHOLD_ISOLATION = "static_threshold_isolation"      # Baseline 2: Static Threshold IDS + Naive Isolation
    ML_FIXED_RECOVERY = "ml_fixed_recovery"                        # Baseline 3: ML Detection + Fixed Heuristic Recovery
    RL_RECOVERY = "rl_recovery"                                    # Baseline 4 (RL): Deep Reinforcement Learning (DQN) Recovery Policy
    PROPOSED_DIGITAL_TWIN = "proposed_digital_twin"                # Proposed: Full Closed-Loop Digital Twin Framework


class ExperimentMetricRecord(BaseModel):
    """Single-timestep physical and network state observation during an experiment run."""
    timestamp: float
    pdr: float = Field(..., description="Instantaneous network-wide Packet Delivery Ratio [0, 1]")
    packet_loss_rate: float = Field(..., description="Instantaneous packet loss rate [0, 1]")
    latency_ms: float = Field(..., description="Mean network latency in milliseconds")
    throughput_pps: float = Field(..., description="Instantaneous network throughput in pkts/s")
    mean_energy_remaining: float = Field(..., description="Average battery energy percentage across nodes")
    mean_cpu_utilization: float = Field(..., description="Average CPU utilization across nodes [0, 1]")
    active_node_count: int = Field(..., description="Number of actively operational nodes")
    connected_components: int = Field(..., description="Number of connected components k(G') in topology")
    is_partitioned: bool = Field(..., description="True if k(G') > 1 (network partition condition)")
    attack_active: bool = Field(..., description="True if attack injection window is active")
    mitigation_active: bool = Field(..., description="True if self-healing or baseline mitigation is applied")
    trust_score_target: Optional[float] = Field(None, description="Dynamic trust score of primary target node")


class ExperimentRunResult(BaseModel):
    """Complete summary of an individual experimental benchmark execution."""
    baseline: BaselineType
    attack_type: str
    target_node: int
    seed: int
    duration_s: float
    attack_start_s: float
    attack_end_s: float

    # Temporal responsiveness
    mttd_s: Optional[float] = Field(None, description="Mean Time to Detect (seconds)")
    mtta_s: Optional[float] = Field(None, description="Mean Time to Actuate (seconds)")
    mttr_s: Optional[float] = Field(None, description="Mean Time to Recover to >= 90% nominal QoS (seconds)")

    # Aggregate QoS and resilience metrics
    resilience_score: float = Field(..., description="Macroscopic integral Resilience Score R in [0, 1]")
    mean_pdr: float = Field(..., description="Time-averaged Packet Delivery Ratio")
    min_pdr: float = Field(..., description="Nadir Packet Delivery Ratio during incident")
    final_pdr: float = Field(..., description="Final steady-state Packet Delivery Ratio")
    mean_latency_ms: float = Field(..., description="Time-averaged network latency")
    max_latency_ms: float = Field(..., description="Peak network latency surge")
    total_packets_sent: int = Field(..., description="Total packets generated across nodes")
    total_packets_delivered: int = Field(..., description="Total packets successfully delivered to sink")
    total_packets_dropped: int = Field(..., description="Total packets lost / dropped")
    energy_consumed_j: float = Field(..., description="Total energy consumed across all nodes (Joules)")

    # Safety and topological integrity
    partition_events_count: int = Field(..., description="Count of timesteps where network was partitioned")
    partition_rate: float = Field(..., description="Fraction of time network experienced partitioning")
    rollback_count: int = Field(0, description="Count of safety rollbacks triggered")
    mitigation_action: Optional[str] = Field(None, description="Mitigation strategy executed")

    # Full timeseries trajectory (optional in summaries)
    timeseries: List[ExperimentMetricRecord] = Field(default_factory=list)


class BenchmarkConfig(BaseModel):
    """Configuration for an experimental benchmarking sweep."""
    baselines: List[BaselineType] = Field(
        default=[
            BaselineType.UNMITIGATED,
            BaselineType.STATIC_THRESHOLD_ISOLATION,
            BaselineType.ML_FIXED_RECOVERY,
            BaselineType.PROPOSED_DIGITAL_TWIN,
        ]
    )
    attack_types: List[str] = Field(default=["dos", "compromised_node", "node_failure", "on_off"])
    seeds: List[int] = Field(default_factory=lambda: list(range(42, 72)))
    duration_s: float = 120.0
    attack_start_s: float = 30.0
    attack_end_s: float = 90.0
    num_nodes: int = 6
    topology_layout: str = "mesh"
    weight_profile: str = "BALANCED"


class StatisticalComparison(BaseModel):
    """Rigorous two-sample statistical comparison between Proposed and a Baseline."""
    metric_name: str
    baseline: BaselineType
    proposed_mean: float
    baseline_mean: float
    delta_mean: float
    percent_improvement: float
    proposed_std: float
    baseline_std: float
    t_statistic: float
    p_value: float
    is_significant: bool = Field(..., description="True if p < 0.05")
    is_highly_significant: bool = Field(..., description="True if p < 0.001")
    cohens_d: float = Field(..., description="Standardized effect size (Cohen's d)")
    confidence_interval_95: Tuple[float, float] = Field(..., description="95% CI of the difference")
    mann_whitney_u: Optional[float] = Field(None, description="Mann-Whitney non-parametric U statistic")
    mann_whitney_p: Optional[float] = Field(None, description="Mann-Whitney asymptotic two-tailed p-value")
    statistical_power: Optional[float] = Field(None, description="Empirical post-hoc statistical power (1 - beta)")
    bayes_factor_10: Optional[float] = Field(None, description="Bayes Factor BF_10 evidence for alternative hypothesis")


class HorizonAblationRecord(BaseModel):
    """Ablation metrics for a specific lookahead horizon H."""
    horizon_s: int
    mean_pdr: float
    mttr_s: float
    prediction_rmse: float = Field(..., description="Root Mean Squared Error between sandbox and physical PDR")
    solve_latency_ms: float = Field(..., description="Optimization computation latency in milliseconds")
    resilience_score: float


class WeightSensitivityRecord(BaseModel):
    """Ablation metrics for a specific multi-objective weight profile."""
    profile_name: str
    weights: Tuple[float, float, float, float] = Field(..., description="(w1_latency, w2_loss, w3_energy, w4_signaling)")
    mean_pdr: float
    mean_latency_ms: float
    total_energy_consumed_j: float
    signaling_overhead_bytes: int
    selected_action: str
    resilience_score: float


class ChannelLossAblationRecord(BaseModel):
    """Ablation metrics under variable telemetry and actuation downlink loss."""
    channel_loss_rate: float = Field(..., description="Simulated wireless packet loss [0.0, 0.30]")
    downlink_delivery_rate: float
    mean_retries: float
    verification_delay_s: float
    resilience_score: float
    final_pdr: float


class TrustPenaltyAblationRecord(BaseModel):
    """Ablation metrics for dynamic trust asymmetry penalty ratio."""
    penalty_ratio: float = Field(..., description="Ratio lambda_penalty / lambda_recovery")
    mttd_s: float
    false_alarm_rate: float
    evasion_suppression_rate: float = Field(..., description="Fraction of volatile on-off cycles successfully flagged")
    resilience_score: float

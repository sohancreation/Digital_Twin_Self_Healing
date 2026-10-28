"""
Data Models and Typed Schemas for Phase 12:
Scalability, Edge Deployment & Network Stress Evaluation.
"""

from typing import Dict, List, Optional, Tuple, Any, Literal
from pydantic import BaseModel, Field


class NetworkScaleProfile(BaseModel):
    """Topological properties and dimensions for a scaled network."""
    num_nodes: int = Field(..., ge=2, description="Total node count N")
    layout: str = Field(..., description="Topology layout ('mesh', 'grid', 'random_geometric')")
    num_edges: int = Field(..., ge=0, description="Total communication links |E|")
    avg_degree: float = Field(..., ge=0.0, description="Average node degree")
    network_diameter: int = Field(..., ge=1, description="Graph diameter")
    clustering_coefficient: float = Field(..., ge=0.0, le=1.0, description="Average clustering coefficient")
    communication_range_m: float = Field(default=35.0, description="Node RF transmission range in meters")


class ComputationalProfileRecord(BaseModel):
    """Timing and resource consumption metrics across an operational control cycle."""
    num_nodes: int = Field(..., ge=2)
    topology_layout: str
    num_candidates_evaluated: int = Field(..., ge=1)
    lookahead_horizon_s: int = Field(..., ge=1)

    # Component-level execution latencies (milliseconds)
    sync_latency_ms: float = Field(..., ge=0.0, description="Telemetry batch ingestion & shadow update")
    trust_eval_latency_ms: float = Field(..., ge=0.0, description="Bayesian trust and hazard scoring")
    candidate_gen_latency_ms: float = Field(..., ge=0.0, description="Candidate strategy pool synthesis")
    sandbox_sim_latency_ms: float = Field(..., ge=0.0, description="In-silico forward sandbox simulation")
    optimization_latency_ms: float = Field(..., ge=0.0, description="Pareto / TOPSIS objective optimization")
    total_cycle_latency_ms: float = Field(..., ge=0.0, description="Sum of all closed-loop control stages")

    # Resource consumption
    memory_footprint_mb: float = Field(..., ge=0.0, description="Process RSS memory in Megabytes")
    memory_delta_mb: float = Field(..., description="Memory increase relative to baseline")
    cpu_percent: float = Field(..., ge=0.0, le=100.0, description="CPU core utilization percentage")


class TrafficStressRecord(BaseModel):
    """Network stability and QoS metrics under traffic rate scaling."""
    traffic_rate_pps: float = Field(..., ge=0.0, description="Traffic generation rate per node (pkts/s)")
    total_network_throughput_pps: float = Field(..., ge=0.0, description="Total network-wide packet generation rate")
    mean_pdr: float = Field(..., ge=0.0, le=1.0, description="Packet Delivery Ratio")
    min_pdr: float = Field(..., ge=0.0, le=1.0, description="Nadir Packet Delivery Ratio")
    mean_latency_ms: float = Field(..., ge=0.0, description="Mean end-to-end packet latency")
    queue_overflow_drops: int = Field(..., ge=0, description="Packets dropped due to buffer exhaustion")
    channel_loss_drops: int = Field(..., ge=0, description="Packets lost due to wireless channel fading")
    total_energy_consumed_j: float = Field(..., ge=0.0, description="Total energy consumed across all nodes")
    is_queue_saturated: bool = Field(..., description="True if queue buffers exceeded 90% capacity")
    is_system_stable: bool = Field(..., description="True if mean PDR >= 0.85 and buffer drops <= 15%")


class MultiTargetAttackRecord(BaseModel):
    """Resilience metrics under coordinated multi-node adversarial attacks."""
    num_compromised_nodes: int = Field(..., ge=1, description="Count of simultaneous adversary nodes K")
    compromised_node_ids: List[int] = Field(default_factory=list)
    attack_type: str = Field(..., description="Attack archetype ('coordinated_dos', 'multi_grayhole', 'distributed_failure')")
    total_network_nodes: int = Field(..., ge=2)
    mean_pdr: float = Field(..., ge=0.0, le=1.0)
    nadir_pdr: float = Field(..., ge=0.0, le=1.0)
    resilience_score: float = Field(..., ge=0.0, le=1.0, description="Macroscopic integral Resilience Score R")
    mttr_s: Optional[float] = Field(None, description="Mean Time to Recover (seconds)")
    partition_events_count: int = Field(0, description="Network partition instances")
    rollback_count: int = Field(0, description="Safety rollbacks executed")
    mitigation_action: str = Field(..., description="Multi-node mitigation strategy applied")


class EdgeGatewaySpec(BaseModel):
    """Specification and hardware budget for an edge IoT deployment platform."""
    gateway_name: str = Field(..., description="Platform identifier (e.g. 'Raspberry Pi 4', 'Jetson Nano')")
    processor_arch: str = Field(..., description="Processor architecture (e.g. 'Cortex-A72 @ 1.5GHz')")
    ram_capacity_mb: int = Field(..., ge=4, description="Total onboard RAM in Megabytes")
    real_time_deadline_ms: float = Field(default=100.0, description="Maximum allowable closed-loop control cycle deadline")
    observed_cycle_latency_ms: float = Field(..., ge=0.0)
    deadline_slack_ms: float = Field(..., description="deadline - observed_latency (positive = margin)")
    is_deadline_met: bool = Field(..., description="True if observed latency <= deadline")
    max_supported_nodes: int = Field(..., ge=1, description="Maximum network size supported within deadline")


class AsymptoticFitResult(BaseModel):
    """Empirical complexity curve fitting result against theoretical Big-O models."""
    pipeline_stage: str = Field(..., description="Component name (e.g. 'synchronizer', 'sandbox_simulation')")
    theoretical_complexity: str = Field(..., description="Formal model (e.g. 'O(N)', 'O(N^2)', 'O(|S| * H)')")
    fitted_model_name: str = Field(..., description="Fitted functional form (e.g. 'Linear', 'Quadratic', 'Log-Linear')")
    coefficients: List[float] = Field(default_factory=list, description="Regression polynomial coefficients")
    r_squared: float = Field(..., ge=0.0, le=1.0, description="Coefficient of determination R^2")
    empirical_pass: bool = Field(..., description="True if R^2 >= 0.90")


class ScalabilityCampaignResult(BaseModel):
    """Full aggregated dataset from a complete Phase 12 scalability and stress campaign."""
    scale_profiles: List[NetworkScaleProfile] = Field(default_factory=list)
    computational_profiles: List[ComputationalProfileRecord] = Field(default_factory=list)
    traffic_stress_records: List[TrafficStressRecord] = Field(default_factory=list)
    multi_target_attacks: List[MultiTargetAttackRecord] = Field(default_factory=list)
    edge_gateway_evaluations: List[EdgeGatewaySpec] = Field(default_factory=list)
    asymptotic_fits: List[AsymptoticFitResult] = Field(default_factory=list)

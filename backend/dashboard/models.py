"""
Data models and typed schemas for Phase 10:
Real-Time Research Monitoring Dashboard.
Defines payloads for topology state, telemetry streaming frames, ML predictions,
trust breakdowns, shadow fidelity, and interactive control triggers.
"""

from typing import Dict, List, Optional, Any, Tuple, Literal
from pydantic import BaseModel, Field


NodeOperationalState = Literal[
    "NOMINAL",
    "ATTACKED",
    "DEGRADED",
    "QUARANTINED",
    "REBOOTING",
    "OFFLINE",
]

LinkDisplayStatus = Literal[
    "ACTIVE",
    "CONGESTED",
    "SEVERED",
    "BRIDGED",
]


class NodeDisplayState(BaseModel):
    """
    Visual and operational telemetry state of an individual IoT node.
    """
    node_id: int = Field(..., description="Unique node integer identifier")
    x: float = Field(..., description="2D visual layout X coordinate")
    y: float = Field(..., description="2D visual layout Y coordinate")
    is_alive: bool = Field(default=True, description="Physical hardware responsiveness")
    connection_state: str = Field(default="CONNECTED", description="Connection status: CONNECTED or DISCONNECTED")
    operational_state: NodeOperationalState = Field(default="NOMINAL", description="High-level operational health mode")
    trust_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Bayesian trust score in [0.0, 1.0]")
    packet_rate: float = Field(default=2.0, ge=0.0, description="Packets transmitted per second")
    forwarding_rate: float = Field(default=2.0, ge=0.0, description="Transit packets forwarded per second")
    packet_loss: float = Field(default=0.02, ge=0.0, le=1.0, description="Observed packet loss ratio")
    latency_ms: float = Field(default=12.0, ge=0.0, description="Round-trip transmission latency in ms")
    energy_pct: float = Field(default=100.0, ge=0.0, le=100.0, description="Remaining battery reserve percentage")
    cpu_pct: float = Field(default=10.0, ge=0.0, le=100.0, description="Node processor utilization percentage")
    queue_length: int = Field(default=0, ge=0, description="Ingress transmission buffer queue length")
    is_cut_vertex: bool = Field(default=False, description="True if node is a topological articulation point")
    rate_limit: Optional[float] = Field(default=None, description="Active token bucket ingress limit if throttled")
    t_fused: float = Field(default=1.0, ge=0.0, le=1.0, description="Theorem 4 GNN-Bayesian Fused Trust")
    t_gnn: float = Field(default=1.0, ge=0.0, le=1.0, description="GNN Predicted Trust")
    gnn_threat: str = Field(default="Normal", description="GNN classified attack category")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class EdgeDisplayState(BaseModel):
    """
    Visual state of a wireless communication link between neighboring nodes.
    """
    source: int
    target: int
    status: LinkDisplayStatus = Field(default="ACTIVE")
    rssi_dbm: float = Field(default=-55.0, description="Received Signal Strength Indicator in dBm")
    packet_loss: float = Field(default=0.01, ge=0.0, le=1.0)
    latency_ms: float = Field(default=12.0, ge=0.0)
    is_bridged: bool = Field(default=False, description="True if link is formed via power-boosted bridge")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class TopologySnapshot(BaseModel):
    """
    Full network graph topology representation for canvas rendering.
    """
    nodes: List[NodeDisplayState] = Field(default_factory=list)
    edges: List[EdgeDisplayState] = Field(default_factory=list)
    connected_components: int = Field(default=1, ge=1)
    is_partitioned: bool = Field(default=False)
    graph_diameter: int = Field(default=2)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class MLPredictionState(BaseModel):
    """
    Real-time machine learning threat classification inference output.
    """
    predicted_label: str = Field(default="normal", description="Classified attack category or 'normal'")
    is_anomaly: bool = Field(default=False, description="Binary anomaly flag")
    confidence: float = Field(default=0.98, ge=0.0, le=1.0)
    probabilities: Dict[str, float] = Field(
        default_factory=lambda: {"normal": 0.98, "dos": 0.01, "compromised": 0.01, "failure": 0.0}
    )
    inference_latency_ms: float = Field(default=0.85, ge=0.0)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class TrustBreakdownState(BaseModel):
    """
    Multi-dimensional Bayesian trust score breakdown for an inspected node.
    """
    node_id: int
    composite_trust: float = Field(..., ge=0.0, le=1.0)
    direct_trust: float = Field(..., ge=0.0, le=1.0)
    recommendation_trust: float = Field(..., ge=0.0, le=1.0)
    volatility_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    is_trusted: bool = Field(default=True)
    classification: str = Field(default="TRUSTED")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class FidelityMetricState(BaseModel):
    """
    Physical-to-Virtual Shadow synchronization and tracking fidelity metrics.
    """
    clock_drift_ms: float = Field(default=0.0, description="Desynchronization time skew in ms")
    mean_state_discrepancy: float = Field(default=0.005, description="L2 norm difference between physical and virtual states")
    loss_delta: float = Field(default=0.002, description="Absolute packet loss delta")
    latency_delta_ms: float = Field(default=0.4, description="Absolute latency discrepancy")
    shadow_fidelity_score: float = Field(default=0.995, ge=0.0, le=1.0, description="Overall digital twin tracking accuracy")
    synchronized_nodes: int = Field(default=6)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class HealingAuditState(BaseModel):
    """
    Closed-loop mitigation, verification, and resilience audit event.
    """
    decision_epoch: float = Field(..., ge=0.0)
    chosen_strategy_id: Optional[str] = Field(default=None)
    action_type: Optional[str] = Field(default=None)
    target_nodes: List[int] = Field(default_factory=list)
    multi_objective_cost_j: Optional[float] = Field(default=None)
    topsis_score: Optional[float] = Field(default=None)
    sprt_log_likelihood: Optional[float] = Field(default=None)
    sprt_decision: Optional[str] = Field(default=None)
    escalation_tier: str = Field(default="TIER_1_PRIMARY_OPTIMAL")
    flapping_index: float = Field(default=0.0)
    is_flapping_held_down: bool = Field(default=False)
    verification_status: str = Field(default="PENDING")
    resilience_score_r: Optional[float] = Field(default=None)
    explanation_summary: str = Field(default="")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class GNNTelemetryState(BaseModel):
    """
    Real-time Spatio-Temporal Graph Attention Network (BridgeAwareGAT) state.
    """
    model_loaded: bool = Field(default=True)
    predicted_classes: Dict[str, str] = Field(default_factory=dict)
    threat_probabilities: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    t_gnn: Dict[str, float] = Field(default_factory=dict)
    t_fused: Dict[str, float] = Field(default_factory=dict)
    attention_matrix: List[List[float]] = Field(default_factory=list)
    cut_vertices: List[int] = Field(default_factory=list)
    detour_active: bool = Field(default=False)
    inference_latency_ms: float = Field(default=0.72)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class TelemetryFrame(BaseModel):
    """
    Full real-time streaming frame broadcasted to dashboard clients via WebSocket.
    """
    tick: int = Field(..., ge=0, description="Monotonically increasing sequence step tick")
    timestamp: float = Field(..., ge=0.0, description="Simulated time in seconds")
    topology: TopologySnapshot
    active_attacks: List[Dict[str, Any]] = Field(default_factory=list)
    network_pdr: float = Field(..., ge=0.0, le=1.0)
    network_loss: float = Field(..., ge=0.0, le=1.0)
    network_latency_ms: float = Field(..., ge=0.0)
    network_throughput_pkts_s: float = Field(..., ge=0.0)
    network_energy_pct: float = Field(..., ge=0.0, le=100.0)
    instantaneous_qos: float = Field(..., ge=0.0, le=1.0)
    macroscopic_resilience_r: float = Field(default=1.0, ge=0.0, le=1.0)
    fidelity: FidelityMetricState
    recent_audit: Optional[HealingAuditState] = None
    ml_prediction: Optional[MLPredictionState] = None
    gnn: Optional[GNNTelemetryState] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AttackTriggerRequest(BaseModel):
    """
    Request schema to inject an active cyberattack scenario into the live simulation.
    """
    attack_type: Literal["dos", "compromised_node", "node_failure", "on_off_cycling"]
    target_node: int = Field(..., description="Target node ID receiving malicious payload")
    duration_s: float = Field(default=15.0, ge=1.0, le=120.0, description="Attack duration in seconds")
    intensity: float = Field(default=1.0, ge=0.1, le=5.0, description="Attack intensity / rate multiplier")
    drop_probability: float = Field(default=0.75, ge=0.0, le=1.0, description="Selective drop probability if applicable")


class HealingTriggerRequest(BaseModel):
    """
    Request schema to force evaluation, optimization, and live actuation of mitigations.
    """
    target_node: Optional[int] = None
    weight_profile: str = Field(default="BALANCED", description="Optimization profile: BALANCED, SECURITY_FIRST, ENERGY_CONSTRAINED, LATENCY_CRITICAL")
    force_escalation: bool = Field(default=False)


class RollbackTriggerRequest(BaseModel):
    """
    Request schema to force automated safety rollback to the pre-actuation baseline.
    """
    reason: str = Field(default="Operator manual rollback trigger")


class ScenarioRunRequest(BaseModel):
    """
    Request schema to load and execute an automated end-to-end multi-attack scenario.
    """
    scenario_id: str = Field(default="180s_multi_attack_benchmark")
    speed_multiplier: float = Field(default=1.0, ge=0.2, le=10.0)

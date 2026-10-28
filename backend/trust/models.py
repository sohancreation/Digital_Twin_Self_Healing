"""
Data models and typed schemas for the Dynamic Risk & Trust Assessment Engine.
Defines trust components, node-level trust evaluations, macro network trust summaries,
and behavioral evaluation configurations.
"""

from typing import Literal, Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, field_validator
import numpy as np


class TrustComponents(BaseModel):
    """
    Decomposed sub-trust values across orthogonal behavioral dimensions.
    All components normalized to [0.0, 1.0], where 1.0 indicates optimal fidelity.
    """
    forwarding_trust: float = Field(..., ge=0.0, le=1.0, description="Packet forwarding compliance score")
    energy_trust: float = Field(..., ge=0.0, le=1.0, description="Energy consumption consistency score")
    loss_trust: float = Field(..., ge=0.0, le=1.0, description="Channel loss fidelity score")
    ml_trust: float = Field(..., ge=0.0, le=1.0, description="ML intrusion detection trust (1.0 - P_attack)")
    recommendation_trust: Optional[float] = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Bayesian neighbor consensus recommendation trust with collusion filtering"
    )

    def to_dict(self) -> Dict[str, float]:
        return self.model_dump()


class NodeTrustEvaluation(BaseModel):
    """
    Comprehensive trust and risk evaluation record for an individual IoT node.
    """
    node_id: int = Field(..., ge=0, description="Unique node identifier")
    timestamp: float = Field(..., ge=0.0, description="Evaluation timestamp in simulated seconds")
    components: TrustComponents = Field(..., description="Decomposed sub-trust components")
    instantaneous_trust: float = Field(..., ge=0.0, le=1.0, description="Raw weighted instantaneous composite trust")
    smoothed_trust: float = Field(..., ge=0.0, le=1.0, description="Asymmetrically smoothed historical trust")
    trust_volatility: float = Field(
        default=0.0, ge=0.0,
        description="Rolling standard deviation of instantaneous trust (detects cycling/instability)"
    )
    operational_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Operational confidence score (depressed by high trust volatility)"
    )
    trust_state: Literal["TRUSTED", "SUSPICIOUS", "QUARANTINED"] = Field(
        default="TRUSTED",
        description="Categorical operational trust state"
    )
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Systemic risk score")
    criticality_factor: float = Field(..., ge=0.0, le=1.0, description="Topological centrality importance factor")
    cascading_hazard: float = Field(
        default=0.10, ge=0.0, le=1.0,
        description="Downstream load transfer / neighbor congestion hazard upon node isolation"
    )
    threat_severity: float = Field(default=0.0, ge=0.0, le=1.0, description="Assessed attack vector severity")
    attack_probability: float = Field(default=0.0, ge=0.0, le=1.0, description="Phase 5 ML attack probability")
    detected_attack_type: str = Field(default="normal", description="Phase 5 classified attack category")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class NetworkTrustSummary(BaseModel):
    """
    Macroscopic aggregation of network-wide trust and systemic risk conditions.
    """
    timestamp: float = Field(..., ge=0.0)
    total_nodes: int = Field(..., ge=0)
    trusted_node_count: int = Field(..., ge=0)
    suspicious_node_count: int = Field(..., ge=0)
    quarantined_node_count: int = Field(..., ge=0)
    average_trust: float = Field(..., ge=0.0, le=1.0)
    minimum_trust: float = Field(..., ge=0.0, le=1.0)
    average_risk: float = Field(..., ge=0.0, le=1.0)
    maximum_risk: float = Field(..., ge=0.0, le=1.0)
    quarantined_node_ids: List[int] = Field(default_factory=list)
    network_health_recommendation: Literal["STABLE", "MONITOR", "CONTAINMENT_REQUIRED", "EMERGENCY_REROUTE"] = Field(
        default="STABLE"
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class TrustConfig(BaseModel):
    """
    Configuration parameters governing trust weights, asymmetric decay rates,
    topological weighting, and operational classification boundaries.
    """
    # 1. Multi-dimensional trust weights (alpha + beta + gamma + delta = 1.0)
    weight_forwarding: float = Field(default=0.30, ge=0.0, le=1.0, description="Weight alpha for forwarding compliance")
    weight_energy: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight beta for energy consistency")
    weight_loss: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight gamma for channel loss fidelity")
    weight_ml: float = Field(default=0.40, ge=0.0, le=1.0, description="Weight delta for ML security probability")

    # 2. Asymmetric temporal dynamics (penalty vs recovery rate)
    penalty_decay_rate: float = Field(
        default=0.40, ge=0.01, le=1.0,
        description="Smoothing factor lambda_penalty when observed trust degrades (rapid collapse)"
    )
    recovery_decay_rate: float = Field(
        default=0.05, ge=0.001, le=0.50,
        description="Smoothing factor lambda_recovery when observed trust improves (gradual recovery)"
    )

    # 3. Categorical classification thresholds
    threshold_trusted: float = Field(default=0.70, ge=0.0, le=1.0, description="Minimum trust for TRUSTED status")
    threshold_quarantine: float = Field(default=0.40, ge=0.0, le=1.0, description="Trust below which node is QUARANTINED")
    threshold_risk_quarantine: float = Field(default=0.65, ge=0.0, le=1.0, description="Risk above which node is QUARANTINED")

    # 4. Systemic risk weighting
    weight_criticality: float = Field(default=0.60, ge=0.0, le=1.0, description="Weight of topological centrality in risk")
    weight_severity: float = Field(default=0.40, ge=0.0, le=1.0, description="Weight of attack vector severity in risk")

    # 5. Attack vector severity mappings
    severity_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "normal": 0.05,
            "dos": 0.85,
            "compromised_node": 0.95,
            "node_failure": 0.70,
        }
    )

    # 6. Physical & behavioral baseline tolerances
    nominal_energy_drain_per_pkt: float = Field(default=0.0008, ge=0.0, description="Expected battery % consumed per packet")
    energy_tolerance_multiplier: float = Field(default=3.0, ge=1.0, description="Tolerance factor before penalizing drain")
    max_expected_packet_loss: float = Field(default=0.15, ge=0.0, le=1.0, description="Max normal loss due to fading alone")

    @field_validator("weight_ml")
    @classmethod
    def validate_weights_sum(cls, v, info):
        # We allow small floating point slack
        weights = [
            info.data.get("weight_forwarding", 0.30),
            info.data.get("weight_energy", 0.15),
            info.data.get("weight_loss", 0.15),
            v
        ]
        total = sum(weights)
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Trust weights must sum to 1.0, got {total:.4f}")
        return v

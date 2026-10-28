"""
Data models and configuration schemas for the Cyberattack Simulation Framework.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class AttackConfig(BaseModel):
    """
    Validated configuration for an individual cyberattack or fault injection scenario.
    """
    attack_id: str = Field(..., description="Unique alphanumeric attack scenario identifier (e.g., 'DOS_001')")
    attack_type: Literal["normal", "dos", "compromised_node", "node_failure"] = Field(
        ...,
        description="Type of attack scenario"
    )
    target_nodes: List[int] = Field(..., min_length=1, description="List of target node IDs subjected to attack")
    start_time: float = Field(..., ge=0.0, description="Attack injection start time in simulated seconds")
    end_time: float = Field(..., gt=0.0, description="Attack termination time in simulated seconds (exclusive)")
    intensity: float = Field(default=1.0, ge=0.0, description="Quantitative intensity parameter (interpretation depends on attack_type)")
    enabled: bool = Field(default=True, description="Whether this attack scenario is active in the schedule")

    @field_validator("end_time")
    @classmethod
    def validate_time_window(cls, v: float, info) -> float:
        start = info.data.get("start_time")
        if start is not None and v <= start:
            raise ValueError(f"end_time ({v}) must be strictly greater than start_time ({start})")
        return v

    @field_validator("target_nodes")
    @classmethod
    def validate_target_nodes(cls, nodes: List[int]) -> List[int]:
        if not nodes:
            raise ValueError("target_nodes cannot be empty")
        for n in nodes:
            if n < 0:
                raise ValueError(f"target node ID must be non-negative, got {n}")
        return sorted(list(set(nodes)))

    @field_validator("intensity")
    @classmethod
    def validate_intensity_bounds(cls, v: float, info) -> float:
        atype = info.data.get("attack_type")
        if atype == "compromised_node" and not (0.0 <= v <= 1.0):
            raise ValueError(f"For compromised_node, intensity represents packet drop probability in [0.0, 1.0], got {v}")
        return v


class AttackGroundTruth(BaseModel):
    """
    Ground-truth annotation emitted per node per timestep.
    Kept separate from TelemetryRecord to prevent physical telemetry contamination.
    """
    timestamp: float = Field(..., ge=0.0, description="Simulation timestamp in seconds")
    node_id: int = Field(..., ge=0, description="Node identifier")
    attack_active: int = Field(..., ge=0, le=1, description="Binary indicator: 1 if attack active on node, 0 otherwise")
    attack_type: str = Field(default="normal", description="Attack type label ('normal', 'dos', 'compromised_node', 'node_failure')")
    attack_id: Optional[str] = Field(default=None, description="Identifier of the active attack scenario")
    target_node: Optional[int] = Field(default=None, description="Primary target node ID")
    intensity: float = Field(default=0.0, ge=0.0, description="Quantitative attack intensity")
    is_indirectly_affected: bool = Field(
        default=False,
        description="True if node is not direct target but experiences collateral network effects (e.g. routing detour)"
    )

    def to_dict(self):
        return self.model_dump()

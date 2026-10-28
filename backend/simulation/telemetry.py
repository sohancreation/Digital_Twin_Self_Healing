"""
Structured telemetry schema and serialization for IoT nodes.
Provides standard abstraction for simulator, Digital Twin, and eventual hardware.
"""

from typing import Literal, Dict, Any, List
import pandas as pd
from pydantic import BaseModel, Field, field_validator


class TelemetryRecord(BaseModel):
    """
    Standardized, type-safe telemetry record emitted by each IoT node per timestep.
    Acts as the primary contract between physical/simulated nodes and upstream components.
    """
    timestamp: float = Field(..., ge=0.0, description="Simulation or wall-clock epoch timestamp in seconds")
    node_id: int = Field(..., ge=0, description="Unique integer identifier for the node")
    packet_rate: float = Field(..., ge=0.0, description="Locally generated packets per second (pkt/s)")
    forwarding_rate: float = Field(..., ge=0.0, description="Forwarded in-transit packets per second (pkt/s)")
    packet_loss: float = Field(..., ge=0.0, le=1.0, description="Packet loss ratio within [0.0, 1.0]")
    latency: float = Field(..., ge=0.0, description="Average end-to-end or single-hop latency in milliseconds")
    rssi: float = Field(..., le=0.0, description="Average received signal strength indicator in dBm")
    energy: float = Field(..., ge=0.0, le=100.0, description="Remaining battery energy percentage [0.0, 100.0]")
    cpu: float = Field(..., ge=0.0, le=100.0, description="CPU utilization percentage [0.0, 100.0]")
    memory: float = Field(..., ge=0.0, le=100.0, description="RAM utilization percentage [0.0, 100.0]")
    neighbor_count: int = Field(..., ge=0, description="Number of currently active 1-hop wireless neighbors")
    connection_state: Literal["CONNECTED", "DEGRADED", "DISCONNECTED"] = Field(
        default="CONNECTED",
        description="Logical network link state"
    )
    routing_state: Literal["IDLE", "ROUTING", "CONGESTED"] = Field(
        default="IDLE",
        description="Routing queue/processing state"
    )
    threat_level: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Assigned threat level [0.0 = Benign, 1.0 = High Threat]"
    )
    trust_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Computed node trust score [0.0 = Untrusted, 1.0 = Fully Trusted]"
    )

    @field_validator("packet_loss", "energy", "cpu", "memory", "threat_level", "trust_score")
    @classmethod
    def check_percentage_or_ratio_bounds(cls, v: float, info) -> float:
        if info.field_name == "packet_loss" and not (0.0 <= v <= 1.0):
            raise ValueError(f"packet_loss {v} outside valid range [0.0, 1.0]")
        if info.field_name in ("energy", "cpu", "memory") and not (0.0 <= v <= 100.0):
            raise ValueError(f"{info.field_name} {v} outside valid percentage range [0.0, 100.0]")
        if info.field_name in ("threat_level", "trust_score") and not (0.0 <= v <= 1.0):
            raise ValueError(f"{info.field_name} {v} outside valid range [0.0, 1.0]")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to primitive Python dictionary."""
        return self.model_dump()


def telemetry_records_to_dataframe(records: List[TelemetryRecord]) -> pd.DataFrame:
    """Converts a sequence of TelemetryRecord objects into a pandas DataFrame."""
    if not records:
        return pd.DataFrame(columns=[field for field in TelemetryRecord.model_fields.keys()])
    data = [r.model_dump() for r in records]
    df = pd.DataFrame(data)
    # Ensure consistent column ordering matching the schema
    columns = list(TelemetryRecord.model_fields.keys())
    return df[columns]

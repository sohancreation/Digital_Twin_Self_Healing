"""
Configuration models and utilities for the IoT Network Simulator.
Uses Pydantic for validation and type safety.
"""

from typing import Literal, Optional, Dict, Any
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, field_validator


class SimulationConfig(BaseModel):
    """General simulation timing and execution parameters."""
    nodes: int = Field(default=6, ge=2, le=500, description="Number of IoT nodes in the network")
    duration: float = Field(default=300.0, gt=0, description="Simulation duration in seconds")
    timestep: float = Field(default=1.0, gt=0, le=60.0, description="Simulation step interval in seconds")
    seed: Optional[int] = Field(default=42, description="Deterministic pseudo-random seed")


class TopologyConfig(BaseModel):
    """Network topology configuration parameters."""
    type: Literal["grid", "random", "mesh", "ring", "star", "scale_free"] = Field(
        default="grid",
        description="Topology structure type"
    )
    area_width: float = Field(default=100.0, gt=0, description="Field width in meters")
    area_height: float = Field(default=100.0, gt=0, description="Field height in meters")
    comm_range: float = Field(default=55.0, gt=0, description="Maximum wireless communication range in meters")
    grid_rows: Optional[int] = Field(default=2, ge=1, description="Rows for grid topology")
    grid_cols: Optional[int] = Field(default=3, ge=1, description="Columns for grid topology")


class TrafficConfig(BaseModel):
    """Traffic generation and queuing parameters."""
    base_packet_rate: float = Field(default=2.0, ge=0.0, description="Mean packets generated per second per node")
    packet_rate_std: float = Field(default=0.4, ge=0.0, description="Standard deviation of packet generation rate")
    packet_size_bytes: int = Field(default=128, ge=16, le=1500, description="Average packet payload size in bytes")
    max_queue_size: int = Field(default=50, ge=5, le=1000, description="Node buffer queue capacity (packets)")


class ChannelConfig(BaseModel):
    """Wireless channel and physical layer propagation parameters."""
    tx_power_dbm: float = Field(default=14.0, description="Transmit power in dBm (e.g., standard LoRa/ESP-NOW)")
    path_loss_exponent: float = Field(default=2.8, ge=1.5, le=5.0, description="Log-distance path loss exponent")
    ref_distance_m: float = Field(default=1.0, gt=0, description="Reference distance in meters")
    ref_rssi_dbm: float = Field(default=-30.0, le=0.0, description="RSSI at reference distance in dBm")
    rssi_noise_std: float = Field(default=2.0, ge=0.0, description="Standard deviation of shadowing noise in dB")
    min_rssi_dbm: float = Field(default=-120.0, description="Physical receiver sensitivity threshold in dBm")
    max_rssi_dbm: float = Field(default=-10.0, description="Maximum saturation RSSI in dBm")


class ResourceConfig(BaseModel):
    """Energy, CPU, and memory consumption parameters for resource-constrained nodes."""
    initial_energy_j: float = Field(default=1000.0, gt=0, description="Initial battery capacity in Joules")
    max_energy_j: float = Field(default=1000.0, gt=0, description="Maximum battery capacity in Joules")
    idle_power_w: float = Field(default=0.015, ge=0.0, description="Power consumed in idle/sleep state in Watts (J/s)")
    tx_energy_per_packet_j: float = Field(default=0.008, ge=0.0, description="Energy per transmitted packet in Joules")
    rx_energy_per_packet_j: float = Field(default=0.004, ge=0.0, description="Energy per received/forwarded packet in Joules")
    cpu_baseline_pct: float = Field(default=5.0, ge=0.0, le=100.0, description="Baseline OS/RTOS CPU utilization percentage")
    cpu_per_packet_pct: float = Field(default=1.8, ge=0.0, description="CPU percentage consumed per processed packet/s")
    memory_baseline_pct: float = Field(default=15.0, ge=0.0, le=100.0, description="Baseline RTOS memory utilization percentage")
    memory_per_packet_pct: float = Field(default=0.8, ge=0.0, description="Memory percentage increase per queued packet")


class MasterConfig(BaseModel):
    """Root configuration holding all sub-system configurations."""
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    topology: TopologyConfig = Field(default_factory=TopologyConfig)
    traffic: TrafficConfig = Field(default_factory=TrafficConfig)
    channel: ChannelConfig = Field(default_factory=ChannelConfig)
    resources: ResourceConfig = Field(default_factory=ResourceConfig)


def load_config_from_yaml(config_path: Path | str) -> MasterConfig:
    """
    Loads and parses a YAML configuration file into MasterConfig.
    Falls back to default values if fields are omitted.
    """
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    return MasterConfig(**raw_data)

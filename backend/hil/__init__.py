"""
Hardware-in-the-Loop (HIL) & Real-World IoT Dataset Trace Replay Module.
Provides realistic trace adapters for TON_IoT, CIC-IoT2023, and BoT-IoT,
alongside physical gateway serial/MQTT bridges for ESP32-S3 and Raspberry Pi 4B.
"""

from .trace_adapter import (
    TraceDatasetType,
    RealWorldTraceGenerator,
    RealWorldTraceBatch,
)
from .hardware_bridge import (
    HardwarePlatform,
    HardwareGatewaySpec,
    SerialPacketFramer,
    HILActuationTranslator,
    HardwareGatewayBridge,
)
from .engine import HILExecutionEngine

__all__ = [
    "TraceDatasetType",
    "RealWorldTraceGenerator",
    "RealWorldTraceBatch",
    "HardwarePlatform",
    "HardwareGatewaySpec",
    "SerialPacketFramer",
    "HILActuationTranslator",
    "HardwareGatewayBridge",
    "HILExecutionEngine",
]

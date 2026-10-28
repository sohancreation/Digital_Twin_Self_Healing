"""
Hardware-in-the-Loop (HIL) Physical Gateway Interface & Binary Packet Bridge.
Models hardware execution constraints and binary telemetry serial/MQTT framing
for ESP32-S3 and Raspberry Pi 4B edge gateway deployments.
"""

from enum import Enum
import struct
import time
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.simulation.telemetry import TelemetryRecord


class HardwarePlatform(str, Enum):
    ESP32_S3 = "ESP32-S3"
    RASPBERRY_PI_4B = "Raspberry Pi 4B"


class HardwareGatewaySpec(BaseModel):
    """Specifications and computational bounds for physical edge gateways."""
    platform: HardwarePlatform
    cpu_cores: int
    clock_mhz: float
    sram_kb: float
    baud_rate: int = 115200
    network_transport: str = "UART/LoRa"
    base_os: str = "FreeRTOS"

    def calculate_serialization_delay_ms(self, payload_bytes: int) -> float:
        """Computes UART physical transmission time: 1 start + 8 data + 1 stop bit = 10 bits/byte."""
        bits = payload_bytes * 10
        delay_sec = bits / float(self.baud_rate)
        return float(delay_sec * 1000.0)


# Standard profile instances
ESP32_S3_SPEC = HardwareGatewaySpec(
    platform=HardwarePlatform.ESP32_S3,
    cpu_cores=2,
    clock_mhz=240.0,
    sram_kb=512.0,
    baud_rate=115200,
    network_transport="UART/Serial",
    base_os="FreeRTOS",
)

RASPBERRY_PI_4B_SPEC = HardwareGatewaySpec(
    platform=HardwarePlatform.RASPBERRY_PI_4B,
    cpu_cores=4,
    clock_mhz=1500.0,
    sram_kb=4194304.0,  # 4GB
    baud_rate=921600,
    network_transport="MQTT/Ethernet",
    base_os="Linux (Debian)",
)


class SerialPacketFramer:
    """
    Encodes and decodes telemetry frames into binary packets with CRC16 validation.
    Frame Format:
      Header: 2 bytes (0xAA, 0x55)
      Payload Length: 2 bytes uint16
      Node ID: 2 bytes uint16
      Timestamp: 4 bytes float32
      Packet Rate: 2 bytes uint16 (scaled by 10)
      Forwarding Rate: 2 bytes uint16 (scaled by 10)
      Packet Loss: 2 bytes uint16 (scaled by 1000)
      Latency: 2 bytes uint16 (scaled by 10)
      RSSI: 1 byte int8
      Energy: 1 byte uint8 (scaled 0-100)
      CPU: 1 byte uint8 (scaled 0-100)
      Memory: 1 byte uint8 (scaled 0-100)
      CRC16: 2 bytes uint16 (CCITT)
      Total Frame Size = 2 + 2 + 2 + 4 + 2 + 2 + 2 + 2 + 1 + 1 + 1 + 1 + 2 = 24 bytes
    """

    SYNC_HEADER = bytes([0xAA, 0x55])

    @staticmethod
    def compute_crc16(data: bytes) -> int:
        """Computes CCITT CRC16 checksum."""
        crc = 0xFFFF
        for byte in data:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc

    @classmethod
    def encode_record(cls, record: TelemetryRecord) -> bytes:
        """Serializes TelemetryRecord into a compact 24-byte binary frame."""
        payload = struct.pack(
            "!HfHHHHbBBB",
            int(record.node_id),
            float(record.timestamp),
            int(min(65535, round(record.packet_rate * 10))),
            int(min(65535, round(record.forwarding_rate * 10))),
            int(min(1000, round(record.packet_loss * 1000))),
            int(min(65535, round(record.latency * 10))),
            int(np_clip(round(record.rssi), -128, 0)),
            int(np_clip(round(record.energy), 0, 100)),
            int(np_clip(round(record.cpu), 0, 100)),
            int(np_clip(round(record.memory), 0, 100)),
        )

        length = len(payload)
        header_and_len = cls.SYNC_HEADER + struct.pack("!H", length)
        body = header_and_len + payload
        crc = cls.compute_crc16(body)
        frame = body + struct.pack("!H", crc)
        return frame

    @classmethod
    def decode_frame(cls, frame_bytes: bytes) -> Optional[TelemetryRecord]:
        """Decodes binary frame back into TelemetryRecord, validating header and CRC."""
        if len(frame_bytes) != 24:
            return None

        header = frame_bytes[:2]
        if header != cls.SYNC_HEADER:
            return None

        body_without_crc = frame_bytes[:-2]
        expected_crc = struct.unpack("!H", frame_bytes[-2:])[0]
        actual_crc = cls.compute_crc16(body_without_crc)

        if expected_crc != actual_crc:
            return None  # Corrupted packet in transit

        length = struct.unpack("!H", frame_bytes[2:4])[0]
        payload = frame_bytes[4:4 + length]

        (
            nid,
            t,
            pkt_rate_raw,
            fwd_rate_raw,
            loss_raw,
            lat_raw,
            rssi_raw,
            energy_raw,
            cpu_raw,
            mem_raw,
        ) = struct.unpack("!HfHHHHbBBB", payload)

        return TelemetryRecord(
            timestamp=float(round(t, 2)),
            node_id=nid,
            packet_rate=float(pkt_rate_raw / 10.0),
            forwarding_rate=float(fwd_rate_raw / 10.0),
            packet_loss=float(loss_raw / 1000.0),
            latency=float(lat_raw / 10.0),
            rssi=float(rssi_raw),
            energy=float(energy_raw),
            cpu=float(cpu_raw),
            memory=float(mem_raw),
            neighbor_count=3,
            connection_state="CONNECTED" if loss_raw < 300 else "DEGRADED",
            routing_state="ROUTING" if fwd_rate_raw > 20 else "IDLE",
        )


def np_clip(val: float, low: float, high: float) -> float:
    return max(low, min(high, val))


class HILActuationCommand(BaseModel):
    """Low-level actuation command emitted to physical/emulated hardware."""
    command_id: str
    target_node_id: int
    action_type: str
    physical_instruction: str
    parameters: Dict[str, Any]
    dispatch_timestamp_ms: float
    execution_latency_ms: float
    success: bool = True


class HILActuationTranslator:
    """
    Translates Digital Twin recovery decisions into low-level network instructions.
    """

    @staticmethod
    def translate(action_type: str, target_node_id: int, params: Optional[Dict[str, Any]] = None) -> HILActuationCommand:
        t0 = time.perf_counter()
        params = params or {}
        ip_addr = f"10.0.0.{target_node_id + 1}"

        if action_type == "NODE_ISOLATION":
            # Physical eBPF / iptables quarantine
            instruction = f"iptables -A FORWARD -s {ip_addr} -j DROP; ip link set dev wlan{target_node_id} down"
            latency = 1.25  # ~1.25ms to update kernel table
        elif action_type == "DETOUR_BRIDGE":
            # Proactive multi-hop routing detour installation
            detour_via = params.get("detour_via", f"10.0.0.{(target_node_id + 2)}")
            instruction = f"ip route add 10.0.0.0/24 via {detour_via} metric 10; tc qdisc add dev wlan0 root fq"
            latency = 2.10  # Route table injection
        elif action_type == "RATE_LIMITING":
            rate = params.get("rate_pps", 5)
            instruction = f"tc qdisc add dev eth0 root tbf rate {rate*1000}bit burst 10k latency 50ms"
            latency = 0.85
        elif action_type == "NODE_REBOOT":
            instruction = f"ssh admin@{ip_addr} 'reboot -f'"
            latency = 15.0
        else:
            instruction = "noop"
            latency = 0.05

        elapsed_ms = (time.perf_counter() - t0) * 1000.0 + latency

        return HILActuationCommand(
            command_id=f"act_{int(time.time()*1000)}_{target_node_id}",
            target_node_id=target_node_id,
            action_type=action_type,
            physical_instruction=instruction,
            parameters=params,
            dispatch_timestamp_ms=float(time.time() * 1000.0),
            execution_latency_ms=round(elapsed_ms, 3),
            success=True,
        )


class HardwareGatewayBridge:
    """
    Manages physical or emulated edge gateway communications, tracking
    serial transmission delays, buffer occupancy, and actuation latency budgets.
    """

    def __init__(self, spec: HardwareGatewaySpec = ESP32_S3_SPEC):
        self.spec = spec
        self.packet_buffer: List[bytes] = []
        self.transmitted_count = 0
        self.corrupted_count = 0
        self.total_serial_delay_ms = 0.0

    def transmit_record(self, record: TelemetryRecord, simulate_corruption: bool = False) -> Tuple[TelemetryRecord, float]:
        """
        Encodes record, models physical serial/MQTT transmission delay,
        and reconstitutes received record.
        """
        frame = SerialPacketFramer.encode_record(record)
        delay_ms = self.spec.calculate_serialization_delay_ms(len(frame))
        self.total_serial_delay_ms += delay_ms

        if simulate_corruption:
            # Corrupt one byte
            corrupted = bytearray(frame)
            corrupted[10] ^= 0xFF
            frame = bytes(corrupted)

        decoded = SerialPacketFramer.decode_frame(frame)
        if decoded is not None:
            self.transmitted_count += 1
            return decoded, delay_ms
        else:
            self.corrupted_count += 1
            # Return fallback uncorrupted on error
            return record, delay_ms

    def dispatch_actuation(self, action_type: str, target_node_id: int, params: Optional[Dict[str, Any]] = None) -> HILActuationCommand:
        """Dispatches an actuation command through the physical gateway downlink."""
        cmd = HILActuationTranslator.translate(action_type, target_node_id, params)
        return cmd

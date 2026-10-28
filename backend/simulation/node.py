"""
Virtual IoT Node implementation for resource-constrained network simulation.
Enforces internal consistency, physical bounds, and energy/resource models.
"""

from typing import List, Tuple, Optional, Literal
from collections import deque
import numpy as np
from pydantic import BaseModel, Field

from .config import TrafficConfig, ChannelConfig, ResourceConfig
from .telemetry import TelemetryRecord


class IoTNode:
    """
    Virtual representation of a single resource-constrained IoT node.
    Simulates packet processing, radio transmission, buffer queues, energy depletion,
    and computational load under normal baseline conditions.
    """

    def __init__(
        self,
        node_id: int,
        position: Tuple[float, float],
        traffic_config: Optional[TrafficConfig] = None,
        channel_config: Optional[ChannelConfig] = None,
        resource_config: Optional[ResourceConfig] = None,
    ):
        self.node_id = node_id
        self.position = position

        # Config references
        self.traffic_cfg = traffic_config or TrafficConfig()
        self.channel_cfg = channel_config or ChannelConfig()
        self.resource_cfg = resource_config or ResourceConfig()

        # Topology and neighbor awareness
        self.neighbors: List[int] = []
        self.neighbor_distances: dict[int, float] = {}
        self.neighbor_rssi_map: dict[int, float] = {}

        # Internal state variables
        self.current_energy_j: float = self.resource_cfg.initial_energy_j
        self.max_energy_j: float = self.resource_cfg.max_energy_j
        self.packet_queue: deque = deque(maxlen=self.traffic_cfg.max_queue_size)

        # Dynamic metrics initialized to normal resting state
        self.packet_generation_rate: float = 0.0
        self.packet_forwarding_rate: float = 0.0
        self.packet_loss: float = 0.0
        self.latency: float = 0.0
        self.rssi: float = self.channel_cfg.ref_rssi_dbm
        self.cpu_utilization: float = self.resource_cfg.cpu_baseline_pct
        self.memory_utilization: float = self.resource_cfg.memory_baseline_pct
        self.connection_state: Literal["CONNECTED", "DEGRADED", "DISCONNECTED"] = "CONNECTED"
        self.routing_state: Literal["IDLE", "ROUTING", "CONGESTED"] = "IDLE"
        self.trust_score: float = 1.0
        self.threat_level: float = 0.0

        # Operational status
        self.is_alive: bool = True

    def set_neighbors(self, neighbors: List[int], neighbor_distances: dict[int, float]) -> None:
        """Configures the node's wireless neighborhood and neighbor distances."""
        self.neighbors = sorted(neighbors)
        self.neighbor_distances = neighbor_distances

    def calculate_rssi(self, distance_m: float, rng: np.random.Generator) -> float:
        """
        Calculates RSSI based on log-distance path loss model with shadow fading:
        RSSI(d) = RSSI_0 - 10 * eta * log10(d / d_0) + X_sigma
        """
        if distance_m <= 0:
            return self.channel_cfg.ref_rssi_dbm

        # Bound minimum distance to reference distance to prevent log(0)
        eff_dist = max(distance_m, self.channel_cfg.ref_distance_m)
        path_loss_db = 10.0 * self.channel_cfg.path_loss_exponent * np.log10(
            eff_dist / self.channel_cfg.ref_distance_m
        )
        shadowing_noise = rng.normal(0.0, self.channel_cfg.rssi_noise_std)
        raw_rssi = self.channel_cfg.ref_rssi_dbm - path_loss_db + shadowing_noise

        # Clamp within hardware physical bounds
        clamped_rssi = float(np.clip(raw_rssi, self.channel_cfg.min_rssi_dbm, self.channel_cfg.max_rssi_dbm))
        return clamped_rssi

    def step(
        self,
        timestamp: float,
        timestep: float,
        inbound_forward_packets: int,
        rng: np.random.Generator,
    ) -> TelemetryRecord:
        """
        Simulates node dynamics over one discrete timestep dt.
        Calculates packet generation, forwarding, queuing, CPU, memory, energy, and loss.
        Returns a validated TelemetryRecord.
        """
        if not self.is_alive or self.current_energy_j <= 0.0:
            # Node is dead / battery depleted
            self.is_alive = False
            self.current_energy_j = 0.0
            self.packet_generation_rate = 0.0
            self.packet_forwarding_rate = 0.0
            self.packet_loss = 1.0
            self.latency = 0.0
            self.rssi = self.channel_cfg.min_rssi_dbm
            self.cpu_utilization = 0.0
            self.memory_utilization = 0.0
            self.connection_state = "DISCONNECTED"
            self.routing_state = "IDLE"

            return self._create_telemetry_record(timestamp)

        # 1. Packet Generation (Gaussian baseline normal traffic)
        base_rate = max(
            0.0,
            rng.normal(self.traffic_cfg.base_packet_rate, self.traffic_cfg.packet_rate_std)
        )
        packets_generated = int(np.round(base_rate * timestep))
        self.packet_generation_rate = float(packets_generated / timestep)

        # 2. Forwarding Traffic
        packets_to_forward = inbound_forward_packets
        rate_cap = getattr(self, "_rate_limit_token_rate", None)
        if rate_cap is not None:
            packets_to_forward = min(packets_to_forward, int(np.round(rate_cap * timestep)))
        self.packet_forwarding_rate = float(packets_to_forward / timestep)

        total_new_packets = packets_generated + packets_to_forward

        # 3. Queue Buffer and Congestion Packet Loss
        available_queue_space = self.traffic_cfg.max_queue_size - len(self.packet_queue)
        packets_dropped_buffer = max(0, total_new_packets - available_queue_space)
        packets_enqueued = total_new_packets - packets_dropped_buffer

        for _ in range(packets_enqueued):
            self.packet_queue.append(timestamp)

        # Process / Transmit packets from queue
        packets_serviced = min(len(self.packet_queue), packets_enqueued)
        for _ in range(packets_serviced):
            self.packet_queue.popleft()

        # 4. Wireless Channel RSSI Calculation
        if self.neighbors and self.neighbor_distances:
            rssi_samples = [
                self.calculate_rssi(dist, rng)
                for dist in self.neighbor_distances.values()
            ]
            self.rssi = float(np.mean(rssi_samples))
        else:
            self.rssi = self.channel_cfg.min_rssi_dbm

        # 5. Channel-Induced Packet Loss based on RSSI
        # Sigmoid probability of error when RSSI approaches sensitivity threshold (-120 dBm to -95 dBm)
        rssi_loss_prob = float(1.0 / (1.0 + np.exp(0.2 * (self.rssi - (-100.0)))))
        # Combined loss ratio (buffer overflow + channel error)
        if total_new_packets > 0:
            buffer_loss_ratio = packets_dropped_buffer / total_new_packets
            total_loss_ratio = buffer_loss_ratio + (1.0 - buffer_loss_ratio) * rssi_loss_prob
            self.packet_loss = float(np.clip(total_loss_ratio, 0.0, 1.0))
        else:
            self.packet_loss = float(np.clip(rssi_loss_prob, 0.0, 1.0))

        # 6. Latency Calculation (Propagation + Transmission + Queuing Delay)
        # Baseline propagation + radio tx: ~15-25ms
        base_tx_delay_ms = 18.0 + rng.normal(0.0, 2.0)
        # Queuing delay: proportional to queue depth and traffic volume
        queue_delay_ms = (len(self.packet_queue) / max(1, self.traffic_cfg.max_queue_size)) * 40.0
        traffic_delay_ms = (total_new_packets / max(1.0, self.traffic_cfg.base_packet_rate * 2)) * 12.0
        raw_latency = max(1.0, base_tx_delay_ms + queue_delay_ms + traffic_delay_ms)
        self.latency = float(np.clip(raw_latency, 0.0, 5000.0))

        # 7. CPU Utilization (Baseline + processing per packet + minor jitter)
        total_traffic_rate = self.packet_generation_rate + self.packet_forwarding_rate
        cpu_load = (
            self.resource_cfg.cpu_baseline_pct
            + (total_traffic_rate * self.resource_cfg.cpu_per_packet_pct)
            + rng.normal(0.0, 0.5)
        )
        self.cpu_utilization = float(np.clip(cpu_load, 0.0, 100.0))

        # 8. Memory Utilization (Baseline + queue occupancy percentage)
        queue_occupancy_ratio = len(self.packet_queue) / self.traffic_cfg.max_queue_size
        mem_load = (
            self.resource_cfg.memory_baseline_pct
            + (queue_occupancy_ratio * (100.0 - self.resource_cfg.memory_baseline_pct) * 0.5)
            + (self.resource_cfg.memory_per_packet_pct * total_new_packets)
            + rng.normal(0.0, 0.3)
        )
        self.memory_utilization = float(np.clip(mem_load, 0.0, 100.0))

        # 9. Energy Depletion Model
        # E_step = P_idle * dt + E_tx * N_tx + E_rx * N_rx
        energy_draw = (
            (self.resource_cfg.idle_power_w * timestep)
            + (self.resource_cfg.tx_energy_per_packet_j * packets_generated)
            + (self.resource_cfg.rx_energy_per_packet_j * packets_to_forward)
        )
        self.current_energy_j = max(0.0, self.current_energy_j - energy_draw)
        if self.current_energy_j <= 0.0:
            self.is_alive = False
            self.current_energy_j = 0.0
            self.packet_generation_rate = 0.0
            self.packet_forwarding_rate = 0.0
            self.packet_loss = 1.0
            self.latency = 0.0
            self.cpu_utilization = 0.0
            self.memory_utilization = 0.0
            self.connection_state = "DISCONNECTED"
            self.routing_state = "IDLE"
            return self._create_telemetry_record(timestamp)

        # 10. State Assignment
        if self.packet_loss > 0.4 or self.rssi < -110.0:
            self.connection_state = "DEGRADED"
            self.routing_state = "CONGESTED" if len(self.packet_queue) > (self.traffic_cfg.max_queue_size * 0.7) else "ROUTING"
        else:
            self.connection_state = "CONNECTED"
            self.routing_state = "ROUTING" if self.packet_forwarding_rate > 0 else "IDLE"

        return self._create_telemetry_record(timestamp)

    @property
    def energy_percentage(self) -> float:
        """Returns remaining energy as a bounded percentage [0.0, 100.0]."""
        if self.max_energy_j <= 0.0:
            return 0.0
        pct = (self.current_energy_j / self.max_energy_j) * 100.0
        return float(np.clip(pct, 0.0, 100.0))

    def _create_telemetry_record(self, timestamp: float) -> TelemetryRecord:
        """Constructs and validates a TelemetryRecord for this node."""
        return TelemetryRecord(
            timestamp=float(timestamp),
            node_id=int(self.node_id),
            packet_rate=float(np.clip(self.packet_generation_rate, 0.0, 10000.0)),
            forwarding_rate=float(np.clip(self.packet_forwarding_rate, 0.0, 10000.0)),
            packet_loss=float(np.clip(self.packet_loss, 0.0, 1.0)),
            latency=float(max(0.0, self.latency)),
            rssi=float(np.clip(self.rssi, self.channel_cfg.min_rssi_dbm, self.channel_cfg.max_rssi_dbm)),
            energy=float(self.energy_percentage),
            cpu=float(np.clip(self.cpu_utilization, 0.0, 100.0)),
            memory=float(np.clip(self.memory_utilization, 0.0, 100.0)),
            neighbor_count=int(len(self.neighbors)),
            connection_state=self.connection_state,
            routing_state=self.routing_state,
            threat_level=float(self.threat_level),
            trust_score=float(self.trust_score),
        )

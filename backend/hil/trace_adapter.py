"""
Calibrated Synthetic IoT Trace Adapter & Dataset Engine for Hardware-in-the-Loop Benchmarks.
Generates telemetry sequences statistically calibrated to match published empirical
distributions from IoT security benchmarks (TON_IoT, CIC-IoT2023, BoT-IoT),
adapting them into the Digital Twin's invariant TelemetryRecord schema.

SCIENTIFIC INTEGRITY NOTE:
These traces represent calibrated synthetic attack profiles whose statistical
moments (packet arrival rates, loss distributions, transit drop ratios, latency)
are modeled after published characterizations of TON_IoT, CIC-IoT2023, and BoT-IoT.
They are synthetic profile approximations for HIL timing and pipeline replay,
not direct raw packet ingestion of the original PCAP/CSV benchmark files.
"""

from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Iterator
import os
import numpy as np
from pydantic import BaseModel, Field

from backend.simulation.telemetry import TelemetryRecord


class TraceDatasetType(str, Enum):
    TON_IOT = "TON_IoT"
    CIC_IOT2023 = "CIC_IoT2023"
    BOT_IOT = "BoT_IoT"


class AttackCategory(str, Enum):
    BENIGN = "benign"
    DOS_FLOOD = "dos_flood"
    SELECTIVE_DROP = "selective_drop"
    SCANNING_RECON = "scanning_recon"
    BACKDOOR_INJECTION = "backdoor_injection"


class RealWorldTraceEvent(BaseModel):
    """Encapsulates a single telemetry event with dataset profile provenance."""
    dataset: TraceDatasetType
    raw_category: AttackCategory
    is_attack: bool
    record: TelemetryRecord
    raw_packet_count: int
    raw_byte_count: int
    inter_arrival_jitter_ms: float


class RealWorldTraceBatch(BaseModel):
    """Batch of trace events for a given time epoch across multiple nodes."""
    timestamp: float
    events: List[RealWorldTraceEvent]
    active_node_ids: List[int]

    def get_records_dict(self) -> Dict[int, TelemetryRecord]:
        return {e.record.node_id: e.record for e in self.events}


class RealWorldTraceGenerator:
    """
    Generates and replays calibrated synthetic IoT security benchmark traces based on
    published statistical distributions from TON_IoT, CIC-IoT2023, and BoT-IoT datasets.
    Each dataset profile has distinct, empirically motivated parameters.
    """

    def __init__(self, dataset: TraceDatasetType = TraceDatasetType.TON_IOT, seed: int = 42):
        self.dataset = dataset
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def _sample_benign_metrics(self, node_id: int, t: float) -> Tuple[Dict[str, Any], int, int, float]:
        """Samples baseline benign telemetry calibrated to dataset profile."""
        if self.dataset == TraceDatasetType.BOT_IOT:
            # BoT-IoT: High-speed industrial backbone telemetry
            pkt_rate = float(np.clip(self.rng.normal(2.5, 0.4), 1.2, 4.0))
            fwd_rate = float(np.clip(self.rng.normal(1.5, 0.3), 0.5, 2.8))
            pkt_loss = float(np.clip(self.rng.exponential(0.003), 0.0, 0.02))
            latency = float(np.clip(self.rng.normal(6.5, 1.2), 2.5, 15.0))
            rssi = float(np.clip(self.rng.normal(-60.0, 2.5), -75.0, -45.0))
            cpu = float(np.clip(self.rng.normal(9.0, 2.0), 4.0, 20.0))
            memory = float(np.clip(self.rng.normal(32.0, 2.0), 20.0, 42.0))
        elif self.dataset == TraceDatasetType.CIC_IOT2023:
            # CIC-IoT2023: Smart home heterogeneous device mix
            pkt_rate = float(np.clip(self.rng.normal(2.2, 0.35), 1.0, 3.8))
            fwd_rate = float(np.clip(self.rng.normal(1.1, 0.25), 0.3, 2.2))
            pkt_loss = float(np.clip(self.rng.exponential(0.008), 0.0, 0.04))
            latency = float(np.clip(self.rng.normal(9.5, 2.0), 3.5, 22.0))
            rssi = float(np.clip(self.rng.normal(-65.0, 3.5), -82.0, -48.0))
            cpu = float(np.clip(self.rng.normal(14.0, 3.0), 6.0, 28.0))
            memory = float(np.clip(self.rng.normal(42.0, 2.5), 28.0, 52.0))
        else:
            # TON_IoT: Industrial IoT telemetry (Modbus/MQTT/BACnet)
            pkt_rate = float(np.clip(self.rng.normal(1.8, 0.25), 0.9, 3.0))
            fwd_rate = float(np.clip(self.rng.normal(1.0, 0.20), 0.3, 2.0))
            pkt_loss = float(np.clip(self.rng.exponential(0.005), 0.0, 0.025))
            latency = float(np.clip(self.rng.normal(8.0, 1.5), 3.0, 18.0))
            rssi = float(np.clip(self.rng.normal(-62.0, 3.0), -80.0, -45.0))
            cpu = float(np.clip(self.rng.normal(11.0, 2.2), 5.0, 22.0))
            memory = float(np.clip(self.rng.normal(36.0, 2.0), 24.0, 45.0))

        energy = float(np.clip(100.0 - 0.01 * t, 20.0, 100.0))
        jitter = float(np.clip(self.rng.normal(1.5, 0.4), 0.2, 4.0))

        raw_pkts = int(np.round(pkt_rate))
        raw_bytes = int(raw_pkts * 128)

        metrics = {
            "packet_rate": pkt_rate,
            "forwarding_rate": fwd_rate,
            "packet_loss": pkt_loss,
            "latency": latency,
            "rssi": rssi,
            "energy": energy,
            "cpu": cpu,
            "memory": memory,
            "connection_state": "CONNECTED",
            "routing_state": "ROUTING",
        }
        return metrics, raw_pkts, raw_bytes, jitter

    def _sample_dos_metrics(self, node_id: int, t: float) -> Tuple[Dict[str, Any], int, int, float]:
        """Samples volumetric DoS / DDoS flooding telemetry calibrated per dataset."""
        if self.dataset == TraceDatasetType.BOT_IOT:
            # BoT-IoT: Massive volumetric multi-vector DDoS (higher flood intensity)
            pkt_rate = float(np.clip(self.rng.normal(42.0, 4.5), 30.0, 60.0))
            fwd_rate = float(np.clip(self.rng.normal(1.2, 0.3), 0.3, 2.5))
            pkt_loss = float(np.clip(self.rng.normal(0.65, 0.08), 0.45, 0.95))
            latency = float(np.clip(self.rng.normal(140.0, 25.0), 75.0, 350.0))
            rssi = float(np.clip(self.rng.normal(-72.0, 5.0), -92.0, -55.0))
            cpu = float(np.clip(self.rng.normal(97.0, 1.8), 90.0, 99.8))
            memory = float(np.clip(self.rng.normal(88.0, 3.5), 75.0, 98.0))
            jitter = float(np.clip(self.rng.normal(28.0, 6.0), 10.0, 65.0))
        elif self.dataset == TraceDatasetType.CIC_IOT2023:
            # CIC-IoT2023: SYN/UDP flood profile
            pkt_rate = float(np.clip(self.rng.normal(28.0, 3.5), 20.0, 40.0))
            fwd_rate = float(np.clip(self.rng.normal(1.8, 0.4), 0.6, 3.2))
            pkt_loss = float(np.clip(self.rng.normal(0.52, 0.07), 0.35, 0.88))
            latency = float(np.clip(self.rng.normal(95.0, 18.0), 50.0, 260.0))
            rssi = float(np.clip(self.rng.normal(-69.0, 4.0), -88.0, -50.0))
            cpu = float(np.clip(self.rng.normal(91.0, 2.5), 80.0, 98.0))
            memory = float(np.clip(self.rng.normal(80.0, 4.0), 62.0, 94.0))
            jitter = float(np.clip(self.rng.normal(20.0, 4.5), 7.0, 48.0))
        else:
            # TON_IoT: Application-layer HTTP/Modbus buffer flood
            pkt_rate = float(np.clip(self.rng.normal(20.0, 2.5), 15.0, 30.0))
            fwd_rate = float(np.clip(self.rng.normal(1.4, 0.35), 0.5, 2.8))
            pkt_loss = float(np.clip(self.rng.normal(0.42, 0.06), 0.28, 0.75))
            latency = float(np.clip(self.rng.normal(70.0, 12.0), 40.0, 180.0))
            rssi = float(np.clip(self.rng.normal(-67.0, 3.5), -85.0, -50.0))
            cpu = float(np.clip(self.rng.normal(86.0, 3.0), 75.0, 96.0))
            memory = float(np.clip(self.rng.normal(76.0, 3.5), 60.0, 90.0))
            jitter = float(np.clip(self.rng.normal(15.0, 3.5), 5.0, 38.0))

        energy = float(np.clip(100.0 - 0.08 * t, 10.0, 100.0))
        raw_pkts = int(np.round(pkt_rate))
        raw_bytes = int(raw_pkts * 512)

        metrics = {
            "packet_rate": pkt_rate,
            "forwarding_rate": fwd_rate,
            "packet_loss": pkt_loss,
            "latency": latency,
            "rssi": rssi,
            "energy": energy,
            "cpu": cpu,
            "memory": memory,
            "connection_state": "DEGRADED",
            "routing_state": "CONGESTED",
        }
        return metrics, raw_pkts, raw_bytes, jitter

    def _sample_selective_drop_metrics(self, node_id: int, t: float) -> Tuple[Dict[str, Any], int, int, float]:
        """Samples gray-hole / selective forwarding packet drop attack."""
        if self.dataset == TraceDatasetType.CIC_IOT2023:
            # CIC-IoT2023: Classic stealthy selective drop
            pkt_rate = float(np.clip(self.rng.normal(2.1, 0.3), 1.0, 3.5))
            fwd_rate = float(np.clip(self.rng.normal(0.06, 0.03), 0.0, 0.15))
            pkt_loss = float(np.clip(self.rng.normal(0.75, 0.05), 0.60, 0.94))
            latency = float(np.clip(self.rng.normal(26.0, 5.0), 12.0, 60.0))
            cpu = float(np.clip(self.rng.normal(15.0, 2.5), 8.0, 25.0))
        else:
            pkt_rate = float(np.clip(self.rng.normal(1.9, 0.25), 1.0, 3.2))
            fwd_rate = float(np.clip(self.rng.normal(0.10, 0.04), 0.0, 0.25))
            pkt_loss = float(np.clip(self.rng.normal(0.68, 0.06), 0.50, 0.88))
            latency = float(np.clip(self.rng.normal(22.0, 4.0), 10.0, 50.0))
            cpu = float(np.clip(self.rng.normal(17.0, 3.0), 9.0, 30.0))

        rssi = float(np.clip(self.rng.normal(-64.0, 3.0), -80.0, -48.0))
        energy = float(np.clip(100.0 - 0.015 * t, 20.0, 100.0))
        memory = float(np.clip(self.rng.normal(40.0, 3.0), 28.0, 52.0))
        jitter = float(np.clip(self.rng.normal(5.0, 1.5), 1.5, 14.0))

        raw_pkts = int(np.round(pkt_rate))
        raw_bytes = int(raw_pkts * 128)

        metrics = {
            "packet_rate": pkt_rate,
            "forwarding_rate": fwd_rate,
            "packet_loss": pkt_loss,
            "latency": latency,
            "rssi": rssi,
            "energy": energy,
            "cpu": cpu,
            "memory": memory,
            "connection_state": "DEGRADED",
            "routing_state": "ROUTING",
        }
        return metrics, raw_pkts, raw_bytes, jitter

    def _sample_scanning_metrics(self, node_id: int, t: float) -> Tuple[Dict[str, Any], int, int, float]:
        """Samples reconnaissance / network port scanning probe trace."""
        if self.dataset == TraceDatasetType.TON_IOT:
            # TON_IoT: Nmap scanning with OS detection probes
            pkt_rate = float(np.clip(self.rng.normal(10.5, 1.8), 6.0, 18.0))
            fwd_rate = float(np.clip(self.rng.normal(2.5, 0.5), 0.8, 5.0))
            pkt_loss = float(np.clip(self.rng.normal(0.14, 0.03), 0.06, 0.28))
            latency = float(np.clip(self.rng.normal(28.0, 5.0), 12.0, 55.0))
            cpu = float(np.clip(self.rng.normal(46.0, 4.5), 30.0, 65.0))
            memory = float(np.clip(self.rng.normal(52.0, 3.5), 38.0, 68.0))
        else:
            pkt_rate = float(np.clip(self.rng.normal(14.0, 2.2), 8.0, 22.0))
            fwd_rate = float(np.clip(self.rng.normal(3.5, 0.7), 1.2, 7.0))
            pkt_loss = float(np.clip(self.rng.normal(0.20, 0.05), 0.09, 0.35))
            latency = float(np.clip(self.rng.normal(35.0, 7.0), 18.0, 72.0))
            cpu = float(np.clip(self.rng.normal(56.0, 5.5), 38.0, 75.0))
            memory = float(np.clip(self.rng.normal(60.0, 4.5), 45.0, 78.0))

        rssi = float(np.clip(self.rng.normal(-65.0, 3.5), -82.0, -48.0))
        energy = float(np.clip(100.0 - 0.04 * t, 15.0, 100.0))
        jitter = float(np.clip(self.rng.normal(9.0, 2.5), 3.0, 22.0))

        raw_pkts = int(np.round(pkt_rate))
        raw_bytes = int(raw_pkts * 96)

        metrics = {
            "packet_rate": pkt_rate,
            "forwarding_rate": fwd_rate,
            "packet_loss": pkt_loss,
            "latency": latency,
            "rssi": rssi,
            "energy": energy,
            "cpu": cpu,
            "memory": memory,
            "connection_state": "CONNECTED",
            "routing_state": "ROUTING",
        }
        return metrics, raw_pkts, raw_bytes, jitter

    def generate_trace_sequence(
        self,
        num_nodes: int = 24,
        duration_s: float = 60.0,
        attack_node_ids: Optional[List[int]] = None,
        attack_category: AttackCategory = AttackCategory.DOS_FLOOD,
        attack_start_s: float = 10.0,
        attack_end_s: float = 45.0,
    ) -> List[RealWorldTraceBatch]:
        """
        Generates a chronological sequence of trace batches across all nodes.
        """
        if attack_node_ids is None:
            attack_node_ids = [2, 8]  # Strategic bridge default

        batches = []
        timesteps = int(duration_s)

        for step in range(timesteps):
            t = float(step)
            is_attack_epoch = (attack_start_s <= t < attack_end_s)
            events = []

            for nid in range(num_nodes):
                is_node_attacking = is_attack_epoch and (nid in attack_node_ids)

                if is_node_attacking:
                    cat = attack_category
                    if cat == AttackCategory.DOS_FLOOD:
                        m, pkts, b, jit = self._sample_dos_metrics(nid, t)
                    elif cat == AttackCategory.SELECTIVE_DROP:
                        m, pkts, b, jit = self._sample_selective_drop_metrics(nid, t)
                    elif cat == AttackCategory.SCANNING_RECON:
                        m, pkts, b, jit = self._sample_scanning_metrics(nid, t)
                    else:
                        m, pkts, b, jit = self._sample_dos_metrics(nid, t)
                    is_atk = True
                else:
                    cat = AttackCategory.BENIGN
                    m, pkts, b, jit = self._sample_benign_metrics(nid, t)
                    is_atk = False

                rec = TelemetryRecord(
                    timestamp=t,
                    node_id=nid,
                    packet_rate=m["packet_rate"],
                    forwarding_rate=m["forwarding_rate"],
                    packet_loss=m["packet_loss"],
                    latency=m["latency"],
                    rssi=m["rssi"],
                    energy=m["energy"],
                    cpu=m["cpu"],
                    memory=m["memory"],
                    neighbor_count=max(1, int(self.rng.integers(2, 6))),
                    connection_state=m["connection_state"],
                    routing_state=m["routing_state"],
                    threat_level=1.0 if is_atk else 0.0,
                    trust_score=0.2 if is_atk else 0.95,
                )

                events.append(RealWorldTraceEvent(
                    dataset=self.dataset,
                    raw_category=cat,
                    is_attack=is_atk,
                    record=rec,
                    raw_packet_count=pkts,
                    raw_byte_count=b,
                    inter_arrival_jitter_ms=jit,
                ))

            batches.append(RealWorldTraceBatch(
                timestamp=t,
                events=events,
                active_node_ids=list(range(num_nodes)),
            ))

        return batches

    @classmethod
    def load_from_csv(cls, csv_path: str, dataset_type: TraceDatasetType) -> Optional[List[TelemetryRecord]]:
        """
        Optional loader for real benchmark CSV files if present on filesystem.
        """
        if not os.path.exists(csv_path):
            return None
        import pandas as pd
        df = pd.read_csv(csv_path)
        records = []
        for idx, row in df.iterrows():
            rec = TelemetryRecord(
                timestamp=float(row.get("timestamp", idx)),
                node_id=int(row.get("node_id", 1)),
                packet_rate=float(row.get("packet_rate", 2.0)),
                forwarding_rate=float(row.get("forwarding_rate", 1.0)),
                packet_loss=float(row.get("packet_loss", 0.01)),
                latency=float(row.get("latency", 10.0)),
                rssi=float(row.get("rssi", -60.0)),
                energy=float(row.get("energy", 100.0)),
                cpu=float(row.get("cpu", 10.0)),
                memory=float(row.get("memory", 30.0)),
                neighbor_count=int(row.get("neighbor_count", 3)),
            )
            records.append(rec)
        return records

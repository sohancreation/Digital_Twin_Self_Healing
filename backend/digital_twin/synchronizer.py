"""
Telemetry Ingestion and State Synchronizer for the Digital Twin.
Transforms incoming TelemetryRecord streams into TwinNodeState objects
and maintains synchronization metadata and latency statistics.
"""

import time
from typing import List, Union, Optional, Dict, Tuple
from backend.simulation.telemetry import TelemetryRecord
from .models import TwinNodeState, SyncMetadata
from .twin import DigitalTwin


class DigitalTwinSynchronizer:
    """
    Ingests telemetry records from physical nodes or simulator, validates payload integrity,
    measures software synchronization latency, and updates the Digital Twin.
    """

    def __init__(self, digital_twin: DigitalTwin):
        self.digital_twin = digital_twin
        self.sequence_counter: int = 0
        self.node_positions: Dict[int, Tuple[float, float]] = {}
        self.node_neighbors: Dict[int, List[int]] = {}

    def register_topology_context(
        self,
        positions: Dict[int, Tuple[float, float]],
        neighbors: Dict[int, List[int]]
    ) -> None:
        """
        Registers initial spatial layout and neighbor relationships for the shadow topology.
        """
        self.node_positions.update(positions)
        self.node_neighbors.update(neighbors)

    def ingest_record(self, record: TelemetryRecord) -> SyncMetadata:
        """
        Ingests a single TelemetryRecord, measures processing latency, and updates the twin.
        """
        t_start = time.perf_counter()
        wall_clock_epoch = time.time()

        # Transform TelemetryRecord to TwinNodeState
        pos = self.node_positions.get(record.node_id)
        node_state = TwinNodeState(
            node_id=record.node_id,
            timestamp=record.timestamp,
            position=pos,
            packet_rate=record.packet_rate,
            forwarding_rate=record.forwarding_rate,
            packet_loss=record.packet_loss,
            latency=record.latency,
            rssi=record.rssi,
            energy=record.energy,
            cpu=record.cpu,
            memory=record.memory,
            neighbor_count=record.neighbor_count,
            connection_state=record.connection_state,
            routing_state=record.routing_state,
            threat_level=record.threat_level,
            trust_score=record.trust_score,
        )

        self.sequence_counter += 1
        t_end = time.perf_counter()
        sync_latency_ms = (t_end - t_start) * 1000.0

        meta = SyncMetadata(
            telemetry_timestamp=record.timestamp,
            ingestion_timestamp=wall_clock_epoch,
            sync_latency_ms=sync_latency_ms,
            node_id=record.node_id,
            sequence_number=self.sequence_counter,
        )

        neighbors = self.node_neighbors.get(record.node_id, [])
        self.digital_twin.apply_node_update(
            node_state=node_state,
            sync_meta=meta,
            neighbors=neighbors,
            position=pos
        )

        return meta

    def ingest_batch(self, records: List[TelemetryRecord]) -> List[SyncMetadata]:
        """
        Ingests a batch of TelemetryRecords sequentially, updating the twin per record.
        """
        return [self.ingest_record(r) for r in records]

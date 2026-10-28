"""
Historical state management for the Digital Twin.
Maintains bounded, time-windowed chronological telemetry and derived states.
"""

from typing import Dict, List, Optional, Tuple, Any
from collections import deque
from .models import TwinNodeState, NetworkTwinState, SyncMetadata


class HistoryManager:
    """
    Manages historical buffers of node states, network-level states, and sync metadata.
    Enforces configurable time-window retention bounds suitable for resource-constrained systems.
    """

    def __init__(self, history_window_seconds: float = 60.0):
        self.history_window_seconds = max(1.0, float(history_window_seconds))
        self.node_history: Dict[int, deque[TwinNodeState]] = {}
        self.network_history: deque[NetworkTwinState] = deque()
        self.sync_metadata_history: deque[SyncMetadata] = deque()

    def add_node_record(self, record: TwinNodeState) -> None:
        """Appends a node state record to its history deque and prunes expired entries."""
        node_id = record.node_id
        if node_id not in self.node_history:
            self.node_history[node_id] = deque()

        self.node_history[node_id].append(record)
        self._prune_node_history(node_id, record.timestamp)

    def add_network_record(self, record: NetworkTwinState) -> None:
        """Appends a network-level state record and prunes expired entries."""
        self.network_history.append(record)
        cutoff = record.timestamp - self.history_window_seconds
        while self.network_history and self.network_history[0].timestamp < cutoff:
            self.network_history.popleft()

    def add_sync_metadata(self, meta: SyncMetadata) -> None:
        """Appends synchronization metadata record."""
        self.sync_metadata_history.append(meta)
        cutoff = meta.telemetry_timestamp - self.history_window_seconds
        while self.sync_metadata_history and self.sync_metadata_history[0].telemetry_timestamp < cutoff:
            self.sync_metadata_history.popleft()

    def _prune_node_history(self, node_id: int, current_timestamp: float) -> None:
        """Evicts node records older than (current_timestamp - history_window_seconds)."""
        cutoff = current_timestamp - self.history_window_seconds
        dq = self.node_history[node_id]
        while dq and dq[0].timestamp < cutoff:
            dq.popleft()

    def get_node_history(self, node_id: int, window_seconds: Optional[float] = None) -> List[TwinNodeState]:
        """
        Retrieves historical node states for node_id within specified or default window.
        Returns empty list if node has no history.
        """
        if node_id not in self.node_history:
            return []

        records = list(self.node_history[node_id])
        if not records:
            return []

        effective_window = window_seconds if window_seconds is not None else self.history_window_seconds
        latest_ts = records[-1].timestamp
        cutoff = latest_ts - effective_window

        return [r for r in records if r.timestamp >= cutoff]

    def get_recent_state(self, node_id: int, seconds: float) -> List[TwinNodeState]:
        """Convenience method to query the last `seconds` of state for a node."""
        return self.get_node_history(node_id, window_seconds=seconds)

    def get_metric_history(
        self,
        node_id: int,
        metric: str,
        window_seconds: Optional[float] = None
    ) -> List[Tuple[float, Any]]:
        """
        Extracts a time series of (timestamp, metric_value) for a specific node metric.
        Raises AttributeError if metric is not a valid field of TwinNodeState.
        """
        if metric not in TwinNodeState.model_fields:
            raise AttributeError(f"TwinNodeState has no attribute '{metric}'")

        records = self.get_node_history(node_id, window_seconds)
        return [(r.timestamp, getattr(r, metric)) for r in records]

    def get_network_history(
        self,
        metric: str,
        window_seconds: Optional[float] = None
    ) -> List[Tuple[float, Any]]:
        """
        Extracts a time series of (timestamp, metric_value) for network-level metrics.
        Raises AttributeError if metric is not a valid field of NetworkTwinState.
        """
        if metric not in NetworkTwinState.model_fields:
            raise AttributeError(f"NetworkTwinState has no attribute '{metric}'")

        records = list(self.network_history)
        if not records:
            return []

        effective_window = window_seconds if window_seconds is not None else self.history_window_seconds
        latest_ts = records[-1].timestamp
        cutoff = latest_ts - effective_window

        filtered = [r for r in records if r.timestamp >= cutoff]
        return [(r.timestamp, getattr(r, metric)) for r in filtered]

    def clear(self) -> None:
        """Clears all historical buffers."""
        self.node_history.clear()
        self.network_history.clear()
        self.sync_metadata_history.clear()

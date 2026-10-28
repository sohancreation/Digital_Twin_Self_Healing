"""
Digital Twin Core Engine.
Maintains synchronized virtual state, historical buffers, topology shadow,
and descriptive health assessments of the IoT network.
"""

from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import networkx as nx

from .models import (
    TwinNodeState,
    NetworkTwinState,
    NetworkHealthSummary,
    LinkState,
    SyncMetadata,
)
from .history import HistoryManager
from .topology_model import NetworkTopologyModel
from .health import calculate_network_health


class DigitalTwin:
    """
    State Synchronizer and Shadow Model representing the IoT network in virtual space.
    Serves as the foundation for telemetry ingestion, historical query answering,
    topology tracking, and health metrics.
    """

    def __init__(self, history_window_seconds: float = 60.0):
        self.history_window_seconds = history_window_seconds
        self.node_states: Dict[int, TwinNodeState] = {}
        self.topology_model = NetworkTopologyModel()
        self.history_manager = HistoryManager(history_window_seconds=history_window_seconds)

        self.latest_timestamp: float = 0.0
        self.current_network_state: Optional[NetworkTwinState] = None
        self.current_health: Optional[NetworkHealthSummary] = None

        # Synchronization performance tracking
        self.sync_latencies: List[float] = []
        self.total_records_ingested: int = 0

    def apply_node_update(
        self,
        node_state: TwinNodeState,
        sync_meta: SyncMetadata,
        neighbors: Optional[List[int]] = None,
        position: Optional[Tuple[float, float]] = None,
    ) -> None:
        """
        Applies a validated node state update to the Digital Twin.
        Updates local shadow node, history, topology, and recalculates macro network state.
        """
        node_id = node_state.node_id
        self.node_states[node_id] = node_state
        self.latest_timestamp = max(self.latest_timestamp, node_state.timestamp)

        # Update history
        self.history_manager.add_node_record(node_state)
        self.history_manager.add_sync_metadata(sync_meta)

        # Update topology shadow
        active_neighbors = neighbors if neighbors is not None else []
        self.topology_model.sync_node_topology(
            node_id=node_id,
            neighbors=active_neighbors,
            position=position or node_state.position,
            rssi=node_state.rssi,
            latency=node_state.latency,
            packet_loss=node_state.packet_loss,
            timestamp=node_state.timestamp,
            is_connected=(node_state.connection_state != "DISCONNECTED" and node_state.energy > 0)
        )

        # Track sync performance
        self.sync_latencies.append(sync_meta.sync_latency_ms)
        self.total_records_ingested += 1

        # Refresh aggregated network-level state and health
        self._refresh_network_state()

    def _refresh_network_state(self) -> None:
        """Recalculates aggregated network state and descriptive health summary."""
        if not self.node_states:
            return

        total_nodes = len(self.node_states)
        connected_count = sum(1 for n in self.node_states.values() if n.connection_state == "CONNECTED")
        active_count = sum(1 for n in self.node_states.values() if n.energy > 0 and n.connection_state != "DISCONNECTED")

        avg_loss = float(np.mean([n.packet_loss for n in self.node_states.values()]))
        avg_latency = float(np.mean([n.latency for n in self.node_states.values()]))
        avg_rssi = float(np.mean([n.rssi for n in self.node_states.values()]))
        avg_cpu = float(np.mean([n.cpu for n in self.node_states.values()]))
        avg_memory = float(np.mean([n.memory for n in self.node_states.values()]))
        total_energy = float(np.sum([n.energy for n in self.node_states.values()]))
        availability = float(connected_count / max(1, total_nodes))

        self.current_network_state = NetworkTwinState(
            timestamp=self.latest_timestamp,
            node_count=total_nodes,
            active_node_count=active_count,
            connected_node_count=connected_count,
            average_packet_loss=avg_loss,
            average_latency=avg_latency,
            average_rssi=avg_rssi,
            average_cpu=avg_cpu,
            average_memory=avg_memory,
            total_energy=total_energy,
            network_availability=availability,
        )

        self.history_manager.add_network_record(self.current_network_state)
        self.current_health = calculate_network_health(self.node_states, self.latest_timestamp)

    def get_node_state(self, node_id: int) -> TwinNodeState:
        """
        Retrieves the latest state of a specific node.
        Raises KeyError if the node is not registered.
        """
        if node_id not in self.node_states:
            raise KeyError(f"Node {node_id} not found in Digital Twin state.")
        return self.node_states[node_id]

    def get_all_nodes(self) -> Dict[int, TwinNodeState]:
        """Returns a copy of all current node states in the Digital Twin."""
        return self.node_states.copy()

    def get_node_history(self, node_id: int, window_seconds: Optional[float] = None) -> List[TwinNodeState]:
        """Queries historical states for a node within the configured time window."""
        if node_id not in self.node_states:
            raise KeyError(f"Node {node_id} not found in Digital Twin state.")
        return self.history_manager.get_node_history(node_id, window_seconds)

    def get_network_state(self) -> NetworkTwinState:
        """Returns the current macro network state."""
        if self.current_network_state is None:
            self._refresh_network_state()
        if self.current_network_state is None:
            raise ValueError("No network state available (no nodes synchronized).")
        return self.current_network_state

    def get_network_topology(self) -> nx.Graph:
        """Returns the NetworkX topology graph of the Digital Twin shadow."""
        return self.topology_model.get_topology()

    def get_link_state(self, source: int, target: int) -> Optional[LinkState]:
        """Returns link condition between source and target, or None if no link exists."""
        return self.topology_model.get_link_state(source, target)

    def get_network_health(self) -> NetworkHealthSummary:
        """Returns the current descriptive network health summary."""
        if self.current_health is None:
            self._refresh_network_state()
        return self.current_health or calculate_network_health(self.node_states, self.latest_timestamp)

    def get_synchronization_metrics(self) -> Dict[str, float]:
        """Returns summary statistics of software synchronization ingestion latency (ms)."""
        if not self.sync_latencies:
            return {
                "records_ingested": 0.0,
                "min_sync_latency_ms": 0.0,
                "mean_sync_latency_ms": 0.0,
                "max_sync_latency_ms": 0.0,
                "std_sync_latency_ms": 0.0,
            }

        arr = np.array(self.sync_latencies)
        return {
            "records_ingested": float(len(arr)),
            "min_sync_latency_ms": float(np.min(arr)),
            "mean_sync_latency_ms": float(np.mean(arr)),
            "max_sync_latency_ms": float(np.max(arr)),
            "std_sync_latency_ms": float(np.std(arr)),
        }

    def update_node_trust(self, node_id: int, trust_score: float, threat_level: float) -> None:
        """Updates the trust score and threat level of a shadow node."""
        if node_id in self.node_states:
            self.node_states[node_id] = self.node_states[node_id].model_copy(update={
                "trust_score": float(np.clip(trust_score, 0.0, 1.0)),
                "threat_level": float(np.clip(threat_level, 0.0, 1.0))
            })

    def reset(self) -> None:
        """Resets all Digital Twin states, history, and topology shadow."""
        self.node_states.clear()
        self.topology_model.clear()
        self.history_manager.clear()
        self.latest_timestamp = 0.0
        self.current_network_state = None
        self.current_health = None
        self.sync_latencies.clear()
        self.total_records_ingested = 0

    def simulate_recovery_candidate(
        self,
        candidate: Any,
        horizon_s: float = 30.0,
        attack_context: Optional[Dict[int, str]] = None,
    ) -> Any:
        """
        In-silico forward simulation of candidate mitigation strategy s_k in a cloned virtual sandbox.
        """
        from ..recovery.sandbox import RecoverySandbox
        sandbox = RecoverySandbox()
        return sandbox.simulate_candidate(
            digital_twin=self,
            candidate=candidate,
            horizon_s=horizon_s,
            attack_context=attack_context,
        )

    def evaluate_strategy_pool(
        self,
        strategy_pool: Any,
        horizon_s: float = 30.0,
        weights: Optional[Any] = None,
        constraints: Optional[Any] = None,
        attack_context: Optional[Dict[int, str]] = None,
    ) -> Any:
        """
        Evaluates a complete strategy pool using multi-objective optimization and returns optimal decision s*.
        """
        from ..recovery.optimization import MultiObjectiveRecoveryOptimizer
        optimizer = MultiObjectiveRecoveryOptimizer(weights=weights, constraints=constraints)
        return optimizer.evaluate_strategy_pool(
            digital_twin=self,
            strategy_pool=strategy_pool,
            horizon_s=horizon_s,
            attack_context=attack_context,
        )


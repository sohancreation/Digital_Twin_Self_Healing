"""
Topology shadow model for the Digital Twin.
Maintains graph representation, spatial layout, and link condition estimates.
"""

from typing import Dict, List, Optional, Tuple, Set
import networkx as nx
from .models import LinkState


class NetworkTopologyModel:
    """
    Virtual topology shadow of the IoT network within the Digital Twin.
    Synchronizes nodes, links, and wireless adjacency from telemetry streams.
    """

    def __init__(self):
        self.graph: nx.Graph = nx.Graph()
        self.positions: Dict[int, Tuple[float, float]] = {}
        self.links: Dict[Tuple[int, int], LinkState] = {}

    def sync_node_topology(
        self,
        node_id: int,
        neighbors: List[int],
        position: Optional[Tuple[float, float]] = None,
        rssi: float = -80.0,
        latency: float = 20.0,
        packet_loss: float = 0.0,
        timestamp: float = 0.0,
        is_connected: bool = True
    ) -> None:
        """
        Synchronizes a node's topological presence, position, and 1-hop links.
        """
        if not self.graph.has_node(node_id):
            self.graph.add_node(node_id)

        if position is not None:
            self.positions[node_id] = position

        if not is_connected:
            # Remove incident edges if node is disconnected
            edges_to_remove = list(self.graph.edges(node_id))
            for u, v in edges_to_remove:
                self.graph.remove_edge(u, v)
                self.links.pop((u, v), None)
                self.links.pop((v, u), None)
            return

        # Synchronize edges based on reported neighbors
        reported_neighbors = set(neighbors)
        current_neighbors = set(self.graph.neighbors(node_id)) if self.graph.has_node(node_id) else set()

        # Add new neighbor edges
        for neighbor_id in reported_neighbors:
            if not self.graph.has_node(neighbor_id):
                self.graph.add_node(neighbor_id)
            if not self.graph.has_edge(node_id, neighbor_id):
                self.graph.add_edge(node_id, neighbor_id)

            # Store directional link states
            link_state = LinkState(
                source_node=node_id,
                target_node=neighbor_id,
                estimated_rssi=rssi,
                estimated_latency=latency,
                estimated_loss=packet_loss,
                active=True,
                last_updated=timestamp
            )
            self.links[(node_id, neighbor_id)] = link_state

    def get_topology(self) -> nx.Graph:
        """Returns the internal NetworkX graph representing active topology."""
        return self.graph.copy()

    def get_link_state(self, source: int, target: int) -> Optional[LinkState]:
        """Returns link state between source and target, or None if no link exists."""
        return self.links.get((source, target))

    def get_all_link_states(self) -> List[LinkState]:
        """Returns list of all active directional link states."""
        return list(self.links.values())

    def get_neighbors(self, node_id: int) -> List[int]:
        """Returns sorted list of active 1-hop neighbors for a node."""
        if not self.graph.has_node(node_id):
            return []
        return sorted(list(self.graph.neighbors(node_id)))

    def get_connected_components(self) -> List[Set[int]]:
        """Returns connected components as sets of node IDs."""
        if self.graph.number_of_nodes() == 0:
            return []
        return [set(c) for c in nx.connected_components(self.graph)]

    def is_connected(self) -> bool:
        """Returns True if the active topology graph is fully connected."""
        if self.graph.number_of_nodes() <= 1:
            return True
        return nx.is_connected(self.graph)

    def clear(self) -> None:
        """Resets the topology shadow model."""
        self.graph.clear()
        self.positions.clear()
        self.links.clear()

"""
Topological Criticality Engine for IoT Networks.
Analyzes the Digital Twin graph shadow to compute structural importance factors.
Bridge nodes and high-betweenness routing bottlenecks have elevated criticality factors C_i,
directly magnifying their systemic risk R_i(t) if compromised or degraded.
"""

from typing import Dict, Optional, Any
import numpy as np
import networkx as nx


class TopologicalCriticalityEngine:
    """
    Computes node topological criticality factors C_i in [0.1, 1.0] from the Digital Twin topology shadow.
    """

    def __init__(
        self,
        betweenness_weight: float = 0.60,
        degree_weight: float = 0.40,
        articulation_boost: float = 0.25
    ):
        self.betweenness_weight = betweenness_weight
        self.degree_weight = degree_weight
        self.articulation_boost = articulation_boost
        self._last_topology_hash: Optional[int] = None
        self._cached_criticalities: Dict[int, float] = {}

    def compute_criticalities(self, graph: nx.Graph) -> Dict[int, float]:
        """
        Computes normalized criticality factors C_i for all nodes in the graph.
        """
        if graph.number_of_nodes() == 0:
            return {}

        nodes = list(graph.nodes())
        n = len(nodes)

        topo_signature = (n, graph.number_of_edges(), tuple(sorted(nodes)), tuple(sorted(graph.edges())))
        topo_hash = hash(topo_signature)
        if topo_hash == self._last_topology_hash and self._cached_criticalities:
            return self._cached_criticalities

        if n <= 2:
            crits = {node: 0.50 for node in nodes}
            self._last_topology_hash = topo_hash
            self._cached_criticalities = crits
            return crits

        # 1. Betweenness Centrality (traffic transit importance)
        try:
            betweenness = nx.betweenness_centrality(graph, normalized=True)
        except Exception:
            betweenness = {node: 0.0 for node in nodes}

        # 2. Degree Centrality (local neighborhood density)
        try:
            degree_cent = nx.degree_centrality(graph)
        except Exception:
            degree_cent = {node: 0.0 for node in nodes}

        # 3. Articulation Points / Cut Vertices (bridge detection)
        # Removing a cut vertex disconnects the network
        articulation_set = set()
        try:
            articulation_set = set(nx.articulation_points(graph))
        except Exception:
            pass

        criticalities = {}
        for node in nodes:
            b_val = betweenness.get(node, 0.0)
            d_val = degree_cent.get(node, 0.0)

            # Combined base centrality
            base = (self.betweenness_weight * b_val) + (self.degree_weight * d_val)

            # Boost if node is an articulation point (network bridge)
            if node in articulation_set:
                base += self.articulation_boost

            # Normalize to [0.10, 1.00] range
            # Base of 0.10 guarantees every node has non-zero operational criticality
            c_factor = float(np.clip(0.10 + (base * 0.90), 0.10, 1.00))
            criticalities[node] = round(c_factor, 4)

        self._cached_criticalities = criticalities
        self._last_topology_hash = topo_hash
        return criticalities

    def get_node_criticality(self, node_id: int, graph: Optional[nx.Graph] = None) -> float:
        """
        Returns criticality factor C_i for a given node.
        If graph is provided, recomputes; otherwise uses cached values or default 0.50.
        """
        if graph is not None:
            crits = self.compute_criticalities(graph)
            return crits.get(node_id, 0.50)

        return self._cached_criticalities.get(node_id, 0.50)

    def compute_cascading_failure_hazard(
        self,
        node_id: int,
        graph: nx.Graph,
        node_states: Optional[Dict[int, Any]] = None
    ) -> float:
        """
        Evaluates the downstream load transfer / congestion hazard imposed on immediate
        neighbors if node_id is abruptly severed or fails.
        Returns hazard in [0.05, 1.0].
        """
        if node_id not in graph or graph.number_of_nodes() <= 1:
            return 0.10

        neighbors = list(graph.neighbors(node_id))
        if not neighbors:
            return 0.05

        deg = len(neighbors)
        # If node has only 1 neighbor, that neighbor absorbs all redirected traffic
        isolation_factor = 1.0 if deg == 1 else (1.0 / deg)

        # Evaluate neighbor resource load (CPU, energy depletion) if node_states provided
        neighbor_pressure = 0.50
        if node_states:
            pressures = []
            for n in neighbors:
                st = node_states.get(n)
                if st is not None:
                    # Higher CPU (>70%) and lower battery (<30%) increases vulnerability to cascade
                    cpu_load = getattr(st, "cpu", 30.0) / 100.0
                    batt_deplete = 1.0 - (getattr(st, "energy", 80.0) / 100.0)
                    pressures.append(0.60 * cpu_load + 0.40 * batt_deplete)
            if pressures:
                neighbor_pressure = float(np.mean(pressures))

        hazard = (0.50 * isolation_factor) + (0.50 * neighbor_pressure)
        return float(np.clip(hazard, 0.05, 1.00))


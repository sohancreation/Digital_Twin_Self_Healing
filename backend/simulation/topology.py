"""
Network topology generation and graph management for IoT simulations.
Supports grid, random, mesh, ring, and star topologies with NetworkX.
"""

from typing import Dict, List, Tuple, Optional
import math
import numpy as np
import networkx as nx

from .config import TopologyConfig


class NetworkTopology:
    """
    Manages the graph structure, geometric layout, and multi-hop routing paths
    of the simulated IoT network.
    """

    def __init__(self, num_nodes: int, config: Optional[TopologyConfig] = None, rng: Optional[np.random.Generator] = None):
        self.num_nodes = num_nodes
        self.config = config or TopologyConfig()
        self.rng = rng if rng is not None else np.random.default_rng(42)

        self.graph: nx.Graph = nx.Graph()
        self.positions: Dict[int, Tuple[float, float]] = {}
        self.distance_matrix: np.ndarray = np.zeros((num_nodes, num_nodes))
        self.neighbor_map: Dict[int, List[int]] = {}
        self.neighbor_distances: Dict[int, Dict[int, float]] = {}

        self._build_topology()

    def _build_topology(self) -> None:
        """Constructs graph, generates positions, and connects edges based on topology type."""
        self.graph.clear()
        for node_id in range(self.num_nodes):
            self.graph.add_node(node_id)

        topo_type = self.config.type.lower()
        if topo_type == "grid":
            self._build_grid_layout()
        elif topo_type == "random":
            self._build_random_layout()
        elif topo_type == "mesh":
            self._build_mesh_layout()
        elif topo_type == "ring":
            self._build_ring_layout()
        elif topo_type == "star":
            self._build_star_layout()
        elif topo_type in ("scale_free", "barabasi_albert"):
            self._build_scale_free_layout()
        else:
            raise ValueError(f"Unsupported topology type: {self.config.type}")

        self._compute_distances_and_neighbors()

    def _build_grid_layout(self) -> None:
        """Arranges nodes in a regular 2D grid."""
        rows = self.config.grid_rows or int(math.ceil(math.sqrt(self.num_nodes)))
        cols = self.config.grid_cols or int(math.ceil(self.num_nodes / rows))

        # Adjust rows/cols to fit num_nodes if not specified
        if rows * cols < self.num_nodes:
            cols = int(math.ceil(self.num_nodes / rows))

        dx = self.config.area_width / max(1, cols - 1) if cols > 1 else self.config.area_width / 2
        dy = self.config.area_height / max(1, rows - 1) if rows > 1 else self.config.area_height / 2

        for i in range(self.num_nodes):
            r = i // cols
            c = i % cols
            x = c * dx if cols > 1 else self.config.area_width / 2
            y = r * dy if rows > 1 else self.config.area_height / 2
            self.positions[i] = (float(x), float(y))

        # Connect adjacent grid neighbors (horizontal & vertical)
        for i in range(self.num_nodes):
            r = i // cols
            c = i % cols
            # Horizontal right
            if c + 1 < cols and (i + 1) < self.num_nodes:
                self.graph.add_edge(i, i + 1)
            # Vertical down
            if r + 1 < rows and (i + cols) < self.num_nodes:
                self.graph.add_edge(i, i + cols)

    def _build_random_layout(self) -> None:
        """Distributes nodes uniformly at random within the simulation area."""
        for i in range(self.num_nodes):
            x = float(self.rng.uniform(0, self.config.area_width))
            y = float(self.rng.uniform(0, self.config.area_height))
            self.positions[i] = (x, y)

        # Connect nodes within communication range
        for i in range(self.num_nodes):
            for j in range(i + 1, self.num_nodes):
                dist = math.hypot(self.positions[i][0] - self.positions[j][0],
                                  self.positions[i][1] - self.positions[j][1])
                if dist <= self.config.comm_range:
                    self.graph.add_edge(i, j)

        # If disconnected components exist, connect each component's closest pair to ensure global connectivity
        if not nx.is_connected(self.graph) and self.num_nodes > 1:
            components = list(nx.connected_components(self.graph))
            for k in range(len(components) - 1):
                comp_a = list(components[k])
                comp_b = list(components[k + 1])
                # Find min distance between comp_a and comp_b
                min_dist = float('inf')
                best_pair = (comp_a[0], comp_b[0])
                for u in comp_a:
                    for v in comp_b:
                        d = math.hypot(self.positions[u][0] - self.positions[v][0],
                                       self.positions[u][1] - self.positions[v][1])
                        if d < min_dist:
                            min_dist = d
                            best_pair = (u, v)
                self.graph.add_edge(best_pair[0], best_pair[1])

    def _build_mesh_layout(self) -> None:
        """Arranges nodes in a circle and creates a dense mesh connectivity."""
        radius = min(self.config.area_width, self.config.area_height) * 0.4
        center_x = self.config.area_width / 2.0
        center_y = self.config.area_height / 2.0

        for i in range(self.num_nodes):
            angle = 2.0 * math.pi * i / self.num_nodes
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            self.positions[i] = (x, y)

        # Connect all pairs within communication range (or full mesh if range is large)
        for i in range(self.num_nodes):
            for j in range(i + 1, self.num_nodes):
                dist = math.hypot(self.positions[i][0] - self.positions[j][0],
                                  self.positions[i][1] - self.positions[j][1])
                if dist <= self.config.comm_range or self.config.comm_range >= (radius * 2):
                    self.graph.add_edge(i, j)

    def _build_ring_layout(self) -> None:
        """Arranges nodes in a ring with adjacent neighbors connected."""
        radius = min(self.config.area_width, self.config.area_height) * 0.4
        center_x = self.config.area_width / 2.0
        center_y = self.config.area_height / 2.0

        for i in range(self.num_nodes):
            angle = 2.0 * math.pi * i / self.num_nodes
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            self.positions[i] = (x, y)

        for i in range(self.num_nodes):
            nxt = (i + 1) % self.num_nodes
            self.graph.add_edge(i, nxt)

    def _build_star_layout(self) -> None:
        """Arranges node 0 as central hub and nodes 1..N-1 on circumference connected to hub."""
        center_x = self.config.area_width / 2.0
        center_y = self.config.area_height / 2.0
        self.positions[0] = (center_x, center_y)

        radius = min(self.config.area_width, self.config.area_height) * 0.4
        num_leaves = self.num_nodes - 1

        for i in range(1, self.num_nodes):
            angle = 2.0 * math.pi * (i - 1) / max(1, num_leaves)
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            self.positions[i] = (x, y)
            self.graph.add_edge(0, i)

    def _build_scale_free_layout(self) -> None:
        """Generates a Barabási-Albert scale-free network topology with power-law degree distribution."""
        m = max(1, min(2, self.num_nodes - 1))
        seed_val = int(self.rng.integers(0, 100000))
        ba_graph = nx.barabasi_albert_graph(self.num_nodes, m=m, seed=seed_val)
        self.graph = ba_graph
        pos = nx.spring_layout(ba_graph, seed=seed_val)
        for i in range(self.num_nodes):
            x = float((pos[i][0] + 1.0) * 0.5 * self.config.area_width)
            y = float((pos[i][1] + 1.0) * 0.5 * self.config.area_height)
            self.positions[i] = (x, y)

    def _compute_distances_and_neighbors(self) -> None:
        """Computes pairwise Euclidean distances and populates symmetric neighbor caches."""
        self.distance_matrix = np.zeros((self.num_nodes, self.num_nodes))
        self.neighbor_map = {i: [] for i in range(self.num_nodes)}
        self.neighbor_distances = {i: {} for i in range(self.num_nodes)}

        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                if i != j:
                    pos_i = self.positions[i]
                    pos_j = self.positions[j]
                    dist = float(math.hypot(pos_i[0] - pos_j[0], pos_i[1] - pos_j[1]))
                    self.distance_matrix[i, j] = dist
                else:
                    self.distance_matrix[i, j] = 0.0

        for u, v in self.graph.edges():
            self.neighbor_map[u].append(v)
            self.neighbor_map[v].append(u)
            dist = self.distance_matrix[u, v]
            self.neighbor_distances[u][v] = dist
            self.neighbor_distances[v][u] = dist

        for i in range(self.num_nodes):
            self.neighbor_map[i].sort()

    def get_shortest_path(self, source: int, target: int) -> Optional[List[int]]:
        """Returns shortest path sequence of node IDs between source and target, or None."""
        try:
            return nx.shortest_path(self.graph, source=source, target=target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_neighbors(self, node_id: int) -> List[int]:
        """Returns sorted list of 1-hop neighbor node IDs."""
        return self.neighbor_map.get(node_id, [])

    def get_neighbor_distances(self, node_id: int) -> Dict[int, float]:
        """Returns map of {neighbor_id: distance_in_meters}."""
        return self.neighbor_distances.get(node_id, {})

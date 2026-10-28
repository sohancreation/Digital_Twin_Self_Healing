"""
Unit tests for NetworkTopology generation, neighbor symmetry, and scalability.
"""

import pytest
import numpy as np
import networkx as nx
from backend.simulation.topology import NetworkTopology
from backend.simulation.config import TopologyConfig


@pytest.mark.parametrize("topo_type", ["grid", "random", "mesh", "ring", "star"])
@pytest.mark.parametrize("num_nodes", [6, 10, 20, 50, 100])
def test_topology_generation(topo_type, num_nodes):
    """Verify that all topology types generate the exact requested number of nodes and valid graphs."""
    cfg = TopologyConfig(type=topo_type, area_width=100.0, area_height=100.0, comm_range=60.0)
    rng = np.random.default_rng(42)
    topology = NetworkTopology(num_nodes=num_nodes, config=cfg, rng=rng)

    assert topology.num_nodes == num_nodes
    assert len(topology.positions) == num_nodes
    assert topology.graph.number_of_nodes() == num_nodes
    assert topology.distance_matrix.shape == (num_nodes, num_nodes)


def test_neighbor_consistency():
    """Verify neighbor symmetry: u in neighbors(v) <=> v in neighbors(u)."""
    for topo_type in ["grid", "random", "mesh", "ring", "star"]:
        cfg = TopologyConfig(type=topo_type)
        topology = NetworkTopology(num_nodes=6, config=cfg)

        for u in range(topology.num_nodes):
            neighbors_u = topology.get_neighbors(u)
            for v in neighbors_u:
                neighbors_v = topology.get_neighbors(v)
                assert u in neighbors_v, f"Asymmetric neighbor relation found between {u} and {v} in {topo_type}"
                # Check distance symmetry
                dist_uv = topology.get_neighbor_distances(u)[v]
                dist_vu = topology.get_neighbor_distances(v)[u]
                assert pytest.approx(dist_uv, rel=1e-5) == dist_vu


def test_distance_matrix_properties():
    """Verify distance matrix has 0 on diagonal, is symmetric, and non-negative."""
    cfg = TopologyConfig(type="grid")
    topology = NetworkTopology(num_nodes=6, config=cfg)
    matrix = topology.distance_matrix

    for i in range(6):
        assert matrix[i, i] == 0.0
        for j in range(6):
            assert matrix[i, j] >= 0.0
            assert pytest.approx(matrix[i, j], rel=1e-5) == matrix[j, i]


def test_shortest_path_routing():
    """Verify shortest path routing returns valid node paths on connected graph."""
    cfg = TopologyConfig(type="grid", grid_rows=2, grid_cols=3)
    topology = NetworkTopology(num_nodes=6, config=cfg)

    path = topology.get_shortest_path(0, 5)
    assert path is not None
    assert path[0] == 0
    assert path[-1] == 5
    # Verify each consecutive hop is an actual edge
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        assert topology.graph.has_edge(u, v)

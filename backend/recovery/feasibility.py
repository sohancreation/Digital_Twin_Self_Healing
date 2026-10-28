"""
Topological & Physical Feasibility Checker for Candidate Recovery Strategies.
Evaluates graph partition risks, alternate loop-free route existence, and energy constraints.
Prevents naive self-healing actions from partitioning or destabilizing benign subnets.
"""

from typing import Dict, List, Tuple, Optional, Set, Any
import networkx as nx
import numpy as np

from ..digital_twin.models import TwinNodeState


class FeasibilityChecker:
    """
    Validates graph-theoretic and physical constraints of candidate recovery actions.
    """

    def check_isolation_partition(
        self,
        graph: nx.Graph,
        target_node: int
    ) -> Tuple[bool, int, List[List[int]]]:
        """
        Evaluates whether isolating target_node partitions the remaining benign network.
        Returns:
            (is_partitioning: bool, num_components: int, component_node_lists: List[List[int]])
        """
        if target_node not in graph:
            return False, 1, [list(graph.nodes())]

        sub_g = graph.copy()
        sub_g.remove_node(target_node)

        if sub_g.number_of_nodes() <= 1:
            return False, sub_g.number_of_nodes(), [list(sub_g.nodes())]

        components = [list(c) for c in nx.connected_components(sub_g)]
        num_comps = len(components)
        is_partitioning = (num_comps > 1)

        return is_partitioning, num_comps, components

    def find_alternate_routes(
        self,
        graph: nx.Graph,
        target_node: int,
        flow_pairs: Optional[List[Tuple[int, int]]] = None
    ) -> Dict[Tuple[int, int], Optional[List[int]]]:
        """
        Finds loop-free shortest alternate paths bypassing target_node for each pair of neighbors or flows.
        """
        if target_node not in graph:
            return {}

        sub_g = graph.copy()
        sub_g.remove_node(target_node)

        # If no explicit flow pairs provided, test all pairs of immediate neighbors of target_node
        if flow_pairs is None:
            neighbors = list(graph.neighbors(target_node))
            flow_pairs = []
            for i in range(len(neighbors)):
                for j in range(i + 1, len(neighbors)):
                    flow_pairs.append((neighbors[i], neighbors[j]))

        alternate_routes: Dict[Tuple[int, int], Optional[List[int]]] = {}
        for src, dst in flow_pairs:
            if src in sub_g and dst in sub_g and nx.has_path(sub_g, src, dst):
                try:
                    path = nx.shortest_path(sub_g, source=src, target=dst)
                    alternate_routes[(src, dst)] = path
                except Exception:
                    alternate_routes[(src, dst)] = None
            else:
                alternate_routes[(src, dst)] = None

        return alternate_routes

    def check_power_boost_feasibility(
        self,
        node_states: Dict[int, TwinNodeState],
        candidate_nodes: List[int],
        min_energy_threshold: float = 15.0
    ) -> bool:
        """
        Verifies that nodes selected to increase transmission power have adequate battery reserves.
        """
        if not candidate_nodes:
            return False

        for nid in candidate_nodes:
            if nid not in node_states:
                return False
            state = node_states[nid]
            if state.energy < min_energy_threshold or state.connection_state == "DISCONNECTED":
                return False

        return True

    def evaluate_path_stretch(
        self,
        graph: nx.Graph,
        target_node: int,
        max_stretch_hops: int = 3
    ) -> Dict[Tuple[int, int], Dict[str, Any]]:
        """
        Calculates the hop-count stretch Delta_h = len(P_bypass) - len(P_orig) introduced
        when bypassing target_node. Flags excessive stretch violating real-time latency deadlines.
        """
        if target_node not in graph:
            return {}

        neighbors = list(graph.neighbors(target_node))
        sub_g = graph.copy()
        sub_g.remove_node(target_node)

        results = {}
        for i in range(len(neighbors)):
            for j in range(i + 1, len(neighbors)):
                src, dst = neighbors[i], neighbors[j]
                orig_hops = 2  # Through target_node (src -> target -> dst)

                if src in sub_g and dst in sub_g and nx.has_path(sub_g, src, dst):
                    bypass_path = nx.shortest_path(sub_g, source=src, target=dst)
                    bypass_hops = len(bypass_path) - 1
                    stretch = bypass_hops - orig_hops
                    is_excessive = (stretch > max_stretch_hops)
                    results[(src, dst)] = {
                        "bypass_path": bypass_path,
                        "original_hops": orig_hops,
                        "bypass_hops": bypass_hops,
                        "hop_stretch": stretch,
                        "is_excessive_stretch": is_excessive
                    }
                else:
                    results[(src, dst)] = {
                        "bypass_path": None,
                        "original_hops": orig_hops,
                        "bypass_hops": None,
                        "hop_stretch": None,
                        "is_excessive_stretch": True
                    }

        return results

    def check_neighbor_congestion(
        self,
        node_states: Dict[int, TwinNodeState],
        neighbor_nodes: List[int],
        max_cpu_threshold: float = 80.0
    ) -> bool:
        """
        Verifies that candidate alternate neighbors possess sufficient computing
        and buffer headroom to absorb rerouted traffic without queue saturation.
        """
        for nid in neighbor_nodes:
            if nid in node_states:
                st = node_states[nid]
                if st.cpu > max_cpu_threshold or st.packet_loss > 0.20:
                    return False
        return True


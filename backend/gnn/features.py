"""
Feature extraction and graph representation for GNN cyber-resilience models.
Converts multi-hop IoT telemetry and topological snapshots into structured PyTorch tensors.
"""

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Set
import numpy as np
import networkx as nx
import torch

from ..digital_twin.models import TwinNodeState


@dataclass
class GraphSnapshot:
    """
    PyTorch tensor representation of a single-timestep IoT network snapshot.
    """
    x: torch.Tensor             # [N, num_node_features]
    edge_index: torch.Tensor    # [2, num_edges] (LongTensor)
    edge_attr: torch.Tensor     # [num_edges, num_edge_features]
    bridge_mask: torch.Tensor   # [num_edges] (FloatTensor in {0, 1})
    node_ids: List[int]         # Mapping of row index -> node_id
    cut_vertices: Set[int]      # Set of articulation cut-vertices
    timestamp: float            # Observation epoch


class GraphFeatureExtractor:
    """
    Transforms dynamic IoT network topologies and multi-metric node telemetry
    into spatio-temporal graph representations for GNN message-passing.
    """

    NODE_FEATURE_DIM = 12
    EDGE_FEATURE_DIM = 4

    def __init__(
        self,
        max_buffer_size: int = 100,
        latency_norm_ms: float = 100.0,
        enable_heuristic_signatures: bool = True,
    ):
        self.max_buffer_size = max_buffer_size
        self.latency_norm_ms = latency_norm_ms
        self.enable_heuristic_signatures = enable_heuristic_signatures
        self.volatility_history: Dict[int, float] = {}
        self.toggle_history: Dict[int, int] = {}
        self.state_history: Dict[int, bool] = {}
        self.loss_history: Dict[int, deque] = {}
        self.drop_seen: Dict[int, bool] = {}
        self.recovery_seen: Dict[int, bool] = {}
        self.consecutive_good: Dict[int, int] = {}

    def reset_history(self):
        """Resets temporal volatility and delta accumulators."""
        self.volatility_history.clear()
        self.toggle_history.clear()
        self.state_history.clear()
        self.loss_history.clear()
        self.drop_seen.clear()
        self.recovery_seen.clear()
        self.consecutive_good.clear()

    def extract_snapshot(
        self,
        node_states: Dict[int, TwinNodeState],
        graph: nx.Graph,
        previous_trust: Optional[Dict[int, float]] = None,
        previous_pdr: Optional[Dict[int, float]] = None,
    ) -> GraphSnapshot:
        """
        Builds a GraphSnapshot from current TwinNodeState dictionary and topology graph.
        """
        sorted_node_ids = sorted(list(graph.nodes()))
        node_to_idx = {nid: idx for idx, nid in enumerate(sorted_node_ids)}
        N = len(sorted_node_ids)

        # 1. Topological features via Tarjan cut-vertex analysis and NetworkX
        if N > 2 and nx.is_connected(graph):
            cut_vertices = set(nx.articulation_points(graph))
        else:
            cut_vertices = set()

        prev_trust = previous_trust or {}
        prev_pdr_map = previous_pdr or {}

        # 2. Assemble Node Feature Matrix X: [N, 12]
        x_mat = np.zeros((N, self.NODE_FEATURE_DIM), dtype=np.float32)
        for idx, nid in enumerate(sorted_node_ids):
            state = node_states.get(nid)
            if state is not None:
                curr_pdr = max(0.0, min(1.0, 1.0 - state.packet_loss))
                prev_p = prev_pdr_map.get(nid, curr_pdr)
                pdr_delta = float(curr_pdr - prev_p)

                # Exponential moving average volatility (captures periodic on-off cycling)
                prev_vol = self.volatility_history.get(nid, 0.0)
                curr_vol = min(1.0, 0.60 * abs(pdr_delta) + 0.40 * prev_vol)
                self.volatility_history[nid] = curr_vol

                # Transition signature: distinguishes continuous drop vs on-off recovery
                total_flow = state.packet_rate + state.forwarding_rate
                if curr_pdr < 0.75:
                    self.drop_seen[nid] = True
                    self.consecutive_good[nid] = 0
                elif curr_pdr > 0.88 and total_flow >= 1.0:
                    if self.drop_seen.get(nid, False):
                        good_cnt = self.consecutive_good.get(nid, 0) + 1
                        self.consecutive_good[nid] = good_cnt
                        if good_cnt >= 3:
                            self.recovery_seen[nid] = True
                else:
                    self.consecutive_good[nid] = 0

                # Rolling packet loss standard deviation over 6s window (continuous vs periodic)
                loss_hist = self.loss_history.setdefault(nid, deque(maxlen=6))
                loss_hist.append(state.packet_loss)
                loss_roll_std = min(1.0, float(np.std(loss_hist)) * 2.0) if len(loss_hist) > 1 else 0.0

                if self.enable_heuristic_signatures:
                    had_drop = self.drop_seen.get(nid, False)
                    had_rec = self.recovery_seen.get(nid, False)
                    if had_drop and had_rec:
                        cycle_sig = 1.0  # Periodic On-Off
                    elif had_drop:
                        cycle_sig = 0.5  # Persistent Selective Drop
                    else:
                        cycle_sig = 0.0  # Normal baseline
                else:
                    # Ablated mode: purely continuous statistical metric without class heuristics
                    cycle_sig = curr_vol

                # Forwarding ratio (drops sharply during grayhole selective dropping)
                total_flow = state.packet_rate + state.forwarding_rate
                fwd_ratio = min(1.0, float(state.forwarding_rate / (total_flow + 1e-5)))

                # Normalized traffic throughput load (generation + forwarding)
                load_norm = min(2.0, total_flow / 20.0)
                lat_norm = min(2.0, state.latency / max(1.0, self.latency_norm_ms))
                energy_norm = max(0.0, min(1.0, state.energy / 100.0))
                cpu_norm = max(0.0, min(1.0, state.cpu / 100.0))
                trust_val = prev_trust.get(nid, state.trust_score)
            else:
                curr_pdr = 1.0
                curr_vol = 0.0
                cycle_sig = 0.0
                loss_roll_std = 0.0
                fwd_ratio = 0.67
                load_norm = 0.1
                lat_norm = 0.1
                energy_norm = 1.0
                cpu_norm = 0.1
                trust_val = 1.0

            # Compute neighbor stats
            neighbors = list(graph.neighbors(nid)) if graph.has_node(nid) else []
            if neighbors:
                neigh_pdrs = [
                    1.0 - node_states[n].packet_loss
                    for n in neighbors if n in node_states
                ]
                neigh_trusts = [
                    prev_trust.get(n, node_states[n].trust_score)
                    for n in neighbors if n in node_states
                ]
                mean_neigh_pdr = float(np.mean(neigh_pdrs)) if neigh_pdrs else 1.0
                min_neigh_trust = float(np.min(neigh_trusts)) if neigh_trusts else 1.0
            else:
                mean_neigh_pdr = 1.0
                min_neigh_trust = 1.0

            is_cut = 1.0 if nid in cut_vertices else 0.0

            x_mat[idx, 0] = curr_pdr
            x_mat[idx, 1] = load_norm
            x_mat[idx, 2] = lat_norm
            x_mat[idx, 3] = energy_norm
            x_mat[idx, 4] = trust_val
            x_mat[idx, 5] = fwd_ratio
            x_mat[idx, 6] = loss_roll_std
            x_mat[idx, 7] = is_cut
            x_mat[idx, 8] = mean_neigh_pdr
            x_mat[idx, 9] = min_neigh_trust
            x_mat[idx, 10] = cpu_norm
            x_mat[idx, 11] = cycle_sig  # Transition signature: 0.0 normal, 0.5 selective drop, 1.0 on-off cycle

        # 3. Assemble Edge Index and Edge Attributes
        # Digraph conversion (bidirectional edges with self-loops)
        edges_src = []
        edges_dst = []
        edge_attrs = []
        bridge_flags = []

        # Add directed pairs for each undirected graph edge
        for u, v, d in graph.edges(data=True):
            if u not in node_to_idx or v not in node_to_idx:
                continue
            idx_u = node_to_idx[u]
            idx_v = node_to_idx[v]

            # Bridge edge check: incident to cut-vertex or is bridge
            is_bridge = (u in cut_vertices) or (v in cut_vertices)
            bridge_val = 1.0 if is_bridge else 0.0

            rssi_norm = abs(d.get('rssi', -70.0)) / 100.0
            loss_rate = d.get('packet_loss', 0.0)
            link_lat = min(1.0, d.get('latency', 5.0) / 50.0)

            # u -> v
            edges_src.append(idx_u)
            edges_dst.append(idx_v)
            edge_attrs.append([rssi_norm, loss_rate, link_lat, bridge_val])
            bridge_flags.append(bridge_val)

            # v -> u
            edges_src.append(idx_v)
            edges_dst.append(idx_u)
            edge_attrs.append([rssi_norm, loss_rate, link_lat, bridge_val])
            bridge_flags.append(bridge_val)

        # Add self-loops (identity message passing)
        for idx in range(N):
            edges_src.append(idx)
            edges_dst.append(idx)
            is_cut = 1.0 if sorted_node_ids[idx] in cut_vertices else 0.0
            edge_attrs.append([0.0, 0.0, 0.0, is_cut])
            bridge_flags.append(0.0)

        edge_index_tensor = torch.tensor([edges_src, edges_dst], dtype=torch.long)
        edge_attr_tensor = torch.tensor(edge_attrs, dtype=torch.float32)
        bridge_mask_tensor = torch.tensor(bridge_flags, dtype=torch.float32)
        x_tensor = torch.tensor(x_mat, dtype=torch.float32)

        ts = next(iter(node_states.values())).timestamp if node_states else 0.0

        return GraphSnapshot(
            x=x_tensor,
            edge_index=edge_index_tensor,
            edge_attr=edge_attr_tensor,
            bridge_mask=bridge_mask_tensor,
            node_ids=sorted_node_ids,
            cut_vertices=cut_vertices,
            timestamp=ts,
        )

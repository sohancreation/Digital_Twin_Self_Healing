"""
Graph snapshot dataset management and batch collation.
Provides PyG-style block-diagonal batching using pure PyTorch tensors.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import torch
from torch.utils.data import Dataset

from .features import GraphSnapshot


@dataclass
class GraphSnapshotBatch:
    """
    Batched representation of multiple GraphSnapshot objects.
    Forms a single block-diagonal super-graph for efficient parallel GNN computation.
    """
    x: torch.Tensor             # [sum(N_i), in_features]
    edge_index: torch.Tensor    # [2, sum(E_i)]
    edge_attr: torch.Tensor     # [sum(E_i), edge_dim]
    bridge_mask: torch.Tensor   # [sum(E_i)]
    batch_index: torch.Tensor   # [sum(N_i)] indicating graph membership
    num_graphs: int
    node_counts: List[int]
    labels_attack: Optional[torch.Tensor] = None   # [sum(N_i)]
    labels_trust: Optional[torch.Tensor] = None    # [sum(N_i)]


class GraphSnapshotDataset(Dataset):
    """
    PyTorch Dataset containing labeled graph snapshots from IoT simulations.
    """

    def __init__(
        self,
        snapshots: List[GraphSnapshot],
        attack_labels: Optional[List[torch.Tensor]] = None,
        trust_labels: Optional[List[torch.Tensor]] = None,
        window_size: int = 1,
    ):
        self.snapshots = snapshots
        self.attack_labels = attack_labels
        self.trust_labels = trust_labels
        self.window_size = window_size

    def __len__(self) -> int:
        return max(0, len(self.snapshots) - self.window_size + 1)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        """
        Returns a single snapshot or a temporal sequence of W snapshots.
        """
        if self.window_size == 1:
            snap = self.snapshots[idx]
            sample = {
                "snapshot": snap,
                "label_attack": self.attack_labels[idx] if self.attack_labels else None,
                "label_trust": self.trust_labels[idx] if self.trust_labels else None,
            }
            return sample
        else:
            snaps = self.snapshots[idx : idx + self.window_size]
            sample = {
                "sequence": snaps,
                "label_attack": self.attack_labels[idx + self.window_size - 1] if self.attack_labels else None,
                "label_trust": self.trust_labels[idx + self.window_size - 1] if self.trust_labels else None,
            }
            return sample

    @staticmethod
    def collate_snapshots(batch_list: List[Dict[str, Any]]) -> GraphSnapshotBatch:
        """
        Collates a list of single-step snapshot items into a GraphSnapshotBatch.
        """
        x_list = []
        edge_index_list = []
        edge_attr_list = []
        bridge_mask_list = []
        batch_idx_list = []
        labels_att_list = []
        labels_tr_list = []
        node_counts = []

        node_offset = 0
        for graph_id, item in enumerate(batch_list):
            snap: GraphSnapshot = item["snapshot"]
            n_nodes = snap.x.size(0)
            node_counts.append(n_nodes)

            x_list.append(snap.x)
            # Offset edge index
            shifted_edge_index = snap.edge_index + node_offset
            edge_index_list.append(shifted_edge_index)
            edge_attr_list.append(snap.edge_attr)
            bridge_mask_list.append(snap.bridge_mask)

            batch_idx_list.append(torch.full((n_nodes,), graph_id, dtype=torch.long))

            if item["label_attack"] is not None:
                labels_att_list.append(item["label_attack"])
            if item["label_trust"] is not None:
                labels_tr_list.append(item["label_trust"])

            node_offset += n_nodes

        batch_x = torch.cat(x_list, dim=0)
        batch_edge_index = torch.cat(edge_index_list, dim=1)
        batch_edge_attr = torch.cat(edge_attr_list, dim=0)
        batch_bridge_mask = torch.cat(bridge_mask_list, dim=0)
        batch_index = torch.cat(batch_idx_list, dim=0)

        batch_att = torch.cat(labels_att_list, dim=0) if labels_att_list else None
        batch_tr = torch.cat(labels_tr_list, dim=0) if labels_tr_list else None

        return GraphSnapshotBatch(
            x=batch_x,
            edge_index=batch_edge_index,
            edge_attr=batch_edge_attr,
            bridge_mask=batch_bridge_mask,
            batch_index=batch_index,
            num_graphs=len(batch_list),
            node_counts=node_counts,
            labels_attack=batch_att,
            labels_trust=batch_tr,
        )

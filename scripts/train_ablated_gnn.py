"""
Train Ablated BridgeAwareGAT without Hand-Tuned Heuristic Signatures.
Specifically trains a model from scratch using GraphFeatureExtractor(enable_heuristic_signatures=False),
so that the 10th feature column represents pure continuous statistical volatility (standard deviation of PDR)
rather than discrete hand-tuned cycle indicators (1.0, 0.5, 0.0).

Outputs:
- results/gnn/best_bridge_gat_ablated.pt
"""

import sys
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import networkx as nx
import torch
from torch.utils.data import DataLoader

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import MasterConfig, SimulationConfig, TopologyConfig
from backend.attacks.injector import AttackInjector
from backend.attacks.models import AttackConfig
from backend.digital_twin.models import TwinNodeState
from backend.gnn.features import GraphFeatureExtractor, GraphSnapshot
from backend.gnn.model import DualHeadGNNClassifier
from backend.gnn.dataset import GraphSnapshotDataset
from backend.gnn.trainer import GNNTrainer

LABEL_MAP = {
    "normal": 0,
    "dos": 1,
    "compromised_node": 2,
    "node_failure": 3,
    "on_off": 4,
}


def generate_ablated_simulation_snapshots(
    seeds: List[int],
    scenarios: List[str],
    duration_s: float = 25.0,
) -> Tuple[List[GraphSnapshot], List[torch.Tensor], List[torch.Tensor]]:
    """Generates snapshots strictly using enable_heuristic_signatures=False."""
    extractor = GraphFeatureExtractor(enable_heuristic_signatures=False)
    all_snapshots = []
    all_att_labels = []
    all_tr_labels = []

    attack_start_s = 5.0
    attack_end_s = 20.0

    for s in seeds:
        sc = scenarios[s % len(scenarios)]
        injector = AttackInjector()

        if sc == "dos":
            target_node = 2 if s % 2 == 0 else 3
            injector.add_attack(AttackConfig(
                attack_id=f"dos_{s}", attack_type="dos",
                target_nodes=[target_node], start_time=attack_start_s, end_time=attack_end_s,
                intensity=20.0 + (s % 10) * 1.5, seed=s,
            ))
        elif sc == "compromised_node":
            target_node = 3 if s % 2 == 0 else 4
            injector.add_attack(AttackConfig(
                attack_id=f"comp_{s}", attack_type="compromised_node",
                target_nodes=[target_node], start_time=attack_start_s, end_time=attack_end_s,
                intensity=0.55 + (s % 5) * 0.05, seed=s,
            ))
        elif sc == "node_failure":
            target_node = 1 if s % 2 == 0 else 5
            injector.add_attack(AttackConfig(
                attack_id=f"fail_{s}", attack_type="node_failure",
                target_nodes=[target_node], start_time=attack_start_s, end_time=attack_end_s,
                seed=s,
            ))
        elif sc == "on_off":
            target_node = 3
            injector.add_attack(AttackConfig(
                attack_id=f"onoff_{s}", attack_type="compromised_node",
                target_nodes=[target_node], start_time=attack_start_s, end_time=15.0,
                intensity=0.75, seed=s,
            ))
        else:
            target_node = -1

        sim_cfg = MasterConfig(
            simulation=SimulationConfig(duration=duration_s, seed=s, nodes=6),
            topology=TopologyConfig(type="mesh"),
        )
        sim = NetworkSimulator(config=sim_cfg, seed=s, attack_injector=injector)

        # Build articulation bridge
        sim.topology.graph.clear()
        sim.topology.graph.add_edges_from([
            (0, 1), (1, 2), (0, 2),
            (2, 3),
            (3, 4), (4, 5), (3, 5),
        ])
        sim.topology._compute_distances_and_neighbors()
        for nid, node in sim.nodes.items():
            nbrs = sim.topology.get_neighbors(nid)
            dists = sim.topology.get_neighbor_distances(nid)
            node.set_neighbors(nbrs, dists)

        prev_trust: Dict[int, float] = {}
        prev_pdr: Dict[int, float] = {}
        extractor.reset_history()

        for step_idx in range(int(duration_s)):
            current_time = float(step_idx)
            recs_list = sim.step()
            telem_records = {r.node_id: r for r in recs_list}

            node_states = {}
            for nid, rec in telem_records.items():
                node_states[nid] = TwinNodeState(
                    timestamp=current_time,
                    node_id=nid,
                    position=(0.0, 0.0),
                    packet_rate=rec.packet_rate,
                    forwarding_rate=rec.forwarding_rate,
                    packet_loss=rec.packet_loss,
                    latency=rec.latency,
                    rssi=rec.rssi,
                    energy=rec.energy,
                    cpu=rec.cpu,
                    memory=rec.memory,
                    neighbor_count=rec.neighbor_count,
                    trust_score=rec.trust_score,
                )

            snap = extractor.extract_snapshot(
                node_states=node_states,
                graph=sim.topology.graph,
                previous_trust=prev_trust,
                previous_pdr=prev_pdr,
            )

            N = len(snap.node_ids)
            att_labels = torch.zeros(N, dtype=torch.long)
            tr_labels = torch.ones(N, dtype=torch.float32)

            is_atk_window = (attack_start_s <= current_time < attack_end_s)
            for n_idx, nid in enumerate(snap.node_ids):
                if sc == "normal" or not is_atk_window:
                    att_labels[n_idx] = 0
                    tr_labels[n_idx] = 0.95
                elif nid == target_node:
                    att_labels[n_idx] = LABEL_MAP[sc]
                    tr_labels[n_idx] = 0.30 if sc in ("dos", "node_failure") else 0.45
                else:
                    att_labels[n_idx] = 0
                    tr_labels[n_idx] = 0.95

            all_snapshots.append(snap)
            all_att_labels.append(att_labels)
            all_tr_labels.append(tr_labels)

            for nid, r in telem_records.items():
                prev_trust[nid] = r.trust_score
                prev_pdr[nid] = max(0.0, 1.0 - r.packet_loss)

    return all_snapshots, all_att_labels, all_tr_labels


def main():
    torch.manual_seed(42)
    np.random.seed(42)

    print("======================================================================")
    print(" TRAINING ABLATED BRIDGE-AWARE GNN (WITHOUT HEURISTIC SIGNATURES)")
    print("======================================================================")

    train_seeds = list(range(100, 160))  # 60 seeds
    val_seeds = list(range(160, 180))    # 20 seeds
    scenarios = ["normal", "dos", "compromised_node", "node_failure", "on_off"]

    print("[*] Generating ablated training snapshots (raw statistical volatility only)...")
    t0 = time.time()
    train_snaps, train_att, train_tr = generate_ablated_simulation_snapshots(train_seeds, scenarios, duration_s=20.0)
    val_snaps, val_att, val_tr = generate_ablated_simulation_snapshots(val_seeds, scenarios, duration_s=20.0)
    print(f"[+] Dataset generated in {time.time() - t0:.2f}s: Train={len(train_snaps)}, Val={len(val_snaps)}")

    train_ds = GraphSnapshotDataset(train_snaps, train_att, train_tr)
    val_ds = GraphSnapshotDataset(val_snaps, val_att, val_tr)

    train_loader = DataLoader(train_ds, batch_size=128, shuffle=True, collate_fn=GraphSnapshotDataset.collate_snapshots)
    val_loader = DataLoader(val_ds, batch_size=128, shuffle=False, collate_fn=GraphSnapshotDataset.collate_snapshots)

    all_train_labels = torch.cat(train_att)
    counts = torch.bincount(all_train_labels, minlength=5).float()
    total_instances = float(len(all_train_labels))
    class_weights = torch.sqrt(total_instances / (5.0 * (counts + 1.0)))
    class_weights = class_weights / class_weights[0]

    model = DualHeadGNNClassifier(in_features=12, hidden_dim=64, embed_dim=32, num_classes=5, bridge_penalty=0.50)
    trainer = GNNTrainer(model=model, lr=3e-3, weight_decay=1e-4, loss_alpha=0.60, class_weights=class_weights)

    out_dir = ROOT_DIR / "results" / "gnn"
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_dir / "best_bridge_gat_ablated.pt"

    print("[*] Training ablated model for 25 epochs...")
    best_f1 = 0.0
    for epoch in range(1, 26):
        train_res = trainer.train_epoch(train_loader)
        val_res = trainer.evaluate(val_loader)
        val_f1 = val_res.get("macro_f1", 0.0)
        if val_f1 > best_f1:
            best_f1 = val_f1
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "best_macro_f1": best_f1,
            }, ckpt_path)
        if epoch % 5 == 0 or epoch == 25:
            print(f"  Epoch {epoch:2d}/25 | Train Loss: {train_res['loss']:.4f} | Val Acc: {val_res['accuracy']*100:.1f}% | Val F1: {val_f1*100:.1f}%")

    print(f"\n[+] Ablated model trained and saved to {ckpt_path} (Best Val Macro F1: {best_f1*100:.2f}%)")


if __name__ == "__main__":
    main()

"""
Hardware-in-the-Loop (HIL) Execution Engine.
Coordinates real-world dataset trace streaming, hardware serialization,
Dual-Head GAT inference, Bayesian evidence fusion, and physical actuation dispatch.
"""

import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
import networkx as nx
import torch

from backend.simulation.telemetry import TelemetryRecord
from backend.gnn.model import DualHeadGNNClassifier
from backend.gnn.features import GraphFeatureExtractor
from backend.gnn.fusion import GNNBayesianFusion
from .trace_adapter import RealWorldTraceBatch, RealWorldTraceEvent, TraceDatasetType, AttackCategory
from .hardware_bridge import (
    HardwareGatewayBridge,
    HardwareGatewaySpec,
    ESP32_S3_SPEC,
    RASPBERRY_PI_4B_SPEC,
    HILActuationCommand,
)


class HILEvaluationMetrics(dict):
    """Container for HIL evaluation statistics."""
    pass


class HILExecutionEngine:
    """
    Executes real-world dataset traces through the hardware-in-the-loop pipeline.
    """

    def __init__(
        self,
        topology_graph: nx.Graph,
        model_path: Optional[Path] = None,
        gateway_spec: HardwareGatewaySpec = ESP32_S3_SPEC,
    ):
        self.topology = topology_graph.copy()
        self.num_nodes = topology_graph.number_of_nodes()
        self.gateway_bridge = HardwareGatewayBridge(spec=gateway_spec)
        self.fusion = GNNBayesianFusion()

        # Load GNN Model
        self.model = DualHeadGNNClassifier()
        if model_path and model_path.exists():
            ckpt = torch.load(model_path, weights_only=False)
            self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.eval()

        self.cut_vertices = set(nx.articulation_points(self.topology))
        self.active_detours: List[Tuple[int, int]] = []
        self.quarantined_nodes: set = set()
        self.feature_extractor = GraphFeatureExtractor()

    def process_trace_batch(
        self,
        batch: RealWorldTraceBatch,
    ) -> Dict[str, Any]:
        """
        Processes a single time epoch through the complete HIL pipeline:
        1. Gateway Serial Ingestion
        2. Graph Tensor Encoding
        3. GNN Inference
        4. Bayesian Evidence Fusion
        5. Closed-Loop Hardware Actuation
        """
        t_start = time.perf_counter()

        # 1. Gateway Serial Transmission
        t0_serial = time.perf_counter()
        reconstituted_records: Dict[int, TelemetryRecord] = {}
        total_serial_delay = 0.0

        for event in batch.events:
            rec, delay_ms = self.gateway_bridge.transmit_record(event.record)
            reconstituted_records[rec.node_id] = rec
            total_serial_delay += delay_ms
        t1_serial = time.perf_counter()
        serial_cpu_time_ms = (t1_serial - t0_serial) * 1000.0

        # 2. Graph Tensor Encoding via Digital Twin Shadow
        t0_feat = time.perf_counter()
        from backend.digital_twin.models import TwinNodeState
        twin_states = {
            nid: TwinNodeState(**rec.model_dump())
            for nid, rec in reconstituted_records.items()
        }
        snap = self.feature_extractor.extract_snapshot(twin_states, self.topology)
        t1_feat = time.perf_counter()
        feat_time_ms = (t1_feat - t0_feat) * 1000.0

        # 3. GNN Inference
        t0_gnn = time.perf_counter()
        with torch.no_grad():
            logits, trust_preds, _ = self.model(snap.x, snap.edge_index, snap.edge_attr, snap.bridge_mask)
            probs = torch.softmax(logits, dim=-1)
            pred_classes = torch.argmax(probs, dim=-1).cpu().numpy()
            threat_probs = (1.0 - probs[:, 0]).cpu().numpy()  # Class 0 is benign
        t1_gnn = time.perf_counter()
        gnn_time_ms = (t1_gnn - t0_gnn) * 1000.0

        # 4. Bayesian Evidence Fusion & Fast-Path Decision
        t0_fusion = time.perf_counter()
        fused_threats = {}
        actuation_commands: List[HILActuationCommand] = []
        node_to_idx = {nid: idx for idx, nid in enumerate(snap.node_ids)}

        for nid in range(self.num_nodes):
            if nid in node_to_idx:
                idx = node_to_idx[nid]
                p_threat = float(threat_probs[idx])
                t_gnn = float(trust_preds[idx].item()) if trust_preds.ndim > 0 else 0.5
            else:
                p_threat = 1.0
                t_gnn = 0.0

            t_bayes = max(0.0, 1.0 - reconstituted_records[nid].packet_loss)
            is_cut = (nid in self.cut_vertices)
            deg = self.topology.degree(nid) if self.topology.has_node(nid) else 2

            fused_score, diag = self.fusion.fuse_node_trust(
                node_id=nid,
                t_bayes=t_bayes,
                t_gnn=t_gnn,
                p_attack_gnn=p_threat,
                is_cut_vertex=is_cut,
                degree=deg,
            )
            fused_threat = 1.0 - fused_score
            fused_threats[nid] = fused_threat

            # Theorem 4 Fast-Path Trigger
            if (fused_threat > 0.55 or p_threat > 0.65) and nid not in self.quarantined_nodes:
                # 5. Closed-Loop Hardware Actuation
                if nid in self.cut_vertices and self.topology.has_node(nid):
                    # Step 5a: Proactive Detour Bridge Actuation connecting all neighbor components
                    nbrs = list(self.topology.neighbors(nid))
                    for i in range(len(nbrs)):
                        for j in range(i + 1, len(nbrs)):
                            u, v = nbrs[i], nbrs[j]
                            if not self.topology.has_edge(u, v):
                                self.topology.add_edge(u, v)
                                self.active_detours.append((u, v))
                                cmd_detour = self.gateway_bridge.dispatch_actuation(
                                    action_type="DETOUR_BRIDGE",
                                    target_node_id=nid,
                                    params={"detour_via": f"10.0.0.{v+1}", "bridge_pair": [u, v]}
                                )
                                actuation_commands.append(cmd_detour)

                # Step 5b: Node Quarantine Actuation
                cmd_iso = self.gateway_bridge.dispatch_actuation(
                    action_type="NODE_ISOLATION",
                    target_node_id=nid
                )
                actuation_commands.append(cmd_iso)
                self.quarantined_nodes.add(nid)
                if self.topology.has_node(nid):
                    # Sever incident links to isolate node from traffic while preserving node tensor alignment
                    self.topology.remove_edges_from(list(self.topology.edges(nid)))

        t1_fusion = time.perf_counter()
        fusion_and_actuation_ms = (t1_fusion - t0_fusion) * 1000.0

        total_loop_ms = (time.perf_counter() - t_start) * 1000.0

        # Compute Ground Truth vs Prediction for this batch
        ground_truth = {e.record.node_id: e.is_attack for e in batch.events}
        predictions = {}
        threat_probs_dict = {}
        for nid in range(self.num_nodes):
            if nid in node_to_idx:
                idx = node_to_idx[nid]
                predictions[nid] = bool(threat_probs[idx] > 0.50)
                threat_probs_dict[nid] = round(float(threat_probs[idx]), 3)
            else:
                # Quarantined node remains classified as threat
                predictions[nid] = True
                threat_probs_dict[nid] = 1.0

        # Connectivity of active communicating subnetwork
        active_nodes = [n for n in self.topology.nodes() if n not in self.quarantined_nodes]
        is_conn = nx.is_connected(self.topology.subgraph(active_nodes)) if len(active_nodes) > 1 else True

        return {
            "timestamp": batch.timestamp,
            "total_serial_delay_ms": round(total_serial_delay, 2),
            "serial_cpu_time_ms": round(serial_cpu_time_ms, 2),
            "feat_time_ms": round(feat_time_ms, 2),
            "gnn_time_ms": round(gnn_time_ms, 2),
            "fusion_and_actuation_ms": round(fusion_and_actuation_ms, 2),
            "total_closed_loop_ms": round(total_loop_ms, 2),
            "actuation_count": len(actuation_commands),
            "ground_truth": ground_truth,
            "predictions": predictions,
            "threat_probs": threat_probs_dict,
            "quarantined_count": len(self.quarantined_nodes),
            "detours_count": len(self.active_detours),
            "is_connected": is_conn,
        }

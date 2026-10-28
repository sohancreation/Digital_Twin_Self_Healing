"""
Unit and Integration Tests for GNN Phase 5:
Real-World IoT Dataset Trace Replay & Hardware-in-the-Loop (HIL) Integration.
"""

from pathlib import Path
import pytest
import networkx as nx

from backend.hil.trace_adapter import (
    TraceDatasetType,
    AttackCategory,
    RealWorldTraceGenerator,
    RealWorldTraceBatch,
)
from backend.hil.hardware_bridge import (
    HardwarePlatform,
    HardwareGatewaySpec,
    ESP32_S3_SPEC,
    RASPBERRY_PI_4B_SPEC,
    SerialPacketFramer,
    HILActuationTranslator,
    HardwareGatewayBridge,
)
from backend.hil.engine import HILExecutionEngine
from scripts.run_gnn_phase4_scalability import build_scale_topology


def test_real_world_trace_generation_and_schema():
    """Verifies trace generator emits valid TelemetryRecord batches across all datasets."""
    datasets = [TraceDatasetType.TON_IOT, TraceDatasetType.CIC_IOT2023, TraceDatasetType.BOT_IOT]
    categories = [AttackCategory.DOS_FLOOD, AttackCategory.SELECTIVE_DROP, AttackCategory.SCANNING_RECON]

    for ds in datasets:
        for cat in categories:
            gen = RealWorldTraceGenerator(dataset=ds, seed=42)
            batches = gen.generate_trace_sequence(
                num_nodes=12,
                duration_s=6.0,
                attack_node_ids=[2],
                attack_category=cat,
                attack_start_s=2.0,
                attack_end_s=5.0,
            )
            assert len(batches) == 6
            for b in batches:
                assert len(b.events) == 12
                for e in b.events:
                    rec = e.record
                    assert 0.0 <= rec.packet_loss <= 1.0
                    assert 0.0 <= rec.cpu <= 100.0
                    assert 0.0 <= rec.memory <= 100.0
                    assert 0.0 <= rec.energy <= 100.0
                    assert rec.packet_rate >= 0.0


def test_binary_packet_framing_and_crc16():
    """Verifies binary serial encoding, CRC16 validation, and packet corruption detection."""
    gen = RealWorldTraceGenerator(dataset=TraceDatasetType.TON_IOT, seed=42)
    batches = gen.generate_trace_sequence(num_nodes=6, duration_s=2.0)
    original_rec = batches[0].events[0].record

    # 1. Successful encode and decode
    frame = SerialPacketFramer.encode_record(original_rec)
    assert len(frame) == 24  # Compact 24-byte IoT frame
    assert frame[:2] == SerialPacketFramer.SYNC_HEADER

    decoded = SerialPacketFramer.decode_frame(frame)
    assert decoded is not None
    assert decoded.node_id == original_rec.node_id
    assert abs(decoded.packet_rate - original_rec.packet_rate) < 0.2
    assert abs(decoded.packet_loss - original_rec.packet_loss) < 0.01

    # 2. Corrupted packet detection
    corrupted_frame = bytearray(frame)
    corrupted_frame[12] ^= 0xFF
    decoded_corrupted = SerialPacketFramer.decode_frame(bytes(corrupted_frame))
    assert decoded_corrupted is None  # CRC mismatch correctly rejected


def test_hardware_actuation_translation():
    """Verifies conversion of DT recovery actions to physical gateway commands."""
    cmd_iso = HILActuationTranslator.translate("NODE_ISOLATION", target_node_id=3)
    assert "iptables" in cmd_iso.physical_instruction
    assert "10.0.0.4" in cmd_iso.physical_instruction
    assert cmd_iso.execution_latency_ms > 0.0

    cmd_detour = HILActuationTranslator.translate(
        "DETOUR_BRIDGE",
        target_node_id=2,
        params={"detour_via": "10.0.0.5"}
    )
    assert "ip route add" in cmd_detour.physical_instruction
    assert "10.0.0.5" in cmd_detour.physical_instruction

    cmd_limit = HILActuationTranslator.translate("RATE_LIMITING", target_node_id=1, params={"rate_pps": 10})
    assert "tc qdisc" in cmd_limit.physical_instruction


def test_hil_execution_engine_pipeline():
    """Verifies end-to-end execution of real trace batch through HILExecutionEngine."""
    topo = build_scale_topology(num_nodes=12, seed=42)
    model_path = Path("results/gnn/best_bridge_gat.pt")
    engine = HILExecutionEngine(topology_graph=topo, model_path=model_path, gateway_spec=ESP32_S3_SPEC)

    gen = RealWorldTraceGenerator(dataset=TraceDatasetType.TON_IOT, seed=42)
    batches = gen.generate_trace_sequence(
        num_nodes=12,
        duration_s=8.0,
        attack_node_ids=[2],
        attack_category=AttackCategory.DOS_FLOOD,
        attack_start_s=3.0,
        attack_end_s=6.0,
    )

    for b in batches:
        res = engine.process_trace_batch(b)
        assert res["total_closed_loop_ms"] > 0.0
        assert res["total_serial_delay_ms"] > 0.0
        assert res["feat_time_ms"] > 0.0
        assert res["gnn_time_ms"] > 0.0
        assert res["is_connected"] is True  # Detour maintains zero partition


def test_hil_benchmark_detection_fidelity():
    """Verifies detection accuracy and precision on real-world intrusion traces."""
    from scripts.run_gnn_phase5_hil_trace_benchmark import evaluate_dataset_trace

    model_path = Path("results/gnn/best_bridge_gat.pt")
    res = evaluate_dataset_trace(
        dataset_type=TraceDatasetType.TON_IOT,
        attack_category=AttackCategory.DOS_FLOOD,
        model_path=model_path,
        num_nodes=12,
        duration_s=40.0,
        seed=42,
        gateway_spec=ESP32_S3_SPEC,
    )

    assert res["accuracy"] >= 0.96
    assert res["precision"] >= 0.90
    assert res["recall"] >= 0.70
    assert res["f1_score"] >= 0.80
    assert res["partition_rate"] == 0.0  # Zero network partitioning

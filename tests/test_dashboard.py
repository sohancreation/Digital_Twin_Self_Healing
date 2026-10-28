"""
Unit and integration tests for Phase 10:
Real-Time Research Monitoring Dashboard.
Verifies models, DashboardService orchestration, REST endpoints, and WebSocket streaming.
"""

import pytest
from fastapi.testclient import TestClient

from backend.dashboard.models import (
    NodeDisplayState,
    EdgeDisplayState,
    TopologySnapshot,
    MLPredictionState,
    TrustBreakdownState,
    FidelityMetricState,
    HealingAuditState,
    TelemetryFrame,
    AttackTriggerRequest,
    HealingTriggerRequest,
    RollbackTriggerRequest,
)
from backend.dashboard.service import DashboardService
from backend.dashboard.app import create_app


# ---------------------------------------------------------------------------
# Test Suite 1: Data Model Serialization & Validation
# ---------------------------------------------------------------------------

def test_node_display_state_model():
    node = NodeDisplayState(
        node_id=0,
        x=120.0,
        y=90.0,
        is_alive=True,
        operational_state="NOMINAL",
        trust_score=0.98,
        packet_rate=2.5,
        forwarding_rate=2.4,
        packet_loss=0.01,
        latency_ms=11.2,
        energy_pct=98.5,
        cpu_pct=15.0,
        queue_length=2,
        is_cut_vertex=False,
    )
    d = node.to_dict()
    assert d["node_id"] == 0
    assert d["operational_state"] == "NOMINAL"
    assert d["trust_score"] == 0.98
    assert d["is_cut_vertex"] is False


def test_topology_snapshot_model():
    n1 = NodeDisplayState(node_id=1, x=100.0, y=100.0)
    n2 = NodeDisplayState(node_id=2, x=200.0, y=200.0)
    e1 = EdgeDisplayState(source=1, target=2, status="ACTIVE")
    topo = TopologySnapshot(nodes=[n1, n2], edges=[e1], connected_components=1, is_partitioned=False)
    d = topo.to_dict()
    assert len(d["nodes"]) == 2
    assert len(d["edges"]) == 1
    assert d["is_partitioned"] is False


def test_telemetry_frame_model():
    topo = TopologySnapshot(nodes=[], edges=[])
    fid = FidelityMetricState(shadow_fidelity_score=0.99)
    frame = TelemetryFrame(
        tick=1,
        timestamp=1.0,
        topology=topo,
        network_pdr=0.98,
        network_loss=0.02,
        network_latency_ms=12.5,
        network_throughput_pkts_s=12.0,
        network_energy_pct=100.0,
        instantaneous_qos=0.95,
        fidelity=fid,
    )
    assert frame.tick == 1
    assert frame.network_pdr == 0.98
    assert frame.fidelity.shadow_fidelity_score == 0.99


# ---------------------------------------------------------------------------
# Test Suite 2: Dashboard Service Orchestration
# ---------------------------------------------------------------------------

@pytest.fixture
def service():
    return DashboardService(seed=42, num_nodes=6)


def test_service_initialization(service):
    assert service.current_tick == 0
    assert service.current_time == 0.0
    assert service.is_running is False
    frame = service.get_current_frame()
    assert frame.tick == 0
    assert len(frame.topology.nodes) == 6
    assert len(frame.topology.edges) >= 5
    assert frame.fidelity.shadow_fidelity_score > 0.90


def test_service_step(service):
    init_tick = service.current_tick
    frame1 = service.step(dt=1.0)
    assert frame1.tick == init_tick + 1
    assert frame1.timestamp == 1.0
    assert frame1.network_pdr >= 0.0
    assert frame1.network_latency_ms > 0.0
    assert len(service.history_frames) >= 1


def test_service_attack_injection_and_stop(service):
    req = AttackTriggerRequest(
        attack_type="dos",
        target_node=2,
        duration_s=10.0,
        intensity=3.0,
    )
    inj_res = service.inject_attack(req)
    assert inj_res["status"] == "ATTACK_INJECTED"
    assert len(service.active_attack_descriptors) == 1

    # Step simulation during attack
    frame_attack = service.step(dt=1.0)
    assert len(frame_attack.active_attacks) == 1
    target_node = next(n for n in frame_attack.topology.nodes if n.node_id == 2)
    assert target_node.operational_state == "ATTACKED"

    # Stop attacks
    stop_res = service.stop_attacks()
    assert stop_res["status"] == "ATTACKS_STOPPED"
    assert len(service.active_attack_descriptors) == 0


def test_service_trigger_healing(service):
    # Step a bit
    service.step(dt=1.0)
    req = HealingTriggerRequest(target_node=2, weight_profile="BALANCED")
    audit = service.trigger_healing(req)
    assert audit.chosen_strategy_id is not None
    assert audit.action_type is not None
    assert audit.verification_status == "VERIFYING"
    assert len(service.audit_history) >= 1


def test_service_trigger_rollback(service):
    service.step(dt=1.0)
    res = service.trigger_rollback(reason="Test rollback invocation")
    assert res["success"] is True
    assert res["elapsed_ms"] >= 0.0
    assert len(service.audit_history) >= 1
    assert service.audit_history[-1].action_type == "ROLLBACK"


def test_service_get_node_trust_breakdown(service):
    service.step(dt=1.0)
    trust = service.get_node_trust_breakdown(node_id=2)
    assert trust.node_id == 2
    assert 0.0 <= trust.composite_trust <= 1.0
    assert 0.0 <= trust.direct_trust <= 1.0
    assert trust.classification in ["TRUSTED", "SUSPICIOUS"]


def test_service_reset(service):
    for _ in range(5):
        service.step(dt=1.0)
    assert service.current_tick == 5
    service.reset(seed=123)
    assert service.current_tick == 0
    assert service.current_time == 0.0
    assert len(service.history_frames) == 1


# ---------------------------------------------------------------------------
# Test Suite 3: FastAPI REST & WebSocket Endpoints
# ---------------------------------------------------------------------------

@pytest.fixture
def client(service):
    app = create_app(service=service)
    with TestClient(app) as c:
        yield c


def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "tick" in data


def test_api_state(client):
    res = client.get("/api/state")
    assert res.status_code == 200
    data = res.json()
    assert "topology" in data
    assert "network_pdr" in data


def test_api_step(client):
    res = client.post("/api/step?dt=1.0")
    assert res.status_code == 200
    data = res.json()
    assert data["tick"] >= 1


def test_api_play_pause(client):
    res_play = client.post("/api/play?speed=2.0")
    assert res_play.status_code == 200
    assert res_play.json()["status"] == "RUNNING"
    assert res_play.json()["playback_speed"] == 2.0

    res_pause = client.post("/api/pause")
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == "PAUSED"


def test_api_reset(client):
    res = client.post("/api/reset?seed=99")
    assert res.status_code == 200
    assert res.json()["status"] == "RESET_SUCCESSFUL"
    assert res.json()["tick"] == 0


def test_api_attack_injection_and_stop(client):
    payload = {
        "attack_type": "dos",
        "target_node": 2,
        "duration_s": 12.0,
        "intensity": 2.0,
        "drop_probability": 0.5,
    }
    res = client.post("/api/attack/inject", json=payload)
    assert res.status_code == 200
    assert res.json()["injection_result"]["status"] == "ATTACK_INJECTED"

    res_stop = client.post("/api/attack/stop")
    assert res_stop.status_code == 200
    assert res_stop.json()["cancellation_result"]["status"] == "ATTACKS_STOPPED"


def test_api_heal_trigger_and_rollback(client):
    payload = {
        "target_node": 2,
        "weight_profile": "SECURITY_FIRST",
        "force_escalation": False,
    }
    res_heal = client.post("/api/heal/trigger", json=payload)
    assert res_heal.status_code == 200
    assert res_heal.json()["status"] == "HEALING_TRIGGERED"

    res_rb = client.post("/api/heal/rollback", json={"reason": "Operator verification"})
    assert res_rb.status_code == 200
    assert res_rb.json()["status"] == "ROLLBACK_TRIGGERED"


def test_api_fidelity(client):
    res = client.get("/api/fidelity")
    assert res.status_code == 200
    data = res.json()
    assert "shadow_fidelity_score" in data
    assert "clock_drift_ms" in data


def test_api_node_trust(client):
    res = client.get("/api/node/2/trust")
    assert res.status_code == 200
    data = res.json()
    assert data["node_id"] == 2
    assert "composite_trust" in data

    # Test invalid node 404
    res_404 = client.get("/api/node/999/trust")
    assert res_404.status_code == 404


def test_api_audit_log(client):
    res = client.get("/api/audit")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_api_index_html(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "IoTDTR" in res.text or "Mission Control" in res.text


def test_websocket_telemetry(client):
    with client.websocket_connect("/ws/telemetry") as ws:
        # Receive initial frame immediately on connect
        data = ws.receive_json()
        assert "tick" in data
        assert "topology" in data
        assert "network_pdr" in data

        # Send step command through websocket
        ws.send_json({"action": "step", "dt": 1.0})
        data2 = ws.receive_json()
        assert data2["tick"] == data["tick"] + 1

        # Send ping
        ws.send_json({"action": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"


# ---------------------------------------------------------------------------
# Test Suite 4: Next-Gen GNN Mission Control REST Endpoints
# ---------------------------------------------------------------------------

def test_api_gnn_attention(client):
    res = client.get("/api/gnn/attention")
    assert res.status_code == 200
    data = res.json()
    assert data["num_nodes"] == 6
    assert "attention_matrix" in data
    assert len(data["attention_matrix"]) == 6
    assert len(data["attention_matrix"][0]) == 6
    assert data["bridge_amplification_ratio"] >= 1.0
    assert len(data["top_attended_edges"]) >= 2
    assert len(data["feature_attribution"]) >= 3


def test_api_gnn_counterfactual(client):
    res = client.get("/api/gnn/counterfactual?node_id=2")
    assert res.status_code == 200
    data = res.json()
    assert "worlds" in data
    assert "W0" in data["worlds"]
    assert "W1" in data["worlds"]
    assert "W2" in data["worlds"]
    assert "W_star" in data["worlds"]
    assert data["chosen_world_id"] == "W_star"
    assert data["compromised_node"] == 2


def test_api_gnn_hil_trace(client):
    res = client.get("/api/gnn/hil_trace")
    assert res.status_code == 200
    data = res.json()
    assert "traces" in data
    assert len(data["traces"]) == 3
    datasets = [t["dataset"] for t in data["traces"]]
    assert "TON_IoT" in datasets
    assert "CIC-IoT2023" in datasets
    assert "BoT-IoT" in datasets
    assert "hardware_profiles" in data
    assert "ESP32-S3" in data["hardware_profiles"]
    assert "Raspberry_Pi_4B" in data["hardware_profiles"]
    assert data["hardware_profiles"]["ESP32-S3"]["total_closed_loop_ms"] < 10.0


def test_api_gnn_adversarial(client):
    # Hardened evaluation
    res_hard = client.get("/api/gnn/adversarial?epsilon=0.05&model_type=hardened")
    assert res_hard.status_code == 200
    data_hard = res_hard.json()
    assert data_hard["epsilon"] == 0.05
    assert data_hard["model_type"] == "hardened"
    assert data_hard["accuracy"] >= 90.0
    assert data_hard["attack_success_rate"] <= 10.0
    assert data_hard["is_defense_active"] is True

    # Standard baseline evaluation
    res_std = client.get("/api/gnn/adversarial?epsilon=0.10&model_type=standard")
    assert res_std.status_code == 200
    data_std = res_std.json()
    assert data_std["epsilon"] == 0.10
    assert data_std["model_type"] == "standard"
    assert data_std["is_defense_active"] is False
    assert data_std["attack_success_rate"] > 0.0


def test_api_gnn_federated(client):
    res = client.get("/api/gnn/federated")
    assert res.status_code == 200
    data = res.json()
    assert data["num_gateways"] == 4
    assert len(data["gateways"]) == 4
    assert "convergence" in data
    assert data["convergence"]["fedgraphbridge_acc"] >= 88.0
    assert "communication_compression" in data
    assert data["communication_compression"]["reduction_pct"] == 87.5


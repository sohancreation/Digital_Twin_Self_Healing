"""
Unit and integration tests for the Master Artifact Evaluation Package.
Verifies execution of all baseline and GNN verification stages, manifest generation,
and cryptographic SHA-256 checksum audits.
"""

import json
from pathlib import Path
import pytest
from scripts.run_artifact_evaluation import ArtifactEvaluator


@pytest.fixture
def evaluator(tmp_path):
    return ArtifactEvaluator(output_dir=tmp_path, quick_mode=True)


def test_evaluator_environment(evaluator):
    env = evaluator.get_system_environment()
    assert "python_version" in env
    assert "pytorch_version" in env
    assert "os_platform" in env
    assert "cpu_cores" in env
    assert env["cpu_cores"] > 0


def test_evaluator_phase1_simulator(evaluator):
    res = evaluator.verify_phase1_simulator()
    assert res["passed"] is True
    assert res["stage_id"] == "P01_Simulator"
    assert res["key_metrics"]["num_nodes"] == 6


def test_evaluator_phase2_digital_twin(evaluator):
    res = evaluator.verify_phase2_digital_twin()
    assert res["passed"] is True
    assert res["stage_id"] == "P02_DigitalTwin"
    assert res["key_metrics"]["records_ingested"] == 1
    assert res["key_metrics"]["energy"] == 99.0


def test_evaluator_gnn_phase1_bridge_gat(evaluator):
    res = evaluator.verify_gnn_phase1_bridge_gat()
    assert res["passed"] is True
    assert res["stage_id"] == "GNN_P1_BridgeGAT"
    assert res["key_metrics"]["num_heads"] == 4


def test_evaluator_gnn_phase2_multitask(evaluator):
    res = evaluator.verify_gnn_phase2_multitask()
    assert res["passed"] is True
    assert res["stage_id"] == "GNN_P2_DualHead"
    assert res["key_metrics"]["num_classes"] == 5


def test_evaluator_gnn_phase6_explainability(evaluator):
    res = evaluator.verify_gnn_phase6_explainability()
    assert res["passed"] is True
    assert res["stage_id"] == "GNN_P6_Explainability"
    assert len(res["key_metrics"]["worlds_evaluated"]) == 4


def test_evaluator_gnn_phase7_adversarial(evaluator):
    res = evaluator.verify_gnn_phase7_adversarial()
    assert res["passed"] is True
    assert res["stage_id"] == "GNN_P7_AdversarialRobustness"


def test_evaluator_gnn_phase8_federated(evaluator):
    res = evaluator.verify_gnn_phase8_federated()
    assert res["passed"] is True
    assert res["stage_id"] == "GNN_P8_FederatedLearning"
    assert res["key_metrics"]["num_gateways"] == 4
    assert res["key_metrics"]["aggregation_strategy"] == "FedGraphBridge"


def test_evaluator_full_execution_and_reports(evaluator, tmp_path):
    summary = evaluator.execute_all_evaluations()
    assert summary["overall_status"] == "ALL_PASS"
    assert summary["total_stages"] == 20
    assert summary["stages_passed"] == 20
    assert summary["stages_failed"] == 0

    # Verify generated report files
    manifest_path = tmp_path / "artifact_evaluation_manifest.json"
    md_path = tmp_path / "artifact_evaluation_report.md"
    html_path = tmp_path / "artifact_evaluation_report.html"

    assert manifest_path.exists(), "Manifest JSON was not generated"
    assert md_path.exists(), "Markdown report was not generated"
    assert html_path.exists(), "HTML report was not generated"

    with open(manifest_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
        assert loaded["overall_status"] == "ALL_PASS"
        assert len(loaded["stages"]) == 20

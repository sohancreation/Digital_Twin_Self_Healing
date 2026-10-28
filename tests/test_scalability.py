"""
Unit and integration tests for Phase 12:
Scalability, Edge Deployment & Network Stress Evaluation.
"""

import pytest
import numpy as np

from backend.scalability.models import (
    NetworkScaleProfile,
    ComputationalProfileRecord,
    TrafficStressRecord,
    MultiTargetAttackRecord,
    EdgeGatewaySpec,
    AsymptoticFitResult,
    ScalabilityCampaignResult,
)
from backend.scalability.profiler import ComputationalProfiler
from backend.scalability.stress import TrafficStressEvaluator, MultiTargetAttackEvaluator
from backend.scalability.edge_budget import EdgeBudgetVerifier
from backend.scalability.runner import ScalabilityRunner


class TestScalabilityModels:
    """Verifies schema validation and boundary constraints for Phase 12 models."""

    def test_network_scale_profile_schema(self):
        profile = NetworkScaleProfile(
            num_nodes=24,
            layout="mesh",
            num_edges=56,
            avg_degree=4.67,
            network_diameter=5,
            clustering_coefficient=0.421,
            communication_range_m=38.0,
        )
        assert profile.num_nodes == 24
        assert profile.num_edges == 56
        assert profile.avg_degree == 4.67
        assert profile.network_diameter == 5
        assert 0.0 <= profile.clustering_coefficient <= 1.0

    def test_computational_profile_record_schema(self):
        rec = ComputationalProfileRecord(
            num_nodes=12,
            topology_layout="mesh",
            num_candidates_evaluated=4,
            lookahead_horizon_s=30,
            sync_latency_ms=1.2,
            trust_eval_latency_ms=2.1,
            candidate_gen_latency_ms=0.8,
            sandbox_sim_latency_ms=4.5,
            optimization_latency_ms=1.1,
            total_cycle_latency_ms=9.7,
            memory_footprint_mb=45.2,
            memory_delta_mb=3.1,
            cpu_percent=18.5,
        )
        assert rec.total_cycle_latency_ms == 9.7
        assert rec.num_nodes == 12
        assert rec.memory_footprint_mb > 0.0

    def test_traffic_stress_record_schema(self):
        stress = TrafficStressRecord(
            traffic_rate_pps=20.0,
            total_network_throughput_pps=240.0,
            mean_pdr=0.88,
            min_pdr=0.75,
            mean_latency_ms=42.5,
            queue_overflow_drops=180,
            channel_loss_drops=40,
            total_energy_consumed_j=85.0,
            is_queue_saturated=True,
            is_system_stable=True,
        )
        assert stress.is_queue_saturated
        assert stress.is_system_stable
        assert stress.queue_overflow_drops > stress.channel_loss_drops

    def test_multi_target_attack_record_schema(self):
        rec = MultiTargetAttackRecord(
            num_compromised_nodes=3,
            compromised_node_ids=[1, 3, 5],
            attack_type="coordinated_dos",
            total_network_nodes=24,
            mean_pdr=0.91,
            nadir_pdr=0.82,
            resilience_score=0.925,
            mttr_s=7.5,
            partition_events_count=0,
            rollback_count=0,
            mitigation_action="RATE_LIMITING (x3)",
        )
        assert rec.num_compromised_nodes == 3
        assert len(rec.compromised_node_ids) == 3
        assert rec.resilience_score > 0.90

    def test_edge_gateway_spec_schema(self):
        spec = EdgeGatewaySpec(
            gateway_name="Raspberry Pi 4B",
            processor_arch="Quad-core ARM Cortex-A72 @ 1.5 GHz",
            ram_capacity_mb=4096,
            real_time_deadline_ms=100.0,
            observed_cycle_latency_ms=22.5,
            deadline_slack_ms=77.5,
            is_deadline_met=True,
            max_supported_nodes=85,
        )
        assert spec.is_deadline_met
        assert spec.deadline_slack_ms > 0
        assert spec.max_supported_nodes > 50


class TestComputationalProfiler:
    """Validates latency measurement, memory tracking, and asymptotic regression."""

    def test_memory_tracking(self):
        profiler = ComputationalProfiler()
        rss = profiler.get_current_memory_mb()
        assert rss > 5.0  # Python process uses at least a few MB

    def test_profile_network_scale(self):
        profiler = ComputationalProfiler(seed=42)
        rec = profiler.profile_network_scale(num_nodes=6, lookahead_horizon_s=15)
        assert rec.num_nodes == 6
        assert rec.total_cycle_latency_ms > 0.0
        assert rec.sync_latency_ms > 0.0
        assert rec.trust_eval_latency_ms > 0.0
        assert rec.memory_footprint_mb > 0.0

    def test_asymptotic_complexity_fitting(self):
        profiler = ComputationalProfiler()
        x = [6, 12, 24, 48]
        # Linear latency pattern
        y = [2.0, 4.1, 7.9, 16.2]
        fit = profiler.fit_asymptotic_complexity(x, y, "Ingestion Stage", "O(N)")
        assert fit.r_squared >= 0.90
        assert fit.empirical_pass
        assert len(fit.coefficients) >= 2


class TestTrafficStressEvaluator:
    """Validates network stability boundaries under packet rate scaling."""

    def test_low_traffic_stability(self):
        evaluator = TrafficStressEvaluator(seed=42, num_nodes=6)
        res = evaluator.evaluate_traffic_rate(rate_pps=2.0, duration_s=10.0)
        assert res.is_system_stable
        assert not res.is_queue_saturated
        assert res.mean_pdr >= 0.90

    def test_high_traffic_saturation(self):
        evaluator = TrafficStressEvaluator(seed=42, num_nodes=6)
        res = evaluator.evaluate_traffic_rate(rate_pps=35.0, duration_s=10.0)
        assert res.is_queue_saturated
        assert res.queue_overflow_drops > 0


class TestMultiTargetAttackEvaluator:
    """Validates multi-node coordinated adversarial attack resilience."""

    def test_single_adversary_recovery(self):
        evaluator = MultiTargetAttackEvaluator(seed=42, num_nodes=12)
        rec = evaluator.evaluate_multi_target_attack(num_compromised=1, duration_s=20.0, attack_start_s=5.0, attack_end_s=15.0)
        assert rec.num_compromised_nodes == 1
        assert rec.mean_pdr >= 0.85
        assert rec.resilience_score >= 0.85

    def test_multi_adversary_coordination(self):
        evaluator = MultiTargetAttackEvaluator(seed=42, num_nodes=12)
        rec = evaluator.evaluate_multi_target_attack(num_compromised=2, duration_s=20.0, attack_start_s=5.0, attack_end_s=15.0)
        assert rec.num_compromised_nodes == 2
        assert len(rec.compromised_node_ids) == 2
        assert rec.nadir_pdr > 0.0


class TestEdgeBudgetVerifier:
    """Validates real-time deadline margins across catalog edge platforms."""

    def test_evaluate_raspberry_pi(self):
        spec = EdgeBudgetVerifier.evaluate_gateway(
            gateway_name="Raspberry Pi 4B",
            reference_cycle_latency_ms=15.0,
            network_size=24,
        )
        assert spec.gateway_name == "Raspberry Pi 4B"
        assert spec.real_time_deadline_ms == 100.0
        assert spec.observed_cycle_latency_ms > 15.0  # Slowdown reflected
        assert spec.is_deadline_met
        assert spec.max_supported_nodes >= 24

    def test_evaluate_all_gateways(self):
        results = EdgeBudgetVerifier.evaluate_all_gateways(
            reference_cycle_latency_ms=10.0,
            network_size=20,
        )
        assert len(results) == 4
        names = [g.gateway_name for g in results]
        assert "Raspberry Pi 4B" in names
        assert "NVIDIA Jetson Nano" in names
        assert "Intel Industrial Edge (x86)" in names
        assert "ESP32-S3 Micro-Gateway" in names
        for g in results:
            assert g.max_supported_nodes >= 10


class TestScalabilityRunner:
    """Validates end-to-end integration across multi-scale sweeps."""

    def test_characterize_topology(self):
        runner = ScalabilityRunner(seed=42)
        topo = runner.characterize_topology(num_nodes=8, layout="mesh")
        assert topo.num_nodes == 8
        assert topo.num_edges > 0
        assert topo.avg_degree > 0.0
        assert topo.network_diameter >= 1

    def test_network_scale_sweep(self):
        runner = ScalabilityRunner(seed=42)
        topos, comps, fits = runner.run_network_scale_sweep(scales=[6, 12], lookahead_horizon_s=10)
        assert len(topos) == 2
        assert len(comps) == 2
        assert len(fits) == 6
        assert comps[1].num_nodes == 12
        assert comps[1].total_cycle_latency_ms >= comps[0].total_cycle_latency_ms

    def test_full_campaign_execution(self):
        runner = ScalabilityRunner(seed=42)
        result = runner.run_full_scalability_campaign(
            scales=[6, 10],
            traffic_rates=[2.0, 10.0],
            adversary_counts=[1, 2],
        )
        assert isinstance(result, ScalabilityCampaignResult)
        assert len(result.scale_profiles) == 2
        assert len(result.computational_profiles) == 2
        assert len(result.traffic_stress_records) == 2
        assert len(result.multi_target_attacks) == 2
        assert len(result.edge_gateway_evaluations) == 4
        assert len(result.asymptotic_fits) == 6

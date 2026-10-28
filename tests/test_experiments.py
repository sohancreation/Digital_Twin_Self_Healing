"""
Unit and integration tests for Phase 11:
End-to-End Experimental Research Framework & Automated Comparative Benchmarking.
"""

import pytest
import numpy as np

from backend.experiments.models import (
    BaselineType,
    ExperimentMetricRecord,
    ExperimentRunResult,
    BenchmarkConfig,
    StatisticalComparison,
    HorizonAblationRecord,
    WeightSensitivityRecord,
    ChannelLossAblationRecord,
    TrustPenaltyAblationRecord,
)
from backend.experiments.baselines import (
    UnmitigatedBaseline,
    StaticThresholdIDSBaseline,
    MLFixedRecoveryBaseline,
    ProposedDigitalTwinBaseline,
)
from backend.experiments.runner import ExperimentRunner
from backend.experiments.ablation import AblationStudyEngine
from backend.experiments.statistics import StatisticalEvaluator
from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import MasterConfig, SimulationConfig, TopologyConfig
from backend.attacks import AttackInjector, AttackConfig


@pytest.fixture
def base_simulator():
    """Provides a fresh deterministic NetworkSimulator."""
    cfg = MasterConfig(
        simulation=SimulationConfig(duration=30.0, seed=42, nodes=6),
        topology=TopologyConfig(layout="mesh"),
    )
    return NetworkSimulator(config=cfg, seed=42)


class TestExperimentModels:
    """Verifies schemas and constraints of Phase 11 data models."""

    def test_benchmark_config_defaults(self):
        cfg = BenchmarkConfig()
        assert len(cfg.baselines) == 4
        assert BaselineType.PROPOSED_DIGITAL_TWIN in cfg.baselines
        assert cfg.num_nodes == 6
        assert cfg.duration_s == 120.0

    def test_metric_record_schema(self):
        rec = ExperimentMetricRecord(
            timestamp=10.0,
            pdr=0.95,
            packet_loss_rate=0.05,
            latency_ms=18.5,
            throughput_pps=12.0,
            mean_energy_remaining=98.2,
            mean_cpu_utilization=0.15,
            active_node_count=6,
            connected_components=1,
            is_partitioned=False,
            attack_active=False,
            mitigation_active=False,
        )
        assert rec.pdr == 0.95
        assert not rec.is_partitioned

    def test_run_result_validation(self):
        res = ExperimentRunResult(
            baseline=BaselineType.PROPOSED_DIGITAL_TWIN,
            attack_type="dos",
            target_node=2,
            seed=42,
            duration_s=60.0,
            attack_start_s=20.0,
            attack_end_s=50.0,
            resilience_score=0.925,
            mean_pdr=0.942,
            min_pdr=0.680,
            final_pdr=0.965,
            mean_latency_ms=22.4,
            max_latency_ms=58.0,
            total_packets_sent=1200,
            total_packets_delivered=1130,
            total_packets_dropped=70,
            energy_consumed_j=84.5,
            partition_events_count=0,
            partition_rate=0.0,
        )
        assert res.resilience_score == 0.925
        assert res.partition_events_count == 0


class TestBaselineControllers:
    """Validates operational behavior across each comparative baseline."""

    def test_unmitigated_baseline_no_intervention(self, base_simulator):
        controller = UnmitigatedBaseline(simulator=base_simulator)
        recs = base_simulator.step()
        telemetry = {r.node_id: r for r in recs}
        out = controller.step(base_simulator.current_time, telemetry)

        assert not out["detected"]
        assert not out["mitigation_active"]
        assert out["action"] == "NO_ACTION"

    def test_static_threshold_ids_isolation_causes_partition(self):
        # Setup simulator with compromised attack targeting cut-vertex node 3
        seed = 42
        injector = AttackInjector(attack_seed=seed)
        injector.add_attack(
            AttackConfig(
                attack_id="atk_comp_3",
                attack_type="compromised_node",
                target_nodes=[3],
                start_time=5.0,
                end_time=25.0,
                intensity=0.75,
                seed=seed,
            )
        )
        cfg = MasterConfig(
            simulation=SimulationConfig(duration=30.0, seed=seed, nodes=6),
            topology=TopologyConfig(layout="mesh"),
        )
        sim = NetworkSimulator(config=cfg, seed=seed, attack_injector=injector)
        controller = StaticThresholdIDSBaseline(simulator=sim, loss_threshold=0.10, consecutive_violations=2)

        # Run until detection & naive isolation
        isolated = False
        for _ in range(15):
            recs = sim.step()
            telemetry = {r.node_id: r for r in recs}
            out = controller.step(sim.current_time, telemetry)
            if out.get("mitigation_active"):
                isolated = True
                break

        assert isolated, "Static threshold IDS should detect high drop and isolate node"
        assert controller.mitigation_applied
        assert "NAIVE_ISOLATION" in controller.mitigation_action

    def test_ml_fixed_recovery_baseline(self):
        seed = 42
        injector = AttackInjector(attack_seed=seed)
        injector.add_attack(
            AttackConfig(
                attack_id="atk_dos_2",
                attack_type="dos",
                target_nodes=[2],
                start_time=5.0,
                end_time=25.0,
                intensity=25.0,
                seed=seed,
            )
        )
        cfg = MasterConfig(
            simulation=SimulationConfig(duration=30.0, seed=seed, nodes=6),
            topology=TopologyConfig(layout="mesh"),
        )
        sim = NetworkSimulator(config=cfg, seed=seed, attack_injector=injector)
        controller = MLFixedRecoveryBaseline(simulator=sim, target_node=2, detection_delay_s=2.0)

        mitigated = False
        for _ in range(15):
            recs = sim.step()
            telemetry = {r.node_id: r for r in recs}
            out = controller.step(sim.current_time, telemetry)
            if out.get("mitigation_active"):
                mitigated = True
                break

        assert mitigated, "ML baseline should trigger fixed heuristic recovery"
        assert "FIXED_RATE_LIMIT" in controller.mitigation_action

    def test_proposed_digital_twin_baseline_execution(self):
        seed = 42
        injector = AttackInjector(attack_seed=seed)
        injector.add_attack(
            AttackConfig(
                attack_id="atk_prop_dos_2",
                attack_type="dos",
                target_nodes=[2],
                start_time=5.0,
                end_time=25.0,
                intensity=20.0,
                seed=seed,
            )
        )
        cfg = MasterConfig(
            simulation=SimulationConfig(duration=30.0, seed=seed, nodes=6),
            topology=TopologyConfig(layout="mesh"),
        )
        sim = NetworkSimulator(config=cfg, seed=seed, attack_injector=injector)
        controller = ProposedDigitalTwinBaseline(simulator=sim, weight_profile="BALANCED", seed=seed)

        for _ in range(15):
            recs = sim.step()
            telemetry = {r.node_id: r for r in recs}
            out = controller.step(sim.current_time, telemetry)

        # Confirm digital twin was updated
        assert len(controller.digital_twin.node_states) == 6
        assert controller.trust_engine is not None


class TestExperimentRunner:
    """Verifies end-to-end benchmark execution across baselines."""

    def test_run_single_experiment_unmitigated(self):
        runner = ExperimentRunner()
        res = runner.run_single_experiment(
            baseline_type=BaselineType.UNMITIGATED,
            attack_type="dos",
            seed=42,
            duration_s=20.0,
            attack_start_s=5.0,
            attack_end_s=15.0,
        )
        assert res.baseline == BaselineType.UNMITIGATED
        assert res.duration_s == 20.0
        assert len(res.timeseries) == 20
        assert res.resilience_score > 0.0

    def test_run_single_experiment_proposed(self):
        runner = ExperimentRunner()
        res = runner.run_single_experiment(
            baseline_type=BaselineType.PROPOSED_DIGITAL_TWIN,
            attack_type="dos",
            seed=42,
            duration_s=20.0,
            attack_start_s=5.0,
            attack_end_s=15.0,
        )
        assert res.baseline == BaselineType.PROPOSED_DIGITAL_TWIN
        assert res.resilience_score > 0.0
        assert res.partition_events_count == 0


class TestAblationStudies:
    """Validates parameter sensitivity and ablation sweeps."""

    def test_horizon_ablation(self):
        engine = AblationStudyEngine(seed=42)
        results = engine.run_horizon_ablation(horizons=[10, 30])
        assert len(results) == 2
        assert results[0].horizon_s == 10
        assert results[1].horizon_s == 30
        assert results[1].prediction_rmse < results[0].prediction_rmse

    def test_weight_sensitivity_ablation(self):
        engine = AblationStudyEngine(seed=42)
        results = engine.run_weight_sensitivity_ablation()
        assert len(results) == 4
        profiles = [r.profile_name for r in results]
        assert "BALANCED" in profiles
        assert "SECURITY_FIRST" in profiles
        assert "ENERGY_CONSTRAINED" in profiles
        assert "LATENCY_CRITICAL" in profiles

    def test_channel_loss_ablation(self):
        engine = AblationStudyEngine(seed=42)
        results = engine.run_channel_loss_ablation(loss_rates=[0.0, 0.10])
        assert len(results) == 2
        assert results[0].downlink_delivery_rate >= results[1].downlink_delivery_rate

    def test_trust_penalty_ablation(self):
        engine = AblationStudyEngine(seed=42)
        results = engine.run_trust_penalty_ablation(ratios=[2.0, 8.0])
        assert len(results) == 2
        assert results[1].evasion_suppression_rate > results[0].evasion_suppression_rate


class TestStatisticalEvaluator:
    """Validates hypothesis testing, confidence intervals, and effect size calculations."""

    def test_summary_stats_calculation(self):
        vals = [0.92, 0.94, 0.93, 0.95, 0.91]
        stats_dict = StatisticalEvaluator.compute_summary_stats(vals)
        assert round(stats_dict["mean"], 2) == 0.93
        assert stats_dict["std"] > 0.0
        assert stats_dict["ci_lower"] < stats_dict["mean"] < stats_dict["ci_upper"]
        assert stats_dict["zero_rate_pct"] == 0.0

        zero_vals = [0.0, 0.0, 0.5, 0.0]
        zero_dict = StatisticalEvaluator.compute_summary_stats(zero_vals)
        assert zero_dict["zero_rate_pct"] == 75.0
        assert zero_dict["zero_count"] == 3

    def test_welch_t_test_and_cohens_d(self):
        proposed = [0.95, 0.96, 0.94, 0.95, 0.97]
        baseline = [0.72, 0.75, 0.70, 0.74, 0.71]
        comp = StatisticalEvaluator.compare_distributions(
            proposed_vals=proposed,
            baseline_vals=baseline,
            metric_name="resilience_score",
            baseline_type=BaselineType.UNMITIGATED,
            higher_is_better=True,
        )
        assert comp.is_significant
        assert comp.is_highly_significant
        assert comp.p_value < 0.001
        assert comp.cohens_d > 2.0  # Very large positive effect size
        assert comp.delta_mean > 0.0
        assert comp.mann_whitney_u is not None
        assert comp.mann_whitney_p is not None and comp.mann_whitney_p < 0.05
        assert comp.statistical_power is not None and comp.statistical_power > 0.80
        assert comp.bayes_factor_10 is not None and comp.bayes_factor_10 > 1.0

    def test_latex_table_generation(self):
        summary_dict = {
            "baseline_summaries": {
                "unmitigated": {"resilience_score": {"mean": 0.85, "std": 0.02}},
                "static_threshold_isolation": {"resilience_score": {"mean": 0.86, "std": 0.03}},
                "ml_fixed_recovery": {"resilience_score": {"mean": 0.88, "std": 0.02}},
                "proposed_digital_twin": {"resilience_score": {"mean": 0.96, "std": 0.01}},
            }
        }
        comp = StatisticalComparison(
            metric_name="resilience_score",
            baseline=BaselineType.STATIC_THRESHOLD_ISOLATION,
            proposed_mean=0.96,
            baseline_mean=0.86,
            delta_mean=0.10,
            percent_improvement=11.63,
            proposed_std=0.01,
            baseline_std=0.03,
            t_statistic=5.2,
            p_value=0.0001,
            is_significant=True,
            is_highly_significant=True,
            cohens_d=2.45,
            confidence_interval_95=(0.06, 0.14),
        )
        latex = StatisticalEvaluator.generate_latex_table(summary_dict, [comp])
        assert r"\begin{table*}" in latex
        assert r"\caption" in latex
        assert r"\end{table*}" in latex
        assert "Resilience Score" in latex
        assert "$^{***}$" in latex

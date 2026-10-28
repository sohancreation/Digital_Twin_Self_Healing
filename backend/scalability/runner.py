"""
Comprehensive Scalability and Stress Test Runner for Phase 12.
Orchestrates network scale sweeps (N in [6, 100]), traffic stress benchmarks,
multi-target coordinated attack evaluations, asymptotic complexity fitting,
and edge gateway budget projections.
"""

import time
from typing import Dict, List, Optional, Tuple, Any
import networkx as nx
import numpy as np

from ..simulation.simulator import NetworkSimulator
from ..simulation.config import MasterConfig, SimulationConfig, TopologyConfig
from .models import (
    NetworkScaleProfile,
    ComputationalProfileRecord,
    TrafficStressRecord,
    MultiTargetAttackRecord,
    EdgeGatewaySpec,
    AsymptoticFitResult,
    ScalabilityCampaignResult,
)
from .profiler import ComputationalProfiler
from .stress import TrafficStressEvaluator, MultiTargetAttackEvaluator
from .edge_budget import EdgeBudgetVerifier


class ScalabilityRunner:
    """
    Automated execution engine coordinating multi-scale, multi-layout,
    and multi-adversary evaluation sweeps.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.profiler = ComputationalProfiler(seed=seed)

    def characterize_topology(
        self,
        num_nodes: int,
        layout: str = "mesh",
        comm_range: float = 38.0,
    ) -> NetworkScaleProfile:
        """Constructs graph and extracts topological invariant parameters."""
        sim_cfg = MasterConfig(
            simulation=SimulationConfig(duration=10.0, seed=self.seed, nodes=num_nodes),
            topology=TopologyConfig(layout=layout, communication_range=comm_range),
        )
        sim = NetworkSimulator(config=sim_cfg, seed=self.seed)
        g = sim.topology.graph

        num_edges = g.number_of_edges()
        degrees = [d for _, d in g.degree()]
        avg_deg = float(np.mean(degrees)) if degrees else 0.0

        if nx.is_connected(g):
            diameter = int(nx.diameter(g))
        else:
            comps = list(nx.connected_components(g))
            sub_diams = [nx.diameter(g.subgraph(c)) for c in comps if len(c) > 1]
            diameter = int(max(sub_diams)) if sub_diams else 1

        clustering = float(nx.average_clustering(g))

        return NetworkScaleProfile(
            num_nodes=num_nodes,
            layout=layout,
            num_edges=num_edges,
            avg_degree=round(avg_deg, 2),
            network_diameter=diameter,
            clustering_coefficient=round(clustering, 4),
            communication_range_m=comm_range,
        )

    def run_network_scale_sweep(
        self,
        scales: Optional[List[int]] = None,
        layout: str = "mesh",
        lookahead_horizon_s: int = 30,
    ) -> Tuple[List[NetworkScaleProfile], List[ComputationalProfileRecord], List[AsymptoticFitResult]]:
        """
        Sweeps across network node counts N in [6, 100], measures step latencies,
        and fits asymptotic complexity curves.
        """
        node_scales = scales or [6, 12, 24, 48, 100]
        topo_profiles: List[NetworkScaleProfile] = []
        comp_records: List[ComputationalProfileRecord] = []

        for n in node_scales:
            comm_range = 36.0 if n <= 24 else (42.0 if n <= 48 else 48.0)
            topo = self.characterize_topology(n, layout=layout, comm_range=comm_range)
            topo_profiles.append(topo)

            comp = self.profiler.profile_network_scale(
                num_nodes=n,
                layout=layout,
                lookahead_horizon_s=lookahead_horizon_s,
            )
            comp_records.append(comp)

        # Fit asymptotic curves
        x_vals = [c.num_nodes for c in comp_records]
        fits = [
            self.profiler.fit_asymptotic_complexity(
                x_vals, [c.sync_latency_ms for c in comp_records], "State Synchronizer", "O(N)"
            ),
            self.profiler.fit_asymptotic_complexity(
                x_vals, [c.trust_eval_latency_ms for c in comp_records], "Dynamic Trust Engine", "O(N)"
            ),
            self.profiler.fit_asymptotic_complexity(
                x_vals, [c.candidate_gen_latency_ms for c in comp_records], "Candidate Strategy Generator", "O(|V| + |E|)"
            ),
            self.profiler.fit_asymptotic_complexity(
                x_vals, [c.sandbox_sim_latency_ms for c in comp_records], "In-Silico Sandbox Simulation", "O(|S| * H)"
            ),
            self.profiler.fit_asymptotic_complexity(
                x_vals, [c.optimization_latency_ms for c in comp_records], "Multi-Objective TOPSIS", "O(|S| * M)"
            ),
            self.profiler.fit_asymptotic_complexity(
                x_vals, [c.total_cycle_latency_ms for c in comp_records], "Total Closed-Loop Cycle", "O(N)"
            ),
        ]

        return topo_profiles, comp_records, fits

    def run_traffic_stress_sweep(
        self,
        rates: Optional[List[float]] = None,
        num_nodes: int = 12,
        duration_s: float = 30.0,
    ) -> List[TrafficStressRecord]:
        """Sweeps traffic rate lambda per node to evaluate buffer saturation boundaries."""
        traffic_rates = rates or [1.0, 5.0, 10.0, 20.0, 35.0, 50.0]
        evaluator = TrafficStressEvaluator(seed=self.seed, num_nodes=num_nodes)
        records = []
        for r in traffic_rates:
            rec = evaluator.evaluate_traffic_rate(rate_pps=r, duration_s=duration_s)
            records.append(rec)
        return records

    def run_multi_target_attack_sweep(
        self,
        adversary_counts: Optional[List[int]] = None,
        num_nodes: int = 24,
        duration_s: float = 40.0,
    ) -> List[MultiTargetAttackRecord]:
        """Evaluates coordinated multi-node attack resilience across K simultaneous adversaries."""
        counts = adversary_counts or [1, 2, 3, 5]
        evaluator = MultiTargetAttackEvaluator(seed=self.seed, num_nodes=num_nodes)
        records = []
        for k in counts:
            rec = evaluator.evaluate_multi_target_attack(
                num_compromised=k,
                attack_type="coordinated_dos",
                duration_s=duration_s,
            )
            records.append(rec)
        return records

    def run_edge_gateway_evaluation(
        self,
        reference_cycle_latency_ms: float,
        network_size: int = 24,
    ) -> List[EdgeGatewaySpec]:
        """Evaluates real-time deadlines across edge computing platforms."""
        return EdgeBudgetVerifier.evaluate_all_gateways(
            reference_cycle_latency_ms=reference_cycle_latency_ms,
            network_size=network_size,
        )

    def run_full_scalability_campaign(
        self,
        scales: Optional[List[int]] = None,
        traffic_rates: Optional[List[float]] = None,
        adversary_counts: Optional[List[int]] = None,
    ) -> ScalabilityCampaignResult:
        """Executes full Phase 12 evaluation campaign and aggregates structured result."""
        topo_profiles, comp_records, fits = self.run_network_scale_sweep(scales=scales)
        stress_records = self.run_traffic_stress_sweep(rates=traffic_rates)
        attack_records = self.run_multi_target_attack_sweep(adversary_counts=adversary_counts)

        edge_comp = self.profiler.profile_network_scale(num_nodes=24, lookahead_horizon_s=10)
        ref_latency = edge_comp.total_cycle_latency_ms
        ref_n = edge_comp.num_nodes
        gateways = self.run_edge_gateway_evaluation(ref_latency, network_size=ref_n)

        return ScalabilityCampaignResult(
            scale_profiles=topo_profiles,
            computational_profiles=comp_records,
            traffic_stress_records=stress_records,
            multi_target_attacks=attack_records,
            edge_gateway_evaluations=gateways,
            asymptotic_fits=fits,
        )

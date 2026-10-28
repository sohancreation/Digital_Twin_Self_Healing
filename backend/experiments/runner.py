"""
Experimental Runner for Phase 11.
Executes automated comparative benchmarking across all 4 baselines,
multi-seed statistical repetitions, and comprehensive metric collection.
"""

import time
import math
from typing import Dict, List, Optional, Any, Tuple
import networkx as nx
import numpy as np

from ..simulation.simulator import NetworkSimulator
from ..simulation.config import MasterConfig, SimulationConfig, TopologyConfig
from ..simulation.telemetry import TelemetryRecord
from ..attacks import AttackInjector, AttackConfig
from .models import (
    BaselineType,
    ExperimentMetricRecord,
    ExperimentRunResult,
    BenchmarkConfig,
)
from .baselines import (
    BaseBaselineController,
    UnmitigatedBaseline,
    StaticThresholdIDSBaseline,
    MLFixedRecoveryBaseline,
    RLRecoveryBaseline,
    ProposedDigitalTwinBaseline,
)


class ExperimentRunner:
    """
    Automated execution engine that coordinates multi-baseline, multi-attack,
    and multi-seed experimental campaigns.
    """

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()

    def run_single_experiment(
        self,
        baseline_type: BaselineType,
        attack_type: str,
        seed: int,
        duration_s: float = 120.0,
        attack_start_s: float = 30.0,
        attack_end_s: float = 90.0,
        target_node: Optional[int] = None,
        weight_profile: str = "BALANCED",
        lookahead_horizon_s: int = 30,
    ) -> ExperimentRunResult:
        """
        Executes a single end-to-end benchmark run for a specific baseline and attack.
        """
        # Determine target node based on attack semantics
        if target_node is None:
            if attack_type in ("compromised_node", "on_off"):
                # Target articulation node 3 in mesh (classic cut-vertex)
                target_node = 3
            elif attack_type == "node_failure":
                target_node = 1
            else:  # DoS
                target_node = 2

        # 1. Setup attack injector
        attack_injector = AttackInjector(attack_seed=seed)
        if attack_type == "dos":
            attack_injector.add_attack(
                AttackConfig(
                    attack_id=f"dos_node_{target_node}_{seed}",
                    attack_type="dos",
                    target_nodes=[target_node],
                    start_time=attack_start_s,
                    end_time=attack_end_s,
                    intensity=20.0,
                    seed=seed,
                )
            )
        elif attack_type == "compromised_node":
            attack_injector.add_attack(
                AttackConfig(
                    attack_id=f"comp_node_{target_node}_{seed}",
                    attack_type="compromised_node",
                    target_nodes=[target_node],
                    start_time=attack_start_s,
                    end_time=attack_end_s,
                    intensity=0.50,
                    seed=seed,
                )
            )
        elif attack_type == "node_failure":
            attack_injector.add_attack(
                AttackConfig(
                    attack_id=f"fail_node_{target_node}_{seed}",
                    attack_type="node_failure",
                    target_nodes=[target_node],
                    start_time=attack_start_s,
                    end_time=attack_end_s,
                    seed=seed,
                )
            )
        elif attack_type == "on_off":
            # On-off evasive attack: alternates between active dropping (T_attack = 10s) and dormant compliance (T_dormant = 15s)
            t_curr = attack_start_s
            idx = 1
            while t_curr < attack_end_s:
                t_burst_end = min(t_curr + 10.0, attack_end_s)
                attack_injector.add_attack(
                    AttackConfig(
                        attack_id=f"onoff_{target_node}_{idx}_{seed}",
                        attack_type="compromised_node",
                        target_nodes=[target_node],
                        start_time=t_curr,
                        end_time=t_burst_end,
                        intensity=0.70,
                        seed=seed,
                    )
                )
                t_curr += 25.0
                idx += 1

        # 2. Setup Simulator
        sim_cfg = MasterConfig(
            simulation=SimulationConfig(
                duration=duration_s,
                timestep=1.0,
                seed=seed,
                nodes=self.config.num_nodes,
            ),
            topology=TopologyConfig(
                layout=self.config.topology_layout,
                communication_range=32.0,
            ),
        )
        simulator = NetworkSimulator(config=sim_cfg, seed=seed, attack_injector=attack_injector)

        # Standard research benchmark topology with articulation cut-vertex (Node 3)
        simulator.topology.graph.clear()
        simulator.topology.graph.add_edges_from([(0, 1), (1, 2), (0, 2), (2, 3), (3, 4), (4, 5), (3, 5)])
        simulator.topology._compute_distances_and_neighbors()
        for nid, node in simulator.nodes.items():
            nbrs = simulator.topology.get_neighbors(nid)
            dists = simulator.topology.get_neighbor_distances(nid)
            node.set_neighbors(nbrs, dists)

        # 3. Instantiate baseline controller
        controller: BaseBaselineController
        if baseline_type == BaselineType.UNMITIGATED:
            controller = UnmitigatedBaseline(simulator=simulator)
        elif baseline_type == BaselineType.STATIC_THRESHOLD_ISOLATION:
            controller = StaticThresholdIDSBaseline(simulator=simulator)
        elif baseline_type == BaselineType.ML_FIXED_RECOVERY:
            controller = MLFixedRecoveryBaseline(simulator=simulator, target_node=target_node)
        elif baseline_type == BaselineType.RL_RECOVERY:
            controller = RLRecoveryBaseline(simulator=simulator, target_node=target_node)
        elif baseline_type == BaselineType.PROPOSED_DIGITAL_TWIN:
            controller = ProposedDigitalTwinBaseline(
                simulator=simulator,
                weight_profile=weight_profile,
                lookahead_horizon_s=lookahead_horizon_s,
                seed=seed,
            )
        else:
            raise ValueError(f"Unknown baseline: {baseline_type}")

        # 4. Step-by-step simulation loop
        timeseries: List[ExperimentMetricRecord] = []
        total_steps = int(duration_s / simulator.timestep)
        t_detect = None
        t_actuate = None
        t_restored = None
        nominal_pdr = 0.98

        partition_count = 0
        total_pdr_integral = 0.0

        for step_idx in range(total_steps):
            current_time = simulator.current_time

            # Step physical simulator
            step_records = simulator.step()
            telemetry_dict = {r.node_id: r for r in step_records}

            # Step baseline controller
            ctrl_out = controller.step(current_time, telemetry_dict)

            # Record temporal timestamps
            if ctrl_out.get("detected") and t_detect is None:
                t_detect = current_time
            if ctrl_out.get("mitigation_active") and t_actuate is None:
                t_actuate = current_time

            # Compute network-wide instantaneous metrics
            active_recs = [r for r in step_records if r.connection_state != "DISCONNECTED"]
            active_count = len(active_recs)

            # Mean metrics across active nodes
            if active_recs:
                mean_loss = float(np.mean([r.packet_loss for r in active_recs]))
                mean_lat = float(np.mean([r.latency for r in active_recs]))
                mean_energy = float(np.mean([r.energy for r in active_recs]))
                mean_cpu = float(np.mean([r.cpu for r in active_recs]))
                throughput = float(np.sum([r.forwarding_rate for r in active_recs]))
            else:
                mean_loss = 1.0
                mean_lat = 100.0
                mean_energy = 0.0
                mean_cpu = 0.0
                throughput = 0.0

            inst_pdr = max(0.0, min(1.0, 1.0 - mean_loss))
            total_pdr_integral += inst_pdr

            # Check network connectivity components k(G')
            active_graph = simulator.topology.graph.copy()
            # If node isolated, remove isolated nodes
            for nid, node in simulator.nodes.items():
                if getattr(node, "connection_state", None) in ("DISCONNECTED", "ISOLATED") or getattr(node, "_is_failed", False):
                    if nid in active_graph:
                        active_graph.remove_node(nid)

            comp_count = nx.number_connected_components(active_graph) if len(active_graph) > 0 else 0
            is_part = comp_count > 1
            if is_part:
                partition_count += 1

            # Check QoS recovery threshold (>= 90% of nominal)
            if t_actuate is not None and t_restored is None and current_time > t_actuate:
                if inst_pdr >= (0.90 * nominal_pdr):
                    t_restored = current_time

            attack_active = (attack_start_s <= current_time < attack_end_s)
            mitigation_active = bool(ctrl_out.get("mitigation_active", False))

            timeseries.append(
                ExperimentMetricRecord(
                    timestamp=round(current_time, 2),
                    pdr=round(inst_pdr, 4),
                    packet_loss_rate=round(mean_loss, 4),
                    latency_ms=round(mean_lat, 2),
                    throughput_pps=round(throughput, 2),
                    mean_energy_remaining=round(mean_energy, 2),
                    mean_cpu_utilization=round(mean_cpu, 4),
                    active_node_count=active_count,
                    connected_components=comp_count,
                    is_partitioned=is_part,
                    attack_active=attack_active,
                    mitigation_active=mitigation_active,
                    trust_score_target=ctrl_out.get("target_trust"),
                )
            )

        # 5. Compute summary metrics
        pdr_values = [r.pdr for r in timeseries]
        lat_values = [r.latency_ms for r in timeseries]

        mean_pdr = float(np.mean(pdr_values))
        min_pdr = float(np.min(pdr_values))
        final_pdr = float(pdr_values[-1])
        mean_lat = float(np.mean(lat_values))
        max_lat = float(np.max(lat_values))

        # Macroscopic Resilience Score: integral(PDR) / (nominal_PDR * duration)
        resilience_score = total_pdr_integral / (nominal_pdr * total_steps)
        resilience_score = max(0.0, min(1.0, resilience_score))

        # Temporal metrics
        mttd = (t_detect - attack_start_s) if t_detect is not None else None
        mtta = (t_actuate - t_detect) if (t_actuate is not None and t_detect is not None) else None
        mttr = (t_restored - t_actuate) if (t_restored is not None and t_actuate is not None) else None

        # Packet and energy accounting
        tot_sent = int(np.sum([r.packet_rate for r in simulator.telemetry_history]))
        tot_loss = int(np.sum([r.packet_rate * r.packet_loss for r in simulator.telemetry_history]))
        tot_delivered = max(0, tot_sent - tot_loss)
        energy_consumed = float(self.config.num_nodes * 100.0 - np.sum([n.current_energy_j for n in simulator.nodes.values()]))

        partition_rate = partition_count / total_steps

        return ExperimentRunResult(
            baseline=baseline_type,
            attack_type=attack_type,
            target_node=target_node,
            seed=seed,
            duration_s=duration_s,
            attack_start_s=attack_start_s,
            attack_end_s=attack_end_s,
            mttd_s=round(mttd, 2) if mttd is not None else None,
            mtta_s=round(mtta, 2) if mtta is not None else None,
            mttr_s=round(mttr, 2) if mttr is not None else None,
            resilience_score=round(resilience_score, 4),
            mean_pdr=round(mean_pdr, 4),
            min_pdr=round(min_pdr, 4),
            final_pdr=round(final_pdr, 4),
            mean_latency_ms=round(mean_lat, 2),
            max_latency_ms=round(max_lat, 2),
            total_packets_sent=tot_sent,
            total_packets_delivered=tot_delivered,
            total_packets_dropped=tot_loss,
            energy_consumed_j=round(energy_consumed, 2),
            partition_events_count=partition_count,
            partition_rate=round(partition_rate, 4),
            rollback_count=controller.rollback_count,
            mitigation_action=controller.mitigation_action,
            timeseries=timeseries,
        )

    def run_comparative_suite(
        self,
        attack_types: Optional[List[str]] = None,
        seeds: Optional[List[int]] = None,
        baselines: Optional[List[BaselineType]] = None,
    ) -> List[ExperimentRunResult]:
        """
        Runs the full Cartesian product of baselines x attack_types x seeds.
        """
        target_attacks = attack_types or self.config.attack_types
        target_seeds = seeds or self.config.seeds
        target_baselines = baselines or self.config.baselines

        all_results: List[ExperimentRunResult] = []

        for b_type in target_baselines:
            for atk in target_attacks:
                for s in target_seeds:
                    res = self.run_single_experiment(
                        baseline_type=b_type,
                        attack_type=atk,
                        seed=s,
                        duration_s=self.config.duration_s,
                        attack_start_s=self.config.attack_start_s,
                        attack_end_s=self.config.attack_end_s,
                    )
                    all_results.append(res)

        return all_results

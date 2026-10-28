"""
Digital Twin Recovery Sandbox Simulator.
Clones the synchronized Digital Twin shadow state into an isolated virtual sandbox,
applies a candidate recovery strategy s_k, and forward-simulates network dynamics
over lookahead horizon H to project latency, packet loss, battery drain, and topology safety.
"""

import time
import copy
from typing import Dict, List, Optional, Tuple, Any, Set
import numpy as np
import networkx as nx

from ..digital_twin.models import TwinNodeState, LinkState
from ..digital_twin.twin import DigitalTwin
from .models import (
    RecoveryCandidate,
    RecoveryActionType,
    SandboxSimulationResult,
    StochasticSimulationSummary,
)
from .feasibility import FeasibilityChecker


class RecoverySandbox:
    """
    Virtual in-silico execution sandbox for simulating candidate recovery actions
    before committing actuation commands to the physical / simulated IoT network.
    """

    def __init__(
        self,
        base_nominal_latency_ms: float = 12.0,
        base_nominal_loss_ratio: float = 0.02,
        base_nominal_energy_drain_per_s: float = 0.03,
        feasibility_checker: Optional[FeasibilityChecker] = None,
    ):
        self.base_nominal_latency_ms = base_nominal_latency_ms
        self.base_nominal_loss_ratio = base_nominal_loss_ratio
        self.base_nominal_energy_drain_per_s = base_nominal_energy_drain_per_s
        self.checker = feasibility_checker or FeasibilityChecker()

    def simulate_candidate(
        self,
        digital_twin: DigitalTwin,
        candidate: RecoveryCandidate,
        horizon_s: float = 30.0,
        timestep: float = 1.0,
        attack_context: Optional[Dict[int, str]] = None,
    ) -> SandboxSimulationResult:
        """
        Clones Digital Twin state and forward-simulates the network over horizon_s
        under candidate mitigation strategy s_k.
        """
        t_start = time.perf_counter()

        # 1. Clone Virtual Environment
        original_nodes = digital_twin.get_all_nodes()
        sandbox_nodes: Dict[int, TwinNodeState] = {
            nid: state.model_copy(deep=True)
            for nid, state in original_nodes.items()
        }
        sandbox_graph: nx.Graph = digital_twin.get_network_topology().copy()
        total_nodes = len(sandbox_nodes)

        # Infer active attack types on nodes if not provided
        attacks: Dict[int, str] = {}
        if attack_context:
            attacks = dict(attack_context)
        else:
            # Infer from node state
            for nid, nstate in sandbox_nodes.items():
                if nstate.threat_level > 0.5:
                    if nstate.packet_rate > 15.0:
                        attacks[nid] = "dos"
                    elif nstate.packet_loss > 0.4:
                        attacks[nid] = "compromised_node"
                    elif nstate.connection_state == "DISCONNECTED":
                        attacks[nid] = "node_failure"
                    else:
                        attacks[nid] = "compromised_node"

        # 2. Configure Candidate Mitigation Parameters in Sandbox
        action = candidate.action_type
        targets = set(candidate.target_nodes)
        params = candidate.parameters or {}

        # Signaling overhead metric
        signaling_overhead = self._compute_signaling_overhead(action, candidate, sandbox_graph)

        # Track active routing bypasses: Dict[Tuple[src, dst], path]
        active_bypasses: Dict[Tuple[int, int], List[int]] = {}
        reboot_duration = float(params.get("reboot_duration_s", 8.0))
        rate_limits: Dict[int, float] = {}
        boosted_nodes: Set[int] = set()

        # Apply topological / structural changes based on action
        if action == "NODE_ISOLATION":
            for t in targets:
                if sandbox_graph.has_node(t):
                    # Remove links to target
                    edges_to_remove = list(sandbox_graph.edges(t))
                    sandbox_graph.remove_edges_from(edges_to_remove)
                    if t in sandbox_nodes:
                        sandbox_nodes[t] = sandbox_nodes[t].model_copy(
                            update={"connection_state": "DISCONNECTED", "trust_score": 0.0}
                        )

        elif action == "DYNAMIC_REROUTING":
            # Install bypass routes around targets
            for t in targets:
                bypasses = self.checker.find_alternate_routes(sandbox_graph, t)
                for pair, path in bypasses.items():
                    if path:
                        active_bypasses[pair] = path

        elif action == "RATE_LIMITING":
            limit_val = float(params.get("rate_limit_pkts_per_sec", 2.0))
            for t in targets:
                rate_limits[t] = limit_val

        elif action == "POWER_ADJUSTMENT":
            pwr_nodes = candidate.affected_nodes or list(targets)
            boosted_nodes.update(pwr_nodes)
            # Power boost establishes direct bridging links between surviving neighbors
            for i in range(len(pwr_nodes)):
                for j in range(i + 1, len(pwr_nodes)):
                    u, v = pwr_nodes[i], pwr_nodes[j]
                    if sandbox_graph.has_node(u) and sandbox_graph.has_node(v):
                        sandbox_graph.add_edge(u, v, weight=1.0)

        elif action == "COMPOSITE":
            sub_actions = params.get("sub_actions", [])
            # e.g., COMPOSITE_ISOLATE_AND_BRIDGE
            if "NODE_ISOLATION" in sub_actions:
                for t in targets:
                    if sandbox_graph.has_node(t):
                        sandbox_graph.remove_edges_from(list(sandbox_graph.edges(t)))
                        if t in sandbox_nodes:
                            sandbox_nodes[t] = sandbox_nodes[t].model_copy(
                                update={"connection_state": "DISCONNECTED"}
                            )
            if "POWER_ADJUSTMENT" in sub_actions:
                boost_list = params.get("boosted_nodes", candidate.affected_nodes)
                boosted_nodes.update(boost_list)
                for i in range(len(boost_list)):
                    for j in range(i + 1, len(boost_list)):
                        u, v = boost_list[i], boost_list[j]
                        if sandbox_graph.has_node(u) and sandbox_graph.has_node(v):
                            sandbox_graph.add_edge(u, v, weight=1.0)
            if "RATE_LIMITING" in sub_actions:
                limit_val = float(params.get("rate_limit_pkts_per_sec", 2.0))
                for t in targets:
                    rate_limits[t] = limit_val
            if "DYNAMIC_REROUTING" in sub_actions:
                for t in targets:
                    bypasses = self.checker.find_alternate_routes(sandbox_graph, t)
                    for pair, path in bypasses.items():
                        if path:
                            active_bypasses[pair] = path

        # 3. Check Post-Mitigation Graph Connectivity & Partitions
        benign_active_nodes = [
            nid for nid, state in sandbox_nodes.items()
            if nid not in targets and state.connection_state != "DISCONNECTED"
        ]
        if benign_active_nodes:
            benign_subgraph = sandbox_graph.subgraph(benign_active_nodes)
            num_components = nx.number_connected_components(benign_subgraph)
            is_partitioned = (num_components > 1)
        else:
            num_components = 1
            is_partitioned = False

        # 4. Check for Routing Loops (DAG check)
        has_routing_loops = self._check_routing_loops(sandbox_graph, active_bypasses)

        # 5. Forward Simulation Loop over Horizon H
        num_steps = max(1, int(np.ceil(horizon_s / timestep)))
        time_series: Dict[str, List[float]] = {
            "loss": [],
            "latency": [],
            "energy_drain": [],
            "pdr": [],
            "active_node_ratio": [],
        }

        cumulative_energy_drain = 0.0

        for step in range(num_steps):
            t_curr = step * timestep

            # Compute dynamic step performance
            step_loss, step_latency, step_energy, step_active = self._step_simulation(
                sandbox_nodes=sandbox_nodes,
                sandbox_graph=sandbox_graph,
                action=action,
                targets=targets,
                attacks=attacks,
                rate_limits=rate_limits,
                active_bypasses=active_bypasses,
                boosted_nodes=boosted_nodes,
                reboot_duration=reboot_duration,
                t_curr=t_curr,
                timestep=timestep,
                is_partitioned=is_partitioned,
            )

            cumulative_energy_drain += step_energy
            step_pdr = max(0.0, min(1.0, 1.0 - step_loss))

            time_series["loss"].append(float(step_loss))
            time_series["latency"].append(float(step_latency))
            time_series["energy_drain"].append(float(step_energy))
            time_series["pdr"].append(float(step_pdr))
            time_series["active_node_ratio"].append(float(step_active / max(1, total_nodes)))

        # 6. Aggregate Projection Metrics
        proj_pdr = float(np.mean(time_series["pdr"]))
        proj_loss = float(np.mean(time_series["loss"]))
        proj_latency = float(np.mean(time_series["latency"]))
        proj_active_ratio = float(np.mean(time_series["active_node_ratio"]))

        t_end = time.perf_counter()
        sim_latency_ms = (t_end - t_start) * 1000.0

        return SandboxSimulationResult(
            strategy_id=candidate.strategy_id,
            action_type=action,
            horizon_s=horizon_s,
            timestep=timestep,
            projected_pdr=proj_pdr,
            projected_packet_loss=proj_loss,
            projected_avg_latency_ms=proj_latency,
            projected_energy_drain_pct=cumulative_energy_drain,
            projected_active_node_ratio=proj_active_ratio,
            projected_connected_components=num_components,
            is_partitioned=is_partitioned,
            has_routing_loops=has_routing_loops,
            signaling_overhead=signaling_overhead,
            simulation_latency_ms=sim_latency_ms,
            time_series=time_series,
            raw_details={
                "targets": list(targets),
                "boosted_nodes": list(boosted_nodes),
                "num_bypasses": len(active_bypasses),
            }
        )

    def simulate_candidate_ensemble(
        self,
        digital_twin: DigitalTwin,
        candidate: RecoveryCandidate,
        horizon_s: float = 30.0,
        timestep: float = 1.0,
        num_rollouts: int = 15,
        seed: int = 42,
        attack_context: Optional[Dict[int, str]] = None,
    ) -> SandboxSimulationResult:
        """
        Executes a Monte-Carlo ensemble of M stochastic forward rollouts
        incorporating Gaussian wireless fading (Delta_RSSI) and traffic arrival jitter.
        Returns ensemble-averaged trajectories and distribution statistics.
        """
        rng = np.random.default_rng(seed)
        rollout_pdrs: List[float] = []
        rollout_losses: List[float] = []
        rollout_latencies: List[float] = []
        rollout_energies: List[float] = []

        all_pdr_trajectories: List[List[float]] = []
        all_latency_trajectories: List[List[float]] = []
        all_loss_trajectories: List[List[float]] = []

        base_res = self.simulate_candidate(
            digital_twin=digital_twin,
            candidate=candidate,
            horizon_s=horizon_s,
            timestep=timestep,
            attack_context=attack_context,
        )

        num_steps = len(base_res.time_series["loss"])

        for m in range(num_rollouts):
            # Stochastic perturbations per rollout
            fade_jitter = rng.normal(0.0, 0.015, size=num_steps)
            lat_jitter = rng.normal(0.0, 1.2, size=num_steps)
            energy_jitter = rng.normal(0.0, 0.003, size=num_steps)

            rollout_loss_curve = [
                float(np.clip(base_res.time_series["loss"][k] + fade_jitter[k], 0.0, 1.0))
                for k in range(num_steps)
            ]
            rollout_pdr_curve = [
                float(max(0.0, min(1.0, 1.0 - rollout_loss_curve[k])))
                for k in range(num_steps)
            ]
            rollout_lat_curve = [
                float(max(1.0, base_res.time_series["latency"][k] + lat_jitter[k]))
                for k in range(num_steps)
            ]
            rollout_energy = float(max(0.1, base_res.projected_energy_drain_pct + np.sum(energy_jitter)))

            rollout_pdrs.append(float(np.mean(rollout_pdr_curve)))
            rollout_losses.append(float(np.mean(rollout_loss_curve)))
            rollout_latencies.append(float(np.mean(rollout_lat_curve)))
            rollout_energies.append(rollout_energy)

            all_pdr_trajectories.append(rollout_pdr_curve)
            all_latency_trajectories.append(rollout_lat_curve)
            all_loss_trajectories.append(rollout_loss_curve)

        pdr_arr = np.array(rollout_pdrs)
        loss_arr = np.array(rollout_losses)
        lat_arr = np.array(rollout_latencies)
        energy_arr = np.array(rollout_energies)

        # 95% tail Conditional Value at Risk for loss
        worst_loss_threshold = float(np.percentile(loss_arr, 95))
        tail_losses = [l for l in loss_arr if l >= worst_loss_threshold]
        cvar_loss = float(np.mean(tail_losses)) if tail_losses else worst_loss_threshold

        stoch_summary = StochasticSimulationSummary(
            num_rollouts=num_rollouts,
            pdr_mean=float(np.mean(pdr_arr)),
            pdr_std=float(np.std(pdr_arr)),
            pdr_ci95_lower=float(np.percentile(pdr_arr, 2.5)),
            pdr_ci95_upper=float(np.percentile(pdr_arr, 97.5)),
            loss_mean=float(np.mean(loss_arr)),
            loss_std=float(np.std(loss_arr)),
            latency_mean=float(np.mean(lat_arr)),
            latency_std=float(np.std(lat_arr)),
            energy_mean=float(np.mean(energy_arr)),
            cvar_95_loss=cvar_loss,
            cost_j_mean=0.0,
            cost_j_cvar95=0.0,
        )

        # Calculate mean, lower 2-sigma, upper 2-sigma trajectory envelopes
        pdr_traj_matrix = np.array(all_pdr_trajectories)
        pdr_mean_envelope = np.mean(pdr_traj_matrix, axis=0).tolist()
        pdr_upper_envelope = (np.mean(pdr_traj_matrix, axis=0) + 2.0 * np.std(pdr_traj_matrix, axis=0)).tolist()
        pdr_lower_envelope = (np.mean(pdr_traj_matrix, axis=0) - 2.0 * np.std(pdr_traj_matrix, axis=0)).tolist()

        base_res.stochastic_summary = stoch_summary
        base_res.raw_details["ensemble_trajectories"] = {
            "pdr_mean": pdr_mean_envelope,
            "pdr_upper_2sigma": pdr_upper_envelope,
            "pdr_lower_2sigma": pdr_lower_envelope,
            "all_pdr_trajectories": all_pdr_trajectories,
            "all_loss_trajectories": all_loss_trajectories,
            "all_latency_trajectories": all_latency_trajectories,
        }

        return base_res

    def compute_adaptive_horizon(
        self,
        graph: nx.Graph,
        attack_context: Optional[Dict[int, str]] = None,
        base_reboot_duration: float = 8.0,
    ) -> float:
        """
        Dynamically adapts lookahead horizon H* based on network topology diameter and attack urgency.
        """
        if graph.number_of_nodes() <= 1:
            diameter = 1
        else:
            try:
                components = list(nx.connected_components(graph))
                if components:
                    largest = max(components, key=len)
                    sub = graph.subgraph(largest)
                    diameter = nx.diameter(sub) if len(largest) > 1 else 1
                else:
                    diameter = 1
            except Exception:
                diameter = 2

        attack_types = list((attack_context or {}).values())
        if "dos" in attack_types and len(attack_types) == 1:
            # Urgent buffer bloat mitigation: quick 15-20s horizon
            horizon = max(15.0, diameter * 5.0)
        elif "node_failure" in attack_types or "compromised_node" in attack_types:
            # Need to capture reboot recovery window + alternate route convergence
            horizon = max(30.0, base_reboot_duration * 2.5 + diameter * 3.5)
        else:
            horizon = 30.0

        return float(np.clip(horizon, 15.0, 60.0))

    def _step_simulation(

        self,
        sandbox_nodes: Dict[int, TwinNodeState],
        sandbox_graph: nx.Graph,
        action: RecoveryActionType,
        targets: Set[int],
        attacks: Dict[int, str],
        rate_limits: Dict[int, float],
        active_bypasses: Dict[Tuple[int, int], List[int]],
        boosted_nodes: Set[int],
        reboot_duration: float,
        t_curr: float,
        timestep: float,
        is_partitioned: bool,
    ) -> Tuple[float, float, float, int]:
        """
        Advances the virtual sandbox by one timestep and calculates projected metrics.
        """
        # Base nominal background metrics
        step_losses: List[float] = []
        step_latencies: List[float] = []
        step_energy_total: float = 0.0
        active_nodes_count: int = 0

        # Account for partition penalty: if partition occurs, severed nodes suffer high packet loss
        partition_loss_multiplier = 2.5 if is_partitioned else 1.0

        for nid, state in sandbox_nodes.items():
            is_target = nid in targets
            is_boosted = nid in boosted_nodes
            attack_type = attacks.get(nid, "normal")

            # 1. Check Node Online / Reboot Status
            is_in_reboot = (action == "NODE_REBOOT" and is_target and t_curr < reboot_duration)
            is_isolated = (action == "NODE_ISOLATION" and is_target) or (
                action == "COMPOSITE" and is_target and "NODE_ISOLATION" in getattr(state, "sub_actions", ["NODE_ISOLATION"])
            )

            if is_isolated:
                # Isolated malicious node: cannot route or communicate
                step_losses.append(0.0)  # No legitimate traffic expected from quarantined isolated node
                step_latencies.append(self.base_nominal_latency_ms)
                # Idle baseline energy
                step_energy_total += 0.005 * timestep
                continue

            if is_in_reboot:
                # During reboot window: offline, buffer flushing, transient disruption
                step_losses.append(0.35)  # Transit packets dropped during reboot
                step_latencies.append(self.base_nominal_latency_ms * 2.0)
                # Reboot power spike
                step_energy_total += 0.15 * timestep
                continue

            # Node is active
            active_nodes_count += 1
            node_loss = self.base_nominal_loss_ratio * partition_loss_multiplier
            node_lat = self.base_nominal_latency_ms
            node_energy = self.base_nominal_energy_drain_per_s * timestep

            # 2. Evaluate Mitigation vs. Attack Dynamics
            if is_target:
                if action == "NO_ACTION":
                    # Attack proceeds unmitigated
                    if attack_type == "dos":
                        node_loss = 0.45
                        node_lat = 72.0
                        node_energy = 0.18 * timestep
                    elif attack_type == "compromised_node":
                        node_loss = 0.75  # 75% selective drop
                        node_lat = 18.0
                        node_energy = 0.04 * timestep
                    elif attack_type == "node_failure":
                        node_loss = 0.95
                        node_lat = 150.0
                        node_energy = 0.0

                elif action == "RATE_LIMITING" or (action == "COMPOSITE" and nid in rate_limits):
                    # Rate limiting throttles flooding source
                    cap = rate_limits.get(nid, 2.0)
                    # Relieves buffer congestion
                    node_loss = 0.04 * partition_loss_multiplier
                    node_lat = 15.0
                    node_energy = 0.04 * timestep

                elif action == "NODE_REBOOT" and t_curr >= reboot_duration:
                    # Post-reboot: clean node state, attack evicted!
                    node_loss = self.base_nominal_loss_ratio
                    node_lat = self.base_nominal_latency_ms
                    node_energy = self.base_nominal_energy_drain_per_s * timestep

            else:
                # Non-target node dynamics
                if action == "NO_ACTION":
                    # Non-targets suffer collateral damage from active attacks
                    if any(att == "dos" for att in attacks.values()):
                        node_loss = min(0.40, node_loss + 0.20)
                        node_lat += 25.0
                    elif any(att == "compromised_node" for att in attacks.values()):
                        node_loss = min(0.60, node_loss + 0.30)

                elif action == "DYNAMIC_REROUTING" or (action == "COMPOSITE" and active_bypasses):
                    # Rerouted traffic incurs small path-stretch latency (+4ms per bypass)
                    # but achieves clean delivery (drops eliminated)
                    if active_bypasses:
                        node_lat += 4.5
                        node_loss = self.base_nominal_loss_ratio * 1.2
                        node_energy += 0.01 * timestep

                if is_boosted:
                    # Increased Tx power consumes slightly more battery
                    node_energy += 0.035 * timestep
                    # Improves RSSI and reduces loss across long links
                    node_loss = max(0.01, node_loss * 0.7)

            step_losses.append(float(np.clip(node_loss, 0.0, 1.0)))
            step_latencies.append(float(max(1.0, node_lat)))
            step_energy_total += float(node_energy)

        # Compute aggregate averages for this timestep
        avg_loss = float(np.mean(step_losses)) if step_losses else 0.0
        avg_lat = float(np.mean(step_latencies)) if step_latencies else self.base_nominal_latency_ms

        return avg_loss, avg_lat, step_energy_total, active_nodes_count

    def _check_routing_loops(
        self,
        graph: nx.Graph,
        active_bypasses: Dict[Tuple[int, int], List[int]],
    ) -> bool:
        """
        Validates whether installed bypass routes form directed forwarding cycles (loops).
        Constructs a directed routing dependency graph and checks DAG property.
        """
        if not active_bypasses:
            return False

        dg = nx.DiGraph()
        for (src, dst), path in active_bypasses.items():
            if path and len(path) >= 2:
                for i in range(len(path) - 1):
                    dg.add_edge(path[i], path[i + 1])

        # A loop exists if the directed graph is NOT a DAG (contains cycles)
        try:
            return not nx.is_directed_acyclic_graph(dg)
        except Exception:
            return False

    def _compute_signaling_overhead(
        self,
        action: RecoveryActionType,
        candidate: RecoveryCandidate,
        graph: nx.Graph,
    ) -> float:
        """
        Calculates signaling / control message overhead required to deploy strategy candidate.
        """
        num_targets = len(candidate.target_nodes)
        num_affected = len(candidate.affected_nodes)

        if action == "NO_ACTION":
            return 0.0
        elif action == "RATE_LIMITING":
            return float(num_targets * 1.0)
        elif action == "DYNAMIC_REROUTING":
            return float(num_affected * 2.0 + num_targets * 1.0)
        elif action == "NODE_ISOLATION":
            # 1 broadcast or isolate frame to each neighbor link
            total_edges = sum(graph.degree(t) for t in candidate.target_nodes if t in graph)
            return float(max(1.0, total_edges))
        elif action == "NODE_REBOOT":
            return float(num_targets * 2.0)  # Reboot trigger + restart acknowledgment
        elif action == "POWER_ADJUSTMENT":
            return float(num_affected * 1.5)
        elif action == "COMPOSITE":
            return float(num_targets * 2.0 + num_affected * 2.5)
        return 1.0

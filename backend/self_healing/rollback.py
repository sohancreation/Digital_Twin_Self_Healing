"""
Automated Rollback Manager for Phase 9.
Captures pre-actuation system snapshots and automatically executes inverse
compensation commands when closed-loop verification fails or network partitions occur.
"""

import time
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple
import networkx as nx

from .models import (
    RollbackSnapshot,
    RollbackExecutionResult,
    ActuationCommand,
    CommandAck,
)
from .actuator import NetworkActuator


class RollbackManager:
    """
    Guarantees operational safety by maintaining lossless rollback capability.
    Captures snapshot state before actuation and restores the network upon verification failure.
    """

    def __init__(self):
        self.snapshots: Dict[str, RollbackSnapshot] = {}
        self.rollback_history: List[RollbackExecutionResult] = []

    def capture_snapshot(
        self,
        actuator: NetworkActuator,
        current_time: float,
    ) -> RollbackSnapshot:
        """
        Records full pre-actuation configuration of topology, routes, rates, and node states.
        """
        snapshot_id = f"SNAP_{int(current_time)}_{uuid.uuid4().hex[:6]}"

        edges: List[Tuple[int, int]] = []
        node_states: Dict[int, Dict[str, Any]] = {}

        if actuator.simulator and actuator.simulator.topology:
            g = actuator.simulator.topology.graph
            edges = [(int(u), int(v)) for u, v in g.edges()]

        if actuator.simulator and actuator.simulator.nodes:
            for nid, node in actuator.simulator.nodes.items():
                node_states[nid] = {
                    "is_alive": node.is_alive,
                    "is_failed": getattr(node, "_is_failed", False),
                    "is_isolated": getattr(node, "_is_isolated", False),
                    "neighbors": list(node.neighbors),
                }

        snap = RollbackSnapshot(
            snapshot_id=snapshot_id,
            timestamp=current_time,
            isolated_nodes=list(actuator.isolated_nodes),
            rate_limits=dict(actuator.rate_limits),
            installed_routes={f"{k[0]}_{k[1]}": v for k, v in actuator.route_overrides.items()},
            power_boosts=dict(actuator.power_boosts),
            topology_edges=edges,
            node_states_summary=node_states,
        )

        self.snapshots[snapshot_id] = snap
        return snap

    def execute_rollback(
        self,
        snapshot: RollbackSnapshot,
        actuator: NetworkActuator,
        current_time: float,
        trigger_reason: str = "Verification failed",
    ) -> RollbackExecutionResult:
        """
        Executes inverse compensation actions to restore network to pre-actuation state.
        """
        t_start = time.perf_counter()
        restored_items: List[str] = []
        commands_dispatched = 0

        # 1. Restore severed topology edges
        if actuator.simulator and actuator.simulator.topology:
            g = actuator.simulator.topology.graph
            target_edges = set(snapshot.topology_edges)
            current_edges = set((int(u), int(v)) for u, v in g.edges())

            # Edges to restore
            edges_to_restore = target_edges - current_edges
            for u, v in edges_to_restore:
                g.add_edge(u, v)
                commands_dispatched += 1
                if u in actuator.simulator.nodes:
                    if v not in actuator.simulator.nodes[u].neighbors:
                        actuator.simulator.nodes[u].neighbors.append(v)
                if v in actuator.simulator.nodes:
                    if u not in actuator.simulator.nodes[v].neighbors:
                        actuator.simulator.nodes[v].neighbors.append(u)

            if edges_to_restore:
                restored_items.append(f"Restored {len(edges_to_restore)} severed topology edges")

        # 2. Restore node isolation flags
        pre_isolated = set(snapshot.isolated_nodes)
        un_isolated = actuator.isolated_nodes - pre_isolated
        for nid in un_isolated:
            if actuator.simulator and nid in actuator.simulator.nodes:
                node = actuator.simulator.nodes[nid]
                node.is_alive = True
                node._is_isolated = False
                node._is_failed = False
            commands_dispatched += 1

        actuator.isolated_nodes = set(snapshot.isolated_nodes)
        actuator.severed_edges.clear()
        if un_isolated:
            restored_items.append(f"Un-isolated falsely quarantined nodes: {list(un_isolated)}")

        # 3. Restore rate limits
        actuator.rate_limits = dict(snapshot.rate_limits)
        if actuator.simulator and actuator.simulator.nodes:
            for nid, node in actuator.simulator.nodes.items():
                if nid in actuator.rate_limits:
                    node._rate_limit_token_rate = actuator.rate_limits[nid]
                else:
                    node._rate_limit_token_rate = None

        restored_items.append("Reverted rate limiting policies")

        # 4. Restore route overrides
        actuator.route_overrides.clear()
        for k_str, path in snapshot.installed_routes.items():
            parts = k_str.split("_")
            if len(parts) == 2:
                src, dst = int(parts[0]), int(parts[1])
                actuator.route_overrides[(src, dst)] = path

        restored_items.append("Reverted dynamic routing tables to pre-actuation bypass paths")

        # 5. Restore power boosts
        actuator.power_boosts = dict(snapshot.power_boosts)
        restored_items.append("Reverted Tx power levels")

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        res = RollbackExecutionResult(
            snapshot_id=snapshot.snapshot_id,
            timestamp=current_time,
            success=True,
            restored_components=restored_items,
            rollback_commands_dispatched=commands_dispatched,
            elapsed_ms=round(elapsed_ms, 2),
            message=f"Rollback successfully restored state ({trigger_reason}).",
        )
        self.rollback_history.append(res)
        return res

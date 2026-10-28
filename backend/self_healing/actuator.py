"""
Network Actuator for Phase 9.
Executes physical/simulated actuation commands directly on the NetworkSimulator,
IoTNode models, and NetworkTopology graph to realize autonomous self-healing.
"""

from typing import Dict, List, Optional, Tuple, Set, Any
import numpy as np
import networkx as nx

from ..simulation.simulator import NetworkSimulator
from ..simulation.node import IoTNode
from .models import ActuationCommand, CommandAck, CommandStatus


class NetworkActuator:
    """
    Direct actuation interface translating downlink ActuationCommands into
    runtime modifications on the NetworkSimulator, topology, and node dynamics.
    """

    def __init__(self, simulator: Optional[NetworkSimulator] = None):
        self.simulator = simulator

        # Actuation state tracking
        self.isolated_nodes: Set[int] = set()
        self.rate_limits: Dict[int, float] = {}  # node_id -> max_pkts_per_sec
        self.route_overrides: Dict[Tuple[int, int], List[int]] = {}  # (src, dst) -> bypass_path
        self.rebooting_nodes: Dict[int, float] = {}  # node_id -> restore_timestamp
        self.power_boosts: Dict[int, float] = {}  # node_id -> boost_dbm
        self.severed_edges: Set[Tuple[int, int]] = set()

    def bind_simulator(self, simulator: NetworkSimulator) -> None:
        """Binds actuator to target simulator instance."""
        self.simulator = simulator

    def execute_command(self, cmd: ActuationCommand, current_time: float) -> CommandAck:
        """
        Executes an individual ActuationCommand against the bound simulator.
        Returns execution acknowledgment.
        """
        if self.simulator is None:
            return CommandAck(
                command_id=cmd.command_id,
                node_id=cmd.target_node,
                status="FAILED",
                round_trip_ms=0.0,
                timestamp=current_time,
                message="No simulator bound to actuator.",
            )

        cmd_type = cmd.command_type
        target = cmd.target_node
        params = cmd.parameters or {}

        try:
            if cmd_type == "ISOLATE_NODE":
                self._apply_isolation(target)
                msg = f"Node {target} isolated: links severed, routing disabled."

            elif cmd_type == "SET_RATE_LIMIT":
                rate_cap = float(params.get("token_rate_pkts_s", 2.0))
                self._apply_rate_limit(target, rate_cap)
                msg = f"Node {target} ingress rate-limited to {rate_cap} pkts/s."

            elif cmd_type == "REROUTE_TRAFFIC":
                bypasses = params.get("installed_bypasses", {})
                remove_neighbors = params.get("remove_neighbors", [])
                self._apply_rerouting(target, bypasses, remove_neighbors)
                msg = f"Node {target} updated with alternate bypass routes."

            elif cmd_type == "REBOOT_NODE":
                duration = float(params.get("duration_s", 8.0))
                self._apply_reboot(target, current_time, duration)
                msg = f"Node {target} reboot initiated: downtime {duration}s."

            elif cmd_type == "ADJUST_TX_POWER":
                boost = float(params.get("power_boost_dbm", 4.0))
                self._apply_power_boost(target, boost)
                msg = f"Node {target} Tx power boosted by +{boost} dBm."

            elif cmd_type == "ROLLBACK_ACTION":
                # Special rollback execution handled via RollbackManager
                msg = f"Rollback action applied for node {target}."

            else:
                msg = f"Unknown command type {cmd_type} ignored."

            cmd.status = "APPLIED"
            return CommandAck(
                command_id=cmd.command_id,
                node_id=target,
                status="APPLIED",
                round_trip_ms=12.0,
                timestamp=current_time,
                message=msg,
            )

        except Exception as ex:
            cmd.status = "FAILED"
            return CommandAck(
                command_id=cmd.command_id,
                node_id=target,
                status="FAILED",
                round_trip_ms=0.0,
                timestamp=current_time,
                message=f"Actuation exception: {str(ex)}",
            )

    def _apply_isolation(self, target: int) -> None:
        """Severs all topology links to the target node and marks it isolated."""
        self.isolated_nodes.add(target)
        if self.simulator and self.simulator.topology and self.simulator.topology.graph:
            g = self.simulator.topology.graph
            if g.has_node(target):
                neighbors = list(g.neighbors(target))
                for n in neighbors:
                    g.remove_edge(target, n)
                    edge_tuple = (min(target, n), max(target, n))
                    self.severed_edges.add(edge_tuple)
                    # Also update neighbor lists on IoTNode instances
                    if n in self.simulator.nodes:
                        cur_neighbors = self.simulator.nodes[n].neighbors
                        if target in cur_neighbors:
                            cur_neighbors.remove(target)

        # Mark target node as isolated in its internal state
        if self.simulator and target in self.simulator.nodes:
            self.simulator.nodes[target].is_alive = False
            self.simulator.nodes[target]._is_isolated = True

    def _apply_rate_limit(self, target: int, rate_cap: float) -> None:
        """Sets token-bucket rate cap on target node."""
        self.rate_limits[target] = rate_cap
        if self.simulator and target in self.simulator.nodes:
            node = self.simulator.nodes[target]
            node._rate_limit_token_rate = rate_cap
            node._token_bucket_capacity = 10.0
            node._token_bucket_tokens = 10.0

    def _apply_rerouting(
        self,
        node_id: int,
        bypasses: Dict[Any, Any],
        remove_neighbors: List[int],
    ) -> None:
        """Installs dynamic path overrides and drops removed neighbors from routing tables."""
        if remove_neighbors and self.simulator and self.simulator.topology:
            g = self.simulator.topology.graph
            for rm in remove_neighbors:
                if g.has_edge(node_id, rm):
                    g.remove_edge(node_id, rm)
                    self.severed_edges.add((min(node_id, rm), max(node_id, rm)))

        for pair_str, path in bypasses.items():
            if isinstance(path, list) and len(path) >= 2:
                src, dst = path[0], path[-1]
                self.route_overrides[(src, dst)] = path

    def _apply_reboot(self, target: int, current_time: float, duration: float) -> None:
        """Triggers soft reboot cycle: temporary downtime, flush state, evict attacks."""
        self.rebooting_nodes[target] = current_time + duration
        if self.simulator and target in self.simulator.nodes:
            node = self.simulator.nodes[target]
            # Offline during reboot
            node._is_failed = True
            node._reboot_finish_time = current_time + duration
            # Flush queue
            if hasattr(node, "queue"):
                node.queue.clear()
            node.queue_length = 0

    def _apply_power_boost(self, target: int, boost_dbm: float) -> None:
        """Boosts Tx power, creating or strengthening bridging communication links."""
        self.power_boosts[target] = boost_dbm
        if self.simulator and self.simulator.topology:
            # Connect target to 2-hop neighbors or extend radius
            g = self.simulator.topology.graph
            pos = self.simulator.topology.positions
            if target in pos:
                target_pos = pos[target]
                # Find closest non-neighbor within extended radius
                for other, o_pos in pos.items():
                    if other != target and not g.has_edge(target, other):
                        dist = float(np.linalg.norm(np.array(target_pos) - np.array(o_pos)))
                        # Boosted range threshold ~35.0
                        if dist <= 38.0:
                            g.add_edge(target, other, weight=dist)
                            if target in self.simulator.nodes:
                                self.simulator.nodes[target].neighbors.append(other)
                            if other in self.simulator.nodes:
                                self.simulator.nodes[other].neighbors.append(target)

    def pre_step_maintenance(self, current_time: float) -> None:
        """
        Hook called at the start of each simulation step to manage reboot recoveries
        and maintain active actuation constraints.
        """
        if not self.simulator:
            return

        # Check completed reboots
        restored = []
        for nid, restore_time in list(self.rebooting_nodes.items()):
            if current_time >= restore_time:
                restored.append(nid)
                if nid in self.simulator.nodes:
                    node = self.simulator.nodes[nid]
                    node._is_failed = False
                    node.is_alive = True
                    # Evict compromise / attack hook
                    if hasattr(self.simulator, "attack_injector") and self.simulator.attack_injector:
                        # Clear attack active status on node
                        if hasattr(self.simulator.attack_injector, "active_attacks"):
                            self.simulator.attack_injector.active_attacks.pop(nid, None)

        for nid in restored:
            self.rebooting_nodes.pop(nid, None)

    def get_route(self, src: int, dst: int, default_path: Optional[List[int]] = None) -> Optional[List[int]]:
        """Returns installed bypass route if present, else default path."""
        if (src, dst) in self.route_overrides:
            return self.route_overrides[(src, dst)]
        return default_path

    def filter_traffic(self, node_id: int, incoming_packets: int) -> int:
        """Applies active token-bucket rate limiting to incoming packet flow."""
        if node_id in self.rate_limits:
            cap = int(np.round(self.rate_limits[node_id]))
            return min(incoming_packets, max(1, cap))
        return incoming_packets

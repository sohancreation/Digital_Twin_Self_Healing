"""
Node Failure / Crash fault injection model.
Simulates unannounced node failure, hardware crash, or loss of connectivity.
The node enters DISCONNECTED state, stops traffic generation/forwarding, and causes
neighboring topology degradation. Recovers post-window if battery is available.
"""

from typing import Dict, Any, Tuple
from .base import BaseAttack


class NodeFailureAttack(BaseAttack):
    """
    Implements a temporary or permanent node failure / crash scenario.
    During the attack window, target node is marked DISCONNECTED, ceases transmission,
    and cannot forward traffic.
    """

    def pre_routing(self, current_time: float, nodes: Dict[int, Any], topology: Any) -> None:
        for node_id in self.config.target_nodes:
            node = nodes.get(node_id)
            if node is None:
                continue

            if self.is_active(current_time):
                # Temporarily disable node from participating in routing
                setattr(node, "_is_failed", True)
            else:
                # Clear failure flag if attack window has elapsed
                if getattr(node, "_is_failed", False):
                    setattr(node, "_is_failed", False)

    def perturb_traffic(
        self,
        current_time: float,
        node_id: int,
        inbound_forward_packets: int,
        timestep: float
    ) -> Tuple[int, float]:
        if self.is_active(current_time) and self.is_target(node_id):
            return 0, 1.0
        return inbound_forward_packets, 0.0

    def post_step(self, current_time: float, node_id: int, record: Any) -> Any:
        if self.is_active(current_time) and self.is_target(node_id):
            record.connection_state = "DISCONNECTED"
            record.routing_state = "IDLE"
            record.packet_rate = 0.0
            record.forwarding_rate = 0.0
            record.packet_loss = 1.0
            record.latency = 0.0
            record.cpu = 0.0
            record.memory = 0.0

        return record

"""
Compromised Node attack model.
Simulates an internally compromised/malicious IoT node performing selective packet dropping
(gray-hole / selective forwarding attack).
"""

from typing import Tuple, Any
import numpy as np
from .base import BaseAttack


class CompromisedNodeAttack(BaseAttack):
    """
    Implements selective packet dropping (gray-hole attack) on compromised node(s).
    Parameter `intensity` represents the packet-drop probability in [0.0, 1.0] (e.g. 0.5 = 50% drop rate).
    """

    def __init__(self, config, rng=None):
        super().__init__(config, rng)
        # Track last drop ratio applied per node for post-step telemetry adjustment
        self.last_drop_ratios = {}

    def perturb_traffic(
        self,
        current_time: float,
        node_id: int,
        inbound_forward_packets: int,
        timestep: float
    ) -> Tuple[int, float]:
        if not self.is_active(current_time) or not self.is_target(node_id):
            return inbound_forward_packets, 0.0

        p_drop = float(np.clip(self.intensity, 0.0, 1.0))

        if inbound_forward_packets > 0:
            # Draw actual dropped packets from binomial distribution using dedicated attack RNG
            dropped = int(self.rng.binomial(inbound_forward_packets, p_drop))
            surviving = inbound_forward_packets - dropped
            actual_ratio = float(dropped / inbound_forward_packets)
        else:
            surviving = 0
            actual_ratio = p_drop

        self.last_drop_ratios[node_id] = actual_ratio
        return surviving, actual_ratio

    def post_step(self, current_time: float, node_id: int, record: Any) -> Any:
        if not self.is_active(current_time) or not self.is_target(node_id):
            return record

        drop_ratio = self.last_drop_ratios.get(node_id, self.intensity)
        if drop_ratio > 0.0:
            # Elevate packet loss to account for malicious selective drops:
            # P_total = 1 - (1 - P_baseline) * (1 - P_malicious)
            combined_loss = 1.0 - (1.0 - record.packet_loss) * (1.0 - drop_ratio)
            record.packet_loss = float(np.clip(combined_loss, 0.0, 1.0))
            if record.packet_loss > 0.4:
                record.connection_state = "DEGRADED"

        return record

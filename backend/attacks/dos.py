"""
Denial of Service (DoS) / Packet Flooding attack model.
Floods target node(s) with an influx of malicious packets, naturally driving
buffer overflow, drop-tail packet loss, elevated latency, high CPU load, and energy drain.
"""

from typing import Tuple
import numpy as np
from .base import BaseAttack


class DoSAttack(BaseAttack):
    """
    Implements a packet flooding DoS attack.
    Parameter `intensity` represents additional flood packets per second injected into the target node.
    """

    def perturb_traffic(
        self,
        current_time: float,
        node_id: int,
        inbound_forward_packets: int,
        timestep: float
    ) -> Tuple[int, float]:
        if not self.is_active(current_time) or not self.is_target(node_id):
            return inbound_forward_packets, 0.0

        # Injected flooding packets according to configured intensity (pkts/sec)
        # Uses dedicated attack RNG to add stochastic jitter if desired, or deterministic rounding
        jitter = self.rng.normal(0.0, 0.2 * self.intensity) if self.intensity > 1.0 else 0.0
        effective_rate = max(1.0, self.intensity + jitter)
        flood_packets = int(np.round(effective_rate * timestep))

        modified_inbound = inbound_forward_packets + flood_packets
        return modified_inbound, 0.0

"""
Route Flapping and Oscillation Hysteresis Damper for Phase 9.
Implements exponential hold-down filtering (analogous to BGP RFC 2439 / RPL hysteresis)
to prevent route thrashing, control message storms, and buffer bloat during
evasive on-off cycling cyber-physical attacks:
  Omega_flap(i, t) = sum_{k: t_k <= t} exp(-lambda_decay * (t - t_k))
"""

from typing import Dict, List, Optional, Any, Tuple
import math

from .models import FlappingState


class RouteFlappingDamper:
    """
    Suppresses rapid route flapping and quarantine oscillations using an
    exponential decay hysteresis filter.
    """

    def __init__(
        self,
        decay_rate: float = 0.15,
        suppress_threshold: float = 2.5,
        reuse_threshold: float = 0.8,
        min_hold_down_s: float = 8.0,
        penalty_per_switch: float = 1.0,
    ):
        self.decay_rate = decay_rate
        self.suppress_threshold = suppress_threshold
        self.reuse_threshold = reuse_threshold
        self.min_hold_down_s = min_hold_down_s
        self.penalty_per_switch = penalty_per_switch

        # History per node/route ID: List of timestamps
        self._switch_timestamps: Dict[int, List[float]] = {}
        # Hold down tracking
        self._hold_down_until: Dict[int, float] = {}
        self._is_held_down: Dict[int, bool] = {}

    def reset(self) -> None:
        """Resets all flapping tracking states."""
        self._switch_timestamps.clear()
        self._hold_down_until.clear()
        self._is_held_down.clear()

    def get_oscillation_index(self, node_id: int, current_time: float) -> float:
        """
        Calculates the instantaneous decayed oscillation index Omega(i, t).
        """
        timestamps = self._switch_timestamps.get(node_id, [])
        if not timestamps:
            return 0.0

        omega = 0.0
        for tk in timestamps:
            if tk <= current_time:
                dt = current_time - tk
                omega += self.penalty_per_switch * math.exp(-self.decay_rate * dt)
        return float(round(omega, 4))

    def record_switch(self, node_id: int, timestamp: float) -> FlappingState:
        """
        Records a route switch event and updates hysteresis suppression status.
        """
        if node_id not in self._switch_timestamps:
            self._switch_timestamps[node_id] = []
        self._switch_timestamps[node_id].append(timestamp)

        omega = self.get_oscillation_index(node_id, timestamp)
        is_held = self._is_held_down.get(node_id, False)
        until = self._hold_down_until.get(node_id, 0.0)

        # Suppression trigger
        if omega >= self.suppress_threshold:
            is_held = True
            until = max(until, timestamp + self.min_hold_down_s)
            self._is_held_down[node_id] = True
            self._hold_down_until[node_id] = until

        return FlappingState(
            node_id=node_id,
            oscillation_index=omega,
            last_switch_timestamp=timestamp,
            switch_count=len(self._switch_timestamps[node_id]),
            is_held_down=is_held,
            hold_down_until=until,
        )

    def is_suppressed(self, node_id: int, current_time: float) -> bool:
        """
        Checks whether a route or node is actively held down (damped).
        Auto-releases hold down if both timer has elapsed and Omega < reuse_threshold.
        """
        if not self._is_held_down.get(node_id, False):
            return False

        until = self._hold_down_until.get(node_id, 0.0)
        omega = self.get_oscillation_index(node_id, current_time)

        if current_time >= until and omega <= self.reuse_threshold:
            # Hysteresis decay allows unsuppressing
            self._is_held_down[node_id] = False
            return False

        return True

    def filter_route_change(self, node_id: int, current_time: float) -> bool:
        """
        Decides whether an actuation route reconfiguration should be permitted.
        Returns True if permitted (not flapping), False if suppressed.
        """
        if self.is_suppressed(node_id, current_time):
            return False

        # Record this switch and check if it triggers suppression
        state = self.record_switch(node_id, current_time)
        return not state.is_held_down

    def get_flapping_state(self, node_id: int, current_time: float) -> FlappingState:
        """Returns the current FlappingState for a node."""
        omega = self.get_oscillation_index(node_id, current_time)
        is_held = self.is_suppressed(node_id, current_time)
        until = self._hold_down_until.get(node_id, 0.0)
        history = self._switch_timestamps.get(node_id, [])
        last_t = history[-1] if history else 0.0

        return FlappingState(
            node_id=node_id,
            oscillation_index=omega,
            last_switch_timestamp=last_t,
            switch_count=len(history),
            is_held_down=is_held,
            hold_down_until=until,
        )

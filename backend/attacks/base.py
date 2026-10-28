"""
Abstract base class for cyberattack and fault models.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
import numpy as np
from .models import AttackConfig


class BaseAttack(ABC):
    """
    Abstract interface for cyberattacks and network failure models.
    Operates on underlying simulation dynamics before or during node steps.
    """

    def __init__(self, config: AttackConfig, rng: Optional[np.random.Generator] = None):
        self.config = config
        self.rng = rng if rng is not None else np.random.default_rng(1001)

    @property
    def attack_id(self) -> str:
        return self.config.attack_id

    @property
    def attack_type(self) -> str:
        return self.config.attack_type

    @property
    def intensity(self) -> float:
        return self.config.intensity

    def is_active(self, current_time: float) -> bool:
        """
        Determines whether the attack is active at current_time.
        Follows standard boundary convention: start_time <= current_time < end_time.
        """
        if not self.config.enabled:
            return False
        return self.config.start_time <= current_time < self.config.end_time

    def is_target(self, node_id: int) -> bool:
        """Checks if a node is an explicit target of this attack."""
        return node_id in self.config.target_nodes

    def pre_routing(self, current_time: float, nodes: Dict[int, Any], topology: Any) -> None:
        """Hook executed prior to multi-hop route computation (e.g. for node failure)."""
        pass

    def perturb_traffic(
        self,
        current_time: float,
        node_id: int,
        inbound_forward_packets: int,
        timestep: float
    ) -> Tuple[int, float]:
        """
        Applies attack perturbation to traffic.
        Returns:
            (modified_inbound_forward_packets, malicious_drop_ratio)
        """
        return inbound_forward_packets, 0.0

    def post_step(self, current_time: float, node_id: int, record: Any) -> Any:
        """Hook executed after TelemetryRecord is generated for any final telemetry adjustments."""
        return record

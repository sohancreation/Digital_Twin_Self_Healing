"""
Deterministic Attack Scheduler.
Manages the temporal activation, termination, and query interfaces for scheduled attacks.
"""

from typing import List, Optional, Union, Dict
import numpy as np
from .models import AttackConfig
from .base import BaseAttack
from .dos import DoSAttack
from .compromised_node import CompromisedNodeAttack
from .node_failure import NodeFailureAttack


class AttackScheduler:
    """
    Coordinates scheduled attacks across the simulation timeline.
    Deterministic boundary condition: start_time <= current_time < end_time.
    """

    def __init__(self, attack_seed: int = 1001):
        self.attack_seed = attack_seed
        self.rng = np.random.default_rng(attack_seed)
        self.attacks: List[BaseAttack] = []

    def create_attack(self, config: AttackConfig) -> BaseAttack:
        """Factory method instantiating the concrete attack class for a given configuration."""
        atype = config.attack_type
        if atype == "dos":
            return DoSAttack(config=config, rng=self.rng)
        elif atype == "compromised_node":
            return CompromisedNodeAttack(config=config, rng=self.rng)
        elif atype == "node_failure":
            return NodeFailureAttack(config=config, rng=self.rng)
        elif atype == "normal":
            # Normal baseline sentinel
            return DoSAttack(config=config, rng=self.rng)
        else:
            raise ValueError(f"Unsupported attack type: {atype}")

    def add_attack(self, attack_or_config: Union[AttackConfig, BaseAttack, Dict]) -> BaseAttack:
        """Schedules an attack from an AttackConfig, dict, or BaseAttack instance."""
        if isinstance(attack_or_config, dict):
            cfg = AttackConfig(**attack_or_config)
            attack = self.create_attack(cfg)
        elif isinstance(attack_or_config, AttackConfig):
            attack = self.create_attack(attack_or_config)
        elif isinstance(attack_or_config, BaseAttack):
            attack = attack_or_config
        else:
            raise TypeError(f"Invalid attack specification: {type(attack_or_config)}")

        self.attacks.append(attack)
        return attack

    def get_active_attacks(self, current_time: float) -> List[BaseAttack]:
        """Returns all attacks currently active at current_time (start <= t < end)."""
        return [atk for atk in self.attacks if atk.is_active(current_time)]

    def get_attack_for_node(self, node_id: int, current_time: float) -> Optional[BaseAttack]:
        """
        Returns the active attack targeting node_id at current_time, or None if benign.
        If multiple attacks target the same node simultaneously, returns the first active.
        """
        for atk in self.attacks:
            if atk.is_active(current_time) and atk.is_target(node_id):
                return atk
        return None

    def has_active_attacks(self, current_time: float) -> bool:
        """Returns True if any scheduled attack is active at current_time."""
        return any(atk.is_active(current_time) for atk in self.attacks)

    def clear(self) -> None:
        """Clears all scheduled attacks."""
        self.attacks.clear()
        self.rng = np.random.default_rng(self.attack_seed)

"""
Attack Injector coordinator.
Integrates scheduled attacks with the IoT network simulation step pipeline
and records ground-truth annotations without contaminating physical telemetry.
"""

from typing import List, Dict, Optional, Union, Tuple, Any
from pathlib import Path
import pandas as pd
from backend.simulation.telemetry import TelemetryRecord
from .models import AttackConfig
from .base import BaseAttack
from .scheduler import AttackScheduler
from .ground_truth import GroundTruthRecorder


class AttackInjector:
    """
    Coordinates cyberattack execution and ground-truth recording alongside the simulator.
    Preserves exact physical causality and backward compatibility.
    """

    def __init__(self, attack_seed: int = 1001, scheduler: Optional[AttackScheduler] = None):
        self.attack_seed = attack_seed
        self.scheduler = scheduler if scheduler is not None else AttackScheduler(attack_seed=attack_seed)
        self.ground_truth = GroundTruthRecorder()

    def add_attack(self, attack_or_config: Union[AttackConfig, BaseAttack, Dict]) -> BaseAttack:
        """Schedules a cyberattack scenario."""
        return self.scheduler.add_attack(attack_or_config)

    def pre_routing(self, current_time: float, nodes: Dict[int, Any], topology: Any) -> None:
        """Invoked prior to route computation to apply pre-routing perturbations (e.g. node failure)."""
        active_attacks = self.scheduler.get_active_attacks(current_time)
        for atk in active_attacks:
            atk.pre_routing(current_time, nodes, topology)

    def perturb_traffic(
        self,
        current_time: float,
        node_id: int,
        inbound_forward_packets: int,
        timestep: float
    ) -> Tuple[int, float]:
        """
        Applies traffic perturbations (flooding, selective drops) for a specific node at current_time.
        Returns:
            (perturbed_inbound_forward_packets, malicious_drop_ratio)
        """
        atk = self.scheduler.get_attack_for_node(node_id, current_time)
        if atk is not None:
            return atk.perturb_traffic(current_time, node_id, inbound_forward_packets, timestep)
        return inbound_forward_packets, 0.0

    def post_step(self, current_time: float, step_records: List[TelemetryRecord]) -> List[TelemetryRecord]:
        """
        Applies post-step modifications to telemetry records and logs ground-truth labels.
        """
        for rec in step_records:
            atk = self.scheduler.get_attack_for_node(rec.node_id, current_time)
            if atk is not None:
                rec = atk.post_step(current_time, rec.node_id, rec)
            self.ground_truth.record_step(current_time, rec.node_id, atk)

        return step_records

    def get_ground_truth_dataframe(self) -> pd.DataFrame:
        """Returns recorded ground truth labels as a DataFrame."""
        return self.ground_truth.get_dataframe()

    def save_ground_truth_csv(self, filepath: Union[str, Path]) -> Path:
        """Saves ground truth labels to CSV."""
        return self.ground_truth.save_csv(filepath)

    def clear(self) -> None:
        """Resets injector scheduler and ground truth history."""
        self.scheduler.clear()
        self.ground_truth.clear()

"""
Ground-truth label recorder and exporter for cyberattack injection experiments.
Produces aligned, verifiable label datasets for machine learning.
"""

from typing import List, Optional, Union
from pathlib import Path
import pandas as pd
from .models import AttackGroundTruth
from .base import BaseAttack


class GroundTruthRecorder:
    """
    Records and exports per-node, per-timestep ground-truth attack labels.
    Maintains clean separation between physical/simulated telemetry and experimental annotations.
    """

    def __init__(self):
        self.records: List[AttackGroundTruth] = []

    def record_step(
        self,
        timestamp: float,
        node_id: int,
        active_attack: Optional[BaseAttack],
        is_indirectly_affected: bool = False
    ) -> AttackGroundTruth:
        """
        Records a ground-truth label entry for a node at a given simulation timestamp.
        """
        if active_attack is not None and active_attack.is_target(node_id):
            gt = AttackGroundTruth(
                timestamp=float(timestamp),
                node_id=int(node_id),
                attack_active=1,
                attack_type=str(active_attack.attack_type),
                attack_id=str(active_attack.attack_id),
                target_node=int(node_id),
                intensity=float(active_attack.intensity),
                is_indirectly_affected=False,
            )
        else:
            gt = AttackGroundTruth(
                timestamp=float(timestamp),
                node_id=int(node_id),
                attack_active=0,
                attack_type="normal",
                attack_id=None,
                target_node=None,
                intensity=0.0,
                is_indirectly_affected=bool(is_indirectly_affected),
            )

        self.records.append(gt)
        return gt

    def get_dataframe(self) -> pd.DataFrame:
        """Returns recorded ground truth labels as a pandas DataFrame."""
        if not self.records:
            return pd.DataFrame(columns=list(AttackGroundTruth.model_fields.keys()))
        data = [r.model_dump() for r in self.records]
        return pd.DataFrame(data)

    def save_csv(self, filepath: Union[str, Path]) -> Path:
        """Saves ground truth labels to a CSV file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        df = self.get_dataframe()
        df.to_csv(path, index=False)
        return path

    def clear(self) -> None:
        """Clears ground truth record history."""
        self.records.clear()

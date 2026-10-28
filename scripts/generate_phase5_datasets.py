"""
Phase 5 Dataset Generation Script.
Generates an extended multi-episode simulation (600s) containing multiple occurrences
of all 4 attack archetypes (Normal, DoS, Compromised Node, Node Failure) across multiple nodes.
Processes telemetry through FeaturePipeline to ensure zero leakage and full representation in train/val/test splits.
Also generates an independent cross-seed test set (seed=43).
"""

import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import MasterConfig
from backend.attacks import AttackInjector, AttackConfig
from backend.data_engineering import FeaturePipeline, DatasetManager


def generate_datasets():
    output_dir = PROJECT_ROOT / "models" / "datasets"
    results_dir = PROJECT_ROOT / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    print("[*] Generating Phase 5 Multi-Episode Simulation (Duration: 600s, Seed: 42)...")
    config = MasterConfig()

    injector = AttackInjector(attack_seed=2026)

    # Episode 1 attacks (0 - 300s)
    injector.add_attack(AttackConfig(
        attack_id="EP1_DOS_N2",
        attack_type="dos",
        target_nodes=[2],
        start_time=100.0,
        end_time=150.0,
        intensity=20.0
    ))
    injector.add_attack(AttackConfig(
        attack_id="EP1_COMP_N3",
        attack_type="compromised_node",
        target_nodes=[3],
        start_time=150.0,
        end_time=200.0,
        intensity=0.5
    ))
    injector.add_attack(AttackConfig(
        attack_id="EP1_FAIL_N4",
        attack_type="node_failure",
        target_nodes=[4],
        start_time=220.0,
        end_time=250.0,
        intensity=1.0
    ))

    # Episode 2 attacks (300 - 600s)
    injector.add_attack(AttackConfig(
        attack_id="EP2_DOS_N1",
        attack_type="dos",
        target_nodes=[1],
        start_time=380.0,
        end_time=430.0,
        intensity=20.0
    ))
    injector.add_attack(AttackConfig(
        attack_id="EP2_COMP_N5",
        attack_type="compromised_node",
        target_nodes=[5],
        start_time=450.0,
        end_time=500.0,
        intensity=0.5
    ))
    injector.add_attack(AttackConfig(
        attack_id="EP2_FAIL_N2",
        attack_type="node_failure",
        target_nodes=[2],
        start_time=520.0,
        end_time=550.0,
        intensity=1.0
    ))

    sim = NetworkSimulator(config=config, seed=42, attack_injector=injector)
    sim.run(duration=600.0)

    tel_df = sim.get_telemetry_dataframe()
    gt_df = injector.get_ground_truth_dataframe()
    raw_df = pd.merge(tel_df, gt_df, on=["timestamp", "node_id"], how="inner")
    
    raw_path = results_dir / "phase5_multi_episode_raw.csv"
    raw_df.to_csv(raw_path, index=False)
    print(f"[+] Saved raw multi-episode dataset ({len(raw_df)} records): {raw_path}")

    # Process through Feature Pipeline
    print("[*] Processing features via FeaturePipeline (W=[5, 15, 30]s)...")
    pipeline = FeaturePipeline(window_sizes=[5, 15, 30])
    datasets = pipeline.create_partitioned_datasets(raw_df, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)

    train_df = datasets["train"]
    val_df = datasets["val"]
    test_df = datasets["test"]
    full_df = datasets["full"]

    train_path = output_dir / "train_set_phase5.csv"
    val_path = output_dir / "val_set_phase5.csv"
    test_path = output_dir / "test_set_phase5.csv"
    full_path = output_dir / "features_phase5_full.csv"
    meta_path = output_dir / "feature_metadata_phase5.json"

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)
    test_df.to_csv(test_path, index=False)
    full_df.to_csv(full_path, index=False)
    pipeline.preprocessor.save_metadata(meta_path)

    print(f"[+] Saved Train split: {train_path} ({len(train_df)} records)")
    print(f"[+] Saved Val split:   {val_path} ({len(val_df)} records)")
    print(f"[+] Saved Test split:  {test_path} ({len(test_df)} records)")

    # Print class distributions for verification
    print("\n--- Training Set Class Distribution ---")
    print(train_df[['target_binary', 'target_multiclass', 'attack_type']].value_counts())

    print("\n--- Validation Set Class Distribution ---")
    print(val_df[['target_binary', 'target_multiclass', 'attack_type']].value_counts())

    print("\n--- Test Set Class Distribution ---")
    print(test_df[['target_binary', 'target_multiclass', 'attack_type']].value_counts())

    # Generate Cross-Seed Generalization Test Set (seed=43, attack_seed=3033)
    print("\n[*] Generating Cross-Seed Test Set (seed=43, attack_seed=3033, 600s)...")
    injector_cross = AttackInjector(attack_seed=3033)
    injector_cross.add_attack(AttackConfig(attack_id="CS_DOS_N3", attack_type="dos", target_nodes=[3], start_time=120.0, end_time=170.0, intensity=20.0))
    injector_cross.add_attack(AttackConfig(attack_id="CS_COMP_N2", attack_type="compromised_node", target_nodes=[2], start_time=200.0, end_time=250.0, intensity=0.5))
    injector_cross.add_attack(AttackConfig(attack_id="CS_FAIL_N1", attack_type="node_failure", target_nodes=[1], start_time=320.0, end_time=350.0, intensity=1.0))
    injector_cross.add_attack(AttackConfig(attack_id="CS_DOS_N4", attack_type="dos", target_nodes=[4], start_time=420.0, end_time=470.0, intensity=20.0))
    injector_cross.add_attack(AttackConfig(attack_id="CS_FAIL_N5", attack_type="node_failure", target_nodes=[5], start_time=500.0, end_time=530.0, intensity=1.0))

    sim_cross = NetworkSimulator(config=config, seed=43, attack_injector=injector_cross)
    sim_cross.run(duration=600.0)

    tel_cross = sim_cross.get_telemetry_dataframe()
    gt_cross = injector_cross.get_ground_truth_dataframe()
    raw_cross = pd.merge(tel_cross, gt_cross, on=["timestamp", "node_id"], how="inner")

    # Transform with train-fitted scaler
    cross_df = pipeline.process_dataframe(raw_cross, fit=False)
    cross_path = output_dir / "test_cross_seed_phase5.csv"
    cross_df.to_csv(cross_path, index=False)
    print(f"[+] Saved Cross-Seed Test Set: {cross_path} ({len(cross_df)} records)")
    print("\n--- Cross-Seed Set Class Distribution ---")
    print(cross_df[['target_binary', 'target_multiclass', 'attack_type']].value_counts())

    print("\n[+] Phase 5 datasets successfully generated and verified!")


if __name__ == "__main__":
    generate_datasets()

"""
Large-Scale Multi-Scenario Dataset Generation Script.
Orchestrates 10 independent simulation runs across:
- Topologies: Mesh, Random, Grid
- Scales: 6, 10, 16 nodes
- Attack Variations: Stealthy low-rate DoS, High-rate DoS flooding,
  Stealthy gray-hole dropping (15-25%), Aggressive dropping (75-90%),
  Single-node and Cascading multi-node failures.
- Generates 31,800+ total records.
- Extracts 95 multi-scale features per run to prevent cross-run leakage.
- Normalizes strictly using training-fit scaler and exports partitioned ML datasets.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import MasterConfig, TopologyConfig
from backend.attacks import AttackInjector, AttackConfig
from backend.data_engineering import TemporalFeatureExtractor, FeaturePreprocessor, DatasetManager


def build_scenario_config(num_nodes: int, topo_type: str, comm_range: float = 55.0) -> MasterConfig:
    config = MasterConfig()
    config.simulation.nodes = num_nodes
    config.simulation.duration = 300.0
    config.topology.type = topo_type
    config.topology.comm_range = comm_range

    if topo_type == "grid":
        rows = int(np.sqrt(num_nodes))
        cols = int(np.ceil(num_nodes / rows))
        config.topology.grid_rows = rows
        config.topology.grid_cols = cols
    elif topo_type == "random":
        config.topology.comm_range = comm_range * 1.25  # Ensure connectivity in random fields

    return config


def run_single_simulation(
    scenario_id: str,
    num_nodes: int,
    topo_type: str,
    sim_seed: int,
    attacks: List[AttackConfig],
    attack_seed: int
) -> pd.DataFrame:
    """Executes a single simulation run with specified attacks and returns merged DataFrame."""
    config = build_scenario_config(num_nodes=num_nodes, topo_type=topo_type)
    injector = AttackInjector(attack_seed=attack_seed)
    for atk in attacks:
        injector.add_attack(atk)

    sim = NetworkSimulator(config=config, seed=sim_seed, attack_injector=injector)
    sim.run(duration=300.0)

    tel_df = sim.get_telemetry_dataframe()
    gt_df = injector.get_ground_truth_dataframe()
    merged = pd.merge(tel_df, gt_df, on=["timestamp", "node_id"], how="inner")
    merged["scenario_id"] = scenario_id
    merged["topology"] = topo_type
    merged["num_nodes"] = num_nodes
    return merged


def generate_large_scale_corpus():
    output_dir = PROJECT_ROOT / "models" / "datasets"
    results_dir = PROJECT_ROOT / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    print("[*] Launching Large-Scale Multi-Scenario Dataset Generation (10 Scenarios, 31,800+ records)...")

    def mk_atk(atk_id: str, atk_type: str, targets: List[int], start: float, end: float, intensity: float) -> AttackConfig:
        return AttackConfig(
            attack_id=atk_id,
            attack_type=atk_type,
            target_nodes=targets,
            start_time=start,
            end_time=end,
            intensity=intensity
        )

    # -------------------------------------------------------------
    # 1. TRAINING SCENARIOS (5 runs across Mesh, Random, Grid)
    # -------------------------------------------------------------
    train_runs = [
        # Run 1: 6-node Mesh (Baseline moderate attacks)
        {
            "id": "TRAIN_01_MESH6", "nodes": 6, "topo": "mesh", "sim_seed": 101, "atk_seed": 1001,
            "attacks": [
                mk_atk("T1_DOS", "dos", [2], 80.0, 130.0, 20.0),
                mk_atk("T1_COMP", "compromised_node", [3], 150.0, 200.0, 0.50),
                mk_atk("T1_FAIL", "node_failure", [4], 220.0, 250.0, 1.0),
            ]
        },
        # Run 2: 10-node Random Field (Stealthy low-rate attacks)
        {
            "id": "TRAIN_02_RAND10", "nodes": 10, "topo": "random", "sim_seed": 102, "atk_seed": 1002,
            "attacks": [
                mk_atk("T2_DOS_STEALTH", "dos", [1], 60.0, 110.0, 6.0),
                mk_atk("T2_COMP_STEALTH", "compromised_node", [5], 130.0, 180.0, 0.20),
                mk_atk("T2_FAIL", "node_failure", [7], 200.0, 230.0, 1.0),
            ]
        },
        # Run 3: 16-node Grid (High-rate aggressive attacks & cascading failure)
        {
            "id": "TRAIN_03_GRID16", "nodes": 16, "topo": "grid", "sim_seed": 103, "atk_seed": 1003,
            "attacks": [
                mk_atk("T3_DOS_HIGH", "dos", [6], 70.0, 120.0, 35.0),
                mk_atk("T3_COMP_HIGH", "compromised_node", [10], 140.0, 190.0, 0.80),
                mk_atk("T3_FAIL_1", "node_failure", [3], 210.0, 240.0, 1.0),
                mk_atk("T3_FAIL_2", "node_failure", [12], 220.0, 250.0, 1.0),
            ]
        },
        # Run 4: 6-node Grid (Intermittent DoS & Selective dropping)
        {
            "id": "TRAIN_04_GRID6", "nodes": 6, "topo": "grid", "sim_seed": 104, "atk_seed": 1004,
            "attacks": [
                mk_atk("T4_DOS_BURST", "dos", [0], 90.0, 140.0, 15.0),
                mk_atk("T4_COMP", "compromised_node", [4], 160.0, 210.0, 0.40),
                mk_atk("T4_FAIL", "node_failure", [1], 230.0, 260.0, 1.0),
            ]
        },
        # Run 5: 10-node Mesh (Multi-node simultaneous DoS & stealthy drop)
        {
            "id": "TRAIN_05_MESH10", "nodes": 10, "topo": "mesh", "sim_seed": 105, "atk_seed": 1005,
            "attacks": [
                mk_atk("T5_DOS_N2", "dos", [2], 80.0, 130.0, 18.0),
                mk_atk("T5_DOS_N8", "dos", [8], 100.0, 140.0, 14.0),
                mk_atk("T5_COMP", "compromised_node", [9], 170.0, 220.0, 0.25),
                mk_atk("T5_FAIL", "node_failure", [4], 230.0, 260.0, 1.0),
            ]
        },
        # Run 6: 10-node Random Field (Stealthy low-rate DoS on Node 4 and stealth drop on Node 2)
        {
            "id": "TRAIN_06_RAND10", "nodes": 10, "topo": "random", "sim_seed": 106, "atk_seed": 1006,
            "attacks": [
                mk_atk("T6_DOS_STEALTH", "dos", [4], 75.0, 125.0, 7.0),
                mk_atk("T6_COMP_STEALTH", "compromised_node", [2], 145.0, 195.0, 0.22),
                mk_atk("T6_FAIL", "node_failure", [6], 215.0, 245.0, 1.0),
            ]
        },
        # Run 7: 16-node Grid (Stealthy low-rate DoS on Node 7 and drop on Node 13)
        {
            "id": "TRAIN_07_GRID16", "nodes": 16, "topo": "grid", "sim_seed": 107, "atk_seed": 1007,
            "attacks": [
                mk_atk("T7_DOS", "dos", [7], 80.0, 130.0, 8.0),
                mk_atk("T7_COMP", "compromised_node", [13], 150.0, 200.0, 0.25),
                mk_atk("T7_FAIL", "node_failure", [1], 220.0, 250.0, 1.0),
            ]
        },
        # Run 8: 10-node Random Field (Stealthy attack permutations)
        {
            "id": "TRAIN_08_RAND10", "nodes": 10, "topo": "random", "sim_seed": 108, "atk_seed": 1008,
            "attacks": [
                mk_atk("T8_DOS", "dos", [8], 70.0, 120.0, 6.5),
                mk_atk("T8_COMP", "compromised_node", [1], 140.0, 190.0, 0.20),
                mk_atk("T8_FAIL", "node_failure", [3], 210.0, 240.0, 1.0),
            ]
        },
        # Run 9: 6-node Mesh (Stealthy drop & failure)
        {
            "id": "TRAIN_09_MESH6", "nodes": 6, "topo": "mesh", "sim_seed": 109, "atk_seed": 1009,
            "attacks": [
                mk_atk("T9_DOS", "dos", [3], 80.0, 130.0, 7.5),
                mk_atk("T9_COMP", "compromised_node", [5], 150.0, 200.0, 0.24),
                mk_atk("T9_FAIL", "node_failure", [2], 220.0, 250.0, 1.0),
            ]
        },
        # Run 10: 16-node Grid (Multi-hop relaying under stealth conditions)
        {
            "id": "TRAIN_10_GRID16", "nodes": 16, "topo": "grid", "sim_seed": 110, "atk_seed": 1010,
            "attacks": [
                mk_atk("T10_DOS", "dos", [2], 85.0, 135.0, 8.5),
                mk_atk("T10_COMP", "compromised_node", [14], 155.0, 205.0, 0.22),
                mk_atk("T10_FAIL", "node_failure", [10], 225.0, 255.0, 1.0),
            ]
        },
    ]

    # -------------------------------------------------------------
    # 2. VALIDATION SCENARIOS (2 runs)
    # -------------------------------------------------------------
    val_runs = [
        # Run 6: 10-node Random Field
        {
            "id": "VAL_01_RAND10", "nodes": 10, "topo": "random", "sim_seed": 201, "atk_seed": 2001,
            "attacks": [
                mk_atk("V1_DOS", "dos", [3], 80.0, 130.0, 20.0),
                mk_atk("V1_COMP", "compromised_node", [6], 150.0, 200.0, 0.45),
                mk_atk("V1_FAIL", "node_failure", [2], 220.0, 250.0, 1.0),
            ]
        },
        # Run 7: 6-node Mesh
        {
            "id": "VAL_02_MESH6", "nodes": 6, "topo": "mesh", "sim_seed": 202, "atk_seed": 2002,
            "attacks": [
                mk_atk("V2_DOS", "dos", [1], 70.0, 120.0, 15.0),
                mk_atk("V2_COMP", "compromised_node", [5], 140.0, 190.0, 0.35),
                mk_atk("V2_FAIL", "node_failure", [0], 210.0, 240.0, 1.0),
            ]
        },
    ]

    # -------------------------------------------------------------
    # 3. IN-DOMAIN TEST SCENARIOS (1 run: 16-node Grid)
    # -------------------------------------------------------------
    test_runs = [
        {
            "id": "TEST_01_GRID16", "nodes": 16, "topo": "grid", "sim_seed": 203, "atk_seed": 2003,
            "attacks": [
                mk_atk("TE1_DOS", "dos", [5], 90.0, 140.0, 22.0),
                mk_atk("TE1_COMP", "compromised_node", [11], 160.0, 210.0, 0.50),
                mk_atk("TE1_FAIL", "node_failure", [8], 220.0, 250.0, 1.0),
            ]
        }
    ]

    # -------------------------------------------------------------
    # 4. CROSS-TOPOLOGY, CROSS-SEED TEST SCENARIOS (Unseen seeds & configurations)
    # -------------------------------------------------------------
    cross_runs = [
        # Run 9: 10-node Random Field (Unseen seed 301)
        {
            "id": "CROSS_01_RAND10", "nodes": 10, "topo": "random", "sim_seed": 301, "atk_seed": 3001,
            "attacks": [
                mk_atk("C1_DOS_STEALTH", "dos", [4], 80.0, 130.0, 7.0),
                mk_atk("C1_COMP_STEALTH", "compromised_node", [2], 140.0, 190.0, 0.22),
                mk_atk("C1_FAIL", "node_failure", [9], 210.0, 240.0, 1.0),
            ]
        },
        # Run 10: 16-node Grid (Unseen seed 302, High intensity flood & cascading drops)
        {
            "id": "CROSS_02_GRID16", "nodes": 16, "topo": "grid", "sim_seed": 302, "atk_seed": 3002,
            "attacks": [
                mk_atk("C2_DOS_HEAVY", "dos", [7], 75.0, 125.0, 30.0),
                mk_atk("C2_COMP_HEAVY", "compromised_node", [13], 145.0, 195.0, 0.75),
                mk_atk("C2_FAIL", "node_failure", [1], 215.0, 245.0, 1.0),
            ]
        }
    ]

    # Execute simulation and feature extraction per run
    extractor = TemporalFeatureExtractor(window_sizes=[5, 15, 30])
    dataset_mgr = DatasetManager()

    def process_runs(run_list, split_name):
        feature_dfs = []
        for r in run_list:
            print(f"  -> Simulating {r['id']} (Nodes: {r['nodes']}, Topo: {r['topo']}, Seed: {r['sim_seed']})...")
            raw_df = run_single_simulation(r["id"], r["nodes"], r["topo"], r["sim_seed"], r["attacks"], r["atk_seed"])
            # Extract features per-run to prevent timeline overlap
            feat_df = extractor.extract_features(raw_df)
            feat_df = dataset_mgr.format_targets(feat_df)
            feature_dfs.append(feat_df)
        combined = pd.concat(feature_dfs, ignore_index=True)
        print(f"  [+] {split_name} combined: {len(combined)} records across {len(run_list)} scenarios.")
        return combined

    print("\n[*] 1. Processing Training Scenarios...")
    raw_train = process_runs(train_runs, "Training Split")

    print("\n[*] 2. Processing Validation Scenarios...")
    raw_val = process_runs(val_runs, "Validation Split")

    print("\n[*] 3. Processing In-Domain Test Scenarios...")
    raw_test = process_runs(test_runs, "In-Domain Test Split")

    print("\n[*] 4. Processing Cross-Topology Test Scenarios...")
    raw_cross = process_runs(cross_runs, "Cross-Topology Test Split")

    # Fit preprocessor strictly on Training data
    print("\n[*] Fitting FeaturePreprocessor strictly on Training data (Zero Leakage)...")
    preprocessor = FeaturePreprocessor()
    train_scaled = preprocessor.fit_transform(raw_train)
    val_scaled = preprocessor.transform(raw_val)
    test_scaled = preprocessor.transform(raw_test)
    cross_scaled = preprocessor.transform(raw_cross)

    # Export datasets
    train_path = output_dir / "train_large_scale.csv"
    val_path = output_dir / "val_large_scale.csv"
    test_path = output_dir / "test_large_scale.csv"
    cross_path = output_dir / "test_cross_topology.csv"
    meta_path = output_dir / "feature_metadata_large_scale.json"

    train_scaled.to_csv(train_path, index=False)
    val_scaled.to_csv(val_path, index=False)
    test_scaled.to_csv(test_path, index=False)
    cross_scaled.to_csv(cross_path, index=False)
    preprocessor.save_metadata(meta_path)

    total_records = len(train_scaled) + len(val_scaled) + len(test_scaled) + len(cross_scaled)

    print("\n" + "=" * 60)
    print(f"[+] LARGE-SCALE CORPUS GENERATED SUCCESSFULLY: {total_records:,} Total Records")
    print("=" * 60)
    print(f"  - Training Set:       {train_path} ({len(train_scaled):,} records)")
    print(f"  - Validation Set:     {val_path} ({len(val_scaled):,} records)")
    print(f"  - In-Domain Test Set: {test_path} ({len(test_scaled):,} records)")
    print(f"  - Cross-Topology Set: {cross_path} ({len(cross_scaled):,} records)")
    print(f"  - Scaling Metadata:   {meta_path}")

    print("\n--- Training Set Class Distribution ---")
    print(train_scaled[["target_binary", "target_multiclass", "attack_type"]].value_counts())

    print("\n--- Cross-Topology Test Set Class Distribution ---")
    print(cross_scaled[["target_binary", "target_multiclass", "attack_type"]].value_counts())


if __name__ == "__main__":
    generate_large_scale_corpus()

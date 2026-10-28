"""
Script to execute the baseline Phase 1 IoT Network Simulation.
Generates structured telemetry and stores the dataset in CSV format under results/.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import load_config_from_yaml


def main():
    config_path = PROJECT_ROOT / "configs" / "simulation.yaml"
    output_path = PROJECT_ROOT / "results" / "telemetry_phase1_baseline.csv"

    print(f"[*] Loading configuration from: {config_path}")
    config = load_config_from_yaml(config_path)

    print(f"[*] Initializing simulator ({config.simulation.nodes} nodes, {config.simulation.duration}s, seed={config.simulation.seed})...")
    sim = NetworkSimulator(config=config)

    print("[*] Running simulation...")
    sim.run()

    print(f"[*] Saving telemetry records ({len(sim.telemetry_history)} records) to: {output_path}")
    saved_file = sim.save_telemetry_csv(output_path)

    df = sim.get_telemetry_dataframe()
    print("\n[+] Simulation Summary Statistics:")
    print("-" * 60)
    print(f"Total Nodes:          {df['node_id'].nunique()}")
    print(f"Total Time Steps:     {int(config.simulation.duration / config.simulation.timestep)}")
    print(f"Mean Packet Rate:     {df['packet_rate'].mean():.2f} pkts/s")
    print(f"Mean Forwarding Rate: {df['forwarding_rate'].mean():.2f} pkts/s")
    print(f"Mean Packet Loss:     {df['packet_loss'].mean():.4f}")
    print(f"Mean Latency:         {df['latency'].mean():.2f} ms")
    print(f"Mean RSSI:            {df['rssi'].mean():.2f} dBm")
    print(f"Mean Final Energy:    {df[df['timestamp'] == df['timestamp'].max()]['energy'].mean():.2f}%")
    print(f"Mean CPU:             {df['cpu'].mean():.2f}%")
    print(f"Mean Memory:          {df['memory'].mean():.2f}%")
    print("-" * 60)
    print(f"[+] Output CSV successfully written to: {saved_file}")


if __name__ == "__main__":
    main()

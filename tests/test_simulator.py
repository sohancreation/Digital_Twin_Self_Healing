"""
Unit and integration tests for NetworkSimulator.
Tests reproducibility, progression, record counts, and data export.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import MasterConfig, SimulationConfig, TopologyConfig


def test_simulation_progression():
    """Verify that the simulator advances time step-by-step and updates state."""
    sim = NetworkSimulator(seed=42)
    assert sim.current_time == 0.0

    step1_records = sim.step()
    assert len(step1_records) == 6
    assert sim.current_time == 1.0
    for rec in step1_records:
        assert rec.timestamp == 0.0

    step2_records = sim.step()
    assert len(step2_records) == 6
    assert sim.current_time == 2.0
    for rec in step2_records:
        assert rec.timestamp == 1.0


def test_record_count():
    """Verify that total generated records equals num_nodes * (duration / timestep)."""
    cfg = MasterConfig(
        simulation=SimulationConfig(nodes=6, duration=50.0, timestep=1.0, seed=42),
        topology=TopologyConfig(type="grid", grid_rows=2, grid_cols=3)
    )
    sim = NetworkSimulator(config=cfg)
    records = sim.run()

    expected_count = 6 * 50
    assert len(records) == expected_count
    assert len(sim.telemetry_history) == expected_count

    df = sim.get_telemetry_dataframe()
    assert len(df) == expected_count
    assert set(df["node_id"].unique()) == {0, 1, 2, 3, 4, 5}


def test_reproducibility():
    """
    Verify strict reproducibility:
    - Same seed produces identical telemetry DataFrames.
    - Different seed produces different telemetry.
    """
    # Run 1: seed = 42
    sim1 = NetworkSimulator(seed=42)
    sim1.run(duration=30.0)
    df1 = sim1.get_telemetry_dataframe()

    # Run 2: seed = 42
    sim2 = NetworkSimulator(seed=42)
    sim2.run(duration=30.0)
    df2 = sim2.get_telemetry_dataframe()

    # Assert exact numerical equality across all columns
    pd.testing.assert_frame_equal(df1, df2)

    # Run 3: seed = 43
    sim3 = NetworkSimulator(seed=43)
    sim3.run(duration=30.0)
    df3 = sim3.get_telemetry_dataframe()

    # Assert that df3 is NOT identical to df1
    with pytest.raises(AssertionError):
        pd.testing.assert_frame_equal(df1, df3)


def test_simulator_reset():
    """Verify that reset() clears history and returns to t=0."""
    sim = NetworkSimulator(seed=42)
    sim.run(duration=20.0)
    assert sim.current_time == 20.0
    assert len(sim.telemetry_history) == 6 * 20

    sim.reset(seed=42)
    assert sim.current_time == 0.0
    assert len(sim.telemetry_history) == 0

    # Running again should yield identical results
    sim.run(duration=20.0)
    assert len(sim.telemetry_history) == 6 * 20


def test_csv_export(tmp_path):
    """Verify that telemetry is correctly saved to CSV and can be reloaded without data loss."""
    sim = NetworkSimulator(seed=42)
    sim.run(duration=10.0)

    csv_path = tmp_path / "test_telemetry.csv"
    saved_path = sim.save_telemetry_csv(csv_path)

    assert saved_path.exists()
    reloaded_df = pd.read_csv(saved_path)
    assert len(reloaded_df) == 6 * 10
    assert "packet_loss" in reloaded_df.columns
    assert "energy" in reloaded_df.columns
    assert "cpu" in reloaded_df.columns

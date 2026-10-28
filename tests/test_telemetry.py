"""
Unit tests for TelemetryRecord schema, validation rules, and DataFrame serialization.
"""

import pytest
from pydantic import ValidationError
from backend.simulation.telemetry import TelemetryRecord, telemetry_records_to_dataframe


def test_telemetry_schema():
    """Verify TelemetryRecord schema integrity and valid field assignments."""
    record = TelemetryRecord(
        timestamp=10.0,
        node_id=1,
        packet_rate=2.5,
        forwarding_rate=1.0,
        packet_loss=0.05,
        latency=24.2,
        rssi=-75.0,
        energy=98.2,
        cpu=12.4,
        memory=18.0,
        neighbor_count=3,
        connection_state="CONNECTED",
        routing_state="ROUTING",
        threat_level=0.0,
        trust_score=1.0,
    )

    data = record.to_dict()
    assert data["timestamp"] == 10.0
    assert data["node_id"] == 1
    assert data["packet_loss"] == 0.05
    assert data["connection_state"] == "CONNECTED"
    assert data["routing_state"] == "ROUTING"


@pytest.mark.parametrize("invalid_field, invalid_val", [
    ("packet_loss", -0.1),
    ("packet_loss", 1.5),
    ("energy", -1.0),
    ("energy", 101.0),
    ("cpu", -5.0),
    ("cpu", 105.0),
    ("memory", -2.0),
    ("memory", 120.0),
    ("threat_level", -0.2),
    ("threat_level", 1.2),
    ("trust_score", -0.1),
    ("trust_score", 1.5),
    ("latency", -5.0),
    ("packet_rate", -1.0),
    ("node_id", -1),
    ("timestamp", -1.0),
])
def test_telemetry_bounds(invalid_field, invalid_val):
    """Verify that impossible/out-of-bounds values raise ValidationError."""
    valid_kwargs = {
        "timestamp": 0.0,
        "node_id": 0,
        "packet_rate": 2.0,
        "forwarding_rate": 0.0,
        "packet_loss": 0.0,
        "latency": 20.0,
        "rssi": -70.0,
        "energy": 100.0,
        "cpu": 10.0,
        "memory": 20.0,
        "neighbor_count": 2,
        "connection_state": "CONNECTED",
        "routing_state": "IDLE",
        "threat_level": 0.0,
        "trust_score": 1.0,
    }
    valid_kwargs[invalid_field] = invalid_val

    with pytest.raises(ValidationError):
        TelemetryRecord(**valid_kwargs)


def test_telemetry_dataframe_conversion():
    """Verify DataFrame export consistency and empty record handling."""
    empty_df = telemetry_records_to_dataframe([])
    assert "timestamp" in empty_df.columns
    assert len(empty_df) == 0

    records = [
        TelemetryRecord(
            timestamp=float(i),
            node_id=i,
            packet_rate=2.0,
            forwarding_rate=0.5,
            packet_loss=0.01,
            latency=15.0,
            rssi=-65.0,
            energy=99.0,
            cpu=10.0,
            memory=15.0,
            neighbor_count=2,
            connection_state="CONNECTED",
            routing_state="IDLE",
        )
        for i in range(5)
    ]

    df = telemetry_records_to_dataframe(records)
    assert len(df) == 5
    assert list(df["node_id"]) == [0, 1, 2, 3, 4]
    assert df["packet_rate"].mean() == 2.0

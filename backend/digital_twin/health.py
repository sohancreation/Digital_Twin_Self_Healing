"""
Descriptive health monitoring model for the Digital Twin.
Aggregates active node conditions into transparent, rule-based health summaries.
"""

from typing import Dict
import numpy as np
from .models import TwinNodeState, NetworkHealthSummary


def calculate_network_health(
    node_states: Dict[int, TwinNodeState],
    timestamp: float = 0.0
) -> NetworkHealthSummary:
    """
    Computes a descriptive health summary from the current set of node states.
    Strictly metric-driven; does not perform machine learning or risk scoring.
    """
    if not node_states:
        return NetworkHealthSummary(
            timestamp=timestamp,
            connected_node_ratio=0.0,
            active_node_ratio=0.0,
            average_packet_loss=0.0,
            average_latency_ms=0.0,
            average_rssi_dbm=-120.0,
            average_energy_pct=0.0,
            degraded_node_count=0,
            disconnected_node_count=0,
            health_status="CRITICAL"
        )

    total_nodes = len(node_states)
    connected_nodes = sum(1 for s in node_states.values() if s.connection_state == "CONNECTED")
    degraded_nodes = sum(1 for s in node_states.values() if s.connection_state == "DEGRADED")
    disconnected_nodes = sum(1 for s in node_states.values() if s.connection_state == "DISCONNECTED")
    active_nodes = sum(1 for s in node_states.values() if s.energy > 0 and s.connection_state != "DISCONNECTED")

    avg_loss = float(np.mean([s.packet_loss for s in node_states.values()]))
    avg_latency = float(np.mean([s.latency for s in node_states.values()]))
    avg_rssi = float(np.mean([s.rssi for s in node_states.values()]))
    avg_energy = float(np.mean([s.energy for s in node_states.values()]))

    connected_ratio = float(connected_nodes / total_nodes)
    active_ratio = float(active_nodes / total_nodes)

    # Descriptive health classification based on transparent physical thresholds
    if connected_ratio >= 0.9 and avg_loss < 0.1 and degraded_nodes == 0:
        status = "HEALTHY"
    elif connected_ratio >= 0.5 and avg_loss < 0.4:
        status = "DEGRADED"
    else:
        status = "CRITICAL"

    return NetworkHealthSummary(
        timestamp=timestamp,
        connected_node_ratio=connected_ratio,
        active_node_ratio=active_ratio,
        average_packet_loss=avg_loss,
        average_latency_ms=avg_latency,
        average_rssi_dbm=avg_rssi,
        average_energy_pct=avg_energy,
        degraded_node_count=degraded_nodes,
        disconnected_node_count=disconnected_nodes,
        health_status=status
    )

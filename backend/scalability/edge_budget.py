"""
Edge Gateway Hardware Budget and Real-Time Deadline Verifier for Phase 12.
Profiles execution budgets across realistic embedded and edge computing platforms:
Raspberry Pi 4, NVIDIA Jetson Nano, Intel Industrial Gateway, and ESP32 Edge Hub.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from .models import EdgeGatewaySpec


class EdgeBudgetVerifier:
    """
    Evaluates real-time control feasibility and compute margins against
    stringent hardware budgets on typical edge gateways.
    """

    GATEWAY_CATALOG = {
        "Raspberry Pi 4B": {
            "processor": "Quad-core ARM Cortex-A72 @ 1.5 GHz",
            "ram_mb": 4096,
            "deadline_ms": 100.0,  # 10 Hz control loop deadline
            "relative_speed_factor": 0.45,  # ~2.2x slower than desktop reference
        },
        "NVIDIA Jetson Nano": {
            "processor": "Quad-core ARM Cortex-A57 @ 1.43 GHz",
            "ram_mb": 4096,
            "deadline_ms": 100.0,
            "relative_speed_factor": 0.40,  # ~2.5x slower
        },
        "Intel Industrial Edge (x86)": {
            "processor": "Intel Core i5-1135G7 @ 2.4 GHz",
            "ram_mb": 8192,
            "deadline_ms": 50.0,  # 20 Hz high-frequency deadline
            "relative_speed_factor": 1.15,  # faster than desktop reference
        },
        "ESP32-S3 Micro-Gateway": {
            "processor": "Dual-core Xtensa LX7 @ 240 MHz (PSRAM)",
            "ram_mb": 8,
            "deadline_ms": 500.0,  # 2 Hz telemetry epoch deadline
            "relative_speed_factor": 0.08,  # ~12.5x slower
        },
    }

    @classmethod
    def evaluate_gateway(
        cls,
        gateway_name: str,
        reference_cycle_latency_ms: float,
        network_size: int = 24,
    ) -> EdgeGatewaySpec:
        """
        Projects reference cycle latency onto the specified edge gateway
        and evaluates deadline margin and maximum node support.
        """
        spec = cls.GATEWAY_CATALOG.get(gateway_name, cls.GATEWAY_CATALOG["Raspberry Pi 4B"])
        speed_factor = spec["relative_speed_factor"]
        deadline = spec["deadline_ms"]

        # Projected execution time on physical target platform
        projected_latency = reference_cycle_latency_ms / max(0.01, speed_factor)
        slack = deadline - projected_latency
        is_met = bool(slack >= 0.0)

        # Estimate maximum node capacity N_max within deadline
        # Based on sub-quadratic scaling: latency(N) ~ alpha * N^1.2
        per_node_factor = projected_latency / max(1, network_size ** 1.15)
        max_n = int((deadline / max(1e-4, per_node_factor)) ** (1.0 / 1.15))
        max_supported_nodes = max(4, min(250, max_n))

        return EdgeGatewaySpec(
            gateway_name=gateway_name,
            processor_arch=spec["processor"],
            ram_capacity_mb=spec["ram_mb"],
            real_time_deadline_ms=deadline,
            observed_cycle_latency_ms=round(projected_latency, 2),
            deadline_slack_ms=round(slack, 2),
            is_deadline_met=is_met,
            max_supported_nodes=max_supported_nodes,
        )

    @classmethod
    def evaluate_all_gateways(
        cls,
        reference_cycle_latency_ms: float,
        network_size: int = 24,
    ) -> List[EdgeGatewaySpec]:
        """Evaluates deadline compliance across all catalog gateways."""
        results = []
        for name in cls.GATEWAY_CATALOG:
            results.append(cls.evaluate_gateway(name, reference_cycle_latency_ms, network_size))
        return results

"""
Edge Gateway Hardware Profiler for Bridge-Aware GAT and DualHeadGNNClassifier.
Profiles model parameter count, FLOPs/MACs, memory footprint, and CPU inference latency
across realistic embedded and IoT edge gateway hardware platforms:
1. Raspberry Pi 4B (Quad-core ARM Cortex-A72 @ 1.5 GHz)
2. NVIDIA Jetson Nano (Quad-core ARM Cortex-A57 @ 1.43 GHz)
3. Intel Industrial Edge (Core i5-1135G7 @ 2.4 GHz)
4. ESP32-S3 Micro-Gateway (Dual-core Xtensa LX7 @ 240 MHz)
"""

import time
import math
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import torch

from ..gnn.model import DualHeadGNNClassifier
from ..gnn.features import GraphFeatureExtractor


class GNNEdgeProfiler:
    """
    Profiles computational, memory, and real-time latency characteristics
    of DualHeadGNNClassifier for embedded IoT edge deployments.
    """

    GATEWAY_SPECS = {
        "Raspberry Pi 4B": {
            "processor": "Quad-core ARM Cortex-A72 @ 1.5 GHz",
            "ram_mb": 4096,
            "deadline_ms": 100.0,  # 10 Hz control loop
            "speed_factor": 0.45,  # ~2.2x slower than modern desktop reference
        },
        "NVIDIA Jetson Nano": {
            "processor": "Quad-core ARM Cortex-A57 @ 1.43 GHz",
            "ram_mb": 4096,
            "deadline_ms": 100.0,
            "speed_factor": 0.40,  # ~2.5x slower
        },
        "Intel Industrial Edge": {
            "processor": "Intel Core i5-1135G7 @ 2.4 GHz",
            "ram_mb": 8192,
            "deadline_ms": 50.0,   # 20 Hz loop
            "speed_factor": 1.15,
        },
        "ESP32-S3 Micro-Gateway": {
            "processor": "Dual-core Xtensa LX7 @ 240 MHz (PSRAM)",
            "ram_mb": 8,
            "deadline_ms": 500.0,  # 2 Hz telemetry loop
            "speed_factor": 0.06,  # ~16x slower
        },
    }

    def __init__(self, model_path: Optional[Path] = None):
        self.model = DualHeadGNNClassifier()
        if model_path and model_path.exists():
            ckpt = torch.load(model_path, weights_only=False)
            self.model.load_state_dict(ckpt["model_state_dict"])
        self.model.eval()

    def count_parameters(self) -> Dict[str, int]:
        """Calculates total trainable and non-trainable parameter count."""
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        encoder_params = sum(p.numel() for p in self.model.encoder.parameters())
        attack_head_params = sum(p.numel() for p in self.model.attack_head.parameters())
        trust_head_params = sum(p.numel() for p in self.model.trust_head.parameters())

        return {
            "total_parameters": int(total_params),
            "trainable_parameters": int(trainable_params),
            "encoder_parameters": int(encoder_params),
            "attack_head_parameters": int(attack_head_params),
            "trust_head_parameters": int(trust_head_params),
            "model_size_kb": float(total_params * 4 / 1024.0),  # FP32: 4 bytes per param
        }

    def estimate_flops(self, num_nodes: int = 6, num_edges: int = 14) -> Dict[str, Any]:
        """
        Estimates total floating-point operations (FLOPs/MACs) for a single graph forward pass.
        Linear layers: 2 * in_features * out_features
        Attention: num_edges * (3 * head_dim + 1)
        """
        # Encoder Layer 1: in=12 -> out=64, edge_dim=4
        # lin_node: 6 nodes * (2 * 12 * 64) = 9,216
        # lin_edge: 14 edges * (2 * 4 * 64) = 7,168
        # attention: 14 edges * (3 * 16 + 1) * 4 heads = ~2,744
        # Layer 2: in=64 -> out=32, edge_dim=4
        # lin_node: 6 * (2 * 64 * 32) = 24,576
        # lin_edge: 14 * (2 * 4 * 32) = 3,584
        # Heads: attack_head (32->32->5) = 6 * (2*32*32 + 2*32*5) = 14,208
        # trust_head (32->32->1) = 6 * (2*32*32 + 2*32*1) = 12,672
        # Total approx MACs: ~75,000 FLOPs (extremely lightweight!)
        total_flops = int(num_nodes * 9800 + num_edges * 1150)
        return {
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "estimated_flops": total_flops,
            "estimated_macs": int(total_flops // 2),
            "gflops": float(total_flops / 1e9),
        }

    def benchmark_inference_latency(
        self,
        num_warmup: int = 50,
        num_iterations: int = 500,
        num_nodes: int = 6,
    ) -> Dict[str, float]:
        """
        Benchmarks actual CPU forward pass latency over repeated iterations.
        """
        # Create representative synthetic graph inputs
        x = torch.randn(num_nodes, 12, dtype=torch.float32)
        edge_index = torch.tensor(
            [[0, 1, 1, 2, 0, 2, 2, 3, 3, 4, 4, 5, 3, 5],
             [1, 0, 2, 1, 2, 0, 3, 2, 4, 3, 5, 4, 5, 3]],
            dtype=torch.long
        )
        edge_attr = torch.randn(edge_index.size(1), 4, dtype=torch.float32)
        bridge_mask = torch.tensor([0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1], dtype=torch.float32)

        # Warmup
        with torch.no_grad():
            for _ in range(num_warmup):
                self.model(x, edge_index, edge_attr, bridge_mask)

        # Benchmarking
        latencies = []
        with torch.no_grad():
            for _ in range(num_iterations):
                t_start = time.perf_counter()
                self.model(x, edge_index, edge_attr, bridge_mask)
                t_end = time.perf_counter()
                latencies.append((t_end - t_start) * 1000.0)  # ms

        lat_arr = np.array(latencies)
        return {
            "mean_ms": float(np.mean(lat_arr)),
            "std_ms": float(np.std(lat_arr)),
            "median_ms": float(np.median(lat_arr)),
            "p95_ms": float(np.percentile(lat_arr, 95)),
            "p99_ms": float(np.percentile(lat_arr, 99)),
            "min_ms": float(np.min(lat_arr)),
            "max_ms": float(np.max(lat_arr)),
        }

    def evaluate_gateways(self, ref_latency_ms: float) -> Dict[str, Any]:
        """
        Projects reference desktop CPU latency onto edge gateway hardware profiles.
        """
        results = {}
        for gw_name, spec in self.GATEWAY_SPECS.items():
            speed_factor = spec["speed_factor"]
            deadline_ms = spec["deadline_ms"]
            ram_mb = spec["ram_mb"]

            projected_lat_ms = float(ref_latency_ms / speed_factor)
            deadline_margin_pct = float(max(0.0, (deadline_ms - projected_lat_ms) / deadline_ms * 100.0))
            is_feasible = bool(projected_lat_ms < deadline_ms)
            max_inferences_per_sec = float(1000.0 / projected_lat_ms)

            results[gw_name] = {
                "processor": spec["processor"],
                "ram_mb": ram_mb,
                "deadline_ms": deadline_ms,
                "projected_latency_ms": round(projected_lat_ms, 3),
                "deadline_margin_pct": round(deadline_margin_pct, 1),
                "is_feasible": is_feasible,
                "max_throughput_hz": round(max_inferences_per_sec, 1),
            }
        return results

    def profile_full(self) -> Dict[str, Any]:
        """Runs end-to-end profiling and returns structured report."""
        params = self.count_parameters()
        flops = self.estimate_flops()
        lat = self.benchmark_inference_latency()
        gateways = self.evaluate_gateways(lat["mean_ms"])

        return {
            "model_architecture": "BridgeAwareGAT + DualHeadGNNClassifier",
            "parameters": params,
            "computational_complexity": flops,
            "desktop_reference_latency": lat,
            "edge_gateway_projections": gateways,
        }

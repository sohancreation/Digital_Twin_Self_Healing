"""
Main IoT Network Simulator engine.
Coordinates topology, routing, node dynamics, discrete-time progression,
and telemetry harvesting.
"""

from typing import List, Dict, Optional, Union, Any
from pathlib import Path
import numpy as np
import pandas as pd

from .config import MasterConfig, load_config_from_yaml
from .topology import NetworkTopology
from .node import IoTNode
from .telemetry import TelemetryRecord, telemetry_records_to_dataframe


class NetworkSimulator:
    """
    Reproducible discrete-time simulator for resource-constrained IoT networks.
    Coordinates node execution, multi-hop routing, channel propagation, and telemetry recording.
    """

    def __init__(
        self,
        config: Optional[Union[MasterConfig, Path, str]] = None,
        seed: Optional[int] = None,
        attack_injector: Optional[Any] = None,
    ):
        if isinstance(config, (Path, str)):
            self.config = load_config_from_yaml(config)
        elif isinstance(config, MasterConfig):
            self.config = config
        elif config is None:
            self.config = MasterConfig()
        else:
            raise TypeError(f"Invalid config type: {type(config)}")

        # Override seed if explicitly provided
        if seed is not None:
            self.config.simulation.seed = seed

        self.seed = self.config.simulation.seed
        self.rng = np.random.default_rng(self.seed)
        self.attack_injector = attack_injector

        # Time management
        self.current_time: float = 0.0
        self.timestep: float = self.config.simulation.timestep
        self.duration: float = self.config.simulation.duration
        self.num_nodes: int = self.config.simulation.nodes

        # Topology and Nodes
        self.topology = NetworkTopology(
            num_nodes=self.num_nodes,
            config=self.config.topology,
            rng=self.rng
        )

        self.nodes: Dict[int, IoTNode] = {}
        self.telemetry_history: List[TelemetryRecord] = []

        self._initialize_nodes()

    def _initialize_nodes(self) -> None:
        """Instantiates all IoT nodes and connects them with topology neighbor data."""
        self.nodes.clear()
        for node_id in range(self.num_nodes):
            pos = self.topology.positions[node_id]
            import copy
            node = IoTNode(
                node_id=node_id,
                position=pos,
                traffic_config=copy.deepcopy(self.config.traffic),
                channel_config=copy.deepcopy(self.config.channel),
                resource_config=copy.deepcopy(self.config.resources),
            )
            neighbors = self.topology.get_neighbors(node_id)
            neighbor_dists = self.topology.get_neighbor_distances(node_id)
            node.set_neighbors(neighbors, neighbor_dists)
            self.nodes[node_id] = node

    def reset(self, seed: Optional[int] = None) -> None:
        """Resets the simulator to initial state t=0 with optional new seed."""
        if seed is not None:
            self.seed = seed
            self.config.simulation.seed = seed

        self.rng = np.random.default_rng(self.seed)
        self.current_time = 0.0
        self.telemetry_history.clear()

        if self.attack_injector is not None:
            self.attack_injector.clear()

        self.topology = NetworkTopology(
            num_nodes=self.num_nodes,
            config=self.config.topology,
            rng=self.rng
        )
        self._initialize_nodes()

    def step(self) -> List[TelemetryRecord]:
        """
        Advances the simulation by one discrete timestep (dt).
        Simulates end-to-end traffic routing and collects telemetry from all nodes.
        """
        # 1. Pre-routing attack hook (e.g. disable failed nodes from routing)
        if self.attack_injector is not None:
            self.attack_injector.pre_routing(self.current_time, self.nodes, self.topology)

        inbound_forward_counts = {node_id: 0 for node_id in range(self.num_nodes)}

        # Multi-hop routing simulation: Active nodes generate flows to random destinations
        for src_id, src_node in self.nodes.items():
            if not src_node.is_alive or getattr(src_node, "_is_failed", False) or self.num_nodes <= 1:
                continue

            # Generate estimated packet count for route planning
            rate = max(0.0, self.rng.normal(self.config.traffic.base_packet_rate, self.config.traffic.packet_rate_std))
            pkts = int(np.round(rate * self.timestep))

            if pkts > 0:
                # Pick a random destination node (must be alive and not failed)
                possible_targets = [
                    n for n in range(self.num_nodes)
                    if n != src_id and self.nodes[n].is_alive and not getattr(self.nodes[n], "_is_failed", False)
                ]
                if possible_targets:
                    dest_id = int(self.rng.choice(possible_targets))
                    path = self.topology.get_shortest_path(src_id, dest_id)
                    # If multi-hop path exists, intermediate nodes forward packets
                    if path and len(path) > 2:
                        for intermediate in path[1:-1]:
                            inbound_forward_counts[intermediate] += pkts

        # 2. Traffic perturbation hook (flooding, selective drops)
        if self.attack_injector is not None:
            for node_id in range(self.num_nodes):
                inbound_forward_counts[node_id], _ = self.attack_injector.perturb_traffic(
                    self.current_time, node_id, inbound_forward_counts[node_id], self.timestep
                )

        # 3. Execute node updates
        step_records: List[TelemetryRecord] = []
        for node_id, node in self.nodes.items():
            rec = node.step(
                timestamp=self.current_time,
                timestep=self.timestep,
                inbound_forward_packets=inbound_forward_counts[node_id],
                rng=self.rng,
            )
            step_records.append(rec)

        # 4. Post-step attack hook & ground-truth labeling
        if self.attack_injector is not None:
            step_records = self.attack_injector.post_step(self.current_time, step_records)

        for rec in step_records:
            self.telemetry_history.append(rec)

        self.current_time += self.timestep
        return step_records

    def run(self, duration: Optional[float] = None) -> List[TelemetryRecord]:
        """
        Runs the full simulation from current_time until duration is reached.
        Returns all generated telemetry records.
        """
        target_duration = duration if duration is not None else self.duration
        num_steps = int(np.ceil(target_duration / self.timestep))

        for _ in range(num_steps):
            self.step()

        return self.telemetry_history

    def get_telemetry_dataframe(self) -> pd.DataFrame:
        """Returns collected telemetry records as a structured pandas DataFrame."""
        return telemetry_records_to_dataframe(self.telemetry_history)

    def save_telemetry_csv(self, filepath: Union[str, Path]) -> Path:
        """Saves collected telemetry records to a CSV file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        df = self.get_telemetry_dataframe()
        df.to_csv(path, index=False)
        return path

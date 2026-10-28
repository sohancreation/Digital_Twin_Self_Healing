"""
Unit and integration tests for Reinforcement Learning (RL) Autonomous Recovery Baseline.
Verifies MDP state representation, Q-network forward pass, action dispatch,
reward computation, and full simulator integration.
"""

import pytest
import numpy as np
import torch
import networkx as nx

from backend.experiments.rl_recovery import (
    QNetwork,
    ReplayBuffer,
    DQNRecoveryAgent,
    RLRecoveryBaseline,
    extract_rl_state,
    compute_rl_reward,
    RL_ACTIONS,
    STATE_DIM,
    ACTION_DIM,
)
from backend.experiments.models import BaselineType
from backend.experiments.runner import ExperimentRunner
from backend.simulation.simulator import NetworkSimulator
from backend.simulation.config import MasterConfig, SimulationConfig, TopologyConfig
from backend.simulation.telemetry import TelemetryRecord


@pytest.fixture
def sim_environment():
    """Provides a deterministic 6-node NetworkSimulator with articulation point (Node 3)."""
    cfg = MasterConfig(
        simulation=SimulationConfig(duration=30.0, seed=42, nodes=6),
        topology=TopologyConfig(layout="mesh"),
    )
    sim = NetworkSimulator(config=cfg, seed=42)
    sim.topology.graph.clear()
    sim.topology.graph.add_edges_from([(0, 1), (1, 2), (0, 2), (2, 3), (3, 4), (4, 5), (3, 5)])
    sim.topology._compute_distances_and_neighbors()
    for nid, node in sim.nodes.items():
        nbrs = sim.topology.get_neighbors(nid)
        dists = sim.topology.get_neighbor_distances(nid)
        node.set_neighbors(nbrs, dists)
    return sim


class TestRLRecoveryArchitecture:
    """Verifies neural network architectures and buffer mechanics."""

    def test_qnetwork_shapes(self):
        net = QNetwork(state_dim=STATE_DIM, action_dim=ACTION_DIM, hidden_dim=64)
        x = torch.randn(4, STATE_DIM)
        q = net(x)
        assert q.shape == (4, ACTION_DIM)
        assert not torch.isnan(q).any()

    def test_replay_buffer(self):
        buf = ReplayBuffer(capacity=100)
        s = np.zeros(STATE_DIM, dtype=np.float32)
        s_next = np.ones(STATE_DIM, dtype=np.float32)

        for i in range(10):
            buf.push(s, action=1, reward=0.5, next_state=s_next, done=False)

        assert len(buf) == 10
        states, actions, rewards, next_states, dones = buf.sample(4)
        assert states.shape == (4, STATE_DIM)
        assert actions.shape == (4,)
        assert rewards.shape == (4,)
        assert next_states.shape == (4, STATE_DIM)
        assert dones.shape == (4,)

    def test_dqn_agent_step(self):
        agent = DQNRecoveryAgent(state_dim=STATE_DIM, action_dim=ACTION_DIM, batch_size=4)
        s = np.zeros(STATE_DIM, dtype=np.float32)
        s_next = np.ones(STATE_DIM, dtype=np.float32)

        for _ in range(8):
            agent.memory.push(s, 2, 1.0, s_next, False)

        loss = agent.train_step()
        assert loss is not None
        assert loss >= 0.0

        action = agent.select_action(s, evaluate=True)
        assert 0 <= action < ACTION_DIM


class TestRLStateAndReward:
    """Verifies MDP state feature extraction and reward formulation."""

    def test_state_bounds_and_cut_vertex(self, sim_environment):
        sim = sim_environment
        telemetry = sim.step()

        # Node 3 is articulation point
        state_node3 = extract_rl_state(sim, telemetry, target_node=3, current_time=1.0)
        assert len(state_node3) == STATE_DIM
        assert 0.0 <= state_node3[0] <= 1.0  # PDR
        assert state_node3[5] == 1.0         # is_cut_vertex == 1.0 for node 3

        # Node 1 is not articulation point
        state_node1 = extract_rl_state(sim, telemetry, target_node=1, current_time=1.0)
        assert state_node1[5] == 0.0         # is_cut_vertex == 0.0 for node 1

    def test_reward_penalties(self):
        # Nominal condition: high reward
        r_nominal = compute_rl_reward(pdr=0.98, loss=0.02, latency_ms=12.0, is_partitioned=False, action_idx=0)
        assert r_nominal > 1.0

        # Partition disaster: huge penalty
        r_partitioned = compute_rl_reward(pdr=0.70, loss=0.30, latency_ms=45.0, is_partitioned=True, action_idx=1)
        assert r_partitioned < -3.0
        assert r_nominal > r_partitioned


class TestRLControllerIntegration:
    """Verifies closed-loop integration of RLRecoveryBaseline in simulation harness."""

    def test_rl_baseline_step_under_perturbation(self, sim_environment):
        sim = sim_environment
        controller = RLRecoveryBaseline(simulator=sim, target_node=3, detection_delay_s=1.0)

        # Inject anomaly by modifying node 3 telemetry
        for t in range(5):
            telem = sim.step()
            # Artificially perturb node 3 loss
            if t >= 2:
                telem[3].packet_loss = 0.50
                telem[3].packet_rate = 25.0
            out = controller.step(current_time=float(t), telemetry_dict=telem)

        assert controller.detection_time is not None
        assert controller.mitigation_applied is True
        assert out["action"].startswith("RL_")

    def test_runner_executes_rl_baseline(self):
        """Verifies end-to-end execution of BaselineType.RL_RECOVERY through ExperimentRunner."""
        runner = ExperimentRunner()
        result = runner.run_single_experiment(
            baseline_type=BaselineType.RL_RECOVERY,
            attack_type="dos",
            target_node=3,
            seed=42,
            duration_s=15.0,
            attack_start_s=5.0,
            attack_end_s=12.0,
        )

        assert result.baseline == BaselineType.RL_RECOVERY
        assert result.duration_s == 15.0
        assert 0.0 <= result.resilience_score <= 1.0
        assert result.total_packets_sent > 0
        assert result.total_packets_delivered > 0

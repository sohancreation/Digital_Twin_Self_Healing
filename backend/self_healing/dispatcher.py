"""
Actuation Policy Dispatcher for Phase 9.
Translates optimal mitigation decisions s* into cryptographically authenticated
downlink actuation frames, models lossy wireless channel delivery with exponential
backoff retries, and collects execution acknowledgments.
"""

import time
import hmac
import hashlib
import uuid
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from ..recovery.models import RecoveryCandidate, OptimizationDecision
from .models import (
    ActuationCommand,
    ActuationCommandType,
    CommandAck,
    ActuationBatch,
    CommandStatus,
)


class ActuationPolicyDispatcher:
    """
    Translates high-level candidate strategies into compact downlink actuation frames.
    Handles cryptographic signing, realistic RF channel delays, packet loss retries,
    and acknowledgment tracking.
    """

    def __init__(
        self,
        shared_secret_key: bytes = b"iot_mesh_dt_hmac_secret_2026",
        base_downlink_delay_ms: float = 12.0,
        downlink_jitter_ms: float = 2.5,
        default_channel_loss_prob: float = 0.05,
        max_retries: int = 3,
        base_backoff_ms: float = 20.0,
        seed: Optional[int] = 42,
    ):
        self.secret_key = shared_secret_key
        self.base_delay_ms = base_downlink_delay_ms
        self.jitter_ms = downlink_jitter_ms
        self.channel_loss_prob = default_channel_loss_prob
        self.max_retries = max_retries
        self.base_backoff_ms = base_backoff_ms
        self.rng = np.random.default_rng(seed)

        self._sequence_counter: int = 1000
        self.dispatched_batches: Dict[str, ActuationBatch] = {}
        self.received_acks: Dict[str, CommandAck] = {}

    def _next_sequence_number(self) -> int:
        self._sequence_counter += 1
        return self._sequence_counter

    def generate_hmac_token(self, cmd_id: str, target_node: int, cmd_type: str, seq: int) -> str:
        """Computes HMAC-SHA256 authorization token over command payload."""
        payload = f"{cmd_id}:{target_node}:{cmd_type}:{seq}".encode("utf-8")
        return hmac.new(self.secret_key, payload, hashlib.sha256).hexdigest()

    def verify_hmac_token(self, cmd: ActuationCommand) -> bool:
        """Verifies cryptographic authenticity of a received downlink command."""
        expected = self.generate_hmac_token(
            cmd.command_id, cmd.target_node, cmd.command_type, cmd.sequence_number
        )
        return hmac.compare_digest(cmd.hmac_token, expected)

    def create_actuation_batch(
        self,
        candidate: RecoveryCandidate,
        decision_epoch: float,
    ) -> ActuationBatch:
        """
        Decomposes a RecoveryCandidate s_k into a structured ActuationBatch of downlink commands.
        """
        batch_id = f"BATCH_{int(decision_epoch)}_{candidate.strategy_id}_{uuid.uuid4().hex[:6]}"
        action = candidate.action_type
        targets = candidate.target_nodes
        affected = candidate.affected_nodes
        params = candidate.parameters or {}

        commands: List[ActuationCommand] = []

        if action == "NO_ACTION":
            # Baseline: no downlink actuation frames needed
            pass

        elif action == "NODE_ISOLATION":
            # Command 1: Isolate target node
            for t in targets:
                cmd_id = f"CMD_ISO_{t}_{uuid.uuid4().hex[:6]}"
                seq = self._next_sequence_number()
                token = self.generate_hmac_token(cmd_id, t, "ISOLATE_NODE", seq)
                commands.append(ActuationCommand(
                    command_id=cmd_id,
                    target_node=t,
                    command_type="ISOLATE_NODE",
                    parameters={"action": "sever_all_links", "quarantine": True},
                    sequence_number=seq,
                    hmac_token=token,
                    timestamp=decision_epoch,
                ))

            # Command 2: Notify 1-hop affected neighbors to drop routes to target
            for a in affected:
                cmd_id = f"CMD_DROP_ROUTE_{a}_{uuid.uuid4().hex[:6]}"
                seq = self._next_sequence_number()
                token = self.generate_hmac_token(cmd_id, a, "REROUTE_TRAFFIC", seq)
                commands.append(ActuationCommand(
                    command_id=cmd_id,
                    target_node=a,
                    command_type="REROUTE_TRAFFIC",
                    parameters={"remove_neighbors": targets},
                    sequence_number=seq,
                    hmac_token=token,
                    timestamp=decision_epoch,
                ))

        elif action == "RATE_LIMITING":
            rate_cap = float(params.get("rate_limit_pkts_per_sec", 2.0))
            for t in targets:
                cmd_id = f"CMD_RL_{t}_{uuid.uuid4().hex[:6]}"
                seq = self._next_sequence_number()
                token = self.generate_hmac_token(cmd_id, t, "SET_RATE_LIMIT", seq)
                commands.append(ActuationCommand(
                    command_id=cmd_id,
                    target_node=t,
                    command_type="SET_RATE_LIMIT",
                    parameters={"token_rate_pkts_s": rate_cap, "bucket_capacity": 10},
                    sequence_number=seq,
                    hmac_token=token,
                    timestamp=decision_epoch,
                ))

        elif action == "DYNAMIC_REROUTING":
            bypass_routes = params.get("alternate_routes", {})
            for a in affected:
                cmd_id = f"CMD_REROUTE_{a}_{uuid.uuid4().hex[:6]}"
                seq = self._next_sequence_number()
                token = self.generate_hmac_token(cmd_id, a, "REROUTE_TRAFFIC", seq)
                commands.append(ActuationCommand(
                    command_id=cmd_id,
                    target_node=a,
                    command_type="REROUTE_TRAFFIC",
                    parameters={"installed_bypasses": bypass_routes},
                    sequence_number=seq,
                    hmac_token=token,
                    timestamp=decision_epoch,
                ))

        elif action == "NODE_REBOOT":
            reboot_dur = float(params.get("reboot_duration_s", 8.0))
            for t in targets:
                cmd_id = f"CMD_REBOOT_{t}_{uuid.uuid4().hex[:6]}"
                seq = self._next_sequence_number()
                token = self.generate_hmac_token(cmd_id, t, "REBOOT_NODE", seq)
                commands.append(ActuationCommand(
                    command_id=cmd_id,
                    target_node=t,
                    command_type="REBOOT_NODE",
                    parameters={"duration_s": reboot_dur, "flush_queues": True, "restore_clean": True},
                    sequence_number=seq,
                    hmac_token=token,
                    timestamp=decision_epoch,
                ))

        elif action == "POWER_ADJUSTMENT":
            power_boost = float(params.get("power_boost_dbm", 4.0))
            for a in affected:
                cmd_id = f"CMD_PWR_{a}_{uuid.uuid4().hex[:6]}"
                seq = self._next_sequence_number()
                token = self.generate_hmac_token(cmd_id, a, "ADJUST_TX_POWER", seq)
                commands.append(ActuationCommand(
                    command_id=cmd_id,
                    target_node=a,
                    command_type="ADJUST_TX_POWER",
                    parameters={"power_boost_dbm": power_boost},
                    sequence_number=seq,
                    hmac_token=token,
                    timestamp=decision_epoch,
                ))

        elif action == "COMPOSITE":
            # Composite mitigation: respect cut-vertex invariance (Theorem 2)
            sub_actions = params.get("sub_actions", ["ISOLATE_NODE", "ADJUST_TX_POWER"])
            is_cut = params.get("is_cut_vertex", False)

            if "ISOLATE_NODE" in sub_actions and not is_cut:
                for t in targets:
                    cmd_id = f"CMD_COMP_ISO_{t}_{uuid.uuid4().hex[:6]}"
                    seq = self._next_sequence_number()
                    token = self.generate_hmac_token(cmd_id, t, "ISOLATE_NODE", seq)
                    commands.append(ActuationCommand(
                        command_id=cmd_id,
                        target_node=t,
                        command_type="ISOLATE_NODE",
                        parameters={"action": "sever_all_links", "quarantine": True},
                        sequence_number=seq,
                        hmac_token=token,
                        timestamp=decision_epoch,
                    ))
            elif "SET_RATE_LIMIT" in sub_actions or is_cut:
                # Theorem 2: Cut-vertices cannot be severed; enforce strict ingress clamping
                rate_cap = float(params.get("rate_limit_pkts_per_sec", 0.5))
                for t in targets:
                    cmd_id = f"CMD_COMP_RL_{t}_{uuid.uuid4().hex[:6]}"
                    seq = self._next_sequence_number()
                    token = self.generate_hmac_token(cmd_id, t, "SET_RATE_LIMIT", seq)
                    commands.append(ActuationCommand(
                        command_id=cmd_id,
                        target_node=t,
                        command_type="SET_RATE_LIMIT",
                        parameters={"token_rate_pkts_s": rate_cap, "bucket_capacity": 10},
                        sequence_number=seq,
                        hmac_token=token,
                        timestamp=decision_epoch,
                    ))

            if "ADJUST_TX_POWER" in sub_actions or params.get("power_boosts"):
                pwr_boost_val = float(params.get("power_boost_dbm", 4.0))
                for a in affected:
                    cmd_id = f"CMD_COMP_PWR_{a}_{uuid.uuid4().hex[:6]}"
                    seq = self._next_sequence_number()
                    token = self.generate_hmac_token(cmd_id, a, "ADJUST_TX_POWER", seq)
                    commands.append(ActuationCommand(
                        command_id=cmd_id,
                        target_node=a,
                        command_type="ADJUST_TX_POWER",
                        parameters={"power_boost_dbm": pwr_boost_val},
                        sequence_number=seq,
                        hmac_token=token,
                        timestamp=decision_epoch,
                    ))

        batch = ActuationBatch(
            batch_id=batch_id,
            decision_epoch=decision_epoch,
            strategy_id=candidate.strategy_id,
            action_type=candidate.action_type,
            commands=commands,
            dispatch_timestamp=decision_epoch,
            all_acknowledged=len(commands) == 0,
        )
        self.dispatched_batches[batch_id] = batch
        return batch

    def dispatch_batch(
        self,
        batch: ActuationBatch,
        current_time: float,
        channel_loss_prob: Optional[float] = None,
    ) -> Tuple[ActuationBatch, List[CommandAck]]:
        """
        Dispatches all commands in an ActuationBatch across simulated lossy RF channel.
        Simulates retries with exponential backoff if transmission fails.
        """
        p_loss = self.channel_loss_prob if channel_loss_prob is None else channel_loss_prob
        batch.dispatch_timestamp = current_time
        batch_acks: List[CommandAck] = []
        total_batch_retries = 0

        for cmd in batch.commands:
            cmd.status = "DISPATCHED"
            # Simulate transmission with potential packet loss & retries
            applied = False
            rtt_total = 0.0
            retries = 0

            for attempt in range(self.max_retries + 1):
                # Channel propagation latency: base + jitter
                delay = max(2.0, self.rng.normal(self.base_delay_ms, self.jitter_ms))
                rtt_total += delay * 2.0  # Downlink + uplink ACK round-trip

                # Random channel drop
                is_dropped = self.rng.random() < p_loss

                if not is_dropped:
                    # Successfully delivered and applied!
                    applied = True
                    cmd.status = "APPLIED"
                    break
                else:
                    if attempt < self.max_retries:
                        # Dropped frame: trigger retransmission with exponential backoff
                        retries += 1
                        backoff = self.base_backoff_ms * (2.0 ** attempt)
                        rtt_total += backoff

            cmd.retry_count = retries
            total_batch_retries += retries

            if applied:
                ack = CommandAck(
                    command_id=cmd.command_id,
                    node_id=cmd.target_node,
                    status="APPLIED",
                    round_trip_ms=round(rtt_total, 2),
                    timestamp=current_time + (rtt_total / 1000.0),
                    message=f"Command {cmd.command_type} successfully applied at node {cmd.target_node} after {retries} retries.",
                )
            else:
                cmd.status = "TIMEOUT"
                ack = CommandAck(
                    command_id=cmd.command_id,
                    node_id=cmd.target_node,
                    status="TIMEOUT",
                    round_trip_ms=round(rtt_total, 2),
                    timestamp=current_time + (rtt_total / 1000.0),
                    message=f"Command {cmd.command_type} delivery timed out after {retries} attempts.",
                )

            batch_acks.append(ack)
            self.received_acks[cmd.command_id] = ack

        batch.total_retries = total_batch_retries
        batch.all_acknowledged = all(ack.status == "APPLIED" for ack in batch_acks) if batch.commands else True
        self.dispatched_batches[batch.batch_id] = batch

        return batch, batch_acks

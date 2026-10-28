"""
Closed-Loop Verifier for Phase 9.
Monitors post-actuation telemetry streams over verification window T_verify,
evaluating multi-attribute health conditions (connectivity, PDR, loss, CPU, latency),
and transitions verification lifecycle states.
"""

import math
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import networkx as nx

from ..digital_twin.twin import DigitalTwin
from ..simulation.telemetry import TelemetryRecord
from .models import (
    VerificationStatus,
    VerificationCriterion,
    VerificationResult,
    ActuationBatch,
    SPRTConfig,
    SPRTState,
    SPRTDecision,
)


class WaldSPRTVerifier:
    """
    Wald's Sequential Probability Ratio Test (SPRT) Verifier.
    Performs sequential hypothesis testing:
      H0: E[x] <= p0 (Nominal, recovered state)
      H1: E[x] >= p1 (Degraded / ongoing attack state)

    Accumulated log-likelihood ratio:
      Lambda_n = sum_{k=1}^n ln( f(x_k | H1) / f(x_k | H0) )
               = d_n * ln(p1 / p0) + (n - d_n) * ln((1 - p1) / (1 - p0))

    Decision boundaries:
      A = ln((1 - beta) / alpha) > 0  (Accept H1: Verification Failure)
      B = ln(beta / (1 - alpha)) < 0  (Accept H0: Early Verification Success)
    """

    def __init__(self, config: Optional[SPRTConfig] = None):
        self.config = config or SPRTConfig()
        self.reset()

    def reset(self) -> None:
        self.sample_count: int = 0
        self.dropped_count: int = 0
        self.log_likelihood_ratio: float = 0.0
        self.decision: SPRTDecision = "CONTINUE"
        self.early_stopped: bool = False
        self.trajectory: List[float] = [0.0]

    def update(self, packet_loss_sample: float, effective_packets: Optional[int] = None) -> SPRTDecision:
        """
        Updates SPRT log-likelihood accumulator with a telemetry observation.
        """
        if self.decision != "CONTINUE":
            return self.decision

        eff = effective_packets if effective_packets is not None else self.config.packets_per_step

        p0 = max(1e-4, min(1.0 - 1e-4, self.config.p0))
        p1 = max(1e-4, min(1.0 - 1e-4, self.config.p1))

        dropped = packet_loss_sample * eff
        delivered = (1.0 - packet_loss_sample) * eff

        self.sample_count += 1
        self.dropped_count += int(round(dropped))

        # Log-likelihood ratio delta
        delta_lambda = dropped * math.log(p1 / p0) + delivered * math.log((1.0 - p1) / (1.0 - p0))
        self.log_likelihood_ratio += delta_lambda
        self.trajectory.append(float(round(self.log_likelihood_ratio, 4)))

        boundary_a = self.config.boundary_a
        boundary_b = self.config.boundary_b

        if self.log_likelihood_ratio <= boundary_b:
            self.decision = "ACCEPT_H0_SUCCESS"
            self.early_stopped = True
        elif self.log_likelihood_ratio >= boundary_a:
            self.decision = "ACCEPT_H1_FAILURE"
            self.early_stopped = True
        elif self.sample_count >= self.config.max_samples:
            # Truncation horizon reached
            self.early_stopped = False
            self.decision = "ACCEPT_H0_SUCCESS" if self.log_likelihood_ratio <= 0.0 else "ACCEPT_H1_FAILURE"
        else:
            self.decision = "CONTINUE"

        return self.decision

    def get_state(self) -> SPRTState:
        return SPRTState(
            sample_count=self.sample_count,
            dropped_count=self.dropped_count,
            log_likelihood_ratio=round(self.log_likelihood_ratio, 4),
            boundary_a=round(self.config.boundary_a, 4),
            boundary_b=round(self.config.boundary_b, 4),
            decision=self.decision,
            early_stopped=self.early_stopped,
            trajectory=list(self.trajectory),
        )


class ClosedLoopVerifier:
    """
    Evaluates runtime telemetry following actuation dispatch.
    Verifies that the optimal mitigation actually restored nominal network operation
    without creating collateral damage (partitions, high loss, or severe latency).
    Supports adaptive stopping via Wald's Sequential Probability Ratio Test (SPRT).
    """

    def __init__(
        self,
        target_min_pdr: float = 0.88,
        max_acceptable_loss: float = 0.12,
        max_acceptable_latency_ms: float = 80.0,
        max_acceptable_cpu_pct: float = 25.0,
        verification_window_s: float = 10.0,
        sprt_config: Optional[SPRTConfig] = None,
        enable_sprt: bool = True,
    ):
        self.target_min_pdr = target_min_pdr
        self.max_loss = max_acceptable_loss
        self.max_latency_ms = max_acceptable_latency_ms
        self.max_cpu_pct = max_acceptable_cpu_pct
        self.verification_window_s = verification_window_s
        self.enable_sprt = enable_sprt
        self.sprt_verifier = WaldSPRTVerifier(config=sprt_config) if enable_sprt else None

        # Buffer for records collected during active verification
        self._verification_records: List[TelemetryRecord] = []
        self._window_start_time: Optional[float] = None
        self._current_batch_id: Optional[str] = None
        self._current_strategy_id: Optional[str] = None

    def start_verification(
        self,
        batch: ActuationBatch,
        start_time: float,
    ) -> None:
        """Initializes the verification window for a newly dispatched ActuationBatch."""
        self._current_batch_id = batch.batch_id
        self._current_strategy_id = batch.strategy_id
        self._window_start_time = start_time
        self._verification_records.clear()
        if self.sprt_verifier:
            self.sprt_verifier.reset()

    def ingest_telemetry_step(self, records: List[TelemetryRecord]) -> None:
        """Ingests step telemetry records during the verification window and updates SPRT."""
        self._verification_records.extend(records)
        if self.enable_sprt and self.sprt_verifier and records:
            step_loss = float(np.mean([r.packet_loss for r in records]))
            self.sprt_verifier.update(step_loss)

    def evaluate_verification(
        self,
        current_time: float,
        digital_twin: Optional[DigitalTwin] = None,
        force_finalize: bool = False,
    ) -> VerificationResult:
        """
        Evaluates criteria against collected telemetry.
        Returns intermediate or finalized VerificationResult.
        """
        batch_id = self._current_batch_id or "BATCH_UNKNOWN"
        strat_id = self._current_strategy_id or "STRAT_UNKNOWN"
        start_t = self._window_start_time if self._window_start_time is not None else current_time
        elapsed_s = max(0.0, current_time - start_t)

        if not self._verification_records:
            # No data yet
            return VerificationResult(
                batch_id=batch_id,
                strategy_id=strat_id,
                verification_status="VERIFYING",
                is_successful=False,
                criteria_results=[],
                verification_duration_s=elapsed_s,
                observed_pdr=1.0,
                observed_packet_loss=0.0,
                observed_latency_ms=12.0,
                observed_connected_components=1,
                failure_reason="Insufficient telemetry collected",
            )

        # Compute macroscopic averages across window records
        losses = [r.packet_loss for r in self._verification_records]
        latencies = [r.latency for r in self._verification_records]
        cpus = [r.cpu for r in self._verification_records]

        avg_loss = float(np.mean(losses)) if losses else 0.0
        avg_pdr = float(max(0.0, min(1.0, 1.0 - avg_loss)))
        avg_lat = float(np.mean(latencies)) if latencies else 12.0
        avg_cpu = float(np.mean(cpus)) if cpus else 10.0

        # Check graph reachability / components via Digital Twin if provided
        num_components = 1
        if digital_twin:
            g = digital_twin.get_network_topology()
            # Filter out known isolated nodes
            active_subgraph = g.copy()
            for nid, nstate in digital_twin.get_all_nodes().items():
                if nstate.connection_state == "DISCONNECTED" and active_subgraph.has_node(nid):
                    active_subgraph.remove_node(nid)
            if active_subgraph.number_of_nodes() > 1:
                num_components = nx.number_connected_components(active_subgraph)

        criteria: List[VerificationCriterion] = []

        # 1. Connectivity Check
        conn_passed = (num_components == 1)
        criteria.append(VerificationCriterion(
            criterion_name="Surviving Graph Reachability",
            metric_name="connected_components",
            threshold=1.0,
            operator="==",
            actual_value=float(num_components),
            passed=conn_passed,
            severity="CRITICAL",
            message="Single connected component verified." if conn_passed else f"Network partitioned into {num_components} components!",
        ))

        # 2. Minimum PDR Check
        pdr_passed = (avg_pdr >= self.target_min_pdr)
        criteria.append(VerificationCriterion(
            criterion_name="Packet Delivery Ratio Recovery",
            metric_name="pdr",
            threshold=self.target_min_pdr,
            operator=">=",
            actual_value=round(avg_pdr, 4),
            passed=pdr_passed,
            severity="CRITICAL",
            message=f"PDR {avg_pdr*100:.1f}% meets target {self.target_min_pdr*100:.1f}%." if pdr_passed else f"PDR {avg_pdr*100:.1f}% below recovery target {self.target_min_pdr*100:.1f}%.",
        ))

        # 3. Maximum Packet Loss Check
        loss_passed = (avg_loss <= self.max_loss)
        criteria.append(VerificationCriterion(
            criterion_name="Packet Loss Mitigation",
            metric_name="packet_loss",
            threshold=self.max_loss,
            operator="<=",
            actual_value=round(avg_loss, 4),
            passed=loss_passed,
            severity="CRITICAL",
            message=f"Packet loss {avg_loss*100:.1f}% within threshold {self.max_loss*100:.1f}%." if loss_passed else f"Packet loss {avg_loss*100:.1f}% exceeds threshold {self.max_loss*100:.1f}%.",
        ))

        # 4. Latency Deadline Check
        lat_passed = (avg_lat <= self.max_latency_ms)
        criteria.append(VerificationCriterion(
            criterion_name="End-to-End Latency Bound",
            metric_name="latency_ms",
            threshold=self.max_latency_ms,
            operator="<=",
            actual_value=round(avg_lat, 2),
            passed=lat_passed,
            severity="WARNING",
            message=f"Latency {avg_lat:.1f}ms within deadline {self.max_latency_ms:.1f}ms." if lat_passed else f"Latency {avg_lat:.1f}ms exceeded deadline {self.max_latency_ms:.1f}ms.",
        ))

        # 5. CPU Congestion Relief Check
        cpu_passed = (avg_cpu <= self.max_cpu_pct)
        criteria.append(VerificationCriterion(
            criterion_name="Compute Headroom Recovery",
            metric_name="cpu_utilization",
            threshold=self.max_cpu_pct,
            operator="<=",
            actual_value=round(avg_cpu, 2),
            passed=cpu_passed,
            severity="INFO",
            message=f"CPU utilization {avg_cpu:.1f}% stabilized." if cpu_passed else f"CPU utilization elevated at {avg_cpu:.1f}%.",
        ))

        # Determine overall verification status
        critical_passed = all(c.passed for c in criteria if c.severity == "CRITICAL")
        all_passed = all(c.passed for c in criteria)

        sprt_decision = self.sprt_verifier.decision if (self.enable_sprt and self.sprt_verifier) else None
        sprt_ll = self.sprt_verifier.log_likelihood_ratio if (self.enable_sprt and self.sprt_verifier) else None
        sprt_early = self.sprt_verifier.early_stopped if (self.enable_sprt and self.sprt_verifier) else False

        if not conn_passed:
            # Immediate catastrophic failure: graph partitioned!
            status = "VERIFICATION_FAILED"
            is_success = False
            reason = f"Actuation caused collateral network partition ({num_components} components)."
        elif self.enable_sprt and self.sprt_verifier and sprt_decision == "ACCEPT_H1_FAILURE":
            # Wald SPRT early rejection: persistent degradation/attack certified
            status = "VERIFICATION_FAILED"
            is_success = False
            reason = f"Wald SPRT early rejection: persistent degradation/attack detected (Lambda={sprt_ll:.2f} >= A={self.sprt_verifier.config.boundary_a:.2f})."
        elif self.enable_sprt and self.sprt_verifier and sprt_decision == "ACCEPT_H0_SUCCESS" and conn_passed and lat_passed:
            # Wald SPRT early acceptance: nominal recovery certified
            status = "VERIFIED_SUCCESS"
            is_success = True
            reason = f"Wald SPRT early verification certified nominal recovery (Lambda={sprt_ll:.2f} <= B={self.sprt_verifier.config.boundary_b:.2f})."
        elif elapsed_s >= self.verification_window_s or force_finalize:
            if critical_passed:
                status = "VERIFIED_SUCCESS"
                is_success = True
                reason = None
            else:
                status = "VERIFICATION_FAILED"
                is_success = False
                failing_criteria = [c.criterion_name for c in criteria if not c.passed and c.severity == "CRITICAL"]
                reason = f"Verification window expired with failing critical criteria: {', '.join(failing_criteria)}."
        else:
            # Window still ongoing
            if critical_passed:
                status = "VERIFYING"
                is_success = True
                reason = "Preliminary criteria satisfied; confirming stability."
            else:
                status = "VERIFYING"
                is_success = False
                reason = "Transient metrics converging; awaiting window completion."

        return VerificationResult(
            batch_id=batch_id,
            strategy_id=strat_id,
            verification_status=status,
            is_successful=is_success,
            criteria_results=criteria,
            verification_duration_s=round(elapsed_s, 2),
            observed_pdr=round(avg_pdr, 4),
            observed_packet_loss=round(avg_loss, 4),
            observed_latency_ms=round(avg_lat, 2),
            observed_connected_components=num_components,
            failure_reason=reason,
            sprt_decision=sprt_decision,
            sprt_log_likelihood=round(sprt_ll, 4) if sprt_ll is not None else None,
            sprt_early_stopped=sprt_early,
        )

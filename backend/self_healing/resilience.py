"""
Resilience Evaluator for Phase 9.
Computes quantitative recovery temporal responsiveness metrics (MTTD, MTTA, MTTR)
and the macroscopic integral Resilience Score R from post-incident telemetry.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from ..simulation.telemetry import TelemetryRecord
from .models import ResilienceMetrics


class ResilienceEvaluator:
    """
    Evaluates self-healing performance using mathematically grounded resilience theory.
    Quantifies incident recovery trajectories, resilience score R, and comparative advantages.
    """

    def __init__(
        self,
        base_nominal_latency_ms: float = 12.0,
        max_acceptable_latency_ms: float = 80.0,
        nominal_qos: float = 1.0,
    ):
        self.base_latency = base_nominal_latency_ms
        self.max_latency = max_acceptable_latency_ms
        self.nominal_qos = nominal_qos

    def compute_instantaneous_qos(
        self,
        pdr: float,
        latency_ms: float,
    ) -> float:
        """
        Calculates instantaneous QoS(t) combining packet delivery fidelity and latency penalty.
        QoS(t) = PDR(t) * (1.0 - clip((latency - base_latency) / max_latency, 0.0, 1.0))
        """
        lat_penalty = float(np.clip((latency_ms - self.base_latency) / self.max_latency, 0.0, 1.0))
        qos = float(np.clip(pdr * (1.0 - lat_penalty * 0.5), 0.0, 1.0))
        return round(qos, 4)

    def evaluate_incident_resilience(
        self,
        attack_type: str,
        t_attack_start: float,
        t_detect: float,
        t_actuate: float,
        t_restored: float,
        telemetry_records: List[TelemetryRecord],
        unmitigated_records: Optional[List[TelemetryRecord]] = None,
        sprt_verified: bool = False,
        escalation_tier: str = "TIER_1_PRIMARY_OPTIMAL",
    ) -> ResilienceMetrics:
        """
        Computes formal resilience metrics and trajectory integrals over the incident span.
        """
        # Temporal metrics
        mttd = max(0.0, t_detect - t_attack_start)
        mtta = max(0.0, t_actuate - t_detect)
        mttr = max(0.0, t_restored - t_detect)
        total_time = max(0.1, t_restored - t_attack_start)

        # Filter incident records within [t_attack_start, t_restored]
        window_records = [
            r for r in telemetry_records
            if t_attack_start <= r.timestamp <= t_restored + 1e-3
        ]

        # Aggregate per-timestep metrics
        timestep_dict: Dict[float, List[TelemetryRecord]] = {}
        for r in window_records:
            t = round(r.timestamp, 1)
            timestep_dict.setdefault(t, []).append(r)

        sorted_times = sorted(timestep_dict.keys())
        if not sorted_times:
            # Degenerate case fallback
            sorted_times = [t_attack_start, t_restored]
            pdr_curve = [1.0, 1.0]
            lat_curve = [self.base_latency, self.base_latency]
            qos_curve = [1.0, 1.0]
        else:
            pdr_curve = []
            lat_curve = []
            qos_curve = []
            for t in sorted_times:
                recs = timestep_dict[t]
                loss = float(np.mean([r.packet_loss for r in recs]))
                pdr = float(max(0.0, min(1.0, 1.0 - loss)))
                lat = float(np.mean([r.latency for r in recs]))
                qos = self.compute_instantaneous_qos(pdr, lat)

                pdr_curve.append(pdr)
                lat_curve.append(lat)
                qos_curve.append(qos)

        # Numerical integration of QoS curve: R = \int QoS(t) dt / (QoS_nominal * T)
        if len(sorted_times) >= 2:
            time_deltas = np.diff(sorted_times)
            # Trapezoidal integration
            integral_qos = float(np.sum(0.5 * (np.array(qos_curve[:-1]) + np.array(qos_curve[1:])) * time_deltas))
            total_span = sorted_times[-1] - sorted_times[0]
            if total_span > 0.0:
                resilience_r = float(np.clip(integral_qos / (self.nominal_qos * total_span), 0.0, 1.0))
            else:
                resilience_r = 1.0
        else:
            resilience_r = float(np.mean(qos_curve)) if qos_curve else 1.0

        resilience_loss_index = float(np.clip(1.0 - resilience_r, 0.0, 1.0))

        # Evaluate unmitigated counterfactual baseline
        unmitigated_r = 0.65  # Default reasonable estimate if unmitigated data not supplied
        if unmitigated_records:
            unmit_window = [
                r for r in unmitigated_records
                if t_attack_start <= r.timestamp <= t_restored + 1e-3
            ]
            unmit_dict: Dict[float, List[TelemetryRecord]] = {}
            for r in unmit_window:
                t = round(r.timestamp, 1)
                unmit_dict.setdefault(t, []).append(r)
            u_times = sorted(unmit_dict.keys())
            if len(u_times) >= 2:
                u_qos = []
                for t in u_times:
                    recs = unmit_dict[t]
                    loss = float(np.mean([r.packet_loss for r in recs]))
                    pdr = float(max(0.0, min(1.0, 1.0 - loss)))
                    lat = float(np.mean([r.latency for r in recs]))
                    u_qos.append(self.compute_instantaneous_qos(pdr, lat))
                u_deltas = np.diff(u_times)
                u_integral = float(np.sum(0.5 * (np.array(u_qos[:-1]) + np.array(u_qos[1:])) * u_deltas))
                u_span = u_times[-1] - u_times[0]
                unmitigated_r = float(np.clip(u_integral / (self.nominal_qos * u_span), 0.0, 1.0))

        # Bruneau Multi-Dimensional Resilience Metrics
        total_span = sorted_times[-1] - sorted_times[0] if len(sorted_times) >= 2 else total_time
        # Loss of Resilience: LOR = \int (1 - QoS(t)) dt
        lor = float(max(0.0, (1.0 - resilience_r) * total_span))
        # Structural Robustness: S_robust = min_t QoS(t)
        s_robust = float(np.min(qos_curve)) if qos_curve else 1.0
        # Recovery Rapidity: v_rec = Delta QoS / Delta t
        qos_actuate = float(np.interp(t_actuate, sorted_times, qos_curve))
        qos_restored = float(np.interp(t_restored, sorted_times, qos_curve))
        delta_rec_t = max(0.1, t_restored - t_actuate)
        v_rec = float(max(0.0, (qos_restored - qos_actuate) / delta_rec_t))

        advantage = float(resilience_r - unmitigated_r)

        return ResilienceMetrics(
            attack_type=attack_type,
            t_attack_start=t_attack_start,
            t_detect=t_detect,
            t_actuate=t_actuate,
            t_restored=t_restored,
            mttd_s=round(mttd, 2),
            mtta_s=round(mtta, 2),
            mttr_s=round(mttr, 2),
            total_incident_time_s=round(total_time, 2),
            resilience_score_r=round(resilience_r, 4),
            resilience_loss_index=round(resilience_loss_index, 4),
            unmitigated_resilience_score=round(unmitigated_r, 4),
            resilience_advantage_delta=round(advantage, 4),
            loss_of_resilience_lor=round(lor, 4),
            recovery_rapidity_v_rec=round(v_rec, 4),
            structural_robustness_s_robust=round(s_robust, 4),
            sprt_verified=sprt_verified,
            escalation_tier=escalation_tier,
            qos_trajectory={
                "timestamps": [round(t, 2) for t in sorted_times],
                "pdr": [round(p, 4) for p in pdr_curve],
                "latency": [round(l, 2) for l in lat_curve],
                "qos": [round(q, 4) for q in qos_curve],
            },
        )

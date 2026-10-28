"""
Behavioral Trust Evaluators for Resource-Constrained IoT Networks.
Computes four orthogonal sub-trust components:
1. Packet Forwarding Compliance (ForwardingFidelityEvaluator)
2. Energy Drain Consistency (EnergyConsistencyEvaluator)
3. Channel Loss Fidelity (ChannelLossFidelityEvaluator)
4. ML Security Threat Level (MLSecurityTrustEvaluator)
"""

from typing import Dict, Optional, Tuple, Any
import numpy as np

from .models import TrustComponents, TrustConfig
from ..digital_twin.models import TwinNodeState


class ForwardingFidelityEvaluator:
    """
    Evaluates packet forwarding compliance and delivery consistency.
    Detects gray-hole, black-hole, and selective packet dropping attacks.
    """

    def __init__(self, config: TrustConfig):
        self.config = config

    def evaluate(
        self,
        node_state: TwinNodeState,
        historical_states: Optional[list] = None
    ) -> float:
        """
        Computes forwarding compliance in [0.0, 1.0].
        If a node has active traffic demands, high packet loss severely penalizes trust.
        """
        if node_state.connection_state == "DISCONNECTED" or node_state.energy <= 0.0:
            return 0.0

        loss = node_state.packet_loss
        fwd_rate = node_state.forwarding_rate
        pkt_rate = node_state.packet_rate

        # If completely idle (0 pkt/s generated and 0 forwarded), trust remains nominal (1.0)
        total_activity = fwd_rate + pkt_rate
        if total_activity < 0.1 and loss < 0.05:
            return 1.0

        # Loss penalty curve: steep degradation as packet loss exceeds normal threshold
        if loss <= 0.03:
            return 1.0
        elif loss <= self.config.max_expected_packet_loss:
            # Linear mild penalty in normal fading regime
            penalty = (loss - 0.03) / (self.config.max_expected_packet_loss - 0.03) * 0.20
            return float(np.clip(1.0 - penalty, 0.0, 1.0))
        else:
            # Severe penalty when loss exceeds wireless fading expectation
            excess = (loss - self.config.max_expected_packet_loss) / (1.0 - self.config.max_expected_packet_loss)
            score = 0.75 * (1.0 - excess ** 1.2)
            return float(np.clip(score, 0.0, 1.0))


class EnergyConsistencyEvaluator:
    """
    Evaluates whether battery depletion velocity matches legitimate communication demands.
    Detects battery exhaustion (vampire attacks), flooding-induced drain, and sudden drop-offs.
    """

    def __init__(self, config: TrustConfig):
        self.config = config

    def evaluate(
        self,
        node_state: TwinNodeState,
        historical_states: Optional[list] = None
    ) -> float:
        """
        Computes energy consistency score in [0.0, 1.0].
        """
        if node_state.energy <= 0.0:
            return 0.0

        # Base score from remaining battery reserve
        # Severe penalty if battery is critically low (< 5%)
        if node_state.energy < 5.0:
            reserve_factor = node_state.energy / 5.0
        else:
            reserve_factor = 1.0

        # If historical states exist, evaluate energy depletion rate delta_E / delta_t
        drain_rate = 0.0
        if historical_states and len(historical_states) >= 2:
            prev_state = historical_states[-2]
            dt = max(0.1, node_state.timestamp - prev_state.timestamp)
            d_energy = max(0.0, prev_state.energy - node_state.energy)
            drain_rate = d_energy / dt  # % energy consumed per second

        # Expected nominal drain given current activity
        total_traffic = node_state.packet_rate + node_state.forwarding_rate
        expected_drain = 0.005 + (total_traffic * self.config.nominal_energy_drain_per_pkt)
        tolerated_drain = expected_drain * self.config.energy_tolerance_multiplier

        if drain_rate <= tolerated_drain:
            drain_score = 1.0
        else:
            # Penalize anomalous vampire / flooding drain
            excess_ratio = min(5.0, (drain_rate - tolerated_drain) / max(0.001, tolerated_drain))
            drain_score = float(np.clip(1.0 - (excess_ratio * 0.25), 0.0, 1.0))

        # CPU utilization penalty if pinned near 100%
        cpu_penalty = 0.0
        if node_state.cpu > 85.0:
            cpu_penalty = (node_state.cpu - 85.0) / 15.0 * 0.30

        score = reserve_factor * drain_score - cpu_penalty
        return float(np.clip(score, 0.0, 1.0))


class ChannelLossFidelityEvaluator:
    """
    Evaluates whether reported packet loss aligns with physical wireless channel conditions (RSSI).
    Differentiates physical channel fading from malicious selective dropping.
    """

    def __init__(self, config: TrustConfig):
        self.config = config

    def evaluate(
        self,
        node_state: TwinNodeState,
        historical_states: Optional[list] = None
    ) -> float:
        """
        Computes channel loss fidelity in [0.0, 1.0].
        If RSSI is strong (-50 dBm) but loss is 50%, fidelity collapses to near 0.
        If RSSI is weak (-95 dBm) and loss is 40%, loss is physically justified.
        """
        if node_state.connection_state == "DISCONNECTED" or node_state.energy <= 0.0:
            return 0.0

        rssi = node_state.rssi
        loss = node_state.packet_loss

        # Estimate physically justified packet loss from RSSI using empirical RF model:
        # Strong signal (> -75 dBm): expected loss < 2%
        # Medium signal (-75 to -90 dBm): expected loss 2% to 15%
        # Weak signal (< -90 dBm): expected loss up to 35%
        if rssi >= -75.0:
            expected_loss = 0.02
        elif rssi >= -90.0:
            ratio = (rssi - (-90.0)) / 15.0
            expected_loss = 0.15 - (ratio * 0.13)
        else:
            ratio = max(0.0, (rssi - (-110.0)) / 20.0)
            expected_loss = 0.40 - (ratio * 0.25)

        # Discrepancy between actual loss and physically explainable loss
        unexplained_loss = max(0.0, loss - expected_loss)

        if unexplained_loss <= 0.02:
            return 1.0
        else:
            # Sharp penalty for unexplained packet loss under strong signal
            fidelity = 1.0 - (unexplained_loss * 2.2)
            return float(np.clip(fidelity, 0.0, 1.0))


class MLSecurityTrustEvaluator:
    """
    Translates calibrated posterior cyberattack probabilities from Phase 5 into security trust.
    P_attack = 0.0 -> ML Trust = 1.0 (Completely Benign)
    P_attack = 1.0 -> ML Trust = 0.0 (Confirmed Cyberattack)
    """

    def __init__(self, config: TrustConfig):
        self.config = config

    def evaluate(self, attack_probability: float) -> float:
        """
        Direct monotonic mapping from calibrated probability to security trust score.
        """
        p = float(np.clip(attack_probability, 0.0, 1.0))
        return float(1.0 - p)


class BayesianRecommendationEvaluator:
    """
    Bayesian Beta-Binomial Neighbor Recommendation Evaluator with Subjective Logic Discounting
    and Median Absolute Deviation (MAD) Collusion / Ballot-Stuffing Filtering.
    """

    def __init__(self, prior_alpha: float = 1.0, prior_beta: float = 1.0):
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta

    def evaluate_recommendations(
        self,
        recommendations: Dict[int, float],
        recommender_trust_scores: Optional[Dict[int, float]] = None
    ) -> float:
        """
        Aggregates neighbor recommendations r_{j -> i} in [0.0, 1.0] with:
        1. Subjective Logic Trust Discounting: weights opinion by recommender's own trust T_j.
        2. Consensus Outlier Filtering: discards ballot-stuffing / bad-mouthing deviations.
        3. Beta posterior expected value: E[theta] = alpha / (alpha + beta).
        """
        if not recommendations:
            return 1.0

        scores = list(recommendations.values())
        if len(scores) == 1:
            r_id, r_score = next(iter(recommendations.items()))
            t_j = recommender_trust_scores.get(r_id, 0.80) if recommender_trust_scores else 0.80
            discounted = (t_j * r_score) + ((1.0 - t_j) * 0.50)
            return float(np.clip(discounted, 0.0, 1.0))

        # 1. Consensus Filtering: compute median recommendation
        med = float(np.median(scores))
        mad = float(np.median([abs(s - med) for s in scores]))
        outlier_margin = max(0.25, 2.0 * mad)

        filtered_recs = {}
        for r_id, rec_val in recommendations.items():
            if abs(rec_val - med) <= outlier_margin:
                filtered_recs[r_id] = rec_val

        if not filtered_recs:
            filtered_recs = recommendations

        # 2. Subjective Logic Trust Discounting
        alpha = self.prior_alpha
        beta = self.prior_beta

        for r_id, r_score in filtered_recs.items():
            # If recommender's own trust is known, discount their opinion
            t_j = recommender_trust_scores.get(r_id, 0.80) if recommender_trust_scores else 0.80
            weight = float(np.clip(t_j, 0.10, 1.0))

            # Discounted observation
            alpha += weight * r_score * 5.0
            beta += weight * (1.0 - r_score) * 5.0

        expected_trust = alpha / (alpha + beta)
        return float(np.clip(expected_trust, 0.0, 1.0))


class CompositeTrustEvaluator:
    """
    Coordinates and computes all trust components, returning a TrustComponents
    object and the instantaneous composite trust score.
    """

    def __init__(self, config: Optional[TrustConfig] = None):
        self.config = config or TrustConfig()
        self.fwd_eval = ForwardingFidelityEvaluator(self.config)
        self.energy_eval = EnergyConsistencyEvaluator(self.config)
        self.loss_eval = ChannelLossFidelityEvaluator(self.config)
        self.ml_eval = MLSecurityTrustEvaluator(self.config)
        self.rec_eval = BayesianRecommendationEvaluator()

    def evaluate_node(
        self,
        node_state: TwinNodeState,
        attack_probability: float = 0.0,
        historical_states: Optional[list] = None,
        neighbor_recommendations: Optional[Dict[int, float]] = None,
        recommender_trust_scores: Optional[Dict[int, float]] = None
    ) -> Tuple[TrustComponents, float]:
        """
        Evaluates an individual node and returns (TrustComponents, instantaneous_trust).
        """
        t_fwd = self.fwd_eval.evaluate(node_state, historical_states)
        t_energy = self.energy_eval.evaluate(node_state, historical_states)
        t_loss = self.loss_eval.evaluate(node_state, historical_states)
        t_ml = self.ml_eval.evaluate(attack_probability)

        t_rec = 1.0
        if neighbor_recommendations:
            t_rec = self.rec_eval.evaluate_recommendations(
                neighbor_recommendations,
                recommender_trust_scores=recommender_trust_scores
            )

        components = TrustComponents(
            forwarding_trust=round(t_fwd, 4),
            energy_trust=round(t_energy, 4),
            loss_trust=round(t_loss, 4),
            ml_trust=round(t_ml, 4),
            recommendation_trust=round(t_rec, 4),
        )

        instantaneous_trust = (
            self.config.weight_forwarding * t_fwd +
            self.config.weight_energy * t_energy +
            self.config.weight_loss * t_loss +
            self.config.weight_ml * t_ml
        )
        instantaneous_trust = float(np.clip(instantaneous_trust, 0.0, 1.0))

        return components, instantaneous_trust


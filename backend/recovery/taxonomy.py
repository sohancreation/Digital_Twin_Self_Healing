"""
Mitigation Action Taxonomy & Candidate Builders.
Constructs concrete, parameterized RecoveryCandidate instances representing
the 6 standard self-healing actions.
"""

from typing import Dict, List, Optional, Tuple, Any
import networkx as nx

from .models import RecoveryCandidate, RecoveryConfig
from .feasibility import FeasibilityChecker
from ..digital_twin.models import TwinNodeState


def build_no_action_candidate(timestamp: float = 0.0) -> RecoveryCandidate:
    """
    Constructs the null baseline candidate (status quo / monitoring).
    Serves as the zero-cost benchmark in multi-objective trade-off evaluation.
    """
    return RecoveryCandidate(
        strategy_id="STRAT_NO_ACTION",
        action_type="NO_ACTION",
        target_nodes=[],
        affected_nodes=[],
        parameters={},
        estimated_cost=0.0,
        is_topology_partitioning=False,
        expected_recovery_time_s=0.0,
        rationale="Maintain nominal operation without active intervention; continuous monitoring."
    )


def build_isolation_candidate(
    target_node: int,
    graph: nx.Graph,
    config: Optional[RecoveryConfig] = None,
    checker: Optional[FeasibilityChecker] = None
) -> RecoveryCandidate:
    """
    Constructs a NODE_ISOLATION candidate severing all links to target_node.
    """
    cfg = config or RecoveryConfig()
    chk = checker or FeasibilityChecker()

    is_partitioning, num_comps, _ = chk.check_isolation_partition(graph, target_node)
    neighbors = list(graph.neighbors(target_node)) if target_node in graph else []

    cost = cfg.base_action_costs.get("NODE_ISOLATION", 3.0)
    if is_partitioning:
        cost += 3.0  # Higher penalty if it induces topological partitioning

    rationale = (
        f"Isolate compromised/failing Node {target_node} by severing {len(neighbors)} links. "
        f"{'WARNING: Induces ' + str(num_comps) + ' partitioned components.' if is_partitioning else 'Topology remains connected.'}"
    )

    return RecoveryCandidate(
        strategy_id=f"STRAT_ISO_{target_node}",
        action_type="NODE_ISOLATION",
        target_nodes=[target_node],
        affected_nodes=neighbors,
        parameters={"severed_links": [(target_node, n) for n in neighbors]},
        estimated_cost=round(cost, 2),
        is_topology_partitioning=is_partitioning,
        expected_recovery_time_s=1.0,
        rationale=rationale
    )


def build_reroute_candidate(
    target_node: int,
    graph: nx.Graph,
    config: Optional[RecoveryConfig] = None,
    checker: Optional[FeasibilityChecker] = None
) -> Optional[RecoveryCandidate]:
    """
    Constructs a DYNAMIC_REROUTING candidate synthesizing loop-free bypass paths.
    Returns None if no alternate routes exist.
    """
    cfg = config or RecoveryConfig()
    chk = checker or FeasibilityChecker()

    alternate_routes = chk.find_alternate_routes(graph, target_node)
    valid_routes = {
        f"{src}->{dst}": path for (src, dst), path in alternate_routes.items()
        if path is not None
    }

    if not valid_routes and alternate_routes:
        # All alternate paths blocked
        return None

    neighbors = list(graph.neighbors(target_node)) if target_node in graph else []
    cost = cfg.base_action_costs.get("DYNAMIC_REROUTING", 2.5)

    return RecoveryCandidate(
        strategy_id=f"STRAT_REROUTE_{target_node}",
        action_type="DYNAMIC_REROUTING",
        target_nodes=[target_node],
        affected_nodes=neighbors,
        parameters={"bypass_routes": valid_routes},
        estimated_cost=round(cost, 2),
        is_topology_partitioning=False,
        expected_recovery_time_s=2.0,
        rationale=f"Reroute transit traffic around Node {target_node} via {len(valid_routes)} alternative loop-free paths."
    )


def build_rate_limit_candidate(
    target_node: int,
    current_packet_rate: float,
    rate_cap_pkts_sec: Optional[float] = None,
    config: Optional[RecoveryConfig] = None
) -> RecoveryCandidate:
    """
    Constructs a RATE_LIMITING candidate clamping ingress traffic from a DoS / flooding node.
    """
    cfg = config or RecoveryConfig()
    cap = rate_cap_pkts_sec or cfg.default_rate_limit_pkts_sec

    cost = cfg.base_action_costs.get("RATE_LIMITING", 1.0)
    reduction_pct = max(0.0, (current_packet_rate - cap) / max(0.1, current_packet_rate)) * 100.0

    # Token bucket parameters
    burst_tolerance = 5
    bucket_capacity = round(cap * burst_tolerance, 1)

    return RecoveryCandidate(
        strategy_id=f"STRAT_THROTTLE_{target_node}",
        action_type="RATE_LIMITING",
        target_nodes=[target_node],
        affected_nodes=[],
        parameters={
            "ingress_rate_cap_pkts_sec": cap,
            "previous_packet_rate": current_packet_rate,
            "rate_reduction_pct": round(reduction_pct, 1),
            "token_refill_rate_pkts_sec": cap,
            "bucket_capacity_pkts": bucket_capacity,
            "burst_tolerance_pkts": burst_tolerance,
        },
        estimated_cost=round(cost, 2),
        is_topology_partitioning=False,
        expected_recovery_time_s=1.0,
        rationale=f"Clamp ingress packet generation on Node {target_node} from {current_packet_rate:.1f} to {cap:.1f} pkts/s ({reduction_pct:.0f}% reduction, TokenBucket capacity={bucket_capacity}) to clear buffer congestion."
    )


def build_reboot_candidate(
    target_node: int,
    reboot_duration_s: Optional[float] = None,
    config: Optional[RecoveryConfig] = None
) -> RecoveryCandidate:
    """
    Constructs a NODE_REBOOT candidate soft-power cycling a crashed, frozen, or compromised node.
    """
    cfg = config or RecoveryConfig()
    duration = reboot_duration_s or cfg.default_reboot_duration_s
    cost = cfg.base_action_costs.get("NODE_REBOOT", 5.0)

    return RecoveryCandidate(
        strategy_id=f"STRAT_REBOOT_{target_node}",
        action_type="NODE_REBOOT",
        target_nodes=[target_node],
        affected_nodes=[],
        parameters={"reboot_duration_s": duration, "flush_buffers": True, "reset_registers": True},
        estimated_cost=round(cost, 2),
        is_topology_partitioning=False,
        expected_recovery_time_s=duration,
        rationale=f"Power cycle and reset volatile memory on Node {target_node} with {duration:.1f}s soft reboot."
    )


def build_power_adjustment_candidate(
    target_node: int,
    graph: nx.Graph,
    node_states: Dict[int, TwinNodeState],
    boost_dbm: Optional[float] = None,
    config: Optional[RecoveryConfig] = None,
    checker: Optional[FeasibilityChecker] = None
) -> Optional[RecoveryCandidate]:
    """
    Constructs a POWER_ADJUSTMENT candidate boosting transmission power of neighbors
    to bridge across an isolated or dead node.
    """
    cfg = config or RecoveryConfig()
    chk = checker or FeasibilityChecker()
    boost = boost_dbm or cfg.default_power_boost_dbm

    neighbors = list(graph.neighbors(target_node)) if target_node in graph else []
    if len(neighbors) < 2:
        return None

    # Check energy feasibility of neighbors
    is_feasible = chk.check_power_boost_feasibility(node_states, neighbors, min_energy_threshold=20.0)
    if not is_feasible:
        return None

    cost = cfg.base_action_costs.get("POWER_ADJUSTMENT", 4.0)

    return RecoveryCandidate(
        strategy_id=f"STRAT_PWR_BOOST_{target_node}",
        action_type="POWER_ADJUSTMENT",
        target_nodes=[target_node],
        affected_nodes=neighbors,
        parameters={"power_boost_dbm": boost, "boosting_nodes": neighbors},
        estimated_cost=round(cost, 2),
        is_topology_partitioning=False,
        expected_recovery_time_s=1.5,
        rationale=f"Elevate RF transmission power by +{boost:.1f} dBm on {len(neighbors)} neighbors to bridge topological gap around Node {target_node}."
    )


def build_composite_isolate_and_bridge_candidate(
    target_node: int,
    graph: nx.Graph,
    node_states: Dict[int, TwinNodeState],
    boost_dbm: Optional[float] = None,
    config: Optional[RecoveryConfig] = None,
    checker: Optional[FeasibilityChecker] = None
) -> Optional[RecoveryCandidate]:
    """
    Constructs a synergistic COMPOSITE candidate that simultaneously severs links to target_node
    while boosting RF transmission power on surviving neighbors to bridge the cut-vertex gap.
    Guarantees that the resulting network remains connected (is_topology_partitioning=False).
    """
    cfg = config or RecoveryConfig()
    chk = checker or FeasibilityChecker()
    boost = boost_dbm or cfg.default_power_boost_dbm

    neighbors = list(graph.neighbors(target_node)) if target_node in graph else []
    if len(neighbors) < 2:
        return None

    is_feasible = chk.check_power_boost_feasibility(node_states, neighbors, min_energy_threshold=20.0)
    if not is_feasible:
        return None

    # Cost reflects both actions executed cooperatively
    cost = cfg.base_action_costs.get("COMPOSITE", 5.5)

    return RecoveryCandidate(
        strategy_id=f"STRAT_COMP_ISO_BRIDGE_{target_node}",
        action_type="COMPOSITE",
        target_nodes=[target_node],
        affected_nodes=neighbors,
        parameters={
            "sub_actions": ["NODE_ISOLATION", "POWER_ADJUSTMENT"],
            "severed_links": [(target_node, n) for n in neighbors],
            "power_boost_dbm": boost,
            "boosting_nodes": neighbors,
        },
        estimated_cost=round(cost, 2),
        is_topology_partitioning=False,  # Partition is actively bridged by power boost!
        expected_recovery_time_s=2.0,
        rationale=(
            f"Synergistic mitigation: Isolate compromised Node {target_node} while concurrently "
            f"elevating Tx power (+{boost:.1f} dBm) on neighbors {neighbors} to prevent network partition."
        )
    )


def build_composite_throttle_and_reroute_candidate(
    target_node: int,
    graph: nx.Graph,
    current_packet_rate: float,
    rate_cap_pkts_sec: Optional[float] = None,
    config: Optional[RecoveryConfig] = None,
    checker: Optional[FeasibilityChecker] = None
) -> Optional[RecoveryCandidate]:
    """
    Constructs a synergistic COMPOSITE candidate combining ingress rate-limiting with dynamic
    rerouting of transit flows around target_node.
    """
    cfg = config or RecoveryConfig()
    chk = checker or FeasibilityChecker()
    cap = rate_cap_pkts_sec or cfg.default_rate_limit_pkts_sec

    alternate_routes = chk.find_alternate_routes(graph, target_node)
    valid_routes = {
        f"{src}->{dst}": path for (src, dst), path in alternate_routes.items()
        if path is not None
    }
    neighbors = list(graph.neighbors(target_node)) if target_node in graph else []

    cost = cfg.base_action_costs.get("COMPOSITE", 4.0)
    reduction_pct = max(0.0, (current_packet_rate - cap) / max(0.1, current_packet_rate)) * 100.0

    return RecoveryCandidate(
        strategy_id=f"STRAT_COMP_THROTTLE_REROUTE_{target_node}",
        action_type="COMPOSITE",
        target_nodes=[target_node],
        affected_nodes=neighbors,
        parameters={
            "sub_actions": ["RATE_LIMITING", "DYNAMIC_REROUTING"],
            "ingress_rate_cap_pkts_sec": cap,
            "bypass_routes": valid_routes,
            "rate_reduction_pct": round(reduction_pct, 1),
        },
        estimated_cost=round(cost, 2),
        is_topology_partitioning=False,
        expected_recovery_time_s=2.0,
        rationale=(
            f"Synergistic mitigation: Throttle Node {target_node} to {cap:.1f} pkts/s while "
            f"dynamically diverting transit flows through {len(valid_routes)} loop-free bypass paths."
        )
    )


"""
Large-Scale Experimental Benchmark Suite: 30 Seeds x 4 Threat Vectors.
Executes 480 benchmark runs (4 baselines x 4 attacks x 30 seeds).
Computes Mean, SD, Median, IQR, and full Inferential Statistics.
Outputs summary JSON, LaTeX table, and verification metrics.
"""

import sys
import time
import json
import math
from pathlib import Path
from typing import Dict, List, Any, Tuple

import numpy as np
import scipy.stats as stats

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.experiments.models import BaselineType, BenchmarkConfig, ExperimentRunResult
from backend.experiments.runner import ExperimentRunner
from backend.experiments.statistics import StatisticalEvaluator

RESULTS_DIR = ROOT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def execute_large_scale_campaign():
    seeds = list(range(42, 72))  # 30 seeds: 42 to 71
    attacks = ["dos", "compromised_node", "node_failure", "on_off"]
    baselines = [
        BaselineType.UNMITIGATED,
        BaselineType.STATIC_THRESHOLD_ISOLATION,
        BaselineType.ML_FIXED_RECOVERY,
        BaselineType.PROPOSED_DIGITAL_TWIN,
    ]

    total_scenarios = len(seeds) * len(attacks)  # 120 matched scenarios
    total_runs = total_scenarios * len(baselines)  # 480 runs

    print("=" * 80)
    print(f"STARTING 480-RUN BENCHMARK CAMPAIGN")
    print(f"Seeds: {len(seeds)} (42..{seeds[-1]}) | Attacks: {attacks} | Baselines: 4")
    print(f"Total Matched Scenario Pairs: {total_scenarios}")
    print("=" * 80)

    runner = ExperimentRunner()
    results: List[ExperimentRunResult] = []

    t0 = time.perf_counter()
    run_idx = 0

    for b in baselines:
        for atk in attacks:
            for s in seeds:
                run_idx += 1
                res = runner.run_single_experiment(
                    baseline_type=b,
                    attack_type=atk,
                    seed=s,
                    duration_s=80.0,
                    attack_start_s=20.0,
                    attack_end_s=60.0,
                )
                results.append(res)
                if run_idx % 40 == 0 or run_idx == total_runs:
                    elapsed = time.perf_counter() - t0
                    rate = run_idx / elapsed
                    remaining = (total_runs - run_idx) / rate
                    print(f"  [{run_idx}/{total_runs}] ({run_idx/total_runs*100:.1f}%) "
                          f"Elapsed: {elapsed:.1f}s | Est. Remaining: {remaining:.1f}s")

    total_time = time.perf_counter() - t0
    print(f"\nAll 480 runs completed in {total_time:.2f} seconds ({total_runs/total_time:.1f} runs/sec).")

    # =========================================================================
    # Aggregations by Strategy
    # =========================================================================
    metrics = ["resilience_score", "mean_pdr", "min_pdr", "partition_rate", "energy_consumed_j", "mttr_s"]
    strat_summary = {}

    for b in baselines:
        b_runs = [r for r in results if r.baseline == b]
        strat_summary[b.value] = {}
        for m in metrics:
            vals = [getattr(r, m) for r in b_runs if getattr(r, m) is not None]
            if not vals and m == "mttr_s":
                strat_summary[b.value][m] = {"mean": None, "std": None, "median": None, "iqr": None}
                continue
            arr = np.array(vals, dtype=float)
            q25, q75 = float(np.percentile(arr, 25)), float(np.percentile(arr, 75))
            strat_summary[b.value][m] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr, ddof=1)),
                "median": float(np.median(arr)),
                "iqr": float(q75 - q25),
                "q25": q25,
                "q75": q75,
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "n": len(arr),
            }

    # =========================================================================
    # Inferential Statistics: Proposed vs. Baseline 2 (Static IDS)
    # n = 120 matched scenario pairs (same seed and same attack)
    # =========================================================================
    prop_runs = [r for r in results if r.baseline == BaselineType.PROPOSED_DIGITAL_TWIN]
    b2_runs = [r for r in results if r.baseline == BaselineType.STATIC_THRESHOLD_ISOLATION]

    # Map by (attack_type, seed)
    prop_map = {(r.attack_type, r.seed): r for r in prop_runs}
    b2_map = {(r.attack_type, r.seed): r for r in b2_runs}

    matched_pairs = []
    for k in prop_map:
        if k in b2_map:
            matched_pairs.append((prop_map[k], b2_map[k]))

    n_pairs = len(matched_pairs)
    print(f"\nEvaluating inferential statistics over n={n_pairs} matched scenario pairs...")

    # Partition rate differences (in percentage points: B2% - Proposed%)
    p_prop = np.array([p.partition_rate * 100.0 for p, _ in matched_pairs])
    p_b2 = np.array([b.partition_rate * 100.0 for _, b in matched_pairs])
    diff_part = p_b2 - p_prop  # positive means proposed suppresses partition

    paired_diff_mean = float(np.mean(diff_part))
    paired_diff_std = float(np.std(diff_part, ddof=1))
    se_diff = paired_diff_std / math.sqrt(n_pairs)
    ci_95 = (paired_diff_mean - 1.96 * se_diff, paired_diff_mean + 1.96 * se_diff)

    # Paired t-test
    t_stat_paired, p_val_paired = stats.ttest_rel(p_b2, p_prop)

    # Wilcoxon signed-rank test
    try:
        w_stat, p_val_wilcoxon = stats.wilcoxon(p_b2, p_prop)
    except Exception:
        w_stat, p_val_wilcoxon = 0.0, 1.0

    # Independent Welch's t-test
    t_stat_welch, p_val_welch = stats.ttest_ind(p_b2, p_prop, equal_var=False)

    # Cohen's d (paired)
    cohens_d = paired_diff_mean / paired_diff_std if paired_diff_std > 1e-9 else 0.0

    # Empirical Statistical Power
    crit_t = stats.t.ppf(0.975, df=n_pairs - 1)
    ncp = cohens_d * math.sqrt(n_pairs)
    power = float(1.0 - stats.norm.cdf(1.96 - ncp) + stats.norm.cdf(-1.96 - ncp))

    # Bayes Factor BF_10 approximation via BIC
    bic_diff = (t_stat_paired ** 2) - math.log(n_pairs)
    bf_10 = float(math.exp(np.clip(bic_diff / 2.0, -50.0, 50.0)))

    # Per-attack partition breakdown
    attack_breakdown = {}
    for atk in attacks:
        atk_prop = [p.partition_rate * 100.0 for p, b in matched_pairs if p.attack_type == atk]
        atk_b2 = [b.partition_rate * 100.0 for p, b in matched_pairs if p.attack_type == atk]
        atk_b3 = [r.partition_rate * 100.0 for r in results if r.baseline == BaselineType.ML_FIXED_RECOVERY and r.attack_type == atk]
        attack_breakdown[atk] = {
            "prop_mean": float(np.mean(atk_prop)),
            "prop_median": float(np.median(atk_prop)),
            "prop_iqr": float(np.percentile(atk_prop, 75) - np.percentile(atk_prop, 25)),
            "b2_mean": float(np.mean(atk_b2)),
            "b2_median": float(np.median(atk_b2)),
            "b3_mean": float(np.mean(atk_b3)),
            "b3_median": float(np.median(atk_b3)),
        }

    # Summary payload
    summary_data = {
        "n_seeds": len(seeds),
        "n_attacks": len(attacks),
        "n_matched_pairs": n_pairs,
        "total_runs": total_runs,
        "runtime_s": total_time,
        "strategy_summary": strat_summary,
        "attack_breakdown": attack_breakdown,
        "inferential_statistics": {
            "paired_diff_mean_pp": paired_diff_mean,
            "paired_diff_std_pp": paired_diff_std,
            "ci_95": ci_95,
            "paired_t_stat": float(t_stat_paired),
            "paired_t_df": n_pairs - 1,
            "paired_p_val": float(p_val_paired),
            "wilcoxon_w": float(w_stat),
            "wilcoxon_p": float(p_val_wilcoxon),
            "welch_t_stat": float(t_stat_welch),
            "welch_p_val": float(p_val_welch),
            "cohens_d": cohens_d,
            "statistical_power": power,
            "bayes_factor_10": bf_10,
        }
    }

    out_json = RESULTS_DIR / "large_scale_benchmark_summary_30seeds.json"
    with open(out_json, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"\n[SAVED] Benchmark summary -> {out_json}")

    # Print Key Results Table
    print("\n" + "=" * 100)
    print(f"{'Strategy':<32} | {'Resilience (R)':<16} | {'Mean PDR':<16} | {'Nadir PDR':<16} | {'Partition % (Mean±SD)':<22} | {'Partition (Med [IQR])':<20}")
    print("-" * 100)
    for b in baselines:
        b_key = b.value
        s = strat_summary[b_key]
        r_str = f"{s['resilience_score']['mean']:.4f}±{s['resilience_score']['std']:.3f}"
        pdr_str = f"{s['mean_pdr']['mean']:.4f}±{s['mean_pdr']['std']:.3f}"
        nadir_str = f"{s['min_pdr']['mean']:.4f}±{s['min_pdr']['std']:.3f}"
        part_str = f"{s['partition_rate']['mean']*100:.2f}% ± {s['partition_rate']['std']*100:.2f}%"
        med_str = f"{s['partition_rate']['median']*100:.2f}% [{s['partition_rate']['iqr']*100:.2f}%]"
        print(f"{b_key:<32} | {r_str:<16} | {pdr_str:<16} | {nadir_str:<16} | {part_str:<22} | {med_str:<20}")
    print("=" * 100)

    print("\nPer-Attack Partition Rate Breakdown:")
    for atk, bdown in attack_breakdown.items():
        print(f"  - {atk:<18}: Proposed={bdown['prop_mean']:.2f}% (Med: {bdown['prop_median']:.2f}%) vs B2={bdown['b2_mean']:.2f}% (Med: {bdown['b2_median']:.2f}%)")

    print("\nInferential Statistics (Proposed vs. B2, n=120):")
    print(f"  Paired diff: {paired_diff_mean:.2f} ± {paired_diff_std:.2f} pp (95% CI [{ci_95[0]:.2f}, {ci_95[1]:.2f}])")
    print(f"  Paired t({n_pairs - 1}) = {t_stat_paired:.2f}, p = {p_val_paired:.4e}")
    print(f"  Wilcoxon W = {w_stat:.1f}, p = {p_val_wilcoxon:.4e}")
    print(f"  Cohen's d = {cohens_d:.3f}, Power = {power:.4f}, BF10 = {bf_10:.2e}")

    return summary_data


if __name__ == "__main__":
    execute_large_scale_campaign()

"""
Statistical Evaluation and Significance Testing Module for Phase 11.
Provides rigorous multi-seed aggregation, confidence intervals, Welch's t-tests,
p-values, Cohen's d effect sizes, and comparative matrix generation.
"""

import math
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from scipy import stats

from .models import BaselineType, ExperimentRunResult, StatisticalComparison


class StatisticalEvaluator:
    """
    Computes rigorous academic statistics, hypothesis testing, and effect sizes
    comparing the Proposed Digital Twin Framework against all baseline architectures.
    """

    @staticmethod
    def compute_summary_stats(values: List[float]) -> Dict[str, float]:
        """Calculates sample mean, standard deviation, median, IQR, and standard error."""
        if not values:
            return {
                "mean": 0.0, "std": 0.0, "median": 0.0, "iqr": 0.0,
                "q25": 0.0, "q75": 0.0, "se": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "n": 0
            }

        arr = np.array(values, dtype=float)
        n = len(arr)
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
        median = float(np.median(arr))
        q25 = float(np.percentile(arr, 25))
        q75 = float(np.percentile(arr, 75))
        iqr = float(q75 - q25)
        zero_rate_pct = float(np.mean(arr == 0.0) * 100.0)
        zero_count = int(np.sum(arr == 0.0))
        se = float(std / math.sqrt(n)) if n > 1 else 0.0

        if n > 1 and std > 1e-12:
            ci_range = stats.t.ppf(0.975, df=n - 1) * se
        else:
            ci_range = 1.96 * se

        return {
            "mean": mean,
            "std": std,
            "median": median,
            "iqr": iqr,
            "q25": q25,
            "q75": q75,
            "zero_rate_pct": zero_rate_pct,
            "zero_count": zero_count,
            "se": se,
            "ci_lower": mean - ci_range,
            "ci_upper": mean + ci_range,
            "n": n,
        }

    @staticmethod
    def compare_distributions(
        proposed_vals: List[float],
        baseline_vals: List[float],
        metric_name: str,
        baseline_type: BaselineType,
        higher_is_better: bool = True,
    ) -> StatisticalComparison:
        """
        Executes a two-sample Welch's t-test (unequal variances assumed) and
        calculates Cohen's d effect size between Proposed and Baseline.
        """
        p_arr = np.array(proposed_vals, dtype=float)
        b_arr = np.array(baseline_vals, dtype=float)

        p_mean = float(np.mean(p_arr))
        b_mean = float(np.mean(b_arr))
        p_std = float(np.std(p_arr, ddof=1)) if len(p_arr) > 1 else 0.0
        b_std = float(np.std(b_arr, ddof=1)) if len(b_arr) > 1 else 0.0

        delta_mean = p_mean - b_mean
        if abs(b_mean) > 1e-9:
            pct_imp = (delta_mean / abs(b_mean)) * 100.0 if higher_is_better else (-delta_mean / abs(b_mean)) * 100.0
        else:
            pct_imp = 0.0

        # Welch's t-test
        if len(p_arr) > 1 and len(b_arr) > 1 and (p_std > 1e-12 or b_std > 1e-12):
            t_stat, p_val = stats.ttest_ind(p_arr, b_arr, equal_var=False)
            t_stat = float(t_stat)
            p_val = float(p_val)
        else:
            t_stat = 0.0
            p_val = 1.0

        # Cohen's d (pooled standard deviation)
        n1 = len(p_arr)
        n2 = len(b_arr)
        if n1 > 1 and n2 > 1:
            s_pooled = math.sqrt(((n1 - 1) * (p_std ** 2) + (n2 - 1) * (b_std ** 2)) / (n1 + n2 - 2))
            cohens_d = float(delta_mean / s_pooled) if s_pooled > 1e-12 else 0.0
        else:
            cohens_d = 0.0

        # 95% Confidence interval of the difference
        se_diff = math.sqrt((p_std ** 2 / max(1, n1)) + (b_std ** 2 / max(1, n2)))
        ci_diff = (delta_mean - 1.96 * se_diff, delta_mean + 1.96 * se_diff)

        # Mann-Whitney U test (non-parametric hypothesis testing)
        try:
            if len(p_arr) > 1 and len(b_arr) > 1:
                mw_res = stats.mannwhitneyu(p_arr, b_arr, alternative="two-sided")
                mw_u = float(mw_res.statistic)
                mw_p = float(mw_res.pvalue)
            else:
                mw_u, mw_p = 0.0, 1.0
        except Exception:
            mw_u, mw_p = 0.0, 1.0

        # Post-hoc empirical statistical power (1 - beta)
        try:
            n_eff = (n1 * n2) / max(1, n1 + n2)
            ncp = abs(cohens_d) * math.sqrt(n_eff)
            crit_val = stats.norm.ppf(0.975)  # alpha = 0.05 two-tailed
            stat_power = float(1.0 - stats.norm.cdf(crit_val - ncp) + stats.norm.cdf(-crit_val - ncp))
            stat_power = float(np.clip(stat_power, 0.05, 1.0))
        except Exception:
            stat_power = 0.50

        # Bayes Factor BF_10 approximation via BIC
        try:
            total_n = n1 + n2
            if total_n > 2 and abs(t_stat) > 1e-6:
                bic_diff = (t_stat ** 2) - math.log(total_n)
                bf_10 = float(math.exp(np.clip(bic_diff / 2.0, -50.0, 50.0)))
            else:
                bf_10 = 1.0
        except Exception:
            bf_10 = 1.0

        return StatisticalComparison(
            metric_name=metric_name,
            baseline=baseline_type,
            proposed_mean=round(p_mean, 4),
            baseline_mean=round(b_mean, 4),
            delta_mean=round(delta_mean, 4),
            percent_improvement=round(pct_imp, 2),
            proposed_std=round(p_std, 4),
            baseline_std=round(b_std, 4),
            t_statistic=round(t_stat, 4),
            p_value=float(f"{p_val:.6e}"),
            is_significant=bool(p_val < 0.05),
            is_highly_significant=bool(p_val < 0.001),
            cohens_d=round(cohens_d, 3),
            confidence_interval_95=(round(ci_diff[0], 4), round(ci_diff[1], 4)),
            mann_whitney_u=round(mw_u, 2),
            mann_whitney_p=float(f"{mw_p:.6e}"),
            statistical_power=round(stat_power, 4),
            bayes_factor_10=round(bf_10, 4),
        )

    @classmethod
    def evaluate_benchmark_results(
        cls,
        results: List[ExperimentRunResult],
    ) -> Dict[str, Any]:
        """
        Processes a full suite of multi-seed experiment runs and builds
        comprehensive comparative statistical summaries.
        """
        by_baseline: Dict[BaselineType, List[ExperimentRunResult]] = {}
        for r in results:
            by_baseline.setdefault(r.baseline, []).append(r)

        metrics = [
            ("resilience_score", True),
            ("mean_pdr", True),
            ("final_pdr", True),
            ("mean_latency_ms", False),
            ("total_packets_dropped", False),
            ("partition_rate", False),
        ]

        proposed_runs = by_baseline.get(BaselineType.PROPOSED_DIGITAL_TWIN, [])
        comparisons: List[StatisticalComparison] = []

        baseline_summaries: Dict[str, Dict[str, Any]] = {}
        for b_type, runs in by_baseline.items():
            b_summary = {}
            for metric, _ in metrics:
                vals = [getattr(run, metric) for run in runs]
                b_summary[metric] = cls.compute_summary_stats(vals)
            baseline_summaries[b_type.value] = b_summary

        # Compare proposed against each other baseline
        for b_type, runs in by_baseline.items():
            if b_type == BaselineType.PROPOSED_DIGITAL_TWIN:
                continue
            for metric, higher_better in metrics:
                p_vals = [getattr(r, metric) for r in proposed_runs]
                b_vals = [getattr(r, metric) for r in runs]
                comp = cls.compare_distributions(
                    proposed_vals=p_vals,
                    baseline_vals=b_vals,
                    metric_name=metric,
                    baseline_type=b_type,
                    higher_is_better=higher_better,
                )
                comparisons.append(comp)

        summary_dict = {
            "baseline_summaries": baseline_summaries,
            "statistical_comparisons": [c.model_dump() for c in comparisons],
        }
        summary_dict["latex_table"] = cls.generate_latex_table(summary_dict, comparisons)
        return summary_dict

    @staticmethod
    def generate_latex_table(
        summary_dict: Dict[str, Any],
        comparisons: List[StatisticalComparison],
    ) -> str:
        """
        Generates publication-ready IEEE/ACM LaTeX table snippet for inclusion in manuscripts.
        """
        latex = [
            r"\begin{table*}[t]",
            r"\centering",
            r"\caption{End-to-End Comparative Benchmarking across Standardized Baselines and Proposed Framework ($\mu \pm \sigma$, $[95\%\text{ CI}]$). Asterisks denote statistical significance over Baseline 2: $^{*}p < 0.05$, $^{**}p < 0.01$, $^{***}p < 0.001$.}",
            r"\label{tab:comparative_benchmarks}",
            r"\small",
            r"\begin{tabular}{lcccc}",
            r"\toprule",
            r"\textbf{Metric} & \textbf{Baseline 1 (Unmitigated)} & \textbf{Baseline 2 (Static IDS)} & \textbf{Baseline 3 (ML Heuristic)} & \textbf{Proposed (Digital Twin)} \\",
            r"\midrule",
        ]
        metric_labels = [
            ("resilience_score", "Resilience Score $\\mathcal{R}$"),
            ("mean_pdr", "Mean Packet Delivery Ratio"),
            ("final_pdr", "Final Steady-State PDR"),
            ("mean_latency_ms", "Mean Latency (ms)"),
            ("total_packets_dropped", "Total Packets Dropped"),
            ("partition_rate", "Network Partition Rate"),
        ]
        b_sums = summary_dict.get("baseline_summaries", {})
        for key, label in metric_labels:
            u_m = b_sums.get("unmitigated", {}).get(key, {})
            s_m = b_sums.get("static_threshold_isolation", {}).get(key, {})
            m_m = b_sums.get("ml_fixed_recovery", {}).get(key, {})
            p_m = b_sums.get("proposed_digital_twin", {}).get(key, {})

            u_str = f"{u_m.get('mean', 0.0):.3f} $\\pm$ {u_m.get('std', 0.0):.3f}"
            s_str = f"{s_m.get('mean', 0.0):.3f} $\\pm$ {s_m.get('std', 0.0):.3f}"
            m_str = f"{m_m.get('mean', 0.0):.3f} $\\pm$ {m_m.get('std', 0.0):.3f}"

            sig_star = ""
            for comp in comparisons:
                if comp.metric_name == key and comp.baseline == BaselineType.STATIC_THRESHOLD_ISOLATION:
                    if comp.p_value < 0.001:
                        sig_star = "$^{***}$"
                    elif comp.p_value < 0.01:
                        sig_star = "$^{**}$"
                    elif comp.p_value < 0.05:
                        sig_star = "$^{*}$"
                    break

            p_str = f"\\textbf{{{p_m.get('mean', 0.0):.3f}}} $\\pm$ {p_m.get('std', 0.0):.3f}{sig_star}"
            latex.append(f"{label} & {u_str} & {s_str} & {m_str} & {p_str} \\\\")

        latex.extend([
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table*}",
        ])
        return "\n".join(latex)

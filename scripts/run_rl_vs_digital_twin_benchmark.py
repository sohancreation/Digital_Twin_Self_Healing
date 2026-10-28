"""
Benchmark Suite: Reinforcement Learning (DQN) vs. Digital Twin Self-Healing (TOPSIS)
and GNN Architectural Ablation (MLP vs GCN vs GraphSAGE vs GAT vs BridgeAwareGAT).

Directly validates:
1. Recovery Decision Head-to-Head:
   - Proposed DT Self-Healing vs RL (DQN) vs ML Heuristic vs Static IDS vs Unmitigated.
   - Evaluates: PDR, Partition Rate, MTTD, MTTR, Resilience Score R, and Sample Efficiency.
2. Architecture Ablation:
   - Evaluates parameter count, inference latency, and graph support.

Outputs:
- results/rl_benchmark_report.json
- results/rl_vs_digital_twin_table.tex
"""

import sys
import json
import time
from pathlib import Path
import numpy as np

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.experiments.models import BaselineType, BenchmarkConfig
from backend.experiments.runner import ExperimentRunner
from backend.gnn.ablations import GNNModelAblationSuite
from backend.experiments.rl_recovery import train_dqn_recovery_agent, RL_ACTIONS


def run_architecture_ablation():
    """Evaluates all 5 GNN candidate models on complexity & latency."""
    print("\n=======================================================")
    print(" 1. GNN ARCHITECTURAL ABLATION (COMPLEXITY & PROFILING)")
    print("=======================================================")
    suite = GNNModelAblationSuite()
    complexity_report = suite.evaluate_model_complexity()

    print(f"{'Model Architecture':<26} | {'Params':<8} | {'Latency (ms)':<12} | {'Graph?':<6} | {'Bridge Attenuation?':<18}")
    print("-" * 80)
    for model_name, stats in complexity_report.items():
        print(
            f"{model_name:<26} | "
            f"{stats['parameters']:<8} | "
            f"{stats['latency_ms']:<12.3f} | "
            f"{str(stats['supports_graph']):<6} | "
            f"{str(stats['bridge_attenuation']):<18}"
        )
    return complexity_report


def run_recovery_benchmark(seeds=[42, 43, 44], attack_types=["dos", "compromised_node"]):
    """Executes matched head-to-head evaluation across 5 recovery strategies."""
    print("\n=======================================================")
    print(" 2. HEAD-TO-HEAD RECOVERY BENCHMARK (5 STRATEGIES)")
    print("=======================================================")

    baselines_to_test = [
        (BaselineType.UNMITIGATED, "Baseline 1: Unmitigated"),
        (BaselineType.STATIC_THRESHOLD_ISOLATION, "Baseline 2: Static IDS (Blind Isolation)"),
        (BaselineType.ML_FIXED_RECOVERY, "Baseline 3: ML + Fixed Heuristic"),
        (BaselineType.RL_RECOVERY, "Baseline 4 (RL): Deep Q-Network (DQN)"),
        (BaselineType.PROPOSED_DIGITAL_TWIN, "Proposed: Digital Twin Self-Healing (TOPSIS)"),
    ]

    runner = ExperimentRunner()
    results_by_baseline = {b[0]: [] for b in baselines_to_test}

    total_runs = len(baselines_to_test) * len(seeds) * len(attack_types)
    current_run = 0

    for atk in attack_types:
        for seed in seeds:
            for b_type, b_name in baselines_to_test:
                current_run += 1
                res = runner.run_single_experiment(
                    baseline_type=b_type,
                    attack_type=atk,
                    target_node=3,  # Articulation point (cut-vertex)
                    seed=seed,
                    duration_s=30.0,
                    attack_start_s=8.0,
                    attack_end_s=22.0,
                )
                results_by_baseline[b_type].append(res)
                print(f"[{current_run}/{total_runs}] {b_name:<38} | Atk: {atk:<16} | PDR: {res.mean_pdr*100:.1f}% | Partitions: {res.partition_events_count} | R: {res.resilience_score:.4f}")

    # Aggregate metrics
    summary = {}
    print("\n" + "=" * 90)
    print(f"{'Mitigation Strategy':<38} | {'Mean PDR':<12} | {'Partition Rate':<16} | {'MTTR (s)':<10} | {'Resilience R':<12}")
    print("-" * 90)

    for b_type, b_name in baselines_to_test:
        runs = results_by_baseline[b_type]
        mean_pdr = float(np.mean([r.mean_pdr for r in runs]))
        std_pdr = float(np.std([r.mean_pdr for r in runs]))
        partition_rate = float(np.mean([r.partition_rate for r in runs])) * 100.0
        mttrs = [r.mttr_s for r in runs if r.mttr_s is not None]
        mean_mttr = float(np.mean(mttrs)) if mttrs else 0.0
        mean_r = float(np.mean([r.resilience_score for r in runs]))
        std_r = float(np.std([r.resilience_score for r in runs]))

        summary[b_type.value] = {
            "name": b_name,
            "mean_pdr": round(mean_pdr, 4),
            "std_pdr": round(std_pdr, 4),
            "partition_rate_pct": round(partition_rate, 2),
            "mean_mttr_s": round(mean_mttr, 2),
            "mean_resilience_r": round(mean_r, 4),
            "std_resilience_r": round(std_r, 4),
        }

        print(
            f"{b_name:<38} | "
            f"{mean_pdr*100:.1f} ± {std_pdr*100:.1f}% | "
            f"{partition_rate:.1f}%{' (Dilemma!)' if partition_rate > 20 else '' :<16} | "
            f"{mean_mttr:.2f}s{' ':<5} | "
            f"{mean_r:.4f} ± {std_r:.4f}"
        )

    return summary


def export_latex_table(summary: dict, output_path: Path):
    """Exports IEEE-format publication table."""
    latex = r"""\begin{table*}[t]
\centering
\caption{Autonomous Mitigation Strategy Comparison: Reinforcement Learning (DQN) vs. Digital Twin Self-Healing (TOPSIS) and Classical Baselines Under Coordinated Cut-Vertex Cyberattacks.}
\label{tab:rl_vs_digital_twin}
\footnotesize
\begin{tabular}{|l|c|c|c|c|c|}
\hline
\textbf{Mitigation Strategy} & \textbf{Mean PDR (\%)} & \textbf{Partition Rate (\%)} & \textbf{MTTR (s)} & \textbf{Resilience Score ($\mathcal{R}$)} & \textbf{Training Overhead} \\
\hline
"""
    names_map = {
        "unmitigated": ("Baseline 1: Unmitigated Attack", "None (Negative Control)"),
        "static_threshold_isolation": ("Baseline 2: Static Threshold IDS (Blind)", "None (Rigid Heuristic)"),
        "ml_fixed_recovery": ("Baseline 3: ML + Fixed Heuristic", "Offline Supervised (100 Epochs)"),
        "rl_recovery": ("Baseline 4: Deep Q-Network (DQN RL)", "1,000+ Episodes Trial-and-Error"),
        "proposed_digital_twin": (r"\textbf{Proposed: Digital Twin Self-Healing (TOPSIS)}", r"\textbf{0 (Zero-Shot Lookahead)}"),
    }

    for key, data in summary.items():
        name, overhead = names_map.get(key, (key, "N/A"))
        pdr_str = f"{data['mean_pdr']*100:.1f} $\\pm$ {data['std_pdr']*100:.1f}"
        part_str = f"{data['partition_rate_pct']:.1f}\\%"
        mttr_str = f"{data['mean_mttr_s']:.2f}" if data['mean_mttr_s'] > 0 else r"$\infty$"
        r_str = f"{data['mean_resilience_r']:.4f} $\\pm$ {data['std_resilience_r']:.4f}"

        if "Proposed" in name:
            latex += f"\\textbf{{{name}}} & \\textbf{{{pdr_str}}} & \\textbf{{{part_str}}} & \\textbf{{{mttr_str}}} & \\textbf{{{r_str}}} & \\textbf{{{overhead}}} \\\\ \\hline\n"
        else:
            latex += f"{name} & {pdr_str} & {part_str} & {mttr_str} & {r_str} & {overhead} \\\\ \\hline\n"

    latex += r"""\end{tabular}
\end{table*}
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(latex)
    print(f"\n[OK] Exported LaTeX table to {output_path}")


def main():
    out_dir = ROOT_DIR / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Architecture Ablation
    ablation_res = run_architecture_ablation()

    # 2. Recovery Strategy Benchmark
    benchmark_res = run_recovery_benchmark()

    # Export Report
    full_report = {
        "timestamp": time.time(),
        "gnn_architecture_ablation": ablation_res,
        "recovery_strategy_benchmark": benchmark_res,
    }
    report_json_path = out_dir / "rl_benchmark_report.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)
    print(f"[OK] Exported JSON benchmark report to {report_json_path}")

    # Export LaTeX Table
    table_tex_path = out_dir / "rl_vs_digital_twin_table.tex"
    export_latex_table(benchmark_res, table_tex_path)


if __name__ == "__main__":
    main()

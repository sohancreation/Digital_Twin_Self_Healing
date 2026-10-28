"""
Run Edge Gateway Hardware Profiling for GNN Cyber-Resilience Integration.
Outputs:
- results/gnn/gnn_edge_hardware_profile.json
- results/gnn/gnn_edge_hardware_table.tex
"""

import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.scalability.gnn_edge_profiler import GNNEdgeProfiler

RESULTS_DIR = ROOT_DIR / "results" / "gnn"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def export_latex_hardware_table(profile_data: dict, out_path: Path):
    """Exports IEEE-style LaTeX table for hardware budget and edge latency."""
    latex = r"""\begin{table}[t]
\centering
\caption{Embedded Edge Gateway Computational Budget \& Latency Feasibility for DualHeadGNNClassifier ($N=6$ Nodes, $M=14$ Directed Edges)}
\label{tab:gnn_edge_hardware_budget}
\resizebox{\columnwidth}{!}{
\begin{tabular}{l c c c c}
\hline
\textbf{Edge Platform} & \textbf{Processor Architecture} & \textbf{Latency (ms)} & \textbf{Deadline Margin} & \textbf{Max Freq. (Hz)} \\
\hline
"""
    gateways = profile_data["edge_gateway_projections"]
    for name, spec in gateways.items():
        proc = spec["processor"].split("@")[0].strip()
        lat = spec["projected_latency_ms"]
        margin = spec["deadline_margin_pct"]
        hz = spec["max_throughput_hz"]
        latex += f"{name} & {proc} & {lat:.2f} & {margin:.1f}\\% & {hz:.1f} \\\\\n"

    params = profile_data["parameters"]
    flops = profile_data["computational_complexity"]
    latex += r"""\hline
\multicolumn{5}{l}{\textbf{Model Parameters}: %d (%0.1f KB FP32) \quad \textbf{MACs}: %d \quad \textbf{Complexity}: $\mathcal{O}(|V|d + |E|d)$} \\
\hline
\end{tabular}
}
\end{table}
""" % (params["total_parameters"], params["model_size_kb"], flops["estimated_macs"])

    with open(out_path, "w") as f:
        f.write(latex)
    print(f"[+] Saved LaTeX Hardware Table to {out_path}")


def main():
    model_path = RESULTS_DIR / "best_bridge_gat.pt"
    profiler = GNNEdgeProfiler(model_path=model_path)

    print("=" * 80)
    print("EDGE GATEWAY HARDWARE PROFILING FOR DUAL-HEAD GNN CLASSIFIER")
    print("=" * 80)

    profile_report = profiler.profile_full()

    json_path = RESULTS_DIR / "gnn_edge_hardware_profile.json"
    with open(json_path, "w") as f:
        json.dump(profile_report, f, indent=2)
    print(f"[+] Saved Full Profile JSON to {json_path}")

    tex_path = RESULTS_DIR / "gnn_edge_hardware_table.tex"
    export_latex_hardware_table(profile_report, tex_path)

    print("\nModel Complexity Summary:")
    p = profile_report["parameters"]
    print(f"  Total Parameters: {p['total_parameters']:,} ({p['model_size_kb']:.1f} KB)")
    print(f"  Encoder Parameters: {p['encoder_parameters']:,}")
    print(f"  Attack Head Parameters: {p['attack_head_parameters']:,}")
    print(f"  Trust Head Parameters: {p['trust_head_parameters']:,}")
    print(f"  FLOPs / Graph Snapshot: {profile_report['computational_complexity']['estimated_flops']:,}")
    print(f"  Desktop CPU Latency: {profile_report['desktop_reference_latency']['mean_ms']:.3f} ms (p95: {profile_report['desktop_reference_latency']['p95_ms']:.3f} ms)")

    print("\nEdge Gateway Real-Time Feasibility Projections:")
    for gw, spec in profile_report["edge_gateway_projections"].items():
        print(f"  {gw:<28} | Lat: {spec['projected_latency_ms']:6.3f} ms | Margin: {spec['deadline_margin_pct']:5.1f}% | Max Throughput: {spec['max_throughput_hz']:6.1f} Hz")
    print("=" * 80)


if __name__ == "__main__":
    main()

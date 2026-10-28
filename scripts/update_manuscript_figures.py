import re
from pathlib import Path
import subprocess

tex_path = Path("manuscript_6pages.tex")
content = tex_path.read_text(encoding="utf-8")

# 1. Update Fig 2: change to double-column figure*
old_fig2 = r"""\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth,height=4.7cm]{plots/phase10_dashboard_mission_control.png}
\caption{Phase 10: Real-time research monitoring mission-control dashboard. The interface unifies dark glassmorphism live KPI telemetry ribbons (PDR, loss, latency, throughput, energy), dynamic SVG physical mesh and twin shadow topology visualizer with cut-vertex badging, per-node Bayesian trust inspection, and interactive attack/mitigation actuation controls with instant automated safety rollback ($S_{\text{pre}}$).}
\label{fig:phase10_dashboard}
\end{figure}"""

new_fig2 = r"""\begin{figure*}[t]
\centering
\includegraphics[width=0.98\textwidth]{plots/phase10_dashboard_mission_control.png}
\caption{Phase 10: Real-time research monitoring mission-control dashboard. The interface unifies dark glassmorphism live KPI telemetry ribbons (PDR, loss, latency, throughput, energy), dynamic SVG physical mesh and twin shadow topology visualizer with cut-vertex badging, per-node Bayesian trust inspection, sliding multi-channel performance telemetry, and interactive attack/mitigation actuation controls with instant automated safety rollback ($S_{\text{pre}}$).}
\label{fig:phase10_dashboard}
\end{figure*}"""

# 2. Update Fig 3: use single column fig3_column_resilience_partition.png
old_fig3 = r"""\begin{figure*}[t]
\centering
\begin{subfigure}[b]{0.48\textwidth}
    \centering
    \includegraphics[width=\textwidth]{plots/phase11_plot1_comparative_resilience_curves.png}
    \caption{Dynamic resilience trajectories $Q(t)$ with $\pm 1\sigma$ confidence bands.}
    \label{fig:resilience_curves}
\end{subfigure}
\hfill
\begin{subfigure}[b]{0.48\textwidth}
    \centering
    \includegraphics[width=\textwidth]{plots/phase11_plot3_network_partition_and_safety_violations.png}
    \caption{Cut-vertex partition rate: 48.2\% in Baseline 2 vs. near zero in Proposed.}
    \label{fig:partition_violations}
\end{subfigure}
\caption{Comparative resilience benchmarks and structural partition rate across 60 empirical simulation runs under active cyberattacks.}
\label{fig:phase11_results}
\end{figure*}"""

new_fig3 = r"""\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{plots/fig3_column_resilience_partition.png}
\caption{Comparative resilience benchmarks across 60 empirical simulation runs under active cyberattacks: (a) Dynamic resilience trajectory $Q(t)$ under cut-vertex attack; (b) Network partition rate across attack vectors.}
\label{fig:phase11_results}
\end{figure}"""

# 3. Update Fig 4: use single column fig4_column_parameter_sensitivity.png
old_fig4 = r"""\begin{figure}[t]
\centering
\begin{subfigure}[b]{0.48\columnwidth}
    \centering
    \includegraphics[width=\textwidth]{plots/phase11_plot4_lookahead_horizon_ablation.png}
    \caption{Horizon ablation.}
    \label{fig:horizon_ablation}
\end{subfigure}
\hfill
\begin{subfigure}[b]{0.48\columnwidth}
    \centering
    \includegraphics[width=\textwidth]{plots/phase11_plot6_channel_loss_resilience_decay.png}
    \caption{Loss rate tolerance.}
    \label{fig:channel_loss_decay}
\end{subfigure}
\caption{Parameter sensitivity: (a) Lookahead horizon inflection at $H=30$\,s; (b) Downlink tolerance under lossy wireless channels.}
\label{fig:ablation_results}
\end{figure}"""

new_fig4 = r"""\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{plots/fig4_column_parameter_sensitivity.png}
\caption{Parameter sensitivity analysis: (a) In-silico lookahead horizon $H$ trade-off; (b) Downlink tolerance under lossy wireless channels.}
\label{fig:ablation_results}
\end{figure}"""

# 4. Update Fig 5: use double-column fig5_scalability_and_hardware_upgraded.png
old_fig5 = r"""\begin{figure}[t]
\centering
\begin{subfigure}[b]{0.48\columnwidth}
    \centering
    \includegraphics[width=\textwidth]{plots/phase12_plot1_computational_latency_vs_network_scale.png}
    \caption{Latency vs. $N$.}
    \label{fig:latency_decomposition}
\end{subfigure}
\hfill
\begin{subfigure}[b]{0.48\columnwidth}
    \centering
    \includegraphics[width=\textwidth]{plots/phase12_plot7_edge_gateway_hardware_budget.png}
    \caption{Edge deadline slack.}
    \label{fig:edge_budgets}
\end{subfigure}
\caption{Scalability decomposition, linear asymptotic curve fitting, and edge hardware budget validation across embedded hardware platforms.}
\label{fig:scalability_results}
\end{figure}"""

new_fig5 = r"""\begin{figure*}[t]
\centering
\includegraphics[width=0.98\textwidth]{plots/fig5_scalability_and_hardware_upgraded.png}
\caption{Scalability decomposition, linear asymptotic curve fitting ($R^2 = 0.9953$), and edge hardware real-time deadline validation across embedded hardware platforms.}
\label{fig:scalability_results}
\end{figure*}"""

# Replace normalizing whitespace
def do_replace(txt, old_s, new_s, name):
    # Normalize line endings for replacement
    old_norm = old_s.replace("\r\n", "\n")
    txt_norm = txt.replace("\r\n", "\n")
    if old_norm in txt_norm:
        txt_norm = txt_norm.replace(old_norm, new_s.replace("\r\n", "\n"), 1)
        print(f"SUCCESS: Replaced {name}")
    else:
        print(f"ERROR: Could not find {name}")
    return txt_norm

content = do_replace(content, old_fig2, new_fig2, "Fig 2")
content = do_replace(content, old_fig3, new_fig3, "Fig 3")
content = do_replace(content, old_fig4, new_fig4, "Fig 4")
content = do_replace(content, old_fig5, new_fig5, "Fig 5")

tex_path.write_text(content, encoding="utf-8")
print("Saved updated manuscript_6pages.tex")

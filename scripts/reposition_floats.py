from pathlib import Path
import subprocess

tex_file = Path("manuscript_6pages.tex")
txt = tex_file.read_text(encoding="utf-8").replace("\r\n", "\n")

fig2_block = r"""\begin{figure*}[t]
\centering
\includegraphics[width=0.98\textwidth,height=6.8cm]{plots/phase10_dashboard_mission_control.png}
\caption{Phase 10: Real-time research monitoring mission-control dashboard. The interface unifies dark glassmorphism live KPI telemetry ribbons (PDR, loss, latency, throughput, energy), dynamic SVG physical mesh and twin shadow topology visualizer with cut-vertex badging, per-node Bayesian trust inspection, sliding multi-channel performance telemetry, and interactive attack/mitigation actuation controls with instant automated safety rollback ($S_{\text{pre}}$).}
\label{fig:phase10_dashboard}
\end{figure*}"""

# Remove old fig2 position
old_fig2 = r"""\begin{figure*}[t]
\centering
\includegraphics[width=0.98\textwidth]{plots/phase10_dashboard_mission_control.png}
\caption{Phase 10: Real-time research monitoring mission-control dashboard. The interface unifies dark glassmorphism live KPI telemetry ribbons (PDR, loss, latency, throughput, energy), dynamic SVG physical mesh and twin shadow topology visualizer with cut-vertex badging, per-node Bayesian trust inspection, sliding multi-channel performance telemetry, and interactive attack/mitigation actuation controls with instant automated safety rollback ($S_{\text{pre}}$).}
\label{fig:phase10_dashboard}
\end{figure*}"""

if old_fig2 in txt:
    txt = txt.replace(old_fig2, "")
    print("Removed old Fig 2 position")
else:
    print("Warning: old_fig2 not found")

# Insert Fig 2 right before Algorithm 1 so it floats to Page 4
target = r"\begin{algorithm}[t]"
if target in txt:
    txt = txt.replace(target, fig2_block + "\n\n" + target, 1)
    print("Inserted Fig 2 before Algorithm 1")
else:
    print("Warning: target algorithm not found")

# Ensure Fig 5 has height=5.8cm for perfect balance on Page 6
old_fig5 = r"\includegraphics[width=0.98\textwidth]{plots/fig5_scalability_and_hardware_upgraded.png}"
new_fig5 = r"\includegraphics[width=0.98\textwidth,height=5.8cm]{plots/fig5_scalability_and_hardware_upgraded.png}"
if old_fig5 in txt:
    txt = txt.replace(old_fig5, new_fig5)
    print("Adjusted Fig 5 dimensions")

tex_file.write_text(txt, encoding="utf-8")
print("Saved manuscript_6pages.tex")

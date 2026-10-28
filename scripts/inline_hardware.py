with open('manuscript_6pages.tex', 'r', encoding='utf-8') as f:
    text = f.read()

old_sec = r"""\subsection{Edge Deployment Feasibility and Hardware Profiling}
We evaluate per-cycle compute latency across four target architectures (Fig.~\ref{fig:scalability_results}(b)) over 100 trials (mean $\pm$ SD):
(i)~\textbf{Raspberry Pi 4B} (Cortex-A72 @ 1.5\,GHz): $62.3 \pm 2.1$\,ms $\le 100$\,ms deadline (+37.7\,ms slack);
(ii)~\textbf{NVIDIA Jetson Nano} (Cortex-A57 @ 1.43\,GHz): $70.1 \pm 2.8$\,ms $\le 100$\,ms (+29.9\,ms slack);
(iii)~\textbf{Intel Industrial Edge} (Core i5-1135G7 @ 2.4\,GHz): $24.4 \pm 0.9$\,ms $\le 50$\,ms (+25.6\,ms slack); and
(iv)~\textbf{ESP32-S3 Micro-Gateway} (Xtensa LX7 @ 240\,MHz, 8\,MB PSRAM, $H=10$\,s): $350.5 \pm 8.4$\,ms $\le 500$\,ms (+149.5\,ms slack, $<2.5$\,MB RAM).
These latencies confirm embedded cycle budget compliance."""

new_sec = r"""\subsection{Edge Deployment Feasibility and Hardware Profiling}
We evaluate per-cycle compute latency across four target architectures (Fig.~\ref{fig:scalability_results}(b)) over 100 trials (mean $\pm$ SD): (i)~\textbf{Raspberry Pi 4B} (Cortex-A72 @ 1.5\,GHz): $62.3 \pm 2.1$\,ms $\le 100$\,ms deadline (+37.7\,ms slack); (ii)~\textbf{NVIDIA Jetson Nano} (Cortex-A57 @ 1.43\,GHz): $70.1 \pm 2.8$\,ms $\le 100$\,ms (+29.9\,ms slack); (iii)~\textbf{Intel Industrial Edge} (Core i5-1135G7 @ 2.4\,GHz): $24.4 \pm 0.9$\,ms $\le 50$\,ms (+25.6\,ms slack); and (iv)~\textbf{ESP32-S3 Micro-Gateway} (Xtensa LX7 @ 240\,MHz, 8\,MB PSRAM, $H=10$\,s): $350.5 \pm 8.4$\,ms $\le 500$\,ms (+149.5\,ms slack, $<2.5$\,MB RAM). These latencies confirm embedded cycle budget compliance."""

assert old_sec in text, "old_sec not found in manuscript_6pages.tex"
text = text.replace(old_sec, new_sec)

with open('manuscript_6pages.tex', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully inlined Section V-B.")

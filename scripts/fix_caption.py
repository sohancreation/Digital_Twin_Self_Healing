with open('manuscript_6pages.tex', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'plots/fig3_composite_benchmarks.pdf' in l:
        idx = i + 1
        lines[idx] = r'\caption{Comparative resilience benchmarks and parameter sensitivity analysis across 480 simulation runs ($n=120$ matched scenarios across 30 seeds and 4 threat vectors): (a) Dynamic resilience trajectory $Q(t)$ under cut-vertex attack comparing five strategies; (b) Structural network partition rate across attack vectors (DoS, Selective Drop, Crash, On-Off, and Overall), showing complete partition suppression ($0.00\%$); (c) In-silico lookahead horizon $H$ trade-off between fidelity RMSE and solve latency, establishing the dual gateway ($H=30$\,s) and MCU ($H=10$\,s) operational points; (d) Downlink tolerance under lossy wireless channels ($p_{\text{loss}} \le 0.30$).}' + '\n'
        break

with open('manuscript_6pages.tex', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Updated line correctly:')
print(lines[idx][:120])

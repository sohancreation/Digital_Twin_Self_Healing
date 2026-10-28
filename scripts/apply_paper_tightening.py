import re

with open('manuscript_6pages.tex', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Algorithm 1: change \small to \footnotesize
text = text.replace(r'''\begin{algorithmic}[1]
\small''', r'''\begin{algorithmic}[1]
\footnotesize''')

# 2. Table II footnotes: consolidate 4 lines into 2 lines
target_table_footnotes = r'''\multicolumn{8}{|l|}{\textit{Threat Vector Evaluation (Type 4: On-Off Evasive Attack):} Baseline 2 triggers $72.42 \pm 0.85\%$ partition ($72.50\%$ median); Baseline 4 triggers $62.50\%$ median partition;} \\
\multicolumn{8}{|l|}{Proposed maintains $0.00\%$ partition and $\mathcal{R} = 0.9385 \pm 0.010$, empirically confirming Theorem~1 and Theorem~4 bounds where GNN-Bayesian fusion accelerates detection without partition.} \\ \hline
\multicolumn{8}{|l|}{\textit{Inferential Stats (Proposed vs. B2, $n=120$ matched pairs across 30 seeds $\times$ 4 threat vectors):} Paired diff $= 54.20 \pm 31.43$ pp ($95\%$ CI $[48.57, 59.82]$); Paired $t(119) = 18.89, p = 1.29 \times 10^{-37}$;} \\
\multicolumn{8}{|l|}{Wilcoxon $W = 0.0, p = 6.76 \times 10^{-20}$; Welch $t(119.0) = 18.89, p = 1.48 \times 10^{-35}$; Cohen's $d = 1.724$ (very large effect); Empirical power $= 1.0000$; Bayes Factor $BF_{10} = 5.18 \times 10^{21}$ (decisive evidence).} \\'''

replacement_table_footnotes = r'''\multicolumn{8}{|l|}{\textit{Type 4 On-Off Evasion:} B2 triggers $72.42 \pm 0.85\%$ partition ($72.50\%$ median); B4 triggers $62.50\%$ median partition; Proposed sustains $0.00\%$ partition and $\mathcal{R} = 0.9385 \pm 0.010$ (Theorems~1, 4).} \\ \hline
\multicolumn{8}{|l|}{\textit{Inferential Stats (Proposed vs. B2, $n=120$ pairs):} Paired diff $= 54.20 \pm 31.43$\,pp ($95\%$ CI $[48.57, 59.82]$); $t(119)=18.89, p=1.29 \times 10^{-37}$; Wilcoxon $W=0.0, p=6.76 \times 10^{-20}$; $d=1.724; BF_{10}=5.18 \times 10^{21}$.} \\'''

text = text.replace(target_table_footnotes, replacement_table_footnotes)

# 3. Inline Eq (3) first-order radio model
target_eq3 = r'''Energy dissipation adheres to the first-order radio model:
\begin{equation}
E_{\text{tx}}(l, d) = l E_{\text{elec}} + l \epsilon_{\text{amp}} d^\eta, \quad E_{\text{rx}}(l) = l E_{\text{elec}},
\end{equation}
with electronics dissipation $E_{\text{elec}}$ and amplifier factor $\epsilon_{\text{amp}}$.'''

replacement_eq3 = r'''Energy dissipation adheres to the first-order radio model: $E_{\text{tx}}(l, d) = l E_{\text{elec}} + l \epsilon_{\text{amp}} d^\eta$ and $E_{\text{rx}}(l) = l E_{\text{elec}}$, with electronics dissipation $E_{\text{elec}}$ and amplifier factor $\epsilon_{\text{amp}}$.'''

text = text.replace(target_eq3, replacement_eq3)

# 4. Inline Eq (8) TOPSIS vector normalization
target_eq8 = r'''Candidate ranking is executed using TOPSIS with vector normalization:
\begin{equation}
r_{km} = \frac{x_{km}}{\sqrt{\sum_{k=1}^K x_{km}^2}}, \quad v_{km} = w_m r_{km},
\end{equation}
with ideal solution $\mathbf{A}^+$ and negative-ideal $\mathbf{A}^-$. Relative closeness score $\Phi(s_k)$ determines the optimal action:'''

replacement_eq8 = r'''Candidate ranking is executed using TOPSIS with vector normalization $r_{km} = x_{km} / \sqrt{\sum_{k=1}^K x_{km}^2}$ and weighted values $v_{km} = w_m r_{km}$, relative to ideal solution $\mathbf{A}^+$ and negative-ideal $\mathbf{A}^-$. Closeness score $\Phi(s_k)$ determines the optimal action:'''

text = text.replace(target_eq8, replacement_eq8)

# 5. Inline Eq (11) SPRT boundaries A and B
target_eq11 = r'''The sequential decision boundaries are defined with false alarm rate $\alpha = 0.01$ and miss detection rate $\beta = 0.01$:
\begin{equation}
A = \ln\frac{1-\beta}{\alpha} \approx 4.595, \quad B = \ln\frac{\beta}{1-\alpha} \approx -4.595.
\end{equation}'''

replacement_eq11 = r'''The sequential decision boundaries are defined with false alarm $\alpha = 0.01$ and miss detection $\beta = 0.01$ as $A = \ln\frac{1-\beta}{\alpha} \approx 4.595$ and $B = \ln\frac{\beta}{1-\alpha} \approx -4.595$.'''

text = text.replace(target_eq11, replacement_eq11)

# 6. Bibliography: \scriptsize and \itemsep=-4.0pt
target_bib = r'''\bibliographystyle{IEEEtran}
\begin{thebibliography}{19}
\setlength{\itemsep}{-3.6pt plus 0.2pt minus 0.2pt}
\setlength{\parskip}{0pt}
\footnotesize'''

replacement_bib = r'''\bibliographystyle{IEEEtran}
\begin{thebibliography}{22}
\setlength{\itemsep}{-4.2pt plus 0.2pt minus 0.2pt}
\setlength{\parskip}{0pt}
\scriptsize'''

text = text.replace(target_bib, replacement_bib)

with open('manuscript_6pages.tex', 'w', encoding='utf-8') as f:
    f.write(text)

print('Applied paper tightening successfully.')

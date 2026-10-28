import subprocess
from pathlib import Path
import fitz

tikz_tex = r'''\documentclass{article}
\usepackage[paperwidth=7.5in,paperheight=1.85in,margin=0.08in]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{tikz}
\usetikzlibrary{shapes.geometric, arrows.meta, positioning, calc}

\begin{document}
\thispagestyle{empty}
\centering
\vspace*{0.02in}
\begin{tikzpicture}[
    node distance=1.35cm and 1.35cm,
    stage/.style={
        rectangle, rounded corners=5pt, draw=#1!80!black, fill=#1!8,
        line width=1.1pt, minimum width=2.25cm, minimum height=1.75cm,
        inner sep=3pt, align=center
    },
    flow/.style={->, >=Stealth[length=5pt], line width=1.3pt, color=slate!70!black},
    feedback/.style={->, >=Stealth[length=5pt], line width=1.3pt, dashed, color=red!75!black},
    lbl/.style={font=\fontsize{6.0}{7.0}\selectfont\bfseries, fill=white, inner sep=1.2pt}
]

% 5 Horizontal Stages
\node[stage=blue] (s1) {
    \textbf{\small 1. Physical IoT}\\[3pt]
    \scriptsize Sensors $V$\\[1pt]
    \scriptsize Links $E(t)$\\[1pt]
    \scriptsize Queues $B_{\max}$
};

\node[stage=cyan, right=of s1] (s2) {
    \textbf{\small 2. Twin Shadow}\\[3pt]
    \scriptsize Trust $\mathcal{T}_i(t)$\\[1pt]
    \scriptsize Asymmetric Fit\\[1pt]
    \scriptsize Cut-Vertices
};

\node[stage=purple, right=of s2] (s3) {
    \textbf{\small 3. Sandbox}\\[3pt]
    \scriptsize Lookahead\\[1pt]
    \scriptsize Horizon $H = 30$\,s\\[1pt]
    \scriptsize Candidates $\mathcal{S}_{\text{cand}}$
};

\node[stage=orange, right=of s3] (s4) {
    \textbf{\small 4. TOPSIS}\\[3pt]
    \scriptsize 4-D Matrix\\[1pt]
    \scriptsize Score $C_k$\\[1pt]
    \scriptsize Optimal $\mathbf{s}^*$
};

\node[stage=teal, right=of s4] (s5) {
    \textbf{\small 5. Wald SPRT}\\[3pt]
    \scriptsize Log-Ratio\\[1pt]
    \scriptsize Certification\\[1pt]
    \scriptsize Rollback $\mathcal{S}_{\text{pre}}$
};

% Forward Flow Arrows with wide 1.35cm gaps
\draw[flow] (s1) -- node[midway, above=3pt, font=\fontsize{6.2}{7.2}\selectfont\bfseries, text=blue!85!black] {Telemetry}
                   node[midway, below=3pt, font=\fontsize{6.2}{7.2}\selectfont\bfseries, text=blue!85!black] {$\mathbf{z}(t)$} (s2);

\draw[flow] (s2) -- node[midway, above=3pt, font=\fontsize{6.2}{7.2}\selectfont\bfseries, text=cyan!85!black] {Trust \&}
                   node[midway, below=3pt, font=\fontsize{6.2}{7.2}\selectfont\bfseries, text=cyan!85!black] {Bridges} (s3);

\draw[flow] (s3) -- node[midway, above=3pt, font=\fontsize{6.2}{7.2}\selectfont\bfseries, text=purple!85!black] {Simulated}
                   node[midway, below=3pt, font=\fontsize{6.2}{7.2}\selectfont\bfseries, text=purple!85!black] {Outcomes} (s4);

\draw[flow] (s4) -- node[midway, above=3pt, font=\fontsize{6.2}{7.2}\selectfont\bfseries, text=orange!85!black] {Policy}
                   node[midway, below=3pt, font=\fontsize{6.2}{7.2}\selectfont\bfseries, text=orange!85!black] {$\mathbf{s}^*$} (s5);

% Clean Closed-Loop Feedback Arrow Underneath
\draw[feedback] (s5.south) -- ++(0,-0.32) 
    -- node[below=1pt, font=\fontsize{7.2}{8.2}\selectfont\bfseries, text=red!80!black] {Closed-Loop Certified Actuation $\mathbf{s}^*$ \quad / \quad Sub-Millisecond Safety Rollback $\mathcal{S}_{\text{pre}}$ ($<0.1$\,ms)} 
    ($(s1.south) + (0,-0.32)$) -- (s1.south);

\end{tikzpicture}
\end{document}
'''

Path("plots").mkdir(exist_ok=True)
with open("plots/fig1_flowchart_vector.tex", "w", encoding="utf-8") as f:
    f.write(tikz_tex)

res = subprocess.run(["pdflatex", "-interaction=nonstopmode", "fig1_flowchart_vector.tex"], cwd="plots", capture_output=True, text=True)

doc = fitz.open("plots/fig1_flowchart_vector.pdf")
page = doc[0]
pix = page.get_pixmap(dpi=300)
pix.save("plots/fig1_flowchart_vector.png")
print("SUCCESS: Updated plots/fig1_flowchart_vector.pdf and .png")

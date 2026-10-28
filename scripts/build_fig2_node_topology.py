import subprocess
from pathlib import Path
from PIL import Image, ImageOps
import fitz

tikz_node = r'''\documentclass{article}
\usepackage[paperwidth=7.5in,paperheight=2.35in,margin=0.04in]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{tikz}
\usetikzlibrary{shapes.geometric, arrows.meta, positioning, calc, backgrounds}

\begin{document}
\thispagestyle{empty}
\centering
\vspace*{0.02in}
\begin{tikzpicture}[
    scale=0.95, every node/.style={transform shape},
    sensor/.style={circle, draw=blue!85!black, fill=blue!14, line width=1.3pt, minimum size=20pt, font=\fontsize{9.0}{10.0}\selectfont\bfseries},
    bridge/.style={circle, draw=purple!90!black, fill=purple!20, line width=1.5pt, minimum size=21pt, font=\fontsize{9.0}{10.0}\selectfont\bfseries},
    attacker/.style={circle, draw=red!90!black, fill=red!25, line width=1.5pt, minimum size=21pt, font=\fontsize{9.0}{10.0}\selectfont\bfseries},
    quarantine/.style={circle, draw=gray!75!black, fill=gray!20, line width=1.3pt, dashed, minimum size=20pt, font=\fontsize{9.0}{10.0}\selectfont\bfseries},
    detour_node/.style={circle, draw=teal!90!black, fill=teal!20, line width=1.4pt, minimum size=20pt, font=\fontsize{9.0}{10.0}\selectfont\bfseries},
    wlink/.style={-, draw=black!60, line width=1.1pt},
    bridgelink/.style={-, draw=purple!85!black, line width=1.8pt},
    attacklink/.style={-, draw=red!90!black, dashed, line width=1.5pt},
    detourlink/.style={->, >=Stealth, draw=teal!95!black, line width=1.8pt},
    powerlink/.style={->, >=Stealth, draw=orange!95!black, dashed, line width=1.6pt},
    panelbg/.style={rectangle, rounded corners=6pt, draw=black!30, fill=black!2, line width=0.9pt}
]

% ==================== PANEL (a) ====================
\begin{scope}[shift={(0,0)}]
    \draw[panelbg] (-0.3, -0.68) rectangle (4.55, 2.30);
    
    \node[sensor] (a1) at (0.35, 1.05) {$v_1$};
    \node[sensor] (a2) at (1.45, 1.70) {$v_2$};
    \node[sensor] (a3) at (1.35, 0.35) {$v_3$};
    \node[bridge] (ab) at (2.55, 1.05) {$v_4$};
    \node[sensor] (a5) at (3.80, 1.65) {$v_5$};
    \node[sensor] (a6) at (3.90, 0.45) {$v_6$};

    \draw[wlink] (a1) -- (a2);
    \draw[wlink] (a1) -- (a3);
    \draw[wlink] (a2) -- (a3);
    \draw[bridgelink] (a2) -- (ab);
    \draw[bridgelink] (a3) -- (ab);
    \draw[bridgelink] (ab) -- (a5);
    \draw[bridgelink] (ab) -- (a6);
    \draw[wlink] (a5) -- (a6);

    \node at (2.55, 0.45) [fill=white, rounded corners=2pt, inner sep=1.2pt, font=\fontsize{6.5}{7.5}\selectfont\bfseries, text=purple!90!black] {Bridge $\delta_{\text{cut}}=1$};
    \node at (2.12, -0.45) [font=\fontsize{8.0}{9.0}\selectfont\bfseries] {(a) Nominal Mesh: Bridge};
\end{scope}

% ==================== PANEL (b) ====================
\begin{scope}[shift={(4.95, 0)}]
    \draw[panelbg] (-0.3, -0.68) rectangle (4.55, 2.30);
    
    \node[sensor] (b1) at (0.35, 1.05) {$v_1$};
    \node[attacker] (b2) at (1.45, 1.70) {$v_2$};
    \node[sensor] (b3) at (1.35, 0.35) {$v_3$};
    \node[bridge] (bb) at (2.55, 1.05) {$v_4$};
    \node[sensor] (b5) at (3.80, 1.65) {$v_5$};
    \node[sensor] (b6) at (3.90, 0.45) {$v_6$};

    \draw[attacklink] (b1) -- node[above=1pt, font=\fontsize{6.0}{7.0}\selectfont\bfseries\color{red!90!black}] {Flood} (b2);
    \draw[wlink] (b1) -- (b3);
    \draw[attacklink] (b2) -- node[right=1pt, font=\fontsize{6.0}{7.0}\selectfont\bfseries\color{red!90!black}] {Drop} (b3);
    \draw[attacklink] (b2) -- (bb);
    \draw[bridgelink] (b3) -- (bb);
    \draw[bridgelink] (bb) -- (b5);
    \draw[bridgelink] (bb) -- (b6);
    \draw[wlink] (b5) -- (b6);

    \node at (1.45, 2.12) [fill=white, rounded corners=2pt, inner sep=1.2pt, font=\fontsize{6.5}{7.5}\selectfont\bfseries, text=red!90!black] {Attacker ($\mathcal{T}_2 < 0.5$)};
    \node at (2.12, -0.45) [font=\fontsize{8.0}{9.0}\selectfont\bfseries] {(b) Cyberattack Degrades Path};
\end{scope}

% ==================== PANEL (c) ====================
\begin{scope}[shift={(9.9, 0)}]
    \draw[panelbg] (-0.3, -0.68) rectangle (4.65, 2.30);
    
    \node[sensor] (c1) at (0.35, 1.05) {$v_1$};
    \node[quarantine] (c2) at (1.45, 1.70) {$v_2$};
    \node[detour_node] (c3) at (1.35, 0.35) {$v_3$};
    \node[bridge] (cb) at (2.55, 1.05) {$v_4$};
    \node[sensor] (c5) at (3.80, 1.65) {$v_5$};
    \node[sensor] (c6) at (3.90, 0.45) {$v_6$};

    % Detour links
    \draw[detourlink] (c1) -- (c3);
    \node at (0.65, 0.85) [fill=white, rounded corners=2pt, inner sep=1pt, font=\fontsize{5.8}{6.8}\selectfont\bfseries\color{teal!95!black}] {Detour $s_{\text{bypass}}$};
    \draw[detourlink] (c3) -- (cb);
    \draw[detourlink] (cb) -- (c5);
    \draw[wlink] (cb) -- (c6);
    \draw[wlink] (c5) -- (c6);

    % RF power boost link
    \draw[powerlink] (c1) to[out=68, in=122] (cb);
    \node at (1.45, 2.15) [fill=white, rounded corners=2pt, inner sep=1pt, font=\fontsize{6.2}{7.2}\selectfont\bfseries\color{orange!95!black}] {RF Boost $+3$\,dBm};

    \node at (1.45, 1.25) [fill=white, rounded corners=2pt, inner sep=1pt, font=\fontsize{5.8}{6.8}\selectfont\bfseries, text=gray!85!black] {Rate-Clamped};
    \node at (2.17, -0.45) [font=\fontsize{8.0}{9.0}\selectfont\bfseries] {(c) Autonomous BFS Detour};
\end{scope}

\end{tikzpicture}
\end{document}
'''

Path("plots").mkdir(exist_ok=True)
with open("plots/fig2_node_topology.tex", "w", encoding="utf-8") as f:
    f.write(tikz_node)

res = subprocess.run(["pdflatex", "-interaction=nonstopmode", "fig2_node_topology.tex"], cwd="plots", capture_output=True, text=True)

doc = fitz.open("plots/fig2_node_topology.pdf")
page = doc[0]
pix = page.get_pixmap(dpi=300)
pix.save("plots/fig2_temp.png")

im = Image.open("plots/fig2_temp.png").convert("RGB")
inv = ImageOps.invert(im)
gray = inv.convert("L")
thresholded = gray.point(lambda p: 255 if p > 10 else 0)
bbox = thresholded.getbbox()

pad = 12
crop_box = (max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(im.width, bbox[2] + pad), min(im.height, bbox[3] + pad))
im_crop = im.crop(crop_box)
im_crop.save("plots/fig2_node_topology.png")

scale = 72.0 / 300.0
clip_rect = fitz.Rect(crop_box[0]*scale, crop_box[1]*scale, crop_box[2]*scale, crop_box[3]*scale)
doc_tight = fitz.open()
p = doc_tight.new_page(width=clip_rect.width, height=clip_rect.height)
p.show_pdf_page(fitz.Rect(0, 0, clip_rect.width, clip_rect.height), doc, 0, clip=clip_rect)
doc_tight.save("plots/fig2_node_topology_tight.pdf")
print("SUCCESS: Rendered with larger fonts, bbox:", clip_rect.width, "x", clip_rect.height)

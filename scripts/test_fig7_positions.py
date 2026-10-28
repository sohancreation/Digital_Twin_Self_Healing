import os
import subprocess
import fitz

tex_original_path = r"e:\G_Publication\manuscript_6pages.tex"
with open(tex_original_path, "r", encoding="utf-8") as f:
    tex_content = f.read()

scratch_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\bc3d3473-2e39-4d7a-bc18-fffd4ceb5059\scratch"

# Let's test moving the Fig 7 block to right after Section VI or before Section VI or within Subsection B
# Where is Fig 7 currently defined?
fig7_block = r"""\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{plots/fig_1000_nodes_topology_v2_clean.pdf}
\caption{Undirected connected graph structure for 1,000-node large-scale IoT sensor and gateway network. Blue nodes represent resource-constrained IoT sensors, while red nodes denote critical articulation bridges and edge gateways. Green lines represent intra-cluster sensor-to-sensor links, orange lines represent bridge backbones, and brown lines denote uplink connections.}
\label{fig:1000_node_topology}
\end{figure}"""

# Remove fig7_block from its current position
tex_no_fig7 = tex_content.replace(fig7_block, "")

# Case A: Put fig7 right after Subsection B (before Section VI)
tex_case_a = tex_no_fig7.replace(r"\section{Discussion, Reproducibility, and Conclusion}", fig7_block + "\n\n" + r"\section{Discussion, Reproducibility, and Conclusion}")

# Case B: Put fig7 right after Section VI heading
tex_case_b = tex_no_fig7.replace(r"\section{Discussion, Reproducibility, and Conclusion}", r"\section{Discussion, Reproducibility, and Conclusion}" + "\n\n" + fig7_block)

# Case C: Put fig7 right before \bibliographystyle
tex_case_c = tex_no_fig7.replace(r"\bibliographystyle{IEEEtran}", fig7_block + "\n\n" + r"\bibliographystyle{IEEEtran}")

cases = {
    "case_a_before_secVI": tex_case_a,
    "case_b_after_secVI": tex_case_b,
    "case_c_before_bib": tex_case_c,
}

for name, content in cases.items():
    tex_file = os.path.join(scratch_dir, f"{name}.tex")
    with open(tex_file, "w", encoding="utf-8") as f:
        f.write(content)
    # compile twice
    subprocess.run(["pdflatex", "-interaction=nonstopmode", f"{name}.tex"], cwd=scratch_dir, capture_output=True)
    res = subprocess.run(["pdflatex", "-interaction=nonstopmode", f"{name}.tex"], cwd=scratch_dir, capture_output=True, text=True)
    pdf_file = os.path.join(scratch_dir, f"{name}.pdf")
    if os.path.exists(pdf_file):
        doc = fitz.open(pdf_file)
        print(f"{name}: Page count = {len(doc)}")
        # render last 2 pages
        for pno in range(len(doc)-2, len(doc)):
            page = doc[pno]
            pix = page.get_pixmap(dpi=150)
            pix.save(os.path.join(scratch_dir, f"{name}_p{pno+1}.png"))
    else:
        print(f"{name}: Failed to compile!")

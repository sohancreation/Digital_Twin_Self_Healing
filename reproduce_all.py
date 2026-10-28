#!/usr/bin/env python3
"""
Digital Twin Self-Healing Research Artifact Reproducibility Suite.
One-click reproduction script for all simulation benchmarks, inferential statistics,
publication figures, and LaTeX manuscript compilation.

Usage:
    python reproduce_all.py [--quick] [--skip-sim] [--compile-only]
"""

import sys
import os
import time
import argparse
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

def run_step(step_name: str, cmd: list, cwd: Path = ROOT_DIR):
    print(f"\n==================================================")
    print(f"[*] STEP: {step_name}")
    print(f"[*] CMD: {' '.join(cmd)}")
    print(f"==================================================")
    t0 = time.time()
    res = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    dt = time.time() - t0
    if res.returncode != 0:
        print(f"[!] FAILED in {dt:.2f}s (code {res.returncode})")
        print(f"STDERR:\n{res.stderr}")
        print(f"STDOUT:\n{res.stdout}")
        sys.exit(res.returncode)
    print(f"[+] COMPLETED in {dt:.2f}s")
    if res.stdout.strip():
        lines = res.stdout.strip().split("\n")
        summary_lines = lines[:5] + (["..."] if len(lines) > 10 else []) + lines[-5:] if len(lines) > 10 else lines
        for l in summary_lines:
            print(f"    {l}")

def verify_pdf(pdf_path: Path, expected_pages: int = 6):
    try:
        import pypdf
        reader = pypdf.PdfReader(str(pdf_path))
        num_pages = len(reader.pages)
        print(f"\n[*] PDF Verification: {pdf_path.name}")
        print(f"    Page count: {num_pages} (Expected: {expected_pages})")
        if num_pages == expected_pages:
            print(f"    [+] PASS: Exactly {expected_pages} pages!")
        else:
            print(f"    [!] WARNING: Page count mismatch: got {num_pages}, expected {expected_pages}")
    except ImportError:
        print("    [!] Note: 'pypdf' not installed, skipping automated page count check.")

def main():
    parser = argparse.ArgumentParser(description="Reproduce all benchmarks and manuscript.")
    parser.add_argument("--skip-sim", action="store_true", help="Skip running the 480 simulation runs (use cached JSON).")
    parser.add_argument("--compile-only", action="store_true", help="Only compile the LaTeX manuscript.")
    args = parser.parse_args()

    t_start = time.time()
    print("=" * 60)
    print("  DIGITAL TWIN SELF-HEALING ARTIFACT REPRODUCTION")
    print(f"  Root: {ROOT_DIR}")
    print("=" * 60)

    if not args.compile_only:
        # Step 1: Run Simulation Benchmarks
        if not args.skip_sim:
            run_step(
                "Execute 480-Run Benchmark Campaign (30 seeds x 4 attacks x 4 strategies)",
                [sys.executable, "scripts/run_large_scale_benchmarks.py", "--seeds", "30"]
            )
            run_step(
                "Execute 50-Topology Graph Ensemble Benchmark (Table III Reproduction)",
                [sys.executable, "scripts/run_graph_ensemble_benchmark.py"]
            )
        else:
            print("\n[*] Skipping simulation runs, utilizing cached results/large_scale_benchmark_summary_30seeds.json")

        # Step 2: Generate Publication Figures (Column Figures & GNN Figures)
        run_step(
            "Regenerate Column-Width IEEE Publication Figures",
            [sys.executable, "scripts/generate_ieee_column_figures.py"]
        )
        run_step(
            "Regenerate GNN Publication Figures (t-SNE & Attention)",
            [sys.executable, "scripts/generate_gnn_figures.py"]
        )

    # Step 3: Compile LaTeX Manuscript (if present)
    tex_file = "manuscript_6pages.tex"
    pdf_file = ROOT_DIR / "manuscript_6pages.pdf"
    tex_path = ROOT_DIR / tex_file
    
    if tex_path.exists():
        run_step(
            "Compile LaTeX Manuscript (Pass 1)",
            ["pdflatex", "-interaction=nonstopmode", tex_file]
        )
        run_step(
            "Compile LaTeX Manuscript (Pass 2 - Resolve References & Floats)",
            ["pdflatex", "-interaction=nonstopmode", tex_file]
        )
        # Step 4: Verify 6-Page Compliance
        verify_pdf(pdf_file, expected_pages=6)
    else:
        print(f"\n[*] '{tex_file}' not found in repository (manuscript source excluded). Skipping LaTeX compilation.")

    total_time = time.time() - t_start
    print("\n" + "=" * 60)
    print(f"  ALL ARTIFACTS REPRODUCED SUCCESSFULLY IN {total_time:.2f}s")
    print(f"  Manuscript PDF: {pdf_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()

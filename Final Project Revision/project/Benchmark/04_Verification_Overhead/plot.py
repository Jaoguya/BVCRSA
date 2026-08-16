#!/usr/bin/env python3
"""
Plot: Verification Overhead — BVCRSA vs Trinity vs VC-KASE
Reads from verification_overhead_exp_results.csv (Task 6B-compliant).
Generates fig_verification_overhead.png for the manuscript.
"""

import pandas as pd
import matplotlib.pyplot as plt
import os

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 13,
    'axes.labelsize': 14,
    'axes.titlesize': 14,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 11,
    'lines.linewidth': 2.5,
    'lines.markersize': 8,
})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CSVDIR = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "CSV")
_FIGDIR = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "Figures")
CSV_FILE = os.path.join(_CSVDIR, "exp04_verification_overhead.csv")
OUT_FILE = os.path.join(_FIGDIR, "exp04_verification_overhead.svg")  # vector only, R1-C8

COLORS = {
    "BVCRSA (Ours)": '#e31a1c',
    "Trinity": '#1f78b4',
    "VC-KASE": '#33a02c',
}
MARKERS = {"BVCRSA (Ours)": 'o', "Trinity": 's', "VC-KASE": '^'}


def main():
    df = pd.read_csv(CSV_FILE).sort_values("returned_results")

    fig, ax = plt.subplots(figsize=(7, 5.5))
    series = {
        "BVCRSA (Ours)": df["bvcrsa_verify_ms"],
        "Trinity": df["trinity_verify_ms"],
        "VC-KASE": df["vckase_verify_ms"],
    }
    for name, y in series.items():
        ax.plot(df["returned_results"], y, marker=MARKERS[name],
                color=COLORS[name], label=name)

    ax.set_xlabel("Number of Returned Results ($|R_Q|$)")
    ax.set_ylabel("Verification Time (ms)")
    ax.legend(frameon=False)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_FILE, format="svg", bbox_inches="tight")
    print(f"Saved {OUT_FILE}")


if __name__ == "__main__":
    main()

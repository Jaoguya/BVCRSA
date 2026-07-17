#!/usr/bin/env python3
"""
plot_fig2_5_7.py
================
Generates the three paper figures from the FAIR, bug-fixed benchmark results
(benchmark_fig2_5_7_fair_results.csv) — not from hardcoded/pasted data, unlike
original_reference/graph_figures_ORIGINAL.py, which plotted a literal pasted CSV
string disconnected from any results file. Reading directly from the real output
CSV keeps a traceable, reproducible link between measurement and figure.

Output (in figures/, then copied to the paper's all_figures/ directory):
  fig_index_construction.png           <- Fig. 2: Index-construction time vs N
  fig_query_vs_N.png                   <- Fig. 5: Query processing time vs N
  fig_query_throughput_matched_colors.png <- Fig. 7: Query throughput vs workload

Points explicitly derived via linear extrapolation (ABSE-Range query time for
N > 10,000 — see reviseplan.md) are rendered with an open/hollow marker and a
dotted (not solid/dashed) connecting segment, and are called out in the caption
text printed to stdout, so the distinction between measured and predicted data
is visible in the figure itself, not just buried in a CSV note column.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_CSV = os.path.join(BASE_DIR, "benchmark_fig2_5_7_fair_results.csv")
OUT_DIR = os.path.join(BASE_DIR, "figures")
os.makedirs(OUT_DIR, exist_ok=True)

MARKERS = {"BVCRSA": "o", "Trinity": "^", "ABSE-Range": "D", "Latt-IBEKS": "s", "VC-KASE": "v"}
COLORS  = {"BVCRSA": "#e31a1c", "Trinity": "#33a02c", "ABSE-Range": "#ff7f00",
           "Latt-IBEKS": "#1f78b4", "VC-KASE": "#6a3d9a"}
N_TICKS = [1000, 5000, 10000, 50000, 100000]
N_LABELS = ["1K", "5K", "10K", "50K", "100K"]

df = pd.read_csv(RESULTS_CSV)
df["note"] = df["note"].fillna("")
algos_present = [a for a in MARKERS if a in df["algo"].unique()]


def _is_predicted(row):
    return "predicted" in str(row.get("note", ""))


# ── Fig. 2: Index-construction time vs database size ──────────────────────
plt.figure(figsize=(7, 5))
df2 = df[df["exp"] == "exp2_5"].dropna(subset=["index_ms"]).sort_values("N")
for algo in algos_present:
    sub = df2[df2["algo"] == algo]
    if sub.empty:
        continue
    plt.plot(sub["N"], sub["index_ms"], marker=MARKERS[algo], color=COLORS[algo],
              linewidth=2, markersize=8, linestyle="--", label=algo)
plt.yscale("log")
plt.xscale("log")
plt.xticks(N_TICKS, N_LABELS)
plt.title("Index-Construction Time versus Database Size", fontsize=12, fontweight="bold")
plt.xlabel("Number of Records (N)", fontsize=11, fontweight="bold")
plt.ylabel("Index-Construction Time (ms) [log scale]", fontsize=11, fontweight="bold")
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fig_index_construction.png"), dpi=300, bbox_inches="tight")
plt.close()

# ── Fig. 5: Query processing time vs database size ─────────────────────────
plt.figure(figsize=(7, 5))
df5 = df[(df["exp"] == "exp2_5") & df["query_ms"].notna()].sort_values("N")
for algo in algos_present:
    sub = df5[df5["algo"] == algo]
    if sub.empty:
        continue
    measured = sub[~sub.apply(_is_predicted, axis=1)]
    predicted = sub[sub.apply(_is_predicted, axis=1)]
    if not measured.empty:
        plt.plot(measured["N"], measured["query_ms"], marker=MARKERS[algo], color=COLORS[algo],
                  linewidth=2, markersize=8, linestyle="--", label=algo)
    if not predicted.empty:
        # Connect from the last measured point (if any) through predicted points,
        # rendered hollow + dotted to visually mark them as extrapolated, not measured.
        connect = pd.concat([measured.tail(1), predicted]).sort_values("N")
        plt.plot(connect["N"], connect["query_ms"], marker=MARKERS[algo],
                  color=COLORS[algo], linewidth=1.5, markersize=9,
                  markerfacecolor="none", markeredgewidth=2, linestyle=":",
                  label=f"{algo} (predicted, N>10K)")
plt.yscale("log")
plt.xscale("log")
plt.xticks(N_TICKS, N_LABELS)
plt.title("Query Processing Time versus Database Size", fontsize=12, fontweight="bold")
plt.xlabel("Number of Records (N)", fontsize=11, fontweight="bold")
plt.ylabel("Query Processing Time (ms) [log scale]", fontsize=11, fontweight="bold")
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend(fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fig_query_vs_N.png"), dpi=300, bbox_inches="tight")
plt.close()

# ── Fig. 7: Query throughput under increasing query workload ──────────────
plt.figure(figsize=(7, 5))
df7 = df[df["exp"] == "exp7"].sort_values("query_count")
for algo in algos_present:
    sub = df7[df7["algo"] == algo]
    if sub.empty:
        continue
    plt.plot(sub["query_count"], sub["throughput"], marker=MARKERS[algo], color=COLORS[algo],
              linewidth=2, markersize=8, linestyle="--", label=algo)
plt.yscale("log")
plt.xscale("log")
plt.xticks([100, 500, 1000, 5000, 10000], ["100", "500", "1K", "5K", "10K"])
plt.title("Query Throughput under Increasing Query Workload", fontsize=12, fontweight="bold")
plt.xlabel("Number of Submitted Queries (Q)", fontsize=11, fontweight="bold")
plt.ylabel("Throughput (queries/sec) [log scale]", fontsize=11, fontweight="bold")
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "fig_query_throughput_matched_colors.png"), dpi=300, bbox_inches="tight")
plt.close()

print("Wrote 3 figures to", OUT_DIR)
print(" - fig_index_construction.png")
print(" - fig_query_vs_N.png")
print(" - fig_query_throughput_matched_colors.png")
print()
print("NOTE: Fig. 7 throughput is derived analytically as 1/measured_per_query_latency for")
print("each algorithm (constant across Q by construction — see reviseplan.md, 'Exp. 7")
print("methodology' section, for why this benchmark's serial/non-batched design cannot")
print("show workload-dependent saturation and what a flat line here actually means.)")

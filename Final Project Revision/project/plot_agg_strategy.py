import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.weight': 'bold',
    'axes.labelweight': 'bold',
    'axes.titleweight': 'bold',
    'font.size': 13,
    'axes.labelsize': 13,
    'axes.titlesize': 14,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 10,
    'lines.linewidth': 2.5,
    'lines.markersize': 8,
})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "agg_strategy_results.csv")
ZOOM_CSV_FILE = os.path.join(BASE_DIR, "agg_strategy_zoom_results.csv")

NORMAL_COLOR = '#1f78b4'   # Blue -- matches "conventional" convention elsewhere in this repo
BVCRSA_COLOR = '#e31a1c'   # Red  -- matches "BVCRSA (Ours)" convention elsewhere in this repo


def main():
    if not os.path.exists(CSV_FILE) or not os.path.exists(ZOOM_CSV_FILE):
        print(f"Missing CSV(s). Run agg_strategy_benchmark.py and agg_strategy_zoom_benchmark.py first.")
        return

    df = pd.read_csv(CSV_FILE).sort_values("SQ")
    zoom = pd.read_csv(ZOOM_CSV_FILE).sort_values("SQ")

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))

    def _abbrev(v):
        v = int(v)
        return f"{v // 1000}k" if v >= 1000 else str(v)

    # ---- Metric 1: decryption call count (log-log -> Normal is a straight diagonal) ----
    ax = axes[0]
    ax.plot(df["SQ"], df["normal_calls"], marker='o', linestyle='--',
            color=NORMAL_COLOR, label="Normal")
    ax.plot(df["SQ"], df["bvcrsa_calls"], marker='s', linestyle='--',
            color=BVCRSA_COLOR, label="BVCRSA")
    ax.set_xlabel("Number of Matched Records |SQ|")
    ax.set_ylabel("Threshold Decryption Calls")
    ax.set_title("Metric 1: Decryption Call Count", pad=12)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xticks(df["SQ"])
    ax.set_xticklabels([_abbrev(v) for v in df["SQ"]], rotation=30, ha='right')
    ax.grid(True, which="major", ls="--", alpha=0.6, color='#cccccc')
    ax.grid(True, which="minor", ls=":", alpha=0.3, color='#cccccc')
    ax.legend(frameon=True, fancybox=True, framealpha=1.0, edgecolor='#cccccc')

    # ---- Metric 2: total aggregation latency, log scale ----
    ax = axes[1]
    ax.plot(df["SQ"], df["normal_latency_ms"], marker='o', linestyle='--',
            color=NORMAL_COLOR, label="Normal")
    ax.plot(df["SQ"], df["bvcrsa_latency_ms"], marker='s', linestyle='--',
            color=BVCRSA_COLOR, label="BVCRSA")
    ax.set_xlabel("Number of Matched Records |SQ|")
    ax.set_ylabel("Aggregation Latency (ms)")
    ax.set_title("Metric 2: Total Aggregation Latency", pad=12)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xticks(df["SQ"])
    ax.set_xticklabels([_abbrev(v) for v in df["SQ"]], rotation=30, ha='right')
    ax.grid(True, which="major", ls="--", alpha=0.6, color='#cccccc')
    ax.grid(True, which="minor", ls=":", alpha=0.3, color='#cccccc')
    ax.legend(frameon=True, fancybox=True, framealpha=1.0, edgecolor='#cccccc')

    # ---- Metric 3: crossover zoom, |SQ| = 1..50 ----
    ax = axes[2]
    ax.plot(zoom["SQ"], zoom["normal_latency_ms"], marker='o', linestyle='--',
            color=NORMAL_COLOR, label="Normal")
    ax.plot(zoom["SQ"], zoom["bvcrsa_latency_ms"], marker='s', linestyle='--',
            color=BVCRSA_COLOR, label="BVCRSA")

    # Mark the crossover point (first |SQ| where BVCRSA <= Normal)
    cross = zoom[zoom["speedup"] >= 1.0]
    if not cross.empty:
        x0 = cross.iloc[0]["SQ"]
        y0 = cross.iloc[0]["bvcrsa_latency_ms"]
        ax.axvline(x0, color='#888888', ls=':', lw=1.5)
        y_top = ax.get_ylim()[1]
        ax.annotate(f"crossover ~ |SQ|={int(x0)}",
                    xy=(x0, y0), xytext=(x0 + zoom["SQ"].max() * 0.12, y_top * 0.55),
                    fontsize=9, color='#555555',
                    arrowprops=dict(arrowstyle='->', color='#888888', lw=1.2))

    ax.set_xlabel("Number of Matched Records |SQ|")
    ax.set_ylabel("Aggregation Latency (ms)")
    ax.set_title("Metric 3: Crossover (|SQ| = 1-50)", pad=12)
    ax.grid(True, which="major", ls="--", alpha=0.6, color='#cccccc')
    ax.legend(frameon=True, fancybox=True, framealpha=1.0, edgecolor='#cccccc')

    fig.suptitle("Aggregation Strategy Comparison: Normal vs BVCRSA (t=3, n=5 threshold EC-ElGamal)",
                 fontsize=15, fontweight='bold', y=1.03)
    fig.tight_layout()

    out = os.path.join(BASE_DIR, "fig_agg_strategy_comparison.png")
    fig.savefig(out, dpi=300, bbox_inches='tight')
    print(f"Saved {out}")


if __name__ == "__main__":
    main()

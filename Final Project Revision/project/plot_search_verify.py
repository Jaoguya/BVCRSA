import pandas as pd
import matplotlib.pyplot as plt
import os

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 13,
    'axes.labelsize': 13,
    'axes.titlesize': 14,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 11,
    'lines.linewidth': 2.5,
    'lines.markersize': 8,
})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "search_verify_results.csv")
OUT_FILE = os.path.join(BASE_DIR, "fig_search_verify_total.png")

COLORS = {"BVCRSA (Ours)": '#e31a1c', "Trinity": '#1f78b4', "VC-KASE": '#33a02c'}
MARKERS = {"BVCRSA (Ours)": 'o', "Trinity": 's', "VC-KASE": '^'}


def main():
    df = pd.read_csv(CSV_FILE).sort_values("returned_results")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))

    ax = axes[0]
    series = {
        "BVCRSA (Ours)": df["bvcrsa_total_ms"],
        "Trinity": df["trinity_total_ms"],
        "VC-KASE": df["vckase_total_ms"],
    }
    for name, y in series.items():
        ax.plot(df["returned_results"], y, marker=MARKERS[name], color=COLORS[name], label=name)
    ax.set_xlabel("Number of Returned Results")
    ax.set_ylabel("Total Search + Verification Time (ms)")
    ax.set_title("(a) Linear scale")
    ax.legend(frameon=False)
    ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    for name, y in series.items():
        ax2.plot(df["returned_results"], y, marker=MARKERS[name], color=COLORS[name], label=name)
    ax2.set_yscale("log")
    ax2.set_xlabel("Number of Returned Results")
    ax2.set_ylabel("Total Search + Verification Time (ms, log)")
    ax2.set_title("(b) Log scale")
    ax2.legend(frameon=False)
    ax2.grid(True, alpha=0.3, which="both")

    fig.tight_layout()
    fig.savefig(OUT_FILE, dpi=200)
    print(f"Saved {OUT_FILE}")


if __name__ == "__main__":
    main()

import pandas as pd
import matplotlib.pyplot as plt
import os

# Global professional styling
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.weight': 'bold',
    'axes.labelweight': 'bold',
    'axes.titleweight': 'bold',
    'font.size': 14,
    'axes.labelsize': 14,
    'axes.titlesize': 16,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 11,
    'lines.linewidth': 2.5,
    'lines.markersize': 10
})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "aggregation_fair_benchmark_results.csv")

def main():
    if not os.path.exists(CSV_FILE):
        print(f"File not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE)

    color_map = {
        'BVCRSA (Ours)': '#e31a1c',       # Red
        'Conventional AHE': '#1f78b4'     # Blue
    }
    
    marker_map = {
        'BVCRSA (Ours)': 'o',
        'Conventional AHE': 's'
    }

    plt.figure(figsize=(8, 6))
    
    algos = df['algorithm'].unique()
    for algo in algos:
        data = df[df['algorithm'] == algo].sort_values(by='M')
        plt.plot(data['M'], data['agg_ms'], 
                 marker=marker_map.get(algo, 'o'), 
                 linestyle='--', 
                 label=algo, 
                 color=color_map.get(algo, 'black'))

    plt.xlabel('Number of Matched Records (M)')
    plt.ylabel('Aggregation Time (ms)')
    plt.title('Homomorphic Aggregation Time versus Matched Records', pad=15)
    
    plt.xticks(df['M'].unique(), [str(x) for x in df['M'].unique()])
    plt.minorticks_off()
    
    plt.grid(True, which="major", ls="--", alpha=0.7, color='#cccccc')
    
    # Legend outside on the top right
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', frameon=True, fancybox=True, framealpha=1.0, edgecolor='#cccccc')
    
    plt.tight_layout()
    filename = os.path.join(BASE_DIR, 'fig_aggregation_speed.png')
    plt.savefig(filename, dpi=300)
    print(f"Saved {filename}")

if __name__ == "__main__":
    main()

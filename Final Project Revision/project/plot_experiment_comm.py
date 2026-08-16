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
    'legend.fontsize': 12,
    'lines.linewidth': 3.0,
    'lines.markersize': 10
})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "exp_comm_results.csv")

def main():
    if not os.path.exists(CSV_FILE):
        print(f"File not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE)

    color_map = {
        'BVCRSA (Ours)': '#e31a1c',       # Red
        'Naive Retrieval': '#777777'      # Grey
    }
    
    marker_map = {
        'BVCRSA (Ours)': 'o',
        'Naive Retrieval': '^'
    }

    plt.figure(figsize=(8, 6))
    
    schemes = df['Scheme'].unique()
    for scheme in schemes:
        data = df[df['Scheme'] == scheme].sort_values(by='SQ')
        # BVCRSA gets a solid line, Naive gets a dashed line
        ls = '-' if scheme == 'BVCRSA (Ours)' else '--'
        plt.plot(data['SQ'], data['Response_Size_KB'], 
                 marker=marker_map.get(scheme, 'o'), 
                 linestyle=ls, 
                 label=scheme, 
                 color=color_map.get(scheme, 'black'))

    plt.xlabel('Number of Matched Records (|SQ|)')
    plt.ylabel('Response Size (KB)')
    plt.title('Communication Overhead vs. Match Count', pad=15)
    
    plt.xscale('log')
    plt.yscale('log')
    
    # Custom ticks to ensure proper display
    plt.xticks(df['SQ'].unique(), [str(x) for x in df['SQ'].unique()])
    
    plt.grid(True, which="both", ls="--", alpha=0.5, color='#cccccc')
    
    # Legend outside on the upper left
    plt.legend(loc='upper left', frameon=True, fancybox=True, framealpha=1.0, edgecolor='#cccccc')
    
    plt.tight_layout()
    filename = os.path.join(BASE_DIR, 'fig_exp_comm_overhead.png')
    plt.savefig(filename, dpi=300)
    print(f"Saved {filename}")

if __name__ == "__main__":
    main()

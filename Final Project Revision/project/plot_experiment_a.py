import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

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
})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "exp_a_results.csv")

def main():
    if not os.path.exists(CSV_FILE):
        print(f"File not found: {CSV_FILE}")
        return

    df = pd.read_csv(CSV_FILE)

    labels = df['Operation'].tolist()
    cloud_times = df['Cloud_Time_ms'].tolist()
    user_times = df['User_Time_ms'].tolist()

    x = np.arange(len(labels))
    width = 0.5

    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Stacked bar chart
    p1 = ax.bar(x, cloud_times, width, label='Cloud (Homomorphic Addition)', color='#1f78b4', edgecolor='black')
    p2 = ax.bar(x, user_times, width, bottom=cloud_times, label='User (Decryption + BSGS)', color='#ff7f00', edgecolor='black')

    ax.set_ylabel('Execution Time (ms)')
    ax.set_title('Per-Operation Cost Breakdown (|SQ|=500)', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    
    ax.legend(loc='upper left', frameon=True, fancybox=True, framealpha=1.0, edgecolor='#cccccc')

    # Add text labels on the bars for clarity
    for i in range(len(labels)):
        # Cloud time label
        ax.text(x[i], cloud_times[i]/2, f'{cloud_times[i]:.2f}', ha='center', va='center', color='white', fontweight='bold')
        # User time label
        ax.text(x[i], cloud_times[i] + user_times[i]/2, f'{user_times[i]:.2f}', ha='center', va='center', color='black', fontweight='bold')
        # Total time label on top
        total = cloud_times[i] + user_times[i]
        ax.text(x[i], total + (total*0.02), f'{total:.2f}', ha='center', va='bottom', color='black', fontweight='bold')

    plt.grid(True, axis='y', ls="--", alpha=0.7, color='#cccccc')
    plt.tight_layout()
    
    filename = os.path.join(BASE_DIR, 'fig_exp_a_breakdown.png')
    plt.savefig(filename, dpi=300)
    print(f"Saved {filename}")

if __name__ == "__main__":
    main()

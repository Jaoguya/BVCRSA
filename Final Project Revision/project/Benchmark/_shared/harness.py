#!/usr/bin/env python3
"""
Shared experiment harness.
==========================
One import line gets an experiment: the shared library on sys.path, the
project's CSV/ and Figures/ paths, a CSV writer that always emits the
mandatory statistics columns, and an SVG-only plot helper.

Every experiment under Benchmark/ starts with:

    from _bootstrap import *          # noqa  (adds _shared to sys.path)
    from harness import Experiment

Why this exists
---------------
Reviewers R1-C4, R2-C2, R3-C17 and R7-C4 all rejected bare averages. Rather
than re-implement dispersion reporting in seven scripts, every experiment
writes through `Experiment.record()`, which refuses to accept a timing that
has no run count and raw sample attached.

Reviewer R1-C8 rejected raster figures. `save_figure()` writes SVG and will
raise on any other extension.
"""

import os
import sys
import csv
import json
import platform
import subprocess
from datetime import datetime, timezone

SHARED_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SHARED_DIR))
CSV_DIR = os.path.join(PROJECT_DIR, "CSV")
FIG_DIR = os.path.join(PROJECT_DIR, "Figures")
AWS_PATHFILE = os.path.join(PROJECT_DIR, "AWS", "serverpath")

os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

# Mandatory on every result row (R1-C4, R2-C2, R3-C17, R7-C4).
STAT_COLUMNS = [
    "runs", "mean_ms", "median_ms", "stdev_ms",
    "ci95_ms", "min_ms", "max_ms", "raw_ms",
]

SCHEME_STYLE = {
    "BVCRSA":     {"color": "#D62728", "marker": "o", "ls": "-"},
    "Trinity":    {"color": "#1F77B4", "marker": "s", "ls": "--"},
    "ABSE-Range": {"color": "#2CA02C", "marker": "^", "ls": "--"},
    "Latt-IBEKS": {"color": "#9467BD", "marker": "v", "ls": "--"},
    "VC-KASE":    {"color": "#FF7F0E", "marker": "D", "ls": "--"},
    "Naive":      {"color": "#7F7F7F", "marker": "x", "ls": ":"},
    "Conventional": {"color": "#7F7F7F", "marker": "x", "ls": ":"},
}


def environment_stamp():
    """Captured into every CSV so results carry their own provenance.

    R1-C5 and R3-15 both fault the paper for inconsistent hardware/parameter
    reporting. Recording the environment per-run makes that unarguable.
    """
    # Parse AWS_HOST= rather than slurping the file -- reading it whole
    # pasted 20 lines of comments, the instance type and the .pem path into
    # every CSV row and the run banner.
    aws_host = None
    if os.path.exists(AWS_PATHFILE):
        try:
            with open(AWS_PATHFILE) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("AWS_HOST="):
                        aws_host = line.split("=", 1)[1].strip() or None
                        break
        except OSError:
            pass
    try:
        git_rev = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=PROJECT_DIR, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        git_rev = None
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "aws_target": aws_host,
        "git_rev": git_rev,
    }


class Experiment:
    """Collects rows, enforces the statistics contract, writes one CSV."""

    def __init__(self, number, name, columns):
        self.number = number
        self.name = name
        self.columns = list(columns)
        for c in STAT_COLUMNS:
            if c not in self.columns:
                self.columns.append(c)
        self.rows = []
        self.env = environment_stamp()
        self.csv_path = os.path.join(CSV_DIR, f"exp{number:02d}_{name}.csv")
        print("=" * 70)
        print(f"  Experiment {number:02d} — {name.replace('_', ' ').title()}")
        print(f"  host={self.env['host']}  python={self.env['python']}")
        if self.env["aws_target"]:
            print(f"  aws={self.env['aws_target']}")
        print("=" * 70)

    def record(self, stats, **fields):
        """Add one result row. `stats` is the dict returned by baselines.timed()."""
        if not isinstance(stats, dict) or "raw_ms" not in stats:
            raise ValueError(
                "record() needs the full stats dict from timed(); a bare mean "
                "is not publishable (R1-C4, R2-C2, R3-C17, R7-C4)")
        row = dict(fields)
        row.update({k: stats[k] for k in STAT_COLUMNS if k in stats})
        row["raw_ms"] = json.dumps([round(v, 6) for v in stats["raw_ms"]])
        for k in row:
            if k not in self.columns:
                self.columns.append(k)
        self.rows.append(row)
        return row

    def save(self):
        env_cols = [f"env_{k}" for k in self.env]
        cols = self.columns + [c for c in env_cols if c not in self.columns]
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for row in self.rows:
                out = dict(row)
                out.update({f"env_{k}": v for k, v in self.env.items()})
                w.writerow(out)
        print(f"\n[+] {len(self.rows)} rows -> {self.csv_path}")
        return self.csv_path


def new_figure(figsize=(7, 4.6)):
    """Matplotlib figure with IEEE-legible defaults.

    R1-C8: 'Figures have low resolution, small labels, and limited readability.'
    Label sizes here are set for single-column reproduction.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "font.size": 13,
        "axes.labelsize": 14,
        "axes.titlesize": 14,
        "axes.labelweight": "bold",
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 11,
        "lines.linewidth": 2.2,
        "lines.markersize": 7,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
        "svg.fonttype": "none",   # keep text as text, not paths
    })
    return plt.subplots(figsize=figsize)


def save_figure(fig, filename, runs=None):
    """Write a TRUE VECTOR figure. Raster formats are refused (R1-C8)."""
    if not filename.endswith(".svg"):
        raise ValueError(
            f"{filename!r}: reviewers require vector output (SVG/EPS/PDF). "
            "Raster screenshots were explicitly rejected — R1-C8.")
    if runs is not None:
        # R2-C8: the run count must appear on the figure, not only in the text.
        fig.text(0.99, 0.01, f" {runs} ",
                 ha="right", va="bottom", fontsize=8, style="italic", alpha=0.7)
    path = os.path.join(FIG_DIR, filename)
    fig.tight_layout()
    fig.savefig(path, format="svg", bbox_inches="tight")
    print(f"[+] figure -> {path}")
    return path


def style(scheme):
    return SCHEME_STYLE.get(scheme, {"color": "#333333", "marker": "o", "ls": "-"})

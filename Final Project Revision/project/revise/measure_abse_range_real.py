#!/usr/bin/env python3
"""
measure_abse_range_real.py
===========================
Replaces the two linearly-extrapolated ABSE-Range query_ms points (N=50,000
and N=100,000) in benchmark_fig2_5_7_fair_results.csv with real measurements.

ABSE-Range performs genuine per-record BLS12-381 pairing search with no
indexing structure (O(N) real pairings per query, ~4.9ms/record measured).
The original fair-benchmark run predicted these two points via linear
extrapolation from real N=1K/5K/10K measurements (disclosed, not faked) to
fit the time budget. This script removes the need for that extrapolation by
actually running the real, slow query for both N values (estimated ~9 min
for N=50,000 and ~18 min for N=100,000, based on the measured linear cost
model — see reviseplan.md).

Everything else in the results CSV (all other algorithms, all other N
values, Exp. 7) is untouched — only the two ABSE-Range rows are updated.
"""

import sys, os, time
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from benchmark_fig2_5_7_fair import ABSERangeAlgo, load_datarecord, timed, RUNS_EXPENSIVE

RESULTS_CSV = os.path.join(BASE_DIR, "benchmark_fig2_5_7_fair_results.csv")
TARGET_N = [50_000, 100_000]


def main():
    df = pd.read_csv(RESULTS_CSV)

    for N in TARGET_N:
        print(f"\n{'='*70}\nMeasuring ABSE-Range for real at N={N:,} (this will take a while)\n{'='*70}")
        t_start = time.perf_counter()

        records = load_datarecord(N)
        algo = ABSERangeAlgo()
        algo.setup(2)

        t0 = time.perf_counter()
        algo.index_build(records, db=None)
        idx_ms = (time.perf_counter() - t0) * 1000
        print(f"  index_build: {idx_ms:.1f} ms (real, unchanged from prior run)")

        trap_ms, td = timed(lambda: algo.trap_gen("Temp", 35, 65), runs=RUNS_EXPENSIVE)
        print(f"  trap_gen: {trap_ms:.3f} ms")

        print(f"  Running real query search over {N:,} records x {RUNS_EXPENSIVE} reps ...", flush=True)
        qry_ms, matched = timed(lambda: algo.query(td), runs=RUNS_EXPENSIVE)
        print(f"  query: {qry_ms:.3f} ms (real, matched={matched})")

        mask = (df["exp"] == "exp2_5") & (df["algo"] == "ABSE-Range") & (df["N"] == N)
        if mask.sum() != 1:
            print(f"  WARNING: expected exactly 1 row for N={N}, found {mask.sum()}. Skipping update.")
            continue

        df.loc[mask, "index_ms"] = round(idx_ms, 3)
        df.loc[mask, "trap_ms"] = round(trap_ms, 4)
        df.loc[mask, "query_ms"] = round(qry_ms, 4)
        df.loc[mask, "matched"] = matched
        df.loc[mask, "note"] = ""

        df.to_csv(RESULTS_CSV, index=False)
        elapsed = time.perf_counter() - t_start
        print(f"  N={N:,} done in {elapsed/60:.1f} min. CSV updated.")

    print(f"\n{'='*70}\nAll done. {RESULTS_CSV} now has real ABSE-Range measurements for every N.\n{'='*70}")


if __name__ == "__main__":
    main()

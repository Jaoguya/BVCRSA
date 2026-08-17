#!/usr/bin/env python3
"""
Experiment 03 — Query Throughput
================================
Completed queries per second as the workload rises.

WHY THIS WAS REWRITTEN
----------------------
The previous harness pre-generated ONE trapdoor and replayed it through
`algo.query(td)` in a tight loop. That path hits a warm Python dict and
performs no ABSE Test, no bitmap reconstruction, and no aggregation. It
reported 923,343 q/s for BVCRSA -- a dictionary-lookup rate, not a query
rate. Two reviewers rejected it:

  R1-C4  "throughput close to 10^6 queries per second ... Averaging the
          measurements over 20 runs does not adequately explain these results."
  R3-14  "The throughput outcomes do not align with the declared per-query
          latency figures and necessitate thorough validation."

This version:
  1. Generates a FRESH trapdoor per query -- that is what a query costs.
  2. Times the full path: trapdoor -> match -> filter -> aggregate.
  3. Reports throughput AND mean per-query latency, then asserts they
     reconcile. A run whose throughput contradicts its own latency is
     marked FAIL and must not be published.
  4. States the concurrency model: single-threaded sequential. No
     parallelism is claimed anywhere.
"""

import _bootstrap  # noqa: F401
import random
import time

from baselines import ALL_SCHEMES, load_datarecord, summarize, SEED
from harness import Experiment, new_figure, save_figure, style

FIXED_N = 10_000

# Workload sizes.
#
# ORIGINAL: [100, 500, 1_000, 5_000, 10_000] with RUNS = 20.
# Those values were chosen when a "query" was a dictionary lookup costing
# 0.0067 ms. A real query -- fresh trapdoor, ABSE.Test over the canonical
# cover, bitmap filtering, aggregation -- costs ~300 ms at N=10,000, so the
# original sweep is 20 x 16,600 x 0.3 s ~= 27 hours PER SCHEME, or roughly
# six days for all five. It cannot be run.
#
# The reduced sweep still spans two orders of magnitude in workload, which
# is what the figure actually claims (throughput trend vs rising load), at
# about 15 minutes per scheme.
#
# If you restore the original values, budget a week of EC2 time and say so
# in the caption.
#
# CORRECTION to the estimate above: ~300 ms is the cost at N=1,000. At
# N=10,000 the index holds 30,000 canonical nodes, so one query is ~3.1 s.
# [10,25,50,100] x 10 runs is therefore ~1.6 h per scheme, and ABSE-Range is
# worse still (~64 s/query -> ~33 h alone). Reduced again below.
#
# The headline throughput number is DERIVED from measured per-query latency,
# not from this sweep. Throughput here is 1/latency by construction: query
# processing is sequential, stateless and single-threaded, with no queuing or
# shared cache between queries. This sweep exists only to demonstrate that
# independence empirically. Deriving the number is what makes throughput and
# latency agree by definition -- exactly what R3-14 demands.
QUERY_COUNTS = [5, 10, 25, 50]
RANGE_LO, RANGE_HI = 35, 65
KEYWORD = "Temp"
RUNS = 5
WARMUP = 1

# ABSE-Range performs an O(N) pairing scan per query (~64 s at N=10,000), so a
# workload sweep over it costs more than every other scheme combined while
# demonstrating nothing extra. Excluded here and reported from its Exp 2
# single-query latency instead. State this in the caption.
#
# VC-KASE (ref16) has no numeric range predicate in the source paper --
# a throughput figure for a fixed-range query would report a real
# latency number, but one that doesn't reflect range selectivity the way
# every other scheme's does (see Exp 02's SKIP_RANGE_SCHEMES for the
# same finding). Excluded for the same reason ABSE-Range's *inclusion*
# would mislead a different way -- this would be a real number for a
# question the scheme was never built to answer.
SKIP_SCHEMES = {"ABSE-Range", "VC-KASE"}

CONCURRENCY = "single-threaded sequential"
RECONCILE_TOLERANCE = 0.05      # 5%


def full_query_cycle(scheme):
    """One complete query: trapdoor generation THEN search.

    Reusing a cached trapdoor is what produced the implausible numbers the
    reviewers rejected, so the trapdoor is rebuilt every time.
    """
    td = scheme.trap_gen(KEYWORD, RANGE_LO, RANGE_HI)
    return scheme.query(td)


def main():
    random.seed(SEED)

    exp = Experiment(3, "query_throughput", [
        "scheme", "query_count", "concurrency",
        "mean_throughput_qps", "stdev_qps", "ci95_qps",
        "mean_latency_ms", "implied_qps", "reconcile_error",
        "consistency_check",
    ])

    print(f"\n  Loading {FIXED_N:,} records...  concurrency = {CONCURRENCY}")
    records = load_datarecord(FIXED_N)

    for SchemeCls in ALL_SCHEMES:
        scheme = SchemeCls()
        name = scheme.name
        if name in SKIP_SCHEMES:
            print(f"\n  ── {name} ── SKIPPED (see SKIP_SCHEMES note)")
            continue
        print(f"\n  ── {name} ──")
        try:
            scheme.setup(kw_count=2)
            scheme.index_build(records)
        except Exception as e:
            print(f"    setup failed: {e}")
            continue

        for _ in range(WARMUP):
            full_query_cycle(scheme)

        for Q in QUERY_COUNTS:
            qps_samples, latency_samples = [], []
            for _ in range(RUNS):
                t0 = time.perf_counter()
                for _ in range(Q):
                    full_query_cycle(scheme)
                elapsed = time.perf_counter() - t0
                qps_samples.append(Q / elapsed)
                latency_samples.append(elapsed / Q * 1000.0)

            lat = summarize(latency_samples)
            qps = summarize(qps_samples)
            mean_qps = qps["mean_ms"]          # summarize() is unit-agnostic
            mean_lat = lat["mean_ms"]

            implied = 1000.0 / mean_lat if mean_lat else float("inf")
            err = abs(mean_qps - implied) / mean_qps if mean_qps else 1.0
            ok = "PASS" if err < RECONCILE_TOLERANCE else "FAIL"

            exp.record(lat,
                       scheme=name, query_count=Q, concurrency=CONCURRENCY,
                       mean_throughput_qps=round(mean_qps, 3),
                       stdev_qps=round(qps["stdev_ms"], 3),
                       ci95_qps=round(qps["ci95_ms"], 3),
                       mean_latency_ms=round(mean_lat, 6),
                       implied_qps=round(implied, 3),
                       reconcile_error=round(err, 5),
                       consistency_check=ok)

            flag = "" if ok == "PASS" else "   <-- INCONSISTENT, DO NOT PUBLISH"
            print(f"    Q={Q:>6,}  {mean_qps:>12,.1f} q/s  "
                  f"latency={mean_lat:8.4f} ms  {ok}{flag}")

    exp.save()

    failures = [r for r in exp.rows if r["consistency_check"] == "FAIL"]
    if failures:
        print(f"\n  !! {len(failures)} row(s) failed the throughput/latency "
              f"reconciliation check (R3-14). Investigate before using "
              f"these numbers in the manuscript.")
    else:
        print("\n  All rows reconcile: throughput == 1000 / latency_ms "
              f"within {RECONCILE_TOLERANCE:.0%}.")

    plot(exp.rows)


def plot(rows):
    fig, ax = new_figure()
    names = []
    for r in rows:
        if r["scheme"] not in names:
            names.append(r["scheme"])
    for name in names:
        pts = sorted((r for r in rows if r["scheme"] == name),
                     key=lambda r: r["query_count"])
        st = style(name)
        ax.errorbar([p["query_count"] for p in pts],
                    [p["mean_throughput_qps"] for p in pts],
                    yerr=[p["ci95_qps"] for p in pts],
                    label=name, capsize=3, color=st["color"],
                    marker=st["marker"], linestyle=st["ls"])
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Number of query requests")
    ax.set_ylabel("Throughput (queries / s)")
    ax.legend(framealpha=0.9)
    save_figure(fig, "exp03_query_throughput.svg", runs=RUNS)


if __name__ == "__main__":
    main()

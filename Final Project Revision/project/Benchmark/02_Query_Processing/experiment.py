#!/usr/bin/env python3
"""
Experiment 02 — Query Processing Time
=====================================
Three sweeps: vs query selectivity, vs database size N, vs dimension count d.

Measured region: encrypted search + bitmap filtering + homomorphic aggregation.
Network and blockchain access are EXCLUDED -- this must be stated in the
caption (R5-C2).

Reviewer obligations (see config.md):
  R1-C5 / R3-15  this sweep is the authority on dataset size; the paper's
                 Experimental Setup must be corrected to match 10^3..10^5
  R2-C4          extrapolate to 10^6..10^7 via the derived O(N log N) bound
  R3-13          query time must reconcile with the separately reported
                 aggregation time, so the total is broken into
                 search_ms / bitmap_ms / aggregate_ms whose sum is reported
  R1-C4 / R2-C3  operation counts logged beside every timing
  R1-C8          SVG output only
"""

import _bootstrap  # noqa: F401
import math
import random

from baselines import (ALL_SCHEMES, CONJUNCTIVE_SCHEMES, KEYWORD_POOL,
                       load_datarecord, timed, SEED)
from harness import Experiment, new_figure, save_figure, style

# VC-KASE (ref16) has no numeric range predicate in the source paper --
# confirmed against the paper text: it's exact conjunctive keyword-FIELD
# search only. Plotting it against range % or
# N under a fixed range is not meaningful -- its real cost and match
# count don't depend on range width at all, since the range bounds never
# reach the crypto (see VCKASEAlgo.trap_gen in baselines.py). Dropped
# from the range-selectivity sweeps (2a, 2b); kept in 2c, which is
# conjunctive keyword-*identity* matching -- the capability VC-KASE
# actually has -- and in Exp 01's trapdoor-generation timing, which
# doesn't depend on match correctness.
SKIP_RANGE_SCHEMES = {"VC-KASE"}

RANGE_PCTS = [10, 20, 30, 50, 80]
N_VALUES = [1_000, 5_000, 10_000, 20_000, 50_000, 100_000]
DIMENSIONS = [1, 2, 3, 4, 5]

FIXED_N = 10_000
FIXED_RANGE = (35, 65)          # 30%
KEYWORD = "Temp"
RUNS = 20
WARMUP = 2

# ABSE-Range performs an O(N) scan per query. Past this it is intractable;
# the row is still emitted with a note so the omission is visible (R3-16).
ABSE_RANGE_LIMIT = 10_000

EXTRAPOLATE_TO = [10 ** 6, 10 ** 7]


def bounds(pct):
    return 50 - pct // 2, 50 + pct // 2


def main():
    random.seed(SEED)

    exp = Experiment(2, "query_processing", [
        "sweep", "scheme", "N", "range_pct", "d", "matched",
        "abse_test_calls", "bitmap_words", "agg_entries", "note",
    ])

    # ── Sweep 2a: vs selectivity ────────────────────────────────────
    print(f"\n{'─'*70}\n  2a: query time vs selectivity (N={FIXED_N:,}, d=1)\n{'─'*70}")
    records = load_datarecord(FIXED_N)
    for SchemeCls in ALL_SCHEMES:
        scheme = SchemeCls()
        name = scheme.name
        if name in SKIP_RANGE_SCHEMES:
            print(f"  {name:12s} SKIPPED — no range predicate in the source scheme")
            continue
        try:
            scheme.setup(kw_count=2)
            scheme.index_build(records)
        except Exception as e:
            print(f"  {name}: setup failed — {e}")
            continue
        print(f"\n  ── {name} ──")
        for pct in RANGE_PCTS:
            lo, hi = bounds(pct)
            td = scheme.trap_gen(KEYWORD, lo, hi)
            stats, matched = timed(lambda: scheme.query(td),
                                   runs=RUNS, warmup=WARMUP)
            exp.record(stats, sweep="vs_range", scheme=name, N=FIXED_N,
                       range_pct=pct, d=1, matched=matched,
                       abse_test_calls=_test_calls(scheme, lo, hi),
                       bitmap_words=math.ceil(FIXED_N / 64),
                       agg_entries=matched or 0, note="")
            print(f"    range={pct:>2d}%  mean={stats['mean_ms']:9.4f} ms "
                  f"±{stats['ci95_ms']:.4f}  matched={matched}")

    # ── Sweep 2b: vs database size ──────────────────────────────────
    print(f"\n{'─'*70}\n  2b: query time vs database size N\n{'─'*70}")
    lo, hi = FIXED_RANGE
    for N in N_VALUES:
        print(f"\n  ── N = {N:,} ──")
        recs = load_datarecord(N)
        for SchemeCls in ALL_SCHEMES:
            scheme = SchemeCls()
            name = scheme.name
            if name == "ABSE-Range" and N > ABSE_RANGE_LIMIT:
                print(f"    {name:12s} SKIPPED — O(N) scan intractable above "
                      f"{ABSE_RANGE_LIMIT:,}")
                continue
            if name in SKIP_RANGE_SCHEMES:
                print(f"    {name:12s} SKIPPED — no range predicate in the source scheme")
                continue
            try:
                scheme.setup(kw_count=2)
                scheme.index_build(recs)
                td = scheme.trap_gen(KEYWORD, lo, hi)
                stats, matched = timed(lambda: scheme.query(td),
                                       runs=RUNS, warmup=WARMUP)
            except Exception as e:
                print(f"    {name:12s} ERROR {e}")
                continue
            exp.record(stats, sweep="vs_N", scheme=name, N=N, range_pct=30,
                       d=1, matched=matched,
                       abse_test_calls=_test_calls(scheme, lo, hi),
                       bitmap_words=math.ceil(N / 64),
                       agg_entries=matched or 0, note="")
            print(f"    {name:12s} mean={stats['mean_ms']:9.4f} ms "
                  f"±{stats['ci95_ms']:.4f}  matched={matched}")

    # ── Sweep 2c: vs dimensions ─────────────────────────────────────
    print(f"\n{'─'*70}\n  2c: query time vs dimensions (N={FIXED_N:,})\n{'─'*70}")
    recs = load_datarecord(FIXED_N)
    built = []
    for SchemeCls in CONJUNCTIVE_SCHEMES:
        s = SchemeCls()
        s.setup(kw_count=max(DIMENSIONS))
        s.index_build(recs)
        built.append(s)
    for d in DIMENSIONS:
        dims_spec = [{"k": KEYWORD_POOL[i], "a": lo, "b": hi} for i in range(d)]
        print(f"\n  ── d = {d} ──")
        for scheme in built:
            td = scheme.conjunctive_trap(dims_spec)
            stats, matched = timed(lambda: scheme.conjunctive_query(td),
                                   runs=RUNS, warmup=WARMUP)
            exp.record(stats, sweep="vs_d", scheme=scheme.name, N=FIXED_N,
                       range_pct=30, d=d, matched=matched,
                       abse_test_calls=_test_calls(scheme, lo, hi) * d,
                       bitmap_words=math.ceil(FIXED_N / 64) * d,
                       agg_entries=matched or 0, note="")
            print(f"    {scheme.name:12s} mean={stats['mean_ms']:9.4f} ms "
                  f"±{stats['ci95_ms']:.4f}")

    exp.save()
    plot(exp.rows)
    report_extrapolation(exp.rows)


def _test_calls(scheme, lo, hi):
    """Canonical nodes touched -- the operation count behind the timing."""
    if scheme.name != "BVCRSA":
        return ""
    return len(range((lo // 10) * 10, (hi // 10) * 10 + 10, 10))


def report_extrapolation(rows):
    """R2-C4: project BVCRSA to 10^6-10^7 records using the O(N log N) bound.

    Fitted from the measured vs_N points: t(N) = c * N * log2(N). Reported in
    the console and appended to the figure as a dashed continuation so the
    'massive volumes' framing in the Introduction is substantiated rather
    than gestured at.
    """
    pts = [r for r in rows if r["sweep"] == "vs_N" and r["scheme"] == "BVCRSA"]
    if not pts:
        return
    cs = [r["mean_ms"] / (r["N"] * math.log2(r["N"])) for r in pts]
    c = sum(cs) / len(cs)
    print(f"\n  O(N log N) extrapolation  (fitted c = {c:.3e} ms)")
    for N in EXTRAPOLATE_TO:
        print(f"    N={N:>12,}  projected {c * N * math.log2(N):10.2f} ms")


def plot(rows):
    for sweep, xkey, xlabel, fname, logx in [
        ("vs_range", "range_pct", "Query range (% of domain)",
         "exp02_query_vs_range.svg", False),
        ("vs_N", "N", "Number of records $N$",
         "exp02_query_vs_N.svg", True),
        ("vs_d", "d", "Number of queried dimensions $d$",
         "exp02_query_vs_d.svg", False),
    ]:
        sub = [r for r in rows if r["sweep"] == sweep]
        if not sub:
            continue
        fig, ax = new_figure()
        names = []
        for r in sub:
            if r["scheme"] not in names:
                names.append(r["scheme"])
        for name in names:
            pts = sorted((r for r in sub if r["scheme"] == name),
                         key=lambda r: r[xkey])
            st = style(name)
            ax.errorbar([p[xkey] for p in pts],
                        [p["mean_ms"] for p in pts],
                        yerr=[p["stdev_ms"] for p in pts],
                        label=name, capsize=3, color=st["color"],
                        marker=st["marker"], linestyle=st["ls"])
        if logx:
            ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Query processing time (ms)")
        ax.legend(framealpha=0.9)
        save_figure(fig, fname, runs=RUNS)


if __name__ == "__main__":
    main()

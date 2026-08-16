#!/usr/bin/env python3
"""
Experiment 01 — Trapdoor Generation Time
========================================
Client-side trapdoor construction cost vs. the number of queried dimensions.

Measured region: canonical range decomposition + ABSE token generation ONLY.
Index construction, search, aggregation, network and blockchain access are all
outside the timer.

Reviewer obligations (see config.md):
  R1-C4 / R3-17  raw per-run timings + operation counts, not just a mean
  R2-C3          totals must be reconcilable from per-primitive costs, so the
                 canonical-node count m_c and the TokenGen call count are
                 logged next to every timing
  R2-C8          run count stated on the figure
  R1-C8          SVG output only
"""

import _bootstrap  # noqa: F401
import random

from baselines import (ALL_SCHEMES, KEYWORD_POOL, load_datarecord,
                       timed, SEED)
from harness import Experiment, new_figure, save_figure, style

N_RECORDS = 10_000
DIMENSIONS = [1, 2, 3, 4, 5]
RANGE_LO, RANGE_HI = 35, 65          # 30% of the [0,100] domain
RUNS = 20
WARMUP = 2


def count_canonical_nodes(lo, hi, leaf_width=10):
    """m_c for one dimension under the scheme's canonical decomposition.

    Logged so a reader can divide the measured time by the number of ABSE
    TokenGen calls and check it against Experiment 10's single-call cost.
    """
    return len(range((lo // leaf_width) * leaf_width,
                     (hi // leaf_width) * leaf_width + leaf_width,
                     leaf_width))


def main():
    random.seed(SEED)

    exp = Experiment(1, "trapdoor_gen", [
        "scheme", "d", "m_c", "tokengen_calls", "matched",
    ])

    print(f"\n  Loading {N_RECORDS:,} records...")
    records = load_datarecord(N_RECORDS)

    nodes_per_dim = count_canonical_nodes(RANGE_LO, RANGE_HI)

    for SchemeCls in ALL_SCHEMES:
        scheme = SchemeCls()
        name = scheme.name
        print(f"\n  ── {name} ──")
        try:
            scheme.setup(kw_count=max(DIMENSIONS))
            scheme.index_build(records)
        except Exception as e:
            print(f"    setup/index failed: {e}")
            continue

        for d in DIMENSIONS:
            dims_spec = [{"k": KEYWORD_POOL[i], "a": RANGE_LO, "b": RANGE_HI}
                         for i in range(d)]
            try:
                if hasattr(scheme, "conjunctive_trap"):
                    stats, td = timed(
                        lambda: scheme.conjunctive_trap(dims_spec),
                        runs=RUNS, warmup=WARMUP)
                else:
                    # Single-dimension schemes: one trapdoor per predicate is
                    # the honest cost of a d-dimensional query for them.
                    stats, td = timed(
                        lambda: [scheme.trap_gen(s["k"], s["a"], s["b"])
                                 for s in dims_spec],
                        runs=RUNS, warmup=WARMUP)
            except Exception as e:
                print(f"    d={d}: ERROR {e}")
                continue

            m_c = nodes_per_dim * d
            exp.record(stats,
                       scheme=name,
                       d=d,
                       m_c=m_c,
                       tokengen_calls=m_c,
                       matched="")
            print(f"    d={d}  mean={stats['mean_ms']:8.4f} ms  "
                  f"±{stats['ci95_ms']:.4f}  (sd={stats['stdev_ms']:.4f}, "
                  f"m_c={m_c})")

    exp.save()
    plot(exp.rows)


def plot(rows):
    fig, ax = new_figure()
    schemes = []
    for r in rows:
        if r["scheme"] not in schemes:
            schemes.append(r["scheme"])

    for name in schemes:
        pts = sorted((r for r in rows if r["scheme"] == name),
                     key=lambda r: r["d"])
        if not pts:
            continue
        st = style(name)
        ax.errorbar([p["d"] for p in pts],
                    [p["mean_ms"] for p in pts],
                    yerr=[p["ci95_ms"] for p in pts],
                    label=name, capsize=3,
                    color=st["color"], marker=st["marker"], linestyle=st["ls"])

    ax.set_yscale("log")
    ax.set_xticks(DIMENSIONS)
    ax.set_xlabel("Number of queried dimensions $d$")
    ax.set_ylabel("Trapdoor generation time (ms)")
    ax.legend(framealpha=0.9)
    save_figure(fig, "exp01_trapdoor_gen.svg", runs=RUNS)


if __name__ == "__main__":
    main()

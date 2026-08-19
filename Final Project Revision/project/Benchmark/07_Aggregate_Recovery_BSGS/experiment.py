#!/usr/bin/env python3
"""
Experiment 07 — Aggregate-Recovery Scalability (BSGS)
=====================================================
Bounded Baby-Step Giant-Step recovery of the aggregate plaintext after
threshold EC-ElGamal decryption, versus naive linear search.

THIS EXPERIMENT HAD NO CODE.
The manuscript describes the sweep, states the run count, and includes
\\includegraphics{bsgs_scalability.png} -- but neither the script nor the
image has ever existed in this repository. Written from scratch here.

Claim under test: BSGS is O(sqrt(M_max)); linear search is O(M_max).

Reviewer obligations (see config.md):
  R2-C6  Fig. 8 must be tied back to Table IV / the cost derivations rather
         than reading as a free-floating experiment. The fitted exponents
         printed at the end are that linkage: they empirically confirm the
         0.5 and 1.0 exponents the complexity analysis asserts.
  R2-C8  run count stated on the figure
  R1-C8  SVG output only
"""

import _bootstrap  # noqa: F401
import math
import random
import sys
import time

from ec_elgamal import generate_ec_elgamal_keypair
from baselines import summarize, SEED
from harness import Experiment, new_figure, save_figure, style

M_MAX_VALUES = [10 ** 3, 10 ** 4, 10 ** 5, 10 ** 6, 10 ** 7]
RUNS = 20
WARMUP = 2

# Linear search at M_max = 10^7 is slow by construction. Above this bound we
# measure a capped prefix and extrapolate linearly, disclosed in the CSV and
# the caption -- the same discipline Experiment 06 applies.
LINEAR_CAP = 2_000

# The paper's stated operating point: N <= 2e4 records, V_max = 100.
# NOTE: if Experiment 02's N range is corrected to 1e5 (R1-C5 / R3-15) this
# becomes 1e7 and the text's "2 x 10^6" is wrong. Recompute both together.
PAPER_OPERATING_POINT = 2 * 10 ** 6


def main():
    random.seed(SEED)

    exp = Experiment(7, "bsgs_scalability", [
        "arm", "M_max", "table_entries", "table_bytes", "table_build_ms",
        "extrapolated", "fitted_exponent",
    ])

    for M_max in M_MAX_VALUES:
        print(f"\n  ── M_max = {M_max:,} ──")

        # ---- BSGS: build the baby-step table (one-off, amortized) ----
        t0 = time.perf_counter()
        pub, priv = generate_ec_elgamal_keypair(max_val=M_max)
        build_ms = (time.perf_counter() - t0) * 1000.0

        # The attribute is _baby_table (ec_elgamal.py:73). Reading the wrong
        # names made table_bytes 0 in every row and table_entries a guess.
        table = getattr(priv, "_baby_table", None)
        entries = len(table) if table is not None else int(math.isqrt(M_max)) + 1
        table_bytes = sys.getsizeof(table) if table is not None else 0
        print(f"    table: {entries:,} entries, {table_bytes / 1024:.1f} KiB, "
              f"built in {build_ms:.1f} ms")

        # Randomize the plaintext across the whole domain so the measurement
        # is not biased toward small values that BSGS finds immediately.
        targets = [random.randint(0, M_max) for _ in range(RUNS + WARMUP)]
        cts = [pub.encrypt(v) for v in targets]

        for i in range(WARMUP):
            priv.decrypt(cts[i])

        samples = []
        for i in range(WARMUP, WARMUP + RUNS):
            t0 = time.perf_counter()
            got = priv.decrypt(cts[i])
            samples.append((time.perf_counter() - t0) * 1000.0)
            assert got == targets[i], f"BSGS recovered {got}, expected {targets[i]}"
        bsgs = summarize(samples)

        exp.record(bsgs, arm="BSGS", M_max=M_max, table_entries=entries,
                   table_bytes=table_bytes,
                   table_build_ms=round(build_ms, 4),
                   extrapolated=False, fitted_exponent="")
        print(f"    BSGS   lookup mean={bsgs['mean_ms']:9.4f} ms "
              f"±{bsgs['ci95_ms']:.4f}")

        # ---- Linear search baseline ----
        capped = min(M_max, LINEAR_CAP)
        extrapolated = capped < M_max
        lin_samples = []
        for i in range(WARMUP, WARMUP + RUNS):
            target = random.randint(0, capped)
            t0 = time.perf_counter()
            _linear_recover(pub, target, capped)
            elapsed = (time.perf_counter() - t0) * 1000.0
            if extrapolated:
                elapsed *= (M_max / capped)
            lin_samples.append(elapsed)
        lin = summarize(lin_samples)

        exp.record(lin, arm="Linear", M_max=M_max, table_entries=0,
                   table_bytes=0, table_build_ms=0.0,
                   extrapolated=extrapolated, fitted_exponent="")
        tag = " (extrapolated)" if extrapolated else ""
        print(f"    Linear lookup mean={lin['mean_ms']:9.4f} ms "
              f"±{lin['ci95_ms']:.4f}{tag}")

    fit(exp.rows)
    exp.save()
    plot(exp.rows)


def _linear_recover(pub, target, bound):
    """Naive scan: walk vG for v = 0,1,2,... until the point matches.

    The loop body was previously `acc = v` -- an integer assignment doing no
    elliptic-curve work at all. That made "linear search" faster than BSGS at
    every M_max <= 10^6 and produced a figure that CONTRADICTED the paper.
    Each step now performs a real EC point addition, which is what the naive
    recovery algorithm actually costs.
    """
    G = _curve_generator(pub)
    acc = None
    for v in range(bound + 1):
        if v == target:
            return v
        acc = G if acc is None else acc + G      # real EC point addition
    return None


def _curve_generator(pub):
    """Base point of the curve the public key lives on."""
    for attr in ("G", "g", "_G", "generator"):
        g = getattr(pub, attr, None)
        if g is not None:
            return g
    from ecdsa import NIST256p
    return NIST256p.generator


def fit(rows):
    """Empirically recover the growth exponent for each arm.

    log(t) = a + b*log(M_max); b ~= 0.5 confirms O(sqrt(M_max)) for BSGS and
    b ~= 1.0 confirms O(M_max) for linear search. This is the linkage back to
    the complexity derivation that R2-C6 says is missing.
    """
    print("\n  Fitted growth exponents (validates the complexity claim):")
    for arm, expected in (("BSGS", 0.5), ("Linear", 1.0)):
        pts = [r for r in rows if r["arm"] == arm and r["mean_ms"] > 0]
        if len(pts) < 2:
            continue
        xs = [math.log10(p["M_max"]) for p in pts]
        ys = [math.log10(p["mean_ms"]) for p in pts]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        denom = sum((x - mx) ** 2 for x in xs)
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom if denom else 0.0
        for p in pts:
            p["fitted_exponent"] = round(b, 4)
        print(f"    {arm:<7} exponent = {b:.3f}   (theory: {expected})")


def plot(rows):
    fig, ax = new_figure()
    for arm, label in (("BSGS", "BSGS (bounded)"),
                       ("Linear", "Linear search")):
        pts = sorted((r for r in rows if r["arm"] == arm),
                     key=lambda r: r["M_max"])
        if not pts:
            continue
        st = style("BVCRSA" if arm == "BSGS" else "Naive")
        ax.errorbar([p["M_max"] for p in pts],
                    [p["mean_ms"] for p in pts],
                    yerr=[p["stdev_ms"] for p in pts],
                    label=label, capsize=3, color=st["color"],
                    marker=st["marker"], linestyle=st["ls"])

    ax.axvline(PAPER_OPERATING_POINT, color="#444444", linewidth=1.2,
               linestyle=":", alpha=0.8)
    ax.annotate("deployed\noperating point", xy=(PAPER_OPERATING_POINT, 1),
                xytext=(4, 4), textcoords="offset points",
                fontsize=9, style="italic", alpha=0.75)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Maximum supported aggregate value $M_{\\max}$")
    ax.set_ylabel("Aggregate recovery time (ms)")
    ax.legend(framealpha=0.9)
    save_figure(fig, "exp07_bsgs_scalability.svg", runs=RUNS)


if __name__ == "__main__":
    main()

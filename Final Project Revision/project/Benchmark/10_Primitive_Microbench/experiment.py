#!/usr/bin/env python3
"""
Experiment 10 — Per-Primitive Microbenchmarks
=============================================
Cost of ONE call to each cryptographic primitive, so every aggregate timing
in the paper can be checked by hand.

WHY THIS EXPERIMENT EXISTS
--------------------------
R2-C3: "My concern about implausibly fast sub-ms latencies for a Python/py_ecc
        stack was not really engaged with. ... that doesn't explain how
        ABSE.Test + Merkle verify + bitmap AND/OR over 100K-bit vectors
        finishes in well under a millisecond in pure Python. I'd like to see
        per-primitive microbenchmarks (single Test call, single pairing,
        single Merkle verify) so the totals can be checked by hand."

R1-C4: "The authors should provide raw timing data, operation counts, standard
        deviations or confidence intervals, implementation code, optimization
        details, and a precise definition of which operations are included in
        each measurement."

This is the reconciliation table. Experiments 01-07 log operation counts;
multiplying those counts by the per-primitive costs measured here must
approximate the reported totals. If it does not, the totals are wrong.
"""

import _bootstrap  # noqa: F401
import csv
import hashlib
import hmac
import os
import random

from baselines import timed, SEED
from harness import Experiment, new_figure, save_figure, CSV_DIR

RUNS = 200
WARMUP = 20
BITMAP_BITS = 100_000


def main():
    random.seed(SEED)

    exp = Experiment(10, "primitive_microbench", [
        "primitive", "backend", "detail", "calls_per_query_note",
    ])

    # ── 1. ABSE backend: which curve is actually in use? ────────────
    backend, curve = _abse_backend()
    print(f"\n  ABSE backend: {backend}  ({curve})")
    print("  NOTE: the manuscript claims py_ecc over BN128. If this line "
          "says BLS12-381, the paper's text is wrong (see SKILL.md).")

    # ── 2. Single bilinear pairing ──────────────────────────────────
    pairing = _pairing_fn()
    if pairing:
        stats, _ = timed(pairing, runs=RUNS, warmup=WARMUP)
        exp.record(stats, primitive="bilinear_pairing", backend=backend,
                   detail=curve,
                   calls_per_query_note="2 per ABSE.Test")
        _show("bilinear pairing", stats)

    # ── 3. Single ABSE.Test ─────────────────────────────────────────
    test_fn, test_detail = _abse_test_fn()
    if test_fn:
        stats, _ = timed(test_fn, runs=RUNS, warmup=WARMUP)
        exp.record(stats, primitive="abse_test", backend=backend,
                   detail=test_detail,
                   calls_per_query_note="N_u * m_c per query (exhaustive match)")
        _show("ABSE.Test", stats)

    # ── 4. Single ABSE.TokenGen ─────────────────────────────────────
    tok_fn, tok_detail = _abse_token_fn()
    if tok_fn:
        stats, _ = timed(tok_fn, runs=RUNS, warmup=WARMUP)
        exp.record(stats, primitive="abse_tokengen", backend=backend,
                   detail=tok_detail,
                   calls_per_query_note="m_c per trapdoor (Experiment 01)")
        _show("ABSE.TokenGen", stats)

    # ── 5. Single Merkle proof verification ─────────────────────────
    from merkle_tree import MerkleTree
    leaves = [os.urandom(64) for _ in range(10_000)]
    tree = MerkleTree(leaves)
    root = tree.get_root()
    idx = 4242
    proof = tree.get_proof(idx)
    stats, _ = timed(lambda: tree.verify_proof(leaves[idx], proof, root),
                     runs=RUNS, warmup=WARMUP)
    exp.record(stats, primitive="merkle_verify_single", backend="sha256",
               detail="N=10,000 leaves, single-leaf proof",
               calls_per_query_note="r per query if naive; shared in multiproof")
    _show("Merkle verify (1 leaf)", stats)

    # ── 6. SHA-256 and HMAC-SHA256, one call ────────────────────────
    blob = os.urandom(64)
    stats, _ = timed(lambda: hashlib.sha256(blob).digest(),
                     runs=RUNS, warmup=WARMUP)
    exp.record(stats, primitive="sha256", backend="hashlib",
               detail="64-byte input",
               calls_per_query_note="~r*log(N/r) in the multiproof")
    _show("SHA-256", stats)

    key = os.urandom(32)
    stats, _ = timed(lambda: hmac.new(key, blob, hashlib.sha256).digest(),
                     runs=RUNS, warmup=WARMUP)
    exp.record(stats, primitive="hmac_sha256", backend="hmac",
               detail="64-byte input",
               calls_per_query_note="1 per epoch-root signature check")
    _show("HMAC-SHA256", stats)

    # ── 7. Bitmap AND over 100k bits -- R2-C3 names this explicitly ──
    a = random.getrandbits(BITMAP_BITS)
    b = random.getrandbits(BITMAP_BITS)
    stats, _ = timed(lambda: a & b, runs=RUNS, warmup=WARMUP)
    exp.record(stats, primitive="bitmap_and_100k", backend="python int",
               detail=f"{BITMAP_BITS:,}-bit operands, word-parallel",
               calls_per_query_note="d-1 per conjunctive query")
    _show(f"bitmap AND ({BITMAP_BITS:,} bits)", stats)

    stats, _ = timed(lambda: bin(a & b).count("1"), runs=RUNS, warmup=WARMUP)
    exp.record(stats, primitive="bitmap_and_popcount_100k",
               backend="python int", detail=f"{BITMAP_BITS:,} bits + popcount",
               calls_per_query_note="1 per query to size the result set")
    _show(f"bitmap AND + popcount", stats)

    # ── 8. EC-ElGamal ops ───────────────────────────────────────────
    from ec_elgamal import generate_ec_elgamal_keypair
    pub, priv = generate_ec_elgamal_keypair(max_val=100_000)
    stats, _ = timed(lambda: pub.encrypt(42), runs=max(RUNS // 4, 20),
                     warmup=WARMUP)
    exp.record(stats, primitive="ecelgamal_encrypt", backend="NIST P-256",
               detail="lifted, single value",
               calls_per_query_note="1 per record at ingest")
    _show("EC-ElGamal encrypt", stats)

    ct_a, ct_b = pub.encrypt(11), pub.encrypt(22)
    stats, _ = timed(lambda: ct_a + ct_b, runs=RUNS, warmup=WARMUP)
    exp.record(stats, primitive="ecelgamal_add", backend="NIST P-256",
               detail="homomorphic point addition",
               calls_per_query_note="r-1 per aggregation")
    _show("EC-ElGamal add", stats)

    # ── 9. Threshold decryption, one full call ──────────────────────
    try:
        from threshold_ec_elgamal import ThresholdKeyShares, threshold_decrypt
        shares = ThresholdKeyShares(priv._x, t=3, n=5)
        auths = shares.make_authorities()
        ct = pub.encrypt(1234)
        stats, _ = timed(
            lambda: threshold_decrypt(ct, auths, [1, 2, 3], priv),
            runs=max(RUNS // 20, 20), warmup=2)
        exp.record(stats, primitive="threshold_decrypt", backend="NIST P-256",
                   detail="(t,n)=(3,5): 3 partials + 3 DLEQ + Lagrange + BSGS",
                   calls_per_query_note="2 per query (SUM, COUNT)")
        _show("threshold decrypt", stats)
    except Exception as e:
        print(f"    threshold decrypt skipped: {e}")

    exp.save()
    reconcile(exp.rows)
    plot(exp.rows)


def _show(label, s):
    print(f"    {label:<34} {s['mean_ms']:11.6f} ms  ±{s['ci95_ms']:.6f}  "
          f"(sd={s['stdev_ms']:.6f})")


def _abse_backend():
    try:
        import py_arkworks_bls12381  # noqa: F401
        return "py_arkworks_bls12381", "BLS12-381"
    except ImportError:
        return "py_ecc", "BN128"


def _pairing_fn():
    try:
        from py_arkworks_bls12381 import G1Point, G2Point, Scalar, GT
        g1 = G1Point() * Scalar(random.randint(1, 2 ** 64))
        g2 = G2Point() * Scalar(random.randint(1, 2 ** 64))
        return lambda: GT.pairing(g1, g2)
    except ImportError:
        pass
    try:
        from py_ecc import optimized_bn128 as bn128
        return lambda: bn128.pairing(bn128.G2, bn128.G1)
    except Exception:
        return None


def _abse_test_fn():
    """One ABSE.Test call -- named explicitly by R2-C3.

    Signature is abse.encrypt(tag, policy) and abse.test(token, ct); the
    policy must be one the user's attribute set satisfies, or test() returns
    False without doing the full pairing work and the timing is meaningless.
    """
    try:
        from TA import TrustedAuthority
        ta = TrustedAuthority()
        secrets = ta.key_gen(["Analyst", "Temp"])
        abse = ta.abse
        tag = "Temp|0|10"
        ct = abse.encrypt(tag, "Analyst")
        tok = abse.token_gen(secrets["SK_A"], tag)
        ok = abse.test(tok, ct)
        if not ok:
            print("    WARNING: ABSE.Test returned False -- the timing below "
                  "is a rejection path, not a successful match.")
        return (lambda: abse.test(tok, ct)), f"single Test call (match={ok})"
    except Exception as e:
        print(f"    ABSE.Test unavailable: {type(e).__name__}: {e}")
        return None, ""


def _abse_token_fn():
    try:
        from TA import TrustedAuthority
        ta = TrustedAuthority()
        secrets = ta.key_gen(["Analyst", "Temp"])
        abse, sk = ta.abse, secrets.get("SK_A")
        return (lambda: abse.token_gen(sk, "Temp|0|10")), "single TokenGen call"
    except Exception as e:
        print(f"    ABSE.TokenGen unavailable: {e}")
        return None, ""


# ══════════════════════════════════════════════════════════════════
#  R2-C3: the two standalone tables
# ══════════════════════════════════════════════════════════════════
#
# R2-C3: "I'd like to see per-primitive microbenchmarks (single Test
#         call, single pairing, single Merkle verify) so the totals can
#         be checked by hand."
#
# "Checked by hand" needs TWO tables, not one:
#
#   Table A  cost of ONE call to each primitive          -> exp10_primitive_table.csv
#   Table B  every reported total decomposed into        -> exp10_reconciliation.csv
#            (calls x unit cost), next to what was
#            actually measured, with the ratio
#
# Table B is the one that answers the objection: a reader multiplies the
# operation count by the unit cost from Table A and must land on the
# published total. Both are emitted as CSV *and* as Markdown ready to
# paste into the manuscript.
#
# Each spec row: (experiment, what is predicted, [(primitive, calls)...],
#                 source CSV for the measured value, row filter, column)
RECONCILE_SPEC = [
    ("Exp 01", "trapdoor, d=1 (m_c=4 TokenGen)",
     [("abse_tokengen", 4)],
     "exp01_trapdoor_gen.csv", {"scheme": "BVCRSA", "d": "1"}, "mean_ms"),
    ("Exp 01", "trapdoor, d=5 (m_c=20 TokenGen)",
     [("abse_tokengen", 20)],
     "exp01_trapdoor_gen.csv", {"scheme": "BVCRSA", "d": "5"}, "mean_ms"),
    ("Exp 04", "verify r=500, naive single proofs (multiproof must beat this)",
     [("merkle_verify_single", 500), ("hmac_sha256", 1)],
     "exp04_verification_overhead.csv",
     {"scheme": "BVCRSA", "returned_results": "500"}, "mean_ms"),
    ("Exp 05", "BVCRSA-Compact floor: 2 threshold decrypts",
     [("threshold_decrypt", 2)],
     "exp05_homomorphic_aggregation.csv",
     {"arm": "BVCRSA-Compact", "matched_records": "100"}, "mean_ms"),
    ("Exp 05", "Naive, r=100: one threshold decrypt per record",
     [("threshold_decrypt", 100)],
     "exp05_homomorphic_aggregation.csv",
     {"arm": "Naive", "matched_records": "100"}, "mean_ms"),
    ("Exp 06", "BVCRSA arm: 2 threshold decrypts + |S_Q|-1 EC adds (|S_Q|=1000)",
     [("threshold_decrypt", 2), ("ecelgamal_add", 999)],
     "exp06_agg_strategy.csv", {"arm": "BVCRSA", "SQ": "1000"}, "mean_ms"),
    ("Exp 06", "Conventional arm, |S_Q|=1000: one threshold decrypt per record",
     [("threshold_decrypt", 1000)],
     "exp06_agg_strategy.csv", {"arm": "Conventional", "SQ": "1000"}, "mean_ms"),
    ("Exp 02", "BVCRSA query at N=1,000: N x 0.16 pairings/doc x ABSE.Test",
     [("abse_test", 160)],
     "exp02_query_processing.csv",
     {"sweep": "vs_N", "scheme": "BVCRSA", "N": "1000"}, "mean_ms"),
]

# Operation counts measured with cProfile on the query path, N=300
# (SKILL.md §11 fairness audit, 2026-08-17). Kept here so Table B can
# state pairings-per-document beside the per-primitive cost -- that
# product is what makes a query total checkable by hand.
PER_DOC_PAIRINGS = {
    "BVCRSA": 0.16, "VC-KASE": 1.00, "ABSE-Range": 5.26,
    "Trinity": 0.0, "Latt-IBEKS": 0.0,
}


def _load_measured(fname, filt, col):
    """Pull one measured value from another experiment's CSV, if present."""
    path = os.path.join(CSV_DIR, fname)
    if not os.path.exists(path):
        return None
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if all(str(row.get(k, "")) == str(v) for k, v in filt.items()):
                    return float(row[col])
    except (OSError, ValueError, KeyError):
        return None
    return None


def reconcile(rows):
    """Emit Table A and Table B (R2-C3). Returns nothing; writes 2 CSVs."""
    cost = {r["primitive"]: r["mean_ms"] for r in rows}
    ci = {r["primitive"]: r["ci95_ms"] for r in rows}

    # ── Table A — one call to each primitive ────────────────────────
    a_path = os.path.join(CSV_DIR, "exp10_primitive_table.csv")
    with open(a_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["primitive", "backend", "detail", "mean_ms", "ci95_ms",
                    "runs", "calls_per_query_note"])
        for r in rows:
            w.writerow([r["primitive"], r.get("backend", ""),
                        r.get("detail", ""), f"{r['mean_ms']:.6f}",
                        f"{r['ci95_ms']:.6f}", r["runs"],
                        r.get("calls_per_query_note", "")])
    print(f"\n[+] Table A (per-primitive) -> {a_path}")

    print("\n" + "=" * 78)
    print("  TABLE A — cost of ONE call to each primitive (R2-C3)")
    print("=" * 78)
    print(f"| {'Primitive':<28} | {'Backend':<22} | {'Mean (ms)':>12} | {'95% CI':>10} |")
    print(f"|{'-'*30}|{'-'*24}|{'-'*14}|{'-'*12}|")
    for r in sorted(rows, key=lambda r: r["mean_ms"]):
        print(f"| {r['primitive'].replace('_',' '):<28} | "
              f"{str(r.get('backend','')):<22} | {r['mean_ms']:12.6f} | "
              f"{r['ci95_ms']:10.6f} |")

    # ── Table B — totals decomposed, predicted vs measured ──────────
    b_path = os.path.join(CSV_DIR, "exp10_reconciliation.csv")
    print("\n" + "=" * 78)
    print("  TABLE B — every total decomposed into (calls x unit cost)")
    print("=" * 78)
    print(f"| {'Exp':<7} | {'Quantity':<52} | {'Predicted':>10} | "
          f"{'Measured':>10} | {'Ratio':>7} |")
    print(f"|{'-'*9}|{'-'*54}|{'-'*12}|{'-'*12}|{'-'*9}|")

    with open(b_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["experiment", "quantity", "decomposition",
                    "predicted_ms", "measured_ms", "ratio_measured_over_predicted",
                    "verdict"])
        for label, what, terms, src, filt, col in RECONCILE_SPEC:
            if any(p not in cost for p, _ in terms):
                continue                      # primitive unavailable this run
            predicted = sum(cost[p] * n for p, n in terms)
            decomp = " + ".join(f"{n}x{p}({cost[p]:.4f}ms)" for p, n in terms)
            measured = _load_measured(src, filt, col)
            if measured is None:
                ratio, verdict, mtxt, rtxt = "", "NOT YET MEASURED", "-", "-"
            else:
                ratio = measured / predicted if predicted else 0.0
                # A total far BELOW its primitive floor means the harness is
                # not doing the work it claims -- exactly the R1-C4 / R3-14
                # failure mode that produced the old 10^6 q/s figure.
                if ratio < 0.5:
                    verdict = "BELOW FLOOR — harness suspect"
                elif ratio > 3.0:
                    verdict = "far above — unmodelled cost"
                else:
                    verdict = "consistent"
                mtxt, rtxt = f"{measured:10.4f}", f"{ratio:7.2f}"
            w.writerow([label, what, decomp, f"{predicted:.4f}",
                        "" if measured is None else f"{measured:.4f}",
                        "" if measured is None else f"{ratio:.4f}", verdict])
            print(f"| {label:<7} | {what:<52} | {predicted:10.4f} | "
                  f"{mtxt:>10} | {rtxt:>7} |")
    print(f"\n[+] Table B (reconciliation) -> {b_path}")

    # ── Query-total check: pairings/doc x unit pairing cost ─────────
    test = cost.get("abse_test")
    if test:
        print("\n  Query totals are checkable as: N x (pairings/doc) x "
              f"ABSE.Test({test:.4f} ms)")
        print(f"  {'scheme':<12} {'pairings/doc':>13} {'=> per 1,000 docs':>20}")
        for name, ppd in PER_DOC_PAIRINGS.items():
            if ppd:
                print(f"  {name:<12} {ppd:13.2f} {1000 * ppd * test:17.1f} ms")
        print("  (counts measured with cProfile at N=300 — SKILL.md §11 F1.)")
        print("  A reported query total far below its row here means the "
              "search is not doing the matching it claims (R1-C4, R3-14).")


def plot(rows):
    rows = [r for r in rows if r["mean_ms"] > 0]
    rows = sorted(rows, key=lambda r: r["mean_ms"])
    fig, ax = new_figure(figsize=(7.5, 5))
    labels = [r["primitive"].replace("_", " ") for r in rows]
    vals = [r["mean_ms"] for r in rows]
    errs = [r["ci95_ms"] for r in rows]
    ax.barh(labels, vals, xerr=errs, color="#D62728", alpha=0.85, capsize=3)
    ax.set_xscale("log")
    ax.set_xlabel("Time per single call (ms, log scale)")
    ax.grid(True, axis="x", alpha=0.3, linestyle="--")
    save_figure(fig, "exp10_primitive_microbench.svg", runs=RUNS)


if __name__ == "__main__":
    main()

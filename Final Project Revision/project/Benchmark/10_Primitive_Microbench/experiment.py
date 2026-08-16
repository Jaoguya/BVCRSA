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
import hashlib
import hmac
import os
import random

from baselines import timed, SEED
from harness import Experiment, new_figure, save_figure

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
    try:
        from TA import TrustedAuthority
        ta = TrustedAuthority()
        secrets = ta.key_gen(["Analyst", "Temp"])
        abse = ta.abse
        tag = "Temp|0|10"
        ct = abse.encrypt(tag) if hasattr(abse, "encrypt") else None
        tok = abse.token_gen(secrets.get("SK_A"), tag)
        if ct is None or not hasattr(abse, "test"):
            return None, ""
        return (lambda: abse.test(tok, ct)), "single Test call"
    except Exception as e:
        print(f"    ABSE.Test unavailable: {e}")
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


def reconcile(rows):
    """Print the hand-check table the reviewers asked for."""
    cost = {r["primitive"]: r["mean_ms"] for r in rows}
    print("\n" + "=" * 70)
    print("  RECONCILIATION — expected totals from primitive costs")
    print("=" * 70)
    test = cost.get("abse_test")
    tok = cost.get("abse_tokengen")
    if tok:
        print(f"  Exp 01 trapdoor, d=5 (m_c=20 TokenGen):"
              f" {20 * tok:10.4f} ms expected")
    if test:
        print(f"  Exp 02 query, exhaustive match N_u*m_c = 1000*4:"
              f" {4000 * test:10.4f} ms expected")
        print("     ^ if the measured query time is far below this, the "
              "harness is not doing exhaustive ABSE matching (R1-C4, R3-14)")
    mv = cost.get("merkle_verify_single")
    if mv:
        print(f"  Exp 04 verify, r=500 naive single proofs:"
              f" {500 * mv:10.4f} ms expected (multiproof should be lower)")
    td = cost.get("threshold_decrypt")
    if td:
        print(f"  Exp 05/06 BVCRSA arm, 2 threshold decrypts:"
              f" {2 * td:10.4f} ms expected floor")


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

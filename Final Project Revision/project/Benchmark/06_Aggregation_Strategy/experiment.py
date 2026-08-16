#!/usr/bin/env python3
"""
Experiment: Aggregation Strategy Comparison
=============================================
Normal (decrypt-then-aggregate) vs BVCRSA (aggregate-then-decrypt), using
REAL (t=3, n=5) threshold EC-ElGamal decryption over NIST P-256
(threshold_ec_elgamal.py): each decryption call is t Chaum-Pedersen partial
decryptions + t DLEQ verifications + Lagrange combination + BSGS recovery.

Both paths must produce the identical final numeric result -- this is the
correctness precondition that makes the cost comparison fair. On every run,
BVCRSA's threshold-decrypted homomorphic Sum/Count are asserted equal to
the raw plaintext sum/|SQ| (i.e., to what the Normal path's decryptions --
which are the *same* decrypt() function -- would themselves sum to).

Independent variable: |SQ|, the number of matched records.
Fixed parameters: N = 10,000 total records (context only -- both paths'
costs depend only on |SQ|, not on N), t = 3, n = 5 threshold authorities.

For |SQ| > SAMPLE_CAP, the Normal path's per-record decrypt cost is
measured on a representative sample of SAMPLE_CAP *real* threshold
decryptions per run (each decrypt() call has ~constant cost -- it is
dominated by the fixed-length secret share x_l, not by which record is
being decrypted) and linearly extrapolated to the full |SQ|; this keeps a
full sweep x 20-run average tractable. Every |SQ| <= SAMPLE_CAP -- which
covers the entire Metric-3 crossover region -- is decrypted in full, with
no extrapolation.
"""

import sys, os, csv, time, random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.join(os.path.dirname(BASE_DIR), "_shared")
_CSVDIR = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "CSV")
sys.path.insert(0, _SHARED)

from ec_elgamal import generate_ec_elgamal_keypair
from threshold_ec_elgamal import ThresholdKeyShares, threshold_decrypt

N_TOTAL = 10_000
T, N_AUTH = 3, 5
CHOSEN_AUTHORITIES = [1, 2, 3]
SQ_VALUES = [10, 50, 100, 500, 1000, 5000, 10000]
RUNS = 20
SAMPLE_CAP = 150
VALUE_RANGE = (1, 100)
MAX_VAL = 10_000 * 100  # covers CTsum for the largest |SQ| (10000 * max value 100)

CSV_FILE = os.path.join(_CSVDIR, "exp06_agg_strategy.csv")


def main():
    random.seed(42)

    print("=" * 64)
    print("  Aggregation Strategy Comparison: Normal vs BVCRSA")
    print(f"  N={N_TOTAL}  threshold=({T},{N_AUTH})  RUNS={RUNS}")
    print("=" * 64)

    print("\n[+] Generating EC-ElGamal keypair (NIST P-256) + BSGS table...")
    pub, priv = generate_ec_elgamal_keypair(max_val=MAX_VAL)

    print(f"[+] Shamir-splitting the private key into {N_AUTH} shares (t={T})...")
    shares = ThresholdKeyShares(priv._x, t=T, n=N_AUTH)
    authorities = shares.make_authorities()

    print("[+] Correctness precondition check (|SQ|=200, full decryption)...")
    check_vals = [random.randint(*VALUE_RANGE) for _ in range(200)]
    check_ct = [pub.encrypt(v) for v in check_vals]
    decrypted = [threshold_decrypt(c, authorities, CHOSEN_AUTHORITIES, priv)[0] for c in check_ct]
    assert decrypted == check_vals, "threshold decrypt does not recover exact plaintexts"
    agg = check_ct[0]
    for c in check_ct[1:]:
        agg = agg + c
    agg_sum, _ = threshold_decrypt(agg, authorities, CHOSEN_AUTHORITIES, priv)
    assert agg_sum == sum(check_vals), "aggregate-then-decrypt != decrypt-then-aggregate"
    print("    OK: decrypt-then-aggregate == aggregate-then-decrypt\n")

    rows = []
    for SQ in SQ_VALUES:
        print(f"[+] |SQ|={SQ}")
        plaintexts = [random.randint(*VALUE_RANGE) for _ in range(SQ)]
        CT_v = [pub.encrypt(v) for v in plaintexts]
        CT_1 = [pub.encrypt(1) for _ in range(SQ)]

        sample_n = min(SQ, SAMPLE_CAP)
        exact = sample_n == SQ

        normal_totals = []
        bvcrsa_totals = []

        for _run in range(RUNS):
            # ---------------- Normal: decrypt-then-aggregate ----------------
            sample_idx = list(range(SQ)) if exact else random.sample(range(SQ), sample_n)

            t0 = time.perf_counter()
            decrypted_sample = []
            for i in sample_idx:
                pt, _ = threshold_decrypt(CT_v[i], authorities, CHOSEN_AUTHORITIES, priv)
                decrypted_sample.append(pt)
            sample_elapsed = time.perf_counter() - t0
            per_record = sample_elapsed / sample_n
            t_normal_decrypt = per_record * SQ  # extrapolated to the full |SQ|

            t0 = time.perf_counter()
            manual_sum = sum(plaintexts)
            t_normal_sum = time.perf_counter() - t0

            normal_totals.append((t_normal_decrypt + t_normal_sum) * 1000)

            if exact:
                assert sum(decrypted_sample) == manual_sum

            # ---------------- BVCRSA: aggregate-then-decrypt ----------------
            t0 = time.perf_counter()
            CTsum = CT_v[0]
            for c in CT_v[1:]:
                CTsum = CTsum + c
            CTcount = CT_1[0]
            for c in CT_1[1:]:
                CTcount = CTcount + c
            t_bvcrsa_add = time.perf_counter() - t0

            t0 = time.perf_counter()
            Sum, _ = threshold_decrypt(CTsum, authorities, CHOSEN_AUTHORITIES, priv)
            Count, _ = threshold_decrypt(CTcount, authorities, CHOSEN_AUTHORITIES, priv)
            t_bvcrsa_decrypt = time.perf_counter() - t0

            bvcrsa_totals.append((t_bvcrsa_add + t_bvcrsa_decrypt) * 1000)

            assert Sum == manual_sum
            assert Count == SQ

        normal_avg = sum(normal_totals) / RUNS
        bvcrsa_avg = sum(bvcrsa_totals) / RUNS
        speedup = normal_avg / bvcrsa_avg if bvcrsa_avg > 0 else float("inf")

        rows.append({
            "SQ": SQ,
            "normal_calls": SQ,
            "bvcrsa_calls": 2,
            "normal_latency_ms": round(normal_avg, 4),
            "bvcrsa_latency_ms": round(bvcrsa_avg, 4),
            "speedup": round(speedup, 2),
        })
        print(f"    normal={normal_avg:>10.3f} ms   bvcrsa={bvcrsa_avg:>8.3f} ms   "
              f"speedup={speedup:>7.1f}x   ({'exact' if exact else f'sampled n={sample_n}'})")

    fields = ["SQ", "normal_calls", "bvcrsa_calls", "normal_latency_ms", "bvcrsa_latency_ms", "speedup"]
    with open(CSV_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\n[+] Results saved to {CSV_FILE}")

    print("\n" + "=" * 96)
    print(f"  {'|SQ|':>8} {'Normal calls':>14} {'BVCRSA calls':>14} "
          f"{'Normal (ms)':>14} {'BVCRSA (ms)':>14} {'Speedup':>10}")
    print("  " + "-" * 92)
    for r in rows:
        print(f"  {r['SQ']:>8} {r['normal_calls']:>14} {r['bvcrsa_calls']:>14} "
              f"{r['normal_latency_ms']:>14.2f} {r['bvcrsa_latency_ms']:>14.3f} {r['speedup']:>9.1f}x")
    print("=" * 96)


if __name__ == "__main__":
    main()

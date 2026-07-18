#!/usr/bin/env python3
"""
Companion to agg_strategy_benchmark.py: a finer-grained |SQ| = 1..50 sweep
so Metric 3 (the crossover plot) has enough resolution to show exactly
where BVCRSA overtakes Normal aggregation. Same real (t=3, n=5) threshold
EC-ElGamal setup; every point here is decrypted in full (no sampling --
all |SQ| values are tiny).
"""

import sys, os, csv, time, random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from ec_elgamal import generate_ec_elgamal_keypair
from threshold_ec_elgamal import ThresholdKeyShares, threshold_decrypt

T, N_AUTH = 3, 5
CHOSEN_AUTHORITIES = [1, 2, 3]
SQ_VALUES = [1, 2, 3, 5, 8, 10, 15, 20, 30, 40, 50]
RUNS = 20
VALUE_RANGE = (1, 100)
MAX_VAL = 50 * 100

CSV_FILE = os.path.join(BASE_DIR, "agg_strategy_zoom_results.csv")


def main():
    random.seed(42)

    print("=" * 64)
    print("  Aggregation Strategy Comparison: Crossover Zoom (|SQ| 1-50)")
    print(f"  threshold=({T},{N_AUTH})  RUNS={RUNS}")
    print("=" * 64)

    pub, priv = generate_ec_elgamal_keypair(max_val=MAX_VAL)
    shares = ThresholdKeyShares(priv._x, t=T, n=N_AUTH)
    authorities = shares.make_authorities()

    rows = []
    for SQ in SQ_VALUES:
        plaintexts = [random.randint(*VALUE_RANGE) for _ in range(SQ)]
        CT_v = [pub.encrypt(v) for v in plaintexts]
        CT_1 = [pub.encrypt(1) for _ in range(SQ)]

        normal_totals, bvcrsa_totals = [], []

        for _run in range(RUNS):
            t0 = time.perf_counter()
            decrypted = []
            for c in CT_v:
                pt, _ = threshold_decrypt(c, authorities, CHOSEN_AUTHORITIES, priv)
                decrypted.append(pt)
            t_normal_decrypt = time.perf_counter() - t0

            t0 = time.perf_counter()
            manual_sum = sum(plaintexts)
            t_normal_sum = time.perf_counter() - t0
            normal_totals.append((t_normal_decrypt + t_normal_sum) * 1000)
            assert decrypted == plaintexts

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
            "SQ": SQ, "normal_calls": SQ, "bvcrsa_calls": 2,
            "normal_latency_ms": round(normal_avg, 4),
            "bvcrsa_latency_ms": round(bvcrsa_avg, 4),
            "speedup": round(speedup, 3),
        })
        print(f"  |SQ|={SQ:>3}  normal={normal_avg:>9.3f} ms  bvcrsa={bvcrsa_avg:>8.3f} ms  speedup={speedup:>6.2f}x")

    fields = ["SQ", "normal_calls", "bvcrsa_calls", "normal_latency_ms", "bvcrsa_latency_ms", "speedup"]
    with open(CSV_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\n[+] Results saved to {CSV_FILE}")


if __name__ == "__main__":
    main()

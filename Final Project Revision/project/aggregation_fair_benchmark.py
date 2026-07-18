#!/usr/bin/env python3
"""
Fair Aggregation Speed Benchmark
Compares Homomorphic Addition performance:
- BVCRSA (Ours): EC-ElGamal
- Conventional AHE: Paillier
"""

import sys, os, time, random
import pandas as pd

try:
    from phe import generate_paillier_keypair
except ImportError:
    print("Please install phe: pip install phe")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from ec_elgamal import generate_ec_elgamal_keypair, ECEncryptedNumber

M_VALUES = [100, 200, 500, 800, 1000]
RUNS = 10
CSV_FILE = os.path.join(BASE_DIR, "aggregation_fair_benchmark_results.csv")

def main():
    print("="*60)
    print("  Fair Aggregation Benchmark (Homomorphic Addition)")
    print("="*60)

    # 1. Setup Keys
    print("\n[+] Generating EC-ElGamal Keypair (secp256k1)...")
    ec_pub, ec_priv = generate_ec_elgamal_keypair()
    
    print("[+] Generating Paillier Keypair (2048-bit for 112-bit security)...")
    p_pub, p_priv = generate_paillier_keypair(n_length=2048)

    results = []

    for M in M_VALUES:
        print(f"\n[+] Testing aggregation of {M} records...")
        
        # Pre-generate plaintexts
        plaintexts = [random.randint(1, 100) for _ in range(M)]

        # Pre-encrypt ciphertexts
        print("    Encrypting data...", end="", flush=True)
        t0 = time.perf_counter()
        ec_ciphertexts = [ec_pub.encrypt(v) for v in plaintexts]
        ec_enc_time = (time.perf_counter() - t0)*1000

        t0 = time.perf_counter()
        p_ciphertexts = [p_pub.encrypt(v) for v in plaintexts]
        p_enc_time = (time.perf_counter() - t0)*1000
        print(f" Done. (EC: {ec_enc_time:.1f}ms, Paillier: {p_enc_time:.1f}ms)")

        # --- Benchmark BVCRSA (EC-ElGamal) ---
        ec_times = []
        for _ in range(RUNS):
            t0 = time.perf_counter()
            agg = ec_ciphertexts[0]
            for c in ec_ciphertexts[1:]:
                agg = agg + c
            ec_times.append((time.perf_counter() - t0) * 1000)
        ec_agg_ms = sum(ec_times) / RUNS
        print(f"    BVCRSA (EC-ElGamal): {ec_agg_ms:>8.2f} ms")
        
        results.append({
            "M": M,
            "algorithm": "BVCRSA (Ours)",
            "agg_ms": round(ec_agg_ms, 3)
        })

        # --- Benchmark Conventional AHE (Paillier) ---
        p_times = []
        for _ in range(RUNS):
            t0 = time.perf_counter()
            agg = p_ciphertexts[0]
            for c in p_ciphertexts[1:]:
                agg = agg + c
            p_times.append((time.perf_counter() - t0) * 1000)
        p_agg_ms = sum(p_times) / RUNS
        print(f"    Conventional AHE :   {p_agg_ms:>8.2f} ms")

        results.append({
            "M": M,
            "algorithm": "Conventional AHE",
            "agg_ms": round(p_agg_ms, 3)
        })

    # Save results
    df = pd.DataFrame(results)
    df.to_csv(CSV_FILE, index=False)
    print(f"\n[+] Results saved to {CSV_FILE}")

if __name__ == "__main__":
    main()

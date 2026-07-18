#!/usr/bin/env python3
"""
Experiment A: Per-Operation Cost Breakdown (Sum vs. Count vs. Average)
Validates that Average (Sum + Count) has no hidden overhead.
"""

import sys, os, time, random
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from ec_elgamal import generate_ec_elgamal_keypair

RUNS = 20
SQ_SIZE = 500
CSV_FILE = os.path.join(BASE_DIR, "exp_a_results.csv")

def main():
    print("="*60)
    print(f" Experiment A: Cost Breakdown (|SQ|={SQ_SIZE})")
    print("="*60)

    print("[+] Generating EC-ElGamal Keypair with BSGS table...")
    # Increase max_val slightly to ensure 500*100 (50,000) is well within range
    pub_key, priv_key = generate_ec_elgamal_keypair(max_val=100000)

    # Pre-generate 500 plaintexts
    plaintexts = [random.randint(10, 100) for _ in range(SQ_SIZE)]

    print("[+] Encrypting CT_v (values) and CT_1 (ones) for all matched records...")
    CT_v = [pub_key.encrypt(v) for v in plaintexts]
    CT_1 = [pub_key.encrypt(1) for _ in range(SQ_SIZE)]
    print("    Done.")

    results = []

    # 1. SUM ONLY
    print("\n[+] Testing SUM Only...")
    cloud_sum_times = []
    user_sum_times = []
    
    for _ in range(RUNS):
        # Cloud Side
        t0 = time.perf_counter()
        agg_sum = CT_v[0]
        for c in CT_v[1:]:
            agg_sum = agg_sum + c
        cloud_sum_times.append((time.perf_counter() - t0) * 1000)
        
        # User Side
        t0 = time.perf_counter()
        dec_sum = priv_key.decrypt(agg_sum)
        user_sum_times.append((time.perf_counter() - t0) * 1000)

    avg_cloud_sum = sum(cloud_sum_times) / RUNS
    avg_user_sum = sum(user_sum_times) / RUNS
    print(f"    Cloud Time: {avg_cloud_sum:.2f} ms")
    print(f"    User Time:  {avg_user_sum:.2f} ms")

    results.append({
        "Operation": "Sum",
        "Cloud_Time_ms": avg_cloud_sum,
        "User_Time_ms": avg_user_sum
    })

    # 2. COUNT ONLY
    print("\n[+] Testing COUNT Only...")
    cloud_count_times = []
    user_count_times = []
    
    for _ in range(RUNS):
        # Cloud Side
        t0 = time.perf_counter()
        agg_count = CT_1[0]
        for c in CT_1[1:]:
            agg_count = agg_count + c
        cloud_count_times.append((time.perf_counter() - t0) * 1000)
        
        # User Side
        t0 = time.perf_counter()
        dec_count = priv_key.decrypt(agg_count)
        user_count_times.append((time.perf_counter() - t0) * 1000)

    avg_cloud_count = sum(cloud_count_times) / RUNS
    avg_user_count = sum(user_count_times) / RUNS
    print(f"    Cloud Time: {avg_cloud_count:.2f} ms")
    print(f"    User Time:  {avg_user_count:.2f} ms")

    results.append({
        "Operation": "Count",
        "Cloud_Time_ms": avg_cloud_count,
        "User_Time_ms": avg_user_count
    })

    # 3. AVERAGE (SUM + COUNT)
    print("\n[+] Testing AVERAGE (Sum + Count)...")
    cloud_avg_times = []
    user_avg_times = []
    
    for _ in range(RUNS):
        # Cloud Side: Add both CT_v and CT_1 independently (simulating parallel)
        t0 = time.perf_counter()
        agg_sum = CT_v[0]
        for c in CT_v[1:]:
            agg_sum = agg_sum + c
            
        agg_count = CT_1[0]
        for c in CT_1[1:]:
            agg_count = agg_count + c
        cloud_avg_times.append((time.perf_counter() - t0) * 1000)
        
        # User Side: Decrypt both and divide
        t0 = time.perf_counter()
        dec_sum = priv_key.decrypt(agg_sum)
        dec_count = priv_key.decrypt(agg_count)
        if dec_count > 0:
            final_avg = dec_sum / dec_count
        user_avg_times.append((time.perf_counter() - t0) * 1000)

    avg_cloud_avg = sum(cloud_avg_times) / RUNS
    avg_user_avg = sum(user_avg_times) / RUNS
    print(f"    Cloud Time: {avg_cloud_avg:.2f} ms")
    print(f"    User Time:  {avg_user_avg:.2f} ms")

    results.append({
        "Operation": "Average",
        "Cloud_Time_ms": avg_cloud_avg,
        "User_Time_ms": avg_user_avg
    })

    # Save results
    df = pd.DataFrame(results)
    df.to_csv(CSV_FILE, index=False)
    print(f"\n[+] Results saved to {CSV_FILE}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Experiment 4: Verification Overhead — BVCRSA vs Trinity vs VC-KASE
===================================================================
Task 6B-compliant benchmark measuring VERIFICATION COST ONLY,
strictly independent of search, trapdoor generation, and aggregation.

┌─────────────────────────────────────────────────────────────────┐
│  Experimental Conditions                                        │
│  ───────────────────────────────────────────────────────────────│
│  Variable:       |R_Q| (number of returned results)             │
│  Sweep:          [50, 100, 150, 200, 250, 300, 350, 400, 450,  │
│                   500]                                          │
│  Fixed:          N = 10,000 records                             │
│                  Range = [0, 100] (full domain)                 │
│                  Keywords = 1 ("Temp"), d = 1                   │
│                  Query type = conjunctive range (single-dim)    │
│  Schemes:        BVCRSA, Trinity, VC-KASE                      │
│  Repetitions:    300 (median reported), 10 warmup               │
│  Sampling:       Interleaved (A→B→C per round, not back-to-    │
│                  back blocks)                                   │
│  Phase measured: VERIFICATION ONLY                              │
│                  (all setup/search/proof-generation is untimed) │
└─────────────────────────────────────────────────────────────────┘

Verification algorithms (each matching their published design):

  BVCRSA   — Real MerkleTree.verify_multi_proof() over committed
             SCRAT nodes built by the production pipeline
             (TA → sensor_encrypt → blockchain_edge → merkle_tree),
             plus a constant-cost HMAC-SHA256 blockchain-root
             signature check.  Complexity: O(r·log(N/r)).

  Trinity  — Per-result AES-GCM decrypt-and-content-check,
             matching the published Trinity-II algorithm
             (paper Section V-B2 "Verification"): the cloud
             sends an encrypted per-result verify array; the
             client decrypts and checks it against the query
             predicate.  Complexity: O(r).

  VC-KASE  — Fixed number of REAL BLS12-381 bilinear pairings
             (result-count independent), matching its O(T_pair)
             verification complexity.

Result-set sizes |R_Q| are controlled via deterministic evenly-
spaced index selection over the committed leaf set.  This removes
the confounding effect of search selectivity and isolates pure
verification cost.

All results are the median of 300 independent runs, with the
garbage collector disabled during timing.  Runs are INTERLEAVED
across schemes so all three are sampled under the same transient
system conditions at every point in the sweep.
"""

import os
import sys
import csv
import gc
import hmac
import hashlib
import random
import statistics
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_SHARED = os.path.join(os.path.dirname(BASE_DIR), "_shared")
_CSVDIR = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "CSV")
_FIGDIR = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "Figures")
sys.path.insert(0, _SHARED)

# ── Experimental Parameters ──
N_TOTAL = 10_000
RESULT_COUNTS = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]
RUNS = 300
WARMUP_RUNS = 10
CSV_FILE = os.path.join(_CSVDIR, "exp04_verification_overhead.csv")

random.seed(42)


# ══════════════════════════════════════════════════════════════════
#  Utility Functions
# ══════════════════════════════════════════════════════════════════

def evenly_spaced_indices(r, n):
    """Deterministic, evenly-spaced subset of size r out of range(n)."""
    return [int(i * n / r) for i in range(r)]


def timed_interleaved_ms(fns, runs=RUNS, warmup=WARMUP_RUNS):
    """Time several zero-arg callables under IDENTICAL run conditions.

    Rather than completing all repetitions of fn A before starting
    fn B, a single round runs A→B→C→loop, so every scheme is sampled
    in close succession under the same transient system state.

    Returns dict of {name: median_ms}.
    """
    names = list(fns.keys())
    for name in names:
        for _ in range(warmup):
            fns[name]()

    samples = {name: [] for name in names}
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(runs):
            for name in names:
                t0 = time.perf_counter()
                fns[name]()
                samples[name].append((time.perf_counter() - t0) * 1000)
    finally:
        if gc_was_enabled:
            gc.enable()
    return {name: statistics.median(vals) for name, vals in samples.items()}


# ══════════════════════════════════════════════════════════════════
#  BVCRSA: Real Production Pipeline → Merkle Multi-Proof Verify
# ══════════════════════════════════════════════════════════════════
print("=" * 66)
print("  Experiment 4: Verification Overhead")
print("  Building BVCRSA index via real pipeline (N=%d)..." % N_TOTAL)
print("=" * 66)

from TA import TrustedAuthority
from blockchain_edge import BlockchainEdgeManager
from sensor import sensor_encrypt
from merkle_tree import MerkleTree

# Phase 1: Setup (TA key generation)
_ta = TrustedAuthority()
_secrets = _ta.key_gen(["Analyst", "Temp"])
_edge = BlockchainEdgeManager(_secrets, _secrets["abse"])
_aes_key = _ta.get_sensor_key("S1")
_hmac_key = _ta.get_sensor_hmac_key("S1")

# Phase 2: Index Construction (Edge builds SCRAT nodes)
print("[setup] Ingesting %d sensor records through real pipeline..." % N_TOTAL)
_all_nodes = []
for i in range(N_TOTAL):
    payload = sensor_encrypt(
        "S1", "M1", "Temp", "2026-05-20 15:00:00",
        random.randint(0, 100), _aes_key, _hmac_key,
        _ta.ec_pubkey, seq_counter=i + 1,
    )
    _edge.verify_sensor_payload(payload, _hmac_key)
    _all_nodes.extend(_edge.build_scrat_from_payload(payload))

print(f"[setup] Built {len(_all_nodes)} SCRAT nodes.")

# Build Merkle tree over the real committed leaves
# Leaf format matches blockchain_edge.py line 282:
#   f"{tag}|{sigma}|{CT_v}|{Cnt_u}"
_leaf_strs = [
    f"{n['search_tag']}|{n['sigma']}|{n['CT_v']}|{n['Cnt_u']}"
    for n in _all_nodes
]
_verify_tree = MerkleTree(_leaf_strs)
_verify_root = _verify_tree.get_root()
_n_leaves = len(_leaf_strs)

# Blockchain-root signing key (Edge Gateway signs epoch root)
_gw_signing_key = os.urandom(32)

# Pre-compute multi-proofs for each |R_Q| (untimed setup)
print("[setup] Pre-computing Merkle multi-proofs for each |R_Q|...")
_bvcrsa_precomputed = {}
for r in RESULT_COUNTS:
    idxs = evenly_spaced_indices(r, _n_leaves)
    leaves = {i: _leaf_strs[i] for i in idxs}
    mp = _verify_tree.get_multi_proof(idxs)
    _bvcrsa_precomputed[r] = {"leaves": leaves, "multi_proof": mp}
print("[setup] BVCRSA setup complete.")


def bvcrsa_verify(r):
    """TIMED: Verify r selected leaves against the Merkle root using
    the production MerkleTree.verify_multi_proof(), then verify the
    blockchain-anchored root signature (constant-cost HMAC-SHA256).
    """
    pre = _bvcrsa_precomputed[r]
    # Step 1: Merkle multi-proof verification — O(r·log(N/r))
    assert MerkleTree.verify_multi_proof(
        pre["leaves"], pre["multi_proof"], _verify_root
    )
    # Step 2: Blockchain-root epoch-commitment signature check — O(1)
    hmac.new(
        _gw_signing_key, _verify_root.encode(), hashlib.sha256
    ).digest()


# ══════════════════════════════════════════════════════════════════
#  Trinity: Per-Result AES-GCM Decrypt-and-Check (Paper Sec V-B2)
# ══════════════════════════════════════════════════════════════════
print("[setup] Building Trinity-II verification data (N=%d)..." % N_TOTAL)
from Crypto.Cipher import AES

# Trinity verify key and query predicate (paper: "extra secret key sk")
_trinity_verify_key = os.urandom(32)
_trinity_query_predicate = os.urandom(16)

# Pre-build encrypted verify arrays for N entries
_trinity_verify_entries = []
for i in range(N_TOTAL):
    # ~1/3 true positives (matching the query predicate)
    verify_array = _trinity_query_predicate if i % 3 == 0 else os.urandom(16)
    nonce = os.urandom(12)
    cipher = AES.new(_trinity_verify_key, AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(verify_array)
    _trinity_verify_entries.append({"nonce": nonce, "ct": ct, "tag": tag})

print("[setup] Trinity setup complete.")


def trinity_verify(r):
    """TIMED: Per-result AES-GCM decrypt + content-check.
    Published Trinity-II (Sec V-B2): CS sends encrypted verify array
    vt_i; DU decrypts and checks against the query predicate.
    """
    idxs = evenly_spaced_indices(r, N_TOTAL)
    for i in idxs:
        entry = _trinity_verify_entries[i]
        cipher = AES.new(
            _trinity_verify_key, AES.MODE_GCM, nonce=entry["nonce"]
        )
        decrypted = cipher.decrypt_and_verify(entry["ct"], entry["tag"])
        _ = decrypted == _trinity_query_predicate  # DU's content check


# ══════════════════════════════════════════════════════════════════
#  VC-KASE: Fixed BLS12-381 Bilinear Pairings
# ══════════════════════════════════════════════════════════════════
print("[setup] Initializing VC-KASE BLS12-381 pairing elements...")
from py_arkworks_bls12381 import G1Point, G2Point, Scalar, GT

_vckase_g1 = G1Point() * Scalar(random.randint(1, 2**64))
_vckase_g2 = G2Point() * Scalar(random.randint(1, 2**64))
VCKASE_PAIRINGS_PER_QUERY = 2  # Fixed, result-count-independent

print("[setup] VC-KASE setup complete.")


def vckase_verify(r):
    """TIMED: Fixed number of bilinear-pairing tests regardless of
    how many results matched.  Result-count-independent O(T_pair).
    """
    for _ in range(VCKASE_PAIRINGS_PER_QUERY):
        GT.pairing(_vckase_g1, _vckase_g2)


# ══════════════════════════════════════════════════════════════════
#  Main Benchmark Loop
# ══════════════════════════════════════════════════════════════════

def main():
    print("\n" + "=" * 66)
    print("  Experiment 4: Verification Overhead")
    print(f"  N={N_TOTAL}  RUNS={RUNS}  WARMUP={WARMUP_RUNS}")
    print("-" * 66)
    print("  Variable:       |R_Q| (number of returned results)")
    print(f"  Sweep:          {RESULT_COUNTS}")
    print(f"  Fixed:          N={N_TOTAL}, range=[0,100], d=1, kw=Temp")
    print("  Query type:     Conjunctive range search (single-dim)")
    print("  Phase measured: VERIFICATION ONLY")
    print("  Sampling:       Interleaved (BVCRSA→Trinity→VC-KASE per round)")
    print("=" * 66)

    rows = []
    for r in RESULT_COUNTS:
        results = timed_interleaved_ms({
            "bvcrsa": lambda r=r: bvcrsa_verify(r),
            "trinity": lambda r=r: trinity_verify(r),
            "vckase": lambda r=r: vckase_verify(r),
        })
        bvcrsa_ms = results["bvcrsa"]
        trinity_ms = results["trinity"]
        vckase_ms = results["vckase"]
        rows.append({
            "returned_results": r,
            "bvcrsa_verify_ms": round(bvcrsa_ms, 4),
            "trinity_verify_ms": round(trinity_ms, 4),
            "vckase_verify_ms": round(vckase_ms, 4),
        })
        print(
            f"  |R_Q|={r:>4d}  "
            f"BVCRSA={bvcrsa_ms:>8.3f}ms  "
            f"Trinity={trinity_ms:>9.3f}ms  "
            f"VC-KASE={vckase_ms:>7.3f}ms"
        )

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[+] Results saved to {CSV_FILE}")
    print("\n[Experimental Conditions Summary]")
    print(f"    Database size:       N = {N_TOTAL}")
    print(f"    SCRAT nodes built:   {_n_leaves}")
    print(f"    Merkle tree root:    {_verify_root[:32]}...")
    print(f"    Result-set sizes:    {RESULT_COUNTS}")
    print(f"    Runs per point:      {RUNS} (median)")
    print(f"    Index selection:     Deterministic evenly-spaced")
    print(f"    BVCRSA verification: MerkleTree.verify_multi_proof()")
    print(f"    Trinity verification: AES-GCM decrypt + content-check")
    print(f"    VC-KASE verification: {VCKASE_PAIRINGS_PER_QUERY} BLS12-381 pairings (fixed)")


if __name__ == "__main__":
    main()

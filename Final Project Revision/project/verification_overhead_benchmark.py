#!/usr/bin/env python3
"""
Verification Overhead: BVCRSA vs Trinity vs VC-KASE
=====================================================
Measures the real cost of verifying a set of returned search-query
results as the result-set size grows from 50 to 500 (fixed database
size N=10,000). Backs the paper's "Verification Overhead" figure
(fig_verification_overhead.png), which was previously missing from
the repo.

Each scheme's verification step follows its own real algorithmic
design rather than an arbitrary cost model:

  BVCRSA    -- a real Merkle MULTI-proof over the r selected
               aggregation entries (Eq. eq:p4-aggregation-proof,
               pi_Q^agg = MerkleMultiProof(...)), i.e. O(r log(N/r))
               hash operations: internal nodes shared by multiple
               selected leaves are hashed once and reused, not
               recomputed once per leaf. This is what the paper's own
               computation-cost table claims for BVCRSA verification
               (Table tab:complexity_comparison:
               O(|U_Q| n_b log n_b + r log(N/r))); a naive
               "r independent single-leaf proofs" implementation
               (O(r log N)) -- our first attempt -- does NOT match
               that design and is strictly slower.
  Trinity   -- real per-result validation of "authentication
               information", exactly as trinity.py's TrinityII.query()
               performs it per candidate: a real SHVE.Match predicate
               re-check (shve.py, vector_length=3 as in trinity.py)
               plus the HMAC-SHA256 verify_tag check. Trinity has no
               batched/multi-proof verification in its design,
               matching its own O(|R_Q|) verification complexity in
               Table tab:complexity_comparison.
  VC-KASE   -- a fixed, result-count-independent number of REAL
               BLS12-381 bilinear pairings (py_arkworks_bls12381,
               the same library abse_fast.py uses), matching its
               O(T_pair) verification complexity.

All results are the median of 300 independent runs, with the garbage
collector disabled during timing. Runs are INTERLEAVED across schemes
(one BVCRSA rep, one Trinity rep, one VC-KASE rep, repeat) rather than
run as three back-to-back blocks, so all three schemes are sampled
under the same transient system conditions at every point in the
sweep instead of each scheme's block being exposed to however the
system happened to be loaded during the minutes it ran in isolation.

Methodology note: which specific subset of |R_Q| positions is
verified is picked DETERMINISTICALLY (evenly spaced across the
N-record space), not via a fresh random.sample() per call. A random
subset changes the Merkle multi-proof's sibling-sharing pattern from
draw to draw -- variance in WHICH indices got picked, unrelated to
the variable actually being studied (|R_Q|) -- which was adding noise
on top of genuine timing jitter. Evenly-spaced indices remove that
confound while remaining a fair, non-adversarial access pattern; the
underlying crypto operations performed per result are unchanged.
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
import math

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

N_TOTAL = 10_000
RESULT_COUNTS = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]
RUNS = 300
WARMUP_RUNS = 10
CSV_FILE = os.path.join(BASE_DIR, "verification_overhead_results.csv")

random.seed(42)


def evenly_spaced_indices(r, n=N_TOTAL):
    """Deterministic, evenly-spaced subset of size r out of range(n)."""
    return [int(i * n / r) for i in range(r)]


def timed_interleaved_ms(fns, runs=RUNS, warmup=WARMUP_RUNS):
    """Time several zero-arg callables under IDENTICAL run conditions:
    rather than completing all `runs` repetitions of fn A before
    starting fn B (which lets system load drift over the minutes a
    full sweep takes bias one scheme's block relative to another's),
    a single round runs A, then B, then C, then loops back to A --
    so every scheme is sampled in close succession, under essentially
    the same transient system state, at every point in the sweep.

    Args:
        fns: dict of {name: zero-arg callable}.
    Returns:
        dict of {name: median_ms}.
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


def _hash(data):
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


# ── BVCRSA: real Merkle tree + Merkle MULTI-proof verification ──
_bvcrsa_leaves_raw = [os.urandom(64) for _ in range(N_TOTAL)]
_num_levels = math.ceil(math.log2(N_TOTAL))
_tree_size = 1 << _num_levels  # padded to a power of two

_levels = [[_hash(_bvcrsa_leaves_raw[i]) if i < N_TOTAL else _hash(b"\x00")
            for i in range(_tree_size)]]
while len(_levels[-1]) > 1:
    prev = _levels[-1]
    nxt = [_hash(prev[i] + prev[i + 1]) for i in range(0, len(prev), 2)]
    _levels.append(nxt)
_bvcrsa_root = _levels[-1][0]
_bvcrsa_gw_signing_key = os.urandom(32)


def bvcrsa_verify_multiproof(r):
    """Verify r selected leaves against the root using ONE shared
    multi-proof: internal nodes on the shared path of >=2 selected
    leaves are combined once and reused, rather than rehashed per leaf.
    """
    idxs = evenly_spaced_indices(r)
    # known[level] = {index: hash}; recompute leaf hashes from raw data
    # (the real per-leaf hashing work every verifier must do).
    known = {0: {i: _hash(_bvcrsa_leaves_raw[i]) for i in idxs}}
    for level in range(_num_levels):
        cur = known[level]
        nxt = {}
        seen_parents = set()
        for idx in cur:
            parent = idx // 2
            if parent in seen_parents:
                continue
            seen_parents.add(parent)
            left_idx, right_idx = 2 * parent, 2 * parent + 1
            left = cur.get(left_idx, _levels[level][left_idx])
            right = cur.get(right_idx, _levels[level][right_idx])
            nxt[parent] = _hash(left + right)
        known[level + 1] = nxt
    computed_root = known[_num_levels][0]
    assert computed_root == _bvcrsa_root
    # constant-cost blockchain-root (epoch commitment) signature check
    hmac.new(_bvcrsa_gw_signing_key, _bvcrsa_root.encode(), hashlib.sha256).digest()


# ── Trinity: real per-result SHVE.Match + HMAC verify_tag check
#    (trinity.py TrinityII.query(): "validate authentication
#    information associated with each returned result") ──
from shve import SHVE

_trinity_shve = SHVE(vector_length=3)  # lat, lon, time -- as in trinity.py
_trinity_shve_key = _trinity_shve.keygen()
_trinity_tag_key = os.urandom(32)

_trinity_query_vector = (13, 100, 1700000000)  # fixed predicate under test
_trinity_token = _trinity_shve.token_gen(_trinity_shve_key, _trinity_query_vector)

_trinity_entries = []
for i in range(N_TOTAL):
    ct = _trinity_shve.encrypt(_trinity_shve_key, _trinity_query_vector)  # matches
    tag = hmac.new(_trinity_tag_key, f"{i}".encode(), hashlib.sha256).digest()
    _trinity_entries.append({"shve_ct": ct, "entry_id": i, "verify_tag": tag})


def trinity_verify(r):
    idxs = evenly_spaced_indices(r)
    for i in idxs:
        entry = _trinity_entries[i]
        # Step 1: real SHVE.Match predicate re-check
        assert _trinity_shve.match(_trinity_token, entry["shve_ct"])
        # Step 2: real HMAC-SHA256 integrity-tag check
        expected_tag = hmac.new(
            _trinity_tag_key, f"{entry['entry_id']}".encode(), hashlib.sha256
        ).digest()
        assert hmac.compare_digest(expected_tag, entry["verify_tag"])


# ── VC-KASE: fixed number of REAL BLS12-381 pairing operations ──
from py_arkworks_bls12381 import G1Point, G2Point, Scalar, GT

_vckase_g1 = G1Point() * Scalar(random.randint(1, 2 ** 64))
_vckase_g2 = G2Point() * Scalar(random.randint(1, 2 ** 64))
VCKASE_PAIRINGS_PER_QUERY = 2  # fixed, result-count-independent


def vckase_verify(r):
    # Verification cost does not depend on r: a constant number of
    # bilinear-pairing tests regardless of how many results matched.
    for _ in range(VCKASE_PAIRINGS_PER_QUERY):
        GT.pairing(_vckase_g1, _vckase_g2)


def main():
    print("=" * 64)
    print("  Verification Overhead: BVCRSA vs Trinity vs VC-KASE")
    print(f"  N={N_TOTAL}  RUNS={RUNS}")
    print("=" * 64)

    rows = []
    for r in RESULT_COUNTS:
        results = timed_interleaved_ms({
            "bvcrsa": lambda r=r: bvcrsa_verify_multiproof(r),
            "trinity": lambda r=r: trinity_verify(r),
            "vckase": lambda r=r: vckase_verify(r),
        })
        bvcrsa_ms, trinity_ms, vckase_ms = results["bvcrsa"], results["trinity"], results["vckase"]
        rows.append({
            "returned_results": r,
            "bvcrsa_ms": round(bvcrsa_ms, 4),
            "trinity_ms": round(trinity_ms, 4),
            "vckase_ms": round(vckase_ms, 4),
        })
        print(f"  |R|={r:>4d}  BVCRSA={bvcrsa_ms:>8.3f}ms  "
              f"Trinity={trinity_ms:>9.3f}ms  VC-KASE={vckase_ms:>7.3f}ms")

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n[+] Results saved to {CSV_FILE}")


if __name__ == "__main__":
    main()

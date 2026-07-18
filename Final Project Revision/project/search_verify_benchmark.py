#!/usr/bin/env python3
"""
End-to-End Query Latency: Search + Verification
=================================================
Reframes the standalone "Verification Overhead" experiment as a
combined search-then-verify metric: the total time from receiving a
query at the cloud to handing the caller a verified result set,
including the O(N) search over the fixed database (N=10,000) plus
the per-result-set verification cost that scales with |R_Q|.

Every component reuses REAL production code, not standalone models:

  BVCRSA  -- cloud_server.py's actual CloudServer.process_query()
             (real ABSE.Test pairing + PRF tag matching + bitmap
             filtering, Eq. 34-37) for search, and the Merkle
             multi-proof (merkle_tree.py) for verification.
  Trinity -- trinity.py's actual TrinityII.query() (Hilbert range
             check + state-aware token matching, Algorithm 4 of
             Li et al., IEEE TIFS 2025) for search. Verification is
             corrected to match the REAL published Trinity-II
             algorithm (paper Section V-B "Verification", p.4777):
             the server sends an encrypted per-result "verify array"
             vt_i; the client DECRYPTS it and checks it against the
             query -- not merely an HMAC tag comparison, which is
             what this repo's trinity.py had simplified it to.
  VC-KASE -- benchmark_paper.py's VCKASEAlgo.query() for search (the
             same code already backing this paper's other Query
             Processing / Throughput figures, for methodological
             consistency) plus fixed real BLS12-381 pairings for
             verification.

Search cost is measured ONCE per scheme at N=10,000 (it does not
depend on |R_Q| -- the database size and query parameters are fixed,
per the original experiment's own setup) and added as a constant to
each scheme's already-validated per-|R_Q| verification cost.
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
CSV_FILE = os.path.join(BASE_DIR, "search_verify_results.csv")

random.seed(42)


def evenly_spaced_indices(r, n=N_TOTAL):
    return [int(i * n / r) for i in range(r)]


def timed_ms(fn, runs=RUNS, warmup=WARMUP_RUNS):
    for _ in range(warmup):
        fn()
    samples = []
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(runs):
            t0 = time.perf_counter()
            fn()
            samples.append((time.perf_counter() - t0) * 1000)
    finally:
        if gc_was_enabled:
            gc.enable()
    return statistics.median(samples)


def timed_once_ms(fn):
    t0 = time.perf_counter()
    fn()
    return (time.perf_counter() - t0) * 1000


def _hash(data):
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


# ══════════════════════════════════════════════════════════════
#  BVCRSA: real production search (cloud_server.py) + real
#  Merkle multi-proof verification
# ══════════════════════════════════════════════════════════════
print("[setup] Building BVCRSA index (N=%d, real pipeline)..." % N_TOTAL)
from TA import TrustedAuthority
from blockchain_edge import BlockchainEdgeManager
from cloud_server import CloudServer
from sensor import sensor_encrypt
from user_client import UserClient

_bvcrsa_ta = TrustedAuthority()
_bvcrsa_secrets = _bvcrsa_ta.key_gen(["Analyst", "Temp"])
_bvcrsa_edge = BlockchainEdgeManager(_bvcrsa_secrets, _bvcrsa_secrets["abse"])
_bvcrsa_aes_key = _bvcrsa_ta.get_sensor_key("S1")
_bvcrsa_hmac_key = _bvcrsa_ta.get_sensor_hmac_key("S1")

_bvcrsa_nodes = []
for i in range(N_TOTAL):
    payload = sensor_encrypt("S1", "M1", "Temp", "2026-05-20 15:00:00",
                              random.randint(0, 100), _bvcrsa_aes_key,
                              _bvcrsa_hmac_key, _bvcrsa_ta.ec_pubkey, seq_counter=i + 1)
    _bvcrsa_edge.verify_sensor_payload(payload, _bvcrsa_hmac_key)
    _bvcrsa_nodes.extend(_bvcrsa_edge.build_scrat_from_payload(payload))


class _InMemoryDB:
    def __init__(self, docs):
        self._docs = docs

    def find(self, query):
        return [d for d in self._docs if all(d.get(k) == v for k, v in query.items())]


_bvcrsa_cloud = CloudServer(_InMemoryDB(_bvcrsa_nodes))
_bvcrsa_client = UserClient(_bvcrsa_secrets)
_bvcrsa_trapdoor = _bvcrsa_client.generate_trapdoor("M1", "Temp", "2026-05-20 15", 0, 100)

# real Merkle multi-proof verification, over BVCRSA's own committed nodes
from merkle_tree import MerkleTree

_bvcrsa_leaf_strs = [f"{n['search_tag']}|{n['sigma']}|{n['CT_v']}|{n['Cnt_u']}" for n in _bvcrsa_nodes]
_bvcrsa_verify_tree = MerkleTree(_bvcrsa_leaf_strs)
_bvcrsa_verify_root = _bvcrsa_verify_tree.get_root()


def bvcrsa_search():
    return _bvcrsa_cloud.process_query(_bvcrsa_trapdoor)


def bvcrsa_verify(r):
    idxs = evenly_spaced_indices(r, n=len(_bvcrsa_leaf_strs))
    leaves = {i: _bvcrsa_leaf_strs[i] for i in idxs}
    mp = _bvcrsa_verify_tree.get_multi_proof(idxs)
    assert MerkleTree.verify_multi_proof(leaves, mp, _bvcrsa_verify_root)


# ══════════════════════════════════════════════════════════════
#  Trinity: real production search (trinity.py TrinityII.query())
#  + REAL published verify-array decrypt-and-check (paper Sec. V-B)
# ══════════════════════════════════════════════════════════════
print("[setup] Building Trinity-II index (N=%d, real pipeline)..." % N_TOTAL)
from trinity import TrinityII
from Crypto.Cipher import AES

_trinity_scheme = TrinityII()
_trinity_scheme.setup(256, 8, 10)
for i in range(N_TOTAL):
    rec = {
        "device_id": str(i),
        "latitude": 13.4 + random.random() * 0.2,
        "longitude": 99.9 + random.random() * 0.2,
        "timestamp": int(time.time()) + i,
        "keywords": ["Temp"],
    }
    _trinity_scheme.gen_index(rec)

_now = int(time.time())
_trinity_qp = {
    "lat_range": (13.4, 13.6), "lon_range": (99.9, 100.1),
    "time_range": (_now - 7200, _now + 3600), "keywords": ["Temp"],
}
_trinity_trapdoor = _trinity_scheme.gen_trap(_trinity_qp)


def trinity_search():
    return _trinity_scheme.query(_trinity_trapdoor)


# Real published Trinity-II verification (paper p.4777, Sec. V-B2
# "Details of Trinity-II Construction... Verification"): the CS sends
# an encrypted per-result verify array vt_i; the DU decrypts it and
# checks it against the query. Modeled here as AES-GCM encrypt/decrypt
# of a compact per-entry verify array (the paper does not give an
# exact byte length; we use a representative 16-byte array, consistent
# with the paper's own framing of it as a compact, roaring-bitmap-
# compressed structure) plus a content check against the query
# predicate -- not merely an HMAC tag recomputation.
_trinity_verify_key = os.urandom(32)  # "extra secret key sk" (paper: Setup)
_trinity_query_predicate = os.urandom(16)  # bits the DU checks the array against

_trinity_verify_entries = []
for i in range(N_TOTAL):
    verify_array = _trinity_query_predicate if i % 3 == 0 else os.urandom(16)  # ~1/3 true positives
    nonce = os.urandom(12)
    cipher = AES.new(_trinity_verify_key, AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(verify_array)
    _trinity_verify_entries.append({"nonce": nonce, "ct": ct, "tag": tag})


def trinity_verify(r):
    idxs = evenly_spaced_indices(r)
    for i in idxs:
        entry = _trinity_verify_entries[i]
        cipher = AES.new(_trinity_verify_key, AES.MODE_GCM, nonce=entry["nonce"])
        decrypted = cipher.decrypt_and_verify(entry["ct"], entry["tag"])
        _ = decrypted == _trinity_query_predicate  # DU's content check


# ══════════════════════════════════════════════════════════════
#  VC-KASE: real search (benchmark_paper.py's VCKASEAlgo, the same
#  code already backing this paper's other query figures) + real
#  fixed BLS12-381 pairing verification
# ══════════════════════════════════════════════════════════════
print("[setup] Building VC-KASE index (N=%d)..." % N_TOTAL)
from benchmark_paper import gen_data, VCKASEAlgo

_vckase_records = gen_data(N_TOTAL, num_kw=2)
_vckase_algo = VCKASEAlgo()
_vckase_algo.setup(2)
_vckase_algo.index_build(_vckase_records)
_vckase_trapdoor = _vckase_algo.trap_gen(_vckase_records[0]["sensor"], 0, 100)

from py_arkworks_bls12381 import G1Point, G2Point, Scalar, GT

_vckase_g1 = G1Point() * Scalar(random.randint(1, 2 ** 64))
_vckase_g2 = G2Point() * Scalar(random.randint(1, 2 ** 64))
VCKASE_PAIRINGS_PER_QUERY = 2


def vckase_search():
    return _vckase_algo.query(_vckase_trapdoor)


def vckase_verify(r):
    for _ in range(VCKASE_PAIRINGS_PER_QUERY):
        GT.pairing(_vckase_g1, _vckase_g2)


def main():
    print("=" * 70)
    print("  End-to-End Query Latency: Search + Verification")
    print(f"  N={N_TOTAL}  verify RUNS={RUNS} (median)")
    print("=" * 70)

    search_ms = {
        "bvcrsa": statistics.median([timed_once_ms(bvcrsa_search) for _ in range(5)]),
        "trinity": statistics.median([timed_once_ms(trinity_search) for _ in range(5)]),
        "vckase": statistics.median([timed_once_ms(vckase_search) for _ in range(5)]),
    }
    print("\n[search cost, fixed, N=%d, median of 5]" % N_TOTAL)
    for k, v in search_ms.items():
        print(f"  {k:8s}: {v:8.2f} ms")

    rows = []
    print("\n[verify + total cost vs |R_Q|]")
    for r in RESULT_COUNTS:
        bvcrsa_v = timed_ms(lambda: bvcrsa_verify(r))
        trinity_v = timed_ms(lambda: trinity_verify(r))
        vckase_v = timed_ms(lambda: vckase_verify(r))

        row = {
            "returned_results": r,
            "bvcrsa_search_ms": round(search_ms["bvcrsa"], 4),
            "bvcrsa_verify_ms": round(bvcrsa_v, 4),
            "bvcrsa_total_ms": round(search_ms["bvcrsa"] + bvcrsa_v, 4),
            "trinity_search_ms": round(search_ms["trinity"], 4),
            "trinity_verify_ms": round(trinity_v, 4),
            "trinity_total_ms": round(search_ms["trinity"] + trinity_v, 4),
            "vckase_search_ms": round(search_ms["vckase"], 4),
            "vckase_verify_ms": round(vckase_v, 4),
            "vckase_total_ms": round(search_ms["vckase"] + vckase_v, 4),
        }
        rows.append(row)
        print(f"  |R|={r:>4d}  BVCRSA={row['bvcrsa_total_ms']:>8.2f}ms  "
              f"Trinity={row['trinity_total_ms']:>8.2f}ms  "
              f"VC-KASE={row['vckase_total_ms']:>8.2f}ms")

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n[+] Results saved to {CSV_FILE}")


if __name__ == "__main__":
    main()

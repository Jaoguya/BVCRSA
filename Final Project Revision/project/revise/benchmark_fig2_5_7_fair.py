#!/usr/bin/env python3
"""
benchmark_fig2_5_7_fair.py
==========================
Fair, bug-fixed re-run of paper Experiments 2, 5, and 7:

  Fig. 2 (paper): Index-construction time versus database size
  Fig. 5 (paper): Query processing time versus database size
  Fig. 7 (paper): Query throughput under increasing query workload

This is a corrected replacement for original_reference/benchmark_exp2_5_7_ORIGINAL_buggy.py
and original_reference/benchmark_exp_7_ORIGINAL_buggy.py. See reviseplan.md for the full
reviewer-style writeup. In short, the original script had two serious fairness bugs in
BVCRSAAlgo that are fixed here:

  BUG #1 (fake search): the original `query()` located matching nodes via a plain Python
  dict lookup keyed by *plaintext* (machine, keyword, time_slot, lo, hi) tuples. It never
  called ABSE.test(), never did a bitmap AND, and never checked the PRF search tag. Every
  other baseline (VC-KASE, Latt-IBEKS, Trinity, ABSE-Range) does real O(N) work (and
  ABSE-Range does genuine per-record bilinear pairings). This made BVCRSA's reported query
  time and throughput several orders of magnitude better than reality — not a measurement
  of the scheme, just a hash-table lookup with zero cryptographic cost.

  BUG #2 (fake aggregation): the original code did
      agg = matched[0]["Agg_u"]; for n in matched[1:]: agg += n["Agg_u"]
  but `Agg_u` is a *serialized string* ("x1:y1:x2:y2"), so `+=` was Python string
  concatenation, not EC point addition. The "homomorphic aggregation" component of the
  claimed query-processing time cost essentially nothing.

Fix: BVCRSAAlgo.query() now mirrors the project's own cloud_server.py design (the
"ABSE-once fast path"): candidates are narrowed to the keyword bucket — the same coarse
filter a real `db.find({k_enc})` index lookup would give in production (an
*architectural* advantage of the authenticated range-cover index, which is the paper's
actual scientific claim and is legitimate to keep) — then, for that bucket:
  1. a real ABSE.test() bilinear-pairing authorization loop (as cloud_server.py does:
     iterate candidates until one pairing succeeds, or the bucket is exhausted),
  2. a real bitmap AND per candidate,
  3. a real PRF search-tag equality check per candidate,
  4. real EC-ElGamal point addition (not string concatenation) over matched ciphertexts.

BUG #3 (found while smoke-testing the fix above, not present in the original bug list):
the original `index_build`/`trap_gen` tagged every canonical node with context
(machine, keyword, hour-slot) baked into the PRF tag input (`gen_tag(Ks, m, k, t_slot,
node)`), and `trap_gen` picked ONE arbitrary sample record's (machine, hour) as the
query's fixed context. That scopes every BVCRSA query to a single (machine, hour) slice
of the data, while every baseline's `query()` scans the *entire* N-record corpus for a
keyword+range match with no machine/time restriction — a semantic mismatch, not just a
performance one: BVCRSA was being asked a much narrower question. It also explains why
the original results CSV showed `matched` pinned at a constant 4 regardless of N from
1,000 to 100,000 — a fixed (machine, hour) slice doesn't grow with N (this dataset's
generator spreads more records over more elapsed time as N grows, not more density per
hour), so the experiment could never show real query-cost scaling for BVCRSA at all.
Fix: for this single-dimension experiment (keyword + numeric range only — matching
exactly what Fig. 2/5/7 and every baseline actually query), BVCRSA's node context is
fixed to a constant placeholder instead of the record's real machine/hour, so canonical
nodes are bucketed by keyword alone, multiple records legitimately collide onto the same
node (accumulated via the existing homomorphic Agg_u/Cnt_u update path already in
blockchain_edge.py — this is exactly what that code path is for), and a single trapdoor
covers the whole dataset, matching the baselines' query semantics.

ABSE-Range handling: its query() performs genuine O(N) bilinear pairings with no index
narrowing (that scheme has no indexing structure — this is its real, disclosed weakness,
not a bug). At N=50,000/100,000 this is computationally infeasible to run for real within
the available time (measured: ~8.5ms/record x N -> tens of minutes to hours). Its
*index-construction* time (Encrypt only, ~1ms/record) IS measured for real at every N.
Its *query* time is measured for real only at N in {1000, 5000, 10000}, then extrapolated
to N in {50000, 100000} via a linear least-squares fit (search cost is provably O(N) —
fixed pairings per record) and clearly marked note="predicted_linear_extrapolation" in the
CSV, together with the fitted slope/intercept and R^2 so the extrapolation is auditable.
This is NOT the same thing as fabricating a result: the model is disclosed, falsifiable,
and grounded in a measured, real per-record cost.

Exp. 7 (throughput) methodology change: the original script looped calling query() up to
10,000 times per (algorithm, Q) pair. For algorithms with expensive per-query cost (e.g.
Trinity ~1.6s/query, ABSE-Range ~8.5ms/record x N), this is either impractically slow
(Trinity's own historical run: ~4.25 hours for a single Q=10,000 data point) or outright
infeasible (ABSE-Range at N=10,000: ~85s/query x 10,000 reps = ~10 days). Because every
query in this benchmark is stateless and identically costed (no batching, caching, or
contention modeling), throughput = Q / (Q * per_query_latency) = 1 / per_query_latency is
mathematically exact — looping does not measure anything a single averaged latency
doesn't already capture, it just re-measures the same constant with more noise. We
therefore measure per_query_latency once per algorithm (average of R independent repeated
queries, R chosen per algorithm's cost) and derive total_ms/throughput analytically for
every target Q. This is disclosed in the CSV (method="latency_x_Q") and in reviseplan.md,
including the implication that a single-threaded, non-batched design of this kind cannot
show saturation/contention effects — the "throughput vs workload" curve for every
algorithm is expected to be flat (see reviseplan.md discussion).

Output: benchmark_fig2_5_7_fair_results.csv (all columns preserved/extended from the
original for drop-in compatibility with plotting code).
"""

import sys, os, time, random, hashlib, traceback
import numpy as np
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
ADDED_DIR = os.path.join(BASE_DIR, "added_paper")
sys.path.insert(0, ADDED_DIR)

DATARECORD_CSV = os.path.join(BASE_DIR, "Datarecord.csv")
OUTPUT_CSV     = os.path.join(BASE_DIR, "benchmark_fig2_5_7_fair_results.csv")

# ── Import crypto modules (same modules the fixed BVCRSA path uses) ────────
from TA import TrustedAuthority as RealTA
from blockchain_edge import BlockchainEdgeManager
from utils import gen_tag, gen_query_bitmap
from ec_elgamal import ECEncryptedNumber
from trinity import TrinityI

try:
    from abse_fast import ABSE as _ABSE_ACTIVE
    ABSE_BACKEND = "abse_fast (BLS12-381 / py_arkworks_bls12381)"
except ImportError:
    from abse_real import ABSE as _ABSE_ACTIVE
    ABSE_BACKEND = "abse_real (BN128 / py_ecc)"

try:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "abse_range", os.path.join(ADDED_DIR, "Attribute-based.py"))
    abse_range_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(abse_range_mod)
    HAS_ABSE_RANGE = True
except Exception as e:
    print(f"  [warn] ABSE-Range unavailable: {e}")
    HAS_ABSE_RANGE = False
    abse_range_mod = None

print(f"  [config] ABSE backend in use: {ABSE_BACKEND}")
print(f"           (paper's Experimental Setup text states BN128 via py_ecc; see")
print(f"            reviseplan.md for the disclosure/decision on this discrepancy)")

# ── Constants ────────────────────────────────────────────────────────────
KEYWORD_POOL = [
    "Temp", "Humidity", "Pressure", "Vibration", "Voltage",
    "Current", "Power", "Flow", "Level", "Speed",
    "Torque", "RPM", "Weight", "Density", "pH",
    "Viscosity", "Turbidity", "Proximity", "Strain", "Acoustic",
]
N_VALUES          = [1_000, 5_000, 10_000, 50_000, 100_000]
ABSE_RANGE_QUERY_MAX_N = 10_000   # beyond this, query_ms is predicted, not measured
FIXED_N_THRU      = 10_000
QUERY_COUNTS      = [100, 500, 1_000, 5_000, 10_000]
RUNS              = 5             # trap/query timing repeats for cheap algorithms
RUNS_EXPENSIVE    = 2              # for ABSE-Range (real per-record pairings)
THROUGHPUT_REPS = {                # per-algorithm reps for the single-query latency probe
    "BVCRSA": 30, "Trinity": 5, "VC-KASE": 30, "Latt-IBEKS": 30, "ABSE-Range": 3,
}
SEED = 42


def load_datarecord(n):
    import csv
    recs = []
    with open(DATARECORD_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= n:
                break
            recs.append({
                "id":            int(row["id"]),
                "machine":       row["machine"],
                "sensor":        row["sensor"],
                "value":         int(row["value"]),
                "timestamp":     datetime.strptime(row["timestamp_str"], "%Y-%m-%d %H:%M:%S"),
                "timestamp_str": row["timestamp_str"],
                "t_slot":        row["t_slot"],
            })
    return recs


def timed(fn, runs=RUNS):
    results, ret = [], None
    for _ in range(runs):
        t0 = time.perf_counter()
        ret = fn()
        results.append((time.perf_counter() - t0) * 1000)
    return sum(results) / len(results), ret


# ════════════════════════════════════════════════════════════════════════
#  BVCRSA — FIXED: real ABSE.test + real bitmap AND + real tag check +
#                  real EC-ElGamal point addition (no plaintext-key lookup,
#                  no string-concatenation "aggregation")
# ════════════════════════════════════════════════════════════════════════
class BVCRSAAlgo:
    name = "BVCRSA"

    def setup(self, kw_count=2):
        self.ta = RealTA()
        self.abse = self.ta.abse
        attrs = ["Analyst"] + KEYWORD_POOL[:kw_count]
        self.secrets = self.ta.key_gen(attrs)
        self.enclave = BlockchainEdgeManager(self.secrets, self.abse)
        self.Ks = self.secrets["Ks"]
        self.sk_abse = self.secrets.get("SK_A")
        self.ec_pub  = self.secrets["ec_pubkey"]
        self.ec_priv = self.secrets["ec_privkey"]

    # Fixed placeholder context: this experiment (Fig. 2/5/7) is a single-dimension
    # keyword+range query, matching exactly what every baseline algorithm queries
    # (whole-dataset keyword+range scan, no machine/time restriction). See BUG #3
    # in the module docstring for why machine/hour must NOT be baked into the tag
    # context here.
    CTX_M = "GLOBAL"
    CTX_T = "GLOBAL"

    def index_build(self, records, db=None):
        self.enclave.blockchain.clear()
        self.enclave.node_state = {}
        self.enclave.merkle_leaves = []
        self.enclave.seq_counters = {}
        self.enclave.epoch = 0
        self.nodes = []
        # Bucket keyed by keyword ONLY — mirrors cloud_server.py's real production
        # query `db.find({"k_enc": ...})`, which narrows by keyword hash. This
        # preserves the paper's actual architectural claim (index narrows candidates
        # vs. full O(N) scan) without shortcutting the crypto verification that must
        # still run per candidate, and keeps the query scope identical to every
        # baseline (whole dataset, one keyword, one numeric range).
        self.node_index = {}
        for rec in records:
            ns = self.enclave.build_scrat_from_payload({
                "ct_aes": "dummy",
                "ct_v": self.ec_pub.encrypt(rec["value"]).ciphertext(),
                "ctx": {"m": self.CTX_M, "k": rec["sensor"], "t": self.CTX_T},
                "path": [{"l": (rec["value"] // 10) * 10, "r": (rec["value"] // 10) * 10 + 10}],
                "seq": 1, "hmac": b""
            })
            for n in ns:
                self.nodes.append(n)
                self.node_index.setdefault(n["k"], []).append(n)
        return len(self.nodes)

    def trap_gen(self, keyword, a, b):
        ranges = [(i, i + 10) for i in range((a // 10) * 10, (b // 10) * 10 + 10, 10)]
        tags = [gen_tag(self.Ks, self.CTX_M, keyword, self.CTX_T, {"l": lo, "r": hi})
                for lo, hi in ranges]
        query_bitmaps = [gen_query_bitmap(self.Ks, self.CTX_M, keyword, self.CTX_T, lo, hi)
                          for lo, hi in ranges]

        auth_token = None
        if self.sk_abse:
            try:
                auth_token = self.abse.token_gen(self.sk_abse, tags[0])
            except Exception:
                auth_token = None

        return {
            "ranges": ranges, "tags": tags, "query_bitmaps": query_bitmaps,
            "k": keyword, "auth_token": auth_token,
        }

    def query(self, td):
        if td is None:
            return 0

        candidates = self.node_index.get(td["k"], [])
        if not candidates:
            return 0

        # Step 1: real ABSE.Test bilinear-pairing authorization loop — mirrors
        # cloud_server.py's `_query_fast` exactly: try candidates' CT_tag against
        # the auth token until one pairing succeeds (real crypto cost every
        # iteration), or the bucket is exhausted (real worst-case cost too).
        authorized = False
        if td["auth_token"] is not None:
            for n in candidates:
                try:
                    if self.abse.test(td["auth_token"], n["CT_tag"]):
                        authorized = True
                        break
                except Exception:
                    continue
        if not authorized:
            return 0

        # Step 2: real per-candidate bitmap AND + real PRF tag equality check.
        expected_tags = set(td["tags"])
        query_bms = [int(b, 2) for b in td["query_bitmaps"]]
        matched = []
        for n in candidates:
            b_node = int(n["B_tilde"], 2)
            if not any(b_node & qb for qb in query_bms):
                continue
            if n["search_tag"] in expected_tags:
                matched.append(n)

        # Step 3: real EC-ElGamal homomorphic aggregation (point addition, not
        # string concatenation).
        if matched:
            agg = ECEncryptedNumber.from_string(self.ec_pub, matched[0]["Agg_u"])
            for n in matched[1:]:
                agg = agg + ECEncryptedNumber.from_string(self.ec_pub, n["Agg_u"])

        return len(matched)


# ════════════════════════════════════════════════════════════════════════
#  VC-KASE / Latt-IBEKS / Trinity / ABSE-Range — unchanged from the
#  original harness (already do real O(N) per-query work; ABSE-Range does
#  genuine bilinear pairings). Kept identical so the comparison baselines
#  are apples-to-apples with the original run.
# ════════════════════════════════════════════════════════════════════════
class SimulatedPairingGroup:
    def __init__(self, p=2**256 - 2**32 - 977):
        self.p = p; self.g = 2
    def exp_G(self, base, exp): return pow(base, exp, self.p)
    def pair(self, g1, g2):    return pow(g1 * g2, 3, self.p)


class VCKASEAlgo:
    name = "VC-KASE"
    def setup(self, kw_count=2):
        self.group = SimulatedPairingGroup()
        self.n_docs = 100_000
        self.alpha  = random.randint(1, self.group.p - 1)
        self.g_list = {}
        self.beta   = random.randint(1, self.group.p - 1)
        self.lam    = random.randint(1, self.group.p - 1)
        self.pk_o   = self.group.exp_G(self.group.g, self.beta)
        self.gamma  = random.randint(1, self.group.p - 1)
        self.pk_s   = self.group.exp_G(self.group.g, self.gamma)

    def _get_g(self, i):
        if i not in self.g_list:
            self.g_list[i] = self.group.exp_G(self.group.g, pow(self.alpha, i, self.group.p - 1))
        return self.g_list[i]

    def hash_H(self, s):
        return int(hashlib.sha256(str(s).encode()).hexdigest(), 16) % self.group.p

    def index_build(self, records, db=None):
        self.index = []
        for rec in records:
            r  = random.randint(1, self.group.p - 1)
            c1 = self.group.exp_G(self.group.g, r)
            c2 = self.group.exp_G(self.group.g, (self.lam * r) % (self.group.p - 1))
            self.index.append({"id": rec["id"] + 1, "c1": c1, "c2": c2,
                                "sensor": rec["sensor"], "value": rec["value"]})
        self.K1_S = 1
        for j in [rec2["id"] + 1 for rec2 in records]:
            self.K1_S = (self.K1_S *
                self.group.exp_G(self._get_g(self.n_docs + 1 - j), self.beta)) % self.group.p
        return len(records)

    def trap_gen(self, keyword, a, b):
        x = random.randint(1, self.group.p - 1)
        y = random.randint(1, self.group.p - 1)
        sw = sum(self.hash_H(w) for w in [keyword, str(a), str(b)]) % (self.group.p - 1)
        T1 = (self.K1_S
              * self.group.exp_G(self.pk_o, (sw * x) % (self.group.p - 1))
              * self.group.exp_G(self.group.g, y)) % self.group.p
        return {"T1": T1, "T2": self.group.exp_G(self.group.g, x),
                "keyword": keyword, "a": a, "b": b}

    def query(self, td):
        return sum(1 for ct in self.index
                   if ct["sensor"] == td["keyword"] and td["a"] <= ct["value"] <= td["b"])


class LatticeIBEKSAlgo:
    name = "Latt-IBEKS"
    def setup(self, kw_count=2):
        self.n_dim = 17; self.q = 4093; self.N_kw = 5
        self.m     = int(6 * self.n_dim * 1.5)
        self.A     = np.random.randint(0, self.q, (self.n_dim, self.m))
        self.B     = np.random.randint(0, self.q, (self.n_dim, self.m))

    def hash_H2(self, kw):
        return int(hashlib.sha256(str(kw).encode()).hexdigest(), 16) % self.q

    def index_build(self, records, db=None):
        self.index = []
        for rec in records:
            xw  = self.hash_H2(rec["sensor"])
            y_0 = np.array([(xw**i) % self.q for i in range(self.N_kw + 1)])
            y   = np.zeros(self.n_dim, dtype=int)
            y[:len(y_0)] = y_0
            self.index.append({"y": y, "sensor": rec["sensor"], "value": rec["value"]})
        return len(records)

    def trap_gen(self, keyword, a, b):
        roots = [self.hash_H2(w) for w in [keyword, str(a), str(b)]]
        while len(roots) < self.N_kw:
            roots.append(np.random.randint(0, self.q))
        coeffs = np.poly(roots)
        b_0    = np.array([int(round(c)) % self.q for c in coeffs[::-1]])
        b_vec  = np.zeros(self.n_dim, dtype=int)
        b_vec[:len(b_0)] = b_0
        return {"b_vec": b_vec, "keyword": keyword, "a": a, "b": b}

    def query(self, td):
        return sum(1 for ct in self.index
                   if ct["sensor"] == td["keyword"] and td["a"] <= ct["value"] <= td["b"])


class TrinityAlgo:
    name = "Trinity"
    def setup(self, kw_count=2):
        self.scheme = TrinityI()
        self.scheme.setup(256, 8, 10)
        from datetime import datetime as _dt
        self.scheme.time_min = int(_dt(2024, 1, 1).timestamp())
        self.scheme.time_max = int(_dt(2025, 1, 1).timestamp())

    def index_build(self, records, db=None):
        self.scheme.EDB = {}
        self.scheme.entry_counter = 0
        self.scheme.qf = type(self.scheme.qf)(quotient_bits=12, remainder_bits=8)
        self.entries = [
            self.scheme.gen_index({
                "device_id": str(rec["id"]),
                "latitude":  13.5, "longitude": 100.0,
                "timestamp": int(rec["timestamp"].timestamp()),
                "keywords":  [rec["sensor"]]
            }) for rec in records
        ]
        return len(self.entries)

    def trap_gen(self, keyword, a, b):
        from datetime import datetime as _dt
        t_lo = int(_dt(2024, 1, 1).timestamp())
        t_hi = int(_dt(2024, 12, 31).timestamp())
        return self.scheme.gen_trap({
            "lat_range": (13.4, 13.6), "lon_range": (99.9, 100.1),
            "time_range": (t_lo, t_hi), "keywords": [keyword]
        })

    def query(self, trapdoor):
        if not trapdoor or not trapdoor.get("intervals"):
            return 0
        return sum(1 for entry in self.entries
                   for lo, hi in trapdoor["intervals"]
                   if lo <= entry["hilbert_index"] <= hi)


class ABSERangeAlgo:
    name = "ABSE-Range"
    def setup(self, kw_count=2):
        self.pk, self.msk = abse_range_mod.setup()
        self.sk = abse_range_mod.key_gen(self.msk, ["Analyst", "Temp", "Humidity"])

    def index_build(self, records, db=None):
        self.cts = [abse_range_mod.encrypt(self.pk, ["Analyst"], rec["value"], [rec["sensor"]])
                    for rec in records]
        return len(self.cts)

    def trap_gen(self, keyword, a, b):
        td, _ = abse_range_mod.trap_gen(self.sk, [keyword])
        return td

    def query(self, trapdoor):
        matched = 0
        for ct in self.cts:
            try:
                abse_range_mod.search(ct, trapdoor); matched += 1
            except Exception:
                pass
        return matched


def eta(elapsed_s, done, total):
    if done == 0:
        return "?"
    rem = elapsed_s / done * (total - done)
    if rem < 60:
        return f"{rem:.0f}s"
    if rem < 3600:
        return f"{rem / 60:.1f}min"
    return f"{rem / 3600:.1f}h"


def _save_csv(results, path):
    if not results:
        return
    pd.DataFrame(results).to_csv(path, index=False)


def linear_fit(xs, ys):
    """Least-squares linear fit y = slope*x + intercept, plus R^2."""
    xs = np.array(xs, dtype=float); ys = np.array(ys, dtype=float)
    slope, intercept = np.polyfit(xs, ys, 1)
    pred = slope * xs + intercept
    ss_res = np.sum((ys - pred) ** 2)
    ss_tot = np.sum((ys - np.mean(ys)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return float(slope), float(intercept), float(r2)


def main():
    print("\n" + "=" * 70)
    print("  BVCRSA FAIR Benchmark — Experiments 2, 5 & 7 (bug-fixed)")
    print("  N values: 1K / 5K / 10K / 50K / 100K")
    print("=" * 70)

    if not os.path.exists(DATARECORD_CSV):
        print(f"  Datarecord.csv not found at {DATARECORD_CSV}. Run generate_datarecord.py first.")
        sys.exit(1)

    ALL_ALGOS = [BVCRSAAlgo, TrinityAlgo, VCKASEAlgo, LatticeIBEKSAlgo]
    if HAS_ABSE_RANGE:
        ALL_ALGOS.insert(3, ABSERangeAlgo)

    results = []
    abse_range_query_points = []  # (N, query_ms) real measurements for extrapolation

    # ══════════════════════════════════════════════════════════
    #  EXP 2 & 5: Index Construction + Query Processing vs N
    # ══════════════════════════════════════════════════════════
    exp_start = time.perf_counter()
    total_tasks = len(N_VALUES) * len(ALL_ALGOS)
    done_tasks = 0

    for N in N_VALUES:
        print(f"\n  -- Loading {N:,} records --", flush=True)
        records = load_datarecord(N)

        for AlgoCls in ALL_ALGOS:
            algo = AlgoCls()
            name = algo.name
            skip_query = (name == "ABSE-Range" and N > ABSE_RANGE_QUERY_MAX_N)

            try:
                print(f"    {name:12s} | building index for N={N:,}...", end="", flush=True)
                algo.setup(2)
                t0 = time.perf_counter()
                algo.index_build(records, db=None)
                idx_ms = (time.perf_counter() - t0) * 1000
                print(f" {idx_ms:>10.1f}ms", end="", flush=True)

                runs = RUNS_EXPENSIVE if name == "ABSE-Range" else RUNS
                trap_ms, td = timed(lambda: algo.trap_gen("Temp", 35, 65), runs=runs)

                if skip_query:
                    print(f" | trap={trap_ms:>8.3f}ms | query=PREDICTED (see note)")
                    results.append({
                        "exp": "exp2_5", "dim": "vs_N", "N": N, "algo": name,
                        "index_ms": round(idx_ms, 3), "trap_ms": round(trap_ms, 4),
                        "query_ms": None, "matched": None,
                        "note": "query_predicted_linear_extrapolation",
                    })
                else:
                    qry_ms, matched = timed(lambda: algo.query(td), runs=runs)
                    print(f" | trap={trap_ms:>8.3f}ms | qry={qry_ms:>8.3f}ms | match={matched}")
                    if name == "ABSE-Range" and N <= ABSE_RANGE_QUERY_MAX_N:
                        abse_range_query_points.append((N, qry_ms))
                    results.append({
                        "exp": "exp2_5", "dim": "vs_N", "N": N, "algo": name,
                        "index_ms": round(idx_ms, 3), "trap_ms": round(trap_ms, 4),
                        "query_ms": round(qry_ms, 4), "matched": matched,
                        "note": "",
                    })
            except Exception as e:
                print(f" | ERROR: {e}")
                traceback.print_exc()
                results.append({
                    "exp": "exp2_5", "dim": "vs_N", "N": N, "algo": name,
                    "index_ms": None, "trap_ms": None, "query_ms": None, "matched": None,
                    "note": f"error: {e}",
                })

            done_tasks += 1
            elapsed = time.perf_counter() - exp_start
            print(f"         [Progress {done_tasks}/{total_tasks} | elapsed={elapsed/60:.1f}min | "
                  f"ETA={eta(elapsed, done_tasks, total_tasks)}]")
            _save_csv(results, OUTPUT_CSV)

    # ── Backfill predicted ABSE-Range query_ms for N > 10,000 ──────────
    if HAS_ABSE_RANGE and len(abse_range_query_points) >= 2:
        xs, ys = zip(*abse_range_query_points)
        slope, intercept, r2 = linear_fit(xs, ys)
        print(f"\n  ABSE-Range query_ms linear fit: slope={slope:.6f} ms/record, "
              f"intercept={intercept:.4f} ms, R^2={r2:.5f}")
        for row in results:
            if (row["exp"] == "exp2_5" and row["algo"] == "ABSE-Range"
                    and row["note"] == "query_predicted_linear_extrapolation"):
                pred = slope * row["N"] + intercept
                row["query_ms"] = round(pred, 3)
                row["note"] = (f"predicted_linear_extrapolation "
                                f"(slope={slope:.6f},intercept={intercept:.4f},R2={r2:.5f},"
                                f"fit_points={list(abse_range_query_points)})")
        _save_csv(results, OUTPUT_CSV)

    # ══════════════════════════════════════════════════════════
    #  EXP 7: Query Throughput — analytic (measure latency once,
    #  derive total_ms/throughput for each Q; see module docstring)
    # ══════════════════════════════════════════════════════════
    print(f"\n{'-'*70}")
    print(f"  EXP 7: Query Throughput vs Query Workload (N={FIXED_N_THRU:,} fixed)")
    print(f"  Method: average per-query latency over R reps, then throughput = 1/latency")
    print(f"{'-'*70}")

    records_thru = load_datarecord(FIXED_N_THRU)

    for AlgoCls in ALL_ALGOS:
        algo = AlgoCls()
        name = algo.name
        reps = THROUGHPUT_REPS.get(name, 10)
        print(f"\n  -- {name} (R={reps} reps) --")
        try:
            algo.setup(2)
            algo.index_build(records_thru, db=None)
            td = algo.trap_gen("Temp", 35, 65)

            lat_ms, _ = timed(lambda: algo.query(td), runs=reps)
            lat_s = lat_ms / 1000.0
            print(f"    measured per-query latency: {lat_ms:.4f} ms (avg of {reps} reps)")

            for Q in QUERY_COUNTS:
                total_s = Q * lat_s
                throughput = (1.0 / lat_s) if lat_s > 0 else float("inf")
                results.append({
                    "exp": "exp7", "dim": "vs_throughput", "N": FIXED_N_THRU, "algo": name,
                    "query_count": Q, "total_ms": round(total_s * 1000, 3),
                    "throughput": round(throughput, 3),
                    "note": f"method=latency_x_Q;measured_latency_ms={lat_ms:.4f};reps={reps}",
                })
            print(f"    throughput (constant across Q, by construction): {1.0/lat_s:.2f} q/s")
        except Exception as e:
            print(f"    ERROR: {e}")
            traceback.print_exc()

        _save_csv(results, OUTPUT_CSV)

    _save_csv(results, OUTPUT_CSV)
    total_elapsed = (time.perf_counter() - exp_start) / 60
    print(f"\n{'='*70}")
    print(f"  Done. Total time: {total_elapsed:.1f} minutes")
    print(f"  Results: {OUTPUT_CSV}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

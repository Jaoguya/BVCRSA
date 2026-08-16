#!/usr/bin/env python3
"""
Baseline scheme implementations + shared benchmark harness.
===========================================================
Extracted from the retired monolithic `benchmark_paper.py` so that every
experiment under Benchmark/ imports ONE canonical definition of each
scheme instead of re-declaring it.

Schemes provided
----------------
  BVCRSAAlgo      -- our scheme (TA -> blockchain_edge -> bitmap index)
  TrinityAlgo     -- Trinity-I (ref26), via trinity.py
  ABSERangeAlgo   -- ABSE-Range (ref27), via Attribute-based.py
  VCKASEAlgo      -- VC-KASE (ref16), key-aggregate searchable encryption
  LatticeIBEKSAlgo-- Latt-IBEKS (ref28), lattice/LWE searchable encryption
                     incl. the Scheme-II conjunctive patch

Data source
-----------
`load_datarecord(n)` reads the first n rows of CSV/Datarecord.csv. This is
the canonical path -- MongoDB has been removed from the pipeline entirely.
`gen_data()` is retained ONLY for the skew-robustness check, which needs a
non-uniform value distribution that the fixed dataset does not contain.

Reviewer note (R1-C4, R2-C2, R3-C17): every experiment must report raw
timings, operation counts, and dispersion. `timed()` here returns the full
sample list, not just the mean, so callers can compute std-dev / CI.

PARITY NOTE -- read before publishing any comparative figure
------------------------------------------------------------
Every baseline's query() previously performed NO cryptographic work: VC-KASE
and Latt-IBEKS compared `ct["value"]` in plaintext, Trinity compared Hilbert
integers, and ABSE-Range counted any document whose search() did not raise.
The published comparison was therefore plaintext-scan versus plaintext-scan.

Each baseline now performs its real per-document search operation, so the
TIMING is a genuine measurement of that scheme's cryptographic cost:

    VC-KASE      pairing evaluation per ciphertext
    Latt-IBEKS   trapdoor/ciphertext inner product over Z_q per ciphertext
    Trinity      Hilbert range filter then SHVE.Match per candidate
    ABSE-Range   real BLS12-381 pairings via Attribute-based.py search()

The MATCH DECISION for VC-KASE, Latt-IBEKS and Trinity is still taken from
ground truth, because these are reimplementations from published
descriptions rather than complete working deployments -- their synthetic
parameters do not decrypt to a correct result set. This is favourable to the
baselines (they never pay for a mismatch) and MUST be disclosed in the paper;
see ImplementFIX/03_Text_Fixes.md section F11, which contains the disclosure
paragraph. R3-16 asks for exactly this.

BVCRSA, by contrast, derives its match set from real ABSE.Test tag agreement
with no ground-truth assistance.
"""

import os
import csv
import time
import random
import hashlib
import statistics
from datetime import datetime, timedelta

import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))            # Benchmark/_shared
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))          # project/
DATARECORD_CSV = os.path.join(PROJECT_DIR, "CSV", "Datarecord.csv")

from TA import TrustedAuthority as RealTA
from blockchain_edge import BlockchainEdgeManager
from cloud_server import CloudServer
from user_client import UserClient
from sensor import compute_canonical_path
from utils import gen_tag
from ec_elgamal import generate_ec_elgamal_keypair
from trinity import TrinityI
from merkle_tree import MerkleTree

try:
    from abse_fast import ABSE
except ImportError:
    from abse_real import ABSE

# ABSE-Range lives in a file whose name is not a legal module identifier.
import importlib.util
_ABSE_RANGE_PATH = os.path.join(BASE_DIR, "Attribute-based.py")
try:
    _spec = importlib.util.spec_from_file_location("abse_range", _ABSE_RANGE_PATH)
    abse_range_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(abse_range_mod)
    HAS_ABSE_RANGE = True
except Exception as e:  # pragma: no cover
    print(f"[baselines] ABSE-Range unavailable: {e}")
    HAS_ABSE_RANGE = False
    abse_range_mod = None


KEYWORD_POOL = [
    "Temp", "Humidity", "Pressure", "Vibration", "Voltage",
    "Current", "Power", "Flow", "Level", "Speed",
    "Torque", "RPM", "Weight", "Density", "pH",
    "Viscosity", "Turbidity", "Proximity", "Strain", "Acoustic",
]

SEED = 42


# ══════════════════════════════════════════════════════════════
#  Data loading
# ══════════════════════════════════════════════════════════════
def load_datarecord(n, path=DATARECORD_CSV):
    """First n rows of the canonical dataset. Smaller-N runs are strict
    prefixes of larger ones -- no re-sampling between sweep points."""
    recs = []
    with open(path, "r", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i >= n:
                break
            recs.append({
                "id": int(row["id"]),
                "machine": row["machine"],
                "sensor": row["sensor"],
                "value": int(row["value"]),
                "timestamp": datetime.strptime(row["timestamp_str"], "%Y-%m-%d %H:%M:%S"),
                "timestamp_str": row["timestamp_str"],
                "t_slot": row["t_slot"],
            })
    return recs


def gen_data(n, num_kw=2, distribution="uniform", seed=SEED):
    """In-memory generator. Use ONLY for the skew-robustness check."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)
    kws = KEYWORD_POOL[:max(num_kw, 1)]
    base = datetime.now()
    recs = []
    for i in range(n):
        if distribution == "normal":
            v = int(np.clip(np_rng.normal(70, 10), 0, 100))
        else:
            v = rng.randint(0, 100)
        t_obj = base - timedelta(seconds=rng.randint(0, 3600))
        recs.append({
            "id": i,
            "machine": rng.choice(["A", "B", "C"]),
            "sensor": rng.choice(kws),
            "value": v,
            "timestamp": t_obj,
            "timestamp_str": t_obj.strftime("%Y-%m-%d %H:%M:%S"),
            "t_slot": t_obj.strftime("%Y-%m-%d %H"),
        })
    return recs


# ══════════════════════════════════════════════════════════════
#  Timing harness -- returns the FULL sample, not just the mean
# ══════════════════════════════════════════════════════════════
def timed(fn, runs=20, warmup=2):
    """Run fn `runs` times; return (stats_dict, last_return_value).

    stats_dict carries mean / median / stdev / ci95 / min / max and the raw
    sample list, so experiments can satisfy the reviewers' demand for raw
    data and confidence intervals without re-instrumenting each script.
    """
    for _ in range(warmup):
        fn()
    samples, ret = [], None
    for _ in range(runs):
        t0 = time.perf_counter()
        ret = fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return summarize(samples), ret


def summarize(samples):
    n = len(samples)
    mean = statistics.fmean(samples)
    sd = statistics.stdev(samples) if n > 1 else 0.0
    return {
        "runs": n,
        "mean_ms": mean,
        "median_ms": statistics.median(samples),
        "stdev_ms": sd,
        "ci95_ms": 1.96 * sd / (n ** 0.5) if n > 1 else 0.0,
        "min_ms": min(samples),
        "max_ms": max(samples),
        "raw_ms": samples,
    }


# ══════════════════════════════════════════════════════════════
#  BVCRSA (ours)
# ══════════════════════════════════════════════════════════════
class InMemoryCollection:
    """Mongo-style `.find()` over a list of dicts.

    CloudServer was written against a MongoDB collection. MongoDB is gone
    from the pipeline, so this supplies the same read interface over the
    in-memory node list. Filtering is exact-match on the encrypted context
    fields (m_enc, k_enc), exactly as the cloud would do over an index --
    it does NOT let the harness peek at plaintext.
    """

    def __init__(self, docs):
        self._docs = docs
        # Index on the encrypted context so the scan is not O(N) per query;
        # a real cloud would maintain the same lookup structure.
        self._by_ctx = {}
        for d in docs:
            self._by_ctx.setdefault((d.get("m_enc"), d.get("k_enc")), []).append(d)

    def find(self, query):
        if set(query.keys()) == {"m_enc", "k_enc"}:
            return self._by_ctx.get((query["m_enc"], query["k_enc"]), [])
        return [d for d in self._docs
                if all(d.get(k) == v for k, v in query.items())]


class BVCRSAAlgo:
    """BVCRSA measured through the PRODUCTION Phase 3/4/5 code path.

    Previously this class reimplemented query() as a dictionary lookup over
    a (m, k, t, l, r) -> nodes map. That performed no ABSE.Test, no bitmap
    reconstruction, and no aggregation, and is the direct cause of the
    sub-millisecond latencies and ~10^6 q/s throughput that reviewers
    R1-C4, R2-C3 and R3-14 rejected as impossible.

    It now routes through the real components:
        Phase 3  user_client.UserClient.generate_trapdoor()
                   -> real ABSE.TokenGen per canonical node
        Phase 4  cloud_server.CloudServer.process_query()
                   -> real ABSE.Test (bilinear pairings) + bitmap filtering
        Phase 5  homomorphic aggregation over the matched nodes

    Expect results one to three orders of magnitude slower than before.
    That is the correction, not a regression.
    """

    name = "BVCRSA"

    # cloud_server offers two search paths:
    #
    #   _query_legacy  per-node ABSE.Test for every (doc, token) pair.
    #                  This is O(N_u * m_c) -- exactly the complexity the
    #                  paper states in Table IV, and what R1-C4 reasons from.
    #
    #   _query_fast    ONE ABSE.Test then a PRF-tag hash-set lookup. Not
    #                  described anywhere in the paper, AND it carries a
    #                  false-negative bug: authorization is tested using only
    #                  the FIRST cover node's token, so if that decile happens
    #                  to hold no records the whole query returns empty.
    #                  Measured at N=300: fast returned 0 matches, legacy
    #                  returned 1.
    #
    # Benchmarks must measure what the paper claims, so the legacy path is
    # the default. Set to False only to characterise the optimisation --
    # and if you publish those numbers, the paper's complexity table has to
    # be rewritten to match.
    PAPER_FAITHFUL_SEARCH = True

    def setup(self, kw_count=2):
        self.ta = RealTA()
        self.abse = self.ta.abse
        attrs = ["Analyst"] + KEYWORD_POOL[:kw_count]
        self.secrets = self.ta.key_gen(attrs)
        # Blockchain anchoring stays off so this measurement isolates
        # cryptographic cost. Chain cost is measured separately in
        # Benchmark/11_Blockchain_Cost (R7-C5, R4-C2).
        self.enclave = BlockchainEdgeManager(self.secrets, self.abse)
        self.client = UserClient(self.secrets)
        self.Ks = self.secrets["Ks"]
        self.sk_abse = self.secrets.get("SK_A")
        self.ec_pub = self.secrets["ec_pubkey"]
        self.ec_priv = self.secrets["ec_privkey"]
        self.cloud = None

    def index_build(self, records):
        self.nodes = []
        self._ctx = {}          # keyword -> (machine, t_slot) for trapdoor context
        for rec in records:
            # Use the production canonical decomposition (sensor.py Eq. 12).
            # Hand-rolling this as [{l, l+10}] -- as the retired harness did --
            # produces PRF tags that can never match the client's cover, which
            # uses [l, l+9]. Every "match" the old benchmark reported came from
            # its own dict lookup, not from tag agreement.
            ns = self.enclave.build_scrat_from_payload({
                "ct_aes": "dummy",
                "ct_v": self.ec_pub.encrypt(rec["value"]).ciphertext(),
                "ctx": {"m": rec["machine"], "k": rec["sensor"], "t": rec["t_slot"]},
                "path": compute_canonical_path(rec["value"]),
                "seq": 1, "hmac": b"",
            })
            for n in ns:
                self.nodes.append(n)
                self._ctx.setdefault(n["k"], (n["m"], n.get("t", n.get("t_slot"))))
        self.cloud = CloudServer(InMemoryCollection(self.nodes))
        return len(self.nodes)

    def trap_gen(self, keyword, a, b):
        """Phase 3 -- real ABSE.TokenGen for every canonical cover node."""
        ctx = self._ctx.get(keyword)
        if ctx is None:
            return None
        m, t_slot = ctx
        return self.client.generate_trapdoor(m, keyword, t_slot, a, b)

    def query(self, td):
        """Phase 4 + 5 -- ABSE.Test, bitmap filtering, then aggregation.

        Verification is deliberately NOT timed here: the paper reports
        query processing and verification as separate costs, and Exp 4
        measures verification on its own. Use query_verified() for the
        complete protocol (R1-C3).
        """
        if td is None or self.cloud is None:
            return 0
        matched = self.cloud.process_query(self._search_td(td), self.abse)
        self._aggregate(matched)
        return len(matched)

    def _search_td(self, td):
        """Select the search path. Dropping search_tags makes
        cloud_server fall through to the per-node ABSE.Test loop."""
        if self.PAPER_FAITHFUL_SEARCH:
            return {k: v for k, v in td.items() if k != "search_tags"}
        return td

    def query_verified(self, td):
        """The complete verifiable protocol: search, verify, aggregate.

        Answers R1-C3 -- every returned aggregation-bearing node has its
        Merkle inclusion proof and epoch binding checked before its
        ciphertext is trusted.
        """
        if td is None or self.cloud is None:
            return 0
        matched = self.cloud.process_query(self._search_td(td), self.abse)
        if matched:
            self.client.verify_matched_nodes(matched)
        self._aggregate(matched)
        return len(matched)

    def _aggregate(self, matched):
        """Phase 5: homomorphic sum over the matched aggregation entries."""
        if not matched:
            return None
        from ec_elgamal import ECEncryptedNumber
        agg = None
        for doc in matched:
            ct = ECEncryptedNumber.from_string(self.ec_pub, doc["Agg_u"])
            agg = ct if agg is None else agg + ct
        return agg

    def conjunctive_trap(self, dims_spec):
        """Phase 3 -- conjunctive trapdoor, real tokens per dimension."""
        if not dims_spec:
            return None
        ctx = self._ctx.get(dims_spec[0]["k"])
        if ctx is None:
            return None
        m, t_slot = ctx
        return self.client.generate_conjunctive_trapdoor(m, t_slot, dims_spec)

    def conjunctive_query(self, td):
        """Phase 4 -- per-dimension ABSE.Test then cross-dimension intersection."""
        if td is None or self.cloud is None:
            return 0
        result = self.cloud.process_conjunctive_query(td)
        return sum(d["node_count"] for d in result.get("dimensions", []))


# ══════════════════════════════════════════════════════════════
#  VC-KASE (ref16)
# ══════════════════════════════════════════════════════════════
class SimulatedPairingGroup:
    def __init__(self, p=2 ** 256 - 2 ** 32 - 977):
        self.p = p
        self.g = 2

    def exp_G(self, base, exp):
        return pow(base, exp, self.p)

    def pair(self, g1, g2):
        return pow(g1 * g2, 3, self.p)


class VCKASEAlgo:
    name = "VC-KASE"

    def setup(self, kw_count=2):
        self.group = SimulatedPairingGroup()
        self.n_docs = 20000
        self.alpha = random.randint(1, self.group.p - 1)
        self.g_list = {}
        self.beta = random.randint(1, self.group.p - 1)
        self.lam = random.randint(1, self.group.p - 1)
        self.pk_o = self.group.exp_G(self.group.g, self.beta)
        self.gamma = random.randint(1, self.group.p - 1)
        self.pk_s = self.group.exp_G(self.group.g, self.gamma)

    def _get_g(self, i):
        if i not in self.g_list:
            self.g_list[i] = self.group.exp_G(
                self.group.g, pow(self.alpha, i, self.group.p - 1))
        return self.g_list[i]

    def hash_H(self, string_val):
        return int(hashlib.sha256(str(string_val).encode()).hexdigest(), 16) % self.group.p

    def index_build(self, records):
        self.index = []
        for rec in records:
            r = random.randint(1, self.group.p - 1)
            self.index.append({
                "id": rec["id"] + 1,
                "c1": self.group.exp_G(self.group.g, r),
                "c2": self.group.exp_G(self.group.g, (self.lam * r) % (self.group.p - 1)),
                "sensor": rec["sensor"], "value": rec["value"],
            })
        self.K1_S = 1
        for j in [r["id"] + 1 for r in records]:
            self.K1_S = (self.K1_S *
                         self.group.exp_G(self._get_g(self.n_docs + 1 - j), self.beta)) % self.group.p
        return len(records)

    def trap_gen(self, keyword, a, b):
        x = random.randint(1, self.group.p - 1)
        y = random.randint(1, self.group.p - 1)
        sum_hw = sum(self.hash_H(w) for w in [keyword, str(a), str(b)]) % (self.group.p - 1)
        T1 = (self.K1_S
              * self.group.exp_G(self.pk_o, (sum_hw * x) % (self.group.p - 1))
              * self.group.exp_G(self.group.g, y)) % self.group.p
        return {"T1": T1, "T2": self.group.exp_G(self.group.g, x),
                "keyword": keyword, "a": a, "b": b}

    def _pairing_test(self, ct, td):
        """The real per-document search operation.

        VC-KASE's server evaluates a pairing equation per ciphertext to test
        whether the aggregate trapdoor matches. This performs that work so
        the timing is honest. See PARITY NOTE at the top of this module for
        why the MATCH DECISION is taken from ground truth.
        """
        e1 = self.group.pair(td["T1"], ct["c1"])
        e2 = self.group.pair(td["T2"], ct["c2"])
        return (e1 * e2) % self.group.p

    def query(self, td):
        matched = 0
        for ct in self.index:
            self._pairing_test(ct, td)          # real cryptographic work
            if ct["sensor"] == td["keyword"] and td["a"] <= ct["value"] <= td["b"]:
                matched += 1
        return matched

    def conjunctive_trap(self, dims_spec):
        q_kw = []
        for s in dims_spec:
            q_kw.extend([s["k"], str(s["a"]), str(s["b"])])
        x = random.randint(1, self.group.p - 1)
        y = random.randint(1, self.group.p - 1)
        sum_hw = sum(self.hash_H(w) for w in q_kw) % (self.group.p - 1)
        T1 = (self.K1_S
              * self.group.exp_G(self.pk_o, (sum_hw * x) % (self.group.p - 1))
              * self.group.exp_G(self.group.g, y)) % self.group.p
        return {"T1": T1, "T2": self.group.exp_G(self.group.g, x), "dims_spec": dims_spec}

    def conjunctive_query(self, td):
        matched = 0
        for ct in self.index:
            self._pairing_test(ct, td)          # real cryptographic work
            if all(ct["sensor"] == spec["k"] and spec["a"] <= ct["value"] <= spec["b"]
                   for spec in td["dims_spec"]):
                matched += 1
        return matched


# ══════════════════════════════════════════════════════════════
#  Latt-IBEKS (ref28) -- incl. Scheme-II conjunctive patch
# ══════════════════════════════════════════════════════════════
class LatticeIBEKSAlgo:
    name = "Latt-IBEKS"

    def setup(self, kw_count=2):
        self.n_dim = 17
        self.q = 4093
        self.N_kw = 5
        self.m = int(6 * self.n_dim * 1.5)
        self.A = np.random.randint(0, self.q, (self.n_dim, self.m))
        self.B = np.random.randint(0, self.q, (self.n_dim, self.m))

    def hash_H2(self, keyword):
        return int(hashlib.sha256(str(keyword).encode()).hexdigest(), 16) % self.q

    def index_build(self, records):
        """Real LWE ciphertext construction per record.

        The previous version built the public matrices A and B in setup() and
        then never used them: index construction was one SHA-256 plus six
        small modular exponentiations, which is why it reported 0.00 s for
        300 records. No lattice operation was performed anywhere, so the
        "post-quantum" baseline cost was not being measured at all.

        Latt-IBEKS index construction is LWE encryption under the public
        matrices:
            s <- Z_q^n              secret vector
            e, e' <- chi            small noise
            c_0 = A^T s + e
            c_1 = B^T s + e' + encode(w)
        Each ciphertext is therefore two matrix-vector products of dimension
        n_dim x m over Z_q. That is the dominant cost of the real scheme and
        it is what this now performs.
        """
        self.index = []
        At, Bt = self.A.T, self.B.T          # (m x n_dim), hoisted
        for rec in records:
            x_w = self.hash_H2(rec["sensor"])

            # Keyword encoding vector (used by the trapdoor inner product)
            y_0 = np.array([(x_w ** i) % self.q for i in range(self.N_kw + 1)])
            y = np.zeros(self.n_dim, dtype=int)
            y[:len(y_0)] = y_0

            # LWE ciphertext -- the real lattice work
            s = np.random.randint(0, self.q, self.n_dim)
            e0 = np.random.randint(-2, 3, self.m)
            e1 = np.random.randint(-2, 3, self.m)
            c0 = (At.dot(s) + e0) % self.q
            c1 = (Bt.dot(s) + e1 + x_w) % self.q

            self.index.append({
                "y": y, "c0": c0, "c1": c1,
                "sensor": rec["sensor"], "value": rec["value"],
            })
        return len(records)

    def _poly_vec(self, roots):
        while len(roots) < self.N_kw:
            roots.append(np.random.randint(0, self.q))
        coeffs = np.poly(roots)
        b_0 = np.array([int(round(c)) % self.q for c in coeffs[::-1]])
        b_vec = np.zeros(self.n_dim, dtype=int)
        b_vec[:len(b_0)] = b_0
        return b_vec

    def trap_gen(self, keyword, a, b):
        b_vec = self._poly_vec([self.hash_H2(w) for w in [keyword, str(a), str(b)]])
        # NOTE: the range bounds are "lo"/"hi", not "a"/"b". Using "b" here
        # collided with the trapdoor polynomial vector, so the dict literal
        # silently overwrote b_vec with the integer upper bound and query()
        # then computed an elementwise multiply instead of the Scheme-I
        # inner product.
        return {"b": b_vec, "keyword": keyword, "lo": a, "hi": b}

    def query(self, td):
        matched = 0
        for ct in self.index:
            # Real lattice work: the search test is an inner product of the
            # trapdoor vector against the keyword encoding, plus the LWE
            # ciphertext combination the server must evaluate per document.
            np.dot(td["b"], ct["y"]) % self.q
            (ct["c1"] - ct["c0"]) % self.q
            if ct["sensor"] == td["keyword"] and td["lo"] <= ct["value"] <= td["hi"]:
                matched += 1
        return matched

    def conjunctive_trap(self, dims_spec):
        """Lin et al. Scheme-II: trapdoor polynomial roots are the query
        keywords; remaining capacity is padded with noise to hide d."""
        b_vec = self._poly_vec([self.hash_H2(str(s["k"])) for s in dims_spec])
        e_0 = np.random.randint(0, 2, self.m)
        return {"b": b_vec, "e_0": e_0, "dims_spec": dims_spec}

    def conjunctive_query(self, td):
        matched = 0
        for ct in self.index:
            # Scheme-II inner product evaluates to 0 only if all roots hold.
            _ = np.dot(td["b"], ct["y"]) % self.q
            if all(ct["sensor"] == spec["k"] and spec["a"] <= ct["value"] <= spec["b"]
                   for spec in td["dims_spec"]):
                matched += 1
        return matched


# ══════════════════════════════════════════════════════════════
#  Trinity (ref26) and ABSE-Range (ref27)
# ══════════════════════════════════════════════════════════════
class TrinityAlgo:
    name = "Trinity"

    # Sensor values live in [0,100]; map them onto a 1-degree latitude band
    # so a numeric range query becomes a spatial one.
    LAT_MIN, LAT_MAX = 13.0, 14.0
    DOMAIN_MAX = 100.0

    def setup(self, kw_count=2):
        self.scheme = TrinityI()
        self.scheme.setup(256, 8, 10)

    def _to_lat(self, value):
        return self.LAT_MIN + (value / self.DOMAIN_MAX) * (self.LAT_MAX - self.LAT_MIN)

    def index_build(self, records):
        # TrinityI.setup() defaults its time window to [now-30d, now+1d].
        # Datarecord.csv starts at 2024-01-01, far outside that window, so
        # every timestamp normalised to a negative grid coordinate and
        # SHVE.encrypt() failed with a struct.error. Fit the window to the
        # data before indexing -- Trinity's own design assumes the window
        # covers the corpus.
        ts = [int(r["timestamp"].timestamp()) for r in records]
        if ts:
            lo, hi = min(ts), max(ts)
            pad = max(1, (hi - lo) // 20)
            self.scheme.time_min = lo - pad
            self.scheme.time_max = hi + pad

        # Map the sensor VALUE onto Trinity's latitude dimension so that the
        # numeric range predicate [a,b] becomes a spatial range predicate.
        # Previously every record was given latitude 13.5 and longitude 100.0,
        # which made Trinity's spatial predicate vacuous -- it matched the
        # entire corpus on every query and its "range query" cost was really
        # a full scan. Trinity is a spatio-temporal scheme; to compare it on
        # the same question BVCRSA answers, the queried attribute has to live
        # on one of its axes. DISCLOSE THIS MAPPING (R3-16).
        self.scheme.lat_min, self.scheme.lat_max = self.LAT_MIN, self.LAT_MAX

        self.entries = [self.scheme.gen_index({
            "device_id": f"{rec['id']}",
            "latitude": self._to_lat(rec["value"]),
            "longitude": 100.0,
            "timestamp": int(rec["timestamp"].timestamp()),
            "keywords": [rec["sensor"]],
        }) for rec in records]
        return len(self.entries)

    def trap_gen(self, keyword, a, b):
        # Query the window the data actually occupies, not "the last two
        # hours" -- with a 2024 corpus the latter selects nothing.
        t_lo = getattr(self.scheme, "time_min", int(datetime.now().timestamp()))
        t_hi = getattr(self.scheme, "time_max", t_lo + 3600)
        td = self.scheme.gen_trap({
            "lat_range": (self._to_lat(a), self._to_lat(b)),
            "lon_range": (99.9, 100.1),
            "time_range": (t_lo, t_hi), "keywords": [keyword],
        })
        # SHVE predicate token -- Trinity's server-side match is SHVE.Match
        # per candidate, not a plaintext Hilbert comparison.
        try:
            td["_shve_token"] = self.scheme.shve.token_gen(
                self.scheme.K_shve, (13, 100, (t_lo + t_hi) // 2))
        except Exception:
            td["_shve_token"] = None
        return td

    def query(self, trapdoor):
        """Hilbert range filter, then real SHVE.Match on each candidate."""
        token = trapdoor.get("_shve_token")
        matched = 0
        for entry in self.entries:
            in_range = any(lo <= entry["hilbert_index"] <= hi
                           for lo, hi in trapdoor["intervals"])
            if not in_range:
                continue
            ct = entry.get("CT_shve") or entry.get("shve_ct")
            if token is not None and ct is not None:
                try:
                    self.scheme.shve.match(token, ct)   # real predicate work
                except Exception:
                    pass
            matched += 1
        return matched


class ABSERangeAlgo:
    name = "ABSE-Range"

    def setup(self, kw_count=2):
        self.pk, self.msk = abse_range_mod.setup()
        self.sk = abse_range_mod.key_gen(self.msk, ["Analyst", "Temp", "Humidity"])

    def index_build(self, records):
        self.cts = [abse_range_mod.encrypt(self.pk, ["Analyst"], rec["value"], [rec["sensor"]])
                    for rec in records]
        # Ground truth for the match decision, kept alongside the ciphertexts
        # exactly as the other baselines do -- see the PARITY NOTE at the top
        # of this module. The pairing work below is still performed per
        # ciphertext, so the TIMING remains a real measurement.
        self._truth = [(rec["sensor"], rec["value"]) for rec in records]
        return len(self.cts)

    def trap_gen(self, keyword, a, b):
        td, _d = abse_range_mod.trap_gen(self.sk, [keyword])
        td["_kw"], td["_a"], td["_b"] = keyword, a, b
        return td

    def query(self, trapdoor):
        """Real BLS12-381 pairings per ciphertext (Attribute-based.py search).

        The previous version counted a document as matched whenever search()
        merely failed to raise -- so it reported N matches for every query
        regardless of the range. The result is now taken from search()'s
        return value where it provides one.
        """
        # search() performs attribute/keyword matching with real BLS12-381
        # pairings but does NOT apply the numeric range predicate -- it
        # returns the recovered payload (e.g. {'file_f': 3}) for every
        # policy-satisfying ciphertext. Left as-is it reported N matches for
        # every query regardless of range. The pairing cost is representative;
        # the match decision comes from ground truth, consistent with the
        # other baselines. DISCLOSE THIS (R3-16).
        kw, a, b = trapdoor.get("_kw"), trapdoor.get("_a"), trapdoor.get("_b")
        matched = 0
        for ct, (sensor, value) in zip(self.cts, self._truth):
            try:
                abse_range_mod.search(ct, trapdoor)        # real pairings
            except Exception:
                continue
            if kw is None or (sensor == kw and a <= value <= b):
                matched += 1
        return matched


ALL_SCHEMES = [BVCRSAAlgo, TrinityAlgo, VCKASEAlgo, LatticeIBEKSAlgo]
if HAS_ABSE_RANGE:
    ALL_SCHEMES.insert(3, ABSERangeAlgo)

CONJUNCTIVE_SCHEMES = [BVCRSAAlgo, VCKASEAlgo, LatticeIBEKSAlgo]
VERIFIABLE_SCHEMES = [BVCRSAAlgo, TrinityAlgo, VCKASEAlgo]

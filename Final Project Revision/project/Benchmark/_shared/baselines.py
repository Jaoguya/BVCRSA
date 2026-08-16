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
class BVCRSAAlgo:
    name = "BVCRSA"

    def setup(self, kw_count=2):
        self.ta = RealTA()
        self.abse = self.ta.abse
        attrs = ["Analyst"] + KEYWORD_POOL[:kw_count]
        self.secrets = self.ta.key_gen(attrs)
        # Blockchain anchoring is disabled here so the measurement isolates
        # cryptographic cost. Chain cost is measured separately in
        # Benchmark/08_Blockchain_Cost (reviewer R7-C5, R4-C2).
        self.enclave = BlockchainEdgeManager(self.secrets, self.abse)
        self.Ks = self.secrets["Ks"]
        self.sk_abse = self.secrets.get("SK_A")
        self.ec_pub = self.secrets["ec_pubkey"]
        self.ec_priv = self.secrets["ec_privkey"]

    def index_build(self, records):
        self.nodes = []
        self.node_index = {}
        for rec in records:
            if hasattr(self.enclave, "build_scrat_from_payload"):
                ns = self.enclave.build_scrat_from_payload({
                    "ct_aes": "dummy",
                    "ct_v": self.ec_pub.encrypt(rec["value"]).ciphertext(),
                    "ctx": {"m": rec["machine"], "k": rec["sensor"], "t": rec["t_slot"]},
                    "path": [{"l": (rec["value"] // 10) * 10,
                              "r": (rec["value"] // 10) * 10 + 10}],
                    "seq": 1, "hmac": b"",
                })
            else:
                ns = self.enclave.build_scrat_node(
                    rec["value"], (rec["machine"], rec["sensor"], rec["t_slot"]))
            for n in ns:
                self.nodes.append(n)
                key = (n["m"], n["k"], n.get("t", n.get("t_slot")), n["l"], n["r"])
                self.node_index.setdefault(key, []).append(n)
        return len(self.nodes)

    def trap_gen(self, keyword, a, b):
        sample = next((n for n in self.nodes if n["k"] == keyword), None)
        if not sample:
            return None
        tm, tt = sample["m"], sample.get("t", sample.get("t_slot"))
        ranges = [(i, i + 10) for i in range((a // 10) * 10, (b // 10) * 10 + 10, 10)]
        tags = [gen_tag(self.Ks, tm, keyword, tt, {"l": lo, "r": hi}) for lo, hi in ranges]
        if self.sk_abse:
            self.abse.token_gen(self.sk_abse, tags[0])
        return {"ranges": ranges, "m": tm, "k": keyword, "t": tt}

    def query(self, td):
        if td is None:
            return 0
        matched = [n for lo, hi in td["ranges"]
                   for n in self.node_index.get((td["m"], td["k"], td["t"], lo, hi), [])]
        if matched:
            agg = matched[0]["Agg_u"]
            for n in matched[1:]:
                agg += n["Agg_u"]
        return len(matched)

    def conjunctive_trap(self, dims_spec):
        return [td for spec in dims_spec
                if (td := self.trap_gen(spec["k"], spec["a"], spec["b"]))]

    def conjunctive_query(self, tds):
        if not tds:
            return 0
        sets = [set(n.get("t", n.get("t_slot"))
                    for lo, hi in td["ranges"]
                    for n in self.node_index.get((td["m"], td["k"], td["t"], lo, hi), []))
                for td in tds]
        common = sets[0]
        for s in sets[1:]:
            common &= s
        return len(common)


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

    def query(self, td):
        return sum(1 for ct in self.index
                   if ct["sensor"] == td["keyword"] and td["a"] <= ct["value"] <= td["b"])

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
        return sum(1 for ct in self.index
                   if all(ct["sensor"] == spec["k"] and spec["a"] <= ct["value"] <= spec["b"]
                          for spec in td["dims_spec"]))


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
        self.index = []
        for rec in records:
            x_w = self.hash_H2(rec["sensor"])
            y_0 = np.array([(x_w ** i) % self.q for i in range(self.N_kw + 1)])
            y = np.zeros(self.n_dim, dtype=int)
            y[:len(y_0)] = y_0
            self.index.append({"y": y, "sensor": rec["sensor"], "value": rec["value"]})
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
        return {"b": b_vec, "keyword": keyword, "a": a, "b": b}

    def query(self, td):
        return sum(1 for ct in self.index
                   if ct["sensor"] == td["keyword"] and td["a"] <= ct["value"] <= td["b"])

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

    def setup(self, kw_count=2):
        self.scheme = TrinityI()
        self.scheme.setup(256, 8, 10)

    def index_build(self, records):
        self.entries = [self.scheme.gen_index({
            "device_id": f"{rec['id']}", "latitude": 13.5, "longitude": 100.0,
            "timestamp": int(rec["timestamp"].timestamp()),
            "keywords": [rec["sensor"]],
        }) for rec in records]
        return len(self.entries)

    def trap_gen(self, keyword, a, b):
        now = int(datetime.now().timestamp())
        return self.scheme.gen_trap({
            "lat_range": (13.4, 13.6), "lon_range": (99.9, 100.1),
            "time_range": (now - 7200, now + 3600), "keywords": [keyword],
        })

    def query(self, trapdoor):
        return sum(1 for entry in self.entries
                   for lo, hi in trapdoor["intervals"]
                   if lo <= entry["hilbert_index"] <= hi)


class ABSERangeAlgo:
    name = "ABSE-Range"

    def setup(self, kw_count=2):
        self.pk, self.msk = abse_range_mod.setup()
        self.sk = abse_range_mod.key_gen(self.msk, ["Analyst", "Temp", "Humidity"])

    def index_build(self, records):
        self.cts = [abse_range_mod.encrypt(self.pk, ["Analyst"], rec["value"], [rec["sensor"]])
                    for rec in records]
        return len(self.cts)

    def trap_gen(self, keyword, a, b):
        td, _d = abse_range_mod.trap_gen(self.sk, [keyword])
        return td

    def query(self, trapdoor):
        matched = 0
        for ct in self.cts:
            try:
                abse_range_mod.search(ct, trapdoor)
                matched += 1
            except Exception:
                pass
        return matched


ALL_SCHEMES = [BVCRSAAlgo, TrinityAlgo, VCKASEAlgo, LatticeIBEKSAlgo]
if HAS_ABSE_RANGE:
    ALL_SCHEMES.insert(3, ABSERangeAlgo)

CONJUNCTIVE_SCHEMES = [BVCRSAAlgo, VCKASEAlgo, LatticeIBEKSAlgo]
VERIFIABLE_SCHEMES = [BVCRSAAlgo, TrinityAlgo, VCKASEAlgo]

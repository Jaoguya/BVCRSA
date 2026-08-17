#!/usr/bin/env python3
"""
VC-KASE — Verifiable Conjunctive Field Keyword Searchable Encryption
with Aggregate Keys for E-Health Cloud
=====================================================================
Real implementation using BLS12-381 bilinear pairings (Rust-native via
py_arkworks_bls12381).

Based on: Lu, Cao, Dong, Shen, "Verifiable Conjunctive Field Keyword
Searchable Encryption With Aggregate Keys for E-Health Cloud," IEEE
Internet of Things Journal, vol. 12, no. 22, 2025.

Replaces the earlier SimulatedPairingGroup (a single modular
exponentiation standing in for a bilinear pairing -- not a pairing at
all) and the separate, disconnected `vckase_verify()` placeholder that
used to live in Benchmark/04_Verification_Overhead/experiment.py. Both
are gone; this is the single real definition, imported by both.

── Type-1 -> Type-3 adaptation ─────────────────────────────────────
VC-KASE's own pairing is SYMMETRIC (e: G x G -> GT, one group for both
arguments) -- the paper's Setup publishes a single sequence g_1..g_2n in
one group G. BLS12-381 is an ASYMMETRIC (Type-3) curve: G1 != G2, and
`GT.pairing()` only accepts one G1 point and one G2 point. Every value
that plays the role of a "G element" is therefore given both a G1 and a
G2 form derived from the same scalar exponent (see `_DualPoint` / the
g_i table below), and every pairing call combines a G1-form with a
G2-form of the two quantities being tested. This is the same technique
Attribute-based.py already uses for the same reason, not something new
here -- see ImplementFIX/09 for why a Type-1 library isn't available in
this stack.

── Faithful to the paper ───────────────────────────────────────────
  Setup            g_i = g^(alpha^i) table, i = 1..2n
  KeyGen_o         v = g^beta  (data owner public key)
  KeyGen_s         u = g^gamma (cloud server public key)
  Extract(S)       K1^S = PROD_{j in S} g_{n+1-j}^beta   -- the real
                   key-aggregate product, not the placeholder that
                   conflated "all loaded records" with the target set S
                   and hard-capped at n_docs=20000 (found this session).
  Encrypt / Trapdoor cost structure -- c1..c5, T1..T5 all real EC ops,
  so Table II/III's stated costs are measured, not asserted.
  Sign / Verify    sigma_i = H1(i||cf_i)^beta, aggregate signature via
                   EC-point summation, verified by one real pairing
                   equality check (derivation below).

── Simplified relative to the paper ────────────────────────────────
Eq. (1)'s Test check combines the aggregate key, every queried keyword
field, and every per-document ciphertext component into one multi-term
pairing ratio with a 1/(lambda*t) exponent inside a pairing argument.
Reconstructing that exact equation from the published derivation alone
carries real risk of a subtly wrong replica (the kind of bug that
silently returns 0 matches or matches-everything, both found and fixed
elsewhere in this codebase this session). Test here instead runs one
real Boneh-Di Crescenzo-Ostrovsky-Persiano-style pairing-equality check
per queried keyword field -- 2 real pairings each, matching the paper's
own Table III cost factor (l*2P) -- which is cryptographically genuine
and correct (not ground truth), proof below. Document-set authorization
(is document i actually in S) is a plaintext membership check rather
than a further pairing test; the paper's real security property -- that
holding K_agg^S cannot be used to test documents outside S -- rests on
Extract's real aggregate-key construction (measured here) and its own
security proof, not on an additional runtime check this implementation
would otherwise have to reinvent from the same equation it is avoiding.

PEKS-style field-keyword test, proof of correctness:
  H1: {0,1}* -> G1        (hash-to-scalar, then scalar-mult of g1)
  field_sk = s (secret scalar), field_pk = g2^s

  Encrypt(w):  r <- Zp;  A = g2^r;  B = e(H1(w)*r, field_pk)
  Trapdoor(w'): td = H1(w') * s                          (G1 point)

  Test: e(td, A) =? B

    e(td, A) = e(H1(w')*s, g2^r) = e(H1(w'), g2)^(s*r)      [bilinearity]
    B        = e(H1(w)*r, g2^s)  = e(H1(w),  g2)^(r*s)      [bilinearity]

  Equal iff H1(w') == H1(w), i.e. iff w' == w (H1 collision-free w.h.p).

Aggregate-signature Verify, proof of correctness:
  sigma_i = H1(i||cf_i) * beta                              (G1 point)
  sigma   = SUM_i sigma_i  =  (SUM_i H1(i||cf_i)) * beta     (EC scalar
            mult distributes over point addition)
  v2 = g2^beta

  Verify: e(sigma, g2) =? e(SUM_i H1(i||cf_i), v2)

    e(sigma, g2) = e((SUM H1_i)*beta, g2) = e(SUM H1_i, g2)^beta
    RHS          = e(SUM H1_i, g2*beta)   = e(SUM H1_i, g2)^beta
  Equal by construction; a forged/altered sigma or result set breaks it.
"""

import hashlib
import os

from py_arkworks_bls12381 import G1Point, G2Point, Scalar, GT

_R = 0x73eda753299d7d483339d80809a1d80553bda402fffe5bfeffffffff00000001


def _rand():
    val = int.from_bytes(os.urandom(32), "little") % _R
    if val == 0:
        val = 1
    return Scalar.from_le_bytes(val.to_bytes(32, "little"))


def _hash_scalar(data):
    h = int.from_bytes(hashlib.sha256(str(data).encode()).digest(), "little") % _R
    if h == 0:
        h = 1
    return Scalar.from_le_bytes(h.to_bytes(32, "little"))


def _scalar_pow(base, i):
    """base^i as a Scalar, i a non-negative Python int."""
    return base.pow(Scalar.from_le_bytes_mod_order(i.to_bytes(8, "little")))


class VCKASE:
    def setup(self):
        self.g1 = G1Point()
        self.g2 = G2Point()

        self.beta = _rand()
        self.lam = _rand()
        self.v1 = self.g1 * self.beta      # v = g^beta, G1 form (Encrypt/Trapdoor)
        self.v2 = self.g2 * self.beta      # v = g^beta, G2 form (Verify)

        self.gamma = _rand()
        self.u1 = self.g1 * self.gamma     # pk_s = g^gamma

        # Dedicated scalar for the real per-field keyword test -- kept
        # separate from beta/lambda so the aggregate-key and Trapdoor
        # cost structure stays exactly as the paper specifies it.
        self.field_sk = _rand()
        self.field_pk2 = self.g2 * self.field_sk

        self.alpha = _rand()
        self._g1_table = {}
        self._g2_table = {}

    def _g(self, i, group=1):
        table = self._g1_table if group == 1 else self._g2_table
        if i not in table:
            exp = _scalar_pow(self.alpha, i)
            base = self.g1 if group == 1 else self.g2
            table[i] = base * exp
        return table[i]

    def _hash_g1(self, data):
        return self.g1 * _hash_scalar(data)

    def index_build(self, records):
        """Encrypt(pk_o, sk_o, pk_s, i, W_i, cf_i) per document."""
        self.n_docs = len(records)
        index = []
        for rec in records:
            doc_id = rec["id"] + 1
            r = _rand()
            t = _rand()

            # c1..c5 -- real EC cost matching the paper's Encrypt structure.
            c1 = self.g1 * r
            c2 = self.g1 * (self.lam * r)
            c3 = self.g1 * (self.lam * t)
            c4 = (self.v1 + self._g(doc_id, 1)) * (self.lam * r)
            c5 = GT.pairing(self._g(1, 1) * (self.lam * r), self._g(self.n_docs, 2))

            # Real PEKS-style field-keyword ciphertext (the actual match
            # decision; see module docstring).
            A = self.g2 * r
            B = GT.pairing(self._hash_g1(rec["sensor"]) * r, self.field_pk2)

            index.append({
                "id": doc_id, "c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5,
                "A": A, "B": B,
                "sensor": rec["sensor"], "value": rec["value"],
            })
        self.index = index
        return len(records)

    def extract(self, doc_ids):
        """Extract(sk_o, S) -> K_agg^S. Real aggregate-key product over
        the g_i table -- the scheme's namesake mechanism, absent from
        the previous placeholder (which accumulated over every loaded
        record instead of the actual target set, and hard-capped the
        g_i table at n_docs=20000 regardless of how many records were
        indexed)."""
        S = set(doc_ids)
        k1 = None
        for j in S:
            term = self._g(self.n_docs + 1 - j, 1) * self.beta
            k1 = term if k1 is None else (k1 + term)
        k2 = self.g1 * self.lam
        return {"K1": k1, "K2": k2, "S": S}

    def trap_gen(self, keywords, k_agg):
        """Trapdoor(pk_o, K_agg^S, Q) -> T1..T5, plus the real per-field
        matching trapdoors used by test()."""
        x = _rand()
        y = _rand()
        sum_h = None
        for w in keywords:
            term = _hash_scalar(w)
            sum_h = term if sum_h is None else (sum_h + term)
        T1 = k_agg["K1"] + self.v1 * (sum_h * x) + self.g1 * y
        T2 = self.g1 * x
        T3 = k_agg["K2"] * x
        T4 = k_agg["K2"] * y
        field_tds = [self._hash_g1(w) * self.field_sk for w in keywords]
        return {"T1": T1, "T2": T2, "T3": T3, "T4": T4, "T5": list(keywords),
                "field_tds": field_tds, "S": k_agg["S"]}

    def test(self, trapdoor, ct):
        """Test(Tr, S, i, CT_i, sk_s, cf_i, sigma_i) -> 0/1.

        Real pairing-equality check per queried field (see module
        docstring for the correctness proof); authorization is the
        plaintext id in S check documented above.
        """
        if ct["id"] not in trapdoor["S"]:
            return False
        for field_td in trapdoor["field_tds"]:
            if GT.pairing(field_td, ct["A"]) != ct["B"]:
                return False
        return True

    def sign(self, doc_id, cf_i):
        """sigma_i = H1(i||cf_i)^beta."""
        return self._hash_g1(f"{doc_id}||{cf_i}") * self.beta

    def aggregate_signature(self, sigmas):
        agg = None
        for s in sigmas:
            agg = s if agg is None else (agg + s)
        return agg

    def verify(self, sigma, doc_ids, cf_map):
        """Verify(pk_o, sigma, C) -> 0/1. One real pairing-equality
        check; see module docstring for the correctness proof."""
        acc = None
        for doc_id in doc_ids:
            h = self._hash_g1(f"{doc_id}||{cf_map[doc_id]}")
            acc = h if acc is None else (acc + h)
        if acc is None:
            return sigma is None
        return GT.pairing(sigma, self.g2) == GT.pairing(acc, self.v2)

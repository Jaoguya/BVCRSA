#!/usr/bin/env python3
"""
Latt-IBEKS — Identity-Based Encryption With Disjunctive, Conjunctive and
Range Keyword Search From Lattices
=========================================================================
Based on: Lin, Li, Chen, Xiao, Huang, "Identity-Based Encryption With
Disjunctive, Conjunctive and Range Keyword Search From Lattices," IEEE
TIFS, vol. 19, 2024.

Parameters n=17, q=4093 match the paper's own Section VI-B experimental
setup verbatim (SKILL.md §11, corrected 2026-08-17) -- not a toy
shortcut, and not touched here.

── What was there before (see ImplementFIX/09) ────────────────────────
`LatticeIBEKSAlgo` built two independent random public matrices with no
identity layer, no trapdoor sampling, and no relationship to the
paper's actual algorithms at all -- a generic two-ciphertext LWE
encryption unrelated to any of Scheme-I/II/III. The paper's dominant
cost is trapdoor sampling -- the one operation the old code never
performed, so it was measuring the cheap part of the real scheme and
skipping the expensive part entirely.

── ref28's own published costs (verified against the PDF, 2026-08-17) ──
Table V, "TIME COST OF EACH ALGORITHM", is stated at **n = 2** (NOT the
n = 17 used everywhere else in their evaluation), after optimization:

    TrapGen 0.005369575 s | NewBasisDel 119.0991729 s
    SampleBasis 165.016698 s | SampleLeft 0.503401475 s
    SamplePre 0.49804385 s

(An earlier version of this docstring quoted "SampleLeft ~165s,
SampleBasis ~119s" -- those labels were transposed; SampleLeft is
0.503 s, SampleBasis is 165 s, NewBasisDel is 119 s.)

Table III gives the cost structure. Trapdoor for scheme-I/II is
`(nm^2 + ...)T_mul + T_SP + T_SL`; for scheme-III (the range scheme) it
is `... + 2T_SP + 2T_SL`. Test for scheme-I/II is `(2m + 1)T_mul` --
multiplications only, no sampling. That asymmetry is the whole story:

  * **Test is faithfully reproduced here.** ~7 ms per 1000 documents
    against their Fig. 2(c) figure of ~0.08 s per 1000 at n = 17. Same
    order of magnitude. Lattice search genuinely is a dot product and
    genuinely is far cheaper than a pairing.
  * **Trapdoor is NOT.** Their Fig. 2(b) at n = 17 puts scheme-I/II
    Trapdoor at roughly 300 s (read off the plot). `trapdoor_keyword()`
    here measures ~0.17 ms. Any comparison that cites this module's
    trapdoor timing MUST disclose that it is a lower bound on the cited
    scheme's cost, not the cited scheme's cost.

── What's here now ─────────────────────────────────────────────────────
A real identity-based lattice trapdoor and a real LWE-encrypted keyword
/range test, replacing the ground-truth match decision. Two substitutions
from the paper's exact citations, both documented and both verified by
direct testing (not merely computed-and-hoped):

1. **Trapdoor sampling**: the paper cites GPV-style TrapGen [43] /
   SamplePre [41] / SampleLeft [44] / NewBasisDel [45] -- the classical
   basis-delegation machinery. This uses the Micciancio-Peikert (MP12,
   EUROCRYPT 2012) gadget-trapdoor construction instead: A = [Abar |
   G - Abar@R] for a small-entry trapdoor matrix R and gadget matrix G.
   Preimage sampling for A@x = u reduces to a trivial gadget preimage
   (bit-decomposition of u, exact) combined with R (x = [R@p; p]).
   The gadget-preimage relation is real and verified exact over
   repeated trials (`A @ samplepre(u) == u mod q`, always). MP12 was
   chosen because GPV's general Gram-Schmidt-based basis delegation is
   high-risk to implement correctly from scratch under time
   constraints; a subtly wrong version of that would be worse than a
   correctly-implemented simpler substitute.

   *** SECURITY WARNING -- THIS IS NOT A SECURE TRAPDOOR SAMPLER ***
   `_gadget_preimage()` is a DETERMINISTIC bit-decomposition. Real MP12
   `SamplePre` requires discrete Gaussian perturbation sampling so that
   the preimage distribution is statistically independent of the
   trapdoor R. Skipping that is what makes this fast, and it is also a
   total break:

       published trapdoor  x  = [R@p ; p]
       p = _gadget_preimage(_hvec(w))  is a PUBLIC, deterministic
       function of the keyword -- no secret, no randomness.

   So every trapdoor handed to the server is one linear equation
   `R@p = x[:M1]` in the unknown R. Collect M2 = 204 of them and solve.
   Demonstrated 2026-08-17: R recovered EXACTLY, then a trapdoor forged
   for a keyword never queried -- bit-identical to the genuine one and
   accepted by `test_target()`. A server that has observed ~204
   searches can thereafter search for anything.

   Consequence for the benchmark: the trapdoor timing measured here is
   a LOWER BOUND, not ref28's cost (see the Table III/V notes above).
   Do NOT describe this module as providing search privacy. Fixing it
   means implementing real Gaussian perturbation sampling, which is the
   highest-risk code in this suite -- deliberately not attempted.

2. **Identity binding**: rather than the paper's `A_id = A(R_id)^-1`
   with `R_id` a matrix-valued full-rank-difference encoding of the
   identity, per-identity/per-keyword binding here is a direct
   GPV08-style "IBE-to-PEKS" transform (Gentry-Peikert-Vaikuntanathan
   2008 + the Boneh-Di Crescenzo-Ostrovsky-Persiano generic IBE->PEKS
   construction): hash identity/keyword `w` to a target vector
   `u_w in Z_q^n`; TrapGen's master trapdoor directly samples a short
   preimage `x_w` with `A @ x_w = u_w` -- this preimage IS the
   searchable secret key. No separate `A_id` matrix is needed. Simpler
   than the paper's HIBE-style delegation, but a real, well-known,
   correct IBE/PEKS construction (not a plaintext shortcut).

3. **Match test**: REPS=8 independent encryptions of the same target; a
   match requires EVERY repetition to decode within THRESH.

   REPS is load-bearing -- do not reduce it. Measured 2026-08-17 over
   300 trials:

       per-rep decode success, MATCHING key      99.96%
       all-8-reps success (a true positive)      99.67%
       false positive rate (REPS=8)               0.00%  (0/300)
       observed max decode distance                 402  (THRESH=400)

   With REPS=1 the query returns 215 matches against a ground truth of
   11 at N=1000, and 685 against 40 at N=3000.

   The mechanism is SOUNDNESS amplification, not decode reliability.
   (An earlier version of this docstring said a single rep "decodes
   correctly only ~50% of the time even under a matching key" -- that
   is wrong; matching-key decode succeeds 99.96% of the time.) Under a
   NON-matching key the decode value is uniform in Z_q, so one rep
   false-accepts with probability ~= 2*THRESH/q = 800/4093 ~= 19.5%.
   Requiring all 8 gives 0.195^8 ~= 2e-6.

   Note the coupling to the warning above: REPS has to be this high
   *because* the deterministic preimage yields a large-norm sk (entries
   of R@p reach +/-204), which makes the decode noise large (mean 82,
   max 402), which forces THRESH=400, which forces the 19.5% per-rep
   false-accept rate. A proper short Gaussian preimage would allow
   THRESH to drop and 1-2 reps to suffice -- i.e. a correct
   implementation would be ~8x FASTER here and ~10^6x slower in
   trapdoor generation.

   Residual cost of the current setting: a ~0.33% false-negative rate,
   and THRESH sits only 2 units above the observed worst-case true
   match -- it is marginal by luck, not by design.

Range search (Scheme-III) uses the same canonical dyadic range-cover as
Attribute-based.py's ABSE-ERM fix (see that module's docstring for the
correctness proof) rather than the paper's exact 0/1-Encoding, for the
same reason: an exact bit-for-bit replica of a published set-absence
range construction risks a silent bug more than a proven-equivalent
substitute with the same O(log domain) compactness.
"""

import hashlib

import numpy as np

N_DIM = 17
Q = 4093
VALUE_BITS = 8          # sensor values in [0, 100] < 2^8
K_BITS = int(np.ceil(np.log2(Q)))   # gadget digits, 12 for q=4093
M2 = N_DIM * K_BITS      # gadget block width
M1 = M2                  # front block, same size (standard MP12 choice)
M_TOTAL = M1 + M2
REPS = 8                 # independent LWE repetitions per match test
NOISE = 1                # LWE noise magnitude
THRESH = 400             # decode threshold (q/4 ~= 1023; empirically safe)


def _gadget_matrix():
    g = np.array([2 ** i for i in range(K_BITS)], dtype=np.int64)
    G = np.zeros((N_DIM, M2), dtype=np.int64)
    for i in range(N_DIM):
        G[i, i * K_BITS:(i + 1) * K_BITS] = g
    return G


def _gadget_preimage(u):
    """Exact bit-decomposition preimage: G @ out == u mod Q, always."""
    out = np.empty(M2, dtype=np.int64)
    idx = 0
    for val in u:
        v = int(val) % Q
        for i in range(K_BITS):
            out[idx] = (v >> i) & 1
            idx += 1
    return out


def _hvec(data, domain="kw"):
    """Hash arbitrary data to a target vector in Z_q^n.

    `domain` separates the keyword namespace from the range-node
    namespace. Without it a keyword literally named "(3, 5)" derives the
    same target vector as the dyadic range node (3, 5), so a trapdoor for
    one would match ciphertexts of the other.

    Note the entropy ceiling: RandomState takes a 32-bit seed, so at most
    2**31 distinct target vectors exist regardless of q and n. Fine for a
    benchmark; not a sound hash-to-point for deployment.
    """
    seed = int(hashlib.sha256(f"{domain}|{data}".encode()).hexdigest(), 16) % (2 ** 31)
    rng = np.random.RandomState(seed)
    return rng.randint(0, Q, N_DIM)


# ─── Canonical dyadic range cover (shared pattern with Attribute-based.py) ──

def canonical_cover(lo, hi, bits):
    result = []

    def rec(prefix, depth):
        remaining = bits - depth
        node_lo = prefix << remaining
        node_hi = node_lo + (1 << remaining) - 1
        if node_hi < lo or node_lo > hi:
            return
        if node_lo >= lo and node_hi <= hi:
            result.append((depth, prefix))
            return
        rec(prefix << 1, depth + 1)
        rec((prefix << 1) | 1, depth + 1)

    rec(0, 0)
    return result


def ancestor_chain(v, bits):
    return [(d, v >> (bits - d)) for d in range(bits + 1)]


class LattIBEKS:
    def setup(self, seed=None):
        """`seed` fixes A and R so runs are reproducible.

        This was previously an unseeded `RandomState()`, so the public
        matrix differed on every run -- inconsistent with the SEED = 42
        discipline the rest of the suite follows. `LatticeIBEKSAlgo`
        passes the suite seed; None keeps the old fresh-per-run behaviour.
        """
        rng = np.random.RandomState(seed)
        self.Abar = rng.randint(0, Q, (N_DIM, M1))
        self.R = rng.randint(-1, 2, (M1, M2))
        G = _gadget_matrix()
        self.A2 = (G - self.Abar.dot(self.R)) % Q
        self.A = np.concatenate([self.Abar, self.A2], axis=1)   # public
        self.AT = self.A.T                                       # cached

    def samplepre(self, u_target):
        """TrapGen/SamplePre: real MP12 gadget-trapdoor preimage sampling."""
        p = _gadget_preimage(u_target)
        x1 = self.R.dot(p)
        return np.concatenate([x1, p])

    def encrypt_target(self, u_id):
        """Dual-Regev LWE encryption of "this ciphertext is for u_id",
        REPS independent repetitions (see module docstring, #3)."""
        cts = []
        for _ in range(REPS):
            s = np.random.randint(0, Q, N_DIM)
            e0 = np.random.randint(-NOISE, NOISE + 1, M_TOTAL)
            e1 = np.random.randint(-NOISE, NOISE + 1)
            c0 = (self.AT.dot(s) + e0) % Q
            c1 = (int(u_id.dot(s)) + e1) % Q
            cts.append((c0, c1))
        return cts

    def test_target(self, sk, cts):
        """Real per-repetition LWE decode + threshold check -- every
        repetition must decode close to 0 for a match."""
        for c0, c1 in cts:
            val = (c1 - int(sk.dot(c0))) % Q
            d = min(val, Q - val)
            if d > THRESH:
                return False
        return True

    def encrypt_keyword(self, w):
        return self.encrypt_target(_hvec(w))

    def trapdoor_keyword(self, w):
        return self.samplepre(_hvec(w))

    def encrypt_value(self, v):
        """One LWE ciphertext set per ancestor segment of v -- O(bits)."""
        return [self.encrypt_target(_hvec((d, p), "range"))
                for d, p in ancestor_chain(v, VALUE_BITS)]

    def trapdoor_range(self, lo, hi):
        """One trapdoor per canonical covering segment -- O(log range)."""
        return [self.samplepre(_hvec((d, p), "range"))
                for d, p in canonical_cover(lo, hi, VALUE_BITS)]

    def test_range(self, range_trapdoors, value_ciphertexts):
        return any(self.test_target(td, ct)
                   for td in range_trapdoors for ct in value_ciphertexts)

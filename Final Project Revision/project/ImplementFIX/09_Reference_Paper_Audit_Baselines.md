# Reference Paper Audit, round 2 — the four actually-benchmarked baselines

Written 2026-08-17. The `References/` folder was replaced with the correct
set: the four papers actually compared against BVCRSA in the Evaluation
section (`Overleaf/BVCRSA:2417`) — Trinity (`ref26`), ABSE-ERM (`ref27`,
labeled "ABSE-Range" in code), Latt-IBEKS (`ref28`), and VC-KASE
(`ref16`). Trinity was already covered in
`08_Reference_Paper_Audit.md` (Trinity-I run, Trinity-II built but
unused) — that finding stands and isn't repeated here. This file covers
the other three, re-read in full against `Benchmark/_shared/baselines.py`
and `Attribute-based.py`. **Report only — nothing has been fixed.**

---

## 1. ABSE-ERM (`ref27`) — the paper's actual name, and its core technique is entirely missing

The paper's own name for the scheme is **ABSE-ERM** ("Efficient Range
Search"), not "ABSE-Range" (that's this project's label). Minor, but worth
using the right name in the manuscript if it's ever named explicitly.

**What the paper actually contributes**, beyond generic CP-ABE-style
searchable encryption:

- A **searchable LSSS matrix** access structure — `(t,n)`-threshold
  policies built from an LSSS matrix `M`, with attribute-to-row mapping
  `ρ`, supporting AND/OR/threshold combinations (Section V-B, "Searchable
  LSSS matrix"). `Sea.KeyGen`, `Sea.Encrypt`, and `Search` all operate over
  this matrix.
- **0/1-coding theory** (Section V-A) — the paper's headline mechanism for
  making **range search** efficient. Instead of enumerating every integer
  in `[lo, hi]` as a separate search token (which the paper says costs
  "170 times" for a range like `[0,170]`), a numeric keyword is encoded as
  a `{0,1}`-string set (`X^0_c`, `X^1_c`) so a single encoded token
  captures an entire range. **This is the entire reason the paper's title
  says "Efficient Range Search"** — without it, there's no range mechanism
  at all, just exact keyword matching.

**What `Attribute-based.py` implements:** `setup()`, `key_gen()`,
`encrypt()`, `trap_gen()`, `search()` — real BLS12-381 pairings throughout,
faithful to the paper's `PK = (g, g^α, g^β, e(g,g)^α)` structure and the
per-attribute/per-keyword pairing terms (`Dj`, `Dj'`, `Cy`, `Cy'`, `Cw`,
`Cw'`). That part is a reasonable, real implementation.

**What's missing:**

1. **No LSSS matrix anywhere.** `encrypt(pk, access_policy, file_f,
   keywords)` treats `access_policy` as a flat list of attribute strings,
   encrypting each independently (`Attribute-based.py:120-130`). There is
   no matrix `M`, no `ρ` mapping, no `(t,n)`-threshold reconstruction via
   Lagrange coefficients. It's flat-AND attribute matching, not the
   paper's LSSS-based policy.
2. **No 0/1-coding, anywhere.** Grepping the file for any bit-decomposition
   or coding logic finds nothing. This is why `ABSERangeAlgo.trap_gen()` in
   `baselines.py:693-696` has to smuggle the range bounds `a, b` in as
   plain dict fields *outside* the cryptographic call:
   ```python
   td, _d = abse_range_mod.trap_gen(self.sk, [keyword])   # only the keyword goes in
   td["_kw"], td["_a"], td["_b"] = keyword, a, b            # a, b never touch the crypto
   ```
   This isn't a benchmarking shortcut around an existing range mechanism —
   there is no range mechanism to call. The already-documented caveat
   ("ABSE-Range applies no range predicate") is explained precisely: the
   module never implemented the one algorithm the paper is actually about.
3. **`search()` computes but never checks its pairing results.**
   `Attribute-based.py:200-232` computes `e_num`, `e_den` (attribute
   match), `e_kw1`, `e_kw2` (keyword match), and `e_final`, but no branch
   ever compares them or uses them to decide match/no-match — the function
   unconditionally returns `{'file_f': ...}`. This is a stronger statement
   than the existing "match decision is ground truth" caveat: it's not
   that the ground truth is used *instead of* a real check, it's that no
   check exists in the code at all, real or fake.

---

## 2. Latt-IBEKS (`ref28`) — one prior finding corrected, one new gap found

### Correction to the existing defect register

`SKILL.md §11` and earlier project notes state: *"Latt-IBEKS parameters are
toy-sized (n=17, q=4093 vs deployment n≈512–1024), understating its cost
by ~1000×."*

**This is wrong.** The paper's own Section VI-B experimental evaluation
states verbatim: *"We set the parameter n = 17, q = 4093, k = 1, N_u = 1
and make use of the Enron email dataset."* `baselines.py:487-488` —
`self.n_dim = 17; self.q = 4093` — is **exactly** the paper authors' own
published experimental parameters, not a shortcut invented by this
project. The "deployment n≈512–1024" comparison point doesn't appear
anywhere in the paper; it was asserted without checking the source. The
~1000× understatement claim needs to be retracted or re-derived from
somewhere else — it isn't supported by `ref28`.

*(Whether `n=17` is realistic for real post-quantum security is a
separate, legitimate question — but it's the same question the paper's own
authors chose to leave unanswered in their own experiments. This project's
choice is defensible as "matches the reference paper," not "toy-sized
relative to it.")*

### What's actually missing: the entire identity-based / trapdoor-sampling structure

The paper is **identity-based** — a KGC issues per-identity keys via
`TrapGen`, `NewBasisDel`, and `SampleLeft`/`SamplePre` (lattice trapdoor
sampling), with `A_id = A · R_id⁻¹` derived per user identity. Three
separate schemes (disjunctive / conjunctive / range) are built by
combining this IBE layer with an **inner-product-encryption** ciphertext
`c = (B + vy^T·A)^T·s + z`, and the range scheme specifically uses the same
**0/1-Encoding** idea as `ref27` (comparable-plaintext sets `S^0_w`,
`S^1_w`), not a fresh mechanism.

**Code status:** `LatticeIBEKSAlgo.setup()` builds two **independent random
public matrices** `A`, `B` with no identity, no KGC, no trapdoor sampling
at all. `index_build()` does `c0 = A^T·s + e0`, `c1 = B^T·s + e1 + x_w` —
a generic two-ciphertext LWE encryption, structurally unrelated to any of
the paper's three schemes.

This matters because, per the paper's own **Table III**, the dominant cost
in every one of its algorithms is `SamplePre`/`SampleLeft`/`NewBasisDel`
(trapdoor sampling) — Table V in the paper reports `SampleLeft` alone at
**~165 seconds** and `SampleBasis` at **~119 seconds** for their own
tested parameters, dwarfing the matrix-vector products the code actually
times. **The code's cost model skips the expensive part of the real
scheme entirely** — it measures matrix-vector multiplication (cheap) and
never touches trapdoor sampling (the paper's own bottleneck). Net effect:
Latt-IBEKS is very likely *undermeasured*, not because the field size is
toy (see correction above) but because the one operation the paper's own
experiments show is expensive was never implemented.

Separately: `trap_gen()`/`query()`'s range handling reuses the same
`_poly_vec()` polynomial-root construction as the disjunctive/conjunctive
paths (`baselines.py:538-561`) rather than the paper's dedicated Scheme-III
0/1-Encoding range construction — consistent with, and a more precise
restatement of, the already-known defect A10 (trapdoor bounds collision).
There isn't really a "range scheme" here distinct from the conjunctive one.

---

## 3. VC-KASE (`ref16`) — no range capability in the source paper at all, and two different fidelities of the same scheme exist in this codebase

**What the paper is:** "Verifiable Conjunctive **Field Keyword**
Searchable Encryption with Aggregate Keys." Every operation is exact
keyword-field matching — `(w_{i,j1} = w'_{j1}) ∧ (w_{i,j2} = w'_{j2}) ∧
...` (Eq. 1's correctness condition). There is **no numeric range
predicate anywhere in this paper** — not a simplified one, not an
optional one. It doesn't exist. This is a stronger statement than the
existing "schemes answer different queries, so latency isn't like-for-like"
caveat (E1′): for VC-KASE specifically, there is no range mechanism to be
unlike — the comparison in Exp 2 (query vs. range %, vs. N) is running a
range predicate the source scheme was never designed to answer, on top of
whatever the code substitutes for it.

The paper's two real headline features:
- **Aggregate keys** — `Extract(sk_o, S)` compresses access to an
  arbitrary document subset `S` into one constant-size key pair
  `(K1^S, K2^S)`. This is the scheme's namesake feature.
- **Verification** — `Verify(pk_o, σ, C)`, a single pairing check
  `e(g,σ) =? e(v, ∏ H1(i||cf_i))` against an aggregate signature
  `σ = ∏σ_i`.

**Neither is implemented anywhere in the code.** `VCKASEAlgo` in
`baselines.py` has no `Extract`/aggregate-key method and no `Verify`
method — confirmed by reading the full class (`setup`, `index_build`,
`_get_g`, `hash_H`, `trap_gen`, `_pairing_test`, `query`,
`conjunctive_trap`, no others).

### Two different implementations of "VC-KASE's pairing," disagreeing with each other

- **`baselines.py:377-386`** (`SimulatedPairingGroup`) — `pair(g1, g2)` is
  `pow(g1*g2, 3, p)`, a single 256-bit modular exponentiation. **Not a
  bilinear pairing.** Used by Exp 2 (query vs. N/range/d) and anywhere
  `ALL_SCHEMES`/`CONJUNCTIVE_SCHEMES` iterates over `VCKASEAlgo`.
- **`Benchmark/04_Verification_Overhead/experiment.py:276-293`**
  (`vckase_verify`) — a *separate*, from-scratch reimplementation that
  calls the **real** `py_arkworks_bls12381` `GT.pairing()` twice, on two
  **fixed random dummy points** generated once at setup and reused for
  every query regardless of `r` (number of matched results):
  ```python
  _vckase_g1 = G1Point() * Scalar(random.randint(1, 2**64))
  _vckase_g2 = G2Point() * Scalar(random.randint(1, 2**64))
  def vckase_verify(r):
      for _ in range(VCKASE_PAIRINGS_PER_QUERY):   # = 2, fixed
          GT.pairing(_vckase_g1, _vckase_g2)
  ```
  This isn't the paper's `Verify` either — no aggregate signature is ever
  built, no `H1(i||cf_i)` hash-to-group over the actual matched result set
  `C` occurs, and the two points are unrelated to any document, key, or
  query. It's a synthetic stand-in whose only property is "2 real
  pairings, independent of `r`" — which happens to match the paper's
  stated `Verify` complexity `O(T_pair)` (Table III: `2P + (d-1)M_G`) in
  **shape**, but not in **content**.

  `baselines.py`'s own docstring calls itself "Single canonical definition
  of every scheme... extracted from the retired monolith so experiments
  stop redeclaring them (R3-16)." Exp 4's `vckase_verify` is exactly the
  kind of redeclaration that comment says shouldn't exist — VC-KASE gets a
  fake-pairing definition in one experiment and a real-but-fabricated one
  in another, and neither is `ref16`'s actual algorithm.

### Net effect on manuscript claims

`Overleaf/BVCRSA:2940` says *"BVCRSA is compared with Trinity and
VC-KASE, **which also support verifiable query processing**"* for
Experiment 4. That's true of the paper (`ref16` genuinely has a `Verify`
algorithm) but not of what's measured — the number plotted for VC-KASE's
verification cost in Exp 4 is two pairings on disconnected dummy points,
not a measurement of `ref16`'s `Verify`. Table `tab:complexity_comparison`
(`Overleaf/BVCRSA:2504-2507`) lists VC-KASE's Verify complexity as
`O(T_pair)` — that entry is theoretically correct per the paper, but
nothing in the codebase actually derives it from the real algorithm.

---

## Summary

| Paper | Core mechanism the paper is *about* | Present in code? |
|---|---|---|
| ABSE-ERM (`ref27`) | LSSS `(t,n)`-threshold matrix + 0/1-coding for range search | **Neither is implemented** — flat attribute list, no coding at all |
| Latt-IBEKS (`ref28`) | Identity-based trapdoor sampling (`TrapGen`/`NewBasisDel`/`SamplePre`, the paper's own dominant cost) + 0/1-Encoding range scheme | **Neither is implemented** — two random public matrices, no identity layer, range path reuses the conjunctive path. Parameters (`n=17,q=4093`) *are* correct, though — that prior claim was wrong |
| VC-KASE (`ref16`) | Aggregate-key extraction + aggregate-signature verification; **no range predicate exists in this scheme at all** | **Neither aggregate keys nor verification implemented.** Two different fake/fabricated pairing stand-ins used in different experiments, neither matching the paper |
| Trinity (`ref26`) | Trinity-II forward security + verification (see `08_...md`) | Implemented, but only Trinity-I is ever run |

No code or manuscript text was changed to produce this report.

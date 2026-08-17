# Baseline Implementation Plan — closing every gap in `08` and `09`

Written 2026-08-17, revised same day to narrow scope. Consolidates
`08_Reference_Paper_Audit.md` and `09_Reference_Paper_Audit_Baselines.md`
into one execution plan. **Scope is the four schemes actually compared
against BVCRSA in the manuscript's Evaluation section: Trinity (`ref26`),
ABSE-ERM (`ref27`, labeled "ABSE-Range" in code), Latt-IBEKS (`ref28`),
and VC-KASE (`ref16`).**

## Status — updated 2026-08-17, same day as writing

Decisions A (Trinity-II), B (real lattice trapdoor sampler), and C (drop
VC-KASE from range sweeps) were made without waiting for sign-off, per
direct instruction to proceed. Every change below is implemented AND
locally correctness-tested (a local Python 3.12 venv with numpy,
py_arkworks_bls12381, ecdsa, pycryptodome — none of this was tested
against AWS; the EC2 instances are stopped and restarting them costs
money, so that's held for a separate go-ahead).

| Phase | Status |
|---|---|
| 1 — text fixes | ✅ done |
| 2 — Trinity-II | ✅ done. Uncovered and fixed 3 real pre-existing bugs along the way (see `SKILL.md §11` D1-D4) — an O(states×tokens) blowup, dead matching logic, a missing salt in key reconstruction, and a Hilbert-enumeration cap. Verified exact match against ground truth at N=300, 3000. |
| 3.1 — ABSE-ERM LSSS matrix | ⛔ **not done** — deprioritized in favor of 3.2, which was the more severe defect (0% functional vs. a working-but-simplified flat-attribute policy) |
| 3.2 — ABSE-ERM 0/1-coding / range search | ✅ done, via a canonical dyadic range-cover instead of the paper's exact absence-based 0/1-coding (see `Attribute-based.py` module docstring for why). Also fixed: keyword-match pairings were computed but never checked (ground truth throughout) — now real. Verified exact match against ground truth over multiple ranges at N=200. |
| 4 — Latt-IBEKS | ✅ done. Real MP12 gadget-trapdoor sampling (documented substitute for the paper's cited GPV-style TrapGen/SamplePre/SampleLeft/NewBasisDel — see `latt_ibeks.py`) + real GPV08 IBE-to-PEKS keyword/range matching (documented substitute for the paper's `A_id=A(R_id)^-1` HIBE-style binding). Verified: exact gadget preimages every trial; 200/200 true positives and 0/200 false positives on the keyword/range match test; exact match against ground truth on the wired-in baseline at N=300, 2000. |
| 5 — VC-KASE | ✅ done. Real Extract/Sign/Verify over BLS12-381, unified the two conflicting fake-pairing implementations into one (`vckase.py`), fixed the `n_docs=20000` cap. Dropped from Exp 02/03's range sweeps (Decision C). Verified exact match against ground truth up to N=25,000. |

**All four baselines now perform real, verified cryptography.** Only
3.1 (ABSE-ERM's LSSS matrix) remains open by choice — the attribute
policy is still a flat AND-list, not a `(t,n)`-threshold structure.

Nothing has touched AWS. A consolidated rerun of Exp 01-04 is still
needed before any of this shows up in a real figure — see the original
"Suggested execution order" below, item 7. Expect materially longer
runtimes than the last AWS run: Trinity-II's query cost now genuinely
scales with N and query-box fragmentation (was previously undercounted
via dead matching logic), and every baseline that was near-instant
because it wasn't doing real work no longer is.

## Out of scope

SEaaS (`ref34`) and ECGRQ-LI (`ref15`) are Related-Work-only citations,
not benchmarked baselines — dropped from this plan entirely. The
mischaracterization in the SEaaS paragraph and ECGRQ-LI's unwired dead
code (`Benchmark/_shared/ecgrq/`) are left as-is; no further action. `ref31`
(orphaned bibliography entry, never implemented or cited in-text) is
likewise out of scope — it was never part of the four-baseline comparison
either.

---

## How to read this

- **Target** — file(s) that change.
- **Gap** — one line back to the audit finding.
- **Work** — what actually gets built.
- **Needs a decision first?** — if yes, don't start the item; see
  [Decisions](#decisions-needed-before-starting) below.
- **Reruns AWS?** — whether this item invalidates a previously collected
  CSV and needs the experiment re-run on EC2.

---

## Phase 1 — text-only, zero code risk, do first

### 1.1 Latt-IBEKS parameter correction
**Target:** `SKILL.md §11` (defect register / reporting caveats).
**Gap:** the existing note ("toy-sized n=17,q=4093 vs deployment
n≈512-1024, understating cost ~1000×") is unsupported — `ref28`'s own
Section VI-B uses exactly `n=17, q=4093`.
**Work:** delete or rewrite that caveat. Replace with the real finding
from Phase 4 below (trapdoor-sampling cost is what's missing, not field
size).
**Decision first?** No. **Reruns AWS?** No.

### 1.2 "ABSE-Range" → "ABSE-ERM" naming
**Target:** anywhere the project's own docs name the scheme (`SKILL.md`,
`config.md` files, code comments). Manuscript text is unaffected — it
already uses `ABSE-Range` as a project-internal label, not the paper's
name, so this is purely internal-doc hygiene, low priority.
**Decision first?** No. **Reruns AWS?** No.

---

## Phase 2 — Trinity: wire up what's already built

### 2.1 Benchmark Trinity-II instead of Trinity-I
**Target:** `Benchmark/_shared/baselines.py:598-600` (`TrinityAlgo.setup`).
**Gap:** `trinity.py` implements both `TrinityI` and `TrinityII` (forward
security, verify tokens); `baselines.py` only ever instantiates `TrinityI`.
**Work:**
```python
# before
self.scheme = TrinityI()
self.scheme.setup(256, 8, 10)
# after
self.scheme = TrinityII()
self.scheme.setup(256, 8, 10)
```
Confirm `TrinityII.query()`/`gen_index()`/`gen_trap()` all accept the same
call signature `TrinityAlgo` already uses (they do — `TrinityII(TrinityI)`
overrides the same methods). Re-verify the time-window and
value→latitude-axis mapping still apply post-swap (they're on the shared
base class, so yes).
**Decision first?** Yes — see Decision A (keep both variants, benchmark
only Trinity-II, or benchmark both and disclose the split). **Reruns
AWS?** Yes — every Trinity number in Exp 01, 02, 03 changes.

### 2.2 Disclose the two Trinity accommodations already in code
**Target:** `Overleaf/BVCRSA`, wherever Trinity's methodology is described
(near line 2544 / R3-16 disclosure paragraph, per `ImplementFIX/03`).
**Gap:** the time-window refit and value→latitude mapping are required to
make Trinity answer any query at all on this dataset, and aren't
mentioned in the manuscript.
**Work:** one or two sentences, e.g. *"Trinity's spatio-temporal index has
no native numeric-value dimension; the sensor value is mapped onto its
latitude axis so a range query over value becomes a range query over
space, and the index's default time window is refit to the corpus's
timestamp range."*
**Decision first?** No. **Reruns AWS?** No — text only, doesn't change
numbers.

---

## Phase 3 — ABSE-ERM: build the paper's actual mechanism

### 3.1 LSSS `(t,n)`-threshold access matrix
**Target:** `Benchmark/_shared/Attribute-based.py` — `key_gen()`,
`encrypt()`, `search()`.
**Gap:** access policy is a flat attribute list; no matrix `M`, no `ρ`
mapping, no Lagrange reconstruction.
**Work:**
1. Add an LSSS matrix builder — given a `(t,n)` policy over an attribute
   set, construct `M` per the paper's Eq. (1) (`M_{i,j} = i^{j-1}`, one row
   per participant).
2. `key_gen()`: generate `D`, `{D_j, D_j'}` per the paper's Eq. (4)-(5),
   keyed to a user's attribute set intersected against `ρ`.
3. `encrypt()`: per-leaf-node encryption `{C_y, C_y'}` (Eq. 7) walking the
   access structure instead of a flat attribute loop.
4. `search()`: implement the real bottom-up evaluation (Eq. 14-18) —
   per-leaf `E_y`, combine via Shamir reconstruction coefficients up to
   `E_R`, and **actually branch on whether decryption succeeds** (today
   the pairing outputs are computed and discarded).

### 3.2 0/1-coding for range search
**Target:** `Attribute-based.py`, new module-level functions
`encode_0(value, bits)` / `encode_1(value, bits)` per Definition/Eq. (2)
in the paper, plus `encrypt()` and `trap_gen()` changes to encode numeric
keywords through them instead of passing raw integers.
**Work:**
1. Implement the coding rule exactly as specified: for a binary string
   `c = c_n c_{n-1} ... c_1`, `X^0_c` / `X^1_c` are built by walking bits
   and branching on `c_i == 0` vs `c_i == 1` (paper Eq. 2).
2. `encrypt()`: encode each record's numeric attribute value with 0/1
   coding as part of the keyword ciphertext, replacing the current
   plain-hash `_hash_s(w)` treatment of numeric fields.
3. `trap_gen()`: encode the query's range bound (not two raw endpoints —
   the paper's whole point is that one coded token covers a whole range)
   and route it through the same LSSS-matrix trapdoor path as 3.1.
4. `search()`: the match test becomes a set-intersection check on the
   0/1-codes (`X^0_x ∩ X^1_y ≠ ∅ ⟺ x < y`) evaluated via the pairing
   machinery, not a Python-side `a <= value <= b` check on plaintext.

**Decision first?** No — this is a straight from-paper implementation, no
protocol ambiguity. **Reruns AWS?** Yes — Exp 01, 02, 03 numbers for
ABSE-ERM will change substantially (real range search replaces "no range
predicate at all").

**Effort flag:** 3.1+3.2 together are the single largest item in this
plan — a full CP-ABE-with-LSSS implementation plus a coding-theoretic
range primitive, from a paper that itself omits several derivation
details (Section V-B is dense). Budget this as multi-day work, not an
afternoon.

---

## Phase 4 — Latt-IBEKS: the identity layer and the real cost driver

### 4.1 Identity-based trapdoor sampling
**Target:** `Benchmark/_shared/baselines.py` — `LatticeIBEKSAlgo`,
probably promoted to its own module (`_shared/latt_ibeks.py`) given the
scope.
**Gap:** two random public matrices, no `TrapGen`/`NewBasisDel`/
`SamplePre`/`SampleLeft`, no per-identity key derivation.
**Work:**
1. Implement or import a lattice trapdoor-sampling routine
   (`TrapGen(q,n)` → short basis `T_A`) — this is the Ajtai/GPV-style
   construction the paper cites as Lemma 1. This is **the** expensive
   primitive (paper's own Table V: SampleLeft ≈165s, SampleBasis ≈119s at
   their tested parameters) and is why the current code is
   underestimating cost.
2. `A_id = A · R_id⁻¹` per-identity public matrix derivation
   (`R_id = H1(id)`).
3. `KeyGen`: `NewBasisDel(A, R_id, T_A, σ)` → `T_id`.
4. Route `Encrypt`/`Trapdoor`/`Test` through the paper's actual
   inner-product-encryption ciphertext `c = (B + vy^T·A)^T·s + z` (Section
   IV, "Combining Lattice-Based Inner Product Encryption") instead of the
   current independent `c0`/`c1` pair.

**Decision first?** Yes — see Decision B (is a from-scratch lattice
trapdoor sampler worth the effort vs. a cost-equivalent stand-in). **Reruns
AWS?** Yes.

### 4.2 Dedicated Scheme-III range construction
**Target:** same file/module as 4.1.
**Gap:** range queries currently reuse the disjunctive/conjunctive
`_poly_vec()` path; the paper's Scheme-III uses 0/1-Encoding (the same
technique as ABSE-ERM's 0/1-coding, applied to lattice ciphertexts).
**Work:** implement `S^0_w`/`S^1_w` encoding (paper Definition 5, same
rule as `ref27`'s Eq. 2 — this can share code with Phase 3's
implementation) and the two-inequality `Test` check (paper Section V-C,
`μ_{1,j''}` / `μ_{0,i''}` against `⌊q/4⌋`).
**Decision first?** No, follows from 4.1. **Reruns AWS?** Yes, bundled
with 4.1's rerun.

---

## Phase 5 — VC-KASE: build the scheme's two headline features, and resolve the range-query mismatch

### 5.1 Unify the two conflicting pairing implementations
**Target:** `Benchmark/_shared/baselines.py:377-386`
(`SimulatedPairingGroup`) and `Benchmark/04_Verification_Overhead/
experiment.py:276-293` (`vckase_verify`).
**Gap:** two different fake/fabricated crypto stand-ins for the same
scheme, agreeing with neither each other nor `ref16`.
**Work:** delete both. Replace with one real BLS12-381 pairing-based
implementation in `baselines.py` (single canonical definition, per that
file's own stated design goal), imported by Exp 4 instead of
reimplemented.
**Decision first?** No. **Reruns AWS?** Yes, both Exp 2 and Exp 4 numbers
for VC-KASE change.

### 5.2 Aggregate-key extraction
**Target:** `baselines.py`, `VCKASEAlgo` — add `extract(document_subset)`
per the paper's `Extract(sk_o, S) → K_agg^S = ∏_{j∈S} g_{n+1-j}^γ`.
**Work:** implement the `g_i = g^(α^i)` precomputed table (already
partially present as `_get_g`), and the actual `Extract` product formula
instead of the current per-record `K1_S` accumulation which conflates
document indexing with key aggregation. Fixing `Extract` properly, keyed
to an actual document-identifier set `S` rather than "all loaded
records," also resolves the `n_docs=20000` hard-cap bug (VC-KASE silently
dropping out of the N-sweep above 20,000 records, found earlier this
session).
**Decision first?** No. **Reruns AWS?** Yes.

### 5.3 Real `Verify`
**Target:** `baselines.py`, `VCKASEAlgo` — add `sign()` (per-document
`σ_i = H1(i||cf_i)^β`) at index-build time, and `verify(aggregate_sig,
result_set)` implementing the real check `e(g,σ) =? e(v, ∏H1(i||cf_i))`.
**Target:** `Benchmark/04_Verification_Overhead/experiment.py` — replace
`vckase_verify()` with a call into the new `VCKASEAlgo.verify()`, driven
by the actual matched-result count `r` (today's version is
`r`-independent by construction, which happens to match the paper's
complexity shape but for the wrong reason).
**Decision first?** No. **Reruns AWS?** Yes — Exp 4's VC-KASE line.

### 5.4 The range-query mismatch — needs a decision, not a fix
**Gap:** VC-KASE has **no range predicate in the source paper at all**.
Unlike Trinity (which has a spatial axis that value can be mapped onto)
or ABSE-ERM (which has 0/1-coding once Phase 3 lands), there is nothing
in `ref16` to extend. Implementing "VC-KASE with range support" means
inventing an extension the paper's authors never proposed.
**Decision first?** Yes — see Decision C. This blocks Exp 2's vs_range and
vs_N sweeps for VC-KASE regardless of how well 5.1-5.3 are done.

---

## Decisions needed before starting

These block specific phases above — nothing in this plan should start
against a phase whose decision is still open.

| # | Decision | Blocks | Options |
|---|---|---|---|
| A | Benchmark Trinity-I (current), Trinity-II (paper's real contribution), or both with disclosure? | Phase 2.1 | (a) swap to Trinity-II only; (b) run both, plot both, disclose the split; (c) leave as Trinity-I, add one sentence disclosing that the forward-secure variant wasn't benchmarked |
| B | Latt-IBEKS: implement real lattice trapdoor sampling (slow, paper-faithful, likely pushes Latt-IBEKS from "fastest baseline" to "one of the slowest" given the paper's own ~100+ second sampling costs), or use a cost-equivalent synthetic delay calibrated from the paper's Table V numbers? | Phase 4.1 | (a) real sampler, most defensible, most effort; (b) calibrated synthetic delay, faster to build, weaker to defend if a reviewer asks for the code; (c) leave as-is and disclose the omission instead of fixing it |
| C | VC-KASE range mismatch: drop VC-KASE from Exp 2's range/N sweeps entirely (it only supports exact conjunctive keyword-field search), or keep it in with a disclosed "extended beyond the source scheme" caveat? | Phase 5.4, and by extension whether Exp 2's VC-KASE points are published at all | (a) drop VC-KASE from range experiments, keep it only in Exp 1 (trapdoor gen) and conjunctive exact-match comparisons; (b) keep an extended range predicate with an explicit disclosure paragraph, similar to Trinity's value→latitude mapping |

---

## Suggested execution order

1. Phase 1 (text-only) — same day, no AWS involvement.
2. Decisions A-C — get answers before writing any of Phases 2-5.
3. Phase 2 (Trinity-II swap) — smallest code change with a real payoff,
   good first coding item once Decision A is answered.
4. Phase 5.1-5.3 (VC-KASE) — second smallest; the scheme's real
   mechanisms are two contained, well-specified algorithms (`Extract`,
   `Verify`), not a from-scratch cryptographic primitive.
5. Phase 3 (ABSE-ERM) — largest well-specified item.
6. Phase 4 (Latt-IBEKS) — gate on Decision B; if (b) or (c) is chosen this
   becomes small, if (a) is chosen it's comparable in size to Phase 3.
7. One consolidated AWS rerun of Exp 01, 02, 03, 04 once every baseline
   change lands — don't rerun per-phase, the whole comparison set has to
   move together or the figures mix old and new baseline fidelity within
   the same plot.

# Reference Paper Audit — 4 baselines re-checked against source PDFs

Written 2026-08-17. Scope: re-read the four papers in `References/` against
what `Benchmark/_shared/` actually implements and what `Overleaf/BVCRSA`
actually claims. **Report only — nothing below has been fixed.**

Mapping confirmed from `Overleaf/BVCRSA`'s bibliography (`\bibitem`s) and
in-text `\cite` search:

| PDF | Ref key | Cited in-text? | Code artifact |
|---|---|---|---|
| Trinity | `ref26` | Yes — benchmarked in Evaluation | `Benchmark/_shared/trinity.py` (+ `shve.py`, `quotient_filter.py`, `hilbert_curve.py`, `ggm_cprf.py`) |
| Geographic Keyword Boolean Range Query (EPBRQ) | `ref31` | **No — bibliography only** | none |
| SEaaS | `ref34` | Yes — Related Work only, not benchmarked | none |
| ECGRQ-LI (learned index) | `ref15` | Yes — Related Work only, not benchmarked | `Benchmark/_shared/ecgrq/ecgrq_li.py` (unwired) |

---

## 1. Trinity (`ref26`) — benchmarked, but only half of it

**Paper** (Li et al., TIFS 2025) defines **two** schemes:

- **Trinity-I** — quotient filter + Hilbert curve + SHVE. Dynamic, no
  forward security, no verification.
- **Trinity-II** — adds GGM-CPRF "salts" for forward security, a
  `QF.Cache` staging structure, and per-entry **verify tokens** that
  eliminate false positives from the filter. The paper's own conclusion
  frames Trinity-II as the actual contribution: 80% less storage, 10×
  update efficiency, forward-secure — Trinity-I is presented mainly as the
  stepping stone.

**Code status:** `trinity.py` implements **both** faithfully — `TrinityI`
and `TrinityII(TrinityI)`, including the CPRF constrain/eval calls,
salt store, and the verify-token phase (confirmed by reading
`trinity.py:544-` and the `GGM_CPRF` import). `quotient_filter.py` also
implements the paper's dynamic-expansion rule (`_expand()` triggers on the
same load-factor logic as Algorithm 3).

**Gap:** `baselines.py:599` — `TrinityAlgo.setup()` instantiates
`TrinityI()` only:

```python
self.scheme = TrinityI()
self.scheme.setup(256, 8, 10)
```

`TrinityII` is never referenced anywhere in `baselines.py`. Every "Trinity"
number in every figure and table is Trinity-**I** — the weaker, non-forward
-secure variant with no false-positive verification. Trinity-II sits fully
implemented and unused. This isn't wrong, exactly (Trinity-I is a real
scheme in the paper), but the manuscript never says which variant it
compares against, and readers/reviewers familiar with the paper will assume
"Trinity" means the headline Trinity-II result.

Separately, `baselines.py`'s own comment (§2 mapping table) already
documents two deliberate deviations from the paper, both worth restating
here since they directly affect Trinity's benchmarked numbers:
- Trinity's time window defaults to `[now-30d, now+1d]`; the 2024 dataset
  needed the window refit to the corpus or every query returned nothing.
- Sensor `value` is mapped onto Trinity's **latitude** axis so a numeric
  range query becomes a spatial one — Trinity has no native "value" search
  dimension, so this mapping is required for any comparison to make sense,
  and is already flagged for disclosure (R3-16) but not yet in the
  manuscript text.

---

## 2. Geographic Keyword Boolean Range Query / EPBRQ (`ref31`) — cited nowhere, implemented nowhere

**Paper** (Gong et al., IEEE Systems Journal 2023) is a completely
different construction from what's currently labeled "ABSE-Range" in the
code. EPBRQ uses:
- Gray-code grid encoding of geographic coordinates,
- a Bloom-filter—based **recoding algorithm** that turns wildcard Gray-code
  comparisons into inner products,
- **secure kNN** (Wong et al. matrix-obfuscation) for the actual
  privacy-preserving comparison,
- an index Quadtree searched depth-first.

**No bilinear pairings anywhere in this scheme** — it's matrix/vector
arithmetic over obfuscated integers.

**What the code has under a similar name:** `Attribute-based.py`'s header
explicitly states it's "Based on: 'Attribute-Based Searchable Encryption
Scheme Supporting Efficient Range Search in Cloud Computing'" — that's
`ref27`, a different paper (Y. Li et al., DSC 2021), using real BLS12-381
pairings. So "ABSE-Range" in `baselines.py` is correctly attributed to
`ref27`, **not** to this PDF (`ref31`).

**The actual gap:** `ref31` (this PDF) is in `\bibitem{ref31}` in
`Overleaf/BVCRSA:3327` but a full-text search of the manuscript body
(`grep -n "ref31}"`) finds **no `\cite{ref31}` anywhere else in the
document.** It's an orphaned bibliography entry — cited by nothing, and
not implemented as a baseline or discussed in Related Work under any
alias. Either the manuscript intended to cite it somewhere (geographic/grid
-based indexing is directly relevant to the Related Work section around
`ref23`-`ref30`) and the `\cite` was dropped, or it's a leftover reference
from an earlier draft that should be removed from the bibliography
entirely. Worth a decision either way — an uncited reference in a
submitted IEEE manuscript is the kind of thing a copy-editor or reviewer
flags.

---

## 3. SEaaS (`ref34`) — not implemented (correctly), but possibly mischaracterized

**Paper** (Ihtesham et al., IEEE Access 2023) is a **multi-keyword
searchable encryption** scheme: DGHV fully-homomorphic encryption over
integers is used only to homomorphically evaluate **keyword-match
predicates** (Algorithm 5, `MultiKS`: subtract ciphertext-hash pairs, test
for zero). The "HE" throughout the paper is about hiding *which keyword
matched*, not about aggregating data values. There is no SUM/COUNT
operation, no numeric field, no range predicate, and no notion of
"aggregating" search results beyond returning a list of encrypted matching
filenames — confirmed across the abstract, system model (Fig. 1), all six
algorithms, and the conclusion.

**Manuscript text** (`Overleaf/BVCRSA:382, 408`):

> "SEaaS~\cite{ref34} integrates searchable encryption with homomorphic
> analytics..."
> "SEaaS~\cite{ref34} **supports encrypted aggregation** but lacks
> conjunctive range search, fine-grained access control, and verifiable
> query processing."

**Gap:** "supports encrypted aggregation" does not match what the SEaaS
paper actually does. SEaaS's homomorphic operation is a **match test**
(ciphertext subtraction to check equality), structurally nothing like
BVCRSA's homomorphic SUM/COUNT over selected records. Table
`tab:feature_comparison` (referenced at the same manuscript location)
should be checked — if it lists SEaaS with a ✓ under an "Aggregation"
column, that checkmark is not supported by the source paper and should be
corrected to ✗, with the text changed to something like "SEaaS applies
homomorphic evaluation to keyword matching, not to aggregation of record
values." This is a citation-accuracy issue, not a missing-implementation
issue — SEaaS correctly has no baseline class, since it doesn't do
conjunctive range search or aggregation and isn't a fair comparison point
for BVCRSA's benchmarks. It just shouldn't be described as doing something
it doesn't.

---

## 4. ECGRQ-LI (`ref15`) — implemented, but completely disconnected

**Paper** (Li, Jia, Du, Ha, IEEE TC 2025) — the scheme SKILL.md already
flags as "cited in Related Work but not one of the four benchmarked
baselines." Confirmed by reading the paper: it's a genuinely different
mechanism from every currently-benchmarked baseline —
- Z-order curve dimensionality reduction,
- a **hierarchical learned index** (small neural nets predicting record
  position from encrypted Z-code, Fig. 3),
- **differential privacy** via Laplace noise added to the *polynomial
  expansion of the objective function's coefficients* (Eq. 3), not to the
  raw output — a specific, deliberate mechanism to avoid the accuracy loss
  of naive output-perturbation,
- symmetric-key **predicate encryption** (Shen-Shi-Waters SHVE-family,
  `ref24` in that paper) as the underlying comparison primitive,
- a **spatial segmentation algorithm** (Algorithm 2) that splits a query
  region across grid partitions to avoid touching irrelevant Z-codes.

**Code status:** `Benchmark/_shared/ecgrq/ecgrq_li.py` (303 lines) actually
implements a recognizable subset —
- `LearnedIndex` class with a real 1-hidden-layer NN and
  `_add_dp_noise()` that adds Laplace noise (`ecgrq_li.py:61-67`,
  explicitly comments "Eq. 3 in paper") — **but noise is added to the raw
  gradients during training**, not to the polynomial-coefficient expansion
  the paper specifies. Functionally similar (both are DP mechanisms
  protecting the learned model) but not the same construction, and the
  paper is explicit that naive gradient/output noise was the thing it was
  trying to avoid.
- `PredicateEncryption` class, self-labeled in a comment as **"simplified
  SHVE-based"** — not real predicate encryption.
- `spatial_segmentation()` — Algorithm 2, present.
- `BTreeIndex` / `BinaryTreeIndex` — stand-ins for the `[12]` comparison
  schemes (Kermanshahi et al.) the ECGRQ-LI paper itself benchmarks
  against.

**The actual gap:** none of this is reachable. `grep -rln "ecgrq"
Benchmark/ | grep -v _shared/ecgrq/` returns **nothing** — no experiment,
no `baselines.py` entry, no `ALL_SCHEMES` membership. The file is dead
code from the moment it was salvaged (per `SKILL.md §8`: "kept only so the
learned index can be promoted to a baseline if a reviewer asks"). If a
reviewer does ask why a learned-index comparison is absent given it's
prominently discussed in Related Work, there's a half-built answer sitting
in the repo that was never finished or benchmarked — worth knowing before
that question is asked, not after.

---

## Summary table

| Paper | Cited in text? | Implemented? | Wired into any benchmark? | Main issue |
|---|---|---|---|---|
| Trinity (`ref26`) | Yes, heavily | Yes — both variants | **Only Trinity-I** | Trinity-II (the paper's actual contribution) is built but never run; manuscript doesn't disclose which variant is compared |
| EPBRQ (`ref31`) | **No** | No | No | Orphaned bibliography entry — never `\cite`'d anywhere in the body |
| SEaaS (`ref34`) | Yes, Related Work only | No (correctly) | No | Text claims it "supports encrypted aggregation" — the paper has no aggregation, only homomorphic keyword-match testing |
| ECGRQ-LI (`ref15`) | Yes, Related Work only | Partial (simplified PE, gradient-noise DP instead of coefficient-noise DP) | **No** — completely unwired | Sitting dead in `_shared/ecgrq/`, not defensible as "already covered" if a reviewer asks about it |

No code or manuscript text was changed to produce this report.

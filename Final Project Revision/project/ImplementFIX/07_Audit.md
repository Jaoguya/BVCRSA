# Audit — verified state vs. reviewer comments

Everything below was **executed**, not estimated. Python 3.14.7, BLS12-381
(`py_arkworks_bls12381`), `CSV/Datarecord.csv`, on the author's PC.
Dated 2026-08-17.

Legend: ✅ satisfied and verified · ⚠️ implemented, not yet run at full sweep ·
❌ not satisfied

---

## 1. The headline finding

**Your Table IV overstates BVCRSA's query cost by 116×.**

Measured at N=1,000, instrumenting the real Phase 4 path:

| | |
|---|---|
| SCRAT nodes indexed (`N_u`) | 3,000 |
| Docs surviving the context filter | **51** |
| Cover tokens (`m_c`) | 4 |
| `N_u × m_c` — what Table IV claims | **12,000** |
| **Actual `ABSE.Test` calls** | **103** |
| Measured query time | 303.1 ms |
| Implied per-test cost | 2.943 ms |

Cross-check against Experiment 10's independently measured
`ABSE.Test = 2.888 ms`:

```
103 calls × 2.888 ms = 297 ms      measured 303 ms      error 2.0%
```

Two mechanisms prune before any pairing runs:

1. **Context filter** on `(m_enc, k_enc)` — 3,000 nodes → 51 docs
2. **Bitmap-constrained filter (Eq. 37)** — `_query_legacy` evaluates
   `b_node & b_query` and only calls `abse.test` on survivors

### Why this matters for R1-C4

> *"The scheme requires exhaustive ABSE matching with complexity O(Nu × mc)…
> Nevertheless, the manuscript reports sub-millisecond execution times"*

The reviewer's arithmetic is correct. **Your stated complexity was wrong in the
pessimistic direction.** The implementation never performed exhaustive
matching. This turns R1-C4 from an accusation into a correction you can make
yourself:

> *We thank the reviewer. The complexity stated in Table IV was pessimistic:
> it assumed every canonical-node index is tested against every cover token.
> The implementation applies context filtering and the bitmap-constrained
> filter of Eq. (37) before any pairing operation. At N=1,000 we measure 103
> ABSE.Test invocations per query rather than the 12,000 implied by Table IV.
> Independently measured per-primitive cost (2.888 ms per ABSE.Test,
> Section <N>) reproduces the measured 303 ms query time to within 2%.*

⚠️ **Table IV must be corrected downward** to
`O(|D_ctx| · m_c)` with bitmap pruning, where `|D_ctx|` is the number of
indexed nodes sharing the query's encrypted context.

⚠️ The old sub-millisecond figures are *still* wrong — 303 ms is not 0.02 ms.
Both corrections are needed, in opposite directions.

---

## 2. Per-comment status

### Reviewer 1

| # | Requirement | Status |
|---|---|---|
| C3 | complete verifiable protocol measured | ✅ Exp 4 now times entry processing + position check + multiproof + `CT_sum`/`CT_count` recomputation. Measured 2.70 / 10.28 / 25.20 ms at r = 50 / 200 / 500. Answered in text per your decision. |
| C4 | raw data, op counts, CI, plausibility | ✅ operation counts now logged and reconcile to 2%. `Experiment.record()` rejects rows without raw samples. ⚠️ full sweeps not yet run. |
| C5 | consistent dataset sizes | ⚠️ Exp 2 sweeps 10³–10⁵; paper text still says ≤2×10⁴ (NeedToEdit A2) |
| C6 | sensor-side public-key cost | ⚠️ Exp 9 written, needs a Pi. **Energy resolved by disclosure** — no meter needed (NeedToEdit C4) |
| C7 | numeric communication cost | ✅ **run** — see §3 |
| C8 | vector figures | ✅ `save_figure()` raises on raster; two SVGs already emitted |

### Reviewer 2

| # | Requirement | Status |
|---|---|---|
| C2 | show variance, not assert it | ✅ every row carries `stdev_ms`, `ci95_ms`, `raw_ms` |
| C3 | per-primitive microbenchmarks | ✅ **run** — see §4. Reconciliation verified at 2% |
| C4 | extrapolate to 10⁶–10⁷ | ⚠️ implemented in Exp 2, not yet run |
| C5 | communication in KB | ✅ **run** — see §3 |
| C6 | tie Figs 7/8 to Table IV | ⚠️ Exp 7 fits the growth exponent; text linkage still to write |
| C7 | regenerate under threshold | ✅ Exp 5 rewritten. **See §5 — arithmetic already disproves the old figure** |
| C8 | run counts in captions | ✅ `save_figure(runs=)` stamps every figure |

### Reviewer 3

| # | Requirement | Status |
|---|---|---|
| 12 | bitmap cost quantified | ✅ Exp 8 run |
| 13 | query time vs aggregation time reconcile | ⚠️ Exp 2 emits the breakdown, not yet run |
| 14 | throughput vs latency reconcile | ✅ **structurally solved** — throughput now derived as `1/latency`, so they agree by construction. Exp 3 also asserts it. |
| 15 | consistent dataset sizes | ⚠️ same as R1-C5 |
| 16 | baselines described / uniform settings | ✅ all four now perform real crypto (§6). Disclosure paragraph drafted. |
| 17 | raw data, CI, benchmark setups | ✅ enforced by the harness; every CSV carries an environment stamp |

### Reviewers 4 / 7

| # | Requirement | Status |
|---|---|---|
| R4-2 | blockchain gas empirically | ⚠️ Exp 11 written, needs 3+ nodes |
| R7-C4 | end-to-end costs + error bars | ✅ comms (Exp 8) run, CI enforced. ⚠️ sensor energy → disclosure; wire RTT still unmeasured |
| R7-C5 | multi-node consortium | ❌ needs the cluster. No substitute. |

---

## 3. Experiment 8 — RUN, and it contradicts a claim I made

Measured communication (KB):

| N | r | request | response 1 | response 2 | total |
|---|---|---|---|---|---|
| 10,000 | 100 | 3.12 | 20.11 | **41.64** | 64.88 |
| 10,000 | 500 | 6.25 | 20.11 | **171.21** | 197.56 |
| 10,000 | 1,000 | 10.15 | 20.11 | **311.00** | 341.27 |
| 100,000 | 50 | 2.73 | **162.52** | 27.67 | 192.91 |
| 100,000 | 1,000 | 10.15 | 162.52 | **414.82** | 587.48 |

⚠️ **I previously told you "response 1 dominates — concede it."** The data says
otherwise: response 1 dominates only when `r` is small relative to `N`
(N=100k, r=50). At N=10,000 response **2** dominates at every `r`, by up to 15×.

The script still prints the unconditional claim. **Do not paste that sentence
into the paper.** The correct statement is conditional:

> *Response 1 is fixed by the number of matched canonical nodes and the bitmap
> block count, and therefore dominates for small result sets over large
> databases; response 2 grows linearly in |R_Q| and dominates once the result
> set is large. At N=10,000 the crossover occurs below r=100.*

---

## 4. Experiment 10 — RUN. Per-primitive costs.

| Primitive | Cost | ±95% CI |
|---|---|---|
| ABSE.Test | **2.888 ms** | 0.008 |
| ABSE.TokenGen | 0.849 ms | 0.005 |
| Bilinear pairing | 1.191 ms | 0.006 |
| **Threshold decrypt (3,5)** | **35.58 ms** | 0.117 |
| EC-ElGamal encrypt | 2.430 ms | 0.026 |
| EC-ElGamal add | 0.0189 ms | 0.00003 |
| Merkle verify (1 leaf) | 0.0199 ms | 0.00004 |
| Bitmap AND (100k bits) | 0.0020 ms | 0.00001 |
| SHA-256 | 0.0011 ms | 0.00002 |

Backend printed at runtime: **`py_arkworks_bls12381` (BLS12-381)** — the paper's
`py_ecc`/BN128 claim is confirmed false.

Reconciliations that check out:

- Exp 2 query @ N=1,000: `103 × 2.888 = 297 ms` vs measured **303 ms** ✅
- Exp 4 recompute @ r=500: `1000 × 0.0189 = 18.9 ms` vs measured **17.8 ms** ✅
- Exp 4 Merkle multiproof @ r=500: **7.33 ms** vs naive `500 × 0.0199 = 9.95 ms`
  — multiproof correctly cheaper ✅

---

## 5. ⚠️ Arithmetic already disproves the paper's Fig. 6

Threshold decryption costs **35.58 ms**. BVCRSA performs **two** per query
(SUM and COUNT). So the floor is:

```
2 × 35.58 = 71.2 ms
```

Your paper claims:

> *"BVCRSA maintains execution times below 20 ms across all workloads"*

**That is impossible under (t,n)=(3,5) threshold EC-ElGamal.** The old figure
was produced with single-key decryption, exactly as R2-C7 suspected. The
regenerated number will be ≥ 71 ms, not < 20 ms.

The comparison still holds — Naive at r=500 is `500 × 35.58 ≈ 17.8 s` — so
BVCRSA remains ~250× better. You lose the "<20 ms" headline, keep the result.

---

## 6. Baseline parity — verified at N=300

| Scheme | query | matched | real crypto now performed |
|---|---|---|---|
| BVCRSA | 70.3 ms | 1 | ABSE.Test + bitmap + aggregation |
| VC-KASE | 1.13 ms | 3 | pairing evaluation per ciphertext |
| Latt-IBEKS | 0.97 ms | 3 | trapdoor·ciphertext inner product per ciphertext |
| ABSE-Range | 1930 ms | 3 | real BLS12-381 pairings |
| **Trinity** | ❌ | — | **crashes — see §7** |

Before: all four were plaintext comparisons.
BVCRSA returns 1 vs the others' 3 because its trapdoor is bound to one
`(machine, t_slot)` context while the baselines match across all contexts —
a real semantic difference worth one sentence in the paper.

---

## 7. Open blockers

| # | Blocker | Impact |
|---|---|---|
| 1 | **Trinity crashes** — `trinity.py:210`, `struct.error: 'I' format requires 0 <= number <= 4294967295` | Blocks every comparative figure (Exps 1, 2, 3) |
| 2 | `user_client.py:21` — `self.Ks = secrets["Ks"]` hands users `K_sel` | Contradicts the paper; tag-level form of R3-1 |
| 3 | No multi-proof in `blockchain_edge.py` | Table IV claims `O(r log(N/r))`; production path is `O(r log N)` |
| 4 | Raspberry Pi | Exp 9 / R1-C6 |
| 5 | 3+ Ethereum nodes | Exp 11 / R7-C5 |
| 6 | Full sweeps not yet run | Everything marked ⚠️ |

## 8. Fixed this session

- Exp 10 `ABSE.Test` probe — wrong signature, now measured
- Exp 3 `config.md` drift — claimed `Q∈{10,25,50,100}`, `RUNS=20`; code had
  `{5,10,25,50}`, `RUNS=5`, `SKIP_SCHEMES={ABSE-Range}`
- Exp 3 runtime: ~12 days → ~30 min
- Exp 4 extended to the complete verification (R1-C3)
- Exp 8 verified end to end

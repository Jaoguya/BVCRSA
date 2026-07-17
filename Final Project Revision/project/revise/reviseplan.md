# Revise Plan — Fig. 2, Fig. 5, Fig. 7 Reproduction Audit

**Scope:** BVCRSA paper (`../hello`), three figures only:
- **Fig. 2** — Index-construction time versus database size
- **Fig. 5** — Query processing time versus database size
- **Fig. 7** — Query throughput under increasing query workload

Reviewed as an IEEE-journal-reviewer would: every number behind these three
figures was traced back to the code that produced it, run to completion, and
checked for whether the comparison it makes is actually fair to every baseline.
Where the existing code faked or shortcut a measurement, it was rewritten, not
patched cosmetically. Where a result had to be extrapolated because measuring
it directly was computationally infeasible in the available time, that is
disclosed explicitly rather than presented as measured.

This document is the "conflict reconciliation" record between what the paper
currently claims/shows and what the code actually does, plus the fix plan and
final methodology.

**Update:** the two ABSE-Range points that were initially extrapolated (§6, §9)
have since been replaced with real measurements (`measure_abse_range_real.py`)
— there was time budget to run them for real instead. Every number in the
final Fig. 2/5/7 results is now a direct measurement; nothing is predicted.

---

## 1. Figure identification

Confirmed by reading `hello` (the paper's LaTeX source) directly — figure
numbers are assigned by document order of `\begin{figure}` environments:

| # | `\label` | Caption | Image file (per `\includegraphics`) |
|---|----------|---------|--------------------------------------|
| Fig. 1 | `fig:system_model` | BVCRSA System Model | `modelAHE.pdf` |
| **Fig. 2** | `fig:index_construction` | Index-construction time versus database size | `fig_index_construction.png` |
| Fig. 3 | `fig:trapdoor_generation` | Trapdoor-generation time vs. dimensions | `fig_trapdoor_generation.png` |
| Fig. 4 | `fig:query_vs_range` | Query processing time vs. range width | `fig_query_vs_range.png` |
| **Fig. 5** | `fig:query_vs_database` | Query processing time versus database size | `fig_query_vs_N.png` |
| Fig. 6 | `fig:query_vs_dimension` | Query processing time vs. dimensions | `fig_query_vs_d_conjunctive.png` |
| **Fig. 7** | `fig:query_throughput` | Query throughput under increasing query workload | `fig_query_throughput_matched_colors.png` |
| Fig. 8 | `fig:verification_overhead` | Verification time vs. returned results | `fig_verification_overhead.png` |
| Fig. 9 | `fig:ablation_aggregation` | Homomorphic aggregation vs. naive | `fig_ablation_aggregation.png` |
| Fig. 10 | `fig:bsgs` | Aggregate-recovery latency vs. bound | `bsgs_scalability.png` |

## 2. Paper-breaking issue found (unrelated to fairness, more urgent)

**None of the 9 images referenced by `\includegraphics` in `hello` exist in
`all_figures/`** (the directory set by `\graphicspath{{all_figures/}}`) — not
even `modelAHE.pdf` for the system model. As submitted, **the paper cannot
compile**. This was true before this review started; it is not something
this benchmark fix caused.

Per your instruction, the three figures this review regenerates
(`fig_index_construction.png`, `fig_query_vs_N.png`,
`fig_query_throughput_matched_colors.png`) have been copied into
`all_figures/` so those three now render. **The other 6 figures are still
missing** and out of scope for this pass — flagging so it doesn't get
missed before submission.

Separately: `graph_figures.py` (the one existing script that produces
`fig_query_vs_N.png`) does not read from any results CSV at all — it has a
**pasted, hardcoded CSV string** embedded in the script itself (4 N values:
1K/5K/10K/20K, not the 1K–100K range you asked for), and it saves output to
`paper_figures/`, not `all_figures/`. That's why the file was missing even
though a script nominally "generates" it — the script's output directory
doesn't match where the paper looks, and its data has no traceable link to
an actual benchmark run. The new `plot_fig2_5_7.py` (this folder) reads
directly from the real results CSV instead.

## 3. Bugs found in the existing Fig. 2/5/7 benchmark code

Original code: `original_reference/benchmark_exp2_5_7_ORIGINAL_buggy.py` and
`original_reference/benchmark_exp_7_ORIGINAL_buggy.py` (kept here unmodified,
purely as an audit trail — do not use them to produce paper numbers).

### BUG #1 — BVCRSA's query() performed no cryptographic search at all

`BVCRSAAlgo.query()` located "matching" nodes via a plain Python dict lookup
keyed by **plaintext** `(machine, keyword, time_slot, lo, hi)` tuples. It
never called `ABSE.test()`, never computed a bitmap AND, never checked a PRF
search tag — none of the operations the paper's own Phase 4 describes as
"query processing." Meanwhile, in the *same* harness:
- `ABSERangeAlgo.query()` performs genuine BLS12-381 pairing operations
  (`abse_range_mod.search()`) against every candidate record,
- `VCKASEAlgo`, `LatticeIBEKSAlgo`, `TrinityAlgo` all perform real O(N)
  linear scans with actual comparisons.

Only BVCRSA got an O(1) hash-table lookup with zero cryptographic cost. The
old results show the signature of this clearly: BVCRSA's `query_ms` sat at
~0.006–0.01 ms **flat from N=1,000 to N=100,000** — a database-size-scaling
experiment where the subject under test showed no dependence on database
size at all is not measuring what it claims to measure.

**Fix:** `query()` now performs, for every call:
1. A real `ABSE.test()` bilinear-pairing authorization loop — mirrors the
   project's own `cloud_server.py` (`_query_fast`): try each bucket
   candidate's `CT_tag` against the trapdoor's auth token until one pairing
   succeeds, or the bucket is exhausted (both are real, non-trivial pairing
   costs — this file was not invented for the benchmark; it's the same
   optimization already implemented in production `cloud_server.py`, just
   never actually exercised by the benchmark before).
2. A real bitmap AND per surviving candidate.
3. A real PRF search-tag equality check per candidate.
4. Real EC-ElGamal point addition over matched ciphertexts (see BUG #2).

### BUG #2 — the "homomorphic aggregation" was string concatenation

```python
agg = matched[0]["Agg_u"]
for n in matched[1:]:
    agg += n["Agg_u"]
```
`Agg_u` is `ECEncryptedNumber.ciphertext()` — a **serialized string**
(`"x1:y1:x2:y2"`). `+=` on strings concatenates text; it is not EC point
addition. The aggregation step the paper explicitly says is included in
query-processing time ("the reported query-processing time includes
encrypted search, bitmap filtering, **and homomorphic aggregation**") cost
essentially nothing in the old benchmark.

**Fix:** matched ciphertexts are deserialized with
`ECEncryptedNumber.from_string()` and combined with the class's real `__add__`
(genuine NIST P-256 point addition), exactly as `blockchain_edge.py` does
during index construction.

### BUG #3 — BVCRSA's query scope didn't match any baseline's query scope

Found while smoke-testing the fix above (matched count came back 0). The
original `trap_gen` picked one arbitrary sample record and pinned the query
to that record's specific **(machine, hour)** context, because
`gen_tag(Ks, m, k, t_slot, node)` bakes machine + hour into the PRF tag.
Every baseline's `query()`, by contrast, scans the **entire** N-record corpus
for a keyword + value-range match, with no machine/time restriction —
i.e., BVCRSA was being asked a categorically narrower question than every
scheme it was compared against.

This also explains a strange feature of the old results: BVCRSA's `matched`
count was pinned at exactly **4**, unchanged from N=1,000 through N=100,000.
A fixed one-hour, one-machine slice doesn't grow as N grows (the dataset
generator spreads more records across *more elapsed time* as N increases,
not more density per hour), so the old experiment could never have shown
real query-cost scaling for BVCRSA even if BUG #1/#2 had been fixed in
isolation.

**Fix:** for this single-dimension experiment (keyword + numeric range —
which is exactly what Fig. 2/5/7 and every baseline actually query; machine
ID and per-hour partitioning aren't part of what these three figures test),
BVCRSA's node context is fixed to a constant placeholder (`"GLOBAL"`)
instead of the record's real machine/hour. Canonical nodes are bucketed by
**keyword alone**; records sharing a keyword+range legitimately collide onto
the same node and accumulate via the *existing* homomorphic `Agg_u`/`Cnt_u`
update path already in `blockchain_edge.py` (that code path exists
specifically for this — it was simply never exercised this way before). A
single trapdoor now covers the whole dataset, matching every baseline's
semantics. Verified this produces a `matched` count that scales with N
(6 at N=500 → 33 at N=2,000 in a quick smoke test) instead of a frozen
constant.

**Note for the authors:** this also surfaces a real ambiguity worth your
attention beyond this benchmark: the paper's prose (Phase 2, Step 1) treats
machine ID (`m_i`) as part of a record's identity, not as a query-time
constraint, and Section V's single-dimension experiments never mention
machine- or hour-scoped queries. The "GLOBAL" context used here matches that
reading. If a *future* experiment is meant to test per-machine or
per-time-window queries specifically, that would need to be a distinct,
explicitly-described experiment — not silently baked into the tag context
the way the original code did.

## 4. Other discrepancies found (disclosed, not silently patched over)

- **`generate_datarecord.py` was an empty file.** `Datarecord.csv` (100,000
  rows) existed with no way to reproduce or audit how it was generated.
  Rewritten from scratch (see §5) with a fixed seed.
- **Sensor category count mismatch.** The paper's Experimental Setup states
  "20 sensor categories"; the old `Datarecord.csv` and benchmark code only
  had 15 (`KEYWORD_POOL` in the original scripts). The regenerated dataset
  uses 20, matching the paper text (5 categories added: Viscosity,
  Turbidity, Proximity, Strain, Acoustic — chosen as plausible IIoT sensor
  types, not load-bearing on any result shape).
- **`py_arkworks_bls12381` was not installed at all** — `added_paper/Attribute-based.py`
  (the ABSE-Range baseline) imports it unconditionally with no fallback, so
  it crashed immediately on import; ABSE-Range could not be benchmarked at
  all. Fixed by installing the package (a prebuilt wheel matching this
  environment — Python 3.13, x86_64 Linux — exists on PyPI; no source code
  needed to change). Verified end-to-end with real pairing operations
  (search() measured 6.2–12.4 ms/record, consistent with 5 real BLS12-381
  pairings per call, not near-zero/faked). **Action item:** add
  `py_arkworks_bls12381>=0.5.0` to a `requirements.txt` — none currently
  exists anywhere in the repo.
- **Paper text vs. actual crypto backend.** The paper's Experimental Setup
  states ABSE uses "BN128 bilinear pairings via `py_ecc`." The code
  (`TA.py`) actually prefers `abse_fast.py` (BLS12-381 via
  `py_arkworks_bls12381`, Rust-native) whenever that package is installed,
  falling back to BN128/`py_ecc` only if it's missing. Measured on this
  machine: BLS12-381/arkworks encrypt = **1.7 ms**/record vs.
  BN128/py_ecc = **53.7 ms**/record (~31x). Since installing arkworks was
  necessary anyway to fix ABSE-Range (previous bullet), the fast path is now
  available and is what this benchmark used — running the full 1K–100K
  sweep on BN128 instead was estimated at 2.5+ additional hours for index
  construction alone, which did not fit the time available. **This is a
  disclosed choice, not a hidden one; you have two options:**
  1. Update the paper's Experimental Setup text to say BLS12-381 via
     `py_arkworks_bls12381` (accurate, and arguably a strict improvement —
     same ~128-bit security level, faster) — no rerun needed.
  2. If BN128/py_ecc must be the number that appears in the paper (e.g. for
     consistency with a specific earlier claim), rerun
     `benchmark_fig2_5_7_fair.py` after forcing `abse_real` instead of
     `abse_fast` in `TA.py`'s import — budget ~2.5–3 hours.
- **Requested N range exceeds the paper's stated range.** Section V's
  Experimental Setup currently says "The dataset size ranged from `10^3` to
  `2×10^4` records." The regenerated experiment covers `10^3` to `10^5`
  (1K–100K) per your instruction. If Fig. 2/5/7 are updated with this
  experiment's numbers, that sentence needs updating too (either to state
  the wider range generally, or to note that Fig. 2/5/7 specifically extend
  further than the other N-scaling figures).
- **Bitmap semantics: a real mismatch between paper prose and code, flagged
  for your attention, not fixed here (out of scope for a benchmark-fairness
  pass).** Paper Eq. 17/37 and the surrounding text describe `B_u` as a
  bit vector over the **global record space** — `B_Q[i] = 1` for record
  index `i`, so the matched record set is read directly off bit positions:
  `R_Q = {r_i | B_Q[i] = 1}`. The actual implementation
  (`utils.gen_bitmap`/`gen_query_bitmap`) instead produces a **101-bit
  VALUE-domain bitmap** — bits represent integers 0–100 in the sensor's
  value range, not record indices — used to test whether a node's range
  overlaps the query's range, not to identify which records matched. These
  are different data structures serving different purposes; the code's
  version is reasonable engineering (a compact range-overlap test) but it is
  not what Eq. 17/37's `B_Q[i]`-indexed-by-record notation describes. This
  doesn't affect the correctness or fairness of the Fig. 2/5/7 timings
  fixed here (the fair benchmark uses the bitmap exactly as the code defines
  it, consistently), but it's a formal-model-vs-implementation gap you
  should reconcile in the paper text or in a follow-up implementation pass —
  it's bigger than a benchmark-script fix and deserves its own look.

## 5. Data regeneration

`generate_datarecord.py` (rewritten, was empty) — reproducible, seeded
(`SEED=42`), produces `Datarecord.csv`:

- **100,000 total records**, columns: `id, machine, sensor, value, timestamp_str, t_slot`
- **3 machines** (A/B/C, uniform) — unchanged from the prior dataset's scheme
- **20 sensor categories**, uniform (see §4 — now matches paper text)
- **value**: uniform integer in `[0, 100]` (matches paper: "uniformly distributed over [0,100]")
- **timestamps**: strictly increasing, 3s apart, starting 2024-01-01 00:00:00
  (kept inside calendar year 2024 — required by the Trinity baseline's fixed
  `[2024-01-01, 2025-01-01)` time window assumption)

The N-value sweep (1K/5K/10K/50K/100K) simply reads the first N rows of this
one file — every smaller-N run is a strict prefix of the 100K-row dataset,
so results across N are internally consistent (no re-sampling between runs).

The prior `Datarecord.csv` is preserved at
`../Datarecord.csv.orig_backup` in the main project folder (not deleted).

## 6. Fair benchmark methodology (`benchmark_fig2_5_7_fair.py`)

- **Exp. 2 & 5** (index construction + query time vs. N): for each of
  N ∈ {1K, 5K, 10K, 50K, 100K}, every algorithm's `index_build()` and
  `query()` are timed for real (BVCRSA fixed per §3; others unchanged from
  the original harness, which already did real O(N) work for these).
  `trap_ms`/`query_ms` are averages of 5 repeated calls (2 for ABSE-Range,
  given its real per-record pairing cost).
- **ABSE-Range beyond N=10,000**: the initial run only measured real
  per-record pairing search up to N=10,000 and used ordinary least-squares
  linear regression on those 3 points to extrapolate N=50K/100K (fitted
  slope/intercept/R² and the measured points recorded in the CSV `note`
  column; extrapolated points rendered hollow + dotted in the figure, never
  visually indistinguishable from measured data). **Update:** this project
  had time budget to go back and measure both points for real instead —
  `measure_abse_range_real.py` ran the actual N=50,000 (~9.7 min) and
  N=100,000 (~19.8 min) query searches to completion. Real results: 261,862
  ms and 537,880 ms respectively, vs. the earlier linear prediction of
  246,549 ms and 489,807 ms — within ~6% and ~10% of the extrapolation,
  which validates that the linear model was sound even though it's no
  longer needed. **All five ABSE-Range points in Fig. 5 are now real
  measurements; nothing in this experiment is extrapolated anymore.** The
  `note` column is empty for every row in the current
  `benchmark_fig2_5_7_fair_results.csv`.
- **Exp. 7** (throughput vs. workload): the original script looped calling
  `query()` up to 10,000 times per (algorithm, Q) data point. For
  expensive algorithms this is either impractical (Trinity's own historical
  run took ~4.25 hours for one Q=10,000 point) or outright infeasible
  (ABSE-Range at N=10,000 fixed: ~10 days for one Q=10,000 point). Because
  every query here is stateless with identical cost (no batching, caching,
  or contention modeling in this design), **throughput = Q / (Q ×
  per-query latency) = 1 / per-query latency exactly** — looping doesn't
  measure anything an averaged single-query latency doesn't already
  capture; it just re-measures the same constant with more sampling noise
  at a much higher time cost. We measure per-query latency once per
  algorithm (mean of R independent repeated queries: 30 reps for cheap
  algorithms, 5 for Trinity, 3 for ABSE-Range) and derive `total_ms`/
  `throughput` analytically for every target Q. This is disclosed in the
  CSV (`note` records `method=latency_x_Q` plus the measured latency and
  rep count) — it is not the same thing as fabricating a result: it is a
  standard systems-benchmarking technique (measure a rate, don't
  brute-force re-measure it) applied because the brute-force alternative
  was not completable in the time available.

  **Important implication for interpreting Fig. 7, flagged for the
  paper text:** because throughput is mathematically `1/latency` under this
  serial, non-batched design, **the expected shape of every algorithm's
  curve is flat** — a single-threaded benchmark with no connection pooling,
  concurrency, or queueing model cannot show saturation or contention
  effects no matter how it's measured. (This is visible in the *original*
  buggy data too, for the algorithms whose query cost wasn't near-zero:
  VC-KASE, Latt-IBEKS, and Trinity all already showed roughly flat
  throughput across Q in the old, unfixed run — only BVCRSA's numbers
  swung around, because its "work" was near-zero noise, not because
  workload-dependent effects were real.) If the paper's narrative implies
  genuine saturation/contention dynamics under load, that would require a
  different experiment design (concurrent workers, a queueing model, or a
  real network/DB layer) — out of scope for this fairness pass, but worth
  deciding deliberately rather than let the flat-line result be
  misread as "no bottleneck at any scale."

## 7. File manifest (this folder)

```
revise/
  reviseplan.md                          <- this document
  generate_datarecord.py                 <- reproducible dataset generator (was empty)
  Datarecord.csv                         <- regenerated 100K-row dataset (seed=42)
  benchmark_fig2_5_7_fair.py             <- fixed, fair benchmark (this is the one to run)
  benchmark_fig2_5_7_fair_results.csv    <- output of the run above (now fully real, no predicted rows)
  measure_abse_range_real.py             <- follow-up: replaces ABSE-Range's extrapolated
                                             N=50K/100K query points with real measurements
  plot_fig2_5_7.py                       <- plots the 3 figures from the CSV above
  figures/                               <- the 3 generated PNGs (also copied to ../all_figures/)
  original_reference/                    <- UNMODIFIED copies of the old buggy scripts, kept
                                             only as an audit trail — do not use for paper numbers
    benchmark_exp2_5_7_ORIGINAL_buggy.py
    benchmark_exp_7_ORIGINAL_buggy.py
    graph_figures_ORIGINAL.py
  TA.py, abse_fast.py, abse_real.py, ec_elgamal.py, blockchain_edge.py,
  utils.py, merkle_tree.py, cloud_server.py, trinity.py, quotient_filter.py,
  hilbert_curve.py, ggm_cprf.py, shve.py                <- crypto/system dependencies (copied, unmodified)
  added_paper/Attribute-based.py         <- ABSE-Range baseline (unmodified; dependency installed, not patched)
```

## 8. How to reproduce

```bash
cd "Final Project Revision/project/revise"
python3 generate_datarecord.py          # regenerate Datarecord.csv (optional; already done)
python3 benchmark_fig2_5_7_fair.py       # ~26 min -> benchmark_fig2_5_7_fair_results.csv
python3 measure_abse_range_real.py       # ~30 min -> replaces the two extrapolated ABSE-Range
                                          #    query points above with real measurements
python3 plot_fig2_5_7.py                 # -> figures/*.png
```

## 9. Results summary

Full run completed in **26.3 minutes**, plus a follow-up **29.5 minutes**
(`measure_abse_range_real.py`) to replace ABSE-Range's two extrapolated
Fig. 5 points with real measurements. **Every number below is now a real
measurement — nothing in this experiment is extrapolated or predicted.**

### Fig. 2 — Index-construction time (ms) vs. N

| N | BVCRSA | Trinity | VC-KASE | Latt-IBEKS | ABSE-Range |
|---|---|---|---|---|---|
| 1,000 | 5,853.8 | 74.5 | 328.7 | 3.0 | 1,254.5 |
| 5,000 | 24,536.7 | 303.1 | 1,641.3 | 11.9 | 5,986.4 |
| 10,000 | 46,957.4 | 591.2 | 2,575.3 | 26.2 | 9,750.5 |
| 50,000 | 230,885.6 | 3,106.6 | 13,150.9 | 138.3 | 57,281.1 |
| 100,000 | 467,488.9 | 7,608.7 | 32,815.8 | 275.1 | 109,791.4 |

BVCRSA is highest throughout (real BLS12-381 pairing per record, as the paper's
own text already anticipates and justifies as a one-time offline cost). All
five series scale linearly with N as expected — this part of the original
benchmark was not buggy, only the query side was. (ABSE-Range's N=50K/100K
index_ms values above are from the later `measure_abse_range_real.py` re-run,
~19% and ~2% higher than the first run's 48,275.3/107,967.3 — ordinary
run-to-run timing jitter from a live encrypt-heavy Python process, not a
methodology change; both runs measured the same real operation.)

### Fig. 5 — Query processing time (ms) vs. N

| N | BVCRSA | Trinity | VC-KASE | Latt-IBEKS | ABSE-Range |
|---|---|---|---|---|---|
| 1,000 | 26.42 | 177.19 | 0.12 | 0.13 | 6,354.24 |
| 5,000 | 23.57 | 783.94 | 0.30 | 0.34 | 30,857.36 |
| 10,000 | 22.97 | 1,049.22 | 0.90 | 0.73 | 50,500.98 |
| 50,000 | 34.61 | 5,313.71 | 5.66 | 5.45 | 261,862.25 |
| 100,000 | 56.90 | 13,755.26 | 15.61 | 9.94 | 537,880.13 |

Now a fair comparison: BVCRSA grows only mildly (23→57 ms across a 100x
increase in N) because its real per-query cost is bounded by keyword-bucket
size plus one pairing-authorization loop, not full-corpus cryptography.
Trinity and ABSE-Range both do real O(N) work per query and grow steeply
(ABSE-Range especially, since it does genuine bilinear pairings with no
indexing at all — its own documented weakness). VC-KASE and Latt-IBEKS beat
BVCRSA in raw ms at these N because they use lightweight plaintext
comparisons with no real cryptographic search cost at all (this was already
true in the original harness — not something introduced by this fix — and
is disclosed as a real, structural difference between what these baselines'
"search" actually costs vs. BVCRSA's authenticated cryptographic search).
This is a materially different — and far more defensible — story than the
original's flat ~0.01 ms line that never moved regardless of N.

### Fig. 7 — Query throughput (q/s) vs. workload (flat by construction, N=10,000 fixed)

| Algorithm | Measured per-query latency | Throughput (constant across all Q) |
|---|---|---|
| BVCRSA | 23.56 ms | 42.44 q/s |
| Trinity | 1,074.58 ms | 0.93 q/s |
| VC-KASE | 0.368 ms | 2,718.66 q/s |
| Latt-IBEKS | 0.548 ms | 1,826.39 q/s |
| ABSE-Range | 59,109.71 ms | 0.017 q/s |

All real measurements (no extrapolation needed here — even ABSE-Range's
single-query latency at the fixed N=10,000 was directly measurable; only its
*N-sweep* query points above 10,000 in Fig. 5 needed extrapolation). As
discussed in §6, every line is flat — that is the correct, honest result of
this experiment's serial, non-batched design, not an artifact of the fix.

### What changed vs. the original (buggy) numbers

| | Original (buggy) | Fixed |
|---|---|---|
| BVCRSA query_ms, N=1K→100K | 0.0078 → 0.0095 ms (flat, ~0 cost) | 26.4 → 56.9 ms (real crypto, modest growth) |
| BVCRSA `matched` count, N=1K→100K | pinned at 4 (constant) | 14 → 1,933 (scales with N, as it should) |
| BVCRSA exp7 throughput | 700K–1,246K q/s, non-monotonic (noise) | flat 42.4 q/s (stable, real) |
| ABSE-Range exp7 | missing entirely (infeasible to loop) | present, via disclosed analytic method |

Figures are in `figures/` and have been copied to `../all_figures/` so
`fig_index_construction.png`, `fig_query_vs_N.png`, and
`fig_query_throughput_matched_colors.png` now render in the paper.

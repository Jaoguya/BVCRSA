# Reviewer 2

**Verdict: MAJOR REVISION** — eight follow-up comments, several noting the
previous response letter asserted things it did not show.

## Summary of position

The recurring theme: *claims were asserted rather than demonstrated.* Three
separate comments (1, 2, 3) say some version of "the response says X but I
cannot find where X was actually done." Cheap to fix, but currently unfixed.

---

## R2-C1 — Adopted vs. novel components never stated plainly

> Response to Comment 1 says the distinction between adopted and novel
> components was clarified "throughout the Introduction, Related Work, and
> Contributions," but I could not locate a single place where this is stated
> plainly. Scattering it across three sections is not the same as answering
> the request. A two- or three-sentence block stating exactly what is reused
> vs. new would take the authors five minutes and would resolve this cleanly.

**Type:** presentation. **Severity: trivial — do it immediately.**

### Fix

Add one explicit paragraph at the end of §I (Introduction), before the
contributions list. Draft:

> *BVCRSA reuses the following existing primitives without modification:
> attribute-based searchable encryption, lifted EC-ElGamal with `(t,n)`
> Shamir threshold decryption and Chaum–Pedersen DLEQ proofs, Merkle
> commitment trees, and permissioned blockchain anchoring. The novel
> contributions are: (i) the authenticated hierarchical range-cover index
> combining canonical interval decomposition with versioned, block-partitioned
> protected bitmaps; (ii) the bitmap-aware encrypted aggregation mechanism
> binding each authenticated bitmap position to a unique aggregation entry;
> and (iii) Verifiable Query-State Anchoring (VQSA).*

Verify against the final contributions list before submitting.

---

## R2-C2 — "Negligible variance" is asserted, not shown

> The claim that "run-to-run variance was negligible" (response to Comment 2)
> is asserted, not shown. If it is truly negligible, reporting it costs
> nothing that a std-dev column in Tables/Figs would settle the matter.

**Type:** experimental reporting. **Severity: easy.**
Also R1-C4, R3-17, R7-C4.

### Fix

Structural, so it cannot be forgotten:

- `_shared/baselines.timed()` returns
  `mean / median / stdev / ci95 / min / max / raw_ms`.
- `harness.Experiment.record()` **raises** if handed a bare mean.
- Every result CSV carries a `stdev_ms` and `ci95_ms` column plus the full
  raw sample list as JSON.
- Every figure draws 95 % CI error bars.

⚠️ If variance turns out **not** to be negligible, report it anyway. The
reviewer asked for the number, not for a particular answer.

---

## R2-C3 — Sub-ms latency in Python still unexplained

> My concern about implausibly fast sub-ms latencies for a Python/py_ecc stack
> was not really engaged with. The response repeats that reported numbers
> exclude network/blockchain latency, which I already knew from the first
> submission — that doesn't explain how ABSE.Test + Merkle verify + bitmap
> AND/OR over 100K-bit vectors finishes in well under a millisecond in pure
> Python. I'd like to see per-primitive microbenchmarks (single Test call,
> single pairing, single Merkle verify) so the totals can be checked by hand.

**Type:** experimental validity. **Severity: blocking.** Also R1-C4.

The reviewer is pointing at a real problem, and the throughput harness proved
it: the old script was measuring dictionary lookups, not queries.

### Fix — **Experiment 10**

`Benchmark/10_Primitive_Microbench/experiment.py` measures one call to each
of: bilinear pairing, `ABSE.Test`, `ABSE.TokenGen`, single Merkle verify,
SHA-256, HMAC-SHA256, **bitmap AND over 100k bits** (named explicitly by this
comment), bitmap AND + popcount, EC-ElGamal encrypt/add, threshold decrypt.

It then prints a reconciliation block — expected total = operation count ×
unit cost — for each other experiment. **Run it first; it calibrates
everything else.**

### ⚠️ Curve disclosure

The reviewer's plausibility argument assumes "pure Python / `py_ecc`". It may
not be:

- The paper says **`py_ecc` over BN128**.
- `_shared/TA.py` prefers `abse_fast.py`, which is **BLS12-381 via Rust
  `py_arkworks_bls12381`** — roughly 50× faster TokenGen, ~140× faster pairing.
- `verification_overhead_exp.py` imported the Rust library *unconditionally*,
  so it was installed when the numbers were taken.

Experiment 10 prints the live backend. Either correct the text to BLS12-381
or pin `py_ecc`. Disclosing this partly answers the objection — it is a
compiled Rust backend, not pure Python — but the claim in the paper must
match the code either way.

---

## R2-C4 — 100k records is still toy scale

> Extending from 20K to 100K records is a fair partial response, but the
> paper's own Introduction motivates the work with "massive volumes" of
> industrial sensor data — i.e. 100K is still a toy scale relative to that
> framing. An extrapolation using the already-derived O(N log N) bound to,
> say, 10^6-10^7 records would cost the authors nothing computationally and
> would substantiate the scalability claim rather than just gesture at it.

**Type:** scope. **Severity: minor — cheap to satisfy.**

### Fix — **Experiment 2**

`report_extrapolation()` fits `t(N) = c · N · log₂(N)` from the measured
`vs_N` points and projects to 10⁶ and 10⁷, plotted as a dashed continuation
and printed to console.

Label it clearly as **extrapolation, not measurement** — a projected curve
presented as data would be worse than not answering.

---

## R2-C5 — Communication cost is the only purely asymptotic dimension

> Table V and the new communication-cost subsection are still purely
> asymptotic. Every other cost in the paper (index construction, trapdoor gen,
> query, verification, aggregation) is backed by measured numbers from the
> prototype, but communication is the one dimension left as O(·) expressions
> only. I'd like actual KB figures for trapdoor size, first-round response,
> and second-round response at a couple of representative N and |R_Q| values.

**Type:** experimental omission. **Severity: major.** Also R1-C7.

### Fix — **Experiment 8**

Measures exactly the three quantities named: request (trapdoor) size,
response 1, response 2, at `N ∈ {1k, 10k, 100k} × |R_Q| ∈ {50, 100, 500, 1000}`.
Sizes derive from concrete wire encodings, not formulas.

Replace Table V's O(·) cells with `total_kb` at `N = 10,000`, `r ∈ {100, 500}`.

---

## R2-C6 — Figs. 7 and 8 are free-floating

> Figures 7 and 8 (aggregation-strategy comparison, BSGS recovery) are new
> additions in this revision and are not tied back to Table IV/the cost
> derivations anywhere in the text. The response to my original Comment 9/10
> predates these figures, so naturally it doesn't cover them — but as they
> stand now they read as free-floating experiments rather than validation of
> the stated complexity.

**Type:** presentation / argument structure. **Severity: minor.**

### Fix

**Fig. 7 (Exp 6):** add a sentence tying panel (a) to Table IV — the
decryption-call counts are the direct empirical realization of the `O(1)` vs
`O(r)` threshold-decrypt terms in the complexity table.

**Fig. 8 (Exp 7):** `Benchmark/07_Aggregate_Recovery_BSGS/experiment.py`
now fits the growth exponent from the measured points via log-log regression
and prints it:

```
BSGS    exponent = 0.5xx   (theory: 0.5)
Linear  exponent = 1.0xx   (theory: 1.0)
```

That fitted exponent **is** the linkage — it empirically confirms the
`O(√M_max)` bound the complexity analysis asserts. Quote it in the text.

---

## R2-C7 — Were the aggregation experiments regenerated under threshold?

> The switch from single-key EC-ElGamal to (t,n)-Threshold EC-ElGamal (done in
> response to a different reviewer) touches the same aggregation pipeline that
> Figs. 6 and 7 report on. Nothing in the response letter confirms these
> experiments were regenerated under the new threshold scheme. If they
> weren't, the 670.5× number and the decryption-call counts in Fig. 7(a) may
> no longer correspond to the protocol actually described in Phase 5.

**Type:** experimental validity. **Severity: blocking.**

**The reviewer's suspicion is half correct.** Checked against the code:

| Figure | Script | Scheme actually used |
|---|---|---|
| Fig. 7 (Exp 6) | `agg_strategy_benchmark.py` | ✅ **real `(3,5)` threshold** — DLEQ proofs, Lagrange combine, BSGS |
| Fig. 6 (Exp 5) | `benchmark_ablation.py` | ❌ **single-key** `generate_ec_elgamal_keypair` + `priv.decrypt` |

So the 670.5× number is safe; **Fig. 6 is not.**

### Fix

- **Exp 6:** already compliant. State plainly in the text that it runs under
  `(t,n) = (3,5)` threshold EC-ElGamal over NIST P-256 — the reviewer asked
  for confirmation, so give it explicitly.
- **Exp 5:** rewritten against `threshold_ec_elgamal.py` with
  `(t,n) = (3,5)`, `CHOSEN_AUTHORITIES = [1,2,3]`. Each decryption is now 3
  partial decryptions + 3 DLEQ verifications + Lagrange + BSGS. **The numbers
  will move.** Regenerate Fig. 6.

⚠️ Also disclose Exp 6's sampling policy: for `|S_Q| > 150` the conventional
arm is measured on 150 real decryptions and linearly extrapolated. An
undisclosed extrapolation behind the headline 670.5× invites exactly this
kind of challenge (see also R3-17).

---

## R2-C8 — Run count missing from figure captions

> Minor: "20 independent runs" is stated in the Experimental Setup, but I
> don't see this repeated consistently in every figure caption (e.g., Fig. 8).

**Type:** presentation. **Severity: trivial.**

### Fix

`harness.save_figure(fig, name, runs=RUNS)` stamps
*"mean of N independent runs, 95 % CI"* onto the figure itself.

⚠️ And make the captions **true**. The stated 20 is not universal:

| Experiment | Actual |
|---|---|
| Exp 4 (verification) | **300 runs, median reported** — not 20, not a mean |
| Exp 10 (microbench) | 200 runs |
| Exp 9 (sensor) | 50 runs |
| Exp 1, 2, 3, 5, 6, 7, 8, 11 | 20 runs |

State each figure's real count and statistic. A blanket "20 runs" in the
setup is currently false for three experiments.

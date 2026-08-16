# Reviewer 5

**Verdict: MAJOR REVISION** — "several critical issues remain insufficiently
addressed in the revised manuscript."

## Summary of position

Three comments, all **paper-side** — exposition, disclosure, and proof rigour.
No code changes required. The mildest of the negative reviews and the cheapest
to satisfy.

*(Note: the three comments appear twice in the source transcript — a
duplicated paste, not six distinct items.)*

---

## R5-1 — Bitmap reconstruction needs a self-contained procedure

> The bitmap reconstruction workflow needs clearer exposition. The derivation
> of node-specific keys Ku and their ABSE encapsulation should be presented as
> a self-contained, step-by-step procedure.

**Type:** exposition. **Severity: major — but purely editorial.**

The mechanism is currently scattered: `K_u = F(K_sel, D_j ‖ u)` appears in
Phase 2 Step 3; the ABSE encapsulation `C_u^K` in the same equation block; the
mask `PRG(F(K_u, b ‖ ν_{u,b}))` in Step 3's protected-block equation; and
recovery is only implied in Phase 4. A reader must assemble it from four
places.

### Fix

Add one boxed procedure (or a numbered algorithm) collecting the whole
lifecycle end to end:

1. Gateway derives `K_u = F(K_sel, D_j ‖ u)`
2. Gateway encapsulates `C_u^K = ABSE.Enc(PP, K_u, P_u, e_q)`
3. Gateway masks each block:
   `B̃_{u,b} = B_{u,b} ⊕ PRG(F(K_u, b ‖ ν_{u,b}), |B_{u,b}|)`
4. Gateway commits `σ_{u,b}^{bmp}` and folds into `Root_u^{bmp}`
5. User matches `I_u` via `ABSE.Test`, receives `C_u^K`
6. User recovers `K_u = ABSE.Dec(SK_A, C_u^K, e_q)` — **requires `A ⊨ P_u`**
7. User verifies each `σ_{u,b}^{bmp}` against `Root_u^{bmp}` and the anchored
   `Root_{e_q}`
8. User regenerates the mask and unmasks: `B_{u,b} = B̃_{u,b} ⊕ PRG(...)`
9. User intersects across dimensions to obtain `B_Q`

State explicitly at step 6 that `K_sel` is **never** disclosed to users — that
is the property doing the security work, and it is currently easy to miss.

⚠️ Cross-check step 9 against **R3-1**: the resulting `B_Q` must be what binds
`S_Q`, or the authorization bypass stands.

---

## R5-2 — Add a disclaimer on measurement scope and baseline parity

> The experimental results would benefit from more explicit clarification. The
> reported latency excludes network and blockchain overhead, and the
> comparison baselines offer different functionality sets. A clear disclaimer
> and discussion of trade-offs would strengthen the presentation.

**Type:** presentation / honesty. **Severity: minor — do it, it costs nothing.**

### Fix

Add an explicit paragraph at the start of the Performance Evaluation:

- **What is excluded.** Reported latencies are cryptographic computation only.
  Network transmission and blockchain interaction are outside the timed
  region. Every `config.md` now states its timed region precisely.
- **What is now measured separately.** Communication is quantified in
  **Experiment 8** (actual KB); blockchain cost in **Experiment 11** (gas,
  finality, ledger growth) — so these are no longer merely excluded, they are
  reported elsewhere. Point the reader there.
- **Baseline functionality parity.** No baseline supports the full feature
  set, so comparisons cover only shared functionality (index construction,
  trapdoor generation, query processing, verification). BVCRSA carries
  overhead the baselines do not — verification, aggregation binding — and that
  cuts against it on shared metrics. Say so; it makes the wins credible.
- ⚠️ **Baseline simplifications.** `VCKASEAlgo` uses a simulated pairing group
  (modular exponentiation, not real pairings) and `LatticeIBEKSAlgo` uses
  small LWE parameters (`n = 17`, `q = 4093`). Disclose both — see R3-16.

---

## R5-3 — Theorem 2 needs a formal simulator argument

> The security proof for Theorem 2 could be further developed. A more formal
> simulator argument would enhance rigor, and explicitly acknowledging that
> matched canonical nodes U_Q inherently reveal some range semantics would
> improve transparency.

**Type:** proof rigour. **Severity: major.**

Theorem 2 (Conjunctive Query Privacy) currently argues informally from ABSE
token pseudorandomness.

### Fix

Two parts, both required:

1. **Simulator.** Write a real-or-simulated indistinguishability argument: a
   PPT simulator `S` given only the leakage `L_BVCRSA(Q)` produces a
   transcript computationally indistinguishable from a real execution. Show
   what `S` must be given — matched node identifiers, result cardinality,
   access pattern — and reduce distinguishing advantage to ABSE token
   indistinguishability.

2. **Concede the leakage.** State plainly that `U_Q` reveals approximate range
   semantics: canonical nodes correspond to fixed dyadic intervals, so knowing
   which matched bounds the queried range to within one node's granularity.
   ⚠️ This is the same concession **R3-6** demands. Making it explicitly in
   Theorem 2 answers both at once and is far better than being told twice.

The honest version of Theorem 2 is a *weaker* statement than the current one.
Weaker and provable beats stronger and hand-waved.

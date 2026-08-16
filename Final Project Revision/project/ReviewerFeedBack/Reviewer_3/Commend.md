# Reviewer 3

**Verdict: REJECT** — the harshest review.

> Rejected in the present form. The manuscript necessitates a redesign of the
> protocol, a definitive ABSE implementation, updated security proofs,
> rectification of the aggregation-authorization vulnerability, and a thorough
> re-execution of the experimental assessment.

## Summary of position

Seventeen comments. Items 1–3 identify a **genuine authorization vulnerability**
that no other reviewer caught in this form — that is the most serious single
finding across all seven reviews. Items 6–12 are leakage and practicality
concessions the paper should make rather than fight. Items 13–17 overlap
R1-C4/R2-C3 on experimental credibility.

**Grouping:** security (1–5), leakage disclosure (6–9), practicality (10–12),
experiments (13–17).

---

# Security — 1 to 5

## R3-1 — Aggregation authorization bypass ⚠️ MOST SERIOUS

> The aggregation protocol allows the user to present any arbitrary set of
> positions S without demonstrating that it was derived from a sanctioned
> range query. This results in a significant authorization circumvention.

**Type:** protocol vulnerability. **Severity: blocking, protocol redesign.**

Correct. In Phase 4 the user sends `S_Q` (selected bitmap positions) and the
cloud aggregates over them. Nothing binds `S_Q` to `B_Q`, the bitmap actually
produced by the authorized trapdoor `T_Q`. A user authorized for *any* range
can submit *any* position set and receive an aggregate over records they were
never entitled to.

### Fix — requires protocol change, not just text

Bind `S_Q` to the authorized query. Options, cheapest first:

- **(a) Cloud-side recomputation.** The cloud already holds the protected
  bitmap blocks and evaluated the tokens. Have it recompute `B_Q` from the
  matched nodes and reject any `S_Q ⊄ B_Q`. Requires the cloud to learn `B_Q`
  — which it partly does anyway via access patterns (see R3-6).
- **(b) Query-bound commitment.** User commits to `S_Q` under `qid` and proves
  membership against the authenticated bitmap blocks it received. Adds a
  proof round; keeps the cloud blind to `B_Q`.
- **(c) TDA-side check.** Fold into R3-3: authorities refuse partial
  decryption unless the aggregate request carries a valid query-authorization
  token.

**(a) is the smallest change and the easiest to prove.** Whichever is chosen,
Theorem 6 (Verifiable Aggregation Correctness) must be restated — it currently
proves the aggregate matches the *presented* `S_Q`, not that `S_Q` was
authorized.

---

## R3-2 — Node and record policies are not connected

> Node-specific policies P_u and record-specific policies P_i elements are not
> cohesively connected. A user might have the capability to consolidate values
> from records that do not meet their specific access policies.

**Type:** protocol vulnerability. **Severity: blocking.**

A user satisfying `P_u` for canonical node `u` recovers `K_u`, reconstructs
`u`'s bitmap, and can aggregate every record at those positions — including
records whose own `P_i` they do not satisfy. Node-level authorization silently
grants record-level access.

### Fix

State and enforce the relationship. Either:

- **Containment invariant** — the gateway must only place record *i* in node
  *u* when `P_u ⟹ P_i` (satisfying the node policy implies satisfying the
  record policy). Enforce at index construction; state as a system assumption.
- **Per-record filtering at aggregation** — the aggregation step includes only
  entries whose `P_i` the requesting user satisfies, checked via ABSE.

The first is cheaper but constrains policy assignment; the second costs a
per-record policy check. Pick one and add it to the Phase 2 / Phase 4
description and the threat model.

---

## R3-3 — TDAs do not verify query authorization

> Threshold decryption authority authenticates partial decryptions but does
> not confirm that the aggregate request stems from a valid, policy-sanctioned
> inquiry.

**Type:** protocol vulnerability. **Severity: blocking.** Completes R3-1.

TDAs verify DLEQ correctness of their own partial decryptions — that the
partial is well-formed — but never that the ciphertext they are decrypting
came from an authorized query. They are an unconditional decryption oracle for
any well-formed EC-ElGamal ciphertext.

### Fix

Require the aggregate request to carry an authorization token the TDAs verify
before releasing a partial: `(e_q, qid, Root_{e_q}, S_Q commitment)` signed or
ABSE-bound to the requesting user's attributes. Update Phase 5 and Theorem 5
(Threshold-Decryption Security).

---

## R3-4 — ABSE is only an abstract interface

> The ABSE element is characterized solely as an abstract interface. The
> document must present a definitive framework, methodologies, security
> premises, and execution specifics.

Duplicate of **R1-C2**. See `../Reviewer_1/Commend.md` for the fix. Blocking.

---

## R3-5 — Security proofs are conditional

> The security proofs rely on unconfirmed ABSE attributes and so are
> conditional rather than definitive validations of the implemented system.

**Type:** proof rigour. **Severity: blocking.** Follows from R3-4.

Theorems 2, 3, 4 all reduce to unproven ABSE properties. Once R1-C2/R3-4 give
a concrete scheme, restate each theorem's assumptions against that scheme's
actual hardness assumption and re-verify the reductions still close.

---

# Leakage — 6 to 9

These four ask the paper to **concede** things, not to fix code. All are cheap
and all strengthen credibility.

## R3-6 — Query privacy is overstated

> The significance of query privacy is exaggerated due to the cloud's ability
> to discern aligned canonical nodes, chosen record locations, query
> frequency, access behaviors, result quantities, and answer dimensions.

**Fix:** the Leakage Profile `L_BVCRSA` already lists most of this. Make the
prose match — do not claim "query privacy" unqualified. State plainly that the
cloud learns matched canonical nodes, selected positions, result cardinality,
dimension count, and access patterns; and that canonical nodes reveal
approximate range semantics. R5-3 asks for the same concession.

## R3-7 — Users learn more than their query results

> Authorized users retrieve comprehensive canonical-node bitmaps, potentially
> disclosing record membership and approximate numerical values that extend
> beyond the intended query results.

**Fix:** true by construction — a user authorized for node `u` gets `u`'s
*entire* bitmap, learning membership for records outside their range. Add to
the leakage profile as **user-side leakage**, a category the paper currently
lacks. Note the granularity/leakage trade-off: finer canonical nodes leak less
but increase `m_c`.

## R3-8 — Gateway metadata leakage

> The gateway monitors metadata related to searchable attributes and bitmap
> affiliations. Confidentiality assertions must explicitly recognize this
> breach.

**Fix:** the threat model already says the gateway "may infer information from
its authorized view, including sensor identities, update times, searchable
dimensions, canonical-node memberships, and bitmap positions." Propagate that
into the confidentiality claims and Theorem 3 so the abstract and conclusion
do not overclaim.

## R3-9 — Blockchain anchoring only attests to gateway-committed state

> Blockchain anchoring only verifies the conditions endorsed by the gateway.
> It cannot identify records that have been excluded or inaccurately
> catalogued by a malicious gateway.

**Fix:** already conceded in the threat model ("verification is therefore
relative to the gateway-committed state") but not in the abstract or
contributions, which claim "authenticated completeness" without qualification.
Qualify both. See R7-C1/C2 — same issue, and R7 treats it as fundamental.

---

# Practicality — 10 to 12

## R3-10 — No efficient revocation

> Efficient user revocation is not achievable because node keys remain
> constant throughout epochs and can be retained by users who were previously
> authorized.

**Fix:** `K_u = F(K_sel, D_j ‖ u)` is epoch-independent, so a revoked user
keeps every node key they ever recovered — and bitmap masking is derived from
`K_u`, so they can unmask future blocks. Either make node keys epoch-bound
(`K_u^{e} = F(K_sel, D_j ‖ u ‖ e)`, at the cost of re-masking every block each
epoch — which feeds R3-11), or add revocation to the stated limitations.
**Honest limitation is acceptable here; silence is not.**

## R3-11 — Epoch binding may force large-scale recommitment

> The epoch-binding approach might necessitate extensive regeneration or
> recommitment of searchable indexes, which contradicts the asserted minimal
> update overhead.

**Fix:** the paper already argues block commitments are *version*-bound rather
than epoch-bound so unchanged blocks need no re-masking. But `σ_u^idx` binds
`e_q`, so every index leaf is rehashed each epoch, and the Merkle root is
rebuilt. Quantify it: measure index-update cost per epoch as a function of
changed blocks. ⚠️ Interacts with R3-10 — epoch-bound node keys would force
full re-masking and destroy this argument.

## R3-12 — Full bitmaps are expensive

> Retaining a comprehensive bitmap for each canonical node could result in
> substantial storage, communication, and client-memory expenses.

**Fix:** storage analysis already admits `O(m_c · N)` bits. **Experiment 8**
now quantifies the communication half in KB — and response 1 will dominate,
exactly as suspected. Report the client-side memory for bitmap reconstruction
too. Concede rather than defend.

---

# Experiments — 13 to 17

## R3-13 — Query time and aggregation time do not agree

> The reported query-processing durations do not align with the independently
> reported homomorphic aggregation durations.

**Type:** internal inconsistency. **Severity: blocking.**

Query processing claims to *include* homomorphic aggregation (0.04–0.45 ms),
yet the aggregation experiment reports 20 ms+ for the same workload. Both
cannot be right.

### Fix

**Experiment 2** now breaks the total into `search_ms`, `bitmap_ms`,
`aggregate_ms` whose sum is the reported figure, and `aggregate_ms` must
reconcile with Experiment 5. Cross-check before publishing.

## R3-14 — Throughput and latency do not agree

> The throughput outcomes do not align with the declared per-query latency
> figures and necessitate thorough validation.

**Type:** experimental validity. **Severity: blocking.** Also R1-C4.

**Cause identified:** the old harness replayed one cached trapdoor through a
warm dict — no `ABSE.Test`, no bitmap work, no aggregation.

### Fix — **Experiment 3**

Fresh trapdoor per query, full path timed, and an explicit assertion that
`throughput ≈ 1000 / latency_ms` within 5 %. Failing rows are marked `FAIL`
and must not be published. Concurrency model stated: single-threaded
sequential.

## R3-15 — Dataset sizes stated inconsistently

Duplicate of **R1-C5**. Setup says ≤ 20k; results claim 100k. Experiment 2 is
the authority — correct the setup to 10³–10⁵ and fix the knock-on `Sum_max`
figure in the BSGS discussion.

## R3-16 — Baselines underdescribed

> Baseline methodologies lack adequate description to facilitate the
> replication of comparisons or guarantee uniform security configurations and
> functionalities.

**Type:** reproducibility. **Severity: major.**

### Fix

All five schemes now have a single canonical definition in
`Benchmark/_shared/baselines.py` — no more per-script redeclaration. For the
paper, add a subsection giving for each baseline: source paper, which variant
was implemented (e.g. Trinity-I vs -II; Latt-IBEKS Scheme-II for conjunctive),
security parameter, curve/lattice parameters, and what was simplified.

⚠️ Be honest about simplifications. `VCKASEAlgo` uses a `SimulatedPairingGroup`
(modular exponentiation, not real pairings), and `LatticeIBEKSAlgo` uses
`n_dim = 17, q = 4093` — small for LWE. Both must be disclosed, or the
"comparable security settings" claim is false.

⚠️ ABSE-Range is skipped for `N > 10,000` because its `O(N)` scan is
intractable. Do not drop those points silently — mark them in the figure.

## R3-17 — No raw data, CIs, or benchmark setups

> The experiments are devoid of raw data, confidence intervals, error margins,
> and comprehensive benchmark setups.

**Type:** experimental reporting. **Severity: blocking.** Also R1-C4, R2-C2, R7-C4.

### Fix

- `harness.Experiment.record()` **rejects** any row without run count, stdev,
  CI, and the full raw sample list.
- Every CSV carries an environment stamp: host, platform, Python version, AWS
  target, git revision.
- Every experiment has a `config.md` stating variables, fixed parameters,
  statistics, I/O, and exactly which operations are inside the timed region.
- Release the repository.

⚠️ Disclose Experiment 6's extrapolation policy (`|S_Q| > 150` measured on a
150-sample and scaled). Undisclosed extrapolation behind the 670.5× headline
is precisely what this comment is about.

# Reviewer 4

**Verdict: ACCEPT with minor suggestions**

## Summary of position

Positive. Credits the revision with resolving the bitmap key-provisioning
inconsistency (via node-specific keys encapsulated under ABSE), the
threat-model boundary between honest-but-curious gateway and malicious cloud,
and the formal leakage profile. Considers the added completeness and
aggregation-correctness theorems plus the extended evaluation a substantial
strengthening.

> The authors have thoroughly addressed prior reviewer concerns, in particular
> the bitmap key-provisioning inconsistency (now resolved via node-specific
> keys encapsulated under ABSE), the threat-model boundary between the
> honest-but-curious gateway and the malicious cloud, and the formal leakage
> profile. The added completeness/aggregation-correctness theorems and the
> expanded evaluation (up to 100k records, aggregation-recovery scalability)
> substantially strengthen the paper.

⚠️ **Read alongside R1, R3, and R7.** This reviewer accepts several things
others reject outright — R3-1/2/3 find an authorization bypass in the same
aggregation machinery R4 calls strengthened, and R7-C1/C2 reject the gateway
trust model R4 considers settled. Agreement here is not a defence against
those.

⚠️ R4 credits "aggregation-recovery scalability" as an added experiment. **It
was never implemented** — the manuscript describes the sweep and includes
`bsgs_scalability.png`, but neither the script nor the image existed. Now
written as **Experiment 7**. This reviewer accepted a figure that did not
exist; do not let that stand in the final version.

---

## R4-1 — Tighten notation consistency

> further tighten notation consistency between the main text and tables

**Type:** presentation. **Severity: trivial.**

### Fix

Sweep the manuscript for symbol drift. Known offenders:

| Symbol | Inconsistency |
|---|---|
| `\|U_Q\|` vs `\|\mathcal{U}_Q\|` | mixed across text, Table IV, and Table V |
| `m_c` vs `\sum_j \ell_j` | both used for the canonical-node count |
| `r` vs `\|R_Q\|` | both used for matched-record count — Table V uses `r`, figures use `\|R_Q\|` |
| `n_b` vs `n_{e_q}^{\mathrm{blk}}` | both used for the block count |
| `\|S_Q\|` vs `\|R_Q\|` | Exp 6 uses `S_Q`, Exp 5 uses `R_Q`, for the same quantity |

Pick one form per quantity, fix Table `tab:notation` and `tab:notation_cost`
to match, and align the figure axis labels. The last row matters most —
Figs. 6 and 7 currently label the same variable two different ways.

---

## R4-2 — Quantify blockchain cost empirically

> consider briefly quantifying blockchain gas/communication cost empirically
> rather than only conceptually

**Type:** experimental omission. **Severity: minor here, but R7-C5 makes the
same request as a blocking objection.**

Every reported number was taken with the chain **disabled** — the old harness
set `use_ethereum=False` "to measure pure cryptographic speed." Defensible for
isolating crypto cost, but it means the paper contains **zero** empirical
blockchain measurements while making claims about anchoring overhead.

### Fix — **Experiment 11**

`Benchmark/11_Blockchain_Cost/experiment.py` measures gas per epoch anchor,
anchor latency, finality (one block confirmation, matching the paper's stated
acceptance rule), ledger growth per year, and cross-node sync latency.

Turns two conceptual claims in the Discussion into curves:

- "on-chain storage grows with the number of finalized epochs rather than the
  dataset size" → `ledger_mb_per_year` vs block interval
- "very short epoch durations may still incur increasing blockchain storage"
  → the same curve, quantified

⚠️ R7-C5 additionally requires a **multi-node consortium**. A single-node
re-run satisfies R4 but not R7. Stand up 3+ nodes.

---

## R4-3 — Final proofread

> a final full proofread for residual typographical issues

**Type:** presentation. **Severity: trivial.**

### Fix

Known issues found while reading the source:

| Location | Problem |
|---|---|
| §I | "primarily optimize encrypted retrieval **encrypted retrieval** and generally do not" — duplicated phrase |
| §III-C intro | "To ease of understanding, Table **Table**~\ref{tab:notation}" — duplicated word, and "To ease of understanding" should be "For ease of understanding" |
| §V | "Table IV" referenced in the Verification Overhead text while the label points at `tab:complexity_comparison` — verify every hard-coded table number |

⚠️ Also check the three missing figure files before submission —
`modelAHE.pdf`, `fig_combined_3panel.png`, `bsgs_scalability.png` are all
`\includegraphics`'d but absent, so the document will not compile.

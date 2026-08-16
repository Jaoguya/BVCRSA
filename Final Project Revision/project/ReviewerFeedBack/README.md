# Reviewer Feedback — Index

`Commend` is the raw transcript as received. Each `Reviewer_N/Commend.md`
holds that reviewer's comments verbatim with a fix attached to every one.

## Verdicts

| Reviewer | Verdict | Comments | Blocking items |
|---|---|---|---|
| [Reviewer 1](Reviewer_1/Commend.md) | ❌ **Reject** | 8 | C1, C2, C3, C4, C6 |
| [Reviewer 2](Reviewer_2/Commend.md) | ⚠️ Major revision | 8 | C3, C7 |
| [Reviewer 3](Reviewer_3/Commend.md) | ❌ **Reject** | 17 | 1, 2, 3, 4, 5, 13, 14, 17 |
| [Reviewer 4](Reviewer_4/Commend.md) | ✅ Accept (minor) | 3 | none |
| [Reviewer 5](Reviewer_5/Commend.md) | ⚠️ Major revision | 3 | none — all editorial |
| [Reviewer 6](Reviewer_6/Commend.md) | ✅ **Publish unaltered** | 0 | none |
| [Reviewer 7](Reviewer_7/Commend.md) | ⚠️ Major revision | 5 | C1, C2, C4, C5 |

Two rejects, three major revisions, two accepts.

## The single most serious finding

**R3-1 / R3-2 / R3-3 — aggregation authorization bypass.** A user can present
an arbitrary position set `S_Q` with no proof it came from a sanctioned range
query, node policies `P_u` are not bound to record policies `P_i`, and the
threshold authorities never check that a decryption request came from an
authorized query. No other reviewer found this in this form. It requires a
protocol change and a restatement of Theorems 5 and 6 — not an experiment.

## Where the reviewers converge

| Theme | Raised by |
|---|---|
| Timings are not credible; want raw data, op counts, CIs | R1-C4, R2-C2, R2-C3, R3-13, R3-14, R3-17, R7-C4 |
| ABSE is an abstract interface, not a scheme | R1-C2, R3-4, R3-5 |
| Gateway is a single point of trust | R7-C1, R7-C2, R3-9 |
| Communication cost is asymptotic only | R1-C7, R2-C5 |
| Blockchain cost never measured | R7-C5, R4-2 |
| Dataset size stated inconsistently | R1-C5, R3-15 |
| Leakage understated | R3-6, R3-7, R3-8, R5-3 |

Seven reviewers, four independent complaints about the experimental numbers.
That is the centre of gravity of the rebuild.

## Split of work

**Paper-side only — no code.** R1-C1, R1-C2, R1-C5, R1-C8(partly),
R2-C1, R2-C6, R2-C8, R3-1..12, R3-15, R3-16, R4-1, R4-3, R5-1, R5-2, R5-3,
R7-C1, R7-C2, R7-C3.

**Experiment-side.** 
R1-C3 → Exp 5 · R1-C4 → Exp 3, 10 + harness · R1-C6 → Exp 9 · R1-C7  
R2-C5 → Exp 8 · R2-C3 → Exp 10 · R2-C4 → Exp 2 · R2-C7 → Exp 5, 6 
R3-13 → Exp 2, 5 · R3-14 → Exp 3 · R3-17 → harness ·
R4-2 / R7-C5 → Exp 11 · R7-C4 → Exp 8, 9, 11 + harness.

See [../MD/SKILL.md](../MD/SKILL.md) §3 for the consolidated P1–P8 /
E1–E14 tables, and each experiment's `config.md` for which comments it answers.

## Two things the accepting reviewers credited that did not exist

- **R6** cites "aggregation scalability evaluated separately." The BSGS
  experiment had no script and no figure file, despite being described in the
  text and `\includegraphics`'d. Now written as Exp 7.
- **R6** cites Table V as a "clear communication cost analysis." It is
  asymptotic expressions with no prototype measurement. Now Exp 8.

Worth knowing before leaning on those endorsements in the response letter.

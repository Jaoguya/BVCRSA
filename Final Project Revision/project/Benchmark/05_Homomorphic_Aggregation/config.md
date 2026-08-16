# Experiment 5 — Effect of Homomorphic Aggregation

**Paper:** EVALUATION → Performance Evaluation → *Effect of Homomorphic Aggregation*
**Figure:** `exp05_ablation_aggregation.svg`
**Claim:** BVCRSA stays under 20 ms across all workloads while the naive
baseline (return every matched ciphertext to the user) climbs ~180 ms → ~900 ms.

**File:** `experiment.py` (salvaged from `benchmark_ablation.py`).

## Variables

| | |
|---|---|
| Independent | `|R_Q|` — matched records ∈ **{100, 200, 300, 400, 500}** |
| Fixed | query configuration constant; values uniform `[1, 100]` |

Two arms:

- **BVCRSA** — cloud homomorphically adds all matched ciphertexts; user performs
  a constant number of threshold decryptions.
- **Naive** — cloud returns every matched ciphertext; user decrypts each one.

## ⚠️ Must be regenerated under Threshold EC-ElGamal

`benchmark_ablation.py` as salvaged uses **single-key** `ec_elgamal.py`
(`generate_ec_elgamal_keypair` + `priv.decrypt`). The protocol in Phase 5 is now
`(t,n)` **Threshold** EC-ElGamal. Reviewer **R2-C7** names this exactly:

> "The switch from single-key EC-ElGamal to (t,n)-Threshold EC-ElGamal touches
> the same aggregation pipeline that Figs. 6 and 7 report on. Nothing confirms
> these experiments were regenerated under the new threshold scheme."

Rewrite against `threshold_ec_elgamal.py` with `(t, n) = (3, 5)`,
`CHOSEN_AUTHORITIES = [1, 2, 3]`, so each decryption is 3 Chaum–Pedersen partial
decryptions + 3 DLEQ verifications + Lagrange combine + BSGS recovery. The
numbers **will** move; that is the point.

## ⚠️ The naive arm must reflect the formal protocol

Reviewer **R1-C3**:

> "Every selected aggregation entry A_i must be returned to the user so that the
> user can independently recompute and verify the aggregate. However, the
> performance discussion claims that only compact aggregate ciphertexts and
> verification proofs are returned."

So the BVCRSA arm is currently measuring something the protocol does not permit.
Add a third arm — **BVCRSA-verifiable** — that returns all `r` aggregation
entries `A_i` plus the multi-proof and has the user recompute the aggregate
independently. Report all three. If BVCRSA-verifiable is close to naive, say so;
the honest number is worth more than the flattering one.

## Statistics

```
RUNS = 20    WARMUP = 2
report mean, stdev, ci95, min, max, raw
```

## I/O

| | |
|---|---|
| Output data | `../../CSV/exp05_homomorphic_aggregation.csv` |
| Output figure | `../../Figures/exp05_ablation_aggregation.svg` |

CSV columns:
`arm, matched_records, runs, mean_ms, median_ms, stdev_ms, ci95_ms, min_ms, max_ms, decrypt_calls, ec_adds, bytes_returned, raw_ms`

`bytes_returned` feeds Experiment 8 (communication cost).

## Reviewer requirements this experiment must satisfy

- **R2-C7** — regenerate under threshold EC-ElGamal. Blocking.
- **R1-C3** — measure the complete verifiable protocol, including transmission
  and client-side processing of all selected aggregation entries.
- **R2-C6** — tie the figure back to Table IV / the cost derivations in the text;
  it currently reads as a free-floating experiment.
- **R3-C13** — aggregation time here must reconcile with the `aggregate_ms`
  column of Experiment 2.
- **R1-C8** — SVG. Current script writes `paper_figures/*.png` at dpi=300.

## Execution

AWS EC2 only. No MongoDB.

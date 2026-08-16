# Experiment 6 — Aggregation Strategy Comparison

**Paper:** EVALUATION → Performance Evaluation → *Aggregation Strategy Comparison*
**Figure:** `exp06_agg_strategy_comparison.svg` (3 panels)
**Claim:** aggregate-then-decrypt beats decrypt-then-aggregate by up to
**670.5×** at `|R_Q| = 10,000`; crossover at `|R_Q| ≈ 2`.

**Files:** `experiment.py` (main sweep), `experiment_zoom.py` (crossover
resolution), `plot.py`.

This is the strongest experiment in the repo — it already uses real threshold
EC-ElGamal, 20 runs, and asserts correctness. Keep its structure.

## Variables

| | |
|---|---|
| Independent | `|S_Q|` ∈ **{10, 50, 100, 500, 1000, 5000, 10000}** (main) |
| | `|S_Q|` ∈ **{1, 2, 3, 5, 8, 10, 15, 20, 30, 40, 50}** (zoom) |
| Fixed | `N = 10,000` (context only — both paths depend on `|S_Q|`, not `N`) |
| Threshold | `(t, n) = (3, 5)`, `CHOSEN_AUTHORITIES = [1, 2, 3]`, NIST P-256 |
| Values | uniform `[1, 100]`; `MAX_VAL = 1,000,000` (main), `5,000` (zoom) |

Two arms:

- **Conventional** — threshold-decrypt every matched ciphertext, then sum.
- **BVCRSA** — homomorphically aggregate first, then decrypt exactly **2**
  ciphertexts (SUM and COUNT).

## Correctness precondition — do not remove

At `|S_Q| = 200`, assert that the threshold-decrypted homomorphic Sum/Count
equals the raw plaintext sum / `|S_Q|`. Both paths must produce identical
numeric results; that equality is what makes the cost comparison fair.

## Sampling policy

For `|S_Q| > 150` the conventional path's per-record decrypt cost is measured
on **150 real threshold decryptions** and linearly extrapolated. Each
`threshold_decrypt()` call has ~constant cost — dominated by the fixed-length
share, not by which record is decrypted. Every `|S_Q| ≤ 150`, which covers the
entire crossover region, is decrypted in full with no extrapolation.

**This must be disclosed in the caption.** Reviewer R3-C17 asks for
comprehensive benchmark setups; an undisclosed extrapolation in the headline
670.5× number is exactly the kind of thing that draws a rejection.

## Statistics

```
RUNS = 20    SAMPLE_CAP = 150    seed = 42
report mean, stdev, ci95, min, max, raw
```

## I/O

| | |
|---|---|
| Output data | `../../CSV/exp06_agg_strategy.csv`, `../../CSV/exp06_agg_strategy_zoom.csv` |
| Output figure | `../../Figures/exp06_agg_strategy_comparison.svg` |

CSV columns:
`SQ, arm, decrypt_calls, ec_adds, runs, mean_ms, median_ms, stdev_ms, ci95_ms, min_ms, max_ms, speedup, extrapolated, raw_ms`

`extrapolated` is a boolean — true when `|S_Q| > SAMPLE_CAP`.

## Reviewer requirements this experiment must satisfy

- **R2-C6** — Fig. 7 is not tied back to Table IV or the cost derivations
  anywhere in the text. Add that linkage: panel (a)'s decryption-call counts are
  the direct empirical realization of the `O(1)` vs `O(r)` threshold-decrypt
  terms in the complexity table.
- **R2-C7** — confirm in the text that this experiment runs under `(t,n)`
  threshold EC-ElGamal. It does; say so explicitly.
- **R3-C17** — disclose the sampling/extrapolation policy above.
- **R7-C4 / R2-C2** — error bars.
- **R1-C8** — `plot.py` currently writes PNG at dpi=300. Convert to SVG.

## Execution

AWS EC2 only. No MongoDB.

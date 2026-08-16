# Experiment 7 — Aggregate-Recovery Scalability (BSGS)

**Paper:** EVALUATION → Performance Evaluation → *Aggregate-Recovery Scalability*
**Figure:** `exp07_bsgs_scalability.svg`
**Claim:** bounded Baby-Step Giant-Step recovery grows as `O(√M_max)` while
linear search grows as `O(M_max)` and becomes impractical.

## ⚠️ This experiment has never existed

The paper describes it in full and includes `bsgs_scalability.png` — but **no
script produces it and the image file is not in the repository**. It must be
written from scratch. This is the only one of the seven with no ancestor code.

## Variables

| | |
|---|---|
| Independent | `M_max` — maximum supported aggregate value ∈ **{10³, 10⁴, 10⁵, 10⁶, 10⁷}** |
| Fixed | NIST P-256; lifted EC-ElGamal; recovery of a decrypted point `vG → v` |
| Arms | **BSGS** (bounded, `O(√M_max)`) vs **linear search** (`O(M_max)`) |

## What to measure

1. **Table build time** — constructing the `⌈√M_max⌉`-entry baby-step table.
   One-off, amortized across queries. Report separately from lookup.
2. **Lookup time** — giant-step iterations to recover `v`. Randomize `v` across
   `[0, M_max]` per run so the measurement is not biased toward small values.
3. **Memory footprint** of the baby-step table (bytes). `M_max = 10⁷` needs
   ~3,163 entries; report actual `sys.getsizeof` / `tracemalloc` peak.

Linear search at `M_max = 10⁷` is slow by construction — cap its measured
sample and extrapolate, disclosing that in the caption exactly as Experiment 6 does.

## Grounding in the paper's own parameters

The manuscript states: under the experimental configuration
(`N ≤ 2×10⁴`, `V_max = 100`) the maximum aggregate sum is `2×10⁶`, needing
≈ `√(2×10⁶) ≈ 1.4×10³` baby-step entries. Mark that operating point on the
figure so the sweep visibly brackets the deployed configuration.

⚠️ If Experiment 2's `N` range is corrected to 10⁵ (per R1-C5 / R3-C15), then
`Sum_max = 10⁷` and the stated `2×10⁶` in the text is wrong. Recompute and fix
both places together.

## Statistics

```
RUNS = 20    WARMUP = 2
report mean, stdev, ci95, min, max, raw
```

## I/O

| | |
|---|---|
| Output data | `../../CSV/exp07_bsgs_scalability.csv` |
| Output figure | `../../Figures/exp07_bsgs_scalability.svg` |

CSV columns:
`arm, M_max, table_entries, table_bytes, table_build_ms, runs, mean_lookup_ms, median_ms, stdev_ms, ci95_ms, min_ms, max_ms, extrapolated, raw_ms`

## Reviewer requirements this experiment must satisfy

- **R2-C6** — Fig. 8 (BSGS) is "not tied back to Table IV / the cost derivations
  anywhere in the text" and "reads as a free-floating experiment." Connect it
  explicitly: BSGS recovery is the constant term in the Phase-5 decryption cost,
  and the figure validates the `O(√M_max)` bound asserted in the complexity analysis.
- **R2-C8** — Fig. 8's caption does not state the run count. State it.
- **R1-C8** — SVG.

## Implementation note

The BSGS table already exists inside `Benchmark/ec_elgamal.py`
(`generate_ec_elgamal_keypair(max_val=...)` builds it). Reuse that code path
rather than reimplementing, so the figure measures the production decrypt path.

## Execution

AWS EC2 only. No MongoDB.

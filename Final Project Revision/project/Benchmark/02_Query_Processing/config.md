# Experiment 2 — Query Processing Time

**Paper:** EVALUATION → Performance Evaluation → *Query Processing Time*
**Figures:** `fig_combined_3panel.svg` panels **(b)** and **(c)**, plus
`exp02_query_vs_d.svg`
**Claim:** BVCRSA holds the lowest latency across selectivity, database size,
and dimension count (~0.04 → 0.20 ms over range; ~0.02 → 0.45 ms over N).

## Three sweeps

| Sweep | Independent | Fixed |
|---|---|---|
| **2a** vs selectivity | range % ∈ **{10, 20, 30, 50, 80}** | `N = 10,000`, `d = 1`, kw = `Temp` |
| **2b** vs database size | `N` ∈ **{1k, 5k, 10k, 20k, 50k, 100k}** | range 30 % (`[35,65]`), `d = 1`, kw = `Temp` |
| **2c** vs dimensions | `d` ∈ **{1, 2, 3, 4, 5}** | `N = 10,000`, range 30 % |

Measured phase: encrypted search + bitmap filtering + homomorphic aggregation.
Network and blockchain access are excluded — **this must be stated explicitly
in the caption and text** (R5-C2).

## Schemes

2a / 2b: all five. 2c: BVCRSA, VC-KASE, Latt-IBEKS (the conjunctive-capable
set — `CONJUNCTIVE_SCHEMES` in `Benchmark/baselines.py`).

ABSE-Range is `O(N)` per query and becomes intractable past `N = 10,000`. Do
**not** silently skip it — record the row with `note = "skipped_large_N"` and
say so in the caption, so the omission is visible (R3-C16).

## Statistics

```
RUNS = 20    WARMUP = 2    gc disabled
report mean, stdev, ci95, min, max, raw samples
```

## I/O

| | |
|---|---|
| Input | `../../CSV/Datarecord.csv` |
| Output data | `../../CSV/exp02_query_processing.csv` |
| Output figures | `../../Figures/exp02_query_vs_range.svg`, `exp02_query_vs_N.svg`, `exp02_query_vs_d.svg` |

CSV columns:
`sweep, scheme, N, range_pct, d, matched, runs, mean_ms, median_ms, stdev_ms, ci95_ms, min_ms, max_ms, raw_ms, note`

## Reviewer requirements this experiment must satisfy

- **R1-C5 / R3-C15** — the dataset range must be *one* consistent story. The
  Experimental Setup currently says ≤ 20,000 while results go to 100,000.
  This sweep is the authority: fix the setup text to **10³ – 10⁵**.
- **R2-C4** — 100k is still toy scale against the paper's "massive volumes"
  framing. Add an **extrapolation** to 10⁶–10⁷ using the derived `O(N log N)`
  bound, plotted as a dashed continuation. Costs nothing computationally.
- **R1-C4 / R2-C3** — sub-ms results must be defensible. Log operation counts
  (ABSE `Test` calls, bitmap words ANDed, aggregation entries touched) beside
  every timing.
- **R3-C13** — query-processing time must be *reconcilable* with the separately
  reported aggregation time. Break the measurement into `search_ms`,
  `bitmap_ms`, `aggregate_ms` columns whose sum is the reported total.
- **R1-C8** — SVG.

## Execution

AWS EC2 only. No MongoDB — records come from CSV.

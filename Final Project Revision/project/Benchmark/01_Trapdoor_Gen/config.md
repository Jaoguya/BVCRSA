# Experiment 1 — Trapdoor Generation Time

**Paper:** EVALUATION → Performance Evaluation → *Trapdoor Generation Time*
**Figure:** `fig_combined_3panel.svg` panel **(a)**
**Claim:** trapdoor cost is `O(m_c · k)`; BVCRSA rises only ~0.9 ms → 2.2 ms for d = 1..5.

## Variables

| | |
|---|---|
| Independent | `d` — number of queried dimensions ∈ **{1, 2, 3, 4, 5}** |
| Fixed | `N = 10,000`; range width 30 % (`[35, 65]`); keyword pool = first `d` of `Temp, Humidity, Pressure, Vibration, Voltage` |
| Measured | client-side trapdoor construction ONLY — canonical cover + ABSE token generation. Index build, search, and network are excluded. |

## Schemes

BVCRSA, Trinity (ref26), ABSE-Range (ref27), Latt-IBEKS (ref28), VC-KASE (ref16).
All via `Benchmark/baselines.py` — do not redeclare them here.

## Statistics

```
RUNS   = 20        WARMUP = 2        gc disabled during timing
report = mean, stdev, ci95, min, max, and the full raw sample list
```

Reviewers R1-C4, R2-C2, R3-C17 and R7-C4 all reject bare averages. The raw
per-run milliseconds go into the CSV; the figure carries error bars.

## I/O

| | |
|---|---|
| Input | `../../CSV/Datarecord.csv` (first 10,000 rows) |
| Output data | `../../CSV/exp01_trapdoor_gen.csv` |
| Output figure | `../../Figures/exp01_trapdoor_gen.svg` — **vector, per R1-C8** |

CSV columns:
`scheme, d, runs, mean_ms, median_ms, stdev_ms, ci95_ms, min_ms, max_ms, raw_ms`

## Reviewer requirements this experiment must satisfy

- **R1-C4 / R3-C17** — publish raw timings and operation counts, not just means.
  Also log the *operation count* per trapdoor (number of canonical nodes `m_c`,
  number of ABSE `TokenGen` calls) so the reported time can be checked by hand.
- **R2-C3** — sub-millisecond claims must be reconcilable from per-primitive
  costs. Cross-check the total against Experiment 10 (per-primitive
  microbenchmark): `m_c × cost(TokenGen)` should approximate the measured mean.
- **R2-C8** — state "20 independent runs" in the figure caption.
- **R1-C8** — emit SVG, not PNG.

## Execution

AWS EC2 only (see `../../AWS/serverpath`). No local VM, no MongoDB.

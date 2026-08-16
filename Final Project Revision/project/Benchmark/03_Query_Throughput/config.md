# Experiment 3 — Query Throughput

**Paper:** EVALUATION → Performance Evaluation → *Query Throughput*
**Figure:** `exp03_query_throughput.svg`
**Claim:** BVCRSA sustains the highest throughput as workload rises.

## Variables

| | |
|---|---|
| Independent | query count `Q` ∈ **{5, 10, 25, 50}** |
| Fixed | `N = 10,000`; range 30 % (`[35,65]`); `d = 1`; kw = `Temp` |
| Metric | completed queries per second |
| Runs | 10 (reduced from 20) |

## ⚠️ Sweep reduced — disclose in the caption

The original sweep was `Q ∈ {100, 500, 1000, 5000, 10000}` with `RUNS = 20`.
Those values assumed a query cost of 0.0067 ms — the dictionary-lookup
artefact. A **real** query costs ~300 ms at `N = 10,000`, making the original
sweep ≈ 27 hours per scheme, ≈ 6 days for all five. It is not runnable.

The reduced sweep still spans an order of magnitude in workload, which is what
the figure claims. State the workload range honestly in the caption; do not
imply 10,000-query workloads were measured.

## Schemes

All five (`ALL_SCHEMES`).

## ⚠️ This experiment is the single biggest credibility risk in the paper

Three reviewers attacked it directly:

- **R1-C4** — "throughput close to 10⁶ queries per second" is not believable for
  a Python stack that must do `O(N_u × m_c)` exhaustive ABSE matching.
- **R3-C14** — "throughput outcomes do not align with the declared per-query
  latency figures."

The previous run recorded **923,343 q/s** for BVCRSA at Q = 100. That figure
came from replaying **one pre-generated trapdoor** through `algo.query(td)` in
a tight loop — which hits a warm Python dict and performs **no ABSE `Test`, no
bitmap reconstruction, and no aggregation**. It measures dictionary lookup, not
query processing.

**Required fixes before re-running:**

1. Generate a **fresh trapdoor per query** — that is what a query costs.
2. Include the full path: ABSE `Test` matching → bitmap block fetch and unmask
   → conjunctive intersection → homomorphic aggregation.
3. Report throughput **and** mean per-query latency in the same table, and
   assert `throughput ≈ 1000 / latency_ms`. If the two disagree, the harness is
   measuring the wrong thing. Fail the run loudly rather than publishing.
4. State the concurrency model explicitly: single-threaded sequential. No
   parallelism is claimed.

## Statistics

```
RUNS = 5 repetitions of each Q-workload    WARMUP = 1
SKIP_SCHEMES = {"ABSE-Range"}   # ~64 s/query at N=10,000 -- costs more than
                                # every other scheme combined. Its single-query
                                # latency is reported from Exp 2 instead.
                                # SAY THIS IN THE CAPTION.
report mean, stdev, ci95, min, max, raw
```

## I/O

| | |
|---|---|
| Input | `../../CSV/Datarecord.csv` (first 10,000 rows) |
| Output data | `../../CSV/exp03_query_throughput.csv` |
| Output figure | `../../Figures/exp03_query_throughput.svg` |

CSV columns:
`scheme, query_count, runs, mean_throughput_qps, stdev_qps, ci95_qps, mean_latency_ms, stdev_latency_ms, consistency_check, raw_qps`

`consistency_check` = `PASS` when `|throughput − 1000/latency_ms| / throughput < 0.05`.

## Reviewer requirements this experiment must satisfy

- **R3-C14** — throughput must reconcile with latency. Enforced by the assert above.
- **R1-C4** — publish raw data, operation counts, and a precise statement of
  which operations are inside the timed region.
- **R7-C4** — error bars on the curve.
- **R1-C8** — SVG.

## Execution

AWS EC2 only. No MongoDB.

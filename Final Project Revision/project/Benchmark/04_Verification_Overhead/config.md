# Experiment 4 — Verification Overhead

**Paper:** EVALUATION → Performance Evaluation → *Verification Overhead*
**Figure:** `exp04_verification_overhead.svg`
**Claim:** BVCRSA verification is `O(r · log(N/r))` — ~0.35 → 3.0 ms across
|R_Q| = 50…500, beating Trinity (1.4 → 13.6 ms) and matching VC-KASE's flat
~1.8 ms for small/moderate result sets.

**Files:** `experiment.py` (salvaged from `verification_overhead_exp.py` —
already the highest-quality script in the repo), `plot.py`.

## Variables

| | |
|---|---|
| Independent | `|R_Q|` ∈ **{50, 100, 150, 200, 250, 300, 350, 400, 450, 500}** |
| Fixed | `N = 10,000`; range `[0, 100]` (full domain); `d = 1`; kw = `Temp` |
| Measured | **verification only** — setup, search, trapdoor generation, and proof *generation* are all outside the timed region |

## Per-scheme verification, each matching its published design

- **BVCRSA** — real `MerkleTree.verify_multi_proof()` over SCRAT nodes built by
  the production pipeline (`TA → sensor_encrypt → blockchain_edge → merkle_tree`),
  plus a constant-cost HMAC-SHA256 epoch-root signature check. `O(r·log(N/r))`.
  Internal nodes shared by multiple selected leaves are hashed **once**; a naive
  "r independent single-leaf proofs" implementation is `O(r log N)` and does not
  match the design claimed in the complexity table.
- **Trinity** — per-result AES-GCM decrypt-and-content-check of the encrypted
  verify array, per the real Trinity-II algorithm (§V-B2). Not a bare HMAC
  compare. `O(r)`.
- **VC-KASE** — fixed, result-count-independent count of real BLS12-381
  pairings. `O(T_pair)`.

## Two methodology controls — preserve these

1. **Interleaved sampling.** One BVCRSA rep, one Trinity rep, one VC-KASE rep,
   then repeat. Running each scheme as a back-to-back block lets system load
   drift over the minutes a sweep takes and biases one scheme relative to another.
2. **Deterministic evenly-spaced indices.** A fresh `random.sample()` per call
   changes the Merkle multi-proof's sibling-sharing pattern from draw to draw,
   injecting variance unrelated to `|R_Q|`.

## Statistics

```
RUNS = 300 (median reported)    WARMUP = 10    gc disabled    seed = 42
```

This is the one experiment already exceeding the paper's stated 20 runs. **The
text says "average of 20 independent runs" but this reports the median of 300**
— fix the caption to say so (R2-C8).

## I/O

| | |
|---|---|
| Output data | `../../CSV/exp04_verification_overhead.csv` |
| Output figure | `../../Figures/exp04_verification_overhead.svg` |

CSV columns:
`scheme, returned_results, runs, mean_ms, median_ms, stdev_ms, ci95_ms, min_ms, max_ms, hash_ops, pairing_ops, raw_ms`

## Reviewer requirements this experiment must satisfy

- **R1** (opening) — "record-linear verification process" is claimed
  incompatible with the reported numbers. Log `hash_ops` per run so the
  `O(r·log(N/r))` shape is demonstrable from counts, not just wall-clock.
- **R2-C3** — cross-check the total against Experiment 10's single-Merkle-verify
  microbenchmark.
- **R7-C4 / R3-C17** — error bars and raw data.
- **R1-C8** — `plot.py` currently emits PNG at dpi=200. Convert to SVG.

## Execution

AWS EC2 only. No MongoDB.

# Experiment 10 — Per-Primitive Microbenchmarks

**Status:** NEW — reviewer-mandated, no prior code.
**Figure:** `exp10_primitive_microbench.svg`
**Answers:** R2-C3, R1-C4

## Why it exists

> **R2-C3** — "My concern about implausibly fast sub-ms latencies for a
> Python/py_ecc stack was not really engaged with. The response repeats that
> reported numbers exclude network/blockchain latency, which I already knew
> from the first submission — that doesn't explain how ABSE.Test + Merkle
> verify + bitmap AND/OR over 100K-bit vectors finishes in well under a
> millisecond in pure Python. I'd like to see per-primitive microbenchmarks
> (single Test call, single pairing, single Merkle verify) so the totals can
> be checked by hand."

This is the **reconciliation table for the whole paper**. Every other
experiment logs operation counts; multiplying those counts by the costs
measured here must approximate the reported totals. Where it doesn't, the
total is wrong and must be re-examined before publication.

Run this **first**. It calibrates everything else.

## Primitives measured

| Primitive | Where it appears |
|---|---|
| bilinear pairing | 2 per `ABSE.Test` |
| `ABSE.Test` | `N_u × m_c` per query (exhaustive match) |
| `ABSE.TokenGen` | `m_c` per trapdoor — Exp 01 |
| Merkle verify (single leaf) | `r` per query if naive; shared in multi-proof — Exp 04 |
| SHA-256 | ~`r·log(N/r)` in the multi-proof |
| HMAC-SHA256 | 1 per epoch-root signature check |
| **bitmap AND over 100k bits** | `d−1` per conjunctive query — *named explicitly by R2-C3* |
| bitmap AND + popcount | 1 per query |
| EC-ElGamal encrypt | 1 per record at ingest |
| EC-ElGamal add | `r−1` per aggregation |
| threshold decrypt `(3,5)` | 2 per query — Exp 05, 06 |

## Backend detection

The script prints which ABSE backend is live:

- `py_arkworks_bls12381` → **BLS12-381**
- `py_ecc` → **BN128**

⚠️ The manuscript claims *"implemented with `py_ecc` over the BN128 bilinear
curve."* If this prints BLS12-381, the paper's text is wrong and the reported
numbers are from a different curve. **Fix the text or pin the backend** —
R2-C3's plausibility objection partly rests on believing the stack is pure
Python `py_ecc`, which it is not if arkworks is installed.

## Statistics

```
RUNS = 200    WARMUP = 20
```

Higher than elsewhere because these are sub-microsecond operations where
timer resolution dominates.

## Output

`../../CSV/exp10_primitive_microbench.csv` —
`primitive, backend, detail, calls_per_query_note` + stats columns

The script also prints a reconciliation block, e.g.:

```
Exp 02 query, exhaustive match N_u*m_c = 1000*4:   <expected> ms
   ^ if the measured query time is far below this, the harness is not
     doing exhaustive ABSE matching (R1-C4, R3-14)
```

That check is the point of the experiment. If Exp 02/03 come in orders of
magnitude under the expected floor, the harness is measuring the wrong thing —
which is exactly what happened with the old throughput script.

# Experiment 8 — End-to-End Communication Cost

**Status:** NEW — reviewer-mandated, no prior code.
**Figure:** `exp08_communication_cost.svg`
**Answers:** R2-C5, R1-C7

## Why it exists

> **R2-C5** — "Table V and the new communication-cost subsection are still
> purely asymptotic. Every other cost in the paper is backed by measured
> numbers from the prototype, but communication is the one dimension left as
> O(·) expressions only. I'd like actual KB figures for trapdoor size,
> first-round response, and second-round response at a couple of
> representative N and |R_Q| values."

> **R1-C7** — "A numerical end-to-end communication evaluation is necessary
> rather than relying only on asymptotic complexity expressions."

## Variables

| | |
|---|---|
| Independent | `N` ∈ {1k, 10k, 100k} × `|R_Q|` ∈ {50, 100, 500, 1000} |
| Fixed | `d = 3`, range 30 %, `β = 4096` bits per bitmap block |

## Measured rounds

| Round | Contents |
|---|---|
| Request | `m_c` ABSE tokens + epoch header + selected positions |
| Response 1 | per matched canonical node: all `n_blk` protected bitmap blocks + version counters + Merkle proofs |
| Response 2 | `r` aggregation entries `A_i` + aggregation multi-proof + `CT_sum` + `CT_count` |

## Wire sizes

Derived from the concrete primitives, not assumed:

```
EC point (P-256, compressed)  33 B      SHA-256 hash    32 B
AHE ciphertext                66 B      ECDSA sig       64 B
ABSE token (BLS12-381)       192 B      (2×G1 + 1×G2 compressed)
```

## Output

`../../CSV/exp08_communication_cost.csv` —
`N, r, d, m_c, matched_nodes, n_blk, request_bytes, response1_bytes, response2_bytes, total_bytes, total_kb, naive_all_records_kb, saving_vs_naive_pct`

## What to do with the result

Replace the O(·) cells in **Table V** with the `total_kb` column at
`N = 10,000`, `r ∈ {100, 500}`.

Response 1 will dominate, because every matched canonical node ships all
`n_blk` blocks regardless of how many bits are set. **State that plainly.**
R1-C7 and R3-12 both already suspect it; conceding it costs less than being
caught hiding it behind an asymptotic.

⚠️ Cross-check `bytes_returned` against Experiment 5's column of the same name.
They must agree.

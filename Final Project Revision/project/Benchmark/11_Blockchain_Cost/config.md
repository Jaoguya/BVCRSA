# Experiment 11 — Blockchain Anchoring Cost

**Status:** NEW — reviewer-mandated, no prior code.
**Figure:** `exp11_blockchain_cost.svg`
**Answers:** R7-C5, R4-C2

## Why it exists

> **R7-C5** — "The blockchain prototype is only validated on a single-node
> Clique PoA private testnet deployed on a standalone machine, with a fixed
> block interval adopted for all experiments. No multi-node consortium cluster
> is constructed, and no comparative measurements under multiple epoch
> submission frequencies are conducted. Quantitative curves of ledger
> expansion, transaction gas cost and cross-node synchronization latency under
> multi-node networks and variable epoch cycles are absent."

> **R4-C2** — "consider briefly quantifying blockchain gas/communication cost
> empirically rather than only conceptually."

Every other experiment ran with the chain **disabled** — the old harness set
`use_ethereum=False` "to measure pure cryptographic speed." Defensible for
isolating crypto cost, but it means the paper currently reports **zero**
empirical blockchain numbers while making claims about anchoring overhead.

## Variables

| | |
|---|---|
| Independent | block interval ∈ {1, 2, 5, 15} s × node count ∈ {1, 3, 5} |
| Fixed | 20 epoch anchors per configuration |
| Payload | `(e_q, N, β, n_blk, Root, ts, σ_DO)` = 124 B |

## Measured

| Metric | Meaning |
|---|---|
| `gas_used` | per epoch-anchor transaction, from the receipt |
| `anchor_latency_ms` | submit → mined |
| `finality_ms` | submit → one block confirmation (the paper's stated acceptance rule) |
| `ledger_mb_per_year` | projected on-chain growth at that epoch frequency |
| `sync_latency_ms` | cross-node propagation — **multi-node only** |

## Setup

Deploy `_shared/contracts/BVCRSALedger.sol` via `_shared/deploy_contract.py`,
then:

```bash
export BVCRSA_NODE_RPCS=http://10.0.1.10:8545,http://10.0.1.11:8545,http://10.0.1.12:8545
export BVCRSA_BLOCK_INTERVALS=1,2,5,15
export BVCRSA_EPOCHS=20
python experiment.py
```

Requires `pip install web3`.

## Fails loudly rather than faking

If `web3` is missing or no node answers, the script **exits non-zero and
writes no CSV**. Placeholder blockchain numbers would be worse than none —
R7 is already unconvinced by the single-node setup, and inventing multi-node
figures would be indefensible.

With a single node connected, `sync_latency_ms` is left blank and the row is
annotated `single-node: sync latency not measurable (R7-C5)`.

## What this feeds in the paper

The Discussion currently says on-chain storage "grows with the number of
finalized epochs rather than the dataset size" and warns that "very short
epoch durations may still incur increasing blockchain storage." Both are
conceptual. `ledger_mb_per_year` versus block interval turns them into a
curve — which is precisely the ask.

⚠️ R7-C5 asks specifically for a **multi-node consortium**. A single-node
re-run does not answer it. Stand up at least 3 nodes before claiming
consortium applicability.

## Output

`../../CSV/exp11_blockchain_cost.csv` —
`nodes, block_interval_s, epoch, gas_used, anchor_latency_ms, finality_ms, ledger_bytes_per_epoch, ledger_mb_per_year, sync_latency_ms, note` + stats columns

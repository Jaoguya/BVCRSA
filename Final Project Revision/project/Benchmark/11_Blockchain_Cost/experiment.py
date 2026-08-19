#!/usr/bin/env python3
"""
Experiment 11 — Blockchain Anchoring Cost
=========================================
Gas, ledger growth, and epoch-anchor latency for the permissioned chain.

WHY THIS EXPERIMENT EXISTS
--------------------------
R7-C5: "The blockchain prototype is only validated on a single-node Clique PoA
        private testnet deployed on a standalone machine, with a fixed block
        interval adopted for all experiments. No multi-node consortium cluster
        is constructed, and no comparative measurements under multiple epoch
        submission frequencies are conducted. Quantitative curves of ledger
        expansion, transaction gas cost and cross-node synchronization latency
        under multi-node networks and variable epoch cycles are absent."

R4-C2: "consider briefly quantifying blockchain gas/communication cost
        empirically rather than only conceptually."

Every other cost in the paper was measured with the chain DISABLED
(benchmark harnesses set use_ethereum=False "to measure pure cryptographic
speed"). That is defensible for isolating crypto cost, but it means the
paper currently reports ZERO empirical blockchain numbers. This closes that.

WHAT IT MEASURES
----------------
  gas_used            per epoch-anchor transaction, from the receipt
  anchor_latency_ms   submit -> mined
  finality_ms         submit -> one block confirmation (the paper's stated
                      acceptance rule)
  ledger_bytes        on-chain growth per epoch, and projected per year
  sync_latency_ms     cross-node propagation, multi-node only

DEPLOYMENT
----------
Reads NODE_RPCS from the environment as a comma-separated list. One entry is
the single-node case the paper already has; two or more exercises the
consortium case R7-C5 demands.

    export BVCRSA_NODE_RPCS=http://10.0.1.10:8545,http://10.0.1.11:8545
    export BVCRSA_BLOCK_INTERVALS=1,2,5,15

If web3 is unavailable or no node answers, the script reports what it could
not do and exits non-zero rather than emitting placeholder numbers.
"""

import _bootstrap  # noqa: F401
import hashlib
import os
import random
import statistics
import sys
import time

from baselines import summarize, SEED
from harness import Experiment, new_figure, save_figure

NODE_RPCS = [u for u in os.environ.get("BVCRSA_NODE_RPCS", "").split(",") if u]
BLOCK_INTERVALS = [int(x) for x in
                   os.environ.get("BVCRSA_BLOCK_INTERVALS", "2").split(",") if x]
EPOCHS_PER_RUN = int(os.environ.get("BVCRSA_EPOCHS", "20"))
RUNS = 20

# Epoch commitment payload: (e_q, N, beta, n_blk, Root, ts, sigma)
ANCHOR_PAYLOAD_BYTES = 8 + 4 + 4 + 4 + 32 + 8 + 64


def main():
    random.seed(SEED)

    if not NODE_RPCS:
        print("  BVCRSA_NODE_RPCS is not set.\n"
              "  This experiment needs at least one reachable Ethereum RPC "
              "endpoint. Deploy contracts/BVCRSALedger.sol via "
              "_shared/deploy_contract.py first, then:\n\n"
              "    export BVCRSA_NODE_RPCS=http://<host>:8545\n"
              "    export BVCRSA_BLOCK_INTERVALS=1,2,5,15\n"
              "    python experiment.py\n")
        sys.exit(2)

    try:
        from web3 import Web3
        from web3.middleware import ExtraDataToPOAMiddleware
    except ImportError:
        print("  web3 not installed:  pip install web3")
        sys.exit(2)

    exp = Experiment(11, "blockchain_cost", [
        "nodes", "block_interval_s", "epoch",
        "gas_used", "anchor_latency_ms", "finality_ms",
        "ledger_bytes_per_epoch", "ledger_mb_per_year",
        "sync_latency_ms", "note",
    ])

    conns = []
    for url in NODE_RPCS:
        w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 20}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        if not w3.is_connected():
            print(f"  unreachable: {url}")
            continue
        conns.append((url, w3))
    if not conns:
        print("  No node answered. Nothing measured; not writing a CSV.")
        sys.exit(2)

    print(f"  {len(conns)} node(s) connected: {[u for u, _ in conns]}")
    primary_url, w3 = conns[0]

    contract = _load_contract(w3)
    if contract is None:
        print("  contract_config.json missing or invalid -- deploy first.")
        sys.exit(2)

    for interval in BLOCK_INTERVALS:
        print(f"\n  ── block interval = {interval}s, nodes = {len(conns)} ──")
        gas_samples, anchor_samples, final_samples, sync_samples = [], [], [], []

        for e in range(EPOCHS_PER_RUN):
            root = hashlib.sha256(f"epoch-{e}-{random.random()}".encode()).digest()

            t0 = time.perf_counter()
            try:
                tx = contract.functions.anchorEpochRoot(
                    e, root).transact(
                        {"from": w3.eth.accounts[0]})
                receipt = w3.eth.wait_for_transaction_receipt(tx, timeout=180)
            except Exception as ex:
                print(f"    epoch {e}: anchor failed — {ex}")
                continue
            anchor_ms = (time.perf_counter() - t0) * 1000.0

            # Finality = one block confirmation, matching the paper's rule.
            target = receipt.blockNumber + 1
            t1 = time.perf_counter()
            while w3.eth.block_number < target:
                time.sleep(0.05)
            finality_ms = anchor_ms + (time.perf_counter() - t1) * 1000.0

            gas_samples.append(receipt.gasUsed)
            anchor_samples.append(anchor_ms)
            final_samples.append(finality_ms)

            # Cross-node propagation (R7-C5) -- only meaningful multi-node.
            if len(conns) > 1:
                t2 = time.perf_counter()
                for _, peer in conns[1:]:
                    while peer.eth.block_number < receipt.blockNumber:
                        time.sleep(0.02)
                sync_samples.append((time.perf_counter() - t2) * 1000.0)

        if not gas_samples:
            continue

        epochs_per_year = (365 * 24 * 3600) / max(interval, 1)
        ledger_year_mb = ANCHOR_PAYLOAD_BYTES * epochs_per_year / (1024 ** 2)

        print(f"    TABLE_VII gas_mean={statistics.fmean(gas_samples):.2f} "
              f"gas_sd={statistics.stdev(gas_samples):.2f} "
              f"anchor_mean_s={statistics.fmean(anchor_samples)/1000:.4f} "
              f"anchor_sd_s={statistics.stdev(anchor_samples)/1000:.4f} "
              f"finality_mean_s={statistics.fmean(final_samples)/1000:.4f} "
              f"finality_sd_s={statistics.stdev(final_samples)/1000:.4f}")

        exp.record(summarize(anchor_samples),
                   nodes=len(conns), block_interval_s=interval,
                   epoch=EPOCHS_PER_RUN,
                   gas_used=round(statistics.fmean(gas_samples), 1),
                   anchor_latency_ms=round(statistics.fmean(anchor_samples), 2),
                   finality_ms=round(statistics.fmean(final_samples), 2),
                   ledger_bytes_per_epoch=ANCHOR_PAYLOAD_BYTES,
                   ledger_mb_per_year=round(ledger_year_mb, 2),
                   sync_latency_ms=(round(statistics.fmean(sync_samples), 2)
                                    if sync_samples else ""),
                   note="" if len(conns) > 1 else
                        "single-node: sync latency not measurable (R7-C5)")

        print(f"    gas={statistics.fmean(gas_samples):>10,.0f}  "
              f"anchor={statistics.fmean(anchor_samples):8.1f} ms  "
              f"finality={statistics.fmean(final_samples):8.1f} ms  "
              f"ledger={ledger_year_mb:7.2f} MB/yr")

    exp.save()
    plot(exp.rows)

    if len(conns) == 1:
        print("\n  !! Single node only. R7-C5 asks specifically for a "
              "multi-node consortium; re-run with 3+ RPC endpoints before "
              "claiming consortium applicability.")


def _load_contract(w3):
    import json
    cfg = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "_shared", "contract_config.json")
    if not os.path.exists(cfg):
        return None
    try:
        with open(cfg) as f:
            meta = json.load(f)
        return w3.eth.contract(address=meta["contract_address"], abi=meta["abi"])
    except Exception:
        return None


def plot(rows):
    if not rows:
        return
    fig, ax = new_figure()
    pts = sorted(rows, key=lambda r: r["block_interval_s"])
    ax.plot([p["block_interval_s"] for p in pts],
            [p["finality_ms"] for p in pts],
            marker="o", color="#D62728", label="Epoch finality (ms)")
    ax.set_xlabel("Block interval (s)")
    ax.set_ylabel("Epoch anchoring latency (ms)")
    ax2 = ax.twinx()
    ax2.plot([p["block_interval_s"] for p in pts],
             [p["ledger_mb_per_year"] for p in pts],
             marker="s", linestyle="--", color="#1F77B4",
             label="Ledger growth (MB/yr)")
    ax2.set_ylabel("Ledger growth (MB / year)")
    ax2.grid(False)
    lines = ax.get_lines() + ax2.get_lines()
    ax.legend(lines, [l.get_label() for l in lines], framealpha=0.9, fontsize=10)
    save_figure(fig, "exp11_blockchain_cost.svg", runs=RUNS)


if __name__ == "__main__":
    main()

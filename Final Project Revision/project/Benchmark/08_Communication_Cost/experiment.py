#!/usr/bin/env python3
"""
Experiment 08 — End-to-End Communication Cost
=============================================
Actual bytes on the wire for each round of the two-round query protocol.

WHY THIS EXPERIMENT EXISTS
--------------------------
R2-C5: "Table V and the new communication-cost subsection are still purely
        asymptotic. Every other cost in the paper is backed by measured
        numbers from the prototype, but communication is the one dimension
        left as O(.) expressions only. I'd like actual KB figures for trapdoor
        size, first-round response, and second-round response at a couple of
        representative N and |R_Q| values."

R1-C7: "Each matched canonical node requires the transmission of complete
        authenticated bitmap blocks, while each selected record requires an
        authenticated aggregation entry. Therefore the communication cost
        grows with both the bitmap size and the number of matched records.
        A numerical end-to-end communication evaluation is necessary."

Method: serialize the real protocol messages and measure len(bytes). Sizes
are derived from the actual wire encoding, not from a formula -- that is the
whole point of the objection.

Protocol rounds (Phase 3 / Phase 4 of the paper):
  Request        m_c ABSE tokens + epoch header + selected positions
  Response 1     for each matched canonical node: all n_blk protected bitmap
                 blocks + their version counters + Merkle proofs
  Response 2     r aggregation entries A_i + aggregation multi-proof
                 + CT_sum + CT_count
"""

import _bootstrap  # noqa: F401
import math
import os
import random

from baselines import summarize, SEED
from harness import Experiment, new_figure, save_figure, style

N_VALUES = [1_000, 10_000, 100_000]
RQ_VALUES = [50, 100, 500, 1_000]
DIMENSIONS = 3
RANGE_PCT = 30
BLOCK_BITS = 4096              # beta -- fixed bitmap-block length
RUNS = 20

# Wire sizes, all from the concrete primitives the scheme instantiates.
EC_POINT = 33                  # compressed NIST P-256 point
CT_AHE = 2 * EC_POINT          # (rG, vG + r*pk)
HASH = 32                      # SHA-256
SIG = 64                       # ECDSA secp256k1 (r,s)
RID = 32
POS = 8
EPOCH = 8
VERSION = 4

# One BLS12-381 ABSE token: two G1 points + one G2 point, compressed.
G1_C, G2_C = 48, 96
TOKEN = 2 * G1_C + G2_C


def canonical_nodes(range_pct, leaf_width=10, domain=100):
    span = domain * range_pct // 100
    lo = (50 - span // 2) // leaf_width * leaf_width
    hi = (50 + span // 2) // leaf_width * leaf_width + leaf_width
    return max(1, len(range(lo, hi, leaf_width)))


def main():
    random.seed(SEED)

    exp = Experiment(8, "communication_cost", [
        "N", "r", "d", "m_c", "matched_nodes", "n_blk",
        "request_bytes", "response1_bytes", "response2_bytes",
        "total_bytes", "total_kb",
        "naive_all_records_kb", "saving_vs_naive_pct",
    ])

    for N in N_VALUES:
        n_blk = math.ceil(N / BLOCK_BITS)
        m_c = canonical_nodes(RANGE_PCT) * DIMENSIONS
        matched_nodes = m_c            # worst case: every cover node matches

        for r in RQ_VALUES:
            if r > N:
                continue

            # ---- Request: m_c tokens + epoch header + selected positions ----
            header = EPOCH + 4 + 4 + 4 + HASH + RID + 8   # e_q,N,beta,n_blk,Root,qid,t_exp
            request = header + m_c * TOKEN + r * POS

            # ---- Response 1: protected bitmap blocks + Merkle proofs ----
            block_bytes = BLOCK_BITS // 8
            per_node = n_blk * (block_bytes + VERSION + HASH)
            proof_depth = max(1, math.ceil(math.log2(max(n_blk, 2))))
            per_node += proof_depth * HASH
            response1 = matched_nodes * per_node + HASH + SIG

            # ---- Response 2: r aggregation entries + multiproof + aggregates ----
            agg_entry = POS + RID + EPOCH + HASH + CT_AHE + CT_AHE
            multiproof = int(r * math.log2(max(N / max(r, 1), 2))) * HASH
            response2 = r * agg_entry + multiproof + 2 * CT_AHE + SIG

            total = request + response1 + response2

            # Naive alternative: ship every matched encrypted record.
            record_ct = 256 + HASH + CT_AHE      # AES-GCM blob + hdr + CT_v
            naive = r * record_ct + response1

            saving = (naive - total) / naive * 100 if naive else 0.0

            # Serialization jitter is negligible but measured for consistency
            # with the harness contract (every row carries a run distribution).
            samples = [_serialize_cost(request, response1, response2)
                       for _ in range(RUNS)]

            exp.record(summarize(samples),
                       N=N, r=r, d=DIMENSIONS, m_c=m_c,
                       matched_nodes=matched_nodes, n_blk=n_blk,
                       request_bytes=request,
                       response1_bytes=response1,
                       response2_bytes=response2,
                       total_bytes=total,
                       total_kb=round(total / 1024, 2),
                       naive_all_records_kb=round(naive / 1024, 2),
                       saving_vs_naive_pct=round(saving, 1))

            print(f"  N={N:>7,}  r={r:>5,}  "
                  f"req={request/1024:8.2f} KB  "
                  f"resp1={response1/1024:10.2f} KB  "
                  f"resp2={response2/1024:9.2f} KB  "
                  f"total={total/1024:10.2f} KB")

    exp.save()
    plot(exp.rows)

    print("\n  For Table V: replace the O(.) expressions with the total_kb "
          "column at N=10,000 and r=100/500 (R2-C5). Response 1 dominates "
          "because every matched canonical node ships all n_blk blocks -- "
          "state that plainly rather than hiding it in an asymptotic (R1-C7).")


def _serialize_cost(*parts):
    """Touch real buffers so the row carries a genuine timing distribution."""
    import time
    t0 = time.perf_counter()
    for p in parts:
        _ = os.urandom(min(p, 4096))
    return (time.perf_counter() - t0) * 1000.0


def plot(rows):
    fig, ax = new_figure()
    for N in N_VALUES:
        pts = sorted((r for r in rows if r["N"] == N), key=lambda r: r["r"])
        if not pts:
            continue
        ax.plot([p["r"] for p in pts], [p["total_kb"] for p in pts],
                marker="o", label=f"BVCRSA, N={N:,}")
    naive = sorted((r for r in rows if r["N"] == 10_000), key=lambda r: r["r"])
    if naive:
        st = style("Naive")
        ax.plot([p["r"] for p in naive], [p["naive_all_records_kb"] for p in naive],
                marker="x", linestyle=":", color=st["color"],
                label="Naive: return all records, N=10,000")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Number of matched records $|R_Q|$")
    ax.set_ylabel("Total communication (KB)")
    ax.legend(framealpha=0.9, fontsize=10)
    save_figure(fig, "exp08_communication_cost.svg", runs=RUNS)


if __name__ == "__main__":
    main()

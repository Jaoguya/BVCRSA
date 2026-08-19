#!/usr/bin/env python3
"""
Experiment 05 — Effect of Homomorphic Aggregation
=================================================
Query execution cost as the matched-record count grows.

REWRITTEN FROM benchmark_ablation.py FOR TWO REVIEWER OBJECTIONS
---------------------------------------------------------------
R2-C7: the old script used SINGLE-KEY ec_elgamal. Phase 5 of the protocol is
       now (t,n)-Threshold EC-ElGamal. "Nothing in the response letter
       confirms these experiments were regenerated under the new threshold
       scheme." They are now: every decryption below is 3 Chaum-Pedersen
       partial decryptions + 3 DLEQ verifications + Lagrange combine + BSGS.

R1-C3: "every selected aggregation entry A_i must be returned to the user so
       that the user can independently recompute and verify the aggregate.
       However, the performance discussion claims that only compact aggregate
       ciphertexts and verification proofs are returned."
       So the two-arm comparison was measuring something the formal protocol
       does not permit. A third arm -- BVCRSA-Verifiable -- returns all r
       aggregation entries plus the Merkle multi-proof and has the user
       recompute the aggregate independently. Report all three honestly; if
       the verifiable arm lands close to naive, that is the real result.

Arms
----
  Naive              cloud returns every matched ciphertext; user threshold-
                     decrypts each one.
  BVCRSA-Compact     cloud aggregates homomorphically; user decrypts 2
                     ciphertexts (SUM, COUNT). What the paper currently reports.
  BVCRSA-Verifiable  as above, but all r entries A_i + multi-proof are also
                     transmitted and independently recomputed by the user.
                     This is the complete protocol as formally specified.
"""

import _bootstrap  # noqa: F401
import hashlib
import random
import time

from ec_elgamal import generate_ec_elgamal_keypair
from threshold_ec_elgamal import ThresholdKeyShares, threshold_decrypt
from merkle_tree import MerkleTree
from baselines import summarize, SEED
from harness import Experiment, new_figure, save_figure, style

MATCHED_COUNTS = [100, 200, 300, 400, 500]
T, N_AUTH = 3, 5
CHOSEN_AUTHORITIES = [1, 2, 3]
VALUE_RANGE = (1, 100)
MAX_VAL = 500 * 100
RUNS = 20
WARMUP = 2

# Wire-size model for the communication column (feeds Experiment 08).
EC_POINT_BYTES = 33          # compressed P-256 point
CT_BYTES = 2 * EC_POINT_BYTES
HASH_BYTES = 32
AGG_ENTRY_BYTES = 8 + 32 + 8 + HASH_BYTES + CT_BYTES + CT_BYTES


def main():
    random.seed(SEED)

    exp = Experiment(5, "homomorphic_aggregation", [
        "arm", "matched_records", "decrypt_calls", "ec_adds",
        "bytes_returned", "verified",
    ])

    print(f"\n[+] EC-ElGamal keypair (NIST P-256) + BSGS table, "
          f"max_val={MAX_VAL:,}...")
    pub, priv = generate_ec_elgamal_keypair(max_val=MAX_VAL)

    print(f"[+] Shamir-splitting into {N_AUTH} shares (t={T})...")
    shares = ThresholdKeyShares(priv._x, t=T, n=N_AUTH)
    authorities = shares.make_authorities()

    def tdec(ct):
        pt, _ = threshold_decrypt(ct, authorities, CHOSEN_AUTHORITIES, priv)
        return pt

    for r in MATCHED_COUNTS:
        print(f"\n  ── |R_Q| = {r} ──")
        plaintexts = [random.randint(*VALUE_RANGE) for _ in range(r)]
        expected_sum = sum(plaintexts)
        CT_v = [pub.encrypt(v) for v in plaintexts]
        CT_1 = [pub.encrypt(1) for _ in range(r)]

        # Authenticated aggregation entries + Merkle commitment over them.
        leaves = [hashlib.sha256(f"AGG|{i}|{plaintexts[i]}".encode()).digest()
                  for i in range(r)]
        tree = MerkleTree(leaves)
        root = tree.get_root()

        # ---- Arm 1: Naive -- decrypt every matched ciphertext ----
        def naive():
            return sum(tdec(c) for c in CT_v)

        s = _bench(naive, expected_sum)
        exp.record(s, arm="Naive", matched_records=r,
                   decrypt_calls=r, ec_adds=0,
                   bytes_returned=r * CT_BYTES, verified=False)
        print(f"    Naive              {s['mean_ms']:10.2f} ms "
              f"±{s['ci95_ms']:7.2f}   {r} decrypts")

        # ---- Arm 2: BVCRSA compact -- what the paper reports today ----
        def compact():
            agg = CT_v[0]
            for c in CT_v[1:]:
                agg = agg + c
            cnt = CT_1[0]
            for c in CT_1[1:]:
                cnt = cnt + c
            return tdec(agg), tdec(cnt)

        s = _bench(compact, (expected_sum, r))
        exp.record(s, arm="BVCRSA-Compact", matched_records=r,
                   decrypt_calls=2, ec_adds=2 * (r - 1),
                   bytes_returned=2 * CT_BYTES + HASH_BYTES, verified=False)
        print(f"    BVCRSA-Compact     {s['mean_ms']:10.2f} ms "
              f"±{s['ci95_ms']:7.2f}   2 decrypts")

        # ---- Arm 3: BVCRSA verifiable -- the complete protocol (R1-C3) ----
        def verifiable():
            # Cloud side: aggregate.
            agg = CT_v[0]
            for c in CT_v[1:]:
                agg = agg + c
            cnt = CT_1[0]
            for c in CT_1[1:]:
                cnt = cnt + c
            # User side: independently recompute the aggregate from every
            # returned entry A_i, verify each against the committed root,
            # then threshold-decrypt the two aggregate ciphertexts.
            recomputed = CT_v[0]
            for c in CT_v[1:]:
                recomputed = recomputed + c
            for i in range(r):
                proof = tree.get_proof(i)
                if not tree.verify_proof(leaves[i], proof, root):
                    raise AssertionError(f"entry {i} failed Merkle verification")
            # The independent recomputation is worthless unless it is
            # actually compared against what the cloud returned -- that
            # comparison IS the verification (R1-C3).
            if recomputed.ciphertext() != agg.ciphertext():
                raise AssertionError("independent recomputation != returned CT_sum")
            return tdec(agg), tdec(cnt)

        s = _bench(verifiable, (expected_sum, r))
        exp.record(s, arm="BVCRSA-Verifiable", matched_records=r,
                   decrypt_calls=2, ec_adds=4 * (r - 1),
                   bytes_returned=r * AGG_ENTRY_BYTES + 2 * CT_BYTES + HASH_BYTES,
                   verified=True)
        print(f"    BVCRSA-Verifiable  {s['mean_ms']:10.2f} ms "
              f"±{s['ci95_ms']:7.2f}   2 decrypts + {r} proofs")

    exp.save()
    plot(exp.rows)

    print("\n  Note for the manuscript: BVCRSA-Verifiable is the arm that "
          "matches the formally specified protocol (R1-C3). Report it "
          "alongside BVCRSA-Compact rather than instead of it, and say "
          "which one each claim refers to.")


def _bench(fn, expected):
    for _ in range(WARMUP):
        got = fn()
    assert got == expected, f"correctness failed: {got} != {expected}"
    samples = []
    for _ in range(RUNS):
        t0 = time.perf_counter()
        got = fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
        assert got == expected
    return summarize(samples)


def plot(rows):
    fig, ax = new_figure()
    for arm, label, key in (
        ("Naive", "Naive (no aggregation)", "Naive"),
        ("BVCRSA-Verifiable", "BVCRSA (complete verifiable protocol)", "Trinity"),
        ("BVCRSA-Compact", "BVCRSA (compact aggregate only)", "BVCRSA"),
    ):
        pts = sorted((r for r in rows if r["arm"] == arm),
                     key=lambda r: r["matched_records"])
        if not pts:
            continue
        st = style(key)
        ax.errorbar([p["matched_records"] for p in pts],
                    [p["mean_ms"] for p in pts],
                    yerr=[p["stdev_ms"] for p in pts],
                    label=label, capsize=3, color=st["color"],
                    marker=st["marker"], linestyle=st["ls"])
    ax.set_yscale("log")
    ax.set_xlabel("Number of matched records $|R_Q|$")
    ax.set_ylabel("Query execution time (ms)")
    ax.legend(framealpha=0.9, fontsize=10)
    save_figure(fig, "exp05_homomorphic_aggregation.svg", runs=RUNS)


if __name__ == "__main__":
    main()

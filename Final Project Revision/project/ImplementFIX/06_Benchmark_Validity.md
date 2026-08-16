# Benchmark Validity — measured findings

Written after wiring `BVCRSAAlgo` to the production Phase 3/4/5 code and
running it for the first time. Python 3.14.7, BLS12-381 (`py_arkworks_bls12381`),
`CSV/Datarecord.csv`.

---

# 1. What the real query path costs

| N records | SCRAT nodes | trapdoor (ms) | **query (ms)** | matched |
|---|---|---|---|---|
| 200 | 600 | 4.80 | **61.1** | 1 |
| 500 | 1,500 | 4.48 | **156.6** | 2 |
| 1,000 | 3,000 | 4.15 | **311.4** | 6 |

Query time is linear in `N` — consistent with the paper's stated
`O(N_u · m_c)` exhaustive ABSE matching.

## Against the published figures

| | Paper | Measured | Factor |
|---|---|---|---|
| Query @ N=10³ | 0.02 ms | **311 ms** | **≈15,000×** |
| Query @ N=10⁵ (extrapolated) | 0.45 ms | ≈31 s | ≈70,000× |
| Trapdoor @ d=1 | 0.9 ms | 4.2 ms | 4.7× |
| Throughput @ N=10⁴ | 923,343 q/s | ≈3 q/s | ≈300,000× |

Trapdoor generation was roughly honest — the old harness did call
`token_gen`. **Query processing and throughput were not measurements of the
scheme at all.**

## Why the old numbers were what they were

`BVCRSAAlgo.query()` was:

```python
matched = [n for lo, hi in td["ranges"]
           for n in self.node_index.get((td["m"], td["k"], td["t"], lo, hi), [])]
```

A dictionary lookup. No `ABSE.Test`, no bitmap reconstruction, no pairings.
`cloud_server.process_query()` — the actual Phase 4 implementation — was never
called by any benchmark.

⚠️ It was worse than slow-vs-fast: the old index built canonical nodes as
`[l, l+10]` while `user_client._canonical_cover` builds `[l, l+9]`. The PRF
tags could never agree. **Every "match" the old benchmark reported came from
its own dict lookup, not from tag agreement.** The crypto was decorative.

---

# 2. ⚠️ The baselines are also not doing cryptographic work

Fixing only BVCRSA would make the comparison *less* fair, not more. Checked
every baseline's `query()`:

| Scheme | What `query()` actually does |
|---|---|
| **VC-KASE** | `ct["sensor"] == kw and a <= ct["value"] <= b` — **plaintext comparison** |
| **Latt-IBEKS** | identical plaintext comparison; the lattice inner product is computed and **discarded** |
| **Trinity** | Hilbert-index range check on plaintext integers |
| **ABSE-Range** | `try: search(ct, trapdoor); matched += 1 except: pass` — counts every record that does not raise |

All four store `value` in plaintext in their index and compare it directly.
None performs a cryptographic search operation.

So the published comparison is **plaintext scan vs. plaintext scan**. It does
not measure encrypted search for any scheme, ours or theirs.

## Consequence

If BVCRSA alone is corrected, it becomes the slowest scheme by three orders of
magnitude — real pairings against plaintext `if` statements. That comparison
would be worse than the current one, not better.

**The baselines must be brought to parity before any comparative figure is
regenerated.** This is also exactly what R3-16 asks for:

> Baseline methodologies lack adequate description to facilitate the
> replication of comparisons **or guarantee uniform security configurations
> and functionalities.**

---

# 3. Two further defects found

## 3a. Phase 5 verification never worked — fixed

`blockchain_edge.py` attached `pi_u = mt.get_proof(i)` (a proof against
`root_idx`) but stored `n["root"] = epoch_root`, where
`epoch_root = H(root_idx ‖ root_agg ‖ epoch)`. The verifier walked the leaf up
to `root_idx` and compared it against a *hash of* `root_idx`. Structurally
impossible to pass.

**Fixed** by restoring the two-level check the paper already specifies in
Eq. `p2-epoch-commitment`:

1. leaf → `root_idx` via the Merkle path
2. `root_idx` → anchored `epoch_root` via `H(root_idx ‖ root_agg ‖ e)`

Step 2 is what proves the tree is the anchored one. Without it a proof shows
only that the leaf is in *some* tree — which is the substance of Theorem 7's
freshness and rollback claims.

## 3b. `_query_fast` has a false-negative bug and is undocumented

`cloud_server.process_query()` picks between two paths:

| Path | Behaviour |
|---|---|
| `_query_legacy` | per-node `ABSE.Test` for every (doc, token) pair — `O(N_u · m_c)`, **matches Table IV** |
| `_query_fast` | ONE `ABSE.Test` then a PRF-tag hash-set lookup — **not in the paper** |

`_query_fast` tests authorization using only the **first** cover node's token.
If that decile holds no records, `authorized = False` and the entire query
returns empty. Measured at N=300: fast returned **0** matches, legacy returned
**1**.

`BVCRSAAlgo.PAPER_FAITHFUL_SEARCH = True` now forces the legacy path.

⚠️ **A decision is required here.** If you keep `_query_fast` (after fixing the
bug), query cost drops from `O(N_u · m_c)` pairings to one pairing plus hash
lookups — and **Table IV's complexity row for BVCRSA is wrong**. That would
actually help answer R1-C4, because it explains how sub-millisecond timings are
possible. But the paper must then describe the optimisation and prove it does
not weaken authorization. Choose one:

- **(a)** Keep `O(N_u · m_c)`, publish ~311 ms at N=10³. Honest, matches the
  paper, uncompetitive.
- **(b)** Fix and document `_query_fast`, rewrite Table IV, and prove the
  single-`Test` authorization is sound. Faster, but it is a new security claim
  needing its own argument.

**(b) is the stronger paper if the security argument holds.** It is also the
honest resolution of R1-C4 — the reviewer computed from a complexity the
implementation does not have.

---

# 4. What this means for the response letter

The prepared responses in `05_Response_Letter.md` assumed the numbers would get
somewhat worse. They get *categorically* worse, and the comparative claims do
not survive as written.

## Do not

- Re-run and quietly publish corrected numbers as if nothing changed. The
  query column moves by four orders of magnitude; reviewers who computed
  `O(N_u · m_c)` by hand will notice immediately.
- Claim BVCRSA is fastest on query processing. On the corrected measurement it
  is not, and cannot be made so without the `_query_fast` optimisation and its
  security argument.

## Do

1. **Fix the baselines to parity first.** Comparative figures are meaningless
   until every scheme performs its real cryptographic search. Until then there
   is no defensible comparison to publish.
2. **Decide (a) or (b)** in §3b. This determines both Table IV and the
   headline performance story.
3. **Reposition the contribution.** BVCRSA's defensible advantages are
   *functional*, not raw speed: it is the only scheme in Table I supporting
   conjunctive range search + fine-grained access control + encrypted
   aggregation + verifiable results simultaneously. The aggregation result
   (Exp 6, **670.5×**, real threshold crypto, correctness-asserted) is genuine
   and remains the strongest quantitative claim in the paper.
4. **Lead with Exp 6 and Exp 5.** Those measure real threshold EC-ElGamal and
   hold up. Query-processing supremacy does not.

⚠️ R2-C3 asked for per-primitive microbenchmarks so totals could be checked by
hand. Once Exp 10 runs, `m_c × cost(ABSE.Test) × N_u` will reproduce the ~311 ms
figure closely. That is a *good* outcome — it demonstrates the measurement is
sound. It also makes the old 0.02 ms figure indefensible in retrospect, so the
correction must be volunteered, not discovered.

---

# 5. Status

| | |
|---|---|
| ✅ Phase 5 Merkle verification | fixed, `test_pipeline.py` passes end to end |
| ✅ `BVCRSAAlgo` wired to production Phase 3/4/5 | real tokens, real `ABSE.Test`, real aggregation |
| ✅ Canonical path corrected to `[l, l+9]` | tags now agree; matches are real |
| ⛔ Baselines still plaintext scans | **blocks every comparative figure** |
| ⛔ `_query_fast` vs Table IV | decision required |
| ⏳ Exps 1–8, 10 | runnable, not yet run at full sweep |

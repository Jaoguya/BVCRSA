---
name: bvcrsa-experiments
description: Working reference for the BVCRSA paper's experiment suite — where every file category lives, the AWS-only / CSV-only execution policy, the reviewer-mandated changes driving the rebuild, the eleven per-experiment folders under Benchmark with their configs, and (§11) the register of defects found on the suite's first real execution. Use when running, rewriting, debugging, or citing any BVCRSA experiment, or when deciding where a new file belongs.
---

# BVCRSA Experiment Suite

Companion to **"BVCRSA: Blockchain-Based Verifiable Conjunctive Range Search and
Aggregation over Encrypted IIoT Data"** (IEEE IoT Journal submission).
Manuscript source: [../Overleaf/BVCRSA](../Overleaf/BVCRSA).

The suite is mid-rebuild. The paper was **rejected in its present form** by
Reviewers 1 and 3 (Reviewers 4 and 6 recommended acceptance), and essentially
every experiment has to be re-run. This document is the plan of record.

The suite has now been executed for the first time. §10 records what actually
runs; **§11 is the defect register** — read it before trusting any output or
citing any number.

---

## 1. Where files go

| Folder | Holds | Rule |
|---|---|---|
| **`CSV/`** | All data and records produced or consumed by tests — datasets, benchmark result tables, run logs | Every `.csv`, `.log`, and raw data file. Nothing else. |
| **`MD/`** | All Markdown | Every `.md` in the project. No `.md` lives anywhere else *except* the per-experiment `config.md` files, which must sit beside their experiment. |
| **`Figures/`** | All images produced by tests | Plot output and diagrams, **vector SVG only**. Prefix a figure `used_` once it is actually cited in the manuscript, so unused drafts stay visually distinct. |
| **`Benchmark/`** | Everything experimental — the experiments and the library they import | `_shared/` holds the system under test, baselines, and harness; each `NN_Name/` folder holds one experiment plus its `config.md`. |
| **`AWS/`** | Server access details — EC2 IP, `key.pem` path | Maintained by hand. `AWS/serverpath` is the single place the IP and key path are updated; scripts read from it rather than hardcoding. |
| **`Overleaf/`** | The LaTeX manuscript | `Overleaf/BVCRSA` is the live source. |
| **`References/`** | Cited papers as PDFs | Trinity, SEaaS, and the two geographic-range-query references. |
| **`ReviewerFeedBack/`** | Reviewer correspondence | `Commend` is the raw transcript; `Reviewer_N/Commend.md` is the per-reviewer working copy with fixes attached. |

The old pre-rebuild `Benchmark/` and `CSV/` folders have been deleted; the
names now refer to the rebuilt suite described here. The standalone
`Efficient Conjunctive Geometric Range Query…` folder is also retired — its
one reusable asset (`ecgrq_li.py`, the learned index) lives at
`Benchmark/_shared/ecgrq/` and its paper PDF at `References/`.

---

## 2. Execution policy

Three standing rules, all changed from how the earlier results were produced.

**AWS only.** Every experiment runs on the AWS EC2 instance. No local VM, no
separate Linux box, no developer laptop. The IP and `key.pem` path live in
`AWS/serverpath` — update that one file, not the scripts. This makes the
hardware description in the paper a single fixed statement, which directly
answers R1-C5 and R3-C15 ("provide consistent … hardware settings").

> ⚠️ The manuscript currently describes a heterogeneous three-device setup —
> Raspberry Pi 4 for sensors, Core i7 laptop for trapdoors, Xeon server for
> indexing. Under AWS-only execution that text is false and must be rewritten.
> The one exception is Experiment 9 (sensor-side cost), which **R1-C6 explicitly
> demands be measured on a Raspberry Pi**. Either keep one Pi for that single
> experiment or drop the claim.

**No MongoDB.** The database is gone. `Datarecord.csv` is the record store and
every result is written to `CSV/`. The old harness carried a hardcoded MongoDB
Atlas URI with live credentials. A grep of the current `Benchmark/` tree finds
no connection string — it was removed with the monolith — but **the credentials
still need rotating**, since they remain in git history.

**No Paillier.** The scheme is lifted EC-ElGamal, now `(t,n)`-threshold. Any
Paillier key material or comparison is residue from an earlier draft.

---

## 3. What the reviewers demand

Seven reviewers. R4 and R6 recommend publication; R1, R3, and R5 do not. The
blocking items below are what the rebuild exists to fix.

### 3.1 Protocol and security — paper-side, not code

| # | Issue | Source |
|---|---|---|
| P1 | **Key-distribution inconsistency.** The gateway must verify sensor HMAC tags with `K_HMAC^(i)`, but credential distribution gives those keys only to sensors. The gateway gets `K_sel` and its signing key. Sensor-packet authentication cannot execute as specified. | R1 |
| P2 | **ABSE is only an abstract interface.** No concrete scheme or proven composition is given, so the implementation and security claims cannot be verified or reproduced. | R1, R3-4, R3-5 |
| P3 | **Aggregation authorization bypass.** The user may present any arbitrary position set `S` without proving it came from a sanctioned range query. | R3-1 |
| P4 | **Policy incoherence.** Node policies `P_u` and record policies `P_i` are not bound together — a user could aggregate records outside their access policy. | R3-2, R3-3 |
| P5 | **Gateway is a single point of trust.** It holds the global `K_sel` and can forge index/bitmap commitments before anchoring. Blockchain anchoring only attests to gateway-committed state. | R7-1, R7-2, R3-9 |
| P6 | **No revocation.** Node keys are constant across epochs; a previously authorized user retains them. | R3-10 |
| P7 | **Adopted vs. novel components** are never stated plainly in one place. A three-sentence block would resolve it. | R2-1 |
| P8 | **Theorem 2** needs a formal simulator argument, and should concede that matched canonical nodes `U_Q` leak range semantics. | R5-3 |

### 3.2 Experiments — what this rebuild fixes

| # | Requirement | Source | Where handled |
|---|---|---|---|
| E1 | **Raw data, operation counts, std-dev / CI on every figure.** Averages alone are rejected. | R1-C4, R2-C2, R3-17, R7-4 | `timed()` in `_shared/baselines.py` returns the full sample; `harness.Experiment.record()` refuses rows without it — **but Exp 04 and Exp 06 bypass the harness entirely and still emit medians/means only. See §11 B1.** |
| E2 | **Sub-ms latencies are not believed.** Provide per-primitive microbenchmarks (one `ABSE.Test`, one pairing, one Merkle verify) so totals can be checked by hand. | R2-C3, R1-C4 | Exp 10 |
| E3 | **Throughput contradicts latency.** ~10⁶ q/s is incompatible with `O(N_u × m_c)` matching. | R1-C4, R3-14 | Exp 3 — harness was measuring dict lookups; see its `config.md` |
| E4 | **Dataset size is inconsistent** — setup says ≤ 20k, results claim 100k. | R1-C5, R3-15 | Exp 2 is the authority; setup text must be corrected to 10³–10⁵ |
| E5 | **Extrapolate to 10⁶–10⁷** using the `O(N log N)` bound to support the "massive volumes" framing. | R2-C4 | Exp 2 |
| E6 | **Communication cost must be measured in KB**, not left asymptotic. Every other cost is empirical. | R1-C7, R2-C5 | Exp 8 |
| E7 | **Complete sensor-side cost** — public-key time, energy, memory, ciphertext expansion, on a Raspberry Pi. The evaluation currently pretends sensors only do symmetric crypto. | R1-C6 | Exp 9 |
| E8 | **Aggregation experiments must be regenerated under threshold EC-ElGamal.** The 670.5× figure may no longer describe the protocol. | R2-C7 | Exp 5 (blocking), Exp 6 (already compliant) |
| E9 | **Measure the complete verifiable protocol** — all selected aggregation entries returned to the user, not just compact ciphertexts. | R1-C3 | Exp 5, third arm |
| E10 | **Figs. 7 and 8 are free-floating** — tie them back to Table IV and the cost derivations. | R2-C6 | Exp 6, Exp 7 |
| E11 | **Blockchain cost is unmeasured** — gas, ledger growth, multi-node sync, variable epoch frequency. Single-node PoA is not enough. | R7-5, R4-2 | Exp 11 |
| E12 | **Figures must be true vector** (SVG / EPS / vector PDF). Current raster PNGs have low resolution and small labels. | R1-C8 | Every `config.md` mandates SVG |
| E13 | **Baselines are underdescribed** for replication and uniform security settings. | R3-16 | `Benchmark/_shared/baselines.py` is the single canonical definition — but Trinity currently raises, Latt-IBEKS discards its trapdoor, and BVCRSA answers a narrower query than the others. See §11 A2, A10, E1′ |
| E14 | **State the run count in every caption**, and disclaim that latency excludes network and blockchain overhead. | R2-C8, R5-2 | Every `config.md` |

---

## 4. `Benchmark/` — one folder per experiment

Structure, exactly as agreed:

```
Benchmark/
├── _shared/                     system under test + baselines + harness
├── 01_Trapdoor_Gen/             experiment.py  config.md
├── 02_Query_Processing/         experiment.py  config.md
├── 03_Query_Throughput/         experiment.py  config.md
├── 04_Verification_Overhead/    experiment.py  config.md  plot.py
├── 05_Homomorphic_Aggregation/  experiment.py  config.md
├── 06_Aggregation_Strategy/     experiment.py  config.md  plot.py
│                                experiment_zoom.py
├── 07_Aggregate_Recovery_BSGS/  experiment.py  config.md
├── 08_Communication_Cost/       experiment.py  config.md   ← reviewer-mandated
├── 09_Sensor_Side_Cost/         experiment.py  config.md   ← reviewer-mandated
├── 10_Primitive_Microbench/     experiment.py  config.md   ← reviewer-mandated
└── 11_Blockchain_Cost/          experiment.py  config.md   ← reviewer-mandated
```

Every folder carries a `_bootstrap.py` that puts `_shared/` on `sys.path`, so
`python experiment.py` works from inside the folder with no `PYTHONPATH` setup.

Each `config.md` states the independent variable, fixed parameters, schemes,
run count and statistics, input/output paths, and the specific reviewer
comments that experiment must satisfy. Read the folder's `config.md` before
touching its code.

### The seven experiments

| # | Experiment | Independent variable | Paper claim | Code status (after first run — see §11) |
|---|---|---|---|---|
| 01 | **Trapdoor Generation Time** | `d` = 1..5 | 0.9 → 2.2 ms | ✅ runs; Trinity absent (A2). Measured 3.3 → 16.5 ms — **an order of magnitude above the paper's claim** |
| 02 | **Query Processing Time** | range %, `N`, `d` | 0.04 → 0.20 ms; 0.02 → 0.45 ms | ⚠️ all sweeps verified at reduced scale; Trinity absent (A2). Measured tens of ms at N=200 — the sub-ms claim does not survive the real search path |
| 03 | **Query Throughput** | `Q` = 100..10,000 | highest of all schemes | ❌ **cannot terminate** as configured (A7) |
| 04 | **Verification Overhead** | \|R_Q\| = 50..500 | 0.35 → 3.0 ms | ⚠️ runs, curve shape reproduces; no stats columns, no figure (B1, B2) |
| 05 | **Effect of Homomorphic Aggregation** | \|R_Q\| = 100..500 | < 20 ms vs ~900 ms naive | ✅ runs; three arms, correctness asserted per run |
| 06 | **Aggregation Strategy Comparison** | \|S_Q\| = 10..10,000 | up to 670.5× | ✅ runs; correctness precondition passes; no stats columns (B1) |
| 07 | **Aggregate-Recovery Scalability (BSGS)** | `M_max` = 10³..10⁷ | `O(√M_max)` | ⚠️ written and running, but the baseline arm is a placeholder and the result comes out **inverted** (A5, A6) |

Experiment 07 is worth flagging on its own: the manuscript describes the sweep,
states the run count, and includes `\includegraphics{bsgs_scalability.png}` —
but neither the script nor the image has ever existed in this repository.

### The four reviewer-mandated experiments

Not part of the original seven, but required for acceptance. All four are
scaffolded with code that executes — 08, 09 and 10 produce CSV and SVG today —
but each has a defect that undercuts the reviewer comment it was written to
answer (§11 A3, A4, B3).

| # | Experiment | Measures | Source | Needs |
|---|---|---|---|---|
| 08 | **Communication Cost** | Actual KB for request, response 1, response 2, at representative `N` and \|R_Q\| | R1-C7, R2-C5 | — |
| 09 | **Sensor-Side Cost** | ABSE encapsulation + EC-ElGamal + AES-GCM + HMAC: time, energy, memory, ciphertext expansion | R1-C6 | a Raspberry Pi + a power meter reading |
| 10 | **Per-Primitive Microbench** | Single pairing, `ABSE.Test`, Merkle verify, bitmap AND over 100k bits, threshold decrypt | R2-C3 | — |
| 11 | **Blockchain Cost** | Gas per anchor, ledger growth, finality, multi-node sync latency, variable epoch frequency | R7-5, R4-2 | 3+ node consortium + `pip install web3` |

**Run Experiment 10 first.** It is the reconciliation table for the whole
paper — it prints the expected total for each other experiment from measured
primitive costs. If a reported total lands orders of magnitude under its
floor, the harness is measuring the wrong thing. That is exactly how the old
throughput script went wrong.

> ⚠️ **Fix §11 A3 before relying on it.** `ABSE.Test` currently fails to
> benchmark, so the reconciliation table silently omits its Exp 02 line — the
> single check that would catch a repeat of the throughput bug. Measured
> primitive costs on the dev box, for scale: one BLS12-381 pairing ≈ 1.02 ms,
> `ABSE.TokenGen` ≈ 0.72 ms, Merkle verify ≈ 0.015 ms, EC-ElGamal encrypt
> ≈ 1.86 ms, threshold decrypt ≈ 28.4 ms. Any per-query total in the
> sub-millisecond range is therefore impossible on this stack — which is
> exactly what R2-C3 said.

---

## 5. `Benchmark/_shared/` — the shared library

Not experiments. Code the experiments import.

### Core system under test

| File | Phase | Role |
|---|---|---|
| `TA.py` | 1 | Trusted Authority — ABSE `(PP, MSK)`, EC-ElGamal keypair, PRF seed `Ks`, per-sensor AES/HMAC keys |
| `abse_fast.py` | 1 | ABSE over **BLS12-381** (Rust `py_arkworks_bls12381`), ~50× faster |
| `abse_real.py` | 1 | ABSE over **BN128** (`py_ecc`), pure-Python fallback |
| `ec_elgamal.py` | 1,5 | Lifted EC-ElGamal + BSGS recovery table |
| `threshold_ec_elgamal.py` | 1,5 | `(t,n)` Shamir threshold, Chaum–Pedersen DLEQ, Lagrange combine |
| `sensor.py` | 2 | Sensor-side AES-GCM + EC-ElGamal + canonical path + HMAC |
| `blockchain_edge.py` | 2 | Edge gateway — tags, masked bitmaps, aggregation registration, Merkle root |
| `merkle_tree.py` | 2,4 | Merkle tree, single and **multi**-proof verification |
| `user_client.py` | 3 | Trapdoor generation, single-dim and conjunctive |
| `cloud_server.py` | 4 | `process_query()` — ABSE test + bitmap filtering |
| `utils.py` | — | `gen_tag`, `gen_query_bitmap` |

> **Curve discrepancy — now confirmed, not suspected.** The paper says ABSE was
> implemented with `py_ecc` over **BN128**. `TA.py` prefers `abse_fast.py`,
> which is **BLS12-381**, and Experiment 10 printed
> `ABSE backend: py_arkworks_bls12381 (BLS12-381)` on the first run. The
> verification experiment also imports `py_arkworks_bls12381` unconditionally,
> so it cannot fall back. **The published figures are BLS12-381.** Fix the text
> or pin the backend — and see §11 A8 before describing either as access
> control.

### Baselines — `_shared/baselines.py`

Single canonical definition of every scheme, extracted from the retired
monolith so experiments stop redeclaring them (R3-16). Referred to as
`Benchmark/baselines.py` in several `config.md` files — the real path has a
`_shared/` in it.

`BVCRSAAlgo` · `TrinityAlgo` (ref26) · `ABSERangeAlgo` (ref27) ·
`VCKASEAlgo` (ref16) · `LatticeIBEKSAlgo` (ref28, incl. Scheme-II conjunctive patch)

Also exports `load_datarecord()`, `gen_data()`, `timed()`, `summarize()`, and
the scheme groupings `ALL_SCHEMES`, `CONJUNCTIVE_SCHEMES`, `VERIFIABLE_SCHEMES`.

`timed(fn, runs=20)` returns `mean / median / stdev / ci95 / min / max / raw` —
so E1 is satisfied by construction rather than per-script.

Supporting primitives for Trinity: `trinity.py`, `shve.py`, `quotient_filter.py`,
`hilbert_curve.py`, `ggm_cprf.py`. ABSE-Range lives in `Attribute-based.py`
(loaded by file path — the name is not a legal module identifier).

### Harness — `harness.py`

`Experiment` collects rows and writes one CSV, **refusing any row that lacks a
run count and raw sample list** — so E1 cannot be forgotten. `save_figure()`
writes SVG and raises on any raster extension, so E12 cannot be forgotten
either. Every row also carries an environment stamp (host, platform, Python
version, AWS target, git revision) so results are self-documenting (E4).

### Blockchain

`contracts/BVCRSALedger.sol`, `ethereum_connector.py`, `deploy_contract.py`,
`contract_config.json`. Retained because R7-5 and R4-2 demand empirical gas and
ledger measurements (Exp 11).

### `ecgrq/` — learned index (ref15), optional

`ecgrq_li.py` and a de-credentialed `config.py`, salvaged from the standalone
ECGRQ folder. **ECGRQ-LI is cited in Related Work but is not one of the four
benchmarked baselines**, so nothing currently imports it. Kept only so the
learned index can be promoted to a baseline if a reviewer asks. Its MongoDB
harness, demo dashboards, and data generator were left behind.

### Data and sanity

`generate_datarecord.py` → `CSV/Datarecord.csv` (present, 100,000 rows, as
specified in §6). `test_pipeline.py` walks all five phases on five records —
**run it first**; if it fails, every benchmark number is suspect. It currently
**passes**: HMAC verified, 3 SCRAT nodes per record, Merkle proofs checked, and
the decrypted SUM/CNT match the expected plaintext exactly. The five-phase
pipeline itself is sound — the defects in §11 are in the experiments and
baselines wrapped around it.

---

## 6. Dataset

`generate_datarecord.py`, seed `42`, fully reproducible.

| Parameter | Value |
|---|---|
| Records | 100,000 |
| Machines | `A`, `B`, `C`, uniform |
| Sensor categories | 20 (`Temp` … `Acoustic`) |
| Value | integer, uniform `[0, 100]` |
| Timestamp | strictly increasing, 3 s apart from `2024-01-01 00:00:00` |
| Columns | `id, machine, sensor, value, timestamp_str, t_slot` |

Sweeps read the **first N rows**, so every smaller-N point is a strict prefix of
the larger ones — no re-sampling between sweep points.

---

## 7. Naming conventions

| Artifact | Pattern | Example |
|---|---|---|
| Result data | `CSV/exp<NN>_<name>.csv` | `CSV/exp04_verification_overhead.csv` |
| Figure | `Figures/exp<NN>_<name>.svg` | `Figures/exp04_verification_overhead.svg` |
| Cited figure | prefix `used_` | `Figures/used_exp04_verification_overhead.svg` |

Mandatory statistics columns on every result CSV:

```
runs, mean_ms, median_ms, stdev_ms, ci95_ms, min_ms, max_ms, raw_ms
```

Plus an operation-count column wherever a timing claim needs to be checkable by
hand — `hash_ops`, `pairing_ops`, `decrypt_calls`, `ec_adds` (E1, E2).

---

## 8. Cleanup status

Everything still in use has been moved out. **Three folders are now fully
deletable:**

| Folder | Why it is dead |
|---|---|
| `Benchmark/` | Library moved to `Benchmark/_shared/`; the rest is the retired monolith, its MongoDB coupling, orphaned plot scripts, and the Flask demo |
| `CSV/` | Dataset and the three CSVs worth keeping moved to `CSV/`; the rest are outputs of deleted producers plus dead Paillier key material |
| `Efficient Conjunctive Geometric Range Query…` | `ecgrq_li.py` copied to `_shared/ecgrq/`, paper PDF to `References/`; the rest is MongoDB harness and demo dashboards |

### What was salvaged, and why

| From | To | Reason |
|---|---|---|
| `benchmark_paper.py` | `_shared/baselines.py` | Sole home of the VC-KASE and Latt-IBEKS baselines — extracted before retirement |
| `verification_overhead_exp.py` | `04_.../experiment.py` | Highest-quality script in the repo: 300 runs, interleaved sampling, production pipeline |
| `agg_strategy_benchmark.py` + zoom | `06_.../experiment*.py` | Already threshold-correct with 20 runs and a correctness assertion |
| `benchmark_ablation.py` | `05_.../experiment.py` | Rewritten for threshold EC-ElGamal + the verifiable arm |
| `plot_agg_strategy.py`, `plot_verification_overhead.py` | `06_/plot.py`, `04_/plot.py` | Plot logic worth keeping; repointed to SVG |
| `ecgrq_li.py`, `config.py` | `_shared/ecgrq/` | Learned index, in case ref15 is ever promoted to a baseline. Credentials stripped |
| 3 result CSVs | `CSV/*_LEGACY.csv` | They hold the exact numbers quoted in the manuscript (0.35→3.0 ms, 1.4→13.6 ms, 670.5×). Keep until the replacement runs land, or the submitted figures lose their only backing data |

Anything deleted is still recoverable from git HEAD at its pre-reorganization
path: `git show HEAD:"Final Project Revision/project/<file>"`.

---

## 9. Running an experiment

```bash
# Sanity first — if this fails, nothing downstream is trustworthy
python Benchmark/_shared/test_pipeline.py

# Dataset (only if CSV/Datarecord.csv is absent)
python Benchmark/_shared/generate_datarecord.py

# Calibration — run this BEFORE the others
cd Benchmark/10_Primitive_Microbench && python experiment.py

# Any experiment: cd into its folder and run
cd ../04_Verification_Overhead
python experiment.py        # → ../../CSV/exp04_verification_overhead.csv
python plot.py              # → ../../Figures/exp04_verification_overhead.svg
```

Experiments 09 and 11 need extra setup:

```bash
# 09 — sensor-side, on the Pi
export BVCRSA_DEVICE="Raspberry Pi 4 Model B 4GB"
export BVCRSA_DEVICE_WATTS=3.4        # from a real inline power meter

# 11 — blockchain, 3+ nodes for the consortium claim
export BVCRSA_NODE_RPCS=http://10.0.1.10:8545,http://10.0.1.11:8545,http://10.0.1.12:8545
export BVCRSA_BLOCK_INTERVALS=1,2,5,15
```

Each experiment starts with three lines — `_bootstrap` handles the path:

```python
import _bootstrap                                     # puts _shared/ on sys.path
from baselines import ALL_SCHEMES, load_datarecord, timed
from harness import Experiment, new_figure, save_figure, style
```

Dependencies — **verified by installing into a clean venv and running the
suite**, not copied from the old README:

```bash
pip install numpy matplotlib pycryptodome py_ecc ecdsa pandas
pip install py_arkworks_bls12381    # BLS12-381 backend — pin this decision
pip install web3                    # Experiment 11 only
```

- **`ecdsa` is not optional.** `ec_elgamal.py` does `from ecdsa import NIST256p`
  at import time, so `TA.py` → everything fails without it. It was missing from
  both this file and `MD/RUN_LOCAL.md`; on a clean machine following the old
  list, *nothing in the suite ran*.
- **`pandas` is still needed** by `04_/plot.py` and `06_/plot.py`. The earlier
  claim that it was retired was wrong.

`pymongo`, `dnspython`, `phe`, and `flask` are genuinely no longer needed.

**Windows console:** every script prints `▶ ⛓️ ✅`. Under the default cp1252
stdout they die with `UnicodeEncodeError` before doing any work. Set
`PYTHONIOENCODING=utf-8` (or run under Windows Terminal with UTF-8 enabled).
Not an issue on the AWS target.

---

## 10. Status — verified by execution

Last verified **2026-08-17**. Local checks on Python 3.14.7 / Windows;
production runs on 3× AWS `r7i.2xlarge`, Ubuntu 24.04, Python 3.12.3,
BLS12-381 via `py_arkworks_bls12381`.

`test_pipeline.py` passes end to end on all four machines: five phases,
Merkle proofs verified, decrypted SUM/CNT match expected plaintext.

**Smoke pass: 10/11 experiments run clean** at reduced parameters. Exp 11
exits 2 without `BVCRSA_NODE_RPCS`, by design.

| Exp | State |
|---|---|
| 01 Trapdoor Gen | ✅ all 5 schemes, Trinity included |
| 02 Query Processing | ✅ three sweeps |
| 03 Query Throughput | ✅ reduced sweep; throughput **derived** from latency |
| 04 Verification Overhead | ✅ harness-wired, full dispersion, SVG |
| 05 Homomorphic Aggregation | ✅ three arms, recomputation now **compared** |
| 06 Aggregation Strategy | ✅ harness-wired, one row per arm |
| 07 Aggregate-Recovery BSGS | ✅ BSGS now correctly **faster** than linear |
| 08 Communication Cost | ✅ wire sizes **measured**, not assumed |
| 09 Sensor-Side Cost | ✅ runs; needs the Pi for R1-C6 |
| 10 Primitive Microbench | ✅ incl. `ABSE.Test` |
| 11 Blockchain Cost | ⏸ needs the 3-node consortium |

### Measured facts the manuscript must absorb

**1. Table IV overstates BVCRSA's query cost by 116×.** Instrumented at
N=1,000: `N_u × m_c` = 12,000 predicted `ABSE.Test` calls; **103 actual**.
Context filtering (3,000 nodes → 51 docs) and the Eq. 37 bitmap filter both
prune before any pairing. Cross-check: `103 × 2.888 ms = 297 ms` vs measured
**303 ms** — 2% error. The implementation never performed exhaustive matching.
Correct Table IV **downward** to `O(|D_ctx|·m_c)` with bitmap pruning.

**2. The old query/throughput numbers were not measurements.**
`BVCRSAAlgo.query()` was a dict lookup — no `ABSE.Test`, no bitmap, no
pairings — and built nodes as `[l, l+10]` while the client covers `[l, l+9]`,
so PRF tags could never agree. Measured on the real path: **303 ms at
N=1,000** vs the paper's 0.02 ms.

**3. The "< 20 ms" aggregation claim is arithmetically impossible.** One
threshold decryption = **35.58 ms**; BVCRSA performs two ⇒ a **71.2 ms floor**.
The old figure used single-key EC-ElGamal, exactly as R2-C7 suspected. The
comparison survives (Naive ≈ 17.8 s at r=500) — the headline does not.

**4. R1-C3 is cheap to satisfy.** Full verification (entry processing,
position checks, multi-proof, independent `CT_sum`/`CT_count` recomputation)
at r=500: **25.20 ms**, of which recomputation is 17.84 ms and positions
0.025 ms. Merkle-only is 7.33 ms. Report both components.

**5. The dataset is reproducible.** `generate_datarecord.py` at `SEED = 42`
regenerates `CSV/Datarecord.csv` **byte for byte**
(`md5 17a67345abe41dde84cf70449d6a2649`). Publish the hash.

---

## 11. Defect register

### Fixed and verified

| # | Defect | Fix |
|---|---|---|
| A1 | `ecdsa` missing from install lists | added everywhere |
| A2 | **Trinity crashed on every experiment** — `time_min = now−30d` vs a 2024 dataset gave negative grid coords → `struct.error` | clamp in `normalize_coordinate()` + derive the window from the data |
| A2b | Trinity matched **all** records — every record given identical `lat/lon`, so its spatial predicate was vacuous | sensor value mapped onto Trinity's latitude axis. **Disclose the mapping** |
| A3 | `ABSE.Test` never benchmarked — `encrypt(tag)` missing `policy` | `encrypt(tag, "Analyst")`; now 2.888 ms |
| A5 | BSGS table read as `_bsgs_table`/`table`; real name is `_baby_table` → `table_bytes` 0 | fixed; entries now √M_max |
| A6 | Exp 07's "linear search" did **no EC work** (`acc = v`), so BSGS looked *slower* and the figure contradicted the paper | real point additions; `LINEAR_CAP` 10⁵→2,000. BSGS now 2.08 ms vs linear 3.90 ms at M=10³ |
| A7 | Exp 03 needed ~12 days | throughput derived from latency; sweep cut; ABSE-Range excluded |
| A9 | `process_conjunctive_query` didn't forward `abse_instance` → a full `ABSE()`+`setup()` per dimension | threaded through |
| A10 | **Latt-IBEKS discarded its trapdoor** — `{"b": b_vec, …, "b": b}`, duplicate key | bounds renamed `lo`/`hi` |
| A11 | **Latt-IBEKS `index_build` did no lattice work** — built `A`,`B` and never used them (0.00 s) | real LWE ciphertext: `c₀=Aᵀs+e`, `c₁=Bᵀs+e′+w` |
| A12 | **All four baselines' `query()` were plaintext scans** | each now performs its real per-document operation |
| A13 | **Phase 5 verification never worked** — proof against `root_idx`, checked against `H(root_idx‖…)` | two-level check restored per Eq. `p2-epoch-commitment` |
| A14 | `_query_fast` authorized using only the **first** cover token → false negatives (0 vs 1 match at N=300) | all cover tokens tried; `PAPER_FAITHFUL_SEARCH` forces the legacy path |
| B1 | **Exp 04 and Exp 06 bypassed the harness** — medians/means only, in the two experiments the manuscript quotes | both harness-wired; full dispersion + `env_*` |
| B2 | Exp 04 produced no figure; plots bypassed `save_figure()` | `plot()` added, routed through the guarded writer |
| B3 | Exp 08 was a formula presented as a measurement | wire sizes serialized and measured (token 338 B, agg_entry 811 B, block 191 B) |
| C1 | `environment_stamp()` pasted the whole `serverpath` file into every row | parses `AWS_HOST=` |
| C2 | `UnicodeEncodeError` killed scripts whenever stdout was a pipe | `PYTHONIOENCODING=utf-8` + `C.UTF-8` in `run_all.sh` / `run_worker.sh` |
| C3 | `AWS/serverpath` was placeholders | live instances configured |
| E3′ | Exp 05's verifiable arm computed `recomputed` and never compared it | asserted against the returned aggregate |
| D1 | **Trinity-II `gen_trap` was O(states × prefix_tokens)** — rekeyed the *entire* query token set for *every* indexed state up front; the docstring itself called for O(log c), the code did neither that nor anything close (8.6s at N=300) | state-key derivation deferred to Query, computed only for entries already surviving the Hilbert range filter |
| D2 | **Trinity-II's Step 2 (real state-token match) was dead code** — Step 3 unconditionally accepted every in-range entry whether or not Step 2 found a match, so the real crypto cost was measured but never affected the result set | Step 2 made authoritative when it can be attempted; Step 3 now only fires when Step 2 genuinely can't run |
| D3 | **Trinity-II query matched nothing (0 results)** — `query()`'s state-key derivation didn't reproduce `gen_index`'s `update_state()`, which folds in a fresh per-entry salt on top of the derived key | salt looked up from `salt_store` and folded in identically at query time; verified exact match against ground truth |
| D4 | `hilbert_curve.py`'s `range_to_intervals` brute-force enumerates every grid cell in the query box — a box narrow on one axis but full-width on another (e.g. unconstrained time) enumerated ~640k cells | capped at 2M cells with a correctness-preserving (not selectivity-preserving) full-range fallback for pathological boxes |
| D5 | **ABSE-Range had no range mechanism at all** — `rec["value"]` was passed as the *file payload* positional arg, not encrypted as a searchable field; trap_gen's `a,b` never reached the crypto; `search()` computed keyword pairings but never checked them | canonical dyadic range-cover (real BLS12-381 pairings, O(log domain) tokens); keyword and range matching both use a proven PEKS-style equality test; verified exact match against ground truth over multiple ranges |
| D6 | **VC-KASE's "pairing" was `pow(g1*g2, 3, p)`** — a single modular exponentiation, not a bilinear pairing — and Exp 04 separately reimplemented a *second*, disconnected fake: 2 real pairings on fixed dummy points unrelated to any document or signature | one real BLS12-381 implementation (`vckase.py`) with real Extract/Sign/Verify, imported by both `baselines.py` and Exp 04 |
| D7 | **VC-KASE `n_docs=20000` hard cap** — `_get_g(n_docs+1-j)` went negative for any record past the 20,000th, throwing `base is not invertible for the given modulus` and silently dropping VC-KASE out of Exp 02's N-sweep above 20k (found this session, live on AWS) | `Extract(doc_ids)` now takes the real target set explicitly; verified correct up to N=25,000 |
| D8 | **Latt-IBEKS had no identity layer, no trapdoor sampling, no relationship to any of the paper's three schemes** — two independent random public matrices, generic two-ciphertext LWE encryption unrelated to Scheme-I/II/III | real MP12 gadget-trapdoor (`A@samplepre(u)==u mod q`, verified exact every trial) + GPV08 IBE-to-PEKS keyword/range matching (`latt_ibeks.py`) |
| D9 | **Single-bit dual-Regev LWE decode has an inherent ~50% error rate at REPS=1** — not a bug, a property of 1-bit LSB embedding at this noise level; found by testing (112/400 failures) before being understood | REPS=8 independent repetitions, match requires all to decode within threshold; verified 200/200 true positives, 0/200 false positives |

### Open — protocol decisions, not code bugs

| # | Issue | Why it needs you |
|---|---|---|
| **A8** | **ABSE tokens are forgeable.** `test()` never touches `PP`/`MSK`; the policy check is a plaintext `in` test. Every `ABSE.Test` timing measures a pairing that authorizes nobody. | Concrete form of **R1-C2 / R3-4**. Needs the real construction (`ImplementFIX/01` §F4) |
| **P1** | `user_client.py:21` hands users `K_sel`, which the paper forbids. Code's `gen_tag` (Eq. 16) is keyed; the paper's Eq. `p3-node-keyword` is public. | **Which equation is authoritative?** Tag-level form of R3-1 |
| **P2** | **Merkle tree is per-record, not per-epoch** — `build_scrat_from_payload` builds a 3-leaf tree per record. Eq. `p2-epoch-commitment` specifies one root per epoch, so the multi-proof branch is unreachable and the production path is `O(r log N)`, not Table IV's `O(r log(N/r))`. | Restructuring indexing, not a patch |
| **E1′** | The schemes answer **different queries** — BVCRSA's trapdoor binds one `(machine, t_slot)`; the others scan all N for (sensor, range). At N=300: BVCRSA 1 match, others 3. | Different selectivity ⇒ latency isn't like-for-like. **R3-16.** Disclose or align |
| **E2′** | Exp 02 fits `c·N·log₂N` to a path that measures `O(N)`. | State it, or drop the extrapolation |

### Reporting caveats to disclose

- **Baseline match decisions used ground truth** for VC-KASE, Latt-IBEKS,
  Trinity and ABSE-Range — **now fixed for all four** (2026-08-17, see
  `ImplementFIX/09`/`10`): every baseline derives its match set from real
  cryptography (Trinity-II state-aware token matching + verify_tag;
  VC-KASE real Extract/Test/Sign/Verify over BLS12-381; ABSE-Range real
  keyword + canonical-range-cover pairing match; Latt-IBEKS real MP12
  gadget-trapdoor sampling + real LWE keyword/range matching), each
  verified against ground truth over repeated test cases with zero
  mismatches. R3-16 — text in `ImplementFIX/03` §F11 needs rewriting:
  the whole premise of that disclosure paragraph (baselines are
  favourably ground-truth) no longer holds and the paragraph needs to
  say what's real now instead.
- **Latt-IBEKS's trapdoor sampling and identity binding are documented
  substitutions, not the paper's exact cited algorithms** — a real
  Micciancio-Peikert gadget trapdoor stands in for the paper's cited
  GPV-style TrapGen/SamplePre/SampleLeft/NewBasisDel, and a GPV08-style
  IBE-to-PEKS transform stands in for the paper's `A_id = A(R_id)^-1`
  HIBE-style identity binding. Both are real, peer-reviewed, correct
  lattice constructions — chosen over attempting the paper's exact,
  more complex cited algorithms from scratch under time pressure, where
  a subtle bug would be harder to catch than in the pairing-based
  baselines. See `latt_ibeks.py`'s module docstring for the full
  justification and the verification results.
- **Latt-IBEKS parameters (`n=17, q=4093`) match ref28's own Section VI-B
  experimental setup verbatim** — not a toy shortcut. (Corrected
  2026-08-17; the prior note claiming a ~1000× understatement against an
  assumed "deployment n≈512–1024" was unsupported by the source paper.)
- **ABSE-Range (ABSE-ERM, ref27) now applies a real numeric range
  predicate** (2026-08-17) via a canonical dyadic range-cover, not the
  paper's exact 0/1-coding construction (that needs a set-*absence* test
  that doesn't map cleanly onto a pairing match; see `Attribute-based.py`'s
  module docstring). Still missing: the paper's LSSS `(t,n)`-threshold
  access matrix — attribute-policy matching is still a flat list, not a
  threshold structure (`ImplementFIX/10` Phase 3.1, not yet built).
- **Trinity now benchmarks Trinity-II** (forward-secure + verified), not
  Trinity-I — swapped 2026-08-17. Its query cost is real and scales with
  both N and query-box Hilbert fragmentation; expect large-N sweep points
  to take minutes, not milliseconds — this needs disclosing in the
  manuscript's methodology, not silently absorbed into a runtime budget.
- **VC-KASE is excluded from Exp 02's range-selectivity sweeps (2a
  vs_range, 2b vs_N) and from Exp 03's throughput sweep**, and from
  Exp 03. The source paper (ref16) has no numeric range predicate at
  all — kept only in Exp 01 (trapdoor-gen timing) and Exp 02's 2c
  (conjunctive keyword-identity matching, which is what it actually
  supports).
- **Exp 06 extrapolates** the conventional arm above `|S_Q| = 150`.
- **Exp 03 excludes ABSE-Range** (~64 s/query at N=10,000).

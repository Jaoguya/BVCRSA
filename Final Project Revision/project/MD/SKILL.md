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

## 10. Status — after the first actual execution

The suite has now been run. Python 3.11 + the §9 dependency list, in a clean
venv, on the Windows dev box (not AWS — these are correctness observations,
not publishable timings). `test_pipeline.py` **passes end to end**: all five
phases, Merkle proofs verified, decrypted SUM/CNT match the expected plaintext.

| Exp | Runs? | State |
|---|---|---|
| 01 Trapdoor Gen | ✅ | Produces CSV + SVG. **Trinity silently absent** (A2). |
| 02 Query Processing | ⚠️ | All three sweeps verified at reduced scale. Trinity absent (A2). Full config is a multi-hour run; no warning anywhere. |
| 03 Query Throughput | ❌ | **Cannot terminate** — ≈228 h for BVCRSA alone at the configured N and Q (A7). |
| 04 Verification Overhead | ⚠️ | Runs, reproduces the legacy curve shape. **No stats columns, no figure, no provenance** (B1, B2). |
| 05 Homomorphic Aggregation | ✅ | Runs clean; three arms, correctness asserted every run. **Contradicts the paper's "< 20 ms" claim** — see below. |
| 06 Aggregation Strategy | ✅ | Runs clean; correctness precondition passes; **722× at \|S_Q\|=10,000, so the 670.5× claim reproduces**. **No stats columns** (B1). |
| 07 Aggregate-Recovery BSGS | ⚠️ | Runs, but the "linear search" arm does no EC work, so the headline claim comes out **inverted** (A5, A6). |
| 08 Communication Cost | ⚠️ | Runs, but is a **formula, not a measurement** (B4). |
| 09 Sensor-Side Cost | ⚠️ | Runs; **the ABSE step errors out** (A4), so the R1-C6 answer is incomplete. Still needs a Pi + power meter. |
| 10 Primitive Microbench | ⚠️ | Runs; **`ABSE.Test` — the primitive R2-C3 asked for by name — is skipped** (A3). |
| 11 Blockchain Cost | ⏸ | Exits 2 without `BVCRSA_NODE_RPCS`, as designed. Needs the consortium. |

Every module in `_shared/` imports cleanly and the whole tree byte-compiles;
there are no syntax errors and no missing modules. The defects below are
behavioural.

### Two results the manuscript needs to absorb

**The reconciliation idea works — and it convicts Experiment 05's claim.**
Experiment 10 measured one threshold decryption at **28.4 ms**, and therefore
printed `Exp 05/06 BVCRSA arm, 2 threshold decrypts: 56.89 ms expected floor`.
Experiment 05 then measured BVCRSA-Compact at **57.66 ms** at |R_Q| = 100 —
within 1.4 % of the predicted floor. That is the reconciliation table doing
exactly its job. It also means the paper's *"BVCRSA stays under 20 ms across
all workloads"* **cannot be true under threshold EC-ElGamal**: two threshold
decryptions alone cost ~57 ms. This is the concrete form of R2-C7. Measured
range was 57.7 → 92.2 ms (Compact) against 2 742 → 14 223 ms (Naive), versus
the claimed < 20 ms vs ~180 → 900 ms. **Both numbers in that sentence have to
be restated.**

**R1-C3 turns out to be cheap to satisfy.** BVCRSA-Verifiable — all r
aggregation entries plus the multi-proof, independently recomputed — costs
**59.6 ms vs 57.7 ms** for the compact arm at |R_Q| = 100, and 90.2 vs 77.9 ms
at 500. Returning what the formal protocol actually requires adds single-digit
percent, not an order of magnitude. Report the verifiable arm; it is a
strength, not a concession.

*(Timings above are dev-box, some under CPU contention — treat the ratios and
the floors as the finding, not the absolute values. Re-run on AWS for print.)*

Run `test_pipeline.py` first, then Experiment 10, then the rest.

---

## 11. Verified defects

Everything here was reproduced by execution, not by reading. Grouped by what
it costs you.

### A. Correctness — these produce wrong or absent data

| # | Defect | Where | Fix |
|---|---|---|---|
| **A1** | **`ecdsa` missing from every install list.** Import-time failure of `ec_elgamal` → `TA` → the entire suite. | `_shared/ec_elgamal.py:29`; `MD/RUN_LOCAL.md:75`; §9 above | Fixed in §9; fix `RUN_LOCAL.md` too |
| **A2** | **Trinity (ref26) raises on every experiment and is silently dropped.** `TrinityI.setup()` sets `time_min = now − 30 d`; the dataset starts **2024-01-01**, so `normalize_coordinate()` returns a large *negative* grid coordinate (it never clamps), and `struct.pack('<I', …)` raises `argument out of range`. Callers catch it with a broad `except` and print one line, so the headline baseline is missing from Exp 01/02/03 data and figures. | `_shared/trinity.py:125`, `_shared/hilbert_curve.py:239`, `_shared/shve.py:124`, `_shared/baselines.py:560` | Clamp in `normalize_coordinate()` **and** set Trinity's domain bounds from the dataset, not from `time.time()` |
| **A3** | **`ABSE.Test` is never benchmarked.** `abse.encrypt(tag)` omits the required `policy` argument → `TypeError`, caught, step skipped. R2-C3 named this primitive explicitly. The reconciliation table then silently loses its "Exp 02 query floor" line — the one check that would have caught the throughput bug. | `10_Primitive_Microbench/experiment.py:200` | `abse.encrypt(tag, "Analyst")` |
| **A4** | **Same call, same bug, in the sensor experiment** — `ABSE_encapsulate_record_key` errors out. The script still prints "SENSOR-SIDE BREAKDOWN (answers R1-C6)" claiming public-key work is 98.6 % of sensor cost, **omitting the ABSE encapsulation R1-C6 asked about**. Ciphertext-expansion figure is understated for the same reason. | `09_Sensor_Side_Cost/experiment.py:122` | Pass the policy; make a failed public-key step abort rather than print a partial answer |
| **A5** | **BSGS table is never measured.** Reads `_bsgs_table` / `table`; the real attribute is `_baby_table`. `table_bytes` is `0` in every row and `table_entries` is a fallback estimate. | `07_.../experiment.py:65` vs `_shared/ec_elgamal.py:73` | `getattr(priv, "_baby_table")` |
| **A6** | **Exp 07's "linear search" baseline performs no elliptic-curve work** — the loop body is `acc = v`. Measured result: BSGS is *slower* than "linear" at every `M_max ≤ 10⁶` (1.83 ms vs 0.009 ms at 10³), i.e. the figure currently **contradicts** the paper. Above `LINEAR_CAP` the linear value is *defined* as measured × (M_max/cap), so "fitted exponent = 1.001" is arithmetic, not evidence. Fitted BSGS exponent came out **0.378, not 0.5**. | `07_.../experiment.py:120-132` | Make the baseline walk real points (`acc = acc + G`) or drop the arm and compare BSGS against its own √ bound |
| **A7** | **Exp 03 cannot finish.** Measured at N=200: one full query cycle = 53 ms, scaling linearly in N → ≈2.5 s at the configured N=10 000. The script runs Σ(Q)=16 600 cycles × 20 runs = **332 000 cycles per scheme ⇒ ≈228 h for BVCRSA alone**; ABSE-Range is ~100× worse again. | `03_.../experiment.py:37-41` | Cut `QUERY_COUNTS`/`RUNS`, or measure per-query latency once and *derive* throughput with the reconciliation check it already has |
| **A8** | **ABSE trapdoors are forgeable — `Test` is bound to no key.** Verified: a token built as `(H(tag)·z, G₂·z)` for a random `z`, with an attacker-chosen plaintext `attrs` list, **passes `abse.test()`** against a legitimate ciphertext; so does a token from a second ABSE instance with a different MSK. `test()` never touches `self.PP`/`self.MSK`, and the policy check is `all(attr in token["attrs"] …)` — a plaintext Python membership test. Both backends. This is reviewer objection **P2** made concrete: every ABSE.Test timing measures a pairing check that authorizes nobody. | `_shared/abse_fast.py:159-179`, `_shared/abse_real.py:206-238` | Protocol-level fix (bind the token to `MSK`/`SK_A` and make the attribute check cryptographic). Until then, do not describe Test as access control |
| **A9** | **Conjunctive queries build a fresh ABSE per dimension.** `process_conjunctive_query()` calls `self.process_query(dim_td)` without forwarding `abse_instance`, so each dimension pays a full `ABSE()` + `setup()`. It only *works* because of A8. Inflates every Exp 02 sweep-2c timing. | `_shared/cloud_server.py:161` | `self.process_query(dim_td, abse_instance)` — thread the instance through |
| **A10** | **Latt-IBEKS discards its own trapdoor.** `trap_gen()` returns a dict literal with **`"b"` twice** — `{"b": b_vec, …, "b": b}` — so the polynomial vector is overwritten by the integer range bound. `query()` then computes `np.dot(65, y)`, an elementwise multiply, not the Scheme-I inner product its comment claims. Explains the flat ~0.09 ms d-sweep. (`conjunctive_trap()` is unaffected.) | `_shared/baselines.py:518` | Rename the range bounds, e.g. `"lo"`/`"hi"` |

### B. Reporting contract — the reviewer-mandated columns are missing

| # | Defect | Where |
|---|---|---|
| **B1** | **Exp 04 and Exp 06 bypass the harness entirely.** Neither imports `_bootstrap`/`harness`; each writes its own CSV by hand. Exp 04 emits `returned_results, bvcrsa_verify_ms, trinity_verify_ms, vckase_verify_ms` — **medians only**. Exp 06 emits means only. Neither carries `runs / stdev / ci95 / min / max / raw_ms`, nor the `env_*` provenance stamp. §3.2 claims `record()` makes E1 unforgettable; **E1 is forgotten in exactly the two experiments whose numbers the manuscript quotes** (0.35→3.0 ms and 670.5×). Confirmed by running both. | `04_/experiment.py:294`, `06_/experiment.py:150`, `06_/experiment_zoom.py:95` |
| **B2** | **Exp 04 produces no figure at all**, and both salvaged `plot.py` files call `fig.savefig()` directly — bypassing `save_figure()`, so the SVG-only guard *and* the "mean of N runs, 95 % CI" stamp (E14 / R2-C8) are skipped. The plots draw no error bars, because there are no dispersion columns to draw. | `04_/plot.py:57`, `06_/plot.py:110` |
| **B3** | **Exp 08 is an analytical model presented as a measurement.** Its docstring says it will "serialize the real protocol messages and measure `len(bytes)` … not from a formula — that is the whole point of the objection". No message is ever serialized; every number comes from the constants at the top. `_serialize_cost()` times `os.urandom()` calls, so the mandatory `raw_ms` column holds RNG timings unrelated to communication cost. R2-C5 asked for measured KB. | `08_/experiment.py:90-151` |

### C. Environment and provenance

| # | Defect | Where |
|---|---|---|
| **C1** | **The whole `AWS/serverpath` file is pasted into every CSV row.** `environment_stamp()` does `f.read().strip()` instead of parsing `AWS_HOST=`, so `env_aws_target` contains 20 lines of comments, the instance type, and the `.pem` path — and the run banner prints them too. | `_shared/harness.py:66-70` |
| **C2** | **UnicodeEncodeError on a stock Windows console** kills every script before it does any work (see §9). `MD/RUN_LOCAL.md` is a Windows guide and does not mention it. | all experiments |
| **C3** | **`AWS/serverpath` is still placeholders** — `ec2-<PUBLIC-IP>.<region>…` and a Windows key path `C:/Users/Jzguyr/.ssh/…`. "AWS-only execution" is not actually configured. | `AWS/serverpath:8-10` |

### D. Documentation drift

- `config.md` for **01/02** cites `fig_combined_3panel.svg`; the code writes `exp01_trapdoor_gen.svg` and `exp02_query_vs_*.svg`. **05**'s cites `exp05_ablation_aggregation.svg`; the code writes `exp05_homomorphic_aggregation.svg`.
- `06_/plot.py`'s missing-CSV message names the retired `agg_strategy_benchmark.py` / `agg_strategy_zoom_benchmark.py`; `experiment_zoom.py`'s docstring does too. `04_/plot.py`'s docstring says it reads `verification_overhead_exp_results.csv` and writes a `.png`.
- **`Figures/` still holds four raster PNGs** — the figures actually cited in the manuscript — contradicting the vector-only rule (E12 / R1-C8). One is misnamed `usedfig_query_vs_d_conjunctive.png`, breaking the `used_` convention in §7.
- **01**'s `config.md` claims "gc disabled during timing"; `baselines.timed()` never touches gc. Only Exp 04's own `timed_interleaved_ms()` does.
- `MD/comprehensive_review.md` is pre-rebuild — Paillier, Flask `main.py`, `/home/student/Downloads/project` paths — and contradicts the current design throughout. Retire or rewrite it.

### E. Methodology worth arguing about before publication

- **E1′ — the schemes are not answering the same query.** `BVCRSAAlgo.trap_gen()` looks up `self._ctx[keyword]`, the *first* `(machine, t_slot)` seen, so BVCRSA searches one machine in one hour, while VC-KASE / Latt-IBEKS / ABSE-Range scan all N records for (sensor, range). Observed at N=200/400: BVCRSA `matched=1`, the others `matched=2–3` on identical data. Different selectivity means the latency comparison is not like-for-like — precisely R3-16's concern. (`_shared/baselines.py:301-307`)
- **E2′ — Exp 02 fits `c·N·log₂N` to a path that measures O(N).** At N=10⁶ it projects ≈588 s *per query*; state that plainly or drop the extrapolation.
- **E3′ — Exp 05's verifiable arm computes `recomputed` and never compares it to `agg`.** The independent recomputation is timed but not checked. It also plots BVCRSA-Verifiable with the `Trinity` style key.
- **E4′** — Exp 05 / 09 reuse a fixed GCM nonce inside the benchmark loops (timing is unaffected; still a smell in a crypto paper's artifact). Exp 09 also calls `aes_gcm()` an extra, untimed time just to compute `output_bytes`.

### Suggested order of attack

1. **A1, C2** — otherwise nobody can reproduce anything.
2. **A3, A4, A5, A10** — one-line fixes that restore missing measurements.
3. **A2** — brings the primary baseline back into three experiments.
4. **B1, B2** — the two manuscript-quoted experiments currently violate the statistics contract the rebuild exists to enforce.
5. **A7, A6, B3** — redesign the three experiments that cannot produce a publishable number as written.
6. **A8** — protocol-level, and the reviewers already suspect it.

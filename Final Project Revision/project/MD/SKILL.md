---
name: bvcrsa-experiments
description: Working reference for the BVCRSA paper's experiment suite — where every file category lives, the AWS-only / CSV-only execution policy, the reviewer-mandated changes driving the rebuild, and the seven per-experiment folders under Benchmark with their configs. Use when running, rewriting, or citing any BVCRSA experiment, or when deciding where a new file belongs.
---

# BVCRSA Experiment Suite

Companion to **"BVCRSA: Blockchain-Based Verifiable Conjunctive Range Search and
Aggregation over Encrypted IIoT Data"** (IEEE IoT Journal submission).
Manuscript source: [../Overleaf/BVCRSA](../Overleaf/BVCRSA).

The suite is mid-rebuild. The paper was **rejected in its present form** by
Reviewers 1 and 3 (Reviewers 4 and 6 recommended acceptance), and essentially
every experiment has to be re-run. This document is the plan of record.

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
Atlas URI with live credentials — that connection string is now dead code, but
**the credentials in it still need rotating**, since they are in git history.

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
| E1 | **Raw data, operation counts, std-dev / CI on every figure.** Averages alone are rejected. | R1-C4, R2-C2, R3-17, R7-4 | `timed()` in `_shared/baselines.py` returns the full sample; `harness.Experiment.record()` refuses rows without it |
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
| E13 | **Baselines are underdescribed** for replication and uniform security settings. | R3-16 | `Benchmark/baselines.py` is now the single canonical definition |
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

| # | Experiment | Independent variable | Paper claim | Code status |
|---|---|---|---|---|
| 01 | **Trapdoor Generation Time** | `d` = 1..5 | 0.9 → 2.2 ms | ✏️ to write |
| 02 | **Query Processing Time** | range %, `N`, `d` | 0.04 → 0.20 ms; 0.02 → 0.45 ms | ✏️ to write |
| 03 | **Query Throughput** | `Q` = 100..10,000 | highest of all schemes | ⚠️ rewrite — old harness measured dict lookups |
| 04 | **Verification Overhead** | \|R_Q\| = 50..500 | 0.35 → 3.0 ms | ✅ salvaged, needs SVG + stats columns |
| 05 | **Effect of Homomorphic Aggregation** | \|R_Q\| = 100..500 | < 20 ms vs ~900 ms naive | ⚠️ rewrite — single-key, needs threshold + verifiable arm |
| 06 | **Aggregation Strategy Comparison** | \|S_Q\| = 10..10,000 | up to 670.5× | ✅ salvaged, best script in repo |
| 07 | **Aggregate-Recovery Scalability (BSGS)** | `M_max` = 10³..10⁷ | `O(√M_max)` | ❌ **never existed** — no code, no figure |

Experiment 07 is worth flagging on its own: the manuscript describes the sweep,
states the run count, and includes `\includegraphics{bsgs_scalability.png}` —
but neither the script nor the image has ever existed in this repository.

### The four reviewer-mandated experiments

Not part of the original seven, but required for acceptance. All four are
scaffolded with working code.

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

> **Curve discrepancy.** The paper says ABSE was implemented with `py_ecc` over
> **BN128**. `TA.py` prefers `abse_fast.py`, which is **BLS12-381**. If
> `py_arkworks_bls12381` was installed when the numbers were taken — and the
> verification experiment imports it unconditionally, so it was — the published
> figures are BLS12-381. Fix the text or pin the backend.

### Baselines — `baselines.py`

Single canonical definition of every scheme, extracted from the retired
monolith so experiments stop redeclaring them (R3-16).

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

`generate_datarecord.py` → `CSV/Datarecord.csv`. `test_pipeline.py` walks
all five phases on five records — **run it first**; if it fails, every
benchmark number is suspect.

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

Dependencies:

```bash
pip install numpy matplotlib pycryptodome py_ecc
pip install py_arkworks_bls12381    # BLS12-381 backend — pin this decision
pip install web3                    # Experiment 11 only
```

`pymongo`, `dnspython`, `phe`, `pandas`, and `flask` are no longer needed.

---

## 10. Status

| | |
|---|---|
| ✅ Written and ready to run | 01, 02, 03, 05, 07, 08, 10 |
| ✅ Salvaged, repointed to `CSV/` + SVG | 04, 06 |
| ⚙️ Needs hardware before it can run | 09 (Raspberry Pi + power meter), 11 (3+ node consortium) |
| ❌ Not started | none |

**Not yet executed.** No Python interpreter was available in the authoring
environment, so none of these scripts have been run even once. Expect
import-path and API-signature fixes on the first pass — particularly in
Experiment 10, which probes for `abse.encrypt` / `abse.test` / `token_gen`
method names that may differ from what `abse_fast.py` actually exposes, and
Experiment 07, which reads the BSGS table through attribute names
(`_bsgs_table`, `table`) that need confirming against `ec_elgamal.py`.

Run `test_pipeline.py` first, then Experiment 10, then the rest.

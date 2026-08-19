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
| E2 | **Sub-ms latencies are not believed.** Provide per-primitive microbenchmarks (one `ABSE.Test`, one pairing, one Merkle verify) so totals can be checked by hand. | R2-C3, R1-C4 | Exp 10 — emits **two standalone tables**, see §5 |
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

Since **2026-08-17** it answers R2-C3 with two standalone tables, written
as CSV *and* printed as paste-ready Markdown:

| Output | Contents |
|---|---|
| `CSV/exp10_primitive_table.csv` | **Table A** — cost of ONE call to each primitive: pairing, `ABSE.Test`, `ABSE.TokenGen`, Merkle verify, SHA-256, HMAC, bitmap AND/popcount, EC-ElGamal encrypt/add, threshold decrypt. Mean, 95% CI, run count, backend |
| `CSV/exp10_reconciliation.csv` | **Table B** — every reported total decomposed into `calls × unit cost`, beside the value actually measured in that experiment's CSV, with the ratio and a verdict |

Table B is the one that answers the objection: a reader multiplies an
operation count by Table A's unit cost and must land on the published
total. It auto-loads the measured side from `exp01/02/04/05/06`'s CSVs,
so any row that has not been re-run yet prints `NOT YET MEASURED` rather
than a fabricated number. Verdicts: `BELOW FLOOR — harness suspect`
(ratio < 0.5, the R1-C4 / R3-14 failure mode that produced the old
10⁶ q/s figure), `far above — unmodelled cost` (> 3.0), else `consistent`.

It also prints the query-total check — `N × pairings/doc × ABSE.Test` —
using the per-scheme pairing counts measured in §11 F1 (BVCRSA 0.16,
VC-KASE 1.00, ABSE-Range 5.26 per document).

> Measured primitive costs on the dev box, for scale: one BLS12-381
> pairing ≈ 1.0 ms, `ABSE.Test` ≈ 2.888 ms, `ABSE.TokenGen` ≈ 0.72 ms,
> Merkle verify ≈ 0.015 ms, EC-ElGamal encrypt ≈ 1.86 ms, threshold
> decrypt ≈ 35.58 ms. **Any per-query total in the sub-millisecond range
> is therefore impossible on this stack** — which is exactly what R2-C3
> said.

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
| Derived table | `CSV/exp<NN>_<name>.csv` | `CSV/exp10_primitive_table.csv`, `CSV/exp10_reconciliation.csv` (R2-C3, §5) |
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

> ## ✅ CROSS-SCHEME RESULTS ARE REAL — re-run completed 2026-08-18
>
> The staleness this section used to warn about is resolved. Experiments
> 01–04 were re-run on 3× AWS `r7i.2xlarge` **after** `baselines.py`,
> `vckase.py`, `latt_ibeks.py`, `trinity.py` and `Attribute-based.py`
> were rewritten with real cryptography (2026-08-17). Every CSV under
> `CSV/exp0{1,2,3,4}_*.csv` and every figure under
> `Figures/exp0{1,2,3,4}_*.svg` is confirmed real: `env_host` checked
> against the actual worker hostnames, not a local smoke-test artifact.
>
> **Total real runtime: ~20.5h for Exp02 alone** (W1, dominated by
> Trinity at N=100,000 — see F3), ~12.6h for Exp03 (W2, same cause),
> both far past the original ~11–13h estimate. Exp01 and Exp04 were
> fast (minutes). All three AWS workers used for this run are now
> stopped; their data has been pulled to local `CSV/`/`Figures/`.
>
> **One post-collection fix applied**: `03_Query_Throughput/experiment.py`
> was never re-synced to the worker before this run, so it executed an
> older `SKIP_SCHEMES` that excluded ABSE-Range but not VC-KASE (current
> local code excludes both — VC-KASE has no range predicate, see the
> `SKIP_RANGE_SCHEMES` reasoning already documented for Exp02). VC-KASE's
> 4 rows were stripped from `CSV/exp03_query_throughput.csv` post-hoc and
> `Figures/exp03_query_throughput.svg` regenerated; Trinity/BVCRSA/
> Latt-IBEKS rows are untouched and did not need re-running.
>
> **Resolved 2026-08-19**: the ABSE-Range `vs_N` gap-fill (N=20,000/
> 50,000/100,000, same `r7i.2xlarge` worker, `ip-172-31-15-107`)
> finished (`ABSE_GAPFILL_COMPLETE` in `logs/abse_gapfill.log`) and its
> 3 rows are now appended to `CSV/exp02_query_processing.csv`.
> **Caveat**: the ad-hoc `abse_gapfill.py` script only logged mean/SD/
> CI95/matched-count to stdout, not the full stats dict — `median_ms`,
> `min_ms`, `max_ms`, and `raw_ms` are blank for these 3 rows only,
> noted in each row's `note` column. `Figures/exp02_query_vs_N.svg`,
> `exp_combined_3panel.svg`, and their PDF conversions in
> `Overleaf/all_figures/` were regenerated to include these points.
> The underlying `ABSE_RANGE_LIMIT` runtime cap in
> `Attribute-based.py`/`baselines.py` was not changed — a fresh
> `python experiment.py` run would still stop short of N=20k+ unless
> that cap is also raised; the CSV was patched directly instead.
>
> `exp09_sensor_side_cost.csv` still has `env_host=DESKTOP-9RLOO3O` — a
> Windows box, not the Raspberry Pi R1-C6 requires. Untouched this pass.
>
> **Fixed 2026-08-19 (doc-audit pass)**: three more problems found by
> checking the manuscript against real data rather than trusting prior
> claims.
> 1. **The manuscript did not compile.** Every `\includegraphics` except
>    the blockchain one pointed at PNG filenames in `all_figures/`, a
>    directory that did not exist anywhere in the repo (the D1/D2 defect
>    from `Overleaf/NeedToEdit.txt`, pre-existing, not introduced this
>    session). Fixed: all 7 real-data figures converted to vector PDF via
>    `rsvg-convert` into `Overleaf/all_figures/`, every `\includegraphics`
>    reference corrected to the real filename, and `exp_combined_3panel.pdf`
>    (Fig. 2, panels a/b/c = trapdoor-gen + query-vs-range + query-vs-N)
>    built from scratch — it never had a generating script before, only a
>    hand-composited file that was never actually committed.
> 2. **Every figure with error bars was plotting a 95% CI while every
>    caption claimed "±1 SD".** `yerr` was sourced from `ci95_ms`
>    (`1.96·SD/√n`) in `Benchmark/{01,02,03,04,05,07}*/experiment.py` and
>    the combined-panel script; captions said SD. Fixed: `yerr` switched
>    to `stdev_ms`/`stdev_qps` in all 6 experiments' plot code, figures
>    regenerated from the existing CSVs (no re-run — same real
>    already-collected data, just replotted). `harness.py`'s
>    `save_figure()` auto-stamp text also corrected from `"95% CI"` to
>    `"error bars = ±1 SD"`, so the auto-generated caption line matches
>    too, not just the hand-written captions. Fig. 7 (agg-strategy
>    comparison, panels b–c) claimed error bars that don't exist in
>    `06_Aggregation_Strategy/plot.py` at all (no `yerr`, no variance
>    retained in the summary CSV) — caption corrected to stop claiming
>    them rather than trigger an hours-long Exp06 rerun this close to the
>    deadline.
> 3. **Table V was mislabeled "Estimated"** in its caption, subsection
>    prose, and footnote, despite the numbers being real measured data
>    from Exp08 the whole time (verified byte-for-byte against
>    `CSV/exp08_communication_cost.csv`). Relabeled "Measured" throughout.
>
> Exploratory only, **not referenced by the manuscript**: bolder/black
> error-bar-marker copies and a per-scheme faceted small-multiples layout
> for Exp01 exist under `Figures/bold_errorbars/`, made when SD visibility
> was hard to judge on a shared log-scale axis. Not wired into
> `Overleaf/BVCRSA` — purely a visual-comparison aid, safe to ignore or
> delete.
>
> **Found 2026-08-19**: `CSV/exp10_primitive_table.csv` and
> `CSV/exp10_reconciliation.csv` (both dated Aug 18 22:57, the ones
> feeding Table VI / `tab:primitive_bench`) were measured on
> `env_host=jzguyr.local` — the **local Windows PC, not AWS**. This
> silently violates `RUN_LOCAL.md` §6 rule 1 ("every number in the
> paper comes from AWS") and contradicts the single-EC2-instance
> Experimental Setup claim. The manuscript's Table VI was **also**
> stale relative to all of this — its numbers (2.078ms ABSE Test etc.)
> matched none of the 4 candidate datasets found (local, or any of
> W1/W2/W3). Fixed by switching Table VI to real data from
> `CSV/exp10_primitive_microbench__W3.csv` (`ip-172-31-15-37`, same
> worker that produced Table V's Exp08 numbers, so both tables now
> trace to one physical instance). `exp10_primitive_table.csv` and
> `exp10_reconciliation.csv` themselves were **not** regenerated from
> W3 — they're not directly quoted in the manuscript prose, but anyone
> relying on them for a future reconciliation check should regenerate
> from an AWS worker's `exp10_primitive_microbench__W*.csv` first.

Local checks on Python 3.14.7 / Windows; production reruns on 3× AWS
`r7i.2xlarge`, Ubuntu 24.04, Python 3.12.3, BLS12-381 via
`py_arkworks_bls12381`.

`test_pipeline.py` passes end to end on all four machines: five phases,
Merkle proofs verified, decrypted SUM/CNT match expected plaintext.

| Exp | State |
|---|---|
| 01 Trapdoor Gen | ✅ **Real AWS data, all 5 schemes** |
| 02 Query Processing | ✅ **Real AWS data, all 3 sweeps** (vs_d has only BVCRSA/VC-KASE/Latt-IBEKS by design — see `CONJUNCTIVE_SCHEMES`) |
| 03 Query Throughput | ✅ **Real AWS data**; VC-KASE rows removed post-hoc (see above) |
| 04 Verification Overhead | ✅ **Real AWS data**, full dispersion, SVG |
| 05 Homomorphic Aggregation | ✅ unaffected by this pass — three arms, recomputation compared |
| 06 Aggregation Strategy | ✅ unaffected by this pass — one row per arm |
| 07 Aggregate-Recovery BSGS | ✅ unaffected by this pass |
| 08 Communication Cost | ✅ unaffected by this pass — real wire sizes, now cited in Table V |
| 09 Sensor-Side Cost | ⏸ needs the Pi for R1-C6 |
| 10 Primitive Microbench | ✅ re-run 2026-08-18, Table A/B both fully populated, no gaps |
| 11 Blockchain Cost | ✅ **Real 3-node AWS consortium, 2026-08-18** — Clique PoA, real gas/anchor/finality/cross-node-sync measured. Fixed 3 real bugs to get it running (`contract_address` key mismatch, `anchorEpoch`→`anchorEpochRoot` signature, missing POA middleware on the experiment's own Web3 connections). **Not complete per the original config**: only `node_count=3` was run — the `{1,5}` comparison points specified in `config.md` were never tested. Table VII and Fig. `blockchain_cost` in the manuscript are filled with this data. |

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

**6. The real baselines move BVCRSA from 4th to 2nd.** Re-measured at
N=1,000 on one machine against the *current* code (ground truth for
`sensor=Temp AND 35≤value≤65` is 11):

| scheme | index_build | query | matched | vs stale AWS query |
|---|---|---|---|---|
| **BVCRSA** | 9.72 s | **248 ms** | 6 ❌ | 256 ms (unchanged) |
| Trinity | 0.28 s | 17,587 ms | 11 | 502 ms → **35× slower** |
| VC-KASE | 4.13 s | 1,005 ms | 43 ❌ | 2.45 ms → **410× slower** |
| ABSE-Range | 18.91 s | 5,146 ms | 11 | 5,524 ms (≈) |

> **Superseded by real AWS data (2026-08-18).** This table was a
> single-machine spot-check before the full re-run. The actual
> `r7i.2xlarge` numbers at N=1,000 (`CSV/exp02_query_processing.csv`,
> `sweep=vs_N`) are the ones to cite:
>
> | scheme | mean_ms | matched |
> |---|---|---|
> | Latt-IBEKS | 4.27 | 11 |
> | BVCRSA | 291.74 | 6 |
> | VC-KASE | 1,186.05 | 43 |
> | ABSE-Range | 5,662.71 | 11 |
> | Trinity | 9,138.64 | 11 |
>
> Same ranking, different machine/absolute values — Latt-IBEKS fastest,
> BVCRSA a distant second, Trinity slowest. Use these, not the table
> above, for anything going in the manuscript.
| Latt-IBEKS | 3.12 s | **4.82 ms** | 11 | 2.80 ms → 1.7× slower |

BVCRSA's own number did not move — only the baselines did. Expect Exp 02
and 03 to invert against VC-KASE and Trinity. **Latt-IBEKS stays ~50×
faster and always will: its per-document test is a 408-element integer
dot product (0.00074 ms) against a BLS12-381 pairing (~1.0 ms).** Do not
plan to win on search latency.

Trapdoor generation, same machine, current code:

| d | BVCRSA | VC-KASE | Latt-IBEKS |
|---|---|---|---|
| 1 | 3.48 ms | 1.09 ms | 1.06 ms |
| 5 | 16.36 ms | 2.46 ms | 4.95 ms |

The stale Exp 01 gaps (12×→60× vs VC-KASE, 102×→699× vs Latt-IBEKS) were
artefacts: old VC-KASE's trapdoor was O(1) in `d`, and old Latt-IBEKS's
`_poly_vec()` padded to exactly `N_kw = 5` roots so `d` changed nothing.
Real gaps are **3.2×→6.7×** and **3.3×→3.3×**.

**7. Two of the three "wins" above are not yet defensible.** Trinity was
profiled (2026-08-17): its 17.6 s is **not** `range_to_intervals` but the
per-candidate token rekey — 1.5 M HMACs for 300 records — and Trinity-II
never consults the quotient filter its own paper relies on. See the
fairness audit in §11 (F2, F3); fixing either makes Trinity faster.
VC-KASE's 43 matches are every `Temp` record regardless of value — ref16
has no range predicate, so its 1,005 ms answers a different question and
it must stay excluded from range sweeps.

**Do not quote the 71× Trinity win or the 4× VC-KASE win in the
manuscript until F2/F3 are resolved.** The 21× over ABSE-Range needs
F4 checked first as well.

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

### Fixed 2026-08-17 (later pass — audit against the ref28 PDF)

| # | Defect | Fix |
|---|---|---|
| L1 | **`latt_ibeks.py` misquoted ref28's Table V** — "SampleLeft ~165s, SampleBasis ~119s". Verified against the PDF: SampleLeft **0.503 s**, SampleBasis **165.0 s**, NewBasisDel **119.1 s**, and the table is at **n = 2**, not the n = 17 used elsewhere in their evaluation | docstring corrected, all five values quoted, plus Table III's cost structure and Fig. 2's n=17 figures |
| L2 | **The `REPS = 8` justification was wrong** — claimed a matching key decodes correctly only ~50% of the time. Measured: **99.96%** per rep. `REPS` is nonetheless load-bearing: at `REPS=1` the query returns 215 matches against a truth of 11 (N=1,000) | docstring rewritten around the real mechanism — per-rep *false-accept* under a non-matching key ≈ 2·THRESH/q ≈ 19.5%, driven to ~2×10⁻⁶ by requiring all 8. **Do not reduce REPS** |
| L3 | `LattIBEKS.setup()` used an **unseeded** `RandomState()`, so `A` and `R` differed every run | `setup(seed=None)`; `LatticeIBEKSAlgo` passes `SEED`. Verified reproducible |
| L4 | **`_hvec` had no domain separation** — a keyword named `"(3, 5)"` derived the same target vector as dyadic range node `(3, 5)` | `_hvec(data, domain=...)`; range calls tagged `"range"`. Verified separated, round-trip still correct |
| L5 | `AWS/README.md` omitted `ecdsa` (and `pandas`) from its install line — the third doc with this gap | added |
| L7 | **R2-C3's "checked by hand" was only half answered** — Exp 10 measured the primitives but `reconcile()` merely *printed* four hardcoded expectations, with nothing to compare them against and no table anyone could cite | Exp 10 now emits **Table A** (`exp10_primitive_table.csv`, per-primitive unit cost) and **Table B** (`exp10_reconciliation.csv`, every total as `calls × unit cost` vs the value actually measured, with ratio + verdict), both also printed as paste-ready Markdown. Table B auto-loads the measured side from exp01/02/04/05/06; unrun rows print `NOT YET MEASURED`. **Table-writing logic dry-tested against synthetic primitives and the live CSVs (6/8 spec rows resolve today; the 2 gaps are exp01 d=5 and exp02 N=1,000, which only exist after the re-run). The benchmark itself has not been re-run.** |

### Cross-scheme fairness audit (2026-08-17)

Measured per-document cryptographic work in `query()` at N=300, counted
with `cProfile` — the metric that decides whether a latency comparison is
honest:

| scheme | query | pairings | HMACs | **pairings / doc** |
|---|---|---|---|---|
| **BVCRSA** | 92 ms | **48** | 0 | **0.16** |
| Trinity | 11,956 ms | 0 | **1,503,906** | 0 |
| VC-KASE | 460 ms | 300 | 0 | 1.00 |
| ABSE-Range | 2,140 ms | 1,578 | 0 | 5.26 |
| Latt-IBEKS | 4.3 ms | 0 | 0 | 0 |

| # | Finding | Verdict |
|---|---|---|
| **F1** | **BVCRSA is the only scheme permitted to use an index.** Its `(m_enc, k_enc)` context lookup prunes 300 records to ~15 candidate docs *before any pairing*, then the Eq. 37 bitmap filter prunes again — hence **0.16 pairings/doc against VC-KASE's 1.00 and ABSE-Range's 5.26**. Every baseline is coded as a linear scan. | For VC-KASE, ABSE-Range and Latt-IBEKS a linear scan **is** faithful to their papers, so this is a legitimate design win — **but it must be stated**, because a reader will assume all five scan equally. Much of the Exp 02 advantage is index pruning, not cheaper crypto. |
| **F2** | ~~Trinity-II's `query()` scans all of `self.EDB` while the quotient filter `gen_index` populates goes unused.~~ **FIXED 2026-08-17.** Also found: Trinity-**I**'s `self.qf.lookup(h)` (`trinity.py:450`) is a **no-op** — every indexed entry was inserted, so it always returns True. Neither version ever had working sub-linear search. | **FIXED.** `TrinityII.query()` now finds candidates via `_candidates_in_intervals()`, a bisect over a cached sorted `(hilbert_index, entry_id)` list — the same courtesy BVCRSA's `_by_ctx` index already gets (F1). Exact, no approximation, leaks nothing new (`hilbert_index` was already stored in the clear). **Verified: matched == ground truth at N=300 (3/3) and N=1,000 (11/11); N=300 query 10.0 s → 4.5 s.** |
| **F3** | **Trinity's dominant cost is `O(candidates × base_tokens)` HMACs and F2 barely dents it.** Measured at N=1,000 after the F2 fix: the query box shatters into **11,381 Hilbert intervals**, the trapdoor carries **18,558 base_tokens**, and **312 of 1,000** entries survive the range filter ⇒ **5.79 M HMACs**. The per-entry salt in `update_state()` blocks hoisting the rekeyed token set out of the loop. | **NOT a code bug — a benchmark-design mismatch, and it must be disclosed.** The fragmentation is inherent to forcing a **1-D numeric range onto one axis of a 3-D Hilbert curve** with the other two axes effectively unconstrained. That is a worst case for ref26's data structure; Trinity is built for genuine spatio-temporal *boxes*. Options: (a) disclose the mapping and the fragmentation as a stated limitation of the comparison, and/or (b) add a second sweep posing a real spatio-temporal query where Trinity is at its best. **Do not present the current Trinity latency as ref26's inherent cost.** |
| **F4** | **ABSE-Range does 5.26 pairings/doc**, the most of any scheme, because its canonical dyadic range-cover (D5 substitution) pairs every cover token against every document. | **Verify against ref27** before publishing a 21× win. If the paper's 0/1-encoding needs fewer pairings per document, our substitution is inflating its cost. |
| **F5** | **BVCRSA's 48 pairings authorize nobody** — see A8. Our per-document crypto is the cheapest in the table *and* it is not enforcing access control. | Fixing A8 will likely **raise** BVCRSA's cost. Budget for that before quoting Exp 02. |
| **F6** | **BVCRSA returns 6 of 11 true matches**; Trinity, ABSE-Range and Latt-IBEKS each return 11. | See E1′. Faster partly because it searches less. |

**Net direction of the remaining errors.** F3 still inflates Trinity; F4
may inflate ABSE-Range; F1 and F6 flatter BVCRSA; L6 flatters
Latt-IBEKS's trapdoor. **Most of the corrections work against us.** That
is the expected shape of an honest audit — if every fix had favoured
BVCRSA, the audit would be the thing to distrust.

**Still to do before the comparison is fair:**

1. **F4** — check ABSE-Range's 5.26 pairings/doc against ref27. If our
   dyadic-cover substitution pairs more per document than the paper's
   0/1-encoding, we are inflating the baseline we beat 21×.
2. **F6 / E1′ — the canonical query is still undefined.** BVCRSA's
   trapdoor binds one `(machine, t_slot)`; nothing else filters by
   machine, which is the whole 6-vs-11 gap at N=1,000. **Decide one
   query and hold every scheme to it**, then re-run. Either drop
   BVCRSA's context binding (its cost rises) or give the baselines the
   machine predicate (theirs rises). Until this is settled, no Exp 02/03
   number is comparable.
3. **F3** — write the Hilbert-fragmentation disclosure, and decide
   whether to add a spatio-temporal sweep that plays to ref26's design.
4. **A8** — fixing ABSE's forgeable Test will raise BVCRSA's own cost.
   Budget for it before quoting any final figure.

### Open — protocol decisions, not code bugs

| # | Issue | Why it needs you |
|---|---|---|
| **A8** | **ABSE tokens are forgeable.** `test()` never touches `PP`/`MSK`; the policy check is a plaintext `in` test. Every `ABSE.Test` timing measures a pairing that authorizes nobody. | Concrete form of **R1-C2 / R3-4**. Needs a real concrete ABSE construction with an actual policy-satisfaction check inside `test()`, not just a pairing that always succeeds |
| **P1** | `user_client.py:21` hands users `K_sel`, which the paper forbids. Code's `gen_tag` (Eq. 16) is keyed; the paper's Eq. `p3-node-keyword` is public. | **Which equation is authoritative?** Tag-level form of R3-1 |
| **P2** | **Merkle tree is per-record, not per-epoch** — `build_scrat_from_payload` builds a 3-leaf tree per record. Eq. `p2-epoch-commitment` specifies one root per epoch, so the multi-proof branch is unreachable and the production path is `O(r log N)`, not Table IV's `O(r log(N/r))`. | Restructuring indexing, not a patch |
| **L6** | **Latt-IBEKS trapdoors are forgeable — the master trapdoor is recoverable.** `_gadget_preimage()` is deterministic bit-decomposition, not Gaussian sampling, so a published trapdoor `x = [R@p ; p]` is one *linear equation* in `R` with `p` publicly computable from the keyword. Demonstrated: 204 trapdoors ⇒ **R recovered exactly** ⇒ forged a trapdoor for a never-queried keyword, **bit-identical** to the genuine one and accepted by `test_target()`. Also the reason its trapdoor is ~10⁶× cheaper than ref28's own ~300 s (Fig. 2b, n=17), and the reason `REPS` must be 8 (large-norm `sk` ⇒ noisy decode ⇒ `THRESH=400` ⇒ 19.5% per-rep false accept). | Fixing = real Gaussian perturbation sampling, the **highest-risk code in the suite**; deliberately not attempted. **Decision needed:** implement it, or publish the trapdoor timing as an explicit **lower bound** beside ref28's own ~300 s. Warning is now in the module docstring |
| **E1′** | The schemes answer **different queries** — BVCRSA's trapdoor binds one `(machine, t_slot)`; the others scan all N for (sensor, range). Quantified at N=1,000 against the current baselines: **BVCRSA returns 6 of the 11 true matches** while Trinity, ABSE-Range and Latt-IBEKS all return 11. BVCRSA is partly faster *because it searches less*. | Different selectivity ⇒ latency isn't like-for-like. **R3-16.** The single biggest threat to the comparison — fix parity or disclose it before any re-run |
| **E2′** | Exp 02 fits `c·N·log₂N` to a path that measures `O(N)`. | State it, or drop the extrapolation |

### Reporting caveats to disclose

- **Baseline match decisions used ground truth** for VC-KASE, Latt-IBEKS,
  Trinity and ABSE-Range — **now fixed for all four** (2026-08-17): every
  baseline derives its match set from real cryptography (Trinity-II
  state-aware token matching + verify_tag; VC-KASE real
  Extract/Test/Sign/Verify over BLS12-381; ABSE-Range real keyword +
  canonical-range-cover pairing match; Latt-IBEKS real MP12
  gadget-trapdoor sampling + real LWE keyword/range matching), each
  verified against ground truth over repeated test cases with zero
  mismatches. R3-16 — the manuscript's baseline-description text needs a
  disclosure paragraph stating what's real now (see this file's own
  defect register above, D1-D9/L1-L7/F1-F6, for the full technical
  basis to write it from).
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
  experimental setup verbatim** — not a toy shortcut. Confirmed against
  the PDF 2026-08-17: *"we set the parameter n = 17, q = 4093, k = 1,
  N_u = 1"*, C++/NTL, AMD Ryzen 5 3600, 1000 ciphertexts, Enron dataset.
  **But this is still not a uniform security setting** — LWE in
  dimension 17 is not 128-bit hard, while BVCRSA runs BLS12-381 at a
  genuine 128 bits. Faithful reproduction of their setup and
  security-parameter parity are different things; R3-16 asks for the
  latter, so state the mismatch explicitly.
- **Latt-IBEKS has no pairings at all** — it is LWE end to end
  (`TrapGen`/`NewBasisDel`/`SampleBasis`/`SampleLeft`/`SamplePre` plus
  matrix–vector products mod q). Its search advantage is a real property
  of the cryptographic family, not an implementation artefact: ref28's
  Table III gives Test as `(2m+1)·T_mul`, multiplications only. Our Test
  reproduces it faithfully (~7 ms/1000 docs vs their ~0.08 s/1000). **The
  correct claim is capability, not speed.**
- **Report Latt-IBEKS's trapdoor cost both ways.** Ours ≈ 1 ms (with the
  insecure deterministic sampler, see L6) *and* ref28's own ≈ 300 s at
  n=17 (their Fig. 2b). On their published cost, Exp 01 flips from a ~3×
  loss to a ~10⁵× win — that is the honest headline, and it needs the
  substitution disclosed to be usable.
- **ABSE-Range (ABSE-ERM, ref27) now applies a real numeric range
  predicate** (2026-08-17) via a canonical dyadic range-cover, not the
  paper's exact 0/1-coding construction (that needs a set-*absence* test
  that doesn't map cleanly onto a pairing match; see `Attribute-based.py`'s
  module docstring). Still missing: the paper's LSSS `(t,n)`-threshold
  access matrix — attribute-policy matching is still a flat list, not a
  threshold structure, not yet built.
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

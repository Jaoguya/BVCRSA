# Handoff — current state

Written 2026-08-17, rewritten 2026-08-19 — the previous version described a
run that finished and was fully superseded; nothing on this page was
accurate anymore. Read this first in a new session, then `SKILL.md` §10-11
for full detail.

---

## Where things actually stand

**Experiments 01–04**: real data, from a real AWS rerun against the current
(real-crypto) baselines, completed 2026-08-18. All 3 crypto-benchmark
workers used for that run are **stopped**. `CSV/exp0{1,2,3,4}_*.csv` and
the matching `Figures/` are current and correct — `env_host` in each row
confirms they came from the real workers, not a local smoke test.

**Experiment 11 (Blockchain)**: real data, from a real 3-node AWS Clique
PoA consortium, completed 2026-08-18. Those 3 instances are still up as
of this writing (not yet stopped — check before assuming). Table VII and
`Fig. blockchain_cost` in the manuscript are filled with this data.
**Known gap**: only `node_count=3` was run; the paper's own `config.md`
also specifies `{1,5}` as comparison points, never tested. See
`SKILL.md §10` and `Overleaf/NeedToEdit_Baselines.txt` item 11 for a full
skeptic pass on these numbers (submitter bias, non-independent trials
across the interval sweep, an unverified gas-anomaly explanation).

**Experiments 05–08, 10**: unaffected by any of this session's baseline
work (05-08 never import `baselines.py`; 10 was re-run 2026-08-18 anyway
for fresh Table A/B reconciliation data). All current.

**Experiment 09 (Sensor-side)**: still needs a Raspberry Pi. Not started.

---

## What actually happened this session, if you need the history

1. All four baselines (Trinity, ABSE-Range/ABSE-ERM, VC-KASE, Latt-IBEKS)
   were rebuilt from ground-truth-assisted matching to real cryptography.
   Full defect register: `SKILL.md §11` (D1-D9, L1-L7, F1-F6).
2. Exp01-04 were rerun on 3 AWS `r7i.2xlarge` workers against the rebuilt
   baselines. Total real runtime was far past the original estimate
   (~20.5h for Exp02 alone, dominated by Trinity) — see `SKILL.md §10`.
3. A 3-node Ethereum Clique PoA consortium was stood up on 3 new AWS
   `t3.medium` instances for Exp11. Real gotcha hit and fixed: AWS
   security-group self-reference rules don't reliably work over
   public-IP hairpin routing between same-VPC instances — P2P had to be
   reconfigured to use private IPs. Also fixed 3 code bugs in
   `11_Blockchain_Cost/experiment.py` to get it running at all (contract
   config key mismatch, wrong contract function signature, missing POA
   middleware on the experiment's own Web3 connections).
4. Manuscript tables/figures updated with real data: Table V
   (Communication Cost, from Exp08), the primitive-microbenchmark table
   (from Exp10), Table VII (Blockchain Anchoring Overhead, from Exp11),
   plus text corrections where prose claims didn't match measured
   numbers (the two "consistently achieves lowest/highest" sentences,
   the Exp03 run-count claim, the "multi-node not captured" paragraph).

## ImplementFIX cleanup (2026-08-19) — done

Per explicit instruction, every reference to `ImplementFIX/` was removed
from the project (the user is deleting that folder). This included
`Overleaf/NeedToEdit.txt`'s 13 dangling pointers to
`01_Protocol_Fixes.md`, `02_Proof_Fixes.md`, `03_Text_Fixes.md` —
rather than just deleting the pointers, the actual drafted LaTeX they
pointed to (recovered from commit `33ee254`, since `ImplementFIX/` was
already gone from HEAD) was inlined directly into `NeedToEdit.txt` at
each site: B1 (gateway HMAC), B2 (ABSE instantiation), B3 (the
aggregation-authorization-bypass fix, R3-1, "the most serious finding
in the review set"), B6 (completeness scope remark), B7 (Theorem 2
simulator proof), B8 (leakage concessions), B10 (invalidation
procedure), E1 (adopted-vs-novel paragraph), E2 (measurement-scope
disclaimer), E3 (bitmap-reconstruction algorithm). Nothing was lost —
`NeedToEdit.txt` is now self-contained and has no external pointers.
All other files (`MD/SKILL.md`, `MD/MACOS_HANDOFF.md`, `MD/RUN_LOCAL.md`,
`AWS/README.md`, `Overleaf/NeedToEdit_Baselines.txt`,
`Benchmark/_shared/*.py`) were cleaned the same session — confirmed via
`grep -rln "ImplementFIX" .` returning nothing outside `ImplementFIX/`
itself (which the user will delete directly).

One caveat left inline in `NeedToEdit.txt` (item C2/E2): the recovered
draft's baseline-implementation-choice paragraph (Trinity-I,
prime-order VC-KASE, small-parameter Latt-IBEKS) is now **stale** —
this session's baseline-fidelity work replaced those with real fixes
(Trinity-II, real VC-KASE Extract/Verify, real Latt-IBEKS MP12+LWE).
Use `Overleaf/NeedToEdit_Baselines.txt`'s disclosure text instead of
the inlined draft for that specific paragraph.

---

## Reconnecting to a running instance

IPs change on every stop/start (AWS reassigns the public IP). If an
instance is up and you don't have its current IP, check with whoever
last restarted it. Standard connection pattern once you have the IP:

```bash
ssh -i ~/BVCRSA_key.pem ubuntu@<ip>              # crypto-benchmark workers
ssh -i ~/Downloads/BlockchainBVCRSA.pem ubuntu@<ip>   # blockchain consortium nodes
```

Different key pairs for the two different instance groups — don't mix
them up.

---

## Still open — needs a decision, not more code

| # | Issue |
|---|---|
| **L6** | Latt-IBEKS's trapdoor sampler is demonstrably forgeable (deterministic preimage, not Gaussian). A fix attempt this session failed and confirmed the real fix needs proper Gaussian perturbation sampling — high-risk, deliberately not attempted. Currently reported as a documented lower-bound. |
| **F3** | Trinity's measured cost is inflated by a benchmark-query-shape mismatch (1-D range forced onto a 3-D Hilbert curve) — not representative of ref26's real-world cost. Needs disclosure text or a second Trinity-favorable sweep. |
| **A8** | ABSE tokens are forgeable — `test()` never touches `PP`/`MSK`. Fixing it will raise BVCRSA's own measured cost; budget for that before quoting a final Exp02 number. |
| **Exp11 node-count gap** | Only `node_count=3` tested; `{1,5}` from the experiment's own `config.md` never run. |

Plus everything in `Overleaf/NeedToEdit_Baselines.txt` (this session's
baseline-fidelity punch list) and `Overleaf/NeedToEdit.txt` (now
self-contained, see the ImplementFIX-cleanup note above).

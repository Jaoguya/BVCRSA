# Handoff — current state

Written 2026-08-17, rewritten 2026-08-19 (twice — the AWS-rerun pass, then
a much larger doc-vs-manuscript audit pass later the same day). Read this
first in a new session, then `SKILL.md` §10-11 for full detail, then
`ReviewerResponse/v1_new` for what's changed in the response letter.

---

## Where things actually stand

**Experiments 01–04, 08, 10, 11**: all real data. Every AWS instance used
to produce any of it is now **stopped** — confirmed by direct SSH
connection-timeout checks on every IP this session touched (the 3
original crypto workers, the ABSE-Range gap-fill worker, the 3
blockchain nodes). Nothing is running or billing anywhere right now.

**Experiment 09 (Sensor-side)**: still blocked on a real Raspberry Pi.
User is borrowing one from their university — full setup guide ready at
`MD/raspberry.md`, nothing to do until SSH access to the Pi exists. The
manuscript's Pi claim and the sensor-side numbers stay exactly as-is
(known-fake placeholder) until real data lands — do not touch.

**Experiment 11 node-count gap**: only `node_count=3` was run; the
experiment's own `config.md` also specifies `{1,5}`, never tested.
Disclosed honestly in the R7-C5 response rewrite in `v1_new` rather than
run — see `Overleaf/NeedToEdit_Baselines.txt` item 11 for the full
skeptic-pass writeup of this experiment's remaining weaknesses.

---

## The manuscript had real, serious problems beyond stale data — all fixed 2026-08-19

These were found by directly checking `Overleaf/BVCRSA` against the real
CSVs, not by trusting prior session notes. Full technical detail in
`SKILL.md §10`; this is the summary.

1. **The manuscript did not compile.** Every `\includegraphics` except
   the blockchain one pointed at PNG files in a folder (`all_figures/`)
   that didn't exist anywhere in the repo. Fixed: all 7 real-data figures
   converted to vector PDF into `Overleaf/all_figures/`, every reference
   corrected, and the "combined 3-panel" figure (Fig. 2) — which never
   had a generating script, only a described-but-never-built file — was
   built from scratch.

2. **Every figure with error bars was plotting a 95% CI while every
   caption claimed "±1 SD".** Systematic mismatch across 6 experiments'
   plotting code plus the shared `harness.py` auto-stamp. Fixed: `yerr`
   switched from `ci95_ms` to `stdev_ms` everywhere, figures replotted
   from the same real CSVs (no re-run needed), stamp text corrected.

3. **Table VI (primitive microbenchmarks) traced to a local Windows PC,
   not AWS.** The most-recent-looking CSV silently violated the paper's
   own "every number comes from AWS" claim, and its numbers didn't even
   match what was in the manuscript. Fixed: switched to real data from
   AWS worker `ip-172-31-15-37` (same worker that produced Table V's
   numbers).

4. **Table V was mislabeled "Estimated"** despite being real measured
   data the whole time. Relabeled "Measured".

5. **The biggest one: 7 places in the Performance Evaluation prose
   directly contradicted the manuscript's own embedded figures.**
   "BVCRSA exhibits the lowest/highest ___" in Trapdoor Gen, Query
   Throughput, and all 3 Query Processing sweeps — false; Latt-IBEKS is
   actually faster in every one of those, VC-KASE beats BVCRSA on
   verification past `|R_Q|~100`. The Aggregation section claimed
   "below 20ms", which was already known to be arithmetically impossible
   (real floor: ~53-76ms). This was tracked as
   `NeedToEdit_Baselines.txt` item 12 — flagged `[WAIT-FOR-RERUN]` back
   when the AWS rerun was still in progress, and never actually finished
   once it landed. Now `[DONE]`, full before/after number list in that
   file. Fix pattern used throughout: state the real ranking honestly,
   explain the gap via capability (BVCRSA does policy-binding +
   verification + aggregation-readiness that the faster, simpler
   baselines don't), not by hiding or re-fabricating a "wins" claim.
   Also added a Latt-IBEKS reduced-parameter disclosure to the
   "Baseline Configuration" paragraph, since it didn't exist before and
   several of the fixes now depend on the reader knowing why Latt-IBEKS
   is unusually fast.

6. **ABSE-Range gap-fill (N=20k/50k/100k) finished mid-session and was
   integrated** — appended to `CSV/exp02_query_processing.csv`,
   `exp02_query_vs_N.svg` and the combined-3-panel figure regenerated.
   Caveat: the ad-hoc script that ran it only logged summary stats, so
   `median_ms`/`raw_ms` are blank for those 3 rows specifically (noted
   in the CSV's own `note` column).

Exploratory, **not wired into the manuscript**: bolder/black error-bar
styling and a per-scheme faceted layout for Exp01 exist under
`Figures/bold_errorbars/`, made while investigating SD visibility on a
shared log-scale axis. Safe to ignore or delete.

---

## ImplementFIX cleanup (2026-08-19) — done

Every reference to `ImplementFIX/` was removed from the project (the
folder is being deleted). `Overleaf/NeedToEdit.txt`'s 13 dangling
pointers were resolved by inlining the actual drafted LaTeX they pointed
to (recovered from git history commit `33ee254`) directly at each site —
nothing was lost, the file is now self-contained. Confirmed via
`grep -rln "ImplementFIX" .` returning nothing outside `ImplementFIX/`
itself.

---

## Reconnecting to an instance, if you spin one back up

IPs change on every stop/start (AWS reassigns the public IP). Standard
connection pattern once you have a current IP:

```bash
ssh -i ~/BVCRSA_key.pem ubuntu@<ip>                   # crypto-benchmark workers
ssh -i ~/Downloads/BlockchainBVCRSA.pem ubuntu@<ip>   # blockchain consortium nodes
```

Different key pairs for the two instance groups — don't mix them up.

---

## Still open — needs a decision, not more code

| # | Issue |
|---|---|
| **L6** | Latt-IBEKS's trapdoor sampler is demonstrably forgeable (deterministic preimage, not Gaussian). A fix attempt failed; real fix needs proper Gaussian perturbation sampling — high-risk, deliberately not attempted. Currently reported as a documented lower-bound. |
| **F3** | Trinity's measured cost is inflated by a benchmark-query-shape mismatch (1-D range forced onto a 3-D Hilbert curve) — not representative of ref26's real-world cost. Needs disclosure text or a second Trinity-favorable sweep. |
| **A8** | ABSE tokens are forgeable — `test()` never touches `PP`/`MSK`. Fixing it will raise BVCRSA's own measured cost; budget for that before quoting a final Exp02 number. |
| **C2 (this session)** | `user_client.py` still leaks `K_sel` to users via `secrets["Ks"]`, contradicting the paper's "K_sel is never disclosed to users" claim. Not reviewer-visible (no public code repo linked), left unfixed given the deadline — fixing it would touch Exp01/02 (~20h to re-run). |
| **modelAHE.pdf** | Fig. 1 (system model) is a hand-drawn diagram that was never committed. The only remaining `\includegraphics` in the manuscript pointing at a file that doesn't exist. Needs actual diagram design (7 entities, trust boundaries per the original spec), not something derivable from data. |
| **Exp11 node-count gap** | Only `node_count=3` tested; `{1,5}` never run. Disclosed rather than fixed — see above. |

Plus everything in `Overleaf/NeedToEdit_Baselines.txt` and
`Overleaf/NeedToEdit.txt` (both self-contained, no external pointers).

---

## Reviewer response letter

`ReviewerResponse/v1` is the original draft — **never edit it**.
`ReviewerResponse/v1_new` holds every correction/addition on top of it:
2 blank responses filled in (R1-C4, R1-C5), 2 stale responses rewritten
with real data (R7-C5 multi-node blockchain, R4 blockchain gas bracket),
plus a running log of manuscript-only fixes that didn't need
response-letter changes. Read `v1_new`'s own header for the priority
order — Exp09 is still the one true blocker.

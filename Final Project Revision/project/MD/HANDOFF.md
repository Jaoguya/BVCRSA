# Handoff — current state

Written 2026-08-17, rewritten 2026-08-19 (three times that day), rewritten
again 2026-08-20 after the workflow rule change below. Read this first in
a new session, then `Overleaf/NeedToEdit.txt`'s "OVERLEAF SYNC LIST" for
what actually needs applying to the manuscript, then `SKILL.md` §10-11 for
full experiment/defect detail.

---

## ⚠️ CRITICAL WORKFLOW RULE (since 2026-08-20) — read this first

**Claude does not edit `Overleaf/BVCRSA` directly anymore.** All manuscript
changes go into `Overleaf/NeedToEdit.txt`'s "OVERLEAF SYNC LIST" section as
explicit old-context/new-context blocks, for the user to apply by hand to
the real Overleaf.com project.

**Why this changed**: the local `Overleaf/BVCRSA` file and the user's real
Overleaf.com project are two separately-maintained copies, manually synced
by hand (copy-paste) in both directions — there is no automatic sync. This
caused real damage during 2026-08-19: a teammate's local commit
accidentally reverted a large batch of real-AWS-data fixes back to
pre-session placeholder text (see "Git collaboration incident" below), and
separately the user pasted stale Overleaf.com content back over the local
file at least twice, undoing direct edits Claude had made that were never
actually round-tripped to Overleaf.com in the first place. The user does
not fully trust which copy is current anymore, reasonably. The fix is
structural, not another one-time restore: **one single channel
(`NeedToEdit.txt`) for all manuscript changes, applied by the user's own
hand, verified against their own Overleaf.com view.**

Practical effect: `Overleaf/BVCRSA` in this repo should be treated as a
**mirror of whatever's currently on Overleaf.com**, not a source of truth.
Don't trust its content without checking `NeedToEdit.txt` for outstanding
sync items first.

---

## Where things actually stand

**Experiments 01–04, 08, 10, 11**: all real data, all AWS instances that
produced them are stopped (verified via SSH timeout on every IP touched
this session — 3 crypto workers, the ABSE-Range gap-fill worker, 3
blockchain nodes). Nothing running or billing anywhere.

**Experiment 09 (Sensor-side)**: ✅ **DONE — real data collected 2026-08-19/20.**
Full story: the borrowed Pi's SD card initially had 32-bit Raspberry Pi OS
(Raspbian 11, Python 3.9) with no prebuilt BLS12-381 wheel available —
re-flashed via direct `dd` (not the Imager GUI, which had already failed
twice) to Ubuntu Server 24.04.4 LTS 64-bit, cloud-init `user-data` hand-edited
to guarantee working SSH (username `ubuntu`, password `bvcrsa2026pi`,
hostname `bvcrsa-pi`). Confirmed Python 3.12.3, real prebuilt
`py_arkworks_bls12381` wheel, no Rust compile needed — exactly the plan
`MD/raspberry.md` laid out. Found and fixed a real bug in
`09_Sensor_Side_Cost/experiment.py` (`abse.encrypt()` missing a required
`policy` arg). Data went through several real re-runs at the user's and
co-author's request: RUNS=50 first, then RUNS=20 (matches the paper's
20-run default elsewhere — both `experiment.py` and `config.md` updated),
Peak Memory column added then dropped again (co-author, an IEEE reviewer,
wanted crypto-operation focus only), precision taken to 4 decimal places.
Final numbers are in `Overleaf/NeedToEdit.txt` item 8 — total per-record
latency 72.6695ms, 98.8% public-key-dominated, 11.8x ciphertext expansion.
**Not yet applied to Overleaf.com** — that's on the user now, per the
workflow rule above.

**Experiment 11 node-count gap**: only `node_count=3` was run; `{1,5}`
from `config.md` never tested. Disclosed rather than run — see
`Overleaf/NeedToEdit_Baselines.txt` item 11.

---

## Git collaboration incident (2026-08-19/20) — resolved, but process changed because of it

A teammate (git identity `yewza101 <yewza232@gmail.com>`) accidentally
reverted ~200 lines of real-AWS-data fixes back to pre-session placeholder
text (their own commit message: "Revert experimental setup and performance
claims to pre-AWS version") — turned out to be an accidental pull/overwrite
from a stale branch, not a deliberate rejection. Restored by diffing
against the last-known-good commit (`788c634`) and re-merging in the
teammate's own genuinely-new addition (the Sensor-Side Table VII scaffold)
on top. Along the way: fixed the repo's git identity (was auto-detected as
`Jzguyr <puumax@jzguyr.local>`, now `Jzguyr <guyhd9119@gmail.com>`, local
to this repo only, not global), amended a commit message that had
inappropriate language in it, pushed the restore to
`origin/main` (`git@github.com:Jaoguya/BVCRSA.git`).

**This incident is the direct reason for the workflow rule above** — the
same "which copy is current" confusion happened a second time afterward
(this time via the user, not the teammate), which is what actually
triggered the switch to `NeedToEdit.txt`-only editing.

If working with the teammate again: confirm before either side pulls or
force-pushes, and point them at `NeedToEdit.txt`'s sync list rather than
letting them edit `Overleaf/BVCRSA` directly either.

---

## The manuscript had real, serious problems beyond stale data — found 2026-08-19, sync status varies

These were found by directly checking `Overleaf/BVCRSA` against the real
CSVs. Some were fixed directly in the local file before the workflow rule
change (2026-08-19); given the sync issues above, **do not assume any of
this has landed on the real Overleaf.com** — cross-check against
`NeedToEdit.txt`'s sync list, which is the authoritative "what's actually
missing on Overleaf.com" record as of 2026-08-20.

1. **The manuscript did not compile.** Every `\includegraphics` except
   the blockchain one pointed at PNG files in a folder (`all_figures/`)
   that didn't exist anywhere in the repo. Real vector PDF versions of
   all 7 figures exist in `Overleaf/all_figures/` now, ready to upload —
   see `NeedToEdit.txt` item 20 for the exact filename swaps needed.

2. **Every figure with error bars was plotting a 95% CI while every
   caption claimed "±1 SD".** Fixed in the local plotting code
   (`Benchmark/*/experiment.py`, `harness.py`) and regenerated —
   figures in `Overleaf/all_figures/` already reflect this fix.

3. **Table VI (primitive microbenchmarks) traced to a local Windows PC,
   not AWS**, and didn't match the manuscript's numbers either. Per the
   user's own screenshot check, **this is already correct on Overleaf.com**
   (real AWS numbers, matches worker `ip-172-31-15-37`) — no sync item
   needed.

4. **Table V mislabeled "Estimated"** despite real measured data.
   Numbers already correct on Overleaf.com per screenshot; only the label
   itself needs fixing — `NeedToEdit.txt` items 1-4.

5. **7 places in the Performance Evaluation prose directly contradicted
   the manuscript's own embedded figures** ("BVCRSA exhibits the
   lowest/highest ___" when Latt-IBEKS is actually faster in every one of
   them, VC-KASE beats BVCRSA on verification past `|R_Q|~100`, the
   Aggregation section's "below 20ms" is arithmetically impossible).
   Tracked as `NeedToEdit_Baselines.txt` item 12. Not yet confirmed
   applied to Overleaf.com — `NeedToEdit.txt` items 9-17 have the full
   fix text.

6. **ABSE-Range gap-fill (N=20k/50k/100k)** integrated into
   `CSV/exp02_query_processing.csv` and the regenerated figures. Caveat:
   `median_ms`/`raw_ms` blank for those 3 rows (ad-hoc script limitation,
   noted in the CSV).

Exploratory, **not part of the manuscript**: bolder/black error-bar
styling for several figures, including legend-repositioning fixes to
avoid line collisions (exp02_query_vs_range, exp03_query_throughput),
exist under `Figures/bold_errorbars/` as both SVG and genuine vector PDF.
Safe to ignore, delete, or ask about swapping into the real manuscript.

---

## ImplementFIX cleanup (2026-08-19) — done

Every reference to `ImplementFIX/` was removed from the project (the
folder is being deleted). `Overleaf/NeedToEdit.txt`'s old dangling
pointers were resolved by inlining the actual drafted LaTeX they pointed
to (recovered from git history commit `33ee254`) — nothing was lost.
Confirmed via `grep -rln "ImplementFIX" .` returning nothing outside
`ImplementFIX/` itself.

---

## Reconnecting to instances

**AWS** (IPs change on every stop/start):
```bash
ssh -i ~/BVCRSA_key.pem ubuntu@<ip>                   # crypto-benchmark workers
ssh -i ~/Downloads/BlockchainBVCRSA.pem ubuntu@<ip>   # blockchain consortium nodes
```

**Raspberry Pi** (static-ish on the home LAN, but DHCP could reassign):
```bash
ssh ubuntu@192.168.1.174   # password: bvcrsa2026pi, or SSH key already installed
```
If the IP changed, ping-sweep the LAN or check the router's DHCP client
list for hostname `bvcrsa-pi`.

---

## Still open — needs a decision, not more code

| # | Issue |
|---|---|
| **L6** | Latt-IBEKS's trapdoor sampler is demonstrably forgeable (deterministic preimage, not Gaussian). Real fix needs proper Gaussian perturbation sampling — high-risk, deliberately not attempted. Currently reported as a documented lower-bound. |
| **F3** | Trinity's measured cost is inflated by a benchmark-query-shape mismatch (1-D range forced onto a 3-D Hilbert curve). Needs disclosure text or a second Trinity-favorable sweep. |
| **A8** | ABSE tokens are forgeable — `test()` never touches `PP`/`MSK`. Fixing it will raise BVCRSA's own measured cost. |
| **C2** | `user_client.py` still leaks `K_sel` to users via `secrets["Ks"]`, contradicting the paper's "K_sel is never disclosed to users" claim. Not reviewer-visible (no public code repo linked), left unfixed — fixing it would touch Exp01/02 (~20h to re-run). |
| **modelAHE.pdf** | Fig. 1 (system model) is a hand-drawn diagram, never committed. Needs actual diagram design (7 entities, trust boundaries), not data-derivable. |
| **Exp11 node-count gap** | Only `node_count=3` tested; `{1,5}` never run. Disclosed rather than fixed. |

Plus everything in `Overleaf/NeedToEdit_Baselines.txt` and
`Overleaf/NeedToEdit.txt`'s sync list (both self-contained).

---

## Reviewer response letter

`ReviewerResponse/v1` is the original draft — **never edit it**.
`ReviewerResponse/v1_new` holds every correction/addition on top of it.
Exp09 being done means Reviewer 1 Comment 6's response can now be
finalized with real numbers — not yet done, since `v1_new` hadn't been
touched since before Exp09 completed. Worth a pass next time this file is
open.

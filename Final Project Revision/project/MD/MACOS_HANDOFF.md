# Handoff — switching to macOS

Read this when you move from the Windows PC to the Mac. Self-contained: it
assumes nothing carried over from the previous session.

---

## 1. What the Mac is for

**The Mac is an SSH terminal. Nothing else.**

```
Mac  ──ssh──►  EC2 (Ubuntu)  ← experiments run HERE
```

- No Python needed on the Mac.
- No venv on the Mac.
- **Do not run experiments on the Mac.** It would be a third hardware
  environment and break the consistent-hardware claim (R1-C5, R3-15).

The Windows PC keeps its own venv at `project/.venv` for development and
smoke tests. Both machines are just terminals into the same EC2 instance.

---

## 2. Where the work stands

### Done

| | |
|---|---|
| Repo restructured | `Benchmark/` (11 experiments + `_shared/`), `CSV/`, `Figures/`, `MD/`, `Overleaf/`, `ReviewerFeedBack/`, `AWS/` |
| Python environment | 3.14.7 on the PC, all deps installed, **BLS12-381 backend live** |
| `test_pipeline.py` | passes all five phases end to end |
| Reviewer analysis | `ReviewerFeedBack/Reviewer_1..7/Commend.md`, each comment with a fix |
| Paper edit list | `Overleaf/NeedToEdit.txt` (original) and `Overleaf/NeedToEdit_Baselines.txt` (baseline-fidelity session) — parts A–G |

### Bugs fixed (code)

1. Merkle proof verified against the wrong root — Phase 5 verification had
   **never** worked
2. Canonical path `[l, l+10]` vs client's `[l, l+9]` — PRF tags could never agree
3. `BVCRSAAlgo.query()` was a dict lookup; now routes through the real
   `UserClient → CloudServer → aggregate` path
4. `_query_fast` authorization tested only the first cover token → false negatives
5. All four baselines performed **no** cryptographic work; now they do
6. Exp 4 verification extended to include position checks and homomorphic
   recomputation of `CT_sum`/`CT_count`

### Not run yet

No full sweep has been executed. Everything so far is smoke tests on the PC.

---

## 3. First-time EC2 setup

⚠️ **Ubuntu needs a venv.** `pip install` into system Python is blocked
outright by PEP 668 — this is a Python/Linux thing, not a Windows thing.

```bash
ssh -i ~/.ssh/bvcrsa-key.pem ubuntu@<PUBLIC-IP>

sudo apt update && sudo apt install -y python3-pip python3-venv tmux rsync
python3 -m venv ~/venv && source ~/venv/bin/activate
pip install numpy matplotlib pycryptodome py_ecc ecdsa pandas
pip install py_arkworks_bls12381
echo "source ~/venv/bin/activate" >> ~/.bashrc
```

⚠️ `ecdsa` and `pandas` are required — `ec_elgamal.py` imports `ecdsa`, and the
salvaged plot scripts use `pandas`. Missing them was the first crash on the PC.

⚠️ Installing `py_arkworks_bls12381` selects **BLS12-381**. The paper says
`py_ecc`/BN128 — that text is wrong and must be corrected (NeedToEdit A1).
Keep the choice identical across every run.

Key permissions on the Mac:

```bash
chmod 400 ~/.ssh/bvcrsa-key.pem
```

Connection details live in `AWS/serverpath` — update that file, not the scripts.

---

## 4. Upload, run, retrieve

### Upload

From the project directory on whichever machine holds the current code:

```bash
rsync -avz -e "ssh -i ~/.ssh/bvcrsa-key.pem" \
  --exclude '__pycache__' --exclude '.venv' --exclude '*.pyc' \
  Benchmark/ ubuntu@<IP>:~/bvcrsa/Benchmark/
rsync -avz -e "ssh -i ~/.ssh/bvcrsa-key.pem" \
  CSV/Datarecord.csv ubuntu@<IP>:~/bvcrsa/CSV/
```

The remote tree must mirror the local one — `harness.py` resolves `CSV/` and
`Figures/` as siblings of `Benchmark/`:

```
~/bvcrsa/
├── Benchmark/   ├── CSV/   ├── Figures/   ├── AWS/   └── logs/
```

### Run unattended

This is the part that matters when you are not at a machine all day.

```bash
ssh -i ~/.ssh/bvcrsa-key.pem ubuntu@<IP>
tmux new -s bvcrsa
bash AWS/run_all.sh
```

Detach with **Ctrl-B** then **D**. Close the laptop, go to class. Reattach
later from *any* machine:

```bash
ssh -i ~/.ssh/bvcrsa-key.pem ubuntu@<IP>
tmux attach -t bvcrsa
```

`run_all.sh` runs every experiment in order, logs each to `logs/`, and keeps
going if one fails — a single broken experiment does not cost you the night.

Check progress without attaching:

```bash
ssh -i ~/.ssh/bvcrsa-key.pem ubuntu@<IP> "ls -la ~/bvcrsa/CSV/ && tail -5 ~/bvcrsa/logs/*.log"
```

### Retrieve

```bash
rsync -avz -e "ssh -i ~/.ssh/bvcrsa-key.pem" ubuntu@<IP>:~/bvcrsa/CSV/     ./CSV/
rsync -avz -e "ssh -i ~/.ssh/bvcrsa-key.pem" ubuntu@<IP>:~/bvcrsa/Figures/ ./Figures/
rsync -avz -e "ssh -i ~/.ssh/bvcrsa-key.pem" ubuntu@<IP>:~/bvcrsa/logs/    ./logs/
```

Then **stop the instance** in the EC2 console. You pay only for the EBS
volume (~$2.40/month) while stopped.

⚠️ Public IPs change on stop/start unless you attach an **Elastic IP**.

---

## 5. Expected runtimes

| Experiment | Time | Notes |
|---|---|---|
| 10 microbench | minutes | **run first** — calibrates everything else |
| 1 trapdoor | ~30 min | |
| 7 BSGS, 8 communication | minutes | |
| 4 verification | ~1 h | 300 runs × 10 points × 3 schemes |
| 5 aggregation | tens of min | real threshold decryptions |
| 6 agg strategy | several hours | |
| 3 throughput | ~15 min/scheme | sweep was cut — see §7 |
| 2 query processing | **many hours** | index builds to N=100k |
| 9 sensor-side | — | **Raspberry Pi only** |
| 11 blockchain | — | needs 3+ EC2 instances |

Full suite ≈ one overnight run. At ~$0.36/h for `c7i.2xlarge` that is roughly
$9 of compute.

---

## 6. Rules that must not be broken

1. **Every number in the paper comes from AWS.** PC runs are for debugging only.
2. **Never mix the legacy CSVs with new runs.** `CSV/exp*_LEGACY.csv` came from
   different hardware and a different Python. They are kept only because they
   hold the numbers currently quoted in the manuscript.
3. **Keep the pairing backend fixed.** Installing `py_arkworks_bls12381`
   changes the curve and therefore what the paper is describing.
4. Every result CSV records `env_host`, `env_platform`, `env_python`,
   `env_git_rev` — use them to prove which machine produced which numbers.

---

## 7. Decisions still open

> Historical — all 5 of these are resolved now (Trinity fixed to
> Trinity-II, `_query_fast`/`K_sel` leak documented as known issue not
> fixed, revocation disclosed as a limitation, Pi kept and real Exp09
> data collected 2026-08-19/20, Exp11 got a real 3-node consortium).
> See `MD/HANDOFF.md` for current status, this table is left as-is for
> historical context on what the original decision points were.

| # | Decision | Blocks |
|---|---|---|
| **1** | **Trinity crashes** on index build: `trinity.py:210` `shve.encrypt` → `struct.error: 'I' format requires 0 <= number <= 4294967295`. Pre-existing. Fix it, or drop Trinity from Tables I, IV, V. | Exps 1, 2, 3 comparative figures |
| **2** | `_query_fast` vs Table IV. **Recommendation: keep the `O(N_u·m_c)` legacy path** — `_query_fast` only works because `user_client.py:21` hands users `K_sel`, which the paper explicitly forbids. Fix that leak too. | Headline performance story |
| **3** | Revocation (R3-10): declare the limitation, or make node keys epoch-bound — the latter destroys the low-update-overhead claim. | Paper text |
| **4** | Raspberry Pi for Exp 9: keep one, or drop the heterogeneous-hardware claim. Energy is already resolved — report latency + memory and state that power instrumentation was unavailable. | R1-C6 |
| **5** | 3+ Ethereum nodes for Exp 11. | R7-C5 |

---

## 8. The finding that changes the paper

Wiring the benchmark to the production path gave, at N=1,000: **query 311 ms**
against the published **0.02 ms** — about 15,000× apart. Throughput moves from
a claimed 923,343 q/s to roughly 3 q/s.

The old harness never called `cloud_server.process_query()`, and its canonical
nodes could never match the client's tags, so every reported "match" came from
its own dictionary lookup.

⚠️ **All four baselines were also plaintext scans, historically** — since
fixed. As of 2026-08-18 all four (Trinity, ABSE-Range/ABSE-ERM, VC-KASE,
Latt-IBEKS) perform real cryptographic work *and* derive their match
decision from that real cryptography, not ground truth — see
`MD/SKILL.md §11` (D1-D9, L1-L7, F1-F6) for the full defect register and
`Overleaf/NeedToEdit_Baselines.txt` for what still needs manuscript text
to match. This section is left as a historical record of what the bug
originally was; it is not the current state.

---

## 9. What to do first, in order

This section described the original one-time transition to AWS-only
execution; that transition, the AWS runs, and the baseline rebuild it
anticipated are all long since complete. **For current status, read
`MD/HANDOFF.md` first, then `MD/SKILL.md §10-11`.**

---

## 10. Other reference documents

| File | Contents |
|---|---|
| `MD/HANDOFF.md` | Current live status — read this first |
| `MD/SKILL.md` | Full suite reference — folder rules, all 11 experiments, defect register |
| `MD/RUN_LOCAL.md` | Running on the Windows PC |
| `AWS/README.md` | Detailed AWS guide |
| `Overleaf/NeedToEdit.txt` | Original manuscript edit list, parts A–G (partially superseded — see `HANDOFF.md`) |
| `Overleaf/NeedToEdit_Baselines.txt` | Baseline-fidelity session's manuscript edit list |
| `ReviewerFeedBack/README.md` | Verdicts, convergence, work split |
| `Benchmark/NN_*/config.md` | Per-experiment configuration and reviewer mapping |

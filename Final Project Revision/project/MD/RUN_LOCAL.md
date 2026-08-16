# Running the experiments on your Windows PC

Nothing here needs AWS. The whole suite is single-threaded CPU-bound Python;
a modern desktop CPU is typically **faster per core** than an EC2 instance, so
local is the better place to develop and debug.

Use AWS for the *final* numbers only — see [../AWS/README.md](../AWS/README.md)
— because the paper needs one consistent hardware statement (R1-C5, R3-15) and
because Experiments 2, 4, and 6 run for hours unattended.

---

## Step 0 — Python is not installed

`python.exe` and `python3.exe` on your PATH are **0-byte Microsoft Store alias
stubs**, not interpreters. That is why running anything prints:

> *Python was not found; run without arguments to install from the Microsoft
> Store…*

Two things to fix, in this order.

### 0a. Turn off the Store aliases

**Settings → Apps → Advanced app settings → App execution aliases** →
toggle **off** `python.exe` and `python3.exe`.

Skip this and the 0-byte stubs keep shadowing the real install even after you
install it.

### 0b. Install Python from python.org

Download **Python 3.12** (64-bit) from <https://www.python.org/downloads/>.

⚠️ Not the Microsoft Store version — its filesystem sandboxing causes path
problems with the `CSV/` and `Figures/` writes the harness performs.

In the installer:

- ✅ **Add python.exe to PATH** (checkbox on the first screen — easy to miss)
- ✅ Install pip

Then open a **new** terminal and verify:

```powershell
python --version      # expect: Python 3.12.x
where.exe python      # must NOT be under WindowsApps
```

---

## Step 1 — Virtual environment

From `Final Project Revision\project\`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Your prompt should now start with `(.venv)`.

---

## Step 2 — Dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install numpy matplotlib pycryptodome py_ecc
```

Those four cover Experiments 1–10 with the BN128 backend.

### The pairing backend — a decision, not a preference

```powershell
python -m pip install py_arkworks_bls12381
```

⚠️ **This changes what your paper is describing.**

| Installed? | Backend | Paper text |
|---|---|---|
| yes | BLS12-381 via compiled Rust, ~50× faster pairings | ❌ paper says `py_ecc`/BN128 — **wrong** |
| no | BN128 via pure-Python `py_ecc` | ✅ matches the paper, but everything is ~50× slower |

Pick one, keep it fixed for every run, and make the manuscript match.
`ImplementFIX/01_Protocol_Fixes.md` §F4 has the corrected text for the
BLS12-381 case. Experiment 10 prints which backend is live.

If the install fails on Windows, it is a Rust extension without a prebuilt
wheel for your Python version. Either install the Rust toolchain
(<https://rustup.rs>) and retry, or just skip it and use `py_ecc`.

### Experiment 11 only

```powershell
python -m pip install web3
```

Not needed unless you are running the blockchain experiment, which also needs
Ethereum nodes.

---

## Step 3 — Sanity check

Always first. If this fails, no benchmark number is meaningful.

```powershell
python Benchmark\_shared\test_pipeline.py
```

Walks all five protocol phases on 5 records, in memory. Takes seconds.

---

## Step 4 — Calibration

```powershell
cd Benchmark\10_Primitive_Microbench
python experiment.py
cd ..\..
```

Prints the per-primitive costs and a reconciliation block giving the expected
floor for every other experiment. **Run this before the rest** — if a later
result lands far below its floor, the harness is measuring the wrong thing,
which is precisely the defect R1-C4 and R3-14 identified.

---

## Step 5 — The experiments

Each is `cd` into its folder, then run:

```powershell
cd Benchmark\01_Trapdoor_Gen        ; python experiment.py ; cd ..\..
cd Benchmark\02_Query_Processing    ; python experiment.py ; cd ..\..
cd Benchmark\03_Query_Throughput    ; python experiment.py ; cd ..\..
cd Benchmark\04_Verification_Overhead ; python experiment.py ; python plot.py ; cd ..\..
cd Benchmark\05_Homomorphic_Aggregation ; python experiment.py ; cd ..\..
cd Benchmark\06_Aggregation_Strategy ; python experiment.py ; python experiment_zoom.py ; python plot.py ; cd ..\..
cd Benchmark\07_Aggregate_Recovery_BSGS ; python experiment.py ; cd ..\..
cd Benchmark\08_Communication_Cost  ; python experiment.py ; cd ..\..
```

⚠️ PowerShell has no `&&`. Use `;` as above, or run each line separately.

Results land in `CSV\`, figures in `Figures\` — the harness creates both.

### Rough durations on a desktop CPU

| Experiment | Time |
|---|---|
| 10, 1, 7, 8 | minutes |
| 3, 5 | tens of minutes |
| 4 (300 runs × 10 points × 3 schemes) | ~1 hour |
| 6 (real threshold decryptions to \|S_Q\|=10,000) | several hours |
| 2 (index builds to N=100k) | **many hours** |

Start 2 and 6 when you can leave the PC alone. Exp 2 saves incrementally;
the others do not.

### Skip these locally

| Experiment | Why |
|---|---|
| **09 Sensor-Side** | Needs a Raspberry Pi + inline power meter (R1-C6). Runs on the PC, but the numbers would not answer the comment. |
| **11 Blockchain** | Needs 3+ Ethereum nodes for the consortium claim (R7-C5). Exits non-zero rather than emitting placeholder numbers. |

---

## First-run expectations

**These scripts have never been executed.** Expect import and API-signature
errors on the first pass, particularly:

- **Exp 10** probes for `abse.encrypt` / `abse.test` / `token_gen` method names
  that may differ from what `abse_fast.py` actually exposes.
- **Exp 07** reads the BSGS table via attribute names (`_bsgs_table`, `table`)
  that need confirming against `ec_elgamal.py`.
- **Exp 09** probes `ta.abse.encrypt`, which may not exist.

All three fail gracefully with a printed message rather than crashing the run.
Send me the output and I will fix them.

---

## Local vs AWS — which for what

| | PC | AWS |
|---|---|---|
| Development, debugging, first runs | ✅ faster iteration | ✗ |
| Long unattended runs (Exp 2, 6) | ⚠️ ties up your machine | ✅ tmux, detach |
| **Final numbers for the paper** | ✗ | ✅ one consistent hardware statement |
| Exp 11 multi-node consortium | ✗ | ✅ |

Every result CSV records `env_host`, `env_platform`, `env_python`, and
`env_git_rev`, so local and AWS runs are always distinguishable after the
fact. Do not mix them in the submitted figures — R1-C5 and R3-15 are
specifically about inconsistent hardware reporting.

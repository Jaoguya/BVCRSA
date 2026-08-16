# Running experiments on AWS EC2

AWS here is just **the machine that runs Python**. It is not the "Cloud
Server" of the BVCRSA protocol — that is `Benchmark/_shared/cloud_server.py`,
an in-process Python class requiring no infrastructure at all.

Records stay in `CSV/Datarecord.csv`. There is no database and no storage
service in this pipeline.

---

## 1. Instance sizing

The experiments are **single-threaded and CPU-bound** on bilinear pairings and
EC point arithmetic. Clock speed matters more than core count.

| | Recommendation |
|---|---|
| Type | `c7i.2xlarge` (8 vCPU, 16 GB) — or `c7i.xlarge` (4 vCPU, 8 GB) if cost matters |
| Storage | 30 GB gp3 — the dataset is 5 MB; the room is for the index in swap |
| OS | Ubuntu 22.04 LTS |

Why 16 GB: BVCRSA's index build at `N = 100,000` holds one EC-ElGamal
ciphertext per canonical node as a live Python object. That is the memory
ceiling of the whole suite. Everything else is small.

⚠️ Do not size for 10⁶–10⁷ records. Those figures are **extrapolated** in
Experiment 2 per R2-C4, not measured. The index build already takes ~765 s at
100k; 10⁷ is not reachable on any single instance.

---

## 2. One-time setup

### Key permissions

```bash
# Windows (PowerShell) — remove inherited ACLs, grant only yourself
icacls "C:\Users\Jzguyr\.ssh\bvcrsa-key.pem" /inheritance:r
icacls "C:\Users\Jzguyr\.ssh\bvcrsa-key.pem" /grant:r "$env:USERNAME:(R)"
```

SSH refuses a key readable by others. On Git Bash / Linux: `chmod 400 key.pem`.

### Security group

Inbound: **SSH (22)** from your IP only. Nothing else — no experiment listens
on a port.

⚠️ Experiment 11 (blockchain) is the sole exception: if you run a multi-node
consortium, those nodes need **8545/tcp** open *between the instances*, not to
the internet.

### Connect

```bash
ssh -i "C:/Users/Jzguyr/.ssh/bvcrsa-key.pem" ubuntu@<PUBLIC-IP>
```

### Install dependencies (on the instance)

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv
python3 -m venv ~/venv && source ~/venv/bin/activate
pip install numpy matplotlib pycryptodome py_ecc
pip install py_arkworks_bls12381     # BLS12-381 backend — see note below
pip install web3                     # Experiment 11 only
echo "source ~/venv/bin/activate" >> ~/.bashrc
```

⚠️ **The `py_arkworks_bls12381` decision is a paper-correctness issue, not a
convenience.** The manuscript says ABSE uses `py_ecc` over BN128. `TA.py`
prefers `abse_fast.py` (BLS12-381 via Rust) when this package is present.
Whichever you install is what the numbers describe — so either install it and
correct the paper, or omit it and accept ~50× slower pairings. Decide once,
record it in `serverpath`, and keep it fixed across all runs. Experiment 10
prints the live backend.

---

## 3. Upload

From your machine, in `Final Project Revision/project/`:

```bash
# code + dataset up (skip caches, results, figures)
rsync -avz -e "ssh -i C:/Users/Jzguyr/.ssh/bvcrsa-key.pem" \
  --exclude '__pycache__' --exclude '*.pyc' \
  Benchmark/ CSV/Datarecord.csv \
  ubuntu@<PUBLIC-IP>:/home/ubuntu/bvcrsa/
```

No rsync on Windows? Use `scp -r -i <key> Benchmark ubuntu@<ip>:~/bvcrsa/`.

Recreate the folder layout the harness expects:

```bash
ssh -i <key> ubuntu@<ip> "mkdir -p ~/bvcrsa/CSV ~/bvcrsa/Figures ~/bvcrsa/AWS"
```

`harness.py` derives `CSV/` and `Figures/` as siblings of `Benchmark/`, so the
remote tree must mirror the local one:

```
~/bvcrsa/
├── Benchmark/   (_shared + the 11 experiment folders)
├── CSV/         Datarecord.csv, then results land here
├── Figures/     SVGs land here
└── AWS/serverpath
```

---

## 4. Run

Long experiments outlive an SSH session — use `tmux` or they die when the
connection drops.

```bash
ssh -i <key> ubuntu@<ip>
tmux new -s bvcrsa

cd ~/bvcrsa
python Benchmark/_shared/test_pipeline.py          # sanity — run first

cd Benchmark/10_Primitive_Microbench && python experiment.py   # calibration
cd ../01_Trapdoor_Gen        && python experiment.py
cd ../02_Query_Processing    && python experiment.py
# ... and so on
```

Detach with `Ctrl-B` then `D`; reattach later with `tmux attach -t bvcrsa`.

⚠️ **Run Experiment 10 first.** It prints the expected cost of every other
experiment from measured per-primitive costs. If a later result lands orders
of magnitude below its floor, the harness is measuring the wrong thing — which
is exactly the defect R1-C4 and R3-14 identified.

### Expected durations (rough, `c7i.2xlarge`)

| Experiment | Time |
|---|---|
| 10 microbench | minutes |
| 1 trapdoor | minutes |
| 4 verification (300 runs × 10 points × 3 schemes) | ~1 h |
| 6 aggregation strategy (real threshold decryptions) | several hours |
| 2 query processing (index builds to N=100k) | **many hours** — the 100k index build alone is ~13 min per scheme |

Start 2 and 6 overnight in tmux.

---

## 5. Retrieve results

```bash
rsync -avz -e "ssh -i C:/Users/Jzguyr/.ssh/bvcrsa-key.pem" \
  ubuntu@<PUBLIC-IP>:/home/ubuntu/bvcrsa/CSV/ ./CSV/
rsync -avz -e "ssh -i C:/Users/Jzguyr/.ssh/bvcrsa-key.pem" \
  ubuntu@<PUBLIC-IP>:/home/ubuntu/bvcrsa/Figures/ ./Figures/
```

Every CSV carries `env_host`, `env_platform`, `env_python`, `env_aws_target`,
and `env_git_rev`, so you can prove afterwards which machine produced which
numbers — that is what answers R1-C5 and R3-15 on consistent hardware.

---

## 6. Keep `serverpath` current

`AWS/serverpath` is the single place the IP, key path, and instance type live.
Update it when the instance changes; nothing else hardcodes them.

⚠️ EC2 public IPs change on stop/start unless you attach an **Elastic IP**.
Attach one, or expect to edit this file after every restart.

Copy `AWS_INSTANCE_TYPE`, `AWS_VCPU`, `AWS_RAM_GB`, `AWS_OS` straight into the
paper's Experimental Setup — see `ImplementFIX/03_Text_Fixes.md` §F9, which
has the replacement paragraph with placeholders for exactly these values.

---

## 7. Cost control

`c7i.2xlarge` is roughly $0.36/hour on-demand. A full suite run is a day or
two of compute.

- **Stop** the instance between runs — you pay for the EBS volume only (~$2.40/month for 30 GB).
- Do **not** terminate unless you have pulled the results down.
- Consider a Spot instance for the long runs, but only with tmux + frequent
  CSV writes; Exp 2 already saves incrementally, others do not.

---

## What AWS does *not* change

- **No MongoDB.** Records come from `CSV/Datarecord.csv`.
- **No remote storage service.** Results are local files on the instance,
  pulled back by rsync.
- **`cloud_server.py` is still just a class.** The Cloud Server role runs
  in-process alongside the Edge Gateway and User Client. A distributed
  deployment would be a *different paper* — the current evaluation measures
  cryptographic cost, and §V now says so explicitly (R5-2).

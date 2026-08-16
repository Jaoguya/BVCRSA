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

---

# Multiple instances

There are **two different reasons** to run more than one instance. Do not
confuse them — they have opposite requirements.

| | Purpose | Instances | Requirement |
|---|---|---|---|
| **A. Parallel workers** | Finish the suite faster | 2–3, all **identical type** | Each runs *different* experiments, independently |
| **B. Blockchain consortium** | Experiment 11 only | 3+, networked to each other | They must talk over port 8545 |

---

## A. Parallel workers — cutting wall-clock time

The eleven experiments share no state. Each reads `CSV/Datarecord.csv`, writes
its own `CSV/expNN_*.csv`, and never touches another experiment's output. So
they can be split across instances with no coordination.

### Suggested split

| Worker | Experiments | Why |
|---|---|---|
| **W1** | 02 Query Processing | Longest single job — index builds to N=100k |
| **W2** | 06 Aggregation Strategy, 03 Throughput | Second longest — real threshold decryptions |
| **W3** | 01, 04, 05, 07, 08 | All the short ones together |

Expected wall-clock: roughly the length of W1 instead of the sum of everything.

### ⚠️ Three rules that keep the results publishable

1. **Identical instance type on every worker.** Mixing `c7i.2xlarge` with
   `c7i.xlarge` makes the numbers non-comparable and hands R1-C5 and R3-15
   exactly the inconsistency they objected to.

2. **Never split one experiment across workers.** All schemes inside a single
   experiment must run on the same machine, because the whole point is
   comparing them against each other. The split above respects this — each
   experiment lives entirely on one worker.

3. **Run Experiment 10 on *every* worker.** It takes minutes and measures
   per-primitive costs. Having it on each machine lets you reconcile that
   worker's results against *its own* primitive costs rather than another
   machine's — which is what R2-C3 asked for. Keep each copy; name them
   `exp10_primitive_microbench__W1.csv` etc. when you pull them down.

Every CSV already records `env_host`, `env_platform`, `env_python` and
`env_git_rev`, so which worker produced which row is always auditable.

### Setup

Build one instance completely (§2), then clone it — do not repeat the install
three times.

```bash
# 1. Set up W1 fully: venv, dependencies, code, Datarecord.csv.
#    Verify it works:
python Benchmark/_shared/test_pipeline.py

# 2. In the AWS console: Instances -> select W1 -> Actions ->
#    Image and templates -> Create image.  Wait for the AMI to become
#    "available" (a few minutes).

# 3. Launch 2 more instances from that AMI, same type, same key pair,
#    same security group.
```

Every worker now has identical software. Confirm before starting:

```bash
for h in $W1 $W2 $W3; do
  ssh -i key.pem ubuntu@$h "python --version; pip show py_arkworks_bls12381 | head -2"
done
```

⚠️ If `py_arkworks_bls12381` is present on one worker and missing on another,
that worker runs BN128 while the others run BLS12-381 — a ~50× difference that
would silently corrupt the comparison. Check it every time.

### Running

On each worker, in its own tmux session:

```bash
# W1
ssh -i key.pem ubuntu@$W1
tmux new -s w1
cd ~/bvcrsa/Benchmark/10_Primitive_Microbench && python experiment.py
cd ../02_Query_Processing && python experiment.py
# Ctrl-B, D
```

```bash
# W3 — the short ones
ssh -i key.pem ubuntu@$W3
tmux new -s w3
cd ~/bvcrsa/Benchmark/10_Primitive_Microbench && python experiment.py
for d in 01_Trapdoor_Gen 04_Verification_Overhead 05_Homomorphic_Aggregation \
         07_Aggregate_Recovery_BSGS 08_Communication_Cost; do
  ( cd ~/bvcrsa/Benchmark/$d && python experiment.py )
done
# Ctrl-B, D
```

### Collecting

Pull each worker into its own folder first, then merge — so a name collision
never silently overwrites a result.

```bash
for w in W1 W2 W3; do
  mkdir -p results/$w
  rsync -avz -e "ssh -i key.pem" ubuntu@${!w}:~/bvcrsa/CSV/     results/$w/
  rsync -avz -e "ssh -i key.pem" ubuntu@${!w}:~/bvcrsa/Figures/ results/$w/
  rsync -avz -e "ssh -i key.pem" ubuntu@${!w}:~/bvcrsa/logs/    results/$w/logs/
done
```

Then copy into `CSV/` and `Figures/`, keeping each worker's `exp10_*` under a
distinct name.

### Cost

Three `c7i.2xlarge` ≈ **$1.08/hour** combined. You finish in roughly a third of
the time, so the total bill is about the same — you are buying wall-clock, not
compute. **Stop each worker the moment its jobs finish**; do not leave two idle
while the third grinds through Exp 2.

---

## B. Blockchain consortium — Experiment 11 only

Different purpose entirely. R7-C5 rejects the single-node Clique PoA testnet
and asks for cross-node synchronisation latency, which cannot exist with one
node. These instances must reach each other.

`t3.medium` is sufficient — the nodes do almost no work.

### Security group

Add a rule allowing **8545/tcp** and **30303/tcp+udp** *from the security group
itself*, so the nodes talk to each other but the RPC port is not exposed to the
internet. Never open 8545 to `0.0.0.0/0` — it is an unauthenticated RPC endpoint.

### Setup, per node

```bash
sudo apt update && sudo apt install -y geth   # or the official tarball
geth --datadir ~/node init genesis.json       # same genesis on all 3
```

Use one Clique genesis file with all three signer addresses in `extraData`,
copied identically to every node.

```bash
geth --datadir ~/node --networkid 1337 \
     --http --http.addr 0.0.0.0 --http.port 8545 \
     --http.api eth,net,web3,personal,miner,clique \
     --mine --miner.etherbase <signer> \
     --unlock <signer> --password ~/pw.txt \
     --bootnodes enode://<node1-enode>@<node1-ip>:30303 \
     --syncmode full
```

Confirm the mesh is formed before measuring:

```bash
geth attach http://localhost:8545 --exec 'admin.peers.length'   # expect 2
```

### Running Experiment 11

From whichever instance holds the code:

```bash
export BVCRSA_NODE_RPCS=http://10.0.1.10:8545,http://10.0.1.11:8545,http://10.0.1.12:8545
export BVCRSA_BLOCK_INTERVALS=1,2,5,15
export BVCRSA_EPOCHS=20
cd Benchmark/11_Blockchain_Cost && python experiment.py
```

Block interval is set in the Clique genesis `period` field, so **each interval
in the sweep needs its own genesis and a chain restart**. Script it, or run the
four intervals as four separate short sessions.

⚠️ The experiment exits non-zero and writes no CSV if fewer than the expected
nodes answer. That is deliberate — inventing consortium numbers for a reviewer
who already rejected the single-node setup would be indefensible.

### Cost

Three `t3.medium` ≈ **$0.125/hour** combined. Experiment 11 is short; stop them
the same day.

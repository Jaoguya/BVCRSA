# Handoff — live AWS run

Written 2026-08-17. Read this first in a new session, then `SKILL.md`.

---

## What is running right now

Three EC2 workers, launched **2026-08-16 18:26 UTC**, each in a detached
`tmux` session named `bvcrsa`. They survive SSH disconnects, laptop shutdown,
and the end of any Claude session.

| Worker | Public IP | Queue | Projected |
|---|---|---|---|
| **W1** | `44.197.171.184` | Exp 10 → **Exp 02** | ~6.5 h |
| **W2** | `98.92.182.127` | Exp 10 → **Exp 03** → **Exp 01** | ~3.3 h |
| **W3** | `34.206.1.190` | Exp 10 → 04, 05, 06(+zoom,plot), 07, 08 | ~1 h |

Instances: `r7i.2xlarge` (8 vCPU, 64 GiB), Ubuntu 24.04, Python 3.12.3,
BLS12-381 via `py_arkworks_bls12381`, region `us-east-1`.

Not running: **Exp 09** (needs the Raspberry Pi) and **Exp 11** (needs a
3-node Ethereum consortium).

---

## Connecting from macOS

The key currently lives on the Windows box at
`C:\Users\Jzguyr\Downloads\BVCRSA_key.pem`. Copy it to the Mac, then:

```bash
chmod 400 ~/BVCRSA_key.pem
ssh -i ~/BVCRSA_key.pem ubuntu@44.197.171.184
```

⚠️ SSH refuses a key that is group- or world-readable. `chmod 400` is not
optional.

⚠️ The security group allows SSH **from the Windows machine's IP only**. From
a different network you must add your new IP: *EC2 → Security Groups → Inbound
rules → Edit → SSH → My IP*.

---

## Checking progress

Without attaching:

```bash
for ip in 44.197.171.184 98.92.182.127 34.206.1.190; do
  echo "=== $ip ==="
  ssh -i ~/BVCRSA_key.pem ubuntu@$ip 'tail -12 ~/bvcrsa/logs/STATUS_*.txt'
done
```

Each line is `experiment  OK|FAIL  <seconds>`. A worker is finished when its
status file ends with `WORKER_<label>_COMPLETE`.

Attach to watch live:

```bash
ssh -i ~/BVCRSA_key.pem ubuntu@44.197.171.184
tmux attach -t bvcrsa      # Ctrl-B then D to detach again
```

Per-experiment logs are in `~/bvcrsa/logs/<NN_Name>__experiment.log`.

---

## Collecting results

Run `AWS/collect.sh` from the project root, or by hand:

```bash
cd "Final Project Revision/project"
for ip in 44.197.171.184 98.92.182.127 34.206.1.190; do
  rsync -avz -e "ssh -i ~/BVCRSA_key.pem" ubuntu@$ip:~/bvcrsa/CSV/     ./CSV/
  rsync -avz -e "ssh -i ~/BVCRSA_key.pem" ubuntu@$ip:~/bvcrsa/Figures/ ./Figures/
  rsync -avz -e "ssh -i ~/BVCRSA_key.pem" ubuntu@$ip:~/bvcrsa/logs/    ./logs/
done
```

⚠️ **Each worker runs its own Exp 10**, so `exp10_primitive_microbench.csv`
exists three times and rsync will overwrite. That is deliberate — each
worker's results should reconcile against *its own* primitive costs (R2-C3).
Pull Exp 10 per worker under distinct names:

```bash
for w in W1:44.197.171.184 W2:98.92.182.127 W3:34.206.1.190; do
  scp -i ~/BVCRSA_key.pem ubuntu@${w#*:}:~/bvcrsa/CSV/exp10_primitive_microbench.csv \
      ./CSV/exp10_primitive_microbench__${w%%:*}.csv
done
```

Then **stop the instances** — nothing else needs them.

---

## Plots

Most experiments plot themselves and write SVG directly:

| Exp | Figure | Self-plots? |
|---|---|---|
| 01 | `exp01_trapdoor_gen.svg` | ✅ |
| 02 | `exp02_query_vs_{range,N,d}.svg` | ✅ |
| 03 | `exp03_query_throughput.svg` | ✅ |
| 04 | `exp04_verification_overhead.svg` | ✅ |
| 05 | `exp05_homomorphic_aggregation.svg` | ✅ |
| 06 | `exp06_agg_strategy_comparison.svg` | via `plot.py`, queued on W3 |
| 07 | `exp07_bsgs_scalability.svg` | ✅ |
| 08 | `exp08_communication_cost.svg` | ✅ |
| 10 | `exp10_primitive_microbench.svg` | ✅ |

All are vector — `harness.save_figure()` raises on any raster extension — and
carry 95 % CI error bars plus a "mean of N independent runs" stamp.

To regenerate a plot locally after collecting, re-run that experiment's
`plot.py`, or the experiment itself with the sweep reduced.

⚠️ For Overleaf, convert SVG → vector PDF (`pdflatex` does not take SVG):

```bash
for f in Figures/*.svg; do
  inkscape "$f" --export-type=pdf --export-filename="${f%.svg}.pdf"
done
```

Still vector, so R1-C8 is satisfied.

---

## What to do when the numbers land

1. **Sanity-check against Exp 10.** It prints expected totals from measured
   primitive costs. If a result is orders of magnitude below its floor, the
   harness measured the wrong thing — that is exactly how the original
   throughput bug was found.
2. **Compare to `ImplementFIX/07_Audit.md`** — the local pre-run numbers.
   Ratios should hold; absolute values will differ (different CPU).
3. **Work `Overleaf/NeedToEdit.txt`** top-down. Parts A–C are the experiment-
   dependent edits; parts B (protocol) and E (editorial) need no results and
   can be written while the run finishes.

---

## Still open — needs your decision, not code

| # | Issue |
|---|---|
| **A8** | ABSE tokens are forgeable — `test()` never touches `PP`/`MSK`, and the policy check is a plaintext `in` test. Concrete form of R1-C2 / R3-4. |
| **P1** | `user_client.py:21` gives users `K_sel`, which the paper forbids. Code's `gen_tag` is keyed; paper's Eq. `p3-node-keyword` is public. **Which is authoritative?** |
| **P2** | Merkle tree is **per-record**, not per-epoch, so the `O(r log(N/r))` multi-proof in Table IV is unreachable; production is `O(r log N)`. |
| **E1′** | Schemes answer different queries — BVCRSA binds one `(machine, t_slot)`; baselines scan all N. Selectivity differs, so latency is not like-for-like (R3-16). |

Plus the 24 paper-only reviewer comments in `NeedToEdit.txt`, including
**R3-1/2/3 — the aggregation authorization bypass**, the most serious finding
in the review set. None of that is blocked by the run.

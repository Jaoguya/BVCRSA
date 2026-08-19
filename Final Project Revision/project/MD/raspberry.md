# Raspberry Pi setup — Experiment 09 (sensor-side cost)

This Pi exists for exactly one purpose: real hardware numbers for Exp09
(`Benchmark/09_Sensor_Side_Cost`), which answers R1-C6. Nothing else in the
suite runs here — everything else already ran on AWS (`MD/HANDOFF.md`).

Self-contained: assumes nothing carried over from a previous session.

---

## 1. How control works

**VS Code Remote-SSH is for you** — browsing files, watching output, editing
if needed. **I drive the actual setup and experiment run over direct SSH**
from this Mac's terminal, the same pattern used for every AWS worker this
session (`ssh -i <key> user@<ip>`, no key needed here — password or a
regular SSH key on the LAN). So the one thing that actually matters before I
can do anything: **the Pi must be reachable by SSH from this Mac**, on the
same network or over Tailscale/VPN if not.

Once you give me the Pi's IP (and either its SSH password or a key), I take
it from there — venv, deps, code upload, run, pull results — same as the
AWS workers.

---

## 2. OS choice — Ubuntu Server 24.04.2 LTS (64-bit), not Raspberry Pi OS

**Why it matters:** every real result in this paper so far was measured on
Ubuntu 24.04 with Python 3.12.3 (`MD/SKILL.md` §10). Raspberry Pi OS
(Bookworm) ships **Python 3.11** by default — a silent version mismatch
against every other `env_python` column in the CSVs. Ubuntu Server 24.04 for
Raspberry Pi ships Python 3.12 by default, same as AWS. Use it.

Both are real Linux (Debian-family) — this isn't a "will it boot Linux"
question, it's "which Linux," and the answer is Ubuntu for consistency with
the rest of the suite.

### Imaging steps (do this before first boot)

1. Install **Raspberry Pi Imager** (<https://www.raspberrypi.com/software/>)
   on any machine with an SD-card slot/reader.
2. **Choose Device** → Raspberry Pi 4.
3. **Choose OS** → "Other general-purpose OS" → Ubuntu →
   **Ubuntu Server 24.04.2 LTS (64-bit)**. Not Ubuntu Desktop (no need for a
   GUI, and Desktop's overhead would pollute the sensor-cost numbers).
4. **Choose Storage** → the SD card.
5. Click the **gear icon (⚙ Edit Settings)** before writing — this is what
   makes the Pi reachable headless, no monitor/keyboard/HDMI needed:
   - Set hostname, e.g. `bvcrsa-pi`
   - Set username/password (or leave password blank and rely on SSH key —
     simpler to just set a password for the first login)
   - **Enable SSH** → "Use password authentication" (or paste a public key
     if you already have one you want pre-installed)
   - Configure Wi-Fi if not using Ethernet (SSID + password + correct
     country code — wrong country code is the #1 reason Pi Wi-Fi silently
     fails to associate)
   - Set locale/timezone
6. Write the image, eject, insert into the Pi, power on. First boot takes
   1-2 minutes longer than normal (partition resize).

---

## 3. Find the Pi and confirm SSH access

From this Mac, once the Pi has had ~2 minutes to boot:

```bash
ping bvcrsa-pi.local        # mDNS hostname, if avahi resolves on your LAN
# or check your router's DHCP client list for the hostname/IP
# or: nmap -sn 192.168.1.0/24   (adjust to your subnet)
```

Then confirm SSH works:

```bash
ssh ubuntu@bvcrsa-pi.local     # or ssh ubuntu@<ip> if mDNS doesn't resolve
```

(Ubuntu's cloud-init image defaults the username to whatever you set in the
Imager step above — `ubuntu` is the Ubuntu-image default if you left it.)

**Give me the IP (or working hostname) and confirm SSH is reachable — that's
the handoff point where I take over via direct SSH commands.**

---

## 4. VS Code Remote-SSH (for you to watch/browse)

1. Install the **Remote - SSH** extension in VS Code.
2. `Cmd+Shift+P` → "Remote-SSH: Add New SSH Host" → `ssh ubuntu@bvcrsa-pi.local`
3. `Cmd+Shift+P` → "Remote-SSH: Connect to Host" → pick it.
4. Open folder `~/bvcrsa` once it exists (step 6 below creates it) to watch
   files land and logs update in real time.

This is optional and purely for your visibility — I don't need it to do the
actual work.

---

## 5. What I'll run once I have SSH access

Documented here so you know what's about to happen — no action needed from
you beyond confirming access.

### 5a. System packages

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip git rsync tmux
python3 --version      # expect 3.12.x — confirms the Ubuntu 24.04 choice paid off
```

### 5b. Python environment

```bash
python3 -m venv ~/venv
source ~/venv/bin/activate
pip install --upgrade pip
pip install numpy matplotlib pycryptodome py_ecc ecdsa pandas
pip install py_arkworks_bls12381
```

⚠️ **Pairing backend must match the rest of the paper.** BLS12-381 via
`py_arkworks_bls12381` is what every other real number in this manuscript
uses (Exp01-04, 10). Confirmed before writing this doc: PyPI publishes a
real prebuilt `manylinux_2_17_aarch64` wheel for this package at Python
3.12, so `pip install` should just work — **no Rust toolchain needed** on
a real 64-bit Pi OS. If it somehow tries to build from source (wrong OS
architecture, 32-bit image, etc.), that's a sign step 2 above used the
wrong image — stop and re-check "64-bit" was actually selected, don't
route around it by installing Rust and compiling on a Pi 4, which would
take a long time for no reason.

Verify the backend loaded:

```bash
python3 -c "import py_arkworks_bls12381; print('BLS12-381 backend OK')"
```

### 5c. Upload the experiment code

Exp09 only needs two folders — no dataset CSV, no other experiment code:

```bash
rsync -avz -e ssh \
  "Benchmark/_shared/" ubuntu@bvcrsa-pi.local:~/bvcrsa/Benchmark/_shared/
rsync -avz -e ssh \
  "Benchmark/09_Sensor_Side_Cost/" ubuntu@bvcrsa-pi.local:~/bvcrsa/Benchmark/09_Sensor_Side_Cost/
```

Remote tree mirrors the AWS layout so `harness.py` resolves `CSV/` and
`Figures/` as siblings of `Benchmark/`:

```
~/bvcrsa/
├── Benchmark/{_shared, 09_Sensor_Side_Cost}
├── CSV/
└── Figures/
```

### 5d. Device identity and energy

```bash
export BVCRSA_DEVICE="Raspberry Pi 4 Model B 4GB"
```

⚠️ **Only use "4GB" if that's the actual RAM on the board you borrowed** —
check with `free -h` first. The paper's Experimental Setup names this exact
model; if the university's unit is 2GB or 8GB, tell me and the manuscript
text gets corrected to match, not the other way around.

```bash
free -h    # confirm RAM before setting BVCRSA_DEVICE above
```

Energy (optional): if you have access to an inline USB power meter
(~$10-15, e.g. a USB-C passthrough power meter), set:

```bash
export BVCRSA_DEVICE_WATTS=<measured active-power draw>
```

If you don't have one, **leave it unset** — the harness already handles
this honestly (leaves the energy column blank, `watts_measured=False`,
matching the "energy not estimated, instrumentation unavailable" line
already in the manuscript and the R1-C6 response). Don't guess a wattage
from a spec sheet; that's exactly the unsupported-number problem R1-C4 and
R3-17 already flagged elsewhere in this paper.

### 5e. Run it

```bash
cd ~/bvcrsa/Benchmark/09_Sensor_Side_Cost
source ~/venv/bin/activate
python3 experiment.py
```

RUNS=50, WARMUP=5, over 5 lightweight per-record operations (KDF, AES-GCM,
HMAC, ABSE key encapsulation, EC-ElGamal encrypt). This is small — minutes,
not hours. Watch for `ABSE_encapsulate_record_key` in the output; if it
prints "ABSE encapsulation skipped" instead of a timing, the backend didn't
load correctly — stop and go back to 5b.

### 5f. Sanity-check the output before trusting it

```bash
tail -6 ../../CSV/exp09_sensor_side_cost.csv
```

Confirm, in the `env_host`/`env_platform`/`runs` columns:
- `env_host` is the Pi's hostname (`bvcrsa-pi`), **not** a desktop name
- `env_platform` says `Linux-...-aarch64...`, **not** `Windows-...`
- `runs` = 50, not 2 — the previous CSV on disk right now is a stale
  2-run Windows smoke test that must be fully replaced, not merged with

### 5g. Pull results back to the Mac

```bash
rsync -avz -e ssh ubuntu@bvcrsa-pi.local:~/bvcrsa/CSV/exp09_sensor_side_cost.csv ./CSV/
rsync -avz -e ssh ubuntu@bvcrsa-pi.local:~/bvcrsa/Figures/exp09_sensor_side_cost.svg ./Figures/
```

---

## 6. After the run

Once real data lands, still open (tracked in
`ReviewerResponse/v1_new` PRIORITY 0):

1. Regenerate/replace `Figures/exp09_sensor_side_cost.svg` in the manuscript.
2. Fill the real per-step numbers into whatever table/prose in
   `Overleaf/BVCRSA` currently describes sensor-side cost.
3. Finalize Reviewer 1 Comment 6's response text in
   `ReviewerResponse/v1_new` with the real figures (currently held pending
   exactly this data).
4. Before returning the Pi to the university: `sudo shutdown now`, and
   confirm the SD card doesn't retain anything sensitive if it needs to go
   back with the hardware (it won't, by default nothing sensitive is on
   this box, but worth a glance at `~/bvcrsa` before wiping/returning).

---

## Checklist

- [ ] Ubuntu Server 24.04.2 LTS (64-bit) imaged, SSH enabled, hostname set
- [ ] Pi powered on, reachable via `ping`/`ssh` from this Mac
- [ ] IP/hostname + credentials handed to me
- [ ] `free -h` checked — actual RAM confirmed (paper says 4GB, verify it)
- [ ] (optional) USB inline power meter on hand, active-watts figure ready
- [ ] I take it from here: packages, venv, deps, backend check, code
      upload, run, sanity-check, pull results

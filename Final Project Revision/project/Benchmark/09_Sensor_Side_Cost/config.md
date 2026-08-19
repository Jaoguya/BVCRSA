# Experiment 9 — Complete Sensor-Side Cost

**Status:** NEW — reviewer-mandated, no prior code.
**Figure:** `exp09_sensor_side_cost.svg`
**Answers:** R1-C6

## Why it exists

> **R1-C6** — "The formal protocol requires sensors to perform ABSE key
> encapsulation and Threshold EC-ElGamal encryption in addition to AES-GCM
> encryption and HMAC authentication. However, the evaluation describes the
> sensor workload as consisting only of symmetric encryption and authenticated
> metadata generation. The authors should report the public-key computation
> time, energy consumption, memory usage, ciphertext expansion, and Raspberry
> Pi measurements for the complete sensor-side procedure."

The paper says sensors "perform only data acquisition, symmetric encryption,
and authenticated metadata generation." Phase 2 Step 1 says otherwise — it
requires two public-key operations per record. The evaluation understates the
sensor workload, and the reviewer caught it.

## Per-record steps measured

| Step | Class | Paper equation |
|---|---|---|
| `KDF(K_AES, rid‖N)` | symmetric | record-key derivation |
| `AES-GCM.Enc` | symmetric | `CT_AES` |
| `HMAC` tag | symmetric | `Tag_i` |
| **`ABSE.Enc(K_rec, P_i, e_i)`** | **public key** | `C_i^rec` — **omitted from the paper's description** |
| **`(rG, vG + r·pk_AHE)`** | **public key** | `CT_v` — **omitted from the paper's description** |

Reported per step: mean/stdev/CI, peak memory (`tracemalloc`), output bytes.
Plus a headline split: what fraction of sensor cost is public-key work, and
total ciphertext expansion over the plaintext record.

## ⚠️ Hardware

R1-C6 asks specifically for **Raspberry Pi** measurements. Everything else in
this suite now runs on AWS. Two options, pick one and be consistent:

1. Keep one Pi 4 (4 GB) for this experiment only, and say so.
2. Drop the heterogeneous-hardware claim from the Experimental Setup and
   report AWS numbers, conceding that sensor-class hardware was not measured.

Set the device label so the CSV records what actually ran:

```bash
export BVCRSA_DEVICE="Raspberry Pi 4 Model B 4GB"
```

## ⚠️ Energy

Wall-clock is measured directly; energy is derived as `E = P_active × t`.
`P_active` must come from a real inline USB power meter:

```bash
export BVCRSA_DEVICE_WATTS=3.4
```

If unset, the energy column is left **blank** and flagged
`watts_measured=False`. Do not publish an energy figure derived from a
guessed wattage — that is exactly the kind of unsupported number that drew
R1-C4 and R3-17.

## Statistics

```
RUNS = 20    WARMUP = 5
```

## Output

`../../CSV/exp09_sensor_side_cost.csv` —
`step, class, device, watts, watts_measured, energy_mJ, peak_mem_kb, output_bytes` + stats columns

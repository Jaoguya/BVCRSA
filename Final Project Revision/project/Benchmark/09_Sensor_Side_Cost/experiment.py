#!/usr/bin/env python3
"""
Experiment 09 — Complete Sensor-Side Cost
=========================================
Full per-record cost on the sensor, broken down by primitive.

WHY THIS EXPERIMENT EXISTS
--------------------------
R1-C6: "The formal protocol requires sensors to perform ABSE key encapsulation
        and Threshold EC-ElGamal encryption in addition to AES-GCM encryption
        and HMAC authentication. However, the evaluation describes the sensor
        workload as consisting only of symmetric encryption and authenticated
        metadata generation. The authors should report the public-key
        computation time, energy consumption, memory usage, ciphertext
        expansion, and Raspberry Pi measurements for the complete sensor-side
        procedure."

So the paper currently understates what a sensor does. Phase 2 Step 1 requires,
per record:
    K_i^rec  = KDF(K_AES^(i), rid_i || N_i)            symmetric
    C_i^rec  = ABSE.Enc(PP, K_i^rec, P_i, e_i)         PUBLIC KEY  <-- omitted
    CT_AES   = AES-GCM.Enc(...)                        symmetric
    CT_v     = (r*G, v*G + r*pk_AHE)                   PUBLIC KEY  <-- omitted
    Tag_i    = HMAC(...)                               symmetric

HARDWARE NOTE
-------------
R1-C6 explicitly asks for Raspberry Pi measurements. Everything else in this
suite now runs on AWS. Either keep one Pi 4 (4 GB) for this experiment alone,
or drop the heterogeneous-hardware claim from the Experimental Setup. Set
DEVICE_LABEL below to whatever actually ran it -- it is written into the CSV
so the hardware claim in the paper is auditable.

ENERGY
------
Wall-clock is measured here directly. Energy is derived as
    E = P_active * t
using a measured active-power figure for the device. Fill in DEVICE_WATTS from
an inline USB power meter on the Pi; the default is a placeholder and is
flagged as such in the CSV so it cannot silently become a published number.
"""

import _bootstrap  # noqa: F401
import os
import platform
import random
import tracemalloc

from baselines import timed, SEED
from harness import Experiment, new_figure, save_figure

DEVICE_LABEL = os.environ.get("BVCRSA_DEVICE", platform.node())
DEVICE_WATTS = float(os.environ.get("BVCRSA_DEVICE_WATTS", "0") or 0)
WATTS_MEASURED = DEVICE_WATTS > 0

RUNS = 50
WARMUP = 5
SENSOR_ID = "RPI_01"
MACHINE, KEYWORD, TSLOT = "Machine_01", "Temp", "2026-05-20 15:00:00"


def main():
    random.seed(SEED)

    exp = Experiment(9, "sensor_side_cost", [
        "step", "class", "device", "watts", "watts_measured",
        "energy_mJ", "peak_mem_kb", "output_bytes",
    ])

    print(f"\n  device = {DEVICE_LABEL}")
    if not WATTS_MEASURED:
        print("  !! DEVICE_WATTS not set -- energy column will be blank.")
        print("     Set BVCRSA_DEVICE_WATTS from an inline power meter before "
              "publishing any energy figure (R1-C6).")

    from TA import TrustedAuthority
    ta = TrustedAuthority()
    aes_key = ta.get_sensor_key(SENSOR_ID)
    hmac_key = ta.get_sensor_hmac_key(SENSOR_ID)

    steps = []

    # ── Symmetric: KDF ──────────────────────────────────────────────
    import hashlib
    rid = hashlib.sha256(f"{SENSOR_ID}|1".encode()).digest()
    nonce = os.urandom(12)
    steps.append(("KDF_record_key", "symmetric",
                  lambda: hashlib.sha256(aes_key + rid + nonce).digest(), 32))

    # ── Symmetric: AES-GCM ──────────────────────────────────────────
    try:
        from Crypto.Cipher import AES
        payload = f"{MACHINE}|{KEYWORD}|{TSLOT}|45".encode()

        def aes_gcm():
            c = AES.new(aes_key[:16], AES.MODE_GCM, nonce=nonce)
            ct, tag = c.encrypt_and_digest(payload)
            return ct + tag
        steps.append(("AES_GCM_encrypt", "symmetric", aes_gcm,
                      len(aes_gcm())))
    except ImportError:
        print("    pycryptodome missing -- AES-GCM step skipped")

    # ── Symmetric: HMAC tag ─────────────────────────────────────────
    import hmac as _hmac
    blob = os.urandom(256)
    steps.append(("HMAC_tag", "symmetric",
                  lambda: _hmac.new(hmac_key, blob, hashlib.sha256).digest(), 32))

    # ── PUBLIC KEY: Threshold EC-ElGamal encryption of v ────────────
    from ec_elgamal import generate_ec_elgamal_keypair
    pub, _priv = generate_ec_elgamal_keypair(max_val=100_000)
    steps.append(("ECElGamal_encrypt_value", "public_key",
                  lambda: pub.encrypt(45), 66))

    # ── PUBLIC KEY: ABSE key encapsulation ──────────────────────────
    try:
        abse = ta.abse
        rec_key = hashlib.sha256(aes_key + rid).digest()
        if hasattr(abse, "encrypt"):
            steps.append(("ABSE_encapsulate_record_key", "public_key",
                          lambda: abse.encrypt(rec_key.hex()[:32]), 192))
        else:
            print("    ABSE.Enc not exposed -- encapsulation step skipped")
    except Exception as e:
        print(f"    ABSE encapsulation skipped: {e}")

    # ── Run them ────────────────────────────────────────────────────
    for name, cls, fn, out_bytes in steps:
        tracemalloc.start()
        try:
            stats, _ = timed(fn, runs=RUNS, warmup=WARMUP)
        except Exception as e:
            tracemalloc.stop()
            print(f"    {name}: ERROR {e}")
            continue
        _cur, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        energy = (DEVICE_WATTS * stats["mean_ms"]) if WATTS_MEASURED else ""
        exp.record(stats, step=name, **{"class": cls},
                   device=DEVICE_LABEL,
                   watts=DEVICE_WATTS if WATTS_MEASURED else "",
                   watts_measured=WATTS_MEASURED,
                   energy_mJ=round(energy, 4) if WATTS_MEASURED else "",
                   peak_mem_kb=round(peak / 1024, 2),
                   output_bytes=out_bytes)
        print(f"    {name:<32} {cls:<11} {stats['mean_ms']:9.4f} ms "
              f"±{stats['ci95_ms']:.4f}  peak={peak/1024:8.1f} KiB")

    exp.save()
    summarize_split(exp.rows)
    plot(exp.rows)


def summarize_split(rows):
    """The headline number: how much of sensor cost is public-key work.

    This is the direct answer to R1-C6 -- the paper claims sensors do only
    symmetric crypto, so quantify exactly how wrong that is.
    """
    sym = sum(r["mean_ms"] for r in rows if r["class"] == "symmetric")
    pk = sum(r["mean_ms"] for r in rows if r["class"] == "public_key")
    total = sym + pk
    if not total:
        return
    plaintext = 32
    expansion = sum(r["output_bytes"] for r in rows) / plaintext
    print("\n" + "=" * 70)
    print("  SENSOR-SIDE BREAKDOWN (answers R1-C6)")
    print("=" * 70)
    print(f"  symmetric   {sym:9.4f} ms  ({sym/total*100:5.1f}%)")
    print(f"  public key  {pk:9.4f} ms  ({pk/total*100:5.1f}%)  <-- omitted "
          f"from the paper's current sensor-workload description")
    print(f"  total       {total:9.4f} ms per record")
    print(f"  ciphertext expansion  ~{expansion:.1f}x over a "
          f"{plaintext}-byte plaintext record")


def plot(rows):
    rows = sorted(rows, key=lambda r: r["mean_ms"])
    fig, ax = new_figure(figsize=(7.5, 4.6))
    colors = {"symmetric": "#1F77B4", "public_key": "#D62728"}
    ax.barh([r["step"].replace("_", " ") for r in rows],
            [r["mean_ms"] for r in rows],
            xerr=[r["ci95_ms"] for r in rows],
            color=[colors.get(r["class"], "#777") for r in rows],
            alpha=0.9, capsize=3)
    ax.set_xscale("log")
    ax.set_xlabel(f"Time per record on {DEVICE_LABEL} (ms, log scale)")
    ax.grid(True, axis="x", alpha=0.3, linestyle="--")
    import matplotlib.patches as mpatches
    ax.legend(handles=[mpatches.Patch(color=c, label=k.replace("_", " "))
                       for k, c in colors.items()], framealpha=0.9)
    save_figure(fig, "exp09_sensor_side_cost.svg", runs=RUNS)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
generate_datarecord.py
=======================
Reproducible synthetic IIoT sensor dataset generator for the BVCRSA paper's
scalability experiments (Fig. 2 index-construction time, Fig. 5 query
processing time, Fig. 7 query throughput — all versus database size N).

This script replaces a previously-empty generator: Datarecord.csv existed in
the repo with no way to regenerate or audit how it was produced. Every
parameter below is fixed and seeded so the dataset is fully reproducible.

Design follows the paper's stated Experimental Setup (Section V):
  - "Synthetic IIoT datasets consisting of records D_i = (m_i, k_i, t_i, v_i)
     were generated using 20 sensor categories, with numerical values
     uniformly distributed over [0, 100]."
  - Total pool size: 100,000 records. The N-value sweep used by the
    benchmark (1,000 / 5,000 / 10,000 / 50,000 / 100,000) simply reads the
    first N rows of this file, so all smaller-N experiments are consistent
    prefixes of the same underlying dataset (no re-sampling between runs).

Columns: id, machine, sensor, value, timestamp_str, t_slot
  - machine:       3 machine identifiers (A/B/C), uniformly assigned
  - sensor:        one of 20 sensor categories (see SENSOR_CATEGORIES)
  - value:         integer in [0, 100], uniform
  - timestamp_str: strictly increasing, 3s apart, starting 2024-01-01 00:00:00
                    (kept inside calendar year 2024 to match the fixed
                    [2024-01-01, 2025-01-01) time window assumed by the
                    Trinity baseline in the benchmark harness)
  - t_slot:         hourly bucket, first 13 chars of timestamp_str
"""

import csv
import os
import random
from datetime import datetime, timedelta

SEED = 42
TOTAL_RECORDS = 100_000
MACHINES = ["A", "B", "C"]

# 20 sensor categories per the paper's Experimental Setup text.
SENSOR_CATEGORIES = [
    "Temp", "Humidity", "Pressure", "Vibration", "Voltage",
    "Current", "Power", "Flow", "Level", "Speed",
    "Torque", "RPM", "Weight", "Density", "pH",
    "Viscosity", "Turbidity", "Proximity", "Strain", "Acoustic",
]
assert len(SENSOR_CATEGORIES) == 20

VALUE_MIN, VALUE_MAX = 0, 100
START_TS = datetime(2024, 1, 1, 0, 0, 0)
STEP_SECONDS = 3  # 100,000 records * 3s ≈ 3.47 days — stays within 2024

OUTPUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Datarecord.csv")


def generate(path=OUTPUT_CSV, total=TOTAL_RECORDS, seed=SEED):
    rng = random.Random(seed)
    ts = START_TS

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "machine", "sensor", "value", "timestamp_str", "t_slot"])

        for i in range(total):
            machine = rng.choice(MACHINES)
            sensor = rng.choice(SENSOR_CATEGORIES)
            value = rng.randint(VALUE_MIN, VALUE_MAX)
            timestamp_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            t_slot = timestamp_str[:13]

            writer.writerow([i, machine, sensor, value, timestamp_str, t_slot])

            ts += timedelta(seconds=STEP_SECONDS)

    print(f"Wrote {total:,} records to {path}")
    print(f"  Machines: {MACHINES}")
    print(f"  Sensor categories ({len(SENSOR_CATEGORIES)}): {SENSOR_CATEGORIES}")
    print(f"  Value range: [{VALUE_MIN}, {VALUE_MAX}]")
    print(f"  Timestamp range: {START_TS} .. {ts - timedelta(seconds=STEP_SECONDS)}")
    print(f"  Seed: {seed}")


if __name__ == "__main__":
    generate()

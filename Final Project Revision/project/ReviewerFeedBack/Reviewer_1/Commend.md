# Reviewer 1

**Verdict: REJECT** — "Therefore, I cannot recommend this manuscript for publication."

## Summary of position

Acknowledges the revision addressed user-side bitmap reconstruction, leakage
disclosure, threat-model separation, and completeness relative to the
gateway-committed state. Three blocking objections remain:

1. a key-distribution inconsistency,
2. an insufficiently specified ABSE construction,
3. experimental results incompatible with the stated `O(N_u × m_c)`
   token-matching complexity and record-linear verification.

Plus: the communication and aggregation experiments do not evaluate the
complete protocol as formally specified.

---

## R1-C1 — Gateway cannot verify sensor HMAC tags

> The gateway must verify sensor HMAC tags using K_HMAC^(i). However, the
> credential-distribution algorithm provides these keys only to the sensors.
> The gateway receives only K_sel and its signing key. Therefore, the
> sensor-packet authentication step cannot be executed as currently specified.

**Type:** protocol defect — paper-side. **Severity: blocking.**

This is correct and unambiguous. Phase 1 Step 4 distributes
`(K_AES^(i), K_HMAC^(i), pk_AHE)` to sensor *i* and `(K_sel, sk_DO)` to the
gateway. Phase 2 Step 2 then has the gateway compute
`HMAC.Verify_{K_HMAC^(i)}(...)` with a key it was never given.

### Fix

Amend Phase 1 Step 4 so the TA also provisions the gateway with the sensor
HMAC keys — either the full set `{K_HMAC^(i)}` for registered sensors, or a
master `K_HMAC_master` from which the gateway derives
`K_HMAC^(i) = KDF(K_HMAC_master, ID_i ‖ "hmac")`. The second is cleaner: it
keeps gateway state constant in the number of sensors and matches the
existing KDF pattern in Eq. (sensor-keys).

Then update:
- Eq. `credential-distribution` — add the key to the gateway's row
- `Sec_GW` in Eq. `secret-state` — now `(K_sel, sk_DO, K_HMAC_master)`
- **Threat model** — the gateway can now forge sensor packets. State that
  explicitly; it compounds P5 (R7-C1/C2). Note it cannot decrypt records,
  since `K_AES^(i)` is still sensor-only.
- Theorem 1 (Sensor-Packet Authenticity) — the proof's assumptions change.

⚠️ Verify `_shared/TA.py` and `_shared/blockchain_edge.py` against whichever
option is chosen. The code already does something here; the paper must
describe what the code actually does.

---

## R1-C2 — ABSE is an abstract interface, not a scheme

> The paper assumes an ABSE primitive that simultaneously provides searchable
> indexing, randomized context-bound query tokens, policy enforcement,
> user-collusion resistance, and payload-key encapsulation. However, no
> concrete ABSE scheme or formally proven composition is provided.
> Consequently, the protocol implementation and the associated security claims
> cannot be independently verified or reproduced.

**Type:** construction gap — paper-side. **Severity: blocking.**
Also raised by R3-4 and R3-5.

Eq. `abse-interface` defines ABSE as a 7-tuple of algorithm names with
correctness conditions but no instantiation. Every security theorem is
therefore conditional on unproven ABSE properties.

### Fix

Pick one:

- **(a)** Name a concrete published ABSE scheme, cite it, state its
  assumptions (e.g. DBDH / q-type over BN254), and show the mapping onto
  `Index / Token / Test / Enc / Dec`.
- **(b)** Give the composition explicitly — searchable ABSE + attribute-based
  KEM — and prove the composition secure, including that the two components'
  key material cannot be cross-used.

Then add implementation specifics: curve, library, parameter sizes, and how
`Token` achieves randomization and `(e_q, qid)` binding.

⚠️ Whatever is written must match `_shared/abse_fast.py` (BLS12-381, AND-gate
policy) and `_shared/abse_real.py` (BN128). See R2-C3 — the curve in the text
does not currently match the code.

---

## R1-C3 — Evaluation does not measure the complete verifiable protocol

> According to the formal protocol, every selected aggregation entry A_i must
> be returned to the user so that the user can independently recompute and
> verify the aggregate. However, the performance discussion claims that only
> compact aggregate ciphertexts and verification proofs are returned. The
> evaluation should measure the complete verifiable protocol, including the
> communication and client-side processing costs of all selected aggregation
> entries.

**Type:** experimental validity. **Severity: blocking.**

The measured "BVCRSA" arm returns `CT_sum`, `CT_count`, and a proof. The
formal protocol requires all `r` entries `A_i` so the user can recompute
independently. The headline "< 20 ms" is for a protocol variant the security
argument does not cover.

### Fix — **Experiment 5**, third arm

`Benchmark/05_Homomorphic_Aggregation/experiment.py` now measures three arms:

| Arm | What it does |
|---|---|
| Naive | user threshold-decrypts every matched ciphertext |
| BVCRSA-Compact | user decrypts 2 aggregates — what the paper reports today |
| **BVCRSA-Verifiable** | all `r` entries `A_i` + multi-proof transmitted, user recomputes and verifies independently — **the complete protocol** |

Report all three. Say which arm each claim refers to. If Verifiable lands
close to Naive, publish that; the honest number costs less than being caught.
Communication side is **Experiment 8** (`bytes_returned` column cross-checks).

---

## R1-C4 — Reported timings are not credible

> The scheme requires exhaustive ABSE matching with complexity O(Nu × mc),
> followed by authenticated bitmap processing and homomorphic aggregation.
> Nevertheless, the manuscript reports sub-millisecond execution times in
> Python and throughput close to 10^6 queries per second. Averaging the
> measurements over 20 runs does not adequately explain these results. The
> authors should provide raw timing data, operation counts, standard
> deviations or confidence intervals, implementation code, optimization
> details, and a precise definition of which operations are included in each
> measurement.

**Type:** experimental validity. **Severity: blocking.**
Also R2-C3, R3-13, R3-14, R3-17, R7-C4.

**The reviewer is right, and the cause has been found.** The old throughput
harness pre-generated one trapdoor and replayed it through `algo.query(td)` in
a loop — hitting a warm Python dict, performing no `ABSE.Test`, no bitmap
reconstruction, no aggregation. 923,343 q/s was a dictionary-lookup rate.

### Fix — five parts

1. **Raw data + CI everywhere.** `_shared/baselines.timed()` returns
   `mean / median / stdev / ci95 / min / max / raw_ms`;
   `harness.Experiment.record()` **rejects** any row lacking them. Error bars
   on every figure.
2. **Operation counts** logged beside every timing — `m_c`, `tokengen_calls`,
   `abse_test_calls`, `bitmap_words`, `hash_ops`, `decrypt_calls`, `ec_adds`.
3. **Per-primitive microbenchmarks — Experiment 10.** Single pairing, single
   `ABSE.Test`, single Merkle verify, bitmap AND over 100k bits, threshold
   decrypt. Prints a reconciliation block: expected total = count × unit cost.
   If a reported total is far under its floor, the harness is wrong.
4. **Throughput rebuilt — Experiment 3.** Fresh trapdoor per query, full path,
   and an assertion that `throughput ≈ 1000 / latency_ms`. Rows that fail are
   marked `FAIL` and must not be published.
5. **Precise measurement scope.** Each `config.md` names exactly what is
   inside the timed region and what is excluded.

⚠️ Expect the corrected numbers to be **much worse**. That is the point.

---

## R1-C5 — Dataset sizes are inconsistent

> The experimental setup states that the evaluated datasets contain at most
> 20,000 records, whereas the results section claims experiments involving up
> to 100,000 records. The manuscript should provide consistent dataset sizes,
> parameters, hardware settings, raw results, source code, and reproducible
> experimental scripts.

**Type:** internal inconsistency. **Severity: easy fix.** Also R3-15.

Setup says `10^3`–`2×10^4`; Query Processing says `10^3`–`10^5`.

### Fix

- **Experiment 2 is the authority.** Its sweep is `{1k, 5k, 10k, 20k, 50k, 100k}`.
  Correct the Experimental Setup text to **10³–10⁵**.
- ⚠️ Knock-on: the setup derives `Sum_max = 2×10^6` from `N ≤ 2×10^4`. At
  `N = 10^5` that becomes `10^7`. Fix the BSGS discussion and **Experiment 7**'s
  operating-point marker together.
- **Hardware:** now AWS-only (see R1-C6 for the Pi exception). The
  Pi/i7/Xeon description must be rewritten.
- **Raw results + scripts:** every CSV carries raw samples and an environment
  stamp (host, platform, Python, git rev). Release the repo.

---

## R1-C6 — Sensor-side cost is understated

> The formal protocol requires sensors to perform ABSE key encapsulation and
> Threshold EC-ElGamal encryption in addition to AES-GCM encryption and HMAC
> authentication. However, the evaluation describes the sensor workload as
> consisting only of symmetric encryption and authenticated metadata
> generation. The authors should report the public-key computation time,
> energy consumption, memory usage, ciphertext expansion, and Raspberry Pi
> measurements for the complete sensor-side procedure.

**Type:** experimental omission. **Severity: blocking.**

Phase 2 Step 1 requires two public-key operations per record —
`C_i^rec = ABSE.Enc(...)` and `CT_v = (rG, vG + r·pk_AHE)` — neither reflected
in the sensor-workload description.

### Fix — **Experiment 9**

`Benchmark/09_Sensor_Side_Cost/experiment.py` measures all five per-record
steps, split symmetric vs. public-key, reporting time, peak memory, output
bytes, and total ciphertext expansion.

Two things must be supplied before publishing:

- **Hardware.** `export BVCRSA_DEVICE="Raspberry Pi 4 Model B 4GB"`. Either
  keep one Pi for this experiment or drop the heterogeneous-hardware claim.
- **Energy.** `export BVCRSA_DEVICE_WATTS=<measured>` from a real inline power
  meter. If unset the column stays blank and is flagged `watts_measured=False`
  — a guessed wattage must never become a published number.

---

## R1-C7 — Communication cost needs real numbers

> Each matched canonical node requires the transmission of complete
> authenticated bitmap blocks, while each selected record requires an
> authenticated aggregation entry. Therefore, the communication cost grows
> with both the bitmap size and the number of matched records. A numerical
> end-to-end communication evaluation is necessary rather than relying only on
> asymptotic complexity expressions.

**Type:** experimental omission. **Severity: major.** Also R2-C5.

### Fix — **Experiment 8**

Measures actual bytes for request, response 1, response 2 across
`N ∈ {1k, 10k, 100k} × |R_Q| ∈ {50, 100, 500, 1000}`, from concrete wire
sizes (33 B EC point, 192 B ABSE token, 32 B hash, 64 B ECDSA sig).

Replace the O(·) cells in **Table V** with the `total_kb` column.

⚠️ Response 1 will dominate — every matched canonical node ships all `n_blk`
blocks regardless of how many bits are set. **Concede it in the text.** R1-C7
and R3-12 already suspect it.

---

## R1-C8 — Figures are raster and unreadable

> Figures have low resolution, small labels, and limited readability,
> particularly when viewed at normal manuscript scale. All diagrams and plots
> should be regenerated as true vector graphics and submitted in SVG or
> another IEEE-compatible vector format, such as EPS or vector PDF. Raster
> screenshots should be avoided.

**Type:** presentation. **Severity: easy fix.**

### Fix

`harness.save_figure()` writes **SVG and raises on any raster extension** — so
this cannot regress. `harness.new_figure()` sets IEEE-legible label sizes
(14 pt axis labels, 12 pt ticks) and `svg.fonttype: none` to keep text as text.

Both salvaged plot scripts (Exp 4, Exp 6) were repointed from `dpi=200/300`
PNG to SVG.

⚠️ Still missing and hand-made, not script-generated:
`modelAHE.pdf` (system model) and `fig_combined_3panel` — both must be
redrawn as vector.

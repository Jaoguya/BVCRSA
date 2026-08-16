# Response Letter — skeleton

One section per reviewer. Fill `<...>` after the experiments have run.

## Ground rules

1. **Concede fast on the real defects.** R3-1 (authorization bypass), R1-C1
   (key distribution), and R1-C4 (implausible timings) are all correct. Open
   each response by agreeing, then describe the fix. Arguing costs credibility
   that is needed elsewhere.
2. **Give the number, not the adjective.** R2-C2 rejected "variance was
   negligible." Every claim now has a CSV column behind it — cite it.
3. **Point at locations.** R2-C1's complaint was that changes were claimed but
   not findable. Every response should name section, equation, or figure.
4. **Do not cite R6 on experimental completeness.** R6 endorsed the BSGS
   experiment and the communication analysis; neither existed. Cite R6 on the
   protocol redesign and threshold architecture, which are real.

---

# Reviewer 1 — Reject

> **Overall.** We thank the reviewer for identifying three substantive defects.
> We accept all three. The protocol has been corrected, the ABSE construction
> instantiated concretely, and the entire experimental evaluation rebuilt —
> including one experiment that we discovered had never been implemented.

| Comment | Response |
|---|---|
| **C1** key distribution | Accepted; the reviewer is correct that the step cannot execute. Eq. (gateway-keys) now provisions the gateway with `K_HMAC^mas`, from which per-sensor keys derive (§III-C Phase 1 Step 4). Theorem 1's adversary class narrowed accordingly — the gateway is now excluded, and we state this explicitly. |
| **C2** abstract ABSE | Accepted. §III-C now gives the concrete construction, its DBDH assumption, and the collusion-resistance argument. We also correct the implementation description: measurements use BLS12-381 via `py_arkworks_bls12381`, not `py_ecc`/BN128 as previously stated. |
| **C3** incomplete protocol measured | Accepted. Fig. `<N>` now reports three arms, including **BVCRSA-Verifiable**, in which all `r` aggregation entries and the multi-proof are transmitted and the user recomputes independently. `<Compare the arms honestly.>` |
| **C4** implausible timings | Accepted, and we found the cause. The throughput harness replayed a single cached trapdoor through a warm dictionary, performing no `ABSE.Test`, bitmap reconstruction, or aggregation. Rebuilt: fresh trapdoor per query, full path timed, and an automatic assertion that throughput reconciles with per-query latency. §`<N>` adds per-primitive microbenchmarks so every total is checkable by hand. Raw per-run timings, operation counts, and 95 % CIs are released with the code. |
| **C5** dataset inconsistency | Accepted. The setup now states 10³–10⁵ consistently, and the dependent `Sum_max` figure is corrected to 10⁷. Hardware is now a single AWS instance for all experiments except sensor-side cost. |
| **C6** sensor workload understated | Accepted. §`<N>` reports the complete per-record sensor procedure split into symmetric and public-key work, with time, memory, ciphertext expansion, `<and energy on the Raspberry Pi 4>`. Public-key operations account for `<X>` % of sensor cost. |
| **C7** communication asymptotic | Accepted. Table V now carries measured KB for all three protocol rounds. `<State that response 1 dominates.>` |
| **C8** raster figures | Accepted. All plots regenerated as vector; the figure pipeline now refuses raster output. The system-model diagram has been redrawn as vector. |

---

# Reviewer 2 — Major revision

> **Overall.** The reviewer correctly notes that several previous responses
> asserted rather than demonstrated. We have replaced assertion with evidence.

| Comment | Response |
|---|---|
| **C1** adopted vs novel | Accepted. A single explicit paragraph now appears at the end of §I. |
| **C2** variance asserted | Accepted. Every table and figure now reports std-dev and 95 % CI; raw per-run measurements are released. `<Report the actual variance, whatever it is.>` |
| **C3** sub-ms latency | Accepted, and the concern was justified. §`<N>` reports per-primitive microbenchmarks. We also correct a factual error: the pairing backend is compiled-Rust BLS12-381, not pure-Python `py_ecc`, which partly accounts for the observed speeds. The remainder was a measurement error in the throughput harness, now fixed. |
| **C4** 100k is toy scale | Accepted. Fig. `<N>` extends the measured curve with an `O(N log N)` extrapolation to 10⁶–10⁷, labelled as extrapolation. |
| **C5** communication asymptotic | Accepted — see R1-C7. |
| **C6** Figs. 7/8 free-floating | Accepted. Both now tie explicitly to Table IV. For Fig. 8 we fit the growth exponent from the measured data: `<b>` for BSGS vs `<b>` for linear search, confirming the `O(√M_max)` bound. |
| **C7** regenerated under threshold? | **Partly correct, and we thank the reviewer for the check.** Fig. 7 *was* generated under `(3,5)` threshold EC-ElGamal — the 670.5× figure stands. Fig. 6 was **not**; it used single-key EC-ElGamal. It has been regenerated under the threshold scheme and the values updated. |
| **C8** run counts in captions | Accepted. Every caption now states its run count and statistic. We also correct the setup: verification uses the median of 300 runs, not the mean of 20. |

⚠️ C7 is the one place to be scrupulously precise. Half the reviewer's
suspicion was right. Saying exactly which half — and that Fig. 6's numbers
moved — is worth more than a blanket "yes, regenerated."

---

# Reviewer 3 — Reject

> **Overall.** The reviewer identifies an authorization vulnerability that we
> confirm and have corrected by protocol change. We are grateful; it is the
> most consequential finding of this round.

| Comment | Response |
|---|---|
| **1** authorization bypass | **Accepted — confirmed vulnerability.** Phase 4 Step 4 now requires the cloud to recompute the query bitmap and reject any `S_Q ⊄ Supp(B_Q)`. A new **Theorem (Aggregation Authorization)** proves no user obtains an aggregate outside its own authorized result set. |
| **2** policy incoherence | Accepted. The containment invariant `P_u ⟹ P_i` is now stated and enforced at index construction (Eq. `<n>`). |
| **3** TDA authorization | Accepted. Authorities now verify a query-authorization attestation before releasing a partial decryption. We state the residual boundary: this prevents unauthorized users, not cloud–user collusion. |
| **4** abstract ABSE | Accepted — see R1-C2. |
| **5** conditional proofs | Accepted. All theorem assumptions restated against the concrete construction. |
| **6** query privacy overstated | Accepted. Theorem 2 now carries an explicit remark that `U_Q` reveals the queried range to canonical-node granularity. |
| **7** users learn extra | Accepted. A **user-side leakage** subsection has been added — a category the previous version omitted. |
| **8** gateway metadata | Accepted; propagated from the threat model into the confidentiality claims. |
| **9** anchoring scope | Accepted. Completeness is now stated as *relative to the gateway-committed state* throughout, including the abstract. |
| **10** revocation | `<Choose: declare the limitation, or make node keys epoch-bound.>` |
| **11** epoch recommitment | `<Quantify index-update cost per epoch, or state the limitation.>` |
| **12** bitmap cost | Accepted. Now quantified in KB rather than asymptotically. |
| **13** query vs aggregation time | Accepted. Query time is now decomposed into search / bitmap / aggregate components that sum to the reported total and reconcile with the aggregation experiment. |
| **14** throughput vs latency | Accepted — see R1-C4. The harness now fails loudly when the two disagree. |
| **15** dataset sizes | Accepted — see R1-C5. |
| **16** baselines underdescribed | Accepted. §`<N>` describes each baseline's variant, parameters, and simplifications — including that VC-KASE uses a simulated pairing group and Latt-IBEKS small LWE parameters, both of which *understate* baseline cost. |
| **17** no raw data | Accepted. Raw samples, CIs, environment stamps, and per-experiment configuration files are released. |

---

# Reviewer 4 — Accept (minor)

> We thank the reviewer for the positive assessment.

| Comment | Response |
|---|---|
| **1** notation | Done — notation unified across text, tables, and figure axes. |
| **2** blockchain cost | Done. §`<N>` reports measured gas per epoch anchor, finality latency, and ledger growth. |
| **3** proofread | Done. |

⚠️ Add one honest note: *"We also note that the aggregate-recovery scalability
experiment the reviewer cites as a strength was, in the previous version,
described in the text without a corresponding implementation. It has now been
implemented and Fig. `<N>` reports measured results."* Volunteering this is
uncomfortable but far safer than a later reviewer discovering it.

---

# Reviewer 5 — Major revision

| Comment | Response |
|---|---|
| **1** bitmap reconstruction exposition | Done. Algorithm `<n>` presents the full key-derivation, masking, verification, and reconstruction procedure as one self-contained sequence, and states that `K_sel` is never disclosed to users. |
| **2** clarify scope and baseline parity | Done. §V opens with an explicit statement of what is inside the timed region, where communication and blockchain costs are reported instead, and how baseline functionality differs. |
| **3** Theorem 2 rigour | Done. Theorem 2 is restated as a real-or-simulated indistinguishability result with an explicit simulator and hybrid argument, plus a remark conceding that `U_Q` reveals range semantics. |

---

# Reviewer 6 — Publish unaltered

> We thank the reviewer. In the interest of accuracy we note that other
> reviewers identified issues requiring substantial revision, including an
> aggregation-authorization vulnerability and errors in the experimental
> methodology. This version addresses those.

Short and honest. Do not lean on this review.

---

# Reviewer 7 — Major revision

| Comment | Response |
|---|---|
| **1** gateway single point of trust | Accepted. `<Choose: scope the limitation explicitly, or add sensor co-signing of canonical-node metadata.>` The limitation is now prominent in the abstract and contributions, not only §IV. |
| **2** guarantees only vs the cloud | Accepted. Completeness restated as *relative to the gateway-committed state* in Theorem 7 and throughout. A remark sketches sensor co-signing as the route to a stronger guarantee. |
| **3** no update/delete | Accepted. §`<N>` specifies the invalidation workflow, with a remark on what version binding does and does not achieve. |
| **4** offline latency only, no error bars | Accepted. Communication (§`<N>`), blockchain (§`<N>`), and sensor energy (§`<N>`) are now measured. All curves carry 95 % CIs. `<Note whether wire RTT was measured; if not, say transmission time is deployment-dependent.>` |
| **5** single-node blockchain | Accepted. §`<N>` reports gas, finality, ledger growth, and cross-node synchronisation latency across `<k>`-node configurations and block intervals of 1/2/5/15 s. |

⚠️ C5 requires an actual multi-node deployment. A single-node re-run does not
answer it, and claiming otherwise will be checked.

---

# Before sending

- [ ] Every `<placeholder>` filled from measured data
- [ ] Every claimed change has a section/equation/figure number (R2-C1)
- [ ] Numbers in the letter match the CSVs
- [ ] Corrected numbers that got **worse** are stated plainly, not buried
- [ ] The BLS12-381 vs BN128 correction appears in the letter, not only the paper
- [ ] R2-C7 answered precisely: Fig. 7 was threshold, Fig. 6 was not
- [ ] The never-implemented BSGS experiment is disclosed to R4/R6

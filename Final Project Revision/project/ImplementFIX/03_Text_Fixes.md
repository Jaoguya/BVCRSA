# Text Fixes — copy-paste ready

Editorial patches against `../Overleaf/BVCRSA`. Each is self-contained.

---

# F10 — Adopted vs. novel components

**Reviewer:** R2-C1 — *"I could not locate a single place where this is stated
plainly. Scattering it across three sections is not the same as answering the
request."*

Insert at the end of §I, immediately before the contributions list:

```latex
For clarity, we state explicitly which components are adopted and which are
new. BVCRSA reuses the following existing primitives without modification:
attribute-based searchable encryption, lifted EC-ElGamal with $(t,n)$ Shamir
threshold decryption and Chaum--Pedersen DLEQ proofs, Merkle commitment
trees, and permissioned blockchain anchoring. The novel contributions are
(i)~the authenticated hierarchical range-cover index, which combines minimal
canonical interval decomposition with versioned, block-partitioned protected
bitmaps supporting cross-dimensional evaluation; (ii)~the bitmap-aware
encrypted aggregation mechanism, which binds each authenticated bitmap
position to a unique threshold aggregation entry; and (iii)~Verifiable Query
State Anchoring (VQSA), which authenticates index roots, bitmap parameters,
and aggregation state through signed blockchain-anchored Merkle commitments.
```

---

# F8 — Dataset size consistency

**Reviewer:** R1-C5, R3-15

Setup says `10^3`–`2\times10^4`; the results section goes to `10^5`.
**Experiment 2 is the authority: 10³–10⁵.**

§V Experimental Setup, replace:

```latex
The database size ranged from
\(10^3\) to \(2\times10^4\) records. Performance was
evaluated with respect to database size
(\(N=10^3\)--\(2\times10^4\)), query selectivity
```

with:

```latex
The database size ranged from
\(10^3\) to \(10^5\) records. Performance was
evaluated with respect to database size
(\(N=10^3\)--\(10^5\)), query selectivity
```

## ⚠️ Knock-on — the BSGS bound

The same subsection derives `Sum_max` from the old `N`. At `N = 10^5` and
`V_max = 100` it becomes `10^7`, not `2×10^6`. Replace:

```latex
Under our experimental configuration
(\(N\le2\times10^4\), \(V_{\max}=100\)), the maximum
aggregate sum is \(2\times10^6\), requiring approximately
\(\sqrt{2\times10^6}\approx1.4\times10^3\) baby-step
entries and a comparable number of giant-step iterations.
```

with:

```latex
Under our experimental configuration
(\(N\le10^5\), \(V_{\max}=100\)), the maximum
aggregate sum is \(10^7\), requiring approximately
\(\sqrt{10^7}\approx3.2\times10^3\) baby-step
entries and a comparable number of giant-step iterations.
```

⚠️ Update Experiment 7's `PAPER_OPERATING_POINT` in
`../Benchmark/07_Aggregate_Recovery_BSGS/experiment.py` from `2e6` to `1e7`
so the marked operating point on the figure matches the text.

---

# F9 — Hardware description

**Reviewer:** R1-C5 (consistent hardware settings)

Execution is now AWS-only. The current text is false. Replace:

```latex
Experiments were conducted on a heterogeneous IIoT
platform comprising a Raspberry Pi~4 Model~B (4~GB RAM)
for sensor operations, an Intel Core~i7 laptop (16~GB RAM)
for trapdoor generation, and an Intel Xeon server (32~GB
RAM, Ubuntu~22.04~LTS) for index construction, encrypted
query processing, aggregation, and verification.
```

with:

```latex
All experiments were conducted on a single Amazon EC2
\texttt{<INSTANCE\_TYPE>} instance (\texttt{<vCPU>} vCPUs, \texttt{<RAM>}~GB
RAM, Ubuntu~22.04~LTS), so that every reported measurement is taken under an
identical hardware and software configuration. The sole exception is the
sensor-side cost evaluation of Section~\ref{subsec:sensor_cost}, which is
performed on a Raspberry Pi~4 Model~B (4~GB RAM) in order to characterise
performance on resource-constrained IIoT hardware.
```

Fill the placeholders from the instance recorded in `../AWS/serverpath`.
Every result CSV also carries an environment stamp — host, platform, Python
version, git revision — so the claim is auditable.

⚠️ If you do **not** keep a Raspberry Pi, delete the exception sentence and
state in Experiment 9 that sensor-class hardware was not measured. Do not
leave a Pi claim in the text with no Pi behind it — R1-C6 asked for Pi numbers
specifically.

---

# F11 — Measurement scope and baseline parity disclaimer

**Reviewer:** R5-2, R3-16

Insert at the start of §V Performance Evaluation:

```latex
\subsubsection*{\textbf{Scope of Reported Measurements}}

Reported latencies measure cryptographic computation only. Network
transmission and blockchain interaction are excluded from the timed region
and are instead evaluated separately: end-to-end communication volume in
Section~\ref{subsec:comm_cost} and blockchain anchoring cost in
Section~\ref{subsec:chain_cost}. Each experiment states precisely which
operations lie inside its measured region.

The compared schemes do not offer identical functionality. No baseline
simultaneously supports attribute-based search, conjunctive range queries,
encrypted aggregation, and authenticated verification; comparisons are
therefore restricted to shared functionality. BVCRSA additionally performs
authenticated verification and aggregation binding, which the baselines omit,
and this overhead is included in all reported BVCRSA measurements.

For reproducibility we note the following baseline implementation choices.
Trinity is implemented as Trinity-I for index and query evaluation. VC-KASE
is implemented with a prime-order group instantiated by modular
exponentiation rather than a bilinear pairing; its verification cost is
measured using real BLS12-381 pairings. Latt-IBEKS is implemented following
Scheme-II for conjunctive queries with lattice dimension $n=17$ and modulus
$q=4093$, which is smaller than a deployment-grade LWE parameterisation and
therefore \emph{understates} its cost. All baselines were reimplemented from
their original descriptions and evaluated on identical hardware.
```

⚠️ The last paragraph is uncomfortable but necessary. R3-16 asks whether
comparisons guarantee "uniform security configurations". They do not. Saying
so — and noting the direction of the bias — is far stronger than being caught.

---

# F12 — Self-contained bitmap reconstruction

**Reviewer:** R5-1

The mechanism is currently spread across four equation blocks. Add one
algorithm collecting it end to end, in §III after Phase 4 Step 2:

```latex
\begin{algorithm}[t]
\caption{Authorized Bitmap Reconstruction}
\label{alg:bitmap-reconstruction}
\begin{algorithmic}[1]
\Statex \textbf{Gateway (Phase 2):}
\State $K_u \gets F(K_{\mathrm{sel}}, D_j \parallel u)$
\State $C_u^K \gets \mathsf{ABSE.Enc}(PP, K_u, \mathcal P_u, e_q)$
\For{each block $b$ of node $u$}
  \State $\widetilde B_{u,b} \gets B_{u,b} \oplus
         \mathsf{PRG}(F(K_u, b \parallel \nu_{u,b}), |B_{u,b}|)$
  \State $\sigma_{u,b}^{\mathrm{bmp}} \gets
         H(\mathtt{BMP}\parallel D_j\parallel u\parallel b
           \parallel\nu_{u,b}\parallel\widetilde B_{u,b})$
\EndFor
\State $Root_u^{\mathrm{bmp}} \gets
       \mathsf{MerkleRoot}(\mathsf{Sort}_b\{\sigma_{u,b}^{\mathrm{bmp}}\})$

\Statex \textbf{User (Phase 4):}
\State receive $C_u^K$, $\{\widetilde B_{u,b},\nu_{u,b}\}_{b=1}^{n_b}$,
       $\pi^{\mathrm{bmp}}$ for each $u\in\mathcal U_Q$
\State $K_u \gets \mathsf{ABSE.Dec}(SK_{\mathcal A}, C_u^K, e_q)$
       \Comment{succeeds iff $\mathcal A\models\mathcal P_u$}
\State verify each $\sigma_{u,b}^{\mathrm{bmp}}$ against
       $Root_u^{\mathrm{bmp}}$, and $Root_u^{\mathrm{bmp}}$ against the
       anchored $Root_{e_q}$; \textbf{abort} on failure
\State verify $n_b = n_{e_q}^{\mathrm{blk}}$
       \Comment{detects truncation}
\For{each block $b$}
  \State $B_{u,b} \gets \widetilde B_{u,b} \oplus
         \mathsf{PRG}(F(K_u, b \parallel \nu_{u,b}), |B_{u,b}|)$
\EndFor
\State $B_Q \gets
  \bigwedge_{j=1}^{d}\ \bigvee_{u\in\mathcal U_Q\cap\mathcal C_j} B_u$
\end{algorithmic}
\end{algorithm}
```

Follow with the sentence that carries the actual security property:

```latex
The gateway selector key $K_{\mathrm{sel}}$ is never disclosed to users; a
user obtains only those node keys $K_u$ whose policies $\mathcal P_u$ its
attribute set satisfies, and can therefore reconstruct only the bitmaps of
canonical nodes it is authorized to access.
```

---

# F14 — Notation sweep

**Reviewer:** R4-1

Pick one form per quantity and apply everywhere, including axis labels.

| Quantity | Use | Currently also appears as |
|---|---|---|
| matched canonical nodes | `\mathcal U_Q` | `U_Q`, `\|U_Q\|` vs `\|\mathcal U_Q\|` |
| canonical cover size | `m_c` | `\sum_j \ell_j` |
| matched records | `\|R_Q\|` | `r` (Table V), `\|S_Q\|` (Exp 6) |
| bitmap block count | `n_{e_q}^{\mathrm{blk}}` | `n_b` |
| selected positions | `\mathcal S_Q` | `S` (R3-1 quotes it as `S`) |

⚠️ The `r` / `|R_Q|` / `|S_Q|` collision is the one that matters — Figs. 6 and
7 currently label the same variable two different ways, which is what makes
R3-13's "durations do not align" objection hard to refute at a glance.

Update `tab:notation` and `tab:notation_cost` to match, then grep the source
for each discarded form.

---

# F15 — Run counts in captions

**Reviewer:** R2-C8

`harness.save_figure()` stamps the run count onto every figure. But the
captions must be **true**, and the blanket "20 independent runs" in the setup
currently is not:

| Experiment | Runs | Statistic |
|---|---|---|
| 1, 2, 3, 5, 6, 7, 8, 11 | 20 | mean ± 95 % CI |
| 4 — verification | **300** | **median** |
| 9 — sensor | 50 | mean ± 95 % CI |
| 10 — microbench | 200 | mean ± 95 % CI |

Replace the blanket claim in the setup:

```latex
All results represent the average of 20 independent runs.
```

with:

```latex
Unless stated otherwise, all results represent the mean of 20 independent
runs, reported with 95\% confidence intervals; raw per-run measurements are
released with the source code. Experiments whose per-operation cost is at or
below timer resolution use a larger sample: verification overhead
(Section~\ref{subsec:verif}) reports the median of 300 runs, and the
per-primitive microbenchmarks (Section~\ref{subsec:microbench}) the mean of
200 runs.
```

---

# F16 — Tie Figs. 7 and 8 to the cost derivations

**Reviewer:** R2-C6 — *"they read as free-floating experiments rather than
validation of the stated complexity."*

**Fig. 7 (Exp 6)**, append to the discussion:

```latex
Panel~(a) is the empirical realisation of the aggregation terms in
Table~\ref{tab:complexity_comparison}: the conventional strategy performs
$O(|R_Q|)$ threshold decryptions whereas BVCRSA performs $O(1)$, and the
measured call counts match these bounds exactly at every workload.
```

**Fig. 8 (Exp 7)**, append:

```latex
Fitting $\log t=a+b\log M_{\max}$ to the measured points yields
$b=\text{<BSGS\_EXPONENT>}$ for BSGS and $b=\text{<LINEAR\_EXPONENT>}$ for
linear search, confirming the $O(\sqrt{M_{\max}})$ and $O(M_{\max})$ bounds
used in the aggregate-recovery cost derivation of
Section~\ref{subsec:computation_cost}.
```

Experiment 7 prints both exponents. Paste the measured values.

---

# F17 — Leakage concessions

**Reviewer:** R3-6, R3-7, R3-8

Add to the leakage profile subsection. R3-7 names a category the paper
currently lacks entirely — **user-side leakage**:

```latex
\subsubsection*{User-Side Leakage}

An authorized user reconstructs the complete bitmap of every canonical node
its attributes authorize, not merely the positions matching its query range.
It therefore learns record membership for all positions of those nodes, which
reveals approximate numerical values to within the granularity of one
canonical interval, including for records outside its query result. This
leakage is inherent to node-granular bitmap authorization; reducing it
requires finer canonical partitioning, which increases the cover size $m_c$
and hence trapdoor size and query cost.

\subsubsection*{Gateway-Side Leakage}

The Edge Gateway observes sensor identities, update times, searchable
dimensions, canonical-node memberships, and bitmap positions in plaintext.
Confidentiality of record contents and aggregate values is preserved---the
gateway holds neither $K_{\mathrm{AES}}^{(i)}$, the ABSE master secret, nor
any threshold share---but membership and metadata are not hidden from it.
```

And soften the query-privacy claim wherever it appears unqualified, per the
Theorem 2 remark in [02_Proof_Fixes.md](02_Proof_Fixes.md).

---

# F18 — Deletion and update workflow

**Reviewer:** R7-C3

Add to §III or the Discussion:

```latex
\subsubsection*{Record Invalidation}

Although BVCRSA targets append-dominant workloads, expired or faulty readings
must be invalidatable. To invalidate record $i$, the gateway (i)~clears
$B_u[pos_i]\leftarrow0$ for every $u\in\mathsf{Path}(u_{i,j})$; (ii)~increments
$\nu_{u,b}$ for each affected block, forcing re-masking under a fresh PRG
stream; (iii)~marks the aggregation entry $\mathcal A_i$ as tombstoned so it
is excluded from subsequent aggregation; and (iv)~recomputes the affected
$\sigma_{u,b}^{\mathrm{bmp}}$, $Root_u^{\mathrm{bmp}}$,
$\sigma_u^{\mathrm{idx}}$, and $Root_{e_q}$. Only blocks containing $pos_i$
are re-masked; all others retain their existing version and commitment.

\begin{remark}
Version binding prevents an adversary from presenting a stale block as
current, but a user that previously reconstructed $B_{u,b}$ at version
$\nu-1$ retains that plaintext. Invalidation therefore prevents future
disclosure and future aggregation, not retroactive forgetting by users
already authorized at the time of ingestion.
\end{remark}
```

---

# F19 — Revocation

**Reviewer:** R3-10

`K_u = F(K_sel, D_j ‖ u)` is epoch-independent, so a revoked user keeps every
node key it ever recovered and can unmask *future* blocks of those nodes.

Two honest options:

**(a) Declare the limitation** — cheapest, and acceptable if stated:

```latex
Node keys $K_u$ are epoch-independent, so a user that has recovered $K_u$
retains the ability to unmask subsequent blocks of node $u$ even after its
attributes are revoked. BVCRSA therefore does not provide immediate
revocation; revocation takes effect only at the next node-key rotation.
```

**(b) Fix it** — make node keys epoch-bound,
`K_u^{(e)} = F(K_sel, D_j ‖ u ‖ e)`.

⚠️ **(b) conflicts with R3-11.** Epoch-bound node keys force re-masking and
re-committing *every* block each epoch, which destroys the version-binding
argument the paper uses to claim low update overhead. Choose (a) unless you
are prepared to re-measure index maintenance cost and revise that claim.

---

# F20 — Proofread

**Reviewer:** R4-3. Confirmed defects in the source:

| Location | Problem | Fix |
|---|---|---|
| §I | "primarily optimize encrypted retrieval **encrypted retrieval** and generally do not" | delete the duplicate |
| §III-C intro | "To ease of understanding, Table **Table**~\ref{tab:notation}" | "For ease of understanding, Table~\ref{tab:notation}" |
| §V Verification | prose says "Table IV" while the label resolves to `tab:complexity_comparison` | check every hard-coded table number against its `\ref` |

Then: `\DeclareUnicodeCharacter` directives at the top strip LTR/RTL marks —
a sign that invisible characters were pasted in at some point. Re-scan the
source for them before submitting.

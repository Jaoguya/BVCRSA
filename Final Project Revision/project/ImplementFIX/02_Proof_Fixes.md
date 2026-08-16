# Security Proof Fixes

Theorem restatements forced by the protocol changes in
[01_Protocol_Fixes.md](01_Protocol_Fixes.md), plus the rigour gaps reviewers
raised directly.

| Theorem | Change | Driver |
|---|---|---|
| 1 — Sensor-Packet Authenticity | adversary class narrows: gateway now excluded | F5 |
| 2 — Conjunctive Query Privacy | needs a simulator argument; concede `U_Q` leakage | R5-3, R3-6 |
| 5 — Threshold-Decryption Security | add the authorization precondition | F3 |
| 6 — Verifiable Aggregation Correctness | ⚠️ **currently proves the wrong statement** | F1 |
| 7 — Query-State Integrity | qualify completeness | F6 |
| — new | Aggregation Authorization | F1–F3 |

---

# Theorem 1 — Sensor-Packet Authenticity

**Change forced by F5.** Once the gateway holds `K_HMAC^mas`, it can derive
every `K_HMAC^(i)` and forge packets. The theorem no longer holds against the
gateway.

Restate the adversary class explicitly:

```latex
\begin{theorem}[Sensor-Packet Authenticity]
Let $\mathsf{HMAC}$ be an existentially unforgeable MAC. Then no PPT adversary
$\mathcal A$ that does not hold $K_{\mathrm{HMAC}}^{\mathrm{mas}}$---in
particular, the cloud server, unauthorized users, and external network
adversaries---can produce a packet $\mathcal P^{*}$ with a valid tag
$Tag^{*}$ for an unregistered $rid^{*}$, except with negligible probability
in $\lambda$. Replay of a previously accepted packet is prevented by the
strictly increasing sequence counter $seq_i$ and the uniqueness of $rid_i$.
\end{theorem}
```

Add immediately after:

```latex
\begin{remark}
Sensor-packet authenticity is not claimed against the Edge Gateway, which
derives $K_{\mathrm{HMAC}}^{(i)}$ in order to verify incoming packets. A
malicious gateway is outside the threat model; see Remark~\ref{rem:completeness-scope}.
\end{remark}
```

⚠️ Do not quietly leave the old statement standing. R1 found the key
inconsistency; leaving a theorem that implicitly assumes the gateway *cannot*
forge, after fixing the protocol so it *can*, invites the same reviewer to
find it again.

---

# Theorem 2 — Conjunctive Query Privacy

**Reviewer:** R5-3 (simulator), R3-6 (leakage concession). Both required.

The current proof argues informally from ABSE token pseudorandomness. Replace
with a real-or-simulated indistinguishability statement.

```latex
\begin{theorem}[Conjunctive Query Privacy]
Let $\mathcal L_{\mathrm{BVCRSA}}$ be the leakage function of
Section~\ref{sec:leakage}. If $\mathsf{ABSE}$ provides token
indistinguishability under DBDH and $\mathsf{PRG}$ is a secure pseudorandom
generator, then there exists a PPT simulator $\mathcal S$ such that for every
PPT adversary $\mathcal A$ and every query sequence
$\mathbf Q=(Q_1,\ldots,Q_m)$,
\begin{equation}
\left|
\Pr[\mathbf{Real}_{\mathcal A}(\lambda,\mathbf Q)=1]
-
\Pr[\mathbf{Ideal}_{\mathcal A,\mathcal S}
(\lambda,\mathcal L_{\mathrm{BVCRSA}}(\mathbf Q))=1]
\right|
\le\mathsf{negl}(\lambda).
\end{equation}
\end{theorem}
```

Proof sketch to expand:

```latex
\begin{proof}[Proof sketch]
$\mathcal S$ is given only
$\mathcal L_{\mathrm{BVCRSA}}(\mathbf Q)
=\bigl(\{\mathcal U_{Q_k}\},\{|\mathcal S_{Q_k}|\},\{d_k\},
\mathsf{AccPat}(\mathbf Q),\mathsf{QueryPat}(\mathbf Q)\bigr)$.
It simulates each trapdoor as follows.

\emph{Hybrid $\mathbf H_0$.} The real execution.

\emph{Hybrid $\mathbf H_1$.} Replace every $Tok_{j,i}$ with a uniformly random
group element of the same form. $\mathbf H_0\approx_c\mathbf H_1$ by token
indistinguishability of $\mathsf{ABSE}$ under DBDH; a distinguisher yields a
DBDH solver by the standard reduction, using $(e_q,qid)$ as the
context binding so that tokens for distinct queries are independently
randomised.

\emph{Hybrid $\mathbf H_2$.} Replace every protected block
$\widetilde B_{u,b}$ for non-matched $u$ with a uniformly random bitstring of
length $|B_{u,b}|$. $\mathbf H_1\approx_c\mathbf H_2$ by PRG security, since
$K_u$ for non-matched nodes is never recovered by $\mathcal A$.

$\mathbf H_2$ is computable from $\mathcal L_{\mathrm{BVCRSA}}(\mathbf Q)$
alone: $\mathcal S$ knows which nodes matched, how many positions were
selected, and the access pattern, and samples everything else at random.
Setting $\mathcal S:=\mathbf H_2$ gives the claim.
\end{proof}
```

Then the concession — this is what R5-3 and R3-6 both want in writing:

```latex
\begin{remark}[Range-Semantic Leakage]
Theorem~2 guarantees only that nothing beyond
$\mathcal L_{\mathrm{BVCRSA}}$ is revealed; it does not claim that the queried
interval is hidden. Because canonical nodes correspond to fixed dyadic
intervals of the searchable domain, the matched set $\mathcal U_Q$ bounds
$[a_j,b_j]$ to within the granularity of one canonical node. An adversary
observing $\mathcal U_Q$ therefore learns the queried range up to that
granularity. Finer canonical partitions reduce this leakage at the cost of a
larger cover size $m_c$ and correspondingly larger trapdoors.
\end{remark}
```

⚠️ The honest Theorem 2 is **weaker** than the current one. Weaker and
provable beats stronger and hand-waved — and R5 has already signalled they
will accept the weaker version if it is stated openly.

---

# Theorem 5 — Threshold-Decryption Security

**Change forced by F3.** Add the authorization precondition.

```latex
\begin{theorem}[Threshold-Decryption Security]
Under the Decisional Diffie--Hellman assumption in the NIST P-256 group, an
adversary corrupting at most $t-1$ of the $n$ authorities, and colluding with
the cloud and any set of unauthorized users, cannot recover
$x$ or any aggregate plaintext, except with negligible probability.
Malformed partial decryptions are detected by Chaum--Pedersen DLEQ
verification. Moreover, under
Eq.~\eqref{eq:p5-tda-check}, no aggregate plaintext is recovered unless at
least $t$ authorities each independently verify that the request carries a
valid authorization attestation bound to $(e_q,qid,h_{\mathcal S})$.
\end{theorem}
```

⚠️ **Do not overclaim the second sentence.** The attestation is signed by the
cloud, which is *malicious* in the threat model. So this stops an
honest-but-greedy user, not a cloud–user collusion. State the boundary:

```latex
\begin{remark}
The authorization attestation is produced by the cloud server. Consequently
Eq.~\eqref{eq:p5-tda-check} prevents an unauthorized user from obtaining an
aggregate over positions it did not derive from its own trapdoor, but does not
protect against a cloud server that colludes with a user to issue a false
attestation. Achieving the latter requires the authorities to verify the ABSE
query token directly, which we leave as future work.
\end{remark}
```

---

# Theorem 6 — Verifiable Aggregation Correctness ⚠️

**This theorem currently proves the wrong statement.** It establishes that the
returned aggregate is correct *with respect to the presented `\mathcal S_Q`* —
which is exactly the property R3-1 shows is insufficient.

Split into two claims.

```latex
\begin{theorem}[Aggregation Correctness]
If the aggregation multi-proof $\pi_Q^{\mathrm{agg}}$ verifies against
$Root_{e_q}^{\mathrm{agg}}$ and the independent homomorphic recomputation
succeeds, then
\begin{equation}
CT_{\mathrm{sum}}=\!\!\sum_{i\in\mathcal S_Q}\!\!CT_v^{(i)},
\qquad
CT_{\mathrm{count}}=\!\!\sum_{i\in\mathcal S_Q}\!\!CT_1^{(i)},
\end{equation}
where each $(pos_i,rid_i)$ is unique. Omitted, inserted, duplicated, or
substituted aggregation entries are detected except with negligible
probability, under collision resistance of $H$.
\end{theorem}

\begin{theorem}[Aggregation Authorization]
Under Eqs.~\eqref{eq:p4-selection-check}, \eqref{eq:policy-containment} and
\eqref{eq:p5-tda-check}, any position set $\mathcal S_Q$ accepted for
aggregation satisfies
$\mathcal S_Q\subseteq\mathsf{Supp}(B_Q)$, where $B_Q$ is the conjunctive
bitmap induced by the requesting user's own policy-authorized trapdoor
$T_Q$. Consequently no user obtains an aggregate over records outside the
result set of a query its attributes authorize.
\end{theorem}
```

The second theorem is new and is the direct answer to R3-1, R3-2, R3-3. It
must be proved, not merely asserted — the proof is short:

```latex
\begin{proof}[Proof sketch]
By Eq.~\eqref{eq:p4-selection-check} the cloud rejects any
$\mathcal S_Q\not\subseteq\mathsf{Supp}(\widehat B_Q)$, and $\widehat B_Q$ is
computed from exactly those canonical nodes for which the user's tokens
satisfied $\mathsf{ABSE.Test}$---hence from nodes whose policies its
attributes satisfy. By Eq.~\eqref{eq:policy-containment}, every record at a
position of such a node has a policy implied by that node's policy. Finally,
Eq.~\eqref{eq:p5-tda-check} ensures no plaintext is released without $t$
authorities verifying the attestation binding $\mathcal S_Q$ to $qid$.
\end{proof}
```

---

# Theorem 7 — Query-State Integrity, Freshness, Rollback Resistance

**Change forced by F6.** Qualify completeness in the statement itself, not
only in surrounding prose.

Replace the completeness clause with:

```latex
\emph{Completeness relative to the gateway-committed state:} if the cloud
omits any canonical node in $\mathcal U_Q$, any bitmap block of a matched
node, or any aggregation entry indexed by $\mathcal S_Q$, verification fails
except with negligible probability. This guarantee is stated with respect to
the state committed by the Edge Gateway at epoch $e_q$; it does not extend to
canonical-node memberships fabricated by the gateway prior to anchoring
(Remark~\ref{rem:completeness-scope}).
```

---

# Checklist before resubmission

- [ ] Theorem 1 — adversary class excludes the gateway (F5)
- [ ] Theorem 2 — simulator argument written; `U_Q` leakage remark added
- [ ] Theorem 5 — authorization precondition + collusion boundary remark
- [ ] Theorem 6 — split into Correctness + Authorization; new proof written
- [ ] Theorem 7 — completeness qualified in the statement
- [ ] Leakage profile `\mathcal L_{\mathrm{BVCRSA}}` updated for F1's option (a2)
      — matched-node bitmap contents now visible to the cloud
- [ ] Every theorem's assumptions restated against the concrete ABSE of F4
- [ ] `\label{rem:completeness-scope}` added to the F6 remark and cross-referenced

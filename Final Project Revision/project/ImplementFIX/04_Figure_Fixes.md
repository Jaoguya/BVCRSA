# Figure Fixes

**Reviewer:** R1-C8 — *"Figures have low resolution, small labels, and limited
readability… All diagrams and plots should be regenerated as true vector
graphics… Raster screenshots should be avoided."*

---

# ⚠️ The document does not currently compile

Three figures are `\includegraphics`'d and **absent from the repository**:

| Missing file | Referenced at | Status |
|---|---|---|
| `modelAHE.pdf` | line 491 — Fig. 1, System Model | hand-drawn, never committed |
| `fig_combined_3panel.png` | line 2810 — trapdoor/query 3-panel | hand-composited from three separate plots |
| `bsgs_scalability.png` | line 3075 — Fig. 8, BSGS | **no script ever produced it** |

`\graphicspath{{all_figures/}}` — and that directory no longer exists either;
figures now live in `../Figures/`.

⚠️ `bsgs_scalability.png` is the serious one. Reviewer 6 credited
"aggregation-recovery scalability" as an added experiment, and Reviewer 4
called the expanded evaluation a strength. Both were endorsing a figure that
did not exist. Experiment 7 now generates it.

---

# Figure → producer map

After the rebuild, every figure has a script.

| Paper figure | File | Produced by |
|---|---|---|
| Fig. 1 — System Model | `fig01_system_model.svg` | ⚠️ hand-drawn — must be redrawn as vector |
| Fig. 2(a) — trapdoor vs `d` | `exp01_trapdoor_gen.svg` | Exp 1 |
| Fig. 2(b) — query vs range | `exp02_query_vs_range.svg` | Exp 2 |
| Fig. 2(c) — query vs `N` | `exp02_query_vs_N.svg` | Exp 2 |
| Fig. 3 — query vs `d` | `exp02_query_vs_d.svg` | Exp 2 |
| Fig. 4 — throughput | `exp03_query_throughput.svg` | Exp 3 |
| Fig. 5 — verification | `exp04_verification_overhead.svg` | Exp 4 |
| Fig. 6 — aggregation ablation | `exp05_homomorphic_aggregation.svg` | Exp 5 |
| Fig. 7 — aggregation strategy | `exp06_agg_strategy_comparison.svg` | Exp 6 |
| Fig. 8 — BSGS | `exp07_bsgs_scalability.svg` | Exp 7 |
| Fig. 9 — communication | `exp08_communication_cost.svg` | **new** — Exp 8 |
| Fig. 10 — sensor cost | `exp09_sensor_side_cost.svg` | **new** — Exp 9 |
| Fig. 11 — microbenchmarks | `exp10_primitive_microbench.svg` | **new** — Exp 10 |
| Fig. 12 — blockchain cost | `exp11_blockchain_cost.svg` | **new** — Exp 11 |

---

# Fix 1 — the 3-panel figure

`fig_combined_3panel.png` was assembled by hand from three plots, which is why
it was never reproducible. Two options:

**(a) Keep three separate figures.** Simplest; costs a little column space.
Exp 1 and Exp 2 already emit them individually.

**(b) Generate the composite in-script.** Add to Exp 2:

```python
def plot_combined(rows_exp1, rows_exp2):
    """Single 3-panel figure: trapdoor vs d, query vs range, query vs N."""
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    # (a) from exp01 CSV, (b)/(c) from this experiment's rows
    ...
    save_figure(fig, "fig_combined_3panel.svg", runs=RUNS)
```

⚠️ (b) requires Exp 2 to read `../../CSV/exp01_trapdoor_gen.csv`. Run Exp 1
first. **(a) is recommended** — a hand-composited figure was the reason this
one went missing.

---

# Fix 2 — the system model diagram

`modelAHE.pdf` must be redrawn as vector. There is no script and there should
not be one; it is an architecture diagram, not a plot.

Draw in Inkscape / draw.io / TikZ, export as **PDF or SVG**, place in
`../Figures/fig01_system_model.svg`.

Must show the seven entities of §III-A and the trust boundaries:

```
  IIoT Sensors ──packets──▶ Edge Gateway ──index+bitmaps+agg──▶ Cloud Server
       │                         │                                   │
       │                    epoch commits                       tokens/blocks
       │                         ▼                                   ▼
       │                    Blockchain ◀────verify────────────  Data User
       │                                                             │
  Trusted Authority ──keys──▶ (all, setup only)          partial decrypt
                                                                     ▼
                                                        Threshold Authorities
```

Mark on the diagram, because three reviewers attacked exactly these points:

- gateway holds `K_sel` — **single point of trust** (R7-C1)
- gateway is honest-but-curious; cloud is **malicious** (threat model)
- TA participates **only at setup**
- `t`-of-`n` threshold on the authorities

⚠️ Old raster candidates exist — `bvcrsa_system_model_v2.png`,
`fig1_system_model.png` — from the deleted `all_figures/`. If one is the
intended source, recover it from git and trace it as vector:
`git show HEAD:"Final Project Revision/project/all_figures/bvcrsa_system_model_v2.png" > model.png`

---

# Fix 3 — vector output, enforced

Already structural. `harness.save_figure()` refuses raster:

```python
if not filename.endswith(".svg"):
    raise ValueError(
        f"{filename!r}: reviewers require vector output (SVG/EPS/PDF). "
        "Raster screenshots were explicitly rejected — R1-C8.")
```

`harness.new_figure()` sets IEEE-legible defaults — 14 pt axis labels, 12 pt
ticks, 13 pt base — and `svg.fonttype: none` so text stays selectable text
rather than being converted to paths.

Both salvaged plot scripts (Exp 4, Exp 6) were repointed from `dpi=200/300`
PNG to SVG.

---

# Fix 4 — graphicspath and file naming

`\graphicspath{{all_figures/}}` points at a deleted directory. Update to
match wherever the Overleaf project keeps images, and switch every
`\includegraphics` to the `exp<NN>_` names above.

If Overleaf ingests the SVGs directly, they must be converted — Overleaf's
`pdflatex` does not accept SVG. Either:

```bash
# convert to vector PDF for Overleaf (still vector, satisfies R1-C8)
for f in Figures/*.svg; do
  inkscape "$f" --export-type=pdf --export-filename="${f%.svg}.pdf"
done
```

or use `svg` package with `--shell-escape`. **Vector PDF is the safer path**
— R1-C8 explicitly names "vector PDF" as acceptable.

---

# Fix 5 — error bars

Every plot function draws 95 % CI bars via `ax.errorbar(..., yerr=ci95)`,
answering R7-C4 and R2-C2. `save_figure(fig, name, runs=RUNS)` stamps
*"mean of N independent runs, 95 % CI"* onto the figure itself (R2-C8).

⚠️ If a CI is too small to render, say so in the caption rather than
silently omitting the bars — R2-C2's whole point is that "variance was
negligible" must be *shown*, not asserted.

---

# Checklist

- [ ] Redraw `fig01_system_model` as vector, with trust boundaries marked
- [ ] Decide: 3 separate panels (recommended) or scripted composite
- [ ] Run Exp 7 — produces the BSGS figure that never existed
- [ ] Run Exps 8–11 — four genuinely new figures
- [ ] Convert `Figures/*.svg` → vector PDF for Overleaf
- [ ] Update `\graphicspath` and every `\includegraphics` filename
- [ ] Confirm every caption states run count and statistic (F15)
- [ ] Confirm no PNG remains in the submission bundle

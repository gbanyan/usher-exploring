# Major revision: Phase 1–2 findings

Date: 6 October 2026. Phase 1 and Phase 2 are complete. Phase 3 specificity work,
Phase 4 manuscript/rebuttal editing, and Phase 5 submission packaging remain.
The production score, gate, manuscript, and original submission package were
preserved. This report interprets descriptive post-review analyses of the
recovered submission snapshot; it does not supply independent validation.

## Analysis inventory

The specification was committed as `282a087` before the new analyses ran. The
suite evaluates 39 configurations: production, equal weights, six single-layer
baselines, six leave-one-layer-out (LOO) configurations, 24 absolute weight
perturbations, and removal of the cerebellum proxy. It also evaluates 80
score/count/gate operating points without selecting a replacement.

Results use all 20,081 fixed production analysis labels and the same retained
Ensembl IDs across configurations. Production rankings contain 20,053 non-NULL
scores. Top-K sets break score ties by Ensembl ID; percentile ranks retain SQL
PERCENT_RANK tie semantics. Single-layer medians use that layer's observed
population, with coverage and denominators reported explicitly. Different
coverage and boundary ties limit direct comparisons between baselines.

## 1. Raw control recovery and final tiers

| Group | Expected | Raw median percentile | Raw top quartile | HIGH | MEDIUM | LOW/excluded |
|---|---:|---:|---:|---:|---:|---:|
| Established Usher | 9 | 97.77% | 9 | 2 | 7 | 0 |
| Selected SYSCILIA | 28 | 91.93% | 26 | 1 | 27 | 0 |

HIGH contains PCDH15, CDH23, and CEP290. All seven remaining Usher genes fail
the 0.70 score condition; WHRN and USH1G also fail the gate. All nine have five
or six observed evidence layers. Thus absence from HIGH is not explained by
the minimum-three-layer requirement. Failed conditions are recorded separately
in [control_tier_trace.tsv](results/control_tier_trace.tsv).

Only two Usher controls have observed aggregate localization scores, both zero;
the other seven have NULL localization. No Usher control enters HIGH through
the source-level direct-localization route. PCDH15 and CDH23 enter via the
animal-model route. This is a limitation of recorded localization coverage,
not evidence that Usher proteins lack the relevant biological localization.

At score ≥0.70 and ≥3 layers, the ungated list contains 94 genes, including
the same three positive controls and two housekeeping sentinels. The production
gate retains 62 genes and removes those two sentinels. This remains calibration
on previously inspected controls; it does not measure external specificity.

Keeping the production gate and ≥3 layers:

| Score threshold | List size | Usher retained | SYSCILIA retained | Housekeeping retained |
|---|---:|---:|---:|---:|
| 0.60 | 366 | 5 | 6 | 0 |
| 0.65 | 170 | 4 | 1 | 0 |
| 0.70 | 62 | 2 | 1 | 0 |
| 0.75 | 11 | 0 | 0 | 0 |
| 0.80 | 1 | 0 | 0 | 0 |

These operating points expose sensitivity/stringency tradeoffs; the study has
not chosen a new threshold from them. Full results are in
[threshold_sensitivity.tsv](results/threshold_sensitivity.tsv).

## 2. What the simple baselines show

| Scheme | Usher observed/expected | Usher median percentile | Usher top-100 | SYSCILIA top-100 | Housekeeping top-100 |
|---|---:|---:|---:|---:|---:|
| Default six layers | 9/9 | 97.77% | 2 | 1 | 2 |
| Equal weights | 9/9 | 98.29% | 3 | 1 | 2 |
| Animal-model only | 9/9 | 99.30% | 4 | 11 | 0 |
| Expression only | 9/9 | 72.38% | 0 | 0 | 0 |
| Localization only | 2/9 | 0.00% | 0 | 1 | 0 |

The localization-only median applies to its two observed Usher controls, not
all nine. Single-layer ranked populations differ: animal 19,125, expression
20,048, localization 13,089, versus default 20,053. Missing scores are not
converted to zeros. Top-K counts use the complete expected control roster as
their denominator, and score ties at list boundaries are reported.

Animal-model-only recovers more of these established controls in the top 100
than the integrated score. Removing animal evidence from the integrated score
leaves no positive control in its top 100. The new evidence does not support
claiming that six-layer integration outperforms its strongest component for
known-control recovery. The defensible contribution is transparent integration,
coverage, and inspectable tradeoffs; novel-gene performance remains unmeasured.

See [baseline_comparison.tsv](results/baseline_comparison.tsv) for all schemes,
coverage, expected-control recall, pairwise correlation populations, and ties.

## 3. Global rank similarity is not shortlist stability

Default versus equal weights has whole-universe Spearman 0.9952, but only 86
of their top-100 genes overlap (Jaccard 0.7544). Across equal weights plus the
24 modest perturbations, full-ranking correlations range 0.9598–0.9994,
while top-100 overlap ranges 59–97 and Jaccard 0.4184–0.9417.

Among the default top-K genes, the counts retained in every one of the 25
modest-weight configurations are 8/25, 17/50, and 41/100. Their median membership
counts are 24/25, 23/25, and 23/25, respectively. Thus several candidates are
stable under this finite family, while many boundary choices are configuration
dependent. These fractions are not statistical confidence or disease probabilities.

LOO is a separate stress-test family. Its full-ranking correlation range is
0.8867–0.9928, and top-100 overlap is 37–83. Neither these full-universe metrics
nor membership frequency replaces the original manuscript's conditional
Spearman on shared top-100 genes. The estimands must be labeled separately.

Per-gene frequencies, including original HIGH and control genes, are in
[candidate_membership_stability.tsv](results/candidate_membership_stability.tsv).

## 4. Evidence completeness and layer overlap

All 62 HIGH genes have five or six layers: 33 have five and 29 have six.
Increasing the minimum to four or five therefore preserves the entire existing
HIGH list. Restricting it to six retains 29 genes. This answers the concern
about three-layer HIGH genes for this snapshot; it is not a guarantee for
future data or parameter changes.

The raw score/evidence-count Spearman is +0.2402 across 20,053 scored labels.
There is no overall inverse completeness/score association in this snapshot.
Nevertheless, eight one-layer genes exceed the raw 0.70 threshold and enter
the raw top 100; all are classified LOW by the tier rules. The raw top 100
contains 60 HIGH, 32 MEDIUM, and eight LOW genes. Raw rank and HIGH are therefore
different outputs, and a high raw score alone is insufficient support.

The largest pairwise observed-score correlation is annotation/literature,
Spearman 0.3704 over 19,114 labels. Constraint/expression is 0.3417 and
constraint/literature 0.3341. Modest score correlations neither demonstrate
independent evidence nor rule out shared publications, curation, or study bias.
Pairwise observation counts and binary observation-indicator correlations are
reported in [layer_correlations.tsv](results/layer_correlations.tsv).

## 5. Cerebellum proxy and expression contribution

Expression scores were reproduced from all 20,116 stored source rows before
the proxy analysis. Removing cerebellum measurements recomputed source-specific
Tau, contrasts, target percentiles, and the expression layer; the retained IDs,
six weights, and gate remained fixed.

Whole-universe composite correlation is 0.9496, with median absolute movement
of 4.92 percentile points. HIGH changes from 62 to 60 genes, but only 37 are
shared: 25 are lost and 23 gained. A similar tier size therefore conceals
substantial membership change. Under this diagnostic configuration, USH2A and
MYO7A enter HIGH, CDH23 leaves, and PCDH15 remains. This is not a reason to
adopt proxy removal merely because more known Usher genes are retained.

Expression accounts for 15.5%–27.5% of the default composite in the nine Usher
controls. Its effect is heterogeneous: expression LOO lowers ADGRV1 by 3.15
percentile points but raises CLRN1 by 9.31 and USH1C by 7.82. A stronger target
expression claim cannot be inferred simply from including an expression layer.

The source audit distinguishes measurement types. In the 20,116-ID expression
table, quantitative HPA retina nTPM and GTEx retina TPM are entirely unavailable;
HPA retina protein levels are recorded for only 112 IDs. Census photoreceptor
values are recorded for 20,078 IDs, including measured zeros. Non-NULL coverage
does not imply positive expression or disease specificity. Production hair-cell
expression remains unavailable.

After proxy removal, two source rows still receive partial expression scores
from background-only Tau without an observed retinal target. This follows the
unchanged component-availability mean. It is explicitly flagged, not treated as
retinal support or fixed by inventing zero expression. These restricted-panel
statistics must be described more precisely during manuscript editing.

See [usher_expression_diagnostics.tsv](results/usher_expression_diagnostics.tsv)
and [per_gene_diagnostics.tsv](results/per_gene_diagnostics.tsv).

## Verification, reproduction, and phase boundary

Executed locally on macOS with Python 3.13.1, DuckDB 1.5.5, Polars 1.44.2;
NumPy/SciPy/Matplotlib versions are recorded in the results manifest.

```bash
rtk proxy .venv/bin/python scripts/revision_phase2.py \
  --output-dir data/cache/revision-phase2-repeat
rtk proxy .venv/bin/python -m pytest tests/ -q
```

Use a new output directory. The script refuses to overwrite a previous run.
Production scoring and source-expression reconstruction match at absolute
tolerance `1e-12`, and default tiers match all candidate/excluded labels. All
333 tests pass, with 17 existing warnings. Six new tests cover zero-weight NULL
coverage, ties, direct gate versus adjacent localization, proxy/Tau recalculation,
membership families, and undefined constant/empty correlations.
An additional independent read-only DuckDB SQL calculation matched all 1,900
control/scheme score cells across the 38 weight-based configurations at `1e-12`.

The DB, configuration, manuscript, candidate table, checksum manifest, and every
original submission file have unchanged hashes. Output hashes are recorded in
[manifest.json](results/manifest.json). The four-panel figure was visually
inspected after correcting a clipped count label:
[phase2_diagnostics.png](results/phase2_diagnostics.png).

Proceed to Phase 3 with a frozen unrelated-disease comparator protocol. Do not
choose a new weight/gate/proxy policy from improved control recovery. The next
decision requires specificity evidence and the limits of independent evaluation;
none of the Phase 2 results retroactively removes original calibration reuse.

# Major revision: Phase 1–2 analysis specification

Recorded on 6 October 2026 before executing the new analysis suite.
This is a post-review analysis plan, not a preregistration of the original study.

## Scope and fixed production baseline

The working target is genome-wide cilia-/sensory-aware hypothesis generation
for investigation in Usher syndrome. Recovery of general ciliary controls does
not establish Usher-specific prediction or novel disease-gene discovery.

Use the recovered submission database and preserve its bytes, the production
configuration, manuscript, and original submission artifacts. Open DuckDB
read-only. Use all 20,081 scored labels, including the 28 NULL composites and
1,694 excluded labels; ranking denominators exclude NULL scores. Check the DB
against the recovery record and candidate table before analysis.

Controls are the existing nine established Usher genes and 28 selected SYSCILIA
genes, reported separately. The thirteen existing housekeeping sentinels are
internal diagnostics. None of these sets provides independent evaluation after
its use in development. Do not fit weights, select thresholds, or redefine
controls to improve these results.

The fixed analysis unit is the retained Ensembl ID/label in `scored_genes`.
Weight comparisons hold this mapping fixed instead of selecting new duplicate-ID
representatives. Scores use the existing six normalized evidence values.

## Ranking and coverage

- NULL-aware mean: sum of observed score × weight divided by observed positive
  weight. A zero-weight layer supplies neither score nor denominator. If no
  weighted layer is observed, the scheme score is NULL.
- Whole-universe Spearman: pairwise non-NULL scores, with paired count recorded.
- Percentile: SQL PERCENT_RANK semantics, `(minimum ascending rank - 1)/(N - 1)`;
  zero for N=1, NULL for unranked genes. Equal scores share percentile.
- Exact top 25/50/100 lists: descending score, then ascending Ensembl ID. Report
  boundary ties, actual ranked population, intersection count, and Jaccard.
- Control recovery: scored/expected coverage, median percentile, top-quartile
  count, recall at top 10% and exact top 25/50/100. Unranked controls count as
  unrecovered in expected-control denominators. These are descriptive metrics.
- Keep raw ranking and final priority tiers separate. Record both original
  evidence count and active-weight evidence coverage where appropriate.

## Baselines and weight sensitivity

Compare default weights, equal weights, six individual layers, six
leave-one-layer-out (LOO) scores, and the existing 24 absolute one-weight
perturbations (±0.05/±0.10, followed by normalization of all six weights).

For each scheme, report coverage, whole-universe rank correlation, exact top-K
overlap, and separate control recovery. Single layers are diagnostic baselines;
they are not equivalent biological targets or production tiers.

Report per-gene top-K membership frequency in two explicitly separate families:
(1) equal weights plus 24 perturbations (25 configurations), and (2) six LOO
configurations. Default membership is reported separately. These frequencies
describe a finite chosen family; they are not probabilities of disease relevance.
Include all baseline HIGH/control genes and every gene entering any tested top
100. Do not combine single-layer extremes into the modest-weight family.

## Production tier trace and threshold sensitivity

Use source-level direct localization fields, not merely a positive aggregate
localization score. The production animal route is Q75 over positive animal
scores in all scored labels, using Polars' production quantile convention.
Keep this Q75 fixed in comparisons.

Trace each positive control through score ≥0.70, observed layers ≥3, direct
localization, animal-model Q75, combined gate, and final tier. List every failed
condition rather than attributing every loss to the last filter.

Evaluate the Cartesian grid of score thresholds 0.60/0.65/0.70/0.75/0.80,
minimum observed layers 3/4/5/6, and four gates: production OR, direct-only,
animal-Q75-only, and no gate. Report shortlist sizes and separate Usher,
SYSCILIA, and housekeeping counts. Do not select a new operating point.

## Missing evidence and overlapping layers

Report observed-count strata 0–6: population, non-NULL score count, median/IQR
score, raw ≥0.70 count, and production HIGH count. Report raw-score versus
evidence-count Spearman with N and HIGH composition by evidence count.

For each pair of evidence layers, compute Spearman on pairwise observed values
(zero is observed), recording N and missingness. Also report correlation of
binary observation indicators, with zero-variance pairs undefined. These
descriptive associations do not establish independence or double counting.

## Expression and cerebellum proxy

First reproduce the expression scores from the stored source-specific columns
and verify them against production. Then remove all cerebellum measurements,
recompute source-specific restricted-panel Tau, enrichment, target percentiles,
and expression scores using the same functions, and replace only the expression
layer in a diagnostic composite. Keep retained IDs, weights, and gate fixed.
Record source/target availability; no target feature must remain genuinely
unavailable rather than being interpreted as negative biological evidence.

Report genome-wide rank/coverage shifts, top-K overlap, HIGH membership changes,
and Usher control score/rank changes. For each Usher control, report expression's
weighted share of the raw composite, expression-LOO effects, and proxy-removal
effects. This is sensitivity analysis, not adoption of a new production score.

## Phase 3 boundary: specificity and independent evidence

Phase 2 does not add or evaluate new negative controls. Before inspecting ranks
of a new set, Phase 3 must record a versioned gene–disease curation source,
mapping rules, inclusion evidence strength, exclusions for auditory/retinal/
ciliary involvement, ambiguous-case handling, and matching rules. Match
publication burden and annotation density only; do not match on gate outputs
or sensory phenotype/localization scores. Freeze the roster before ranking.
Genes are operational unrelated-disease comparators, not proven true negatives.
Feasibility and eligible sample size may require a documented plan amendment
before any outcome analysis, rather than an invented sample target.

Historical-cutoff validation is feasible only if input evidence can be restricted
to the cutoff. A later disease association alone is insufficient. New controls
will not retroactively erase original calibration reuse.

## Deliverables and phase completion

Phase 1: this specification, reviewer crosswalk, and hashed input manifest.
Phase 2: reusable read-only script, TSV summaries/diagnostics, scientific plots,
machine-readable results manifest, and an English interpretation report.
Record environment and local execution commands. Verify unchanged DB/config/
submission hashes, baseline scores and tiers, and meaningful unit tests for
NULL scoring, tie handling, gate logic, and proxy-removal recalculation.

Complete Phase 2 when all planned comparisons are available, or explicitly
mark a source-driven unavailable comparison with its cause. Do not modify the
manuscript, weights, production gate, or adopt a new proxy policy in this phase.

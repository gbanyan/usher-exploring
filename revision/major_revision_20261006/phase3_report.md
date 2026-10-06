# Phase 3: disease comparator specificity and independent-evidence limits

Completed locally on 6 October 2026 against the recovered submission database.
The production configuration, database, manuscript and submission files remain
unchanged. The new comparator analysis supplies a descriptive specificity check;
it does not validate novel disease-gene prediction or establish clinical accuracy.

## Selection before outcomes

The [specification](phase3_spec.md) was committed at `0ae2c3d`, before outcome
access. The roster, matching script, source hashes and matching diagnostics were
then committed at `61abb61`, also before outcome access. The outcome script checks
that the frozen roster bytes are committed in HEAD before reading score fields.
The roster script reads retained IDs/labels and raw publication/GO counts only;
it does not read scores, ranks, gate fields or tiers.

Sources were the [ClinGen expert-curated validity export](https://search.clinicalgenome.org/kb/downloads)
(file date 2026-10-06), the [official HGNC complete-set export](https://hgnc.genenames.org/download/),
and [HPO release v2026-09-01](https://github.com/obophenotype/human-phenotype-ontology/releases/tag/v2026-09-01).
The two live exports are frozen by byte hashes, rather than inferred release
versions. URLs, hashes, sizes and download-completion times from file metadata
are in [the roster manifest](phase3_roster/manifest.json). Raw snapshots remain
in ignored `data/cache/phase3-sources-20261006/`; the local frozen caches are
required for exact replay of the live exports. A future live download may differ.

Require Strong/Definitive disease validity, exact unambiguous HGNC-to-retained
Ensembl mapping, an unambiguous Entrez cross-reference and HPO annotations.
Exclude original controls, auditory/retinal/ciliary assertion or panel names,
and the prespecified hearing, eye, motile-cilium, mucociliary and situs branches.
The [audit](phase3_roster/eligibility_audit.tsv) covers 3,056 ClinGen genes and
retains 420 operational unrelated-disease comparators. Exclusion reasons overlap:
2,149 genes have excluded HPO terms, 887 lack Strong/Definitive assertions,
467 match excluded assertion/panel names, 210 lack HPO annotations, 41 are original
controls, and 38 are outside the retained production mapping. These counts must
not be added as disjoint categories.

Of 420 eligible genes, 418 have both raw matching covariates. NULL covariates
were not replaced by zero. Matching uses log1p total gene-linked PubMed counts and
GO term counts, scaled by their SD in the combined complete comparator/positive
population. The fixed caliper is 0.75 SD in EACH coordinate. Maximum-cardinality,
minimum-distance assignment matched three distinct genes to every positive
control: 27 comparators for nine Usher controls and 84 for 28 SYSCILIA controls,
with no comparator reused. All 37 controls have complete matching covariates.
The maximum absolute coordinate difference among pairs is 0.70945 SD.

| Group | Feature | Mean difference before matching (SD) | After matching (SD) |
|---|---|---:|---:|
| Usher | log1p publication count | −0.4119 | 0.0093 |
| Usher | log1p GO count | 0.3073 | 0.0105 |
| SYSCILIA | log1p publication count | −0.7932 | −0.0412 |
| SYSCILIA | log1p GO count | −0.2619 | 0.0385 |

After-matching differences give each matched control equal weight and average
its three comparators first. This controls these two measured aspects of research
intensity; it does not balance genetic constraint, complete annotation content,
phenotypes, expression, all layer coverage, or unmeasured research bias.

## Default raw ranking and final tiers

Every comparator and positive control has a non-NULL default composite. The
ranking denominator is 20,053. Percentiles use the Phase 2 minimum-rank tie policy;
exact top-K lists break ties by retained Ensembl ID.

| Group | N | Median percentile | Top quartile | Raw top100 | Score ≥0.70 and ≥3 layers | HIGH |
|---|---:|---:|---:|---:|---:|---:|
| Usher controls | 9 | 97.77 | 9 | 2 | 2 | 2 |
| Matched to Usher | 27 | 64.21 | 11 | 0 | 0 | 0 |
| SYSCILIA controls | 28 | 91.93 | 26 | 1 | 1 | 1 |
| Matched to SYSCILIA | 84 | 60.30 | 24 | 1 | 1 | 0 |
| Full comparator pool | 420 | 66.16 | 151 | 6 | 6 | 3 |
| Original housekeeping sentinels | 13 | 94.82 | 11 | 2 | 2 | 0 |

Usher controls outrank their individual matches in 24/27 comparisons (88.89%);
SYSCILIA controls do so in 72/84 (85.71%). No pair is unranked. Equally weighting
controls after averaging each control's matches gives mean default percentile
advantages of 31.16 and 29.96 percentile points, respectively. These are
descriptive matched concordances, not cross-validated AUCs.

The full pool has 3 HIGH, 292 MEDIUM, 124 LOW and 1 EXCLUDED genes. The 27
Usher-matched genes have 17 MEDIUM and 10 LOW; the 84 SYSCILIA-matched genes have
54 MEDIUM, 29 LOW and 1 EXCLUDED. GRIA2 is the one matched gene with raw score
≥0.70; it fails both gate routes and remains MEDIUM. Only 2/27 and 6/84 matched
genes pass the gate at any score, compared with 7/9 and 28/28 original positives.

The zero HIGH count among the 111 matches cannot be attributed entirely to the
gate: 110 already fail the raw 0.70 threshold. In the broader pool, the gate reduces
the six score/count-qualified genes to three. Neither 0/111 nor 3/420 is a clinical
false-positive rate or proof of complete specificity.

## Simpler scores and the source of separation

| Raw ranking | Usher median percentile | Its matched group | SYSCILIA median percentile | Its matched group |
|---|---:|---:|---:|---:|
| Default | 97.77 | 64.21 | 91.93 | 60.30 |
| Equal weights | 98.29 | 65.48 | 94.15 | 60.34 |
| Constraint only | 56.02 | 66.91 | 49.91 | 59.44 |
| Expression only | 72.38 | 49.75 | 59.28 | 55.76 |
| Annotation only | 82.74 | 82.74 | 73.55 | 70.64 |
| Localization only | 0.00 | 0.00 | 91.17 | 0.00 |
| Animal model only | 99.30 | 0.00 | 97.90 | 0.00 |
| Literature only | 99.13 | 50.40 | 99.78 | 49.87 |

Single-layer medians use observed genes only; zero is an observed value, not a
substitute for NULL. In particular, localization is observed for only two Usher
controls, both zero. Denominators and group coverage for all eight schemes are
in [the summary table](phase3_results/comparator_summary.tsv); different ranking
universes preclude treating the percentile differences as identical experiments.

Constraint does not separate these positives from their matches; annotation-only
Usher medians are identical after matching. Animal-model and contextual-literature
scores show substantial separation. This is compatible with disease-focused
evidence contributing information beyond publication and GO counts. However,
the comparator exclusions intentionally remove known human sensory/ciliary
phenotypes, and production animal/literature layers encode closely related
biology. Shared knowledge and ascertainment therefore remain plausible sources
of separation. The composite has not been shown to outperform all single-layer
scores, nor to discover genes lacking already annotated sensory characteristics.

## Residual biological overlap: preserve the frozen pool

Three eligible-pool genes remain HIGH: CRB2 (0.70394, animal route), ATP1A1
(0.78882, animal route), and DYNC1H1 (0.80010, both direct and animal routes).
Their ClinGen assertions concern focal segmental glomerulosclerosis or motor
neuropathy. Their presence illustrates why curated human disease labels and HPO
screening do not prove absence of sensory function.

A post-outcome literature check found established experimental sensory biology
for all three: [CRB2 rod-photoreceptor loss produces retinal degeneration](https://pmc.ncbi.nlm.nih.gov/articles/PMC6747345/),
[conditional DYNC1H1 deletion disrupts photoreceptors and retinal lamination](https://pmc.ncbi.nlm.nih.gov/articles/PMC7951903/),
and [ATP1A1 participates in the cochlear blood-labyrinth barrier](https://pmc.ncbi.nlm.nih.gov/articles/PMC3031570/).
These studies predate this revision. They explain residual overlap rather than
validate new Usher associations; production animal/literature evidence may already
reflect this knowledge. None was removed after seeing results. The post-outcome
check is not a systematic biological adjudication of all 420 genes, so the
remaining pool cannot be promoted to a verified negative set.

## Independent and temporal validation feasibility

**Subsequent extension:** the paragraphs below record the original local-cache
audit. External archives have since been investigated and a restricted historical
case series executed; see [the temporal extension report](temporal_extension/report.md).
Several historical sources are available. The restricted reconstruction gives
mixed results and does not validate the complete production score or HIGH gate.

No independent novel Usher-gene validation was performed. The new comparator
roster was not used in the original production calibration, but the positive
controls and calibrated gate remain reused. Separating them from new comparators
does not erase that reuse or establish sensitivity to genuinely novel genes.
The mantis-ml comparison remains limited by 33/35 shared positives being seeds.

The [six-layer temporal audit](temporal_feasibility.tsv) records why the local
inputs do not support a defensible pre-association reconstruction. Annotation
and animal phenotypes are derived donor fields without complete dated historical
raw evidence. Cached gene2pubmed rows contain tax_id/GeneID/PubMed_ID only; the
context JSON contains PMID sets rather than publication dates. Modern expression,
constraint and localization snapshots likewise do not establish all necessary
cutoff-specific evidence. A newly dated ClinGen curation is not necessarily a
new biological discovery. No historical cutoff, held-out gene set or temporal
performance number has been invented. Obtaining and reconstructing historical
sources would be a separate study, not a relabelling of these results.

## Validation and Phase 4 disposition

Executed locally with `.venv` Python 3.13.1, using the analysis environment recorded
in the manifests. Full regression suite: **338 passed**, 17 existing warnings.
Five new tests cover transitive HPO/alternative-ID handling, ambiguous mappings,
global maximum-cardinality matching, per-coordinate calipers/no replacement,
and tied/NULL pair concordance. An independent read-only DuckDB window query
verified all 420 default scores and percentiles to absolute tolerance 1e-12.
All Phase 2 protected hashes remain identical. The exported figure was visually
inspected. A first test command accidentally selected global Python, which lacked
the project dependencies; validation was rerun with the recorded `.venv` interpreter.

Reproduction commands (use NEW output directories for reruns):

```sh
rtk proxy .venv/bin/python scripts/revision_phase3_roster.py
rtk proxy .venv/bin/python scripts/revision_phase3_outcomes.py
rtk proxy .venv/bin/python -m pytest -q
```

The default directories already contain preserved outputs. For replay, pass
`--output-dir` to each script; the outcome script must point `--roster-dir` to a
roster whose exact bytes have been committed. Preserve the raw source cache and
check its recorded hashes. Production data are always opened read-only.

Proceed to Phase 4 with the original production ranking as the reported baseline,
not a model optimized against these comparators. Describe predefined weights as
heuristic and report simpler baselines and finite-family candidate stability.
Define HIGH as a calibrated heuristic priority tier, present Usher/SYSCILIA
separately, add the matched-comparator results with residual-overlap caveats,
and explicitly state absence of novel-gene/temporal validation. Incorporate the
Phase 2 missingness and expression/proxy sensitivity results. The large proxy
effect requires a direct response to the reviewer; it has not been resolved by
this specificity analysis. Preserve essential biological background and add the
requested supporting reference before considering optional shortening.

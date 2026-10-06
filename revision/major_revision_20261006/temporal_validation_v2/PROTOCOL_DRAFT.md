# Expanded temporal validation protocol — pre-outcome draft

Status: source acquisition and cohort adjudication are underway. No v2 ranking
has been calculated or inspected. Freeze the final protocol and adjudicated
roster in Git before generating v2 outcomes. This study is separate from the
unchanged four-layer pilot. Its three cases have known pilot ranks and must be
reported separately from newly ascertained cases.

## Question and temporal boundary

Can a historical analogue of the six evidence families rank genes whose first
human Usher/ciliopathy/sensory disease association was reported after
31 December 2020? Evaluate ranking and heuristic HIGH recovery separately.
This is a retrospective temporal stress test, not a prospectively developed
predictor or validation of clinical disease probability. The production design
and control-calibrated gate were developed after 2020. Reconstructing older
inputs does not make those design choices historically prospective.

Sources may precede the cutoff by differing intervals. Record their actual
dates; do not imply complete evidence through the cutoff. Test reports may be
published from 1 January 2021 through the acquisition date, 6 October 2026.
Use the earliest verified public human-association report, including online
publication and preprints, rather than issue year or panel curation date.

## Independent case ascertainment

Systematically screen the acquired complete RetNet catalog and PanelApp panels
307 (retinal), 126 (hearing), 543, 724, 722, 178, 150, 725, 550 and 726
(ciliopathy domains). Save source versions, full responses, URLs and hashes.
RetNet mapping/cloning dates and panel reference dates nominate records for
adjudication; they are not sufficient proof of first human association.

Review source references and search pre-cutoff human disease reports for each
candidate using official symbol, historical symbol/aliases and disease domain.
Preserve all screened records and exclusions, including unresolvable dates,
non-protein-coding genes and absent historical identifiers. Never remove a case
because its score, coverage or rank is poor. Use frozen HGNC IDs to resolve
renamed genes; do not map historical evidence by a guessed animal symbol.

Adjudicate mutually exclusively before ranking into: (a) first association with
any human disease, also involving a target disease domain; (b) first target-domain
association, with an earlier established non-target human disease; (c) an already
established target-domain gene with a later phenotype expansion; (d) an earlier
target association without an eligible new phenotype; (e) insufficient or unresolved
human evidence. The main novelty cohort combines (a)/(b), reports both separately,
and does not describe (b) as genuinely first human disease-gene discovery. Group
(c) is a separate phenotype-expansion analysis and is not mixed into novel-gene
recall. Groups (d)/(e) are excluded/descriptive records with explicit reasons.
Mark whether the report claims a ciliary mechanism,
combined hearing/retinal phenotype, or broader sensory disease. Mechanism
classification uses independent disease reports, not predictor localization or
animal score. Broad sensory cases are a prespecified comparison stratum and
must not be represented as new Usher genes.

Use the same clinical rubric across all sources. The main clinical cohort requires
human genotype/phenotype evidence in at least two unrelated families, consistent
inheritance/segregation, and either supporting functional evidence or an independent
replication report. Candidate reports and single-family evidence remain a separate
exploratory cohort, even when currently rated green. A RetNet-only or amber case
meeting the rubric can enter the main clinical cohort. Current PanelApp status is
supporting curation, not proof of novelty, mechanism or clinical strength. Document
the actual relevant phenotype for multi-domain genes and separate strong evidence
for another phenotype from evidence for the target association.

Exclude all original nine Usher and 28 SYSCILIA development controls from the
novel-case test set. Show their recovery only as development/reference biology.
The pilot cases CEP162, CFAP20 and LRRC45 are previously inspected references,
regardless of their eligibility in the expanded catalog. No resampling of these
cases creates an independent validation cohort.

Catalog ascertainment may miss uncurated or disputed associations. Report this
limitation and the case denominator explicitly. Do not call this exhaustive
discovery of every post-2020 disease gene. An absent test case in the historical
universe is an out-of-scope prediction and remains in the attrition table.

## Historical universe and source contract

Use the pilot's archived HGNC 1 October 2020 Approved protein-coding genes with
unique nonempty Ensembl identifiers (19,167). Never join production scores into
the reconstruction. Preserve production DB, configuration, baseline tables,
manuscript and pilot result hashes during numerical runs.

1. Constraint: gnomAD v2.1.1 LOEUF, existing complete archive. Same min-max
   inverse transform as the pilot over the historical universe.
2. Expression: HPA v20 accepted ordinal protein observations and archived GTEx
   v8 median TPM for the existing retina/cerebellum/testis/fallopian panel.
   Compute quantitative Tau within GTEx, and use the existing source-separated
   expression transform. GTEx has no retina or hair cells. Downloaded HPA v20
   `rna_tissue_hpa.tsv` has neither retina nor cerebellum: its background-only
   TPM values cannot supply a target/background contrast or target-relevant Tau
   and are excluded from this variant. They are not mislabeled as nTPM. Census
   and hair-cell channels remain unavailable historically. Do not import 2023+
   Census or undated single-cell matrices.
3. Annotation: GO GAF 8 December 2020, unique positive GO terms, exclude NOT,
   mapped using archived HGNC UniProt accessions and unambiguous historical
   symbol fallback. Same production annotation formula with unavailable
   UniProt annotation-score and pathway subcomponents zero, not family-level
   weight redistribution. All unobserved annotation components remain NULL at
   family level. This partial annotation family is explicitly disclosed.
4. Localization: HPA v20 subcellular observations only, production classification
   and reliability priorities. Do not import undated compendia. Observed
   non-ciliary localization is zero; absent source observation is NULL.
5. Animal: native archived MGI human-mouse links/phenotype report 2 February
   2020, MP vocabulary 29 January 2019 supplemented only by historical IMPC
   release11 MP names, and ZFIN archive 30 December 2020. Use the 30 December
   archive to avoid the 31 December file's 1 January 2021 modification boundary.
   Resolve human IDs through historical Entrez/HGNC IDs. Union phenotype terms
   across all native curated orthologs per human gene; deduplicate mouse terms
   across MGI/IMPC. Retain abnormal ZFIN annotations and existing sensory/cilia
   keyword rules. Do not introduce a p-value filter absent from production.
   Unknown MP labels remain unresolved and are audited. If at least one sensory
   term is recognized, score the recognized positives and record incomplete
   count coverage. If no positive is recognized but at least one term cannot be
   resolved, that animal channel is NULL rather than zero. An observed, fully
   interpretable channel with no relevant terms is zero. Combine only known
   channel evidence; when neither channel is interpretable the family is NULL.
   ZFIN uses the archive's documented 25-column structure: native gene ID at
   column3, abnormal tag at column12, and term-name fields 5/9/14/18/11 (1-based).
   Deduplicate native gene-ID/structure-ID/concatenated-term-name tuples before
   human-ortholog union. Do not count duplicate publication/figure rows separately.
   Audit compound/multigene symbols or gene IDs and exclude ambiguous assignments
   rather than treating every genetic-background gene as the causal perturbation.
   Historical HCOP support votes have not been recovered. Primary native-link
   variant uses unit ortholog weights, explicitly without claiming HCOP HIGH
   confidence. Score `(0.4*mouse_positive + 0.3*zfish_positive) *
   log2(total_sensory_terms+1)/log2(global_max+1)`. Mapped genes without matching
   terms receive zero source evidence; genes without an identifiable ortholog
   receive NULL. Report uniform 0.7 and 0.4 scale sensitivity variants, plus
   leave-animal-out. Record every ortholog count and add a unique-native-link
   sensitivity that removes channels with multiple linked animal orthologs;
   do not choose an ortholog by its phenotype score. Global scaling alone cannot
   establish robustness to ortholog choice. This analogue differs from production's selected
   single HCOP ortholog and vote-dependent weighting.
6. Literature: complete 29 June 2020 gene2pubmed archived human associations,
   47,311,419 gzip bytes, validated assembled ranges and gzip CRC/end-of-stream.
   Use only historical human Entrez mapping and unique PMID sets. Context queries
   are fixed in `literature_queries.json`, title/abstract only, with both first
   publication and first indexing dates bounded by 31 December 2020. Retrieve
   every result with cursor pagination, validate unique IDs against hit counts,
   preserve responses and hashes. No present-day MeSH annotations are used.
   Use production context weights, quality precedence and positive percentile
   normalization. Direct experimental evidence requires a same-PMID context
   intersection. An HGNC gene with an archived Entrez ID but no linked PMID has
   zero evidence in this source with score explicitly set to zero before any
   `log2(total+1)` division, not a claim of no publications anywhere. The denominator
   is the full unique human gene2pubmed-linked PMID count for that gene, including
   links without date/context metadata; only matching dated PMIDs contribute to
   context/quality counts. Audit linked PMIDs absent from query metadata and do
   not interpret them as verified lack of biological context. Missing
   Entrez mapping gives NULL. Present-day title/abstract revisions are not a
   historical text snapshot: this family has residual temporal uncertainty.

Freeze the verified source manifest before computing scores. Do not replace
sources, cutoff, mappings or keywords based on case performance. The fully
archived family subset omits literature; the six-family analogue includes the
date-bounded text-query family. Neither is an exact replica of all modern
production subchannels. Preserve that distinction in manuscript and rebuttal.

## Frozen scoring and evaluation family

Co-primary historical versions are (i) the fully archived five-family version
without literature and (ii) the six-family augmented analogue with date-bounded
modern-text matches. Both are reported regardless of performance. The latter uses
weights 0.20 constraint, 0.20 expression,
0.15 annotation, 0.15 localization, 0.15 animal and 0.15 literature. Renormalize
over observed family scores per gene, keeping observed zero in the denominator.
Use deterministic descending-score/ascending-Ensembl sorting. The primary endpoint
is top100 gene recovery in the clinically supported (a)/(b) novelty cohort for
each co-primary version. Deduplicate genes by historical HGNC ID; a gene appearing
in several panels/domains contributes once to overall recall. Disease-domain
strata can overlap and are labeled as such. Report tied average percentiles as
`100*(average ascending score rank-1)/(N_scored-1)` (single scored gene: zero),
minimum-rank percentiles for continuity with the pilot, and descending tie ranges.
Primary topK uses deterministic gene-ID tie-breaking; tie-inclusive and strictly
above-boundary recovery are sensitivities. Percent recovery cutoffs use
`ceil(p*N_scored)` deterministic ranks and the same boundary-tie sensitivities.

Report all of: default; equal weights; each single family; each leave-one-family
out; joint animal/literature omission; fully archived no-literature variant;
animal uniform-weight and unique-native-link variants; available-GO renormalization
(GO subscore divided by 0.5) as a named annotation-scale sensitivity. Retain all cases in every comparison, and
report missing scores explicitly. Do not select the favorable scheme as final.

For each clinical/mechanism/novelty stratum and the pilot references, report
per-gene components, coverage, percentiles, tie ranges, top25/50/100/500/1000 and
top1/5/10 percent recovery. Report complete cohort counts and uncertainty for
small strata. The main rank-recovery denominator includes all clinically eligible
genes in the historical universe, including NULL-score genes counted as not
recovered. Also report the total eligible clinical cohort, scored subset and
end-to-end recovery over every eligible gene including universe exclusions.
Compare all schemes on the same historical universe and cases;
report rank correlations and topK overlap on shared scored IDs. No fitted
weights or threshold optimization are allowed.

Evaluate historical HIGH separately: score >=0.7, production >=3 observed families,
and historical direct HPA cilia/centrosome/basal-body/transition-zone/stereocilia
signal OR animal >= historical positive-score Q75. Calculate Q75 from the full
historical universe without using test labels, with nearest interpolation matching
the production Polars quantile default. Recompute Q75 within each animal source
variant; uniform scaling is expected to preserve the Q75 gate. Add a named
stricter-count >=4 sensitivity rather than silently changing production HIGH.
Also show the original fixed
animal threshold 0.12765713253595054 as a sensitivity, with its cross-version
scale limitation. Record each case's raw-score, count and gate failures.
Gate design remains development-control-calibrated. Independent later case
recovery cannot turn the HIGH tier into validated disease probability.

Do not treat unlabeled genome genes or the prior 111 matched comparators as
verified new clinical negatives. This study's positive-cohort recovery does not
estimate clinical false-positive rate, precision or specificity. Preserve the
earlier matched-specificity work separately. Report housekeeping/reference
behavior descriptively, clearly labeled as previously inspected controls.

## Validation and reporting

Verify archive sizes/hashes, source schemas, mapping ambiguity, NULL/zero
semantics, date exclusions, score bounds and deterministic output. Verify that
held-out association PMIDs are absent from historical literature links. Audit
date-boundary examples including TMEM218, DYNC2I2/WDR34 and NDUFAF5; their issue
dates must not override pre-cutoff online reports. Reproduce pilot components
for shared unchanged families. Provide executable reconstruction/evaluation
commands, locked environment reference, complete input/output hashes and case
adjudication provenance. Any post-outcome change is explicitly exploratory,
with original outputs preserved. Negative and mixed findings are retained.

Only update scientific claims after results and independent review. Final
submission packaging remains a later phase. The conservative Phase4 revision
and restricted pilot remain available as preserved context, regardless of v2
performance.

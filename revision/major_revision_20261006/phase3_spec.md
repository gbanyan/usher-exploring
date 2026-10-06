# Phase 3: unrelated-disease comparator specification

Recorded before comparator score/rank inspection on 6 October 2026. This is a
post-review specification, not an original-study preregistration. Production
scores, weights, retained IDs and the calibrated gate remain fixed.

## Sources and eligibility

Use the current ClinGen Gene-Disease Validity CSV from
https://search.clinicalgenome.org/kb/gene-validity/download (file date 2026-10-06),
HGNC complete-set TSV from its official public-download bucket, and HPO release
v2026-09-01 (`hp.obo`, `genes_to_phenotype.txt`). Cache raw downloads outside Git;
record URLs, byte hashes, retrieval timestamps, source dates and sizes. The
ClinGen CSV is a live export, frozen here by its hash, rather than a named release.
GenCC was considered but its download page returned HTTP 403; use ClinGen's
direct, expert-curated export consistently, without combining sources.

Require at least one ClinGen Strong or Definitive assertion. Map HGNC ID through
the official approved HGNC record to a single exact retained production Ensembl
ID; never resolve an ambiguous mapping using scores or a symbol fallback. Use
HGNC Entrez ID for HPO mapping. Require an unambiguous Entrez mapping and at least
one HPO annotation, to avoid treating absent phenotype information as absence
of sensory involvement. Exclude the original positive and housekeeping sets.

Exclude a gene if ANY of its ClinGen assertion labels or expert-panel names
(regardless of strength) matches the case-insensitive pattern
`usher|hearing|deaf|retin|amaurosis|ciliopath|ciliary|cilium|joubert|bardet|meckel|nephronophthis|alstrom|senior.loken`.
Also exclude if any HPO annotation is a descendant (including the root) of:

- HP:0000365, Hearing impairment;
- HP:0000478, Abnormality of the eye;
- HP:0005938, Abnormal respiratory motile cilium morphology;
- HP:0012261, Abnormal respiratory motile cilium physiology;
- HP:0031602, Abnormal mucociliary clearance;
- HP:0030853, Heterotaxy;
- HP:0011620, Abnormality of abdominal situs;
- HP:0011615, Abnormal pulmonary situs morphology;
- HP:0011538 / HP:0011539, atrial situs inversus / ambiguous.

Resolve HPO alternative IDs and traverse `is_a` ancestry. Broad eye and situs
exclusions deliberately remove some diseases outside Usher biology. They reduce
obvious contamination but do not establish that remaining genes lack ciliary
functions. Record every exclusion and source assertion; no manual rank-informed
additions/removals. These are operational comparators, not proven negatives.
Do not use production localization, animal phenotypes, gate membership or
sensory-context publication counts for selection.

## Matching and roster freeze

Before reading comparator outcomes, query only retained IDs/labels and raw
`total_pubmed_count` and `go_term_count`. NULL covariates are not zero: report
missingness and restrict matching to genes with both observed. Use log1p counts,
standardized by the population SD of the combined eligible comparator pool and
the 37 original positive controls with complete covariates. Require each
coordinate difference <= 0.75 SD. Match up to three distinct comparators per
control jointly across the two positive groups, without replacement, using
minimum squared Euclidean distance with dummy unmatched slots. Penalize dummies
enough to prioritize maximum feasible cardinality; stable Ensembl ordering
resolves implementation ties. Record software version, unmatched controls,
coordinate differences, distances, and group-specific standardized mean
differences before/after matching. No outcome-dependent caliper relaxation.

Freeze the full eligible/excluded-gene audit and matched pairs with SHA256 hashes
in a Git checkpoint before outcome analysis. If sources or usable pool sizes
require different rules, amend this specification before any outcome access.

## Fixed outcome analyses and interpretation

For the full eligible pool and each matched group, report ranked coverage,
raw-score and genome-wide percentile median/IQR, exact top25/50/100 counts,
top-quartile counts, raw score >=0.70, score >=0.70 plus >=3 layers, gate passes,
and final HIGH/MEDIUM/LOW/EXCLUDED counts. Use the Phase 2 tie/NULL conventions.
Report default, equal-weight and six single-layer raw rankings, with actual
ranking denominators. Production tier metrics apply only to the default.

For each original control with matches, report its default percentile minus
each matched comparator percentile, and mean pairwise score concordance
(1/0.5/0 for greater/equal/less). Aggregate by averaging within each matched
control, then equally across controls; report Usher and SYSCILIA separately.
Report matched-control coverage so an unmatched control cannot silently vanish.
Do not interpret descriptive concordance as independent validation or estimate
a clinical false-positive rate from these selected, partially annotated genes.

Audit temporal-validation feasibility against the existing source manifest and
local caches. A new curation date alone does not date the underlying biological
association and cannot supply a held-out experiment. If all score layers cannot
be restricted to a pre-association cutoff, state that temporal validation was
not performed. Do not claim novel disease-gene prediction from comparator
separation, original control recovery, or mantis-ml seed overlap.

## Deliverables and next decision

Read-only source/roster and outcome scripts, frozen audit/pairs, matching
diagnostics, comparator summary and paired results, manifests and an English
Phase 3 report. Preserve and recheck Phase 2 protected-input hashes. Run focused
tests for ontology ancestry/alternative IDs, ambiguous mappings and caliper/
no-replacement matching, plus relevant regression tests locally. Manuscript
revision starts in Phase 4 after reporting these findings and the remaining
limits; Phase 3 does not adopt a new production model.

# Independent post-outcome review — 6 October 2026

## Conclusion

No critical numerical, source-mapping, missingness or denominator error was
identified in the successful frozen temporal run. The low recovery is
reproducible from the adopted inputs and transforms. It should be reported as
a negative/weak result for these historical analogues and this ascertained
later-case cohort, without changing the cohort, weights or thresholds to
improve it.

This review concerns the nine result TSVs and manifest produced under amended
freeze commit `53da295`, following original freeze `bd6bb2f`. The parent has
reported byte-identical independent clean replay and committed the results,
report and figure in `90f13d0`. The reviewer independently checked the nine
output hashes against the result manifest. Frozen inputs, evaluator code and
result files were not modified. This new document was created after outcomes
and is not represented as a pre-outcome decision.

## Confirmed outcomes and clinical denominator

The frozen principal cohort contains 45 unique HGNC keys. Exactly 41 are in
the historical protein-coding universe and all 41 receive a score under both
co-primary schemes. RNU4-2, RNU6-2, RNU6-8 and RNU6-9 are present in archived
HGNC as noncoding RNAs; their exclusion follows the frozen protein-coding
universe, not a failure to recognize their identifiers. They remain failures
in the 45-gene end-to-end denominator.

Archived HGNC mapping also preserves the renamed genes RSG1/CPLANE2,
SAXO6/MDM1 and KIAA1024L/MINAR2 through stable keys. No incorrect exclusion of
these renamed principal cases was found. Candidates, unresolved novelty,
phenotype expansion/maturation, development references and previously
inspected pilot cases remain separate from principal recovery.

| Endpoint | Five-layer archived analogue | Six-layer augmented analogue |
|---|---:|---:|
| Principal genes in universe and scored | 41/45 | 41/45 |
| Top 100 | 0/41; 0/45 end-to-end | 0/41; 0/45 end-to-end |
| Top 500 | 0/41 | 1/41 |
| Top 1,000 | 2/41 | 3/41 |
| Top 10% | 5/41 | 6/41 |
| HIGH | 0/41; 0/45 end-to-end | 0/41; 0/45 end-to-end |
| Median ascending percentile among 41 | 46.23 | 44.95 |
| Highest principal composite score | 0.5059867 | 0.5623070 |

All 41 in-universe principal genes have at least four observed positively
weighted families in both co-primary versions. None reaches composite score
0.7. Zero HIGH recovery therefore follows from the score threshold even
before considering the gate. One principal gene has direct HPA localization
and three pass the animal-Q75 route. Neither the count-four nor the fixed
production animal-threshold sensitivity changes principal HIGH recovery.

The whole historical universe contains 19,167 genes. Five layers score 19,157
and leave ten NULL; six layers score all 19,167. A mapped but unlinked
literature record can supply an observed zero for a gene otherwise lacking
all five families. This behavior follows the explicitly frozen source
contract; zero is not treated as positive support.

## Independent numerical checks

Checks ran locally with the installed `.venv`. They used read-only original
sources and result tables. The full reconstruction/evaluator was not rerun by
this reviewer; instead, separate reduction and arithmetic code was used to
avoid relying solely on the evaluator reproducing itself.

- **All 38,334 co-primary ranking rows:** independently recomputed weighted
  means from the 19,167-gene component matrix, observed-family counts,
  deterministic descending-score/ascending-Ensembl positions, statistical
  tie minima/maxima and ascending average percentiles. No discrepancies.
- **All 4,531 case-by-scheme rows:** independently recomputed weighted means
  and observed counts under their manifest weights, deterministic topK,
  tie-inclusive and whole-tie cutoff decisions, and percentage cutoffs. NULL
  and out-of-universe cases correctly fail recovery. All saved HIGH and
  count-four decisions agree with composite score, count and gate inputs.
- **All 37,950 recovery rows:** independently rebuilt clinical/status/domain/
  novelty/reference groups, the historical-universe, all-eligible and
  scored-only denominators, and recovered fractions. No discrepancies.
  Wilson limits agree with an independently expressed Wilson formula.
  For example, the upper 95% Wilson limit for 0/41 is approximately 8.57%;
  these are descriptive bounds within a nonrandom ascertained cohort.
- **Animal threshold:** independently selected the positive-score Q75 from
  sorted scores using the stated nearest rule: `0.13475306857428798`.
  Observed zero and missing scores are excluded from that threshold.
- **All 19,167 animal and literature component formulas:** independently
  recomputed scores from saved source counts. Missing channels, measured
  zero, log normalization and average-rank ties agree.
- **200 comparison rows covering 20 schemes:** independently reconstructed
  component-derived scheme vectors, average-rank correlations and full-list
  topK intersections/unions. No discrepancies. The three alternate-expression
  whole-universe comparison vectors were not independently reconstructed in
  this particular check; their case arithmetic was checked, and the parent
  reports byte-identical full replay for all schemes.

The five-versus-six Spearman correlation is approximately 0.870708 over
19,157 shared scored genes; their complete top-100 sets intersect in 57
genes. This is sensitivity to literature inclusion, not evidence that one
version is clinically superior.

## Independent raw-source checks

### Constraint, GO and localization

The constraint vector was independently reconstructed directly from archived
gnomAD LOEUF. Universe-wide bounds are 0.03 and 1.996. Every available or
missing constraint component matches.

The GO vector was independently reconstructed from the raw GAF, using archived
HGNC accession/symbol mapping, unambiguous mappings, unique positive terms
and exclusion of NOT annotations. The maximum unique term count is 180.
Every saved term count and the `0.5 * log2(count+1)/log2(max+1)` partial-GO
component matches. The maximum annotation-family score of 0.5 is a disclosed
consequence of missing other subchannels, not a coding accident.

HPA localization scores and direct-gate flags were independently reconstructed
from the original ZIP member, compartment text and reliability weights.
Every component and every reported case gate matches. No unrecognized
reliability category was found among the matching source rows. The resulting
universe has 212 direct-gate genes.

### Expression

Expression was independently reconstructed from accepted ordinal HPA protein
rows, original GTEx medians, and both original retinal matrices/labels.
GTEx has 56,200 distinct normalized keys, including 44 preserved `_PAR_Y`
keys; 19,074 canonical historical identifiers match. The technical amendment
prevents conflation of canonical and Y-pseudoautosomal records.

For retinal counts, this review used a COO coordinate reduction with
`bincount` over selected cells rather than the reconstruction's CSR submatrix
sum. Original labels select 9,356 and 847 photoreceptor cells. Mapping yields
15,133 and 14,530 genes by platform, and 15,496 in their pooled union. The
independent expression calculation applies positive-only source-specific
ranks, zero preservation, GTEx-only Tau, restricted within-source contrasts,
and redistribution across observed expression subcomponents.

All 19,167 expression components match, with maximum absolute discrepancy
`2.220446049250313e-16`, consistent with floating-point arithmetic. Thus the
poor co-primary recovery is not explained by an observed retinal summation,
identifier join, positive-percentile or expression-composite implementation
error.

### Animal and literature

Archived human/mouse and human/zebrafish mappings, MP vocabulary supplemented
by historical IMPC names, raw phenotype term unions and ZFIN abnormal records
were independently parsed. All 19,167 saved ortholog counts, relevant-term
counts and NULL decisions match. The maximum combined relevant term count is
53. The adopted corpus happened to yield no unresolved-label-only mouse
channels or positive mouse lower bounds; the code still preserves those
cases as specified if encountered.

Literature gene-to-PMID sets were independently rebuilt from the original
June 2020 archive and matched against all six frozen context sets. Every
gene's publication count and context intersection count agrees. Each context
set has the declared unique size, and the direct-experimental context set
is contained in the sensory/cilia union, as required for same-PMID context.
No cited postcutoff association PMID from the frozen clinical ledger appears
in a corresponding historical gene link.

These checks establish consistency with the acquired archive and frozen
keyword policy. They do not prove that every historical biological annotation
was available or that modern title/abstract text has never been revised.

## Missingness and interpretation

Among the 41 scored principal cases, constraint, expression and GO are all
observed and positive. Localization has ten NULL, 29 observed-zero and two
positive values. Animal evidence has 28 observed-zero and 13 positive values;
literature has 16 observed-zero and 25 positive values. A recorded zero in
these channels is absence of qualifying evidence under the adopted source
policy, not demonstrated biological absence.

The historical HIGH distribution is strongly affected by the partial source
scale: there are zero whole-universe HIGH genes in five layers and five in
six layers. A fixed modern threshold cannot be described as historically
calibrated merely because it was applied unchanged. The topK results avoid
that absolute-score interpretation but still show weak later-case recovery.

All 23 schemes have zero principal HIGH recovery. Two prespecified
sensitivity results do recover one principal gene at top 100: SAXO6 under
single localization (deterministic position 19, tie range 1–77), and PLCG1
under localization-weight omission (position 90 without a boundary tie).
The SAXO6 result survives the whole-tie top-100 criterion. Both should remain
reported as sensitivity outcomes, not substituted for the two co-primary
analyses. No superiority conclusion follows from selecting a favorable
scheme among these comparisons.

The reviewed outcome report appropriately separates first-target associations
with prior other-phenotype evidence from first-ever reported human causal
associations. It labels control recovery as previously inspected reference
biology, and retains the limitations of native ortholog links, partial GO,
raw-UMI retinal substitution, missing direct cochlear/developmental data and
modern-text literature queries. The standalone PNG figure was visually
inspected: the 41-case denominator and recovery numerators are legible and
agree with the tables.

Clinical ascertainment remains conditional on the adopted catalogs and
searches. The 895 unconfirmed or unnominated ledger entries are not verified
clinical negatives. This study neither establishes exhaustive discovery
coverage nor estimates clinical specificity, precision, penetrance,
false-positive rate or disease probability. The medians and small recovery
counts do not demonstrate broad prioritization of later disease genes;
they also do not establish a formal below-chance result or the performance
of an exact modern production replay.

The report's negative/weak conclusion is supported within these bounds. No
post-outcome repair to the scorer, cohort, source selection or thresholds is
recommended on the basis of this review.

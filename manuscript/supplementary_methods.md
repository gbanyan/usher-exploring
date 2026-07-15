# Supplementary Methods and Analyses

## S1. Optional post-hoc shortlist refinement

The production scoring and tiering procedure ends at the 83-gene HIGH tier. The analyses below are optional annotations evaluated within HIGH and do not alter composite scores, confidence tiers, or the six production evidence layers.

### S1.1 Tau tissue-specificity thresholds

Tau specificity was propagated from `tissue_expression` into the scored-gene output and evaluated at thresholds of 0.70, 0.75, 0.78, and 0.80 after production tier assignment. All 83 HIGH genes had non-NULL Tau. The resulting shortlist sizes were 80, 72, 62, and 54, respectively. Although 53 `tissue_expression` gene IDs had duplicate rows, none had more than one distinct non-NULL Tau value, so aggregation did not alter threshold assignment.

### S1.2 GSE135913 fetal cochlear data

Processed cluster-level matrices were downloaded from GEO series GSE135913 for human cochlea samples GSM4037819 (15 weeks), GSM4037820 (17 weeks), and GSM4037821 (23 weeks). SHA-256 checksums and source URLs are recorded in `gse135913_hair_cell_provenance.json`.

The matrices provide standardized CellFindR mean expression by cluster but do not include cell-type labels. Putative hair-cell clusters were therefore identified with a prespecified panel that excludes all Usher and SYSCILIA positive-control genes: *ATOH1, OTOF, POU4F3, GFI1, RBM24, LMO7, EPS8L2,* and *SLC17A8*. A sample was accepted only when at least four markers were represented, the highest aggregate marker mean was positive, and its margin over the next-ranked cluster was at least 0.5. The 15-week sample selected cluster 11 (8/8 markers; margin 4.735) and the 17-week sample selected cluster 10 (8/8; margin 5.221). The 23-week sample was excluded: five markers were represented, but the margin between the first and second clusters was only 0.097.

To test marker dependence, cluster selection was repeated after removing each marker individually. Every leave-one-marker-out run selected cluster 11 at 15 weeks and cluster 10 at 17 weeks. Because the primary marker panel contains neither *MYO7A* nor *PCDH15*, retention of these or other Usher controls is not used to define the clusters.

Per-gene standardized means from accepted clusters were averaged across samples with NULL preservation. The output also records contributing sample count and a developmental-consistency measure. Hair-cell Q75 denotes the 75th percentile calculated among genes already assigned to HIGH; it is a relative experimental-priority annotation, not a claim of absent expression below the threshold.

### S1.3 Interpretation

Tau, hair-cell Q75, photoreceptor Q75, and the hair-cell/photoreceptor intersection represent alternative biological assumptions. They are not a sequential filtering cascade. Missing or below-threshold expression does not change the production tier and is not treated as evidence against disease relevance.

## S2. Data-driven weight fitting

As a secondary robustness analysis, we evaluated cross-validated grid search over the weight simplex and L2-penalized logistic regression using the selected disease controls. Both improved separation of those controls from comparison genes, but concentrated most discriminative weight on the animal-model layer and substantially altered the genome-wide ranking. Logistic regression assigned 89% of total weight to the animal-model layer; alternative fitted configurations produced Spearman correlations against the default ranking as low as 0.58 and shifted sparse-evidence genes upward by roughly 30 percentile points on average. Because the same limited control set would influence both model selection and evaluation, these analyses were treated as tests of possible over-specialization rather than as a basis for replacing the biologically specified production weights. Implementations and detailed outputs are provided by `scripts/weight_tuning.py` and `scripts/weight_logreg.py`.

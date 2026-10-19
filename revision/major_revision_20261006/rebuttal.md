# Response to the editor and reviewers

Original reviewer comments are reproduced below, with page references to the revised PDFs.

We thank the editor and reviewers for their comments. The revision clarifies the score’s purpose and HIGH-tier calibration, adds the requested comparisons and sensitivity analyses, and reports a retrospective temporal assessment. Its weak recovery limits the claims to hypothesis generation. Subsequent human review of all 45 temporal cases is described in R1-major-8.

## Editor

**Comment.**

> Please ensure the results are accurately reported, any overstated conclusions are rewritten and the limitations of the work fully explained.

**Response.** We have narrowed the conclusions to hypothesis generation. The revised manuscript reports the control-informed calibration of HIGH, the high raw ranks of housekeeping genes, shortlist sensitivity to weights and expression proxies, and weak temporal recovery. HIGH is now consistently described as a heuristic priority tier. These findings and their limitations are stated in the Abstract, Results and Discussion.

## Reviewer 1 — major comments

### R1-major-1. Define the prediction task; separate Usher and SYSCILIA controls

**Comment.**

> The intended prediction task is not entirely clear
>
> This paper describes UsherPipe as a gene prioritization tool related to Usher syndrome in several parts, but in others, it extends its scope to Usher syndrome and related ciliopathy. These are related, but they are not the same prediction problem.
>
> This distinction matters because the evaluation set includes nine established Usher genes together with 28 selected SYSCILIA genes. Good recovery of general ciliary genes does not necessarily demonstrate good performance for Usher-specific gene discovery.
>
> I would like the authors to define the main objective more clearly. Does this pipeline aim to identify new genes associated with Usher syndrome, genes associated with sensory ciliary disease, or a broader range of cilia-related genes that could be studied further in relation to Usher syndrome?
>
> The results for the nine Usher genes and the 28 SYSCILIA genes should also be reported separately throughout the manuscript rather than relying mainly on the combined set of 37 controls.

**Response.** The primary task is to prioritize genes with sensory or ciliary evidence for follow-up in the Usher context. We have clarified this scope and separated the nine established Usher controls from the 28 selected SYSCILIA controls throughout the Abstract, Results and Conclusions. Their median raw percentiles are 97.77% and 91.93%, with two and one genes in HIGH, respectively. The selected SYSCILIA subset is not a random validation sample; pooled counts are retained only when describing the original combined benchmark.

The temporal cohort covers inherited retinal/optic disease, hearing impairment and explicitly supported ciliopathies. It is not a cohort of newly identified Usher genes. R1-major-8 describes the human review and representative differences in disease mechanism.

**Changes/evidence.** Main Background “Usher syndrome as a specialized sensory ciliopathy”, Results “Internal control recovery” and Table 3; `results/control_rankings.tsv`, `results/control_tier_trace.tsv`; Supplementary Methods S4.

**Revised PDF locations.** Manuscript p. 1–2 (Abstract); Manuscript p. 3 (Usher syndrome as a specialized sensory ciliopathy); Manuscript p. 18–19 (Internal control recovery); Manuscript p. 30 (Conclusions); Supplementary Methods p. 4 (S4. Control traces).

### R1-major-2. Calibration and HIGH evaluation reuse the controls

**Comment.**

> The calibration and evaluation of the HIGH tier are not independent
>
> A central concern is that the cilia-signal gate was chosen after examining the behavior of both positive and negative controls.
>
> The authors are commendably transparent about this, but it creates an important circularity. Once the controls have been used to inform the definition of the gate, those same controls cannot provide an independent assessment of how well the final HIGH tier performs.
>
> This is particularly relevant because the HIGH tier is one of the main outputs of the pipeline.
>
> Ideally, the authors should separate calibration and evaluation using an independent set of genes. This could be done using a held-out control set, a temporal split, or another pre-specified development/test design.
>
> If such an analysis is not feasible, I would recommend describing the HIGH tier consistently as a heuristically calibrated prioritization tier, rather than implying that its specificity has been validated.
>
> The distinction between the raw six-layer score and the post-hoc gated HIGH tier should also be made more prominent in the Abstract and Results.

**Response.** The reviewer is correct that the gate and its control-based evaluation are not independent. We now describe HIGH as a heuristically calibrated priority tier and distinguish it from the raw score in the Abstract, Methods and Results. Raw scoring uses no training labels or similarity seeds, but known-gene information remains an input: 26 of 28 SYSCILIA controls overlap the embedded compendium used in localization scoring and gate passage. Internal control recovery therefore cannot establish independent specificity.

The added retrospective temporal assessment did not resolve this limitation. Neither historical analogue recovered a principal case in the top 100 or HIGH: recovery was 0/41 in the coding universe and 0/45 overall. Historical HIGH contained zero and five genes, respectively. The study evaluates historical analogues of a method developed after the cutoff and does not establish prospective validity. Design, results and subsequent human review are detailed in R1-major-8 and S6.

**Changes/evidence.** Abstract; Methods “Retrospective evaluation of historical analogues”; Results “Retrospective temporal evaluation” and Table 4; Discussion “Limitations”; S6; Additional file 12, including original/amended pre-outcome manifests and all 23 scheme outcomes.

**Revised PDF locations.** Manuscript p. 1–2 (Abstract); Manuscript p. 10–11 (NULL-aware composite scoring); Manuscript p. 12–13 (Retrospective evaluation of historical analogues); Manuscript p. 23–25 (Retrospective temporal evaluation); Manuscript p. 28–29 (Limitations); Supplementary Methods p. 2–4 (S3. Implemented); Supplementary Methods p. 5–11 (S6. Retrospective).

### R1-major-3. Show final control tiers, reasons for losses and threshold sensitivity

**Comment.**

> Recovery of known genes in the final HIGH tier needs to be shown directly
>
> The manuscript emphasizes that 35 of 37 controls fall within the top quartile of the genome-wide ranking. This sounds encouraging, but it does not tell the reader how the known genes behave after the complete prioritization procedure is applied.
>
> According to the supplementary analyses, only two established Usher genes are present among the 62 HIGH-tier genes, and only three controls in total are retained when the selected SYSCILIA genes are also considered.
>
> For a pipeline whose practical output is a relatively small HIGH-priority shortlist, this is an important result and should be presented clearly in the main manuscript.
>
> I suggest reporting:
>
> how many of the nine known Usher genes fall into HIGH, MEDIUM, LOW, or the excluded group;
>
> the same information for the SYSCILIA controls;
>
> why each established Usher gene that fails to reach HIGH is lost—i.e., score threshold, evidence count, or cilia-signal gate;
>
> how the sensitivity of the HIGH tier changes if alternative thresholds are used.
>
> A simple table tracing the known Usher genes through the different filtering steps would be very helpful.

**Response.** The main Results now report Usher HIGH/MEDIUM/LOW/excluded = 2/7/0/0 and SYSCILIA = 1/27/0/0. Table 3 traces every Usher control. All seven non-HIGH Usher controls fail composite ≥0.70; WHRN and USH1G additionally fail the gate. None fails the layer-count criterion. With the gate and minimum three layers fixed, thresholds 0.60/0.65/0.70/0.75/0.80 yield 366/170/62/11/1 HIGH labels, retaining 5/4/2/0/0 Usher and 6/1/1/0/0 SYSCILIA controls. The production threshold remains 0.70.

**Changes/evidence.** Main Table 3 and adjacent Results; `results/control_tier_trace.tsv`, `results/threshold_sensitivity.tsv`; S4.

**Revised PDF locations.** Manuscript p. 18–19 (Internal control recovery); Supplementary Methods p. 4 (S4. Control traces).

### R1-major-4. Raw housekeeping specificity failure; larger matched disease comparators

**Comment.**

> The housekeeping-gene result raises a substantial specificity concern
>
> One of the most notable results is that housekeeping genes rank very high in the base score. The median percentile was reported at 94.8%, and 11 of the 13 housekeeping genes fall within the top 25%.
>
> The authors correctly describe this as a specificity failure. I agree with that interpretation.
>
> However, the subsequent removal of these genes from the HIGH tier is less convincing as evidence of improved specificity because the gate was designed after examining these same negative controls.
>
> I also wonder whether housekeeping genes are the most informative negative set for this task. Many of these genes are highly constrained, extensively annotated, and well studied—features that naturally produce high scores in several of the six layers.
>
> A larger and better-matched negative-control set would strengthen the analysis considerably. For example, the authors could consider well-characterized genes associated with diseases unrelated to auditory, retinal, or ciliary biology, with matching for publication burden or annotation density where possible.
>
> Without such an analysis, I would avoid interpreting the current results as an estimate of biological specificity.

**Response.** We retain the raw housekeeping median of 94.8% as a specificity failure; the gate does not change raw rankings. We added a comparator analysis whose protocol and 111-pair roster were committed before outcome inspection. A Strong/Definitive ClinGen pool excluded recorded auditory/retinal/ciliary disease and HPO annotations and matched three unique genes per control on standardized log1p publication and GO counts, with a fixed 0.75-SD coordinate caliper and no reuse. The 27 and 84 comparator groups had median raw percentiles 64.21% and 60.30%, versus 97.77% and 91.93% for controls; pair concordances were 24/27 and 72/84.

None of the 111 matches was HIGH, but 110 already failed the raw score threshold, so this cannot be credited to gate specificity. The broader 420-gene pool retained three HIGH genes with residual sensory biology identified in a subsequent source check. They were not removed after outcomes. Coverage differs between groups; additional post-outcome common-observed-layer analyses preserve separation, whereas joint animal/literature removal reduces concordance to 55.6%/57.1%. S5 discusses the remaining limits of two-covariate matching, shared curation and comparator eligibility. These are descriptive specificity diagnostics, not clinical false-positive rates or novel-gene validation.

**Changes/evidence.** Results “Matched unrelated-disease comparators”; Discussion; S5; Additional file 11 contains the frozen matching protocol and roster, outcomes, source-completeness balance and omission diagnostics.

**Revised PDF locations.** Manuscript p. 19–20 (Negative controls); Manuscript p. 20–21 (Matched unrelated-disease comparators); Manuscript p. 28–29 (Limitations); Supplementary Methods p. 4–5 (S5. Frozen).

### R1-major-5. Heuristic weights, simple baselines and top-K persistence

**Comment.**

> The choice of weights remains somewhat arbitrary
>
> The six evidence-layer weights are biologically motivated, but the exact values appear heuristic.
>
> This is not necessarily a problem for a transparent prioritization framework, but the sensitivity analysis shows that the resulting ranking is not uniformly stable. Only 16 of 24 perturbations meet the predefined stability threshold, and some correlations fall to approximately 0.61. The animal-model layer appears to have particularly strong influence.
>
> The post-hoc logistic-regression experiment is also informative in this regard. It places most of the fitted weight on the animal-model layer and produces a substantially different genome-wide ranking.
>
> I agree with the authors that such fitted weights should not replace the default model because the same controls are involved in model fitting. Nevertheless, these findings suggest that the default weights should be presented as one reasonable biological configuration rather than as a particularly robust or optimal solution.
>
> It would strengthen the manuscript to include several simple comparisons, such as:
>
> equal weights;
>
> animal-model evidence alone;
>
> expression alone;
>
> localization/cilia evidence alone;
>
> leave-one-layer-out rankings.
>
> It would also be useful to report how frequently genes remain in the top 25, 50, or 100 across plausible alternative weighting schemes.

**Response.** The exact weights are heuristic, not optimal. Methods now explains the modest five-percentage-point emphasis on constraint/expression and equal weighting of the other layers, while stating that this does not establish superiority. We added equal, all six individual-layer and all six leave-one-layer-out comparisons. Animal-only gives the strongest Usher recovery (4/9 at top 100), whereas literature-only gives the strongest SYSCILIA recovery (21/28; Usher 2/9), compared with default 2/9 and 1/28. Literature-only medians are 99.13%/99.78%, with all nine Usher controls in its top 10%. Known disease terms and research/curation dependence limit these internal results.

Equal weighting gives whole-ranking ρ=0.9952 and 86 shared top 100 genes. Across equal plus 24 modest perturbations, only 8 default top25, 17 top50 and 41 top 100 genes persist in every configuration. The finite-family frequencies are not probabilities. Global correlations (0.9598–0.9994) coexist with meaningful shortlist movement; the earlier mean 0.8548 statistic is conditional on overlap, not whole-ranking stability. Logistic fitting (ρ=0.646 versus default; animal weight 0.903) remains a control-reuse diagnostic, not a production replacement.

**Changes/evidence.** Methods “NULL-aware composite scoring”; Results “Sensitivity analysis”; S2/S4; `results/baseline_comparison.tsv`, `candidate_membership_stability.tsv`, `control_rankings.tsv`.

**Revised PDF locations.** Manuscript p. 10–11 (NULL-aware composite scoring); Manuscript p. 22–23 (Sensitivity analysis); Supplementary Methods p. 2 (S2. Data-driven); Supplementary Methods p. 4 (S4. Control traces).

### R1-major-6. Sparse observed-layer means and completeness thresholds

**Comment.**

> NULL-aware scoring has advantages, but it may also favor genes with sparse evidence
>
> I find the explicit treatment of missing values to be one of the more interesting aspects of the pipeline. Treating missing evidence as zero can clearly be problematic.
>
> At the same time, the current available-layer weighted mean introduces another issue. A gene with only a few observed layers can receive a high composite score if those observed values happen to be high.
>
> The evidence-count requirement partially addresses this, but a HIGH-tier gene may still be supported by only three of the six evidence layers.
>
> The manuscript would benefit from a more direct analysis of this issue. For example:
>
> How many HIGH-tier genes have evidence from 3, 4, 5, or 6 layers?
>
> Does the HIGH list change substantially if at least four or five observed layers are required?
>
> Is composite score associated with evidence completeness?
>
> In addition, authors are encouraged to provide clear measures of evidence completeness along with the scores. A composite score of 0.75 based on three factors does not necessarily have the same evidential weight as a score of 0.75 supported by all six factors.

**Response.** All 62 HIGH labels have five/six layers (33/29); none has three/four. Requiring four or five retains all 62, while six retains 29. Nevertheless, eight one-layer genes appear in the raw top 100 and are all LOW. Composite score correlates with observed-layer count (ρ=0.2402; n=20,053). We retain per-gene counts/source flags and explain that available-layer means avoid an automatic missingness penalty but do not equalize evidential strength or quantify uncertainty.

**Changes/evidence.** Results “Impact of missing data handling”; Discussion; S4/S6; `results/evidence_completeness.tsv`, `threshold_sensitivity.tsv`, `per_gene_diagnostics.tsv`; `phase4_results/historical_topk_completeness.tsv`.

**Revised PDF locations.** Manuscript p. 21–22 (Impact of missing data handling); Manuscript p. 22–23 (Sensitivity analysis); Supplementary Methods p. 4 (S4. Control traces); Supplementary Methods p. 5–11 (S6. Retrospective).

### R1-major-7. Inter-layer overlap and within-layer combination

**Comment.**

> The six evidence layers may not be as independent as the framework implies
>
> Some of the evidence layers likely capture overlapping properties.
>
> For example, annotation completeness and literature evidence may both strongly favor well-studied genes. Localization evidence may also partly reflect the same published experiments used in ciliary databases or literature mining.
>
> This could help explain why highly characterized housekeeping genes receive unexpectedly high scores.
>
> I therefore think an inter-layer correlation analysis would be useful. A leave-one-layer-out analysis would also help establish whether the integrated model provides information beyond the strongest individual components.
>
> In addition, the Methods could provide a little more detail about how multiple sources are combined within each layer, particularly for expression, localization, annotation, and literature evidence.

**Response.** We added pairwise observed-gene correlations with sample sizes, all six leave-one-layer-out rankings and matched-pair omissions. Annotation–literature is the strongest correlation (ρ=0.3704; n=19,114); moderate correlations are not evidence of independent biology. Animal/literature omissions weaken matched separation, especially jointly. Methods and S3 now describe expression source/ordinal semantics and available-component normalization, annotation missing-subcomponent zero contribution, localization HPA reliability/embedded-list handling, animal term union and literature tier precedence. The embedded compendium contributes to both localization scoring and gate passage (R1-major-2). Sensory literature queries include Usher syndrome terms. Shared studies and disease knowledge contribute to multiple layers. At top 100, animal-only scoring recovers more Usher controls and literature-only scoring more SYSCILIA controls than the integrated score (R1-major-8; S4).

**Changes/evidence.** Main Methods “Evidence layers”; Results missingness/sensitivity/comparator sections; S3–S5; `results/layer_correlations.tsv`, `baseline_comparison.tsv`; `phase4_results/fixed_pair_sensitivities.tsv`.

**Revised PDF locations.** Manuscript p. 8–10 (Evidence layers); Manuscript p. 22–23 (Sensitivity analysis); Supplementary Methods p. 2–4 (S3. Implemented); Supplementary Methods p. 4 (S4. Control traces); Supplementary Methods p. 4–5 (S5. Frozen).

### R1-major-8. Seed-confounded mantis-ml benchmark; temporal or simple baselines

**Comment.**

> The mantis-ml comparison is informative but does not provide a strong external benchmark
>
> The manuscript appropriately acknowledges that the mantis-ml comparison is difficult to interpret because 33 of the 35 shared positive controls were used as mantis-ml training seeds.
>
> For that reason, the higher control recovery of mantis-ml cannot really be interpreted as a conventional head-to-head benchmark. Conversely, the comparison also does not establish how well UsherPipe performs on genuinely novel genes.
>
> If possible, a temporal validation would be particularly interesting—for example, testing whether the pipeline can prioritize genes that were associated with the relevant biology only after a defined historical cutoff.
>
> If this is not practical, simpler baselines would still be valuable. The authors could compare the full six-layer score against each major layer alone and against an equal-weight model. This would help demonstrate whether the integrated framework provides a meaningful benefit over simpler scoring strategies.

**Response.** We now describe the mantis-ml analysis as an exploratory comparison of cached outputs. Of the 35 shared controls, 33 were mantis-ml training seeds; the two non-seeds cannot support a meaningful independent benchmark. We also added equal-weight, individual-layer and leave-one-layer-out baselines. Animal-only scoring recovered the most Usher controls, and literature-only scoring recovered the most SYSCILIA controls; both exceeded the integrated score for their respective group.

We completed a retrospective temporal assessment using an evidence cutoff of 31 December 2020. The 45 later target-association cases and the analysis rules were fixed before the new rankings; development controls and previously inspected pilot cases were excluded. Forty-one cases mapped to the historical protein-coding universe, while four noncoding cases remained failures in the 45-case overall denominator. Neither the five-layer nor six-layer historical analogue recovered a case in the top 100 or HIGH (0/41; 0/45 overall). Top-1,000 recovery was 2/41 and 3/41, and median percentiles were 46.23 and 44.95. Historical HIGH contained zero and five genes, respectively. These weak results are reported in the Abstract, Results, Table 4 and Figure 8. No principal case represents a new Usher association.

The initial literature screening was AI-assisted. After the frozen analysis, a human author reviewed primary reports and family/pedigree evidence for all 45 cases, together with phenotype, inheritance, functional mechanisms and publication chronology. Human review raised family-evidence concerns for **PDIA6, VWA8 and PLCG1**. The initial PDIA6 report described one family; the earlier VWA8 developmental-disorder report also described one family, whereas the temporal target was a later retinal association. PLCG1 had a single-family immune-disorder report and a later auditory/ocular multisystem report involving four families. The retained screening ledger records cumulative target-family lower bounds of two, two and three, respectively, using the relevant reports. These remain screening classifications. Eligibility of the flagged cases remains under review; all three remain in the original cohort and results (S6.6).

The review also clarified the cohort's broader sensory scope: CRLS1 involves mitochondrial disease, CTNND1 retinal vascular disease, DHRSX glycosylation disease, and the RNU genes spliceosomal RNA-associated retinal disease. These mechanisms are not collectively evidence of ciliopathy. A separate contemporary GO description found no FDR-significant enrichment and does not provide predictive validation (S8). A bounded publication-version audit supported post-cutoff first-target publicity intervals; its date uncertainties are documented in S6.6.

This assessment uses historical analogues rather than an exact production replay. Post-cutoff method development, source substitutions, modern-text uncertainty and non-exhaustive ascertainment limit its interpretation. It provides no evidence of reliable novel disease-gene prediction and does not include a harmonized mantis-ml rerun.

**Changes/evidence.** Methods temporal design; Results temporal assessment, sensitivity and mantis-ml sections; Discussion/Conclusions; Table 4/Figure 8; S4/S6; Additional files 11/12 with protocols, clinical ledger, baselines and full outputs.

**Revised PDF locations.** Manuscript p. 22–23 (Sensitivity analysis); Manuscript p. 23–25 (Retrospective temporal evaluation); Manuscript p. 25 (Biological scope of the temporal cohort); Manuscript p. 26 (Comparison with mantis-ml); Supplementary Methods p. 4 (S4. Control traces); Supplementary Methods p. 5–11 (S6. Retrospective); Supplementary Methods p. 11–13 (S8. Contemporary).

### R1-major-9. Versions, timestamps, locked environment, commands and actual supplementary checksums

**Comment.**

> Reproducibility should be strengthened
>
> The authors have made a serious effort to document reproducibility, which is appropriate for a BMC Bioinformatics manuscript. However, the current provenance information is still incomplete.
>
> The reproducibility manifest records only a subset of source URLs and versions and does not include retrieval timestamps for the recorded inputs.
>
> For a computational pipeline paper, I would strongly encourage the authors to provide, where possible:
>
> exact database versions or snapshot identifiers;
>
> source URLs or accession numbers;
>
> retrieval dates;
>
> checksums for local input files;
>
> a locked software environment or dependency file;
>
> the commands needed to reproduce the figures and tables;
>
> ideally, a containerized environment or an equivalent reproducible setup.
>
> I also recommend checking the consistency of the submitted supplementary files against the checksum manifest. In the material provided for review, the checksum associated with the expression-shortlist report does not appear to match the submitted Additional file 6. This may simply reflect a conversion from a repository Markdown file to the journal TXT file, but if so, that distinction should be documented.

**Response.** We have added source versions and URLs, retrieval metadata where recorded, input/output SHA-256 hashes, exact tested dependency locks and commands for reproducing the figures and tables (S7; Additional files 11/12). Clean replay reproduced 28 production/revision TSVs and, separately, all nine temporal TSVs and their manifest. The tested environment is Python 3.13.1 on macOS arm64. Original unrecorded retrieval dates remain unknown, and the production bundle supports numerical replay rather than complete regeneration from every original raw source. No container image is supplied; the tested environment and replay commands are documented in S7.

The reviewer correctly identified the checksum mismatch: the original manifest hashed the repository Markdown report rather than the submitted Additional file 6 TXT. The revision records source and converted files separately. Additional file 10 hashes the actual delivered additional files, and the package manifest identifies the delivered documents and their sources.

**Changes/evidence.** Methods “Reproducibility”; S7; Additional files 4/10/11/12; package manifest and response location index. The complete executable numerical replay remains in the repository.

**Revised PDF locations.** Manuscript p. 14–15 (Reproducibility); Manuscript p. 31–32 (Availability of data and materials); Manuscript p. 33–34 (Additional files); Supplementary Methods p. 11 (S7. Numerical replay).

### R1-major-10. Retina/proxy expression, absence of hair-cell production data and proxy sensitivity

**Comment.**

> The production expression layer seems more retina-oriented than fully Usher-specific
>
> The manuscript appropriately emphasizes that Usher syndrome involves both retinal and auditory biology. However, the production expression layer does not appear to include cochlear hair-cell data. The GSE135913 cochlear analysis is instead treated as a post-hoc exploratory analysis based on two accepted fetal samples.
>
> At the same time, cerebellum is retained as a proxy tissue in the production score.
>
> I think the authors should explain this choice more clearly, because tissue specificity is presented as an important feature distinguishing UsherPipe from more general gene-prioritization tools.
>
> It would be useful to show how much the expression layer contributes to the ranking of established Usher genes, and whether removing the proxy tissue materially changes the results.
>
> Until direct auditory-cell data are incorporated into the production score, the term “Usher-specific tissue weighting” may be somewhat stronger than the available data support.

**Response.** We replace “Usher-specific tissue weighting” with explicit retina/proxy expression terminology. To include neural expression context in the cilia-focused panel, we used cerebellum, which had measurements in both HPA and GTEx. This was a pragmatic proxy choice; it does not provide cochlear evidence. Production lacks direct cochlear hair-cell measurements; developmental or auditory-restricted genes can be disadvantaged when other evidence is also limited. The fetal GSE135913 analyses remain exploratory views within an already selected HIGH tier and do not repair this production gap.

Expression contributes 15.5–27.5% of individual Usher controls' weighted support. Removing cerebellum and recomputing source transforms yields whole-ranking ρ=0.9496 and median absolute shift 4.92 percentile points. HIGH is 60 versus 62, with only 37 shared genes (25 leave/23 enter): USH2A/MYO7A enter, CDH23 leaves and PCDH15 remains. We report this material dependence without selecting a revised score using control recovery. Source coverage and background-only Tau contributions are made explicit.

**Changes/evidence.** Methods expression layer/Table 1; Results “Expression dependence”; Discussion; S3; `results/usher_expression_diagnostics.tsv`, `baseline_comparison.tsv`, `per_gene_diagnostics.tsv`.

**Revised PDF locations.** Manuscript p. 23 (Expression dependence); Manuscript p. 28–29 (Limitations); Supplementary Methods p. 1–2 (S1. Optional); Supplementary Methods p. 2–4 (S3. Implemented).

## Reviewer 1 — minor comments

### R1-minor-1. Define seed-free at first introduction

**Comment.**

> The term “seed-free” should be defined clearly when it is first introduced. Known genes are not used in the raw composite score, but control behavior did influence the downstream cilia-signal gate.

**Response.** Abstract Results now defines raw scoring as using neither known disease training labels nor similarity seeds and immediately distinguishes the control-informed downstream gate. The fuller Methods definition acknowledges that known-gene annotations and disease-name literature terms enter the score (R1-major-2). Seed-free is restricted to absence of training labels and similarity seeds, not absence of known-gene knowledge.

**Revised PDF locations.** Manuscript p. 1–2 (Abstract); Manuscript p. 10–11 (NULL-aware composite scoring); Supplementary Methods p. 2–4 (S3. Implemented).

### R1-minor-2. Use priority tiers rather than confidence tiers

**Comment.**

> I would consider replacing “confidence tier” with “priority tier.” HIGH, MEDIUM, and LOW are rule-based prioritization categories rather than calibrated statistical confidence levels.

**Response.** Revised manuscript and supplementary prose use “priority tier”, including figure captions. The legacy data column `confidence_tier` remains for schema compatibility, explicitly documented as a rule-based priority category rather than calibrated statistical confidence. Original frozen artifacts retain their historical wording.

**Revised PDF locations.** Manuscript p. 10–11 (NULL-aware composite scoring); Manuscript p. 18–19 (Internal control recovery); Supplementary Methods p. 2–4 (S3. Implemented).

### R1-minor-3. Check canonical/HGNC terminology

**Comment.**

> Gene-identifier terminology should be checked carefully. The manuscript acknowledges that many displayed gene names are not formally validated current HGNC symbols, so wording such as “canonical identifier” should only be used where it is strictly accurate.

**Response.** We describe retained analysis IDs/labels, duplicate-symbol consolidation and 573 ENSG fallback labels without calling them validated current HGNC symbols. Additional file 1's description is corrected to retained analysis identifiers. Current HGNC mappings are used for comparator eligibility and the separate contemporary GO classification; these do not retrospectively validate all production names.

**Revised PDF locations.** Manuscript p. 7–8 (Gene universe); Supplementary Methods p. 1–2 (S1. Optional).

### R1-minor-4. Main-text control tier distribution

**Comment.**

> The distribution of established Usher and SYSCILIA controls across the final tiers should be included in the main Results section.

**Response.** Added 2 HIGH/7 MEDIUM Usher and 1 HIGH/27 MEDIUM SYSCILIA in Results, with zero LOW/excluded in both groups and all nine Usher traces in Table 3 (R1-major-3).

**Revised PDF locations.** Manuscript p. 18–19 (Internal control recovery); Supplementary Methods p. 4 (S4. Control traces).

### R1-minor-5. Background sampling and random seed

**Comment.**

> Please state how the random background genes shown in the control-recovery analysis were sampled and provide the random seed.

**Response.** Figure 5 caption and S7 specify 500 non-control scored labels sampled without replacement, NumPy `default_rng(42)`. The revision figure code orders the 20,016 eligible background labels by retained Ensembl ID and exports sampled IDs and percentiles, making selection reproducible rather than dependent on database row order.

**Revised PDF locations.** Manuscript p. 39 (Figure 5. Internal control recovery); Supplementary Methods p. 11 (S7. Numerical replay).

### R1-minor-6. Permanent exact-version archive/DOI if possible

**Comment.**

> In addition to the GitHub commit, I would encourage archiving the exact software version used for the manuscript in a permanent repository with a DOI if possible.

**Response.** A DOI-bearing archive has not been deposited. The exact revised code and analysis records are available in the [20 October 2026 release](https://github.com/gbanyan/usher-exploring/tree/major-revision-author-review-20261020-v2), with dependency locks, numerical replay inputs and delivered-file hashes. The original public code/data commit and submitted files remain identified separately in Data Availability and S7.

**Changes/evidence.** Data availability; S7; Additional files 10-12; exact temporal outcome/audit checkpoint 736e16f and production revision checkpoint 0e1634a.

**Revised PDF locations.** Manuscript p. 31–32 (Availability of data and materials); Supplementary Methods p. 11 (S7. Numerical replay).

### R1-minor-7. Consider shortening biological background

**Comment.**

> The biological background is thorough, but somewhat long for a BMC Bioinformatics paper. Some of the detailed discussion of Usher molecular biology could be shortened so that more emphasis can be placed on the computational design, validation strategy, benchmarking, and scoring assumptions.

**Response.** Following the reviewer’s suggestion, we have shortened the biological background by condensing the multisystem-ciliopathy overview, removing repeated scope explanations and reducing the lists of protein functions. The retinal and hair-cell rationale, the stereocilia/cilia distinction and supporting references are retained. For example, the scope paragraph now states: “General ciliary function alone does not establish involvement in the combined auditory–retinal phenotype. UsherPipe therefore supplies sensory/ciliary hypotheses for follow-up in the Usher context.”

**Revised PDF locations.** Manuscript p. 3 (Usher syndrome as a specialized sensory ciliopathy); Manuscript p. 3–4 (Ciliary and stereociliary biology underlying Usher syndrome).

## Reviewer 2

**Comment.**

> The figures were not in an accessible form. So I could not review this.

**Response.** Thank you for identifying the access problem. The prepared revision material includes the figures embedded with their legends in the manuscript and as separate figure files. Before resubmission, we will check that the journal-generated review PDF renders each figure and that the uploaded figure files are available to reviewers. We would welcome the reviewer's assessment once the figures are accessible.

## Reviewer 3

### R3-1. Add support for the ciliary/periciliary Background sentence

**Comment.**

> In Background, in the sentence beginning “Because the known Usher genes encode ciliary and periciliary proteins acting at hair-cell stereocilia, the photoreceptor connecting cilium, and the periciliary membrane complex, Usher syndrome may…”, a supporting reference should be added.

**Response.** The revised sentence describes several Usher proteins in stereociliary and photoreceptor connecting-cilium/periciliary complexes, supported by references [8, 9, 10, 11]. This avoids treating every Usher protein as exclusively ciliary and distinguishes actin-based stereocilia from true cilia. See Background “Usher syndrome as a specialized sensory ciliopathy”.

**Revised PDF locations.** Manuscript p. 3 (Usher syndrome as a specialized sensory ciliopathy).

### R3-2. Seed-free versus post-hoc gate calibration and HIGH interpretation

**Comment.**

> The manuscript describes UsherPipe as a seed-free approach, but the cilia-signal gate was defined after examining control and negative-control behavior. The authors note that this is a post-hoc calibration. It would be helpful to clarify how this affects the interpretation of control-recovery performance and the definition of the HIGH tier.

**Response.** We define seed-free narrowly as no training labels or similarity seeds, disclose embedded known-gene/disease-term inputs, and separate raw scoring from downstream control-informed calibration in the Abstract, Methods and Results. HIGH is a heuristic priority tier, not validated specificity or disease probability. Table 3 reports the control filtering losses directly, and the matched comparison does not independently calibrate HIGH. See R1-major-2/3 and Supplementary Methods S3/S5/S6.

**Revised PDF locations.** Manuscript p. 10–11 (NULL-aware composite scoring); Manuscript p. 18–19 (Internal control recovery); Supplementary Methods p. 2–4 (S3. Implemented); Supplementary Methods p. 4–5 (S5. Frozen); Supplementary Methods p. 5–11 (S6. Retrospective).

### R3-3. Justify final weights and discuss logistic-ranking sensitivity

**Comment.**

> The manuscript reports that alternative weighting strategies, including logistic-regression-based weighting, substantially changed the genome-wide ranking (default vs. logistic regression rank ρ = 0.646). These alternatives were not adopted due to concerns about control reuse and over-specialization. Additional justification for the final predefined weights would be useful, along with a discussion of how this degree of ranking sensitivity affects the robustness of candidate prioritization.

**Response.** Constraint and expression receive 0.20 each for general functional relevance and sensory-tissue plausibility; the remaining four layers receive 0.15 each. These are heuristic design choices. Equal, individual-layer and leave-one-layer-out baselines and top25/50/100 persistence show that high global correlation does not ensure stable shortlists. Only 41 default top 100 genes persist in all 25 modest configurations; animal-only better recovers Usher controls and literature-only better recovers SYSCILIA controls (4/9 and 21/28 at top 100, respectively). Logistic weighting substantially changes the ranking (ρ=0.646) and was not adopted for production because it reuses the evaluation controls and risks over-specialization. See R1-major-5 and Results/S2/S4.

**Revised PDF locations.** Manuscript p. 22–23 (Sensitivity analysis); Supplementary Methods p. 2 (S2. Data-driven); Supplementary Methods p. 4 (S4. Control traces).

### R3-4. Independent support for genuinely novel disease-gene prioritization

**Comment.**

> The recovery of known Usher and ciliary genes shows that the pipeline captures relevant disease biology. However, because the cilia-signal gate was calibrated using these same controls, it would be helpful to clarify what independent evidence supports UsherPipe’s ability to prioritize genuinely novel disease genes rather than mainly rediscovering genes with established Usher/ciliary characteristics.

**Response.** We have not established reliable prioritization of genuinely novel disease genes. The added retrospective temporal assessment provides a separate test of later associations, but its results were weak: neither historical analogue recovered a principal case in the top 100 or HIGH (0/41 in the coding universe; 0/45 overall), and top-1,000 recovery was 2/41 and 3/41. No principal case represents a new Usher association. Source substitutions and post-cutoff method development also prevent treating this as an exact production replay or prospective validation.

We have therefore limited the claims to hypothesis generation. R1-major-8 and S6 describe the cohort, subsequent human review of all 45 cases and unresolved eligibility concerns.

**Changes/evidence.** Methods/Results temporal sections; Table 4/Figure 8; S6; Additional file 12 with the 45-case roster, date/family evidence, exclusions, source contract, all outcomes and reconstruction code.

**Revised PDF locations.** Manuscript p. 12–13 (Retrospective evaluation of historical analogues); Manuscript p. 23–25 (Retrospective temporal evaluation); Manuscript p. 25 (Biological scope of the temporal cohort); Manuscript p. 28–29 (Limitations); Supplementary Methods p. 5–11 (S6. Retrospective); Supplementary Methods p. 11–13 (S8. Contemporary).

### R3-5. Impact of excluding hair-cell expression and developmental bias

**Comment.**

> Because Usher syndrome affects cochlear hair cells, the authors could more directly discuss the impact of excluding hair-cell expression data from the production score. The exploratory fetal cochlear analyses are useful, but they do not contribute to the final composite score. It would be helpful to comment on whether the absence of suitable hair-cell data may disadvantage genes with more limited or developmentally restricted evidence.

**Response.** Main Methods/Results/Discussion now state the lack of production auditory-cell evidence and possible disadvantage for auditory-restricted or developmentally restricted genes. The fetal analyses do not enter the score, are based on two marker-selected samples and already selected HIGH genes, and do not establish adult expression or independent validity. We quantify expression contribution and substantial cerebellum-proxy sensitivity rather than implying complete Usher-tissue coverage. See R1-major-10, S1/S3.

**Revised PDF locations.** Manuscript p. 23 (Expression dependence); Manuscript p. 28–29 (Limitations); Supplementary Methods p. 1–2 (S1. Optional); Supplementary Methods p. 2–4 (S3. Implemented).

### R3-6. General gene importance/research intensity versus disease specificity

**Comment.**

> A broader conceptual issue concerns the biological specificity of the composite score. Several evidence layers, such as gnomAD constraint, functional annotation completeness, and publication-based evidence, may reflect general gene importance or research intensity rather than disease-specific involvement in Usher syndrome. This is particularly relevant because housekeeping genes ranked very highly in the raw multi-evidence score (median at the 94.8th percentile). Clarifying how the composite score distinguishes general biological importance from evidence specifically supporting a role in Usher syndrome or related ciliopathies would strengthen the interpretation. The authors might also consider discussing whether additional disease-specific negative controls or specificity analyses could help quantify this distinction.

**Response.** The composite only partly distinguishes sensory/ciliary evidence from general gene importance and research intensity. Constraint, annotation depth and publication evidence can elevate well-studied genes, as shown by the housekeeping median at the 94.8th percentile. We now state this limitation explicitly.

We added disease comparators matched on publication and GO counts, layer correlations and omission analyses. Control advantage persists when pairs are compared on shared observed layers, but falls to 55.6% for Usher and 57.1% for SYSCILIA after joint animal/literature omission. These findings show dependence on sensory-model and literature evidence; the comparators are not verified clinical negatives and do not establish a clinical specificity estimate. R1-major-4/7 and S3–S5 provide the analyses. The weak temporal recovery reported in R1-major-8 further limits claims of disease-specific prediction.

**Revised PDF locations.** Manuscript p. 19–20 (Negative controls); Manuscript p. 20–21 (Matched unrelated-disease comparators); Manuscript p. 22–23 (Sensitivity analysis); Manuscript p. 25 (Biological scope of the temporal cohort); Supplementary Methods p. 2–4 (S3. Implemented); Supplementary Methods p. 4 (S4. Control traces); Supplementary Methods p. 4–5 (S5. Frozen); Supplementary Methods p. 11–13 (S8. Contemporary).


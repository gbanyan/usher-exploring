# Point-by-point response to major revision

Response aligned with the revised manuscript, Supplementary Methods and delivered additional files. Reviewer A denotes the downloaded report (10 major and 7 minor comments); Reviewer B denotes the six comments supplied in correspondence. These source labels preserve the available reports; journal-assigned reviewer numbers were not provided. Original comment text is reproduced below. Revised locations identify section headings and tables; the accompanying location index identifies pages in the generated revision PDFs.

We thank both reviewers for helping distinguish transparent hypothesis generation from validated disease-gene prediction. We have separated seed-free raw scoring from control-informed HIGH calibration, reported final control tiers and filtering losses, added matched disease comparators and simple baselines, quantified weight/completeness/proxy dependence, and strengthened numerical replay and delivered-file checksums. We also completed a retrospective temporal assessment with 45 later target associations fixed before new ranking calculation. Its weak recovery is reported directly and narrows the claims. Production scores, weights and thresholds were not optimized against these new outcomes.

## Reviewer A — major comments

### A-major-1. Define the prediction task; separate Usher and SYSCILIA controls

**Comment.**

> The intended prediction task is not entirely clear
> This paper describes UsherPipe as a gene prioritization tool related to Usher syndrome in several parts, but in others, it extends its scope to Usher syndrome and related ciliopathy. These are related, but they are not the same prediction problem.
> This distinction matters because the evaluation set includes nine established Usher genes together with 28 selected SYSCILIA genes. Good recovery of general ciliary genes does not necessarily demonstrate good performance for Usher-specific gene discovery.
> I would like the authors to define the main objective more clearly. Does this pipeline aim to identify new genes associated with Usher syndrome, genes associated with sensory ciliary disease, or a broader range of cilia-related genes that could be studied further in relation to Usher syndrome?
> The results for the nine Usher genes and the 28 SYSCILIA genes should also be reported separately throughout the manuscript rather than relying mainly on the combined set of 37 controls.

**Response.** The primary task is genome-wide cilia/sensory-aware hypothesis generation for follow-up in the Usher context. It is neither an Usher-specific diagnostic classifier nor proof that broad ciliary genes cause the combined auditory–retinal phenotype. The Abstract, Background, Results and Conclusions now distinguish the nine established Usher controls from the 28 selected SYSCILIA controls. Raw median percentiles are 97.77% and 91.93%; final HIGH counts are two and one. The curated SYSCILIA subset is not a random validation sample. Pooled counts are retained only where describing the historical cached benchmark or original combined artifacts, with the group composition explicit.

**Changes/evidence.** Main Background “Usher syndrome as a specialized sensory ciliopathy”, Results “Internal control recovery” and Table 3; `results/control_rankings.tsv`, `results/control_tier_trace.tsv`; Supplementary Methods S4.

### A-major-2. Calibration and HIGH evaluation reuse the controls

**Comment.**

> The calibration and evaluation of the HIGH tier are not independent
> A central concern is that the cilia-signal gate was chosen after examining the behavior of both positive and negative controls.
> The authors are commendably transparent about this, but it creates an important circularity. Once the controls have been used to inform the definition of the gate, those same controls cannot provide an independent assessment of how well the final HIGH tier performs.
> This is particularly relevant because the HIGH tier is one of the main outputs of the pipeline.
> Ideally, the authors should separate calibration and evaluation using an independent set of genes. This could be done using a held-out control set, a temporal split, or another pre-specified development/test design.
> If such an analysis is not feasible, I would recommend describing the HIGH tier consistently as a heuristically calibrated prioritization tier, rather than implying that its specificity has been validated.
> The distinction between the raw six-layer score and the post-hoc gated HIGH tier should also be made more prominent in the Abstract and Results.

**Response.** We agree. The downstream gate was selected after inspection of positive/housekeeping behavior, although the raw mean uses no disease training labels or similarity seeds. The Abstract and Methods now identify HIGH as a heuristically calibrated priority tier. We corrected the gate description to the actual direct-compartment/compendium source flags OR the positive-animal Q75 threshold, not any positive aggregate localization score. Internal control recovery and removal of housekeeping genes are calibration diagnostics, not independent specificity validation.

We added a separate later-association cohort selected from clinical/date evidence before new rank calculation. Two co-primary historical analogues evaluated 41 eligible protein-coding cases; four noncoding cases remained failures in the 45-case end-to-end denominator. Neither version recovered a principal case at top 100 or HIGH. All 41 had at least four observed weighted families, but none met score 0.7, so gate failure alone cannot explain the result. The control-informed gate architecture and post-cutoff method development remain disclosed; the temporal assessment does not establish clinical specificity or prospective validity. We consistently describe HIGH as a heuristically calibrated priority tier.

**Changes/evidence.** Abstract; Methods “Retrospective evaluation of historical analogues”; Results “Retrospective temporal evaluation” and Table 4; Discussion “Limitations”; S6; Additional file 12, including original/amended pre-outcome manifests and all 23 scheme outcomes.

### A-major-3. Show final control tiers, reasons for losses and threshold sensitivity

**Comment.**

> Recovery of known genes in the final HIGH tier needs to be shown directly
> The manuscript emphasizes that 35 of 37 controls fall within the top quartile of the genome-wide ranking. This sounds encouraging, but it does not tell the reader how the known genes behave after the complete prioritization procedure is applied.
> According to the supplementary analyses, only two established Usher genes are present among the 62 HIGH-tier genes, and only three controls in total are retained when the selected SYSCILIA genes are also considered.
> For a pipeline whose practical output is a relatively small HIGH-priority shortlist, this is an important result and should be presented clearly in the main manuscript.
> I suggest reporting:
> how many of the nine known Usher genes fall into HIGH, MEDIUM, LOW, or the excluded group;
> the same information for the SYSCILIA controls;
> why each established Usher gene that fails to reach HIGH is lost—i.e., score threshold, evidence count, or cilia-signal gate;
> how the sensitivity of the HIGH tier changes if alternative thresholds are used.
> A simple table tracing the known Usher genes through the different filtering steps would be very helpful.

**Response.** The main Results now report Usher HIGH/MEDIUM/LOW/excluded = 2/7/0/0 and SYSCILIA = 1/27/0/0. Table 3 traces every Usher control. All seven non-HIGH Usher controls fail composite ≥0.70; WHRN and USH1G additionally fail the gate. None fails the layer-count criterion. With the gate and minimum three layers fixed, thresholds 0.60/0.65/0.70/0.75/0.80 yield 366/170/62/11/1 HIGH labels, retaining 5/4/2/0/0 Usher and 6/1/1/0/0 SYSCILIA controls. We report this full family without choosing a more favorable production threshold.

**Changes/evidence.** Main Table 3 and adjacent Results; `results/control_tier_trace.tsv`, `results/threshold_sensitivity.tsv`; S4.

### A-major-4. Raw housekeeping specificity failure; larger matched disease comparators

**Comment.**

> The housekeeping-gene result raises a substantial specificity concern
> One of the most notable results is that housekeeping genes rank very high in the base score. The median percentile was reported at 94.8%, and 11 of the 13 housekeeping genes fall within the top 25%.
> The authors correctly describe this as a specificity failure. I agree with that interpretation.
> However, the subsequent removal of these genes from the HIGH tier is less convincing as evidence of improved specificity because the gate was designed after examining these same negative controls.
> I also wonder whether housekeeping genes are the most informative negative set for this task. Many of these genes are highly constrained, extensively annotated, and well studied—features that naturally produce high scores in several of the six layers.
> A larger and better-matched negative-control set would strengthen the analysis considerably. For example, the authors could consider well-characterized genes associated with diseases unrelated to auditory, retinal, or ciliary biology, with matching for publication burden or annotation density where possible.
> Without such an analysis, I would avoid interpreting the current results as an estimate of biological specificity.

**Response.** We retain the raw housekeeping median of 94.8% as a specificity failure; the gate does not change raw rankings. We added a comparator analysis whose protocol and 111-pair roster were committed before outcome inspection. A Strong/Definitive ClinGen pool excluded recorded auditory/retinal/ciliary disease and HPO annotations and matched three unique genes per control on standardized log1p publication and GO counts, with a fixed 0.75-SD coordinate caliper and no reuse. The 27 and 84 comparator groups had median raw percentiles 64.21% and 60.30%, versus 97.77% and 91.93% for controls; pair concordances were 24/27 and 72/84.

None of the 111 matches was HIGH, but 110 already failed the raw score threshold, so this cannot be credited to gate specificity. The broader 420-gene pool retained three HIGH genes with residual sensory biology identified in a subsequent source check. They were not removed after outcomes. Coverage differs between groups; additional post-outcome common-observed-layer analyses preserve separation, whereas joint animal/literature removal reduces concordance to 55.6%/57.1%. We explicitly discuss matching only two measured research-burden quantities, shared curation, eligibility–feature overlap, and absence of verified biological negatives. These are descriptive specificity diagnostics, not clinical false-positive rates or novel-gene validation.

**Changes/evidence.** Results “Matched unrelated-disease comparators”; Discussion; S5; `phase3_spec.md`, `phase3_roster/`, `phase3_results/`, `phase4_results/fixed_pair_summary.tsv` and `matching_completeness_balance.tsv`.

### A-major-5. Heuristic weights, simple baselines and top-K persistence

**Comment.**

> The choice of weights remains somewhat arbitrary
> The six evidence-layer weights are biologically motivated, but the exact values appear heuristic.
> This is not necessarily a problem for a transparent prioritization framework, but the sensitivity analysis shows that the resulting ranking is not uniformly stable. Only 16 of 24 perturbations meet the predefined stability threshold, and some correlations fall to approximately 0.61. The animal-model layer appears to have particularly strong influence.
> The post-hoc logistic-regression experiment is also informative in this regard. It places most of the fitted weight on the animal-model layer and produces a substantially different genome-wide ranking.
> I agree with the authors that such fitted weights should not replace the default model because the same controls are involved in model fitting. Nevertheless, these findings suggest that the default weights should be presented as one reasonable biological configuration rather than as a particularly robust or optimal solution.
> It would strengthen the manuscript to include several simple comparisons, such as:
> equal weights;
> animal-model evidence alone;
> expression alone;
> localization/cilia evidence alone;
> leave-one-layer-out rankings.
> It would also be useful to report how frequently genes remain in the top 25, 50, or 100 across plausible alternative weighting schemes.

**Response.** The exact weights are heuristic, not optimal. Methods now explains the modest five-percentage-point emphasis on constraint/expression and equal weighting of the other layers, while stating that this does not establish superiority. We added equal, all six individual-layer and all six leave-one-layer-out comparisons. Animal-only is a stronger internal recovery baseline: top 100 contains four Usher/eleven SYSCILIA controls, compared with two/one under default. We report this unfavorable comparison directly.

Equal weighting gives whole-ranking ρ=0.9952 and 86 shared top 100 genes. Across equal plus 24 modest perturbations, only 8 default top25, 17 top50 and 41 top 100 genes persist in every configuration. The finite-family frequencies are not probabilities. Global correlations (0.9598–0.9994) coexist with meaningful shortlist movement; the earlier mean 0.8548 statistic is conditional on overlap, not whole-ranking stability. Logistic fitting (ρ=0.646 versus default; animal weight 0.903) remains a control-reuse diagnostic, not a production replacement.

**Changes/evidence.** Methods “NULL-aware composite scoring”; Results “Sensitivity analysis”; S2/S4; `results/baseline_comparison.tsv`, `candidate_membership_stability.tsv`, `control_rankings.tsv`.

### A-major-6. Sparse observed-layer means and completeness thresholds

**Comment.**

> NULL-aware scoring has advantages, but it may also favor genes with sparse evidence
> I find the explicit treatment of missing values to be one of the more interesting aspects of the pipeline. Treating missing evidence as zero can clearly be problematic.
> At the same time, the current available-layer weighted mean introduces another issue. A gene with only a few observed layers can receive a high composite score if those observed values happen to be high.
> The evidence-count requirement partially addresses this, but a HIGH-tier gene may still be supported by only three of the six evidence layers.
> The manuscript would benefit from a more direct analysis of this issue. For example:
> How many HIGH-tier genes have evidence from 3, 4, 5, or 6 layers?
> Does the HIGH list change substantially if at least four or five observed layers are required?
> Is composite score associated with evidence completeness?
> In addition, authors are encouraged to provide clear measures of evidence completeness along with the scores. A composite score of 0.75 based on three factors does not necessarily have the same evidential weight as a score of 0.75 supported by all six factors.

**Response.** All 62 HIGH labels actually have five/six layers (33/29); none has three/four. Requiring four or five retains all 62, while six retains 29. Nevertheless, eight one-layer genes appear in the raw top 100 and are all LOW. Composite score correlates with observed-layer count (ρ=0.2402; n=20,053). We retain per-gene counts/source flags and explain that available-layer means avoid an automatic missingness penalty but do not equalize evidential strength or quantify uncertainty. The historical audit also exposes sparse high-ranking genes; this limitation is not dismissed because production HIGH is well-covered.

**Changes/evidence.** Results “Impact of missing data handling”; Discussion; S4/S6; `results/evidence_completeness.tsv`, `threshold_sensitivity.tsv`, `per_gene_diagnostics.tsv`; `phase4_results/historical_topk_completeness.tsv`.

### A-major-7. Inter-layer overlap and within-layer combination

**Comment.**

> The six evidence layers may not be as independent as the framework implies
> Some of the evidence layers likely capture overlapping properties.
> For example, annotation completeness and literature evidence may both strongly favor well-studied genes. Localization evidence may also partly reflect the same published experiments used in ciliary databases or literature mining.
> This could help explain why highly characterized housekeeping genes receive unexpectedly high scores.
> I therefore think an inter-layer correlation analysis would be useful. A leave-one-layer-out analysis would also help establish whether the integrated model provides information beyond the strongest individual components.
> In addition, the Methods could provide a little more detail about how multiple sources are combined within each layer, particularly for expression, localization, annotation, and literature evidence.

**Response.** We added pairwise observed-gene correlations with sample sizes, all six leave-one-layer-out rankings and matched-pair omissions. Annotation–literature is the strongest correlation (ρ=0.3704; n=19,114); moderate correlations are not evidence of independent biology. Animal/literature omissions weaken matched separation, especially jointly. Methods and S3 now describe expression source/ordinal semantics and available-component normalization, annotation missing-subcomponent zero contribution, localization HPA reliability/embedded-list handling, animal term union and literature tier precedence. We corrected descriptions that conflated Approved/Uncertain antibody evidence with computational predictions or embedded lists with newly acquired proteomics datasets.

**Changes/evidence.** Main Methods “Evidence layers”; Results missingness/sensitivity/comparator sections; S3–S5; `results/layer_correlations.tsv`, `baseline_comparison.tsv`; `phase4_results/fixed_pair_sensitivities.tsv`.

### A-major-8. Seed-confounded mantis-ml benchmark; temporal or simple baselines

**Comment.**

> The mantis-ml comparison is informative but does not provide a strong external benchmark
> The manuscript appropriately acknowledges that the mantis-ml comparison is difficult to interpret because 33 of the 35 shared positive controls were used as mantis-ml training seeds.
> For that reason, the higher control recovery of mantis-ml cannot really be interpreted as a conventional head-to-head benchmark. Conversely, the comparison also does not establish how well UsherPipe performs on genuinely novel genes.
> If possible, a temporal validation would be particularly interesting—for example, testing whether the pipeline can prioritize genes that were associated with the relevant biology only after a defined historical cutoff.
> If this is not practical, simpler baselines would still be valuable. The authors could compare the full six-layer score against each major layer alone and against an equal-weight model. This would help demonstrate whether the integrated framework provides a meaningful benefit over simpler scoring strategies.

**Response.** The cached-output comparison retains the 33/35 shared-positive seed overlap and only two non-seeds, without claiming head-to-head novel-gene performance or rerunning mantis-ml training. Simple baselines are now reported; animal-only outperforms the integrated score on selected-control recovery.

We subsequently completed the requested temporal assessment, extending the preserved restricted pilot. RetNet/PanelApp catalogs, gene/alias searches and primary reports were used to review dates, unrelated target families, inheritance and functional/replication evidence. The 45 principal cases, sources, code and comparisons were fixed before expanded scores; development controls and the three previously inspected pilot examples were excluded. We distinguish first-ever human associations from first target associations after another phenotype. The adopted cohort is not exhaustive, and 895 unconfirmed/unnominated catalog records remain uncertain rather than clinical negatives.

Using a 31 December 2020 evidence cutoff, we reconstructed gnomAD v2.1.1, HPA v20, GTEx v8, GO, original 2019 retinal matrices, native MGI/IMPC/ZFIN evidence and archived gene2pubmed. Two co-primary versions omit or include date-bounded literature queried from modern text; 21 additional comparisons were specified before outcomes. Among 41 in-universe cases, top 100/HIGH recovery was 0/41 in both versions, top 1,000 was 2/41 and 3/41, and top 10% was 5/41 and 6/41. Four noncoding cases remained nonrecoveries in the 45-case denominator. These negative/weak results are in the Abstract, Results, Table 4 and Figure 9. We did not replace them with favorable sensitivity outcomes.

This is a retrospective evaluation of historical analogues, not an exact production replay or prospectively developed predictor. Historical source substitutions, missing HCOP/annotation channels, modern-text uncertainty and conditional catalog ascertainment are explicit. The temporal study does not include a harmonized mantis-ml rerun or validate its comparative novel-gene performance. The preserved pilot results remain separately documented.

**Changes/evidence.** Methods temporal design; Results temporal assessment, sensitivity and mantis-ml sections; Discussion/Conclusions; Table 4/Figure 9; S4/S6; Additional files 11/12 with protocols, clinical ledger, baselines and full outputs.

### A-major-9. Versions, timestamps, locked environment, commands and actual supplementary checksums

**Comment.**

> Reproducibility should be strengthened
> The authors have made a serious effort to document reproducibility, which is appropriate for a BMC Bioinformatics manuscript. However, the current provenance information is still incomplete.
> The reproducibility manifest records only a subset of source URLs and versions and does not include retrieval timestamps for the recorded inputs.
> For a computational pipeline paper, I would strongly encourage the authors to provide, where possible:
> exact database versions or snapshot identifiers;
> source URLs or accession numbers;
> retrieval dates;
> checksums for local input files;
> a locked software environment or dependency file;
> the commands needed to reproduce the figures and tables;
> ideally, a containerized environment or an equivalent reproducible setup.
> I also recommend checking the consistency of the submitted supplementary files against the checksum manifest. In the material provided for review, the checksum associated with the expression-shortlist report does not appear to match the submitted Additional file 6. This may simply reflect a conversion from a repository Markdown file to the journal TXT file, but if so, that distinction should be documented.

**Response.** We supply four schema-checked canonical derived-input tables, preserved baseline prose, explicit database/cache/output options, frozen ClinGen/HGNC exports and exact tested dependency locks. Production numerical replay is distinguished from complete raw-source acquisition; restored donor-derived annotation/animal fields and originally unknown retrieval dates remain disclosed. The earlier clean Python 3.13.1/macOS-arm64 replay reproduced 28 TSVs, including eligibility/matching. The expanded temporal run verified 24 numerical source files (204,322,926 bytes) and a committed dependency/source/clinical freeze; a separate clean reconstruction reproduced all nine temporal TSVs and the manifest byte-for-byte. The latest full suite passed 354 tests with 17 existing warnings. Source versions, URLs, accessions, retrieval metadata where recorded, local SHA-256 and figure/table commands are included in Additional files 11/12 and S7. Linux/container parity is not claimed.

We confirmed the original mismatch: repository expression-shortlist Markdown hashes to `e046dbcd...`, while the submitted Additional file 6 TXT hashes to `13fc6ddd...`. The revised Additional file 10 instead hashes the actual delivered additional files, including freshly converted files 3/6; it excludes itself rather than claiming a self-hash. A separate package manifest records the delivered manuscript/response DOCX and PDF bytes, source hashes and source-analysis checkpoints. Both revised TXT files are generated from their named Markdown sources. Rendered document checks and a page location index accompany this revision. Large raw archives/clinical caches are not silently represented as distributed or backed up.

**Changes/evidence.** Methods “Reproducibility”; S7; Additional files 4/10/11/12; package manifest and response location index. The complete executable numerical replay remains in the repository.

### A-major-10. Retina/proxy expression, absence of hair-cell production data and proxy sensitivity

**Comment.**

> The production expression layer seems more retina-oriented than fully Usher-specific
> The manuscript appropriately emphasizes that Usher syndrome involves both retinal and auditory biology. However, the production expression layer does not appear to include cochlear hair-cell data. The GSE135913 cochlear analysis is instead treated as a post-hoc exploratory analysis based on two accepted fetal samples.
> At the same time, cerebellum is retained as a proxy tissue in the production score.
> I think the authors should explain this choice more clearly, because tissue specificity is presented as an important feature distinguishing UsherPipe from more general gene-prioritization tools.
> It would be useful to show how much the expression layer contributes to the ranking of established Usher genes, and whether removing the proxy tissue materially changes the results.
> Until direct auditory-cell data are incorporated into the production score, the term “Usher-specific tissue weighting” may be somewhat stronger than the available data support.

**Response.** We replace “Usher-specific tissue weighting” with explicit retina/proxy expression terminology. Cerebellum is an adult neural proxy, not auditory evidence. Production lacks direct cochlear hair-cell measurements; developmental or auditory-restricted genes can be disadvantaged when other evidence is also limited. The fetal GSE135913 analyses remain exploratory views within an already selected HIGH tier and do not repair this production gap.

Expression contributes 15.5–27.5% of individual Usher controls' weighted support. Removing cerebellum and recomputing source transforms yields whole-ranking ρ=0.9496 and median absolute shift 4.92 percentile points. HIGH is 60 versus 62, with only 37 shared genes (25 leave/23 enter): USH2A/MYO7A enter, CDH23 leaves and PCDH15 remains. We report this material dependence without selecting a revised score using control recovery. Source coverage and background-only Tau contributions are made explicit.

**Changes/evidence.** Methods expression layer/Table 1; Results “Expression dependence”; Discussion; S3; `results/usher_expression_diagnostics.tsv`, `baseline_comparison.tsv`, `per_gene_diagnostics.tsv`.

## Reviewer A — minor comments

### A-minor-1. Define seed-free at first introduction

**Comment.**

> The term “seed-free” should be defined clearly when it is first introduced. Known genes are not used in the raw composite score, but control behavior did influence the downstream cilia-signal gate.

**Response.** Abstract Results now defines raw scoring as using neither known disease training labels nor similarity seeds and immediately distinguishes the control-informed downstream gate. The fuller Methods definition remains explicit.

### A-minor-2. Use priority tiers rather than confidence tiers

**Comment.**

> I would consider replacing “confidence tier” with “priority tier.” HIGH, MEDIUM, and LOW are rule-based prioritization categories rather than calibrated statistical confidence levels.

**Response.** Revised manuscript and supplementary prose use “priority tier”, including figure captions. The legacy data column `confidence_tier` remains for schema compatibility, explicitly documented as a rule-based priority category rather than calibrated statistical confidence. Original frozen artifacts retain their historical wording.

### A-minor-3. Check canonical/HGNC terminology

**Comment.**

> Gene-identifier terminology should be checked carefully. The manuscript acknowledges that many displayed gene names are not formally validated current HGNC symbols, so wording such as “canonical identifier” should only be used where it is strictly accurate.

**Response.** We describe retained analysis IDs/labels, duplicate-symbol consolidation and 573 ENSG fallback labels without calling them validated current HGNC symbols. Additional file 1's description is corrected to retained analysis identifiers. Exact current HGNC mappings are used only for the comparator eligibility analysis; that does not retrospectively validate all production names.

### A-minor-4. Main-text control tier distribution

**Comment.**

> The distribution of established Usher and SYSCILIA controls across the final tiers should be included in the main Results section.

**Response.** Added 2 HIGH/7 MEDIUM Usher and 1 HIGH/27 MEDIUM SYSCILIA in Results, with zero LOW/excluded in both groups and all nine Usher traces in Table 3 (A-major-3).

### A-minor-5. Background sampling and random seed

**Comment.**

> Please state how the random background genes shown in the control-recovery analysis were sampled and provide the random seed.

**Response.** Figure 5 caption and S7 specify 500 non-control scored labels sampled without replacement, NumPy `default_rng(42)`. The revision figure code orders the 20,016 eligible background labels by retained Ensembl ID and exports sampled IDs and percentiles, making selection reproducible rather than dependent on database row order.

### A-minor-6. Permanent exact-version archive/DOI if possible

**Comment.**

> In addition to the GitHub commit, I would encourage archiving the exact software version used for the manuscript in a permanent repository with a DOI if possible.

**Response.** We identify the original submission version and exact revision/temporal analysis checkpoints, supply source/input/output hashes, dependency locks and numerical replay bundles, and hash the actual delivered files. No permanent DOI-bearing archive has been minted, and we do not imply that Git is equivalent to one. The reproducibility bundles and exact Git versions provide a version-specific record; DOI archival remains an optional additional deposit rather than a completed action.

**Changes/evidence.** Data availability; S7; Additional files 10-12; exact temporal outcome/audit checkpoint 736e16f and production revision checkpoint 0e1634a.

### A-minor-7. Consider shortening biological background

**Comment.**

> The biological background is thorough, but somewhat long for a BMC Bioinformatics paper. Some of the detailed discussion of Usher molecular biology could be shortened so that more emphasis can be placed on the computational design, validation strategy, benchmarking, and scoring assumptions.

**Response.** We retain the mechanistic rationale needed to understand sensory/ciliary scope and the distinction between actin-based stereocilia and true cilia. We clarify the scope paragraph and add the requested references, while expanding computational design, diagnostics and limitations. The mechanistic background explains why the biological target is broader than an Usher diagnosis, while the added computational design and validation sections address the methodological emphasis requested. Rendered layout/readability was checked in the revised document package.

## Reviewer B

### B-1. Add support for the ciliary/periciliary Background sentence

**Comment.**

> In Background, in the sentence beginning “Because the known Usher genes encode ciliary and periciliary proteins acting at hair-cell stereocilia, the photoreceptor connecting cilium, and the periciliary membrane complex, Usher syndrome may…”, a supporting reference should be added.

**Response.** The revised sentence describes several Usher proteins in stereociliary and photoreceptor connecting-cilium/periciliary complexes, supported by references [8, 9, 10, 11]. This avoids treating every Usher protein as exclusively ciliary and explicitly distinguishes actin-based stereocilia in the next paragraph. See Background “Usher syndrome as a specialized sensory ciliopathy”.

### B-2. Seed-free versus post-hoc gate calibration and HIGH interpretation

**Comment.**

> The manuscript describes UsherPipe as a seed-free approach, but the cilia-signal gate was defined after examining control and negative-control behavior. The authors note that this is a post-hoc calibration. It would be helpful to clarify how this affects the interpretation of control-recovery performance and the definition of the HIGH tier.

**Response.** We separate raw seed-free scoring from downstream control-informed calibration in the Abstract, Methods and Results. HIGH is a heuristic priority tier, not validated specificity or disease probability. Table 3 reports the control filtering losses directly, and matched comparator results cannot undo reused-positive calibration. See A-major-2/3 and Supplementary Methods S3/S5/S6.

### B-3. Justify final weights and discuss logistic-ranking sensitivity

**Comment.**

> The manuscript reports that alternative weighting strategies, including logistic-regression-based weighting, substantially changed the genome-wide ranking (default vs. logistic regression rank ρ = 0.646). These alternatives were not adopted due to concerns about control reuse and over-specialization. Additional justification for the final predefined weights would be useful, along with a discussion of how this degree of ranking sensitivity affects the robustness of candidate prioritization.

**Response.** We explain the limited design rationale for 0.20/0.20/0.15/0.15/0.15/0.15 and explicitly label exact values heuristic. Equal, individual-layer and leave-one-layer-out baselines and top25/50/100 persistence show that high global correlation does not ensure stable shortlists. Only 41 default top 100 genes persist in all 25 modest configurations; animal-only better recovers controls. Logistic rank ρ=0.646 remains a material alternative, rejected as production fitting because of control reuse/over-specialization, not because it is numerically equivalent. See A-major-5 and Results/S2/S4.

### B-4. Independent support for genuinely novel disease-gene prioritization

**Comment.**

> The recovery of known Usher and ciliary genes shows that the pipeline captures relevant disease biology. However, because the cilia-signal gate was calibrated using these same controls, it would be helpful to clarify what independent evidence supports UsherPipe’s ability to prioritize genuinely novel disease genes rather than mainly rediscovering genes with established Usher/ciliary characteristics.

**Response.** We added a retrospective, temporally separated later-association evaluation and report its weak results rather than relying solely on known-control recovery. The 45 cases were fixed from clinical/date evidence before expanded ranking; development controls and the previously inspected pilot cases were excluded. Forty-one were in the historical protein-coding universe, with four noncoding cases retained as end-to-end failures. Neither five-layer nor six-layer analogue recovered a principal case at top 100 or HIGH; top 1,000 recovery was 2/41 and 3/41. Median ascending percentiles were 46.23/44.95. No principal case reached HIGH under any of 23 schemes.

This is evidence about the limitations of later-association recovery under the stated historical conditions, not evidence of reliable novel Usher-gene discovery. It includes broader sensory/ciliopathy associations and distinguishes first-target reports after prior other-disease evidence. The score/gate was developed after the historical cutoff, several source channels differ from production, modern text retains uncertainty, and catalog ascertainment is non-exhaustive. We therefore retain a hypothesis-generation interpretation throughout Abstract, Discussion and Conclusions. The matched comparator analysis and control recovery also remain descriptive; neither validates clinical specificity or HIGH disease probability.

**Changes/evidence.** Methods/Results temporal sections; Table 4/Figure 9; S6; Additional file 12 with the 45-case roster, date/family evidence, exclusions, source contract, all outcomes and reconstruction code.

### B-5. Impact of excluding hair-cell expression and developmental bias

**Comment.**

> Because Usher syndrome affects cochlear hair cells, the authors could more directly discuss the impact of excluding hair-cell expression data from the production score. The exploratory fetal cochlear analyses are useful, but they do not contribute to the final composite score. It would be helpful to comment on whether the absence of suitable hair-cell data may disadvantage genes with more limited or developmentally restricted evidence.

**Response.** Main Methods/Results/Discussion now state the lack of production auditory-cell evidence and possible disadvantage for auditory-restricted or developmentally restricted genes. The fetal analyses do not enter the score, are based on two marker-selected samples and already selected HIGH genes, and do not establish adult expression or independent validity. We quantify expression contribution and substantial cerebellum-proxy sensitivity rather than implying complete Usher-tissue coverage. See A-major-10, S1/S3.

### B-6. General gene importance/research intensity versus disease specificity

**Comment.**

> A broader conceptual issue concerns the biological specificity of the composite score. Several evidence layers, such as gnomAD constraint, functional annotation completeness, and publication-based evidence, may reflect general gene importance or research intensity rather than disease-specific involvement in Usher syndrome. This is particularly relevant because housekeeping genes ranked very highly in the raw multi-evidence score (median at the 94.8th percentile). Clarifying how the composite score distinguishes general biological importance from evidence specifically supporting a role in Usher syndrome or related ciliopathies would strengthen the interpretation. The authors might also consider discussing whether additional disease-specific negative controls or specificity analyses could help quantify this distinction.

**Response.** We retain the 94.8th-percentile housekeeping failure and clarify that constraint, annotation depth and publication context can encode general importance or research effort. We added publication/GO-matched unrelated-disease comparators, correlations, source-completeness balance and common-layer/omission analyses. Separation remains with common layers but weakens to 55.6%/57.1% after animal/literature omission; clinical-label exclusions also overlap features relevant to the score. These checks do not make the composite Usher-specific or remove all ascertainment. Rigorously adjudicated clinical negatives remain unavailable. The separate later-association cohort has now been evaluated, with weak outcomes that do not establish disease-specific predictive validity. See A-major-4/7 and S3–S5.

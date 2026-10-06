# Point-by-point response to major revision

Working response, aligned with revised source manuscript and Supplementary Methods. Reviewer A denotes the downloaded report (10 major and 7 minor comments); Reviewer B denotes the six comments supplied in the correspondence. These labels must be mapped to the journal's numbering during packaging. Comment summaries below are abridged, not verbatim quotations. Section names are used until final journal pagination. Final DOCX/PDF, Additional-file hashes and DOI disposition remain packaging tasks; the corresponding responses explicitly distinguish them from completed work.

We thank both reviewers for identifying the distinction between transparent hypothesis generation and validated disease-gene prediction. We have clarified the target, separated raw scoring from control-informed HIGH calibration, reported final control tiers, added prespecified specificity and sensitivity analyses, and strengthened numerical replay. We preserve the submitted scores and weights rather than optimize them against the new comparisons. The revised conclusions do not claim independently validated novel Usher-gene discovery.

## Reviewer A — major comments

### A-major-1. Define the prediction task; separate Usher and SYSCILIA controls

**Response.** The primary task is genome-wide cilia/sensory-aware hypothesis generation for follow-up in the Usher context. It is neither an Usher-specific diagnostic classifier nor proof that broad ciliary genes cause the combined auditory–retinal phenotype. The Abstract, Background, Results and Conclusions now distinguish the nine established Usher controls from the 28 selected SYSCILIA controls. Raw median percentiles are 97.77% and 91.93%; final HIGH counts are two and one. The curated SYSCILIA subset is not a random validation sample. Pooled counts are retained only where describing the historical cached benchmark or original combined artifacts, with the group composition explicit.

**Changes/evidence.** Main Background “Usher syndrome as a specialized sensory ciliopathy”, Results “Internal control recovery” and Table 3; `results/control_rankings.tsv`, `results/control_tier_trace.tsv`; Supplementary Methods S4.

### A-major-2. Calibration and HIGH evaluation reuse the controls

**Response.** We agree. The downstream gate was selected after inspection of positive/housekeeping behavior, although the raw mean uses no disease training labels or similarity seeds. The Abstract and Methods now identify HIGH as a heuristically calibrated priority tier. We corrected the gate description to the actual direct-compartment/compendium source flags OR the positive-animal Q75 threshold, not any positive aggregate localization score. Internal control recovery and removal of housekeeping genes are calibration diagnostics, not independent specificity validation.

We investigated archives and executed a restricted historical reconstruction rather than stopping at a local-cache feasibility check. This four-layer pilot does not reproduce the complete production score or HIGH gate, and did not establish full temporal validation. No independent positive cohort was available in the executed study. We therefore adopt the reviewer's stated interpretation fallback and explicitly limit the claims.

**Changes/evidence.** Abstract; Methods “NULL-aware composite scoring”; Results “Restricted historical reconstruction”; Discussion “Limitations”; S3/S6; `temporal_extension/protocol.md`, `temporal_extension/report.md` and complete historical results.

### A-major-3. Show final control tiers, reasons for losses and threshold sensitivity

**Response.** The main Results now report Usher HIGH/MEDIUM/LOW/excluded = 2/7/0/0 and SYSCILIA = 1/27/0/0. Table 3 traces every Usher control. All seven non-HIGH Usher controls fail composite ≥0.70; WHRN and USH1G additionally fail the gate. None fails the layer-count criterion. With the gate and minimum three layers fixed, thresholds 0.60/0.65/0.70/0.75/0.80 yield 366/170/62/11/1 HIGH labels, retaining 5/4/2/0/0 Usher and 6/1/1/0/0 SYSCILIA controls. We report this full family without choosing a more favorable production threshold.

**Changes/evidence.** Main Table 3 and adjacent Results; `results/control_tier_trace.tsv`, `results/threshold_sensitivity.tsv`; S4.

### A-major-4. Raw housekeeping specificity failure; larger matched disease comparators

**Response.** We retain the raw housekeeping median of 94.8% as a specificity failure; the gate does not change raw rankings. We added a comparator analysis whose protocol and 111-pair roster were committed before outcome inspection. A Strong/Definitive ClinGen pool excluded recorded auditory/retinal/ciliary disease and HPO annotations and matched three unique genes per control on standardized log1p publication and GO counts, with a fixed 0.75-SD coordinate caliper and no reuse. The 27 and 84 comparator groups had median raw percentiles 64.21% and 60.30%, versus 97.77% and 91.93% for controls; pair concordances were 24/27 and 72/84.

None of the 111 matches was HIGH, but 110 already failed the raw score threshold, so this cannot be credited to gate specificity. The broader 420-gene pool retained three HIGH genes with residual sensory biology identified in a subsequent source check. They were not removed after outcomes. Coverage differs between groups; additional post-outcome common-observed-layer analyses preserve separation, whereas joint animal/literature removal reduces concordance to 55.6%/57.1%. We explicitly discuss matching only two measured research-burden quantities, shared curation, eligibility–feature overlap, and absence of verified biological negatives. These are descriptive specificity diagnostics, not clinical false-positive rates or novel-gene validation.

**Changes/evidence.** Results “Matched unrelated-disease comparators”; Discussion; S5; `phase3_spec.md`, `phase3_roster/`, `phase3_results/`, `phase4_results/fixed_pair_summary.tsv` and `matching_completeness_balance.tsv`.

### A-major-5. Heuristic weights, simple baselines and top-K persistence

**Response.** The exact weights are heuristic, not optimal. Methods now explains the modest five-percentage-point emphasis on constraint/expression and equal weighting of the other layers, while stating that this does not establish superiority. We added equal, all six individual-layer and all six leave-one-layer-out comparisons. Animal-only is a stronger internal recovery baseline: top100 contains four Usher/eleven SYSCILIA controls, compared with two/one under default. We report this unfavorable comparison directly.

Equal weighting gives whole-ranking ρ=0.9952 and 86 shared top100 genes. Across equal plus 24 modest perturbations, only 8 default top25, 17 top50 and 41 top100 genes persist in every configuration. The finite-family frequencies are not probabilities. Global correlations (0.9598–0.9994) coexist with meaningful shortlist movement; the earlier mean 0.8548 statistic is conditional on overlap, not whole-ranking stability. Logistic fitting (ρ=0.646 versus default; animal weight 0.903) remains a control-reuse diagnostic, not a production replacement.

**Changes/evidence.** Methods “NULL-aware composite scoring”; Results “Sensitivity analysis”; S2/S4; `results/baseline_comparison.tsv`, `candidate_membership_stability.tsv`, `control_rankings.tsv`.

### A-major-6. Sparse observed-layer means and completeness thresholds

**Response.** All 62 HIGH labels actually have five/six layers (33/29); none has three/four. Requiring four or five retains all 62, while six retains 29. Nevertheless, eight one-layer genes appear in the raw top100 and are all LOW. Composite score correlates with observed-layer count (ρ=0.2402; n=20,053). We retain per-gene counts/source flags and explain that available-layer means avoid an automatic missingness penalty but do not equalize evidential strength or quantify uncertainty. The historical audit also exposes sparse high-ranking genes; this limitation is not dismissed because production HIGH is well-covered.

**Changes/evidence.** Results “Impact of missing data handling”; Discussion; S4/S6; `results/evidence_completeness.tsv`, `threshold_sensitivity.tsv`, `per_gene_diagnostics.tsv`; `phase4_results/historical_topk_completeness.tsv`.

### A-major-7. Inter-layer overlap and within-layer combination

**Response.** We added pairwise observed-gene correlations with sample sizes, all six leave-one-layer-out rankings and matched-pair omissions. Annotation–literature is the strongest correlation (ρ=0.3704; n=19,114); moderate correlations are not evidence of independent biology. Animal/literature omissions weaken matched separation, especially jointly. Methods and S3 now describe expression source/ordinal semantics and available-component normalization, annotation missing-subcomponent zero contribution, localization HPA reliability/embedded-list handling, animal term union and literature tier precedence. We corrected descriptions that conflated Approved/Uncertain antibody evidence with computational predictions or embedded lists with newly acquired proteomics datasets.

**Changes/evidence.** Main Methods “Evidence layers”; Results missingness/sensitivity/comparator sections; S3–S5; `results/layer_correlations.tsv`, `baseline_comparison.tsv`; `phase4_results/fixed_pair_sensitivities.tsv`.

### A-major-8. Seed-confounded mantis-ml benchmark; temporal or simple baselines

**Response.** The cached-output comparison retains the 33/35 shared-positive seed overlap and only two non-seeds, without claiming head-to-head novel-gene performance or rerunning mantis-ml training. Simple baselines are now reported; animal-only outperforms the integrated score on selected-control recovery.

We also executed an archive-only pilot with cutoff 2020-12-31 and three manually selected later human associations: CEP162, CFAP20 and LRRC45. Pre-cutoff ciliary biology was allowed, and initial candidates are distinguished from later causal support. Default historical ranks were 8,289/11,004/253 among 19,033 scored genes; none entered top100. Reconstruction included historical constraint, partial GO annotation and HPA protein/localization, with animal/literature unavailable and no HIGH assignments. All three lacked retinal HPA observations; eleven historical top100 genes were one-layer and 83 lacked localization. GTEx/HPA RNA archives were available but not fully integrated under the restricted contract. This is a bounded archive/scoring diagnostic, not proof of full temporal validity or infeasibility. We explicitly retain the limitation rather than relabel the pilot as independent validation.

**Changes/evidence.** Results “Comparison with mantis-ml”, “Sensitivity analysis” and “Restricted historical reconstruction”; S4/S6; temporal protocol, source/date audit and full rank outputs.

### A-major-9. Versions, timestamps, locked environment, commands and actual supplementary checksums

**Response.** We strengthened numerical reproducibility with four schema-checked, canonical derived-input tables; preserved original baseline prose; exposed database/cache/input/output options; froze the otherwise mutable ClinGen/HGNC exports; and supplied dated archive URLs/hashes and an exact tested Python dependency lock. A clean Python 3.13.1 macOS arm64 environment passed dependency compatibility and the 343 existing tests. Phase2, frozen Phase3 outcomes, the archival pilot and post-review diagnostics reproduced 28 TSVs byte-for-byte, including the five eligibility/matching tables. This bundle includes restored donor-derived annotation/animal fields: it reproduces numerical analyses, not every original raw acquisition. Unknown original retrieval dates are explicitly unknown.

The checksum mismatch is confirmed: the original manifest hashes repository Markdown (`e046dbcd…`), whereas submitted Additional file 6 TXT hashes to `13fc6ddd…`. The source and converted-file records are now separated in a conversion audit. **Packaging outstanding:** the revised final TXT/JSON/DOCX/PDF and checksum manifest have not yet been assembled in this Phase 4 source response. Phase 5 will hash the actual delivered files after conversion and add final artifact references. We do not claim those final-file checks are already complete.

**Changes/evidence.** Methods “Reproducibility”; S7; `replay_inputs/manifest.json`; `reproducibility/requirements.lock.txt`, `README.md`, `numerical_replay_verification.json`, `submission_conversion_audit.json`; replay/source/figure command options.

### A-major-10. Retina/proxy expression, absence of hair-cell production data and proxy sensitivity

**Response.** We replace “Usher-specific tissue weighting” with explicit retina/proxy expression terminology. Cerebellum is an adult neural proxy, not auditory evidence. Production lacks direct cochlear hair-cell measurements; developmental or auditory-restricted genes can be disadvantaged when other evidence is also limited. The fetal GSE135913 analyses remain exploratory views within an already selected HIGH tier and do not repair this production gap.

Expression contributes 15.5–27.5% of individual Usher controls' weighted support. Removing cerebellum and recomputing source transforms yields whole-ranking ρ=0.9496 and median absolute shift 4.92 percentile points. HIGH is 60 versus 62, with only 37 shared genes (25 leave/23 enter): USH2A/MYO7A enter, CDH23 leaves and PCDH15 remains. We report this material dependence without selecting a revised score using control recovery. Source coverage and background-only Tau contributions are made explicit.

**Changes/evidence.** Methods expression layer/Table 1; Results “Expression dependence”; Discussion; S3; `results/usher_expression_diagnostics.tsv`, `baseline_comparison.tsv`, `per_gene_diagnostics.tsv`.

## Reviewer A — minor comments

### A-minor-1. Define seed-free at first introduction

**Response.** Abstract Results now defines raw scoring as using neither known disease training labels nor similarity seeds and immediately distinguishes the control-informed downstream gate. The fuller Methods definition remains explicit.

### A-minor-2. Use priority tiers rather than confidence tiers

**Response.** Revised manuscript and supplementary prose use “priority tier”, including figure captions. The legacy data column `confidence_tier` remains for schema compatibility, explicitly documented as a rule-based priority category rather than calibrated statistical confidence. Original frozen artifacts retain their historical wording.

### A-minor-3. Check canonical/HGNC terminology

**Response.** We describe retained analysis IDs/labels, duplicate-symbol consolidation and 573 ENSG fallback labels without calling them validated current HGNC symbols. Additional file 1's description is corrected to retained analysis identifiers. Exact current HGNC mappings are used only for the comparator eligibility analysis; that does not retrospectively validate all production names.

### A-minor-4. Main-text control tier distribution

**Response.** Added 2 HIGH/7 MEDIUM Usher and 1 HIGH/27 MEDIUM SYSCILIA in Results, with zero LOW/excluded in both groups and all nine Usher traces in Table 3 (A-major-3).

### A-minor-5. Background sampling and random seed

**Response.** Figure 5 caption and S7 specify 500 non-control scored labels sampled without replacement, NumPy `default_rng(42)`. The revision figure code orders the 20,016 eligible background labels by retained Ensembl ID and exports sampled IDs and percentiles, making selection reproducible rather than dependent on database row order.

### A-minor-6. Permanent exact-version archive/DOI if possible

**Response.** The revision preserves exact Git checkpoints, source hashes, dependency lock and numerical replay inputs. **Packaging outstanding:** final release archival and DOI disposition follow final artifact assembly. No DOI has been minted and none is claimed. A DOI-bearing archive, if created, will identify the final verified version rather than an intermediate draft; otherwise the final response will state its absence and provide the exact Git version.

### A-minor-7. Consider shortening biological background

**Response.** We retain the mechanistic rationale needed to understand sensory/ciliary scope and the distinction between actin-based stereocilia and true cilia. We clarify the scope paragraph and add the requested references, while expanding computational design, diagnostics and limitations. We have not removed useful biological discussion solely to shorten the manuscript; the comment is an editorial suggestion rather than a requirement for a particular length. Final layout/readability will be reviewed during packaging.

## Reviewer B

### B-1. Add support for the ciliary/periciliary Background sentence

**Response.** The revised sentence describes several Usher proteins in stereociliary and photoreceptor connecting-cilium/periciliary complexes, supported by references [8, 9, 11, 16]. This avoids treating every Usher protein as exclusively ciliary and explicitly distinguishes actin-based stereocilia in the next paragraph. See Background “Usher syndrome as a specialized sensory ciliopathy”.

### B-2. Seed-free versus post-hoc gate calibration and HIGH interpretation

**Response.** We separate raw seed-free scoring from downstream control-informed calibration in the Abstract, Methods and Results. HIGH is a heuristic priority tier, not validated specificity or disease probability. Table 3 reports the control filtering losses directly, and matched comparator results cannot undo reused-positive calibration. See A-major-2/3 and Supplementary Methods S3/S5/S6.

### B-3. Justify final weights and discuss logistic-ranking sensitivity

**Response.** We explain the limited design rationale for 0.20/0.20/0.15/0.15/0.15/0.15 and explicitly label exact values heuristic. Equal, individual-layer and leave-one-layer-out baselines and top25/50/100 persistence show that high global correlation does not ensure stable shortlists. Only 41 default top100 genes persist in all 25 modest configurations; animal-only better recovers controls. Logistic rank ρ=0.646 remains a material alternative, rejected as production fitting because of control reuse/over-specialization, not because it is numerically equivalent. See A-major-5 and Results/S2/S4.

### B-4. Independent support for genuinely novel disease-gene prioritization

**Response.** We do not have independent novel Usher-positive validation and now say so directly. The new matched comparator study is frozen before outcomes but retains original positives and gate, with shared-curation caveats; it cannot demonstrate novel discovery. The executed archival pilot is partial, manually ascertained and not full production validation; none of three default examples reaches top100. Recovery of established biology supports plausibility but does not estimate sensitivity for novel genes or specificity of HIGH. Abstract, Discussion and Conclusions accordingly define the output as hypotheses for follow-up. See A-major-2/4/8, S5/S6.

### B-5. Impact of excluding hair-cell expression and developmental bias

**Response.** Main Methods/Results/Discussion now state the lack of production auditory-cell evidence and possible disadvantage for auditory-restricted or developmentally restricted genes. The fetal analyses do not enter the score, are based on two marker-selected samples and already selected HIGH genes, and do not establish adult expression or independent validity. We quantify expression contribution and substantial cerebellum-proxy sensitivity rather than implying complete Usher-tissue coverage. See A-major-10, S1/S3.

### B-6. General gene importance/research intensity versus disease specificity

**Response.** We retain the 94.8th-percentile housekeeping failure and clarify that constraint, annotation depth and publication context can encode general importance or research effort. We added publication/GO-matched unrelated-disease comparators, correlations, source-completeness balance and common-layer/omission analyses. Separation remains with common layers but weakens to 55.6%/57.1% after animal/literature omission; clinical-label exclusions also overlap features relevant to the score. These checks do not make the composite Usher-specific or remove all ascertainment. Additional rigorously adjudicated negatives and independent positives remain future validation rather than completed analyses. See A-major-4/7 and S3–S5.

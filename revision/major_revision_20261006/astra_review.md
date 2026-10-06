# Independent review of the major-revision evidence

Reviewed on 6 October 2026, branch `revision/major-revision`, HEAD `c9834c6`.
This report is independent review, not an implementation or a replacement analysis protocol.
Persistent report language is English under the repository instructions.

## Verdict

**Phase 4 writing can start, but “all reviewer requests fulfilled” and “all experimental work complete” would be premature.** Phase 2 provides substantial, correctly qualified answers to the requested diagnostic analyses. Phase 3 is a useful new comparator experiment. Neither independently validates the calibrated HIGH gate or novel Usher-gene prediction. The historical extension is an archive-feasibility demonstration and exploratory retrospective case series of a materially different score; it cannot settle those validation questions.

The minimum remaining work is: correct the actual scoring/gate description; incorporate the unfavorable sensitivity and baseline results prominently; add small fixed-roster missingness/source-ablation checks and historical coverage diagnostics if that series is retained; and provide an executable, distributable reproduction package. A broader temporal study would strengthen the paper, but the original reviewer explicitly offers simpler baselines and cautious interpretation as alternatives. Incorporating cochlear data into production, shortening Background, and obtaining a DOI are suggestions, not unconditional reviewer requirements.

## Review basis and verification

I read the original `word/document.xml` in `/Users/gbanyan/Downloads/Reviewer_comment.docx`: ten major and seven minor comments. I also reviewed all six original pasted comments, rather than relying solely on `reviewer_crosswalk.tsv`. Below, A refers to the DOCX report and B to the pasted report; these are source labels, not assigned journal reviewer numbers.

I inspected the specifications, reports, manifests, result tables, all seven revision scripts, relevant production transforms and tiering, the recovery documentation, and both submitted manuscript DOCX variants. The method-description discrepancies below appear in both submitted DOCX files, not only in the Markdown draft.

Independent read-only checks confirmed all output hashes in the Phase 2, Phase 3 roster/outcome, and temporal results manifests and all protected hashes in `input_manifest.json`. Git records show the Phase 3 plan, roster, and results in separate successive commits, and the temporal protocol committed at `377eae3` before results at `c9834c6`. This supports the recorded freeze sequence; it does not establish prospective validation or prove that authors had never encountered case outcomes before the study. I inspected the DuckDB schema before opening score queries read-only. No production file, result artifact, script, or database was changed. I did not rerun the test suite; the reported 343 passes remain the implementation team's result, not a new independent test claim.

Additional arithmetic below was computed in memory during review from frozen files and read-only database queries. It is explicitly **review-time exploratory diagnostics**, not prespecified Phase 3/temporal evidence. It must be reproduced and recorded separately before use as a manuscript result.

## Essential corrections before submission

### 1. The written HIGH rule and localization model do not describe the implemented method

**Requirements:** A2, A3, A7, A9; B2.

**Evidence:** `manuscript/draft.md:116` describes CiliaCarta as proteomics evidence and 0.6× as a computational-prediction weight. The production code instead treats HPA categories as antibody-staining reliability and embedded lists as curated compendia (`src/usher_pipeline/evidence/localization/transform.py:58`, `:143`, `:265`). The manuscript's gate is “non-zero cilia-proximity localization score” (`manuscript/draft.md:134`), whereas production requires one of five compartment flags or either curated-compendium membership, OR the animal Q75 route (`src/usher_pipeline/evidence/localization/models.py:48`, `:76`; `src/usher_pipeline/output/tiers.py:67`, `:109`). Positive adjacent-localization scores alone do not pass. The two submitted DOCX files contain the same descriptions in their localization and HIGH-gate paragraphs.

**Consequence:** An independent implementation following the manuscript need not reproduce the reported 62-gene HIGH list. Review-time calculation with the manuscript's positive-localization rule gives **63 genes**, adding **TUBB2B**. This is a factual reproducibility problem, not merely terminology.

**Minimum correction:** State the exact source-level OR rule and animal quantile population/interpolation, distinguish adjacent localization from gate-qualifying evidence, distinguish HPA reliability from modality, and describe curated-list evidence without calling it a directly measured proteomics channel. Include the within-layer formulas, missing-subcomponent rules, and animal MGI/IMPC union logic. Also remove the suggestion that animal evidence is necessarily independent of human knowledge (`manuscript/draft.md:118`): cross-species observations can arise from the same disease-driven research and curation. Update manuscript, supplementary methods, and captions consistently; preserve the production model.

### 2. Remaining validation limits must govern the Abstract, Results, and rebuttal

**Requirements:** A1–A5, A8, A10; B2–B6.

**Evidence:** Only 2/9 Usher and 1/28 SYSCILIA controls reach HIGH (`phase2_report.md:26`). All seven other Usher controls fail the score threshold; WHRN and USH1G additionally fail the gate (`phase2_report.md:31`). Animal-only top-100 recovery exceeds the composite, and LOO animal retains no positive control in the top 100 (`phase2_report.md:64`, `:78`). Equal/modest weights have high whole-universe correlations but top-100 overlaps of 59–97, with only 41/100 default genes retained in every tested modest-weight configuration (`phase2_report.md:90`). Removing cerebellum changes HIGH from 62 to 60 with only 37 shared genes (`phase2_report.md:138`).

**Consequence:** These analyses address the reviewers, but do not support an optimal/especially robust integrated model, an independently validated HIGH tier, or superior gene discovery. The new comparator and historical analyses do not repair original control reuse. The newly high whole-universe correlations are a different estimand from the original shared-top-100 conditional Spearman; replacing the latter with the former without explanation would mislead.

**Minimum correction:** Present separate Usher/SYSCILIA raw and final-tier results in main Results, the control filtering trace, the stronger single-layer baseline, finite-family top-K stability, and large proxy-membership change. Justify the default as a retained heuristic biological configuration rather than a data-selected optimum. Use “priority tier”; define seed-free for the raw score only. State plainly that discovery of novel Usher genes and independent sensitivity/specificity of HIGH remain unvalidated. Label expression as a restricted retina/proxy-oriented layer; explain why available production data did not include hair cells and how that can disadvantage developmental or cell-restricted genes. The reviewers do **not** require adding the two-sample fetal analysis to production.

### 3. Reproducibility remains materially incomplete despite excellent local hash checks

**Requirements:** A9, A minor 6.

**Evidence:** Recovery still requires an ignored historical donor database for derived annotation and animal fields (`docs/submission-database-recovery.md:48`, `:55`); this is not an end-to-end reconstruction from public raw inputs. The Phase 3 live exports likewise require ignored frozen caches (`phase3_report.md:17`). `pyproject.toml:25` uses open lower bounds; `uv.lock` was untracked when review began. Neither an installed-version inventory nor numerical agreement reconstructs a locked environment (`docs/submission-database-recovery.md:92`).

The temporal report says to use clean cache/output directories (`temporal_extension/report.md:85`, `:93`), but the downloader hardcodes both directories and only accepts `--preserve-completed-only` (`scripts/revision_temporal_download.py:10`, `:54`), while analysis has no CLI and rejects the already committed `results` directory (`scripts/revision_temporal_analysis.py:24`, `:86`). Thus the printed commands cannot replay the temporal analysis from the published checkout without moving/deleting tracked artifacts or editing code. The verifier also hardcodes paths and overwrites `verification.json` (`scripts/revision_temporal_verify.py:11`, `:75`). The 51 probes span follow-up JSON records not replayed by the default 17-entry probe script. Phase 3 outcome replay additionally requires its supplied roster path to be committed in HEAD (`scripts/revision_phase3_outcomes.py:41`), which is not satisfied by an arbitrary new scratch roster directory.

**Minimum correction:** Provide a clean replay mode with explicit input/cache/output paths and separate verification output; document how to use the original frozen roster without an extra Git commit. Archive the essential frozen source/derived inputs or a distributable minimal scoring-input package with schema, license/access instructions, hashes, and source limitations. Supply an actual tested dependency lock or equivalent environment and exact figure/table commands. Make replay independent of the mutable manuscript file: current protected hashes intentionally reject a manuscript edited in Phase 4, so use an immutable submission-baseline copy when verifying later revision analyses. Report missing historical retrieval dates honestly, separate original acquisition from recovery/retrieval of archives, and preserve original files while creating a new package manifest.

Additional file 10 hashes the repository Markdown expression report (`e046db...`), while the submitted Additional file 6 TXT has hash `13fc6d...` (`input_manifest.json`). Recording both is useful but does not resolve the reviewer's discrepancy by itself. Document the source-to-delivered-file conversion and verify hashes of the actual new journal files. A DOI is desirable if feasible, not mandatory; a reproducible accessible package is the immediate need.

## Minimum extra analyses or audits recommended

### 4. Quantify comparator missingness imbalance on the existing frozen pairs

**Requirements:** A4, A6, A7; B6.

**Evidence:** Matching correctly uses two raw nuisance covariates, not outcome scores, with maximum-cardinality/no-replacement assignment and a per-coordinate caliper (`scripts/revision_phase3_roster.py:66`, `:93`, `:155`). The code and report appropriately distinguish a descriptive comparator sample from true negatives. However, balance on publication and GO counts does not balance the observed-layer denominator (`phase3_report.md:53`). From `results/control_tier_trace.tsv` and `phase3_results/eligible_gene_outcomes.tsv`:

| Group | Four layers | Five layers | Six layers | Localization observed |
| --- | ---: | ---: | ---: | ---: |
| Usher controls | 0 | 7 | 2 | 2/9 |
| Usher matches | 1 | 10 | 16 | 17/27 |
| SYSCILIA controls | 0 | 2 | 26 | 28/28 |
| SYSCILIA matches | 3 | 25 | 56 | 61/84 |

Missing localization removes its weight from the denominator, whereas an observed zero retains it. This can favor Usher genes relative to more completely observed comparators, with a different direction for SYSCILIA. All groups have a non-NULL default score, so the default percentile population itself is the same 20,053 genes; the concern is gene-specific score denominators. Single-layer comparisons have different universes and coverage (`scripts/revision_phase3_outcomes.py:71`; `phase3_report.md:103`), making cross-layer median percentiles an imperfect measure of added predictive value.

**Review-time exploratory check:** On the unchanged 111 pairs, I recomputed weighted means using (a) only layers observed in both genes of each pair and (b) excluding localization. I also removed animal/literature separately and together, without refitting or rematching:

| Pair score comparison | Usher wins / 27 | SYSCILIA wins / 84 |
| --- | ---: | ---: |
| Original default | 24 (88.89%) | 72 (85.71%) |
| Common observed layers within each pair | 23 (85.19%) | 75 (89.29%) |
| LOO localization | 23 (85.19%) | 73 (86.90%) |
| LOO animal | 21 (77.78%) | 64 (76.19%) |
| LOO literature | 18 (66.67%) | 55 (65.48%) |
| Exclude animal and literature | 15 (55.56%) | 48 (57.14%) |

There were no ties in these comparisons. Each control has three matches, so pair-average and control-average concordance agree. Shared-layer comparisons use pair-specific scoring functions and should **not** be presented as a new genome-wide ranking/AUC. They show that unequal missingness does not explain all separation, while animal/literature carry much of it.

**Minimum addition:** Record the completeness/source-coverage table and reproduce the common-observed-layer and joint animal/literature ablation results in a separate post-outcome sensitivity artifact with hashes. Keep the roster, caliper, and production model fixed; do not select the most favorable specification. This is a small diagnostic, not a request to redesign the study.

The modern ClinGen/HPO roster has additional ascertainment limits: it requires well-curated Strong/Definitive associations and excludes any eye descendant and several broader branches (`phase3_spec.md:18`, `:28`). These are relatively easy phenotype-separated comparators, and the historical well-known positives may have more disease-focused model experiments even after matching total publications. Classification date is not first-association date; the current export cannot create a temporal test. The post-outcome biological explanation of the three HIGH comparators is appropriate only as disclosed residual overlap, not as a rescue of apparent false positives. Preserve all three; do not recode or remove them. A systematic audit of all 420 genes, a broader exclusion-rule sensitivity, or matched model-organism study intensity would be optional strengthening if strong specificity claims were retained.

### 5. The historical series needs explicit coverage and normalization diagnostics

**Requirements:** A6–A8, A10; B3–B5, if the historical results are presented.

**Evidence:** The historical score keeps annotation's 0.15 inter-layer weight in the denominator but only the 0.5 GO subcomponent in the numerator (`scripts/revision_temporal_analysis.py:118`, `:144`; `src/usher_pipeline/evidence/annotation/transform.py:85`, `:132`). Whole missing layers are renormalized away, but missing annotation subcomponents are not. This is faithful to the production function, not a coding error; it nevertheless changes the available score scale and the relative effect of research coverage. The frozen protocol acknowledges non-equivalence (`temporal_extension/protocol.md:25`), and the report notes it (`temporal_extension/report.md:71`), but its consequences are not quantified.

**Review-time exploratory checks:** Counting the existing historical ranking and components tables gives **10/25 top-25 genes supported by one layer** and **11/100 top-100 genes supported by one layer**. Among the top 100, **83 lack localization**. In the accepted HPA v20 raw file, retinal observations cover only 108 source genes before historical-universe restriction; none of CEP162, CFAP20, or LRRC45 has accepted retinal observations. CEP162/LRRC45 expression comes from cerebellum relative to testis/fallopian-tube measurements; CFAP20 has no accepted panel expression. The published components at `historical_components.tsv:1122`, `:6924`, and `:12388` omit these tissue-level details.

**Correction (6 October 2026):** The original count of 63 included only genes missing localization alone. Another 20 also lack other layers (10 expression/localization, 8 expression/annotation/localization, and 2 gnomAD/annotation/localization), giving 83/100 missing localization in total. The 11/100 single-layer count is unchanged.

To illustrate denominator dependence, restricting the already computed scores to the 7,824 complete-four-layer genes moves LRRC45 from 253/19,033 to **27/7,824**, while excluding CFAP20 entirely. This is a changed comparison population, **not improved recovery**. Giving the GO-only component its full available-subcomponent scale instead moves LRRC45 to **627/19,033**; omitting annotation yields **530/18,535**. These are exploratory sensitivity checks, not replacement scores. The negative historical results should remain visible under the frozen analysis.

**Minimum addition:** Publish per-tissue coverage and case source provenance; report historical top-K evidence-count/missing-pattern composition; explicitly explain that observed-zero HPA localization and wholly missing localization have different effects. If historical ranking performance receives substantive interpretation, add predeclared follow-up coverage-stratified and partial-annotation-policy sensitivities, keeping frozen primary results untouched and labeling the changed populations. Do not treat “no top-100 cases” as a failure of the six-layer production model, or a good complete-case rank as temporal success. The current reconstruction is most defensibly an availability/scoring diagnostic with illustrative cases.

### 6. The bounded archival scope is a choice, not an exhausted feasibility limit

**Requirements:** A8; B4. This is conditional strengthening, not a reviewer-imposed obligation to reconstruct every historical layer.

**Evidence:** `temporal_extension/report.md:23` records actual MGI/MP files, available ZFIN and IMPC inputs, and incomplete gene2pubmed retrieval. The HPA v20 RNA file was **fully downloaded**, not merely shown in an index (`temporal_extension/final_source_probes.json:105`). Most importantly, GTEx v8 is both pre-cutoff and the same configured production source (`src/usher_pipeline/evidence/expression/models.py:80`; `manuscript/draft.md:112`), yet was omitted as a pilot-scope choice (`temporal_extension/report.md:32`). Its omission cannot be justified by the HPA RNA measurement-contract difference. The protocol's statement that GTEx is unavailable “in this restricted reconstruction” (`protocol.md:24`) should not be shortened to an assertion of archival unavailability.

Accepting GO as a partial substitute while excluding every animal input because a full HCOP-weighted equivalent was not reconstructed is a defensible bounded-pilot design, but not a demonstration that no more informative historical comparison can be done. Phase 2 already identifies animal evidence as the strongest control-recovery component. Omitting it and the literature channel sharply changes the question under study. A 150 MiB download cap or a slow interrupted transfer (`scripts/revision_temporal_download.py:42`) is an operational bound, not scientific infeasibility.

**Minimum disposition:** Explicitly decide whether this is only an exploratory archival pilot. If so, retain that modest role and answer A8 primarily with the complete simple-baseline analysis; do not claim temporal validation or comprehensive infeasibility. If a stronger temporal response is intended, the next practical experiment is an appended, frozen-before-execution **GTEx v8 augmentation**, preserving historical IDs, cases and weights and recomputing source-specific Tau/ranks. Validate dated file identity first; this review did not independently establish the original cached GTEx file's release authenticity. A separately named historical animal-only or partial-animal baseline using dated ortholog links is also feasible to investigate, with confidence assumptions disclosed; absence of old HCOP weights prevents exact equivalence, not every useful baseline. Do not silently assign current confidence or modify the original frozen reconstruction. None of these additions by itself establishes full-pipeline or HIGH-tier validation.

## Optional future validation and selection limitations

The three cases were frozen before historical rankings, a meaningful protection against selecting cases based on these particular results. Nevertheless, they were manually ascertained and heterogeneous. The protocol includes an initial CFAP20 candidate report and a putative LRRC45 association, but excludes SLC30A7 partly because the series already has a putative case (`temporal_extension/protocol.md:13`, `:15`). That is a bounded editorial selection, not a reproducible disease-cohort eligibility rule. Freezing it does not make the sample representative. The cases are later human retinal/ciliopathy reports, not three new Usher genes, and pre-cutoff ciliary biology is allowed.

The exclusion of TMEM218 using the earlier online date and the distinction between first candidate report and later confirmation are good safeguards. `date_evidence.json` stores primary XML date evidence for three papers, but an exhaustive earliest-paper/preprint search for all included/excluded genes is not demonstrated. The reports appropriately refrain from claiming exhaustive first-association dates. Stronger validation would require systematic ascertainment, uniform eligibility/association-strength rules, a documented preprint/date search, sufficient independent positives, and an evaluation plan not selected using those outcomes. Novel HIGH-tier performance would also require an independent evaluation of that gate itself; it was never applied temporally (`protocol.md:9`, `:32`). Retrospectively withholding some already inspected controls would not erase the existing reuse.

These are future study requirements **if the authors want a validated predictive-performance claim**. A2 explicitly permits consistently describing HIGH as heuristically calibrated if independent evaluation is not feasible; A8 explicitly allows simple baselines instead of temporal validation. They should not be converted into mandatory new studies for this cautious hypothesis-generation paper.

## Coverage of every original comment

| Original request | Assessment and remaining action |
| --- | --- |
| A major 1: prediction target, separate 9 Usher/28 SYSCILIA | Evidence ready. Adopt one cilia/sensory-aware hypothesis-generation target and separate groups throughout, including Abstract/conclusions where recovery is summarized. |
| A major 2: calibration versus evaluation | Not independently resolved. Use the reviewer's heuristic-tier fallback; neither new comparators nor temporal pilot validates HIGH. |
| A major 3: actual tiers, failed conditions, threshold sensitivity | Substantially fulfilled analytically by trace and threshold grid. Main-text presentation pending; correct the gate formula. |
| A major 4: larger matched disease comparators | Substantive response completed. Add small missingness/source diagnostics and preserve operational-comparator caveats. No clinical FPR claim. |
| A major 5: weights, simple/LOO baselines, top25/50/100 persistence | Requested analyses present. Justify heuristic choice; report unfavorable animal-only and shortlist-stability findings. |
| A major 6: sparse evidence, higher minimum count, completeness association | Production analysis answers it: all HIGH have five/six layers; four/five-layer minima retain all. Raw top-100 sparse artifacts must remain visible. Add analogous context if using temporal ranks. |
| A major 7: inter-layer correlation, LOO, within-layer methods | Correlation and LOO done. Correct factual within-layer descriptions and explain shared underlying knowledge; low correlations do not prove independence. |
| A major 8: mantis limitations, possible temporal or simpler baselines | Simpler-baseline alternative is fulfilled analytically. Historical pilot is additional exploratory work, not successful temporal validation or proof of impossibility. |
| A major 9: versions, URLs, dates, hashes, lock, commands, delivered-file checksum | Still open. Improved hashes are useful but cache-dependent inputs, replay interfaces, environment lock, and final conversion/checksum mapping need work. |
| A major 10: expression contribution and proxy removal | Requested diagnostics done. Discuss substantial proxy dependence and absence of auditory-cell support; production hair-cell incorporation is not explicitly demanded. |
| A minor 1: seed-free | Define at first use, including Abstract; downstream calibration remains control-informed. |
| A minor 2: confidence versus priority | Apply terminology consistently to prose/tables/figures; explain any retained legacy schema field name. |
| A minor 3: HGNC/canonical identifiers | Replace inaccurate “canonical” wording, including Additional file 1 caption (`manuscript/draft.md:341`); report retained Ensembl IDs/analysis labels and unresolved symbols accurately. |
| A minor 4: main-text final-tier distribution | Same ready evidence as major 3; main Results still pending. |
| A minor 5: random background sampling/seed | `scripts/paper_figures.py:265` computes percentiles, excludes positive controls, then `:292` samples up to 500 without replacement using NumPy default_rng(42). Document the actual eligible background population and input ordering/version for exact sampled identities. |
| A minor 6: permanent archive/DOI if possible | Package/release task remains; DOI is conditional, not an absolute requirement. |
| A minor 7: consider shortening biology | Optional editorial decision; preserve necessary rationale while reducing repetition if useful. |
| B1: supporting reference for the opening ciliary/periciliary claim | Still pending. Attach a source supporting the specific hair-cell/photoreceptor/periciliary claim and check sentence scope; a generic ciliopathy citation may not support every clause. |
| B2: seed-free gate calibration and HIGH | Same corrections as A2; explicitly qualify control-recovery interpretation. |
| B3: logistic rank shift and predefined weights | Preserve default-versus-logistic rho=0.646 context and distinguish it from new whole-universe modest-perturbation results. No optimized-weight claim. |
| B4: independent novel disease-gene evidence | Not supplied. Say so directly; case anecdotes and new negative comparators do not substitute. |
| B5: production cochlear exclusion and developmental bias | Direct discussion required; additional production cochlear integration is optional. Explain source/sample limitations without treating NULL or low fetal expression as absence of function. |
| B6: general importance/research intensity versus biological specificity | Comparator analysis is useful but selected; include matching/missingness limits and disease-focused channel dependence. Retain raw housekeeping specificity failure. |

## Recommended phase boundary

Proceed with Phase 4 drafting now, using the original production model and all negative results. Before freezing revised Results, record the small fixed-pair diagnostics and historical tissue/missingness summaries if temporal results remain. Resolve replay/package defects before Phase 5 submission. Treat a richer temporal reconstruction, new independent positive cohort, and production auditory-cell integration as optional further study unless the authors elect to make stronger predictive claims. The rebuttal should distinguish **request answered by new analysis**, **request answered by corrected description/limited claims**, and **independent validation still absent** rather than marking all requests generically complete.

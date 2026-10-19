# Independent readability and response-adequacy review — 20 October 2026

Reviewer: OpenAI GPT-6 Astra, xhigh reasoning. This is an internal model review of the current sources, not human clinical sign-off or external peer review.

I read the complete current `rebuttal.md`, `manuscript/draft.md`, `manuscript/supplementary_methods.md` and `cover_letter_revision.md`, after reading `AGENTS.md` and `CURRENT_STATE.md`. The assessment below compares the responses with the original Editor, Reviewer 2 and 23 Reviewer 1/3 comments. Line numbers refer to those current Markdown sources. Only this new report was written; the source documents and 19 October upload package were not edited.

## Overall verdict

**The revision answers almost all of the reviewers' substantive questions, but the response letter needs a focused editorial reduction.** Its principal problem is repeated explanation of why evidence is limited, often after the limit has already been made clear. The cumulative effect is defensive and procedural. The underlying scientific candour is a strength and should survive the cuts.

All substantive scientific questions have responses, including explicit acknowledgements of unavailable validation or provenance. Reviewer 2 has an appropriate remedy, with the journal-generated review-PDF check still pending. R1-minor-7 is the weakest editorial reply: it does state that the biology was retained, so it is not unanswered, but repeats the rationale and adds an irrelevant layout check. The reviewer suggested considering a cut; retaining necessary biology with a direct explanation is defensible.

The letter does **not** suffer from repeated apologies or excessive “we agree” openings. Most numerical replies, especially R1-major-3 and R1-major-6, are already direct. The conspicuous model-like features are long inventories, slash-heavy shorthand, repeated “does not establish” conclusions, and narration of internal audit history. The appropriate intervention is selective compression, not a new layer of qualifications.

I found no need to strengthen the scientific claims. The stated results support a transparent method for organizing hypotheses, with weak temporal recovery and substantial dependence on available evidence. They do not establish reliable novel-gene prediction, independently calibrated HIGH specificity or superiority over the strongest simple baselines. Those conclusions are already clear.

## Adequacy against every original comment

**Answered** means the requested explanation or analysis is present. **Disclosed limit** means the answer is responsive while openly acknowledging that a desired stronger result or resource is unavailable. **Editorial clarification** identifies a weakly expressed editorial decision. These labels assess responsiveness, not whether the method performs well.

| Comment | Verdict | What the current response actually answers; remaining action |
|---|---|---|
| Editor | Answered | `rebuttal.md:13`: narrows claims, reports calibration dependence, housekeeping failure, shortlist sensitivity and weak temporal performance. Shorten the repeated validation disclaimers. |
| Reviewer 2 | Remedy described; delivery check pending | `:390`: figures are embedded with legends and supplied separately; journal review-PDF visibility will be checked. This correctly answers inaccessible **figures**. The final portal check cannot be called completed yet. |
| R1-major-1 | Answered | `:31–33`: defines broad sensory/ciliary hypothesis generation, separates nine Usher and 28 SYSCILIA controls, and explains the broader temporal target. Start with plain language; the mechanism examples can remain in R1-major-8. |
| R1-major-2 | Disclosed limit | `:57–59`: distinguishes raw scoring from the control-informed gate, acknowledges compendium overlap and reports an unsuccessful temporal test. Independent calibration is not claimed; this follows the reviewer's explicitly offered fallback. |
| R1-major-3 | Answered | `:89`: gives both full tier distributions, each Usher control's filtering losses and five threshold settings. Main Table 3 provides the requested trace. Retain this concise answer. |
| R1-major-4 | Disclosed limit | `:113–115`: adds 111 publication/GO-matched disease comparators, reports separation and residual limitations, and avoids clinical specificity estimates. The comparators' imperfect negative status is disclosed rather than concealed. |
| R1-major-5 | Answered | `:149–151`: labels weights heuristic, explains their modest emphasis, supplies equal/single-layer/leave-one-layer-out comparisons and top-25/50/100 persistence. Adverse simple-baseline results are explicit. |
| R1-major-6 | Answered | `:179`: gives the 3/4/5/6-layer distribution, stricter completeness thresholds, score–completeness correlation and per-gene information. The last historical-audit sentence can go. |
| R1-major-7 | Answered | `:201`: supplies correlations with sample sizes, layer omissions and within-layer combination rules. Shared studies and known-gene information are acknowledged. Detailed implementation corrections can be left to Methods/S3. |
| R1-major-8 | Disclosed limit | `:221–244`: retains the 33/35 mantis-ml seed overlap, adds simple baselines and an extensive retrospective temporal evaluation, reports weak recovery and explains later human review. A harmonized mantis-ml rerun is unperformed but was not required by this comment. This is the largest compression opportunity. |
| R1-major-9 | Disclosed limit | `:278–280`: provides recorded versions, URLs, retrieval metadata, hashes, locked environment, replay commands and the actual Markdown/TXT mismatch explanation. Original missing metadata and incomplete raw-source regeneration remain clear; a container was suggested, not required. Lead with these answers instead of test counts and artifact inventories. |
| R1-major-10 | Answered | `:302–304`: identifies cerebellum as an adult neural proxy, removes the stronger tissue-specific label, quantifies expression support and substantial proxy-removal effects, and states the missing hair-cell component. A brief explanation of the proxy's intended role would improve flow, but absence of proven optimality is not a new missing analysis. |
| R1-minor-1 | Answered | `:318`: the Abstract explains absence of training labels/similarity seeds before the later “seed-free” terminology; Methods distinguishes known-gene knowledge and gate calibration. |
| R1-minor-2 | Answered | `:328`: uses “priority tier” and explains the legacy `confidence_tier` field. No further work needed. |
| R1-minor-3 | Answered | `:338`: distinguishes analysis labels, retained IDs and HGNC validation, including 573 ENSG fallback labels. No further work needed. |
| R1-minor-4 | Answered | `:348`: both tier distributions and Table 3 are in the main Results. The cross-reference is sufficient. |
| R1-minor-5 | Answered | `:358`: gives the sample size, population, sampling without replacement, seed 42 and ordering. No further work needed. |
| R1-minor-6 | Disclosed limit | `:368`: states that no DOI archive exists and supplies exact versions and artifact hashes. The requested archive remains unfulfilled, but the reviewer said “if possible.” Remove the extended justification; do not imply that missing raw inputs make depositing a clearly scoped version impossible. |
| R1-minor-7 | Editorial clarification | `:380`: says the biology was retained but repeats its rationale and invokes layout checking. State the decision and scientific reason once. The reviewer suggested shortening rather than requiring it; retaining necessary biology is a reasonable author choice. |
| R3-1 | Answered | `:400`; `draft.md:41`: the sentence has references [8–11] and distinguishes stereocilia from true cilia. Preserve these citations. |
| R3-2 | Disclosed limit | `:410`: directly explains seed-free scope, control reuse and heuristic HIGH interpretation. Replace awkward “cannot undo reused-positive calibration”; do not repeat the whole temporal story. |
| R3-3 | Answered | `:420`: justifies the modest weight choices, retains logistic ρ=0.646 and explains shortlist instability and control-reuse concerns. This is an adequate rationale, not evidence of optimality. |
| R3-4 | Disclosed limit | `:430–434`: answers the request with a temporally separated but unsuccessful evaluation and limits the claim accordingly. Open with the conclusion that reliable novel-gene prioritization has not been established; cross-reference R1-major-8 for ascertainment and human review. |
| R3-5 | Answered | `:446`: directly discusses auditory/developmental disadvantage and the exploratory status of the fetal observations. No new dataset is needed for this response. |
| R3-6 | Disclosed limit | `:456–458`: explains research-intensity/general-importance contributions, matched comparisons and their limits. The repeated human-review/GO paragraph is unnecessary here; R1-major-8 and S8 already provide it. |

## Prioritized cuts

### 1. State the Background decision directly

**`rebuttal.md:380`; `draft.md:39–51`.** Preserve the author's decision to retain necessary biological context. Explain that it motivates the sensory/ciliary scope and the distinction between stereocilia and true cilia. Remove the repeated rationale and rendered-layout sentence. Do not claim that the section was shortened. Small sentence-level cuts remain optional and need not remove the mechanistic discussion or alter references.

### 2. Give the temporal assessment one full home

**`rebuttal.md:221–244`, repeated at `:59`, `:430–434` and `:456–458`.** R1-major-8 alone contains approximately 849 response words, excluding the reviewer quotation and location lists. It should retain the design, the principal negative result, the all-45 human review, the family concerns with cumulative context, and representative mechanism examples. It need not enumerate historical source releases, category A/B recovery, all GO test counts, all date-audit rules and pilot history.

R3-4 contains approximately 283 words and largely retells the same account. Reduce it to a direct negative answer, the principal recovery figures and a precise cross-reference. R1-major-2 needs only a short temporal conclusion after explaining calibration. R3-6 should end after the specificity conclusion. Cross-references can remove repeated detail while keeping each answer understandable on its own.

### 3. Replace the opening inventory with the revision's conclusion

**`rebuttal.md:3–5`, `:13`.** The first paragraph describes downloaded reports, correspondence and journal mapping; this is internal assembly history. The second lists almost every analysis and repeats material immediately below. Retain the statement that original comments are reproduced and PDF locations are supplied, then summarize the three main changes in a short paragraph. The Editor's answer does not need another human-review/validation paragraph.

### 4. Put reproducibility answers before implementation inventories

**`rebuttal.md:278–280`, `:368`.** The reviewer asked for provenance, an executable environment and a checksum correction. Open with those. The byte count 204,322,926, historical test totals, 17 warnings, database-option inventory, self-hashing explanation and rendering-index history are useful audit records but do not all belong in this answer. Keep the distinction between numerical replay and incomplete original raw-source regeneration once. For the DOI response, state nondeposit and identify the exact current release; the older commit chronology belongs in availability records.

### 5. Remove small defensive tails without weakening the answers

- **`:89`**: replace “We report this full family without choosing a more favorable production threshold” with “The production threshold remains 0.70.”
- **`:149`**: delete “We report this unfavorable comparison directly.” The preceding numbers already do so.
- **`:179`**: delete the final sentence about not dismissing historical sparse-evidence limitations; the actual production result and general limitation already answer the question.
- **`:201`**: move the sentence beginning “We corrected descriptions that conflated…” out of the response. State the final method rather than narrating the correction history.
- **`:410`**: replace “matched comparator results cannot undo reused-positive calibration” with “The matched comparison does not independently calibrate HIGH.”
- **`:420`**: replace “rejected as production fitting” with “was not adopted for production.”
- **`:458`**: delete the repeated mechanism/GO paragraph and cross-reference R1-major-8 if needed.

### 6. Consolidate repeated manuscript qualifications

**`draft.md:92,104,112,166,192,453`.** The warning that configured release labels do not prove source immutability appears throughout Methods, Usage and the architecture caption. State the original provenance limitation clearly in Reproducibility and S7; delete the sentence-level repetitions elsewhere. The detailed “six source records, six checksums, two URLs, two versions, no retrieval times” inventory also repeats at `:92`, `:166` and `:416`; one full occurrence is enough.

**`draft.md:371`.** This 238-word paragraph combines missingness, temporal performance, a random-ordering arithmetic comparison, source substitutions, catalog ascertainment, target definitions and human-review status. Separate missingness from the temporal interpretation. Keep the adverse recovery result, the retrospective/source differences and unresolved eligibility; place procedural details in S6. The sentence “These limits remain despite rules and cases being fixed…” adds no new information.

**`draft.md:309`.** The main temporal Results paragraph mixes principal failures, gate mechanics, six sensitivity details, old-control recovery and A/B strata. Keep the score-threshold explanation and principal failures here; detailed control and subgroup outcomes are already available in S6/Additional file 12. This is a relocation of results, not selective suppression.

**`draft.md:39,41`.** “Indispensable hubs,” “pleiotropic, multisystemic pathologies” and “profound clinical overlap” are conspicuously inflated. The next paragraph states the combined auditory–retinal distinction twice. Plain biological description will be more persuasive.

### 7. Remove internal audit history from Supplement and cover letter

**`supplementary_methods.md:96`**: retain the correct 83 localization-missing count; remove the final sentence correcting an earlier reviewer shorthand of 63. That exchange is irrelevant to a reader of the final method.

**`supplementary_methods.md:98`**: retain the pilot's restricted sources and limits; move the interrupted transfer and resource-availability history to the existing audit record.

**`supplementary_methods.md:173`**: the sequence 343 → 345 → 354 → 362 tests is development history. The tested environment, current total and byte-identical replay results suffice here. **`:163`** should retain cumulative family support and unresolved decisions, but the final two sentences can be one: “Eligibility remains under review; the original cohort and recovery estimates are retained.”

**`cover_letter_revision.md:12–16,30`**: the cover letter repeats the response's inventories and then repeats the fixed tag after the signature. Keep the principal adverse temporal result, narrowed claim, all-45 review and unresolved concerns, figure remedy and one release link. Remove the 7 October tag history, analysis checkpoint and trailing tag paragraph.

## Proposed replacement responses

These are proposed text, not applied changes. Existing quotations and useful manuscript/PDF locations should remain. Numerical and methodological detail removed here remains in the cited Results, Supplement or additional files.

### R1-major-2

> The reviewer is correct that the gate and its control-based evaluation are not independent. We now describe HIGH as a heuristically calibrated priority tier and distinguish it from the raw score in the Abstract, Methods and Results. Raw scoring uses no training labels or similarity seeds, but known-gene information remains an input: 26 of 28 SYSCILIA controls overlap the embedded compendium used in localization scoring and gate passage. Internal control recovery therefore cannot establish independent specificity.
>
> The added retrospective temporal assessment did not resolve this limitation. Neither historical analogue recovered a principal case in the top 100 or HIGH: recovery was 0/41 in the coding universe and 0/45 overall. Historical HIGH contained zero and five genes, respectively. The study evaluates historical analogues of a method developed after the cutoff and does not establish prospective validity. Design, results and subsequent human review are detailed in R1-major-8 and S6.

### R1-major-8

> We now describe the mantis-ml analysis as an exploratory comparison of cached outputs. Of the 35 shared controls, 33 were mantis-ml training seeds; the two non-seeds cannot support a meaningful independent benchmark. We also added equal-weight, individual-layer and leave-one-layer-out baselines. Animal-only scoring recovered the most Usher controls, and literature-only scoring recovered the most SYSCILIA controls; both exceeded the integrated score for their respective group.
>
> We completed a retrospective temporal assessment using an evidence cutoff of 31 December 2020. The 45 later target-association cases and the analysis rules were fixed before the new rankings; development controls and previously inspected pilot cases were excluded. Forty-one cases mapped to the historical protein-coding universe, while four noncoding cases remained failures in the 45-case overall denominator. Neither the five-layer nor six-layer historical analogue recovered a case in the top 100 or HIGH (0/41; 0/45 overall). Top-1,000 recovery was 2/41 and 3/41, and median percentiles were 46.23 and 44.95. Historical HIGH contained zero and five genes, respectively. These weak results are reported in the Abstract, Results, Table 4 and Figure 8. No principal case represents a new Usher association.
>
> After the frozen analysis, a human author reviewed primary reports and family/pedigree evidence for all 45 cases, together with phenotype, inheritance, functional mechanisms and publication chronology. Concerns about **PDIA6, VWA8 and PLCG1** require interpretation across reports. The initial PDIA6 report described one family; the earlier VWA8 developmental-disorder report also described one family, whereas the temporal target was a later retinal association. PLCG1 had a single-family immune-disorder report and a later auditory/ocular multisystem report involving four families. The retained screening ledger records cumulative target-family lower bounds of two, two and three, respectively, using the relevant reports. These remain screening classifications: eligibility of the flagged cases is under review, and all three remain in the original cohort and results (S6.6).
>
> The review also clarified the cohort's broader sensory scope: CRLS1 involves mitochondrial disease, CTNND1 retinal vascular disease, DHRSX glycosylation disease, and the RNU genes spliceosomal RNA-associated retinal disease. These mechanisms are not collectively evidence of ciliopathy. A separate contemporary GO description found no FDR-significant enrichment and does not provide predictive validation (S8). A bounded publication-version audit supported post-cutoff first-target publicity intervals; its date uncertainties are documented in S6.6.
>
> This assessment uses historical analogues rather than an exact production replay. Post-cutoff method development, source substitutions, modern-text uncertainty and non-exhaustive ascertainment limit its interpretation. It provides no evidence of reliable novel disease-gene prediction and does not include a harmonized mantis-ml rerun.

### R1-major-9

> We have added source versions and URLs, retrieval metadata where recorded, input/output SHA-256 hashes, exact tested dependency locks and commands for reproducing the figures and tables (S7; Additional files 11/12). Clean replay reproduced 28 production/revision TSVs and, separately, all nine temporal TSVs and their manifest. The tested environment is Python 3.13.1 on macOS arm64. Original unrecorded retrieval dates remain unknown, and the production bundle supports numerical replay rather than complete regeneration from every original raw source.
>
> The reviewer correctly identified the checksum mismatch: the original manifest hashed the repository Markdown report rather than the submitted Additional file 6 TXT. The revision records source and converted files separately. Additional file 10 hashes the actual delivered additional files, and the package manifest identifies the delivered documents and their sources.

### R1-minor-7 — concise statement of the retained author choice

> We have retained the mechanistic background because it explains the sensory/ciliary scope of the score and distinguishes actin-based stereocilia from true cilia. We have clarified this rationale and expanded the computational design and evaluation sections, while retaining the biological detail needed to interpret them.

This is an explicit decision to retain the material, not a claim that it was shortened. The reviewer's wording permits that response.

### R3-4

> We have not established reliable prioritization of genuinely novel disease genes. The added retrospective temporal assessment provides a separate test of later associations, but its results were weak: neither historical analogue recovered a principal case in the top 100 or HIGH (0/41 in the coding universe; 0/45 overall), and top-1,000 recovery was 2/41 and 3/41. No principal case represents a new Usher association. Source substitutions and post-cutoff method development also prevent treating this as an exact production replay or prospective validation.
>
> We have therefore limited the claims to hypothesis generation. R1-major-8 and S6 describe the cohort, subsequent human review of all 45 cases and unresolved eligibility concerns.

### R3-6

> The composite only partly distinguishes sensory/ciliary evidence from general gene importance and research intensity. Constraint, annotation depth and publication evidence can elevate well-studied genes, as shown by the housekeeping median at the 94.8th percentile. We now state this limitation explicitly.
>
> We added disease comparators matched on publication and GO counts, layer correlations and omission analyses. Control advantage persists when pairs are compared on shared observed layers, but falls to 55.6% for Usher and 57.1% for SYSCILIA after joint animal/literature omission. These findings show dependence on sensory-model and literature evidence; the comparators are not verified clinical negatives and do not establish a clinical specificity estimate. R1-major-4/7 and S3–S5 provide the analyses. The weak temporal recovery reported in R1-major-8 further limits claims of disease-specific prediction.

## Limits to preserve when applying cuts

Keep the adverse temporal recovery explicit, along with the 41 coding plus four noncoding cases; retrospective historical-analogue design; all-45 post-analysis human review; retained PDIA6/VWA8/PLCG1 concerns and cumulative later-report context; and contemporary, post-hoc, nonsignificant GO findings. These observations authorize neither new exclusions nor final human eligibility approval. The process summary and representative examples are sufficient; the full working human-review form need not be attached. Preserve main-text reference numbering and first-citation order [1–66].

The documents agree on these central facts. The historical 354-test checkpoint and current 362-test suite are not contradictory. No new experiments or broader audit are needed for the prose recommendations in this report.

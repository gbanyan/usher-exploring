# Phase5 author-review status — 7 October 2026

This update supersedes the next-step paragraph below; the earlier conservative and expanded-temporal decision history remains preserved.

The revised manuscript, Supplementary Methods, all 23 responses to Reviewer 1 (downloaded report) and Reviewer 3 (pasted report), and cover letter are prepared. Reviewer 2 supplied only a supplementary-file access complaint; the user instructed us to leave it outside the current response scope. New author-review artifacts are in `submission/bmc_bioinformatics_major_revision_20261007/`; the original submission is preserved.

**Important author clarification:** on 7 October the author confirmed that none of the 45 principal cases had yet been individually verified by a human author. Clinical eligibility and association dates therefore remain provisional AI-assisted screening classifications. This qualification now appears in the main manuscript, supplement, response, cover letter and package README. Numerical execution and reproducibility are complete; individual human case/date review is not. Do not call the package submission-ready or the cohort independently clinically validated. Use `phase5_claude_review/principal_case_human_verification.tsv` to record the remaining human work.

Actual Claude Opus5.5 first-party CLI review is recorded in `phase5_claude_review/round1_*`. Its substantive findings were addressed in `round1_resolution.md`, including known-gene compendium circularity, literature-only control baselines, empty/near-empty historical HIGH tiers, weak temporal recovery, case-category distinctions, ATP2B2 phenotype-extension wording, and explicit AI/source limitations. Rounds 2–4 audited the actual final artifacts; the final Opus verdict is ready for author review with no remaining material error, but not journal-submission-ready. See phase5_report.md and phase5_claude_review/round4_review.md. No production weights, gate thresholds or frozen scores were changed to improve outcomes. All 21 protected baseline hashes remain unchanged; 354 tests pass. The new derived temporal checker exactly reproduces 38,334 co-primary score/count/rank rows, without claiming raw HIGH or clinical verification.

Version correction: the previously cited public commit 4cf8c5b is real on GitHub despite its absence from the local object history. Direct page/API verification restored the original reference, separately from the preserved submitted-files checkpoint ed2d00d. The fixed final author-review release tag is major-revision-author-review-20261007; post-commit dual-remote/LFS publication evidence is recorded in phase5_claude_review/publication_verification.json.

Remaining author work: verify the 45 original-report eligibility/date decisions, resolve any affected cohort/outcome changes transparently, approve revised text and AI disclosure, and confirm cover-letter declarations and manuscript ID before journal upload. No journal upload or DOI deposition has been performed.

---

# Major revision continuation state — 6 October 2026

Read this file before continuing the major revision. It supersedes any earlier
interpretation that temporal work should stop after the restricted pilot. It does
not supersede frozen protocols, results or source manifests.

## Current user decision and deadline

The intended submission deadline is **20 October 2026**. On 6 October the user
challenged the assumption that fuller independent validation would be too costly,
noted the remaining 14 days, and instructed us to preserve the decision history
and proceed. Expanded temporal validation is now the next research workstream.
The 14-day schedule is a planning target, not demonstrated feasibility or a
guarantee of completion.

The expanded historical-analogue workstream has now been executed. The original
pre-outcome freeze is **bd6bb2f**, followed by a guarded GTEx canonical/PAR_Y
schema repair committed at **53da295** before any composite/rank/recovery result.
Both checkpoints were pushed to Gitea and GitHub. Results/report/figure/replay evidence
are checkpoint **90f13d0**, also on both remotes. Original protocol/manifest and
the aborted-attempt record remain preserved.

**Current outcome:** 45 principal strong later-target cases, 41 in the historical
protein-coding universe and all scored. Four noncoding RNU genes remain in the
45-case end-to-end denominator as nonrecoveries. Five-/six-layer top100 and HIGH
recovery are both 0/41; top1000 is 2/41 and 3/41; top10% is 5/41 and 6/41. Median
score percentiles are 46.23 and 44.95. All 23 prespecified schemes were executed.
No principal case reaches HIGH under any scheme. Do not promote favorable
sensitivity results or exploratory candidates to rescue the primary outcome.

Read `temporal_validation_v2/OUTCOME_REPORT.md`, final `PROTOCOL.md`,
`freeze_amended.json`, `results/manifest.json`, `execution_verification.json` and
the post-outcome Astra review before changing scientific claims. This is an
expanded retrospective temporal stress test of historical analogues, not an exact
modern production replay or proof of prospective independent predictive validity.
Source substitutions, modern text/date-bounded literature uncertainty, absent
direct hair-cell data, bounded conference/thesis dates and conditional catalog
ascertainment are explicit. The 895 unconfirmed/unnominated catalog records are
not clinically established negatives.

Validation: **354 tests passed, 17 existing warnings**, local Python3.13.1/macOS
arm64; clean reconstruction replay gives nine TSVs and manifest byte-identically.
Protected baseline hashes (including production DuckDB) are unchanged; shared
pilot components reproduce exactly; held-out clinical PMIDs are absent from the
historical links. Raw scoring data: 24 files, 204,322,926 bytes, retained locally.
The caches have hash/provenance records, not an off-machine data backup.

Astra outcome review found no critical numerical or mapping error. Independent
raw-source reconstruction agrees; pooled expression differs by at most 2.22e-16;
all 4,531 case-scheme rows and 37,950 recovery rows reproduce. The review is an
internal independent-agent audit, not external peer review.

Next: integrate the reviewed negative/weak temporal result into manuscript,
supplementary methods and both reviewers' responses while preserving the earlier
conservative checkpoint; then complete Phase5 journal packaging. Do not claim
reliable novel-gene discovery, calibrated HIGH probability or clinical specificity.

## Why there are two routes

1. **Original conservative revision route, completed at source level.** Additional
   specificity, weighting, missingness and proxy analyses were performed. Claims
   were narrowed to transparent cilia/sensory-aware hypothesis generation. HIGH
   is a control-calibrated heuristic priority tier, not independently established
   disease probability or clinical specificity. Revised prose, supplementary
   methods and all 23 response points are ready for packaging.
2. **Restricted temporal extension, already executed.** An initial local-cache
   feasibility audit was insufficient grounds to stop. External archives were
   then investigated and a frozen four-layer historical pilot was run. It is not
   full six-layer temporal validation or an independent HIGH-gate test.
3. **Astra's conditional review conclusion.** The user-requested gpt-6-astra/high
   review judged that no further experiment was necessary to support the
   *conservative claims already written*. It did not establish that temporal
   validation is infeasible, prohibit further work, or certify independent
   novel-gene performance.
4. **Decision reopened by the user.** The assistant had not performed a complete
   time/cost assessment before favoring the conservative stopping point. Calling
   the remaining work “too costly” was premature. The user considers the work
   worthwhile and potentially feasible before 20 October. We will investigate
   and execute a fuller defensible design rather than treat conservative wording
   as an automatic stopping rule.

The conservative route remains a preserved fallback and scientific baseline. Do
not discard it, overwrite its outcomes, or automatically strengthen its claims
because further work has been authorized. New results may support, qualify or
weaken the manuscript. Negative findings must remain visible.

## Completed checkpoints and source documents

Working branch: `revision/major-revision`. Gitea and GitHub both contain Phase4
checkpoint **`0e1634a`**. That commit preserves source content and replay, not a
final revised journal submission or DOI-bearing release.

| Item | State / location |
|---|---|
| Submission database recovery | Complete; `docs/submission-database-recovery.md`, `data/report/database_recovery_20261006.json` |
| Phase2 protocol and results | Frozen; `analysis_spec.md`, `results/`, `phase2_report.md` |
| Phase3 comparator protocol | Frozen before outcomes at `0ae2c3d`; `phase3_spec.md` |
| Phase3 comparator roster | Frozen before outcomes at `61abb61`; `phase3_roster/` |
| Phase3 outcomes | Complete; `phase3_results/`, `phase3_report.md` |
| Restricted temporal protocol | Frozen before its outcomes at `377eae3`; `temporal_extension/protocol.md` |
| Restricted temporal results | Executed checkpoint `c9834c6`; `temporal_extension/results/`, `report.md`, source/date/probe audits |
| Independent Astra review | `astra_review.md`, `astra_phase4_review.md` |
| Phase4 post-review sensitivities | Frozen; `phase4_spec.md`, `phase4_results/`, `phase4_report.md` |
| Revised manuscript | `../../manuscript/draft.md` |
| Revised supplementary methods | `../../manuscript/supplementary_methods.md` |
| Point-by-point response | `rebuttal.md`; 10 major + 7 minor from downloaded report, 6 pasted comments |
| Comment tracking | `reviewer_crosswalk.tsv`; A/B are source labels, not verified journal reviewer numbers |
| Derived numerical replay | `replay_inputs/`, `reproducibility/README.md`, exact dependency lock and source inventory |
| Immutable original prose | `baseline/`; numerical checks must use these copies, not revised prose |

## Scientific baseline that must not drift

Recovered production DB: `data/pipeline.duckdb`, SHA-256
`0beb4f61c62ebff2ba6358069d9eb37cb6c4a9366140bb1c1c486cd2d59f2c65`.
It has 20,081 scored labels, 20,053 non-NULL composites, and 62 HIGH / 9,673 MEDIUM /
8,652 LOW / 1,694 excluded labels. Universe IDs before consolidation: 20,116.

- Nine Usher controls: raw median percentile 97.77, HIGH/MEDIUM 2/7.
- Twenty-eight SYSCILIA controls: raw median 91.93, HIGH/MEDIUM 1/27.
- Housekeeping median 94.8: a raw-score specificity failure, not repaired by tier
  relabeling.
- Fixed matched comparison: 27/84 comparators, medians 64.21/60.30; original pair
  wins 24/27 and 72/84. All 111 matches preserved; they are not verified biological
  negatives. Zero HIGH among matches is not independently validated gate
  specificity because 110 already fail the raw score threshold.
- Post-review common-layer pair wins: 23/27 and 75/84. Joint animal/literature
  omission: 15/27 and 48/84 (55.6%/57.1%). These are post-outcome sensitivities.
- Animal-only top100 control recovery 4 Usher / 11 SYSCILIA exceeds default 2/1.
  Only 41 default top100 genes persist through all 25 modest weight configurations.
- Removing cerebellum: ranking correlation 0.9496; HIGH 60 with only 37 shared
  genes, 25 lost / 23 gained. Production contains no direct hair-cell expression.
- Exact layer weights remain 0.20/0.20/0.15/0.15/0.15/0.15. Gate uses direct
  compartment/compendium flags OR animal positive-Q75 threshold 0.12765713253595054,
  not arbitrary positive aggregate localization. Do not retune on new outcomes.

## What the existing temporal pilot established

Cutoff: **2020-12-31**. Historical uniquely mapped protein-coding population:
19,167, with 19,033 scored. Constraint, ordinal HPA expression, partial GO
annotation and HPA localization were reconstructed. Animal/literature were NULL;
no historical HIGH tiers were assigned. Current undated compendia and modern
scores were not imported.

Three manually selected later human-association examples were frozen before
pilot rank inspection: CEP162, CFAP20, LRRC45. Pre-cutoff ciliary biology was
allowed. These are not three new Usher genes, not an exhaustive cohort, and
candidate reports are distinguished from stronger disease evidence. Default ranks
were 8,289 / 11,004 / 253; none entered top100. All three lacked accepted retinal
HPA protein observations. Eleven historical top100 genes had one observed layer;
83 lacked localization (63 counted only one subgroup in an earlier shorthand).

The pilot neither demonstrates full-pipeline success nor establishes that fuller
reconstruction is impossible. Available GTEx/HPA RNA were omitted by its limited
source contract. Preserve this protocol and its negative/mixed outcomes as the
earlier study, not a protocol to silently rewrite.

## Retained data and audit

`continuation_data_audit_20261006.json` records current file presence, sizes and
expected/actual SHA-256 checks. It checks original protected submission inputs,
recovery sources, completed historical downloads, comparator snapshots, frozen
numerical results and distributed replay inputs. Production row counts are read
through a read-only database connection. Read its final status before asserting
data integrity.

Important local-only paths:

- `data/pipeline_source.duckdb`: historical donor, required for recovery.
- `data/pipeline.duckdb.bak-prerecovery-20261006`: pre-recovery backup.
- `data/cache/submission-recovery-20261006/`: isolated recovery and source copies.
- `data/cache/phase3-sources-20261006/`: exact original comparator raw snapshots.
- `data/cache/temporal-extension-20261006/raw/`: seven completed historical files
  plus an **incomplete** `gene2pubmed_20200629.gz.part`; the `.part` is not an
  acquired/validated full source.
- `data/cache/temporal-extension-20261006/probes/`: bounded probe prefixes.
- `data/cache/phase4-replay-20261006/`: clean replay DB, environment and outputs.
- `.venv/`: installed development environment. The clean replay environment is
  `data/cache/phase4-replay-20261006/venv/`.

Git contains derived replay tables, numerical outputs, manifests and frozen live
ClinGen/HGNC text exports. **Git does not back up ignored live databases or raw
caches.** This integrity audit is not an off-machine backup; do not delete these
local directories or assume a fresh checkout includes them. Leave unrelated
untracked root `uv.lock` untouched.

Last validated computation checkpoint: **345 tests passed**, 17 existing
warnings; **28 TSVs byte-identical** in a clean Python3.13.1/macOS-arm64 environment.
Linux/container parity is not established. Commands and pinned versions are in
the replay guide. A documentation checkpoint does not itself rerun that suite.

## Original expanded-work plan and decision boundaries (historical record)

Proposed work directories (create when needed; do not reuse pilot output paths):
`revision/major_revision_20261006/temporal_validation_v2/` for committed protocol,
selection/source audits and outputs; `data/cache/temporal-validation-v2-20261006/`
for task-owned raw inputs. These names identify the expanded study without
claiming full validation has already been achieved.

1. Inventory complete versus partial historical sources and source-equivalent
   transforms. First attention: GTEx/HPA RNA, MGI/ZFIN/IMPC, historical orthology
   confidence, literature links/context and UniProt/pathway components. Current
   Census is unavailable in 2020; never silently backdate it.
2. Distinguish the test of historical **raw ranking** from independent **HIGH-gate
   evaluation**. A fuller ranking reconstruction alone cannot certify gate
   specificity. Define calibration/test separation and allowable data
   substitutions before expanded rank inspection.
3. Develop systematic cohort inclusion/exclusion and first-human-association date
   rules, including preprints/early-online versus indexing, candidate versus causal
   reports, and prior disease associations. Select by evidence/date criteria, not
   favorable rank. The three pilot ranks are already known and must not be
   presented as untouched new held-out observations.
4. Freeze the expanded protocol, source contract, cutoff justification, cohort
   roster, comparisons and unavailable-source rules before new outcomes. If a
   different cutoff is considered, justify it from source availability/question,
   not better recovery. Do not label changed-source variants exact production
   replicas or retrospectively prespecified studies.
5. Execute complete-case/source-coverage checks, historical rankings, simple
   baselines, top-K recovery and missingness/substitution sensitivities; preserve
   every prespecified outcome. Obtain independent review before changing claims.

Planning target: 6–8 October source audit/protocol; 9–12 October source/cohort
reconstruction; 13–15 October computations; 16–19 October independent review,
writing and submission packaging. **8 October is the first feasibility decision
checkpoint, not an automatic stop date.** Escalate concrete blocking inputs or
time tradeoffs with evidence rather than concluding “too costly” without an
assessment. A smaller cohort or incomplete source contract may still limit claims.

## Packaging remains unfinished

Phase5 final journal DOCX/PDF rendering, Additional-file assembly, actual delivered
file checksums, reviewer-number mapping/pagination and exact-version archive/DOI
disposition remain required. The original Additional6 mismatch is repository
Markdown versus converted TXT, documented in `reproducibility/submission_conversion_audit.json`.
Do not claim new converted-file verification or a DOI before packaging is completed.
The expanded historical-analogue study is executed; independent novel Usher-gene
prediction remains unvalidated. Preserve the conservative checkpoint while
integrating the new negative/weak findings.


## Pre-outcome v2 freeze preparation (superseded execution-state record)

The final `temporal_validation_v2/PROTOCOL.md`, source inventory, reference index
and clinical roster are ready for a Git checkpoint before any real v2 reconstruction.
There are 45 principal strong later-target associations, 18 exploratory candidates,
three unresolved-novelty cases, 50 previously inspected controls and three pilot
references. All 1,092 selection decisions are closed; this is not exhaustive
clinical adjudication. The 358 historical curated, 96 historical RetNet and 441
unaccepted-nomination records retain explicit clinical uncertainty.

The freeze covers 24 numerical source files and 3,122 total dependencies, including
adopted search pages, clinical XML/metadata, source provenance, all production Python
modules, revision scripts and the exact installed v2 environment. Raw caches remain
local-only. Mutable progress STATUS is deliberately outside the experimental freeze.
Astra's clinical/numerical pre-outcome review is saved; latest test command
`.venv/bin/python -m pytest tests/ -q` passed 353 tests, with 17 existing warnings
on local macOS arm64/Python 3.13.1. A first accidental invocation of system pytest
failed collection because it used Python 3.14 without project dependencies; the
correct .venv run above passed.

No case score, rank, HIGH recovery or recall has been calculated yet. Commit the
freeze before running `scripts/revision_temporal_v2_evaluate.py --freeze-commit HASH`.
Any subsequent implementation correction must preserve original attempts, record
its post-outcome timing, and use a new output directory. Conservative Phase4 and
the restricted pilot are unchanged.

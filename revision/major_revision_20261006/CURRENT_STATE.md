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

Checkpoint `91f34dd` recorded state and verified retained data. The user then
explicitly authorized execution. Expanded acquisition and design review are now
underway; see `temporal_validation_v2/STATUS.md`. **The expanded protocol/cohort
are not yet frozen and no expanded numerical rankings have been computed.** Do
not confuse complete archive acquisition with completed validation.

Latest pre-outcome progress: checkpoint `9f903d3` is on both remotes; subsequent
work is awaiting a new checkpoint. All 24 adopted scoring files are inventoried
(204,322,926 bytes with individual SHA-256 hashes). Broad all-source target
searches completed for all 682 non-historical-green genes: 57,153 records with
complete pagination. Four ordinary-English aliases were corrected before
outcomes; earlier raw requests/pages are preserved. Read the adopted aggregate
manifest, not a glob of obsolete query attempts.

Clinical working notes contain 143 records (not 143 accepted cases). A draft
roster preserves 1,081 catalog gene/locus keys plus 11 appended reference
controls, with 45 proposed strong cases before final independent review.
Do not treat draft statuses as eligibility approval or unresolved catalog records
as clinical negatives. New findings include pre-cutoff STXBP3 conference evidence,
EGFLAM hearing candidate evidence, DAP3 thesis-date uncertainty, corrected target
family counts and contested OGDHL validity. Astra is continuing pre-outcome review.

Reconstruction/evaluation adapters are written but have not run on real evidence.
The evaluator requires a committed protocol/source/clinical freeze and rejects
development/pilot contamination, insufficient target-family evidence and dates
crossing the cutoff. Local Python3.13.1/macOS-arm64 full suite: **352 passed,
17 existing warnings**. This test run does not demonstrate reconstruction parity
or outcome reproducibility. **No v2 score, rank, HIGH outcome or recall statistic
has been computed; do not compute outcomes before the committed freeze.**
Read `temporal_validation_v2/STATUS.md`, `PROTOCOL_DRAFT.md`, clinical drafts and
the independent review documents before continuing.

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

## Expanded temporal work: next actions and decision boundaries

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
Do not claim new converted-file verification, a DOI, full temporal validation or
independent novel Usher-gene prediction until actually completed. Keep the current
manuscript/rebuttal as the conservative checkpoint while the expanded study runs.


## Pre-outcome v2 freeze ready (6 October 2026)

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

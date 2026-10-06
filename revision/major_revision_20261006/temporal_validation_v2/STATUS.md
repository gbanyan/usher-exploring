# Expanded temporal validation — executed workstream

Latest status (6 October 2026): all 23 historical-analogue schemes are executed;
45 principal cases, 41 in the historical protein-coding universe. Co-primary
top100/HIGH recovery is zero; top1000 is 2/41 (five layers) and 3/41 (six).
Clean reconstruction replay matches nine TSVs and the manifest byte-for-byte.
354 tests pass; protected baseline/production hashes are unchanged.

Freeze commits: original `bd6bb2f`, technical GTEx identifier amendment `53da295`.
Read `OUTCOME_REPORT.md`, final `PROTOCOL.md`, `execution_verification.json`,
`results/manifest.json` and the post-outcome independent review. The source
contract is a historical analogue, not an exact production replay; conditional
ascertainment and 895 unresolved/unaccepted catalog records remain explicit.
Results checkpoint `90f13d0` is on both remotes. Astra outcome review found no
critical numerical or mapping error; independent raw-source reconstruction and
all case/recovery arithmetic reproduce. Next is manuscript/rebuttal integration
and Phase5 packaging.

The dated acquisition/pre-outcome notes below are retained as decision history;
their pending-status statements do not describe the latest execution state.


Authorized by the user on 6 October 2026, following the completed conservative
Phase4 revision and restricted historical pilot. Submission target: 20 October.
Read [the continuation state](../CURRENT_STATE.md) for the decision history,
scientific baseline, source paths and deadline checkpoints.

Completed for this workstream:

- Preserved the conservative route as checkpoint `0e1634a` on both remotes.
- Rechecked 78 recorded file hashes; all matched. Production row counts remained
  20,081 / 20,053 non-NULL composites.
- Recorded the difference between Astra's conditional acceptance of conservative
  claims and a conclusion that fuller temporal validation is infeasible.
- Added an automatic continuation pointer in repository `AGENTS.md`.

Next: assess remaining source reconstruction, define ranking versus HIGH-gate
evaluation, and freeze a defensible expanded protocol/cohort before new outcomes.
The existing pilot cases/ranks are already known. This status file is **not** a
frozen experimental protocol, and no expanded scoring or independent-validation
result has yet been produced.

Preserve earlier `temporal_extension/` protocols/results unchanged. Use separate
task-owned raw caches and outputs; avoid source substitutions justified by better
case performance. The first planned source-feasibility checkpoint is 8 October.

## Execution started on 6 October 2026

The user explicitly instructed execution of the full expanded workstream after
checkpoint `91f34dd`. No expanded ranking has yet been calculated.

- Historical HPA v20 RNA, IMPC release11 and ZFIN 30/31 December 2020 files
  downloaded completely; acquisition manifests and schemas retained.
- June2020 gene2pubmed recovered by validated resumable byte ranges: 47,311,419
  bytes, SHA-256 `b8e197c83c43bfa2a34660244b1522e6f9d5168039471c77f4b64f63dbc57b37`;
  full gzip integrity checked, 12,720,364 lines, 1,501,741 human associations.
- RetNet complete genes/references/discovery-date catalogs and ten relevant
  PanelApp panels acquired. RetNet date screening nominated 42 records,
  including noncoding and date-ineligible cases; this is not an eligible cohort.
- Complete date-bounded title/abstract PMID context-set acquisition has finished
  for all six queries; unique PMID counts equal their returned hit counts.
  This is not a historical text snapshot; no present-day MeSH queries are used.
- `PROTOCOL_DRAFT.md` describes source differences and required adjudication.
  Astra independent review requested before protocol/roster freeze.
- The expanded analogue cannot be called an exact modern production replay:
  historical HCOP vote counts and complete annotation subchannels have not been
  recovered. Census did not exist, but original 2019 retinal single-cell matrices
  and labels can replace that channel. The no-literature archived variant and source sensitivities are
  part of the design, not fallbacks selected after case outcomes.

The range and literature acquisitions are complete. Raw files reside only in the ignored task-owned local
cache; Git records their manifests, not a backup of those source files.

## Additional pre-outcome progress

Checkpoint `e54b883` was pushed to both remotes. Later work is a new checkpoint.
No v2 score, case rank, HIGH outcome or recall statistic exists yet.

- Fresh GTEx v8 download verified against recovered decompressed content;
  official public release date 26 August 2019.
- GEO GSE137537/GSE137846 original matrices/features/labels downloaded completely:
  9,356/847 original rods/cones. Seq-Well's omitted barcode header is repaired
  explicitly. HPA v20 RNA has neither retina nor cerebellum and is excluded;
  it cannot supply target/background contrast. No direct hair-cell channel.
- Complete catalog ledger: 2,100 source/domain records, 1,081 gene/locus keys,
  394 historical green-reference keys. Human phenotype/inheritance closure audit
  remains necessary. Other 682 have completed original standardized searches;
  broader all-source gene/alias+target searches now run with laterality/heterotaxy,
  relaxed abstract requirements and every cursor-page hash.
- 157 pre-cutoff nomination searches completed. Broader Mendelian/preprint
  searches cover 164 nominations, with two large queries resumed by pagination.
  No-hit never establishes clinical absence.
- 169 clinical JATS requests finished: 132 complete, 37 retained HTTP500 responses.
  Official PMC/publisher reads supply fallbacks; missing proof stays unresolved.
- `cohort_screening/adjudication_notes_draft.json` records clinical evidence,
  date pitfalls and pending checks; it is **not a frozen accepted roster**.
  Preprints/early-human candidates affect novelty assignments. Pilot cases stay
  previously inspected references.
- Annotated/compound PMID parsing corrected after Astra review. Before/after
  ledgers retained; original 682 standardized requests are byte-identical.
- Reconstruction adapters drafted in `scripts/revision_temporal_v2_reconstruct.py`,
  **not executed on real evidence**. Five focused parser checks passed locally:
  `.venv/bin/python -m pytest tests/test_revision_temporal_v2.py -q`,
  Python3.13.1/macOS arm64, one existing Pydantic warning.

Next: finish broader screening and uniform clinical/date/scope closure, freeze
protocol/source manifest/clinical roster in Git, then reconstruct and evaluate.


## Latest pre-outcome closure work

Broad screening is now complete: 682/682 requests, 57,153 adopted records.
The aliases ALL (BCR), LARGE (LARGE1), GAP (RASA1) and AT-1 (SLC33A1) produced
large ordinary-language result sets and were omitted from corrected requests.
Genes/official symbols were retained; all superseded pages remain in the ignored
cache. `broad_target_search_manifest.json` selects the adopted paths. The
nomination helper now consumes that manifest, including its corrected subdirectory.

`source_inventory_draft.json` inventories 24 adopted numerical source files,
204,322,926 bytes. This is still a draft source contract, not an outcome freeze.
`clinical_roster_draft.json` retains all 1,081 catalog keys and 11 additional
previously inspected controls. Its 45 proposed strong cases are not final:
functional/date/target-family fields and independent review must close first.
No unresolved or unnominated catalog record is called a clinical negative.

Important new source adjudications: STXBP3's primary2018 hearing abstract precedes
its2021 journal report; EGFLAM was proposed in a2015 familial-Meniere study;
DAP3 appears in a2017 thesis whose public-deposit date is not verified. OGDHL
has substantial contrary human-validity evidence and is exploratory rather than
principal. TBX2's earlier CNV/negative-screen claim remains unresolved. RNF220,
DHRSX, MRPL49, DAP3, PLCG1 and KCNJ16 family counts have been checked without
substituting total multisystem patient/family counts for target-family counts.
RNU noncoding cases remain explicit universe exclusions; RNU6-1's per-paralog
family count is unresolved. Publisher SSL failures and an interrupted EPMC ZIP
attempt are recorded; the partial ZIP is not an accepted workbook.

New evaluator enforces a committed freeze before numerical reconstruction and
principal cohort rules. Full local suite:352 passed,17 existing warnings on
Python3.13.1/macOS arm64. No numerical reconstruction or Linux parity claim.
Next: finish pre-outcome independent roster review, commit the final freeze,
then execute both co-primary versions and every declared sensitivity.


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

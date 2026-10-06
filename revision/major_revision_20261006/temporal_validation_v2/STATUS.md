# Expanded temporal validation — workstream status

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

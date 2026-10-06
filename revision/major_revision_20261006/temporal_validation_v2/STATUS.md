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
- Complete date-bounded title/abstract PMID context-set acquisition is running.
  This is not a historical text snapshot; no present-day MeSH queries are used.
- `PROTOCOL_DRAFT.md` describes source differences and required adjudication.
  Astra independent review requested before protocol/roster freeze.
- The expanded analogue cannot be called an exact modern production replay:
  historical HCOP vote counts, complete annotation subchannels and Census are
  unavailable. The no-literature archived variant and source sensitivities are
  part of the design, not fallbacks selected after case outcomes.

Active acquisition commands are `scripts/revision_temporal_v2_ranges.py`
(resumable, now complete) and `scripts/revision_temporal_v2_literature.py`
(resumable page caches). Raw files reside only in the ignored task-owned local
cache; Git records their manifests, not a backup of those source files.

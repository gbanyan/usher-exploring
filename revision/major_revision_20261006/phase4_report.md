# Phase 4 completion: revised claims and numerical replay

Phase4 completes revised source content, post-review diagnostics and replay infrastructure. Final journal artifacts are not yet packaged. The production database/configuration, weights, source-level HIGH gate, comparator selection and frozen primary outcomes are preserved. The manuscript is now revised; immutable submission prose is in `baseline/` rather than used as a mutable replay input.

## Scientific results and interpretation

Six post-outcome diagnostic TSVs report the entire fixed-pair family, source-observation balance and historical tissue/completeness audit. Common-observed-layer paired concordance remains 23/27 Usher and 75/84 SYSCILIA; joint animal/literature omission falls to 15/27 and 48/84 (55.6%/57.1%). No matching/threshold retuning occurred. Historical top100 has eleven one-layer genes and 83 lacking localization; three manually selected later association cases lack accepted retinal HPA observations. This reinforces dependence on ascertainment and available measurements rather than establishing novel disease-gene validity.

Revised main text gives separate nine-Usher/28-SYSCILIA outcomes, all nine Usher traces in Table3 and separately traced optional-strategy control groups in Table2, threshold sensitivities, matched comparators, all major weighting/missingness/proxy limitations and the restricted archive pilot. Exact animal combined-count and localization HPA-factor precedence descriptions were corrected against implementation after independent review. The biological rationale is preserved, with supporting references added and retina/proxy expression replacing overstrong Usher-specific tissue terminology. HIGH denotes a control-calibrated priority tier. No independently validated novel Usher-gene discovery, optimal weights, full temporal validation or general clinical specificity is claimed.

`rebuttal.md` covers all 10 major/7 minor downloaded-report points and six correspondence points. `reviewer_crosswalk.tsv` records completed source changes and explicitly retains final-file checksums/release disposition as Phase5 tasks. A/B source labels await journal numbering, and section references await final pagination. Comparators are eligibility-negative disease annotations, not verified biological negatives.

## Reproducibility and checks

The derived bundle contains schema-checked canonical TSVs for four tables, a frozen historical HPA ordinal panel and manifests. Live ClinGen/HGNC comparator exports are distributed as exact text snapshots. URLs, dates, hashes, unknown original acquisition fields and raw-regeneration limits are recorded in `reproducibility/source_inventory.json`. Large text snapshots retain useful diffs; live databases, raw caches, binaries and environments are excluded. The unrelated untracked root `uv.lock` remains untouched.

A fresh task-owned local macOS arm64 environment used Python3.13.1, uv0.12.23 and 105 pinned dependencies plus the editable project. Dependency compatibility: 106 packages compatible. Final full test command:

```sh
rtk proxy data/cache/phase4-replay-20261006/venv/bin/python -m pytest -q
```

Result: **345 passed**, 17 pre-existing warnings (343 existing tests plus two new replay/missingness tests). Tests cover quoted text/empty string/zero/NULL round-trips, hash rejection and common-layer omission semantics. A first clean run exposed an import-path issue introduced by the helper extraction; fixed before validation.

Clean-environment replay rebuilt a task-owned DuckDB from the bundle and reproduced **28 TSVs byte-for-byte**: nine Phase2, five eligibility/matching, four Phase3, four archival, six post-review. The historical verifier independently checked 115,002 ranking rows and 72 case rows, with maximum composite error 2.22e−16 and all position/percentile/top-K checks passing. Recorded verification remains in `reproducibility/numerical_replay_verification.json`; exact commands and limitations are in its README. This is numerical replay, not complete raw-source regeneration or tested Linux/container parity.

Figure commands were exercised in clean task-owned output directories with original cached mantis classifier predictions. Figure5 was visually checked, records the explicit 500/20,016 background sample with seed42/ID ordering and exports sampled IDs. A Figure6 function default briefly wrote original figure paths during replay; original tracked figure bytes were restored and the call now explicitly passes the task-owned output. No original submission figure changes are included. PNG/PDF byte identity is not claimed; final rendering belongs to Phase5.

Independent Astra high review checked revised formulas/claims, numerical tables, temporal coverage and then the rebuttal/replay guide. It found no further major method or numerical issue after corrections; minor 23→28-table count and Additional8/9 versus checksum10 references were fixed. No additional experiments are needed to support the present conservative claims. This conclusion does not mean independent validation has been achieved.

## Phase5 boundary

Assemble/render revised journal DOCX/PDF and supplementary artifacts; integrate selected revision tables into Additional-file topology; verify actual delivered TXT/JSON/table hashes after conversion; replace branch links with the exact final version; decide exact-version permanent archival/DOI disposition; map reviewer labels and paginate the response. `submission_conversion_audit.json` confirms the original Additional6 mismatch hashes Markdown versus TXT separately. None of those final converted-file/DOI tasks is represented as already complete.

# Revision numerical replay

This package reproduces the frozen numerical analyses from distributable derived tables. It is not complete regeneration of the original six raw-source acquisition layers. Production annotation/animal fields include restored historical donor-derived fields; original unrecorded retrieval times remain unknown. See `source_inventory.json`, `../input_manifest.json` and `../../../docs/submission-database-recovery.md`.

## Tested environment

Local macOS arm64, Python 3.13.1, uv 0.12.23. `requirements.lock.txt` pins 105 non-project distributions, including build tooling; the editable project is installed without dependency resolution or build isolation. A task-owned fresh environment passed `uv pip check` (106 compatible distributions) and the 343 existing tests with 17 existing warnings. Linux/container parity has not been tested. This is an exact-version lock, not a cross-platform hashed-wheel lock. The unrelated root `uv.lock` was not adopted.

From repository root, with uv available, use a NEW task-owned directory (existing outputs are intentionally preserved):

```sh
rtk proxy uv venv --python 3.13.1 data/cache/revision-replay/venv
rtk proxy uv pip install --python data/cache/revision-replay/venv/bin/python --no-deps -r revision/major_revision_20261006/reproducibility/requirements.lock.txt
rtk proxy uv pip install --python data/cache/revision-replay/venv/bin/python --no-deps --no-build-isolation -e .
rtk proxy uv pip check --python data/cache/revision-replay/venv/bin/python
rtk proxy data/cache/revision-replay/venv/bin/python -m pytest -q
rtk proxy data/cache/revision-replay/venv/bin/python scripts/revision_replay.py build --database data/cache/revision-replay/pipeline.duckdb
rtk proxy data/cache/revision-replay/venv/bin/python scripts/revision_replay.py verify --database data/cache/revision-replay/pipeline.duckdb
```

The bundle contains four canonical sorted TSVs and exact DuckDB column schemas. `\N` is NULL; an empty string and an observed zero remain distinct. Import validates canonical hashes of all four tables. The replay database is derived/task-owned, not the live database; scripts open it read-only. The frozen submission manuscript copy is used for baseline checks, so revised prose may change without invalidating numerical replay.

## Frozen analyses and additional diagnostics

```sh
rtk proxy data/cache/revision-replay/venv/bin/python scripts/revision_phase2.py --database data/cache/revision-replay/pipeline.duckdb --output-dir data/cache/revision-replay/phase2
rtk proxy data/cache/revision-replay/venv/bin/python scripts/revision_phase3_outcomes.py --database data/cache/revision-replay/pipeline.duckdb --output-dir data/cache/revision-replay/phase3
rtk proxy data/cache/revision-replay/venv/bin/python scripts/revision_phase4.py --output-dir data/cache/revision-replay/phase4
```

Phase3 uses the already frozen, committed roster; it does not require reselecting negatives or committing a copied scratch roster. If replaying a copied byte-identical roster, pass `--roster-dir` and retain the default `--frozen-roster-dir` reference. Phase4 reads the distributed score bundle, original 111 pairs and frozen historical components; it requires no live database or full HPA archive. Its common-layer/omission analyses are explicitly post-outcome review sensitivities, not retrospectively prespecified validation.

## Comparator roster replay

The mutable 2026-10-06 ClinGen/HGNC exports are included as text snapshots in `phase3_live_snapshots/`; downloads of today's live exports would not be equivalent. The two HPO v2026-09-01 files can be acquired from the fixed release URLs and must match the original hashes.

```sh
rtk proxy data/cache/revision-replay/venv/bin/python scripts/revision_sources.py --output-dir data/cache/revision-replay/comparator-sources
rtk proxy data/cache/revision-replay/venv/bin/python scripts/revision_phase3_roster.py --database data/cache/revision-replay/pipeline.duckdb --source-dir data/cache/revision-replay/comparator-sources --output-dir data/cache/revision-replay/roster
```

For an existing verified cache, add `--existing-source-dir data/cache/phase3-sources-20261006` to source preparation. All four source hashes are checked. The eligibility/matching TSVs, not newly generated timestamps/manifest execution paths, are expected to be byte-identical.

## Restricted historical reconstruction

Only five complete historical files are required for the executed four-layer score. Failed probes and partial downloads are preserved in original records but not needed for numerical reconstruction. This remains a bounded archive/scoring pilot, not full temporal validation. Available GTEx/HPA RNA were outside the executed source contract; absence from this pilot is not archival infeasibility.

```sh
rtk proxy data/cache/revision-replay/venv/bin/python scripts/revision_temporal_download.py --required-only --cache-dir data/cache/revision-replay/historical-raw --output-manifest data/cache/revision-replay/historical-download.json
rtk proxy data/cache/revision-replay/venv/bin/python scripts/revision_temporal_analysis.py --cache-dir data/cache/revision-replay/historical-raw --source-manifest revision/major_revision_20261006/temporal_extension/download_manifest.json --baseline-database data/cache/revision-replay/pipeline.duckdb --output-dir data/cache/revision-replay/temporal
rtk proxy data/cache/revision-replay/venv/bin/python scripts/revision_temporal_verify.py --cache-dir data/cache/revision-replay/historical-raw --results-dir data/cache/revision-replay/temporal --baseline-database data/cache/revision-replay/pipeline.duckdb --output data/cache/revision-replay/temporal-verification.json
```

The analysis compares downloaded bytes against the original frozen source manifest, not merely the new download log. Existing local historical files can also be supplied through `--cache-dir`; this was the clean-environment replay used for verification. Five required files were acquired and hash-verified originally; this revision replay did not redownload them all. Source acquisition metadata distinguishes cached mtime from original HTTP response timestamps. `probe_registry.json` lists the 51 bounded archival probes; exploratory requests can be rerun with `revision_temporal_probe.py --registry-json ... --cache-dir ... --output ...`, but network responses/prefix hashes can change and are not numerical validation.

## Figures and historical exploratory outputs

```sh
rtk proxy data/cache/revision-replay/venv/bin/python scripts/fig1_architecture.py --output-dir data/cache/revision-replay/fig1
rtk proxy data/cache/revision-replay/venv/bin/python scripts/paper_figures.py --database data/cache/revision-replay/pipeline.duckdb --output-dir data/cache/revision-replay/figures
rtk proxy data/cache/revision-replay/venv/bin/python scripts/ablation_study.py --database data/cache/revision-replay/pipeline.duckdb --output-dir data/cache/revision-replay/fig6 --output-csv data/cache/revision-replay/ablation.csv
rtk proxy data/cache/revision-replay/venv/bin/python scripts/mantisml_benchmark.py --database data/cache/revision-replay/pipeline.duckdb --mantisml-dir data/external/mantisml --output-dir data/cache/revision-replay/mantis
```

Figure 5 samples 500 of 20,016 eligible non-control scored labels, without replacement, NumPy seed 42 and retained-ID ordering. It exports sampled IDs. Figure 7 retains the earlier conditional-overlap statistic; Phase2 reports full-universe/top-K alternatives. The cached mantis comparison requires the original six per-classifier prediction CSVs; their training run is not reconstructed. They are local ignored external inputs, so The original Figure8 (revised Figure9) full regeneration is not guaranteed from the derived bundle alone. These commands were exercised with existing caches. Updated Figure5 sampling order may change display points compared with the original submission; it does not change scores or control percentiles. PNG/PDF byte identity is not asserted because rendering/metadata can vary.

## Verified outputs and packaging limits

`numerical_replay_verification.json` records 28 byte-identical TSVs: nine Phase2, five eligibility/matching, four Phase3 outcomes, four historical and six post-review diagnostics. Execution metadata and script hashes differ legitimately from preserved original manifests. `submission_conversion_audit.json` distinguishes original repository Markdown from submitted Additional file6 TXT hashes; it does not certify newly converted journal files.

The Phase5 upload set is in `submission/bmc_bioinformatics_major_revision_20261007/`, with editable documents, rendered PDFs, page-location index, and actual delivered-file checksums. `scripts/package_revision_submission.py --verify-only` checks those artifacts and ZIP payloads. No archive DOI has been minted; the exact analysis Git checkpoints and package/source SHA-256 hashes identify the versions. Source/bundle hashes cannot substitute for hashes of converted journal artifacts. Large HGNC and derived TSVs are retained as text for useful inspection/diffs; no live database, raw cache, environment or binary release output is included. Source terms and citation metadata remain attached to their respective source records.

## Expanded retrospective temporal evaluation

The later expanded evaluation is separate from the preserved restricted pilot. Its original/amended pre-outcome freezes are `bd6bb2f` and `53da295`; completed numerical outputs and the bounded internal review are at `736e16f`. See `../temporal_validation_v2/OUTCOME_REPORT.md` and Supplementary Methods S6. The current analysis environment passed 354 tests (17 existing warnings); nine expanded temporal TSVs plus their manifest were byte-identical in clean raw reconstruction.

Additional file 12 includes all historical components, co-primary ranking rows, 23-scheme case/endpoint tables, clinical/date ledger, source records, code and environment lock. For an archive-only derived numerical check in the pinned analysis environment:

```sh
rtk proxy .venv/bin/python scripts/revision_temporal_derived_replay.py
```

This verifies 38,334 primary score/count/rank rows exactly, including NULLs, using contiguous float64 component storage as in the original reconstruction. It does not recreate HIGH source flags, alternative global expression vectors, raw-source acquisition or clinical adjudication. Full raw reconstruction additionally requires the recorded original source/cache bytes and original Git freeze commits; clinical search/full-text caches are not distributed. Six frozen literature-context PMID sets are bundled without paper text. Do not query current PubMed and label the new response equivalent to the frozen context sets.

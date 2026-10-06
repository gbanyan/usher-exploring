# August 2026 submission database recovery

The production database was recovered locally on macOS on 6 October 2026.
`data/pipeline.duckdb` now contains 20,116 frozen Ensembl 113 universe IDs,
20,081 scored analysis labels, and 20,053 non-NULL composite scores.

## Why recovery was necessary

The 14 August integration session rebuilt the database inside
`herdr-integration-final` and validated its outputs before submission. The final
transfer to the main checkout used a Git binary patch plus a separate PDF copy.
DuckDB files were ignored by Git and were not included in that transfer. The
integration worktree was subsequently removed, leaving the main checkout's old
19,557-row scored database alongside the updated tracked outputs.

Historical session evidence:

- Integration/rebuild: `01a00051-6809-7f30-ad7b-e18385f305a8`.
- Transfer/cleanup: `019fff90-4786-74c2-8084-7d056ce458c5`.
- Supplementary artifact checkpoint: `73935caa8bc1f80af3e89347efcfc27118a496af`.
- Code used for this recovery: `ed2d00d9be0de3fbdf692bd46acbf0102bfc8d35`.

## Preserved local files

- Active recovered DB: `data/pipeline.duckdb`.
- Original historical donor: `data/pipeline_source.duckdb`.
- Additional pre-recovery backup: `data/pipeline.duckdb.bak-prerecovery-20261006`.
- Isolated recovery, generated reports, and stage logs:
  `data/cache/submission-recovery-20261006/`.
- Previous provenance sidecars:
  `data/cache/submission-recovery-20261006/previous_provenance/`.
- Tracked verification record: `data/report/database_recovery_20261006.json`.

These databases, logs, and raw caches are intentionally excluded from Git.
Preserve them separately before deleting a checkout or worktree. Git commits
and artifact checksum tests do not back up or validate an ignored runtime DB.

## Offline reproduction

Run from the repository root using its installed development environment:

```bash
rtk proxy .venv/bin/python scripts/recover_submission_database.py \
  --destination data/cache/submission-recovery-new \
  --donor-db data/pipeline_source.duckdb
```

The destination must be new. The script verifies all eleven input hashes against
the historical integration-session audit before copying sources into an isolated
directory. It runs cache-only setup, donor migration for annotation and animal
phenotypes, local reprocessing of gnomAD/localization/literature/expression,
scoring, reporting, and internal evaluation. Outbound socket connections are
blocked in each pipeline stage; missing inputs fail rather than fetching.

Annotation and animal-model evidence reuse historical derived source fields by
exact Ensembl ID and recompute their scores. This is not a raw-source rerun of
those two layers. Recovery does not fill missing historical retrieval dates or
establish complete upstream provenance.

The script produces a new DB, logs, and `verification.json`; it does not replace
the active DB or any submission artifacts. A completed recovery can be checked
again without rerunning the pipeline:

```bash
rtk proxy .venv/bin/python scripts/recover_submission_database.py \
  --destination data/cache/submission-recovery-20261006 --verify-only
```

## Verification and installation

The 6 October recovery passed these checks before installation:

- All eleven historical input SHA-256 values matched, including the donor DB.
- All 20,081 scored IDs, labels, evidence counts, and composite scores matched
  the tracked full-universe ablation table, including excluded/NULL-score genes.
- All 18,387 candidate IDs and all 34 output columns matched the submission
  candidate table, with absolute numeric tolerance `1e-12`.
- Tiers matched: HIGH 62, MEDIUM 9,673, LOW 8,652.
- Both donor-migration audit TSVs were byte-identical.
- Every internal evaluation report line matched; the two positive-control group
  rows were rendered in a different order.
- Existing regression suite: `rtk proxy .venv/bin/python -m pytest tests/ -q`:
  327 passed, 17 existing warnings, on local macOS.

The old DB was copied to the backup and donor paths before the validated DB was
copied to a temporary file and atomically installed. Recovered provenance
sidecars were copied back with their previous versions archived. The original
manuscript, submission files, candidate tables, and checksum manifest were
preserved. The new recovery record is separate from the frozen submission
checksum manifest.

Recovery environment: Python 3.13.1, DuckDB 1.5.5, Polars 1.44.2, with
`POLARS_MAX_THREADS=2`. The original report recorded Polars 1.43.2; numerical
reproduction passed with the installed version. This is not a claim that the
complete historical software environment was recreated or locked.

The recovered DB SHA-256 is
`0beb4f61c62ebff2ba6358069d9eb37cb6c4a9366140bb1c1c486cd2d59f2c65`.
The historical donor SHA-256 is
`1f5f606d0fb1d1ea3ca90386416c804ea70c809b8ea670c4a94e7659dac641d8`.
Database bytes include runtime/checkpoint metadata; numerical equivalence to
the submission is the recovery criterion, not byte identity to the removed DB.

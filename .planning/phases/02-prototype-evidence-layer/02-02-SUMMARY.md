---
phase: 02-prototype-evidence-layer
plan: 02
subsystem: evidence-layer
tags: [gnomad, duckdb, cli, provenance, checkpoint-restart, integration-tests]

# Dependency graph
requires:
  - phase: 01-data-infrastructure
    provides: "DuckDB persistence, provenance tracking, CLI framework"
  - plan: 02-01
    provides: "gnomAD constraint fetch->filter->normalize pipeline"
provides:
  - "DuckDB persistence for gnomAD constraint data (gnomad_constraint table)"
  - "CLI evidence command group with gnomad subcommand"
  - "Checkpoint-restart pattern for evidence layers"
  - "Provenance tracking for evidence processing"
  - "Query helper for constrained genes (validates GCON-03 interpretation)"
  - "Complete fetch->transform->load->query evidence layer pattern"
affects: [03-multi-evidence-scoring, evidence-integration, future-evidence-sources]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Evidence layer DuckDB persistence: load_to_duckdb with CREATE OR REPLACE (idempotent)"
    - "CLI evidence command group structure (extensible for future sources)"
    - "Checkpoint-restart with has_checkpoint: skip processing if table exists"
    - "Provenance sidecar pattern: JSON metadata alongside data files"
    - "Query helper functions: demonstrate DuckDB query capability and evidence interpretation"
    - "Integration testing pattern: synthetic fixtures, mocked downloads, end-to-end verification"

key-files:
  created:
    - src/usher_pipeline/evidence/gnomad/load.py
    - src/usher_pipeline/cli/evidence_cmd.py
    - tests/test_gnomad_integration.py
  modified:
    - src/usher_pipeline/evidence/gnomad/__init__.py
    - src/usher_pipeline/cli/main.py

key-decisions:
  - "load_to_duckdb uses CREATE OR REPLACE for idempotency (not INSERT, can safely re-run)"
  - "query_constrained_genes demonstrates GCON-03 interpretation: constrained genes are weak signal for under-studied importance, not direct cilia evidence"
  - "CLI evidence command group for extensibility: future evidence sources (ClinGen, GTEx, etc.) follow same pattern"
  - "Checkpoint at table level not file level: has_checkpoint('gnomad_constraint') checks DuckDB table existence"
  - "Provenance sidecar saved alongside raw data (data/gnomad/constraint.provenance.json) for traceability"
  - "Integration tests use synthetic TSV fixtures (no external downloads, fast, reproducible)"
  - "CLI evidence gnomad supports --force flag for re-download/reprocess, --url for custom data sources"

patterns-established:
  - "Evidence layer CLI pattern: command group with subcommands for each source"
  - "Evidence layer persistence: process DataFrame -> load_to_duckdb -> save provenance sidecar"
  - "Evidence layer checkpoint-restart: check has_checkpoint before processing, skip if exists unless --force"
  - "Integration test pattern: test_config fixture, sample_tsv fixture, end-to-end verification with mocked downloads"

# Metrics
duration: 4min
completed: 2026-02-11
---

# Phase 02 Plan 02: gnomAD Evidence Layer Integration Summary

**DuckDB persistence, CLI orchestration, checkpoint-restart, and provenance tracking complete the end-to-end evidence layer pattern for gnomAD constraint data**

## Performance

- **Duration:** 3 min 51 sec
- **Started:** 2026-02-11T10:17:32Z
- **Completed:** 2026-02-11T10:21:23Z
- **Tasks:** 2
- **Files modified:** 5 (3 created, 2 modified)
- **Tests added:** 12 integration tests (all passing)
- **Total test count:** 70 passing, 1 skipped

## Accomplishments

- DuckDB persistence layer: gnomAD constraint data saved to gnomad_constraint table with CREATE OR REPLACE (idempotent)
- CLI evidence command group with gnomad subcommand orchestrates full fetch->transform->load pipeline
- Checkpoint-restart pattern: re-running skips processing if gnomad_constraint table exists (use --force to override)
- Provenance tracking records all processing steps with details (row counts, quality flag counts, NULL handling)
- Provenance sidecar JSON saved alongside data (data/gnomad/constraint.provenance.json) for full traceability
- query_constrained_genes helper demonstrates DuckDB query capability and validates GCON-03 interpretation
- 12 comprehensive integration tests cover end-to-end pipeline, checkpoint-restart, provenance, CLI, and edge cases
- Full test suite passes: 70 tests (58 existing + 12 new) with no regressions from Phase 1

## Task Commits

Each task was committed atomically:

1. **Task 1: Create DuckDB loader and CLI evidence command** - `ee27f3a` (feat)
   - load_to_duckdb: Saves constraint DataFrame to gnomad_constraint table with provenance tracking
   - query_constrained_genes: Queries constrained genes by LOEUF threshold (validates GCON-03 interpretation)
   - evidence_cmd.py: CLI command group with gnomad subcommand (fetch->transform->load orchestration)
   - Checkpoint-restart: Skips processing if gnomad_constraint table exists (--force to override)
   - Full CLI: usher-pipeline evidence gnomad [--force] [--url URL] [--min-depth N] [--min-cds-pct N]

2. **Task 2: Create integration tests for full gnomAD pipeline** - `56e04e6` (test)
   - 12 integration tests covering full pipeline: fetch->transform->load->query
   - test_full_pipeline_to_duckdb: End-to-end pipeline verification with DuckDB storage
   - test_checkpoint_restart_skips_processing: Checkpoint detection works correctly
   - test_provenance_recorded: Provenance step records expected details
   - test_provenance_sidecar_created: JSON sidecar file creation and structure
   - test_query_constrained_genes_filters_correctly: Query returns only measured genes below threshold
   - test_null_loeuf_not_in_constrained_results: NULL LOEUF genes excluded from queries
   - test_duckdb_schema_has_quality_flag: Schema includes quality_flag with valid values
   - test_normalized_scores_in_duckdb: Normalized scores in [0,1] for measured genes, NULL for others
   - test_cli_evidence_gnomad_help: CLI help text displays correctly
   - test_cli_evidence_gnomad_with_mock: CLI command runs end-to-end with mocked download
   - test_idempotent_load_replaces_table: Loading twice replaces table (not appends)
   - test_quality_flag_categorization: Quality flags correctly categorize genes

## Files Created/Modified

**Created:**
- `src/usher_pipeline/evidence/gnomad/load.py` - DuckDB loader and query helpers for gnomAD constraint data
- `src/usher_pipeline/cli/evidence_cmd.py` - CLI evidence command group with gnomad subcommand
- `tests/test_gnomad_integration.py` - 12 integration tests covering end-to-end pipeline

**Modified:**
- `src/usher_pipeline/evidence/gnomad/__init__.py` - Added load_to_duckdb and query_constrained_genes exports
- `src/usher_pipeline/cli/main.py` - Registered evidence command group

## Decisions Made

1. **load_to_duckdb uses CREATE OR REPLACE** - Idempotent operation, safe to re-run without data duplication
2. **query_constrained_genes as GCON-03 interpretation** - Demonstrates constrained genes are "important but under-studied" signals, not direct cilia involvement
3. **CLI evidence command group** - Extensible pattern for future evidence sources (ClinGen, GTEx, HPA, etc.)
4. **Checkpoint at table level** - has_checkpoint('gnomad_constraint') checks DuckDB table existence, simpler than file-based checkpoints
5. **Provenance sidecar co-located with data** - data/gnomad/constraint.provenance.json saved alongside raw data for traceability
6. **Integration tests with synthetic fixtures** - Fast, reproducible, no external dependencies (no real gnomAD downloads)
7. **CLI --force flag for re-processing** - Override checkpoint to re-download and reprocess data

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed smoothly with no blockers.

## User Setup Required

None - evidence layer ready to use. To fetch gnomAD constraint data:

```bash
usher-pipeline evidence gnomad
```

No external authentication required. gnomAD constraint file is publicly accessible.

## Next Phase Readiness

**Ready for Phase 3 (Multi-Evidence Scoring):**
- Evidence layer pattern complete: fetch -> transform -> load -> query
- DuckDB storage ready for evidence aggregation across sources
- Checkpoint-restart pattern established for long-running evidence fetches
- Provenance tracking captures full pipeline execution history
- CLI command structure extensible for future evidence sources
- Integration test pattern established for evidence layers

**Template for future evidence sources:**
- CLI: Add subcommand to evidence command group (e.g., `evidence clingen`)
- Pipeline: fetch (download with retry) -> transform (filter/normalize) -> load (DuckDB) -> save provenance
- Checkpoint: Check has_checkpoint before processing, skip if exists unless --force
- Tests: Integration tests with synthetic fixtures, mocked downloads, end-to-end verification

**Blockers:** None

**Considerations for next plans:**
- Evidence aggregation: Join gnomad_constraint with gene_universe on Ensembl IDs
- Multi-source scoring: Combine gnomAD constraint with other evidence layers
- Evidence weighting: Apply scoring weights from config (gnomad: 0.20)
- Missing evidence handling: Genes without gnomAD data should not be penalized (NULL != zero)

---
*Phase: 02-prototype-evidence-layer*
*Completed: 2026-02-11*

## Self-Check: PASSED

All claimed files verified:
- src/usher_pipeline/evidence/gnomad/load.py ✓
- src/usher_pipeline/cli/evidence_cmd.py ✓
- tests/test_gnomad_integration.py ✓

All claimed commits verified:
- ee27f3a (Task 1) ✓
- 56e04e6 (Task 2) ✓

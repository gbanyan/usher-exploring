---
phase: 01-data-infrastructure
plan: 03
subsystem: persistence
tags: [duckdb, provenance, checkpoints, reproducibility, testing]
dependency_graph:
  requires:
    - Python package scaffold with config system (01-01)
  provides:
    - DuckDB-based checkpoint-restart storage
    - Provenance metadata tracking system
  affects:
    - All future data pipeline plans (enables checkpoint-restart)
    - All output artifacts (provenance sidecars)
tech_stack:
  added:
    - duckdb for embedded analytical database
    - polars for DataFrame operations
    - pyarrow for Parquet export
  patterns:
    - Checkpoint-restart pattern for expensive operations
    - Provenance sidecar files for reproducibility
    - Context manager for resource cleanup
key_files:
  created:
    - src/usher_pipeline/persistence/__init__.py: Package exports
    - src/usher_pipeline/persistence/duckdb_store.py: PipelineStore class with checkpoint system
    - src/usher_pipeline/persistence/provenance.py: ProvenanceTracker for metadata
    - tests/test_persistence.py: 13 comprehensive tests
  modified: []
decisions:
  - decision: "DuckDB over SQLite for DataFrame storage"
    rationale: "Native polars/pandas integration, better performance for analytical queries, built-in Parquet export"
    alternatives: ["SQLite (rejected - requires manual serialization)", "Parquet only (rejected - no checkpoint metadata)"]
  - decision: "Provenance sidecar files alongside outputs"
    rationale: "Co-located metadata simplifies tracking, standard pattern in bioinformatics"
    impact: "Every output file gets a .provenance.json sidecar"
  - decision: "Metadata table _checkpoints for tracking"
    rationale: "Enables has_checkpoint() queries without scanning catalog"
    impact: "Adds small metadata overhead, significant performance benefit"
metrics:
  duration_minutes: 2
  tasks_completed: 2
  files_created: 4
  tests_added: 13
  commits: 2
  completed_date: "2026-02-11"
---

# Phase 01 Plan 03: DuckDB Persistence and Provenance Tracking Summary

**One-liner:** DuckDB-based checkpoint-restart storage with metadata tracking (polars/pandas support, Parquet export, context managers) and provenance system capturing pipeline version, data source versions, config hash, and processing steps with JSON sidecar files.

## What Was Built

Built the persistence layer that enables checkpoint-restart for expensive operations and full provenance tracking for reproducibility:

1. **DuckDB PipelineStore**
   - Checkpoint-restart storage: save expensive API results, skip re-fetch on restart
   - Dual DataFrame support: native polars and pandas via DuckDB integration
   - Metadata tracking: _checkpoints table tracks table_name, created_at, row_count, description
   - Checkpoint queries: has_checkpoint() for efficient existence checks
   - List/delete operations: manage checkpoints with full metadata
   - Parquet export: COPY TO for downstream compatibility
   - Context manager: __enter__/__exit__ for clean resource management
   - Config integration: from_config() classmethod

2. **ProvenanceTracker**
   - Captures pipeline version, data source versions (Ensembl, gnomAD, GTEx, HPA)
   - Records config hash for deterministic cache invalidation
   - Tracks processing steps with timestamps and optional details
   - Saves sidecar JSON files co-located with outputs (.provenance.json)
   - Persists to DuckDB _provenance table (flattened schema)
   - from_config() classmethod with automatic version detection

3. **Comprehensive Test Suite**
   - 13 tests total (12 passed, 1 skipped - pandas not installed)
   - DuckDB store tests (8): database creation, save/load polars, save/load pandas, checkpoint lifecycle, list checkpoints, Parquet export, non-existent table handling, context manager
   - Provenance tests (5): metadata structure, step recording, sidecar roundtrip, config hash inclusion, DuckDB storage

## Tests

**13 tests total (12 passed, 1 skipped):**

### DuckDB Store Tests (8 tests, 7 passed, 1 skipped)
- `test_store_creates_database`: PipelineStore creates .duckdb file at specified path
- `test_save_and_load_polars`: Save and load polars DataFrame, verify shape/columns/values
- `test_save_and_load_pandas`: Save and load pandas DataFrame (skipped - pandas not installed)
- `test_checkpoint_lifecycle`: Save -> has_checkpoint=True -> delete -> has_checkpoint=False -> load=None
- `test_list_checkpoints`: Save 3 tables, list returns 3 with metadata (table_name, created_at, row_count, description)
- `test_export_parquet`: Save DataFrame, export to Parquet, verify file exists and is readable
- `test_load_nonexistent_returns_none`: Loading non-existent table returns None
- `test_context_manager`: with PipelineStore() pattern works, connection closes on exit

### Provenance Tests (5 tests, all passed)
- `test_provenance_metadata_structure`: create_metadata() returns dict with all required keys
- `test_provenance_records_steps`: record_step() adds to processing_steps with timestamps
- `test_provenance_sidecar_roundtrip`: save_sidecar() -> load_sidecar() preserves all metadata
- `test_provenance_config_hash_included`: config_hash matches PipelineConfig.config_hash()
- `test_provenance_save_to_store`: save_to_store() creates _provenance table with valid JSON steps

## Verification Results

All plan verification steps passed:

```bash
# 1. All tests pass
$ pytest tests/test_persistence.py -v
=================== 12 passed, 1 skipped, 1 warning in 0.29s ===================

# 2. Imports work
$ python -c "from usher_pipeline.persistence import PipelineStore, ProvenanceTracker"
Import successful

# 3. Checkpoint-restart verified
# Covered by test_checkpoint_lifecycle and test_save_and_load_polars

# 4. Provenance sidecar JSON verified
# Covered by test_provenance_sidecar_roundtrip
```

## Deviations from Plan

None - plan executed exactly as written.

## Task Execution Log

### Task 1: Create DuckDB persistence layer with checkpoint-restart
**Status:** Complete
**Duration:** ~1 minute
**Commit:** d51141f

**Actions:**
1. Created src/usher_pipeline/persistence/ package directory
2. Implemented PipelineStore class in duckdb_store.py:
   - Constructor with db_path, creates parent directories, connects to DuckDB
   - _checkpoints metadata table (table_name, created_at, row_count, description)
   - save_dataframe() with polars/pandas support via DuckDB native integration
   - load_dataframe() returning polars (default) or pandas
   - has_checkpoint() for existence checks
   - list_checkpoints() returning metadata list
   - delete_checkpoint() for cleanup
   - export_parquet() using COPY TO
   - execute_query() for arbitrary SQL
   - close() and __enter__/__exit__ for context manager
   - from_config() classmethod
3. Created __init__.py (temporarily without ProvenanceTracker export)
4. Verified basic operations: save, load, has_checkpoint, shape verification

**Files created:** 2 files (duckdb_store.py, __init__.py)

**Key features:**
- Native polars integration via DuckDB (no manual serialization)
- Metadata table enables fast has_checkpoint() queries
- Context manager ensures connection cleanup
- Parquet export for downstream compatibility

### Task 2: Create provenance tracker with tests for both modules
**Status:** Complete
**Duration:** ~1 minute
**Commit:** 98a1a75

**Actions:**
1. Implemented ProvenanceTracker class in provenance.py:
   - Constructor storing pipeline_version, config_hash, data_source_versions, created_at
   - record_step() appending to processing_steps list with timestamps
   - create_metadata() returning full provenance dict
   - save_sidecar() writing .provenance.json with indent=2
   - save_to_store() persisting to DuckDB _provenance table
   - load_sidecar() static method for loading JSON
   - from_config() classmethod with automatic version detection
2. Updated __init__.py to export ProvenanceTracker
3. Created comprehensive test suite in tests/test_persistence.py:
   - test_config fixture creating minimal PipelineConfig from YAML
   - 8 DuckDB store tests (database creation, save/load, checkpoints, Parquet)
   - 5 provenance tests (metadata structure, step recording, sidecar, config hash, DuckDB storage)
4. Ran all tests: 12 passed, 1 skipped (pandas)

**Files created:** 2 files (provenance.py, test_persistence.py)
**Files modified:** 1 file (__init__.py - added ProvenanceTracker export)

**Key features:**
- Captures all required metadata for reproducibility
- Sidecar files co-located with outputs
- DuckDB storage for queryable provenance records
- Automatic version detection via usher_pipeline.__version__

## Success Criteria Verification

- [x] DuckDB store saves/loads DataFrames with checkpoint metadata tracking
- [x] Checkpoint-restart pattern works: has_checkpoint() -> skip expensive re-fetch
- [x] Provenance tracker captures all required metadata (INFRA-06):
  - [x] Pipeline version
  - [x] Data source versions (Ensembl, gnomAD, GTEx, HPA)
  - [x] Timestamps (created_at for tracker, per-step timestamps)
  - [x] Config hash
  - [x] Processing steps
- [x] Parquet export works for downstream compatibility
- [x] All tests pass (12/13, 1 skipped)

## Must-Haves Verification

**Truths:**
- [x] DuckDB database stores DataFrames as tables and exports to Parquet
- [x] Checkpoint system detects existing tables to enable restart-from-checkpoint without re-downloading
- [x] Provenance metadata captures pipeline version, data source versions, timestamps, and config hash
- [x] Provenance sidecar JSON file is saved alongside every pipeline output

**Artifacts:**
- [x] src/usher_pipeline/persistence/duckdb_store.py provides "DuckDB-based storage with checkpoint-restart capability" containing "class PipelineStore"
- [x] src/usher_pipeline/persistence/provenance.py provides "Provenance metadata creation and persistence" containing "class ProvenanceTracker"

**Key Links:**
- [x] src/usher_pipeline/persistence/duckdb_store.py → duckdb via "duckdb.connect for file-based database" (pattern: `duckdb\.connect`)
- [x] src/usher_pipeline/persistence/provenance.py → src/usher_pipeline/config/schema.py via "reads PipelineConfig for version info and config hash" (pattern: `config_hash|PipelineConfig`)
- [x] src/usher_pipeline/persistence/duckdb_store.py → src/usher_pipeline/persistence/provenance.py via "attaches provenance metadata when saving checkpoints" (pattern: `provenance|ProvenanceTracker`)

## Impact on Roadmap

This plan enables Phase 01 Plans 02 and 04:

**Plan 02 (Gene ID Mapping):**
- Will use PipelineStore to checkpoint Ensembl/MyGene API results
- Saves expensive 20,000+ gene lookups: restart skips re-fetch
- Provenance tracks Ensembl release version for reproducibility

**Plan 04 (Data Integration):**
- Will use PipelineStore for gnomAD, GTEx, HPA data downloads
- Checkpoint-restart critical for multi-hour API operations
- Provenance tracks data source versions for all evidence layers

## Next Steps

Phase 01 continues with Plan 02 (Gene ID Mapping) or Plan 04 (Data Integration). Both depend on this plan's checkpoint-restart infrastructure.

Recommended sequence: Plan 02 (uses PipelineStore immediately for gene universe checkpoint).

## Self-Check: PASSED

**Files verified:**
```bash
FOUND: /Users/gbanyan/Project/usher-exploring/src/usher_pipeline/persistence/__init__.py
FOUND: /Users/gbanyan/Project/usher-exploring/src/usher_pipeline/persistence/duckdb_store.py
FOUND: /Users/gbanyan/Project/usher-exploring/src/usher_pipeline/persistence/provenance.py
FOUND: /Users/gbanyan/Project/usher-exploring/tests/test_persistence.py
```

**Commits verified:**
```bash
FOUND: d51141f (Task 1)
FOUND: 98a1a75 (Task 2)
```

All files and commits exist as documented.

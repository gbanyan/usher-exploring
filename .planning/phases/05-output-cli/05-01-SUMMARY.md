---
phase: 05-output-cli
plan: 01
subsystem: output
tags: [polars, yaml, tsv, parquet, tiering, evidence-summary]

# Dependency graph
requires:
  - phase: 04-scoring-integration
    provides: scored_genes DataFrame with composite_score, evidence_count, and layer contributions
provides:
  - Confidence tier classification (HIGH/MEDIUM/LOW) based on composite_score and evidence_count
  - Per-gene evidence summary (supporting_layers and evidence_gaps columns)
  - Dual-format TSV+Parquet writer with YAML provenance sidecar
  - Comprehensive unit test suite for output module
affects: [05-02, 05-03, reporting, visualization, downstream-tools]

# Tech tracking
tech-stack:
  added: [pyyaml]
  patterns: [vectorized-polars-expressions, dual-format-output, provenance-sidecars, deterministic-sorting]

key-files:
  created:
    - src/usher_pipeline/output/tiers.py
    - src/usher_pipeline/output/evidence_summary.py
    - src/usher_pipeline/output/writers.py
    - src/usher_pipeline/output/__init__.py
    - tests/test_output.py
  modified: []

key-decisions:
  - "Configurable tier thresholds (HIGH: score>=0.7 and evidence>=3, MEDIUM: score>=0.4 and evidence>=2, LOW: score>=0.2)"
  - "EXCLUDED genes filtered out (below LOW threshold or NULL composite_score)"
  - "Deterministic sorting (composite_score DESC, gene_id ASC) for reproducible output"
  - "Dual-format TSV+Parquet with identical data for downstream tool compatibility"
  - "YAML provenance sidecar includes statistics (tier counts) and column metadata"
  - "Fixed deprecated pl.count() -> pl.len() usage for polars 0.20.5+ compatibility"

patterns-established:
  - "Vectorized polars when/then/otherwise chains for tier assignment (not row-by-row)"
  - "concat_list + list.drop_nulls + list.join for comma-separated string columns"
  - "Provenance YAML sidecars alongside output files for full traceability"
  - "Deterministic sorting before writing for reproducible output across runs"

# Metrics
duration: 4min
completed: 2026-02-11
---

# Phase 05 Plan 01: Output Generation Core Summary

**Tiered candidate classification with supporting/gap evidence tracking and dual-format TSV+Parquet output with YAML provenance sidecars**

## Performance

- **Duration:** 4 minutes
- **Started:** 2026-02-11T19:55:28Z
- **Completed:** 2026-02-11T19:59:31Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Implemented configurable confidence tier classification (HIGH/MEDIUM/LOW) with filtering of EXCLUDED genes
- Added per-gene evidence summary columns (supporting_layers and evidence_gaps) tracking which layers contributed
- Created dual-format writer producing identical TSV and Parquet outputs with YAML provenance sidecars
- Built comprehensive test suite with 9 tests covering all functionality (100% pass rate)

## Task Commits

Each task was committed atomically:

1. **Task 1: Tiering logic and evidence summary module** - `d2ef3a2` (feat)
   - tiers.py with assign_tiers() and configurable TIER_THRESHOLDS
   - evidence_summary.py with add_evidence_summary() and EVIDENCE_LAYERS
   - __init__.py with exports

2. **Task 2: Dual-format writer with provenance sidecar and unit tests** - `4e46b48` (feat)
   - writers.py with write_candidate_output()
   - tests/test_output.py with 9 comprehensive tests
   - Fixed deprecated pl.count() -> pl.len() usage

## Files Created/Modified

- `src/usher_pipeline/output/tiers.py` - Confidence tier assignment (HIGH/MEDIUM/LOW) with configurable thresholds
- `src/usher_pipeline/output/evidence_summary.py` - Per-gene supporting_layers and evidence_gaps columns
- `src/usher_pipeline/output/writers.py` - Dual-format TSV+Parquet writer with YAML provenance sidecar
- `src/usher_pipeline/output/__init__.py` - Package exports
- `tests/test_output.py` - 9 unit tests covering tiering, evidence summary, and writers

## Decisions Made

- **Configurable thresholds:** TIER_THRESHOLDS dictionary allows CLI configurability later while providing sensible defaults from research
- **EXCLUDED filtering:** Genes below LOW threshold (score < 0.2) or with NULL composite_score are filtered out before output
- **Deterministic sorting:** Sort by composite_score DESC, gene_id ASC for reproducible output across runs
- **Dual-format output:** TSV for human-readability and tools like Excel; Parquet for efficient large-scale data processing
- **YAML provenance:** Sidecar includes statistics (tier counts), column metadata, and timestamp for full reproducibility tracking
- **Polars 0.20.5+ compatibility:** Replaced deprecated pl.count() with pl.len() to eliminate deprecation warnings

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed deprecated polars API usage**
- **Found during:** Task 2 (test execution)
- **Issue:** pl.count() deprecated in polars 0.20.5+, producing warnings
- **Fix:** Replaced all occurrences of pl.count() with pl.len() in tests and writers.py, updated row access from row["count"] to row["len"]
- **Files modified:** tests/test_output.py, src/usher_pipeline/output/writers.py
- **Verification:** Tests run without deprecation warnings
- **Committed in:** 4e46b48 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Necessary fix for current polars version compatibility. No scope creep.

## Issues Encountered

None - plan executed smoothly with only the deprecated API fix needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Output module core complete with tiering, evidence summary, and dual-format writing
- Ready for visualization module (05-02) and reproducibility reporting (05-03)
- Ready for CLI command integration to generate candidate outputs
- All tests pass, no blockers

---
*Phase: 05-output-cli*
*Completed: 2026-02-11*


## Self-Check: PASSED

All files and commits verified:

**Files created:**
- ✓ src/usher_pipeline/output/tiers.py
- ✓ src/usher_pipeline/output/evidence_summary.py  
- ✓ src/usher_pipeline/output/writers.py
- ✓ src/usher_pipeline/output/__init__.py
- ✓ tests/test_output.py

**Commits:**
- ✓ d2ef3a2 (Task 1: Tiering logic and evidence summary module)
- ✓ 4e46b48 (Task 2: Dual-format writer with provenance and tests)


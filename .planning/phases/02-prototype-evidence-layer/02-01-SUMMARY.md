---
phase: 02-prototype-evidence-layer
plan: 01
subsystem: evidence-layer
tags: [gnomad, constraint-metrics, polars, httpx, structlog, data-pipeline]

# Dependency graph
requires:
  - phase: 01-data-infrastructure
    provides: "Config system, DuckDB persistence, gene universe framework"
provides:
  - "gnomAD v4.1 constraint metrics download with streaming and retry"
  - "Coverage quality filtering with quality_flag categorization (measured/incomplete_coverage/no_data)"
  - "LOEUF score normalization with inversion (lower LOEUF = higher score)"
  - "NULL preservation pattern (unknown != zero constraint)"
  - "Evidence layer fetch->filter->normalize pattern for future evidence sources"
affects: [03-multi-evidence-scoring, phase-03-plans, evidence-integration]

# Tech tracking
tech-stack:
  added: [httpx>=0.28, structlog>=25.0]
  patterns:
    - "Evidence layer pattern: fetch (streaming download with retry) -> filter (coverage QC) -> normalize (0-1 scoring)"
    - "NULL preservation: missing data stays NULL, not 0.0 (unknown != zero)"
    - "Quality flags instead of dropping data: measured/incomplete_coverage/no_data"
    - "Lazy evaluation with polars LazyFrame until final collect()"
    - "Column name variant mapping for gnomAD version compatibility (v2.1.1, v4.x)"

key-files:
  created:
    - src/usher_pipeline/evidence/__init__.py
    - src/usher_pipeline/evidence/gnomad/__init__.py
    - src/usher_pipeline/evidence/gnomad/models.py
    - src/usher_pipeline/evidence/gnomad/fetch.py
    - src/usher_pipeline/evidence/gnomad/transform.py
    - tests/test_gnomad.py
  modified:
    - pyproject.toml

key-decisions:
  - "httpx for streaming downloads (not requests) - better async support, native streaming"
  - "structlog for structured logging (JSON-formatted, context-aware)"
  - "LOEUF normalization with inversion: lower LOEUF (more constrained) = higher score (0-1 range)"
  - "Quality flags instead of dropping genes: preserves all genes with categorization (measured/incomplete/no_data)"
  - "NULL preservation throughout pipeline: 'unknown' is semantically different from 'zero constraint'"
  - "Lazy polars evaluation: scan_csv returns LazyFrame, defer materialization until final collect()"
  - "Column mapping with variant support: handle gnomAD v2.1.1 vs v4.x naming differences"

patterns-established:
  - "Evidence layer fetch pattern: streaming download with tenacity retry (5 attempts, exponential backoff 4-60s)"
  - "Evidence layer transform pattern: coverage filter -> score normalization -> collect"
  - "Quality categorization: measured (good coverage + data) vs incomplete_coverage vs no_data"
  - "Test pattern: synthetic TSV fixtures, no external API calls, comprehensive edge case coverage"

# Metrics
duration: 4min
completed: 2026-02-11
---

# Phase 02 Plan 01: gnomAD Constraint Data Pipeline Summary

**Streaming gnomAD v4.1 constraint download with coverage filtering, LOEUF normalization (inverted 0-1 scale), and NULL preservation - establishing the fetch->filter->normalize evidence layer pattern**

## Performance

- **Duration:** 4 min 15 sec
- **Started:** 2026-02-11T10:10:32Z
- **Completed:** 2026-02-11T10:14:47Z
- **Tasks:** 2
- **Files modified:** 7 (5 created, 2 modified)
- **Tests added:** 15 (all passing)

## Accomplishments
- gnomAD v4.1 constraint metrics downloadable with httpx streaming and retry (handles 50-100MB files without memory loading)
- Coverage quality filtering categorizes genes by data quality without dropping any genes (measured/incomplete_coverage/no_data)
- LOEUF normalization inverts scale (lower LOEUF = more constrained = higher 0-1 score) and preserves NULLs for unmeasured genes
- Evidence layer pattern established: fetch (streaming + retry) -> filter (QC with flags) -> normalize (scoring) - template for future evidence sources
- 15 comprehensive unit tests cover NULL handling, normalization bounds/inversion, coverage filtering, column mapping variants

## Task Commits

Each task was committed atomically:

1. **Task 1: Create gnomAD data model and download module** - `a88b0ee` (feat)
   - Evidence layer package structure
   - ConstraintRecord Pydantic model with NULL-aware fields
   - Streaming download with httpx and tenacity retry
   - Lazy TSV parser with column name variant handling for gnomAD v2.1.1/v4.x compatibility
   - Added httpx and structlog dependencies

2. **Task 2: Create coverage filter, normalization, and unit tests** - `174c4af` (feat)
   - filter_by_coverage: adds quality_flag column (measured/incomplete_coverage/no_data) without dropping genes
   - normalize_scores: LOEUF inversion (lower = more constrained = higher score), NULL preservation
   - process_gnomad_constraint: end-to-end pipeline convenience function
   - 15 unit tests: NULL handling, coverage filtering, normalization bounds/inversion, mixed type handling, download checkpoint behavior
   - Fixed column mapping to handle gnomAD v4.x loeuf/loeuf_upper duplication issue

## Files Created/Modified

**Created:**
- `src/usher_pipeline/evidence/__init__.py` - Evidence layer package root
- `src/usher_pipeline/evidence/gnomad/__init__.py` - gnomAD module exports
- `src/usher_pipeline/evidence/gnomad/models.py` - ConstraintRecord Pydantic model, column variant mappings, URL constant
- `src/usher_pipeline/evidence/gnomad/fetch.py` - download_constraint_metrics (streaming httpx with retry), parse_constraint_tsv (lazy polars with column mapping)
- `src/usher_pipeline/evidence/gnomad/transform.py` - filter_by_coverage, normalize_scores, process_gnomad_constraint pipeline
- `tests/test_gnomad.py` - 15 comprehensive unit tests with synthetic TSV fixtures

**Modified:**
- `pyproject.toml` - Added httpx>=0.28 and structlog>=25.0 dependencies

## Decisions Made

1. **httpx over requests** - Better streaming support, async-native, cleaner API for large file downloads
2. **structlog for logging** - JSON-formatted structured logs with context awareness (better than stdlib logging for data pipelines)
3. **LOEUF inversion in normalization** - Lower LOEUF (more loss-of-function constrained) maps to higher score (0-1 range) for consistent "higher = better" semantics across evidence types
4. **Quality flags instead of filtering** - Preserve all genes with categorization (measured/incomplete_coverage/no_data) rather than dropping low-coverage genes - "unknown" is valuable information
5. **NULL preservation pattern** - Missing constraint data stays NULL, not 0.0 - "unknown constraint" is semantically different from "zero constraint" and must not be conflated
6. **Lazy polars evaluation** - Use LazyFrame until final collect() to enable query optimization and reduce memory footprint
7. **Column name variant mapping** - Handle gnomAD v2.1.1 (oe_lof_upper) vs v4.x (lof.oe_ci.upper) naming differences in same codebase

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed column mapping for loeuf/loeuf_upper duplication**
- **Found during:** Task 2 (running initial tests)
- **Issue:** Both `loeuf` and `loeuf_upper` mapped to same gnomAD source column `lof.oe_ci.upper`, causing only one to be present in LazyFrame. Tests failed with "column 'loeuf' not found".
- **Fix:** Added duplicate detection in column mapping logic - track used source columns to avoid double-mapping. Added special case: if loeuf is mapped but loeuf_upper is not, duplicate loeuf to loeuf_upper (vice versa). In gnomAD, the "upper CI" value IS the LOEUF score we use.
- **Files modified:** src/usher_pipeline/evidence/gnomad/fetch.py, src/usher_pipeline/evidence/gnomad/models.py
- **Verification:** All 15 tests pass, both loeuf and loeuf_upper columns present in parsed LazyFrame
- **Committed in:** 174c4af (Task 2 commit)

**2. [Rule 1 - Bug] Fixed type comparison error in filter_by_coverage for NULL values**
- **Found during:** Task 2 (test_filter_by_coverage_handles_missing_columns failing)
- **Issue:** When mean_depth or cds_covered_pct are NULL (represented as "." in TSV), polars reads them as strings if column has mixed types. Comparison operators (>=, <) fail with "cannot compare string with numeric type (f64)".
- **Fix:** Added explicit type casting to Float64 at start of filter_by_coverage function (strict=False to handle NULL/"." conversion). Reordered quality_flag conditions to check is_not_null() before comparison operators.
- **Files modified:** src/usher_pipeline/evidence/gnomad/transform.py
- **Verification:** test_filter_by_coverage_handles_missing_columns passes, NULL values handled correctly
- **Committed in:** 174c4af (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correct functioning with real-world gnomAD data edge cases (version compatibility, NULL handling). No scope changes - fixes enable plan implementation.

## Issues Encountered

None - plan executed smoothly with two necessary edge case fixes (documented above as auto-fixed deviations).

## User Setup Required

None - no external service configuration required. gnomAD constraint file is publicly accessible via HTTPS.

## Next Phase Readiness

**Ready for Phase 3:**
- Evidence layer pattern established and tested (fetch->filter->normalize)
- gnomAD constraint data pipeline ready for DuckDB storage integration
- NULL preservation pattern documented for other evidence sources
- Quality flag pattern applicable to other evidence types (coverage, data quality issues)

**Template for future evidence sources:**
- This plan establishes the pattern for all future evidence layers (ClinGen, OMIM, GTEx, etc.)
- Fetch: streaming download with retry
- Filter: quality control with flags, preserve all data
- Normalize: 0-1 scoring with consistent "higher = better" semantics
- NULL preservation: unknown != zero

**Blockers:** None

**Considerations for next plans:**
- DuckDB integration: store processed gnomAD DataFrame in database
- Provenance tracking: record download timestamp, gnomAD version, filter thresholds
- Gene ID joining: ensure gnomAD gene IDs (ENSG...) match gene universe Ensembl IDs

---
*Phase: 02-prototype-evidence-layer*
*Completed: 2026-02-11*

## Self-Check: PASSED

All claimed files verified:
- src/usher_pipeline/evidence/__init__.py ✓
- src/usher_pipeline/evidence/gnomad/__init__.py ✓
- src/usher_pipeline/evidence/gnomad/models.py ✓
- src/usher_pipeline/evidence/gnomad/fetch.py ✓
- src/usher_pipeline/evidence/gnomad/transform.py ✓
- tests/test_gnomad.py ✓

All claimed commits verified:
- a88b0ee (Task 1) ✓
- 174c4af (Task 2) ✓

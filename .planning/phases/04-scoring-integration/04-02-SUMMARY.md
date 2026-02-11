---
phase: 04-scoring-integration
plan: 02
subsystem: scoring
tags: [qc, validation, quality-control, outlier-detection, positive-controls, mad, percentile-rank]

# Dependency graph
requires:
  - phase: 04-scoring-integration
    plan: 01
    provides: scored_genes table, known_genes compilation
  - phase: 01-data-infrastructure
    provides: PipelineStore, DuckDB persistence
provides:
  - Quality control checks for missing data, distributions, outliers
  - MAD-based robust outlier detection per evidence layer
  - Positive control validation against known gene rankings
  - PERCENT_RANK window function validation
  - QC orchestrator with composite score statistics
affects: [04-03, candidate-ranking, filtering, quality-assessment]

# Tech tracking
tech-stack:
  added:
    - scipy>=1.14 for MAD-based outlier detection
  patterns:
    - MAD-based robust outlier detection (>3 MAD threshold)
    - PERCENT_RANK window function for percentile ranking
    - Threshold-based classification (warn/error levels)
    - Temporary table pattern for DuckDB joins

key-files:
  created:
    - src/usher_pipeline/scoring/quality_control.py
    - src/usher_pipeline/scoring/validation.py
  modified:
    - pyproject.toml
    - src/usher_pipeline/scoring/__init__.py

key-decisions:
  - "scipy.stats.median_abs_deviation for MAD computation (robust to outliers)"
  - "Missing data thresholds: 50% warn, 80% error"
  - "Outlier threshold: >3 MAD from median per layer"
  - "PERCENT_RANK computed across ALL genes before exclusion (validates scoring system)"
  - "Top quartile validation: median percentile >= 0.75 for known genes"
  - "Temporary table pattern for known gene join (avoids external temp files)"

patterns-established:
  - "QC orchestrator pattern: run_qc_checks combines all checks with pass/fail boolean"
  - "Composite score percentiles (p10, p25, p50, p75, p90) for distribution analysis"
  - "Human-readable validation reports with formatted tables"
  - "NULL-aware statistics: only compute on non-NULL values per layer"

# Metrics
duration: 2m 54s
completed: 2026-02-11
---

# Phase 04 Plan 02: Quality Control and Positive Control Validation Summary

**MAD-based outlier detection and PERCENT_RANK validation ensuring scoring system credibility before candidate ranking**

## Performance

- **Duration:** 2 minutes 54 seconds (174 seconds)
- **Started:** 2026-02-11T12:45:12Z
- **Completed:** 2026-02-11T12:48:06Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added scipy>=1.14 dependency for robust statistical methods
- Implemented compute_missing_data_rates() with warn (>50%) and error (>80%) thresholds
- Created compute_distribution_stats() detecting no variation (std < 0.01) and out-of-range values
- Built detect_outliers() using MAD-based detection (>3 MAD from median per layer)
- Developed run_qc_checks() orchestrator with composite score percentiles (p10-p90)
- Implemented validate_known_gene_ranking() using PERCENT_RANK window function
- Created generate_validation_report() with human-readable formatted output
- Exported run_qc_checks, validate_known_gene_ranking, generate_validation_report from scoring module

## Task Commits

Each task was committed atomically:

1. **Task 1: Quality control checks for scoring results** - `ba2f97a` (feat)
2. **Task 2: Positive control validation against known gene rankings** - `70a5d6e` (feat)

## Files Created/Modified
- `src/usher_pipeline/scoring/quality_control.py` - QC checks with MAD-based outlier detection
- `src/usher_pipeline/scoring/validation.py` - Known gene ranking validation with PERCENT_RANK
- `pyproject.toml` - Added scipy>=1.14 dependency
- `src/usher_pipeline/scoring/__init__.py` - Export QC and validation functions

## Decisions Made

1. **scipy for MAD computation:** Used scipy.stats.median_abs_deviation with scale="normal" for robust outlier detection. MAD is less sensitive to outliers than standard deviation, making it ideal for detecting anomalous genes in scored datasets.

2. **Missing data threshold classification:** 50% missing = warning (may still be usable), 80% missing = error (too sparse to trust). This dual-threshold approach allows for graduated QC feedback.

3. **Outlier threshold calibration:** >3 MAD from median flags outliers. This is a standard robust statistics threshold balancing sensitivity and specificity. Layers with MAD=0 (no variation) skip outlier detection.

4. **PERCENT_RANK validation timing:** Validation computes percentile ranks BEFORE known gene exclusion to validate the scoring system itself (not post-filtering artifacts). Uses temporary table pattern for efficient DuckDB join.

5. **Top quartile validation criterion:** Median percentile >= 0.75 ensures known cilia/Usher genes rank in top 25% of all genes. This threshold confirms scoring logic prioritizes cilia-relevant features.

6. **Composite score percentiles:** Included p10, p25, p50, p75, p90 in run_qc_checks() for distribution analysis. These percentiles help identify skewness, outliers, and score concentration patterns.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Both verification tests passed on first attempt.

## User Setup Required

None - scipy installed automatically in virtual environment.

## Next Phase Readiness

Ready for Phase 04 Plan 03 (ranked candidate list generation and filtering):
- QC checks available via run_qc_checks() for post-scoring validation
- Positive control validation confirms scoring system works correctly
- Outlier detection identifies anomalous genes per layer
- Composite score percentiles provide distribution context for threshold selection

No blockers. Next plan can implement:
- Known gene exclusion filtering
- Quality flag filtering (sufficient_evidence threshold)
- Composite score ranking
- Top-N candidate selection with provenance

## Self-Check: PASSED

All claimed files and commits verified:
- src/usher_pipeline/scoring/quality_control.py - FOUND
- src/usher_pipeline/scoring/validation.py - FOUND
- pyproject.toml - FOUND
- Commit ba2f97a (Task 1) - FOUND
- Commit 70a5d6e (Task 2) - FOUND

---
*Phase: 04-scoring-integration*
*Plan: 02*
*Completed: 2026-02-11*

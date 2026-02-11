---
phase: 05-output-cli
plan: 03
subsystem: cli
tags: [click, cli, report, integration-testing, clir unner]

# Dependency graph
requires:
  - phase: 05-01
    provides: assign_tiers, add_evidence_summary, write_candidate_output
  - phase: 05-02
    provides: generate_all_plots, generate_reproducibility_report
  - phase: 04-03
    provides: scored_genes table in DuckDB
provides:
  - CLI report command orchestrating full output pipeline
  - CliRunner integration tests for report command
affects: [unified-cli, end-to-end-workflow, user-experience]

# Tech tracking
tech-stack:
  added: []
  patterns: [cli-checkpoint-restart, dual-format-output, graceful-degradation, integration-testing-with-synthetic-fixtures]

key-files:
  created:
    - src/usher_pipeline/cli/report_cmd.py
    - tests/test_report_cmd.py
  modified:
    - src/usher_pipeline/cli/main.py

key-decisions:
  - "Report command follows established score_cmd.py pattern (config load, store init, checkpoint check, pipeline steps, summary, cleanup)"
  - "Support --output-dir, --force, --skip-viz, --skip-report, and configurable tier threshold flags"
  - "Tier thresholds passed as uppercase keys (HIGH/MEDIUM/LOW) with composite_score and evidence_count fields"
  - "Default output directory: {data_dir}/report if --output-dir not specified"
  - "Checkpoint pattern: warn and skip if candidates.tsv exists without --force"
  - "Integration tests use synthetic DuckDB fixtures with isolated tmp_path instances (no external dependencies)"

patterns-established:
  - "CliRunner integration tests with test_config and populated_db fixtures"
  - "Synthetic test data designed to validate tier distribution (3 HIGH, 5 MEDIUM, 5 LOW, 4 EXCLUDED, 3 NULL)"
  - "Each test uses isolated tmp_path to avoid cross-test contamination"
  - "Graceful degradation: visualization and reproducibility report failures logged as warnings, not errors"

# Metrics
duration: 3min
completed: 2026-02-11
---

# Phase 05 Plan 03: CLI Report Command Summary

**One-liner:** Unified CLI `report` command orchestrates tiering, evidence summary, dual-format output, visualizations, and reproducibility reports in one invocation with configurable thresholds and skip flags.

## Performance

- **Duration:** 3 minutes
- **Started:** 2026-02-11T20:04:06Z
- **Completed:** 2026-02-11T20:07:42Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Implemented CLI report command following established CLI pattern from score_cmd.py and evidence_cmd.py
- Orchestrates full output pipeline: load scored_genes, apply tiering, add evidence summary, write TSV+Parquet, generate plots, create reproducibility reports
- Supports configurable tier thresholds (--high-threshold, --medium-threshold, --low-threshold, --min-evidence-high, --min-evidence-medium)
- Provides skip flags (--skip-viz, --skip-report) for flexible iteration
- Created 9 comprehensive CliRunner integration tests with synthetic fixtures
- Unified CLI now has 5 commands: setup, evidence, score, report, info

## Task Commits

Each task was committed atomically:

1. **Task 1: Report CLI command** - `2ab25ef` (feat)
   - report_cmd.py with full pipeline orchestration
   - Registered in main.py CLI entry point
   - Follows established pattern: config load, store init, checkpoint, steps, summary, cleanup

2. **Task 2: CliRunner integration tests** - `c10d595` (test)
   - test_report_cmd.py with 9 comprehensive tests
   - Fixtures: test_config (minimal YAML), populated_db (synthetic scored_genes)
   - Fixed tier threshold format bug (uppercase keys, composite_score field)
   - Fixed write_candidate_output parameter name bug (filename_base not base_filename)

## Files Created/Modified

- `src/usher_pipeline/cli/report_cmd.py` - CLI report command orchestrating output pipeline
- `src/usher_pipeline/cli/main.py` - Added report command registration
- `tests/test_report_cmd.py` - 9 CliRunner integration tests

## Decisions Made

- **Report command pattern:** Follow score_cmd.py established pattern for consistency (config load, store init, checkpoint check, pipeline steps with click.style output, summary display, cleanup in finally block)
- **Tier threshold format:** Pass uppercase keys (HIGH/MEDIUM/LOW) with composite_score and evidence_count fields to match assign_tiers() signature
- **Default output directory:** Use {data_dir}/report if --output-dir not specified (consistent with other evidence commands)
- **Checkpoint pattern:** Warn and skip if candidates.tsv exists without --force flag (prevents accidental overwrites)
- **Graceful degradation:** Wrap visualization and reproducibility report generation in try/except to log warnings rather than fail entire command
- **Integration test strategy:** Use synthetic DuckDB fixtures with isolated tmp_path instances to avoid external API dependencies and ensure fast, reproducible tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed tier threshold dictionary format**
- **Found during:** Task 2 (test execution)
- **Issue:** assign_tiers() expects uppercase keys "HIGH"/"MEDIUM"/"LOW" and "composite_score" field, but report_cmd.py passed lowercase keys "high"/"medium"/"low" and "score" field
- **Fix:** Changed tier_thresholds dict to use uppercase keys and composite_score field, added evidence_count: 1 for LOW tier
- **Files modified:** src/usher_pipeline/cli/report_cmd.py
- **Verification:** All tests pass after fix
- **Committed in:** c10d595 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed write_candidate_output parameter name**
- **Found during:** Task 2 (test execution)
- **Issue:** write_candidate_output() function parameter is filename_base, not base_filename
- **Fix:** Changed base_filename="candidates" to filename_base="candidates"
- **Files modified:** src/usher_pipeline/cli/report_cmd.py
- **Verification:** All tests pass after fix
- **Committed in:** c10d595 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bug fixes)
**Impact on plan:** Both were trivial parameter/key name mismatches discovered during testing. Fixed inline before test commit. No scope creep.

## Issues Encountered

None - plan executed smoothly with two minor bugs caught and fixed during test-driven development.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 05 (Output & CLI) is now complete
- All output modules implemented: tiering, evidence summary, dual-format writers, visualizations, reproducibility reports
- Unified CLI provides complete end-to-end workflow: setup -> evidence -> score -> report
- Ready for Phase 06 (Final Integration & Validation) if planned
- All tests pass (9/9 CliRunner integration tests), no blockers

---
*Phase: 05-output-cli*
*Completed: 2026-02-11*


## Self-Check: PASSED

All files and commits verified:

**Files created:**
- ✓ src/usher_pipeline/cli/report_cmd.py
- ✓ tests/test_report_cmd.py

**Files modified:**
- ✓ src/usher_pipeline/cli/main.py

**Commits:**
- ✓ 2ab25ef (Task 1: Report CLI command)
- ✓ c10d595 (Task 2: CliRunner integration tests)

**Tests:**
- ✓ 9/9 tests pass (100% pass rate)

All verification checks passed successfully.

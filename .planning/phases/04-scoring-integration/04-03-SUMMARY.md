---
phase: 04-scoring-integration
plan: 03
subsystem: CLI and Testing
tags:
  - cli
  - scoring
  - testing
  - validation
  - checkpoint-restart
dependency_graph:
  requires:
    - 04-01 (scoring integration module)
    - 04-02 (QC and validation modules)
  provides:
    - CLI score command with full pipeline orchestration
    - Comprehensive unit and integration test coverage
  affects:
    - main CLI entry point (command registration)
    - test suite coverage metrics
tech_stack:
  added:
    - click command with --force, --skip-qc, --skip-validation options
    - pytest fixtures for synthetic DuckDB stores
  patterns:
    - Checkpoint-restart pattern (skip if scored_genes exists)
    - Synthetic data testing (no external dependencies)
    - NULL preservation validation in tests
key_files:
  created:
    - src/usher_pipeline/cli/score_cmd.py (343 lines)
    - tests/test_scoring.py (269 lines)
    - tests/test_scoring_integration.py (305 lines)
  modified:
    - src/usher_pipeline/cli/main.py (added score command registration)
decisions:
  - Score command follows evidence_cmd.py pattern for consistency
  - Separate --skip-qc and --skip-validation flags for flexible iteration
  - Tests use tmp_path fixtures for isolated DuckDB instances
  - Synthetic test data designed to ensure known genes rank highly (0.8-0.95 scores across all layers)
metrics:
  duration_minutes: 3
  tasks_completed: 2
  files_created: 3
  files_modified: 1
  test_coverage: 10 tests (7 unit + 3 integration)
  completed_date: 2026-02-11
---

# Phase 04 Plan 03: CLI Score Command and Tests Summary

**One-liner:** CLI command orchestrating full scoring pipeline (known genes → composite scores → QC → validation) with comprehensive test coverage for NULL preservation and validation logic

## Tasks Completed

### Task 1: CLI Score Command with Checkpoint-Restart

**Commit:** d57a5f2

Created `src/usher_pipeline/cli/score_cmd.py` following the established pattern from `evidence_cmd.py`:

**Implementation:**
- Single `score` command (not a group) with options: `--force`, `--skip-qc`, `--skip-validation`
- Uses `@click.pass_context` to access config_path from CLI context
- 5-step pipeline flow:
  1. Load known genes (OMIM Usher + SYSCILIA SCGS) to DuckDB
  2. Compute composite scores with NULL-preserving weighted average
  3. Persist scored_genes table with per-layer contributions
  4. Run QC checks (unless --skip-qc) with warnings/errors display
  5. Validate known gene rankings (unless --skip-validation) with report generation

**Checkpoint-restart:**
- Checks `store.has_checkpoint('scored_genes')` before processing
- If exists and not --force, displays summary and returns early
- Allows fast iteration during development

**CLI integration:**
- Updated `src/usher_pipeline/cli/main.py` to import and register score command
- Command appears in `usher-pipeline --help` alongside setup and evidence

**Output:**
- Displays comprehensive summary: total genes, mean score, quality flag distribution
- Shows QC pass/fail status and validation pass/fail status
- Saves provenance sidecar to `data_dir/scoring/scoring.provenance.json`

**Verification:**
```bash
# CLI help works
usher-pipeline score --help  # Shows --force, --skip-qc, --skip-validation options

# Command registered
usher-pipeline --help  # Lists score command
```

### Task 2: Unit and Integration Tests for Scoring Module

**Commit:** a6ad6c6

Created comprehensive test coverage for scoring module with 10 tests using synthetic data.

#### test_scoring.py (7 unit tests):

1. **test_compile_known_genes_returns_expected_structure**
   - Verifies DataFrame structure (gene_symbol, source, confidence columns)
   - Asserts >= 38 genes (10 OMIM Usher + 28 SYSCILIA SCGS v2)
   - Confirms MYO7A and IFT88 present
   - Validates all confidence = HIGH
   - Checks both sources present (omim_usher, syscilia_scgs_v2)

2. **test_compile_known_genes_no_duplicates_within_source**
   - Verifies no duplicate gene_symbol within same source
   - Allows genes to appear in both sources (separate rows)

3. **test_scoring_weights_validate_sum_defaults**
   - ScoringWeights() with defaults passes validate_sum()

4. **test_scoring_weights_validate_sum_custom_valid**
   - Custom weights summing to 1.0 pass validation

5. **test_scoring_weights_validate_sum_invalid**
   - Weights summing to 1.35 raise ValueError

6. **test_scoring_weights_validate_sum_close_to_one**
   - Weights within 1e-6 of 1.0 pass (0.999999)
   - Weights outside tolerance fail (0.99)

7. **test_null_preservation_in_composite**
   - Creates in-memory DuckDB with 3 genes
   - GENE1: 2 evidence layers (gnomad + annotation) → non-NULL score, moderate_evidence
   - GENE2: 1 evidence layer (gnomad only) → non-NULL score, sparse_evidence
   - GENE3: 0 evidence layers → **NULL score, no_evidence**
   - Verifies NULL preservation (not zero) for genes without evidence

#### test_scoring_integration.py (3 integration tests):

1. **test_scoring_pipeline_end_to_end**
   - Creates synthetic store with 20 genes (17 generic + 3 known: MYO7A, IFT88, CDH23)
   - 6 evidence tables with varying NULL rates:
     - gnomad: 15/20 (75%)
     - expression: 12/20 (60%)
     - annotation: 18/20 (90%)
     - localization: 10/20 (50%)
     - animal_models: 8/20 (40%)
     - literature: 14/20 (70%)
   - Known genes receive high scores (0.8-0.95) across all 6 layers
   - Verifies:
     - All 20 genes present in results
     - Genes with evidence have non-NULL composite_score
     - Genes without evidence have NULL composite_score
     - evidence_count values correct (0-6)
     - quality_flag matches evidence_count thresholds
     - Known genes rank in top 5 (at least 2 of 3)

2. **test_qc_detects_missing_data**
   - Creates synthetic store with 100 genes
   - gnomad: 5% coverage (95% NULL) → should trigger ERROR (>80% threshold)
   - expression: 40% coverage (60% NULL) → should trigger WARNING (>50% threshold)
   - Other layers: >50% coverage (no warnings)
   - Verifies QC detects and reports errors for high missing data rates

3. **test_validation_passes_with_known_genes_ranked_highly**
   - Uses synthetic_store with known genes scoring highly
   - Loads known genes, computes scores, persists, runs validation
   - Verifies:
     - validation_passed = True
     - median_percentile >= 0.75 (top quartile threshold)
     - Known genes rank highly as expected

**Test Execution:**
```bash
pytest tests/test_scoring.py tests/test_scoring_integration.py -v
# 10 passed, 7 warnings in 0.68s
```

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

### Files Created:
```bash
[ -f "/Users/gbanyan/Project/usher-exploring/src/usher_pipeline/cli/score_cmd.py" ] && echo "FOUND: score_cmd.py" || echo "MISSING: score_cmd.py"
# FOUND: score_cmd.py

[ -f "/Users/gbanyan/Project/usher-exploring/tests/test_scoring.py" ] && echo "FOUND: test_scoring.py" || echo "MISSING: test_scoring.py"
# FOUND: test_scoring.py

[ -f "/Users/gbanyan/Project/usher-exploring/tests/test_scoring_integration.py" ] && echo "FOUND: test_scoring_integration.py" || echo "MISSING: test_scoring_integration.py"
# FOUND: test_scoring_integration.py
```

### Commits Exist:
```bash
git log --oneline --all | grep -q "d57a5f2" && echo "FOUND: d57a5f2" || echo "MISSING: d57a5f2"
# FOUND: d57a5f2

git log --oneline --all | grep -q "a6ad6c6" && echo "FOUND: a6ad6c6" || echo "MISSING: a6ad6c6"
# FOUND: a6ad6c6
```

### CLI Command Works:
```bash
usher-pipeline score --help
# Shows --force, --skip-qc, --skip-validation options

usher-pipeline --help | grep score
# score     Compute multi-evidence composite scores for all genes.
```

### Tests Pass:
```bash
pytest tests/test_scoring.py tests/test_scoring_integration.py -v
# 10 passed, 7 warnings in 0.68s
```

## Verification

All success criteria met:

- ✅ `usher-pipeline score --help` shows available options
- ✅ Score command registered in main CLI
- ✅ Unit tests pass: known genes, weight validation, NULL handling
- ✅ Integration tests pass: end-to-end scoring with synthetic data, QC detection, validation
- ✅ All tests runnable with `pytest tests/test_scoring*.py`

## Notes

- Tests use synthetic data exclusively (no external API calls, fast, reproducible)
- NULL preservation pattern validated: genes with no evidence get NULL composite_score, not zero
- Known genes designed to rank highly in synthetic data (0.8-0.95 scores across all layers)
- QC thresholds: 50% missing = warning, 80% missing = error
- Validation threshold: median percentile >= 0.75 (top quartile)

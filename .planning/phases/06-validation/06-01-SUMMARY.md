---
phase: 06-validation
plan: 01
subsystem: validation
tags: [negative-controls, recall-metrics, housekeeping-genes, positive-controls]
dependency_graph:
  requires: [04-02-scoring-qc, 04-01-known-genes]
  provides: [negative-control-validation, recall-at-k-metrics, extended-positive-validation]
  affects: [06-03-comprehensive-validation-report]
tech_stack:
  added: []
  patterns: [inverted-threshold-validation, recall-at-k, per-source-breakdown]
key_files:
  created:
    - src/usher_pipeline/scoring/negative_controls.py
  modified:
    - src/usher_pipeline/scoring/validation.py
    - src/usher_pipeline/scoring/__init__.py
decisions:
  - "Housekeeping genes as negative controls: 13 literature-validated genes (Eisenberg & Levanon 2013)"
  - "Inverted threshold logic for negative controls: median percentile < 50% is success"
  - "Recall@k at both absolute (100, 500, 1000, 2000) and percentage (5%, 10%, 20%) thresholds"
  - "Per-source breakdown separates OMIM Usher from SYSCILIA SCGS v2 for granular analysis"
metrics:
  duration_minutes: 2
  completed_date: 2026-02-12
  tasks_completed: 2
  files_created: 1
  files_modified: 2
  commits: 2
---

# Phase 6 Plan 01: Negative Controls & Recall@k Validation Summary

Negative control validation with housekeeping genes and enhanced positive control validation with recall@k metrics, providing complementary validation approaches (negative + positive controls) with granular metrics.

## Tasks Completed

### Task 1: Create negative control validation module with housekeeping genes
**Status:** Complete
**Commit:** e488ff2
**Files:** src/usher_pipeline/scoring/negative_controls.py

Created negative_controls.py implementing housekeeping gene-based negative control validation:

- **HOUSEKEEPING_GENES_CORE** frozenset with 13 curated genes (RPL13A, RPL32, RPLP0, GAPDH, ACTB, B2M, HPRT1, TBP, SDHA, PGK1, PPIA, UBC, YWHAZ)
- Grouped by function: ribosomal proteins, metabolic enzymes, transcription factors, protein folding
- Source: Eisenberg & Levanon (2013) "Human housekeeping genes, revisited" Trends in Genetics

**compile_housekeeping_genes()**: Returns DataFrame with gene_symbol, source ("literature_validated"), confidence ("HIGH") - matches compile_known_genes() pattern from known_genes.py

**validate_negative_controls()**:
- Uses PERCENT_RANK window function (same pattern as positive control validation)
- INVERTED threshold logic: median_percentile < 0.50 = success (negative controls should rank LOW)
- Returns metrics: total_expected, total_in_dataset, median_percentile, top_quartile_count, in_high_tier_count, validation_passed, housekeeping_gene_details
- Creates temporary _housekeeping_genes table for join, cleans up after query
- Tracks both top quartile presence (should be minimal) and high-tier score count (>= 0.70)

**generate_negative_control_report()**: Human-readable output following validation.py patterns, shows lowest-ranked genes (best outcome for negative controls)

### Task 2: Enhance positive control validation with recall@k metrics
**Status:** Complete
**Commit:** 0f615c0
**Files:** src/usher_pipeline/scoring/validation.py, src/usher_pipeline/scoring/__init__.py

Enhanced validation.py with recall@k functions:

**compute_recall_at_k()**:
- Computes recall at absolute thresholds: top-100, top-500, top-1000, top-2000
- Computes recall at percentage thresholds: top 5%, 10%, 20% of scored genes
- Deduplicates known genes on gene_symbol (genes in both OMIM + SYSCILIA count once)
- Recall@k = (known genes in top-k) / total_known_unique
- Provides the ">70% recall in top 10%" metric required by success criteria
- Returns: recalls_absolute, recalls_percentage, total_known_unique, total_scored

**validate_positive_controls_extended()**:
- Combines base percentile validation (validate_known_gene_ranking) with recall@k metrics
- Adds per-source breakdown: separate median percentile for "omim_usher" vs "syscilia_scgs_v2"
- Per-source uses same PERCENT_RANK CTE pattern but filters JOIN by source
- Allows detecting if one gene set validates better than the other (e.g., disease genes vs ciliary genes)
- Returns: all base metrics + recall_at_k dict + per_source_breakdown dict

**Updated __init__.py**: Added exports for compute_recall_at_k, validate_positive_controls_extended, and all negative_controls.py functions (HOUSEKEEPING_GENES_CORE, compile_housekeeping_genes, validate_negative_controls, generate_negative_control_report)

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All verification checks passed:

1. `from usher_pipeline.scoring.negative_controls import HOUSEKEEPING_GENES_CORE; assert len(HOUSEKEEPING_GENES_CORE) == 13` - OK
2. `from usher_pipeline.scoring import validate_negative_controls, compute_recall_at_k, validate_positive_controls_extended` - All imports OK
3. `compile_housekeeping_genes(); assert 'gene_symbol' in df.columns and 'source' in df.columns` - DataFrame structure correct

## Success Criteria

- [x] negative_controls.py creates housekeeping gene set and validates they rank low (inverted threshold)
- [x] validation.py compute_recall_at_k measures recall at multiple k values including percentage-based thresholds
- [x] validate_positive_controls_extended combines percentile + recall + per-source metrics
- [x] All new functions exported from scoring.__init__

## Key Files

### Created
- **src/usher_pipeline/scoring/negative_controls.py** (287 lines)
  - Housekeeping gene compilation and negative control validation
  - Exports: HOUSEKEEPING_GENES_CORE, compile_housekeeping_genes, validate_negative_controls, generate_negative_control_report

### Modified
- **src/usher_pipeline/scoring/validation.py** (+183 lines)
  - Added compute_recall_at_k() for recall@k metrics
  - Added validate_positive_controls_extended() for comprehensive validation

- **src/usher_pipeline/scoring/__init__.py** (+8 exports)
  - Added negative_controls module exports
  - Added new validation functions: compute_recall_at_k, validate_positive_controls_extended

## Integration Points

**Depends on:**
- Phase 04-01: Known genes compilation (OMIM Usher + SYSCILIA SCGS v2)
- Phase 04-02: scored_genes table with composite_score and PERCENT_RANK validation pattern

**Provides:**
- Negative control validation (housekeeping genes should rank low)
- Recall@k metrics (what % of known genes in top-k candidates)
- Per-source breakdown (separate OMIM vs SYSCILIA analysis)

**Affects:**
- Phase 06-03: Comprehensive validation report will integrate both positive and negative control results

## Technical Notes

**Negative Control Design:**
- Housekeeping genes (ubiquitous, essential, not cilia-specific) serve as negative controls
- Inverted threshold logic: LOW percentiles are GOOD (confirms scoring specificity)
- Complements positive controls: known genes should rank HIGH, housekeeping genes should rank LOW
- If both validations pass: scoring system is both sensitive (catches true positives) and specific (excludes non-ciliary genes)

**Recall@k Metrics:**
- Provides specific measurement for ">70% in top 10%" success criterion
- Absolute thresholds useful for fixed candidate list sizes (e.g., "top 100 for experimental follow-up")
- Percentage thresholds adapt to total scored gene count (dataset-size independent)
- Deduplication ensures genes in both OMIM + SYSCILIA count once (avoids double-counting)

**Per-Source Breakdown:**
- Disease genes (OMIM Usher) vs core ciliary genes (SYSCILIA SCGS v2) may have different evidence profiles
- Usher genes may score higher on expression (retina, inner ear specific)
- SYSCILIA genes may score higher on protein structure (IFT, BBSome domains)
- Separate metrics detect if one set validates poorly (suggests evidence layer imbalance)

## Self-Check: PASSED

**Created files verified:**
- [x] src/usher_pipeline/scoring/negative_controls.py exists and is importable

**Commits verified:**
- [x] e488ff2: Task 1 commit exists (negative control validation module)
- [x] 0f615c0: Task 2 commit exists (recall@k and extended validation)

**Functionality verified:**
- [x] All imports successful from usher_pipeline.scoring
- [x] HOUSEKEEPING_GENES_CORE has 13 genes
- [x] compile_housekeeping_genes() returns correct DataFrame structure
- [x] All functions callable (no import errors)

All claims in summary verified against actual implementation.

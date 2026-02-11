---
phase: 04-scoring-integration
plan: 01
subsystem: scoring
tags: [scoring, known-genes, weighted-average, duckdb, polars, multi-evidence]

# Dependency graph
requires:
  - phase: 01-data-infrastructure
    provides: PipelineStore, DuckDB persistence, gene_universe table
  - phase: 02-prototype-evidence-layer
    provides: gnomad_constraint table with loeuf_normalized
  - phase: 03-core-evidence-layers
    provides: tissue_expression, annotation_completeness, subcellular_localization, animal_model_phenotypes, literature_evidence tables
provides:
  - Known cilia/Usher gene set compilation (OMIM + SYSCILIA SCGS v2)
  - ScoringWeights validation enforcing sum constraint
  - Multi-evidence weighted scoring with NULL-preserving weighted average
  - join_evidence_layers() - LEFT JOIN all 6 evidence tables
  - compute_composite_scores() - weighted_sum / available_weight pattern
  - persist_scored_genes() - DuckDB persistence with quality flags
affects: [04-02, 04-03, ranking, filtering, validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - NULL-preserving weighted average (weighted_sum / available_weight)
    - Evidence quality flags (sufficient/moderate/sparse/no_evidence)
    - Per-layer contribution tracking for explainability
    - Known gene compilation from multiple sources

key-files:
  created:
    - src/usher_pipeline/scoring/__init__.py
    - src/usher_pipeline/scoring/known_genes.py
    - src/usher_pipeline/scoring/integration.py
  modified:
    - src/usher_pipeline/config/schema.py

key-decisions:
  - "OMIM Usher genes: 10 genes as disease positive controls"
  - "SYSCILIA SCGS v2 core: ~28 genes as ciliary positive controls (subset of 686 full list)"
  - "Known genes preserve multi-source provenance (duplicate gene_symbols with different sources)"
  - "ScoringWeights validation: sum must equal 1.0 ± 1e-6 tolerance"
  - "NULL-preserving weighted average: available_weight = sum of weights for non-NULL layers only"
  - "Quality flags based on evidence_count: >=4 sufficient, >=2 moderate, >=1 sparse, 0 no_evidence"
  - "Per-layer contributions computed as score * weight (NULL if score is NULL) for explainability"

patterns-established:
  - "NULL-preserving scoring pattern: COALESCE for weighted_sum, but available_weight excludes NULL layers"
  - "LEFT JOIN all evidence tables to gene_universe preserving all genes"
  - "Quality flag classification based on evidence layer count"
  - "Contribution tracking for transparency (each layer's impact on composite score)"

# Metrics
duration: 4min
completed: 2026-02-11
---

# Phase 04 Plan 01: Known Gene Compilation and Multi-Evidence Scoring Summary

**NULL-preserving weighted scoring engine joining 6 evidence layers with configurable weights, plus OMIM/SYSCILIA known gene compilation for validation**

## Performance

- **Duration:** 4 minutes (228 seconds)
- **Started:** 2026-02-11T12:38:05Z
- **Completed:** 2026-02-11T12:42:13Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Compiled 38 known cilia/Usher genes from OMIM (10 genes) and SYSCILIA SCGS v2 core (28 genes)
- Implemented ScoringWeights.validate_sum() enforcing weight sum constraint (1.0 ± 1e-6)
- Created join_evidence_layers() LEFT JOINing all 6 evidence tables preserving NULLs
- Built compute_composite_scores() with NULL-preserving weighted average (weighted_sum / available_weight)
- Added quality flag classification (sufficient/moderate/sparse/no_evidence) based on evidence count
- Included per-layer contribution columns for explainability

## Task Commits

Each task was committed atomically:

1. **Task 1: Known gene compilation and ScoringWeights validation** - `0cd2f7c` (feat)
2. **Task 2: Multi-evidence weighted scoring integration** - `f441e8c` (feat)

## Files Created/Modified
- `src/usher_pipeline/scoring/__init__.py` - Scoring module exports
- `src/usher_pipeline/scoring/known_genes.py` - OMIM_USHER_GENES (10), SYSCILIA_SCGS_V2_CORE (28), compile_known_genes()
- `src/usher_pipeline/scoring/integration.py` - join_evidence_layers(), compute_composite_scores(), persist_scored_genes()
- `src/usher_pipeline/config/schema.py` - Added ScoringWeights.validate_sum() method

## Decisions Made

1. **Known gene curation:** Limited SYSCILIA SCGS v2 to ~28 core genes (subset of 686 full list) for initial positive control validation. Future enhancement can add fetch_scgs_v2() to download complete list from publication supplementary data.

2. **Multi-source provenance:** compile_known_genes() does NOT de-duplicate gene_symbols across sources. A gene appearing in both OMIM and SYSCILIA will have two rows (one per source). This preserves provenance for validation and analysis.

3. **NULL-preserving weighted average:** Implemented weighted_sum / available_weight pattern where available_weight = sum of weights for non-NULL layers only. Genes with 0 evidence layers receive NULL composite_score (not 0), preserving semantic distinction between "no evidence" and "weak evidence".

4. **Quality flags:** Classification based on evidence_count thresholds (>=4 sufficient, >=2 moderate, >=1 sparse, 0 no_evidence) to guide downstream filtering and prioritization.

5. **Explainability:** Per-layer contribution columns (score * weight) enable tracing which evidence layers drove a gene's composite score. Critical for manual review and trust.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Both verification tests passed on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Phase 04 Plan 02 (ranked candidate list generation):
- Known gene set compiled and ready for exclusion filtering
- Composite scoring engine functional with NULL preservation
- Quality flags available for filtering
- Per-layer contributions available for ranking criteria

No blockers. Next plan can implement:
- Exclusion of known genes
- Ranking by composite score
- Quality flag filtering
- Top-N candidate selection

## Self-Check: PASSED

All claimed files and commits verified:
- src/usher_pipeline/scoring/__init__.py - FOUND
- src/usher_pipeline/scoring/known_genes.py - FOUND
- src/usher_pipeline/scoring/integration.py - FOUND
- Commit 0cd2f7c (Task 1) - FOUND
- Commit f441e8c (Task 2) - FOUND

---
*Phase: 04-scoring-integration*
*Plan: 01*
*Completed: 2026-02-11*

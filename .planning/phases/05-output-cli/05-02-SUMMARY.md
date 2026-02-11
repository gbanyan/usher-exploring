---
phase: 05-output-cli
plan: 02
subsystem: output
tags: [visualization, reproducibility, reporting, matplotlib, seaborn]
completed: 2026-02-11
duration_minutes: 5

dependencies:
  requires:
    - config.schema (PipelineConfig, ScoringWeights, DataSourceVersions)
    - persistence.provenance (ProvenanceTracker)
  provides:
    - visualizations.generate_all_plots
    - reproducibility.generate_reproducibility_report
  affects:
    - output.__init__ (exports visualization and reproducibility functions)

tech_stack:
  added:
    - matplotlib>=3.8.0 (visualization library with Agg backend)
    - seaborn>=0.13.0 (statistical visualization on top of matplotlib)
  patterns:
    - Non-interactive backend (Agg) for headless/CLI safety
    - Proper figure cleanup with plt.close() to prevent memory leaks
    - Graceful degradation (individual plot failures don't block others)
    - Dataclass-based report structure with dual format output (JSON + Markdown)

key_files:
  created:
    - src/usher_pipeline/output/visualizations.py (plot generation functions)
    - src/usher_pipeline/output/reproducibility.py (report generation)
    - tests/test_visualizations.py (6 tests for plot creation)
    - tests/test_reproducibility.py (7 tests for report content)
  modified:
    - pyproject.toml (added matplotlib and seaborn dependencies)
    - src/usher_pipeline/output/__init__.py (exported new functions)

decisions:
  - matplotlib_backend: "Use Agg (non-interactive) backend for headless/CLI safety"
  - plot_dpi: "300 DPI for publication-quality output"
  - tier_colors: "GREEN/ORANGE/RED for HIGH/MEDIUM/LOW (consistent across plots)"
  - error_handling: "Wrap each plot in try/except so failures don't block batch generation"
  - report_formats: "JSON for machine-readable + Markdown for human-readable"
  - validation_optional: "Validation metrics are optional in reproducibility report"

metrics:
  tasks: 2
  commits: 2
  tests: 13
  files_created: 4
  files_modified: 2
---

# Phase 05 Plan 02: Visualization and Reproducibility Reports Summary

**One-liner:** Matplotlib/seaborn visualizations (score distributions, layer contributions, tier breakdowns) and dual-format reproducibility reports (JSON + Markdown) with parameters, data versions, filtering steps, and validation metrics.

## Execution Flow

### Task 1: Visualization module with matplotlib/seaborn plots (commit: 150417f)

**Created visualization module with 3 plot types + orchestrator:**

1. **plot_score_distribution**: Histogram of composite scores colored by confidence tier (HIGH=green, MEDIUM=orange, LOW=red), 30 bins, stacked display
2. **plot_layer_contributions**: Bar chart showing non-null count per evidence layer (gnomAD, expression, annotation, localization, animal model, literature)
3. **plot_tier_breakdown**: Pie chart with percentage labels for tier distribution
4. **generate_all_plots**: Orchestrator that creates all 3 plots with error handling (one failure doesn't block others)

**Key technical decisions:**
- Use matplotlib Agg backend (non-interactive, headless-safe)
- Save all plots at 300 DPI for publication quality
- Always call `plt.close(fig)` after savefig to prevent memory leaks (critical pitfall from research)
- Convert polars DataFrame to pandas via `to_pandas()` for seaborn compatibility (acceptable overhead for small result sets)

**Dependencies added:**
- matplotlib>=3.8.0
- seaborn>=0.13.0

**Tests created (6 tests):**
- test_plot_score_distribution_creates_file
- test_plot_layer_contributions_creates_file
- test_plot_tier_breakdown_creates_file
- test_generate_all_plots_creates_all_files
- test_generate_all_plots_returns_paths
- test_plots_handle_empty_dataframe (edge case)

All tests pass with only expected warnings for empty DataFrame edge cases.

### Task 2: Reproducibility report module (commit: 5af63ea)

**Created reproducibility report generation with dual formats:**

1. **FilteringStep dataclass**: Captures step_name, input_count, output_count, criteria
2. **ReproducibilityReport dataclass**: Contains run_id (UUID4), timestamp, pipeline_version, parameters (scoring weights), data_versions (Ensembl/gnomAD/GTEx/HPA), software_environment (Python/polars/duckdb versions), filtering_steps, validation_metrics (optional), tier_statistics
3. **generate_reproducibility_report**: Extracts all metadata from config, provenance, and tiered DataFrame
4. **Report output methods:**
   - `to_json()`: Indented JSON for machine parsing
   - `to_markdown()`: Tables and headers for human reading
   - `to_dict()`: Dictionary for programmatic access

**Key design patterns:**
- NULL-preserving tier counting with polars `group_by().agg(pl.len())`
- Optional validation metrics (report generates whether or not validation results are provided)
- Filtering steps extracted from ProvenanceTracker.get_steps()
- Software versions captured at report generation time (sys.version, pl.__version__, duckdb.__version__)

**Tests created (7 tests):**
- test_generate_report_has_all_fields
- test_report_to_json_parseable
- test_report_to_markdown_has_headers
- test_report_tier_statistics_match
- test_report_includes_validation_when_provided
- test_report_without_validation
- test_report_software_versions

All tests pass.

## Deviations from Plan

**Auto-fixed Issues:**

**1. [Rule 1 - Bug] Fixed deprecated polars API**
- **Found during:** Task 2 testing
- **Issue:** `pl.count()` is deprecated in polars 0.20.5+, replaced with `pl.len()`
- **Fix:** Updated `pl.count().alias("count")` to `pl.len().alias("count")` in both visualizations.py and reproducibility.py
- **Files modified:** src/usher_pipeline/output/visualizations.py, src/usher_pipeline/output/reproducibility.py
- **Commit:** Included in 5af63ea

**2. [Rule 1 - Bug] Fixed matplotlib/seaborn deprecation warnings**
- **Found during:** Task 1 testing
- **Issue:** seaborn barplot warning about passing `palette` without `hue`, and `set_xticklabels()` warning about fixed ticks
- **Fix:** Added `hue=labels` and `legend=False` to barplot call, changed `ax.set_xticklabels()` to `plt.setp()`
- **Files modified:** src/usher_pipeline/output/visualizations.py
- **Commit:** Included in 150417f (amended during testing)

**3. [Rule 3 - Blocking] __init__.py already updated**
- **Found during:** Task 2 commit preparation
- **Issue:** Discovered that src/usher_pipeline/output/__init__.py was already updated with reproducibility and visualization exports by a parallel process
- **Resolution:** No action needed - integration work already completed by plan 05-01
- **Impact:** Positive - reduces risk of merge conflicts and ensures consistency

## Verification Results

**Import verification:**
```
✓ from usher_pipeline.output.visualizations import generate_all_plots - OK
✓ from usher_pipeline.output.reproducibility import generate_reproducibility_report, ReproducibilityReport - OK
```

**Test results:**
```
✓ 6/6 visualization tests pass
✓ 7/7 reproducibility tests pass
✓ Total: 13/13 tests pass
```

**Success criteria met:**
- [x] Visualization module produces 3 PNG plots at 300 DPI
- [x] Score distribution plot with tier color coding (GREEN/ORANGE/RED)
- [x] Layer contributions bar chart showing evidence coverage
- [x] Tier breakdown pie chart with percentages
- [x] Reproducibility report generates in both JSON and Markdown formats
- [x] Report contains parameters, data versions, filtering steps, tier statistics
- [x] Optional validation metrics handled gracefully
- [x] matplotlib Agg backend used (no display required)
- [x] All tests pass
- [x] Proper figure cleanup (plt.close) implemented

## Self-Check: PASSED

**Created files exist:**
```
✓ FOUND: src/usher_pipeline/output/visualizations.py
✓ FOUND: src/usher_pipeline/output/reproducibility.py
✓ FOUND: tests/test_visualizations.py
✓ FOUND: tests/test_reproducibility.py
```

**Commits exist:**
```
✓ FOUND: 150417f (Task 1 - visualization module)
✓ FOUND: 5af63ea (Task 2 - reproducibility module)
```

**Tests pass:**
```
✓ 13/13 tests pass (6 visualization + 7 reproducibility)
```

**Dependencies installed:**
```
✓ matplotlib>=3.8.0 installed
✓ seaborn>=0.13.0 installed
```

All verification checks passed successfully.

## Integration Notes

**For downstream consumers:**

1. **Visualization usage:**
   ```python
   from usher_pipeline.output.visualizations import generate_all_plots

   plots = generate_all_plots(tiered_df, output_dir)
   # Returns: {"score_distribution": Path, "layer_contributions": Path, "tier_breakdown": Path}
   ```

2. **Reproducibility report usage:**
   ```python
   from usher_pipeline.output.reproducibility import generate_reproducibility_report

   report = generate_reproducibility_report(
       config=config,
       tiered_df=tiered_df,
       provenance=provenance,
       validation_result=validation_dict  # Optional
   )

   report.to_json(output_dir / "reproducibility.json")
   report.to_markdown(output_dir / "reproducibility.md")
   ```

3. **Expected columns in tiered_df:**
   - composite_score, confidence_tier
   - gnomad_score, expression_score, annotation_score, localization_score, animal_model_score, literature_score (can be NULL)

4. **Plot output:**
   - All plots saved as PNG at 300 DPI
   - Figures properly closed (no memory leaks)
   - Empty DataFrames handled gracefully

5. **Report content:**
   - JSON: Machine-readable, parseable with standard json library
   - Markdown: Human-readable with tables, headers, formatted statistics
   - Both contain identical information, just different presentations

## Next Steps

Plan 05-03 will integrate these modules into the CLI with an `output` command that:
- Loads tiered results from DuckDB
- Generates all plots to output directory
- Creates reproducibility reports in both formats
- Provides summary statistics to console

This plan completes the reporting infrastructure. All visualization and documentation generation logic is now available as reusable modules.

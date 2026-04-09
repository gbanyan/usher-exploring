# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bioinformatics pipeline for discovering under-studied candidate genes related to Usher syndrome and ciliopathies. Screens ~22,600 human protein-coding genes across 6 evidence layers, producing weighted composite scores and tiered candidate lists.

## Commands

```bash
# Install (editable, with dev deps)
pip install -e ".[dev]"

# Run full pipeline (sequential steps)
usher-pipeline setup                    # Fetch gene universe via mygene
usher-pipeline evidence gnomad          # gnomAD constraint metrics
usher-pipeline evidence annotation      # GO/InterPro/pathway annotations
usher-pipeline evidence expression      # HPA + GTEx + CellxGene tissue expression
usher-pipeline evidence localization    # HPA subcellular + cilia proteomics
usher-pipeline evidence animal-models   # HCOP orthologs + MGI/ZFIN/IMPC phenotypes
usher-pipeline evidence literature --email USER@EMAIL  # PubMed via NCBI E-utilities
usher-pipeline score                    # Weighted composite scoring
usher-pipeline report                   # Generate TSV/Parquet + visualizations
usher-pipeline validate                 # Validate known Usher genes rank highly

# Tests
pytest                                  # All tests
pytest tests/test_gnomad.py             # Single test file
pytest tests/test_gnomad.py::test_name  # Single test
pytest -k "not integration"            # Skip integration tests (which hit APIs)
```

## Architecture

### Data Flow
```
mygene API → gene_universe table (DuckDB)
    ↓
6 evidence layers (each: fetch → transform → load to DuckDB)
    ↓
scoring/integration.py: LEFT JOIN all layers → weighted composite
    ↓
output/: TSV, Parquet, visualizations, reproducibility report
```

### Key Design Decisions

- **DuckDB** for persistence (`data/pipeline.duckdb`). Single-writer — no concurrent access from multiple processes.
- **Polars** for data manipulation (LazyFrame for fetch/parse, DataFrame for transforms requiring horizontal ops). Use `pl.LazyFrame` where possible and `.collect()` only when materialization is needed.
- **NULL preservation**: Missing evidence ≠ zero score. LEFT JOINs preserve NULLs; scoring weights only applied to non-NULL layers (`evidence_count` tracks coverage). **Never convert NULL to 0.0** — "unknown" is semantically different from "zero evidence".
- **Idempotent loads**: Each evidence layer uses `CREATE OR REPLACE TABLE`.
- **Checkpoint-restart**: Literature layer supports resuming via existing progress in DuckDB. Downloads check if file exists before re-fetching (`force=False` default).
- **Gene symbol deduplication**: `gene_universe` has multiple Ensembl IDs per gene_symbol (~1,539 symbols with excess IDs). Scoring deduplicates by `gene_symbol`, preferring MANE Select canonical IDs, then gnomAD-recognized IDs, then lowest Ensembl ID. See `scoring/integration.py`.

### Evidence Layer Pattern

Each of the 6 evidence layers (`evidence/{layer}/`) follows the same structure:

- `models.py` — Pydantic model, constants (URLs, column mappings)
- `fetch.py` — Download/API calls with retry (`tenacity`) and streaming (`httpx`). Returns file path or LazyFrame.
- `transform.py` — Data cleaning, normalization to 0–1 `{layer}_score_normalized` column. Quality flags assigned here.
- `load.py` — `PipelineStore.save_dataframe()` to DuckDB table. Enriches with `gene_id` from `gene_universe` where source data uses symbols.

When adding a new evidence layer: create all 4 files, register the CLI subcommand in `cli/evidence_cmd.py`, add the DuckDB table to the JOIN in `scoring/integration.py`, and add the weight to `config/schema.py` `ScoringWeights`.

### Key Modules

- **`persistence/duckdb_store.py`** — `PipelineStore` wraps DuckDB with checkpoint metadata (`_checkpoints` table). Use `save_dataframe()` / `load_dataframe()` / `has_checkpoint()` for data access.
- **`api_clients/base.py`** — `CachedAPIClient` provides retry + rate limiting + SQLite-backed HTTP caching via `requests_cache`. Used by annotation and protein layers. gnomAD/expression layers use `httpx` directly for streaming large files.
- **`config/loader.py`** — Loads `config/default.yaml` → `PipelineConfig` (Pydantic). CLI passes `--config` path through Click context.
- **`scoring/integration.py`** — The core JOIN query: CTEs deduplicate each evidence table to one row per `gene_id` via `MAX()`, then LEFT JOINs all 6 onto `gene_universe`. Composite score = `weighted_sum / available_weight` (NULL-aware).
- **`scoring/known_genes.py`** — Positive control gene sets (OMIM Usher genes, SYSCILIA). Used by `scoring/validation.py`.

### DuckDB Tables

| Table | Source | Score Column |
|-------|--------|-------------|
| `gene_universe` | mygene | — |
| `gnomad_constraint` | gnomAD v4.1 | `loeuf_normalized` |
| `tissue_expression` | HPA v23 + GTEx v8 | `expression_score_normalized` |
| `annotation_completeness` | GO/InterPro/Reactome | `annotation_score_normalized` |
| `subcellular_localization` | HPA + proteomics | `localization_score_normalized` |
| `animal_model_phenotypes` | MGI/ZFIN/IMPC via HCOP | `animal_model_score_normalized` |
| `literature_evidence` | PubMed (NCBI E-utils) | `literature_score_normalized` |
| `mane_select` | NCBI MANE v1.3 | — (reference table) |
| `scored_genes` | scoring integration | `composite_score` |

### Testing Conventions

- Unit tests: `tests/test_{layer}.py` — use `tmp_path` fixtures with inline TSV data, mock HTTP calls with `unittest.mock.patch`
- Integration tests: `tests/test_{layer}_integration.py` — hit real APIs, excluded via `pytest -k "not integration"`
- Tests verify NULL preservation explicitly (e.g., `assert gene7["pli"][0] is None`)
- Use `polars.testing.assert_frame_equal` for DataFrame comparisons

### Scoring Weights (config/default.yaml)

gnomAD: 0.20, Expression: 0.20, Annotation: 0.15, Localization: 0.15, Animal Model: 0.15, Literature: 0.15

Weights must sum to 1.0 (validated by `ScoringWeights.validate_sum()` with 1e-6 tolerance).

### Known Limitations

- **gnomAD gene_id alignment**: gnomAD uses transcript-level IDs; join to gene_universe may produce NaN scores for some genes. `gnomad/load.py` enriches via `gene_symbol` fallback.
- **GTEx v8 lacks retina tissue**: "Eye - Retina" not available; retina expression comes only from HPA.
- **HPA expression merge gap**: HPA uses gene_symbol while pipeline keys on gene_id; the join in `expression/transform.py` may miss genes without symbol mapping.
- **Literature layer**: Uses bulk gene2pubmed (~150MB) + 6 batch PubMed MeSH queries. Runtime ~5-10 minutes. Bulk files cached in `data/literature/`. Use `--force` to re-download.
- **HPA URLs pinned to v23**: Using `v23.proteinatlas.org` because latest version changed download paths.

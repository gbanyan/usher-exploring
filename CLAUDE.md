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
- **Polars** for data manipulation (LazyFrame for fetch, DataFrame for transforms requiring horizontal ops).
- **NULL preservation**: Missing evidence ≠ zero score. LEFT JOINs preserve NULLs; scoring weights only applied to non-NULL layers (`evidence_count` tracks coverage).
- **Idempotent loads**: Each evidence layer uses `CREATE OR REPLACE TABLE`.
- **Checkpoint-restart**: Literature layer supports resuming via existing progress in DuckDB.

### Source Layout

```
src/usher_pipeline/
├── cli/                 # Click commands (setup, evidence, score, report, validate)
├── config/              # YAML config loading + schema (ScoringWeights, DataVersions)
├── persistence/         # PipelineStore (DuckDB wrapper), ProvenanceTracker
├── gene_mapping/        # Gene universe fetch (mygene) + validation
├── evidence/            # 6 evidence layers, each with:
│   ├── {layer}/fetch.py       # Download/API calls
│   ├── {layer}/transform.py   # Data processing
│   ├── {layer}/load.py        # DuckDB persistence
│   └── {layer}/models.py      # Pydantic models + constants
├── scoring/             # Composite scoring, validation, sensitivity analysis
└── output/              # Report generation, visualizations
```

### DuckDB Tables

| Table | Source | Score Column |
|-------|--------|-------------|
| `gene_universe` | mygene | — |
| `gnomad_constraint` | gnomAD v4.1 | `loeuf_normalized` |
| `tissue_expression` | HPA v23 + GTEx v8 | `expression_score_normalized` |
| `gene_annotation` | GO/InterPro/Reactome | `annotation_score_normalized` |
| `subcellular_localization` | HPA + proteomics | `localization_score_normalized` |
| `animal_model_phenotypes` | MGI/ZFIN/IMPC via HCOP | `animal_model_score_normalized` |
| `literature_evidence` | PubMed (NCBI E-utils) | `literature_score_normalized` |

### Scoring Weights (config/default.yaml)

gnomAD: 0.20, Expression: 0.20, Annotation: 0.15, Localization: 0.15, Animal Model: 0.15, Literature: 0.15

### Known Limitations

- **gnomAD gene_id alignment**: gnomAD uses transcript-level IDs; join to gene_universe may produce NaN scores for some genes.
- **GTEx v8 lacks retina tissue**: "Eye - Retina" not available; retina expression comes only from HPA.
- **HPA expression merge gap**: HPA uses gene_symbol while pipeline keys on gene_id; the join in `expression/transform.py` may miss genes without symbol mapping.
- **Literature layer is slow**: ~8 genes/minute via NCBI E-utilities; full run takes ~46 hours for 22K genes. Use `--api-key` for 10 req/s (vs 3 req/s default).
- **HPA URLs pinned to v23**: Using `v23.proteinatlas.org` because latest version changed download paths.

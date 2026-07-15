# Pipeline Reproducibility Report

**Run ID:** `cfba131a-9d63-4ed8-8cfe-6b4c353af9be`
**Timestamp:** 2026-07-12T14:21:12.641958+00:00
**Pipeline Version:** 0.1.0

## Parameters

**Scoring Weights:**

- gnomAD: 0.20
- Expression: 0.20
- Annotation: 0.15
- Localization: 0.15
- Animal Model: 0.15
- Literature: 0.15

## Data Versions

- **ensembl_release:** 113
- **gnomad_version:** v4.1
- **gtex_version:** v8
- **hpa_version:** 23.0
- **mane_version:** 1.3

## Software Environment

- **python:** 3.13.11
- **polars:** 1.39.3
- **duckdb:** 1.5.1

## Filtering Steps

| Step | Input Count | Output Count | Criteria |
|------|-------------|--------------|----------|
| load_scored_genes | 19554 | 19554 | Load all scored genes from DuckDB |
| apply_tier_classification | 19554 | 19131 | HIGH: score>=0.7 & evidence>=3 & cilia-signal gate (ciliary localization or top-quartile sensory animal-model phenotype); MEDIUM: score>=0.4 & evidence>=2; LOW: score>=0.2 |
| write_candidate_output | 19131 | 19131 | Write TSV + Parquet with provenance YAML |
| generate_visualizations | 19131 | 3 | Generate score distribution, layer contributions, tier breakdown plots |

## Tier Statistics

- **Total Candidates:** 19131
- **HIGH:** 83
- **MEDIUM:** 11323
- **LOW:** 7725

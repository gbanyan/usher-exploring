# Pipeline Reproducibility Report

**Run ID:** `5e0f1f88-11f3-46ff-a858-83d16ad5f68f`
**Timestamp:** 2026-05-20T02:55:43.199449+00:00
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

- **python:** 3.12.12
- **polars:** 1.39.3
- **duckdb:** 1.5.1

## Filtering Steps

| Step | Input Count | Output Count | Criteria |
|------|-------------|--------------|----------|
| load_scored_genes | 19554 | 19554 | Load all scored genes from DuckDB |
| apply_tier_classification | 19554 | 19132 | HIGH: score>=0.7 & evidence>=3; MEDIUM: score>=0.4 & evidence>=2; LOW: score>=0.2 |
| write_candidate_output | 19132 | 19132 | Write TSV + Parquet with provenance YAML |
| generate_visualizations | 19132 | 3 | Generate score distribution, layer contributions, tier breakdown plots |

## Tier Statistics

- **Total Candidates:** 19132
- **HIGH:** 136
- **MEDIUM:** 11294
- **LOW:** 7702

# Pipeline Reproducibility Report

**Run ID:** `9a0b01a7-9407-4d8d-b9b3-fd0e614a563d`
**Timestamp:** 2026-04-09T15:25:29.810100+00:00
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

## Software Environment

- **python:** 3.13.11
- **polars:** 1.39.3
- **duckdb:** 1.5.1

## Filtering Steps

| Step | Input Count | Output Count | Criteria |
|------|-------------|--------------|----------|
| load_scored_genes | 19555 | 19555 | Load all scored genes from DuckDB |
| apply_tier_classification | 19555 | 18249 | HIGH: score>=0.7 & evidence>=3; MEDIUM: score>=0.4 & evidence>=2; LOW: score>=0.2 |
| write_candidate_output | 18249 | 18249 | Write TSV + Parquet with provenance YAML |

## Tier Statistics

- **Total Candidates:** 18249
- **HIGH:** 8
- **MEDIUM:** 8066
- **LOW:** 10175

# Pipeline Reproducibility Report

**Run ID:** `e7486ff1-f9be-403b-a68d-115fc845f4a1`
**Timestamp:** 2026-02-15T21:13:12.288563+00:00
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

- **python:** 3.14.3
- **polars:** 1.38.1
- **duckdb:** 1.4.4

## Filtering Steps

| Step | Input Count | Output Count | Criteria |
|------|-------------|--------------|----------|
| load_scored_genes | 0 | 0 |  |
| apply_tier_classification | 0 | 0 |  |
| write_candidate_output | 0 | 0 |  |
| generate_visualizations | 0 | 0 |  |

## Tier Statistics

- **Total Candidates:** 21103
- **HIGH:** 18
- **MEDIUM:** 9577
- **LOW:** 11508

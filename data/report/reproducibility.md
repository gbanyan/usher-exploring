# Pipeline Reproducibility Report

**Run ID:** `10c84b97-46b4-4e29-8884-d97cffeed0da`
**Timestamp:** 2026-08-14T13:38:24.688179+00:00
**Pipeline Version:** 0.1.0
**Config SHA-256:** `b579c4b838b92bd6a578947f0ef30ebcdaf34ef2789c0c502c000f196dd2c8cf`

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
- **ensembl_gene_source:** annotation/Homo_sapiens.GRCh38.113.gtf.gz
- **ensembl_gene_source_url:** https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/Homo_sapiens.GRCh38.113.gtf.gz
- **ensembl_gene_source_sha256:** 62f1709b40e083ce9d4cdc64a86b5ffec2c5d5371434bb7095c74dc89079c466
- **gnomad_version:** v4.1
- **gtex_version:** v8
- **hpa_version:** 23.0
- **mane_version:** 1.3
- **cellxgene_census_version:** 2025-11-08

## Data Source Metadata Coverage

**Coverage status:** incomplete
**Recorded source records:** 6

Coverage counts only metadata explicitly recorded for this run; missing source, version, retrieval, or checksum fields are not inferred. Sidecars without an exact current-config hash are rejected.

**Source metadata coverage is incomplete; no missing fields are inferred.**

| Source | Version | URL | Retrieved at | Checksum |
|--------|---------|-----|--------------|----------|
| animal_model_phenotypes_donor_duckdb | N/A | N/A | N/A | 1f5f606d0fb1d1ea3ca90386416c804ea70c809b8ea670c4a94e7659dac641d8 |
| annotation_completeness_donor_duckdb | N/A | N/A | N/A | 1f5f606d0fb1d1ea3ca90386416c804ea70c809b8ea670c4a94e7659dac641d8 |
| download_gnomad_constraint | v4.1 | https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/constraint/gnomad.v4.1.constraint_metrics.tsv | N/A | 68d8abdb7fc48f570869b02dfaa74b9fecaece7fcc5f301ddca40ec1ce12da00 |
| ensembl_gtf_local | N/A | https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/Homo_sapiens.GRCh38.113.gtf.gz | N/A | 62f1709b40e083ce9d4cdc64a86b5ffec2c5d5371434bb7095c74dc89079c466 |
| legacy_mapping_duckdb | N/A | N/A | N/A | 1f5f606d0fb1d1ea3ca90386416c804ea70c809b8ea670c4a94e7659dac641d8 |
| mane_select_local | 1.3 | N/A | N/A | 06637bc2d1f04f54635a8a09ff535ed44e5f7a2ced2d2a30a03f50b233379c35 |

## Software Environment

- **python:** 3.13.1
- **polars:** 1.43.2
- **duckdb:** 1.5.5

## Filtering Steps

| Step | Input Count | Output Count | Criteria |
|------|-------------|--------------|----------|
| derived_cache_reuse | 0 | 0 |  |
| load_animal_model_phenotypes | 0 | 0 |  |
| derived_cache_reuse | 0 | 0 |  |
| load_annotation_completeness | 0 | 0 |  |
| process_expression_evidence | 0 | 0 |  |
| load_tissue_expression | 0 | 0 |  |
| download_gnomad_constraint | 0 | 0 |  |
| process_gnomad_constraint | 0 | 0 |  |
| load_gnomad_constraint | 0 | 0 |  |
| process_literature_evidence | 0 | 0 |  |
| load_literature_evidence | 0 | 0 |  |
| process_localization_evidence | 0 | 0 |  |
| load_subcellular_localization | 0 | 0 |  |
| load_known_genes | 0 | 0 |  |
| compute_composite_scores | 0 | 0 |  |
| run_qc_checks | 0 | 0 |  |
| evaluate_known_gene_control_recovery | 0 | 0 |  |
| fetch_gene_universe | 0 | 0 |  |
| map_gene_ids | 0 | 0 |  |
| load_mane_select | 0 | 0 |  |
| validate_mapping | 0 | 0 |  |
| evaluate_positive_control_recovery | 0 | 0 |  |
| evaluate_negative_control_recovery | 0 | 0 |  |
| run_sensitivity_analysis | 0 | 0 |  |
| load_scored_genes | 20081 | 20081 | Load all scored genes from DuckDB |
| apply_tier_classification | 20081 | 18387 | HIGH: score>=0.7 & evidence>=3 & cilia-signal gate (ciliary localization or top-quartile sensory animal-model phenotype); MEDIUM: score>=0.4 & evidence>=2; LOW: score>=0.2 |
| write_candidate_output | 18387 | 18387 | Write TSV + Parquet with provenance YAML |
| generate_visualizations | 18387 | 3 | Generate score distribution, layer contributions, tier breakdown plots |

## Tier Statistics

- **Total Candidates:** 18387
- **HIGH:** 62
- **MEDIUM:** 9673
- **LOW:** 8652

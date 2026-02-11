"""Unit tests for output generation module: tiering, evidence summary, and writers."""

from pathlib import Path

import polars as pl
import pytest
import yaml

from usher_pipeline.output import (
    EVIDENCE_LAYERS,
    TIER_THRESHOLDS,
    add_evidence_summary,
    assign_tiers,
    write_candidate_output,
)


@pytest.fixture
def synthetic_scored_genes() -> pl.DataFrame:
    """
    Create synthetic scored genes DataFrame spanning all tiers.

    Returns DataFrame with ~20 rows:
    - 3 genes HIGH tier (score >= 0.7, evidence_count >= 3)
    - 5 genes MEDIUM tier (score 0.4-0.69, evidence_count >= 2)
    - 5 genes LOW tier (score 0.2-0.39)
    - 3 genes EXCLUDED (score < 0.2)
    - 4 genes with NULL composite_score (no evidence)
    """
    data = {
        "gene_id": [
            # HIGH tier (3 genes)
            "ENSG001",
            "ENSG002",
            "ENSG003",
            # MEDIUM tier (5 genes)
            "ENSG004",
            "ENSG005",
            "ENSG006",
            "ENSG007",
            "ENSG008",
            # LOW tier (5 genes)
            "ENSG009",
            "ENSG010",
            "ENSG011",
            "ENSG012",
            "ENSG013",
            # EXCLUDED tier (3 genes - score < 0.2)
            "ENSG014",
            "ENSG015",
            "ENSG016",
            # NULL composite_score (4 genes - no evidence)
            "ENSG017",
            "ENSG018",
            "ENSG019",
            "ENSG020",
        ],
        "gene_symbol": [
            "HIGH1",
            "HIGH2",
            "HIGH3",
            "MED1",
            "MED2",
            "MED3",
            "MED4",
            "MED5",
            "LOW1",
            "LOW2",
            "LOW3",
            "LOW4",
            "LOW5",
            "EX1",
            "EX2",
            "EX3",
            "NULL1",
            "NULL2",
            "NULL3",
            "NULL4",
        ],
        "composite_score": [
            # HIGH: >= 0.7
            0.85,
            0.78,
            0.72,
            # MEDIUM: 0.4-0.69
            0.65,
            0.58,
            0.52,
            0.48,
            0.42,
            # LOW: 0.2-0.39
            0.38,
            0.32,
            0.28,
            0.24,
            0.21,
            # EXCLUDED: < 0.2
            0.18,
            0.12,
            0.05,
            # NULL (no evidence)
            None,
            None,
            None,
            None,
        ],
        "evidence_count": [
            # HIGH: >= 3
            5,
            4,
            3,
            # MEDIUM: >= 2
            4,
            3,
            3,
            2,
            2,
            # LOW: >= 1
            2,
            2,
            1,
            1,
            1,
            # EXCLUDED: any count
            1,
            1,
            0,
            # NULL
            0,
            0,
            0,
            0,
        ],
        "quality_flag": [
            "sufficient_evidence",
            "sufficient_evidence",
            "moderate_evidence",
            "sufficient_evidence",
            "moderate_evidence",
            "moderate_evidence",
            "moderate_evidence",
            "moderate_evidence",
            "moderate_evidence",
            "moderate_evidence",
            "sparse_evidence",
            "sparse_evidence",
            "sparse_evidence",
            "sparse_evidence",
            "sparse_evidence",
            "no_evidence",
            "no_evidence",
            "no_evidence",
            "no_evidence",
            "no_evidence",
        ],
        # Layer scores (nullable)
        "gnomad_score": [
            0.9,
            0.8,
            0.7,
            0.6,
            0.5,
            0.4,
            0.3,
            0.2,
            0.4,
            0.3,
            None,
            None,
            0.2,
            None,
            0.1,
            None,
            None,
            None,
            None,
            None,
        ],
        "expression_score": [
            0.85,
            0.75,
            0.65,
            0.7,
            0.6,
            0.5,
            0.45,
            0.4,
            0.35,
            0.3,
            0.25,
            0.2,
            None,
            0.15,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "annotation_score": [
            0.8,
            0.7,
            0.6,
            0.65,
            0.55,
            0.45,
            None,
            None,
            None,
            None,
            0.3,
            0.25,
            0.2,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "localization_score": [
            0.75,
            None,
            None,
            0.6,
            0.5,
            None,
            0.4,
            0.35,
            0.3,
            0.25,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "animal_model_score": [
            0.9,
            0.8,
            0.75,
            None,
            None,
            0.55,
            0.5,
            0.45,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "literature_score": [
            None,
            0.85,
            0.7,
            0.68,
            0.62,
            0.58,
            None,
            None,
            None,
            None,
            None,
            None,
            0.22,
            0.18,
            0.15,
            0.05,
            None,
            None,
            None,
            None,
        ],
        # Contribution columns (score * weight) - simplified for testing
        "gnomad_contribution": [
            0.18,
            0.16,
            0.14,
            0.12,
            0.1,
            0.08,
            0.06,
            0.04,
            0.08,
            0.06,
            None,
            None,
            0.04,
            None,
            0.02,
            None,
            None,
            None,
            None,
            None,
        ],
        "expression_contribution": [
            0.17,
            0.15,
            0.13,
            0.14,
            0.12,
            0.1,
            0.09,
            0.08,
            0.07,
            0.06,
            0.05,
            0.04,
            None,
            0.03,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "annotation_contribution": [
            0.12,
            0.105,
            0.09,
            0.098,
            0.083,
            0.068,
            None,
            None,
            None,
            None,
            0.045,
            0.038,
            0.03,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "localization_contribution": [
            0.113,
            None,
            None,
            0.09,
            0.075,
            None,
            0.06,
            0.053,
            0.045,
            0.038,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "animal_model_contribution": [
            0.135,
            0.12,
            0.113,
            None,
            None,
            0.083,
            0.075,
            0.068,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        "literature_contribution": [
            None,
            0.128,
            0.105,
            0.102,
            0.093,
            0.087,
            None,
            None,
            None,
            None,
            None,
            None,
            0.033,
            0.027,
            0.023,
            0.008,
            None,
            None,
            None,
            None,
        ],
    }

    return pl.DataFrame(data)


def test_assign_tiers_default_thresholds(synthetic_scored_genes):
    """Test tier assignment with default thresholds."""
    result = assign_tiers(synthetic_scored_genes)

    # Check that EXCLUDED genes are filtered out (should have 13 genes remaining)
    # 3 HIGH + 5 MEDIUM + 5 LOW = 13 (7 excluded: 3 below threshold + 4 NULL)
    assert result.height == 13, f"Expected 13 genes, got {result.height}"

    # Verify tier counts
    tier_dist = result.group_by("confidence_tier").agg(pl.len()).sort("confidence_tier")
    tier_counts = {row["confidence_tier"]: row["len"] for row in tier_dist.to_dicts()}

    assert tier_counts.get("HIGH", 0) == 3, "Expected 3 HIGH tier genes"
    assert tier_counts.get("MEDIUM", 0) == 5, "Expected 5 MEDIUM tier genes"
    assert tier_counts.get("LOW", 0) == 5, "Expected 5 LOW tier genes"
    assert "EXCLUDED" not in tier_counts, "EXCLUDED genes should be filtered out"


def test_assign_tiers_custom_thresholds(synthetic_scored_genes):
    """Test tier assignment with custom thresholds."""
    custom_thresholds = {
        "HIGH": {"composite_score": 0.8, "evidence_count": 4},  # Stricter
        "MEDIUM": {"composite_score": 0.5, "evidence_count": 3},  # Stricter
        "LOW": {"composite_score": 0.3, "evidence_count": 1},  # More relaxed
    }

    result = assign_tiers(synthetic_scored_genes, thresholds=custom_thresholds)

    # With stricter HIGH threshold (0.8), only 1 gene qualifies (ENSG001 with 0.85)
    tier_dist = result.group_by("confidence_tier").agg(pl.len()).sort("confidence_tier")
    tier_counts = {row["confidence_tier"]: row["len"] for row in tier_dist.to_dicts()}

    assert tier_counts.get("HIGH", 0) == 1, "Expected 1 HIGH tier gene with stricter threshold"


def test_assign_tiers_sorting(synthetic_scored_genes):
    """Test that output is sorted by composite_score DESC, gene_id ASC."""
    result = assign_tiers(synthetic_scored_genes)

    # Extract composite scores (should be descending)
    scores = result["composite_score"].to_list()

    # Check descending order
    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i + 1], f"Scores not descending at index {i}"

    # Check first gene is the highest scorer
    assert result[0, "gene_id"] == "ENSG001", "Highest scorer should be ENSG001"


def test_add_evidence_summary_supporting_layers(synthetic_scored_genes):
    """Test that supporting_layers correctly lists layers with non-NULL scores."""
    result = add_evidence_summary(synthetic_scored_genes)

    # ENSG001 (HIGH1) has scores in: gnomad, expression, annotation, localization, animal_model
    # (literature is NULL)
    high1_row = result.filter(pl.col("gene_id") == "ENSG001")
    supporting = high1_row["supporting_layers"][0]  # Extract string value from Series

    # Check that the 5 layers are listed
    assert "gnomad" in supporting
    assert "expression" in supporting
    assert "annotation" in supporting
    assert "localization" in supporting
    assert "animal_model" in supporting
    assert "literature" not in supporting  # NULL score


def test_add_evidence_summary_gaps(synthetic_scored_genes):
    """Test that evidence_gaps correctly lists layers with NULL scores."""
    result = add_evidence_summary(synthetic_scored_genes)

    # ENSG020 (NULL4) has all NULL scores
    null4_row = result.filter(pl.col("gene_id") == "ENSG020")
    gaps = null4_row["evidence_gaps"][0]  # Extract string value from Series
    supporting = null4_row["supporting_layers"][0]  # Extract string value from Series

    # All 6 layers should be in gaps
    for layer in EVIDENCE_LAYERS:
        assert layer in gaps, f"Layer {layer} should be in evidence_gaps"

    # supporting_layers should be empty
    assert supporting == "", "Gene with all NULL scores should have empty supporting_layers"


def test_write_candidate_output_creates_files(tmp_path, synthetic_scored_genes):
    """Test that write_candidate_output creates TSV, Parquet, and provenance files."""
    # Add tier and evidence summary columns
    tiered = assign_tiers(synthetic_scored_genes)
    full_df = add_evidence_summary(tiered)

    # Write output
    paths = write_candidate_output(full_df, tmp_path, filename_base="test_candidates")

    # Check all files exist
    assert paths["tsv"].exists(), "TSV file should exist"
    assert paths["parquet"].exists(), "Parquet file should exist"
    assert paths["provenance"].exists(), "Provenance YAML should exist"

    # Check filenames
    assert paths["tsv"].name == "test_candidates.tsv"
    assert paths["parquet"].name == "test_candidates.parquet"
    assert paths["provenance"].name == "test_candidates.provenance.yaml"


def test_write_candidate_output_tsv_readable(tmp_path, synthetic_scored_genes):
    """Test that TSV output can be read back and has correct schema."""
    tiered = assign_tiers(synthetic_scored_genes)
    full_df = add_evidence_summary(tiered)

    paths = write_candidate_output(full_df, tmp_path)

    # Read back TSV
    tsv_df = pl.read_csv(paths["tsv"], separator="\t")

    # Check row count matches
    assert tsv_df.height == full_df.height, "TSV should have same row count as input"

    # Check column count matches
    assert len(tsv_df.columns) == len(full_df.columns), "TSV should have same column count as input"

    # Check key columns exist
    assert "gene_id" in tsv_df.columns
    assert "confidence_tier" in tsv_df.columns
    assert "supporting_layers" in tsv_df.columns
    assert "evidence_gaps" in tsv_df.columns


def test_write_candidate_output_parquet_readable(tmp_path, synthetic_scored_genes):
    """Test that Parquet output can be read back and schema matches."""
    tiered = assign_tiers(synthetic_scored_genes)
    full_df = add_evidence_summary(tiered)

    paths = write_candidate_output(full_df, tmp_path)

    # Read back Parquet
    parquet_df = pl.read_parquet(paths["parquet"])

    # Check row count matches
    assert parquet_df.height == full_df.height, "Parquet should have same row count as input"

    # Check column count matches
    assert len(parquet_df.columns) == len(full_df.columns), "Parquet should have same column count as input"

    # Check schema matches (column names and order)
    assert parquet_df.columns == full_df.columns, "Parquet should have identical schema to input"


def test_write_candidate_output_provenance_yaml(tmp_path, synthetic_scored_genes):
    """Test that provenance YAML contains accurate statistics."""
    tiered = assign_tiers(synthetic_scored_genes)
    full_df = add_evidence_summary(tiered)

    paths = write_candidate_output(full_df, tmp_path)

    # Read provenance YAML
    with open(paths["provenance"]) as f:
        prov = yaml.safe_load(f)

    # Check structure
    assert "generated_at" in prov, "Provenance should have generated_at timestamp"
    assert "output_files" in prov, "Provenance should list output files"
    assert "statistics" in prov, "Provenance should have statistics"
    assert "column_count" in prov, "Provenance should have column_count"
    assert "column_names" in prov, "Provenance should have column_names"

    # Check statistics match
    stats = prov["statistics"]
    assert stats["total_candidates"] == full_df.height, "Total candidates should match row count"
    assert stats["high_count"] == 3, "Should have 3 HIGH tier genes"
    assert stats["medium_count"] == 5, "Should have 5 MEDIUM tier genes"
    assert stats["low_count"] == 5, "Should have 5 LOW tier genes"

    # Check column info
    assert prov["column_count"] == len(full_df.columns), "Column count should match DataFrame"
    assert len(prov["column_names"]) == len(full_df.columns), "Column names list should match DataFrame"

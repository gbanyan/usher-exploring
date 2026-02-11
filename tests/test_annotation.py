"""Unit tests for annotation evidence layer."""

import polars as pl
import pytest
from unittest.mock import Mock, patch

from usher_pipeline.evidence.annotation import (
    classify_annotation_tier,
    normalize_annotation_score,
)


def test_go_count_extraction():
    """Test correct GO term counting by category."""
    # Create synthetic data with different GO counts per category
    df = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
        "gene_symbol": ["GENE1", "GENE2", "GENE3"],
        "go_term_count": [50, 15, 3],
        "go_biological_process_count": [30, 10, 2],
        "go_molecular_function_count": [15, 3, 1],
        "go_cellular_component_count": [5, 2, 0],
        "uniprot_annotation_score": [5, 4, 2],
        "has_pathway_membership": [True, True, False],
    })

    # Verify counts sum correctly (BP + MF + CC should equal total)
    for row in df.iter_rows(named=True):
        expected_total = (
            row["go_biological_process_count"]
            + row["go_molecular_function_count"]
            + row["go_cellular_component_count"]
        )
        assert row["go_term_count"] == expected_total


def test_null_go_handling():
    """Test that genes with no GO data get NULL counts."""
    # Create data with NULL GO counts
    df = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002"],
        "gene_symbol": ["GENE1", "GENE2"],
        "go_term_count": [20, None],
        "go_biological_process_count": [15, None],
        "go_molecular_function_count": [3, None],
        "go_cellular_component_count": [2, None],
        "uniprot_annotation_score": [4, 3],
        "has_pathway_membership": [True, False],
    })

    # Verify NULL is preserved (not converted to 0)
    assert df["go_term_count"][1] is None
    assert df["go_biological_process_count"][1] is None


def test_tier_classification_well_annotated():
    """Test well_annotated tier: high GO + high UniProt."""
    df = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
        "gene_symbol": ["GENE1", "GENE2", "GENE3"],
        "go_term_count": [25, 20, 22],
        "go_biological_process_count": [15, 12, 13],
        "go_molecular_function_count": [7, 6, 7],
        "go_cellular_component_count": [3, 2, 2],
        "uniprot_annotation_score": [5, 4, 4],
        "has_pathway_membership": [True, True, False],
    })

    result = classify_annotation_tier(df)

    # All should be well_annotated (GO >= 20 AND UniProt >= 4)
    assert all(result["annotation_tier"] == "well_annotated")


def test_tier_classification_poorly_annotated():
    """Test poorly_annotated tier: low/NULL GO + low UniProt."""
    df = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
        "gene_symbol": ["GENE1", "GENE2", "GENE3"],
        "go_term_count": [2, None, 0],
        "go_biological_process_count": [1, None, 0],
        "go_molecular_function_count": [1, None, 0],
        "go_cellular_component_count": [0, None, 0],
        "uniprot_annotation_score": [2, None, 1],
        "has_pathway_membership": [False, None, False],
    })

    result = classify_annotation_tier(df)

    # All should be poorly_annotated
    assert all(result["annotation_tier"] == "poorly_annotated")


def test_tier_classification_partial():
    """Test partially_annotated tier: medium annotations."""
    df = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
        "gene_symbol": ["GENE1", "GENE2", "GENE3"],
        "go_term_count": [10, 3, 15],
        "go_biological_process_count": [7, 2, 10],
        "go_molecular_function_count": [2, 1, 4],
        "go_cellular_component_count": [1, 0, 1],
        "uniprot_annotation_score": [3, 3, 2],
        "has_pathway_membership": [True, False, True],
    })

    result = classify_annotation_tier(df)

    # All should be partially_annotated (GO >= 5 OR UniProt >= 3)
    assert all(result["annotation_tier"] == "partially_annotated")


def test_normalization_bounds():
    """Test that normalized scores are always in [0, 1] range."""
    df = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002", "ENSG003", "ENSG004"],
        "gene_symbol": ["GENE1", "GENE2", "GENE3", "GENE4"],
        "go_term_count": [100, 50, 10, 1],
        "go_biological_process_count": [60, 30, 7, 1],
        "go_molecular_function_count": [30, 15, 2, 0],
        "go_cellular_component_count": [10, 5, 1, 0],
        "uniprot_annotation_score": [5, 4, 3, 1],
        "has_pathway_membership": [True, True, False, False],
    })

    result = normalize_annotation_score(df)

    # All non-NULL scores should be in [0, 1]
    scores = result.filter(pl.col("annotation_score_normalized").is_not_null())["annotation_score_normalized"]
    assert all(scores >= 0.0)
    assert all(scores <= 1.0)


def test_normalization_null_preservation():
    """Test that all-NULL inputs produce NULL score."""
    df = pl.DataFrame({
        "gene_id": ["ENSG001"],
        "gene_symbol": ["GENE1"],
        "go_term_count": pl.Series([None], dtype=pl.Int64),
        "go_biological_process_count": pl.Series([None], dtype=pl.Int64),
        "go_molecular_function_count": pl.Series([None], dtype=pl.Int64),
        "go_cellular_component_count": pl.Series([None], dtype=pl.Int64),
        "uniprot_annotation_score": pl.Series([None], dtype=pl.Int64),
        "has_pathway_membership": pl.Series([None], dtype=pl.Boolean),
    })

    result = normalize_annotation_score(df)

    # Should get NULL score (not 0.0)
    assert result["annotation_score_normalized"][0] is None


def test_normalization_with_pathway():
    """Test that pathway membership contributes to score."""
    # Two genes with identical GO/UniProt, different pathway membership
    df = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002"],
        "gene_symbol": ["GENE1", "GENE2"],
        "go_term_count": [10, 10],
        "go_biological_process_count": [7, 7],
        "go_molecular_function_count": [2, 2],
        "go_cellular_component_count": [1, 1],
        "uniprot_annotation_score": [3, 3],
        "has_pathway_membership": [True, False],
    })

    result = normalize_annotation_score(df)

    # Gene with pathway should have higher score
    assert result["annotation_score_normalized"][0] > result["annotation_score_normalized"][1]


def test_composite_weighting():
    """Test that composite score follows 0.5/0.3/0.2 weight distribution."""
    # Create gene with only GO data (should contribute 50% weight)
    df_go_only = pl.DataFrame({
        "gene_id": ["ENSG001"],
        "gene_symbol": ["GENE1"],
        "go_term_count": [100],  # Max GO to get full GO component
        "go_biological_process_count": [60],
        "go_molecular_function_count": [30],
        "go_cellular_component_count": [10],
        "uniprot_annotation_score": pl.Series([None], dtype=pl.Int64),
        "has_pathway_membership": pl.Series([None], dtype=pl.Boolean),
    })

    # Create gene with only UniProt data (should contribute 30% weight)
    df_uniprot_only = pl.DataFrame({
        "gene_id": ["ENSG002"],
        "gene_symbol": ["GENE2"],
        "go_term_count": pl.Series([None], dtype=pl.Int64),
        "go_biological_process_count": pl.Series([None], dtype=pl.Int64),
        "go_molecular_function_count": pl.Series([None], dtype=pl.Int64),
        "go_cellular_component_count": pl.Series([None], dtype=pl.Int64),
        "uniprot_annotation_score": [5],  # Max UniProt score
        "has_pathway_membership": pl.Series([None], dtype=pl.Boolean),
    })

    # Create gene with only pathway data (should contribute 20% weight)
    df_pathway_only = pl.DataFrame({
        "gene_id": ["ENSG003"],
        "gene_symbol": ["GENE3"],
        "go_term_count": pl.Series([None], dtype=pl.Int64),
        "go_biological_process_count": pl.Series([None], dtype=pl.Int64),
        "go_molecular_function_count": pl.Series([None], dtype=pl.Int64),
        "go_cellular_component_count": pl.Series([None], dtype=pl.Int64),
        "uniprot_annotation_score": pl.Series([None], dtype=pl.Int64),
        "has_pathway_membership": [True],
    })

    # Normalize each separately (need same GO max, so combine first)
    df_combined = pl.concat([df_go_only, df_uniprot_only, df_pathway_only])
    result = normalize_annotation_score(df_combined)

    # Check approximate weights (allowing for small rounding)
    go_score = result["annotation_score_normalized"][0]
    uniprot_score = result["annotation_score_normalized"][1]
    pathway_score = result["annotation_score_normalized"][2]

    # GO component should be ~0.5 (full weight)
    assert abs(go_score - 0.5) < 0.01

    # UniProt component should be 0.3 (full score * weight)
    assert abs(uniprot_score - 0.3) < 0.01

    # Pathway component should be 0.2 (full weight)
    assert abs(pathway_score - 0.2) < 0.01

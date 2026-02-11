"""Unit tests for expression evidence layer.

Tests tau calculation, enrichment scoring, and null handling with synthetic data.
NO external API calls - all data is mocked or synthetic.
"""

import polars as pl
import pytest

from usher_pipeline.evidence.expression.transform import (
    calculate_tau_specificity,
    compute_expression_score,
)


def test_tau_calculation_ubiquitous():
    """Equal expression across tissues -> Tau near 0 (ubiquitous)."""
    # Create synthetic data with equal expression across tissues
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001", "ENSG00000002"],
        "tissue1": [10.0, 20.0],
        "tissue2": [10.0, 20.0],
        "tissue3": [10.0, 20.0],
        "tissue4": [10.0, 20.0],
    })

    tissue_cols = ["tissue1", "tissue2", "tissue3", "tissue4"]
    result = calculate_tau_specificity(df, tissue_cols)

    # Tau should be close to 0 for ubiquitous expression
    assert "tau_specificity" in result.columns
    tau_values = result.select("tau_specificity").to_series().to_list()
    assert tau_values[0] == pytest.approx(0.0, abs=0.01)
    assert tau_values[1] == pytest.approx(0.0, abs=0.01)


def test_tau_calculation_specific():
    """Expression in one tissue only -> Tau near 1 (tissue-specific)."""
    # Gene expressed only in one tissue
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001"],
        "tissue1": [100.0],
        "tissue2": [0.0],
        "tissue3": [0.0],
        "tissue4": [0.0],
    })

    tissue_cols = ["tissue1", "tissue2", "tissue3", "tissue4"]
    result = calculate_tau_specificity(df, tissue_cols)

    tau = result.select("tau_specificity").item()
    # Tau = sum(1 - xi/xmax) / (n-1) = (0 + 1 + 1 + 1) / 3 = 1.0
    assert tau == pytest.approx(1.0, abs=0.01)


def test_tau_null_handling():
    """NULL tissue values -> NULL Tau (insufficient data)."""
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001", "ENSG00000002"],
        "tissue1": [10.0, 20.0],
        "tissue2": [None, 20.0],  # NULL for gene 1
        "tissue3": [10.0, 20.0],
        "tissue4": [10.0, 20.0],
    })

    tissue_cols = ["tissue1", "tissue2", "tissue3", "tissue4"]
    result = calculate_tau_specificity(df, tissue_cols)

    tau_values = result.select("tau_specificity").to_series().to_list()
    # Gene 1 has NULL tissue -> NULL Tau
    assert tau_values[0] is None
    # Gene 2 has complete data -> Tau should be valid
    assert tau_values[1] is not None


def test_enrichment_score_high():
    """High retina expression relative to global -> high enrichment."""
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001"],
        "hpa_retina_tpm": [50.0],
        "hpa_cerebellum_tpm": [40.0],
        "gtex_retina_tpm": [60.0],
        "hpa_testis_tpm": [5.0],
        "hpa_fallopian_tube_tpm": [5.0],
        "gtex_testis_tpm": [5.0],
        "cellxgene_photoreceptor_expr": [None],
        "cellxgene_hair_cell_expr": [None],
        "tau_specificity": [0.5],
    })

    result = compute_expression_score(df)

    # Usher tissues (retina, cerebellum) have much higher expression than global
    # Mean Usher: (50+40+60)/3 = 50
    # Mean global: (50+40+60+5+5+5)/6 = 27.5
    # Enrichment: 50/27.5 ≈ 1.82
    assert "usher_tissue_enrichment" in result.columns
    enrichment = result.select("usher_tissue_enrichment").item()
    assert enrichment > 1.5  # Significantly enriched


def test_enrichment_score_low():
    """No target tissue expression -> low enrichment."""
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001"],
        "hpa_retina_tpm": [5.0],
        "hpa_cerebellum_tpm": [5.0],
        "gtex_retina_tpm": [5.0],
        "hpa_testis_tpm": [50.0],
        "hpa_fallopian_tube_tpm": [50.0],
        "gtex_testis_tpm": [50.0],
        "cellxgene_photoreceptor_expr": [None],
        "cellxgene_hair_cell_expr": [None],
        "tau_specificity": [0.8],
    })

    result = compute_expression_score(df)

    enrichment = result.select("usher_tissue_enrichment").item()
    assert enrichment < 1.0  # Not enriched in Usher tissues


def test_expression_score_normalization():
    """Composite score should be in [0, 1] range."""
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001", "ENSG00000002", "ENSG00000003"],
        "hpa_retina_tpm": [50.0, 10.0, 5.0],
        "hpa_cerebellum_tpm": [40.0, 10.0, 5.0],
        "gtex_retina_tpm": [60.0, 10.0, 5.0],
        "hpa_testis_tpm": [5.0, 50.0, 50.0],
        "hpa_fallopian_tube_tpm": [5.0, 50.0, 50.0],
        "gtex_testis_tpm": [5.0, 50.0, 50.0],
        "cellxgene_photoreceptor_expr": [None, None, None],
        "cellxgene_hair_cell_expr": [None, None, None],
        "tau_specificity": [0.5, 0.3, 0.2],
    })

    result = compute_expression_score(df)

    scores = result.select("expression_score_normalized").to_series().to_list()
    for score in scores:
        if score is not None:
            assert 0.0 <= score <= 1.0, f"Score {score} out of range [0,1]"


def test_null_preservation_all_sources():
    """Gene with no data from any source -> NULL score."""
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001"],
        "hpa_retina_tpm": [None],
        "hpa_cerebellum_tpm": [None],
        "gtex_retina_tpm": [None],
        "hpa_testis_tpm": [None],
        "hpa_fallopian_tube_tpm": [None],
        "gtex_testis_tpm": [None],
        "cellxgene_photoreceptor_expr": [None],
        "cellxgene_hair_cell_expr": [None],
        "tau_specificity": [None],
    })

    result = compute_expression_score(df)

    # Both enrichment and score should be NULL
    enrichment = result.select("usher_tissue_enrichment").item()
    score = result.select("expression_score_normalized").item()
    assert enrichment is None
    assert score is None

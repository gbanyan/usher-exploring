"""Tests for validation modules (negative controls, recall@k, sensitivity, report)."""

import polars as pl
import pytest
from pathlib import Path

from usher_pipeline.persistence.duckdb_store import PipelineStore
from usher_pipeline.config.schema import ScoringWeights
from usher_pipeline.scoring import (
    compile_housekeeping_genes,
    validate_negative_controls,
    compute_recall_at_k,
    validate_positive_controls_extended,
)
from usher_pipeline.scoring.sensitivity import (
    perturb_weight,
    run_sensitivity_analysis,
    summarize_sensitivity,
)
from usher_pipeline.scoring.validation_report import (
    generate_comprehensive_validation_report,
    recommend_weight_tuning,
)


def create_synthetic_scored_db(tmp_path: Path) -> PipelineStore:
    """
    Create DuckDB with synthetic scored_genes for testing.

    Designs scores so:
    - Known cilia genes (MYO7A, IFT88, BBS1) get high scores (0.8-0.95)
    - Housekeeping genes (GAPDH, ACTB, RPL13A) get low scores (0.1-0.3)
    - Other genes get mid-range scores (0.3-0.6)

    Returns:
        PipelineStore with synthetic scored_genes table
    """
    db_path = tmp_path / "test.duckdb"
    store = PipelineStore(db_path)

    # Create gene_universe
    gene_symbols = [
        # Known cilia genes (high scores)
        "MYO7A", "IFT88", "BBS1",
        # Housekeeping genes (low scores)
        "GAPDH", "ACTB", "RPL13A",
        # Filler genes (mid scores)
        "GENE001", "GENE002", "GENE003", "GENE004", "GENE005",
        "GENE006", "GENE007", "GENE008", "GENE009", "GENE010",
        "GENE011", "GENE012", "GENE013", "GENE014",
    ]

    gene_universe = pl.DataFrame({
        "gene_id": [f"ENSG{i:011d}" for i in range(len(gene_symbols))],
        "gene_symbol": gene_symbols,
        "hgnc_id": [f"HGNC:{i+1000}" for i in range(len(gene_symbols))],
        "uniprot_primary": [f"P{i+10000}" for i in range(len(gene_symbols))],
    })

    store.conn.execute("CREATE TABLE gene_universe AS SELECT * FROM gene_universe")

    # Create scored_genes with designed scores
    scored_data = {
        "gene_id": gene_universe["gene_id"].to_list(),
        "gene_symbol": gene_symbols,
        # Design composite_score to ensure known genes high, housekeeping low
        "composite_score": [
            # Known cilia genes (indices 0-2): high scores
            0.90, 0.85, 0.92,
            # Housekeeping genes (indices 3-5): low scores
            0.15, 0.20, 0.12,
            # Filler genes: mid scores
            0.45, 0.50, 0.35, 0.55, 0.40,
            0.48, 0.52, 0.38, 0.42, 0.58,
            0.43, 0.47, 0.53, 0.41,
        ],
        # Layer scores (simplified - just use composite_score with small variations)
        "gnomad_score": [
            0.88, 0.83, 0.90,
            0.18, 0.22, 0.15,
            0.44, 0.49, 0.34, 0.54, 0.39,
            0.47, 0.51, 0.37, 0.41, 0.57,
            0.42, 0.46, 0.52, 0.40,
        ],
        "expression_score": [
            0.92, 0.87, 0.94,
            0.12, 0.18, 0.10,
            0.46, 0.51, 0.36, 0.56, 0.41,
            0.49, 0.53, 0.39, 0.43, 0.59,
            0.44, 0.48, 0.54, 0.42,
        ],
        "annotation_score": [
            0.90, 0.85, 0.92,
            0.15, 0.20, 0.12,
            0.45, 0.50, 0.35, 0.55, 0.40,
            0.48, 0.52, 0.38, 0.42, 0.58,
            0.43, 0.47, 0.53, 0.41,
        ],
        "localization_score": [
            0.91, 0.86, 0.93,
            0.14, 0.19, 0.11,
            0.45, 0.50, 0.35, 0.55, 0.40,
            0.48, 0.52, 0.38, 0.42, 0.58,
            0.43, 0.47, 0.53, 0.41,
        ],
        "animal_model_score": [
            0.89, 0.84, 0.91,
            0.16, 0.21, 0.13,
            0.45, 0.50, 0.35, 0.55, 0.40,
            0.48, 0.52, 0.38, 0.42, 0.58,
            0.43, 0.47, 0.53, 0.41,
        ],
        "literature_score": [
            0.90, 0.85, 0.92,
            0.15, 0.20, 0.12,
            0.45, 0.50, 0.35, 0.55, 0.40,
            0.48, 0.52, 0.38, 0.42, 0.58,
            0.43, 0.47, 0.53, 0.41,
        ],
        "evidence_count": [6] * len(gene_symbols),
        "quality_flag": ["sufficient_evidence"] * len(gene_symbols),
    }

    scored_df = pl.DataFrame(scored_data)
    store.conn.execute("CREATE TABLE scored_genes AS SELECT * FROM scored_df")

    # Create known_genes table
    known_genes = pl.DataFrame({
        "gene_symbol": ["MYO7A", "IFT88", "BBS1"],
        "source": ["omim_usher", "syscilia_scgs_v2", "syscilia_scgs_v2"],
        "confidence": ["HIGH", "HIGH", "HIGH"],
    })

    store.conn.execute("CREATE TABLE known_genes AS SELECT * FROM known_genes")

    return store


def test_compile_housekeeping_genes_structure():
    """Test compile_housekeeping_genes returns correct structure."""
    df = compile_housekeeping_genes()

    # Check columns
    assert "gene_symbol" in df.columns
    assert "source" in df.columns
    assert "confidence" in df.columns

    # Check row count
    assert df.height == 13, f"Expected 13 housekeeping genes, got {df.height}"

    # Check all are literature_validated
    assert df["source"].unique().to_list() == ["literature_validated"]

    # Check all are HIGH confidence
    assert df["confidence"].unique().to_list() == ["HIGH"]


def test_compile_housekeeping_genes_known_genes_present():
    """Test known housekeeping genes are present in compiled set."""
    df = compile_housekeeping_genes()

    gene_symbols = df["gene_symbol"].to_list()

    # Check for well-known housekeeping genes
    assert "GAPDH" in gene_symbols
    assert "ACTB" in gene_symbols
    assert "RPL13A" in gene_symbols
    assert "TBP" in gene_symbols


def test_validate_negative_controls_with_synthetic_data(tmp_path):
    """Test negative control validation with synthetic data where housekeeping genes rank low."""
    store = create_synthetic_scored_db(tmp_path)

    try:
        # Run negative control validation
        metrics = validate_negative_controls(store)

        # Should pass (housekeeping genes rank low in synthetic data)
        assert metrics["validation_passed"] is True, \
            f"Validation should pass with low housekeeping scores. Median: {metrics['median_percentile']}"

        # Median percentile should be < 0.5
        assert metrics["median_percentile"] < 0.5, \
            f"Housekeeping median percentile should be < 0.5, got {metrics['median_percentile']}"

        # Check found some housekeeping genes
        assert metrics["total_in_dataset"] > 0, "Should find at least one housekeeping gene"

    finally:
        store.close()


def test_validate_negative_controls_inverted_logic(tmp_path):
    """Test negative control validation fails when housekeeping genes rank HIGH."""
    db_path = tmp_path / "test_inverted.duckdb"
    store = PipelineStore(db_path)

    try:
        # Create gene_universe
        gene_symbols = ["GAPDH", "ACTB", "RPL13A", "GENE001", "GENE002"]
        gene_universe = pl.DataFrame({
            "gene_id": [f"ENSG{i:011d}" for i in range(len(gene_symbols))],
            "gene_symbol": gene_symbols,
            "hgnc_id": [f"HGNC:{i+1000}" for i in range(len(gene_symbols))],
            "uniprot_primary": [f"P{i+10000}" for i in range(len(gene_symbols))],
        })
        store.conn.execute("CREATE TABLE gene_universe AS SELECT * FROM gene_universe")

        # Create scored_genes where housekeeping genes rank HIGH (inverted)
        scored_df = pl.DataFrame({
            "gene_id": gene_universe["gene_id"].to_list(),
            "gene_symbol": gene_symbols,
            "composite_score": [0.90, 0.85, 0.88, 0.20, 0.15],  # Housekeeping HIGH
            "gnomad_score": [0.90, 0.85, 0.88, 0.20, 0.15],
            "expression_score": [0.90, 0.85, 0.88, 0.20, 0.15],
            "annotation_score": [0.90, 0.85, 0.88, 0.20, 0.15],
            "localization_score": [0.90, 0.85, 0.88, 0.20, 0.15],
            "animal_model_score": [0.90, 0.85, 0.88, 0.20, 0.15],
            "literature_score": [0.90, 0.85, 0.88, 0.20, 0.15],
            "evidence_count": [6] * len(gene_symbols),
            "quality_flag": ["sufficient_evidence"] * len(gene_symbols),
        })
        store.conn.execute("CREATE TABLE scored_genes AS SELECT * FROM scored_df")

        # Run negative control validation
        metrics = validate_negative_controls(store)

        # Should FAIL (housekeeping genes rank high)
        assert metrics["validation_passed"] is False, \
            "Validation should fail when housekeeping genes rank high"

        # Median percentile should be >= 0.5
        assert metrics["median_percentile"] >= 0.5, \
            f"Housekeeping median percentile should be >= 0.5, got {metrics['median_percentile']}"

    finally:
        store.close()


def test_compute_recall_at_k(tmp_path):
    """Test recall@k computation with synthetic data."""
    store = create_synthetic_scored_db(tmp_path)

    try:
        # Run recall@k
        metrics = compute_recall_at_k(store)

        # Check structure
        assert "recalls_absolute" in metrics
        assert "recalls_percentage" in metrics
        assert "total_known_unique" in metrics
        assert "total_scored" in metrics

        # Check absolute recalls
        assert 100 in metrics["recalls_absolute"]
        assert 500 in metrics["recalls_absolute"]

        # Check percentage recalls
        assert "5%" in metrics["recalls_percentage"]
        assert "10%" in metrics["recalls_percentage"]

        # Note: compile_known_genes() returns all 38 known genes (OMIM + SYSCILIA),
        # but our synthetic DB only has 3 of them (MYO7A, IFT88, BBS1).
        # So total_known_unique is 38, but only 3 are in dataset.
        total_known = metrics["total_known_unique"]
        assert total_known == 38, f"Expected 38 known genes from compile_known_genes(), got {total_known}"

        # All 3 genes in dataset have high scores, so recall should be 3/38 = 0.0789
        recall_at_100 = metrics["recalls_absolute"].get(100, 0.0)
        expected_recall = 3.0 / 38.0
        assert abs(recall_at_100 - expected_recall) < 0.01, \
            f"Recall@100 should be {expected_recall:.4f} (3/38), got {recall_at_100:.4f}"

    finally:
        store.close()


def test_perturb_weight_renormalizes():
    """Test weight perturbation maintains sum=1.0."""
    baseline = ScoringWeights()  # Default weights

    # Perturb gnomad by +0.10
    perturbed = perturb_weight(baseline, "gnomad", 0.10)

    # Check weights sum to 1.0 (within tolerance)
    weight_sum = (
        perturbed.gnomad +
        perturbed.expression +
        perturbed.annotation +
        perturbed.localization +
        perturbed.animal_model +
        perturbed.literature
    )

    assert abs(weight_sum - 1.0) < 1e-6, f"Weights should sum to 1.0, got {weight_sum}"

    # Check gnomad increased relative to baseline
    assert perturbed.gnomad > baseline.gnomad, \
        f"Perturbed gnomad ({perturbed.gnomad}) should be > baseline ({baseline.gnomad})"


def test_perturb_weight_large_negative():
    """Test weight perturbation with large negative delta (edge case)."""
    baseline = ScoringWeights()

    # Perturb by -0.25 (more than most weight values)
    perturbed = perturb_weight(baseline, "gnomad", -0.25)

    # Check weight is >= 0.0 (clamped)
    assert perturbed.gnomad >= 0.0, f"Weight should be >= 0.0, got {perturbed.gnomad}"

    # Check weights still sum to 1.0
    weight_sum = (
        perturbed.gnomad +
        perturbed.expression +
        perturbed.annotation +
        perturbed.localization +
        perturbed.animal_model +
        perturbed.literature
    )

    assert abs(weight_sum - 1.0) < 1e-6, f"Weights should sum to 1.0, got {weight_sum}"


def test_perturb_weight_invalid_layer():
    """Test perturb_weight raises ValueError for invalid layer."""
    baseline = ScoringWeights()

    with pytest.raises(ValueError, match="Invalid layer"):
        perturb_weight(baseline, "nonexistent", 0.05)


def test_generate_comprehensive_validation_report_format():
    """Test comprehensive validation report contains expected sections."""
    # Create mock metrics
    positive_metrics = {
        "validation_passed": True,
        "total_known_expected": 38,
        "total_known_in_dataset": 35,
        "median_percentile": 0.85,
        "top_quartile_count": 30,
        "top_quartile_fraction": 0.86,
        "recall_at_k": {
            "recalls_absolute": {100: 0.90, 500: 0.95},
            "recalls_percentage": {"5%": 0.85, "10%": 0.92},
            "total_known_unique": 35,
            "total_scored": 20000,
        },
        "per_source_breakdown": {
            "omim_usher": {"median_percentile": 0.88, "count": 10, "top_quartile_count": 9},
            "syscilia_scgs_v2": {"median_percentile": 0.83, "count": 25, "top_quartile_count": 21},
        },
    }

    negative_metrics = {
        "validation_passed": True,
        "total_expected": 13,
        "total_in_dataset": 13,
        "median_percentile": 0.35,
        "top_quartile_count": 1,
        "in_high_tier_count": 0,
    }

    sensitivity_result = {
        "baseline_weights": ScoringWeights().model_dump(),
        "results": [
            {
                "layer": "gnomad",
                "delta": 0.05,
                "perturbed_weights": {},
                "spearman_rho": 0.92,
                "spearman_pval": 1e-10,
                "overlap_count": 95,
                "top_n": 100,
            }
        ],
        "top_n": 100,
        "total_perturbations": 1,
    }

    sensitivity_summary = {
        "min_rho": 0.92,
        "max_rho": 0.92,
        "mean_rho": 0.92,
        "stable_count": 1,
        "unstable_count": 0,
        "total_perturbations": 1,
        "overall_stable": True,
        "most_sensitive_layer": "gnomad",
        "most_robust_layer": "literature",
    }

    # Generate report
    report = generate_comprehensive_validation_report(
        positive_metrics,
        negative_metrics,
        sensitivity_result,
        sensitivity_summary,
    )

    # Check report contains expected sections
    assert "Positive Control Validation" in report
    assert "Negative Control Validation" in report
    assert "Sensitivity Analysis" in report
    assert "Overall Validation Summary" in report
    assert "Weight Tuning Recommendations" in report

    # Check status appears
    assert "PASSED" in report


def test_recommend_weight_tuning_all_pass():
    """Test weight tuning recommendations when all validations pass."""
    positive_metrics = {"validation_passed": True}
    negative_metrics = {"validation_passed": True}
    sensitivity_summary = {"overall_stable": True}

    recommendation = recommend_weight_tuning(
        positive_metrics,
        negative_metrics,
        sensitivity_summary,
    )

    # Should recommend no tuning
    assert "No tuning recommended" in recommendation or "validated" in recommendation.lower()


def test_recommend_weight_tuning_positive_fail():
    """Test weight tuning recommendations when positive controls fail."""
    positive_metrics = {"validation_passed": False}
    negative_metrics = {"validation_passed": True}
    sensitivity_summary = {"overall_stable": True}

    recommendation = recommend_weight_tuning(
        positive_metrics,
        negative_metrics,
        sensitivity_summary,
    )

    # Should suggest increasing weights for layers where known genes score high
    assert "Known Gene Ranking Issue" in recommendation or "Positive Control" in recommendation


def test_recommend_weight_tuning_negative_fail():
    """Test weight tuning recommendations when negative controls fail."""
    positive_metrics = {"validation_passed": True}
    negative_metrics = {"validation_passed": False}
    sensitivity_summary = {"overall_stable": True}

    recommendation = recommend_weight_tuning(
        positive_metrics,
        negative_metrics,
        sensitivity_summary,
    )

    # Should suggest examining layers boosting housekeeping genes
    assert "Housekeeping" in recommendation or "Negative Control" in recommendation


def test_recommend_weight_tuning_sensitivity_fail():
    """Test weight tuning recommendations when sensitivity unstable."""
    positive_metrics = {"validation_passed": True}
    negative_metrics = {"validation_passed": True}
    sensitivity_summary = {
        "overall_stable": False,
        "unstable_count": 5,
        "most_sensitive_layer": "gnomad",
    }

    recommendation = recommend_weight_tuning(
        positive_metrics,
        negative_metrics,
        sensitivity_summary,
    )

    # Should suggest reducing weight of most sensitive layer
    assert "Sensitivity" in recommendation or "gnomad" in recommendation

"""Tests for visualization generation."""

from pathlib import Path

import polars as pl
import pytest

from usher_pipeline.output.visualizations import (
    generate_all_plots,
    plot_layer_contributions,
    plot_score_distribution,
    plot_tier_breakdown,
)


@pytest.fixture
def synthetic_results_df():
    """Create synthetic scored results DataFrame."""
    return pl.DataFrame({
        "gene_symbol": [f"GENE{i}" for i in range(30)],
        "composite_score": [0.1 + i * 0.03 for i in range(30)],
        "confidence_tier": (
            ["HIGH"] * 10 + ["MEDIUM"] * 10 + ["LOW"] * 10
        ),
        "gnomad_score": [0.5 if i % 2 == 0 else None for i in range(30)],
        "expression_score": [0.6 if i % 3 == 0 else None for i in range(30)],
        "annotation_score": [0.7 if i % 4 == 0 else None for i in range(30)],
        "localization_score": [0.8 if i % 5 == 0 else None for i in range(30)],
        "animal_model_score": [0.9 if i % 6 == 0 else None for i in range(30)],
        "literature_score": [0.85 if i % 7 == 0 else None for i in range(30)],
    })


def test_plot_score_distribution_creates_file(synthetic_results_df, tmp_path):
    """Test that score distribution plot creates a PNG file."""
    output_path = tmp_path / "score_dist.png"

    result = plot_score_distribution(synthetic_results_df, output_path)

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_plot_layer_contributions_creates_file(synthetic_results_df, tmp_path):
    """Test that layer contributions plot creates a PNG file."""
    output_path = tmp_path / "layer_contrib.png"

    result = plot_layer_contributions(synthetic_results_df, output_path)

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_plot_tier_breakdown_creates_file(synthetic_results_df, tmp_path):
    """Test that tier breakdown plot creates a PNG file."""
    output_path = tmp_path / "tier_breakdown.png"

    result = plot_tier_breakdown(synthetic_results_df, output_path)

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_generate_all_plots_creates_all_files(synthetic_results_df, tmp_path):
    """Test that generate_all_plots creates all 3 PNG files."""
    output_dir = tmp_path / "plots"

    plots = generate_all_plots(synthetic_results_df, output_dir)

    # Check all files exist
    assert (output_dir / "score_distribution.png").exists()
    assert (output_dir / "layer_contributions.png").exists()
    assert (output_dir / "tier_breakdown.png").exists()


def test_generate_all_plots_returns_paths(synthetic_results_df, tmp_path):
    """Test that generate_all_plots returns dict with 3 entries."""
    output_dir = tmp_path / "plots"

    plots = generate_all_plots(synthetic_results_df, output_dir)

    assert len(plots) == 3
    assert "score_distribution" in plots
    assert "layer_contributions" in plots
    assert "tier_breakdown" in plots


def test_plots_handle_empty_dataframe(tmp_path):
    """Test that plots handle empty DataFrames without crashing."""
    empty_df = pl.DataFrame({
        "gene_symbol": [],
        "composite_score": [],
        "confidence_tier": [],
        "gnomad_score": [],
        "expression_score": [],
        "annotation_score": [],
        "localization_score": [],
        "animal_model_score": [],
        "literature_score": [],
    })

    output_dir = tmp_path / "empty_plots"

    # Should not crash
    plots = generate_all_plots(empty_df, output_dir)

    # At minimum, the function should return without error
    # Some plots may succeed (empty plot) or fail gracefully
    assert isinstance(plots, dict)

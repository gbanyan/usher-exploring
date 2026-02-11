"""Tests for reproducibility report generation."""

import json
from pathlib import Path

import polars as pl
import pytest

from usher_pipeline.config.schema import (
    APIConfig,
    DataSourceVersions,
    PipelineConfig,
    ScoringWeights,
)
from usher_pipeline.output.reproducibility import generate_reproducibility_report
from usher_pipeline.persistence.provenance import ProvenanceTracker


@pytest.fixture
def mock_config(tmp_path):
    """Create mock pipeline configuration."""
    return PipelineConfig(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        duckdb_path=tmp_path / "pipeline.db",
        versions=DataSourceVersions(
            ensembl_release=113,
            gnomad_version="v4.1",
            gtex_version="v8",
            hpa_version="23.0",
        ),
        api=APIConfig(),
        scoring=ScoringWeights(
            gnomad=0.20,
            expression=0.20,
            annotation=0.15,
            localization=0.15,
            animal_model=0.15,
            literature=0.15,
        ),
    )


@pytest.fixture
def mock_provenance(mock_config):
    """Create mock provenance tracker."""
    provenance = ProvenanceTracker(
        pipeline_version="0.1.0",
        config=mock_config,
    )

    # Record some processing steps
    provenance.record_step(
        "gene_universe_fetch",
        details={
            "input_count": 0,
            "output_count": 20000,
            "criteria": "Human protein-coding genes from Ensembl",
        },
    )

    provenance.record_step(
        "gnomad_filtering",
        details={
            "input_count": 20000,
            "output_count": 19500,
            "criteria": "Remove genes with quality flags",
        },
    )

    return provenance


@pytest.fixture
def synthetic_tiered_df():
    """Create synthetic tiered DataFrame."""
    return pl.DataFrame({
        "gene_id": [f"ENSG{i:011d}" for i in range(100)],
        "gene_symbol": [f"GENE{i}" for i in range(100)],
        "composite_score": [0.1 + i * 0.008 for i in range(100)],
        "confidence_tier": (
            ["HIGH"] * 30 + ["MEDIUM"] * 40 + ["LOW"] * 30
        ),
    })


def test_generate_report_has_all_fields(
    mock_config, mock_provenance, synthetic_tiered_df
):
    """Test that report contains all required fields."""
    report = generate_reproducibility_report(
        config=mock_config,
        tiered_df=synthetic_tiered_df,
        provenance=mock_provenance,
        validation_result=None,
    )

    # Check all required fields exist
    assert report.run_id is not None
    assert report.timestamp is not None
    assert report.pipeline_version == "0.1.0"
    assert report.parameters is not None
    assert report.data_versions is not None
    assert report.software_environment is not None
    assert report.tier_statistics is not None


def test_report_to_json_parseable(
    mock_config, mock_provenance, synthetic_tiered_df, tmp_path
):
    """Test that JSON output is valid and parseable."""
    report = generate_reproducibility_report(
        config=mock_config,
        tiered_df=synthetic_tiered_df,
        provenance=mock_provenance,
    )

    json_path = tmp_path / "report.json"
    report.to_json(json_path)

    # Read back and verify it's valid JSON
    with open(json_path) as f:
        data = json.load(f)

    # Verify expected keys
    assert "run_id" in data
    assert "timestamp" in data
    assert "pipeline_version" in data
    assert "parameters" in data
    assert "data_versions" in data
    assert "software_environment" in data
    assert "filtering_steps" in data
    assert "tier_statistics" in data


def test_report_to_markdown_has_headers(
    mock_config, mock_provenance, synthetic_tiered_df, tmp_path
):
    """Test that Markdown output contains required sections."""
    report = generate_reproducibility_report(
        config=mock_config,
        tiered_df=synthetic_tiered_df,
        provenance=mock_provenance,
    )

    md_path = tmp_path / "report.md"
    report.to_markdown(md_path)

    # Read content
    content = md_path.read_text()

    # Verify headers
    assert "# Pipeline Reproducibility Report" in content
    assert "## Parameters" in content
    assert "## Data Versions" in content
    assert "## Filtering Steps" in content
    assert "## Tier Statistics" in content
    assert "## Software Environment" in content


def test_report_tier_statistics_match(
    mock_config, mock_provenance, synthetic_tiered_df
):
    """Test that tier statistics match DataFrame counts."""
    report = generate_reproducibility_report(
        config=mock_config,
        tiered_df=synthetic_tiered_df,
        provenance=mock_provenance,
    )

    # Verify total matches
    assert report.tier_statistics["total"] == synthetic_tiered_df.height

    # Verify tier counts
    assert report.tier_statistics["high"] == 30
    assert report.tier_statistics["medium"] == 40
    assert report.tier_statistics["low"] == 30

    # Verify sum
    tier_sum = (
        report.tier_statistics["high"]
        + report.tier_statistics["medium"]
        + report.tier_statistics["low"]
    )
    assert tier_sum == report.tier_statistics["total"]


def test_report_includes_validation_when_provided(
    mock_config, mock_provenance, synthetic_tiered_df
):
    """Test that validation metrics are included when provided."""
    validation_result = {
        "median_percentile": 0.85,
        "top_quartile_fraction": 0.92,
        "validation_passed": True,
    }

    report = generate_reproducibility_report(
        config=mock_config,
        tiered_df=synthetic_tiered_df,
        provenance=mock_provenance,
        validation_result=validation_result,
    )

    # Verify validation metrics are present
    assert "median_percentile" in report.validation_metrics
    assert report.validation_metrics["median_percentile"] == 0.85
    assert report.validation_metrics["top_quartile_fraction"] == 0.92
    assert report.validation_metrics["validation_passed"] is True


def test_report_without_validation(
    mock_config, mock_provenance, synthetic_tiered_df
):
    """Test that report generates without error when validation_result is None."""
    report = generate_reproducibility_report(
        config=mock_config,
        tiered_df=synthetic_tiered_df,
        provenance=mock_provenance,
        validation_result=None,
    )

    # Should have empty validation metrics
    assert report.validation_metrics == {}


def test_report_software_versions(
    mock_config, mock_provenance, synthetic_tiered_df
):
    """Test that software environment contains expected keys."""
    report = generate_reproducibility_report(
        config=mock_config,
        tiered_df=synthetic_tiered_df,
        provenance=mock_provenance,
    )

    # Verify software versions are captured
    assert "python" in report.software_environment
    assert "polars" in report.software_environment
    assert "duckdb" in report.software_environment

    # Verify they're not empty
    assert report.software_environment["python"] != ""
    assert report.software_environment["polars"] != ""
    assert report.software_environment["duckdb"] != ""

"""Unit tests for gnomAD constraint evidence layer."""

from pathlib import Path
from unittest.mock import Mock, patch

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from usher_pipeline.evidence.gnomad.models import ConstraintRecord
from usher_pipeline.evidence.gnomad.fetch import download_constraint_metrics, parse_constraint_tsv
from usher_pipeline.evidence.gnomad.transform import (
    filter_by_coverage,
    normalize_scores,
    process_gnomad_constraint,
)


@pytest.fixture
def sample_constraint_tsv(tmp_path: Path) -> Path:
    """Create a sample gnomAD constraint TSV for testing.

    Covers edge cases:
    - Normal genes with good coverage (measured)
    - Low depth genes (<30x)
    - Low CDS coverage genes (<90%)
    - NULL LOEUF/pLI (no_data)
    - Extreme LOEUF values for normalization bounds
    """
    tsv_path = tmp_path / "constraint.tsv"

    # Use gnomAD v4.x-style column names
    content = """gene\ttranscript\tgene_symbol\tlof.pLI\tlof.oe_ci.upper\tmean_coverage\tmean_proportion_covered
ENSG00000001\tENST00000001\tGENE1\t0.95\t0.15\t45.0\t0.98
ENSG00000002\tENST00000002\tGENE2\t0.80\t0.85\t50.0\t0.95
ENSG00000003\tENST00000003\tGENE3\t0.10\t2.50\t40.0\t0.92
ENSG00000004\tENST00000004\tGENE4\t0.50\t0.0\t55.0\t0.97
ENSG00000005\tENST00000005\tGENE5\t0.20\t1.20\t25.0\t0.85
ENSG00000006\tENST00000006\tGENE6\t0.70\t0.45\t35.0\t0.75
ENSG00000007\tENST00000007\tGENE7\tNA\tNA\t60.0\t0.99
ENSG00000008\tENST00000008\tGENE8\t0.60\t0.30\t50.0\t0.90
ENSG00000009\tENST00000009\tGENE9\t.\t.\t.\t.
ENSG00000010\tENST00000010\tGENE10\t0.90\t0.18\t48.0\t0.94
ENSG00000011\tENST00000011\tGENE11\t0.15\t1.80\t32.0\t0.91
ENSG00000012\tENST00000012\tGENE12\t0.85\t0.22\t10.0\t0.50
ENSG00000013\tENST00000013\tGENE13\t0.40\t0.65\t38.0\t0.88
ENSG00000014\tENST00000014\tGENE14\tNA\t0.75\t42.0\t0.93
ENSG00000015\tENST00000015\tGENE15\t0.75\tNA\t47.0\t0.96
"""

    tsv_path.write_text(content)
    return tsv_path


def test_parse_constraint_tsv_returns_lazyframe(sample_constraint_tsv: Path):
    """Verify parse returns LazyFrame with expected columns."""
    lf = parse_constraint_tsv(sample_constraint_tsv)

    assert isinstance(lf, pl.LazyFrame)

    # Collect to check columns
    df = lf.collect()
    expected_columns = {"gene_id", "gene_symbol", "transcript", "pli", "loeuf", "mean_depth", "cds_covered_pct"}
    assert expected_columns.issubset(set(df.columns))


def test_parse_constraint_tsv_null_handling(sample_constraint_tsv: Path):
    """NA/empty values become polars null, not zero."""
    lf = parse_constraint_tsv(sample_constraint_tsv)
    df = lf.collect()

    # GENE7 has "NA" for pli and loeuf
    gene7 = df.filter(pl.col("gene_symbol") == "GENE7")
    assert gene7["pli"][0] is None
    assert gene7["loeuf"][0] is None

    # GENE9 has "." for all values
    gene9 = df.filter(pl.col("gene_symbol") == "GENE9")
    assert gene9["pli"][0] is None
    assert gene9["loeuf"][0] is None
    assert gene9["mean_depth"][0] is None


def test_filter_by_coverage_measured(sample_constraint_tsv: Path):
    """Good coverage genes get quality_flag="measured"."""
    lf = parse_constraint_tsv(sample_constraint_tsv)
    lf = filter_by_coverage(lf, min_depth=30.0, min_cds_pct=0.9)
    df = lf.collect()

    # GENE1: depth=45, coverage=0.98, has LOEUF -> measured
    gene1 = df.filter(pl.col("gene_symbol") == "GENE1")
    assert gene1["quality_flag"][0] == "measured"

    # GENE8: depth=50, coverage=0.90 (exactly at threshold), has LOEUF -> measured
    gene8 = df.filter(pl.col("gene_symbol") == "GENE8")
    assert gene8["quality_flag"][0] == "measured"


def test_filter_by_coverage_incomplete(sample_constraint_tsv: Path):
    """Low depth/CDS genes get quality_flag="incomplete_coverage"."""
    lf = parse_constraint_tsv(sample_constraint_tsv)
    lf = filter_by_coverage(lf, min_depth=30.0, min_cds_pct=0.9)
    df = lf.collect()

    # GENE5: depth=25 (< 30) -> incomplete_coverage
    gene5 = df.filter(pl.col("gene_symbol") == "GENE5")
    assert gene5["quality_flag"][0] == "incomplete_coverage"

    # GENE6: coverage=0.75 (< 0.9) -> incomplete_coverage
    gene6 = df.filter(pl.col("gene_symbol") == "GENE6")
    assert gene6["quality_flag"][0] == "incomplete_coverage"

    # GENE12: depth=10 (very low) -> incomplete_coverage
    gene12 = df.filter(pl.col("gene_symbol") == "GENE12")
    assert gene12["quality_flag"][0] == "incomplete_coverage"


def test_filter_by_coverage_no_data(sample_constraint_tsv: Path):
    """NULL loeuf+pli genes get quality_flag="no_data"."""
    lf = parse_constraint_tsv(sample_constraint_tsv)
    lf = filter_by_coverage(lf, min_depth=30.0, min_cds_pct=0.9)
    df = lf.collect()

    # GENE7: both pli and loeuf are NULL -> no_data
    gene7 = df.filter(pl.col("gene_symbol") == "GENE7")
    assert gene7["quality_flag"][0] == "no_data"

    # GENE9: both pli and loeuf are NULL -> no_data
    gene9 = df.filter(pl.col("gene_symbol") == "GENE9")
    assert gene9["quality_flag"][0] == "no_data"


def test_filter_preserves_all_genes(sample_constraint_tsv: Path):
    """Row count before == row count after (no genes dropped)."""
    lf = parse_constraint_tsv(sample_constraint_tsv)
    df_before = lf.collect()
    count_before = len(df_before)

    lf = filter_by_coverage(lf, min_depth=30.0, min_cds_pct=0.9)
    df_after = lf.collect()
    count_after = len(df_after)

    assert count_before == count_after, "Filter should preserve all genes"


def test_normalize_scores_range(sample_constraint_tsv: Path):
    """All non-null normalized scores are in [0, 1]."""
    lf = parse_constraint_tsv(sample_constraint_tsv)
    lf = filter_by_coverage(lf, min_depth=30.0, min_cds_pct=0.9)
    lf = normalize_scores(lf)
    df = lf.collect()

    # Filter to non-null normalized scores
    normalized = df.filter(pl.col("loeuf_normalized").is_not_null())

    if len(normalized) > 0:
        min_score = normalized["loeuf_normalized"].min()
        max_score = normalized["loeuf_normalized"].max()

        assert min_score >= 0.0, f"Min normalized score {min_score} < 0"
        assert max_score <= 1.0, f"Max normalized score {max_score} > 1"


def test_normalize_scores_inversion(sample_constraint_tsv: Path):
    """Lower LOEUF -> higher normalized score."""
    lf = parse_constraint_tsv(sample_constraint_tsv)
    lf = filter_by_coverage(lf, min_depth=30.0, min_cds_pct=0.9)
    lf = normalize_scores(lf)
    df = lf.collect()

    # GENE4: LOEUF=0.0 (most constrained) should have highest normalized score
    gene4 = df.filter(pl.col("gene_symbol") == "GENE4")
    if gene4["quality_flag"][0] == "measured":
        assert gene4["loeuf_normalized"][0] is not None
        # Should be close to 1.0 (most constrained)
        assert gene4["loeuf_normalized"][0] >= 0.95

    # GENE3: LOEUF=2.50 (least constrained) should have lowest normalized score
    gene3 = df.filter(pl.col("gene_symbol") == "GENE3")
    if gene3["quality_flag"][0] == "measured":
        assert gene3["loeuf_normalized"][0] is not None
        # Should be close to 0.0 (least constrained)
        assert gene3["loeuf_normalized"][0] <= 0.05


def test_normalize_scores_null_preserved(sample_constraint_tsv: Path):
    """NULL loeuf stays NULL after normalization."""
    lf = parse_constraint_tsv(sample_constraint_tsv)
    lf = filter_by_coverage(lf, min_depth=30.0, min_cds_pct=0.9)
    lf = normalize_scores(lf)
    df = lf.collect()

    # GENE7: NULL loeuf -> NULL normalized
    gene7 = df.filter(pl.col("gene_symbol") == "GENE7")
    assert gene7["loeuf"][0] is None
    assert gene7["loeuf_normalized"][0] is None


def test_normalize_scores_incomplete_stays_null(sample_constraint_tsv: Path):
    """incomplete_coverage genes get NULL normalized score."""
    lf = parse_constraint_tsv(sample_constraint_tsv)
    lf = filter_by_coverage(lf, min_depth=30.0, min_cds_pct=0.9)
    lf = normalize_scores(lf)
    df = lf.collect()

    # GENE5: incomplete_coverage -> NULL normalized
    gene5 = df.filter(pl.col("gene_symbol") == "GENE5")
    assert gene5["quality_flag"][0] == "incomplete_coverage"
    assert gene5["loeuf_normalized"][0] is None

    # GENE6: incomplete_coverage -> NULL normalized
    gene6 = df.filter(pl.col("gene_symbol") == "GENE6")
    assert gene6["quality_flag"][0] == "incomplete_coverage"
    assert gene6["loeuf_normalized"][0] is None


def test_process_gnomad_constraint_end_to_end(sample_constraint_tsv: Path):
    """Full pipeline returns DataFrame with all expected columns."""
    df = process_gnomad_constraint(sample_constraint_tsv, min_depth=30.0, min_cds_pct=0.9)

    # Check it's a materialized DataFrame
    assert isinstance(df, pl.DataFrame)

    # Check all expected columns exist
    expected_columns = {
        "gene_id",
        "gene_symbol",
        "transcript",
        "pli",
        "loeuf",
        "mean_depth",
        "cds_covered_pct",
        "quality_flag",
        "loeuf_normalized",
    }
    assert expected_columns.issubset(set(df.columns))

    # Check we have genes in each category
    measured_count = df.filter(pl.col("quality_flag") == "measured").height
    incomplete_count = df.filter(pl.col("quality_flag") == "incomplete_coverage").height
    no_data_count = df.filter(pl.col("quality_flag") == "no_data").height

    assert measured_count > 0, "Should have some measured genes"
    assert incomplete_count > 0, "Should have some incomplete_coverage genes"
    assert no_data_count > 0, "Should have some no_data genes"


def test_constraint_record_model_validation():
    """ConstraintRecord validates correctly, rejects bad types."""
    # Valid record
    valid = ConstraintRecord(
        gene_id="ENSG00000001",
        gene_symbol="GENE1",
        transcript="ENST00000001",
        pli=0.95,
        loeuf=0.15,
        loeuf_upper=0.20,
        mean_depth=45.0,
        cds_covered_pct=0.98,
        quality_flag="measured",
        loeuf_normalized=0.85,
    )
    assert valid.gene_id == "ENSG00000001"
    assert valid.loeuf_normalized == 0.85

    # NULL values are OK
    with_nulls = ConstraintRecord(
        gene_id="ENSG00000002",
        gene_symbol="GENE2",
        transcript="ENST00000002",
        pli=None,
        loeuf=None,
        quality_flag="no_data",
        loeuf_normalized=None,
    )
    assert with_nulls.pli is None
    assert with_nulls.loeuf is None
    assert with_nulls.loeuf_normalized is None

    # Invalid type should raise ValidationError
    with pytest.raises(Exception):  # Pydantic ValidationError
        ConstraintRecord(
            gene_id=12345,  # Should be string
            gene_symbol="GENE3",
            transcript="ENST00000003",
        )


@patch("usher_pipeline.evidence.gnomad.fetch.httpx.stream")
def test_download_skips_if_exists(mock_stream: Mock, tmp_path: Path):
    """download_constraint_metrics returns early if file exists and force=False."""
    output_path = tmp_path / "constraint.tsv"

    # Create existing file
    output_path.write_text("gene\ttranscript\npli\tloeuf\n")

    # Call download with force=False
    result = download_constraint_metrics(output_path, force=False)

    # Should return early without making HTTP request
    assert result == output_path
    mock_stream.assert_not_called()


@patch("usher_pipeline.evidence.gnomad.fetch.httpx.stream")
def test_download_forces_redownload(mock_stream: Mock, tmp_path: Path):
    """download_constraint_metrics re-downloads when force=True."""
    output_path = tmp_path / "constraint.tsv"

    # Create existing file
    output_path.write_text("old content")

    # Mock HTTP response
    mock_response = Mock()
    mock_response.headers = {"content-length": "100"}
    mock_response.iter_bytes = Mock(return_value=[b"gene\ttranscript\n", b"data\n"])
    mock_response.raise_for_status = Mock()
    mock_stream.return_value.__enter__.return_value = mock_response

    # Call download with force=True
    result = download_constraint_metrics(output_path, force=True)

    # Should make HTTP request
    assert result == output_path
    mock_stream.assert_called_once()


def test_filter_by_coverage_handles_missing_columns(tmp_path: Path):
    """filter_by_coverage handles genes with missing mean_depth or cds_covered_pct."""
    tsv_path = tmp_path / "partial.tsv"
    content = """gene\ttranscript\tgene_symbol\tlof.pLI\tlof.oe_ci.upper\tmean_coverage\tmean_proportion_covered
ENSG00000001\tENST00000001\tGENE1\t0.95\t0.15\t.\t.
"""
    tsv_path.write_text(content)

    lf = parse_constraint_tsv(tsv_path)
    lf = filter_by_coverage(lf, min_depth=30.0, min_cds_pct=0.9)
    df = lf.collect()

    # GENE1 has NULL depth/coverage but has LOEUF -> should be incomplete_coverage
    gene1 = df.filter(pl.col("gene_symbol") == "GENE1")
    # With NULL depth/coverage, comparisons will be false, so it goes to incomplete_coverage
    assert gene1["quality_flag"][0] in ["incomplete_coverage", "no_data"]

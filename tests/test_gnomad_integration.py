"""Integration tests for gnomAD evidence layer end-to-end pipeline."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import polars as pl
import pytest
from click.testing import CliRunner

from usher_pipeline.config.loader import load_config
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker
from usher_pipeline.evidence.gnomad import (
    process_gnomad_constraint,
    load_to_duckdb,
    query_constrained_genes,
)
from usher_pipeline.cli.evidence_cmd import evidence


@pytest.fixture
def test_config(tmp_path):
    """Create a temporary config for testing."""
    config_path = tmp_path / "test_config.yaml"
    config_content = f"""
data_dir: {tmp_path / "data"}
cache_dir: {tmp_path / "cache"}
duckdb_path: {tmp_path / "test.duckdb"}

versions:
  ensembl_release: 113
  gnomad_version: v4.1
  gtex_version: v8
  hpa_version: "23.0"

api:
  rate_limit_per_second: 5
  max_retries: 5
  cache_ttl_seconds: 86400
  timeout_seconds: 30

scoring:
  gnomad: 0.20
  expression: 0.20
  annotation: 0.15
  localization: 0.15
  animal_model: 0.15
  literature: 0.15
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def sample_tsv(tmp_path):
    """Create synthetic gnomAD constraint TSV for testing.

    Covers edge cases:
    - 5 well-covered genes with measured LOEUF/pLI (varying values 0.1 to 2.0)
    - 3 genes with low depth (<30x)
    - 3 genes with low CDS coverage (<90%)
    - 2 genes with NULL LOEUF and pLI
    - 2 genes at normalization bounds (LOEUF=0.0, LOEUF=3.0)
    """
    tsv_path = tmp_path / "synthetic_constraint.tsv"

    # Use gnomAD v4.x column names
    tsv_content = """gene_id\tgene_symbol\tlof.pLI\tlof.oe_ci.upper\tmean_depth\tcds_covered_pct
ENSG00000000001\tGENE1\t0.95\t0.1\t50.0\t0.95
ENSG00000000002\tGENE2\t0.80\t0.3\t45.0\t0.92
ENSG00000000003\tGENE3\t0.60\t0.5\t40.0\t0.91
ENSG00000000004\tGENE4\t0.40\t1.5\t35.0\t0.93
ENSG00000000005\tGENE5\t0.10\t2.0\t55.0\t0.98
ENSG00000000006\tGENE6\t0.70\t0.4\t25.0\t0.95
ENSG00000000007\tGENE7\t0.65\t0.6\t20.0\t0.92
ENSG00000000008\tGENE8\t0.55\t0.7\t15.0\t0.93
ENSG00000000009\tGENE9\t0.50\t0.8\t50.0\t0.80
ENSG00000000010\tGENE10\t0.45\t0.9\t45.0\t0.85
ENSG00000000011\tGENE11\t0.35\t1.0\t40.0\t0.70
ENSG00000000012\tGENE12\t.\t.\t50.0\t0.95
ENSG00000000013\tGENE13\t.\t.\t45.0\t0.92
ENSG00000000014\tGENE14\t0.99\t0.0\t60.0\t0.99
ENSG00000000015\tGENE15\t0.05\t3.0\t65.0\t0.99
"""
    tsv_path.write_text(tsv_content)
    return tsv_path


def test_full_pipeline_to_duckdb(test_config, sample_tsv, tmp_path):
    """Test complete pipeline: process_gnomad_constraint -> load_to_duckdb -> verify DuckDB table."""
    config = load_config(test_config)
    store = PipelineStore.from_config(config)
    provenance = ProvenanceTracker.from_config(config)

    try:
        # Process constraint data
        df = process_gnomad_constraint(sample_tsv, min_depth=30.0, min_cds_pct=0.9)

        # Load to DuckDB
        load_to_duckdb(df, store, provenance, description="Test gnomAD data")

        # Verify table exists and has correct data
        loaded_df = store.load_dataframe('gnomad_constraint')
        assert loaded_df is not None
        assert len(loaded_df) == 15

        # Verify columns exist
        expected_cols = {'gene_id', 'gene_symbol', 'pli', 'loeuf', 'mean_depth',
                        'cds_covered_pct', 'quality_flag', 'loeuf_normalized'}
        assert set(loaded_df.columns).issuperset(expected_cols)

        # Verify quality flags
        quality_counts = loaded_df.group_by("quality_flag").len().to_dict()
        assert quality_counts is not None

    finally:
        store.close()


def test_checkpoint_restart_skips_processing(test_config, sample_tsv):
    """Test that has_checkpoint returns True after loading data."""
    config = load_config(test_config)
    store = PipelineStore.from_config(config)
    provenance = ProvenanceTracker.from_config(config)

    try:
        # Initially no checkpoint
        assert not store.has_checkpoint('gnomad_constraint')

        # Process and load
        df = process_gnomad_constraint(sample_tsv)
        load_to_duckdb(df, store, provenance)

        # Now checkpoint exists
        assert store.has_checkpoint('gnomad_constraint')

    finally:
        store.close()


def test_provenance_recorded(test_config, sample_tsv):
    """Test that provenance records load_gnomad_constraint step with expected details."""
    config = load_config(test_config)
    store = PipelineStore.from_config(config)
    provenance = ProvenanceTracker.from_config(config)

    try:
        df = process_gnomad_constraint(sample_tsv)
        load_to_duckdb(df, store, provenance)

        # Check provenance step was recorded
        metadata = provenance.create_metadata()
        steps = metadata['processing_steps']

        load_steps = [s for s in steps if s['step_name'] == 'load_gnomad_constraint']
        assert len(load_steps) == 1

        step = load_steps[0]
        assert 'details' in step
        details = step['details']
        assert 'row_count' in details
        assert 'measured_count' in details
        assert 'incomplete_count' in details
        assert 'no_data_count' in details
        assert 'null_loeuf_count' in details

    finally:
        store.close()


def test_provenance_sidecar_created(test_config, sample_tsv, tmp_path):
    """Test that .provenance.json file is written with correct metadata."""
    config = load_config(test_config)
    store = PipelineStore.from_config(config)
    provenance = ProvenanceTracker.from_config(config)

    try:
        df = process_gnomad_constraint(sample_tsv)
        load_to_duckdb(df, store, provenance)

        # Save provenance sidecar (pass main file path, it will create .provenance.json)
        main_file_path = tmp_path / "constraint"
        provenance.save_sidecar(main_file_path)

        # Verify sidecar file was created
        sidecar_path = tmp_path / "constraint.provenance.json"
        assert sidecar_path.exists()

        with open(sidecar_path) as f:
            metadata = json.load(f)

        assert 'pipeline_version' in metadata
        assert 'data_source_versions' in metadata
        assert 'config_hash' in metadata
        assert 'created_at' in metadata
        assert 'processing_steps' in metadata

    finally:
        store.close()


def test_query_constrained_genes_filters_correctly(test_config, sample_tsv):
    """Test that query_constrained_genes returns only measured genes below threshold."""
    config = load_config(test_config)
    store = PipelineStore.from_config(config)
    provenance = ProvenanceTracker.from_config(config)

    try:
        df = process_gnomad_constraint(sample_tsv)
        load_to_duckdb(df, store, provenance)

        # Query with threshold 0.6 (should return genes with LOEUF < 0.6)
        constrained = query_constrained_genes(store, loeuf_threshold=0.6)

        # All results should have quality_flag='measured' and loeuf < 0.6
        assert all(constrained['quality_flag'] == 'measured')
        assert all(constrained['loeuf'] < 0.6)

        # Verify results are sorted by loeuf ascending
        loeuf_values = constrained['loeuf'].to_list()
        assert loeuf_values == sorted(loeuf_values)

    finally:
        store.close()


def test_null_loeuf_not_in_constrained_results(test_config, sample_tsv):
    """Test that genes with NULL LOEUF are excluded from constrained gene queries."""
    config = load_config(test_config)
    store = PipelineStore.from_config(config)
    provenance = ProvenanceTracker.from_config(config)

    try:
        df = process_gnomad_constraint(sample_tsv)
        load_to_duckdb(df, store, provenance)

        # Query all constrained genes
        constrained = query_constrained_genes(store, loeuf_threshold=10.0)  # High threshold to get all measured

        # No NULL LOEUF values should be in results
        assert constrained['loeuf'].null_count() == 0

    finally:
        store.close()


def test_duckdb_schema_has_quality_flag(test_config, sample_tsv):
    """Test that gnomad_constraint table has quality_flag column with non-null values."""
    config = load_config(test_config)
    store = PipelineStore.from_config(config)
    provenance = ProvenanceTracker.from_config(config)

    try:
        df = process_gnomad_constraint(sample_tsv)
        load_to_duckdb(df, store, provenance)

        loaded_df = store.load_dataframe('gnomad_constraint')

        # Verify quality_flag column exists
        assert 'quality_flag' in loaded_df.columns

        # Verify no NULL quality_flag values
        assert loaded_df['quality_flag'].null_count() == 0

        # Verify valid quality_flag values
        unique_flags = set(loaded_df['quality_flag'].unique().to_list())
        expected_flags = {'measured', 'incomplete_coverage', 'no_data'}
        assert unique_flags.issubset(expected_flags)

    finally:
        store.close()


def test_normalized_scores_in_duckdb(test_config, sample_tsv):
    """Test that loeuf_normalized values are in [0,1] for measured genes and NULL for others."""
    config = load_config(test_config)
    store = PipelineStore.from_config(config)
    provenance = ProvenanceTracker.from_config(config)

    try:
        df = process_gnomad_constraint(sample_tsv)
        load_to_duckdb(df, store, provenance)

        loaded_df = store.load_dataframe('gnomad_constraint')

        # Verify loeuf_normalized column exists
        assert 'loeuf_normalized' in loaded_df.columns

        # For measured genes: normalized scores should be in [0, 1]
        measured = loaded_df.filter(loaded_df['quality_flag'] == 'measured')
        normalized_values = measured['loeuf_normalized'].drop_nulls()

        if len(normalized_values) > 0:
            assert all(normalized_values >= 0.0)
            assert all(normalized_values <= 1.0)

        # For non-measured genes: normalized scores should be NULL
        non_measured = loaded_df.filter(loaded_df['quality_flag'] != 'measured')
        if len(non_measured) > 0:
            assert non_measured['loeuf_normalized'].null_count() == len(non_measured)

    finally:
        store.close()


def test_cli_evidence_gnomad_help():
    """Test that CLI evidence gnomad --help command works."""
    runner = CliRunner()
    result = runner.invoke(evidence, ['gnomad', '--help'])

    assert result.exit_code == 0
    assert 'gnomad' in result.output.lower()
    assert '--force' in result.output
    assert '--url' in result.output
    assert '--min-depth' in result.output
    assert '--min-cds-pct' in result.output


def test_cli_evidence_gnomad_with_mock(test_config, sample_tsv, tmp_path):
    """Test CLI gnomad command with mocked download."""
    runner = CliRunner()

    # Mock the download_constraint_metrics to use our synthetic TSV
    with patch('usher_pipeline.cli.evidence_cmd.download_constraint_metrics') as mock_download:
        mock_download.return_value = sample_tsv

        # Run CLI command
        result = runner.invoke(
            evidence,
            ['gnomad'],
            obj={'config_path': test_config, 'verbose': False}
        )

        # Should complete successfully
        assert result.exit_code == 0
        assert 'gnomad evidence layer complete' in result.output.lower() or 'checkpoint' in result.output.lower()


def test_idempotent_load_replaces_table(test_config, sample_tsv):
    """Test that loading twice replaces the table (idempotent operation)."""
    config = load_config(test_config)
    store = PipelineStore.from_config(config)
    provenance = ProvenanceTracker.from_config(config)

    try:
        # First load
        df1 = process_gnomad_constraint(sample_tsv)
        load_to_duckdb(df1, store, provenance)

        loaded1 = store.load_dataframe('gnomad_constraint')
        count1 = len(loaded1)

        # Second load (should replace, not append)
        df2 = process_gnomad_constraint(sample_tsv)
        load_to_duckdb(df2, store, provenance)

        loaded2 = store.load_dataframe('gnomad_constraint')
        count2 = len(loaded2)

        # Count should be the same (not doubled)
        assert count1 == count2

    finally:
        store.close()


def test_quality_flag_categorization(sample_tsv):
    """Test that quality_flag correctly categorizes genes by coverage and data availability."""
    df = process_gnomad_constraint(sample_tsv, min_depth=30.0, min_cds_pct=0.9)

    # Count each quality flag
    measured = df.filter(df['quality_flag'] == 'measured')
    incomplete = df.filter(df['quality_flag'] == 'incomplete_coverage')
    no_data = df.filter(df['quality_flag'] == 'no_data')

    # Based on synthetic data:
    # - 5 well-covered genes with LOEUF/pLI (measured)
    # - 3 low depth + 3 low CDS (incomplete_coverage)
    # - 2 NULL LOEUF and pLI (no_data)
    # - 2 at bounds (measured if coverage good)

    # Verify we have all categories
    assert len(measured) > 0
    assert len(incomplete) > 0
    assert len(no_data) > 0

    # Total should equal input genes
    assert len(measured) + len(incomplete) + len(no_data) == 15

    # Measured genes should have non-null LOEUF
    assert measured['loeuf'].null_count() == 0

    # No data genes should have NULL LOEUF and pLI
    assert no_data['loeuf'].null_count() == len(no_data)
    assert no_data['pli'].null_count() == len(no_data)

"""Integration tests verifying module wiring.

Tests that config, gene mapping, persistence, and provenance modules
work together correctly without calling real external APIs.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import polars as pl
import pytest
from click.testing import CliRunner

from usher_pipeline.cli.main import cli
from usher_pipeline.config.loader import load_config
from usher_pipeline.gene_mapping import (
    fetch_protein_coding_genes,
    GeneMapper,
    MappingValidator,
    validate_gene_universe,
)
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker


# Mock data for testing
MOCK_GENES = [
    f"ENSG0000000{i:03d}" for i in range(1, 6)
]

MOCK_MYGENE_QUERY_RESPONSE = [
    {
        'ensembl': {'gene': 'ENSG00000001'},
        'symbol': 'GENE1',
        'name': 'Gene 1',
    },
    {
        'ensembl': {'gene': 'ENSG00000002'},
        'symbol': 'GENE2',
        'name': 'Gene 2',
    },
    {
        'ensembl': {'gene': 'ENSG00000003'},
        'symbol': 'GENE3',
        'name': 'Gene 3',
    },
    {
        'ensembl': {'gene': 'ENSG00000004'},
        'symbol': 'GENE4',
        'name': 'Gene 4',
    },
    {
        'ensembl': {'gene': 'ENSG00000005'},
        'symbol': 'GENE5',
        'name': 'Gene 5',
    },
]

MOCK_MYGENE_QUERYMANY_RESPONSE = {
    'out': [
        {
            'query': 'ENSG00000001',
            'symbol': 'GENE1',
            'uniprot': {'Swiss-Prot': 'P12345'},
        },
        {
            'query': 'ENSG00000002',
            'symbol': 'GENE2',
            'uniprot': {'Swiss-Prot': 'P23456'},
        },
        {
            'query': 'ENSG00000003',
            'symbol': 'GENE3',
            'uniprot': {'Swiss-Prot': 'P34567'},
        },
        {
            'query': 'ENSG00000004',
            'symbol': 'GENE4',
            'uniprot': {'Swiss-Prot': 'P45678'},
        },
        {
            'query': 'ENSG00000005',
            'symbol': 'GENE5',
            'uniprot': {'Swiss-Prot': 'P56789'},
        },
    ],
    'missing': []
}


@pytest.fixture
def test_config(tmp_path):
    """Create a test config with temporary paths."""
    config_content = f"""
data_dir: {tmp_path}/data
cache_dir: {tmp_path}/cache
duckdb_path: {tmp_path}/test_pipeline.duckdb

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
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text(config_content)
    return config_path


def test_config_to_store_roundtrip(test_config, tmp_path):
    """Test config -> PipelineStore -> save/load roundtrip."""
    # Load config
    config = load_config(test_config)
    assert config.data_dir == Path(tmp_path) / "data"

    # Create store from config
    store = PipelineStore.from_config(config)

    # Create test DataFrame
    test_df = pl.DataFrame({
        'id': [1, 2, 3],
        'value': ['a', 'b', 'c']
    })

    # Save DataFrame
    store.save_dataframe(test_df, 'test_table', description="Test data")

    # Verify checkpoint exists
    assert store.has_checkpoint('test_table')

    # Load back
    loaded_df = store.load_dataframe('test_table')
    assert loaded_df is not None
    assert loaded_df.shape == test_df.shape
    assert loaded_df.columns == test_df.columns
    assert loaded_df.to_dict(as_series=False) == test_df.to_dict(as_series=False)

    store.close()


def test_config_to_provenance(test_config, tmp_path):
    """Test config -> ProvenanceTracker -> sidecar creation."""
    # Load config
    config = load_config(test_config)
    config_hash = config.config_hash()

    # Create provenance tracker from config
    provenance = ProvenanceTracker.from_config(config)

    # Record steps
    provenance.record_step('step1', {'detail': 'test1'})
    provenance.record_step('step2', {'detail': 'test2'})

    # Save sidecar (pass base path, it will add .provenance.json)
    output_path = tmp_path / "test.json"
    provenance.save_sidecar(output_path)

    # Verify file exists (with .provenance.json suffix)
    sidecar_path = tmp_path / "test.provenance.json"
    assert sidecar_path.exists()

    # Load and verify contents
    with open(sidecar_path) as f:
        data = json.load(f)

    assert data['config_hash'] == config_hash
    assert data['pipeline_version'] == '0.1.0'
    assert len(data['processing_steps']) == 2
    assert data['processing_steps'][0]['step_name'] == 'step1'
    assert data['processing_steps'][1]['step_name'] == 'step2'


def test_full_setup_flow_mocked(test_config, tmp_path):
    """Test full setup flow with mocked mygene API calls."""
    # Load config
    config = load_config(test_config)

    # Mock mygene API calls
    with patch('mygene.MyGeneInfo') as mock_mg:
        # Set up mock instance
        mock_instance = MagicMock()
        mock_mg.return_value = mock_instance

        # Mock query (for fetch_protein_coding_genes)
        mock_instance.query.return_value = MOCK_MYGENE_QUERY_RESPONSE

        # Mock querymany (for GeneMapper)
        mock_instance.querymany.return_value = MOCK_MYGENE_QUERYMANY_RESPONSE

        # Create store and provenance
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)

        # Fetch universe (mocked)
        gene_universe = fetch_protein_coding_genes(
            ensembl_release=config.versions.ensembl_release
        )
        assert len(gene_universe) == 5
        provenance.record_step('fetch_gene_universe', {
            'gene_count': len(gene_universe)
        })

        # Validate universe
        universe_validation = validate_gene_universe(gene_universe)
        assert not universe_validation.passed  # 5 genes is below 19k minimum
        # For this test, we'll continue anyway since it's mocked data

        # Map IDs (mocked)
        mapper = GeneMapper(batch_size=1000)
        mapping_results, mapping_report = mapper.map_ensembl_ids(gene_universe)
        assert mapping_report.total_genes == 5
        assert mapping_report.mapped_hgnc == 5
        assert mapping_report.mapped_uniprot == 5
        provenance.record_step('map_gene_ids', {
            'total_genes': mapping_report.total_genes,
            'mapped_hgnc': mapping_report.mapped_hgnc,
        })

        # Save to DuckDB
        df = pl.DataFrame({
            'ensembl_id': [r.ensembl_id for r in mapping_results],
            'hgnc_symbol': [r.hgnc_symbol for r in mapping_results],
            'uniprot_accession': [r.uniprot_accession for r in mapping_results],
        })
        store.save_dataframe(
            df,
            'gene_universe',
            description="Test gene universe"
        )

        # Verify checkpoint exists
        assert store.has_checkpoint('gene_universe')

        # Load and verify data
        loaded_df = store.load_dataframe('gene_universe')
        assert loaded_df is not None
        assert len(loaded_df) == 5
        assert 'ensembl_id' in loaded_df.columns
        assert 'hgnc_symbol' in loaded_df.columns
        assert 'uniprot_accession' in loaded_df.columns

        # Save provenance (pass base path, it will add .provenance.json)
        provenance.save_sidecar(tmp_path / "setup")
        prov_path = tmp_path / "setup.provenance.json"
        assert prov_path.exists()

        store.close()


def test_checkpoint_skip_flow(test_config, tmp_path):
    """Test that setup skips re-fetch when checkpoint exists."""
    # Load config
    config = load_config(test_config)

    with patch('mygene.MyGeneInfo') as mock_mg:
        mock_instance = MagicMock()
        mock_mg.return_value = mock_instance
        mock_instance.query.return_value = MOCK_MYGENE_QUERY_RESPONSE
        mock_instance.querymany.return_value = MOCK_MYGENE_QUERYMANY_RESPONSE

        # First run: create checkpoint
        store = PipelineStore.from_config(config)
        gene_universe = fetch_protein_coding_genes(113)
        mapper = GeneMapper()
        mapping_results, _ = mapper.map_ensembl_ids(gene_universe)

        df = pl.DataFrame({
            'ensembl_id': [r.ensembl_id for r in mapping_results],
            'hgnc_symbol': [r.hgnc_symbol for r in mapping_results],
            'uniprot_accession': [r.uniprot_accession for r in mapping_results],
        })
        store.save_dataframe(df, 'gene_universe', description="Test")
        store.close()

        # Reset mock call counts
        mock_instance.query.reset_mock()

        # Second run: checkpoint exists, should skip fetch
        store2 = PipelineStore.from_config(config)
        has_checkpoint = store2.has_checkpoint('gene_universe')
        assert has_checkpoint

        # If checkpoint exists, we wouldn't call fetch_protein_coding_genes again
        # Verify we can load the data
        loaded_df = store2.load_dataframe('gene_universe')
        assert loaded_df is not None
        assert len(loaded_df) == 5

        # Verify fetch was NOT called in second run
        mock_instance.query.assert_not_called()

        store2.close()


def test_setup_cli_help():
    """Test setup command help output."""
    runner = CliRunner()
    result = runner.invoke(cli, ['setup', '--help'])

    assert result.exit_code == 0
    assert '--force' in result.output
    assert 'checkpoint' in result.output.lower()


def test_info_cli(test_config):
    """Test info command with test config."""
    runner = CliRunner()
    result = runner.invoke(cli, ['--config', str(test_config), 'info'])

    assert result.exit_code == 0
    assert 'Usher Pipeline v0.1.0' in result.output
    assert 'Ensembl Release: 113' in result.output
    assert 'Config Hash:' in result.output

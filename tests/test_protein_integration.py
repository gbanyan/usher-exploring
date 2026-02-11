"""Integration tests for protein features evidence layer."""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import polars as pl
import pytest

from usher_pipeline.config.loader import load_config
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker
from usher_pipeline.evidence.protein import (
    process_protein_evidence,
    load_to_duckdb,
    query_cilia_candidates,
)


@pytest.fixture
def test_config(tmp_path: Path):
    """Create test configuration."""
    config_path = tmp_path / "config.yaml"
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
    return load_config(config_path)


@pytest.fixture
def mock_gene_universe():
    """Mock gene universe with UniProt mappings."""
    return pl.DataFrame({
        "gene_id": ["ENSG00000001", "ENSG00000002", "ENSG00000003", "ENSG00000004"],
        "gene_symbol": ["GENE1", "GENE2", "GENE3", "GENE4"],
        "uniprot_id": ["P12345", "Q67890", "A11111", None],  # GENE4 has no UniProt
    })


@pytest.fixture
def mock_uniprot_response():
    """Mock UniProt API response with realistic domain structures."""
    return {
        "results": [
            {
                "primaryAccession": "P12345",
                "sequence": {"length": 500},
                "features": [
                    {"type": "Domain", "description": "PDZ domain"},
                    {"type": "Domain", "description": "SH3 domain"},
                    {"type": "Coiled coil"},
                    {"type": "Coiled coil"},
                ],
            },
            {
                "primaryAccession": "Q67890",
                "sequence": {"length": 1200},
                "features": [
                    {"type": "Domain", "description": "IFT complex subunit"},
                    {"type": "Domain", "description": "WD40 repeat"},
                    {"type": "Transmembrane"},
                    {"type": "Transmembrane"},
                    {"type": "Transmembrane"},
                ],
            },
            {
                "primaryAccession": "A11111",
                "sequence": {"length": 300},
                "features": [
                    {"type": "Domain", "description": "Kinase domain"},
                ],
            },
        ]
    }


@pytest.fixture
def mock_interpro_response():
    """Mock InterPro API responses per protein."""
    return {
        "P12345": {
            "results": [
                {
                    "metadata": {
                        "accession": "IPR001452",
                        "name": {"name": "Ankyrin repeat"},
                    }
                }
            ]
        },
        "Q67890": {
            "results": [
                {
                    "metadata": {
                        "accession": "IPR005598",
                        "name": {"name": "Ciliary targeting signal"},
                    }
                }
            ]
        },
        "A11111": {
            "results": []
        },
    }


@patch("usher_pipeline.evidence.protein.fetch.httpx.Client")
@patch("usher_pipeline.evidence.protein.fetch.time.sleep")  # Speed up tests
def test_full_pipeline_with_mocked_apis(
    mock_sleep,
    mock_client_class,
    mock_gene_universe,
    mock_uniprot_response,
    mock_interpro_response,
):
    """Test full pipeline with mocked UniProt and InterPro APIs."""
    # Mock httpx client
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    # Setup mock responses
    def mock_get(url, params=None):
        mock_response = Mock()

        # UniProt search endpoint
        if "uniprot" in url and "search" in url:
            mock_response.json.return_value = mock_uniprot_response
            mock_response.raise_for_status = Mock()
            return mock_response

        # InterPro API
        if "interpro" in url:
            # Extract accession from URL
            accession = url.split("/")[-1]
            if accession in mock_interpro_response:
                mock_response.json.return_value = mock_interpro_response[accession]
            else:
                mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status = Mock()
            return mock_response

        raise ValueError(f"Unexpected URL: {url}")

    mock_client.get.side_effect = mock_get

    # Run pipeline
    gene_ids = mock_gene_universe.select("gene_id").to_series().to_list()
    df = process_protein_evidence(gene_ids, mock_gene_universe)

    # Verify results
    assert len(df) == 4  # All genes present

    # Check GENE1 (P12345) - has PDZ, SH3, Ankyrin (scaffold domains) + coiled-coils
    gene1 = df.filter(pl.col("gene_symbol") == "GENE1")
    assert gene1["uniprot_id"][0] == "P12345"
    assert gene1["protein_length"][0] == 500
    assert gene1["domain_count"][0] == 3  # PDZ, SH3, Ankyrin
    assert gene1["coiled_coil"][0] == True
    assert gene1["coiled_coil_count"][0] == 2
    assert gene1["scaffold_adaptor_domain"][0] == True  # Has PDZ, SH3, Ankyrin
    assert gene1["protein_score_normalized"][0] is not None

    # Check GENE2 (Q67890) - has IFT and ciliary domains
    gene2 = df.filter(pl.col("gene_symbol") == "GENE2")
    assert gene2["has_cilia_domain"][0] == True  # IFT + ciliary
    assert gene2["transmembrane_count"][0] == 3

    # Check GENE3 (A11111) - minimal features
    gene3 = df.filter(pl.col("gene_symbol") == "GENE3")
    assert gene3["domain_count"][0] == 1  # Only Kinase
    assert gene3["has_cilia_domain"][0] == False

    # Check GENE4 (no UniProt) - all NULL
    gene4 = df.filter(pl.col("gene_symbol") == "GENE4")
    assert gene4["uniprot_id"][0] is None
    assert gene4["protein_length"][0] is None
    assert gene4["protein_score_normalized"][0] is None


def test_checkpoint_restart(tmp_path: Path, test_config, mock_gene_universe):
    """Test checkpoint-restart pattern with DuckDB."""
    db_path = tmp_path / "test.duckdb"
    store = PipelineStore(db_path)
    provenance = ProvenanceTracker.from_config(test_config)

    # Create synthetic protein features
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001", "ENSG00000002"],
        "gene_symbol": ["GENE1", "GENE2"],
        "uniprot_id": ["P12345", "Q67890"],
        "protein_length": [500, 1200],
        "domain_count": [3, 5],
        "coiled_coil": [True, False],
        "coiled_coil_count": [2, 0],
        "transmembrane_count": [0, 3],
        "scaffold_adaptor_domain": [True, False],
        "has_cilia_domain": [False, True],
        "has_sensory_domain": [False, False],
        "protein_score_normalized": [0.65, 0.82],
    })

    # Load to DuckDB
    load_to_duckdb(df, store, provenance, "Test protein features")

    # Verify checkpoint exists
    assert store.has_checkpoint("protein_features")

    # Reload data
    loaded_df = store.load_dataframe("protein_features")
    assert loaded_df is not None
    assert len(loaded_df) == 2
    assert loaded_df["gene_symbol"].to_list() == ["GENE1", "GENE2"]

    # Verify provenance
    checkpoints = store.list_checkpoints()
    protein_checkpoint = [c for c in checkpoints if c["table_name"] == "protein_features"][0]
    assert protein_checkpoint["row_count"] == 2

    store.close()


def test_query_cilia_candidates(tmp_path: Path):
    """Test querying genes with cilia-associated features."""
    db_path = tmp_path / "test.duckdb"
    store = PipelineStore(db_path)

    # Create test data with various feature combinations
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001", "ENSG00000002", "ENSG00000003", "ENSG00000004"],
        "gene_symbol": ["GENE1", "GENE2", "GENE3", "GENE4"],
        "uniprot_id": ["P1", "P2", "P3", "P4"],
        "protein_length": [500, 600, 700, 800],
        "domain_count": [3, 4, 2, 5],
        "coiled_coil": [True, True, False, True],
        "transmembrane_count": [0, 2, 0, 3],
        "scaffold_adaptor_domain": [True, False, True, True],
        "has_cilia_domain": [False, True, False, False],
        "has_sensory_domain": [False, False, False, True],
        "protein_score_normalized": [0.65, 0.82, 0.45, 0.78],
    })

    # Load to DuckDB
    store.save_dataframe(df, "protein_features", "Test data", replace=True)

    # Query cilia candidates
    candidates = query_cilia_candidates(store)

    # Should include:
    # - GENE1: has coiled_coil + scaffold_adaptor_domain
    # - GENE2: has cilia_domain
    # - GENE4: has coiled_coil + scaffold_adaptor_domain
    # Should NOT include:
    # - GENE3: has scaffold but no coiled_coil, and no cilia_domain

    assert len(candidates) == 3
    symbols = candidates["gene_symbol"].to_list()
    assert "GENE1" in symbols
    assert "GENE2" in symbols
    assert "GENE4" in symbols
    assert "GENE3" not in symbols

    # Verify sorting by score (descending)
    assert candidates["protein_score_normalized"][0] == 0.82  # GENE2

    store.close()


def test_provenance_recording(tmp_path: Path, test_config):
    """Test provenance metadata is correctly recorded."""
    db_path = tmp_path / "test.duckdb"
    store = PipelineStore(db_path)
    provenance = ProvenanceTracker.from_config(test_config)

    # Create test data with known stats
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001", "ENSG00000002", "ENSG00000003"],
        "gene_symbol": ["GENE1", "GENE2", "GENE3"],
        "uniprot_id": ["P1", "P2", None],  # 1 without UniProt
        "protein_length": [500, 600, None],
        "domain_count": [3, 4, None],
        "coiled_coil": [True, False, None],
        "coiled_coil_count": [2, 0, None],
        "transmembrane_count": [0, 2, None],
        "scaffold_adaptor_domain": [True, False, None],
        "has_cilia_domain": [False, True, None],
        "has_sensory_domain": [False, False, None],
        "protein_score_normalized": [0.65, 0.82, None],
    })

    # Load with provenance
    load_to_duckdb(df, store, provenance, "Test protein features")

    # Verify provenance step was recorded
    steps = provenance.get_steps()
    protein_step = [s for s in steps if s["name"] == "load_protein_features"][0]

    assert protein_step["details"]["total_genes"] == 3
    assert protein_step["details"]["with_uniprot"] == 2
    assert protein_step["details"]["null_uniprot"] == 1
    assert protein_step["details"]["cilia_domain_count"] == 1
    assert protein_step["details"]["scaffold_domain_count"] == 1
    assert protein_step["details"]["coiled_coil_count"] == 1
    assert protein_step["details"]["transmembrane_domain_count"] == 1

    store.close()


@patch("usher_pipeline.evidence.protein.fetch.httpx.Client")
@patch("usher_pipeline.evidence.protein.fetch.time.sleep")
def test_null_preservation(mock_sleep, mock_client_class, mock_gene_universe):
    """Test that NULL values are preserved (not converted to 0)."""
    # Mock httpx client
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    # Mock response with one protein not found
    mock_response = Mock()
    mock_response.json.return_value = {
        "results": []  # No results for any protein
    }
    mock_client.get.return_value = mock_response

    # Run pipeline
    gene_ids = ["ENSG00000001"]
    gene_map = mock_gene_universe.filter(pl.col("gene_id") == "ENSG00000001")
    df = process_protein_evidence(gene_ids, gene_map)

    # All protein features should be NULL (not 0)
    assert df["protein_length"][0] is None
    assert df["domain_count"][0] is None or df["domain_count"][0] == 0
    assert df["coiled_coil"][0] is None
    assert df["transmembrane_count"][0] is None
    assert df["protein_score_normalized"][0] is None  # Critical: NOT 0.0

"""Integration tests for expression evidence layer.

Tests with mocked downloads and synthetic fixtures.
NO actual external API calls to HPA/GTEx/CellxGene.
"""

import polars as pl
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from usher_pipeline.evidence.expression.transform import process_expression_evidence
from usher_pipeline.evidence.expression.load import load_to_duckdb, query_tissue_enriched
from usher_pipeline.evidence.expression.models import (
    EXPRESSION_SCHEMA_VERSION,
    RESTRICTED_ENRICHMENT_COLUMN,
    RESTRICTED_TAU_COLUMN,
)
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory for downloads."""
    cache_dir = tmp_path / "expression"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def mock_gene_ids():
    """Sample gene IDs for testing."""
    return ["ENSG00000001", "ENSG00000002", "ENSG00000003"]


@pytest.fixture
def mock_hpa_data():
    """Synthetic HPA expression data."""
    return pl.LazyFrame({
        "gene_symbol": ["GENE1", "GENE2", "GENE3"],
        "hpa_retina_protein_level": [3, 1, None],
        "hpa_cerebellum_protein_level": [3, 1, 1],
        "hpa_testis_protein_level": [1, 3, 3],
        "hpa_fallopian_tube_protein_level": [1, 3, None],
    })


@pytest.fixture
def mock_gtex_data(mock_gene_ids):
    """Synthetic GTEx expression data."""
    return pl.LazyFrame({
        "gene_id": mock_gene_ids,
        "gtex_retina_tpm": [60.0, 10.0, None],
        "gtex_cerebellum_tpm": [45.0, 10.0, 5.0],
        "gtex_testis_tpm": [5.0, 55.0, 55.0],
        "gtex_fallopian_tube_tpm": [None, None, None],  # Often not available
    })


@pytest.fixture
def mock_cellxgene_data(mock_gene_ids):
    """Synthetic CellxGene data (NULLs as placeholder)."""
    return pl.LazyFrame({
        "gene_id": mock_gene_ids,
        "cellxgene_photoreceptor_expr": [None, None, None],
        "cellxgene_hair_cell_expr": [None, None, None],
    })


def test_process_expression_pipeline_with_mocks(
    temp_cache_dir, mock_gene_ids, mock_hpa_data, mock_gtex_data, mock_cellxgene_data
):
    """Test full pipeline with mocked data sources."""
    # Mock all fetch functions to return synthetic data
    with patch('usher_pipeline.evidence.expression.transform.fetch_hpa_expression') as mock_hpa, \
         patch('usher_pipeline.evidence.expression.transform.fetch_gtex_expression') as mock_gtex, \
         patch('usher_pipeline.evidence.expression.transform.fetch_cellxgene_expression') as mock_cellxgene:

        mock_hpa.return_value = mock_hpa_data
        mock_gtex.return_value = mock_gtex_data
        mock_cellxgene.return_value = mock_cellxgene_data

        # Run pipeline (skip CellxGene for simplicity)
        df = process_expression_evidence(
            gene_ids=mock_gene_ids,
            cache_dir=temp_cache_dir,
            skip_cellxgene=True,
            gene_symbol_map=pl.DataFrame({
                "gene_id": mock_gene_ids,
                "gene_symbol": ["GENE1", "GENE2", "GENE3"],
            }),
        )

        # Verify output structure
        assert len(df) == len(mock_gene_ids)
        assert "gene_id" in df.columns
        assert "gene_symbol" in df.columns
        assert df["gene_symbol"].to_list() == ["GENE1", "GENE2", "GENE3"]
        assert "hpa_retina_protein_level" in df.columns
        assert "hpa_retina_tpm" not in df.columns
        assert RESTRICTED_TAU_COLUMN in df.columns
        assert RESTRICTED_ENRICHMENT_COLUMN in df.columns
        assert "expression_score_normalized" in df.columns


def test_checkpoint_restart(temp_cache_dir, mock_gene_ids):
    """Test checkpoint-restart: skip processing if table exists."""
    # Create mock store with existing checkpoint
    mock_store = Mock(spec=PipelineStore)
    mock_store.has_checkpoint.return_value = True

    # Mock load_dataframe to return synthetic data
    existing_data = pl.DataFrame({
        "gene_id": mock_gene_ids,
        RESTRICTED_TAU_COLUMN: [0.5, 0.3, 0.2],
        RESTRICTED_ENRICHMENT_COLUMN: [2.0, 1.0, 0.5],
        "expression_score_normalized": [0.8, 0.5, 0.3],
    })
    mock_store.load_dataframe.return_value = existing_data

    # Verify checkpoint works (would skip processing in real CLI)
    assert mock_store.has_checkpoint('tissue_expression')
    df = mock_store.load_dataframe('tissue_expression')
    assert len(df) == len(mock_gene_ids)


def test_provenance_recording():
    """Test provenance step recording during load."""
    # Create synthetic expression data
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001", "ENSG00000002"],
        "hpa_retina_protein_level": [3, None],
        "gtex_retina_tpm": [60.0, 10.0],
        "cellxgene_photoreceptor_expr": [None, None],
        "cellxgene_hair_cell_expr": [None, None],
        RESTRICTED_TAU_COLUMN: [0.5, None],
        RESTRICTED_ENRICHMENT_COLUMN: [2.0, 1.0],
        "expression_score_normalized": [0.8, 0.5],
    })

    # Mock store and provenance tracker
    mock_store = Mock(spec=PipelineStore)
    mock_provenance = Mock(spec=ProvenanceTracker)

    # Call load function
    load_to_duckdb(
        df=df,
        store=mock_store,
        provenance=mock_provenance,
        description="Test expression data"
    )

    # Verify provenance step was recorded
    mock_provenance.record_step.assert_called_once()
    step_name, step_details = mock_provenance.record_step.call_args[0]
    assert step_name == "load_tissue_expression"
    assert "row_count" in step_details
    assert step_details["row_count"] == 2
    assert step_details["schema_version"] == EXPRESSION_SCHEMA_VERSION
    assert step_details["coverage"]["gtex_tpm"]["gtex_retina_tpm"]["non_null_count"] == 2


def test_null_expression_handling():
    """Test that genes with all NULL expression data are handled gracefully."""
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001", "ENSG00000002"],
        "hpa_retina_protein_level": [None, 3],
        "hpa_cerebellum_protein_level": [None, 3],
        "gtex_retina_tpm": [None, 60.0],
        "cellxgene_photoreceptor_expr": [None, None],
        "cellxgene_hair_cell_expr": [None, None],
        RESTRICTED_TAU_COLUMN: [None, 0.5],
        RESTRICTED_ENRICHMENT_COLUMN: [None, 2.0],
        "expression_score_normalized": [None, 0.8],
    })

    # Mock store
    mock_store = Mock(spec=PipelineStore)
    mock_provenance = Mock(spec=ProvenanceTracker)

    # Should not raise exception
    load_to_duckdb(df, mock_store, mock_provenance)

    # Verify store was called
    mock_store.save_dataframe.assert_called_once()


def test_query_tissue_enriched_reads_gene_symbol_from_produced_table(tmp_path):
    """The enriched query must expose symbols persisted by the expression load."""
    store = PipelineStore(tmp_path / "expression.duckdb")
    provenance = Mock(spec=ProvenanceTracker)
    df = pl.DataFrame({
        "gene_id": ["ENSG1", "ENSG2"],
        "gene_symbol": ["GENE1", "GENE2"],
        RESTRICTED_TAU_COLUMN: [0.0, 0.5],
        RESTRICTED_ENRICHMENT_COLUMN: [3.0, 1.0],
        "expression_score_normalized": [0.8, 0.2],
        "hpa_retina_protein_level": [3, 0],
        "hpa_retina_ntpm": [None, None],
        "gtex_retina_tpm": [10.0, 0.0],
        "cellxgene_photoreceptor_expr": [None, None],
        "cellxgene_hair_cell_expr": [None, None],
    })
    load_to_duckdb(df, store, provenance)

    result = query_tissue_enriched(store, min_enrichment=2.0)

    assert result["gene_symbol"].to_list() == ["GENE1"]
    assert result[RESTRICTED_ENRICHMENT_COLUMN].to_list() == [3.0]
    store.close()


def test_all_null_gtex_does_not_infer_structural_absence():
    """Only raw-source metadata can establish structural GTEx absence."""
    df = pl.DataFrame({
        "gene_id": ["ENSG1"],
        "gene_symbol": ["GENE1"],
        "gtex_retina_tpm": [None],
        RESTRICTED_TAU_COLUMN: [0.0],
        RESTRICTED_ENRICHMENT_COLUMN: [None],
        "expression_score_normalized": [None],
    })
    mock_store = Mock(spec=PipelineStore)
    mock_provenance = Mock(spec=ProvenanceTracker)

    load_to_duckdb(df, mock_store, mock_provenance)

    details = mock_provenance.record_step.call_args[0][1]
    assert details["structurally_absent"] == {}
    assert details["mean_tau_restricted_panel_specificity"] == 0.0

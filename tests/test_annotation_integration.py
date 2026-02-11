"""Integration tests for annotation evidence layer."""

import polars as pl
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from usher_pipeline.config.loader import load_config
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker
from usher_pipeline.evidence.annotation import (
    process_annotation_evidence,
    load_to_duckdb,
    query_poorly_annotated,
)


@pytest.fixture
def test_config(tmp_path):
    """Create test configuration."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    config_yaml = f"""
project_name: "usher-pipeline-test"
data_dir: "{data_dir}"
cache_dir: "{tmp_path / 'cache'}"
duckdb_path: "{tmp_path / 'test.duckdb'}"

versions:
  ensembl_release: 112
  gnomad_version: "4.1"

api:
  rate_limit_per_second: 5
  max_retries: 3
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
    config_file = config_dir / "pipeline.yaml"
    config_file.write_text(config_yaml)

    return load_config(config_file)


@pytest.fixture
def mock_gene_ids():
    """Sample gene IDs for testing."""
    return ["ENSG001", "ENSG002", "ENSG003", "ENSG004", "ENSG005"]


@pytest.fixture
def mock_uniprot_mapping():
    """Mock UniProt mapping DataFrame."""
    return pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
        "uniprot_accession": ["P12345", "Q67890", "A11111"],
    })


@pytest.fixture
def synthetic_annotation_data():
    """Create synthetic annotation data for testing."""
    return pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002", "ENSG003", "ENSG004", "ENSG005"],
        "gene_symbol": ["GENE1", "GENE2", "GENE3", "GENE4", "GENE5"],
        "go_term_count": [50, 15, 5, None, 2],
        "go_biological_process_count": [30, 10, 3, None, 1],
        "go_molecular_function_count": [15, 3, 2, None, 1],
        "go_cellular_component_count": [5, 2, 0, None, 0],
        "uniprot_annotation_score": [5, 4, 3, None, 1],
        "has_pathway_membership": [True, True, False, None, False],
        "annotation_tier": ["well_annotated", "well_annotated", "partially_annotated", "poorly_annotated", "poorly_annotated"],
        "annotation_score_normalized": [0.9, 0.75, 0.45, None, 0.15],
    })


def mock_mygene_querymany(gene_ids, **kwargs):
    """Mock mygene.querymany response."""
    # Simulate different annotation levels
    return [
        {
            "query": "ENSG001",
            "symbol": "GENE1",
            "go": {
                "BP": [{"id": f"GO:000{i}"} for i in range(30)],
                "MF": [{"id": f"GO:100{i}"} for i in range(15)],
                "CC": [{"id": f"GO:200{i}"} for i in range(5)],
            },
            "pathway": {
                "kegg": [{"id": "hsa00001"}],
                "reactome": [{"id": "R-HSA-00001"}],
            },
        },
        {
            "query": "ENSG002",
            "symbol": "GENE2",
            "go": {
                "BP": [{"id": f"GO:000{i}"} for i in range(10)],
                "MF": [{"id": f"GO:100{i}"} for i in range(3)],
                "CC": [{"id": f"GO:200{i}"} for i in range(2)],
            },
            "pathway": {"kegg": [{"id": "hsa00002"}]},
        },
        {
            "query": "ENSG003",
            "symbol": "GENE3",
            "go": {
                "BP": [{"id": "GO:0001"}, {"id": "GO:0002"}],
            },
            "pathway": {},
        },
        {
            "query": "ENSG004",
            "symbol": "GENE4",
            # No GO or pathway data
        },
        {
            "query": "ENSG005",
            "symbol": "GENE5",
            "go": {
                "BP": [{"id": "GO:0001"}],
            },
        },
    ]


def mock_uniprot_api_response():
    """Mock UniProt API response."""
    return {
        "results": [
            {"primaryAccession": "P12345", "annotationScore": 5},
            {"primaryAccession": "Q67890", "annotationScore": 4},
            {"primaryAccession": "A11111", "annotationScore": 3},
        ]
    }


@patch("usher_pipeline.evidence.annotation.fetch._get_mygene_client")
@patch("usher_pipeline.evidence.annotation.fetch._query_uniprot_batch")
def test_process_annotation_evidence_pipeline(
    mock_uniprot, mock_mygene_client, mock_gene_ids, mock_uniprot_mapping
):
    """Test full annotation evidence processing pipeline."""
    # Setup mocks
    mock_mg = Mock()
    mock_mg.querymany.return_value = mock_mygene_querymany(mock_gene_ids)
    mock_mygene_client.return_value = mock_mg

    mock_uniprot.return_value = {
        "P12345": 5,
        "Q67890": 4,
        "A11111": 3,
    }

    # Run pipeline
    result = process_annotation_evidence(mock_gene_ids, mock_uniprot_mapping)

    # Verify results
    assert result.height == len(mock_gene_ids)
    assert "annotation_tier" in result.columns
    assert "annotation_score_normalized" in result.columns

    # Check that tiers are classified
    tiers = result["annotation_tier"].unique().to_list()
    assert "well_annotated" in tiers or "partially_annotated" in tiers or "poorly_annotated" in tiers

    # Verify mygene was called
    mock_mg.querymany.assert_called_once()

    # Verify UniProt was queried
    mock_uniprot.assert_called()


def test_load_to_duckdb_idempotent(test_config, synthetic_annotation_data):
    """Test that load_to_duckdb is idempotent (CREATE OR REPLACE)."""
    store = PipelineStore.from_config(test_config)
    provenance = ProvenanceTracker.from_config(test_config)

    # First load
    load_to_duckdb(synthetic_annotation_data, store, provenance, "First load")

    # Verify data exists
    df1 = store.load_dataframe("annotation_completeness")
    assert df1 is not None
    assert df1.height == synthetic_annotation_data.height

    # Second load (should replace)
    modified_data = synthetic_annotation_data.with_columns(
        pl.lit("test_modified").alias("gene_symbol")
    )
    load_to_duckdb(modified_data, store, provenance, "Second load")

    # Verify data was replaced
    df2 = store.load_dataframe("annotation_completeness")
    assert df2 is not None
    assert df2.height == modified_data.height
    assert all(df2["gene_symbol"] == "test_modified")

    store.close()


def test_checkpoint_restart(test_config, synthetic_annotation_data):
    """Test checkpoint-restart pattern."""
    store = PipelineStore.from_config(test_config)
    provenance = ProvenanceTracker.from_config(test_config)

    # Initially no checkpoint
    assert not store.has_checkpoint("annotation_completeness")

    # Load creates checkpoint
    load_to_duckdb(synthetic_annotation_data, store, provenance)

    # Now checkpoint exists
    assert store.has_checkpoint("annotation_completeness")

    # Can load existing data
    df = store.load_dataframe("annotation_completeness")
    assert df is not None
    assert df.height == synthetic_annotation_data.height

    store.close()


def test_provenance_recording(test_config, synthetic_annotation_data):
    """Test that provenance metadata is recorded correctly."""
    store = PipelineStore.from_config(test_config)
    provenance = ProvenanceTracker.from_config(test_config)

    load_to_duckdb(synthetic_annotation_data, store, provenance)

    # Verify provenance step was recorded
    steps = provenance.processing_steps
    assert len(steps) > 0

    step = steps[-1]
    assert step["step_name"] == "load_annotation_completeness"
    assert "row_count" in step["details"]
    assert step["details"]["row_count"] == synthetic_annotation_data.height
    assert "well_annotated_count" in step["details"]
    assert "poorly_annotated_count" in step["details"]

    store.close()


def test_query_poorly_annotated(test_config, synthetic_annotation_data):
    """Test querying poorly annotated genes."""
    store = PipelineStore.from_config(test_config)
    provenance = ProvenanceTracker.from_config(test_config)

    # Load data
    load_to_duckdb(synthetic_annotation_data, store, provenance)

    # Query poorly annotated genes (score <= 0.3)
    result = query_poorly_annotated(store, max_score=0.3)

    # Should return genes with low scores
    assert result.height > 0
    assert all(result["annotation_score_normalized"] <= 0.3)

    # Results should be sorted by score (lowest first)
    scores = result["annotation_score_normalized"].to_list()
    assert scores == sorted(scores)

    store.close()


def test_null_handling_throughout_pipeline(test_config, mock_gene_ids, mock_uniprot_mapping):
    """Test that NULL values are preserved throughout the pipeline."""
    # Create data with NULLs
    data_with_nulls = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002"],
        "gene_symbol": ["GENE1", "GENE2"],
        "go_term_count": [10, None],
        "go_biological_process_count": [7, None],
        "go_molecular_function_count": [2, None],
        "go_cellular_component_count": [1, None],
        "uniprot_annotation_score": [3, None],
        "has_pathway_membership": [True, None],
        "annotation_tier": ["partially_annotated", "poorly_annotated"],
        "annotation_score_normalized": [0.5, None],
    })

    store = PipelineStore.from_config(test_config)
    provenance = ProvenanceTracker.from_config(test_config)

    # Load to DuckDB
    load_to_duckdb(data_with_nulls, store, provenance)

    # Load back and verify NULLs preserved
    result = store.load_dataframe("annotation_completeness")

    # Gene with NULL GO should have NULL in result
    gene2 = result.filter(pl.col("gene_id") == "ENSG002")
    assert gene2["go_term_count"][0] is None
    assert gene2["annotation_score_normalized"][0] is None

    store.close()

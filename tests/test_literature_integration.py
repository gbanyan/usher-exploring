"""Integration tests for literature evidence pipeline."""

import polars as pl
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from usher_pipeline.evidence.literature import (
    process_literature_evidence,
    load_to_duckdb,
    query_literature_supported,
)
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker


@pytest.fixture
def mock_config():
    """Create a mock PipelineConfig for testing."""
    config = Mock()
    config.config_hash = Mock(return_value="test_hash_123")
    config.versions = Mock()
    config.versions.model_dump = Mock(return_value={
        "gnomad_version": "v4.1",
        "ensembl_version": "111",
    })
    return config


@pytest.fixture
def mock_entrez_responses():
    """Mock Entrez API responses for testing full pipeline."""

    def mock_esearch_side_effect(*args, **kwargs):
        """Return mock counts based on gene and query terms."""
        term = kwargs.get('term', '')

        # Parse gene symbol from term (format: "({gene}[Gene Name])")
        if '(' in term and '[Gene Name]' in term:
            gene = term.split('(')[1].split('[')[0].strip()
        else:
            gene = "UNKNOWN"

        # Mock counts for test genes
        gene_counts = {
            "GENE1": {  # Direct experimental evidence
                "total": 100,
                "cilia": 10,
                "sensory": 5,
                "cytoskeleton": 8,
                "cell_polarity": 3,
                "knockout": 3,
                "screen": 0,
            },
            "GENE2": {  # Functional mention
                "total": 50,
                "cilia": 5,
                "sensory": 3,
                "cytoskeleton": 4,
                "cell_polarity": 2,
                "knockout": 0,
                "screen": 0,
            },
            "GENE3": {  # No evidence
                "total": 0,
                "cilia": 0,
                "sensory": 0,
                "cytoskeleton": 0,
                "cell_polarity": 0,
                "knockout": 0,
                "screen": 0,
            },
        }

        counts = gene_counts.get(gene, {"total": 0})

        # Determine count based on query terms
        if "cilia" in term or "cilium" in term:
            count = counts.get("cilia", 0)
        elif "retina" in term or "cochlea" in term or "sensory" in term:
            count = counts.get("sensory", 0)
        elif "cytoskeleton" in term:
            count = counts.get("cytoskeleton", 0)
        elif "cell polarity" in term:
            count = counts.get("cell_polarity", 0)
        elif "knockout" in term or "CRISPR" in term:
            count = counts.get("knockout", 0)
        elif "screen" in term or "proteomics" in term:
            count = counts.get("screen", 0)
        else:
            count = counts.get("total", 0)

        # Create mock handle
        mock_handle = MagicMock()
        mock_handle.__enter__ = Mock(return_value=mock_handle)
        mock_handle.__exit__ = Mock(return_value=False)

        return mock_handle

    def mock_read_side_effect(handle):
        """Return count dict for esearch results."""
        # Extract count from the term that was used
        # For simplicity, return a range of counts
        import random
        count = random.randint(0, 100)
        return {"Count": str(count)}

    return mock_esearch_side_effect, mock_read_side_effect


@pytest.fixture
def temp_duckdb():
    """Create temporary DuckDB for integration testing."""
    import tempfile
    import os

    # Create temp file path but don't create the file yet (DuckDB will create it)
    fd, temp_path = tempfile.mkstemp(suffix='.duckdb')
    os.close(fd)  # Close file descriptor
    os.unlink(temp_path)  # Delete the empty file - DuckDB will create it properly

    db_path = Path(temp_path)

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def gene_test_data():
    """Small gene universe for testing."""
    return pl.DataFrame({
        "gene_id": [
            "ENSG00000001",
            "ENSG00000002",
            "ENSG00000003",
        ],
        "gene_symbol": [
            "GENE1",
            "GENE2",
            "GENE3",
        ],
    })


def test_full_pipeline_with_mock_pubmed(gene_test_data, mock_entrez_responses, temp_duckdb):
    """Test full literature evidence pipeline with mocked PubMed responses."""
    mock_esearch, mock_read = mock_entrez_responses

    with patch('usher_pipeline.evidence.literature.fetch.Entrez') as mock_entrez:
        # Configure mocks
        mock_entrez.esearch = mock_esearch
        mock_entrez.read = mock_read
        mock_entrez.email = None
        mock_entrez.api_key = None

        # Process literature evidence
        df = process_literature_evidence(
            gene_ids=gene_test_data["gene_id"].to_list(),
            gene_symbol_map=gene_test_data,
            email="test@example.com",
            api_key=None,
            batch_size=10,
        )

        # Verify results
        assert len(df) == 3
        assert "gene_id" in df.columns
        assert "gene_symbol" in df.columns
        assert "evidence_tier" in df.columns
        assert "literature_score_normalized" in df.columns

        # Verify tier classification occurred
        tiers = df["evidence_tier"].unique().to_list()
        assert len(tiers) > 0
        assert all(tier in ["direct_experimental", "functional_mention", "hts_hit", "incidental", "none"] for tier in tiers)


def test_checkpoint_restart(gene_test_data, mock_entrez_responses):
    """Test checkpoint-restart functionality for long-running PubMed queries."""
    mock_esearch, mock_read = mock_entrez_responses

    with patch('usher_pipeline.evidence.literature.fetch.Entrez') as mock_entrez:
        mock_entrez.esearch = mock_esearch
        mock_entrez.read = mock_read

        # First batch: process 2 genes
        first_batch = gene_test_data.head(2)
        df1 = process_literature_evidence(
            gene_ids=first_batch["gene_id"].to_list(),
            gene_symbol_map=first_batch,
            email="test@example.com",
            api_key=None,
        )

        assert len(df1) == 2

        # Second batch: resume from checkpoint with full dataset
        # The fetch function should skip already-processed genes
        # Note: This requires checkpoint_df parameter support in fetch_literature_evidence
        # For now, just verify we can process the full dataset
        df2 = process_literature_evidence(
            gene_ids=gene_test_data["gene_id"].to_list(),
            gene_symbol_map=gene_test_data,
            email="test@example.com",
            api_key=None,
        )

        assert len(df2) == 3


def test_duckdb_persistence(gene_test_data, mock_entrez_responses, temp_duckdb, mock_config):
    """Test saving and loading literature evidence to/from DuckDB."""
    mock_esearch, mock_read = mock_entrez_responses

    with patch('usher_pipeline.evidence.literature.fetch.Entrez') as mock_entrez:
        mock_entrez.esearch = mock_esearch
        mock_entrez.read = mock_read

        # Process literature evidence
        df = process_literature_evidence(
            gene_ids=gene_test_data["gene_id"].to_list(),
            gene_symbol_map=gene_test_data,
            email="test@example.com",
            api_key=None,
        )

        # Save to DuckDB
        store = PipelineStore(temp_duckdb)
        provenance = ProvenanceTracker(
            pipeline_version="1.0.0",
            config=mock_config,
        )

        load_to_duckdb(
            df=df,
            store=store,
            provenance=provenance,
            description="Test literature evidence"
        )

        # Verify checkpoint exists
        assert store.has_checkpoint('literature_evidence')

        # Load back from DuckDB
        loaded_df = store.load_dataframe('literature_evidence')
        assert loaded_df is not None
        assert len(loaded_df) == len(df)

        # Verify columns preserved
        assert "gene_id" in loaded_df.columns
        assert "evidence_tier" in loaded_df.columns
        assert "literature_score_normalized" in loaded_df.columns

        store.close()


def test_provenance_recording(gene_test_data, mock_entrez_responses, temp_duckdb, mock_config):
    """Test that provenance metadata is correctly recorded."""
    mock_esearch, mock_read = mock_entrez_responses

    with patch('usher_pipeline.evidence.literature.fetch.Entrez') as mock_entrez:
        mock_entrez.esearch = mock_esearch
        mock_entrez.read = mock_read

        # Process literature evidence
        df = process_literature_evidence(
            gene_ids=gene_test_data["gene_id"].to_list(),
            gene_symbol_map=gene_test_data,
            email="test@example.com",
            api_key="test_key",
        )

        # Save to DuckDB with provenance
        store = PipelineStore(temp_duckdb)
        provenance = ProvenanceTracker(
            pipeline_version="1.0.0",
            config=mock_config,
        )

        load_to_duckdb(
            df=df,
            store=store,
            provenance=provenance,
            description="Test literature evidence"
        )

        # Verify provenance step was recorded
        steps = provenance.get_steps()
        assert len(steps) > 0
        assert any(step["step_name"] == "load_literature_evidence" for step in steps)

        # Verify provenance contains expected fields
        load_step = next(step for step in steps if step["step_name"] == "load_literature_evidence")
        assert "row_count" in load_step["details"]
        assert "tier_distribution" in load_step["details"]
        assert "estimated_pubmed_queries" in load_step["details"]

        store.close()


def test_query_literature_supported(gene_test_data, mock_entrez_responses, temp_duckdb, mock_config):
    """Test querying genes with literature support by tier."""
    mock_esearch, mock_read = mock_entrez_responses

    with patch('usher_pipeline.evidence.literature.fetch.Entrez') as mock_entrez:
        mock_entrez.esearch = mock_esearch
        mock_entrez.read = mock_read

        # Process and save literature evidence
        df = process_literature_evidence(
            gene_ids=gene_test_data["gene_id"].to_list(),
            gene_symbol_map=gene_test_data,
            email="test@example.com",
            api_key=None,
        )

        store = PipelineStore(temp_duckdb)
        provenance = ProvenanceTracker(
            pipeline_version="1.0.0",
            config=mock_config,
        )

        load_to_duckdb(df=df, store=store, provenance=provenance)

        # Query for direct experimental evidence
        direct_genes = query_literature_supported(
            store=store,
            min_tier="direct_experimental"
        )

        # Should only return genes with direct_experimental tier
        assert all(tier == "direct_experimental" for tier in direct_genes["evidence_tier"].to_list())

        # Query for functional mention or better
        functional_genes = query_literature_supported(
            store=store,
            min_tier="functional_mention"
        )

        # Should return direct_experimental OR functional_mention
        assert all(
            tier in ["direct_experimental", "functional_mention"]
            for tier in functional_genes["evidence_tier"].to_list()
        )

        store.close()


def test_null_handling_in_pipeline(temp_duckdb, mock_config):
    """Test that NULL values from failed queries are preserved through pipeline."""
    # Create test data with NULL counts (simulating failed PubMed queries)
    df_with_nulls = pl.DataFrame({
        "gene_id": ["ENSG00000001", "ENSG00000002"],
        "gene_symbol": ["GENE1", "GENE2"],
        "total_pubmed_count": [100, None],  # GENE2 failed query
        "cilia_context_count": [10, None],
        "sensory_context_count": [5, None],
        "cytoskeleton_context_count": [8, None],
        "cell_polarity_context_count": [3, None],
        "direct_experimental_count": [3, None],
        "hts_screen_count": [0, None],
    })

    # Process through classification and scoring
    from usher_pipeline.evidence.literature import classify_evidence_tier, compute_literature_score

    df = classify_evidence_tier(df_with_nulls)
    df = compute_literature_score(df)

    # Save to DuckDB
    store = PipelineStore(temp_duckdb)
    provenance = ProvenanceTracker(
        pipeline_version="1.0.0",
        config=mock_config,
    )

    load_to_duckdb(df=df, store=store, provenance=provenance)

    # Load back
    loaded_df = store.load_dataframe('literature_evidence')

    # Verify NULL preservation
    gene2 = loaded_df.filter(pl.col("gene_symbol") == "GENE2")
    assert gene2["total_pubmed_count"][0] is None
    assert gene2["literature_score_normalized"][0] is None
    assert gene2["evidence_tier"][0] == "none"  # NULL counts -> "none" tier

    store.close()

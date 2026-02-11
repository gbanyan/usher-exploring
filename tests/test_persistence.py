"""Tests for persistence layer (DuckDB store and provenance tracking)."""

import json
from pathlib import Path

import polars as pl
import pytest

from usher_pipeline.config.loader import load_config
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker


@pytest.fixture
def test_config(tmp_path):
    """Create a minimal test config."""
    # Create a minimal config YAML
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text("""
data_dir: {data_dir}
cache_dir: {cache_dir}
duckdb_path: {duckdb_path}
versions:
  ensembl_release: 113
  gnomad_version: "v4.1"
  gtex_version: "v8"
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
""".format(
        data_dir=str(tmp_path / "data"),
        cache_dir=str(tmp_path / "cache"),
        duckdb_path=str(tmp_path / "test.duckdb"),
    ))
    return load_config(config_path)


# ============================================================================
# DuckDB Store Tests
# ============================================================================

def test_store_creates_database(tmp_path):
    """Test that PipelineStore creates .duckdb file at specified path."""
    db_path = tmp_path / "test.duckdb"
    assert not db_path.exists()

    store = PipelineStore(db_path)
    store.close()

    assert db_path.exists()


def test_save_and_load_polars(tmp_path):
    """Test saving and loading polars DataFrame."""
    store = PipelineStore(tmp_path / "test.duckdb")

    # Create test DataFrame
    df = pl.DataFrame({
        "gene": ["BRCA1", "TP53", "MYO7A"],
        "score": [0.95, 0.88, 0.92],
        "chr": ["17", "17", "11"],
    })

    # Save
    store.save_dataframe(df, "genes", "test genes")

    # Load
    loaded = store.load_dataframe("genes", as_polars=True)

    # Verify
    assert loaded.shape == df.shape
    assert loaded.columns == df.columns
    assert loaded["gene"].to_list() == df["gene"].to_list()
    assert loaded["score"].to_list() == df["score"].to_list()

    store.close()


def test_save_and_load_pandas(tmp_path):
    """Test saving and loading pandas DataFrame."""
    pd = pytest.importorskip("pandas")

    store = PipelineStore(tmp_path / "test.duckdb")

    # Create test DataFrame
    df = pd.DataFrame({
        "gene": ["BRCA1", "TP53"],
        "score": [0.95, 0.88],
    })

    # Save
    store.save_dataframe(df, "genes_pandas", "pandas test")

    # Load as pandas
    loaded = store.load_dataframe("genes_pandas", as_polars=False)

    # Verify
    assert loaded.shape == df.shape
    assert list(loaded.columns) == list(df.columns)
    assert loaded["gene"].tolist() == df["gene"].tolist()

    store.close()


def test_checkpoint_lifecycle(tmp_path):
    """Test checkpoint lifecycle: save -> has -> delete -> not has."""
    store = PipelineStore(tmp_path / "test.duckdb")

    df = pl.DataFrame({"col": [1, 2, 3]})

    # Initially no checkpoint
    assert not store.has_checkpoint("test_table")

    # Save creates checkpoint
    store.save_dataframe(df, "test_table", "test")
    assert store.has_checkpoint("test_table")

    # Delete removes checkpoint
    store.delete_checkpoint("test_table")
    assert not store.has_checkpoint("test_table")

    # Load returns None after deletion
    assert store.load_dataframe("test_table") is None

    store.close()


def test_list_checkpoints(tmp_path):
    """Test listing checkpoints returns metadata."""
    store = PipelineStore(tmp_path / "test.duckdb")

    # Create 3 tables
    for i in range(3):
        df = pl.DataFrame({"val": list(range(i + 1))})
        store.save_dataframe(df, f"table_{i}", f"description {i}")

    # List checkpoints
    checkpoints = store.list_checkpoints()

    assert len(checkpoints) == 3

    # Verify metadata structure
    for ckpt in checkpoints:
        assert "table_name" in ckpt
        assert "created_at" in ckpt
        assert "row_count" in ckpt
        assert "description" in ckpt

    # Verify specific metadata
    table_0 = [c for c in checkpoints if c["table_name"] == "table_0"][0]
    assert table_0["row_count"] == 1
    assert table_0["description"] == "description 0"

    store.close()


def test_export_parquet(tmp_path):
    """Test exporting table to Parquet."""
    store = PipelineStore(tmp_path / "test.duckdb")

    # Create and save DataFrame
    df = pl.DataFrame({
        "gene": ["BRCA1", "TP53", "MYO7A"],
        "score": [0.95, 0.88, 0.92],
    })
    store.save_dataframe(df, "genes", "test genes")

    # Export to Parquet
    parquet_path = tmp_path / "output" / "genes.parquet"
    store.export_parquet("genes", parquet_path)

    # Verify Parquet file exists and is readable
    assert parquet_path.exists()
    loaded_from_parquet = pl.read_parquet(parquet_path)
    assert loaded_from_parquet.shape == df.shape
    assert loaded_from_parquet["gene"].to_list() == df["gene"].to_list()

    store.close()


def test_load_nonexistent_returns_none(tmp_path):
    """Test that loading non-existent table returns None."""
    store = PipelineStore(tmp_path / "test.duckdb")

    result = store.load_dataframe("nonexistent_table")
    assert result is None

    store.close()


def test_context_manager(tmp_path):
    """Test context manager support."""
    db_path = tmp_path / "test.duckdb"

    df = pl.DataFrame({"col": [1, 2, 3]})

    # Use context manager
    with PipelineStore(db_path) as store:
        store.save_dataframe(df, "test_table", "test")
        assert store.has_checkpoint("test_table")

    # Connection should be closed after context exit
    # Open a new connection to verify data persists
    with PipelineStore(db_path) as store:
        loaded = store.load_dataframe("test_table")
        assert loaded is not None
        assert loaded.shape == df.shape


# ============================================================================
# Provenance Tests
# ============================================================================

def test_provenance_metadata_structure(test_config):
    """Test that provenance metadata has all required keys."""
    tracker = ProvenanceTracker("0.1.0", test_config)

    metadata = tracker.create_metadata()

    assert "pipeline_version" in metadata
    assert "data_source_versions" in metadata
    assert "config_hash" in metadata
    assert "created_at" in metadata
    assert "processing_steps" in metadata

    assert metadata["pipeline_version"] == "0.1.0"
    assert isinstance(metadata["data_source_versions"], dict)
    assert isinstance(metadata["config_hash"], str)
    assert len(metadata["processing_steps"]) == 0


def test_provenance_records_steps(test_config):
    """Test that processing steps are recorded with timestamps."""
    tracker = ProvenanceTracker("0.1.0", test_config)

    # Record steps
    tracker.record_step("download_genes")
    tracker.record_step("filter_protein_coding", {"count": 19000})

    metadata = tracker.create_metadata()
    steps = metadata["processing_steps"]

    assert len(steps) == 2

    # Check first step
    assert steps[0]["step_name"] == "download_genes"
    assert "timestamp" in steps[0]

    # Check second step
    assert steps[1]["step_name"] == "filter_protein_coding"
    assert steps[1]["details"]["count"] == 19000
    assert "timestamp" in steps[1]


def test_provenance_sidecar_roundtrip(test_config, tmp_path):
    """Test saving and loading provenance sidecar."""
    tracker = ProvenanceTracker("0.1.0", test_config)
    tracker.record_step("test_step", {"key": "value"})

    # Save sidecar
    output_path = tmp_path / "output.parquet"
    tracker.save_sidecar(output_path)

    # Verify sidecar file exists
    sidecar_path = tmp_path / "output.provenance.json"
    assert sidecar_path.exists()

    # Load and verify content
    loaded = ProvenanceTracker.load_sidecar(sidecar_path)

    assert loaded["pipeline_version"] == "0.1.0"
    assert loaded["config_hash"] == test_config.config_hash()
    assert len(loaded["processing_steps"]) == 1
    assert loaded["processing_steps"][0]["step_name"] == "test_step"


def test_provenance_config_hash_included(test_config):
    """Test that config hash is included in metadata."""
    tracker = ProvenanceTracker("0.1.0", test_config)

    metadata = tracker.create_metadata()

    assert metadata["config_hash"] == test_config.config_hash()


def test_provenance_save_to_store(test_config, tmp_path):
    """Test saving provenance to DuckDB store."""
    store = PipelineStore(tmp_path / "test.duckdb")
    tracker = ProvenanceTracker("0.1.0", test_config)
    tracker.record_step("test_step")

    # Save to store
    tracker.save_to_store(store)

    # Verify _provenance table exists and has data
    result = store.conn.execute("SELECT * FROM _provenance").fetchall()
    assert len(result) > 0

    # Verify content
    row = result[0]
    assert row[0] == "0.1.0"  # version
    assert row[1] == test_config.config_hash()  # config_hash

    # Verify steps_json is valid JSON
    steps = json.loads(row[3])
    assert len(steps) == 1
    assert steps[0]["step_name"] == "test_step"

    store.close()

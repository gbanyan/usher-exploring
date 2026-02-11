"""Tests for configuration loading and validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from usher_pipeline.config import load_config, load_config_with_overrides
from usher_pipeline.config.schema import PipelineConfig


def test_load_valid_config():
    """Test loading valid default configuration."""
    config = load_config("config/default.yaml")

    assert isinstance(config, PipelineConfig)
    assert config.versions.ensembl_release == 113
    assert config.versions.gnomad_version == "v4.1"
    assert config.api.rate_limit_per_second == 5
    assert config.api.max_retries == 5
    assert config.scoring.gnomad == 0.20


def test_invalid_config_missing_field(tmp_path):
    """Test that missing required field raises ValidationError."""
    invalid_config = tmp_path / "invalid.yaml"
    invalid_config.write_text("""
versions:
  ensembl_release: 113
api:
  rate_limit_per_second: 5
scoring:
  gnomad: 0.20
""")

    with pytest.raises(ValidationError) as exc_info:
        load_config(invalid_config)

    # Check that error mentions missing field
    assert "data_dir" in str(exc_info.value)


def test_invalid_ensembl_release(tmp_path):
    """Test that ensembl_release < 100 raises ValidationError."""
    invalid_config = tmp_path / "invalid_ensembl.yaml"
    invalid_config.write_text("""
data_dir: data
cache_dir: data/cache
duckdb_path: data/pipeline.duckdb
versions:
  ensembl_release: 99
  gnomad_version: v4.1
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
""")

    with pytest.raises(ValidationError) as exc_info:
        load_config(invalid_config)

    # Check that error mentions ensembl_release constraint
    error_str = str(exc_info.value)
    assert "ensembl_release" in error_str
    assert "greater than or equal to 100" in error_str.lower() or "100" in error_str


def test_config_hash_deterministic():
    """Test that config hash is deterministic and changes with config."""
    config1 = load_config("config/default.yaml")
    config2 = load_config("config/default.yaml")

    # Same config should produce same hash
    assert config1.config_hash() == config2.config_hash()

    # Hash should be SHA-256 (64 hex chars)
    assert len(config1.config_hash()) == 64

    # Different config should produce different hash
    config3 = load_config_with_overrides(
        "config/default.yaml",
        {"api.rate_limit_per_second": 10},
    )
    assert config3.config_hash() != config1.config_hash()


def test_config_creates_directories(tmp_path):
    """Test that loading config creates data and cache directories."""
    config_file = tmp_path / "test_config.yaml"

    # Use non-existent directories
    data_dir = tmp_path / "test_data"
    cache_dir = tmp_path / "test_cache"

    config_file.write_text(f"""
data_dir: {data_dir}
cache_dir: {cache_dir}
duckdb_path: {tmp_path / "test.duckdb"}
versions:
  ensembl_release: 113
  gnomad_version: v4.1
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
""")

    # Directories should not exist before loading
    assert not data_dir.exists()
    assert not cache_dir.exists()

    # Load config
    config = load_config(config_file)

    # Directories should be created
    assert data_dir.exists()
    assert cache_dir.exists()
    assert data_dir.is_dir()
    assert cache_dir.is_dir()

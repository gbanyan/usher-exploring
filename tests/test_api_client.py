"""Tests for API client with caching and retry logic."""

import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from usher_pipeline.api_clients.base import CachedAPIClient
from usher_pipeline.config import load_config


def test_client_creates_cache_dir(tmp_path):
    """Test that client creates cache directory if it doesn't exist."""
    cache_dir = tmp_path / "nonexistent_cache"

    # Directory should not exist before creating client
    assert not cache_dir.exists()

    # Create client
    client = CachedAPIClient(cache_dir=cache_dir)

    # Directory should be created
    assert cache_dir.exists()
    assert cache_dir.is_dir()


def test_client_caches_response(tmp_path):
    """Test that responses are cached and retrieved from cache."""
    cache_dir = tmp_path / "cache"
    client = CachedAPIClient(cache_dir=cache_dir, rate_limit=100)

    test_url = "https://api.example.com/test"
    mock_response_data = {"data": "test"}

    # Mock the underlying session.get method
    with patch.object(client.session, "get") as mock_get:
        # Configure mock to return a response object
        mock_response_1 = Mock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = mock_response_data
        mock_response_1.from_cache = False
        mock_response_1.raise_for_status = Mock()

        mock_response_2 = Mock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = mock_response_data
        mock_response_2.from_cache = True
        mock_response_2.raise_for_status = Mock()

        # First call: not from cache
        mock_get.return_value = mock_response_1
        response_1 = client.get(test_url)
        assert response_1.status_code == 200

        # Second call: from cache
        mock_get.return_value = mock_response_2
        response_2 = client.get(test_url)
        assert response_2.status_code == 200

        # Verify both calls were made to session.get
        assert mock_get.call_count == 2


def test_client_from_config(tmp_path):
    """Test creating client from PipelineConfig."""
    # Create a test config file
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(f"""
data_dir: {tmp_path / "data"}
cache_dir: {tmp_path / "cache"}
duckdb_path: {tmp_path / "test.duckdb"}
versions:
  ensembl_release: 113
  gnomad_version: v4.1
api:
  rate_limit_per_second: 10
  max_retries: 3
  cache_ttl_seconds: 3600
  timeout_seconds: 60
scoring:
  gnomad: 0.20
  expression: 0.20
  annotation: 0.15
  localization: 0.15
  animal_model: 0.15
  literature: 0.15
""")

    # Load config and create client
    config = load_config(config_file)
    client = CachedAPIClient.from_config(config)

    # Verify settings were applied
    assert client.rate_limit == 10
    assert client.max_retries == 3
    assert client.timeout == 60
    assert client.cache_dir == tmp_path / "cache"


def test_rate_limit_respected(tmp_path):
    """Test that rate limiting sleeps between non-cached requests."""
    cache_dir = tmp_path / "cache"
    client = CachedAPIClient(cache_dir=cache_dir, rate_limit=10)

    test_url = "https://api.example.com/test"

    with patch("time.sleep") as mock_sleep, patch.object(
        client.session, "get"
    ) as mock_get:
        # Configure mock to return non-cached response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.from_cache = False
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Make request
        client.get(test_url)

        # Verify sleep was called with correct rate limit
        mock_sleep.assert_called_once()
        # Rate limit is 10 req/sec = 1/10 = 0.1 seconds between requests
        assert mock_sleep.call_args[0][0] == pytest.approx(0.1)


def test_rate_limit_skipped_for_cached(tmp_path):
    """Test that cached requests don't trigger rate limiting sleep."""
    cache_dir = tmp_path / "cache"
    client = CachedAPIClient(cache_dir=cache_dir, rate_limit=10)

    test_url = "https://api.example.com/test"

    with patch("time.sleep") as mock_sleep, patch.object(
        client.session, "get"
    ) as mock_get:
        # Configure mock to return cached response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.from_cache = True
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Make request
        client.get(test_url)

        # Verify sleep was NOT called for cached response
        mock_sleep.assert_not_called()

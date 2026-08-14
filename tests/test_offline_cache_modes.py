"""Fail-closed checks for explicit local raw-cache reprocessing modes."""

import polars as pl
import pytest

from usher_pipeline.evidence.literature.fetch import (
    download_bulk_files,
    fetch_context_pmid_sets,
)
from usher_pipeline.evidence.localization.fetch import fetch_hpa_subcellular


def test_literature_cache_only_rejects_missing_bulk_sources(tmp_path):
    with pytest.raises(FileNotFoundError, match="local bulk sources"):
        download_bulk_files(tmp_path, cache_only=True)


def test_literature_cache_only_rejects_missing_context_cache(tmp_path):
    with pytest.raises(FileNotFoundError, match="local PubMed context cache"):
        fetch_context_pmid_sets(
            "offline@example.invalid",
            cache_path=tmp_path / "pubmed_context_sets.json",
            cache_only=True,
        )


def test_literature_cache_only_rejects_malformed_context_cache(tmp_path):
    cache = tmp_path / "pubmed_context_sets.json"
    cache.write_text('{"contexts": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="schema-mismatched"):
        fetch_context_pmid_sets(
            "offline@example.invalid",
            cache_path=cache,
            cache_only=True,
        )


def test_localization_cache_only_rejects_missing_hpa_source(tmp_path):
    with pytest.raises(FileNotFoundError, match="local HPA raw source"):
        fetch_hpa_subcellular(
            gene_ids=["ENSG00000000001"],
            gene_symbol_map=pl.DataFrame({
                "gene_id": ["ENSG00000000001"],
                "gene_symbol": ["GENE1"],
            }),
            cache_dir=tmp_path,
            cache_only=True,
        )

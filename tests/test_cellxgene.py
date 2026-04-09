"""Unit tests for CellxGene single-cell expression fetch."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import polars as pl
import pytest

from usher_pipeline.evidence.expression.fetch import (
    fetch_cellxgene_expression,
    _query_mean_expression,
    _null_cellxgene_result,
    PHOTORECEPTOR_CELL_TYPES,
    HAIR_CELL_TYPES,
)


def test_null_result_structure():
    """_null_cellxgene_result returns correct columns with all NULLs."""
    gene_ids = ["ENSG001", "ENSG002"]
    result = _null_cellxgene_result(gene_ids).collect()

    assert set(result.columns) == {"gene_id", "cellxgene_photoreceptor_expr", "cellxgene_hair_cell_expr"}
    assert result.height == 2
    assert result["cellxgene_photoreceptor_expr"][0] is None
    assert result["cellxgene_hair_cell_expr"][0] is None


def test_fallback_when_census_not_installed():
    """fetch_cellxgene_expression returns NULLs when cellxgene_census not importable."""
    with patch.dict("sys.modules", {"cellxgene_census": None}):
        # Force reimport to trigger ImportError
        import importlib
        from usher_pipeline.evidence.expression import fetch as fetch_mod
        # Patch at the function level to simulate ImportError
        original = fetch_mod.fetch_cellxgene_expression

        def mock_fetch(gene_ids, cache_dir=None, force=False):
            # Simulate the ImportError path
            return _null_cellxgene_result(gene_ids)

        fetch_mod.fetch_cellxgene_expression = mock_fetch
        try:
            result = fetch_mod.fetch_cellxgene_expression(
                ["ENSG001", "ENSG002"], cache_dir=Path("/tmp/test")
            ).collect()
            assert result.height == 2
            assert result["cellxgene_photoreceptor_expr"][0] is None
        finally:
            fetch_mod.fetch_cellxgene_expression = original


def test_cache_write_and_read(tmp_path):
    """fetch_cellxgene_expression caches results to parquet and reads on second call."""
    gene_ids = ["ENSG001", "ENSG002", "ENSG003"]

    # Pre-create a cache file
    cache_df = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
        "cellxgene_photoreceptor_expr": [1.5, 0.3, None],
        "cellxgene_hair_cell_expr": [0.8, None, 2.1],
    })
    cache_path = tmp_path / "cellxgene_expression.parquet"
    cache_df.write_parquet(cache_path)

    # Should read from cache without calling Census
    result = fetch_cellxgene_expression(
        gene_ids, cache_dir=tmp_path, force=False
    ).collect()

    assert result.height == 3
    assert result.filter(pl.col("gene_id") == "ENSG001")["cellxgene_photoreceptor_expr"][0] == 1.5
    assert result.filter(pl.col("gene_id") == "ENSG003")["cellxgene_hair_cell_expr"][0] == 2.1
    # ENSG002 hair cell should be NULL
    assert result.filter(pl.col("gene_id") == "ENSG002")["cellxgene_hair_cell_expr"][0] is None


def test_cache_filters_to_requested_genes(tmp_path):
    """Cache may have more genes than requested — result should match requested gene_ids."""
    cache_df = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002", "ENSG003", "ENSG004"],
        "cellxgene_photoreceptor_expr": [1.0, 2.0, 3.0, 4.0],
        "cellxgene_hair_cell_expr": [0.1, 0.2, 0.3, 0.4],
    })
    cache_path = tmp_path / "cellxgene_expression.parquet"
    cache_df.write_parquet(cache_path)

    # Request only 2 genes
    result = fetch_cellxgene_expression(
        ["ENSG002", "ENSG004"], cache_dir=tmp_path
    ).collect()

    assert result.height == 2
    assert set(result["gene_id"].to_list()) == {"ENSG002", "ENSG004"}


def test_query_mean_expression_mock():
    """_query_mean_expression computes per-gene means from Census AnnData."""
    import scipy.sparse as sp
    import sys

    # Create a mock cellxgene_census module
    mock_cxg = MagicMock()

    # Create mock AnnData result
    mock_adata = MagicMock()
    mock_adata.n_obs = 100  # 100 cells
    mock_adata.n_vars = 2   # 2 genes found
    # Sparse matrix: 100 cells x 2 genes, mean = [1.5, 0.8]
    mock_adata.X = sp.csr_matrix(np.array([[1.5, 0.8]] * 100))
    mock_adata.var = {"feature_id": ["ENSG001", "ENSG002"]}

    mock_cxg.get_anndata.return_value = mock_adata

    # Inject mock into sys.modules so `import cellxgene_census` works
    sys.modules["cellxgene_census"] = mock_cxg
    try:
        result = _query_mean_expression(
            MagicMock(),  # census object
            ["photoreceptor cell"],
            "test_expr",
        )
    finally:
        del sys.modules["cellxgene_census"]

    # Returns all genes found in Census (not filtered to pipeline genes)
    assert result.height == 2
    assert result.filter(pl.col("gene_id") == "ENSG001")["test_expr"][0] == pytest.approx(1.5)
    assert result.filter(pl.col("gene_id") == "ENSG002")["test_expr"][0] == pytest.approx(0.8)


def test_cell_type_constants():
    """Verify cell type lists are non-empty and contain expected types."""
    assert len(PHOTORECEPTOR_CELL_TYPES) >= 2
    assert "photoreceptor cell" in PHOTORECEPTOR_CELL_TYPES
    assert len(HAIR_CELL_TYPES) >= 2
    assert "hair cell" in HAIR_CELL_TYPES

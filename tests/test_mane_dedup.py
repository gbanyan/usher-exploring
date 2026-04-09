"""Test MANE Select-based gene deduplication in scoring."""

import polars as pl
import pytest

from usher_pipeline.config.schema import ScoringWeights
from usher_pipeline.persistence.duckdb_store import PipelineStore
from usher_pipeline.scoring.integration import compute_composite_scores


def _setup_db_with_mane(tmp_path, mane_rows):
    """Create test DuckDB with gene_universe, evidence tables, and mane_select."""
    db_path = tmp_path / "test.duckdb"
    store = PipelineStore(db_path)

    # gene_universe: two Ensembl IDs for same gene_symbol
    gene_universe = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
        "gene_symbol": ["GENEA", "GENEA", "GENEB"],
    })
    store.save_dataframe(gene_universe, "gene_universe", "test gene universe")

    # gnomAD: ENSG002 has gnomAD data, ENSG001 does not
    gnomad = pl.DataFrame({
        "gene_id": ["ENSG002", "ENSG003"],
        "loeuf_normalized": [0.5, 0.7],
        "quality_flag": ["measured", "measured"],
    })
    store.save_dataframe(gnomad, "gnomad_constraint", "test gnomad")

    # MANE Select table
    mane = pl.DataFrame(mane_rows)
    store.save_dataframe(mane, "mane_select", "test mane")

    # Empty evidence tables
    for table_name, score_col in [
        ("tissue_expression", "expression_score_normalized"),
        ("annotation_completeness", "annotation_score_normalized"),
        ("subcellular_localization", "localization_score_normalized"),
        ("animal_model_phenotypes", "animal_model_score_normalized"),
        ("literature_evidence", "literature_score_normalized"),
    ]:
        empty = pl.DataFrame({"gene_id": pl.Series([], dtype=pl.Utf8), score_col: pl.Series([], dtype=pl.Float64)})
        store.save_dataframe(empty, table_name, f"test {table_name}")

    return store


def test_mane_preferred_over_gnomad(tmp_path):
    """MANE Select ID should be preferred even when gnomAD data exists on another ID."""
    store = _setup_db_with_mane(tmp_path, {
        "ensembl_gene_id": ["ENSG001"],
        "ensembl_transcript_id": ["ENST001"],
        "gene_symbol": ["GENEA"],
        "refseq_transcript_id": ["NM_001"],
        "mane_status": ["MANE Select"],
    })

    weights = ScoringWeights()
    result = compute_composite_scores(store, weights)

    # GENEA should use ENSG001 (MANE Select), not ENSG002 (has gnomAD)
    genea = result.filter(pl.col("gene_symbol") == "GENEA")
    assert genea.height == 1
    assert genea["gene_id"][0] == "ENSG001"

    store.close()


def test_gnomad_fallback_when_mane_empty(tmp_path):
    """With empty MANE table, fall back to gnomAD proxy."""
    store = _setup_db_with_mane(tmp_path, {
        "ensembl_gene_id": pl.Series([], dtype=pl.Utf8),
        "ensembl_transcript_id": pl.Series([], dtype=pl.Utf8),
        "gene_symbol": pl.Series([], dtype=pl.Utf8),
        "refseq_transcript_id": pl.Series([], dtype=pl.Utf8),
        "mane_status": pl.Series([], dtype=pl.Utf8),
    })

    weights = ScoringWeights()
    result = compute_composite_scores(store, weights)

    # GENEA should use ENSG002 (has gnomAD), since no MANE data
    genea = result.filter(pl.col("gene_symbol") == "GENEA")
    assert genea.height == 1
    assert genea["gene_id"][0] == "ENSG002"

    store.close()


def test_scoring_works_without_mane_table(tmp_path):
    """Scoring should still work if mane_select table doesn't exist (graceful fallback)."""
    db_path = tmp_path / "test.duckdb"
    store = PipelineStore(db_path)

    gene_universe = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002"],
        "gene_symbol": ["GENEA", "GENEA"],
    })
    store.save_dataframe(gene_universe, "gene_universe", "test")

    gnomad = pl.DataFrame({
        "gene_id": ["ENSG002"],
        "loeuf_normalized": [0.5],
        "quality_flag": ["measured"],
    })
    store.save_dataframe(gnomad, "gnomad_constraint", "test")

    # NO mane_select table at all

    for table_name, score_col in [
        ("tissue_expression", "expression_score_normalized"),
        ("annotation_completeness", "annotation_score_normalized"),
        ("subcellular_localization", "localization_score_normalized"),
        ("animal_model_phenotypes", "animal_model_score_normalized"),
        ("literature_evidence", "literature_score_normalized"),
    ]:
        empty = pl.DataFrame({"gene_id": pl.Series([], dtype=pl.Utf8), score_col: pl.Series([], dtype=pl.Float64)})
        store.save_dataframe(empty, table_name, f"test {table_name}")

    weights = ScoringWeights()
    result = compute_composite_scores(store, weights)

    # Should fall back to gnomAD proxy: ENSG002 preferred
    genea = result.filter(pl.col("gene_symbol") == "GENEA")
    assert genea.height == 1
    assert genea["gene_id"][0] == "ENSG002"

    store.close()

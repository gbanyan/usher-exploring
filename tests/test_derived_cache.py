"""Tests for fail-closed donor-derived evidence migration."""

from pathlib import Path

import duckdb
import polars as pl
import pytest

from usher_pipeline.evidence.derived_cache import (
    reindex_animal_models_from_donor,
    reindex_annotation_from_donor,
)


def _target_universe() -> pl.DataFrame:
    ids = [f"ENSG{i:011d}" for i in range(1, 20117)]
    return pl.DataFrame({
        "gene_id": ids,
        "gene_symbol": [f"SYM{i}" for i in range(1, 20117)],
    })


def _write_donor(
    path: Path,
    *,
    annotation_rows: list[tuple] | None = None,
    animal_rows: list[tuple] | None = None,
    donor_ids: list[str] | None = None,
) -> None:
    donor_ids = donor_ids or ["ENSG00000000001", "ENSG00000000002"]
    connection = duckdb.connect(str(path))
    connection.execute(
        "CREATE TABLE gene_universe AS SELECT * FROM (VALUES "
        + ",".join(f"('{gene_id}', 'DONOR_{gene_id}', NULL)" for gene_id in donor_ids)
        + ") AS t(gene_id, gene_symbol, uniprot_accession)"
    )
    connection.execute(
        """
        CREATE TABLE annotation_completeness (
            gene_id VARCHAR,
            gene_symbol VARCHAR,
            go_term_count BIGINT,
            go_biological_process_count BIGINT,
            go_molecular_function_count BIGINT,
            go_cellular_component_count BIGINT,
            has_pathway_membership BOOLEAN,
            uniprot_annotation_score BIGINT,
            annotation_tier VARCHAR,
            annotation_score_normalized DOUBLE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE animal_model_phenotypes (
            gene_id VARCHAR,
            mouse_ortholog VARCHAR,
            mouse_ortholog_confidence VARCHAR,
            zebrafish_ortholog VARCHAR,
            zebrafish_ortholog_confidence VARCHAR,
            has_mouse_phenotype BOOLEAN,
            has_zebrafish_phenotype BOOLEAN,
            has_impc_phenotype BOOLEAN,
            sensory_phenotype_count INTEGER,
            phenotype_categories VARCHAR,
            animal_model_score_normalized DOUBLE
        )
        """
    )
    if annotation_rows:
        connection.executemany(
            "INSERT INTO annotation_completeness VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            annotation_rows,
        )
    if animal_rows:
        connection.executemany(
            "INSERT INTO animal_model_phenotypes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            animal_rows,
        )
    connection.close()


def test_annotation_migration_intersects_exact_ids_recomputes_scores_and_audits(tmp_path):
    donor = tmp_path / "pipeline_source.duckdb"
    annotation_rows = [
        ("ENSG00000000001", "STALE", 20, 10, 5, 5, True, 4, "wrong", 0.01),
        ("ENSG00000000001", "STALE", 20, 10, 5, 5, True, 4, "wrong", 0.01),
        ("ENSG00000000002", "DONOR2", 1, 1, 0, 0, False, 1, "wrong", 0.99),
        ("ENSG00009999999", "ROGUE", 100, 100, 100, 100, True, 5, "wrong", 1.0),
    ]
    _write_donor(donor, annotation_rows=annotation_rows)

    result, audit, summary = reindex_annotation_from_donor(donor, _target_universe())

    assert result.height == 20116
    assert result["gene_id"].n_unique() == 20116
    assert result.filter(pl.col("gene_id") == "ENSG00000000001")["gene_symbol"].item() == "SYM1"
    assert result.filter(pl.col("gene_id") == "ENSG00000000001")["annotation_tier"].item() == "well_annotated"
    assert result.filter(pl.col("gene_id") == "ENSG00000000003")["annotation_score_normalized"].item() is None
    assert summary["mode"] == "derived_cache_reuse"
    assert summary["rogue_id_count"] == 1
    assert summary["merged_duplicate_id_count"] == 1
    assert audit.filter(pl.col("status") == "rogue_excluded").height == 1
    assert set(result["gene_id"].to_list()) == set(_target_universe()["gene_id"].to_list())


def test_animal_migration_recomputes_score_and_keeps_missing_ids_null(tmp_path):
    donor = tmp_path / "pipeline_source.duckdb"
    animal_rows = [
        ("ENSG00000000001", "MOUSE1", "HIGH", None, None, True, False, True, 4, "hearing", 0.0),
        ("ENSG00000000001", "MOUSE1", "HIGH", None, None, True, False, True, 4, "hearing", 0.0),
    ]
    _write_donor(donor, animal_rows=animal_rows)

    result, _audit, summary = reindex_animal_models_from_donor(donor, _target_universe())

    assert result.height == 20116
    assert result["gene_id"].n_unique() == 20116
    assert result.filter(pl.col("gene_id") == "ENSG00000000001")["animal_model_score_normalized"].item() > 0
    assert result.filter(pl.col("gene_id") == "ENSG00000000003")["animal_model_score_normalized"].item() is None
    assert result["animal_model_score_normalized"].drop_nulls().max() <= 1.0
    assert summary["merged_duplicate_id_count"] == 1


def test_derived_cache_rejects_conflicting_duplicate_source_rows(tmp_path):
    donor = tmp_path / "pipeline_source.duckdb"
    _write_donor(
        donor,
        annotation_rows=[
            ("ENSG00000000001", "STALE", 20, 10, 5, 5, True, 4, "wrong", 0.01),
            ("ENSG00000000001", "STALE", 21, 10, 5, 5, True, 4, "wrong", 0.01),
        ],
    )

    with pytest.raises(ValueError, match="conflicting duplicate source IDs"):
        reindex_annotation_from_donor(donor, _target_universe())


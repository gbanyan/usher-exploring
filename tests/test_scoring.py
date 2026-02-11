"""Unit tests for scoring module.

Tests:
- Known gene compilation and structure
- Scoring weight validation
- NULL preservation in composite scores
"""

import duckdb
import polars as pl
import pytest

from usher_pipeline.config.schema import ScoringWeights
from usher_pipeline.persistence.duckdb_store import PipelineStore
from usher_pipeline.scoring import (
    compile_known_genes,
    compute_composite_scores,
)


def test_compile_known_genes_returns_expected_structure():
    """Verify compile_known_genes returns expected structure with OMIM + SYSCILIA genes."""
    df = compile_known_genes()

    # Assert structure
    assert isinstance(df, pl.DataFrame)
    assert set(df.columns) == {"gene_symbol", "source", "confidence"}

    # Assert minimum expected count (10 OMIM Usher + 28 SYSCILIA SCGS v2 core)
    assert df.height >= 38, f"Expected at least 38 genes, got {df.height}"

    # Assert known genes are present
    gene_symbols = df.select("gene_symbol").to_series().to_list()
    assert "MYO7A" in gene_symbols, "MYO7A (Usher 1B) should be present"
    assert "IFT88" in gene_symbols, "IFT88 (SYSCILIA core) should be present"

    # Assert all confidence values are HIGH
    confidence_values = df.select("confidence").to_series().unique().to_list()
    assert confidence_values == ["HIGH"], f"Expected only HIGH confidence, got {confidence_values}"

    # Assert sources include both OMIM and SYSCILIA
    sources = df.select("source").to_series().unique().to_list()
    assert "omim_usher" in sources, "Expected omim_usher source"
    assert "syscilia_scgs_v2" in sources, "Expected syscilia_scgs_v2 source"


def test_compile_known_genes_no_duplicates_within_source():
    """Verify no duplicate gene_symbol within the same source."""
    df = compile_known_genes()

    # Group by source and check for duplicates within each source
    for source in df.select("source").to_series().unique().to_list():
        source_genes = df.filter(pl.col("source") == source).select("gene_symbol").to_series()
        unique_count = source_genes.unique().len()
        total_count = source_genes.len()

        assert unique_count == total_count, (
            f"Found duplicate genes in {source}: "
            f"{unique_count} unique out of {total_count} total"
        )


def test_scoring_weights_validate_sum_defaults():
    """ScoringWeights with defaults should pass validate_sum()."""
    weights = ScoringWeights()
    weights.validate_sum()  # Should not raise


def test_scoring_weights_validate_sum_custom_valid():
    """ScoringWeights with custom weights summing to 1.0 should pass."""
    weights = ScoringWeights(
        gnomad=0.30,
        expression=0.25,
        annotation=0.15,
        localization=0.10,
        animal_model=0.10,
        literature=0.10,
    )
    weights.validate_sum()  # Should not raise


def test_scoring_weights_validate_sum_invalid():
    """ScoringWeights with weights not summing to 1.0 should raise ValueError."""
    weights = ScoringWeights(
        gnomad=0.50,  # Increases sum to 1.35
    )

    with pytest.raises(ValueError, match="Scoring weights must sum to 1.0"):
        weights.validate_sum()


def test_scoring_weights_validate_sum_close_to_one():
    """Weights within 1e-6 of 1.0 should pass, outside should fail."""
    # Should pass: within tolerance
    weights_pass = ScoringWeights(
        gnomad=0.20,
        expression=0.20,
        annotation=0.15,
        localization=0.15,
        animal_model=0.15,
        literature=0.149999,  # Sum = 0.999999
    )
    weights_pass.validate_sum()  # Should not raise

    # Should fail: outside tolerance
    weights_fail = ScoringWeights(
        gnomad=0.20,
        expression=0.20,
        annotation=0.15,
        localization=0.15,
        animal_model=0.15,
        literature=0.14,  # Sum = 0.99
    )

    with pytest.raises(ValueError, match="Scoring weights must sum to 1.0"):
        weights_fail.validate_sum()


def test_null_preservation_in_composite(tmp_path):
    """Verify genes with no evidence get NULL composite scores, not zero."""
    # Create in-memory DuckDB with minimal synthetic data
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))

    # Create gene_universe with 3 genes
    gene_universe = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
        "gene_symbol": ["GENE1", "GENE2", "GENE3"],
        "hgnc_id": ["HGNC:001", "HGNC:002", "HGNC:003"],
    })
    conn.execute("CREATE TABLE gene_universe AS SELECT * FROM gene_universe")

    # Create gnomad_constraint: only genes 1 and 2 have scores
    gnomad = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002"],
        "loeuf_normalized": [0.8, 0.6],
        "quality_flag": ["measured", "measured"],
    })
    conn.execute("CREATE TABLE gnomad_constraint AS SELECT * FROM gnomad")

    # Create annotation_completeness: only gene 1 has score
    annotation = pl.DataFrame({
        "gene_id": ["ENSG001"],
        "annotation_score_normalized": [0.9],
        "annotation_tier": ["well_annotated"],
    })
    conn.execute("CREATE TABLE annotation_completeness AS SELECT * FROM annotation")

    # Create empty tables for other evidence layers
    for table_name, score_col in [
        ("tissue_expression", "expression_score_normalized"),
        ("subcellular_localization", "localization_score_normalized"),
        ("animal_model_phenotypes", "animal_model_score_normalized"),
        ("literature_evidence", "literature_score_normalized"),
    ]:
        empty_df = pl.DataFrame({
            "gene_id": [],
            score_col: [],
        })
        conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM empty_df")

    # Create PipelineStore wrapper
    store = PipelineStore(db_path)
    store.conn = conn  # Use the existing connection

    # Compute composite scores
    weights = ScoringWeights()  # Use defaults
    scored_df = compute_composite_scores(store, weights)

    # Verify structure
    assert scored_df.height == 3, f"Expected 3 genes, got {scored_df.height}"

    # Verify GENE3 (no evidence) has NULL composite_score
    gene3 = scored_df.filter(pl.col("gene_id") == "ENSG003")
    assert gene3.height == 1, "GENE3 should be present in results"
    assert gene3["composite_score"][0] is None, "GENE3 with no evidence should have NULL composite_score"
    assert gene3["evidence_count"][0] == 0, "GENE3 should have evidence_count = 0"
    assert gene3["quality_flag"][0] == "no_evidence", "GENE3 should have quality_flag = no_evidence"

    # Verify GENE1 (2 evidence layers) has non-NULL composite_score
    gene1 = scored_df.filter(pl.col("gene_id") == "ENSG001")
    assert gene1["composite_score"][0] is not None, "GENE1 with 2 evidence layers should have non-NULL score"
    assert gene1["evidence_count"][0] == 2, "GENE1 should have evidence_count = 2"
    assert gene1["quality_flag"][0] == "moderate_evidence", "GENE1 should have quality_flag = moderate_evidence"

    # Verify GENE2 (1 evidence layer) has non-NULL composite_score
    gene2 = scored_df.filter(pl.col("gene_id") == "ENSG002")
    assert gene2["composite_score"][0] is not None, "GENE2 with 1 evidence layer should have non-NULL score"
    assert gene2["evidence_count"][0] == 1, "GENE2 should have evidence_count = 1"
    assert gene2["quality_flag"][0] == "sparse_evidence", "GENE2 should have quality_flag = sparse_evidence"

    # Clean up
    conn.close()

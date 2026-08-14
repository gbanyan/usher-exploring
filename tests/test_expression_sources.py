"""Tests for expression source schemas and source-specific provenance."""

from pathlib import Path

import polars as pl
import pytest

from usher_pipeline.evidence.expression.fetch import (
    expression_source_metadata,
    fetch_gtex_expression,
    fetch_hpa_expression,
)


def _write_hpa(path: Path, rows: list[str], header: str) -> None:
    path.write_text(header + "\n" + "\n".join(rows) + "\n")


def test_hpa_categorical_source_is_explicitly_ordinal(tmp_path):
    _write_hpa(
        tmp_path / "hpa_normal_tissue.tsv",
        [
            "ENSG1\tGENE1\tretina\tcones\tLow\tApproved",
            "ENSG1\tGENE1\tretina\trods\tHigh\tApproved",
            "ENSG1\tGENE1\ttestis\tLeydig cells\tMedium\tApproved",
        ],
        "Gene\tGene name\tTissue\tCell type\tLevel\tReliability",
    )

    result = fetch_hpa_expression([], tmp_path).collect()

    assert "hpa_retina_protein_level" in result.columns
    assert "hpa_retina_protein_level_label" in result.columns
    assert "hpa_retina_ntpm" in result.columns
    assert not any(column.endswith("_tpm") for column in result.columns if column.startswith("hpa_"))
    assert result.filter(pl.col("gene_symbol") == "GENE1")["hpa_retina_protein_level"][0] == 3
    assert result.filter(pl.col("gene_symbol") == "GENE1")["hpa_retina_protein_level_label"][0] == "High"


def test_hpa_reliability_is_filtered_before_cell_type_aggregation(tmp_path):
    """Uncertain rows cannot elevate an accepted HPA tissue aggregate."""
    _write_hpa(
        tmp_path / "hpa_normal_tissue.tsv",
        [
            "ENSG1\tGENE1\tretina\tcones\tLow\tApproved",
            "ENSG1\tGENE1\tretina\trods\tHigh\tUncertain",
            "ENSG1\tGENE1\ttestis\tLeydig cells\tMedium\tSupported",
        ],
        "Gene\tGene name\tTissue\tCell type\tLevel\tReliability",
    )

    result = fetch_hpa_expression([], tmp_path).collect()

    assert result.filter(pl.col("gene_symbol") == "GENE1")["hpa_retina_protein_level"][0] == 1
    assert result.filter(pl.col("gene_symbol") == "GENE1")["hpa_retina_protein_level_label"][0] == "Low"


def test_hpa_aggregation_requires_reliability_column(tmp_path):
    _write_hpa(
        tmp_path / "hpa_normal_tissue.tsv",
        ["ENSG1\tGENE1\tretina\tcones\tHigh"],
        "Gene\tGene name\tTissue\tCell type\tLevel",
    )

    with pytest.raises(ValueError, match="Reliability"):
        fetch_hpa_expression([], tmp_path)


def test_hpa_ntpm_is_preferred_when_available(tmp_path):
    _write_hpa(
        tmp_path / "hpa_normal_tissue.tsv",
        [
            "ENSG1\tGENE1\tretina\tcones\tLow\t2.0\tApproved",
            "ENSG1\tGENE1\tretina\trods\tHigh\t6.0\tApproved",
        ],
        "Gene\tGene name\tTissue\tCell type\tLevel\tnTPM\tReliability",
    )

    result = fetch_hpa_expression([], tmp_path).collect()

    assert result["hpa_retina_ntpm"][0] == 4.0
    assert result["hpa_retina_protein_level"][0] is None


def test_hpa_ntpm_does_not_require_categorical_reliability_column(tmp_path):
    _write_hpa(
        tmp_path / "hpa_normal_tissue.tsv",
        [
            "ENSG1\tGENE1\tretina\tcones\tLow\t2.0",
            "ENSG1\tGENE1\ttestis\tLeydig cells\tHigh\t1.0",
        ],
        "Gene\tGene name\tTissue\tCell type\tLevel\tnTPM",
    )

    result = fetch_hpa_expression([], tmp_path).collect()

    assert result["hpa_retina_ntpm"][0] == 2.0


def test_gtex_retina_absence_is_structural_and_provenance_is_reproducible(tmp_path):
    _write_hpa(
        tmp_path / "hpa_normal_tissue.tsv",
        ["ENSG1\tGENE1\tretina\tcones\tHigh\tApproved"],
        "Gene\tGene name\tTissue\tCell type\tLevel\tReliability",
    )
    (tmp_path / "gtex_median_tpm.gct").write_text(
        "#1.2\n"
        "1\t2\n"
        "Name\tDescription\tBrain - Cerebellum\tTestis\tFallopian Tube\n"
        "ENSG1.1\tGENE1\t10\t2\t1\n"
    )

    gtex = fetch_gtex_expression(["ENSG1"], tmp_path).collect()
    metadata = expression_source_metadata(tmp_path, gtex)

    assert gtex["gtex_retina_tpm"][0] is None
    assert metadata["structurally_absent"]["gtex"]["retina"]["raw_column"] == "Eye - Retina"
    assert metadata["sources"]["hpa"]["measurement_kind"] == "ordinal_protein_level"
    assert "ordinal only" in metadata["sources"]["hpa"]["semantics"]
    assert metadata["contrast_scope"] == "restricted_panel"
    assert metadata["coverage"]["gtex_tpm"]["gtex_retina_tpm"]["non_null_count"] == 0
    assert metadata["coverage"]["gtex_tpm"]["gtex_retina_tpm"]["expressed_positive_count"] == 0

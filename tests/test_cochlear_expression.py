"""Tests for exploratory GSE135913 cochlear expression processing."""

import polars as pl

from scripts.cochlear_expression import (
    aggregate_samples,
    extract_cluster_expression,
    identify_hair_cell_cluster,
    leave_one_marker_out_sensitivity,
)


def marker_matrix() -> pl.DataFrame:
    genes = ["ATOH1", "OTOF", "POU4F3", "GFI1", "RBM24", "LMO7", "EPS8L2", "SLC17A8", "OTHER"]
    return pl.DataFrame({
        "": genes,
        "0_Mean": [0.0, 0.1, 0.0, 0.2, 0.1, 0.0, 0.2, 0.1, 4.0],
        "1_Mean": [5.0, 6.0, 4.0, 5.0, 4.5, 3.5, 4.0, 5.5, 0.0],
        "2_Mean": [0.5, 0.4, 0.3, 0.2, 0.1, 0.4, 0.2, 0.3, 1.0],
    })


def test_identifies_concordant_hair_cell_cluster():
    cluster, detail = identify_hair_cell_cluster(marker_matrix())
    assert cluster == "1"
    assert detail["marker_coverage"] == 8
    assert detail["margin"] > 0.5


def test_rejects_insufficient_marker_coverage():
    matrix = marker_matrix().filter(pl.col("").is_in(["ATOH1", "OTOF", "OTHER"]))
    cluster, detail = identify_hair_cell_cluster(matrix)
    assert cluster is None
    assert "marker coverage" in detail["reason"]


def test_leave_one_marker_out_assignment_is_stable():
    stable, assignments = leave_one_marker_out_sensitivity(marker_matrix())
    assert stable is True
    assert set(assignments.values()) == {"1"}


def test_extract_and_null_aware_aggregate():
    first = extract_cluster_expression(marker_matrix(), "1", "S1")
    second = pl.DataFrame({"gene_symbol": ["ATOH1", "NEW"],
                           "S2_hair_cell_mean": [3.0, 2.0]})
    result = aggregate_samples([first, second])
    atoh1 = result.filter(pl.col("gene_symbol") == "ATOH1").row(0, named=True)
    new = result.filter(pl.col("gene_symbol") == "NEW").row(0, named=True)
    assert atoh1["cochlear_hair_cell_expression"] == 4.0
    assert atoh1["hair_cell_sample_count"] == 2
    assert new["cochlear_hair_cell_expression"] == 2.0
    assert new["hair_cell_sample_count"] == 1

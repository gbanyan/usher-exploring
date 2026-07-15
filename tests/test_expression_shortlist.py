"""Tests for the expression/protein shortlist exploration."""

import polars as pl

from scripts.expression_shortlist import add_shortlist_strategies, summarize_strategies


def fixture_high() -> pl.DataFrame:
    return pl.DataFrame({
        "gene_symbol": ["MYO7A", "CEP290", "NOVEL1", "NOVEL2"],
        "cellxgene_photoreceptor_expr": [10.0, 8.0, 2.0, None],
        "hpa_retina_tpm": [9.0, 1.0, 8.0, None],
        "cellxgene_hair_cell_expr": [None, None, None, None],
        "cochlear_hair_cell_expression": [8.0, 7.0, 1.0, None],
        "compartment_cilia": [True, True, False, False],
        "compartment_centrosome": [False, False, False, False],
        "compartment_basal_body": [False, False, False, False],
        "compartment_transition_zone": [False, True, False, False],
        "compartment_stereocilia": [True, False, False, False],
        "in_cilia_proteomics": [False, False, True, False],
        "in_centrosome_proteomics": [False, False, False, False],
    })


def test_strategies_preserve_missing_as_no_gate_support():
    result, thresholds = add_shortlist_strategies(fixture_high())
    novel2 = result.filter(pl.col("gene_symbol") == "NOVEL2").row(0, named=True)
    assert thresholds["photoreceptor_q75"] == 9.0
    assert novel2["photoreceptor_q75"] is False
    assert novel2["expression_or_protein"] is False


def test_direct_protein_accepts_proteomics_or_compartment():
    result, _ = add_shortlist_strategies(fixture_high())
    kept = result.filter(pl.col("direct_protein"))["gene_symbol"].to_list()
    assert kept == ["MYO7A", "CEP290", "NOVEL1"]


def test_summary_reports_reduction_and_control_retention():
    result, _ = add_shortlist_strategies(fixture_high())
    summary = summarize_strategies(result)
    protein = summary.filter(pl.col("strategy") == "direct_protein").row(0, named=True)
    assert protein["shortlist_size"] == 3
    assert protein["reduction_percent"] == 25.0
    assert protein["omim_in_high_retained"] == 1
    assert protein["known_in_high_retained"] == 2

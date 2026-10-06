"""Scientific edge cases in the read-only major-revision analysis."""
import importlib.util
from pathlib import Path

import numpy as np
import polars as pl

spec = importlib.util.spec_from_file_location(
    "revision_phase2", Path(__file__).resolve().parents[1] / "scripts/revision_phase2.py"
)
revision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(revision)


def test_zero_weight_layer_cannot_supply_a_score_or_denominator():
    values = np.array([[.9, np.nan], [np.nan, .2], [.9, .2], [np.nan, np.nan]])
    actual = revision.weighted_mean(values, np.array([0., 1.]))
    np.testing.assert_allclose(actual, [np.nan, .2, .2, np.nan], equal_nan=True)


def test_percentile_ties_and_exact_top_order_are_distinct():
    scores = np.array([.1, .1, .5, np.nan])
    ids = np.array(["ENSG2", "ENSG1", "ENSG3", "ENSG4"])
    np.testing.assert_allclose(revision.percentile(scores), [0, 0, 1, np.nan], equal_nan=True)
    assert revision.order(scores, ids).tolist() == [2, 1, 0]
    assert revision.percentile(np.array([.4]))[0] == 0


def test_gate_uses_direct_fields_not_adjacent_aggregate_localization():
    df = pl.DataFrame({col: [False, False, True, False] for col in revision.LOCALIZATION_GATE_SOURCE_COLUMNS})
    df = df.with_columns(pl.Series("animal_model_score", [0., .1, .2, .3]),
                         pl.Series("localization_score", [.5, .5, 1., 0.]))
    direct, animal, q75 = revision.production_gate(df)
    assert direct.tolist() == [False, False, True, False]
    assert q75 == pl.Series([.1, .2, .3]).quantile(.75)
    assert animal.tolist() == [False, False, False, True]
    assert revision.tiers(np.array([.8, .8, .8, .8]), np.array([6, 6, 2, 6]), direct | animal).tolist() == ["MEDIUM", "MEDIUM", "MEDIUM", "HIGH"]


def test_proxy_removal_recalculates_tau_and_does_not_zero_missing_targets():
    df = pl.DataFrame({"gene_id": ["ENSG1", "ENSG2"], "gtex_cerebellum_tpm": [100., 1.],
                       "gtex_retina_tpm": [None, None], "gtex_testis_tpm": [10., 10.],
                       "gtex_fallopian_tube_tpm": [20., 20.], "cellxgene_photoreceptor_expr": [1., None]})
    original = revision.recompute_expression(df)
    removed = revision.recompute_expression(df, remove_proxy=True)
    assert original[revision.RESTRICTED_TAU_COLUMN][0] != .5
    assert removed[revision.RESTRICTED_TAU_COLUMN].to_list() == [.5, .5]
    assert removed["gtex_cerebellum_tpm"].null_count() == 2
    # Production's partial component mean can still score background-only Tau.
    # The analysis must flag this case instead of treating missing target as zero.
    assert removed["expression_score_normalized"][1] == .5
    assert df["gtex_cerebellum_tpm"].to_list() == [100., 1.]


def test_membership_families_exclude_single_layer_extremes():
    schemes = revision.scheme_vectors(np.array([.2, .2, .15, .15, .15, .15]))
    assert sum(family == "modest_weights" for family, _ in schemes.values()) == 25
    assert sum(family == "leave_one_out" for family, _ in schemes.values()) == 6
    assert sum(family == "single_layer" for family, _ in schemes.values()) == 6
    for _, weights in schemes.values():
        assert abs(weights.sum() - 1) < 1e-12


def test_constant_or_empty_paired_scores_are_unassessed():
    rho, n = revision.correlation(np.array([0., 0., 0.]), np.array([1., 2., 3.]))
    assert np.isnan(rho) and n == 3
    rho, n = revision.correlation(np.array([np.nan]), np.array([1.]))
    assert np.isnan(rho) and n == 0

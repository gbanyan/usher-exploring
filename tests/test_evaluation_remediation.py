"""Focused regression tests for evaluation and reproducibility remediation."""

from pathlib import Path

import polars as pl
import pytest

from scripts.ablation_study import (
    add_ranks,
    rank_statistics,
    score_null_preserve,
    score_zero_impute,
    score_median_impute,
    shift_statistics,
    paired_shift_data,
)
from scripts.paper_figures import background_sample_label, validation_percent_rank
from usher_pipeline.config.schema import APIConfig, DataSourceVersions, PipelineConfig, ScoringWeights
from usher_pipeline.output.reproducibility import generate_reproducibility_report
from usher_pipeline.output.writers import write_candidate_output
from usher_pipeline.persistence.provenance import ProvenanceTracker
from usher_pipeline.scoring.sensitivity import (
    EVIDENCE_LAYERS,
    _perturb_weight_values,
    format_weight_vector,
    generate_sensitivity_report,
    summarize_sensitivity,
)
from usher_pipeline.scoring.validation_report import generate_internal_evaluation_report
from usher_pipeline.output.reproducibility import ReproducibilityReport


def _ablation_fixture() -> pl.DataFrame:
    """One zero-evidence row plus two rows with computed scores."""
    values = {
        "gene_id": ["g0", "g1", "g2"],
        "gene_symbol": ["ZERO", "LOW", "HIGH"],
        "evidence_count": [0, 1, 6],
    }
    for column in [
        "gnomad_score", "expression_score", "annotation_score",
        "localization_score", "animal_model_score", "literature_score",
    ]:
        values[column] = [None, 0.2, 0.8]
    return pl.DataFrame(values)


def test_ablation_rank_denominators_exclude_null_ranks():
    df = _ablation_fixture()
    ranked = add_ranks(
        score_median_impute(
            score_zero_impute(score_null_preserve(df))
        )
    )

    # The NULL-preserve denominator is two computed rows, not all three table
    # rows.  The zero-evidence gene remains explicitly unranked there.
    null_stats = rank_statistics(ranked, "null_preserve")
    assert null_stats["ranked_rows"] == 2
    assert null_stats["null_rank_rows"] == 1
    assert null_stats["zero_evidence_null_rank_rows"] == 1
    assert null_stats["above_threshold_denominator"] == 2
    assert ranked.filter(pl.col("gene_symbol") == "ZERO")["pctile_null_preserve"][0] is None

    # Imputed strategies compute all rows and therefore use three-row
    # denominators.  Paired shifts use only rows ranked by both strategies.
    assert rank_statistics(ranked, "zero_impute")["ranked_rows"] == 3
    assert rank_statistics(ranked, "median_impute")["ranked_rows"] == 3
    assert shift_statistics(ranked, "null_preserve", "zero_impute")["paired_rows"] == 2


def test_sensitivity_reports_raw_delta_and_exact_final_vector():
    baseline = ScoringWeights()
    raw, final, total = _perturb_weight_values(baseline, "gnomad", 0.10)

    assert raw["gnomad"] == pytest.approx(0.30)
    assert total == pytest.approx(1.10)
    assert abs(sum(final.values()) - 1.0) < 1e-12
    assert set(final) == set(EVIDENCE_LAYERS)

    result = {
        "baseline_weights": baseline.model_dump(),
        "top_n": 100,
        "results": [{
            "layer": "gnomad",
            "delta": 0.10,
            "final_weights": final,
            "spearman_rho": 0.95,
            "spearman_pval": 0.01,
            "overlap_count": 95,
            "top_n_jaccard": 0.905,
        }],
    }
    summary = {
        "total_perturbations": 1,
        "stable_count": 1,
        "unstable_count": 0,
        "mean_rho": 0.95,
        "min_rho": 0.95,
        "max_rho": 0.95,
        "overall_stable": True,
        "most_sensitive_layer": "gnomad",
        "most_robust_layer": "gnomad",
    }
    report = generate_sensitivity_report(result, summary)

    assert "raw delta then renormalization" in report
    assert "Final normalized six-weight vectors" in report
    assert format_weight_vector(final) in report


def test_figure5_background_label_distinguishes_sample_and_population():
    assert background_sample_label(500, 19000) == (
        "Background sample\n(n=500 of population N=19000)"
    )


def test_reproducibility_records_hash_and_truthful_source_coverage(tmp_path):
    config = PipelineConfig(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        duckdb_path=tmp_path / "pipeline.db",
        versions=DataSourceVersions(ensembl_release=113),
        api=APIConfig(),
        scoring=ScoringWeights(),
    )
    provenance = ProvenanceTracker("0.1.0", config)
    provenance.record_data_source(
        "example",
        source_url="https://example.test/data.tsv",
        version="2026-01",
        retrieved_at="2026-08-14T00:00:00+00:00",
        checksum="abc123",
        checksum_algorithm="sha256",
    )
    report = generate_reproducibility_report(
        config=config,
        tiered_df=pl.DataFrame({
            "gene_id": ["g0"],
            "gene_symbol": ["GENE0"],
            "confidence_tier": ["HIGH"],
        }),
        provenance=provenance,
    )

    assert report.config_hash == config.config_hash()
    payload = report.to_dict()
    assert payload["config_hash"] == config.config_hash()
    assert payload["provenance_coverage"]["status"] == "complete"
    assert payload["validation_metrics"] == {}
    assert payload["evaluation_metrics"] == {}

    output_paths = write_candidate_output(
        pl.DataFrame({
            "gene_id": ["g1"],
            "gene_symbol": ["GENE1"],
            "composite_score": [0.8],
            "confidence_tier": ["HIGH"],
        }),
        tmp_path / "output",
        provenance=provenance,
    )
    import yaml

    sidecar = yaml.safe_load(Path(output_paths["provenance"]).read_text())
    assert sidecar["config_hash"] == config.config_hash()
    assert set(sidecar["output_checksums"]) == {"candidates.tsv", "candidates.parquet"}
    assert sidecar["provenance_coverage"]["status"] == "complete"


def test_reproducibility_preserves_legacy_constructor_and_serialization(mock_config=None):
    """Legacy constructor and JSON readers retain validation_metrics."""
    report = ReproducibilityReport(
        "run", "now", "0.1.0", {}, {}, {}, [],
        {"median_percentile": 0.8, "validation_passed": True}, {},
    )

    assert report.validation_metrics["validation_passed"] is True
    assert report.evaluation_metrics["control_recovery_meets_reference"] is True
    assert report.to_dict()["validation_metrics"]["median_percentile"] == 0.8


def test_existing_layer_sidecars_are_aggregated(tmp_path):
    config = PipelineConfig(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        duckdb_path=tmp_path / "pipeline.db",
        versions=DataSourceVersions(ensembl_release=113),
        api=APIConfig(),
        scoring=ScoringWeights(),
    )
    sidecar = config.data_dir / "expression" / "tissue.provenance.json"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text(
        '{"config_hash": "' + config.config_hash() + '", "processing_steps": [{"step_name": "download_expression", '
        '"details": {"source_name": "GTEx", "url": "https://example.test/gtex", '
        '"version": "v8"}}]}'
    )

    provenance = ProvenanceTracker.from_config(config)
    loaded = provenance.load_existing_sidecars(config.data_dir)

    assert loaded == [sidecar]
    assert provenance.data_sources[0]["source_name"] == "GTEx"
    assert provenance.data_sources[0]["version"] == "v8"
    assert provenance.provenance_coverage()["status"] == "incomplete"


def test_sidecars_with_missing_or_mismatched_hash_are_rejected(tmp_path):
    config = PipelineConfig(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        duckdb_path=tmp_path / "pipeline.db",
        versions=DataSourceVersions(ensembl_release=113),
        api=APIConfig(),
        scoring=ScoringWeights(),
    )
    missing = config.data_dir / "setup.provenance.json"
    mismatch = config.data_dir / "gnomad" / "constraint.provenance.json"
    mismatch.parent.mkdir(parents=True)
    missing.parent.mkdir(parents=True, exist_ok=True)
    missing.write_text('{"processing_steps": []}')
    mismatch.write_text('{"config_hash": "other", "processing_steps": []}')

    provenance = ProvenanceTracker.from_config(config)
    assert provenance.load_existing_sidecars(config.data_dir) == []
    assert {item["reason"] for item in provenance.rejected_sidecars} == {
        "missing_config_hash",
        "config_hash_mismatch",
    }
    coverage = provenance.provenance_coverage()
    assert coverage["status"] == "incomplete"
    assert coverage["rejected_sidecar_count"] == 2


def test_malformed_matching_sidecars_are_rejected(tmp_path):
    config = PipelineConfig(
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
        duckdb_path=tmp_path / "pipeline.db",
        versions=DataSourceVersions(ensembl_release=113),
        api=APIConfig(),
        scoring=ScoringWeights(),
    )
    root = config.data_dir
    root.mkdir(parents=True, exist_ok=True)
    config_hash = config.config_hash()
    (root / "bad_sources.provenance.json").write_text(
        '{"config_hash": "' + config_hash + '", "data_sources": {}}'
    )
    (root / "bad_steps.provenance.json").write_text(
        '{"config_hash": "' + config_hash + '", "processing_steps": {}}'
    )

    provenance = ProvenanceTracker.from_config(config)
    assert provenance.load_existing_sidecars(root) == []
    assert len(provenance.rejected_sidecars) == 2
    assert all(item["reason"] == "invalid_schema" for item in provenance.rejected_sidecars)
    assert provenance.provenance_coverage()["status"] == "incomplete"


def test_candidate_output_without_tracker_is_incomplete(tmp_path):
    output_paths = write_candidate_output(
        pl.DataFrame({
            "gene_id": ["g1"],
            "gene_symbol": ["GENE1"],
            "composite_score": [0.8],
            "confidence_tier": ["HIGH"],
        }),
        tmp_path / "output",
    )
    import yaml

    sidecar = yaml.safe_load(Path(output_paths["provenance"]).read_text())
    assert sidecar["provenance_coverage"]["status"] == "incomplete"
    assert "incomplete" in sidecar["provenance_coverage"]["note"]


def test_all_unavailable_rho_is_unassessed():
    analysis = {
        "results": [
            {"layer": "gnomad", "delta": -0.1, "spearman_rho": None},
            {"layer": "expression", "delta": -0.1, "spearman_rho": None},
        ],
        "total_perturbations": 2,
    }
    summary = summarize_sensitivity(analysis)

    assert summary["overall_stable"] is None
    assert summary["assessment_status"] == "unassessed"
    assert summary["unstable_count"] == 0
    report = generate_sensitivity_report(analysis, summary)
    assert "UNASSESSED" in report
    assert "Unstable perturbations" not in report


def test_validation_report_fails_closed_on_incoherent_control_metrics():
    report = generate_internal_evaluation_report(
        {
            "validation_passed": True,
            "total_known_expected": 0,
            "total_known_in_dataset": 0,
            "total_scored_non_null": 100,
            "median_percentile": 0.92,
            "top_quartile_count": 4,
            "top_quartile_fraction": 1.0,
        },
        {
            "validation_passed": True,
            "total_expected": 13,
            "total_in_dataset": 13,
            "total_scored_non_null": 100,
            "median_percentile": 0.35,
            "top_quartile_count": 1,
            "top_quartile_fraction": 1 / 13,
        },
        {"baseline_weights": {}, "results": [], "top_n": 100},
        {"overall_stable": None, "total_perturbations": 0},
    )

    assert "Known genes expected: N/A" in report
    assert "Known genes found: N/A" in report
    assert "Median percentile: N/A" in report
    assert "Top quartile count: N/A" in report
    assert "INCOMPLETE" in report
    assert "Known genes expected: 0" not in report
    assert "Known genes found: 0" not in report


def test_figure5_percentile_matches_validation_ties():
    ranked = validation_percent_rank(pl.DataFrame({
        "gene_symbol": ["A", "B", "C", "D"],
        "composite_score": [0.1, 0.1, 0.5, 0.9],
    }))

    assert ranked.sort("gene_symbol")["percentile"].to_list() == pytest.approx(
        [0.0, 0.0, 66.6666666667, 100.0]
    )


def test_figure6_paired_denominator_excludes_null_ranks():
    df = pl.DataFrame({
        "gene_symbol": ["ZERO", "A", "B"],
        "pctile_null_preserve": [None, 10.0, 20.0],
        "pctile_zero_impute": [0.0, 15.0, 25.0],
    })

    assert paired_shift_data(df).height == 2

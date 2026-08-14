"""CLI regression tests for expression cache-only behavior."""

import json
from unittest.mock import patch

import duckdb
import polars as pl
from click.testing import CliRunner

from usher_pipeline.cli.main import cli
from usher_pipeline.evidence.expression.fetch import (
    cellxgene_cache_path,
    cellxgene_legacy_cache_path,
)
from usher_pipeline.persistence import PipelineStore


def _write_config(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
versions:
  ensembl_release: "111"
  gnomad_version: "v4.1"
  gtex_version: "v8"
  hpa_version: "v23"
  cellxgene_census_version: "2025-11-08"

data_dir: {tmp_path}/data
cache_dir: {tmp_path}/cache
duckdb_path: {tmp_path}/expression.duckdb

api:
  rate_limit_per_second: 3
  max_retries: 3
  cache_ttl_seconds: 3600
  timeout_seconds: 30

scoring:
  gnomad: 0.20
  expression: 0.15
  annotation: 0.15
  localization: 0.15
  animal_model: 0.15
  literature: 0.20
"""
    )
    return config_path


def test_reprocess_cached_preflight_blocks_all_live_sources(tmp_path):
    """Missing caches fail before HPA/GTEx downloads or CellxGene access."""
    config_path = _write_config(tmp_path)
    runner = CliRunner()

    with patch(
        "usher_pipeline.evidence.expression.fetch.download_hpa_tissue_data"
    ) as hpa_download, patch(
        "usher_pipeline.evidence.expression.fetch.download_gtex_expression"
    ) as gtex_download, patch(
        "usher_pipeline.evidence.expression.fetch.fetch_cellxgene_expression"
    ) as cellxgene_fetch:
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "evidence",
                "expression",
                "--reprocess-cached",
            ],
        )

    assert result.exit_code != 0
    assert "cache-only expression reprocessing is missing required source caches" in result.output
    hpa_download.assert_not_called()
    gtex_download.assert_not_called()
    cellxgene_fetch.assert_not_called()


def test_reprocess_cached_with_force_is_rejected(tmp_path):
    config_path = _write_config(tmp_path)
    result = CliRunner().invoke(
        cli,
        [
            "--config",
            str(config_path),
            "evidence",
            "expression",
            "--force",
            "--reprocess-cached",
        ],
    )

    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_legacy_checkpoint_migration_is_cache_only(tmp_path):
    """Automatic legacy migration uses local source files and preserves symbols."""
    config_path = _write_config(tmp_path)
    expression_dir = tmp_path / "data" / "expression"
    expression_dir.mkdir(parents=True)
    (expression_dir / "hpa_normal_tissue.tsv").write_text(
        "Gene\tGene name\tTissue\tCell type\tLevel\tReliability\n"
        "ENSG1\tGENE1\tretina\tcones\tHigh\tApproved\n"
        "ENSG1\tGENE1\ttestis\tLeydig cells\tLow\tSupported\n"
    )
    (expression_dir / "gtex_median_tpm.gct").write_text(
        "#1.2\n"
        "1\t2\n"
        "Name\tDescription\tBrain - Cerebellum\tTestis\tFallopian Tube\n"
        "ENSG1.1\tGENE1\t10\t2\t1\n"
    )

    store = PipelineStore(tmp_path / "expression.duckdb")
    store.save_dataframe(
        pl.DataFrame({
            "gene_id": ["ENSG1"],
            "hpa_retina_tpm": [8.0],
            "tau_specificity": [0.5],
            "usher_tissue_enrichment": [2.0],
            "expression_score_normalized": [0.8],
        }),
        "tissue_expression",
        replace=True,
    )
    store.save_dataframe(
        pl.DataFrame({"gene_id": ["ENSG1"], "gene_symbol": ["GENE1"]}),
        "gene_universe",
        replace=True,
    )
    store.close()

    runner = CliRunner()
    with patch(
        "usher_pipeline.evidence.expression.fetch.download_hpa_tissue_data",
        side_effect=AssertionError("HPA download in cache-only migration"),
    ) as hpa_download, patch(
        "usher_pipeline.evidence.expression.fetch.download_gtex_expression",
        side_effect=AssertionError("GTEx download in cache-only migration"),
    ) as gtex_download:
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "evidence",
                "expression",
                "--skip-cellxgene",
            ],
        )

    assert result.exit_code == 0, result.output
    hpa_download.assert_not_called()
    gtex_download.assert_not_called()

    migrated = duckdb.connect(str(tmp_path / "expression.duckdb")).execute(
        "SELECT * FROM tissue_expression"
    ).pl()
    assert migrated["gene_symbol"].to_list() == ["GENE1"]
    assert "hpa_retina_tpm" not in migrated.columns
    assert "tau_restricted_panel_specificity" in migrated.columns
    assert "usher_restricted_panel_contrast" in migrated.columns


def test_cli_migrates_baseline_cellxgene_cache_without_live_query(tmp_path):
    """Cache-only migration recognizes the baseline cache as photo-only."""
    config_path = _write_config(tmp_path)
    expression_dir = tmp_path / "data" / "expression"
    expression_dir.mkdir(parents=True)
    (expression_dir / "hpa_normal_tissue.tsv").write_text(
        "Gene\tGene name\tTissue\tCell type\tLevel\tReliability\n"
        "ENSG1\tGENE1\tretina\tcones\tHigh\tApproved\n"
        "ENSG1\tGENE1\ttestis\tLeydig cells\tLow\tSupported\n"
    )
    (expression_dir / "gtex_median_tpm.gct").write_text(
        "#1.2\n"
        "1\t2\n"
        "Name\tDescription\tBrain - Cerebellum\tTestis\tFallopian Tube\n"
        "ENSG1.1\tGENE1\t10\t2\t1\n"
    )
    legacy_cellxgene_path = cellxgene_legacy_cache_path(
        expression_dir, "2025-11-08"
    )
    pl.DataFrame({
        "gene_id": ["ENSG1"],
        "cellxgene_photoreceptor_expr": [2.0],
        "cellxgene_hair_cell_expr": [9.0],
    }).write_parquet(legacy_cellxgene_path)

    store = PipelineStore(tmp_path / "expression.duckdb")
    store.save_dataframe(
        pl.DataFrame({
            "gene_id": ["ENSG1"],
            "tau_specificity": [0.5],
            "usher_tissue_enrichment": [2.0],
            "expression_score_normalized": [0.8],
        }),
        "tissue_expression",
        replace=True,
    )
    store.save_dataframe(
        pl.DataFrame({"gene_id": ["ENSG1"], "gene_symbol": ["GENE1"]}),
        "gene_universe",
        replace=True,
    )
    store.close()

    runner = CliRunner()
    with patch(
        "usher_pipeline.evidence.expression.fetch.download_hpa_tissue_data",
        side_effect=AssertionError("HPA download during cache-only migration"),
    ) as hpa_download, patch(
        "usher_pipeline.evidence.expression.fetch.download_gtex_expression",
        side_effect=AssertionError("GTEx download during cache-only migration"),
    ) as gtex_download, patch.dict("sys.modules", {"cellxgene_census": None}):
        result = runner.invoke(
            cli,
            ["--config", str(config_path), "evidence", "expression"],
        )

    assert result.exit_code == 0, result.output
    hpa_download.assert_not_called()
    gtex_download.assert_not_called()
    mode_specific_path = cellxgene_cache_path(expression_dir, "2025-11-08")
    assert legacy_cellxgene_path.exists()
    assert mode_specific_path.exists()
    migrated_cache = pl.read_parquet(mode_specific_path)
    assert migrated_cache["cellxgene_hair_cell_expr"].null_count() == 1

    sidecar = expression_dir / "tissue.provenance.provenance.json"
    metadata = json.loads(sidecar.read_text())
    process_step = next(
        step for step in metadata["processing_steps"]
        if step["step_name"] == "process_expression_evidence"
    )
    cellxgene = process_step["details"]["source_metadata"]["sources"]["cellxgene"]
    assert cellxgene["status"] == "legacy_cache_migrated"
    assert cellxgene["legacy_cache_file"] == legacy_cellxgene_path.name
    assert cellxgene["cache_file"] == mode_specific_path.name
    assert cellxgene["query_mode"] == "photoreceptor_only"
    assert cellxgene["coverage"] == "all_genes"
    cellxgene_coverage = process_step["details"]["source_metadata"][
        "coverage"
    ]["cellxgene"]
    assert cellxgene_coverage["cellxgene_hair_cell_expr"]["non_null_count"] == 0
    assert cellxgene_coverage["cellxgene_hair_cell_expr"]["expressed_positive_count"] == 0
    assert "hair" not in cellxgene["query_mode"]

    store = PipelineStore(tmp_path / "expression.duckdb")
    checkpoint = store.load_dataframe("tissue_expression")
    store.close()
    assert checkpoint["cellxgene_hair_cell_expr"].null_count() == checkpoint.height


def test_legacy_checkpoint_with_force_refreshes_instead_of_cache_preflight(tmp_path):
    """--force disables automatic legacy cache-only migration."""
    config_path = _write_config(tmp_path)
    store = PipelineStore(tmp_path / "expression.duckdb")
    store.save_dataframe(
        pl.DataFrame({
            "gene_id": ["ENSG1"],
            "tau_specificity": [0.5],
            "usher_tissue_enrichment": [2.0],
            "expression_score_normalized": [0.8],
        }),
        "tissue_expression",
        replace=True,
    )
    store.save_dataframe(
        pl.DataFrame({"gene_id": ["ENSG1"], "gene_symbol": ["GENE1"]}),
        "gene_universe",
        replace=True,
    )
    store.close()

    refreshed = pl.DataFrame({
        "gene_id": ["ENSG1"],
        "gene_symbol": ["GENE1"],
        "tau_restricted_panel_specificity": [0.25],
        "usher_restricted_panel_contrast": [1.5],
        "expression_score_normalized": [0.6],
    })
    runner = CliRunner()
    with patch(
        "usher_pipeline.cli.evidence_cmd.process_expression_evidence",
        return_value=refreshed,
    ) as process:
        result = runner.invoke(
            cli,
            [
                "--config",
                str(config_path),
                "evidence",
                "expression",
                "--force",
                "--skip-cellxgene",
            ],
        )

    assert result.exit_code == 0, result.output
    kwargs = process.call_args.kwargs
    assert kwargs["force"] is True
    assert kwargs["cache_only"] is False
    assert "--force refreshes source files" in result.output

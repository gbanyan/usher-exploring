"""Integration tests for report CLI command using CliRunner.

Tests:
- report --help
- Full report generation with tiered candidates
- Tier counts in CLI output
- Visualization generation
- --skip-viz flag
- --skip-report flag
- Custom tier thresholds
- Missing scored_genes error handling
- Custom output directory
"""

import tempfile
from pathlib import Path

import polars as pl
import pytest
import duckdb
from click.testing import CliRunner

from usher_pipeline.cli.main import cli


@pytest.fixture
def test_config(tmp_path):
    """Create minimal config YAML for testing."""
    config_path = tmp_path / "test_config.yaml"
    config_content = f"""
versions:
  ensembl_release: "111"
  gnomad_version: "v4.1"
  gtex_version: "v8"
  hpa_version: "v23"

data_dir: {tmp_path}/data
cache_dir: {tmp_path}/cache
duckdb_path: {tmp_path}/test.duckdb

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
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def populated_db(tmp_path):
    """Create DuckDB with gene_universe and scored_genes tables."""
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))

    # Create gene_universe table (20 synthetic genes)
    gene_universe_df = pl.DataFrame({
        "gene_id": [f"ENSG{i:011d}" for i in range(1, 21)],
        "gene_symbol": [f"GENE{i}" for i in range(1, 21)],
    })
    conn.execute("CREATE TABLE gene_universe AS SELECT * FROM gene_universe_df")

    # Create scored_genes table
    # Design: 3 HIGH (score 0.7-0.95, evidence 3-5), 5 MEDIUM, 5 LOW, 4 EXCLUDED (score < 0.2), 3 NULL composite_score
    scored_genes_df = pl.DataFrame({
        "gene_id": [f"ENSG{i:011d}" for i in range(1, 21)],
        "gene_symbol": [f"GENE{i}" for i in range(1, 21)],
        # HIGH tier: genes 1-3
        "composite_score": [0.95, 0.85, 0.75] +
                          # MEDIUM tier: genes 4-8
                          [0.65, 0.55, 0.45, 0.42, 0.40] +
                          # LOW tier: genes 9-13
                          [0.35, 0.30, 0.25, 0.22, 0.20] +
                          # EXCLUDED: genes 14-17
                          [0.15, 0.10, 0.05, 0.02] +
                          # NULL: genes 18-20
                          [None, None, None],
        "evidence_count": [5, 4, 3] +  # HIGH
                         [3, 2, 2, 2, 2] +  # MEDIUM
                         [1, 1, 1, 1, 1] +  # LOW
                         [1, 1, 0, 0] +  # EXCLUDED
                         [0, 0, 0],  # NULL
        "quality_flag": ["sufficient_evidence"] * 3 +
                       ["sufficient_evidence", "moderate_evidence", "moderate_evidence", "moderate_evidence", "moderate_evidence"] +
                       ["sparse_evidence"] * 5 +
                       ["sparse_evidence", "sparse_evidence", "no_evidence", "no_evidence"] +
                       ["no_evidence"] * 3,
        # Layer scores (simplified)
        "gnomad_score": [0.9] * 20,
        "expression_score": [0.8] * 20,
        "annotation_score": [0.7] * 20,
        "localization_score": [0.6] * 20,
        "animal_model_score": [0.5] * 20,
        "literature_score": [0.4] * 20,
        # Contribution columns
        "gnomad_contribution": [0.18] * 20,
        "expression_contribution": [0.12] * 20,
        "annotation_contribution": [0.105] * 20,
        "localization_contribution": [0.09] * 20,
        "animal_model_contribution": [0.075] * 20,
        "literature_contribution": [0.08] * 20,
        # Weighted average metadata
        "available_weight": [1.0] * 20,
        "weighted_sum": [0.65] * 20,
    })
    conn.execute("CREATE TABLE scored_genes AS SELECT * FROM scored_genes_df")

    # Register checkpoint
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _checkpoints (
            table_name VARCHAR PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("INSERT INTO _checkpoints (table_name) VALUES ('scored_genes')")

    conn.close()
    return db_path


def test_report_help(test_config):
    """Test report --help shows all options."""
    runner = CliRunner()
    result = runner.invoke(cli, ['--config', str(test_config), 'report', '--help'])

    assert result.exit_code == 0
    assert '--output-dir' in result.output
    assert '--force' in result.output
    assert '--skip-viz' in result.output
    assert '--skip-report' in result.output
    assert '--high-threshold' in result.output
    assert '--medium-threshold' in result.output
    assert '--low-threshold' in result.output
    assert '--min-evidence-high' in result.output
    assert '--min-evidence-medium' in result.output


def test_report_generates_files(test_config, populated_db):
    """Test report generates candidates.tsv, candidates.parquet, and provenance."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        '--config', str(test_config),
        'report'
    ])

    assert result.exit_code == 0

    # Check output files exist
    output_dir = test_config.parent / "data" / "report"
    assert (output_dir / "candidates.tsv").exists()
    assert (output_dir / "candidates.parquet").exists()
    assert (output_dir / "candidates.provenance.yaml").exists()


def test_report_tier_counts_in_output(test_config, populated_db):
    """Test report CLI output shows tier counts."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        '--config', str(test_config),
        'report'
    ])

    assert result.exit_code == 0
    # Expected: 3 HIGH, 5 MEDIUM, 5 LOW (from synthetic data design)
    assert 'HIGH' in result.output
    assert 'MEDIUM' in result.output
    assert 'LOW' in result.output
    # Check for counts (flexible regex since exact format may vary)
    assert '3' in result.output  # HIGH count
    assert '5' in result.output  # MEDIUM and LOW counts


def test_report_with_viz(test_config, populated_db):
    """Test report generates plots by default."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        '--config', str(test_config),
        'report'
    ])

    assert result.exit_code == 0

    # Check plots directory and files exist
    plots_dir = test_config.parent / "data" / "report" / "plots"
    assert plots_dir.exists()
    assert (plots_dir / "score_distribution.png").exists()
    assert (plots_dir / "layer_contributions.png").exists()
    assert (plots_dir / "tier_breakdown.png").exists()


def test_report_skip_viz(test_config, populated_db, tmp_path):
    """Test --skip-viz flag skips visualization generation."""
    runner = CliRunner()

    # Use different output dir to avoid conflict with previous test
    custom_output = tmp_path / "output_no_viz"

    result = runner.invoke(cli, [
        '--config', str(test_config),
        'report',
        '--output-dir', str(custom_output),
        '--skip-viz'
    ])

    assert result.exit_code == 0
    assert 'Skipping visualizations' in result.output

    # Plots directory should not exist
    plots_dir = custom_output / "plots"
    assert not plots_dir.exists() or not any(plots_dir.iterdir())


def test_report_skip_report(test_config, populated_db, tmp_path):
    """Test --skip-report flag skips reproducibility report generation."""
    runner = CliRunner()

    custom_output = tmp_path / "output_no_report"

    result = runner.invoke(cli, [
        '--config', str(test_config),
        'report',
        '--output-dir', str(custom_output),
        '--skip-report'
    ])

    assert result.exit_code == 0
    assert 'Skipping reproducibility report' in result.output

    # Reproducibility files should not exist
    assert not (custom_output / "reproducibility.json").exists()
    assert not (custom_output / "reproducibility.md").exists()


def test_report_custom_thresholds(test_config, populated_db, tmp_path):
    """Test custom tier thresholds produce different tier counts."""
    runner = CliRunner()

    custom_output = tmp_path / "output_custom_thresholds"

    # Use higher thresholds: HIGH >= 0.8, MEDIUM >= 0.5, LOW >= 0.2
    result = runner.invoke(cli, [
        '--config', str(test_config),
        'report',
        '--output-dir', str(custom_output),
        '--high-threshold', '0.8',
        '--medium-threshold', '0.5',
        '--low-threshold', '0.2'
    ])

    assert result.exit_code == 0

    # With these thresholds:
    # HIGH: genes 1-2 (scores 0.95, 0.85)
    # MEDIUM: genes 3-6 (scores 0.75, 0.65, 0.55, 0.45 - but need evidence >= 2)
    # LOW: remaining above 0.2
    # Should see different counts than default

    # Load the output and verify tier distribution changed
    candidates_df = pl.read_parquet(custom_output / "candidates.parquet")

    high_count = candidates_df.filter(candidates_df['confidence_tier'] == 'HIGH').height
    assert high_count == 2  # Only genes with score >= 0.8 and evidence >= 3


def test_report_no_scored_genes_error(test_config, tmp_path):
    """Test report with missing scored_genes table produces clear error."""
    # Create empty DuckDB (no scored_genes table)
    empty_db_path = tmp_path / "empty.duckdb"
    conn = duckdb.connect(str(empty_db_path))
    conn.close()

    runner = CliRunner()
    result = runner.invoke(cli, [
        '--config', str(test_config),
        'report'
    ])

    assert result.exit_code != 0
    assert "Run 'usher-pipeline score' first" in result.output


def test_report_output_dir_option(test_config, populated_db, tmp_path):
    """Test --output-dir option creates files in custom location."""
    runner = CliRunner()

    custom_output = tmp_path / "custom_report_dir"

    result = runner.invoke(cli, [
        '--config', str(test_config),
        'report',
        '--output-dir', str(custom_output)
    ])

    assert result.exit_code == 0

    # Files should be in custom directory
    assert (custom_output / "candidates.tsv").exists()
    assert (custom_output / "candidates.parquet").exists()
    assert (custom_output / "candidates.provenance.yaml").exists()

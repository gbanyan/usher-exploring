"""Positive control validation against known gene rankings."""

import duckdb
import polars as pl
import structlog

from usher_pipeline.persistence.duckdb_store import PipelineStore
from usher_pipeline.scoring.known_genes import compile_known_genes

logger = structlog.get_logger(__name__)


def validate_known_gene_ranking(
    store: PipelineStore,
    percentile_threshold: float = 0.75
) -> dict:
    """
    Validate that known cilia/Usher genes rank highly in composite scores.

    Computes percentile ranks for known genes using PERCENT_RANK window function
    across ALL genes (not just known genes). Validates that known genes rank in
    top quartile before exclusion filtering.

    Args:
        store: PipelineStore with scored_genes table
        percentile_threshold: Minimum median percentile for validation (default 0.75)

    Returns:
        Dict with keys:
        - total_known_expected: int - count of known genes in reference list
        - total_known_in_dataset: int - count of known genes found in scored_genes
        - median_percentile: float - median percentile rank of known genes
        - top_quartile_count: int - count of known genes >= 75th percentile
        - top_quartile_fraction: float - fraction in top quartile
        - validation_passed: bool - True if median >= percentile_threshold
        - known_gene_details: list[dict] - top 20 known genes with scores and ranks
        - reason: str - explanation if validation failed (optional)

    Notes:
        - Uses PERCENT_RANK() which returns 0.0 (lowest) to 1.0 (highest)
        - Ranks computed BEFORE known gene exclusion (validates scoring system)
        - Genes without composite_score (NULL) are excluded from ranking
        - Creates temporary table _known_genes for the join
    """
    logger.info("validate_known_gene_ranking_start", threshold=percentile_threshold)

    # Compile known genes
    known_df = compile_known_genes()
    total_known_expected = known_df["gene_symbol"].n_unique()

    # Register known genes as temporary DuckDB table
    store.conn.execute("DROP TABLE IF EXISTS _known_genes")
    store.conn.execute("CREATE TEMP TABLE _known_genes AS SELECT * FROM known_df")

    # Query to compute percentile ranks for known genes
    query = """
    WITH ranked_genes AS (
        SELECT
            gene_symbol,
            composite_score,
            PERCENT_RANK() OVER (ORDER BY composite_score) AS percentile_rank
        FROM scored_genes
        WHERE composite_score IS NOT NULL
    )
    SELECT
        rg.gene_symbol,
        rg.composite_score,
        rg.percentile_rank,
        kg.source
    FROM ranked_genes rg
    INNER JOIN _known_genes kg ON rg.gene_symbol = kg.gene_symbol
    ORDER BY rg.percentile_rank DESC
    """

    result = store.conn.execute(query).pl()

    # Clean up temp table
    store.conn.execute("DROP TABLE IF EXISTS _known_genes")

    # If no known genes found, return failure
    if result.height == 0:
        logger.error(
            "validate_known_gene_ranking_failed",
            reason="no_known_genes_found",
            expected=total_known_expected,
            found=0,
        )
        return {
            "total_known_expected": total_known_expected,
            "total_known_in_dataset": 0,
            "median_percentile": None,
            "top_quartile_count": 0,
            "top_quartile_fraction": 0.0,
            "validation_passed": False,
            "known_gene_details": [],
            "reason": "no_known_genes_found",
        }

    # Compute validation metrics
    total_known_in_dataset = result.height
    percentiles = result["percentile_rank"].to_numpy()
    median_percentile = float(result["percentile_rank"].median())

    top_quartile_genes = result.filter(pl.col("percentile_rank") >= 0.75)
    top_quartile_count = top_quartile_genes.height
    top_quartile_fraction = top_quartile_count / total_known_in_dataset

    validation_passed = median_percentile >= percentile_threshold

    # Extract top 20 known genes for reporting
    known_gene_details = result.head(20).select([
        "gene_symbol",
        "composite_score",
        "percentile_rank",
        "source"
    ]).to_dicts()

    # Log validation results
    if validation_passed:
        logger.info(
            "validate_known_gene_ranking_passed",
            total_expected=total_known_expected,
            total_found=total_known_in_dataset,
            median_percentile=f"{median_percentile:.4f}",
            top_quartile_count=top_quartile_count,
            top_quartile_fraction=f"{top_quartile_fraction:.2%}",
            threshold=percentile_threshold,
        )
    else:
        logger.warning(
            "validate_known_gene_ranking_failed",
            reason="median_below_threshold",
            median_percentile=f"{median_percentile:.4f}",
            threshold=percentile_threshold,
            top_quartile_fraction=f"{top_quartile_fraction:.2%}",
        )

    return {
        "total_known_expected": total_known_expected,
        "total_known_in_dataset": total_known_in_dataset,
        "median_percentile": median_percentile,
        "top_quartile_count": top_quartile_count,
        "top_quartile_fraction": top_quartile_fraction,
        "validation_passed": validation_passed,
        "known_gene_details": known_gene_details,
    }


def generate_validation_report(metrics: dict) -> str:
    """
    Generate human-readable validation report.

    Args:
        metrics: Dict returned from validate_known_gene_ranking()

    Returns:
        Multi-line text report summarizing validation results

    Notes:
        - Formats percentiles as percentages (e.g., "87.3%")
        - Includes table of top-ranked known genes
        - Shows pass/fail status prominently
    """
    passed = metrics["validation_passed"]
    status = "PASSED ✓" if passed else "FAILED ✗"

    # Handle case where no known genes found
    if metrics["total_known_in_dataset"] == 0:
        return f"""
Positive Control Validation: {status}

Reason: No known genes found in scored dataset
Expected: {metrics['total_known_expected']} known genes
Found: 0 genes

This indicates either:
1. Known genes were already filtered out
2. Gene symbol mismatch between known list and scored_genes
3. No genes have composite scores yet
"""

    median_pct = metrics["median_percentile"] * 100
    top_q_frac = metrics["top_quartile_fraction"] * 100

    report = [
        f"Positive Control Validation: {status}",
        "",
        "Summary:",
        f"  Known genes expected: {metrics['total_known_expected']}",
        f"  Known genes found: {metrics['total_known_in_dataset']}",
        f"  Median percentile: {median_pct:.1f}%",
        f"  Top quartile count: {metrics['top_quartile_count']}",
        f"  Top quartile fraction: {top_q_frac:.1f}%",
        "",
    ]

    # Add interpretation
    if passed:
        report.append(
            f"Known cilia/Usher genes rank highly (median >= 75th percentile), "
            "validating the scoring system."
        )
    else:
        report.append(
            f"Warning: Known genes rank below expected threshold. "
            f"Median percentile ({median_pct:.1f}%) < 75.0%."
        )
        report.append(
            "This may indicate issues with evidence layer weights or data quality."
        )

    report.append("")
    report.append("Top-Ranked Known Genes:")
    report.append("-" * 80)
    report.append(f"{'Gene':<12} {'Score':>8} {'Percentile':>12} {'Source':<20}")
    report.append("-" * 80)

    for gene in metrics["known_gene_details"]:
        gene_symbol = gene["gene_symbol"]
        score = gene["composite_score"]
        percentile = gene["percentile_rank"] * 100
        source = gene["source"]
        report.append(
            f"{gene_symbol:<12} {score:>8.4f} {percentile:>11.1f}% {source:<20}"
        )

    return "\n".join(report)

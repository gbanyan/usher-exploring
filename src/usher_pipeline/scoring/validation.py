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


def compute_recall_at_k(
    store: PipelineStore,
    k_values: list[int] | None = None
) -> dict:
    """
    Compute recall@k metrics for known genes at various thresholds.

    Measures what fraction of known genes appear in the top-k ranked candidates,
    providing specific metrics like ">70% recall in top 10%" required by success criteria.

    Args:
        store: PipelineStore with scored_genes table
        k_values: Absolute top-k thresholds (default: [100, 500, 1000, 2000])

    Returns:
        Dict with keys:
        - recalls_absolute: dict mapping k -> recall float (e.g., {100: 0.65, 500: 0.85})
        - recalls_percentage: dict mapping pct_string -> recall float (e.g., {"5%": 0.58, "10%": 0.72})
        - total_known_unique: int - count of unique known genes (deduplicated)
        - total_scored: int - count of genes with non-NULL composite scores

    Notes:
        - Known genes are deduplicated on gene_symbol (genes in both sources count once)
        - Recall@k = (known genes in top-k) / total_known_unique
        - Percentage thresholds computed at 5%, 10%, 20% of total_scored
        - Genes without composite_score (NULL) are excluded
        - Ordered by composite_score DESC (highest scores first)
    """
    logger.info("compute_recall_at_k_start")

    # Default k values
    if k_values is None:
        k_values = [100, 500, 1000, 2000]

    # Compile known genes and deduplicate on gene_symbol
    known_df = compile_known_genes()
    known_genes_set = set(known_df["gene_symbol"].unique())
    total_known_unique = len(known_genes_set)

    # Get total count of scored genes
    total_scored = store.conn.execute("""
        SELECT COUNT(*) as total
        FROM scored_genes
        WHERE composite_score IS NOT NULL
    """).fetchone()[0]

    # Compute percentage thresholds
    percentage_thresholds = [0.05, 0.10, 0.20]  # 5%, 10%, 20%
    percentage_k_values = {
        f"{int(pct * 100)}%": int(total_scored * pct)
        for pct in percentage_thresholds
    }

    # Query top-k genes for each threshold and compute recall
    recalls_absolute = {}
    for k in k_values:
        query = f"""
        SELECT gene_symbol
        FROM scored_genes
        WHERE composite_score IS NOT NULL
        ORDER BY composite_score DESC
        LIMIT {k}
        """
        top_k_genes = store.conn.execute(query).pl()
        top_k_set = set(top_k_genes["gene_symbol"])

        # Count how many known genes are in top-k
        known_in_top_k = len(known_genes_set & top_k_set)
        recall = known_in_top_k / total_known_unique if total_known_unique > 0 else 0.0
        recalls_absolute[k] = recall

        logger.info(
            "recall_at_k_absolute",
            k=k,
            recall=f"{recall:.4f}",
            known_in_top_k=known_in_top_k,
            total_known=total_known_unique,
        )

    # Compute recall at percentage thresholds
    recalls_percentage = {}
    for pct_string, k in percentage_k_values.items():
        query = f"""
        SELECT gene_symbol
        FROM scored_genes
        WHERE composite_score IS NOT NULL
        ORDER BY composite_score DESC
        LIMIT {k}
        """
        top_k_genes = store.conn.execute(query).pl()
        top_k_set = set(top_k_genes["gene_symbol"])

        known_in_top_k = len(known_genes_set & top_k_set)
        recall = known_in_top_k / total_known_unique if total_known_unique > 0 else 0.0
        recalls_percentage[pct_string] = recall

        logger.info(
            "recall_at_k_percentage",
            threshold=pct_string,
            k=k,
            recall=f"{recall:.4f}",
            known_in_top_k=known_in_top_k,
            total_known=total_known_unique,
        )

    return {
        "recalls_absolute": recalls_absolute,
        "recalls_percentage": recalls_percentage,
        "total_known_unique": total_known_unique,
        "total_scored": total_scored,
    }


def validate_positive_controls_extended(
    store: PipelineStore,
    percentile_threshold: float = 0.75
) -> dict:
    """
    Extended positive control validation with recall@k and per-source breakdown.

    Combines base percentile validation with recall@k metrics and per-source analysis
    to provide comprehensive validation for Phase 6.

    Args:
        store: PipelineStore with scored_genes table
        percentile_threshold: Minimum median percentile for validation (default 0.75)

    Returns:
        Dict with keys:
        - All keys from validate_known_gene_ranking() (base metrics)
        - recall_at_k: dict from compute_recall_at_k() (recalls_absolute, recalls_percentage, etc.)
        - per_source_breakdown: dict mapping source -> {median_percentile, count, top_quartile_count}

    Notes:
        - Per-source breakdown separates OMIM Usher (10 genes) from SYSCILIA SCGS v2 (28 genes)
        - Uses same PERCENT_RANK CTE pattern but filters JOIN by source
        - Allows detecting if one gene set validates better than the other
    """
    logger.info("validate_positive_controls_extended_start", threshold=percentile_threshold)

    # Get base metrics from existing validation function
    base_metrics = validate_known_gene_ranking(store, percentile_threshold)

    # Compute recall@k metrics
    recall_metrics = compute_recall_at_k(store)

    # Compute per-source breakdown
    known_df = compile_known_genes()
    sources = known_df["source"].unique().to_list()

    per_source_breakdown = {}

    for source in sources:
        # Filter known genes to current source
        source_genes = known_df.filter(pl.col("source") == source)

        # Register as temp table
        store.conn.execute("DROP TABLE IF EXISTS _source_genes")
        store.conn.execute("CREATE TEMP TABLE _source_genes AS SELECT * FROM source_genes")

        # Query with same PERCENT_RANK pattern
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
            rg.percentile_rank
        FROM ranked_genes rg
        INNER JOIN _source_genes sg ON rg.gene_symbol = sg.gene_symbol
        ORDER BY rg.percentile_rank DESC
        """

        result = store.conn.execute(query).pl()

        # Clean up temp table
        store.conn.execute("DROP TABLE IF EXISTS _source_genes")

        if result.height == 0:
            per_source_breakdown[source] = {
                "median_percentile": None,
                "count": 0,
                "top_quartile_count": 0,
            }
            continue

        median_percentile = float(result["percentile_rank"].median())
        count = result.height
        top_quartile_count = result.filter(pl.col("percentile_rank") >= 0.75).height

        per_source_breakdown[source] = {
            "median_percentile": median_percentile,
            "count": count,
            "top_quartile_count": top_quartile_count,
        }

        logger.info(
            "per_source_validation",
            source=source,
            median_percentile=f"{median_percentile:.4f}",
            count=count,
            top_quartile_count=top_quartile_count,
        )

    # Combine all metrics
    extended_metrics = {
        **base_metrics,
        "recall_at_k": recall_metrics,
        "per_source_breakdown": per_source_breakdown,
    }

    logger.info(
        "validate_positive_controls_extended_complete",
        validation_passed=base_metrics["validation_passed"],
        recall_at_10pct=f"{recall_metrics['recalls_percentage'].get('10%', 0.0):.4f}",
    )

    return extended_metrics

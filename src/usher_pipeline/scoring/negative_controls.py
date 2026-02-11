"""Negative control validation using housekeeping genes."""

import polars as pl
import structlog

from usher_pipeline.persistence.duckdb_store import PipelineStore

logger = structlog.get_logger(__name__)

# Housekeeping genes: ubiquitously expressed, essential genes that should NOT rank
# highly in a cilia/Usher-specific scoring system. These serve as negative controls
# to ensure the scoring system shows specificity.
#
# Source: Literature-validated housekeeping genes from Eisenberg & Levanon (2013)
# "Human housekeeping genes, revisited" Trends in Genetics 29(10):569-574
# and widely used reference genes in expression normalization studies.
HOUSEKEEPING_GENES_CORE = frozenset([
    # Ribosomal proteins (structural components of ribosomes)
    "RPL13A",   # 60S ribosomal protein L13a
    "RPL32",    # 60S ribosomal protein L32
    "RPLP0",    # 60S acidic ribosomal protein P0

    # Metabolic enzymes (glycolysis, oxidative phosphorylation)
    "GAPDH",    # Glyceraldehyde-3-phosphate dehydrogenase
    "ACTB",     # Actin beta (cytoskeletal)
    "PGK1",     # Phosphoglycerate kinase 1
    "SDHA",     # Succinate dehydrogenase complex subunit A

    # Transcription/reference genes
    "B2M",      # Beta-2-microglobulin
    "HPRT1",    # Hypoxanthine phosphoribosyltransferase 1
    "TBP",      # TATA-box binding protein

    # Protein folding/modification
    "PPIA",     # Peptidylprolyl isomerase A (cyclophilin A)
    "UBC",      # Ubiquitin C
    "YWHAZ",    # Tyrosine 3-monooxygenase/tryptophan 5-monooxygenase activation protein zeta
])


def compile_housekeeping_genes() -> pl.DataFrame:
    """
    Compile housekeeping genes into a structured DataFrame.

    Returns:
        DataFrame with columns:
        - gene_symbol (str): Gene symbol
        - source (str): "literature_validated" for all entries
        - confidence (str): "HIGH" for all entries in this curated set

    Notes:
        - All genes are literature-validated housekeeping genes
        - Pattern matches compile_known_genes() from known_genes.py
        - Total rows = len(HOUSEKEEPING_GENES_CORE)
    """
    df = pl.DataFrame({
        "gene_symbol": list(HOUSEKEEPING_GENES_CORE),
        "source": ["literature_validated"] * len(HOUSEKEEPING_GENES_CORE),
        "confidence": ["HIGH"] * len(HOUSEKEEPING_GENES_CORE),
    })

    return df


def validate_negative_controls(
    store: PipelineStore,
    percentile_threshold: float = 0.50
) -> dict:
    """
    Validate that housekeeping genes rank LOW in composite scores (negative controls).

    Computes percentile ranks for housekeeping genes using PERCENT_RANK window function
    across ALL genes. Validates that housekeeping genes rank BELOW median (inverted
    threshold logic vs positive controls).

    Args:
        store: PipelineStore with scored_genes table
        percentile_threshold: Maximum median percentile for validation (default 0.50)

    Returns:
        Dict with keys:
        - total_expected: int - count of housekeeping genes in reference list
        - total_in_dataset: int - count of housekeeping genes found in scored_genes
        - median_percentile: float - median percentile rank of housekeeping genes
        - top_quartile_count: int - count of housekeeping genes >= 75th percentile (should be low)
        - in_high_tier_count: int - count of housekeeping genes >= 70% score (should be near zero)
        - validation_passed: bool - True if median < percentile_threshold (INVERTED)
        - housekeeping_gene_details: list[dict] - top 20 housekeeping genes by percentile ASC (lowest-ranking)
        - reason: str - explanation if validation failed (optional)

    Notes:
        - INVERTED LOGIC: Low percentile ranks are GOOD for negative controls
        - Uses PERCENT_RANK() which returns 0.0 (lowest) to 1.0 (highest)
        - Genes without composite_score (NULL) are excluded from ranking
        - Creates temporary table _housekeeping_genes for the join
        - Cleans up temp table after query completion
    """
    logger.info("validate_negative_controls_start", threshold=percentile_threshold)

    # Compile housekeeping genes
    housekeeping_df = compile_housekeeping_genes()
    total_expected = housekeeping_df["gene_symbol"].n_unique()

    # Register housekeeping genes as temporary DuckDB table
    store.conn.execute("DROP TABLE IF EXISTS _housekeeping_genes")
    store.conn.execute("CREATE TEMP TABLE _housekeeping_genes AS SELECT * FROM housekeeping_df")

    # Query to compute percentile ranks for housekeeping genes
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
        hg.source
    FROM ranked_genes rg
    INNER JOIN _housekeeping_genes hg ON rg.gene_symbol = hg.gene_symbol
    ORDER BY rg.percentile_rank ASC
    """

    result = store.conn.execute(query).pl()

    # Clean up temp table
    store.conn.execute("DROP TABLE IF EXISTS _housekeeping_genes")

    # If no housekeeping genes found, return failure
    if result.height == 0:
        logger.error(
            "validate_negative_controls_failed",
            reason="no_housekeeping_genes_found",
            expected=total_expected,
            found=0,
        )
        return {
            "total_expected": total_expected,
            "total_in_dataset": 0,
            "median_percentile": None,
            "top_quartile_count": 0,
            "in_high_tier_count": 0,
            "validation_passed": False,
            "housekeeping_gene_details": [],
            "reason": "no_housekeeping_genes_found",
        }

    # Compute validation metrics
    total_in_dataset = result.height
    median_percentile = float(result["percentile_rank"].median())

    # Count housekeeping genes in top quartile (bad for negative controls)
    top_quartile_genes = result.filter(pl.col("percentile_rank") >= 0.75)
    top_quartile_count = top_quartile_genes.height

    # Count housekeeping genes with high composite scores (>= 0.70, near HIGH tier threshold)
    high_tier_genes = result.filter(pl.col("composite_score") >= 0.70)
    in_high_tier_count = high_tier_genes.height

    # INVERTED validation logic: median should be BELOW threshold
    validation_passed = median_percentile < percentile_threshold

    # Extract top 20 housekeeping genes by percentile ASC (lowest-ranking = best for negative controls)
    housekeeping_gene_details = result.head(20).select([
        "gene_symbol",
        "composite_score",
        "percentile_rank",
        "source"
    ]).to_dicts()

    # Log validation results
    if validation_passed:
        logger.info(
            "validate_negative_controls_passed",
            total_expected=total_expected,
            total_found=total_in_dataset,
            median_percentile=f"{median_percentile:.4f}",
            top_quartile_count=top_quartile_count,
            in_high_tier_count=in_high_tier_count,
            threshold=percentile_threshold,
        )
    else:
        logger.warning(
            "validate_negative_controls_failed",
            reason="median_above_threshold",
            median_percentile=f"{median_percentile:.4f}",
            threshold=percentile_threshold,
            top_quartile_count=top_quartile_count,
            in_high_tier_count=in_high_tier_count,
        )

    return {
        "total_expected": total_expected,
        "total_in_dataset": total_in_dataset,
        "median_percentile": median_percentile,
        "top_quartile_count": top_quartile_count,
        "in_high_tier_count": in_high_tier_count,
        "validation_passed": validation_passed,
        "housekeeping_gene_details": housekeeping_gene_details,
    }


def generate_negative_control_report(metrics: dict) -> str:
    """
    Generate human-readable negative control validation report.

    Args:
        metrics: Dict returned from validate_negative_controls()

    Returns:
        Multi-line text report summarizing validation results

    Notes:
        - Formats percentiles as percentages (e.g., "32.5%")
        - Includes table of lowest-ranked housekeeping genes (best outcome)
        - Shows pass/fail status prominently
        - INVERTED interpretation: LOW percentiles are GOOD for negative controls
    """
    passed = metrics["validation_passed"]
    status = "PASSED ✓" if passed else "FAILED ✗"

    # Handle case where no housekeeping genes found
    if metrics["total_in_dataset"] == 0:
        return f"""
Negative Control Validation: {status}

Reason: No housekeeping genes found in scored dataset
Expected: {metrics['total_expected']} housekeeping genes
Found: 0 genes

This indicates either:
1. Housekeeping genes were filtered out
2. Gene symbol mismatch between housekeeping list and scored_genes
3. No genes have composite scores yet
"""

    median_pct = metrics["median_percentile"] * 100
    top_q_count = metrics["top_quartile_count"]
    high_tier_count = metrics["in_high_tier_count"]

    report = [
        f"Negative Control Validation: {status}",
        "",
        "Summary:",
        f"  Housekeeping genes expected: {metrics['total_expected']}",
        f"  Housekeeping genes found: {metrics['total_in_dataset']}",
        f"  Median percentile: {median_pct:.1f}%",
        f"  Top quartile count: {top_q_count}",
        f"  High-tier count (score >= 0.70): {high_tier_count}",
        "",
    ]

    # Add interpretation (INVERTED: low percentile is good)
    if passed:
        report.append(
            f"Housekeeping genes rank LOW (median < 50th percentile), "
            "confirming scoring system specificity."
        )
    else:
        report.append(
            f"Warning: Housekeeping genes rank higher than expected. "
            f"Median percentile ({median_pct:.1f}%) >= 50.0%."
        )
        report.append(
            "This may indicate lack of specificity in evidence layer weights."
        )

    report.append("")
    report.append("Lowest-Ranked Housekeeping Genes (Best Outcome):")
    report.append("-" * 80)
    report.append(f"{'Gene':<12} {'Score':>8} {'Percentile':>12} {'Source':<20}")
    report.append("-" * 80)

    for gene in metrics["housekeeping_gene_details"]:
        gene_symbol = gene["gene_symbol"]
        score = gene["composite_score"]
        percentile = gene["percentile_rank"] * 100
        source = gene["source"]
        report.append(
            f"{gene_symbol:<12} {score:>8.4f} {percentile:>11.1f}% {source:<20}"
        )

    return "\n".join(report)

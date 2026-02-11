"""Confidence tiering logic for scored candidate genes."""

import polars as pl

# Default tier thresholds from research
TIER_THRESHOLDS = {
    "HIGH": {"composite_score": 0.7, "evidence_count": 3},
    "MEDIUM": {"composite_score": 0.4, "evidence_count": 2},
    "LOW": {"composite_score": 0.2, "evidence_count": 1},
}


def assign_tiers(
    scored_df: pl.DataFrame, thresholds: dict | None = None
) -> pl.DataFrame:
    """
    Assign confidence tiers to scored genes and filter out EXCLUDED genes.

    Uses configurable thresholds to classify genes into HIGH/MEDIUM/LOW tiers
    based on composite_score and evidence_count. Genes below LOW threshold
    are marked as EXCLUDED and filtered out.

    Args:
        scored_df: Polars DataFrame with columns:
            - gene_id (str)
            - gene_symbol (str)
            - composite_score (float, nullable)
            - evidence_count (int)
            - quality_flag (str)
            - All 6 layer score columns (nullable)
            - All 6 contribution columns (nullable)
        thresholds: Optional dict overriding TIER_THRESHOLDS. Expected format:
            {
                "HIGH": {"composite_score": float, "evidence_count": int},
                "MEDIUM": {"composite_score": float, "evidence_count": int},
                "LOW": {"composite_score": float, "evidence_count": int},
            }

    Returns:
        DataFrame with added confidence_tier column (str), sorted by
        composite_score DESC, gene_id ASC. EXCLUDED genes are filtered out.

    Notes:
        - Uses vectorized polars expressions (not row-by-row iteration)
        - Genes with NULL composite_score are always EXCLUDED
        - Deterministic sorting for reproducibility
        - Filtering happens before return (EXCLUDED rows removed)
    """
    # Use provided thresholds or defaults
    t = thresholds if thresholds is not None else TIER_THRESHOLDS

    # Extract threshold values for readability
    high_score = t["HIGH"]["composite_score"]
    high_count = t["HIGH"]["evidence_count"]
    med_score = t["MEDIUM"]["composite_score"]
    med_count = t["MEDIUM"]["evidence_count"]
    low_score = t["LOW"]["composite_score"]

    # Add confidence_tier column using vectorized when/then/otherwise chain
    result = scored_df.with_columns(
        pl.when(
            (pl.col("composite_score") >= high_score)
            & (pl.col("evidence_count") >= high_count)
        )
        .then(pl.lit("HIGH"))
        .when(
            (pl.col("composite_score") >= med_score)
            & (pl.col("evidence_count") >= med_count)
        )
        .then(pl.lit("MEDIUM"))
        .when(pl.col("composite_score") >= low_score)
        .then(pl.lit("LOW"))
        .otherwise(pl.lit("EXCLUDED"))
        .alias("confidence_tier")
    )

    # Filter out EXCLUDED genes
    result = result.filter(pl.col("confidence_tier") != "EXCLUDED")

    # Sort deterministically: composite_score DESC, gene_id ASC
    result = result.sort(["composite_score", "gene_id"], descending=[True, False])

    return result

"""Transform literature evidence: classify tiers and compute quality-weighted scores."""

from typing import Optional

import polars as pl
import structlog

logger = structlog.get_logger()


# Evidence quality weights for scoring
# Direct experimental evidence is most valuable, incidental mentions least valuable
EVIDENCE_QUALITY_WEIGHTS = {
    "direct_experimental": 1.0,
    "functional_mention": 0.6,
    "hts_hit": 0.3,
    "incidental": 0.1,
    "none": 0.0,
}

# Context relevance weights
# Cilia and sensory contexts are most relevant, cytoskeleton/polarity supportive
CONTEXT_WEIGHTS = {
    "cilia_context_count": 2.0,
    "sensory_context_count": 2.0,
    "cytoskeleton_context_count": 1.0,
    "cell_polarity_context_count": 1.0,
}


def classify_evidence_tier(df: pl.DataFrame) -> pl.DataFrame:
    """Classify literature evidence into quality tiers.

    Tiers (highest to lowest quality):
    - direct_experimental: Knockout/mutation + cilia/sensory context (highest confidence)
    - functional_mention: Mentioned in cilia/sensory context with multiple publications
    - hts_hit: High-throughput screen hit + cilia/sensory context
    - incidental: Publications exist but no cilia/sensory context
    - none: No publications found (or query failed)

    Args:
        df: DataFrame with columns: gene_symbol, total_pubmed_count, cilia_context_count,
            sensory_context_count, direct_experimental_count, hts_screen_count

    Returns:
        DataFrame with added evidence_tier column
    """
    logger.info("literature_classify_start", row_count=len(df))

    # Define tier classification logic using polars expressions
    # Priority order: direct_experimental > functional_mention > hts_hit > incidental > none

    df = df.with_columns([
        pl.when(
            # Direct experimental: knockout/mutation evidence + cilia/sensory context (HIGHEST TIER)
            (pl.col("direct_experimental_count").is_not_null()) &
            (pl.col("direct_experimental_count") >= 1) &
            (
                (pl.col("cilia_context_count").is_not_null() & (pl.col("cilia_context_count") >= 1)) |
                (pl.col("sensory_context_count").is_not_null() & (pl.col("sensory_context_count") >= 1))
            )
        ).then(pl.lit("direct_experimental"))
        .when(
            # HTS hit: screen evidence + cilia/sensory context (SECOND TIER - prioritized over functional mention)
            (pl.col("hts_screen_count").is_not_null()) &
            (pl.col("hts_screen_count") >= 1) &
            (
                (pl.col("cilia_context_count").is_not_null() & (pl.col("cilia_context_count") >= 1)) |
                (pl.col("sensory_context_count").is_not_null() & (pl.col("sensory_context_count") >= 1))
            )
        ).then(pl.lit("hts_hit"))
        .when(
            # Functional mention: cilia/sensory context + multiple publications (THIRD TIER)
            (
                (pl.col("cilia_context_count").is_not_null() & (pl.col("cilia_context_count") >= 1)) |
                (pl.col("sensory_context_count").is_not_null() & (pl.col("sensory_context_count") >= 1))
            ) &
            (pl.col("total_pubmed_count").is_not_null()) &
            (pl.col("total_pubmed_count") >= 3)
        ).then(pl.lit("functional_mention"))
        .when(
            # Incidental: publications exist but no cilia/sensory context
            (pl.col("total_pubmed_count").is_not_null()) &
            (pl.col("total_pubmed_count") >= 1)
        ).then(pl.lit("incidental"))
        .otherwise(pl.lit("none"))  # No publications or query failed
        .alias("evidence_tier")
    ])

    # Count tier distribution for logging
    tier_counts = (
        df.group_by("evidence_tier")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )

    logger.info(
        "literature_classify_complete",
        tier_distribution={
            row["evidence_tier"]: row["count"]
            for row in tier_counts.to_dicts()
        },
    )

    return df


def compute_literature_score(df: pl.DataFrame) -> pl.DataFrame:
    """Compute quality-weighted literature score with bias mitigation.

    Quality-weighted scoring formula:
    1. Context score = weighted sum of context counts (cilia * 2.0 + sensory * 2.0 + cytoskeleton * 1.0 + polarity * 1.0)
    2. Apply evidence quality weight based on tier
    3. CRITICAL: Normalize by log2(total_pubmed_count + 1) to penalize genes where
       cilia mentions are tiny fraction of total literature (e.g., TP53: 5 cilia / 100K total)
    4. Rank-percentile normalization to [0, 1] scale

    This prevents well-studied genes (TP53, BRCA1) from dominating scores over
    focused candidates with high-quality but fewer publications.

    Args:
        df: DataFrame with context counts and evidence_tier column

    Returns:
        DataFrame with added literature_score_normalized column [0-1]
    """
    logger.info("literature_score_start", row_count=len(df))

    # Step 1: Compute weighted context score
    df = df.with_columns([
        (
            (pl.col("cilia_context_count").fill_null(0) * CONTEXT_WEIGHTS["cilia_context_count"]) +
            (pl.col("sensory_context_count").fill_null(0) * CONTEXT_WEIGHTS["sensory_context_count"]) +
            (pl.col("cytoskeleton_context_count").fill_null(0) * CONTEXT_WEIGHTS["cytoskeleton_context_count"]) +
            (pl.col("cell_polarity_context_count").fill_null(0) * CONTEXT_WEIGHTS["cell_polarity_context_count"])
        ).alias("context_score")
    ])

    # Step 2: Apply evidence quality weight
    # Map evidence_tier to quality weight using replace_strict with default
    df = df.with_columns([
        pl.col("evidence_tier")
        .replace_strict(EVIDENCE_QUALITY_WEIGHTS, default=0.0, return_dtype=pl.Float64)
        .alias("quality_weight")
    ])

    # Step 3: Bias mitigation via total publication normalization
    # Penalize genes where cilia mentions are small fraction of total literature
    df = df.with_columns([
        pl.when(pl.col("total_pubmed_count").is_not_null())
        .then(
            (pl.col("context_score") * pl.col("quality_weight")) /
            ((pl.col("total_pubmed_count") + 1).log(base=2))
        )
        .otherwise(pl.lit(None))
        .alias("raw_score")
    ])

    # Step 4: Rank-percentile normalization to [0, 1]
    # Only rank genes with non-null raw_score
    total_with_scores = df.filter(pl.col("raw_score").is_not_null()).height

    if total_with_scores == 0:
        # No valid scores - all NULL
        df = df.with_columns([
            pl.lit(None, dtype=pl.Float64).alias("literature_score_normalized")
        ])
    else:
        # Compute rank percentile
        df = df.with_columns([
            pl.when(pl.col("raw_score").is_not_null())
            .then(
                pl.col("raw_score").rank(method="average") / total_with_scores
            )
            .otherwise(pl.lit(None))
            .alias("literature_score_normalized")
        ])

    # Drop intermediate columns
    df = df.drop(["context_score", "quality_weight", "raw_score"])

    # Log score statistics
    score_stats = df.filter(pl.col("literature_score_normalized").is_not_null()).select([
        pl.col("literature_score_normalized").min().alias("min"),
        pl.col("literature_score_normalized").max().alias("max"),
        pl.col("literature_score_normalized").mean().alias("mean"),
        pl.col("literature_score_normalized").median().alias("median"),
    ])

    if len(score_stats) > 0:
        stats = score_stats.to_dicts()[0]
        logger.info(
            "literature_score_complete",
            min_score=round(stats["min"], 4) if stats["min"] is not None else None,
            max_score=round(stats["max"], 4) if stats["max"] is not None else None,
            mean_score=round(stats["mean"], 4) if stats["mean"] is not None else None,
            median_score=round(stats["median"], 4) if stats["median"] is not None else None,
            genes_with_scores=total_with_scores,
        )

    return df


def process_literature_evidence(
    gene_ids: list[str],
    gene_symbol_map: pl.DataFrame,
    email: str,
    api_key: Optional[str] = None,
    batch_size: int = 500,
    checkpoint_df: Optional[pl.DataFrame] = None,
    checkpoint_callback=None,
) -> pl.DataFrame:
    """End-to-end literature evidence processing pipeline.

    1. Map gene IDs to symbols
    2. Fetch PubMed literature evidence
    3. Classify evidence tiers
    4. Compute quality-weighted scores
    5. Join back to gene IDs

    Args:
        gene_ids: List of Ensembl gene IDs
        gene_symbol_map: DataFrame with columns: gene_id, gene_symbol
        email: Email for NCBI E-utilities (required)
        api_key: Optional NCBI API key for higher rate limit
        batch_size: Checkpoint save frequency (default: 500)
        checkpoint_df: Optional partial results to resume from

    Returns:
        DataFrame with columns: gene_id, gene_symbol, total_pubmed_count,
        cilia_context_count, sensory_context_count, cytoskeleton_context_count,
        cell_polarity_context_count, direct_experimental_count, hts_screen_count,
        evidence_tier, literature_score_normalized
    """
    from usher_pipeline.evidence.literature.fetch import fetch_literature_evidence

    logger.info(
        "literature_process_start",
        gene_count=len(gene_ids),
        has_checkpoint=checkpoint_df is not None,
    )

    # Step 1: Map gene IDs to symbols
    gene_map = gene_symbol_map.filter(pl.col("gene_id").is_in(gene_ids))
    # Deduplicate symbols for PubMed queries (many gene_ids can share a symbol)
    unique_symbols = gene_map["gene_symbol"].unique().to_list()

    logger.info(
        "literature_gene_mapping",
        input_ids=len(gene_ids),
        mapped_symbols=len(unique_symbols),
    )

    # Step 2: Fetch literature evidence (one query per unique symbol)
    lit_df = fetch_literature_evidence(
        gene_symbols=unique_symbols,
        email=email,
        api_key=api_key,
        batch_size=batch_size,
        checkpoint_df=checkpoint_df,
        checkpoint_callback=checkpoint_callback,
    )

    # Step 3: Classify evidence tiers
    lit_df = classify_evidence_tier(lit_df)

    # Step 4: Compute quality-weighted scores
    lit_df = compute_literature_score(lit_df)

    # Step 5: Join back to gene IDs (lit_df has unique symbols, gene_map may have
    # multiple gene_ids per symbol — this is correct, each gene_id gets its score)
    result_df = gene_map.join(
        lit_df,
        on="gene_symbol",
        how="left",
    )

    logger.info(
        "literature_process_complete",
        total_genes=len(result_df),
    )

    return result_df

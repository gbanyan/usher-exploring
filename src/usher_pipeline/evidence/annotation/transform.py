"""Transform and normalize gene annotation completeness metrics."""

import math
from pathlib import Path

import polars as pl
import structlog

from usher_pipeline.evidence.annotation.fetch import (
    fetch_go_annotations,
    fetch_uniprot_scores,
)

logger = structlog.get_logger()


def classify_annotation_tier(df: pl.DataFrame) -> pl.DataFrame:
    """Classify genes into annotation tiers based on composite metrics.

    Tier definitions:
    - "well_annotated": go_term_count >= 20 AND uniprot_annotation_score >= 4
    - "partially_annotated": go_term_count >= 5 OR uniprot_annotation_score >= 3
    - "poorly_annotated": Everything else (including NULLs)

    Conservative approach: NULL GO counts treated as zero for tier classification
    (assume unannotated until proven otherwise).

    Args:
        df: DataFrame with go_term_count and uniprot_annotation_score columns

    Returns:
        DataFrame with annotation_tier column added
    """
    logger.info("classify_annotation_tier_start", row_count=df.height)

    # Fill NULL GO counts with 0 for tier classification (conservative)
    # But preserve original NULL for downstream NULL handling
    df = df.with_columns([
        pl.col("go_term_count").fill_null(0).alias("_go_count_filled"),
        pl.col("uniprot_annotation_score").fill_null(0).alias("_uniprot_score_filled"),
    ])

    # Apply tier classification logic
    df = df.with_columns(
        pl.when(
            (pl.col("_go_count_filled") >= 20) & (pl.col("_uniprot_score_filled") >= 4)
        )
        .then(pl.lit("well_annotated"))
        .when(
            (pl.col("_go_count_filled") >= 5) | (pl.col("_uniprot_score_filled") >= 3)
        )
        .then(pl.lit("partially_annotated"))
        .otherwise(pl.lit("poorly_annotated"))
        .alias("annotation_tier")
    )

    # Drop temporary filled columns
    df = df.drop(["_go_count_filled", "_uniprot_score_filled"])

    # Log tier distribution
    tier_counts = df.group_by("annotation_tier").len().sort("annotation_tier")
    logger.info("classify_annotation_tier_complete", tier_distribution=tier_counts.to_dicts())

    return df


def normalize_annotation_score(df: pl.DataFrame) -> pl.DataFrame:
    """Compute normalized composite annotation score (0-1 range).

    Formula: Weighted average of three components:
    - GO component (50%): log2(go_term_count + 1) normalized by max across dataset
    - UniProt component (30%): uniprot_annotation_score / 5.0
    - Pathway component (20%): has_pathway_membership as 0/1

    Result clamped to [0, 1]. NULL if ALL three inputs are NULL.

    Args:
        df: DataFrame with go_term_count, uniprot_annotation_score, has_pathway_membership

    Returns:
        DataFrame with annotation_score_normalized column added
    """
    logger.info("normalize_annotation_score_start", row_count=df.height)

    # Component weights
    WEIGHT_GO = 0.5
    WEIGHT_UNIPROT = 0.3
    WEIGHT_PATHWAY = 0.2

    # Compute GO component: log2(count + 1) normalized by max
    df = df.with_columns(
        pl.when(pl.col("go_term_count").is_not_null())
        .then((pl.col("go_term_count") + 1).log(base=2))
        .otherwise(None)
        .alias("_go_log")
    )

    # Get max for normalization (from non-NULL values)
    go_max = df.filter(pl.col("_go_log").is_not_null()).select(pl.col("_go_log").max()).item()

    if go_max is None or go_max == 0:
        # No GO data in dataset - all get NULL for GO component
        df = df.with_columns(pl.lit(None).cast(pl.Float64).alias("_go_component"))
    else:
        df = df.with_columns(
            pl.when(pl.col("_go_log").is_not_null())
            .then((pl.col("_go_log") / go_max) * WEIGHT_GO)
            .otherwise(None)
            .alias("_go_component")
        )

    # Compute UniProt component: score / 5.0
    df = df.with_columns(
        pl.when(pl.col("uniprot_annotation_score").is_not_null())
        .then((pl.col("uniprot_annotation_score") / 5.0) * WEIGHT_UNIPROT)
        .otherwise(None)
        .alias("_uniprot_component")
    )

    # Compute pathway component: boolean as 0/1
    df = df.with_columns(
        pl.when(pl.col("has_pathway_membership").is_not_null())
        .then(
            pl.when(pl.col("has_pathway_membership"))
            .then(WEIGHT_PATHWAY)
            .otherwise(0.0)
        )
        .otherwise(None)
        .alias("_pathway_component")
    )

    # Composite score: sum of non-NULL components, NULL if all NULL
    # Need to handle NULL properly: only compute if at least one component is non-NULL
    df = df.with_columns(
        pl.when(
            pl.col("_go_component").is_not_null()
            | pl.col("_uniprot_component").is_not_null()
            | pl.col("_pathway_component").is_not_null()
        )
        .then(
            # Sum components, treating NULL as 0 for the sum
            pl.col("_go_component").fill_null(0.0)
            + pl.col("_uniprot_component").fill_null(0.0)
            + pl.col("_pathway_component").fill_null(0.0)
        )
        .otherwise(None)
        .alias("annotation_score_normalized")
    )

    # Clamp to [0, 1] range (shouldn't exceed but defensive)
    df = df.with_columns(
        pl.when(pl.col("annotation_score_normalized").is_not_null())
        .then(
            pl.col("annotation_score_normalized").clip(0.0, 1.0)
        )
        .otherwise(None)
        .alias("annotation_score_normalized")
    )

    # Drop temporary columns
    df = df.drop(["_go_log", "_go_component", "_uniprot_component", "_pathway_component"])

    # Log score statistics
    stats = df.filter(pl.col("annotation_score_normalized").is_not_null()).select([
        pl.col("annotation_score_normalized").mean().alias("mean"),
        pl.col("annotation_score_normalized").median().alias("median"),
        pl.col("annotation_score_normalized").min().alias("min"),
        pl.col("annotation_score_normalized").max().alias("max"),
    ])

    if stats.height > 0:
        logger.info("normalize_annotation_score_complete", stats=stats.to_dicts()[0])
    else:
        logger.warning("normalize_annotation_score_complete", message="No valid scores computed")

    return df


def process_annotation_evidence(
    gene_ids: list[str],
    uniprot_mapping: pl.DataFrame,
) -> pl.DataFrame:
    """End-to-end annotation evidence processing pipeline.

    Composes: fetch GO -> fetch UniProt -> join -> classify tier -> normalize -> collect.

    Args:
        gene_ids: List of Ensembl gene IDs to process
        uniprot_mapping: DataFrame with gene_id and uniprot_accession columns

    Returns:
        Materialized DataFrame with all annotation completeness metrics ready for DuckDB
    """
    logger.info("process_annotation_evidence_start", gene_count=len(gene_ids))

    # Fetch GO annotations and pathway memberships
    go_df = fetch_go_annotations(gene_ids)

    # Fetch UniProt annotation scores
    uniprot_df = fetch_uniprot_scores(gene_ids, uniprot_mapping)

    # Join GO and UniProt data
    df = go_df.join(uniprot_df, on="gene_id", how="left")

    # Classify annotation tiers
    df = classify_annotation_tier(df)

    # Normalize composite score
    df = normalize_annotation_score(df)

    logger.info("process_annotation_evidence_complete", result_count=df.height)

    return df

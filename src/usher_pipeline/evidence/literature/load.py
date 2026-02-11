"""Load literature evidence to DuckDB with provenance tracking."""

from typing import Optional

import polars as pl
import structlog

from usher_pipeline.persistence import PipelineStore, ProvenanceTracker

logger = structlog.get_logger()


def load_to_duckdb(
    df: pl.DataFrame,
    store: PipelineStore,
    provenance: ProvenanceTracker,
    description: str = ""
) -> None:
    """Save literature evidence DataFrame to DuckDB with provenance.

    Creates or replaces the literature_evidence table (idempotent).
    Records provenance step with summary statistics.

    Args:
        df: Processed literature evidence DataFrame with evidence_tier and literature_score_normalized
        store: PipelineStore instance for DuckDB persistence
        provenance: ProvenanceTracker instance for metadata recording
        description: Optional description for checkpoint metadata
    """
    logger.info("literature_load_start", row_count=len(df))

    # Calculate summary statistics for provenance
    tier_counts = (
        df.group_by("evidence_tier")
        .agg(pl.count().alias("count"))
        .to_dicts()
    )
    tier_distribution = {row["evidence_tier"]: row["count"] for row in tier_counts}

    genes_with_evidence = df.filter(
        pl.col("evidence_tier").is_in(["direct_experimental", "functional_mention", "hts_hit"])
    ).height

    # Calculate mean literature score (excluding NULL)
    mean_score_result = df.filter(
        pl.col("literature_score_normalized").is_not_null()
    ).select(pl.col("literature_score_normalized").mean())

    mean_score = None
    if len(mean_score_result) > 0:
        mean_score = mean_score_result.to_dicts()[0]["literature_score_normalized"]

    # Count total PubMed queries made (estimate: 6 queries per gene)
    total_queries = len(df) * 6

    # Save to DuckDB with CREATE OR REPLACE (idempotent)
    store.save_dataframe(
        df=df,
        table_name="literature_evidence",
        description=description or "PubMed literature evidence with context-specific queries and quality-weighted scoring",
        replace=True
    )

    # Record provenance step with details
    provenance.record_step("load_literature_evidence", {
        "row_count": len(df),
        "genes_with_direct_evidence": tier_distribution.get("direct_experimental", 0),
        "genes_with_functional_mention": tier_distribution.get("functional_mention", 0),
        "genes_with_hts_hits": tier_distribution.get("hts_hit", 0),
        "genes_with_any_evidence": genes_with_evidence,
        "tier_distribution": tier_distribution,
        "mean_literature_score": round(mean_score, 4) if mean_score is not None else None,
        "estimated_pubmed_queries": total_queries,
    })

    logger.info(
        "literature_load_complete",
        row_count=len(df),
        tier_distribution=tier_distribution,
        genes_with_evidence=genes_with_evidence,
        mean_score=round(mean_score, 4) if mean_score is not None else None,
    )


def query_literature_supported(
    store: PipelineStore,
    min_tier: str = "functional_mention"
) -> pl.DataFrame:
    """Query genes with literature support at or above specified tier.

    Demonstrates DuckDB query capability and filters genes by evidence quality.

    Args:
        store: PipelineStore instance
        min_tier: Minimum evidence tier (default: "functional_mention")
                  Options: "direct_experimental", "functional_mention", "hts_hit", "incidental"

    Returns:
        DataFrame with literature-supported genes sorted by literature_score_normalized (desc)
        Columns: gene_id, gene_symbol, evidence_tier, literature_score_normalized,
                 cilia_context_count, sensory_context_count, total_pubmed_count
    """
    logger.info("literature_query_supported", min_tier=min_tier)

    # Define tier hierarchy
    tier_hierarchy = {
        "direct_experimental": 0,
        "functional_mention": 1,
        "hts_hit": 2,
        "incidental": 3,
        "none": 4,
    }

    if min_tier not in tier_hierarchy:
        raise ValueError(f"Invalid tier: {min_tier}. Must be one of {list(tier_hierarchy.keys())}")

    min_tier_rank = tier_hierarchy[min_tier]

    # Build tier list for SQL IN clause
    valid_tiers = [tier for tier, rank in tier_hierarchy.items() if rank <= min_tier_rank]
    tiers_str = ", ".join(f"'{tier}'" for tier in valid_tiers)

    # Query DuckDB
    df = store.execute_query(
        f"""
        SELECT gene_id, gene_symbol, evidence_tier, literature_score_normalized,
               cilia_context_count, sensory_context_count, total_pubmed_count,
               direct_experimental_count, hts_screen_count
        FROM literature_evidence
        WHERE evidence_tier IN ({tiers_str})
        ORDER BY literature_score_normalized DESC NULLS LAST
        """
    )

    logger.info("literature_query_complete", result_count=len(df))

    return df

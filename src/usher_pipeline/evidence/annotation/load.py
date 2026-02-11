"""Load gene annotation completeness data to DuckDB with provenance tracking."""

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
    """Save annotation completeness DataFrame to DuckDB with provenance.

    Creates or replaces the annotation_completeness table (idempotent).
    Records provenance step with summary statistics.

    Args:
        df: Processed annotation completeness DataFrame with tiers and normalized scores
        store: PipelineStore instance for DuckDB persistence
        provenance: ProvenanceTracker instance for metadata recording
        description: Optional description for checkpoint metadata
    """
    logger.info("annotation_load_start", row_count=len(df))

    # Calculate summary statistics for provenance
    well_annotated_count = df.filter(pl.col("annotation_tier") == "well_annotated").height
    partial_count = df.filter(pl.col("annotation_tier") == "partially_annotated").height
    poor_count = df.filter(pl.col("annotation_tier") == "poorly_annotated").height
    null_go_count = df.filter(pl.col("go_term_count").is_null()).height
    null_uniprot_count = df.filter(pl.col("uniprot_annotation_score").is_null()).height
    null_score_count = df.filter(pl.col("annotation_score_normalized").is_null()).height

    # Compute mean/median for non-NULL scores
    score_stats = df.filter(pl.col("annotation_score_normalized").is_not_null()).select([
        pl.col("annotation_score_normalized").mean().alias("mean"),
        pl.col("annotation_score_normalized").median().alias("median"),
    ])

    mean_score = score_stats["mean"][0] if score_stats.height > 0 else None
    median_score = score_stats["median"][0] if score_stats.height > 0 else None

    # Save to DuckDB with CREATE OR REPLACE (idempotent)
    store.save_dataframe(
        df=df,
        table_name="annotation_completeness",
        description=description or "Gene annotation completeness metrics with GO terms, UniProt scores, and pathway membership",
        replace=True
    )

    # Record provenance step with details
    provenance.record_step("load_annotation_completeness", {
        "row_count": len(df),
        "well_annotated_count": well_annotated_count,
        "partially_annotated_count": partial_count,
        "poorly_annotated_count": poor_count,
        "null_go_count": null_go_count,
        "null_uniprot_count": null_uniprot_count,
        "null_score_count": null_score_count,
        "mean_annotation_score": mean_score,
        "median_annotation_score": median_score,
    })

    logger.info(
        "annotation_load_complete",
        row_count=len(df),
        well_annotated=well_annotated_count,
        partially_annotated=partial_count,
        poorly_annotated=poor_count,
        null_go=null_go_count,
        null_uniprot=null_uniprot_count,
        null_score=null_score_count,
        mean_score=mean_score,
        median_score=median_score,
    )


def query_poorly_annotated(
    store: PipelineStore,
    max_score: float = 0.3
) -> pl.DataFrame:
    """Query poorly annotated genes from DuckDB.

    Identifies under-studied genes that may be promising cilia/Usher candidates
    when combined with other evidence layers.

    Args:
        store: PipelineStore instance
        max_score: Maximum annotation score threshold (default: 0.3 = lower 30% of annotation distribution)

    Returns:
        DataFrame with poorly annotated genes sorted by annotation score (lowest first)
        Columns: gene_id, gene_symbol, go_term_count, uniprot_annotation_score,
                 has_pathway_membership, annotation_tier, annotation_score_normalized
    """
    logger.info("annotation_query_poorly_annotated", max_score=max_score)

    # Query DuckDB: poorly annotated genes with valid scores
    df = store.execute_query(
        """
        SELECT gene_id, gene_symbol, go_term_count, uniprot_annotation_score,
               has_pathway_membership, annotation_tier, annotation_score_normalized
        FROM annotation_completeness
        WHERE annotation_score_normalized IS NOT NULL
          AND annotation_score_normalized <= ?
        ORDER BY annotation_score_normalized ASC
        """,
        params=[max_score]
    )

    logger.info("annotation_query_complete", result_count=len(df))

    return df

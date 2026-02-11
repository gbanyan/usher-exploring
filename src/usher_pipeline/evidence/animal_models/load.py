"""Load animal model phenotype data to DuckDB with provenance tracking."""

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
    """Save animal model phenotype DataFrame to DuckDB with provenance.

    Creates or replaces the animal_model_phenotypes table (idempotent).
    Records provenance step with summary statistics.

    Args:
        df: Processed animal model DataFrame with orthologs, phenotypes, and scores
        store: PipelineStore instance for DuckDB persistence
        provenance: ProvenanceTracker instance for metadata recording
        description: Optional description for checkpoint metadata
    """
    logger.info("animal_model_load_start", row_count=len(df))

    # Calculate summary statistics for provenance
    with_mouse = df.filter(pl.col("mouse_ortholog").is_not_null()).height
    with_zebrafish = df.filter(pl.col("zebrafish_ortholog").is_not_null()).height
    with_sensory = df.filter(pl.col("sensory_phenotype_count").is_not_null()).height

    # Ortholog confidence distribution
    if with_mouse > 0:
        mouse_conf_dist = (
            df.filter(pl.col("mouse_ortholog").is_not_null())
            .group_by("mouse_ortholog_confidence")
            .agg(pl.len())
            .to_dicts()
        )
    else:
        mouse_conf_dist = []

    if with_zebrafish > 0:
        zebrafish_conf_dist = (
            df.filter(pl.col("zebrafish_ortholog").is_not_null())
            .group_by("zebrafish_ortholog_confidence")
            .agg(pl.len())
            .to_dicts()
        )
    else:
        zebrafish_conf_dist = []

    # Mean sensory phenotype count
    mean_sensory_count = (
        df.filter(pl.col("sensory_phenotype_count").is_not_null())
        .select(pl.col("sensory_phenotype_count").mean())
        .item()
    )
    if mean_sensory_count is None:
        mean_sensory_count = 0.0

    # Save to DuckDB with CREATE OR REPLACE (idempotent)
    store.save_dataframe(
        df=df,
        table_name="animal_model_phenotypes",
        description=description or "Animal model phenotypes from MGI, ZFIN, and IMPC with ortholog confidence scoring",
        replace=True
    )

    # Record provenance step with details
    provenance.record_step("load_animal_model_phenotypes", {
        "row_count": len(df),
        "genes_with_mouse_ortholog": with_mouse,
        "genes_with_zebrafish_ortholog": with_zebrafish,
        "genes_with_sensory_phenotypes": with_sensory,
        "mouse_confidence_distribution": mouse_conf_dist,
        "zebrafish_confidence_distribution": zebrafish_conf_dist,
        "mean_sensory_phenotype_count": round(mean_sensory_count, 2),
    })

    logger.info(
        "animal_model_load_complete",
        row_count=len(df),
        with_mouse=with_mouse,
        with_zebrafish=with_zebrafish,
        with_sensory=with_sensory,
    )


def query_sensory_phenotype_genes(
    store: PipelineStore,
    min_score: float = 0.3
) -> pl.DataFrame:
    """Query genes with high animal model evidence from DuckDB.

    Args:
        store: PipelineStore instance
        min_score: Minimum animal model score threshold (0-1)

    Returns:
        DataFrame with genes having animal model score >= min_score,
        sorted by score (highest first)
    """
    logger.info("animal_model_query_start", min_score=min_score)

    # Query DuckDB: genes with sufficient animal model evidence
    df = store.execute_query(
        """
        SELECT gene_id, mouse_ortholog, zebrafish_ortholog,
               sensory_phenotype_count, phenotype_categories,
               animal_model_score_normalized
        FROM animal_model_phenotypes
        WHERE animal_model_score_normalized >= ?
        ORDER BY animal_model_score_normalized DESC
        """,
        params=[min_score]
    )

    logger.info("animal_model_query_complete", result_count=len(df))

    return df

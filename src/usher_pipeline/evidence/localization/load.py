"""Load localization evidence to DuckDB with provenance tracking."""

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
    """Save localization evidence DataFrame to DuckDB with provenance.

    Creates or replaces the subcellular_localization table (idempotent).
    Records provenance step with summary statistics.

    Args:
        df: Processed localization DataFrame with evidence types and scores
        store: PipelineStore instance for DuckDB persistence
        provenance: ProvenanceTracker instance for metadata recording
        description: Optional description for checkpoint metadata
    """
    logger.info("localization_load_start", row_count=len(df))

    # Calculate summary statistics for provenance
    experimental_count = df.filter(pl.col("evidence_type") == "experimental").height
    computational_count = df.filter(pl.col("evidence_type") == "computational").height
    both_count = df.filter(pl.col("evidence_type") == "both").height
    none_count = df.filter(pl.col("evidence_type") == "none").height

    cilia_compartment_count = df.filter(
        (pl.col("compartment_cilia") == True) | (pl.col("compartment_centrosome") == True)
    ).height

    mean_localization_score = df["localization_score_normalized"].mean()

    # Count genes with high cilia proximity (> 0.5)
    high_proximity_count = df.filter(
        pl.col("cilia_proximity_score") > 0.5
    ).height

    # Save to DuckDB with CREATE OR REPLACE (idempotent)
    store.save_dataframe(
        df=df,
        table_name="subcellular_localization",
        description=description or "HPA subcellular localization with cilia/centrosome proteomics cross-references",
        replace=True
    )

    # Record provenance step with details
    provenance.record_step("load_subcellular_localization", {
        "row_count": len(df),
        "experimental_count": experimental_count,
        "computational_count": computational_count,
        "both_count": both_count,
        "none_count": none_count,
        "cilia_compartment_count": cilia_compartment_count,
        "high_proximity_count": high_proximity_count,
        "mean_localization_score": float(mean_localization_score) if mean_localization_score is not None else None,
    })

    logger.info(
        "localization_load_complete",
        row_count=len(df),
        experimental=experimental_count,
        computational=computational_count,
        both=both_count,
        none=none_count,
        cilia_compartment=cilia_compartment_count,
        high_proximity=high_proximity_count,
        mean_score=mean_localization_score,
    )


def query_cilia_localized(
    store: PipelineStore,
    proximity_threshold: float = 0.5
) -> pl.DataFrame:
    """Query genes with high cilia proximity scores from DuckDB.

    Demonstrates DuckDB query capability and provides helper for downstream
    analysis. Returns genes with strong localization evidence for cilia-related
    compartments.

    Args:
        store: PipelineStore instance
        proximity_threshold: Minimum cilia_proximity_score (default: 0.5)

    Returns:
        DataFrame with cilia-localized genes sorted by localization score
        Columns: gene_id, gene_symbol, evidence_type, compartment flags,
                 cilia_proximity_score, localization_score_normalized
    """
    logger.info("localization_query_cilia", proximity_threshold=proximity_threshold)

    # Query DuckDB: genes with high cilia proximity
    df = store.execute_query(
        """
        SELECT gene_id, gene_symbol, evidence_type,
               compartment_cilia, compartment_centrosome, compartment_basal_body,
               in_cilia_proteomics, in_centrosome_proteomics,
               cilia_proximity_score, localization_score_normalized
        FROM subcellular_localization
        WHERE cilia_proximity_score > ?
        ORDER BY localization_score_normalized DESC, cilia_proximity_score DESC
        """,
        params=[proximity_threshold]
    )

    logger.info("localization_query_complete", result_count=len(df))

    return df

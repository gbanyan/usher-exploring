"""Load expression evidence data to DuckDB with provenance tracking."""

from typing import Optional

import polars as pl
import structlog

from usher_pipeline.persistence import PipelineStore, ProvenanceTracker
from usher_pipeline.evidence.expression.models import EXPRESSION_TABLE_NAME

logger = structlog.get_logger()


def load_to_duckdb(
    df: pl.DataFrame,
    store: PipelineStore,
    provenance: ProvenanceTracker,
    description: str = ""
) -> None:
    """Save expression evidence DataFrame to DuckDB with provenance.

    Creates or replaces the tissue_expression table (idempotent).
    Records provenance step with summary statistics.

    Args:
        df: Processed expression DataFrame with tau_specificity and expression_score_normalized
        store: PipelineStore instance for DuckDB persistence
        provenance: ProvenanceTracker instance for metadata recording
        description: Optional description for checkpoint metadata
    """
    logger.info("expression_load_start", row_count=len(df))

    # Calculate summary statistics for provenance
    # Genes with retina expression (any source)
    retina_expr_count = df.filter(
        pl.col("hpa_retina_tpm").is_not_null() |
        pl.col("gtex_retina_tpm").is_not_null() |
        pl.col("cellxgene_photoreceptor_expr").is_not_null()
    ).height

    # Genes with inner ear expression (primarily CellxGene)
    inner_ear_expr_count = df.filter(
        pl.col("cellxgene_hair_cell_expr").is_not_null()
    ).height

    # Mean Tau specificity (excluding NULLs)
    mean_tau = df.select(pl.col("tau_specificity").mean()).item()

    # Expression score distribution
    expr_score_stats = df.select([
        pl.col("expression_score_normalized").min().alias("min"),
        pl.col("expression_score_normalized").max().alias("max"),
        pl.col("expression_score_normalized").mean().alias("mean"),
        pl.col("expression_score_normalized").median().alias("median"),
    ]).to_dicts()[0]

    # Save to DuckDB with CREATE OR REPLACE (idempotent)
    store.save_dataframe(
        df=df,
        table_name=EXPRESSION_TABLE_NAME,
        description=description or "Tissue expression evidence with HPA, GTEx, and CellxGene data",
        replace=True
    )

    # Record provenance step with details
    provenance.record_step("load_tissue_expression", {
        "row_count": len(df),
        "retina_expression_count": retina_expr_count,
        "inner_ear_expression_count": inner_ear_expr_count,
        "mean_tau_specificity": round(mean_tau, 3) if mean_tau else None,
        "expression_score_min": round(expr_score_stats["min"], 3) if expr_score_stats["min"] else None,
        "expression_score_max": round(expr_score_stats["max"], 3) if expr_score_stats["max"] else None,
        "expression_score_mean": round(expr_score_stats["mean"], 3) if expr_score_stats["mean"] else None,
        "expression_score_median": round(expr_score_stats["median"], 3) if expr_score_stats["median"] else None,
    })

    logger.info(
        "expression_load_complete",
        row_count=len(df),
        retina_expr=retina_expr_count,
        inner_ear_expr=inner_ear_expr_count,
        mean_tau=round(mean_tau, 3) if mean_tau else None,
    )


def query_tissue_enriched(
    store: PipelineStore,
    min_enrichment: float = 2.0
) -> pl.DataFrame:
    """Query genes enriched in Usher-relevant tissues from DuckDB.

    Args:
        store: PipelineStore instance
        min_enrichment: Minimum usher_tissue_enrichment threshold (default: 2.0 = 2x enriched)

    Returns:
        DataFrame with tissue-enriched genes sorted by enrichment (most enriched first)
        Columns: gene_id, gene_symbol, usher_tissue_enrichment, tau_specificity,
                 expression_score_normalized
    """
    logger.info("expression_query_enriched", min_enrichment=min_enrichment)

    # Query DuckDB: enriched genes
    df = store.execute_query(
        f"""
        SELECT gene_id, gene_symbol, usher_tissue_enrichment, tau_specificity,
               expression_score_normalized,
               hpa_retina_tpm, gtex_retina_tpm, cellxgene_photoreceptor_expr,
               cellxgene_hair_cell_expr
        FROM {EXPRESSION_TABLE_NAME}
        WHERE usher_tissue_enrichment >= ?
        ORDER BY usher_tissue_enrichment DESC
        """,
        params=[min_enrichment]
    )

    logger.info("expression_query_complete", result_count=len(df))

    return df

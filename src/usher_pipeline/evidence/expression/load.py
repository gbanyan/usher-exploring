"""Load expression evidence data to DuckDB with provenance tracking."""

from typing import Optional

import polars as pl
import structlog

from usher_pipeline.persistence import PipelineStore, ProvenanceTracker
from usher_pipeline.evidence.expression.models import (
    CELLXGENE_COLUMNS,
    EXPRESSION_SCHEMA_VERSION,
    EXPRESSION_TABLE_NAME,
    GTEX_TPM_COLUMNS,
    HPA_NTPM_COLUMNS,
    HPA_PROTEIN_LEVEL_COLUMNS,
    RESTRICTED_ENRICHMENT_COLUMN,
    RESTRICTED_TAU_COLUMN,
    RETINA_EVIDENCE_COLUMNS,
)

logger = structlog.get_logger()


def load_to_duckdb(
    df: pl.DataFrame,
    store: PipelineStore,
    provenance: ProvenanceTracker,
    description: str = "",
    source_metadata: Optional[dict] = None,
) -> None:
    """Save expression evidence DataFrame to DuckDB with provenance.

    Creates or replaces the tissue_expression table (idempotent).
    Records provenance step with summary statistics.

    Args:
        df: Processed expression DataFrame with restricted-panel expression
        contracts and expression_score_normalized
        store: PipelineStore instance for DuckDB persistence
        provenance: ProvenanceTracker instance for metadata recording
        description: Optional description for checkpoint metadata
        source_metadata: Source fingerprints and raw-column metadata from
            ``expression_source_metadata``.
    """
    logger.info("expression_load_start", row_count=len(df))

    # Calculate summary statistics for provenance
    # Genes with retina expression (any source) — check column existence
    retina_filter_parts = []
    for col in RETINA_EVIDENCE_COLUMNS:
        if col in df.columns:
            retina_filter_parts.append(pl.col(col) > 0)
    retina_expr_count = df.filter(
        pl.any_horizontal(retina_filter_parts) if retina_filter_parts else pl.lit(False)
    ).height

    # Genes with inner ear expression (primarily CellxGene)
    inner_ear_expr_count = (
        df.filter(pl.col("cellxgene_hair_cell_expr") > 0).height
        if "cellxgene_hair_cell_expr" in df.columns else 0
    )

    # Mean Tau specificity (excluding NULLs)
    mean_tau = df.select(pl.col(RESTRICTED_TAU_COLUMN).mean()).item()

    # Expression score distribution
    expr_score_stats = df.select([
        pl.col("expression_score_normalized").min().alias("min"),
        pl.col("expression_score_normalized").max().alias("max"),
        pl.col("expression_score_normalized").mean().alias("mean"),
        pl.col("expression_score_normalized").median().alias("median"),
    ]).to_dicts()[0]

    def coverage(columns: tuple[str, ...]) -> dict:
        return {
            column: {
                "non_null_count": int(df[column].is_not_null().sum())
                if column in df.columns else 0,
                "expressed_positive_count": int(df.filter(pl.col(column) > 0).height)
                if column in df.columns else 0,
                "row_count": len(df),
            }
            for column in columns
        }

    coverage_details = {
        "row_count": len(df),
        "hpa_protein_level": coverage(HPA_PROTEIN_LEVEL_COLUMNS),
        "hpa_ntpm": coverage(HPA_NTPM_COLUMNS),
        "gtex_tpm": coverage(GTEX_TPM_COLUMNS),
        "cellxgene": coverage(CELLXGENE_COLUMNS),
    }
    if source_metadata is not None:
        structural_absence = source_metadata.get("structurally_absent", {})
    else:
        # Structural absence can only be established from raw-source schema
        # metadata, never from an all-NULL derived checkpoint column.
        structural_absence = {}

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
        "mean_tau_restricted_panel_specificity": (
            round(mean_tau, 3) if mean_tau is not None else None
        ),
        "expression_score_min": round(expr_score_stats["min"], 3) if expr_score_stats["min"] is not None else None,
        "expression_score_max": round(expr_score_stats["max"], 3) if expr_score_stats["max"] is not None else None,
        "expression_score_mean": round(expr_score_stats["mean"], 3) if expr_score_stats["mean"] is not None else None,
        "expression_score_median": round(expr_score_stats["median"], 3) if expr_score_stats["median"] is not None else None,
        "schema_version": EXPRESSION_SCHEMA_VERSION,
        "coverage": coverage_details,
        "structurally_absent": structural_absence,
        "source_metadata": source_metadata,
    })

    logger.info(
        "expression_load_complete",
        row_count=len(df),
        retina_expr=retina_expr_count,
        inner_ear_expr=inner_ear_expr_count,
        mean_tau=round(mean_tau, 3) if mean_tau is not None else None,
    )


def query_tissue_enriched(
    store: PipelineStore,
    min_enrichment: float = 2.0
) -> pl.DataFrame:
    """Query genes enriched in Usher-relevant tissues from DuckDB.

    Args:
        store: PipelineStore instance
        min_enrichment: Minimum restricted-panel contrast threshold

    Returns:
        DataFrame with tissue-enriched genes sorted by enrichment (most enriched first)
        Columns: gene_id, gene_symbol, restricted-panel contrast, restricted-panel Tau,
                 expression_score_normalized
    """
    logger.info("expression_query_enriched", min_enrichment=min_enrichment)

    # Query DuckDB: enriched genes
    df = store.execute_query(
        f"""
        SELECT gene_id, gene_symbol, {RESTRICTED_ENRICHMENT_COLUMN},
               {RESTRICTED_TAU_COLUMN},
               expression_score_normalized,
               hpa_retina_protein_level, hpa_retina_ntpm,
               gtex_retina_tpm, cellxgene_photoreceptor_expr,
               cellxgene_hair_cell_expr
        FROM {EXPRESSION_TABLE_NAME}
        WHERE {RESTRICTED_ENRICHMENT_COLUMN} >= ?
        ORDER BY {RESTRICTED_ENRICHMENT_COLUMN} DESC
        """,
        params=[min_enrichment]
    )

    logger.info("expression_query_complete", result_count=len(df))

    return df

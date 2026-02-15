"""Load gnomAD constraint data to DuckDB with provenance tracking."""

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
    """Save gnomAD constraint DataFrame to DuckDB with provenance.

    Creates or replaces the gnomad_constraint table (idempotent).
    Records provenance step with summary statistics.

    Args:
        df: Processed gnomAD constraint DataFrame with quality_flag and loeuf_normalized
        store: PipelineStore instance for DuckDB persistence
        provenance: ProvenanceTracker instance for metadata recording
        description: Optional description for checkpoint metadata
    """
    logger.info("gnomad_load_start", row_count=len(df))

    # Enrich with Ensembl gene_id from gene_universe if missing
    # gnomAD data only has gene_symbol (HGNC); we need Ensembl gene_id for scoring JOINs
    if "gene_id" not in df.columns or df["gene_id"].null_count() == len(df):
        logger.info("gnomad_enriching_gene_ids", msg="Mapping gene_symbol to Ensembl gene_id via gene_universe")
        gene_map = store.conn.execute(
            "SELECT gene_id, gene_symbol FROM gene_universe"
        ).pl()
        if "gene_id" in df.columns:
            df = df.drop("gene_id")
        df = df.join(gene_map, on="gene_symbol", how="left")
        matched = df.filter(pl.col("gene_id").is_not_null()).height
        logger.info("gnomad_gene_id_enrichment", matched=matched, total=len(df))

    # Calculate summary statistics for provenance
    measured_count = df.filter(pl.col("quality_flag") == "measured").height
    incomplete_count = df.filter(pl.col("quality_flag") == "incomplete_coverage").height
    no_data_count = df.filter(pl.col("quality_flag") == "no_data").height
    null_loeuf_count = df.filter(pl.col("loeuf").is_null()).height

    # Save to DuckDB with CREATE OR REPLACE (idempotent)
    store.save_dataframe(
        df=df,
        table_name="gnomad_constraint",
        description=description or "gnomAD v4.1 constraint metrics with quality flags and normalized LOEUF scores",
        replace=True
    )

    # Record provenance step with details
    provenance.record_step("load_gnomad_constraint", {
        "row_count": len(df),
        "measured_count": measured_count,
        "incomplete_count": incomplete_count,
        "no_data_count": no_data_count,
        "null_loeuf_count": null_loeuf_count,
    })

    logger.info(
        "gnomad_load_complete",
        row_count=len(df),
        measured=measured_count,
        incomplete=incomplete_count,
        no_data=no_data_count,
        null_loeuf=null_loeuf_count,
    )


def query_constrained_genes(
    store: PipelineStore,
    loeuf_threshold: float = 0.6
) -> pl.DataFrame:
    """Query highly constrained genes from DuckDB.

    Demonstrates DuckDB query capability and validates GCON-03 interpretation:
    constrained genes are "important but under-studied" signals, not direct
    cilia involvement evidence.

    Args:
        store: PipelineStore instance
        loeuf_threshold: LOEUF threshold (lower = more constrained)
                         Default: 0.6 (represents genes in lower 40% of LOEUF distribution)

    Returns:
        DataFrame with constrained genes sorted by LOEUF (most constrained first)
        Columns: gene_id, gene_symbol, loeuf, pli, quality_flag, loeuf_normalized
    """
    logger.info("gnomad_query_constrained", loeuf_threshold=loeuf_threshold)

    # Query DuckDB: constrained genes with good coverage only
    df = store.execute_query(
        """
        SELECT gene_id, gene_symbol, loeuf, pli, quality_flag, loeuf_normalized
        FROM gnomad_constraint
        WHERE quality_flag = 'measured'
          AND loeuf < ?
        ORDER BY loeuf ASC
        """,
        params=[loeuf_threshold]
    )

    logger.info("gnomad_query_complete", result_count=len(df))

    return df

"""Load protein features to DuckDB with provenance tracking."""

from typing import Optional

import polars as pl
import structlog

from usher_pipeline.persistence import PipelineStore, ProvenanceTracker

logger = structlog.get_logger()


def load_to_duckdb(
    df: pl.DataFrame,
    store: PipelineStore,
    provenance: ProvenanceTracker,
    description: str = "",
) -> None:
    """Save protein features DataFrame to DuckDB with provenance.

    Creates or replaces the protein_features table (idempotent).
    Records provenance step with summary statistics.

    Args:
        df: Processed protein features DataFrame with normalized scores
        store: PipelineStore instance for DuckDB persistence
        provenance: ProvenanceTracker instance for metadata recording
        description: Optional description for checkpoint metadata
    """
    logger.info("protein_load_start", row_count=len(df))

    # Calculate summary statistics for provenance
    total_genes = len(df)
    with_uniprot = df.filter(pl.col("uniprot_id").is_not_null()).height
    null_uniprot = total_genes - with_uniprot

    cilia_domain_count = df.filter(pl.col("has_cilia_domain") == True).height
    scaffold_domain_count = df.filter(pl.col("scaffold_adaptor_domain") == True).height
    coiled_coil_count = df.filter(pl.col("coiled_coil") == True).height
    tm_domain_count = df.filter(pl.col("transmembrane_count") > 0).height

    # Mean domain count (only for proteins with data)
    mean_domain_count = (
        df.filter(pl.col("domain_count").is_not_null())
        .select(pl.col("domain_count").mean())
        .item()
    )
    if mean_domain_count is not None:
        mean_domain_count = round(mean_domain_count, 2)

    # Save to DuckDB with CREATE OR REPLACE (idempotent)
    store.save_dataframe(
        df=df,
        table_name="protein_features",
        description=description or "Protein features from UniProt/InterPro with domain composition and cilia motif detection",
        replace=True,
    )

    # Record provenance step with details
    provenance.record_step("load_protein_features", {
        "total_genes": total_genes,
        "with_uniprot": with_uniprot,
        "null_uniprot": null_uniprot,
        "cilia_domain_count": cilia_domain_count,
        "scaffold_domain_count": scaffold_domain_count,
        "coiled_coil_count": coiled_coil_count,
        "transmembrane_domain_count": tm_domain_count,
        "mean_domain_count": mean_domain_count,
    })

    logger.info(
        "protein_load_complete",
        row_count=total_genes,
        with_uniprot=with_uniprot,
        cilia_domains=cilia_domain_count,
        scaffold_domains=scaffold_domain_count,
        coiled_coils=coiled_coil_count,
    )


def query_cilia_candidates(
    store: PipelineStore,
) -> pl.DataFrame:
    """Query genes with cilia-associated protein features.

    Identifies candidate genes with:
    - Cilia domain annotations, OR
    - Both coiled-coil regions AND scaffold/adaptor domains

    This combination is enriched in known cilia proteins and provides
    structural evidence for potential cilia involvement.

    Args:
        store: PipelineStore instance

    Returns:
        DataFrame with candidate genes sorted by protein_score_normalized
        Columns: gene_id, gene_symbol, protein_length, domain_count,
                 coiled_coil, has_cilia_domain, scaffold_adaptor_domain,
                 protein_score_normalized
    """
    logger.info("protein_query_cilia_candidates")

    # Query DuckDB for genes with cilia features
    df = store.execute_query(
        """
        SELECT
            gene_id,
            gene_symbol,
            uniprot_id,
            protein_length,
            domain_count,
            coiled_coil,
            transmembrane_count,
            scaffold_adaptor_domain,
            has_cilia_domain,
            has_sensory_domain,
            protein_score_normalized
        FROM protein_features
        WHERE has_cilia_domain = TRUE
           OR (coiled_coil = TRUE AND scaffold_adaptor_domain = TRUE)
        ORDER BY protein_score_normalized DESC NULLS LAST
        """
    )

    logger.info("protein_query_complete", result_count=len(df))

    return df

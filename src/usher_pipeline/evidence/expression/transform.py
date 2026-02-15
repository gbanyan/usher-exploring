"""Transform and normalize tissue expression data."""

from pathlib import Path
from typing import Optional

import polars as pl
import structlog

from usher_pipeline.evidence.expression.fetch import (
    fetch_hpa_expression,
    fetch_gtex_expression,
    fetch_cellxgene_expression,
)

logger = structlog.get_logger()


def calculate_tau_specificity(
    df: pl.DataFrame,
    tissue_columns: list[str],
) -> pl.DataFrame:
    """Calculate Tau tissue specificity index.

    Tau measures tissue specificity: 0 = ubiquitous expression, 1 = tissue-specific.
    Formula: Tau = sum(1 - xi/xmax) / (n-1)
    where xi is expression in tissue i, xmax is max expression across tissues.

    If ANY tissue value is NULL, Tau is NULL (insufficient data for reliable specificity).

    Args:
        df: DataFrame with expression values across tissues
        tissue_columns: List of column names containing tissue expression values

    Returns:
        DataFrame with tau_specificity column added
    """
    logger.info("tau_calculation_start", tissue_count=len(tissue_columns))

    # Check if any tissue columns are missing
    available_cols = [col for col in tissue_columns if col in df.columns]
    if len(available_cols) < len(tissue_columns):
        missing = set(tissue_columns) - set(available_cols)
        logger.warning("tau_missing_columns", missing=list(missing))

    if not available_cols:
        # No tissue data available - return with NULL Tau
        return df.with_columns(pl.lit(None).cast(pl.Float64).alias("tau_specificity"))

    # For each gene, check if all tissue values are non-NULL
    # If any NULL, Tau is NULL
    # Otherwise, compute Tau = sum(1 - xi/xmax) / (n-1)

    # Create expression for NULL check
    has_all_data = pl.all_horizontal([pl.col(col).is_not_null() for col in available_cols])

    # Compute Tau only for genes with complete data
    # Step 1: Find max expression across tissues
    max_expr = pl.max_horizontal([pl.col(col) for col in available_cols])

    # Step 2: Compute sum(1 - xi/xmax) for each gene
    # Handle division by zero: if max_expr is 0, Tau is undefined (set to NULL)
    tau_sum = sum([
        pl.when(max_expr > 0)
        .then(1.0 - (pl.col(col) / max_expr))
        .otherwise(0.0)
        for col in available_cols
    ])

    # Step 3: Divide by (n-1), where n is number of tissues
    n_tissues = len(available_cols)
    if n_tissues <= 1:
        # Cannot compute specificity with only 1 tissue
        tau = pl.lit(None).cast(pl.Float64)
    else:
        tau = tau_sum / (n_tissues - 1)

    # Apply Tau only to genes with complete data
    df = df.with_columns(
        pl.when(has_all_data & (max_expr > 0))
        .then(tau)
        .otherwise(pl.lit(None))
        .alias("tau_specificity")
    )

    logger.info("tau_calculation_complete")

    return df


def compute_expression_score(df: pl.DataFrame) -> pl.DataFrame:
    """Compute Usher tissue enrichment and normalized expression score.

    Computes:
    1. usher_tissue_enrichment: Ratio of mean expression in Usher-relevant tissues
       (retina, inner ear proxies) to mean expression across all tissues.
       Higher ratio = more enriched in target tissues.
    2. expression_score_normalized: Weighted composite of:
       - 40%: usher_tissue_enrichment (normalized to 0-1)
       - 30%: tau_specificity
       - 30%: max_target_tissue_rank (percentile rank of max expression in targets)

    NULL if all expression data is NULL.

    Args:
        df: DataFrame with tissue expression columns and tau_specificity

    Returns:
        DataFrame with usher_tissue_enrichment and expression_score_normalized columns
    """
    logger.info("expression_score_start")

    # Define Usher-relevant tissue columns
    usher_tissue_cols = [
        "hpa_retina_tpm",
        "hpa_cerebellum_tpm",  # Cilia-rich
        "gtex_retina_tpm",
        "gtex_cerebellum_tpm",
        "cellxgene_photoreceptor_expr",
        "cellxgene_hair_cell_expr",
    ]

    # All tissue columns for global mean
    all_tissue_cols = [
        "hpa_retina_tpm",
        "hpa_cerebellum_tpm",
        "hpa_testis_tpm",
        "hpa_fallopian_tube_tpm",
        "gtex_retina_tpm",
        "gtex_cerebellum_tpm",
        "gtex_testis_tpm",
        "gtex_fallopian_tube_tpm",
        "cellxgene_photoreceptor_expr",
        "cellxgene_hair_cell_expr",
    ]

    # Filter to available columns
    usher_available = [col for col in usher_tissue_cols if col in df.columns]
    all_available = [col for col in all_tissue_cols if col in df.columns]

    if not usher_available or not all_available:
        # No expression data - return NULL scores
        return df.with_columns([
            pl.lit(None).cast(pl.Float64).alias("usher_tissue_enrichment"),
            pl.lit(None).cast(pl.Float64).alias("expression_score_normalized"),
        ])

    # Compute mean expression in Usher tissues (ignoring NULLs)
    usher_mean = pl.mean_horizontal([pl.col(col) for col in usher_available])

    # Compute mean expression across all tissues (ignoring NULLs)
    global_mean = pl.mean_horizontal([pl.col(col) for col in all_available])

    # Enrichment ratio: usher_mean / global_mean
    # If global_mean is 0 or NULL, enrichment is NULL
    enrichment = pl.when(global_mean > 0).then(usher_mean / global_mean).otherwise(pl.lit(None))

    df = df.with_columns(enrichment.alias("usher_tissue_enrichment"))

    # Normalize enrichment to 0-1 scale
    # Use percentile rank across all genes
    enrichment_percentile = pl.col("usher_tissue_enrichment").rank(method="average") / pl.col("usher_tissue_enrichment").count()

    # Compute max expression in target tissues
    max_target_expr = pl.max_horizontal([pl.col(col) for col in usher_available])
    max_target_percentile = max_target_expr.rank(method="average") / max_target_expr.count()

    # Composite score (weighted average)
    # If tau_specificity is NULL, we can still compute a partial score
    # But prefer to have at least enrichment or tau available
    composite = pl.when(
        pl.col("usher_tissue_enrichment").is_not_null() | pl.col("tau_specificity").is_not_null()
    ).then(
        0.4 * enrichment_percentile.fill_null(0.0) +
        0.3 * pl.col("tau_specificity").fill_null(0.0) +
        0.3 * max_target_percentile.fill_null(0.0)
    ).otherwise(pl.lit(None))

    df = df.with_columns(composite.alias("expression_score_normalized"))

    logger.info("expression_score_complete")

    return df


def process_expression_evidence(
    gene_ids: list[str],
    cache_dir: Optional[Path] = None,
    force: bool = False,
    skip_cellxgene: bool = False,
    gene_symbol_map: Optional[pl.DataFrame] = None,
) -> pl.DataFrame:
    """End-to-end expression evidence processing pipeline.

    Composes: fetch HPA -> fetch GTEx -> fetch CellxGene -> merge -> compute Tau -> compute score -> collect

    Args:
        gene_ids: List of Ensembl gene IDs to process
        cache_dir: Directory for caching downloads
        force: If True, re-download even if cached
        skip_cellxgene: If True, skip CellxGene fetching (optional dependency)

    Returns:
        Materialized DataFrame with expression evidence ready for DuckDB storage
    """
    logger.info("expression_pipeline_start", gene_count=len(gene_ids))

    cache_dir = Path(cache_dir) if cache_dir else Path("data/expression")

    # Fetch HPA expression (lazy)
    logger.info("fetching_hpa")
    lf_hpa = fetch_hpa_expression(gene_ids, cache_dir=cache_dir, force=force)

    # Fetch GTEx expression (lazy)
    logger.info("fetching_gtex")
    lf_gtex = fetch_gtex_expression(gene_ids, cache_dir=cache_dir, force=force)

    # Create gene universe DataFrame
    gene_universe = pl.LazyFrame({"gene_id": gene_ids})

    # Merge GTEx with gene universe (left join to preserve all genes)
    lf_merged = gene_universe.join(lf_gtex, on="gene_id", how="left")

    # Merge HPA data via gene_symbol mapping
    # HPA returns gene_symbol as key; we need gene_symbol_map to bridge to gene_id
    if gene_symbol_map is not None:
        logger.info("merging_hpa_via_symbol_map")
        # lf_hpa has: gene_symbol, hpa_retina_tpm, hpa_cerebellum_tpm, ...
        # gene_symbol_map has: gene_id, gene_symbol
        # Join HPA → symbol_map to get gene_id, then join into merged
        lf_hpa_with_id = lf_hpa.join(
            gene_symbol_map.select(["gene_id", "gene_symbol"]).lazy(),
            on="gene_symbol",
            how="inner",
        ).drop("gene_symbol")
        lf_merged = lf_merged.join(lf_hpa_with_id, on="gene_id", how="left")
    else:
        logger.warning("hpa_skipped_no_symbol_map", msg="gene_symbol_map not provided; HPA data will be NULL")

    # Fetch CellxGene if not skipped
    if not skip_cellxgene:
        logger.info("fetching_cellxgene")
        lf_cellxgene = fetch_cellxgene_expression(gene_ids, cache_dir=cache_dir)
        lf_merged = lf_merged.join(lf_cellxgene, on="gene_id", how="left")

    # Collect at this point to enable horizontal operations
    df = lf_merged.collect()

    # Calculate Tau specificity
    tissue_columns = [
        "hpa_retina_tpm",
        "hpa_cerebellum_tpm",
        "hpa_testis_tpm",
        "hpa_fallopian_tube_tpm",
        "gtex_retina_tpm",
        "gtex_cerebellum_tpm",
        "gtex_testis_tpm",
        "gtex_fallopian_tube_tpm",
        "cellxgene_photoreceptor_expr",
        "cellxgene_hair_cell_expr",
    ]
    # Filter to available columns
    available_tissue_cols = [col for col in tissue_columns if col in df.columns]

    if available_tissue_cols:
        df = calculate_tau_specificity(df, available_tissue_cols)
    else:
        df = df.with_columns(pl.lit(None).cast(pl.Float64).alias("tau_specificity"))

    # Compute expression score
    df = compute_expression_score(df)

    # Ensure all expected columns exist (NULL if source unavailable)
    expected_cols = {
        "hpa_retina_tpm": pl.Float64,
        "hpa_cerebellum_tpm": pl.Float64,
        "hpa_testis_tpm": pl.Float64,
        "hpa_fallopian_tube_tpm": pl.Float64,
        "gtex_retina_tpm": pl.Float64,
        "gtex_cerebellum_tpm": pl.Float64,
        "gtex_testis_tpm": pl.Float64,
        "gtex_fallopian_tube_tpm": pl.Float64,
        "cellxgene_photoreceptor_expr": pl.Float64,
        "cellxgene_hair_cell_expr": pl.Float64,
        "tau_specificity": pl.Float64,
        "usher_tissue_enrichment": pl.Float64,
        "expression_score_normalized": pl.Float64,
    }
    for col_name, dtype in expected_cols.items():
        if col_name not in df.columns:
            df = df.with_columns(pl.lit(None).cast(dtype).alias(col_name))

    logger.info(
        "expression_pipeline_complete",
        row_count=len(df),
        has_hpa=any("hpa_" in col and df[col].null_count() < len(df) for col in df.columns if "hpa_" in col),
        has_gtex=any("gtex_" in col and df[col].null_count() < len(df) for col in df.columns if "gtex_" in col),
        has_cellxgene=any("cellxgene_" in col and df[col].null_count() < len(df) for col in df.columns if "cellxgene_" in col),
    )

    return df

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
from usher_pipeline.evidence.expression.models import (
    GTEX_TPM_COLUMNS,
    HPA_NTPM_COLUMNS,
    HPA_PROTEIN_LEVEL_COLUMNS,
    HPA_PROTEIN_LEVEL_LABEL_COLUMNS,
    LEGACY_HPA_TPM_COLUMNS,
    RESTRICTED_ENRICHMENT_COLUMN,
    RESTRICTED_TAU_COLUMN,
)

logger = structlog.get_logger()


def calculate_tau_specificity(
    df: pl.DataFrame,
    tissue_columns: list[str],
) -> pl.DataFrame:
    """Calculate Tau tissue specificity index.

    Tau measures restricted-panel tissue specificity: 0 = ubiquitous expression,
    1 = tissue-specific.
    Formula: Tau = sum(1 - xi/xmax) / (n-1)
    where xi is expression in tissue i, xmax is max expression across tissues.

    Tau is computed only within the configured restricted tissue panel. Every
    observed non-NULL tissue, including zero/Not detected, contributes to the
    denominator and formula; only NULL tissues are excluded. Tau is NULL when
    fewer than two tissues are observed, or when the maximum expression is
    zero. Separate positive-expression coverage counts still treat zero as
    zero evidence.

    Args:
        df: DataFrame with expression values across tissues
        tissue_columns: List of column names containing tissue expression values

    Returns:
        DataFrame with the restricted-panel Tau column added
    """
    logger.info("tau_calculation_start", tissue_count=len(tissue_columns))

    # Check if any tissue columns are missing
    available_cols = [col for col in tissue_columns if col in df.columns]
    if len(available_cols) < len(tissue_columns):
        missing = set(tissue_columns) - set(available_cols)
        logger.warning("tau_missing_columns", missing=list(missing))

    if len(available_cols) < 2:
        # Cannot compute specificity with fewer than 2 tissues
        return df.with_columns(pl.lit(None).cast(pl.Float64).alias(RESTRICTED_TAU_COLUMN))

    # Per-gene count of observed tissues. Zero is observed and belongs in the
    # Tau denominator; only NULL observations are excluded.
    n_observed = sum(
        pl.col(col).is_not_null().cast(pl.Int32) for col in available_cols
    )

    # Max expression across the tissues that have data (NULLs ignored)
    max_expr = pl.max_horizontal([pl.col(col) for col in available_cols])

    # sum(1 - xi/xmax) over observed tissues; NULL tissues contribute 0 and
    # observed zero contributes 1 when max_expr is positive.
    tau_sum = sum(
        pl.when(pl.col(col).is_not_null() & (max_expr > 0))
        .then(1.0 - (pl.col(col) / max_expr))
        .otherwise(0.0)
        for col in available_cols
    )

    # Divide by (n_observed - 1); NULL when fewer than two tissues are observed.
    tau = (
        pl.when((n_observed >= 2) & (max_expr > 0))
        .then(tau_sum / (n_observed - 1))
        .otherwise(pl.lit(None))
    )

    df = df.with_columns(tau.alias(RESTRICTED_TAU_COLUMN))

    logger.info("tau_calculation_complete")

    return df


def compute_expression_score(df: pl.DataFrame) -> pl.DataFrame:
    """Compute restricted-panel enrichment and normalized expression score.

    Computes:
    1. usher_restricted_panel_contrast: mean of source-specific target/background
       contrasts.  Quantitative HPA nTPM and GTEx TPM use ratios within their
       own source.  Categorical HPA protein levels use within-column ordinal
       percentile ranks, never arithmetic on the 0-3 codes.
    2. expression_score_normalized: Weighted composite of:
       - 40%: usher_restricted_panel_contrast (normalized to 0-1)
       - 30%: restricted-panel Tau
       - 30%: max_target_tissue_rank (percentile rank of max expression in targets)

    Contrasts are restricted to the configured Usher-relevant tissue panel;
    they are not whole-body enrichment statistics. NULL if all expression
    data is NULL.

    Args:
        df: DataFrame with tissue expression columns and restricted-panel Tau

    Returns:
        DataFrame with restricted-panel enrichment and normalized score columns
    """
    logger.info("expression_score_start")

    legacy_columns = [column for column in LEGACY_HPA_TPM_COLUMNS if column in df.columns]
    if legacy_columns:
        logger.warning(
            "legacy_hpa_tpm_columns_ignored",
            columns=legacy_columns,
            reason="HPA categorical levels were previously mislabeled as TPM",
        )

    def has_values(column: str) -> bool:
        return column in df.columns and df[column].null_count() < df.height

    def ordinal_percentile(column: str) -> pl.Expr:
        # Ranking preserves category order without assuming equal distances
        # between Not detected, Low, Medium, and High.
        positive = pl.col(column) > 0
        positive_values = pl.when(positive).then(pl.col(column)).otherwise(None)
        positive_count = positive_values.count()
        return (
            pl.when(pl.col(column) == 0)
            .then(0.0)
            .when(positive)
            .then(positive_values.rank(method="average") / positive_count)
            .otherwise(pl.lit(None))
        )

    def quantitative_percentile(column: str) -> pl.Expr:
        positive = pl.col(column) > 0
        positive_values = pl.when(positive).then(pl.col(column)).otherwise(None)
        positive_count = positive_values.count()
        return (
            pl.when(pl.col(column) == 0)
            .then(0.0)
            .when(positive)
            .then(positive_values.rank(method="average") / positive_count)
            .otherwise(pl.lit(None))
        )

    source_enrichments: list[pl.Expr] = []
    enrichment_names: list[str] = []
    ordinal_target_columns: list[str] = []
    quantitative_target_columns: list[str] = []

    # HPA nTPM, when present, is quantitative; otherwise HPA protein levels
    # are ordinal and are compared only after within-tissue rank normalization.
    hpa_ntpm_target = [
        column for column in HPA_NTPM_COLUMNS[:2] if has_values(column)
    ]
    hpa_ntpm_background = [
        column for column in HPA_NTPM_COLUMNS[2:] if has_values(column)
    ]
    hpa_level_target = [
        column for column in HPA_PROTEIN_LEVEL_COLUMNS[:2] if has_values(column)
    ]
    hpa_level_background = [
        column for column in HPA_PROTEIN_LEVEL_COLUMNS[2:] if has_values(column)
    ]
    if hpa_ntpm_target and hpa_ntpm_background:
        target_mean = pl.mean_horizontal([pl.col(column) for column in hpa_ntpm_target])
        background_mean = pl.mean_horizontal(
            [pl.col(column) for column in hpa_ntpm_background]
        )
        name = "_hpa_ntpm_enrichment"
        source_enrichments.append(
            pl.when(
                target_mean.is_not_null()
                & background_mean.is_not_null()
                & (background_mean > 0)
            )
            .then(target_mean / background_mean)
            .otherwise(pl.lit(None))
            .alias(name)
        )
        enrichment_names.append(name)
        quantitative_target_columns.extend(hpa_ntpm_target)
    elif hpa_level_target and hpa_level_background:
        target_mean = pl.mean_horizontal(
            [ordinal_percentile(column) for column in hpa_level_target]
        )
        background_mean = pl.mean_horizontal(
            [ordinal_percentile(column) for column in hpa_level_background]
        )
        name = "_hpa_ordinal_enrichment"
        source_enrichments.append(
            pl.when(
                target_mean.is_not_null()
                & background_mean.is_not_null()
                & (background_mean > 0)
            )
            .then(target_mean / background_mean)
            .otherwise(pl.lit(None))
            .alias(name)
        )
        enrichment_names.append(name)
        ordinal_target_columns.extend(hpa_level_target)

    # GTEx median TPM remains a quantitative source and is normalized only
    # against other GTEx columns.
    gtex_target = [column for column in GTEX_TPM_COLUMNS[:2] if has_values(column)]
    gtex_background = [column for column in GTEX_TPM_COLUMNS[2:] if has_values(column)]
    if gtex_target and gtex_background:
        target_mean = pl.mean_horizontal([pl.col(column) for column in gtex_target])
        background_mean = pl.mean_horizontal([pl.col(column) for column in gtex_background])
        name = "_gtex_enrichment"
        source_enrichments.append(
            pl.when(
                target_mean.is_not_null()
                & background_mean.is_not_null()
                & (background_mean > 0)
            )
            .then(target_mean / background_mean)
            .otherwise(pl.lit(None))
            .alias(name)
        )
        enrichment_names.append(name)
        quantitative_target_columns.extend(gtex_target)

    cellxgene_target = "cellxgene_photoreceptor_expr"
    if cellxgene_target in df.columns:
        quantitative_target_columns.append(cellxgene_target)

    if not source_enrichments and not quantitative_target_columns and not ordinal_target_columns:
        # No expression data - return NULL scores
        return df.with_columns([
            pl.lit(None).cast(pl.Float64).alias(RESTRICTED_ENRICHMENT_COLUMN),
            pl.lit(None).cast(pl.Float64).alias("expression_score_normalized"),
        ])

    if source_enrichments:
        df = df.with_columns(source_enrichments)
        enrichment = pl.mean_horizontal([pl.col(name) for name in enrichment_names])
    else:
        enrichment = pl.lit(None).cast(pl.Float64)
    df = df.with_columns(enrichment.alias(RESTRICTED_ENRICHMENT_COLUMN))

    # Normalize enrichment to 0-1 scale
    # Use percentile rank across all genes
    enrichment_percentile = quantitative_percentile(RESTRICTED_ENRICHMENT_COLUMN)

    # Rank each source/target column independently before combining.  HPA
    # ordinal codes are ranked only; they are never mixed as raw values with
    # GTEx TPM or Census expression.
    target_percentiles = [
        quantitative_percentile(column)
        for column in quantitative_target_columns
    ] + [ordinal_percentile(column) for column in ordinal_target_columns]
    max_target_percentile = (
        pl.max_horizontal(target_percentiles)
        if target_percentiles
        else pl.lit(None).cast(pl.Float64)
    )

    # Composite score (weighted average)
    # If restricted-panel Tau is NULL, we can still compute a partial score
    # But prefer to have at least enrichment or tau available
    weighted_components = [
        (enrichment_percentile, 0.4),
        (pl.col(RESTRICTED_TAU_COLUMN), 0.3),
        (max_target_percentile, 0.3),
    ]
    numerator = sum(
        pl.when(expr.is_not_null()).then(expr * weight).otherwise(0.0)
        for expr, weight in weighted_components
    )
    denominator = sum(
        pl.when(expr.is_not_null()).then(weight).otherwise(0.0)
        for expr, weight in weighted_components
    )
    composite = pl.when(denominator > 0).then(numerator / denominator).otherwise(pl.lit(None))

    df = df.with_columns(composite.alias("expression_score_normalized"))

    logger.info("expression_score_complete")

    return df


def process_expression_evidence(
    gene_ids: list[str],
    cache_dir: Optional[Path] = None,
    force: bool = False,
    skip_cellxgene: bool = False,
    gene_symbol_map: Optional[pl.DataFrame] = None,
    census_version: str = "2025-11-08",
    cache_only: bool = False,
    cellxgene_metadata: Optional[dict] = None,
) -> pl.DataFrame:
    """End-to-end expression evidence processing pipeline.

    Composes: fetch HPA -> fetch GTEx -> fetch CellxGene -> merge -> compute Tau -> compute score -> collect

    Args:
        gene_ids: List of Ensembl gene IDs to process
        cache_dir: Directory for caching downloads
        force: If True, re-download even if cached
        skip_cellxgene: If True, skip CellxGene fetching (optional dependency)
        census_version: Named CELLxGENE Census release/build date.
        cache_only: If True, use only existing HPA, GTEx, and CellxGene caches.
        cellxgene_metadata: Optional dictionary populated with CellxGene status.

    Returns:
        Materialized DataFrame with expression evidence ready for DuckDB storage
    """
    logger.info("expression_pipeline_start", gene_count=len(gene_ids))

    if cache_only and force:
        raise ValueError("cache_only expression processing cannot use force=True")

    cache_dir = Path(cache_dir) if cache_dir else Path("data/expression")

    # Fetch HPA expression (lazy)
    logger.info("fetching_hpa")
    lf_hpa = fetch_hpa_expression(
        gene_ids, cache_dir=cache_dir, force=force, cache_only=cache_only
    )

    # Fetch GTEx expression (lazy)
    logger.info("fetching_gtex")
    lf_gtex = fetch_gtex_expression(
        gene_ids, cache_dir=cache_dir, force=force, cache_only=cache_only
    )

    # Create gene universe DataFrame
    gene_universe = pl.LazyFrame({"gene_id": gene_ids})
    if gene_symbol_map is not None:
        gene_universe = gene_universe.join(
            gene_symbol_map.select(["gene_id", "gene_symbol"])
            .unique(subset=["gene_id"])
            .lazy(),
            on="gene_id",
            how="left",
        )
    else:
        gene_universe = gene_universe.with_columns(
            pl.lit(None).cast(pl.Utf8).alias("gene_symbol")
        )

    # Merge GTEx with gene universe (left join to preserve all genes)
    lf_merged = gene_universe.join(lf_gtex, on="gene_id", how="left")

    # Merge HPA data via gene_symbol mapping
    # HPA returns gene_symbol as key; we need gene_symbol_map to bridge to gene_id
    if gene_symbol_map is not None:
        logger.info("merging_hpa_via_symbol_map")
        # lf_hpa has explicit HPA nTPM or ordinal protein-level columns.
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
        lf_cellxgene = fetch_cellxgene_expression(
            gene_ids,
            cache_dir=cache_dir,
            force=force,
            cache_only=cache_only,
            census_version=census_version,
            metadata=cellxgene_metadata,
        )
        lf_merged = lf_merged.join(lf_cellxgene, on="gene_id", how="left")
    elif cellxgene_metadata is not None:
        cellxgene_metadata.update(
            {
                "status": "skipped",
                "error": None,
                "reason": "skip_cellxgene=True",
                "census_version": census_version,
            }
        )

    # Collect at this point to enable horizontal operations
    df = lf_merged.collect()

    # Calculate Tau independently within quantitative bulk sources.  HPA
    # categorical protein levels are ordinal and therefore excluded from Tau;
    # HPA nTPM is included when that quantitative source is available.
    tau_columns = []
    for source_name, source_cols in {
        "hpa": list(HPA_NTPM_COLUMNS),
        "gtex": list(GTEX_TPM_COLUMNS),
    }.items():
        available = [col for col in source_cols if col in df.columns]
        if len(available) >= 2:
            df = calculate_tau_specificity(df, available).rename({
                RESTRICTED_TAU_COLUMN: f"_tau_{source_name}"
            })
            tau_columns.append(f"_tau_{source_name}")

    if tau_columns:
        df = df.with_columns(
            pl.mean_horizontal([pl.col(col) for col in tau_columns]).alias(
                RESTRICTED_TAU_COLUMN
            )
        ).drop(tau_columns)
    else:
        df = df.with_columns(
            pl.lit(None).cast(pl.Float64).alias(RESTRICTED_TAU_COLUMN)
        )

    # Compute expression score
    df = compute_expression_score(df)

    # Source-specific enrichment terms are implementation details of the
    # composite score; keep the persisted schema focused on documented fields.
    internal_score_columns = [
        column for column in df.columns if column.startswith("_")
    ]
    if internal_score_columns:
        df = df.drop(internal_score_columns)

    # Do not carry the pre-remediation HPA columns into a new checkpoint.  A
    # legacy checkpoint must be reprocessed from the cached raw source.
    legacy_columns = [column for column in LEGACY_HPA_TPM_COLUMNS if column in df.columns]
    if legacy_columns:
        df = df.drop(legacy_columns)

    # Ensure all expected columns exist (NULL if source unavailable)
    expected_cols = {
        **{column: pl.Int8 for column in HPA_PROTEIN_LEVEL_COLUMNS},
        **{column: pl.Utf8 for column in HPA_PROTEIN_LEVEL_LABEL_COLUMNS},
        **{column: pl.Float64 for column in HPA_NTPM_COLUMNS},
        **{column: pl.Float64 for column in GTEX_TPM_COLUMNS},
        "cellxgene_photoreceptor_expr": pl.Float64,
        "cellxgene_hair_cell_expr": pl.Float64,
        RESTRICTED_TAU_COLUMN: pl.Float64,
        RESTRICTED_ENRICHMENT_COLUMN: pl.Float64,
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

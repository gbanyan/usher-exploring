"""Transform and normalize gnomAD constraint metrics."""

from pathlib import Path

import polars as pl
import structlog

from usher_pipeline.evidence.gnomad.fetch import parse_constraint_tsv

logger = structlog.get_logger()


def filter_by_coverage(
    lf: pl.LazyFrame,
    min_depth: float = 30.0,
    min_cds_pct: float = 0.9,
) -> pl.LazyFrame:
    """Add quality_flag column based on coverage thresholds.

    Does NOT drop any genes - preserves all rows with quality categorization.
    "Unknown" constraint is semantically different from "zero" constraint.

    Args:
        lf: LazyFrame with gnomAD constraint data
        min_depth: Minimum mean sequencing depth (default: 30x)
        min_cds_pct: Minimum CDS coverage fraction (default: 0.9 = 90%)

    Returns:
        LazyFrame with quality_flag column added:
        - "measured": Has LOEUF estimate (and good coverage if available)
        - "incomplete_coverage": Coverage below thresholds
        - "no_data": Both LOEUF and pLI are NULL
    """
    # Check which columns are available (gnomAD v4.1 lacks coverage columns)
    available_cols = lf.collect_schema().names()
    has_coverage = "mean_depth" in available_cols and "cds_covered_pct" in available_cols

    # Ensure numeric columns are properly cast
    cast_exprs = [
        pl.col("loeuf").cast(pl.Float64, strict=False),
        pl.col("pli").cast(pl.Float64, strict=False),
    ]
    if has_coverage:
        cast_exprs.extend([
            pl.col("mean_depth").cast(pl.Float64, strict=False),
            pl.col("cds_covered_pct").cast(pl.Float64, strict=False),
        ])
    lf = lf.with_columns(cast_exprs)

    if has_coverage:
        return lf.with_columns(
            pl.when(
                pl.col("mean_depth").is_not_null()
                & pl.col("cds_covered_pct").is_not_null()
                & (pl.col("mean_depth") >= min_depth)
                & (pl.col("cds_covered_pct") >= min_cds_pct)
                & pl.col("loeuf").is_not_null()
            )
            .then(pl.lit("measured"))
            .when(pl.col("loeuf").is_null() & pl.col("pli").is_null())
            .then(pl.lit("no_data"))
            .when(
                pl.col("mean_depth").is_not_null()
                & pl.col("cds_covered_pct").is_not_null()
                & ((pl.col("mean_depth") < min_depth) | (pl.col("cds_covered_pct") < min_cds_pct))
            )
            .then(pl.lit("incomplete_coverage"))
            .otherwise(pl.lit("incomplete_coverage"))
            .alias("quality_flag")
        )
    else:
        # No coverage columns (gnomAD v4.1) — classify by presence of constraint data
        logger.info("gnomad_no_coverage_columns", msg="Using constraint-only quality flags")
        return lf.with_columns(
            pl.when(pl.col("loeuf").is_not_null())
            .then(pl.lit("measured"))
            .when(pl.col("loeuf").is_null() & pl.col("pli").is_null())
            .then(pl.lit("no_data"))
            .otherwise(pl.lit("incomplete_coverage"))
            .alias("quality_flag")
        )


def normalize_scores(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Normalize LOEUF scores to 0-1 range with inversion.

    Lower LOEUF = more constrained = HIGHER normalized score.
    Only genes with quality_flag="measured" get normalized scores.
    Others get NULL (not 0.0 - "unknown" != "zero constraint").

    Args:
        lf: LazyFrame with gnomAD constraint data and quality_flag column

    Returns:
        LazyFrame with loeuf_normalized column added
    """
    # Compute min/max from measured genes only
    measured = lf.filter(pl.col("quality_flag") == "measured")

    # Aggregate min/max in a single pass
    stats = measured.select(
        pl.col("loeuf").min().alias("loeuf_min"),
        pl.col("loeuf").max().alias("loeuf_max"),
    ).collect()

    if len(stats) == 0:
        # No measured genes - all get NULL
        return lf.with_columns(pl.lit(None).cast(pl.Float64).alias("loeuf_normalized"))

    loeuf_min = stats["loeuf_min"][0]
    loeuf_max = stats["loeuf_max"][0]

    if loeuf_min is None or loeuf_max is None or loeuf_min == loeuf_max:
        # Handle edge case: all measured genes have same LOEUF
        return lf.with_columns(pl.lit(None).cast(pl.Float64).alias("loeuf_normalized"))

    # Invert: lower LOEUF -> higher score
    # Formula: (max - value) / (max - min)
    return lf.with_columns(
        pl.when(pl.col("quality_flag") == "measured")
        .then((loeuf_max - pl.col("loeuf")) / (loeuf_max - loeuf_min))
        .otherwise(pl.lit(None))
        .alias("loeuf_normalized")
    )


def process_gnomad_constraint(
    tsv_path: Path,
    min_depth: float = 30.0,
    min_cds_pct: float = 0.9,
) -> pl.DataFrame:
    """Full gnomAD constraint processing pipeline.

    Composes: parse -> filter_by_coverage -> normalize_scores -> collect

    Args:
        tsv_path: Path to gnomAD constraint TSV file
        min_depth: Minimum mean sequencing depth (default: 30x)
        min_cds_pct: Minimum CDS coverage fraction (default: 0.9)

    Returns:
        Materialized DataFrame ready for DuckDB storage
    """
    logger.info("gnomad_process_start", tsv_path=str(tsv_path))

    # Parse with lazy evaluation
    lf = parse_constraint_tsv(tsv_path)

    # Filter and normalize
    lf = filter_by_coverage(lf, min_depth=min_depth, min_cds_pct=min_cds_pct)
    lf = normalize_scores(lf)

    # Materialize
    df = lf.collect()

    # Log summary statistics
    stats = df.group_by("quality_flag").len().sort("quality_flag")
    total = len(df)

    logger.info(
        "gnomad_process_complete",
        total_genes=total,
        measured=df.filter(pl.col("quality_flag") == "measured").height,
        incomplete_coverage=df.filter(
            pl.col("quality_flag") == "incomplete_coverage"
        ).height,
        no_data=df.filter(pl.col("quality_flag") == "no_data").height,
    )

    return df

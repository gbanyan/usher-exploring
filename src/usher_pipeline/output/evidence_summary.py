"""Per-gene evidence summary: supporting layers and gaps."""

import polars as pl

# Six evidence layer names (must match column names in scored_genes)
EVIDENCE_LAYERS = [
    "gnomad",
    "expression",
    "annotation",
    "localization",
    "animal_model",
    "literature",
]


def add_evidence_summary(df: pl.DataFrame) -> pl.DataFrame:
    """
    Add supporting_layers and evidence_gaps columns to scored genes.

    For each gene, identifies which evidence layers contributed scores
    (supporting_layers) and which layers are missing (evidence_gaps).

    Args:
        df: Polars DataFrame with columns like:
            - gene_id, gene_symbol, composite_score, evidence_count
            - gnomad_score, expression_score, annotation_score, etc. (all nullable)

    Returns:
        DataFrame with two added columns:
            - supporting_layers (str): comma-separated list of layers with non-NULL scores
            - evidence_gaps (str): comma-separated list of layers with NULL scores

    Examples:
        - Gene with gnomad, expression, annotation scores:
          supporting_layers = "gnomad,expression,annotation"
          evidence_gaps = "localization,animal_model,literature"
        - Gene with all NULL scores:
          supporting_layers = ""
          evidence_gaps = "gnomad,expression,annotation,localization,animal_model,literature"

    Notes:
        - Uses polars expressions (no pandas conversion)
        - Empty string for supporting_layers if no evidence
        - Preserves DataFrame order and all other columns
    """
    # Build supporting_layers: comma-separated list of non-NULL layers
    # Strategy: create a list column, filter nulls, join to string
    supporting_exprs = []
    gap_exprs = []

    for layer in EVIDENCE_LAYERS:
        score_col = f"{layer}_score"

        # For supporting_layers: keep layer name if score is NOT NULL, else NULL
        supporting_exprs.append(
            pl.when(pl.col(score_col).is_not_null())
            .then(pl.lit(layer))
            .otherwise(pl.lit(None))
        )

        # For evidence_gaps: keep layer name if score IS NULL, else NULL
        gap_exprs.append(
            pl.when(pl.col(score_col).is_null())
            .then(pl.lit(layer))
            .otherwise(pl.lit(None))
        )

    # Combine into list columns, drop nulls, join with comma
    result = df.with_columns(
        # supporting_layers: join all non-NULL layer names
        pl.concat_list(supporting_exprs)
        .list.drop_nulls()
        .list.join(",")
        .alias("supporting_layers"),
        # evidence_gaps: join all NULL layer names
        pl.concat_list(gap_exprs)
        .list.drop_nulls()
        .list.join(",")
        .alias("evidence_gaps"),
    )

    return result

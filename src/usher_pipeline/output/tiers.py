"""Confidence tiering logic for scored candidate genes."""

import polars as pl

from usher_pipeline.evidence.localization.models import (
    LOCALIZATION_GATE_SOURCE_COLUMNS,
)

HAS_CILIA_SIGNAL_SEMANTICS_VERSION = (
    "v2: positive aggregate localization or positive animal-model signal"
)

# Default tier thresholds from research
TIER_THRESHOLDS = {
    "HIGH": {"composite_score": 0.7, "evidence_count": 3},
    "MEDIUM": {"composite_score": 0.4, "evidence_count": 2},
    "LOW": {"composite_score": 0.2, "evidence_count": 1},
}


def assign_tiers(
    scored_df: pl.DataFrame, thresholds: dict | None = None
) -> pl.DataFrame:
    """
    Assign confidence tiers to scored genes and filter out EXCLUDED genes.

    Uses configurable thresholds to classify genes into HIGH/MEDIUM/LOW tiers
    based on composite_score and evidence_count. Genes below LOW threshold
    are marked as EXCLUDED and filtered out.

    Args:
        scored_df: Polars DataFrame with columns:
            - gene_id (str)
            - gene_symbol (str)
            - composite_score (float, nullable)
            - evidence_count (int)
            - quality_flag (str)
            - All 6 layer score columns (nullable)
            - All 6 contribution columns (nullable)
        thresholds: Optional dict overriding TIER_THRESHOLDS. Expected format:
            {
                "HIGH": {"composite_score": float, "evidence_count": int},
                "MEDIUM": {"composite_score": float, "evidence_count": int},
                "LOW": {"composite_score": float, "evidence_count": int},
            }

    Returns:
        DataFrame with added confidence_tier column (str), sorted by
        composite_score DESC, gene_id ASC. EXCLUDED genes are filtered out.

    Notes:
        - Uses vectorized polars expressions (not row-by-row iteration)
        - Genes with NULL composite_score are always EXCLUDED
        - Deterministic sorting for reproducibility
        - Filtering happens before return (EXCLUDED rows removed)
    """
    # Use provided thresholds or defaults
    t = thresholds if thresholds is not None else TIER_THRESHOLDS

    # Extract threshold values for readability
    high_score = t["HIGH"]["composite_score"]
    high_count = t["HIGH"]["evidence_count"]
    med_score = t["MEDIUM"]["composite_score"]
    med_count = t["MEDIUM"]["evidence_count"]
    low_score = t["LOW"]["composite_score"]

    # Keep source-level direct evidence separate from the aggregate
    # localization score. A positive score can represent only adjacent
    # cytoskeleton/microtubule localization and is not sufficient for HIGH.
    missing_source_columns = [
        column
        for column in LOCALIZATION_GATE_SOURCE_COLUMNS
        if column not in scored_df.columns
    ]
    if missing_source_columns:
        raise ValueError(
            "scored_genes checkpoint lacks source-level localization fields: "
            f"{', '.join(missing_source_columns)}. Re-run localization evidence "
            "processing and composite scoring before generating tiers."
        )

    has_direct_cilia_signal = pl.lit(False)
    for column in LOCALIZATION_GATE_SOURCE_COLUMNS:
        has_direct_cilia_signal = has_direct_cilia_signal | pl.col(column).fill_null(False)

    # ``has_cilia_signal`` is a broad, versioned reporting field retained for
    # compatibility. It includes positive aggregate localization and animal
    # model signal; direct source evidence is reported separately below.
    localization_positive = (
        (pl.col("localization_score") > 0.0).fill_null(False)
        if "localization_score" in scored_df.columns
        else pl.lit(False)
    )
    animal_positive = (
        (pl.col("animal_model_score") > 0.0).fill_null(False)
        if "animal_model_score" in scored_df.columns
        else pl.lit(False)
    )
    has_cilia_signal = localization_positive | animal_positive

    scored_df = scored_df.with_columns(
        has_direct_cilia_signal.alias("has_direct_localization_signal"),
        has_cilia_signal.alias("has_cilia_signal"),
        pl.lit(HAS_CILIA_SIGNAL_SEMANTICS_VERSION).alias(
            "has_cilia_signal_semantics_version"
        ),
    )

    # Cilia-signal gate on the HIGH tier. A HIGH-priority hypothesis must show
    # explicit direct cilia/centrosome/basal-body/transition-zone/stereocilia
    # localization or membership in one of the embedded curated ciliary/centrosomal
    # compendia. The separately named sensory animal-model Q75 route is retained as
    # an independent way through the gate. Genes meeting the score/evidence
    # thresholds but failing both routes fall through to MEDIUM.
    if "animal_model_score" in scored_df.columns:
        animal_pos = scored_df.filter(
            pl.col("animal_model_score").is_not_null()
            & (pl.col("animal_model_score") > 0.0)
        )["animal_model_score"]
        if len(animal_pos):
            animal_q75 = float(animal_pos.quantile(0.75))
            sensory_animal_model_q75 = (
                pl.col("animal_model_score").is_not_null()
                & (pl.col("animal_model_score") > 0.0)
                & (pl.col("animal_model_score") >= animal_q75)
            )
        else:
            sensory_animal_model_q75 = pl.lit(False)
    else:
        sensory_animal_model_q75 = pl.lit(False)

    high_cilia_gate = (
        pl.col("has_direct_localization_signal") | sensory_animal_model_q75
    )

    # Add confidence_tier column using vectorized when/then/otherwise chain
    result = scored_df.with_columns(
        pl.when(
            (pl.col("composite_score") >= high_score)
            & (pl.col("evidence_count") >= high_count)
            & high_cilia_gate
        )
        .then(pl.lit("HIGH"))
        .when(
            (pl.col("composite_score") >= med_score)
            & (pl.col("evidence_count") >= med_count)
        )
        .then(pl.lit("MEDIUM"))
        .when(pl.col("composite_score") >= low_score)
        .then(pl.lit("LOW"))
        .otherwise(pl.lit("EXCLUDED"))
        .alias("confidence_tier")
    )

    # Filter out EXCLUDED genes
    result = result.filter(pl.col("confidence_tier") != "EXCLUDED")

    # Sort deterministically: composite_score DESC, gene_id ASC
    result = result.sort(["composite_score", "gene_id"], descending=[True, False])

    return result

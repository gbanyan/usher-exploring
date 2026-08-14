"""Transform localization data: classify evidence type and score cilia proximity."""

import polars as pl
import structlog

from usher_pipeline.evidence.localization.models import (
    CILIA_COMPARTMENTS,
    CILIA_ADJACENT_COMPARTMENTS,
    CURATED_COMPENDIUM_COLUMNS,
    CURATED_COMPENDIUM_EVIDENCE_WEIGHT,
    CURATED_COMPENDIUM_FALLBACK_SCORE,
    HPA_EVIDENCE_MODALITY,
    HPA_RELIABILITY_WEIGHTS,
    LEGACY_CURATED_PROTEOMICS_COLUMNS,
    LOCALIZATION_CHECKPOINT_SCHEMA_VERSION,
    LOCALIZATION_CHECKPOINT_VERSION_COLUMN,
)
from usher_pipeline.evidence.localization.fetch import (
    fetch_hpa_subcellular,
    fetch_cilia_compendium,
)

logger = structlog.get_logger()


def _hpa_reliability_weight_expr() -> pl.Expr:
    """Return the explicit weight for each HPA antibody-staining reliability."""
    weight_expr = pl.lit(None, dtype=pl.Float64)
    for reliability, weight in HPA_RELIABILITY_WEIGHTS.items():
        weight_expr = pl.when(
            pl.col("hpa_reliability") == reliability
        ).then(pl.lit(weight)).otherwise(weight_expr)
    return weight_expr


def _normalize_compendium_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Normalize known legacy names before in-memory localization processing."""
    for legacy, current in zip(
        LEGACY_CURATED_PROTEOMICS_COLUMNS, CURATED_COMPENDIUM_COLUMNS
    ):
        if current not in df.columns and legacy in df.columns:
            df = df.rename({legacy: current})
    missing = [column for column in CURATED_COMPENDIUM_COLUMNS if column not in df.columns]
    if missing:
        df = df.with_columns([
            pl.lit(False).cast(pl.Boolean).alias(column) for column in missing
        ])
    return df


def _compendium_evidence_expr() -> pl.Expr:
    return (
        (pl.col(CURATED_COMPENDIUM_COLUMNS[0]) == True)
        | (pl.col(CURATED_COMPENDIUM_COLUMNS[1]) == True)
    )


def classify_evidence_type(df: pl.DataFrame) -> pl.DataFrame:
    """Classify localization evidence by its measurement modality.

    HPA reliability levels:
    - Enhanced/Supported: antibody staining with stronger validation
    - Approved/Uncertain: antibody-staining reliability categories with less
      validation; they are not computational predictions

    Embedded compendium membership is curated evidence, not experimental/MS
    evidence. HPA staining remains experimental antibody evidence.

    Evidence type categories:
    - "experimental": HPA antibody staining only
    - "curated_compendium": embedded compendium membership only
    - "mixed": HPA staining and compendium membership
    - "none": no localization data available

    Args:
        df: DataFrame with hpa_reliability and curated compendium flags

    Returns:
        DataFrame with added columns:
        - hpa_evidence_modality: "antibody_staining" (NULL if no HPA data)
        - hpa_evidence_type: legacy "experimental" HPA modality label
        - hpa_reliability_weight: explicit validation-strength weight
        - evidence_type: experimental, curated_compendium, mixed, or none
    """
    logger.info("classify_evidence_start", row_count=len(df))

    df = _normalize_compendium_columns(df)

    # All recognized HPA reliability values describe antibody-staining
    # reliability. Approved and Uncertain are not prediction classes.
    recognized_hpa = pl.col("hpa_reliability").is_in(
        list(HPA_RELIABILITY_WEIGHTS)
    )
    df = df.with_columns([
        pl.when(recognized_hpa)
        .then(pl.lit(HPA_EVIDENCE_MODALITY))
        .otherwise(pl.lit(None, dtype=pl.Utf8))
        .alias("hpa_evidence_modality"),
        pl.when(recognized_hpa)
        .then(pl.lit("experimental"))
        .otherwise(pl.lit(None, dtype=pl.Utf8))
        .alias("hpa_evidence_type"),
        _hpa_reliability_weight_expr().alias("hpa_reliability_weight"),
    ])

    has_hpa = pl.col("hpa_evidence_modality").is_not_null()
    has_compendium = _compendium_evidence_expr()

    # Keep HPA experimental modality distinct from curated compendium
    # membership; the latter has no local assay-table attribution.
    df = df.with_columns([
        pl.when(
            has_hpa & has_compendium
        )
        .then(pl.lit("mixed"))
        .when(has_hpa)
        .then(pl.lit("experimental"))
        .when(has_compendium)
        .then(pl.lit("curated_compendium"))
        .otherwise(pl.lit("none"))
        .alias("evidence_type"),
        pl.lit(LOCALIZATION_CHECKPOINT_SCHEMA_VERSION)
        .cast(pl.Int32)
        .alias(LOCALIZATION_CHECKPOINT_VERSION_COLUMN),
    ])

    logger.info(
        "classify_evidence_complete",
        experimental=df.filter(pl.col("evidence_type") == "experimental").height,
        curated_compendium=df.filter(pl.col("evidence_type") == "curated_compendium").height,
        mixed=df.filter(pl.col("evidence_type") == "mixed").height,
        computational=0,
        both=0,
        none=df.filter(pl.col("evidence_type") == "none").height,
    )

    return df


def score_localization(df: pl.DataFrame) -> pl.DataFrame:
    """Score cilia proximity based on compartment localization.

    Scoring logic:
    1. Parse HPA location string to identify compartments
    2. Set compartment boolean flags
    3. Calculate base cilia_proximity_score:
       - 1.0: Direct cilia compartment (Cilia, Centrosome, Basal body, etc.)
       - 0.5: Adjacent compartment (Cytoskeleton, Microtubules, etc.)
       - 0.3: In curated compendium after direct/adjacent checks
       - 0.0: No cilia-related evidence
       - NULL: No localization data at all
    4. Apply explicit evidence weights:
       - Enhanced/Supported HPA staining: 1.0x
       - Approved/Uncertain HPA staining: 0.6x
       - curated compendium: 0.5x
       - none: NULL
    5. Calculate localization_score_normalized: cilia_proximity_score * evidence_weight

    Args:
        df: DataFrame with hpa_main_location, curated compendium flags,
            evidence_type

    Returns:
        DataFrame with added columns:
        - compartment_cilia, compartment_centrosome, etc.: boolean flags
        - cilia_proximity_score: 0-1 score (NULL if no data)
        - localization_score_normalized: weighted score (NULL if no data)
    """
    logger.info("score_localization_start", row_count=len(df))

    df = _normalize_compendium_columns(df)

    # Keep direct callers and legacy in-memory frames safe while ensuring the
    # score itself uses reliability, not the HPA modality label.
    if "hpa_reliability" not in df.columns:
        df = df.with_columns(pl.lit(None, dtype=pl.Utf8).alias("hpa_reliability"))
    if "hpa_reliability_weight" not in df.columns:
        df = df.with_columns(
            _hpa_reliability_weight_expr().alias("hpa_reliability_weight")
        )

    # Parse compartment flags from HPA location string
    # Check if any CILIA_COMPARTMENTS substring appears in hpa_main_location
    df = df.with_columns([
        # Cilia/Cilium
        pl.when(
            pl.col("hpa_main_location").is_not_null()
        ).then(
            pl.col("hpa_main_location").str.to_lowercase().str.contains("cili")
        ).otherwise(None).alias("compartment_cilia"),

        # Centrosome
        pl.when(
            pl.col("hpa_main_location").is_not_null()
        ).then(
            pl.col("hpa_main_location").str.to_lowercase().str.contains("centrosome|centriole")
        ).otherwise(None).alias("compartment_centrosome"),

        # Basal body
        pl.when(
            pl.col("hpa_main_location").is_not_null()
        ).then(
            pl.col("hpa_main_location").str.to_lowercase().str.contains("basal body")
        ).otherwise(None).alias("compartment_basal_body"),

        # Transition zone (rare in HPA, but check)
        pl.when(
            pl.col("hpa_main_location").is_not_null()
        ).then(
            pl.col("hpa_main_location").str.to_lowercase().str.contains("transition zone")
        ).otherwise(None).alias("compartment_transition_zone"),

        # Stereocilia (hearing-related cilia)
        pl.when(
            pl.col("hpa_main_location").is_not_null()
        ).then(
            pl.col("hpa_main_location").str.to_lowercase().str.contains("stereocili")
        ).otherwise(None).alias("compartment_stereocilia"),
    ])

    # Check for adjacent compartments (cytoskeleton, microtubules)
    df = df.with_columns([
        pl.when(
            pl.col("hpa_main_location").is_not_null()
        ).then(
            pl.col("hpa_main_location").str.to_lowercase().str.contains(
                "cytoskeleton|microtubule|cell junction|focal adhesion"
            )
        ).otherwise(None).alias("has_adjacent_compartment")
    ])

    # Calculate base cilia proximity score
    df = df.with_columns([
        pl.when(
            # Direct cilia compartment
            (pl.col("compartment_cilia") == True)
            | (pl.col("compartment_centrosome") == True)
            | (pl.col("compartment_basal_body") == True)
            | (pl.col("compartment_transition_zone") == True)
            | (pl.col("compartment_stereocilia") == True)
        ).then(
            pl.lit(1.0)  # Direct match
        ).when(
            # Adjacent compartment only
            pl.col("has_adjacent_compartment") == True
        ).then(
            pl.lit(0.5)  # Adjacent
        ).when(
            # Curated compendium membership is a documented fallback after
            # direct and adjacent HPA checks, including HPA non-ciliary rows.
            _compendium_evidence_expr()
        ).then(
            pl.lit(CURATED_COMPENDIUM_FALLBACK_SCORE)
        ).when(
            # Has HPA or compendium data but no cilia evidence
            pl.col("hpa_main_location").is_not_null()
            | _compendium_evidence_expr()
        ).then(
            pl.lit(0.0)  # No cilia proximity
        ).otherwise(
            None  # No data at all
        ).alias("cilia_proximity_score")
    ])

    # Modality and reliability are separate: all recognized HPA rows are
    # antibody staining, but Approved/Uncertain receive the lower reliability
    # weight. Curated compendium membership supplies an independent lower
    # weight signal.
    compendium_evidence = _compendium_evidence_expr()
    effective_weight = (
        pl.when(pl.col("hpa_reliability_weight").is_not_null())
        .then(pl.col("hpa_reliability_weight"))
        .when(compendium_evidence)
        .then(pl.lit(CURATED_COMPENDIUM_EVIDENCE_WEIGHT))
        .otherwise(pl.lit(None, dtype=pl.Float64))
    )
    df = df.with_columns([
        pl.when(
            pl.col("evidence_type") == "none"
        ).then(
            pl.lit(None, dtype=pl.Float64)  # No evidence -> NULL score
        ).otherwise(
            (pl.col("cilia_proximity_score").cast(pl.Float64) * effective_weight)
        ).alias("localization_score_normalized")
    ])

    # Drop temporary column
    df = df.drop("has_adjacent_compartment")

    logger.info(
        "score_localization_complete",
        direct_cilia=df.filter((pl.col("compartment_cilia") == True) | (pl.col("compartment_centrosome") == True)).height,
        mean_proximity=df["cilia_proximity_score"].mean(),
        mean_normalized=df["localization_score_normalized"].mean(),
    )

    return df


def process_localization_evidence(
    gene_ids: list[str],
    gene_symbol_map: pl.DataFrame,
    cache_dir=None,
    force: bool = False,
    cache_only: bool = False,
) -> pl.DataFrame:
    """End-to-end localization evidence processing pipeline.

    Fetches HPA subcellular data and curated-compendium cross-references,
    merges them, classifies evidence type, and scores cilia proximity.

    Args:
        gene_ids: List of Ensembl gene IDs
        gene_symbol_map: DataFrame with gene_id and gene_symbol columns
        cache_dir: Directory to cache HPA download
        force: If True, re-download HPA data
        cache_only: If True, require the local HPA source and never download

    Returns:
        DataFrame with all LocalizationRecord fields
    """
    logger.info("process_localization_start", gene_count=len(gene_ids))

    # Fetch HPA subcellular data
    hpa_df = fetch_hpa_subcellular(
        gene_ids=gene_ids,
        gene_symbol_map=gene_symbol_map,
        cache_dir=cache_dir,
        force=force,
        cache_only=cache_only,
    )

    # Fetch curated-compendium cross-references
    compendium_df = fetch_cilia_compendium(
        gene_ids=gene_ids,
        gene_symbol_map=gene_symbol_map,
    )

    # Merge HPA and curated-compendium data
    # Use full outer join to preserve genes in either dataset
    df = gene_symbol_map.filter(pl.col("gene_id").is_in(gene_ids))
    df = df.select(["gene_id", "gene_symbol"])

    # Left join HPA data
    df = df.join(
        hpa_df.select(["gene_id", "hpa_main_location", "hpa_reliability"]),
        on="gene_id",
        how="left",
    )

    # Left join curated-compendium data
    df = df.join(
        compendium_df.select(["gene_id", *CURATED_COMPENDIUM_COLUMNS]),
        on="gene_id",
        how="left",
    )

    # Fill NULL compendium flags with False (absence is informative)
    df = df.with_columns([
        pl.col(CURATED_COMPENDIUM_COLUMNS[0]).fill_null(False),
        pl.col(CURATED_COMPENDIUM_COLUMNS[1]).fill_null(False),
    ])

    logger.info(
        "process_merge_complete",
        row_count=len(df),
        has_hpa=df.filter(pl.col("hpa_main_location").is_not_null()).height,
        has_compendium=df.filter(_compendium_evidence_expr()).height,
    )

    # Classify evidence type
    df = classify_evidence_type(df)

    # Score localization
    df = score_localization(df)

    logger.info("process_localization_complete", row_count=len(df))

    return df

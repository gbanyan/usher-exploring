"""Transform localization data: classify evidence type and score cilia proximity."""

import polars as pl
import structlog

from usher_pipeline.evidence.localization.models import (
    CILIA_COMPARTMENTS,
    CILIA_ADJACENT_COMPARTMENTS,
)
from usher_pipeline.evidence.localization.fetch import (
    fetch_hpa_subcellular,
    fetch_cilia_proteomics,
)

logger = structlog.get_logger()


def classify_evidence_type(df: pl.DataFrame) -> pl.DataFrame:
    """Classify localization evidence as experimental vs computational.

    HPA reliability levels:
    - Enhanced/Supported: experimental (antibody-based IHC with validation)
    - Approved/Uncertain: computational (predicted from RNA-seq or unvalidated)

    Proteomics datasets are always experimental (MS-based detection).

    Evidence type categories:
    - "experimental": high-confidence experimental evidence only
    - "computational": predicted/uncertain only
    - "both": both experimental and computational evidence
    - "none": no localization data available

    Args:
        df: DataFrame with hpa_reliability, in_cilia_proteomics, in_centrosome_proteomics

    Returns:
        DataFrame with added columns:
        - hpa_evidence_type: "experimental" or "computational" (NULL if no HPA data)
        - evidence_type: "experimental", "computational", "both", "none"
    """
    logger.info("classify_evidence_start", row_count=len(df))

    # Classify HPA evidence type based on reliability
    df = df.with_columns([
        pl.when(pl.col("hpa_reliability").is_in(["Enhanced", "Supported"]))
        .then(pl.lit("experimental"))
        .when(pl.col("hpa_reliability").is_in(["Approved", "Uncertain"]))
        .then(pl.lit("computational"))
        .otherwise(None)
        .alias("hpa_evidence_type")
    ])

    # Determine overall evidence type
    # Proteomics presence overrides computational HPA classification
    df = df.with_columns([
        pl.when(
            # Has proteomics evidence
            (pl.col("in_cilia_proteomics") == True) | (pl.col("in_centrosome_proteomics") == True)
        ).then(
            # Proteomics is experimental
            pl.when(pl.col("hpa_evidence_type") == "experimental")
            .then(pl.lit("experimental"))  # Both proteomics and HPA experimental
            .when(pl.col("hpa_evidence_type") == "computational")
            .then(pl.lit("both"))  # Proteomics experimental, HPA computational
            .when(pl.col("hpa_evidence_type").is_null())
            .then(pl.lit("experimental"))  # Only proteomics
            .otherwise(pl.lit("experimental"))
        ).when(
            # No proteomics, but has HPA
            pl.col("hpa_evidence_type").is_not_null()
        ).then(
            pl.col("hpa_evidence_type")  # Use HPA classification
        ).otherwise(
            # No proteomics, no HPA
            pl.lit("none")
        ).alias("evidence_type")
    ])

    logger.info(
        "classify_evidence_complete",
        experimental=df.filter(pl.col("evidence_type") == "experimental").height,
        computational=df.filter(pl.col("evidence_type") == "computational").height,
        both=df.filter(pl.col("evidence_type") == "both").height,
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
       - 0.3: In proteomics but no HPA cilia location
       - 0.0: No cilia-related evidence
       - NULL: No localization data at all
    4. Apply evidence weight:
       - experimental: 1.0x
       - computational: 0.6x
       - both: 1.0x (experimental evidence present)
       - none: NULL
    5. Calculate localization_score_normalized: cilia_proximity_score * evidence_weight

    Args:
        df: DataFrame with hpa_main_location, in_cilia_proteomics,
            in_centrosome_proteomics, evidence_type

    Returns:
        DataFrame with added columns:
        - compartment_cilia, compartment_centrosome, etc.: boolean flags
        - cilia_proximity_score: 0-1 score (NULL if no data)
        - localization_score_normalized: weighted score (NULL if no data)
    """
    logger.info("score_localization_start", row_count=len(df))

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
            # In proteomics but no HPA cilia location
            ((pl.col("in_cilia_proteomics") == True) | (pl.col("in_centrosome_proteomics") == True))
            & (pl.col("hpa_main_location").is_null() | (pl.col("compartment_cilia").is_null()))
        ).then(
            pl.lit(0.3)  # Proteomics evidence without HPA confirmation
        ).when(
            # Has HPA or proteomics data but no cilia evidence
            pl.col("hpa_main_location").is_not_null()
            | (pl.col("in_cilia_proteomics") == True)
            | (pl.col("in_centrosome_proteomics") == True)
        ).then(
            pl.lit(0.0)  # No cilia proximity
        ).otherwise(
            None  # No data at all
        ).alias("cilia_proximity_score")
    ])

    # Apply evidence type weighting
    df = df.with_columns([
        pl.when(
            pl.col("evidence_type") == "none"
        ).then(
            None  # No evidence -> NULL score
        ).when(
            pl.col("evidence_type") == "computational"
        ).then(
            (pl.col("cilia_proximity_score") * 0.6).cast(pl.Float64)  # Downweight computational
        ).when(
            (pl.col("evidence_type") == "experimental") | (pl.col("evidence_type") == "both")
        ).then(
            (pl.col("cilia_proximity_score") * 1.0).cast(pl.Float64)  # Full weight for experimental
        ).otherwise(
            pl.col("cilia_proximity_score")
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
) -> pl.DataFrame:
    """End-to-end localization evidence processing pipeline.

    Fetches HPA subcellular data and proteomics cross-references,
    merges them, classifies evidence type, and scores cilia proximity.

    Args:
        gene_ids: List of Ensembl gene IDs
        gene_symbol_map: DataFrame with gene_id and gene_symbol columns
        cache_dir: Directory to cache HPA download
        force: If True, re-download HPA data

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
    )

    # Fetch proteomics cross-references
    proteomics_df = fetch_cilia_proteomics(
        gene_ids=gene_ids,
        gene_symbol_map=gene_symbol_map,
    )

    # Merge HPA and proteomics data
    # Use full outer join to preserve genes in either dataset
    df = gene_symbol_map.filter(pl.col("gene_id").is_in(gene_ids))
    df = df.select(["gene_id", "gene_symbol"])

    # Left join HPA data
    df = df.join(
        hpa_df.select(["gene_id", "hpa_main_location", "hpa_reliability"]),
        on="gene_id",
        how="left",
    )

    # Left join proteomics data
    df = df.join(
        proteomics_df.select(["gene_id", "in_cilia_proteomics", "in_centrosome_proteomics"]),
        on="gene_id",
        how="left",
    )

    # Fill NULL proteomics flags with False (absence is informative)
    df = df.with_columns([
        pl.col("in_cilia_proteomics").fill_null(False),
        pl.col("in_centrosome_proteomics").fill_null(False),
    ])

    logger.info(
        "process_merge_complete",
        row_count=len(df),
        has_hpa=df.filter(pl.col("hpa_main_location").is_not_null()).height,
        has_proteomics=df.filter(
            (pl.col("in_cilia_proteomics") == True) | (pl.col("in_centrosome_proteomics") == True)
        ).height,
    )

    # Classify evidence type
    df = classify_evidence_type(df)

    # Score localization
    df = score_localization(df)

    logger.info("process_localization_complete", row_count=len(df))

    return df

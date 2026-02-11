"""Transform animal model phenotype data: filter and score."""

import polars as pl
import structlog

from usher_pipeline.evidence.animal_models.models import (
    SENSORY_MP_KEYWORDS,
    SENSORY_ZP_KEYWORDS,
)
from usher_pipeline.evidence.animal_models.fetch import (
    fetch_ortholog_mapping,
    fetch_mgi_phenotypes,
    fetch_zfin_phenotypes,
    fetch_impc_phenotypes,
)

logger = structlog.get_logger()


def filter_sensory_phenotypes(
    phenotype_df: pl.DataFrame,
    keywords: list[str],
    term_column: str = "mp_term_name"
) -> pl.DataFrame:
    """Filter phenotypes for sensory/cilia relevance using keyword matching.

    Performs case-insensitive substring matching against phenotype terms.
    Returns only rows where the phenotype term matches at least one keyword.

    Args:
        phenotype_df: DataFrame with phenotype terms
        keywords: List of keywords to match (e.g., SENSORY_MP_KEYWORDS)
        term_column: Name of column containing phenotype term names

    Returns:
        Filtered DataFrame with only sensory-relevant phenotypes
    """
    if phenotype_df.is_empty():
        return phenotype_df

    # Skip filtering if term column is missing or all NULL
    if term_column not in phenotype_df.columns:
        logger.warning("filter_sensory_phenotypes_skip", reason=f"column_{term_column}_missing")
        return pl.DataFrame(schema=phenotype_df.schema).clear()

    if phenotype_df[term_column].null_count() == len(phenotype_df):
        logger.warning("filter_sensory_phenotypes_skip", reason=f"all_{term_column}_null")
        return pl.DataFrame(schema=phenotype_df.schema).clear()

    logger.info("filter_sensory_phenotypes_start", row_count=len(phenotype_df))

    # Create case-insensitive match condition
    # Match if ANY keyword appears as substring in term (handles NULL by checking is_not_null first)
    match_condition = pl.lit(False)

    for keyword in keywords:
        match_condition = match_condition | (
            pl.col(term_column).is_not_null() &
            pl.col(term_column).str.to_lowercase().str.contains(keyword.lower())
        )

    # Filter phenotypes
    filtered = phenotype_df.filter(match_condition)

    logger.info(
        "filter_sensory_phenotypes_complete",
        input_count=len(phenotype_df),
        output_count=len(filtered),
        filtered_pct=round(100 * len(filtered) / len(phenotype_df), 1) if len(phenotype_df) > 0 else 0,
    )

    return filtered


def score_animal_evidence(df: pl.DataFrame) -> pl.DataFrame:
    """Compute animal model evidence scores with ortholog confidence weighting.

    Scoring formula:
    - Base score = 0 if no phenotypes
    - For each organism with sensory phenotypes:
      * Mouse (MGI): +0.4 weighted by ortholog confidence
      * Zebrafish (ZFIN): +0.3 weighted by ortholog confidence
      * IMPC: +0.3 (independent confirmation bonus)
    - Confidence weighting: HIGH=1.0, MEDIUM=0.7, LOW=0.4
    - Multiply by log2(sensory_phenotype_count + 1) / log2(max_count + 1) to reward multiple phenotypes
    - Clamp to [0, 1]
    - NULL if no ortholog mapping exists

    Args:
        df: DataFrame with ortholog mappings and phenotype flags

    Returns:
        DataFrame with added animal_model_score_normalized column
    """
    logger.info("score_animal_evidence_start", gene_count=len(df))

    # Define confidence weights
    confidence_weight = pl.when(pl.col("confidence") == "HIGH").then(1.0)\
        .when(pl.col("confidence") == "MEDIUM").then(0.7)\
        .when(pl.col("confidence") == "LOW").then(0.4)\
        .otherwise(0.0)

    # Score for mouse phenotypes (MGI)
    mouse_score = (
        pl.when(pl.col("has_mouse_phenotype") == True)
        .then(
            0.4 * pl.when(pl.col("mouse_ortholog_confidence") == "HIGH").then(1.0)
            .when(pl.col("mouse_ortholog_confidence") == "MEDIUM").then(0.7)
            .when(pl.col("mouse_ortholog_confidence") == "LOW").then(0.4)
            .otherwise(0.0)
        )
        .otherwise(0.0)
    )

    # Score for zebrafish phenotypes (ZFIN)
    zebrafish_score = (
        pl.when(pl.col("has_zebrafish_phenotype") == True)
        .then(
            0.3 * pl.when(pl.col("zebrafish_ortholog_confidence") == "HIGH").then(1.0)
            .when(pl.col("zebrafish_ortholog_confidence") == "MEDIUM").then(0.7)
            .when(pl.col("zebrafish_ortholog_confidence") == "LOW").then(0.4)
            .otherwise(0.0)
        )
        .otherwise(0.0)
    )

    # Score for IMPC phenotypes (independent confirmation)
    impc_score = (
        pl.when(pl.col("has_impc_phenotype") == True)
        .then(0.3)
        .otherwise(0.0)
    )

    # Combine scores
    base_score = mouse_score + zebrafish_score + impc_score

    # Get max sensory phenotype count for normalization
    max_count = df.select(pl.col("sensory_phenotype_count").max()).item()
    if max_count is None or max_count == 0:
        max_count = 1  # Avoid division by zero

    # Apply phenotype count scaling (diminishing returns via log)
    # log2(count + 1) / log2(max_count + 1)
    import math
    max_log = math.log2(max_count + 1)

    phenotype_scaling = (
        pl.when(pl.col("sensory_phenotype_count").is_not_null())
        .then((pl.col("sensory_phenotype_count") + 1).log(2) / max_log)
        .otherwise(0.0)
    )

    # Final score: base_score * phenotype_scaling, clamped to [0, 1]
    # NULL if no ortholog mapping
    animal_model_score = (
        pl.when(
            pl.col("mouse_ortholog").is_null() & pl.col("zebrafish_ortholog").is_null()
        )
        .then(None)
        .otherwise(
            (base_score * phenotype_scaling).clip(0.0, 1.0)
        )
        .alias("animal_model_score_normalized")
    )

    result = df.with_columns([animal_model_score])

    logger.info(
        "score_animal_evidence_complete",
        scored_genes=result.filter(pl.col("animal_model_score_normalized").is_not_null()).height,
        null_genes=result.filter(pl.col("animal_model_score_normalized").is_null()).height,
    )

    return result


def process_animal_model_evidence(gene_ids: list[str]) -> pl.DataFrame:
    """End-to-end processing of animal model phenotype evidence.

    Executes the full pipeline:
    1. Fetch ortholog mappings (mouse and zebrafish)
    2. Fetch phenotypes from MGI, ZFIN, and IMPC
    3. Filter for sensory/cilia-relevant phenotypes
    4. Aggregate phenotypes by gene
    5. Score evidence with confidence weighting

    Args:
        gene_ids: List of human gene IDs (ENSG format)

    Returns:
        DataFrame with animal model evidence for each gene
    """
    logger.info("process_animal_model_evidence_start", gene_count=len(gene_ids))

    # Step 1: Fetch ortholog mappings
    logger.info("step_1_fetch_orthologs")
    orthologs = fetch_ortholog_mapping(gene_ids)

    # Extract lists of orthologs to query
    mouse_genes = orthologs.filter(pl.col("mouse_ortholog").is_not_null())["mouse_ortholog"].to_list()
    zebrafish_genes = orthologs.filter(pl.col("zebrafish_ortholog").is_not_null())["zebrafish_ortholog"].to_list()

    logger.info(
        "orthologs_extracted",
        mouse_count=len(mouse_genes),
        zebrafish_count=len(zebrafish_genes),
    )

    # Step 2: Fetch phenotypes
    logger.info("step_2_fetch_phenotypes")

    # MGI phenotypes
    mgi_pheno = fetch_mgi_phenotypes(mouse_genes)
    mgi_sensory = filter_sensory_phenotypes(mgi_pheno, SENSORY_MP_KEYWORDS, "mp_term_name")

    # ZFIN phenotypes
    zfin_pheno = fetch_zfin_phenotypes(zebrafish_genes)
    zfin_sensory = filter_sensory_phenotypes(zfin_pheno, SENSORY_ZP_KEYWORDS, "zp_term_name")

    # IMPC phenotypes
    impc_pheno = fetch_impc_phenotypes(mouse_genes)
    impc_sensory = filter_sensory_phenotypes(impc_pheno, SENSORY_MP_KEYWORDS, "mp_term_name")

    logger.info(
        "phenotypes_filtered",
        mgi_total=len(mgi_pheno),
        mgi_sensory=len(mgi_sensory),
        zfin_total=len(zfin_pheno),
        zfin_sensory=len(zfin_sensory),
        impc_total=len(impc_pheno),
        impc_sensory=len(impc_sensory),
    )

    # Step 3: Aggregate phenotypes by gene
    logger.info("step_3_aggregate_phenotypes")

    # Count sensory phenotypes per mouse gene
    if not mgi_sensory.is_empty():
        mgi_counts = (
            mgi_sensory
            .group_by("mouse_gene")
            .agg([
                pl.col("mp_term_name").count().alias("mgi_phenotype_count"),
                pl.col("mp_term_name").str.join("; ").alias("mgi_terms"),
            ])
        )
    else:
        mgi_counts = pl.DataFrame({
            "mouse_gene": [],
            "mgi_phenotype_count": [],
            "mgi_terms": [],
        }, schema={"mouse_gene": pl.String, "mgi_phenotype_count": pl.Int64, "mgi_terms": pl.String})

    # Count sensory phenotypes per zebrafish gene
    if not zfin_sensory.is_empty():
        zfin_counts = (
            zfin_sensory
            .group_by("zebrafish_gene")
            .agg([
                pl.col("zp_term_name").count().alias("zfin_phenotype_count"),
                pl.col("zp_term_name").str.join("; ").alias("zfin_terms"),
            ])
        )
    else:
        zfin_counts = pl.DataFrame({
            "zebrafish_gene": [],
            "zfin_phenotype_count": [],
            "zfin_terms": [],
        }, schema={"zebrafish_gene": pl.String, "zfin_phenotype_count": pl.Int64, "zfin_terms": pl.String})

    # Count sensory phenotypes per mouse gene from IMPC
    if not impc_sensory.is_empty():
        impc_counts = (
            impc_sensory
            .group_by("mouse_gene")
            .agg([
                pl.col("mp_term_name").count().alias("impc_phenotype_count"),
                pl.col("mp_term_name").str.join("; ").alias("impc_terms"),
            ])
        )
    else:
        impc_counts = pl.DataFrame({
            "mouse_gene": [],
            "impc_phenotype_count": [],
            "impc_terms": [],
        }, schema={"mouse_gene": pl.String, "impc_phenotype_count": pl.Int64, "impc_terms": pl.String})

    # Step 4: Join phenotype data with ortholog mappings
    logger.info("step_4_join_data")

    result = (
        orthologs
        # Join MGI phenotypes
        .join(
            mgi_counts,
            left_on="mouse_ortholog",
            right_on="mouse_gene",
            how="left"
        )
        # Join ZFIN phenotypes
        .join(
            zfin_counts,
            left_on="zebrafish_ortholog",
            right_on="zebrafish_gene",
            how="left"
        )
        # Join IMPC phenotypes
        .join(
            impc_counts,
            left_on="mouse_ortholog",
            right_on="mouse_gene",
            how="left"
        )
        # Add flags
        .with_columns([
            (pl.col("mgi_phenotype_count") > 0).alias("has_mouse_phenotype"),
            (pl.col("zfin_phenotype_count") > 0).alias("has_zebrafish_phenotype"),
            (pl.col("impc_phenotype_count") > 0).alias("has_impc_phenotype"),
        ])
        # Calculate total sensory phenotype count
        .with_columns([
            (
                pl.col("mgi_phenotype_count").fill_null(0) +
                pl.col("zfin_phenotype_count").fill_null(0) +
                pl.col("impc_phenotype_count").fill_null(0)
            ).alias("sensory_phenotype_count")
        ])
        # Combine phenotype terms
        .with_columns([
            pl.concat_str([
                pl.col("mgi_terms").fill_null(""),
                pl.col("zfin_terms").fill_null(""),
                pl.col("impc_terms").fill_null(""),
            ], separator="; ").str.replace_all("; ; ", "; ").str.strip_chars("; ").alias("phenotype_categories")
        ])
        # Set sensory_phenotype_count to NULL if zero (preserve NULL pattern)
        .with_columns([
            pl.when(pl.col("sensory_phenotype_count") == 0)
            .then(None)
            .otherwise(pl.col("sensory_phenotype_count"))
            .alias("sensory_phenotype_count")
        ])
        # Select final columns
        .select([
            "gene_id",
            "mouse_ortholog",
            "mouse_ortholog_confidence",
            "zebrafish_ortholog",
            "zebrafish_ortholog_confidence",
            "has_mouse_phenotype",
            "has_zebrafish_phenotype",
            "has_impc_phenotype",
            "sensory_phenotype_count",
            "phenotype_categories",
        ])
    )

    # Step 5: Score evidence
    logger.info("step_5_score_evidence")
    result = score_animal_evidence(result)

    logger.info(
        "process_animal_model_evidence_complete",
        total_genes=len(result),
        with_orthologs=result.filter(
            pl.col("mouse_ortholog").is_not_null() | pl.col("zebrafish_ortholog").is_not_null()
        ).height,
        with_sensory_phenotypes=result.filter(
            pl.col("sensory_phenotype_count").is_not_null()
        ).height,
    )

    return result

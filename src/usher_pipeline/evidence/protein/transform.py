"""Transform and normalize protein features."""

from typing import List

import polars as pl
import structlog

from usher_pipeline.evidence.protein.models import (
    CILIA_DOMAIN_KEYWORDS,
    SCAFFOLD_DOMAIN_TYPES,
)
from usher_pipeline.evidence.protein.fetch import (
    fetch_uniprot_features,
    fetch_interpro_domains,
)

logger = structlog.get_logger()


def extract_protein_features(
    uniprot_df: pl.DataFrame,
    interpro_df: pl.DataFrame,
) -> pl.DataFrame:
    """Extract and combine protein features from UniProt and InterPro data.

    Joins UniProt and InterPro data, computes domain counts, sets flags
    for coiled-coil and transmembrane regions.

    Args:
        uniprot_df: DataFrame from fetch_uniprot_features with UniProt data
        interpro_df: DataFrame from fetch_interpro_domains with InterPro data

    Returns:
        DataFrame with combined features:
        - uniprot_id, protein_length, domain_count, coiled_coil,
          coiled_coil_count, transmembrane_count, domain_names (combined)
    """
    logger.info(
        "extract_protein_features_start",
        uniprot_rows=len(uniprot_df),
        interpro_rows=len(interpro_df),
    )

    # Join UniProt and InterPro on uniprot_id
    # Use left join to preserve all UniProt entries
    combined = uniprot_df.join(
        interpro_df,
        on="uniprot_id",
        how="left",
        suffix="_interpro",
    )

    # Combine domain names from both sources (deduplicate)
    # Use list.concat instead of + operator
    combined = combined.with_columns([
        # Combine domain name lists
        pl.when(
            pl.col("domain_names_interpro").is_not_null() &
            (pl.col("domain_names_interpro").list.len() > 0)
        )
        .then(
            pl.col("domain_names").list.concat(pl.col("domain_names_interpro"))
            .list.unique()
        )
        .otherwise(pl.col("domain_names"))
        .alias("domain_names_combined"),
    ])

    # Compute domain count from combined sources
    combined = combined.with_columns([
        pl.col("domain_names_combined").list.len().alias("domain_count"),
    ])

    # Set coiled_coil boolean from count
    combined = combined.with_columns([
        pl.when(pl.col("coiled_coil_count").is_not_null())
        .then(pl.col("coiled_coil_count") > 0)
        .otherwise(None)
        .alias("coiled_coil"),
    ])

    # Select final columns
    result = combined.select([
        "uniprot_id",
        "protein_length",
        "domain_count",
        "coiled_coil",
        "coiled_coil_count",
        "transmembrane_count",
        pl.col("domain_names_combined").alias("domain_names"),
    ])

    logger.info(
        "extract_protein_features_complete",
        total_rows=len(result),
        with_domains=result.filter(pl.col("domain_count") > 0).height,
    )

    return result


def detect_cilia_motifs(df: pl.DataFrame) -> pl.DataFrame:
    """Detect cilia-associated motifs via domain keyword matching.

    Scans domain names for cilia-related keywords, scaffold/adaptor domains,
    and sensory-related domains. Pattern matching does NOT presuppose cilia
    involvement - it flags structural features for further investigation.

    Args:
        df: DataFrame with domain_names column (list of domain names)

    Returns:
        DataFrame with added columns:
        - has_cilia_domain: Boolean flag for cilia-associated domains
        - scaffold_adaptor_domain: Boolean flag for scaffold domains
        - has_sensory_domain: Boolean flag for sensory domains
    """
    logger.info("detect_cilia_motifs_start", row_count=len(df))

    # Ensure domain_names is List(String), not List(Null)
    # This handles edge case where all proteins have empty domain lists
    if "domain_names" in df.columns:
        current_dtype = df.schema["domain_names"]
        if str(current_dtype) == "List(Null)" or "Null" in str(current_dtype):
            df = df.with_columns([
                pl.col("domain_names").cast(pl.List(pl.String)).alias("domain_names")
            ])

    # Sensory domain keywords
    sensory_keywords = [
        "stereocilia",
        "photoreceptor",
        "usher",
        "harmonin",
        "cadherin 23",
        "protocadherin",
    ]

    # Helper function to check if any keyword matches any domain (case-insensitive)
    def create_keyword_matcher(keywords: List[str]) -> pl.Expr:
        """Create polars expression that checks if any keyword matches any domain."""
        # For each domain in the list, check if it contains any keyword
        # Case-insensitive substring matching
        conditions = []
        for keyword in keywords:
            conditions.append(
                pl.col("domain_names")
                .list.eval(
                    pl.when(pl.element().is_not_null())
                    .then(pl.element().str.to_lowercase().str.contains(keyword.lower()))
                    .otherwise(False)
                )
                .list.any()
            )
        # Return True if ANY condition matches
        if conditions:
            return pl.any_horizontal(conditions)
        else:
            return pl.lit(False)

    # Detect cilia domains
    df = df.with_columns([
        pl.when(
            pl.col("domain_names").is_not_null() &
            (pl.col("domain_names").list.len() > 0)
        )
        .then(create_keyword_matcher(CILIA_DOMAIN_KEYWORDS))
        .otherwise(None)
        .alias("has_cilia_domain"),
    ])

    # Detect scaffold/adaptor domains
    df = df.with_columns([
        pl.when(
            pl.col("domain_names").is_not_null() &
            (pl.col("domain_names").list.len() > 0)
        )
        .then(create_keyword_matcher(SCAFFOLD_DOMAIN_TYPES))
        .otherwise(None)
        .alias("scaffold_adaptor_domain"),
    ])

    # Detect sensory domains
    df = df.with_columns([
        pl.when(
            pl.col("domain_names").is_not_null() &
            (pl.col("domain_names").list.len() > 0)
        )
        .then(create_keyword_matcher(sensory_keywords))
        .otherwise(None)
        .alias("has_sensory_domain"),
    ])

    # Log summary
    cilia_count = df.filter(pl.col("has_cilia_domain") == True).height
    scaffold_count = df.filter(pl.col("scaffold_adaptor_domain") == True).height
    sensory_count = df.filter(pl.col("has_sensory_domain") == True).height

    logger.info(
        "detect_cilia_motifs_complete",
        cilia_domain_count=cilia_count,
        scaffold_domain_count=scaffold_count,
        sensory_domain_count=sensory_count,
    )

    return df


def normalize_protein_features(df: pl.DataFrame) -> pl.DataFrame:
    """Normalize protein features to 0-1 range and compute composite score.

    Normalizes continuous features (protein_length, domain_count, transmembrane_count)
    and computes weighted composite score. NULL preservation: genes without UniProt
    entries get NULL scores (not 0.0).

    Args:
        df: DataFrame with extracted protein features

    Returns:
        DataFrame with added protein_score_normalized column (0-1 range)
    """
    logger.info("normalize_protein_features_start", row_count=len(df))

    # Filter to proteins with data for normalization stats
    measured = df.filter(pl.col("protein_length").is_not_null())

    if len(measured) == 0:
        # No proteins with data - return with NULL scores
        return df.with_columns([
            pl.lit(None).cast(pl.Float64).alias("length_rank"),
            pl.lit(None).cast(pl.Float64).alias("domain_rank"),
            pl.lit(None).cast(pl.Float64).alias("transmembrane_normalized"),
            pl.lit(None).cast(pl.Float64).alias("protein_score_normalized"),
        ])

    # Normalize protein length via log-transform rank percentile
    # Log-transform handles skewed distribution, rank percentile gives 0-1
    df = df.with_columns([
        pl.when(pl.col("protein_length").is_not_null())
        .then(
            pl.col("protein_length").log10().rank(method="average") /
            measured.select(pl.col("protein_length").log10().rank(method="average").max()).item()
        )
        .otherwise(None)
        .alias("length_rank"),
    ])

    # Normalize domain count via rank percentile
    df = df.with_columns([
        pl.when(pl.col("domain_count").is_not_null())
        .then(
            pl.col("domain_count").rank(method="average") /
            measured.select(pl.col("domain_count").rank(method="average").max()).item()
        )
        .otherwise(None)
        .alias("domain_rank"),
    ])

    # Normalize transmembrane count (cap at 20, then divide)
    df = df.with_columns([
        pl.when(pl.col("transmembrane_count").is_not_null())
        .then(
            pl.min_horizontal(pl.col("transmembrane_count"), pl.lit(20)) / 20.0
        )
        .otherwise(None)
        .alias("transmembrane_normalized"),
    ])

    # Convert boolean flags to 0/1 for composite score
    df = df.with_columns([
        pl.col("coiled_coil").cast(pl.Float64).fill_null(0.0).alias("coiled_coil_score"),
        pl.col("has_cilia_domain").cast(pl.Float64).fill_null(0.0).alias("cilia_score"),
        pl.col("scaffold_adaptor_domain").cast(pl.Float64).fill_null(0.0).alias("scaffold_score"),
    ])

    # Composite protein score (weighted combination)
    # Weights: length 15%, domain 20%, coiled-coil 20%, TM 20%, cilia 15%, scaffold 10%
    # NULL if no protein_length (i.e., no UniProt entry)
    df = df.with_columns([
        pl.when(pl.col("protein_length").is_not_null())
        .then(
            (0.15 * pl.col("length_rank").fill_null(0.0)) +
            (0.20 * pl.col("domain_rank").fill_null(0.0)) +
            (0.20 * pl.col("coiled_coil_score")) +
            (0.20 * pl.col("transmembrane_normalized").fill_null(0.0)) +
            (0.15 * pl.col("cilia_score")) +
            (0.10 * pl.col("scaffold_score"))
        )
        .otherwise(None)
        .alias("protein_score_normalized"),
    ])

    # Drop temporary scoring columns
    df = df.drop([
        "length_rank",
        "domain_rank",
        "transmembrane_normalized",
        "coiled_coil_score",
        "cilia_score",
        "scaffold_score",
    ])

    # Log summary statistics
    score_stats = df.filter(pl.col("protein_score_normalized").is_not_null()).select([
        pl.col("protein_score_normalized").min().alias("min"),
        pl.col("protein_score_normalized").max().alias("max"),
        pl.col("protein_score_normalized").mean().alias("mean"),
    ])

    if len(score_stats) > 0:
        logger.info(
            "normalize_protein_features_complete",
            scored_proteins=df.filter(pl.col("protein_score_normalized").is_not_null()).height,
            score_min=round(score_stats["min"][0], 3),
            score_max=round(score_stats["max"][0], 3),
            score_mean=round(score_stats["mean"][0], 3),
        )
    else:
        logger.info("normalize_protein_features_complete", scored_proteins=0)

    return df


def process_protein_evidence(
    gene_ids: List[str],
    uniprot_mapping: pl.DataFrame,
) -> pl.DataFrame:
    """End-to-end protein evidence processing pipeline.

    Composes: map gene IDs -> fetch UniProt -> fetch InterPro ->
              extract features -> detect motifs -> normalize -> collect

    Args:
        gene_ids: List of Ensembl gene IDs
        uniprot_mapping: DataFrame with gene_id, gene_symbol, uniprot_id columns

    Returns:
        Materialized DataFrame ready for DuckDB storage with columns:
        - gene_id, gene_symbol, uniprot_id, protein_length, domain_count,
          coiled_coil, coiled_coil_count, transmembrane_count,
          scaffold_adaptor_domain, has_cilia_domain, has_sensory_domain,
          protein_score_normalized
    """
    logger.info("process_protein_evidence_start", gene_count=len(gene_ids))

    # Filter mapping to requested genes
    gene_map = uniprot_mapping.filter(pl.col("gene_id").is_in(gene_ids))

    # Extract UniProt IDs (filter out NULLs)
    uniprot_ids = (
        gene_map
        .filter(pl.col("uniprot_id").is_not_null())
        .select("uniprot_id")
        .unique()
        .to_series()
        .to_list()
    )

    logger.info(
        "uniprot_mapping_complete",
        total_genes=len(gene_ids),
        mapped_genes=len(uniprot_ids),
    )

    # Fetch UniProt features
    uniprot_df = fetch_uniprot_features(uniprot_ids)

    # Fetch InterPro domains
    interpro_df = fetch_interpro_domains(uniprot_ids)

    # Extract features
    features_df = extract_protein_features(uniprot_df, interpro_df)

    # Detect cilia motifs
    features_df = detect_cilia_motifs(features_df)

    # Normalize features
    features_df = normalize_protein_features(features_df)

    # Join back to gene mapping to get gene_id and gene_symbol
    # Use right join to preserve all genes (including those without UniProt mapping)
    result = features_df.join(
        gene_map.select(["gene_id", "gene_symbol", "uniprot_id"]),
        on="uniprot_id",
        how="right",
    )

    # Select final columns in order
    result = result.select([
        "gene_id",
        "gene_symbol",
        "uniprot_id",
        "protein_length",
        "domain_count",
        "coiled_coil",
        "coiled_coil_count",
        "transmembrane_count",
        "scaffold_adaptor_domain",
        "has_cilia_domain",
        "has_sensory_domain",
        "protein_score_normalized",
    ])

    logger.info(
        "process_protein_evidence_complete",
        total_genes=len(result),
        with_uniprot=result.filter(pl.col("uniprot_id").is_not_null()).height,
        with_scores=result.filter(pl.col("protein_score_normalized").is_not_null()).height,
    )

    return result

"""Fetch animal model phenotype data and ortholog mappings."""

import gzip
import io
from pathlib import Path
from typing import Optional

import httpx
import polars as pl
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = structlog.get_logger()


# HCOP ortholog database URLs
HCOP_HUMAN_MOUSE_URL = "https://ftp.ebi.ac.uk/pub/databases/genenames/hcop/human_mouse_hcop_fifteen_column.txt.gz"
HCOP_HUMAN_ZEBRAFISH_URL = "https://ftp.ebi.ac.uk/pub/databases/genenames/hcop/human_zebrafish_hcop_fifteen_column.txt.gz"

# MGI phenotype report URL
MGI_GENE_PHENO_URL = "https://www.informatics.jax.org/downloads/reports/MGI_GenePheno.rpt"

# ZFIN phenotype data URL
ZFIN_PHENO_URL = "https://zfin.org/downloads/phenoGeneCleanData_fish.txt"

# IMPC API base URL
IMPC_API_BASE = "https://www.ebi.ac.uk/mi/impc/solr/genotype-phenotype/select"


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def _download_gzipped(url: str) -> bytes:
    """Download and decompress a gzipped file.

    Args:
        url: URL to download

    Returns:
        Decompressed file content as bytes
    """
    logger.info("download_start", url=url)

    with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as response:
        response.raise_for_status()

        # Read compressed data
        compressed_data = b""
        for chunk in response.iter_bytes(chunk_size=8192):
            compressed_data += chunk

    # Decompress
    logger.info("decompress_start", compressed_size_mb=round(len(compressed_data) / 1024 / 1024, 2))
    decompressed = gzip.decompress(compressed_data)
    logger.info("decompress_complete", decompressed_size_mb=round(len(decompressed) / 1024 / 1024, 2))

    return decompressed


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def _download_text(url: str) -> str:
    """Download a text file with retry.

    Args:
        url: URL to download

    Returns:
        File content as string
    """
    logger.info("download_text_start", url=url)

    with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as response:
        response.raise_for_status()
        response.read()
        content = response.text

    logger.info("download_text_complete", size_mb=round(len(content) / 1024 / 1024, 2))
    return content


def fetch_ortholog_mapping(gene_ids: list[str]) -> pl.DataFrame:
    """Fetch human-to-mouse and human-to-zebrafish ortholog mappings from HCOP.

    Downloads HCOP ortholog data, assigns confidence scores based on number of
    supporting databases, and handles one-to-many mappings by selecting the
    ortholog with highest confidence.

    Confidence scoring:
    - HIGH: 8+ supporting databases
    - MEDIUM: 4-7 supporting databases
    - LOW: 1-3 supporting databases

    Args:
        gene_ids: List of human gene IDs (ENSG format)

    Returns:
        DataFrame with columns:
        - gene_id: Human gene ID
        - mouse_ortholog: Mouse gene symbol
        - mouse_ortholog_confidence: HIGH/MEDIUM/LOW
        - zebrafish_ortholog: Zebrafish gene symbol
        - zebrafish_ortholog_confidence: HIGH/MEDIUM/LOW
    """
    logger.info("fetch_ortholog_mapping_start", gene_count=len(gene_ids))

    # Download human-mouse HCOP data
    logger.info("fetch_hcop_mouse")
    mouse_data = _download_gzipped(HCOP_HUMAN_MOUSE_URL)
    mouse_df = pl.read_csv(
        io.BytesIO(mouse_data),
        separator="\t",
        null_values=["", "NA"],
    )

    logger.info("hcop_mouse_columns", columns=mouse_df.columns)

    # Parse mouse ortholog data
    # HCOP columns: human_entrez_gene, human_ensembl_gene, hgnc_id, human_name, human_symbol,
    #               human_chr, human_assert_ids, mouse_entrez_gene, mouse_ensembl_gene,
    #               mgi_id, mouse_name, mouse_symbol, mouse_chr, mouse_assert_ids, support
    mouse_orthologs = (
        mouse_df
        .filter(pl.col("human_ensembl_gene").is_in(gene_ids))
        .select([
            pl.col("human_ensembl_gene").alias("gene_id"),
            pl.col("mouse_symbol").alias("mouse_ortholog"),
            pl.col("support").str.split(",").list.len().alias("support_count"),
        ])
        .with_columns([
            pl.when(pl.col("support_count") >= 8)
            .then(pl.lit("HIGH"))
            .when(pl.col("support_count") >= 4)
            .then(pl.lit("MEDIUM"))
            .otherwise(pl.lit("LOW"))
            .alias("mouse_ortholog_confidence")
        ])
        .sort(["gene_id", "support_count"], descending=[False, True])
        .group_by("gene_id")
        .first()
        .select(["gene_id", "mouse_ortholog", "mouse_ortholog_confidence"])
    )

    logger.info("mouse_orthologs_mapped", count=len(mouse_orthologs))

    # Download human-zebrafish HCOP data
    logger.info("fetch_hcop_zebrafish")
    zebrafish_data = _download_gzipped(HCOP_HUMAN_ZEBRAFISH_URL)
    zebrafish_df = pl.read_csv(
        io.BytesIO(zebrafish_data),
        separator="\t",
        null_values=["", "NA"],
        infer_schema_length=10000,
    )

    logger.info("hcop_zebrafish_columns", columns=zebrafish_df.columns)

    # Parse zebrafish ortholog data
    # Handle case where zebrafish_df might be empty or missing expected columns
    if "zebrafish_symbol" in zebrafish_df.columns and len(zebrafish_df) > 0:
        zebrafish_orthologs = (
            zebrafish_df
            .filter(pl.col("human_ensembl_gene").is_in(gene_ids))
            .select([
                pl.col("human_ensembl_gene").alias("gene_id"),
                pl.col("zebrafish_symbol").alias("zebrafish_ortholog"),
                pl.col("support").str.split(",").list.len().alias("support_count"),
            ])
            .with_columns([
                pl.when(pl.col("support_count") >= 8)
                .then(pl.lit("HIGH"))
                .when(pl.col("support_count") >= 4)
                .then(pl.lit("MEDIUM"))
                .otherwise(pl.lit("LOW"))
                .alias("zebrafish_ortholog_confidence")
            ])
            .sort(["gene_id", "support_count"], descending=[False, True])
            .group_by("gene_id")
            .first()
            .select(["gene_id", "zebrafish_ortholog", "zebrafish_ortholog_confidence"])
        )
    else:
        # Return empty DataFrame with correct schema
        zebrafish_orthologs = pl.DataFrame({
            "gene_id": [],
            "zebrafish_ortholog": [],
            "zebrafish_ortholog_confidence": [],
        }, schema={"gene_id": pl.String, "zebrafish_ortholog": pl.String, "zebrafish_ortholog_confidence": pl.String})

    logger.info("zebrafish_orthologs_mapped", count=len(zebrafish_orthologs))

    # Create base DataFrame with all gene IDs
    base_df = pl.DataFrame({"gene_id": gene_ids})

    # Left join ortholog mappings
    result = (
        base_df
        .join(mouse_orthologs, on="gene_id", how="left")
        .join(zebrafish_orthologs, on="gene_id", how="left")
    )

    logger.info(
        "fetch_ortholog_mapping_complete",
        total_genes=len(result),
        mouse_mapped=result.filter(pl.col("mouse_ortholog").is_not_null()).height,
        zebrafish_mapped=result.filter(pl.col("zebrafish_ortholog").is_not_null()).height,
    )

    return result


def fetch_mgi_phenotypes(mouse_gene_symbols: list[str]) -> pl.DataFrame:
    """Fetch mouse phenotype data from MGI (Mouse Genome Informatics).

    Downloads the MGI gene-phenotype report and extracts phenotype terms
    for the specified mouse genes.

    Args:
        mouse_gene_symbols: List of mouse gene symbols

    Returns:
        DataFrame with columns:
        - mouse_gene: Mouse gene symbol
        - mp_term_id: Mammalian Phenotype term ID
        - mp_term_name: Mammalian Phenotype term name
    """
    if not mouse_gene_symbols:
        logger.info("fetch_mgi_phenotypes_skip", reason="no_mouse_genes")
        return pl.DataFrame({
            "mouse_gene": [],
            "mp_term_id": [],
            "mp_term_name": [],
        })

    logger.info("fetch_mgi_phenotypes_start", gene_count=len(mouse_gene_symbols))

    # Download MGI phenotype report
    content = _download_text(MGI_GENE_PHENO_URL)

    # Parse TSV (skip first line if it's a comment)
    lines = content.strip().split("\n")
    if lines[0].startswith("#"):
        lines = lines[1:]

    # Read as DataFrame (all columns as string to avoid type inference issues)
    df = pl.read_csv(
        io.StringIO("\n".join(lines)),
        separator="\t",
        null_values=["", "NA"],
        has_header=True,
        infer_schema_length=10000,
    )

    logger.info("mgi_raw_columns", columns=df.columns)

    # MGI_GenePheno.rpt columns vary, but typically include:
    # Allelic Composition, Allele Symbol(s), Genetic Background, Mammalian Phenotype ID, PubMed ID, MGI Marker Accession ID
    # We need to identify the right columns
    # Expected columns: marker symbol, MP ID, MP term
    # Common column names: "Marker Symbol", "Mammalian Phenotype ID"

    # Try to find the right columns
    marker_col = None
    mp_id_col = None

    for col in df.columns:
        col_lower = col.lower()
        if "marker" in col_lower and "symbol" in col_lower:
            marker_col = col
        elif "mammalian phenotype id" in col_lower or "mp id" in col_lower:
            mp_id_col = col

    if marker_col is None or mp_id_col is None:
        logger.warning("mgi_column_detection_failed", columns=df.columns)
        # Return empty result
        return pl.DataFrame({
            "mouse_gene": [],
            "mp_term_id": [],
            "mp_term_name": [],
        })

    # Filter for genes of interest and extract phenotypes
    # Note: MGI report may have one row per allele-phenotype combination
    # We'll aggregate unique phenotypes per gene
    result = (
        df
        .filter(pl.col(marker_col).is_in(mouse_gene_symbols))
        .select([
            pl.col(marker_col).alias("mouse_gene"),
            pl.col(mp_id_col).alias("mp_term_id"),
            pl.lit(None).alias("mp_term_name"),  # Term name not in this report
        ])
        .unique()
    )

    logger.info("fetch_mgi_phenotypes_complete", phenotype_count=len(result))

    return result


def fetch_zfin_phenotypes(zebrafish_gene_symbols: list[str]) -> pl.DataFrame:
    """Fetch zebrafish phenotype data from ZFIN.

    Downloads ZFIN phenotype data and extracts phenotype terms for the
    specified zebrafish genes.

    Args:
        zebrafish_gene_symbols: List of zebrafish gene symbols

    Returns:
        DataFrame with columns:
        - zebrafish_gene: Zebrafish gene symbol
        - zp_term_id: Zebrafish Phenotype term ID (or descriptor)
        - zp_term_name: Zebrafish Phenotype term name
    """
    if not zebrafish_gene_symbols:
        logger.info("fetch_zfin_phenotypes_skip", reason="no_zebrafish_genes")
        return pl.DataFrame({
            "zebrafish_gene": [],
            "zp_term_id": [],
            "zp_term_name": [],
        })

    logger.info("fetch_zfin_phenotypes_start", gene_count=len(zebrafish_gene_symbols))

    # Download ZFIN phenotype data
    content = _download_text(ZFIN_PHENO_URL)

    # Parse TSV
    df = pl.read_csv(
        io.StringIO(content),
        separator="\t",
        null_values=["", "NA"],
        has_header=True,
    )

    logger.info("zfin_raw_columns", columns=df.columns)

    # ZFIN phenoGeneCleanData_fish.txt columns (typical):
    # Gene Symbol, Gene ID, Affected Structure or Process 1 subterm ID, etc.
    # Look for gene symbol and phenotype columns
    gene_col = None
    pheno_col = None

    for col in df.columns:
        col_lower = col.lower()
        if "gene" in col_lower and ("symbol" in col_lower or "name" in col_lower):
            gene_col = col
        elif "phenotype" in col_lower or "structure" in col_lower or "process" in col_lower:
            if pheno_col is None:  # Take first phenotype-related column
                pheno_col = col

    if gene_col is None or pheno_col is None:
        logger.warning("zfin_column_detection_failed", columns=df.columns)
        return pl.DataFrame({
            "zebrafish_gene": [],
            "zp_term_id": [],
            "zp_term_name": [],
        })

    # Filter and extract
    result = (
        df
        .filter(pl.col(gene_col).is_in(zebrafish_gene_symbols))
        .select([
            pl.col(gene_col).alias("zebrafish_gene"),
            pl.lit(None).alias("zp_term_id"),
            pl.col(pheno_col).alias("zp_term_name"),
        ])
        .unique()
    )

    logger.info("fetch_zfin_phenotypes_complete", phenotype_count=len(result))

    return result


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def _query_impc_batch(gene_symbols: list[str]) -> pl.DataFrame:
    """Query IMPC API for a batch of genes.

    Args:
        gene_symbols: List of mouse gene symbols (batch)

    Returns:
        DataFrame with IMPC phenotype data
    """
    # Build query: marker_symbol:(gene1 OR gene2 OR ...)
    query = "marker_symbol:(" + " OR ".join(gene_symbols) + ")"

    params = {
        "q": query,
        "rows": 10000,
        "wt": "json",
    }

    logger.info("impc_query_batch", gene_count=len(gene_symbols))

    response = httpx.get(IMPC_API_BASE, params=params, timeout=60.0)
    response.raise_for_status()

    data = response.json()
    docs = data.get("response", {}).get("docs", [])

    if not docs:
        return pl.DataFrame({
            "mouse_gene": [],
            "mp_term_id": [],
            "mp_term_name": [],
            "p_value": [],
        })

    # Extract relevant fields
    records = []
    for doc in docs:
        gene = doc.get("marker_symbol")
        mp_id = doc.get("mp_term_id")
        mp_name = doc.get("mp_term_name")
        p_value = doc.get("p_value")

        if gene and mp_id:
            records.append({
                "mouse_gene": gene,
                "mp_term_id": mp_id,
                "mp_term_name": mp_name,
                "p_value": p_value,
            })

    df = pl.DataFrame(records)
    logger.info("impc_batch_complete", phenotype_count=len(df))

    return df


def fetch_impc_phenotypes(mouse_gene_symbols: list[str]) -> pl.DataFrame:
    """Fetch mouse phenotype data from IMPC (International Mouse Phenotyping Consortium).

    Queries the IMPC SOLR API in batches to get phenotype data for mouse genes.
    Includes statistical significance (p-value) for each phenotype.

    Args:
        mouse_gene_symbols: List of mouse gene symbols

    Returns:
        DataFrame with columns:
        - mouse_gene: Mouse gene symbol
        - mp_term_id: Mammalian Phenotype term ID
        - mp_term_name: Mammalian Phenotype term name
        - p_value: Statistical significance of phenotype
    """
    if not mouse_gene_symbols:
        logger.info("fetch_impc_phenotypes_skip", reason="no_mouse_genes")
        return pl.DataFrame({
            "mouse_gene": [],
            "mp_term_id": [],
            "mp_term_name": [],
            "p_value": [],
        })

    logger.info("fetch_impc_phenotypes_start", gene_count=len(mouse_gene_symbols))

    # Query in batches of 50 to avoid overloading API
    batch_size = 50
    all_results = []

    for i in range(0, len(mouse_gene_symbols), batch_size):
        batch = mouse_gene_symbols[i:i + batch_size]
        try:
            batch_df = _query_impc_batch(batch)
            all_results.append(batch_df)
        except Exception as e:
            logger.warning("impc_batch_failed", batch_index=i // batch_size, error=str(e))
            # Continue with other batches

    if not all_results:
        logger.warning("fetch_impc_phenotypes_no_results")
        return pl.DataFrame({
            "mouse_gene": [],
            "mp_term_id": [],
            "mp_term_name": [],
            "p_value": [],
        })

    # Combine all batches
    result = pl.concat(all_results, how="vertical_relaxed").unique()

    logger.info("fetch_impc_phenotypes_complete", total_phenotypes=len(result))

    return result

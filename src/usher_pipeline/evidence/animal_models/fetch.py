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
# HGNC moved bulk downloads from the EBI FTP to Google Cloud Storage.
HCOP_HUMAN_MOUSE_URL = "https://storage.googleapis.com/public-download-files/hcop/human_mouse_hcop_fifteen_column.txt.gz"
HCOP_HUMAN_ZEBRAFISH_URL = "https://storage.googleapis.com/public-download-files/hcop/human_zebrafish_hcop_fifteen_column.txt.gz"

# MGI phenotype report URLs
# HMD_HumanPhenotype.rpt: human/mouse homology with rolled-up MP IDs per mouse gene
#   (headerless; col 1 human symbol, col 3 mouse symbol, col 5 comma-separated MP IDs)
MGI_HMD_PHENOTYPE_URL = "https://www.informatics.jax.org/downloads/reports/HMD_HumanPhenotype.rpt"
# VOC_MammalianPhenotype.rpt: MP ontology (headerless; col 1 MP ID, col 2 term name)
MGI_MP_VOCAB_URL = "https://www.informatics.jax.org/downloads/reports/VOC_MammalianPhenotype.rpt"

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


def _empty_mgi_result() -> pl.DataFrame:
    """Return an empty MGI phenotype DataFrame with the expected schema."""
    return pl.DataFrame(
        schema={
            "mouse_gene": pl.String,
            "mp_term_id": pl.String,
            "mp_term_name": pl.String,
        }
    )


def fetch_mgi_phenotypes(mouse_gene_symbols: list[str]) -> pl.DataFrame:
    """Fetch mouse phenotype data from MGI (Mouse Genome Informatics).

    Uses two MGI reports, both of which are headerless tab-delimited files:
    - HMD_HumanPhenotype.rpt: human/mouse homology with the set of Mammalian
      Phenotype (MP) IDs rolled up per mouse gene (column 3 = mouse symbol,
      column 5 = comma-separated MP IDs).
    - VOC_MammalianPhenotype.rpt: the MP ontology, used to resolve MP IDs to
      human-readable term names (column 1 = MP ID, column 2 = term name).

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
        return _empty_mgi_result()

    logger.info("fetch_mgi_phenotypes_start", gene_count=len(mouse_gene_symbols))

    # --- MP ontology: MP ID -> term name ---
    vocab_content = _download_text(MGI_MP_VOCAB_URL)
    if not vocab_content.strip():
        logger.warning("mgi_vocab_empty")
        return _empty_mgi_result()
    vocab_df = pl.read_csv(
        io.StringIO(vocab_content),
        separator="\t",
        has_header=False,
        truncate_ragged_lines=True,
        infer_schema_length=0,
    )
    if vocab_df.width < 2:
        logger.warning("mgi_vocab_parse_failed", columns=vocab_df.columns)
        return _empty_mgi_result()
    mp_vocab = vocab_df.select(
        pl.col(vocab_df.columns[0]).alias("mp_term_id"),
        pl.col(vocab_df.columns[1]).alias("mp_term_name"),
    )

    # --- Gene -> MP IDs from the homology/phenotype report ---
    hmd_content = _download_text(MGI_HMD_PHENOTYPE_URL)
    if not hmd_content.strip():
        logger.warning("mgi_hmd_empty")
        return _empty_mgi_result()
    hmd_df = pl.read_csv(
        io.StringIO(hmd_content),
        separator="\t",
        has_header=False,
        truncate_ragged_lines=True,
        infer_schema_length=0,
    )
    # Column 3 (index 2) = mouse symbol, column 5 (index 4) = comma-separated MP IDs
    if hmd_df.width < 5:
        logger.warning("mgi_hmd_parse_failed", columns=hmd_df.columns)
        return _empty_mgi_result()

    result = (
        hmd_df
        .select(
            pl.col(hmd_df.columns[2]).alias("mouse_gene"),
            pl.col(hmd_df.columns[4]).alias("mp_ids"),
        )
        .filter(
            pl.col("mouse_gene").is_in(mouse_gene_symbols)
            & pl.col("mp_ids").is_not_null()
        )
        # One MP ID per row (HMD lists them comma-separated)
        .with_columns(pl.col("mp_ids").str.split(",").alias("mp_term_id"))
        .explode("mp_term_id")
        .with_columns(pl.col("mp_term_id").str.strip_chars())
        .filter(pl.col("mp_term_id").str.starts_with("MP:"))
        .select("mouse_gene", "mp_term_id")
        .unique()
        # Attach human-readable term names for keyword filtering downstream
        .join(mp_vocab, on="mp_term_id", how="left")
    )

    logger.info(
        "fetch_mgi_phenotypes_complete",
        phenotype_count=len(result),
        genes=result["mouse_gene"].n_unique(),
    )

    return result


def _empty_zfin_result() -> pl.DataFrame:
    """Return an empty ZFIN phenotype DataFrame with the expected schema."""
    return pl.DataFrame(
        schema={
            "zebrafish_gene": pl.String,
            "zp_term_id": pl.String,
            "zp_term_name": pl.String,
        }
    )


def fetch_zfin_phenotypes(zebrafish_gene_symbols: list[str]) -> pl.DataFrame:
    """Fetch zebrafish phenotype data from ZFIN.

    Downloads ZFIN phenoGeneCleanData_fish.txt, a headerless tab-delimited
    file. Relevant 1-indexed columns:
    - 2  Gene Symbol
    - 5  Affected Structure or Process 1 subterm Name
    - 8  Affected Structure or Process 1 superterm ID
    - 9  Affected Structure or Process 1 superterm Name
    - 11 Phenotype Keyword Name
    - 12 Phenotype Tag (abnormal/normal)
    - 14 Affected Structure or Process 2 subterm Name
    - 18 Affected Structure or Process 2 superterm Name

    The affected-structure names are concatenated into ``zp_term_name`` so
    downstream keyword filtering can match anatomical terms (retina, ear, ...).

    Args:
        zebrafish_gene_symbols: List of zebrafish gene symbols

    Returns:
        DataFrame with columns:
        - zebrafish_gene: Zebrafish gene symbol
        - zp_term_id: Zebrafish anatomy (ZFA) superterm ID
        - zp_term_name: Concatenated affected-structure / phenotype term names
    """
    if not zebrafish_gene_symbols:
        logger.info("fetch_zfin_phenotypes_skip", reason="no_zebrafish_genes")
        return _empty_zfin_result()

    logger.info("fetch_zfin_phenotypes_start", gene_count=len(zebrafish_gene_symbols))

    # Download ZFIN phenotype data (headerless TSV)
    content = _download_text(ZFIN_PHENO_URL)

    df = pl.read_csv(
        io.StringIO(content),
        separator="\t",
        null_values=["", "NA"],
        has_header=False,
        truncate_ragged_lines=True,
        infer_schema_length=0,
    )

    # phenoGeneCleanData_fish.txt has 25+ columns; we need up to column 18
    if df.width < 12:
        logger.warning("zfin_parse_failed", width=df.width)
        return _empty_zfin_result()

    cols = df.columns

    def _col(idx_1based: int):
        """Column expression by 1-based index, or empty string if absent."""
        i = idx_1based - 1
        if i < len(cols):
            return pl.col(cols[i]).fill_null("")
        return pl.lit("")

    # Affected-structure name columns used for keyword matching
    name_parts = [_col(5), _col(9), _col(14), _col(18), _col(11)]

    result = (
        df
        .select(
            pl.col(cols[1]).alias("zebrafish_gene"),
            _col(8).alias("zp_term_id"),
            pl.concat_str(name_parts, separator=" ", ignore_nulls=True)
            .str.strip_chars()
            .alias("zp_term_name"),
            _col(12).str.to_lowercase().alias("_tag"),
        )
        .filter(
            pl.col("zebrafish_gene").is_in(zebrafish_gene_symbols)
            # Keep abnormal phenotype annotations only
            & (pl.col("_tag") == "abnormal")
            & (pl.col("zp_term_name").str.len_chars() > 0)
        )
        .select("zebrafish_gene", "zp_term_id", "zp_term_name")
        .unique()
    )

    logger.info(
        "fetch_zfin_phenotypes_complete",
        phenotype_count=len(result),
        genes=result["zebrafish_gene"].n_unique(),
    )

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

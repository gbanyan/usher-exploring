"""Download and parse HPA subcellular localization and cilia proteomics data."""

import io
import zipfile
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

from usher_pipeline.evidence.localization.models import HPA_SUBCELLULAR_URL

logger = structlog.get_logger()


# Curated reference gene sets from published proteomics studies
# CiliaCarta: comprehensive cilium proteome database
# Source: van Dam et al. (2019) PLoS ONE, Arnaiz et al. (2014) PNAS
CILIA_PROTEOMICS_GENES = {
    "BBS1", "BBS2", "BBS4", "BBS5", "BBS7", "BBS9", "BBS10", "BBS12",
    "CEP290", "CEP164", "CEP120", "RPGRIP1L", "TCTN1", "TCTN2", "TCTN3",
    "IFT88", "IFT81", "IFT140", "IFT172", "IFT80", "IFT52", "IFT57",
    "DYNC2H1", "DYNC2LI1", "WDR34", "WDR60", "TCTEX1D2",
    "NPHP1", "NPHP4", "INVS", "ANKS6", "NEK8",
    "ARL13B", "INPP5E", "CEP41", "TMEM67", "TMEM216", "TMEM231", "TMEM237",
    "MKS1", "TMEM17", "CC2D2A", "AHI1", "RPGRIP1", "NPHP3",
    "OFD1", "C5orf42", "CSPP1", "C2CD3", "CEP83", "SCLT1",
    "KIF7", "GLI2", "GLI3", "SUFU", "GPR161",
    "TALPID3", "B9D1", "B9D2", "MKS1", "TCTN2",
    "KIAA0586", "NEK1", "DZIP1", "DZIP1L", "FUZ",
    "POC5", "POC1B", "CEP135", "CEP152", "CEP192",
    "ALMS1", "TTC21B", "IFT122", "IFT144", "WDR19", "WDR35",
    "SPAG1", "RSPH1", "RSPH4A", "RSPH9", "DNAH5", "DNAH11", "DNAI1", "DNAI2",
    "C21orf59", "CCDC39", "CCDC40", "CCDC65", "CCDC103", "CCDC114",
    "DRC1", "ARMC4", "TTC25", "ZMYND10", "LRRC6", "PIH1D3",
    "HYDIN", "SPEF2", "CFAP43", "CFAP44", "CFAP53", "CFAP54",
}

# Centrosome proteome database genes
# Source: Firat-Karalar & Stearns (2014), Andersen et al. (2003) MCP
CENTROSOME_PROTEOMICS_GENES = {
    "PCNT", "CDK5RAP2", "CEP192", "CEP152", "CEP135", "CEP120",
    "TUBG1", "TUBG2", "TUBGCP2", "TUBGCP3", "TUBGCP4", "TUBGCP5", "TUBGCP6",
    "NEDD1", "AKAP9", "NINL", "NIN",
    "CEP170", "CEP170B", "CEP131", "CEP63", "CEP72", "CEP97",
    "PLK1", "PLK4", "AURKA", "AURKB",
    "SASS6", "CENPJ", "STIL", "SAS6", "CEP152",
    "POC5", "POC1A", "POC1B", "CPAP", "CEP135",
    "CEP295", "OFD1", "C2CD3", "CCDC14", "CCDC67", "CCDC120",
    "KIAA0753", "SSX2IP", "CEP89", "CEP104", "CEP112", "CEP128",
    "CP110", "CCDC67", "CEP97", "CNTROB", "CETN2", "CETN3",
}


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def download_hpa_subcellular(
    output_path: Path,
    url: str = HPA_SUBCELLULAR_URL,
    force: bool = False,
) -> Path:
    """Download HPA subcellular location data with retry and streaming.

    Downloads the HPA subcellular_location.tsv.zip file, extracts the TSV,
    and saves it to the output path.

    Args:
        output_path: Where to save the TSV file
        url: HPA subcellular location URL (default: official bulk download)
        force: If True, re-download even if file exists

    Returns:
        Path to the downloaded TSV file

    Raises:
        httpx.HTTPStatusError: On HTTP errors (after retries)
        httpx.ConnectError: On connection errors (after retries)
        httpx.TimeoutException: On timeout (after retries)
    """
    output_path = Path(output_path)

    # Checkpoint pattern: skip if already downloaded
    if output_path.exists() and not force:
        logger.info(
            "hpa_subcellular_exists",
            path=str(output_path),
            size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
        )
        return output_path

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("hpa_download_start", url=url)

    # Stream download to memory (HPA file is ~10MB compressed)
    with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as response:
        response.raise_for_status()

        # Read zip content into memory
        zip_content = response.read()

    logger.info("hpa_download_complete", size_mb=round(len(zip_content) / 1024 / 1024, 2))

    # Extract TSV from zip
    logger.info("hpa_extract_start")
    with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
        # Find the TSV file (should be subcellular_location.tsv)
        tsv_files = [f for f in zf.namelist() if f.endswith(".tsv")]
        if not tsv_files:
            raise ValueError(f"No TSV file found in HPA zip: {zf.namelist()}")

        tsv_filename = tsv_files[0]
        logger.info("hpa_extract_file", filename=tsv_filename)

        # Extract to output path
        with zf.open(tsv_filename) as tsv_file:
            with open(output_path, "wb") as f:
                f.write(tsv_file.read())

    logger.info(
        "hpa_extract_complete",
        path=str(output_path),
        size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
    )

    return output_path


def fetch_hpa_subcellular(
    gene_ids: list[str],
    gene_symbol_map: pl.DataFrame,
    cache_dir: Optional[Path] = None,
    force: bool = False,
) -> pl.DataFrame:
    """Fetch HPA subcellular localization data for genes.

    Downloads HPA subcellular location data, parses it, and filters to the
    input gene list. Maps gene symbols to gene IDs using the provided mapping.

    Args:
        gene_ids: List of Ensembl gene IDs to fetch
        gene_symbol_map: DataFrame with gene_id and gene_symbol columns
        cache_dir: Directory to cache HPA download (default: data/localization)
        force: If True, re-download HPA data

    Returns:
        DataFrame with columns:
        - gene_id: Ensembl gene ID
        - gene_symbol: HGNC symbol
        - hpa_main_location: Semicolon-separated location string
        - hpa_reliability: Reliability level
    """
    # Default cache location
    if cache_dir is None:
        cache_dir = Path("data/localization")

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    tsv_path = cache_dir / "hpa_subcellular_location.tsv"

    # Download HPA data
    logger.info("fetch_hpa_start", gene_count=len(gene_ids))
    tsv_path = download_hpa_subcellular(tsv_path, force=force)

    # Parse TSV with polars
    logger.info("hpa_parse_start", path=str(tsv_path))
    df = pl.scan_csv(
        tsv_path,
        separator="\t",
        null_values=["", "NA"],
        has_header=True,
    )

    # Extract relevant columns
    # HPA columns: Gene, Gene name, Reliability, Main location, Additional location, Extracellular location, ...
    df = df.select([
        pl.col("Gene name").alias("gene_symbol"),  # HGNC symbol
        pl.col("Reliability").alias("hpa_reliability"),
        pl.col("Main location").alias("main_location"),
        pl.col("Additional location").alias("additional_location"),
        pl.col("Extracellular location").alias("extracellular_location"),
    ])

    # Combine all locations into one field (semicolon-separated)
    df = df.with_columns([
        pl.concat_str(
            [
                pl.col("main_location").fill_null(""),
                pl.col("additional_location").fill_null(""),
                pl.col("extracellular_location").fill_null(""),
            ],
            separator=";",
        )
        .str.replace_all(";;+", ";")  # Remove multiple semicolons
        .str.strip_chars(";")  # Remove leading/trailing semicolons
        .alias("hpa_main_location")
    ])

    # Select final columns
    df = df.select([
        pl.col("gene_symbol"),
        pl.col("hpa_reliability"),
        pl.col("hpa_main_location"),
    ])

    # Collect to DataFrame
    df = df.collect()

    logger.info("hpa_parse_complete", row_count=len(df))

    # Map gene symbols to gene IDs
    logger.info("hpa_map_gene_ids")
    df = df.join(
        gene_symbol_map.select(["gene_id", "gene_symbol"]),
        on="gene_symbol",
        how="inner",
    )

    # Filter to requested gene_ids
    gene_ids_set = set(gene_ids)
    df = df.filter(pl.col("gene_id").is_in(gene_ids_set))

    logger.info("hpa_filter_complete", row_count=len(df))

    return df


def fetch_cilia_proteomics(
    gene_ids: list[str],
    gene_symbol_map: pl.DataFrame,
) -> pl.DataFrame:
    """Cross-reference genes against curated cilia/centrosome proteomics datasets.

    Uses embedded gene sets from published studies (CiliaCarta, Centrosome-DB).
    Genes not found in datasets are marked as False (not NULL), since absence
    from proteomics is informative (not detected vs. not tested).

    Args:
        gene_ids: List of Ensembl gene IDs to check
        gene_symbol_map: DataFrame with gene_id and gene_symbol columns

    Returns:
        DataFrame with columns:
        - gene_id: Ensembl gene ID
        - gene_symbol: HGNC symbol
        - in_cilia_proteomics: bool (True if in CiliaCarta, False otherwise)
        - in_centrosome_proteomics: bool (True if in Centrosome-DB, False otherwise)
    """
    logger.info(
        "fetch_proteomics_start",
        gene_count=len(gene_ids),
        cilia_ref_count=len(CILIA_PROTEOMICS_GENES),
        centrosome_ref_count=len(CENTROSOME_PROTEOMICS_GENES),
    )

    # Filter gene symbol map to requested gene_ids
    gene_ids_set = set(gene_ids)
    df = gene_symbol_map.filter(pl.col("gene_id").is_in(gene_ids_set))

    # Check membership in proteomics datasets
    df = df.with_columns([
        pl.col("gene_symbol").is_in(CILIA_PROTEOMICS_GENES).alias("in_cilia_proteomics"),
        pl.col("gene_symbol").is_in(CENTROSOME_PROTEOMICS_GENES).alias("in_centrosome_proteomics"),
    ])

    logger.info(
        "fetch_proteomics_complete",
        cilia_hits=df.filter(pl.col("in_cilia_proteomics")).height,
        centrosome_hits=df.filter(pl.col("in_centrosome_proteomics")).height,
    )

    return df.select(["gene_id", "gene_symbol", "in_cilia_proteomics", "in_centrosome_proteomics"])

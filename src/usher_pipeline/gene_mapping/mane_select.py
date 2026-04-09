"""Fetch and parse NCBI MANE Select canonical transcript mappings."""

import gzip
import shutil
from pathlib import Path

import httpx
import polars as pl
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from usher_pipeline.persistence.duckdb_store import PipelineStore

logger = structlog.get_logger(__name__)

MANE_SELECT_URL_TEMPLATE = (
    "https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/"
    "release_{version}/MANE.GRCh38.v{version}.summary.txt.gz"
)


def _strip_ensembl_version(col: pl.Expr) -> pl.Expr:
    """Strip version suffix from Ensembl IDs (ENSG00000163646.18 -> ENSG00000163646)."""
    return col.str.replace(r"\.\d+$", "")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def fetch_mane_select(
    data_dir: Path,
    version: str = "1.3",
    force: bool = False,
) -> Path:
    """Download MANE Select summary from NCBI FTP.

    Args:
        data_dir: Directory to save the downloaded file.
        version: MANE release version (default: 1.3).
        force: Re-download even if file exists.

    Returns:
        Path to the downloaded gzipped TSV file.
    """
    data_dir = Path(data_dir)
    gz_path = data_dir / f"MANE.GRCh38.v{version}.summary.txt.gz"

    if gz_path.exists() and not force:
        logger.info("mane_select_exists", path=str(gz_path))
        return gz_path

    data_dir.mkdir(parents=True, exist_ok=True)
    url = MANE_SELECT_URL_TEMPLATE.format(version=version)
    temp_path = gz_path.with_suffix(".tmp")

    logger.info("mane_select_download_start", url=url)

    with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as response:
        response.raise_for_status()
        with open(temp_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)

    temp_path.rename(gz_path)
    logger.info(
        "mane_select_download_complete",
        path=str(gz_path),
        size_kb=round(gz_path.stat().st_size / 1024, 1),
    )
    return gz_path


def parse_mane_select(gz_path: Path) -> pl.DataFrame:
    """Parse MANE Select summary TSV into a DataFrame.

    Reads the gzipped TSV, selects relevant columns, and strips
    version suffixes from Ensembl gene/transcript IDs so they
    match gene_universe.gene_id format.

    Args:
        gz_path: Path to gzipped MANE summary TSV.

    Returns:
        DataFrame with columns: ensembl_gene_id, ensembl_transcript_id,
        gene_symbol, refseq_transcript_id, mane_status.
    """
    df = pl.read_csv(
        gz_path,
        separator="\t",
        comment_prefix="##",
    )

    # The header line starts with '#NCBI_GeneID' — rename to strip the '#'
    if "#NCBI_GeneID" in df.columns:
        df = df.rename({"#NCBI_GeneID": "NCBI_GeneID"})

    df = df.select(
        _strip_ensembl_version(pl.col("Ensembl_Gene")).alias("ensembl_gene_id"),
        _strip_ensembl_version(pl.col("Ensembl_nuc")).alias("ensembl_transcript_id"),
        pl.col("symbol").alias("gene_symbol"),
        pl.col("RefSeq_nuc").alias("refseq_transcript_id"),
        pl.col("MANE_status").alias("mane_status"),
    )

    logger.info(
        "mane_select_parsed",
        total_rows=df.height,
        mane_select_count=df.filter(pl.col("mane_status") == "MANE Select").height,
        mane_plus_clinical_count=df.filter(
            pl.col("mane_status") == "MANE Plus Clinical"
        ).height,
    )
    return df


def load_mane_select(store: PipelineStore, df: pl.DataFrame) -> None:
    """Save MANE Select DataFrame to DuckDB.

    Args:
        store: PipelineStore instance.
        df: DataFrame from parse_mane_select().
    """
    store.save_dataframe(
        df=df,
        table_name="mane_select",
        description="NCBI MANE Select canonical transcript mappings",
        replace=True,
    )
    logger.info("mane_select_loaded", row_count=df.height)

"""Download and parse gnomAD constraint metrics."""

import gzip
import shutil
from pathlib import Path

import httpx
import polars as pl
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from usher_pipeline.evidence.gnomad.models import (
    GNOMAD_CONSTRAINT_URL,
    COLUMN_VARIANTS,
)

logger = structlog.get_logger()


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def download_constraint_metrics(
    output_path: Path,
    url: str = GNOMAD_CONSTRAINT_URL,
    force: bool = False,
) -> Path:
    """Download gnomAD constraint metrics file with retry and streaming.

    Args:
        output_path: Where to save the TSV file
        url: gnomAD constraint file URL (default: v4.1)
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
            "gnomad_constraint_exists",
            path=str(output_path),
            size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
        )
        return output_path

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine if we need to decompress
    is_compressed = url.endswith(".bgz") or url.endswith(".gz")
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    logger.info("gnomad_download_start", url=url, compressed=is_compressed)

    # Stream download to disk (avoid loading into memory)
    with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as response:
        response.raise_for_status()

        total_bytes = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(temp_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)

                # Log progress every 10MB
                if total_bytes > 0 and downloaded % (10 * 1024 * 1024) < 8192:
                    pct = (downloaded / total_bytes) * 100
                    logger.info(
                        "gnomad_download_progress",
                        downloaded_mb=round(downloaded / 1024 / 1024, 2),
                        total_mb=round(total_bytes / 1024 / 1024, 2),
                        percent=round(pct, 1),
                    )

    # Decompress if needed (bgzip is gzip-compatible)
    if is_compressed:
        logger.info("gnomad_decompress_start", compressed_path=str(temp_path))
        with gzip.open(temp_path, "rb") as f_in:
            with open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        temp_path.unlink()
    else:
        temp_path.rename(output_path)

    logger.info(
        "gnomad_download_complete",
        path=str(output_path),
        size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
    )

    return output_path


def parse_constraint_tsv(tsv_path: Path) -> pl.LazyFrame:
    """Parse gnomAD constraint TSV into a LazyFrame.

    Handles column name variants between gnomAD v2.1.1 and v4.x.
    Null values ("NA", "", ".") are preserved as polars null.

    Args:
        tsv_path: Path to gnomAD constraint TSV file

    Returns:
        LazyFrame with standardized column names matching ConstraintRecord fields
    """
    tsv_path = Path(tsv_path)

    # Read first line to detect actual column names
    with open(tsv_path, "r") as f:
        header_line = f.readline().strip()
        actual_columns = header_line.split("\t")

    logger.info(
        "gnomad_parse_start",
        path=str(tsv_path),
        column_count=len(actual_columns),
    )

    # Scan with lazy evaluation
    lf = pl.scan_csv(
        tsv_path,
        separator="\t",
        null_values=["NA", "", "."],
        has_header=True,
    )

    # Map actual columns to our standardized names
    column_mapping = {}
    for our_name, variants in COLUMN_VARIANTS.items():
        for variant in variants:
            if variant in actual_columns:
                column_mapping[variant] = our_name
                break

    if not column_mapping:
        logger.warning(
            "gnomad_no_column_matches",
            actual_columns=actual_columns[:10],  # Log first 10 for debugging
        )
        # Return as-is if we can't map columns
        return lf

    logger.info("gnomad_column_mapping", mapping=column_mapping)

    # Select and rename mapped columns
    lf = lf.select([pl.col(old).alias(new) for old, new in column_mapping.items()])

    return lf

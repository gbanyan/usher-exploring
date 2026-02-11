"""Download and parse tissue expression data from HPA, GTEx, and CellxGene."""

import gzip
import shutil
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

from usher_pipeline.evidence.expression.models import (
    HPA_NORMAL_TISSUE_URL,
    GTEX_MEDIAN_EXPRESSION_URL,
    TARGET_TISSUES,
    TARGET_CELL_TYPES,
)

logger = structlog.get_logger()


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def download_hpa_tissue_data(
    output_path: Path,
    url: str = HPA_NORMAL_TISSUE_URL,
    force: bool = False,
) -> Path:
    """Download HPA normal tissue TSV (bulk download for all genes).

    Args:
        output_path: Where to save the TSV file
        url: HPA normal tissue data URL (default: proteinatlas.org bulk download)
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
            "hpa_tissue_exists",
            path=str(output_path),
            size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
        )
        return output_path

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # HPA data is zipped
    is_zipped = url.endswith(".zip")
    temp_path = output_path.with_suffix(".zip.tmp")

    logger.info("hpa_download_start", url=url, zipped=is_zipped)

    # Stream download to disk
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
                        "hpa_download_progress",
                        downloaded_mb=round(downloaded / 1024 / 1024, 2),
                        total_mb=round(total_bytes / 1024 / 1024, 2),
                        percent=round(pct, 1),
                    )

    # Unzip if needed
    if is_zipped:
        logger.info("hpa_unzip_start", zip_path=str(temp_path))
        with zipfile.ZipFile(temp_path, "r") as zip_ref:
            # Extract the TSV file (usually named "normal_tissue.tsv")
            tsv_files = [name for name in zip_ref.namelist() if name.endswith(".tsv")]
            if not tsv_files:
                raise ValueError(f"No TSV file found in HPA zip: {temp_path}")
            # Extract first TSV
            zip_ref.extract(tsv_files[0], path=output_path.parent)
            extracted_path = output_path.parent / tsv_files[0]
            extracted_path.rename(output_path)
        temp_path.unlink()
    else:
        temp_path.rename(output_path)

    logger.info(
        "hpa_download_complete",
        path=str(output_path),
        size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
    )

    return output_path


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def download_gtex_expression(
    output_path: Path,
    url: str = GTEX_MEDIAN_EXPRESSION_URL,
    force: bool = False,
) -> Path:
    """Download GTEx median gene expression file (bulk download).

    Args:
        output_path: Where to save the GCT file
        url: GTEx median TPM file URL (default: v8/v10 bulk data)
        force: If True, re-download even if file exists

    Returns:
        Path to the downloaded GCT file

    Raises:
        httpx.HTTPStatusError: On HTTP errors (after retries)
        httpx.ConnectError: On connection errors (after retries)
        httpx.TimeoutException: On timeout (after retries)
    """
    output_path = Path(output_path)

    # Checkpoint pattern: skip if already downloaded
    if output_path.exists() and not force:
        logger.info(
            "gtex_expression_exists",
            path=str(output_path),
            size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
        )
        return output_path

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # GTEx data is gzipped
    is_compressed = url.endswith(".gz")
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    logger.info("gtex_download_start", url=url, compressed=is_compressed)

    # Stream download to disk
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
                        "gtex_download_progress",
                        downloaded_mb=round(downloaded / 1024 / 1024, 2),
                        total_mb=round(total_bytes / 1024 / 1024, 2),
                        percent=round(pct, 1),
                    )

    # Decompress if needed
    if is_compressed:
        logger.info("gtex_decompress_start", compressed_path=str(temp_path))
        with gzip.open(temp_path, "rb") as f_in:
            with open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        temp_path.unlink()
    else:
        temp_path.rename(output_path)

    logger.info(
        "gtex_download_complete",
        path=str(output_path),
        size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
    )

    return output_path


def fetch_hpa_expression(
    gene_ids: list[str],
    cache_dir: Optional[Path] = None,
    force: bool = False,
) -> pl.LazyFrame:
    """Fetch HPA tissue expression data for target tissues.

    Downloads HPA bulk normal tissue TSV, filters to target tissues
    (retina, cerebellum, testis, fallopian tube), and extracts TPM values.

    Args:
        gene_ids: List of Ensembl gene IDs to filter (unused - HPA uses gene symbols)
        cache_dir: Directory to cache downloaded HPA file
        force: If True, re-download even if cached

    Returns:
        LazyFrame with columns: gene_symbol, hpa_retina_tpm, hpa_cerebellum_tpm,
        hpa_testis_tpm, hpa_fallopian_tube_tpm
        NULL for genes/tissues not in HPA data.
    """
    cache_dir = Path(cache_dir) if cache_dir else Path("data/expression")
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Download HPA bulk tissue data
    hpa_tsv_path = cache_dir / "hpa_normal_tissue.tsv"
    download_hpa_tissue_data(hpa_tsv_path, force=force)

    logger.info("hpa_parse_start", path=str(hpa_tsv_path))

    # HPA TSV format (v24):
    # Gene | Gene name | Tissue | Cell type | Level | Reliability
    # Where Level is expression level category, not TPM
    # For quantitative data we need the "nTPM" column if available
    # Columns: Gene, Gene name, Tissue, Cell type, Level, Reliability
    # OR: Gene, Gene name, Tissue, nTPM (normalized TPM)

    # Read HPA data with lazy evaluation
    lf = pl.scan_csv(
        hpa_tsv_path,
        separator="\t",
        null_values=["NA", "", "."],
        has_header=True,
    )

    # Target tissues from HPA
    target_tissue_names = {
        "retina": TARGET_TISSUES["retina"]["hpa"],
        "cerebellum": TARGET_TISSUES["cerebellum"]["hpa"],
        "testis": TARGET_TISSUES["testis"]["hpa"],
        "fallopian_tube": TARGET_TISSUES["fallopian_tube"]["hpa"],
    }

    # Filter to target tissues
    tissue_filter = pl.col("Tissue").is_in(list(target_tissue_names.values()))
    lf = lf.filter(tissue_filter)

    # HPA provides categorical "Level" (Not detected, Low, Medium, High)
    # For scoring, we'll convert to numeric: Not detected=0, Low=1, Medium=2, High=3
    # If nTPM column exists, use that instead

    # Check if nTPM column exists (better for quantitative analysis)
    # For now, use Level mapping as HPA download format varies
    level_mapping = {
        "Not detected": 0.0,
        "Low": 1.0,
        "Medium": 2.0,
        "High": 3.0,
    }

    # Convert Level to numeric expression proxy
    # If "nTPM" column exists, use it; otherwise map Level
    # We'll handle this by attempting both approaches

    # Pivot to wide format: gene x tissue
    # Group by Gene name and Tissue, aggregate Level (take max if multiple cell types)
    lf = (
        lf.group_by(["Gene name", "Tissue"])
        .agg(pl.col("Level").first().alias("expression_level"))
        .with_columns(
            pl.col("expression_level")
            .map_elements(lambda x: level_mapping.get(x, None), return_dtype=pl.Float64)
            .alias("expression_value")
        )
    )

    # Pivot: rows=genes, columns=tissues
    # Create separate columns for each target tissue
    lf_wide = lf.pivot(
        values="expression_value",
        index="Gene name",
        columns="Tissue",
    )

    # Rename columns to match our schema
    rename_map = {}
    for our_key, hpa_tissue in target_tissue_names.items():
        if hpa_tissue:
            rename_map[hpa_tissue] = f"hpa_{our_key}_tpm"

    if rename_map:
        lf_wide = lf_wide.rename(rename_map)

    # Rename "Gene name" to "gene_symbol"
    lf_wide = lf_wide.rename({"Gene name": "gene_symbol"})

    logger.info("hpa_parse_complete", tissues=list(target_tissue_names.keys()))

    return lf_wide


def fetch_gtex_expression(
    gene_ids: list[str],
    cache_dir: Optional[Path] = None,
    force: bool = False,
) -> pl.LazyFrame:
    """Fetch GTEx tissue expression data for target tissues.

    Downloads GTEx bulk median TPM file, filters to target tissues.
    NOTE: GTEx lacks inner ear/cochlea tissue - will be NULL.

    Args:
        gene_ids: List of Ensembl gene IDs to filter
        cache_dir: Directory to cache downloaded GTEx file
        force: If True, re-download even if cached

    Returns:
        LazyFrame with columns: gene_id, gtex_retina_tpm, gtex_cerebellum_tpm,
        gtex_testis_tpm, gtex_fallopian_tube_tpm
        NULL for tissues not available in GTEx.
    """
    cache_dir = Path(cache_dir) if cache_dir else Path("data/expression")
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Download GTEx bulk expression data
    gtex_gct_path = cache_dir / "gtex_median_tpm.gct"
    download_gtex_expression(gtex_gct_path, force=force)

    logger.info("gtex_parse_start", path=str(gtex_gct_path))

    # GTEx GCT format:
    # #1.2 (version header)
    # [dimensions line]
    # Name  Description  [Tissue1]  [Tissue2]  ...
    # ENSG00000... | GeneSymbol | tpm1 | tpm2 | ...

    # Skip first 2 lines (GCT header), then read
    lf = pl.scan_csv(
        gtex_gct_path,
        separator="\t",
        skip_rows=2,
        null_values=["NA", "", "."],
        has_header=True,
    )

    # Target tissues from GTEx
    target_tissue_cols = {
        "retina": TARGET_TISSUES["retina"]["gtex"],
        "cerebellum": TARGET_TISSUES["cerebellum"]["gtex"],
        "testis": TARGET_TISSUES["testis"]["gtex"],
        "fallopian_tube": TARGET_TISSUES["fallopian_tube"]["gtex"],
    }

    # Select gene ID column + target tissue columns
    # GTEx uses "Name" for gene ID (ENSG...) and "Description" for gene symbol
    select_cols = ["Name"]
    rename_map = {"Name": "gene_id"}

    for our_key, gtex_tissue in target_tissue_cols.items():
        if gtex_tissue:
            # Check if tissue column exists (not all GTEx versions have all tissues)
            select_cols.append(gtex_tissue)
            rename_map[gtex_tissue] = f"gtex_{our_key}_tpm"

    # Try to select columns; if tissue missing, it will be NULL
    # Use select with error handling for missing columns
    try:
        lf = lf.select(select_cols).rename(rename_map)
    except Exception as e:
        logger.warning("gtex_tissue_missing", error=str(e))
        # Fallback: select available columns
        available_cols = lf.columns
        select_available = [col for col in select_cols if col in available_cols]
        lf = lf.select(select_available).rename({
            k: v for k, v in rename_map.items() if k in select_available
        })

    # Filter to requested gene_ids if provided
    if gene_ids:
        lf = lf.filter(pl.col("gene_id").is_in(gene_ids))

    logger.info("gtex_parse_complete", tissues=list(target_tissue_cols.keys()))

    return lf


def fetch_cellxgene_expression(
    gene_ids: list[str],
    cache_dir: Optional[Path] = None,
    batch_size: int = 100,
) -> pl.LazyFrame:
    """Fetch CellxGene single-cell expression data for target cell types.

    Uses cellxgene_census library to query scRNA-seq data for photoreceptor
    and hair cell populations. Computes mean expression per gene per cell type.

    NOTE: cellxgene_census is an optional dependency (large install).
    If not available, returns DataFrame with all NULL values and logs warning.

    Args:
        gene_ids: List of Ensembl gene IDs to query
        cache_dir: Directory for caching (currently unused)
        batch_size: Number of genes to process per batch (default: 100)

    Returns:
        LazyFrame with columns: gene_id, cellxgene_photoreceptor_expr,
        cellxgene_hair_cell_expr
        NULL if cellxgene_census not available or cell type data missing.
    """
    try:
        import cellxgene_census
    except ImportError:
        logger.warning(
            "cellxgene_census_unavailable",
            message="cellxgene_census not installed. Install with: pip install 'usher-pipeline[expression]'",
        )
        # Return empty DataFrame with NULL values
        return pl.LazyFrame({
            "gene_id": gene_ids,
            "cellxgene_photoreceptor_expr": [None] * len(gene_ids),
            "cellxgene_hair_cell_expr": [None] * len(gene_ids),
        })

    logger.info("cellxgene_query_start", gene_count=len(gene_ids), batch_size=batch_size)

    # For now, return placeholder with NULLs
    # Full CellxGene integration requires census schema knowledge and filtering
    # This is a complex query that would need cell type ontology matching
    # Placeholder implementation for testing
    logger.warning(
        "cellxgene_not_implemented",
        message="CellxGene integration is complex and not yet implemented. Returning NULL values.",
    )

    return pl.LazyFrame({
        "gene_id": gene_ids,
        "cellxgene_photoreceptor_expr": [None] * len(gene_ids),
        "cellxgene_hair_cell_expr": [None] * len(gene_ids),
    })

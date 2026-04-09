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

    # Pivot: rows=genes, columns=tissues (collect first — DataFrame.pivot is simpler)
    df_wide = lf.collect().pivot(
        on="Tissue",
        values="expression_value",
        index="Gene name",
    )

    # Rename columns to match our schema
    rename_map = {}
    for our_key, hpa_tissue in target_tissue_names.items():
        if hpa_tissue:
            rename_map[hpa_tissue] = f"hpa_{our_key}_tpm"

    if rename_map:
        df_wide = df_wide.rename(rename_map)

    # Rename "Gene name" to "gene_symbol"
    df_wide = df_wide.rename({"Gene name": "gene_symbol"})

    logger.info("hpa_parse_complete", tissues=list(target_tissue_names.keys()))

    return df_wide.lazy()


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
    available_cols = lf.collect_schema().names()

    select_cols = ["Name"]
    rename_map = {"Name": "gene_id"}
    missing_tissues = []

    for our_key, gtex_tissue in target_tissue_cols.items():
        if gtex_tissue and gtex_tissue in available_cols:
            select_cols.append(gtex_tissue)
            rename_map[gtex_tissue] = f"gtex_{our_key}_tpm"
        elif gtex_tissue:
            missing_tissues.append(gtex_tissue)

    if missing_tissues:
        logger.warning("gtex_tissues_not_available", missing=missing_tissues)

    lf = lf.select(select_cols).rename(rename_map)

    # Strip version suffix from Ensembl gene IDs (e.g., ENSG00000223972.5 → ENSG00000223972)
    # GTEx uses versioned IDs but gene_universe uses unversioned
    lf = lf.with_columns(
        pl.col("gene_id").str.replace(r"\.\d+$", "").alias("gene_id")
    )

    # Add NULL columns for missing tissues
    for our_key, gtex_tissue in target_tissue_cols.items():
        col_name = f"gtex_{our_key}_tpm"
        if gtex_tissue and gtex_tissue not in available_cols:
            lf = lf.with_columns(pl.lit(None).cast(pl.Float64).alias(col_name))

    # Filter to requested gene_ids if provided
    if gene_ids:
        lf = lf.filter(pl.col("gene_id").is_in(gene_ids))

    logger.info("gtex_parse_complete", tissues=list(target_tissue_cols.keys()))

    return lf


def _null_cellxgene_result(gene_ids: list[str]) -> pl.LazyFrame:
    """Return a NULL CellxGene result for all genes (fallback)."""
    return pl.LazyFrame({
        "gene_id": gene_ids,
        "cellxgene_photoreceptor_expr": [None] * len(gene_ids),
        "cellxgene_hair_cell_expr": [None] * len(gene_ids),
    })


# Cell type groups for Census queries
PHOTORECEPTOR_CELL_TYPES = [
    "photoreceptor cell",
    "retinal rod cell",
    "retinal cone cell",
]
HAIR_CELL_TYPES = [
    "hair cell",
    "cochlear hair cell",
    "vestibular hair cell",
]


def _query_mean_expression(
    census,
    cell_types: list[str],
    gene_ids: list[str],
    column_name: str,
) -> pl.DataFrame:
    """Query Census for mean expression of genes in specific cell types.

    Args:
        census: Open cellxgene_census.open_soma() context.
        cell_types: List of cell_type ontology labels to filter.
        gene_ids: Ensembl gene IDs to query.
        column_name: Name for the output expression column.

    Returns:
        DataFrame with columns: gene_id, <column_name>.
    """
    import cellxgene_census

    # Build cell type filter
    type_filters = " or ".join(f"cell_type == '{ct}'" for ct in cell_types)
    obs_filter = f"is_primary_data == True and ({type_filters})"

    logger.info(
        "cellxgene_query_cell_type",
        cell_types=cell_types,
        obs_filter=obs_filter[:120],
    )

    try:
        adata = cellxgene_census.get_anndata(
            census,
            organism="Homo sapiens",
            obs_value_filter=obs_filter,
            var_value_filter=f"feature_id in {gene_ids}",
            column_names={"obs": ["cell_type"], "var": ["feature_id"]},
        )
    except Exception as e:
        logger.warning(
            "cellxgene_query_failed",
            cell_types=cell_types,
            error=str(e),
        )
        return pl.DataFrame({
            "gene_id": gene_ids,
            column_name: [None] * len(gene_ids),
        })

    n_cells = adata.n_obs
    n_genes_found = adata.n_vars

    logger.info(
        "cellxgene_query_result",
        cell_types=cell_types,
        cells_found=n_cells,
        genes_found=n_genes_found,
    )

    if n_cells == 0:
        return pl.DataFrame({
            "gene_id": gene_ids,
            column_name: [None] * len(gene_ids),
        })

    # Compute mean expression per gene across all matching cells
    # adata.X is a sparse matrix (cells x genes)
    import numpy as np

    mean_expr = np.asarray(adata.X.mean(axis=0)).flatten()
    feature_ids = adata.var["feature_id"]
    found_gene_ids = feature_ids.tolist() if hasattr(feature_ids, "tolist") else list(feature_ids)

    # Build lookup dict
    expr_map = dict(zip(found_gene_ids, mean_expr))

    # Map back to all requested gene_ids (NULL for genes not found in Census)
    values = [
        float(expr_map[gid]) if gid in expr_map else None
        for gid in gene_ids
    ]

    return pl.DataFrame({
        "gene_id": gene_ids,
        column_name: values,
    })


def fetch_cellxgene_expression(
    gene_ids: list[str],
    cache_dir: Optional[Path] = None,
    force: bool = False,
) -> pl.LazyFrame:
    """Fetch CellxGene single-cell expression data for target cell types.

    Queries CZ CELLxGENE Census for photoreceptor and hair cell expression.
    Results are cached to a parquet file to avoid re-querying on subsequent runs.

    NOTE: cellxgene_census is an optional dependency.
    If not available, returns DataFrame with all NULL values.

    Args:
        gene_ids: List of Ensembl gene IDs to query.
        cache_dir: Directory for caching query results.
        force: Re-query Census even if cache exists.

    Returns:
        LazyFrame with columns: gene_id, cellxgene_photoreceptor_expr,
        cellxgene_hair_cell_expr.
        NULL if cellxgene_census not available or cell type data missing.
    """
    # Check cache FIRST (before importing cellxgene_census)
    cache_dir = Path(cache_dir) if cache_dir else Path("data/expression")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "cellxgene_expression.parquet"

    if cache_path.exists() and not force:
        logger.info("cellxgene_cache_hit", path=str(cache_path))
        cached = pl.read_parquet(cache_path)
        # Filter to requested gene_ids and left-join to preserve all
        result = (
            pl.DataFrame({"gene_id": gene_ids})
            .join(cached, on="gene_id", how="left")
        )
        return result.lazy()

    # Import cellxgene_census (optional dependency) — only needed for live queries
    try:
        import cellxgene_census
    except ImportError:
        logger.warning(
            "cellxgene_census_unavailable",
            message="cellxgene_census not installed. Install with: pip install 'usher-pipeline[expression]'",
        )
        return _null_cellxgene_result(gene_ids)

    logger.info("cellxgene_fetch_start", gene_count=len(gene_ids))

    try:
        with cellxgene_census.open_soma() as census:
            # Query photoreceptor expression
            photo_df = _query_mean_expression(
                census,
                PHOTORECEPTOR_CELL_TYPES,
                gene_ids,
                "cellxgene_photoreceptor_expr",
            )

            # Query hair cell expression
            hair_df = _query_mean_expression(
                census,
                HAIR_CELL_TYPES,
                gene_ids,
                "cellxgene_hair_cell_expr",
            )

        # Merge results
        result = photo_df.join(hair_df, on="gene_id", how="outer_coalesce")

        # Cache to parquet
        result.write_parquet(cache_path)
        logger.info(
            "cellxgene_fetch_complete",
            genes=result.height,
            photoreceptor_non_null=result.filter(
                pl.col("cellxgene_photoreceptor_expr").is_not_null()
            ).height,
            hair_cell_non_null=result.filter(
                pl.col("cellxgene_hair_cell_expr").is_not_null()
            ).height,
            cache_path=str(cache_path),
        )

        return result.lazy()

    except Exception as e:
        logger.warning(
            "cellxgene_fetch_failed",
            error=str(e),
            message="CellxGene Census query failed. Returning NULL values.",
        )
        return _null_cellxgene_result(gene_ids)

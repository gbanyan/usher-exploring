"""Download and parse tissue expression data from HPA, GTEx, and CellxGene."""

import hashlib
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
    CELLXGENE_COLUMNS,
    EXPRESSION_CONTRAST_DESCRIPTION,
    EXPRESSION_CONTRAST_SCOPE,
    EXPRESSION_SCHEMA_VERSION,
    GTEX_STRUCTURAL_ABSENCE,
    GTEX_TPM_COLUMNS,
    HPA_NORMAL_TISSUE_URL,
    HPA_LEVEL_ORDINAL,
    HPA_LEVEL_SEMANTICS,
    HPA_RELIABILITY_POLICY,
    HPA_ORDINAL_LABEL,
    HPA_NTPM_COLUMNS,
    HPA_PROTEIN_LEVEL_COLUMNS,
    HPA_PROTEIN_LEVEL_LABEL_COLUMNS,
    HPA_TISSUE_KEYS,
    GTEX_MEDIAN_EXPRESSION_URL,
    TARGET_TISSUES,
    TARGET_CELL_TYPES,
)

logger = structlog.get_logger()

CELLXGENE_CACHE_COVERAGE = "all_genes"


def cellxgene_cache_identity(
    census_version: str,
    *,
    include_hair_cell: bool = False,
    coverage: str = CELLXGENE_CACHE_COVERAGE,
) -> str:
    """Return the cache identity for a Census query configuration."""
    query_mode = "photoreceptor_hair" if include_hair_cell else "photoreceptor_only"
    return f"{census_version}_{query_mode}_{coverage}"


def cellxgene_cache_path(
    cache_dir: Path,
    census_version: str,
    *,
    include_hair_cell: bool = False,
    coverage: str = CELLXGENE_CACHE_COVERAGE,
) -> Path:
    """Return the mode- and coverage-specific CellxGene cache path."""
    identity = cellxgene_cache_identity(
        census_version,
        include_hair_cell=include_hair_cell,
        coverage=coverage,
    )
    return Path(cache_dir) / f"cellxgene_expression_{identity}.parquet"


def cellxgene_legacy_cache_path(cache_dir: Path, census_version: str) -> Path:
    """Return the pre-v3 baseline cache path.

    The baseline filename had no query-mode field. It is recognized only as
    photoreceptor-only/all-genes data; it is never used for hair-cell queries.
    """
    return Path(cache_dir) / f"cellxgene_expression_{census_version}.parquet"


def _require_cached_file(path: Path, source_name: str) -> Path:
    """Require an existing source cache without creating or downloading it."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"cache-only expression reprocessing requires cached {source_name}: {path}"
        )
    return path


def validate_expression_cache(
    cache_dir: Path,
    *,
    census_version: str,
    require_cellxgene: bool = True,
    include_hair_cell: bool = False,
) -> dict[str, Path]:
    """Preflight all files needed by a cache-only expression rerun.

    This check intentionally happens before any source parser or optional Census
    dependency is invoked, so a missing cache cannot fall through to a network
    download or live query.
    """
    cache_dir = Path(cache_dir)
    required = {
        "HPA": cache_dir / "hpa_normal_tissue.tsv",
        "GTEx": cache_dir / "gtex_median_tpm.gct",
    }
    if require_cellxgene:
        mode_specific_path = cellxgene_cache_path(
            cache_dir,
            census_version,
            include_hair_cell=include_hair_cell,
        )
        if mode_specific_path.is_file():
            required["CellxGene"] = mode_specific_path
        elif not include_hair_cell:
            legacy_path = cellxgene_legacy_cache_path(cache_dir, census_version)
            if legacy_path.is_file():
                required["CellxGene"] = legacy_path
            else:
                required["CellxGene"] = mode_specific_path
        else:
            required["CellxGene"] = mode_specific_path
    missing = [f"{name}: {path}" for name, path in required.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "cache-only expression reprocessing is missing required source caches: "
            + "; ".join(missing)
        )
    return required


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
    cache_only: bool = False,
) -> pl.LazyFrame:
    """Fetch HPA tissue expression data for target tissues.

    Downloads HPA bulk normal tissue TSV, filters to target tissues
    (retina, cerebellum, testis, fallopian tube).  Quantitative HPA
    transcript nTPM is preferred when present.  The local HPA normal-tissue
    source currently contains categorical protein ``Level`` values, which
    are returned as explicitly named ordinal codes and labels.

    Args:
        gene_ids: List of Ensembl gene IDs to filter (unused - HPA uses gene symbols)
        cache_dir: Directory to cache downloaded HPA file
        force: If True, re-download even if cached
        cache_only: If True, require the existing cache and never download

    Returns:
        LazyFrame with HPA nTPM or protein-level columns.  It never returns
        categorical HPA levels under a ``*_tpm`` name.
    """
    cache_dir = Path(cache_dir) if cache_dir else Path("data/expression")

    # Download HPA bulk tissue data
    hpa_tsv_path = cache_dir / "hpa_normal_tissue.tsv"
    if cache_only:
        _require_cached_file(hpa_tsv_path, "HPA normal tissue data")
    else:
        cache_dir.mkdir(parents=True, exist_ok=True)
        download_hpa_tissue_data(hpa_tsv_path, force=force)

    logger.info("hpa_parse_start", path=str(hpa_tsv_path))

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

    source_columns = lf.collect_schema().names()
    ntpm_column = next(
        (column for column in source_columns if column.casefold() == "ntpm"),
        None,
    )
    if "Gene name" not in source_columns or "Tissue" not in source_columns:
        raise ValueError(
            "HPA normal tissue source must contain 'Gene name' and 'Tissue' columns"
        )

    tissue_filter = pl.col("Tissue").is_in(list(target_tissue_names.values()))
    reliability_column = "Reliability" if "Reliability" in source_columns else None
    if reliability_column is None and ntpm_column is None:
        raise ValueError(
            "categorical HPA source must contain 'Reliability' so the "
            "configured policy is applied before cell-type aggregation"
        )
    if reliability_column is not None:
        lf = lf.filter(
            pl.col(reliability_column).is_in(HPA_RELIABILITY_POLICY["accepted"])
        )
    if ntpm_column is not None:
        # nTPM is quantitative transcript expression.  If multiple cell
        # types are reported for a gene/tissue, use their arithmetic mean.
        df = (
            lf.filter(tissue_filter)
            .select(["Gene name", "Tissue", ntpm_column])
            .with_columns(
                pl.col(ntpm_column)
                .cast(pl.Float64, strict=False)
                .alias("_hpa_ntpm")
            )
            .group_by(["Gene name", "Tissue"])
            .agg(pl.col("_hpa_ntpm").mean())
            .collect()
        )
        df_wide = df.pivot(
            on="Tissue",
            values="_hpa_ntpm",
            index="Gene name",
        )
        df_wide = df_wide.rename({
            tissue: f"hpa_{key}_ntpm"
            for key, tissue in target_tissue_names.items()
            if tissue and tissue in df_wide.columns
        })
        measurement_kind = "quantitative_transcript_ntpm"
    else:
        if "Level" not in source_columns:
            raise ValueError(
                "HPA source has neither quantitative nTPM nor categorical Level"
            )

        # Preserve the ordered category as an explicitly ordinal code.  The
        # code is used only for ordering/ranking, never as a TPM quantity.
        df = (
            lf.filter(tissue_filter)
            .select(["Gene name", "Tissue", "Level"])
            .with_columns(
                pl.col("Level")
                .map_elements(
                    lambda value: HPA_LEVEL_ORDINAL.get(value),
                    return_dtype=pl.Int8,
                )
                .alias("_hpa_protein_level")
            )
            .group_by(["Gene name", "Tissue"])
            .agg(pl.col("_hpa_protein_level").max())
            .collect()
        )
        df_wide = df.pivot(
            on="Tissue",
            values="_hpa_protein_level",
            index="Gene name",
        )
        df_wide = df_wide.rename({
            tissue: f"hpa_{key}_protein_level"
            for key, tissue in target_tissue_names.items()
            if tissue and tissue in df_wide.columns
        })
        for key in HPA_TISSUE_KEYS:
            code_column = f"hpa_{key}_protein_level"
            label_column = f"hpa_{key}_protein_level_label"
            if code_column in df_wide.columns:
                df_wide = df_wide.with_columns(
                    pl.col(code_column)
                    .map_elements(
                        lambda value: HPA_ORDINAL_LABEL.get(value),
                        return_dtype=pl.Utf8,
                    )
                    .alias(label_column)
                )
        measurement_kind = "ordinal_protein_level"

    df_wide = df_wide.rename({"Gene name": "gene_symbol"})
    df_wide = _ensure_hpa_schema(df_wide)

    logger.info(
        "hpa_parse_complete",
        tissues=list(target_tissue_names.keys()),
        measurement_kind=measurement_kind,
        categorical_fallback=measurement_kind == "ordinal_protein_level",
    )

    return df_wide.lazy()


def _ensure_hpa_schema(df: pl.DataFrame) -> pl.DataFrame:
    """Add nullable columns so HPA source modes share one explicit schema."""
    additions = []
    for column in HPA_PROTEIN_LEVEL_COLUMNS:
        if column not in df.columns:
            additions.append(pl.lit(None).cast(pl.Int8).alias(column))
    for column in HPA_PROTEIN_LEVEL_LABEL_COLUMNS:
        if column not in df.columns:
            additions.append(pl.lit(None).cast(pl.Utf8).alias(column))
    for column in HPA_NTPM_COLUMNS:
        if column not in df.columns:
            additions.append(pl.lit(None).cast(pl.Float64).alias(column))
    return df.with_columns(additions) if additions else df


def fetch_gtex_expression(
    gene_ids: list[str],
    cache_dir: Optional[Path] = None,
    force: bool = False,
    cache_only: bool = False,
) -> pl.LazyFrame:
    """Fetch GTEx tissue expression data for target tissues.

    Downloads GTEx bulk median TPM file, filters to target tissues.
    NOTE: GTEx lacks inner ear/cochlea tissue - will be NULL.

    Args:
        gene_ids: List of Ensembl gene IDs to filter
        cache_dir: Directory to cache downloaded GTEx file
        force: If True, re-download even if cached
        cache_only: If True, require the existing cache and never download

    Returns:
        LazyFrame with columns: gene_id, gtex_retina_tpm, gtex_cerebellum_tpm,
        gtex_testis_tpm, gtex_fallopian_tube_tpm
        NULL for tissues not available in GTEx.
    """
    cache_dir = Path(cache_dir) if cache_dir else Path("data/expression")

    # Download GTEx bulk expression data
    gtex_gct_path = cache_dir / "gtex_median_tpm.gct"
    if cache_only:
        _require_cached_file(gtex_gct_path, "GTEx median TPM data")
    else:
        cache_dir.mkdir(parents=True, exist_ok=True)
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
        logger.warning(
            "gtex_tissues_structurally_absent",
            missing=missing_tissues,
            reason="raw GTEx GCT has no corresponding tissue column",
        )

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


def _sha256(path: Path) -> str:
    """Return a stable SHA-256 fingerprint for a cached source file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_cellxgene_metadata(
    metadata: Optional[dict],
    *,
    status: str,
    cache_path: Path,
    census_version: str,
    error: Optional[str] = None,
    legacy_cache_path: Optional[Path] = None,
) -> None:
    """Record a machine-readable CellxGene source outcome and fingerprint."""
    if metadata is None:
        return
    metadata.update(
        {
            "status": status,
            "error": error,
            "census_version": census_version,
            "cache_file": cache_path.name,
            "cache_identity": cache_path.stem.removeprefix("cellxgene_expression_"),
            "query_mode": (
                "photoreceptor_hair"
                if "photoreceptor_hair" in cache_path.name
                else "photoreceptor_only"
            ),
            "coverage": CELLXGENE_CACHE_COVERAGE,
            "cache_exists": cache_path.is_file(),
            "cache_sha256": _sha256(cache_path) if cache_path.is_file() else None,
        }
    )
    if legacy_cache_path is not None:
        metadata.update(
            {
                "legacy_cache_file": legacy_cache_path.name,
                "legacy_cache_identity": (
                    f"{census_version}_legacy_photoreceptor_only_all_genes"
                ),
                "legacy_query_mode": "photoreceptor_only",
                "legacy_coverage": CELLXGENE_CACHE_COVERAGE,
                "legacy_cache_sha256": (
                    _sha256(legacy_cache_path)
                    if legacy_cache_path.is_file()
                    else None
                ),
            }
        )


def expression_source_metadata(
    cache_dir: Path,
    df: Optional[pl.DataFrame] = None,
    *,
    census_version: str = "2025-11-08",
    cellxgene_metadata: Optional[dict] = None,
    include_hair_cell: Optional[bool] = None,
) -> dict:
    """Describe expression source schemas, hashes, structural gaps, and coverage.

    The metadata is intentionally source-specific: HPA categorical protein
    levels are identified as ordinal evidence, GTEx values as median TPM, and
    missing GTEx tissue columns are distinguished from per-gene NULL values.
    ``df`` adds exact post-merge non-null counts for rerun auditing.
    """
    cache_dir = Path(cache_dir)
    if include_hair_cell is None:
        include_hair_cell = bool(
            cellxgene_metadata
            and cellxgene_metadata.get("query_mode") == "photoreceptor_hair"
        )
    hpa_path = cache_dir / "hpa_normal_tissue.tsv"
    gtex_path = cache_dir / "gtex_median_tpm.gct"
    cellxgene_path = cellxgene_cache_path(
        cache_dir,
        census_version,
        include_hair_cell=include_hair_cell,
    )
    legacy_cellxgene_path = cellxgene_legacy_cache_path(
        cache_dir, census_version
    )

    result = {
        "schema_version": EXPRESSION_SCHEMA_VERSION,
        "contrast_scope": EXPRESSION_CONTRAST_SCOPE,
        "contrast_description": EXPRESSION_CONTRAST_DESCRIPTION,
        "sources": {},
        "structurally_absent": {},
    }

    cellxgene_source = dict(cellxgene_metadata or {})
    cellxgene_source.setdefault("status", "not_invoked")
    cellxgene_source.setdefault("error", None)
    cellxgene_source.update(
        {
            "census_version": census_version,
            "cache_file": cellxgene_path.name,
            "cache_identity": cellxgene_cache_identity(
                census_version,
                include_hair_cell=include_hair_cell,
            ),
            "query_mode": (
                "photoreceptor_hair" if include_hair_cell else "photoreceptor_only"
            ),
            "coverage": CELLXGENE_CACHE_COVERAGE,
            "cache_exists": cellxgene_path.is_file(),
            "cache_sha256": (
                _sha256(cellxgene_path) if cellxgene_path.is_file() else None
            ),
        }
    )
    result["sources"]["cellxgene"] = cellxgene_source
    if (
        not cellxgene_path.is_file()
        and not include_hair_cell
        and legacy_cellxgene_path.is_file()
    ):
        if cellxgene_source["status"] == "not_invoked":
            cellxgene_source["status"] = "legacy_cache_available"
        cellxgene_source.update(
            {
                "legacy_cache_file": legacy_cellxgene_path.name,
                "legacy_cache_identity": (
                    f"{census_version}_legacy_photoreceptor_only_all_genes"
                ),
                "legacy_query_mode": "photoreceptor_only",
                "legacy_coverage": CELLXGENE_CACHE_COVERAGE,
                "legacy_cache_sha256": _sha256(legacy_cellxgene_path),
            }
        )

    if hpa_path.exists():
        hpa_columns = pl.read_csv(
            hpa_path, separator="\t", n_rows=0, has_header=True
        ).columns
        ntpm_column = next(
            (column for column in hpa_columns if column.casefold() == "ntpm"),
            None,
        )
        measurement_kind = (
            "quantitative_transcript_ntpm"
            if ntpm_column
            else "ordinal_protein_level"
            if "Level" in hpa_columns
            else "unknown"
        )
        result["sources"]["hpa"] = {
            "file": hpa_path.name,
            "sha256": _sha256(hpa_path),
            "measurement_kind": measurement_kind,
            "measurement_column": ntpm_column or "Level",
            "raw_columns": hpa_columns,
            "reliability_policy": HPA_RELIABILITY_POLICY,
            "reliability_column": "Reliability" if "Reliability" in hpa_columns else None,
            "reliability_required_for": "ordinal_protein_level",
            "reliability_filter_applied": "Reliability" in hpa_columns,
            "level_order": HPA_LEVEL_ORDINAL if measurement_kind == "ordinal_protein_level" else None,
            "semantics": HPA_LEVEL_SEMANTICS if measurement_kind == "ordinal_protein_level" else "Quantitative normalized transcript nTPM",
            "aggregation": (
                "mean_across_reported_cell_types"
                if measurement_kind == "quantitative_transcript_ntpm"
                else "maximum_ordered_level_across_reported_cell_types"
                if measurement_kind == "ordinal_protein_level"
                else None
            ),
        }

    if gtex_path.exists():
        gtex_columns = pl.read_csv(
            gtex_path, separator="\t", skip_rows=2, n_rows=0, has_header=True
        ).columns
        configured_gtex = {
            key: TARGET_TISSUES[key]["gtex"]
            for key in ("retina", "cerebellum", "testis", "fallopian_tube")
        }
        absent = [
            key
            for key, raw_column in configured_gtex.items()
            if raw_column and raw_column not in gtex_columns
        ]
        if absent:
            result["structurally_absent"]["gtex"] = {
                key: GTEX_STRUCTURAL_ABSENCE.get(
                    key,
                    {
                        "raw_column": configured_gtex[key],
                        "reason": "configured tissue column absent from raw GTEx GCT",
                    },
                )
                for key in absent
            }
        result["sources"]["gtex"] = {
            "file": gtex_path.name,
            "sha256": _sha256(gtex_path),
            "measurement_kind": "median_transcript_tpm",
            "raw_columns": gtex_columns,
            "available_target_tissues": [
                key
                for key, raw_column in configured_gtex.items()
                if raw_column in gtex_columns
            ],
        }

    if df is not None:
        def counts(columns: tuple[str, ...]) -> dict:
            return {
                column: {
                    "non_null_count": int(df[column].is_not_null().sum())
                    if column in df.columns else 0,
                    "expressed_positive_count": int(
                        df.filter(pl.col(column) > 0).height
                    ) if column in df.columns else 0,
                    "row_count": df.height,
                }
                for column in columns
            }

        result["coverage"] = {
            "row_count": df.height,
            "hpa_protein_level": counts(HPA_PROTEIN_LEVEL_COLUMNS),
            "hpa_ntpm": counts(HPA_NTPM_COLUMNS),
            "gtex_tpm": counts(GTEX_TPM_COLUMNS),
            "cellxgene": counts(CELLXGENE_COLUMNS),
        }

    return result


def _null_cellxgene_result(gene_ids: list[str]) -> pl.LazyFrame:
    """Return a NULL CellxGene result for all genes (fallback)."""
    return pl.LazyFrame({
        "gene_id": gene_ids,
        "cellxgene_photoreceptor_expr": [None] * len(gene_ids),
        "cellxgene_hair_cell_expr": [None] * len(gene_ids),
    })


def _migrate_legacy_cellxgene_cache(
    gene_ids: list[str],
    *,
    legacy_path: Path,
    cache_path: Path,
    census_version: str,
    cache_only: bool,
    metadata: Optional[dict],
) -> Optional[pl.LazyFrame]:
    """Migrate the baseline photoreceptor-only cache to its explicit identity."""
    try:
        cached = pl.read_parquet(legacy_path)
        required_columns = {"gene_id", "cellxgene_photoreceptor_expr"}
        missing_columns = required_columns - set(cached.columns)
        if missing_columns:
            raise ValueError(
                "legacy CellxGene cache is missing columns: "
                + ", ".join(sorted(missing_columns))
            )

        # The baseline filename is ambiguous: an old caller may have populated
        # the hair-cell column with include_hair_cell=True data.  The legacy
        # filename is nevertheless recognized only as photoreceptor-only, so
        # discard that column unconditionally rather than carrying ambiguous
        # values into the migrated cache or returned frame.
        normalized_columns = [
            pl.col("cellxgene_photoreceptor_expr")
            .cast(pl.Float64, strict=False)
            .alias("cellxgene_photoreceptor_expr")
        ]
        normalized_columns.append(
            pl.lit(None).cast(pl.Float64).alias("cellxgene_hair_cell_expr")
        )
        cached = cached.with_columns(normalized_columns)

        temporary_cache_path = cache_path.with_name(cache_path.name + ".tmp")
        cached.write_parquet(temporary_cache_path)
        temporary_cache_path.replace(cache_path)
    except Exception as error:
        if "temporary_cache_path" in locals() and temporary_cache_path.exists():
            temporary_cache_path.unlink()
        _record_cellxgene_metadata(
            metadata,
            status="legacy_cache_migration_failed",
            cache_path=cache_path,
            census_version=census_version,
            error=str(error),
            legacy_cache_path=legacy_path,
        )
        if cache_only:
            raise
        logger.warning("cellxgene_legacy_cache_migration_failed", error=str(error))
        return None

    _record_cellxgene_metadata(
        metadata,
        status="legacy_cache_migrated",
        cache_path=cache_path,
        census_version=census_version,
        legacy_cache_path=legacy_path,
    )
    result = (
        pl.DataFrame({"gene_id": gene_ids})
        .join(cached, on="gene_id", how="left")
    )
    return result.lazy()


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
    column_name: str,
    errors: Optional[list[str]] = None,
) -> pl.DataFrame:
    """Query Census for mean expression of ALL genes in specific cell types.

    Args:
        census: Open cellxgene_census.open_soma() context.
        cell_types: List of cell_type ontology labels to filter.
        column_name: Name for the output expression column.

    Returns:
        DataFrame with columns: gene_id, <column_name> for all genes in Census.
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
            obs_column_names=["cell_type"],
            var_column_names=["feature_id"],
        )
    except Exception as e:
        if errors is not None:
            errors.append(f"{column_name}: {e}")
        logger.warning(
            "cellxgene_query_failed",
            cell_types=cell_types,
            error=str(e),
        )
        return pl.DataFrame({"gene_id": [], column_name: []}).cast(
            {"gene_id": pl.Utf8, column_name: pl.Float64}
        )

    n_cells = adata.n_obs
    n_genes_found = adata.n_vars

    logger.info(
        "cellxgene_query_result",
        cell_types=cell_types,
        cells_found=n_cells,
        genes_found=n_genes_found,
    )

    if n_cells == 0:
        return pl.DataFrame({"gene_id": [], column_name: []}).cast(
            {"gene_id": pl.Utf8, column_name: pl.Float64}
        )

    # Compute mean expression per gene across all matching cells
    # adata.X is a sparse matrix (cells x genes)
    import numpy as np

    mean_expr = np.asarray(adata.X.mean(axis=0)).flatten()
    feature_ids = adata.var["feature_id"]
    found_gene_ids = feature_ids.tolist() if hasattr(feature_ids, "tolist") else list(feature_ids)

    return pl.DataFrame({
        "gene_id": found_gene_ids,
        column_name: mean_expr.tolist(),
    })


def fetch_cellxgene_expression(
    gene_ids: list[str],
    cache_dir: Optional[Path] = None,
    force: bool = False,
    cache_only: bool = False,
    census_version: str = "2025-11-08",
    include_hair_cell: bool = False,
    metadata: Optional[dict] = None,
) -> pl.LazyFrame:
    """Fetch CellxGene single-cell expression data for target cell types.

    Queries the named CZ CELLxGENE Census build for photoreceptor expression.
    Hair-cell querying is opt-in exploratory functionality and is not included
    in the production score. Results are cached in a versioned parquet file.

    NOTE: cellxgene_census is an optional dependency.
    If not available, returns DataFrame with all NULL values.

    Args:
        gene_ids: List of Ensembl gene IDs to query.
        cache_dir: Directory for caching query results.
        force: Re-query Census even if cache exists.
        cache_only: Require the versioned cache and never query Census.
        census_version: Named CELLxGENE Census release/build date.
        include_hair_cell: Also query hair-cell labels for exploratory analyses.
        metadata: Optional dictionary populated with source status and cache fingerprint.

    Returns:
        LazyFrame with columns: gene_id, cellxgene_photoreceptor_expr,
        cellxgene_hair_cell_expr.
        NULL if cellxgene_census not available or cell type data missing.
    """
    # Check cache FIRST (before importing cellxgene_census)
    cache_dir = Path(cache_dir) if cache_dir else Path("data/expression")
    cache_path = cellxgene_cache_path(
        cache_dir,
        census_version,
        include_hair_cell=include_hair_cell,
    )

    if cache_only and force:
        error = "cache_only CellxGene fetch cannot use force=True"
        _record_cellxgene_metadata(
            metadata,
            status="cache_only_invalid",
            cache_path=cache_path,
            census_version=census_version,
            error=error,
        )
        raise ValueError(error)

    if cache_path.exists() and not force:
        logger.info("cellxgene_cache_hit", path=str(cache_path))
        try:
            cached = pl.read_parquet(cache_path)
        except Exception as e:
            _record_cellxgene_metadata(
                metadata,
                status="cache_read_failed",
                cache_path=cache_path,
                census_version=census_version,
                error=str(e),
            )
            if cache_only:
                raise
            logger.warning("cellxgene_cache_read_failed", error=str(e))
        else:
            _record_cellxgene_metadata(
                metadata,
                status="cache_hit",
                cache_path=cache_path,
                census_version=census_version,
            )
            # Filter to requested gene_ids and left-join to preserve all
            result = (
                pl.DataFrame({"gene_id": gene_ids})
                .join(cached, on="gene_id", how="left")
            )
            return result.lazy()

    # The baseline cache predates explicit query identity. It is known to be
    # photoreceptor-only/all-genes and may be migrated without network access.
    # Never use it for hair-cell mode because its coverage is ambiguous there.
    legacy_cache_path = cellxgene_legacy_cache_path(cache_dir, census_version)
    if (
        not cache_path.exists()
        and not force
        and not include_hair_cell
        and legacy_cache_path.is_file()
    ):
        migrated = _migrate_legacy_cellxgene_cache(
            gene_ids,
            legacy_path=legacy_cache_path,
            cache_path=cache_path,
            census_version=census_version,
            cache_only=cache_only,
            metadata=metadata,
        )
        if migrated is not None:
            return migrated

    if cache_only:
        error = f"cache-only expression reprocessing requires cached CellxGene data: {cache_path}"
        _record_cellxgene_metadata(
            metadata,
            status="cache_missing",
            cache_path=cache_path,
            census_version=census_version,
            error=error,
        )
        raise FileNotFoundError(error)

    # Import cellxgene_census (optional dependency) — only needed for live queries
    try:
        import cellxgene_census
    except ImportError:
        _record_cellxgene_metadata(
            metadata,
            status="dependency_unavailable",
            cache_path=cache_path,
            census_version=census_version,
            error="cellxgene_census is not installed",
        )
        logger.warning(
            "cellxgene_census_unavailable",
            message="cellxgene_census not installed. Install with: pip install 'usher-pipeline[expression]'",
        )
        return _null_cellxgene_result(gene_ids)

    cache_dir.mkdir(parents=True, exist_ok=True)

    logger.info("cellxgene_fetch_start", gene_count=len(gene_ids))

    try:
        query_errors: list[str] = []
        with cellxgene_census.open_soma(census_version=census_version) as census:
            # Query photoreceptor expression (all genes)
            photo_df = _query_mean_expression(
                census,
                PHOTORECEPTOR_CELL_TYPES,
                "cellxgene_photoreceptor_expr",
                errors=query_errors,
            )

            if include_hair_cell:
                # Exploratory only; this column is excluded from production
                # scoring unless explicitly requested by a downstream caller.
                hair_df = _query_mean_expression(
                    census,
                    HAIR_CELL_TYPES,
                    "cellxgene_hair_cell_expr",
                    errors=query_errors,
                )
            else:
                hair_df = pl.DataFrame({"gene_id": [], "cellxgene_hair_cell_expr": []}).cast(
                    {"gene_id": pl.Utf8, "cellxgene_hair_cell_expr": pl.Float64}
                )

        # Merge full Census results
        if photo_df.height > 0 and hair_df.height > 0:
            full_result = photo_df.join(hair_df, on="gene_id", how="outer_coalesce")
        elif photo_df.height > 0:
            full_result = photo_df.with_columns(pl.lit(None).cast(pl.Float64).alias("cellxgene_hair_cell_expr"))
        elif hair_df.height > 0:
            full_result = hair_df.with_columns(pl.lit(None).cast(pl.Float64).alias("cellxgene_photoreceptor_expr"))
        else:
            full_result = _null_cellxgene_result(gene_ids).collect()

        query_error = "; ".join(query_errors) if query_errors else None
        query_empty = photo_df.height == 0 and hair_df.height == 0

        # A partial/failed Census query is retryable and must never become a
        # normal cache hit. Preserve any prior valid cache file untouched.
        if query_error:
            _record_cellxgene_metadata(
                metadata,
                status="live_query_failed",
                cache_path=cache_path,
                census_version=census_version,
                error=query_error,
            )
            return _null_cellxgene_result(gene_ids)

        # Cache ALL Census genes atomically (avoid re-querying). A failed
        # write cannot leave a file that looks like a normal cache hit.
        temporary_cache_path = cache_path.with_name(cache_path.name + ".tmp")
        try:
            full_result.write_parquet(temporary_cache_path)
            temporary_cache_path.replace(cache_path)
        except Exception:
            if temporary_cache_path.exists():
                temporary_cache_path.unlink()
            raise
        _record_cellxgene_metadata(
            metadata,
            status=(
                "live_query_failed"
                if query_error
                else "live_query_empty"
                if query_empty
                else "live_query_success"
            ),
            cache_path=cache_path,
            census_version=census_version,
            error=query_error,
        )

        # Filter to requested pipeline gene_ids
        result = (
            pl.DataFrame({"gene_id": gene_ids})
            .join(full_result, on="gene_id", how="left")
        )
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
        _record_cellxgene_metadata(
            metadata,
            status="live_query_failed",
            cache_path=cache_path,
            census_version=census_version,
            error=str(e),
        )
        logger.warning(
            "cellxgene_fetch_failed",
            error=str(e),
            message="CellxGene Census query failed. Returning NULL values.",
        )
        return _null_cellxgene_result(gene_ids)

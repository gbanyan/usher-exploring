"""Download HPA localization and match embedded curated compendium symbols."""

import hashlib
import io
import zipfile
import warnings
from collections import defaultdict
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

from usher_pipeline.evidence.localization.models import (
    CURATED_COMPENDIUM_COLUMNS,
    CURATED_COMPENDIUM_EVIDENCE_MODALITY,
    CURATED_COMPENDIUM_EVIDENCE_WEIGHT,
    CURATED_COMPENDIUM_FALLBACK_SCORE,
    HPA_SUBCELLULAR_URL,
    LEGACY_CURATED_PROTEOMICS_COLUMNS,
)

logger = structlog.get_logger()


# Embedded heterogeneous compendium symbols. The source assay tables are not
# available in this repository, so these are not attributed to an experimental
# modality or to individual studies.
_CILIA_COMPENDIUM_SOURCE_SYMBOLS = {
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

_CENTROSOME_COMPENDIUM_SOURCE_SYMBOLS = {
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


CURATED_COMPENDIUM_SELECTION_VERSION = "embedded-curated-compendium-v3"
CURATED_COMPENDIUM_SELECTION_POLICY = (
    "Use the exact embedded symbol literals in this module as a curated, "
    "heterogeneous ciliary/centrosomal compendium; normalize obsolete aliases "
    "to current HGNC symbols before matching; do not infer assay, study, journal, "
    "or completeness claims from membership."
)

CURATED_COMPENDIUM_ORIGINS = {
    "cilia": {
        "source": "embedded_ciliary_compendium",
        "origin": "Literal symbol list in src/usher_pipeline/evidence/localization/fetch.py",
        "scope": "Heterogeneous curated ciliary-associated symbol compendium; not a complete CiliaCarta or proteomics dataset",
        "source_tables_available": False,
    },
    "centrosome": {
        "source": "embedded_centrosomal_compendium",
        "origin": "Literal symbol list in src/usher_pipeline/evidence/localization/fetch.py",
        "scope": "Heterogeneous curated centrosomal-associated symbol compendium; not a complete centrosome or proteomics dataset",
        "source_tables_available": False,
    },
}

COMPENDIUM_SYMBOL_ALIASES = {
    "TALPID3": "KIAA0586",
    "KIAA0586": "KIAA0586",
    "SAS6": "SASS6",
    "SASS6": "SASS6",
    "CPAP": "CENPJ",
    "CENPJ": "CENPJ",
    "C5ORF42": "CPLANE1",
    "CPLANE1": "CPLANE1",
    "C21ORF59": "CFAP298",
    "CFAP298": "CFAP298",
}


def normalize_compendium_gene_symbol(symbol: str | None) -> str | None:
    """Normalize embedded-compendium aliases to current HGNC symbols."""
    if symbol is None:
        return None
    normalized = symbol.strip().upper()
    return COMPENDIUM_SYMBOL_ALIASES.get(normalized, normalized)


# Compatibility aliases for callers of the prior localization API.
PROTEOMICS_SYMBOL_ALIASES = COMPENDIUM_SYMBOL_ALIASES
normalize_proteomics_gene_symbol = normalize_compendium_gene_symbol


def _normalize_gene_set(symbols: set[str]) -> frozenset[str]:
    return frozenset(
        normalized
        for symbol in symbols
        if (normalized := normalize_compendium_gene_symbol(symbol)) is not None
    )


# Public matching sets contain only normalized current symbols. The raw source
# spellings above are retained in CURATED_COMPENDIUM_RECORDS below.
CILIA_COMPENDIUM_GENES = _normalize_gene_set(_CILIA_COMPENDIUM_SOURCE_SYMBOLS)
CENTROSOME_COMPENDIUM_GENES = _normalize_gene_set(
    _CENTROSOME_COMPENDIUM_SOURCE_SYMBOLS
)

# Compatibility aliases; the gate and current schema use compendium names.
CILIA_PROTEOMICS_GENES = CILIA_COMPENDIUM_GENES
CENTROSOME_PROTEOMICS_GENES = CENTROSOME_COMPENDIUM_GENES


def _gene_set_sha256(genes: set[str] | frozenset[str]) -> str:
    """Return a deterministic hash for an embedded HGNC-symbol gene set."""
    canonical = "\n".join(sorted(genes)) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_compendium_records(
    source_name: str,
    source_symbols: set[str],
) -> list[dict[str, object]]:
    """Build membership provenance without fabricating assay attribution."""
    aliases_by_symbol: defaultdict[str, list[str]] = defaultdict(list)
    for source_symbol in source_symbols:
        normalized = normalize_compendium_gene_symbol(source_symbol)
        if normalized is not None:
            aliases_by_symbol[normalized].append(source_symbol)

    return [
        {
            "gene_symbol": normalized,
            "source": f"embedded_{source_name}_compendium",
            "study": None,
            "evidence_modality": CURATED_COMPENDIUM_EVIDENCE_MODALITY,
            "selection_version": CURATED_COMPENDIUM_SELECTION_VERSION,
            "source_gene_symbols": sorted(aliases_by_symbol[normalized]),
        }
        for normalized in sorted(aliases_by_symbol)
    ]


_CILIA_COMPENDIUM_RECORDS = _build_compendium_records(
    "cilia",
    _CILIA_COMPENDIUM_SOURCE_SYMBOLS,
)
_CENTROSOME_COMPENDIUM_RECORDS = _build_compendium_records(
    "centrosome",
    _CENTROSOME_COMPENDIUM_SOURCE_SYMBOLS,
)
CURATED_COMPENDIUM_RECORDS = [
    *_CILIA_COMPENDIUM_RECORDS,
    *_CENTROSOME_COMPENDIUM_RECORDS,
]
CURATED_PROTEOMICS_RECORDS = CURATED_COMPENDIUM_RECORDS


# Metadata is intentionally per compendium and includes per-gene membership
# records. No unavailable source tables or per-gene assay citations are implied.
CURATED_COMPENDIUM_PROVENANCE = {
    "cilia": {
        **CURATED_COMPENDIUM_ORIGINS["cilia"],
        "set_name": "embedded_curated_ciliary_compendium",
        "complete_source_dataset": False,
        "selection_version": CURATED_COMPENDIUM_SELECTION_VERSION,
        "selection_policy": CURATED_COMPENDIUM_SELECTION_POLICY,
        "evidence_modality": CURATED_COMPENDIUM_EVIDENCE_MODALITY,
        "evidence_weight": CURATED_COMPENDIUM_EVIDENCE_WEIGHT,
        "fallback_score": CURATED_COMPENDIUM_FALLBACK_SCORE,
        "symbol_normalization": "Obsolete aliases normalized to current HGNC symbols for matching",
        "gene_count": len(CILIA_COMPENDIUM_GENES),
        "sha256": _gene_set_sha256(CILIA_COMPENDIUM_GENES),
        "hash_input": "UTF-8 joined sorted normalized HGNC symbols with trailing newline",
        "records": _CILIA_COMPENDIUM_RECORDS,
        "record_count": len(_CILIA_COMPENDIUM_RECORDS),
    },
    "centrosome": {
        **CURATED_COMPENDIUM_ORIGINS["centrosome"],
        "set_name": "embedded_curated_centrosomal_compendium",
        "complete_source_dataset": False,
        "selection_version": CURATED_COMPENDIUM_SELECTION_VERSION,
        "selection_policy": CURATED_COMPENDIUM_SELECTION_POLICY,
        "evidence_modality": CURATED_COMPENDIUM_EVIDENCE_MODALITY,
        "evidence_weight": CURATED_COMPENDIUM_EVIDENCE_WEIGHT,
        "fallback_score": CURATED_COMPENDIUM_FALLBACK_SCORE,
        "symbol_normalization": "Obsolete aliases normalized to current HGNC symbols for matching",
        "gene_count": len(CENTROSOME_COMPENDIUM_GENES),
        "sha256": _gene_set_sha256(CENTROSOME_COMPENDIUM_GENES),
        "hash_input": "UTF-8 joined sorted normalized HGNC symbols with trailing newline",
        "records": _CENTROSOME_COMPENDIUM_RECORDS,
        "record_count": len(_CENTROSOME_COMPENDIUM_RECORDS),
    },
}

# Compatibility aliases for provenance consumers of d26348b.
CURATED_PROTEOMICS_PROVENANCE = CURATED_COMPENDIUM_PROVENANCE
CURATED_PROTEOMICS_SELECTION_VERSION = CURATED_COMPENDIUM_SELECTION_VERSION
CURATED_PROTEOMICS_SELECTION_POLICY = CURATED_COMPENDIUM_SELECTION_POLICY
CURATED_PROTEOMICS_EVIDENCE_MODALITY = CURATED_COMPENDIUM_EVIDENCE_MODALITY


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
    cache_only: bool = False,
) -> pl.DataFrame:
    """Fetch HPA subcellular localization data for genes.

    Downloads HPA subcellular location data, parses it, and filters to the
    input gene list. Maps gene symbols to gene IDs using the provided mapping.

    Args:
        gene_ids: List of Ensembl gene IDs to fetch
        gene_symbol_map: DataFrame with gene_id and gene_symbol columns
        cache_dir: Directory to cache HPA download (default: data/localization)
        force: If True, re-download HPA data
        cache_only: If True, require the local TSV and never access the network

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

    if cache_only and not tsv_path.is_file():
        raise FileNotFoundError(
            "Cache-only localization processing requires the local HPA raw source: "
            f"{tsv_path}"
        )

    # Download HPA data
    logger.info("fetch_hpa_start", gene_count=len(gene_ids))
    tsv_path = download_hpa_subcellular(tsv_path, force=force and not cache_only)

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

    # HPA may emit multiple antibody rows for one symbol, and duplicate
    # symbols in the frozen universe can multiply those rows during the
    # exact-universe join.  Collapse only after the ID intersection: retain
    # the union of reported locations and the strongest reliability so the
    # raw-derived layer has one deterministic row per Ensembl ID.
    if df.height:
        reliability_rank = {
            "Enhanced": 4,
            "Supported": 4,
            "Approved": 2,
            "Uncertain": 2,
        }
        collapsed_rows = []
        for key, group in df.group_by("gene_id", maintain_order=True):
            gene_id = key[0]
            locations = set()
            reliabilities = []
            for row in group.iter_rows(named=True):
                location = row["hpa_main_location"]
                if location:
                    locations.update(
                        part.strip() for part in location.split(";") if part.strip()
                    )
                reliability = row["hpa_reliability"]
                if reliability:
                    reliabilities.append(reliability)
            strongest = (
                sorted(
                    set(reliabilities),
                    key=lambda value: (-reliability_rank.get(value, 0), value),
                )[0]
                if reliabilities
                else None
            )
            collapsed_rows.append({
                "gene_id": gene_id,
                "gene_symbol": group["gene_symbol"][0],
                "hpa_reliability": strongest,
                "hpa_main_location": ";".join(sorted(locations)) if locations else None,
            })
        df = pl.DataFrame(collapsed_rows)

    logger.info("hpa_filter_complete", row_count=len(df))

    return df


def fetch_cilia_compendium(
    gene_ids: list[str],
    gene_symbol_map: pl.DataFrame,
) -> pl.DataFrame:
    """Cross-reference genes against embedded curated compendium lists.

    The lists are heterogeneous ciliary/centrosomal compendia. Their source
    assay tables are unavailable locally, so membership is curated-compendium
    evidence rather than an experimental or mass-spectrometry observation.
    Genes not found are marked False, since compendium membership is explicit.

    Args:
        gene_ids: List of Ensembl gene IDs to check
        gene_symbol_map: DataFrame with gene_id and gene_symbol columns

    Returns:
        DataFrame with columns:
        - gene_id: Ensembl gene ID
        - gene_symbol: HGNC symbol
        - in_cilia_compendium: bool (True if in the embedded ciliary compendium)
        - in_centrosome_compendium: bool (True if in the embedded centrosomal compendium)
    """
    logger.info(
        "fetch_compendium_start",
        gene_count=len(gene_ids),
        cilia_ref_count=len(CILIA_COMPENDIUM_GENES),
        centrosome_ref_count=len(CENTROSOME_COMPENDIUM_GENES),
    )

    # Filter gene symbol map to requested gene_ids
    gene_ids_set = set(gene_ids)
    df = gene_symbol_map.filter(pl.col("gene_id").is_in(gene_ids_set))

    # Normalize aliases before matching while retaining the submitted HGNC
    # symbol in the output for traceability.
    df = df.with_columns([
        pl.col("gene_symbol")
        .map_elements(normalize_compendium_gene_symbol, return_dtype=pl.Utf8)
        .alias("_normalized_gene_symbol"),
    ]).with_columns([
        pl.col("_normalized_gene_symbol")
        .is_in(CILIA_COMPENDIUM_GENES)
        .alias("in_cilia_compendium"),
        pl.col("_normalized_gene_symbol")
        .is_in(CENTROSOME_COMPENDIUM_GENES)
        .alias("in_centrosome_compendium"),
    ])

    logger.info(
        "fetch_compendium_complete",
        cilia_hits=df.filter(pl.col("in_cilia_compendium")).height,
        centrosome_hits=df.filter(pl.col("in_centrosome_compendium")).height,
    )

    return df.select(["gene_id", "gene_symbol", "in_cilia_compendium", "in_centrosome_compendium"])


def fetch_cilia_proteomics(
    gene_ids: list[str],
    gene_symbol_map: pl.DataFrame,
) -> pl.DataFrame:
    """Deprecated wrapper preserving the legacy proteomics column contract."""
    warnings.warn(
        "fetch_cilia_proteomics() is deprecated; use fetch_cilia_compendium()",
        DeprecationWarning,
        stacklevel=2,
    )
    compendium_df = fetch_cilia_compendium(gene_ids, gene_symbol_map)
    return compendium_df.rename(dict(zip(
        CURATED_COMPENDIUM_COLUMNS,
        LEGACY_CURATED_PROTEOMICS_COLUMNS,
    )))

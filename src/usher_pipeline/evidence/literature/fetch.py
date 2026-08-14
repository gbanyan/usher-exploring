"""Bulk literature evidence fetch via gene2pubmed + batch MeSH queries.

Instead of querying PubMed per-gene (135K API calls, ~46 hours), this module:
1. Downloads NCBI gene2pubmed.gz (~150MB) -- curated gene->PMID mapping
2. Downloads NCBI gene_info.gz (~20MB) -- GeneID->symbol mapping
3. Runs 6 batch PubMed queries for context PMID sets (cilia, sensory, etc.)
4. Counts per-gene set intersections locally

Total runtime: ~5-10 minutes (vs 46 hours).
"""

import json
import time
from pathlib import Path
from typing import Optional

import httpx
import polars as pl
import structlog
from Bio import Entrez
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from usher_pipeline.evidence.literature.models import (
    GENE2PUBMED_URL,
    GENE_INFO_URL,
    HUMAN_TAX_ID,
    MESH_CONTEXT_QUERIES,
    DIRECT_EVIDENCE_QUERY,
    HTS_QUERY,
)

logger = structlog.get_logger(__name__)


# -- Bulk file download -------------------------------------------------------


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def _download_gz(url: str, dest: Path, force: bool = False) -> Path:
    """Download a gzipped file from NCBI FTP with retry."""
    if dest.exists() and not force:
        logger.info("bulk_file_exists", path=str(dest))
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest.with_suffix(".tmp")

    logger.info("bulk_download_start", url=url)
    with httpx.stream("GET", url, timeout=300.0, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(temp_path, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=65536):
                f.write(chunk)

    temp_path.rename(dest)
    logger.info(
        "bulk_download_complete",
        path=str(dest),
        size_mb=round(dest.stat().st_size / 1024 / 1024, 1),
    )
    return dest


def download_bulk_files(
    data_dir: Path,
    force: bool = False,
    cache_only: bool = False,
) -> tuple[Path, Path]:
    """Download gene2pubmed.gz and gene_info.gz from NCBI.

    Args:
        data_dir: Directory to save downloaded files.
        force: Re-download even if files exist.
        cache_only: Require both local files and never download.

    Returns:
        Tuple of (gene2pubmed_path, gene_info_path).
    """
    data_dir = Path(data_dir)
    lit_dir = data_dir / "literature"

    if cache_only:
        paths = (lit_dir / "gene2pubmed.gz", lit_dir / "gene_info.gz")
        missing = [path for path in paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                "Cache-only literature processing requires local bulk sources; "
                f"missing: {', '.join(str(path) for path in missing)}"
            )
        return paths

    g2p_path = _download_gz(GENE2PUBMED_URL, lit_dir / "gene2pubmed.gz", force)
    gi_path = _download_gz(GENE_INFO_URL, lit_dir / "gene_info.gz", force)

    return g2p_path, gi_path


# -- Bulk file parsing ---------------------------------------------------------


def parse_gene2pubmed(gz_path: Path) -> pl.DataFrame:
    """Parse gene2pubmed.gz, filtering to human entries only.

    Args:
        gz_path: Path to gene2pubmed.gz.

    Returns:
        DataFrame with columns: gene_id (Int64), pmid (Int64).
    """
    df = pl.read_csv(
        gz_path,
        separator="\t",
        comment_prefix="##",
        has_header=True,
    )

    # Handle the '#tax_id' header prefix
    if "#tax_id" in df.columns:
        df = df.rename({"#tax_id": "tax_id"})

    df = (
        df.filter(pl.col("tax_id") == HUMAN_TAX_ID)
        .select(
            pl.col("GeneID").cast(pl.Int64).alias("gene_id"),
            pl.col("PubMed_ID").cast(pl.Int64).alias("pmid"),
        )
    )

    logger.info(
        "gene2pubmed_parsed",
        human_rows=df.height,
        unique_genes=df["gene_id"].n_unique(),
    )
    return df


def parse_gene_info(gz_path: Path) -> pl.DataFrame:
    """Parse gene_info.gz for human protein-coding gene_id -> symbol mapping.

    Args:
        gz_path: Path to gene_info.gz.

    Returns:
        DataFrame with columns: gene_id (Int64), gene_symbol (str).
    """
    df = pl.read_csv(
        gz_path,
        separator="\t",
        comment_prefix="##",
        has_header=True,
        null_values=["-"],
    )

    if "#tax_id" in df.columns:
        df = df.rename({"#tax_id": "tax_id"})

    df = (
        df.filter(
            (pl.col("tax_id") == HUMAN_TAX_ID)
            & (pl.col("type_of_gene") == "protein-coding")
        )
        .select(
            pl.col("GeneID").cast(pl.Int64).alias("gene_id"),
            pl.col("Symbol").alias("gene_symbol"),
        )
    )

    logger.info("gene_info_parsed", human_protein_coding=df.height)
    return df


def build_gene_pmid_map(
    gene2pubmed: pl.DataFrame,
    gene_info: pl.DataFrame,
) -> dict[str, set[int]]:
    """Build gene_symbol -> set of PMIDs mapping.

    Joins gene2pubmed (gene_id->pmid) with gene_info (gene_id->symbol)
    to produce a dict keyed by HGNC symbol.

    Args:
        gene2pubmed: DataFrame from parse_gene2pubmed().
        gene_info: DataFrame from parse_gene_info().

    Returns:
        Dict mapping gene_symbol to set of PMIDs.
    """
    joined = gene2pubmed.join(gene_info, on="gene_id", how="inner")

    result: dict[str, set[int]] = {}
    for row in joined.group_by("gene_symbol").agg(pl.col("pmid")).iter_rows():
        symbol, pmids = row
        result[symbol] = set(pmids)

    logger.info(
        "gene_pmid_map_built",
        symbols=len(result),
        total_pmid_pairs=joined.height,
    )
    return result


# -- Batch PubMed queries for context PMID sets --------------------------------


def _esearch_all_pmids(
    query: str,
    email: str,
    api_key: Optional[str] = None,
) -> set[int]:
    """Run a single PubMed esearch and retrieve ALL matching PMIDs.

    Uses usehistory for server-side result storage, then paginates
    to get all PMIDs.

    Args:
        query: PubMed search query string.
        email: Email for NCBI E-utilities.
        api_key: Optional NCBI API key.

    Returns:
        Set of PMIDs matching the query.
    """
    Entrez.email = email
    if api_key:
        Entrez.api_key = api_key

    # Rate limit: respect NCBI policy
    rate_delay = 0.11 if api_key else 0.34

    # First: get count and WebEnv for history
    handle = Entrez.esearch(db="pubmed", term=query, retmax=0, usehistory="y")
    record = Entrez.read(handle)
    handle.close()

    total = int(record["Count"])
    web_env = record["WebEnv"]
    query_key = record["QueryKey"]

    logger.info("esearch_context_query", query=query[:80], total_pmids=total)

    if total == 0:
        return set()

    # PubMed esearch caps retstart at 9999. For large result sets, we split
    # by date ranges to stay under the limit per sub-query.
    if total <= 9999:
        # Small enough to get in one call
        time.sleep(rate_delay)
        handle = Entrez.esearch(
            db="pubmed", term=query, retmax=9999, usehistory="y",
        )
        record = Entrez.read(handle)
        handle.close()
        pmids = {int(uid) for uid in record.get("IdList", [])}
    else:
        # Split into year-range sub-queries
        pmids = set()
        year_ranges = [
            ("1900", "1999"),
            ("2000", "2009"),
            ("2010", "2014"),
            ("2015", "2019"),
            ("2020", "2022"),
            ("2023", "2024"),
            ("2025", "2026"),
        ]
        for yr_start, yr_end in year_ranges:
            sub_query = f"({query}) AND {yr_start}:{yr_end}[DP]"
            time.sleep(rate_delay)
            handle = Entrez.esearch(
                db="pubmed", term=sub_query, retmax=9999, usehistory="y",
            )
            sub_record = Entrez.read(handle)
            handle.close()
            sub_ids = {int(uid) for uid in sub_record.get("IdList", [])}
            sub_total = int(sub_record["Count"])
            pmids.update(sub_ids)

            if sub_total > 9999:
                logger.warning(
                    "esearch_year_range_truncated",
                    query=sub_query[:80],
                    total=sub_total,
                    retrieved=len(sub_ids),
                )

    logger.info(
        "esearch_context_complete",
        query=query[:80],
        retrieved_pmids=len(pmids),
    )
    return pmids


def fetch_context_pmid_sets(
    email: str,
    api_key: Optional[str] = None,
    cache_path: Optional[Path] = None,
    cache_only: bool = False,
) -> tuple[dict[str, set[int]], set[int], set[int]]:
    """Fetch PMID sets for each context via batch PubMed queries.

    Runs 6 queries total (4 contexts + direct_experimental + HTS).

    Args:
        email: Email for NCBI E-utilities.
        api_key: Optional NCBI API key.
        cache_path: Optional JSON path for cached query result sets.
        cache_only: Require the JSON cache and never query PubMed.

    Returns:
        Tuple of (context_pmid_sets, direct_experimental_pmids, hts_pmids).
    """
    if cache_path is not None and cache_path.exists():
        logger.info("context_pmid_cache_hit", path=str(cache_path))
        cached = json.loads(cache_path.read_text())
        required_keys = {"contexts", "direct_experimental", "hts"}
        if not required_keys.issubset(cached):
            raise ValueError(
                f"Local PubMed context cache is schema-mismatched: {cache_path}"
            )
        return (
            {
                name: {int(pmid) for pmid in pmids}
                for name, pmids in cached["contexts"].items()
            },
            {int(pmid) for pmid in cached["direct_experimental"]},
            {int(pmid) for pmid in cached["hts"]},
        )

    if cache_only:
        raise FileNotFoundError(
            "Cache-only literature processing requires the local PubMed context "
            f"cache; missing {cache_path}"
        )

    logger.info("fetch_context_pmid_sets_start")

    context_sets = {}
    for name, query in MESH_CONTEXT_QUERIES.items():
        context_sets[name] = _esearch_all_pmids(query, email, api_key)

    # Direct experimental = experimental terms AND cilia context
    direct_query = f"{DIRECT_EVIDENCE_QUERY} AND {MESH_CONTEXT_QUERIES['cilia']}"
    direct_pmids = _esearch_all_pmids(direct_query, email, api_key)

    hts_pmids = _esearch_all_pmids(HTS_QUERY, email, api_key)

    logger.info(
        "fetch_context_pmid_sets_complete",
        context_sizes={k: len(v) for k, v in context_sets.items()},
        direct_experimental=len(direct_pmids),
        hts=len(hts_pmids),
    )
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({
            "contexts": {
                name: sorted(pmids) for name, pmids in context_sets.items()
            },
            "direct_experimental": sorted(direct_pmids),
            "hts": sorted(hts_pmids),
        }))
        logger.info("context_pmid_cache_written", path=str(cache_path))
    return context_sets, direct_pmids, hts_pmids


# -- Local counting ------------------------------------------------------------


def count_context_intersections(
    gene_pmid_map: dict[str, set[int]],
    context_pmid_sets: dict[str, set[int]],
    direct_experimental_pmids: set[int],
    hts_pmids: set[int],
    pipeline_symbols: list[str],
) -> pl.DataFrame:
    """Count per-gene context intersections from PMID sets.

    For each gene in pipeline_symbols, counts how many of its PMIDs
    overlap with each context PMID set. Genes not found in gene2pubmed
    get NULL counts (not 0) to preserve the pipeline's NULL semantics:
    "unknown" is different from "zero evidence".

    Args:
        gene_pmid_map: gene_symbol -> set of PMIDs.
        context_pmid_sets: context_name -> set of PMIDs.
        direct_experimental_pmids: PMIDs from experimental evidence queries.
        hts_pmids: PMIDs from HTS screen queries.
        pipeline_symbols: List of gene symbols from our pipeline.

    Returns:
        DataFrame with columns: gene_symbol, total_pubmed_count,
        cilia_context_count, sensory_context_count,
        cytoskeleton_context_count, cell_polarity_context_count,
        direct_experimental_count, direct_experimental_context_count,
        hts_screen_count.
    """
    rows = []
    for symbol in pipeline_symbols:
        pmids = gene_pmid_map.get(symbol)

        if pmids is None:
            # Gene not in gene2pubmed -- NULL counts (not 0)
            rows.append({
                "gene_symbol": symbol,
                "total_pubmed_count": None,
                "cilia_context_count": None,
                "sensory_context_count": None,
                "cytoskeleton_context_count": None,
                "cell_polarity_context_count": None,
                "direct_experimental_count": None,
                "direct_experimental_context_count": None,
                "hts_screen_count": None,
            })
        else:
            context_pmids = (
                context_pmid_sets.get("cilia", set())
                | context_pmid_sets.get("sensory", set())
            )
            rows.append({
                "gene_symbol": symbol,
                "total_pubmed_count": len(pmids),
                "cilia_context_count": len(pmids & context_pmid_sets.get("cilia", set())),
                "sensory_context_count": len(pmids & context_pmid_sets.get("sensory", set())),
                "cytoskeleton_context_count": len(pmids & context_pmid_sets.get("cytoskeleton", set())),
                "cell_polarity_context_count": len(pmids & context_pmid_sets.get("cell_polarity", set())),
                "direct_experimental_count": len(pmids & direct_experimental_pmids),
                "direct_experimental_context_count": len(
                    pmids & direct_experimental_pmids & context_pmids
                ),
                "hts_screen_count": len(pmids & hts_pmids),
            })

    df = pl.DataFrame(rows)

    genes_known = df.filter(pl.col("total_pubmed_count").is_not_null()).height
    logger.info(
        "context_intersections_complete",
        total_genes=df.height,
        genes_in_gene2pubmed=genes_known,
        genes_with_publications=df.filter(
            pl.col("total_pubmed_count").is_not_null()
            & (pl.col("total_pubmed_count") > 0)
        ).height,
        genes_with_cilia_context=df.filter(
            pl.col("cilia_context_count").is_not_null()
            & (pl.col("cilia_context_count") > 0)
        ).height,
    )
    return df


# -- Compatibility path ------------------------------------------------------


def fetch_legacy_literature_evidence(
    gene_symbols: list[str],
    email: str,
    api_key: Optional[str] = None,
) -> pl.DataFrame:
    """Fetch per-gene counts for callers that do not provide a data directory.

    The production path is :func:`fetch_literature_evidence`, which uses the
    bulk NCBI files and six global PMID-set queries.  A small compatibility
    path is retained for older library callers and lightweight test fixtures
    that historically called ``process_literature_evidence`` without a
    ``data_dir``.  It is deliberately not used by the CLI or manuscript
    reruns, because per-gene E-utilities calls are much slower and less
    reproducible than the bulk path.
    """
    Entrez.email = email
    if api_key:
        Entrez.api_key = api_key

    def _count(query: str) -> int:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=0)
        record = Entrez.read(handle)
        close = getattr(handle, "close", None)
        if callable(close):
            close()
        return int(record.get("Count", 0))

    rows = []
    for symbol in gene_symbols:
        gene_query = f"({symbol}[Gene Name])"
        context_counts = {
            name: _count(f"{gene_query} AND {query}")
            for name, query in MESH_CONTEXT_QUERIES.items()
        }
        direct_count = _count(
            f"{gene_query} AND {DIRECT_EVIDENCE_QUERY} AND {MESH_CONTEXT_QUERIES['cilia']}"
        )
        rows.append({
            "gene_symbol": symbol,
            "total_pubmed_count": _count(gene_query),
            "cilia_context_count": context_counts["cilia"],
            "sensory_context_count": context_counts["sensory"],
            "cytoskeleton_context_count": context_counts["cytoskeleton"],
            "cell_polarity_context_count": context_counts["cell_polarity"],
            "direct_experimental_count": direct_count,
            "direct_experimental_context_count": direct_count,
            "hts_screen_count": _count(f"{gene_query} AND {HTS_QUERY}"),
        })

    return pl.DataFrame(rows)


# -- High-level orchestration --------------------------------------------------


def fetch_literature_evidence(
    gene_symbols: list[str],
    email: str,
    data_dir: Path,
    api_key: Optional[str] = None,
    force: bool = False,
    cache_only: bool = False,
) -> pl.DataFrame:
    """Fetch literature evidence for all genes using bulk data.

    Downloads gene2pubmed + gene_info from NCBI, runs 6 batch PubMed
    queries for context PMID sets, then counts per-gene intersections.

    Runtime: ~5-10 minutes (vs ~46 hours with per-gene E-utilities).

    Args:
        gene_symbols: List of HGNC gene symbols from pipeline.
        email: Email for NCBI E-utilities (required).
        data_dir: Directory for downloading bulk files.
        api_key: Optional NCBI API key.
        force: Re-download bulk files even if cached.
        cache_only: Require local bulk/context caches and never access the network.

    Returns:
        DataFrame with columns: gene_symbol, total_pubmed_count,
        cilia_context_count, sensory_context_count,
        cytoskeleton_context_count, cell_polarity_context_count,
        direct_experimental_count, direct_experimental_context_count,
        hts_screen_count.
    """
    logger.info("literature_bulk_fetch_start", gene_count=len(gene_symbols))

    # Step 1: Download bulk files
    g2p_path, gi_path = download_bulk_files(
        data_dir,
        force=force and not cache_only,
        cache_only=cache_only,
    )

    # Step 2: Parse bulk files
    gene2pubmed = parse_gene2pubmed(g2p_path)
    gene_info = parse_gene_info(gi_path)

    # Step 3: Build gene->PMID map
    gene_pmid_map = build_gene_pmid_map(gene2pubmed, gene_info)

    # Step 4: Fetch context PMID sets (6 batch queries)
    context_sets, direct_pmids, hts_pmids = fetch_context_pmid_sets(
        email,
        api_key,
        cache_path=data_dir / "pubmed_context_sets.json",
        cache_only=cache_only,
    )

    # Step 5: Count intersections
    df = count_context_intersections(
        gene_pmid_map=gene_pmid_map,
        context_pmid_sets=context_sets,
        direct_experimental_pmids=direct_pmids,
        hts_pmids=hts_pmids,
        pipeline_symbols=gene_symbols,
    )

    logger.info("literature_bulk_fetch_complete", gene_count=df.height)
    return df

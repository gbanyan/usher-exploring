# Literature Bulk Fetch Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 46-hour NCBI E-utilities per-gene literature scrape with bulk gene2pubmed download + batch MeSH context queries, reducing runtime to ~5-10 minutes while preserving the same scoring semantics.

**Architecture:** Download NCBI's `gene2pubmed.gz` (~150MB, curated gene-to-PMID mapping) and `gene_info.gz` (~20MB, GeneID-to-symbol mapping) for local gene→PMID resolution. Run 6 batch PubMed esearch queries for context PMID sets (cilia, sensory, cytoskeleton, polarity, direct experimental, HTS). Count per-gene set intersections locally. Feed the same 7 count columns into the unchanged `transform.py` (tier classification + log2 bias-mitigated scoring).

**Tech Stack:** httpx (bulk FTP download), gzip (decompression), polars (parsing), Biopython Entrez (6 batch queries), DuckDB (storage)

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `evidence/literature/fetch.py` | **Replace** | New bulk fetch: download gene2pubmed + gene_info, batch MeSH queries, local counting |
| `evidence/literature/models.py` | **Modify** | Add bulk data URL constants, MeSH query constants |
| `evidence/literature/transform.py` | **Keep as-is** | Unchanged — same tier classification + scoring |
| `evidence/literature/load.py` | **Minor modify** | Update provenance description (queries→bulk) |
| `evidence/literature/__init__.py` | **Modify** | Update exports for new fetch functions |
| `cli/evidence_cmd.py` | **Modify** | Simplify CLI: remove batch-size, update help text, change runtime estimate |
| `tests/test_literature.py` | **Modify** | Update fetch tests for new bulk pattern, keep transform tests as-is |

---

## Chunk 1: New bulk fetch module

### Task 1: Add bulk data constants to models.py

**Files:**
- Modify: `src/usher_pipeline/evidence/literature/models.py:1-8`

- [ ] **Step 1: Add URL constants and MeSH query constants**

Add to `models.py` after the existing constants:

```python
# Bulk data URLs (NCBI Gene FTP)
GENE2PUBMED_URL = "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2pubmed.gz"
GENE_INFO_URL = "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene_info.gz"

# Human taxonomy ID for filtering bulk data
HUMAN_TAX_ID = 9606

# MeSH-based PubMed queries for context PMID sets
# Each query is run once (not per-gene) to get all relevant PMIDs
MESH_CONTEXT_QUERIES = {
    "cilia": "(Cilia[MeSH] OR Ciliopathies[MeSH] OR Flagella[MeSH] OR cilia[Title/Abstract] OR cilium[Title/Abstract] OR ciliary[Title/Abstract] OR intraflagellar[Title/Abstract])",
    "sensory": "(Retina[MeSH] OR Cochlea[MeSH] OR Hair Cells, Auditory[MeSH] OR Photoreceptor Cells[MeSH] OR Usher Syndromes[MeSH] OR retina[Title/Abstract] OR cochlea[Title/Abstract] OR hair cell[Title/Abstract] OR photoreceptor[Title/Abstract] OR vestibular[Title/Abstract] OR hearing[Title/Abstract] OR usher syndrome[Title/Abstract])",
    "cytoskeleton": "(Cytoskeleton[MeSH] OR Actins[MeSH] OR Microtubules[MeSH] OR Molecular Motor Proteins[MeSH])",
    "cell_polarity": "(Cell Polarity[MeSH] OR planar cell polarity[Title/Abstract] OR apicobasal[Title/Abstract] OR tight junction[Title/Abstract])",
}

# Direct experimental evidence query (run once globally, intersected with cilia PMIDs)
DIRECT_EVIDENCE_QUERY = "(knockout[Title/Abstract] OR knockdown[Title/Abstract] OR mutation[Title/Abstract] OR CRISPR[Title/Abstract] OR siRNA[Title/Abstract] OR morpholino[Title/Abstract] OR null allele[Title/Abstract])"

# HTS screen query
HTS_QUERY = "(screen[Title/Abstract] OR proteomics[Title/Abstract] OR transcriptomics[Title/Abstract])"
```

- [ ] **Step 2: Verify no import errors**

Run: `.venv/bin/python -c "from usher_pipeline.evidence.literature.models import GENE2PUBMED_URL, MESH_CONTEXT_QUERIES; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/usher_pipeline/evidence/literature/models.py
git commit -m "feat: add bulk data URL and MeSH query constants for literature layer"
```

---

### Task 2: Write tests for new bulk fetch

**Files:**
- Create: `tests/test_literature_bulk.py`

- [ ] **Step 1: Write tests for bulk parsing and counting logic**

Create `tests/test_literature_bulk.py`:

```python
"""Unit tests for bulk literature fetch (gene2pubmed + MeSH batch queries)."""

import gzip
from pathlib import Path

import polars as pl
import pytest

from usher_pipeline.evidence.literature.fetch import (
    parse_gene2pubmed,
    parse_gene_info,
    build_gene_pmid_map,
    count_context_intersections,
)


# Sample gene2pubmed TSV (real format from NCBI)
SAMPLE_GENE2PUBMED = (
    "#tax_id\tGeneID\tPubMed_ID\n"
    "9606\t1\t30591045\n"
    "9606\t1\t30592043\n"
    "9606\t1\t28854372\n"
    "9606\t2\t12345678\n"
    "9606\t2\t30591045\n"  # Shared PMID with gene 1
    "9606\t3\t99999999\n"
    "10090\t100\t11111111\n"  # Mouse — should be filtered out
)

# Sample gene_info TSV (real format from NCBI)
SAMPLE_GENE_INFO = (
    "#tax_id\tGeneID\tSymbol\tLocusTag\tSynonyms\tdbXrefs\tchromosome\tmap_location\t"
    "description\ttype_of_gene\tSymbol_from_nomenclature_authority\tFull_name_from_nomenclature_authority\t"
    "Nomenclature_status\tOther_designations\tModification_date\tFeature_type\n"
    "9606\t1\tA1BG\t-\tA1B|ABG|GAB|HYST2477\tMIM:138670|HGNC:HGNC:5|Ensembl:ENSG00000121410\t19\t19q13.43\t"
    "alpha-1-B glycoprotein\tprotein-coding\tA1BG\talpha-1-B glycoprotein\tO\t"
    "alpha-1B-glycoprotein|HEL-S-163pA|epididymis secretory sperm binding protein Li 163pA\t20240101\t-\n"
    "9606\t2\tA2M\t-\tA2MD|CPAMD5|FWP007|S863-7\tMIM:103950|HGNC:HGNC:7|Ensembl:ENSG00000175899\t12\t12p13.31\t"
    "alpha-2-macroglobulin\tprotein-coding\tA2M\talpha-2-macroglobulin\tO\t"
    "alpha-2-macroglobulin|C3 and PZP-like alpha-2-macroglobulin domain-containing protein 5\t20240101\t-\n"
    "9606\t3\tA2MP1\t-\tA2MP\tHGNC:HGNC:8\t12\t12p13.31\t"
    "alpha-2-macroglobulin pseudogene 1\tpseudo\tA2MP1\talpha-2-macroglobulin pseudogene 1\tO\t-\t20240101\t-\n"
)


def _write_gz(tmp_path: Path, filename: str, content: str) -> Path:
    gz_path = tmp_path / filename
    with gzip.open(gz_path, "wt") as f:
        f.write(content)
    return gz_path


def test_parse_gene2pubmed_filters_human(tmp_path):
    """gene2pubmed parser should only return human (tax_id=9606) entries."""
    gz_path = _write_gz(tmp_path, "gene2pubmed.gz", SAMPLE_GENE2PUBMED)
    df = parse_gene2pubmed(gz_path)

    assert df.height == 6, f"Expected 6 human rows, got {df.height}"
    assert "tax_id" not in df.columns, "tax_id should be dropped after filtering"
    assert set(df.columns) == {"gene_id", "pmid"}


def test_parse_gene2pubmed_types(tmp_path):
    """gene_id and pmid should be integers."""
    gz_path = _write_gz(tmp_path, "gene2pubmed.gz", SAMPLE_GENE2PUBMED)
    df = parse_gene2pubmed(gz_path)

    assert df["gene_id"].dtype == pl.Int64
    assert df["pmid"].dtype == pl.Int64


def test_parse_gene_info(tmp_path):
    """gene_info parser should return gene_id → symbol mapping for human protein-coding genes."""
    gz_path = _write_gz(tmp_path, "gene_info.gz", SAMPLE_GENE_INFO)
    df = parse_gene_info(gz_path)

    # Should have gene_id and symbol columns
    assert set(df.columns) == {"gene_id", "gene_symbol"}
    # Should only include protein-coding (not pseudo)
    assert df.height == 2
    symbols = df["gene_symbol"].to_list()
    assert "A1BG" in symbols
    assert "A2M" in symbols
    assert "A2MP1" not in symbols  # pseudogene filtered out


def test_build_gene_pmid_map(tmp_path):
    """build_gene_pmid_map should return dict of gene_symbol → set of PMIDs."""
    g2p_gz = _write_gz(tmp_path, "gene2pubmed.gz", SAMPLE_GENE2PUBMED)
    gi_gz = _write_gz(tmp_path, "gene_info.gz", SAMPLE_GENE_INFO)

    gene2pubmed = parse_gene2pubmed(g2p_gz)
    gene_info = parse_gene_info(gi_gz)

    pmid_map = build_gene_pmid_map(gene2pubmed, gene_info)

    assert isinstance(pmid_map, dict)
    assert "A1BG" in pmid_map
    assert "A2M" in pmid_map
    assert len(pmid_map["A1BG"]) == 3  # 3 PMIDs for gene_id=1
    assert len(pmid_map["A2M"]) == 2   # 2 PMIDs for gene_id=2
    # Check shared PMID
    assert 30591045 in pmid_map["A1BG"]
    assert 30591045 in pmid_map["A2M"]


def test_count_context_intersections():
    """count_context_intersections should compute per-gene counts from PMID sets."""
    gene_pmid_map = {
        "GENE1": {1, 2, 3, 4, 5},       # 5 total PMIDs
        "GENE2": {10, 20},               # 2 total PMIDs
        "GENE3": set(),                   # 0 PMIDs
    }

    context_pmid_sets = {
        "cilia": {1, 2, 10, 100},        # GENE1 has 2 overlap, GENE2 has 1
        "sensory": {2, 3, 20, 200},      # GENE1 has 2 overlap, GENE2 has 1
        "cytoskeleton": {4, 100},         # GENE1 has 1 overlap
        "cell_polarity": set(),           # No PMIDs
    }

    direct_exp_pmids = {1, 10}            # GENE1 has 1 overlap, GENE2 has 1
    hts_pmids = {5, 20}                   # GENE1 has 1 overlap, GENE2 has 1

    # Filter to only our pipeline symbols
    pipeline_symbols = ["GENE1", "GENE2", "GENE3"]

    df = count_context_intersections(
        gene_pmid_map=gene_pmid_map,
        context_pmid_sets=context_pmid_sets,
        direct_experimental_pmids=direct_exp_pmids,
        hts_pmids=hts_pmids,
        pipeline_symbols=pipeline_symbols,
    )

    assert df.height == 3
    assert set(df.columns) == {
        "gene_symbol", "total_pubmed_count",
        "cilia_context_count", "sensory_context_count",
        "cytoskeleton_context_count", "cell_polarity_context_count",
        "direct_experimental_count", "hts_screen_count",
    }

    g1 = df.filter(pl.col("gene_symbol") == "GENE1")
    assert g1["total_pubmed_count"][0] == 5
    assert g1["cilia_context_count"][0] == 2
    assert g1["sensory_context_count"][0] == 2
    assert g1["cytoskeleton_context_count"][0] == 1
    assert g1["cell_polarity_context_count"][0] == 0
    assert g1["direct_experimental_count"][0] == 1
    assert g1["hts_screen_count"][0] == 1

    # GENE3 with no PMIDs should have 0 counts (not NULL — gene exists but has no literature)
    g3 = df.filter(pl.col("gene_symbol") == "GENE3")
    assert g3["total_pubmed_count"][0] == 0
    assert g3["cilia_context_count"][0] == 0


def test_count_context_intersections_missing_symbol():
    """Genes in pipeline but not in gene2pubmed should get 0 counts."""
    gene_pmid_map = {"GENE1": {1, 2}}
    context_pmid_sets = {"cilia": {1}, "sensory": set(), "cytoskeleton": set(), "cell_polarity": set()}

    df = count_context_intersections(
        gene_pmid_map=gene_pmid_map,
        context_pmid_sets=context_pmid_sets,
        direct_experimental_pmids=set(),
        hts_pmids=set(),
        pipeline_symbols=["GENE1", "GENE_MISSING"],
    )

    assert df.height == 2
    missing = df.filter(pl.col("gene_symbol") == "GENE_MISSING")
    assert missing["total_pubmed_count"][0] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_literature_bulk.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Commit test file**

```bash
git add tests/test_literature_bulk.py
git commit -m "test: add unit tests for bulk literature fetch"
```

---

### Task 3: Implement new bulk fetch.py

**Files:**
- Replace: `src/usher_pipeline/evidence/literature/fetch.py`

- [ ] **Step 1: Replace fetch.py with bulk implementation**

Replace the entire `src/usher_pipeline/evidence/literature/fetch.py`:

```python
"""Bulk literature evidence fetch via gene2pubmed + batch MeSH queries.

Instead of querying PubMed per-gene (135K API calls, ~46 hours), this module:
1. Downloads NCBI gene2pubmed.gz (~150MB) — curated gene→PMID mapping
2. Downloads NCBI gene_info.gz (~20MB) — GeneID→symbol mapping
3. Runs 6 batch PubMed queries for context PMID sets (cilia, sensory, etc.)
4. Counts per-gene set intersections locally

Total runtime: ~5-10 minutes (vs 46 hours).
"""

import gzip
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
    SEARCH_CONTEXTS,
)

logger = structlog.get_logger(__name__)


# ── Bulk file download ──────────────────────────────────────────────


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
    logger.info("bulk_download_complete", path=str(dest), size_mb=round(dest.stat().st_size / 1024 / 1024, 1))
    return dest


def download_bulk_files(data_dir: Path, force: bool = False) -> tuple[Path, Path]:
    """Download gene2pubmed.gz and gene_info.gz from NCBI.

    Args:
        data_dir: Directory to save downloaded files.
        force: Re-download even if files exist.

    Returns:
        Tuple of (gene2pubmed_path, gene_info_path).
    """
    data_dir = Path(data_dir)
    lit_dir = data_dir / "literature"

    g2p_path = _download_gz(GENE2PUBMED_URL, lit_dir / "gene2pubmed.gz", force)
    gi_path = _download_gz(GENE_INFO_URL, lit_dir / "gene_info.gz", force)

    return g2p_path, gi_path


# ── Bulk file parsing ────────────────────────────────────────────────


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

    logger.info("gene2pubmed_parsed", human_rows=df.height, unique_genes=df["gene_id"].n_unique())
    return df


def parse_gene_info(gz_path: Path) -> pl.DataFrame:
    """Parse gene_info.gz for human protein-coding gene_id → symbol mapping.

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
            (pl.col("tax_id") == HUMAN_TAX_ID) &
            (pl.col("type_of_gene") == "protein-coding")
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
    """Build gene_symbol → set of PMIDs mapping.

    Joins gene2pubmed (gene_id→pmid) with gene_info (gene_id→symbol)
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


# ── Batch PubMed queries for context PMID sets ───────────────────────


def _esearch_all_pmids(query: str, email: str, api_key: Optional[str] = None) -> set[int]:
    """Run a single PubMed esearch and retrieve ALL matching PMIDs.

    Uses usehistory for server-side result storage, then paginates
    through efetch to get all PMIDs.

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

    # Paginate through efetch to get all PMIDs
    pmids = set()
    batch_size = 10000
    for start in range(0, total, batch_size):
        handle = Entrez.efetch(
            db="pubmed",
            rettype="uilist",
            retmode="text",
            retstart=start,
            retmax=batch_size,
            webenv=web_env,
            query_key=query_key,
        )
        batch_text = handle.read()
        handle.close()

        for line in batch_text.strip().split("\n"):
            line = line.strip()
            if line.isdigit():
                pmids.add(int(line))

    logger.info("esearch_context_complete", query=query[:80], retrieved_pmids=len(pmids))
    return pmids


def fetch_context_pmid_sets(
    email: str,
    api_key: Optional[str] = None,
) -> tuple[dict[str, set[int]], set[int], set[int]]:
    """Fetch PMID sets for each context via batch PubMed queries.

    Runs 6 queries total (4 contexts + direct_experimental + HTS).

    Args:
        email: Email for NCBI E-utilities.
        api_key: Optional NCBI API key.

    Returns:
        Tuple of (context_pmid_sets, direct_experimental_pmids, hts_pmids).
        context_pmid_sets maps context name → set of PMIDs.
    """
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
    return context_sets, direct_pmids, hts_pmids


# ── Local counting ───────────────────────────────────────────────────


def count_context_intersections(
    gene_pmid_map: dict[str, set[int]],
    context_pmid_sets: dict[str, set[int]],
    direct_experimental_pmids: set[int],
    hts_pmids: set[int],
    pipeline_symbols: list[str],
) -> pl.DataFrame:
    """Count per-gene context intersections from PMID sets.

    For each gene in pipeline_symbols, counts how many of its PMIDs
    overlap with each context PMID set.

    Args:
        gene_pmid_map: gene_symbol → set of PMIDs.
        context_pmid_sets: context_name → set of PMIDs.
        direct_experimental_pmids: PMIDs from experimental evidence queries.
        hts_pmids: PMIDs from HTS screen queries.
        pipeline_symbols: List of gene symbols from our pipeline.

    Returns:
        DataFrame with same 7 count columns as the old per-gene fetch:
        gene_symbol, total_pubmed_count, cilia_context_count,
        sensory_context_count, cytoskeleton_context_count,
        cell_polarity_context_count, direct_experimental_count,
        hts_screen_count.
    """
    rows = []
    for symbol in pipeline_symbols:
        pmids = gene_pmid_map.get(symbol, set())
        row = {
            "gene_symbol": symbol,
            "total_pubmed_count": len(pmids),
            "cilia_context_count": len(pmids & context_pmid_sets.get("cilia", set())),
            "sensory_context_count": len(pmids & context_pmid_sets.get("sensory", set())),
            "cytoskeleton_context_count": len(pmids & context_pmid_sets.get("cytoskeleton", set())),
            "cell_polarity_context_count": len(pmids & context_pmid_sets.get("cell_polarity", set())),
            "direct_experimental_count": len(pmids & direct_experimental_pmids),
            "hts_screen_count": len(pmids & hts_pmids),
        }
        rows.append(row)

    df = pl.DataFrame(rows)

    logger.info(
        "context_intersections_complete",
        total_genes=df.height,
        genes_with_publications=df.filter(pl.col("total_pubmed_count") > 0).height,
        genes_with_cilia_context=df.filter(pl.col("cilia_context_count") > 0).height,
    )
    return df


# ── High-level orchestration ─────────────────────────────────────────


def fetch_literature_evidence(
    gene_symbols: list[str],
    email: str,
    data_dir: Path,
    api_key: Optional[str] = None,
    force: bool = False,
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

    Returns:
        DataFrame with columns: gene_symbol, total_pubmed_count,
        cilia_context_count, sensory_context_count,
        cytoskeleton_context_count, cell_polarity_context_count,
        direct_experimental_count, hts_screen_count.
    """
    logger.info("literature_bulk_fetch_start", gene_count=len(gene_symbols))

    # Step 1: Download bulk files
    g2p_path, gi_path = download_bulk_files(data_dir, force=force)

    # Step 2: Parse bulk files
    gene2pubmed = parse_gene2pubmed(g2p_path)
    gene_info = parse_gene_info(gi_path)

    # Step 3: Build gene→PMID map
    gene_pmid_map = build_gene_pmid_map(gene2pubmed, gene_info)

    # Step 4: Fetch context PMID sets (6 batch queries)
    context_sets, direct_pmids, hts_pmids = fetch_context_pmid_sets(email, api_key)

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
```

- [ ] **Step 2: Run tests**

Run: `.venv/bin/python -m pytest tests/test_literature_bulk.py -v`
Expected: All PASS (tests only exercise parse + counting, not network)

- [ ] **Step 3: Commit**

```bash
git add src/usher_pipeline/evidence/literature/fetch.py
git commit -m "feat: replace per-gene E-utilities fetch with bulk gene2pubmed + batch MeSH"
```

---

## Chunk 2: Update transform, CLI, package exports, tests

### Task 4: Update process_literature_evidence in transform.py

**Files:**
- Modify: `src/usher_pipeline/evidence/literature/transform.py:204-283`

The `process_literature_evidence()` function in transform.py calls the old `fetch_literature_evidence()` with email/api_key/batch_size/checkpoint args. Update it to call the new bulk fetch with `data_dir` instead.

- [ ] **Step 1: Update process_literature_evidence signature and body**

In `transform.py`, replace `process_literature_evidence()` (lines 204-283):

```python
def process_literature_evidence(
    gene_ids: list[str],
    gene_symbol_map: pl.DataFrame,
    email: str,
    data_dir: Path,
    api_key: Optional[str] = None,
    force: bool = False,
) -> pl.DataFrame:
    """End-to-end literature evidence processing pipeline.

    1. Map gene IDs to symbols
    2. Fetch bulk literature evidence (gene2pubmed + MeSH queries)
    3. Classify evidence tiers
    4. Compute quality-weighted scores
    5. Join back to gene IDs

    Args:
        gene_ids: List of Ensembl gene IDs
        gene_symbol_map: DataFrame with columns: gene_id, gene_symbol
        email: Email for NCBI E-utilities (required)
        data_dir: Directory for bulk file downloads
        api_key: Optional NCBI API key
        force: Re-download bulk files even if cached

    Returns:
        DataFrame with columns: gene_id, gene_symbol, total_pubmed_count,
        cilia_context_count, sensory_context_count, cytoskeleton_context_count,
        cell_polarity_context_count, direct_experimental_count, hts_screen_count,
        evidence_tier, literature_score_normalized
    """
    from usher_pipeline.evidence.literature.fetch import fetch_literature_evidence

    logger.info(
        "literature_process_start",
        gene_count=len(gene_ids),
    )

    # Step 1: Map gene IDs to symbols
    gene_map = gene_symbol_map.filter(pl.col("gene_id").is_in(gene_ids))
    unique_symbols = gene_map["gene_symbol"].unique().to_list()

    logger.info(
        "literature_gene_mapping",
        input_ids=len(gene_ids),
        mapped_symbols=len(unique_symbols),
    )

    # Step 2: Fetch bulk literature evidence
    lit_df = fetch_literature_evidence(
        gene_symbols=unique_symbols,
        email=email,
        data_dir=data_dir,
        api_key=api_key,
        force=force,
    )

    # Step 3: Classify evidence tiers
    lit_df = classify_evidence_tier(lit_df)

    # Step 4: Compute quality-weighted scores
    lit_df = compute_literature_score(lit_df)

    # Step 5: Join back to gene IDs
    result_df = gene_map.join(lit_df, on="gene_symbol", how="left")

    logger.info("literature_process_complete", total_genes=len(result_df))
    return result_df
```

Also add `from pathlib import Path` to the imports at the top of transform.py.

- [ ] **Step 2: Run existing transform tests (should still pass)**

Run: `.venv/bin/python -m pytest tests/test_literature.py -v -k "not mock"`
Expected: All PASS (transform tests don't touch fetch)

- [ ] **Step 3: Commit**

```bash
git add src/usher_pipeline/evidence/literature/transform.py
git commit -m "feat: update process_literature_evidence to use bulk fetch"
```

---

### Task 5: Update load.py provenance description

**Files:**
- Modify: `src/usher_pipeline/evidence/literature/load.py:53-54`

- [ ] **Step 1: Update estimated query count in provenance**

In `load.py`, change line 54:

```python
    # Old: total_queries = len(df) * 6
    # New: 6 batch queries + 2 bulk downloads
    total_queries = 8  # 6 batch PubMed queries + 2 bulk FTP downloads
```

- [ ] **Step 2: Commit**

```bash
git add src/usher_pipeline/evidence/literature/load.py
git commit -m "fix: update literature provenance to reflect bulk fetch (8 queries, not 120K)"
```

---

### Task 6: Update __init__.py exports

**Files:**
- Modify: `src/usher_pipeline/evidence/literature/__init__.py`

- [ ] **Step 1: Update exports**

Replace the fetch imports:

```python
from usher_pipeline.evidence.literature.fetch import (
    fetch_literature_evidence,
    download_bulk_files,
    parse_gene2pubmed,
    parse_gene_info,
    build_gene_pmid_map,
    count_context_intersections,
)
```

Remove `query_pubmed_gene` from `__all__` and add the new functions:
```python
    # Fetch (bulk)
    "fetch_literature_evidence",
    "download_bulk_files",
    "parse_gene2pubmed",
    "parse_gene_info",
    "build_gene_pmid_map",
    "count_context_intersections",
```

- [ ] **Step 2: Verify imports**

Run: `.venv/bin/python -c "from usher_pipeline.evidence.literature import fetch_literature_evidence, parse_gene2pubmed; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/usher_pipeline/evidence/literature/__init__.py
git commit -m "feat: update literature package exports for bulk fetch"
```

---

### Task 7: Update CLI evidence command

**Files:**
- Modify: `src/usher_pipeline/cli/evidence_cmd.py:977-1230`

- [ ] **Step 1: Simplify CLI options and update help text**

Update the `@evidence.command('literature')` section:

1. Remove `--batch-size` option (no longer needed — no per-gene batching)
2. Update `--email` help text
3. Update `--api-key` help text (still useful for batch queries but less critical)
4. Update docstring: remove "3-11 hours" warning, say "~5-10 minutes"
5. Remove partial checkpoint logic (bulk download is atomic)
6. Update the call to `process_literature_evidence()` — pass `data_dir` instead of `batch_size`/`checkpoint_df`/`checkpoint_callback`
7. Remove `--force` behavior on partial checkpoints (no partial checkpoints with bulk approach)

The key changes to the function body:

```python
@evidence.command('literature')
@click.option('--force', is_flag=True, help='Re-download and reprocess data')
@click.option('--email', required=True, help='Email for NCBI E-utilities (required by PubMed API)')
@click.option('--api-key', default=None, help='NCBI API key (optional, speeds up 6 batch queries)')
@click.pass_context
def literature(ctx, force, email, api_key):
    """Fetch and load literature evidence using bulk data.

    Downloads gene2pubmed (~150MB) and gene_info (~20MB) from NCBI,
    runs 6 batch PubMed queries for context classification, then counts
    per-gene intersections locally. Runtime: ~5-10 minutes.
    ...
```

Replace the runtime warning block with:
```python
    click.echo(click.style("  Bulk mode: gene2pubmed + batch MeSH queries", fg='cyan'))
    click.echo(click.style("  Estimated runtime: ~5-10 minutes", fg='cyan'))
    click.echo()
```

Remove the partial checkpoint load/save logic. Replace the `process_literature_evidence()` call:
```python
        df = process_literature_evidence(
            gene_ids=gene_ids,
            gene_symbol_map=gene_symbol_map,
            email=email,
            data_dir=config.data_dir,
            api_key=api_key,
            force=force,
        )
```

- [ ] **Step 2: Commit**

```bash
git add src/usher_pipeline/cli/evidence_cmd.py
git commit -m "feat: simplify literature CLI for bulk fetch (~5min vs ~46hrs)"
```

---

### Task 8: Update existing literature tests

**Files:**
- Modify: `tests/test_literature.py:244-292`

- [ ] **Step 1: Remove the old mock Entrez test**

The `test_query_pubmed_gene_mock` test (lines 244-292) tests the old per-gene `query_pubmed_gene()` which no longer exists. Remove it.

The transform tests (test_direct_experimental_classification through test_score_normalization) should remain — they test classify_evidence_tier and compute_literature_score which are unchanged.

Update the imports at the top to remove `query_pubmed_gene` references:
```python
from usher_pipeline.evidence.literature import (
    classify_evidence_tier,
    compute_literature_score,
    SEARCH_CONTEXTS,
)
```
(Remove `DIRECT_EVIDENCE_TERMS` if only used by the deleted test.)

- [ ] **Step 2: Run all literature tests**

Run: `.venv/bin/python -m pytest tests/test_literature.py tests/test_literature_bulk.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_literature.py
git commit -m "test: remove legacy per-gene Entrez mock, keep transform tests"
```

---

### Task 9: Run full test suite + update CLAUDE.md

- [ ] **Step 1: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v -k "not integration"`
Expected: All PASS (same 10 pre-existing gnomAD failures, 0 new failures)

- [ ] **Step 2: Update CLAUDE.md**

Update the literature layer description in Known Limitations:
```markdown
- **Literature layer**: Uses bulk gene2pubmed (~150MB) + 6 batch PubMed MeSH queries. Runtime ~5-10 minutes. Bulk files cached in `data/literature/`. Use `--force` to re-download.
```

Remove the old "Literature layer is slow: ~8 genes/minute" limitation.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for bulk literature fetch"
```

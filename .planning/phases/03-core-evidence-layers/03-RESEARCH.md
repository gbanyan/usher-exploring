# Phase 3: Core Evidence Layers - Research

**Researched:** 2026-02-11
**Domain:** Biomedical Data Integration, Multi-Source Evidence Retrieval
**Confidence:** MEDIUM-HIGH

## Summary

Phase 3 implements six distinct evidence retrieval modules that query heterogeneous biomedical APIs and databases. The research identifies a landscape of well-documented REST APIs (UniProt, GTEx, PubMed), Python-native data access libraries (cellxgene_census, mygene), and specialized file-based resources (HPA, MGI, ZFIN, IMPC).

The core technical challenge is **heterogeneous data integration**: each source has different identifiers (Ensembl, HGNC, Entrez), data formats (JSON, TSV, XML, HDF5), update frequencies, and evidence quality paradigms. Success requires robust identifier mapping, NULL-versus-zero handling, API rate limiting with exponential backoff, and provenance tracking per source.

The existing codebase patterns (httpx with retry, polars lazy evaluation, DuckDB storage, provenance sidecars, checkpoint-restart) align well with biomedical pipeline best practices identified in 2026 literature.

**Primary recommendation:** Use specialized Python libraries (cellxgene_census, pybiomart, mygene) where available for complex APIs; fall back to httpx+retry for simple REST endpoints; implement unified identifier resolution layer before evidence retrieval; treat missing data as NULL (not zero) throughout; track data source versions in provenance files.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28+ | HTTP client with retry/backoff | Built-in HTTP/2, async support, superior to requests for API-heavy workloads |
| polars | 1.20+ | Data processing with lazy evaluation | 5-20x faster than pandas, query optimizer crucial for large datasets |
| DuckDB | 1.2+ | Analytics database | Native DataFrame integration, memory-efficient (processes TB-scale in <3GB RAM) |
| pydantic | 2.x | Config validation | Already in codebase, ensures type-safe API responses |
| structlog | 24.x | Structured logging | Already in codebase, essential for debugging multi-source pipelines |
| tenacity | 9.x | Retry with exponential backoff | Industry standard for resilient API clients, better than manual retry logic |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cellxgene_census | 1.19+ | CZI CELLxGENE Census API | EXPR-02 scRNA-seq retrieval (photoreceptor, hair cells) |
| pybiomart | 0.2+ | Ensembl BioMart queries | PROT-01 domain queries, ortholog mapping (ANIM-03) |
| mygene | 3.2+ | MyGene.Info service | Gene annotation queries (ANNOT-01), cross-species mapping |
| biopython | 1.84+ | Sequence/structure parsing | UniProt XML/flat file parsing, GO term extraction |
| ratelimit | 2.2+ | Decorator-based rate limiting | Simple rate limit enforcement (3 req/sec NCBI, 200 req/sec UniProt) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests | httpx has native async, HTTP/2, better connection pooling |
| cellxgene_census | Manual HDF5/AnnData | cellxgene_census handles versioning, remote access; manual requires downloads |
| pybiomart | Direct XML queries to BioMart | pybiomart handles pagination, session management automatically |
| mygene | Direct MyGene REST | mygene provides batch queries, pandas integration out-of-box |
| tenacity | Manual retry loops | tenacity provides jitter, backoff strategies, condition-based retry |

**Installation:**
```bash
pip install httpx tenacity cellxgene_census pybiomart mygene biopython ratelimit
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── evidence/
│   ├── __init__.py
│   ├── annotation.py       # ANNOT-01/02/03: GO terms, UniProt scores
│   ├── expression.py        # EXPR-01/02/03/04: HPA, GTEx, CellxGene
│   ├── protein.py           # PROT-01/02/03/04: UniProt features, domains
│   ├── localization.py      # LOCA-01/02/03: HPA subcellular, proteomics
│   ├── animal_models.py     # ANIM-01/02/03: MGI, ZFIN, IMPC
│   ├── literature.py        # LITE-01/02/03: PubMed queries, scoring
│   └── common/
│       ├── identifier_mapping.py  # Unified ID resolution
│       ├── api_client.py          # Base httpx client with retry
│       ├── normalization.py       # 0-1 scaling, NULL handling
│       └── provenance.py          # Source version tracking
```

### Pattern 1: API Client with Exponential Backoff
**What:** httpx client configured with tenacity retry decorator for rate-limited APIs
**When to use:** All external API calls (UniProt, GTEx, PubMed, MGI, ZFIN)
**Example:**
```python
# Source: https://easyparser.com/blog/api-error-handling-retry-strategies-python-guide (2026)
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
import structlog

logger = structlog.get_logger()

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),  # 4s, 8s, 16s, 32s, 60s
    retry=retry_if_exception_type(httpx.HTTPStatusError),
    before_sleep=lambda retry_state: logger.warning(
        "api_retry",
        attempt=retry_state.attempt_number,
        wait=retry_state.next_action.sleep
    )
)
def fetch_with_retry(client: httpx.Client, url: str, params: dict) -> dict:
    """Fetch JSON from API with exponential backoff."""
    response = client.get(url, params=params, timeout=30.0)
    response.raise_for_status()
    return response.json()
```

### Pattern 2: Batch Query with Rate Limiting
**What:** Process large gene lists in batches respecting API rate limits
**When to use:** UniProt queries (200 req/sec), PubMed E-utils (3 req/sec without key, 10 with)
**Example:**
```python
# Source: Based on UniProt API docs and rate limiting best practices
from ratelimit import limits, sleep_and_retry
from typing import List, Iterator
import more_itertools

@sleep_and_retry
@limits(calls=200, period=1)  # 200 requests per second (UniProt limit)
def query_uniprot_single(gene_id: str) -> dict:
    """Query single gene from UniProt."""
    return fetch_with_retry(
        client,
        f"https://rest.uniprot.org/uniprotkb/search",
        params={"query": f"gene:{gene_id}", "format": "json"}
    )

def query_uniprot_batch(gene_ids: List[str], batch_size: int = 500) -> Iterator[dict]:
    """Process genes in batches to optimize memory and API usage."""
    # Source: Batch optimization best practices 2026
    for batch in more_itertools.chunked(gene_ids, batch_size):
        # Option 1: Batch endpoint if available
        if supports_batch_endpoint:
            yield fetch_batch_endpoint(batch)
        # Option 2: Individual requests with rate limiting
        else:
            for gene_id in batch:
                yield query_uniprot_single(gene_id)
```

### Pattern 3: Identifier Mapping with Fallback Chain
**What:** Resolve gene identifiers across namespaces (HGNC → Ensembl → Entrez → UniProt)
**When to use:** Before any evidence retrieval to ensure consistent identifiers
**Example:**
```python
# Source: MyGene.info and identifier mapping best practices
import mygene

mg = mygene.MyGeneInfo()

def resolve_gene_identifiers(gene_symbols: List[str]) -> pl.DataFrame:
    """Map gene symbols to standard identifiers with confidence scores.

    Returns DataFrame with columns:
    - input_symbol: original input
    - hgnc_id: HGNC identifier (authoritative for human)
    - ensembl_gene_id: Ensembl gene ID
    - entrez_id: NCBI Entrez/Gene ID
    - uniprot_id: UniProt accession (primary isoform)
    - mapping_confidence: HIGH/MEDIUM/LOW based on source agreement
    """
    # MyGene.info aggregates HGNC, Ensembl, NCBI with conflict resolution
    results = mg.querymany(
        gene_symbols,
        scopes='symbol,alias',
        fields='HGNC,ensembl.gene,entrezgene,uniprot.Swiss-Prot',
        species='human',
        as_dataframe=True
    )

    # Assign confidence based on source agreement
    # HIGH: All 3 sources agree (HGNC, Ensembl, NCBI)
    # MEDIUM: 2 sources agree
    # LOW: Single source or conflicting mappings
    return (
        pl.from_pandas(results)
        .with_columns([
            pl.when(
                pl.col("HGNC").is_not_null() &
                pl.col("ensembl.gene").is_not_null() &
                pl.col("entrezgene").is_not_null()
            ).then(pl.lit("HIGH"))
            .when(
                (pl.col("HGNC").is_not_null() & pl.col("ensembl.gene").is_not_null()) |
                (pl.col("HGNC").is_not_null() & pl.col("entrezgene").is_not_null()) |
                (pl.col("ensembl.gene").is_not_null() & pl.col("entrezgene").is_not_null())
            ).then(pl.lit("MEDIUM"))
            .otherwise(pl.lit("LOW"))
            .alias("mapping_confidence")
        ])
    )
```

### Pattern 4: NULL Preservation in Evidence Scoring
**What:** Distinguish "no data" (NULL) from "no evidence" (zero score)
**When to use:** All evidence layers when data is unavailable
**Example:**
```python
# Source: Biological data NULL handling best practices
def normalize_expression_score(
    expression_values: pl.DataFrame,
    tissue: str
) -> pl.DataFrame:
    """Normalize tissue expression to 0-1 scale preserving NULLs.

    NULL = data not available for this gene/tissue
    0.0 = gene confirmed not expressed in tissue
    """
    return expression_values.with_columns([
        # Only normalize non-null values
        pl.when(pl.col(f"{tissue}_tpm").is_not_null())
        .then(
            (pl.col(f"{tissue}_tpm") - pl.col(f"{tissue}_tpm").min()) /
            (pl.col(f"{tissue}_tpm").max() - pl.col(f"{tissue}_tpm").min())
        )
        .otherwise(None)  # Preserve NULL for missing data
        .alias(f"{tissue}_score")
    ])
```

### Pattern 5: Data Source Provenance Tracking
**What:** Record API version, query timestamp, and data version per evidence source
**When to use:** Every evidence retrieval operation
**Example:**
```python
# Source: FAIR data pipeline provenance patterns
from datetime import datetime
import json

def create_provenance_record(
    source: str,
    api_endpoint: str,
    query_params: dict,
    response_metadata: dict,
    gene_count: int
) -> dict:
    """Create standardized provenance record."""
    return {
        "source": source,
        "retrieved_at": datetime.utcnow().isoformat(),
        "api_endpoint": api_endpoint,
        "api_version": response_metadata.get("version"),
        "data_release": response_metadata.get("release"),
        "query_params": query_params,
        "gene_count": gene_count,
        "tool_versions": {
            "httpx": httpx.__version__,
            "polars": pl.__version__,
        }
    }

# Write alongside evidence data
with open(f"{output_path}_provenance.json", "w") as f:
    json.dump(provenance, f, indent=2)
```

### Anti-Patterns to Avoid
- **Don't silently replace NULL with zero:** In biological data, NULL means "unknown" not "absent". Replacing with zero corrupts downstream scoring.
- **Don't query APIs without retry logic:** Network failures are common; bare httpx.get() will fail on transient errors.
- **Don't use single identifier namespace:** Genes have multiple IDs; relying on only gene symbols leads to mapping failures.
- **Don't ignore API rate limits:** Burst requests get IP-banned; always implement rate limiting proactively.
- **Don't cache without version tracking:** Cached data becomes stale; always record source version in provenance.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CellxGene data access | HDF5 reader, AnnData parser, cloud bucket queries | cellxgene_census library | Handles versioning, remote S3 access, incremental queries; manual approach requires TB downloads |
| BioMart queries | XML request construction, pagination, session management | pybiomart library | BioMart XML protocol is complex; pybiomart handles timeouts, retries, dataset discovery |
| Gene ID mapping | Manual database queries to HGNC/Ensembl/NCBI | mygene.info service | Resolves conflicts between databases, handles aliases, one-to-many mappings; custom mapping misses edge cases |
| Exponential backoff | While loops with sleep() | tenacity library | Jitter prevents retry storms, configurable conditions, better logging; manual loops lack jitter |
| Coiled-coil prediction | Regular expressions on sequence | CoCoNat or DeepCoil APIs | Deep learning models (ProtT5, ESM2) detect non-canonical coiled-coils missed by regex; CoCoNat is 2023 SOTA |
| Transmembrane domain prediction | Hydrophobicity sliding window | Phobius web service | Phobius jointly models signal peptides and TM helices; reduces false positives from 26% to 3.9% vs TMHMM |
| PubMed parsing | XML parsing, batch download scripts | Biopython.Entrez or dedicated PubMed APIs | E-utilities have complex rate limits (3/sec without key, 10/sec with key), XML schemas change; Biopython abstracts this |
| Ortholog mapping | BLAST searches | HCOP (HGNC), DIOPT, or Ensembl Compara | Integrates 12+ orthology databases with confidence scoring; BLAST alone misses paralog disambiguation |

**Key insight:** Biomedical APIs have extensive error modes (rate limits, identifier ambiguity, version skew, missing data semantics) that specialized libraries already handle. Hand-rolling duplicates years of community debugging.

## Common Pitfalls

### Pitfall 1: Identifier Mapping Failures Cause Silent Data Loss
**What goes wrong:** Different databases use different gene identifiers. Querying UniProt with HGNC symbols fails silently; querying GTEx with UniProt accessions returns no results. Approximately 5-10% of genes have ambiguous mappings (one symbol → multiple Ensembl IDs, or vice versa).
**Why it happens:** No single authoritative gene identifier exists. HGNC is authoritative for symbols, Ensembl for genome coordinates, NCBI for literature, UniProt for protein sequences.
**How to avoid:** Implement unified identifier resolution BEFORE evidence retrieval. Use mygene.info or BioMart to map all input genes to a standard set (HGNC + Ensembl + Entrez + UniProt). Track mapping confidence (HIGH/MEDIUM/LOW) and flag LOW confidence genes for manual review.
**Warning signs:** Evidence tables have unexpectedly low gene counts; many genes score zero across all sources; log files show "gene not found" warnings.

### Pitfall 2: NULL vs Zero Confusion Corrupts Scoring
**What goes wrong:** Biological databases return NULL (missing data) for genes they haven't characterized. If pipeline replaces NULL with 0.0, downstream scoring treats "unknown" as "confirmed absent", biasing against poorly-studied genes.
**Why it happens:** Pandas/Polars default fillna(0) is easy; developers assume NULL means "no evidence" = zero score.
**How to avoid:** Preserve NULL throughout pipeline. Use `.otherwise(None)` in polars transformations. Only assign zero when data source explicitly states "not detected" (e.g., RNA-seq TPM=0 with sequencing coverage confirmed).
**Warning signs:** Poorly-annotated genes score lower than expected; genes with sparse data cluster at score=0.0; downstream ML models treat missing data as informative.

### Pitfall 3: API Rate Limits Cause IP Bans or Cascading Failures
**What goes wrong:** Burst requests to NCBI E-utilities (3 req/sec limit without API key) or UniProt (200 req/sec limit) trigger rate limiting. Without exponential backoff, retries happen immediately, compounding the problem. PubMed bans IPs that repeatedly violate limits.
**Why it happens:** Developers test with small gene lists (no rate limit hit), then deploy on 20,000 genes and flood APIs.
**How to avoid:** Use tenacity with exponential backoff (4s, 8s, 16s, 32s, 60s). Add jitter to prevent synchronized retries. Implement batch processing with ratelimit decorator. For PubMed, obtain NCBI API key (increases limit to 10 req/sec).
**Warning signs:** HTTP 429 errors in logs; requests succeed initially then fail after N genes; API returns "too many requests" errors; IP gets temporarily banned.

### Pitfall 4: Data Version Skew Across Sources
**What goes wrong:** UniProt release 2025_05, GTEx V10, HPA version 25, MGI from January 2026 have different gene annotations. A gene might be "USH2A" in HGNC but renamed to "USH2A-AS1" in newer Ensembl. Mixing versions causes identifier mismatches.
**Why it happens:** Data sources update asynchronously. UniProt releases monthly, GTEx updates yearly, HPA updates quarterly.
**How to avoid:** Record data source version in provenance files for EVERY retrieval. Pin to specific releases during development (e.g., "GTEx V10", "UniProt 2025_05"). Document version compatibility in README. Re-run full pipeline when switching versions.
**Warning signs:** Gene counts differ between evidence layers; identifier mapping fails for recently renamed genes; results not reproducible when re-run weeks later.

### Pitfall 5: Large Batch Queries Cause Memory Overflow
**What goes wrong:** Querying 20,000 genes from CellxGene Census or GTEx at once loads entire result into memory. For scRNA-seq data (millions of cells × thousands of genes), this exceeds RAM and crashes.
**Why it happens:** Developers load full result into pandas DataFrame before processing.
**How to avoid:** Use lazy evaluation (polars.scan_*), streaming queries (cellxgene_census returns iterators), and batch processing (500-1000 genes per batch). Process and write to DuckDB incrementally. For CellxGene, use `get_anndata()` with column filtering to retrieve only target tissues.
**Warning signs:** Memory usage spikes during queries; OOM errors on large gene lists; processing time increases non-linearly with gene count.

### Pitfall 6: One-to-Many Ortholog Mappings Inflate Results
**What goes wrong:** Human gene maps to 3 mouse orthologs (paralogs from genome duplication). Naive join inflates phenotype table 3x. Scoring logic double-counts evidence.
**Why it happens:** Ortholog databases report all matches; pipeline doesn't handle one-to-many explicitly.
**How to avoid:** Use ortholog databases with confidence scores (DIOPT, HCOP). For one-to-many, take best-scoring ortholog or aggregate phenotypes (e.g., max score, OR logic for presence). Document handling in code comments. Track ortholog count per gene in quality flags.
**Warning signs:** Phenotype evidence counts exceed gene counts; duplicated rows in output; suspiciously high phenotype scores for some genes.

### Pitfall 7: Literature Evidence Biased Toward Well-Studied Genes
**What goes wrong:** TP53 has 100,000 PubMed mentions; novel Usher candidate has 5. Raw publication count scores favor well-studied genes regardless of relevance to cilia/sensory function.
**Why it happens:** Publication count is easy to extract; developers don't implement quality weighting.
**How to avoid:** Distinguish evidence types: direct experimental evidence (gene knockout in sensory cells), functional mentions (cilia-related pathways), incidental mentions (cited in unrelated study). Weight by evidence quality, not count. Normalize by total publication count per gene to reduce bias.
**Warning signs:** Literature scores correlate with total PubMed mentions; Usher syndrome genes don't rank highly; scoring favors cancer genes (overrepresented in literature).

## Code Examples

Verified patterns from official sources:

### CellxGene Census Query (scRNA-seq Expression)
```python
# Source: https://chanzuckerberg.github.io/cellxgene-census/notebooks/api_demo/census_query_extract.html
import cellxgene_census

# Open census (uses latest stable version by default)
with cellxgene_census.open_soma() as census:
    # Query retina/cochlea cells for candidate genes
    adata = cellxgene_census.get_anndata(
        census,
        organism="Homo sapiens",
        obs_value_filter=(
            "tissue in ['retina', 'inner ear', 'cochlea'] and "
            "cell_type in ['photoreceptor cell', 'retinal rod cell', 'retinal cone cell', 'hair cell']"
        ),
        var_value_filter="gene_id in ['ENSG00000042781', 'ENSG00000124690']",  # USH2A, USH1C
        column_names={
            "obs": ["cell_type", "tissue", "assay"],
            "var": ["feature_id", "feature_name"]
        }
    )

    # Calculate tissue specificity (e.g., Tau index)
    # NULL for genes with no expression data in target tissues
```

### GTEx Tissue Expression Query
```python
# Source: GTEx API v2 documentation via gtexr package patterns
# Note: Python client requires httpx; R has gtexr package

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_URL = "https://gtexportal.org/api/v2"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_gtex_expression(gene_symbol: str, tissues: List[str]) -> dict:
    """Fetch median tissue expression from GTEx v10."""
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            f"{BASE_URL}/expression/medianGeneExpression",
            params={
                "geneId": gene_symbol,
                "datasetId": "gtex_v10"
            }
        )
        response.raise_for_status()
        data = response.json()

    # Filter to Usher-relevant tissues
    relevant_tissues = {
        "retina": "Eye - Retina",
        "cochlea": None,  # GTEx lacks inner ear; handle NULL
    }

    result = {}
    for tissue_key, gtex_name in relevant_tissues.items():
        if gtex_name is None:
            result[tissue_key] = None  # Preserve NULL for unavailable tissues
        else:
            tissue_data = next(
                (t for t in data["medianGeneExpression"] if t["tissueSiteDetailId"] == gtex_name),
                None
            )
            result[tissue_key] = tissue_data["median"] if tissue_data else None

    return result
```

### UniProt Protein Features Query
```python
# Source: UniProt REST API 2026 documentation, uniprot PyPI package
from typing import Optional
import httpx

UNIPROT_BASE = "https://rest.uniprot.org/uniprotkb"

def get_protein_features(uniprot_id: str) -> Optional[dict]:
    """Extract protein features from UniProt entry.

    Returns:
        dict with keys: length, domain_count, coiled_coil, transmembrane, cilia_motifs
        or None if protein not found
    """
    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            f"{UNIPROT_BASE}/{uniprot_id}.json",
            headers={"Accept": "application/json"}
        )

        if response.status_code == 404:
            return None  # Gene has no UniProt entry

        response.raise_for_status()
        data = response.json()

    # Extract features from JSON
    features = {
        "length": data["sequence"]["length"],
        "domain_count": len([f for f in data.get("features", []) if f["type"] == "Domain"]),
        "coiled_coil": any(f["type"] == "Coiled coil" for f in data.get("features", [])),
        "transmembrane": len([f for f in data.get("features", []) if f["type"] == "Transmembrane"]),
        "cilia_motifs": None,  # Requires specialized tool like CoCoNat
    }

    return features
```

### PubMed Literature Evidence Query
```python
# Source: NCBI E-utilities API documentation
from Bio import Entrez
from ratelimit import limits, sleep_and_retry

Entrez.email = "your_email@example.com"
Entrez.api_key = "your_ncbi_api_key"  # Increases rate limit to 10/sec

@sleep_and_retry
@limits(calls=10, period=1)  # 10 requests/sec with API key
def query_pubmed_evidence(gene_symbol: str, contexts: List[str]) -> dict:
    """Query PubMed for gene mentions in specific contexts.

    Args:
        gene_symbol: HGNC gene symbol
        contexts: e.g., ["cilia", "sensory organ", "cell polarity"]

    Returns:
        dict with counts per context and quality tier
    """
    results = {}

    for context in contexts:
        # Build query for direct experimental evidence
        query_direct = f'({gene_symbol}[Gene Name]) AND ({context}) AND ("knockout"[Title/Abstract] OR "mutation"[Title/Abstract])'

        # Build query for functional mentions
        query_functional = f'({gene_symbol}[Gene Name]) AND ({context})'

        handle_direct = Entrez.esearch(db="pubmed", term=query_direct, retmax=1000)
        record_direct = Entrez.read(handle_direct)
        handle_direct.close()

        handle_functional = Entrez.esearch(db="pubmed", term=query_functional, retmax=5000)
        record_functional = Entrez.read(handle_functional)
        handle_functional.close()

        results[context] = {
            "direct_experimental": int(record_direct["Count"]),
            "functional_mention": int(record_functional["Count"]),
            # Quality tier assigned later based on ratio
        }

    return results
```

### Tissue Specificity Index (Tau) Calculation
```python
# Source: https://academic.oup.com/bib/article/18/2/205/2562739 (Tau metric benchmark)
import polars as pl
import numpy as np

def calculate_tau_specificity(expression_df: pl.DataFrame, tissues: List[str]) -> pl.DataFrame:
    """Calculate Tau tissue specificity index (0=ubiquitous, 1=tissue-specific).

    Tau = Σ(1 - xi/xmax) / (n - 1)
    where xi is expression in tissue i, xmax is max expression across tissues, n is tissue count

    NULL preservation: if any tissue has NULL, tau is NULL (insufficient data)
    """
    # Check for NULL values
    has_null = pl.any_horizontal([pl.col(t).is_null() for t in tissues])

    # Calculate max expression across tissues
    max_expr = pl.max_horizontal([pl.col(t) for t in tissues])

    # Calculate tau
    tau_components = [(1 - pl.col(t) / max_expr) for t in tissues]
    tau = pl.sum_horizontal(tau_components) / (len(tissues) - 1)

    return expression_df.with_columns([
        pl.when(has_null)
        .then(None)  # NULL if incomplete data
        .otherwise(tau)
        .alias("tissue_specificity_tau")
    ])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual BioMart XML queries | pybiomart Python library | 2019 | Simplified complex pagination, session management |
| Pfam direct queries | InterPro REST API (Pfam integrated) | 2021 | Pfam exclusively via InterPro; old Pfam site retired |
| GTEx API v1 | GTEx API v2 | 2024 | Improved query validation, tissue ontology support, pagination |
| Pandas for bioinformatics | Polars with lazy evaluation | 2021-2024 | 5-20x performance gain, query optimization, lower memory |
| TMHMM for TM domains | Phobius (joint signal peptide + TM) | 2004 (rediscovered) | Reduces false positives from 26% to 3.9% vs TMHMM alone |
| Regex for coiled-coil | CoCoNat deep learning (ProtT5/ESM2) | 2023 | Detects non-canonical coiled-coils missed by PCOILS/Marcoil |
| requests library | httpx with async + HTTP/2 | 2021-2024 | Better connection pooling, native async, performance |
| Manual retry loops | tenacity library with jitter | 2016-2024 | Prevents retry storms, configurable backoff strategies |

**Deprecated/outdated:**
- **GTEx API v1:** Discontinued, migrate to v2 (better docs, tissue ontology)
- **Pfam website:** Retired; all Pfam data now via InterPro REST API
- **UniProt legacy text format:** Still supported but JSON/XML preferred for programmatic access
- **NCBI E-utils without API key:** 3 req/sec limit too slow; get free API key for 10 req/sec
- **TMHMM alone for TM prediction:** Phobius superior for distinguishing signal peptides from TM helices

## Open Questions

1. **InterPro API rate limits not documented**
   - What we know: InterPro REST API exists, bulk download via FTP recommended for heavy use
   - What's unclear: Exact rate limits, whether batching is supported
   - Recommendation: Start with conservative rate limiting (10 req/sec), monitor response headers, implement exponential backoff; for >10K genes consider FTP bulk download

2. **MGI/ZFIN/IMPC API availability uncertain**
   - What we know: MGI provides "compute-ready formats", IMPC web portal allows batch queries/downloads, ZFIN has ZebrafishMine with API
   - What's unclear: Whether REST APIs exist for programmatic phenotype queries, or if file-based downloads are required
   - Recommendation: Investigate MGI FTP site and IMPC bulk downloads as primary approach; use ZebrafishMine API for ZFIN; verify in implementation phase

3. **HPA API vs bulk download tradeoff**
   - What we know: HPA has `/api/search_download.php` endpoint for custom queries; bulk downloads available as TSV
   - What's unclear: Whether API is suitable for 20,000 genes or if bulk download + local filtering is better
   - Recommendation: Test API with 100-gene subset; if rate limits are restrictive, download full subcellular location TSV and filter locally

4. **Cilia motif detection approach**
   - What we know: UniProt doesn't explicitly tag "cilia motifs"; specialized tools like CoCoNat detect coiled-coils
   - What's unclear: How to systematically identify cilia-associated motifs (IFT domains, ciliary targeting sequences)
   - Recommendation: Use InterPro domain annotations (search for "IFT", "ciliary", "BBSome"); supplement with literature-based motif list; consider this LOW confidence evidence

5. **Ortholog confidence scoring standardization**
   - What we know: DIOPT, HCOP provide confidence scores; databases differ in scoring methodology
   - What's unclear: How to combine scores from multiple sources (HCOP integrates 12+ databases)
   - Recommendation: Use HCOP as primary (consensus across databases); track source count as confidence proxy (HIGH: 8+ sources agree, MEDIUM: 4-7, LOW: 1-3)

## Sources

### Primary (HIGH confidence)
- [UniProt REST API Documentation](https://academic.oup.com/nar/article/53/W1/W547/8126256) - 2026 publication on API capabilities
- [GTEx Portal API](https://gtexportal.org/home/apiPage) - Official API v2 documentation
- [CellxGene Census Python API](https://chanzuckerberg.github.io/cellxgene-census/python-api.html) - Official docs
- [InterPro 2025 Release](https://academic.oup.com/nar/article/53/D1/D444/7905301) - Latest InterPro documentation
- [PubMed E-utilities](https://www.ncbi.nlm.nih.gov/home/develop/api/) - Official NCBI API docs
- [Human Protein Atlas Data Access](https://www.proteinatlas.org/about/help/dataaccess) - Official download/API docs
- [HCOP Orthology Predictions](https://www.genenames.org/tools/hcop/) - HGNC ortholog database

### Secondary (MEDIUM confidence)
- [Polars Performance Analysis (2026)](https://endjin.com/blog/2026/01/polars-faster-pipelines-simpler-infrastructure-happier-engineers) - Production benchmarks
- [DuckDB vs Polars Benchmarks](https://www.codecentric.de/en/knowledge-hub/blog/duckdb-vs-dataframe-libraries) - Performance comparison
- [Tissue Specificity Metrics Benchmark](https://academic.oup.com/bib/article/18/2/205/2562739) - Tau index validation
- [CoCoNat Coiled-Coil Prediction](https://pmc.ncbi.nlm.nih.gov/articles/PMC10883893/) - 2023 SOTA tool
- [Phobius TM/Signal Peptide Prediction](https://academic.oup.com/nar/article/35/suppl_2/W429/2920784) - Superior to TMHMM
- [FAIR Data Pipeline Provenance](https://royalsocietypublishing.org/doi/10.1098/rsta.2021.0300) - Provenance tracking patterns
- [API Rate Limiting Best Practices (2026)](https://easyparser.com/blog/api-error-handling-retry-strategies-python-guide) - Retry strategies
- [Gene Ontology 2026 Release](https://pmc.ncbi.nlm.nih.gov/articles/PMC12807639/) - Latest GO annotation updates

### Tertiary (LOW confidence - needs validation)
- [MGI Data Access](https://www.informatics.jax.org/) - General info, API details unclear
- [ZFIN Database](https://zfin.org/) - General info, ZebrafishMine API mentioned
- [IMPC Portal](https://www.mousephenotype.org/) - Bulk download confirmed, REST API unclear
- [Biological Data Integration 2026](https://intuitionlabs.ai/articles/biotech-knowledge-graph-architecture) - Blog post, not peer-reviewed
- [Nextflow Pipeline Best Practices](https://tasrieit.com/blog/nextflow-pipelines-guide-2026) - General workflow advice

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official docs/PyPI, codebase already uses httpx/polars/DuckDB
- Architecture patterns: MEDIUM-HIGH - Patterns verified in official docs (CellxGene, UniProt) and peer-reviewed benchmarks (Tau index, Phobius), but not tested on this specific codebase
- API availability: MEDIUM - UniProt, GTEx, PubMed, CellxGene APIs confirmed; MGI/ZFIN/IMPC require implementation phase verification
- Pitfalls: HIGH - Based on documented rate limits (UniProt 200/sec, NCBI 3/sec), identifier mapping literature, NULL handling best practices
- Code examples: MEDIUM-HIGH - Adapted from official documentation but not executed against real data

**Research date:** 2026-02-11
**Valid until:** ~60 days (2026-04-11) - Moderate stability domain. API versions change quarterly (GTEx, HPA), library updates monthly (polars, httpx). Re-verify API endpoints and library compatibility before implementation.

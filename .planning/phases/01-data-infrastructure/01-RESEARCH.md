# Phase 1: Data Infrastructure - Research

**Researched:** 2026-02-11
**Domain:** Python bioinformatics data pipelines, gene ID mapping, API clients, configuration management, provenance tracking
**Confidence:** MEDIUM-HIGH

## Summary

This phase establishes the foundational data infrastructure for a reproducible gene essentiality scoring pipeline. The core technical challenge is building a robust system for gene ID mapping, external API integration with rate limiting and caching, configuration management with validation, and data persistence enabling checkpoint-restart capabilities.

**Python ecosystem strengths:** The bioinformatics Python ecosystem has mature libraries for gene ID mapping (mygene), API retry/caching (tenacity, requests-cache), data validation (Pydantic v2), and analytical data storage (DuckDB, Parquet). These tools are actively maintained with 2026 releases and well-documented patterns for scientific pipelines.

**Key architectural decisions:**
1. Use `mygene` (MyGene.info API) for gene ID mapping - it supports batch queries across Ensembl, HGNC, UniProt with species filtering
2. Use `requests-cache` + `tenacity` for API clients - persistent SQLite cache with exponential backoff retry
3. Use `Pydantic v2` + `pydantic-yaml` for configuration - strong validation with clear error messages
4. Use `DuckDB` for intermediate data persistence - file-based database with native Parquet support and checkpoint capabilities
5. Use `pathlib.Path` consistently for file operations - cross-platform, modern Python standard

**Primary recommendation:** Build modular CLI scripts using `click` framework, separate concerns (config loading, API clients, gene mapping, persistence), and emphasize validation gates at each step (report mapping success rates, validate API responses, check data completeness). Avoid building custom solutions for ID mapping, retry logic, or data serialization - use established libraries.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mygene` | 3.1.0+ | Gene ID mapping (Ensembl ↔ HGNC ↔ UniProt) | Official MyGene.info client, handles batch queries, species filtering, automatic pagination |
| `requests` | 2.32.0+ | HTTP client foundation | Universal Python HTTP library, basis for requests-cache |
| `requests-cache` | 1.3.0+ | Persistent HTTP caching | SQLite backend, TTL support, transparent caching, saves API quota |
| `tenacity` | 9.0.0+ | Retry logic with exponential backoff | Declarative retry strategies, handles rate limits (429), jitter support |
| `Pydantic` | 2.12.5+ | Data validation and settings | Type-safe validation, clear error messages, v2 has Rust-based speed |
| `pydantic-yaml` | 1.4.0+ | YAML ↔ Pydantic integration | Load/dump Pydantic models from YAML, validation on load |
| `DuckDB` | 1.2.0+ | Analytical database for intermediate data | File-based persistence, native Parquet support, fast SQL queries |
| `click` | 8.3.0+ | CLI framework | Decorator-based, excellent help generation, subcommand support |
| `pathlib` | stdlib | Path handling | Cross-platform, object-oriented, modern standard (Python 3.4+) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pyensembl` | 2.3.13+ | Ensembl GTF/FASTA local database | If you need to filter protein-coding genes locally, access transcript details |
| `bioservices` | 1.12.1+ | UniProt/other bio API clients | Direct UniProt queries (though mygene covers most use cases) |
| `polars` | 1.20.0+ | Fast DataFrame operations | Large-scale data transformations (alternative to pandas) |
| `PyArrow` | 18.0.0+ | Parquet read/write, zero-copy interop | Writing Parquet files, Arrow integration |
| `hashlib` | stdlib | Hash generation for provenance | Create config hashes (SHA-256), file integrity checks |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `mygene` | Manual API calls to Ensembl/UniProt | Custom code = maintenance burden, mygene handles pagination, errors, retries |
| `requests-cache` | Manual file-based cache | Reinvent TTL logic, serialization; requests-cache is battle-tested |
| `Pydantic v2` | `attrs` or `dataclass` | attrs is faster but Pydantic has better validation ecosystem for complex rules |
| `click` | `argparse` (stdlib) | argparse is stdlib but click has better DX for complex CLIs with subcommands |
| `DuckDB` | Pure Parquet files | DuckDB adds SQL query capability, simpler checkpoint logic, same Parquet backend |

**Installation:**
```bash
pip install mygene requests requests-cache tenacity pydantic pydantic-yaml duckdb click polars pyarrow
```

For local Ensembl database (optional):
```bash
pip install pyensembl
pyensembl install --release 112 --species homo_sapiens
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── config/              # Configuration schemas and loaders
│   ├── schema.py        # Pydantic models for pipeline config
│   └── loader.py        # YAML → validated config
├── gene_mapping/        # Gene ID mapping utilities
│   ├── universe.py      # Define gene universe (protein-coding, Ensembl filtering)
│   ├── mapper.py        # mygene wrapper, batch mapping
│   └── validator.py     # Mapping validation gates, reporting
├── api_clients/         # External API clients
│   ├── base.py          # Shared retry/cache setup
│   ├── gnomad.py        # gnomAD client
│   ├── gtex.py          # GTEx client
│   ├── hpa.py           # Human Protein Atlas client
│   └── ...              # Other API clients
├── persistence/         # Data persistence layer
│   ├── duckdb_store.py  # DuckDB connection, table management
│   └── provenance.py    # Provenance metadata tracking
└── cli/                 # CLI entry points
    ├── setup.py         # Setup gene universe, validate config
    ├── fetch.py         # Fetch external data
    └── ...              # Other pipeline steps
```

### Pattern 1: Configuration with Pydantic + YAML
**What:** Define configuration schema as Pydantic models, load from YAML with validation
**When to use:** All pipeline parameters (weights, thresholds, data source versions, API keys)

**Example:**
```python
# config/schema.py
from pydantic import BaseModel, Field, field_validator
from pathlib import Path

class DataSourceVersions(BaseModel):
    ensembl_release: int = Field(..., ge=100, description="Ensembl release number")
    gnomad_version: str = Field("v4.1", description="gnomAD version")
    gtex_version: str = Field("v8", description="GTEx data version")

class PipelineConfig(BaseModel):
    data_dir: Path
    cache_dir: Path
    duckdb_path: Path
    versions: DataSourceVersions
    api_rate_limit: int = Field(10, description="Max requests per second")

    @field_validator('duckdb_path')
    def ensure_parent_exists(cls, v: Path) -> Path:
        v.parent.mkdir(parents=True, exist_ok=True)
        return v

# config/loader.py
from pydantic_yaml import parse_yaml_raw_as
from pathlib import Path

def load_config(config_path: Path) -> PipelineConfig:
    """Load and validate YAML config."""
    yaml_content = config_path.read_text()
    config = parse_yaml_raw_as(PipelineConfig, yaml_content)
    return config
```

**Source:** [Pydantic Documentation](https://docs.pydantic.dev/latest/), [pydantic-yaml PyPI](https://pypi.org/project/pydantic-yaml/)

### Pattern 2: Gene ID Mapping with Validation Gates
**What:** Use mygene for batch ID mapping, report success rate, flag unmapped genes
**When to use:** Converting between Ensembl, HGNC, UniProt IDs

**Example:**
```python
# gene_mapping/mapper.py
import mygene
from typing import List, Dict, Tuple

def batch_map_ensembl_to_hgnc(
    ensembl_ids: List[str],
    species: int = 9606  # Human
) -> Tuple[Dict[str, str], List[str]]:
    """
    Map Ensembl gene IDs to HGNC symbols.
    Returns: (successful_mappings, unmapped_ids)
    """
    mg = mygene.MyGeneInfo()

    # Query with scopes for Ensembl gene IDs
    results = mg.querymany(
        ensembl_ids,
        scopes='ensembl.gene',
        fields='symbol',
        species=species,
        returnall=True
    )

    successful = {}
    unmapped = []

    for query_result in results['out']:
        ensembl_id = query_result['query']

        if 'symbol' in query_result and 'notfound' not in query_result:
            successful[ensembl_id] = query_result['symbol']
        else:
            unmapped.append(ensembl_id)

    # Validation gate: report mapping success rate
    total = len(ensembl_ids)
    success_rate = len(successful) / total * 100
    print(f"Mapped {len(successful)}/{total} genes ({success_rate:.1f}%)")

    if success_rate < 90:
        print(f"WARNING: Low mapping success rate. Unmapped genes: {unmapped[:10]}...")

    return successful, unmapped
```

**Source:** [MyGene.py Documentation](https://docs.mygene.info/projects/mygene-py/en/latest/)

### Pattern 3: API Client with Retry and Cache
**What:** Combine requests-cache for persistent caching and tenacity for retry logic
**When to use:** All external API calls (gnomAD, GTEx, HPA, UniProt, PubMed)

**Example:**
```python
# api_clients/base.py
import requests_cache
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from requests.exceptions import HTTPError, Timeout
from pathlib import Path

class CachedAPIClient:
    """Base class for API clients with caching and retry."""

    def __init__(self, cache_dir: Path, rate_limit: int = 10):
        self.session = requests_cache.CachedSession(
            cache_name=str(cache_dir / 'api_cache'),
            backend='sqlite',
            expire_after=86400,  # 24 hours default TTL
        )
        self.rate_limit = rate_limit

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((HTTPError, Timeout)),
        reraise=True
    )
    def get(self, url: str, **kwargs):
        """GET request with retry and cache."""
        response = self.session.get(url, timeout=30, **kwargs)
        response.raise_for_status()  # Raise HTTPError for 4xx/5xx
        return response

# api_clients/gtex.py
class GTExClient(CachedAPIClient):
    """GTEx Portal API client."""

    BASE_URL = "https://gtexportal.org/api/v2"

    def get_gene_expression(self, gene_symbol: str):
        """Fetch gene expression data across tissues."""
        url = f"{self.BASE_URL}/expression/geneExpression"
        params = {'geneId': gene_symbol, 'datasetId': 'gtex_v8'}
        response = self.get(url, params=params)
        return response.json()
```

**Sources:** [requests-cache Documentation](https://requests-cache.readthedocs.io/), [Tenacity Documentation](https://tenacity.readthedocs.io/)

### Pattern 4: DuckDB for Checkpoint-Restart
**What:** Store intermediate results in DuckDB file, enable resuming pipeline from checkpoint
**When to use:** After fetching expensive API data, after transformations

**Example:**
```python
# persistence/duckdb_store.py
import duckdb
from pathlib import Path
from typing import Optional
import pandas as pd

class PipelineStore:
    """DuckDB-based storage for pipeline intermediate results."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = duckdb.connect(str(db_path))

    def save_dataframe(self, df: pd.DataFrame, table_name: str, replace: bool = False):
        """Save DataFrame to DuckDB table."""
        mode = 'replace' if replace else 'append'
        self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df")
        if replace:
            self.conn.execute(f"DELETE FROM {table_name}")
            self.conn.execute(f"INSERT INTO {table_name} SELECT * FROM df")

    def load_dataframe(self, table_name: str) -> Optional[pd.DataFrame]:
        """Load DataFrame from DuckDB table."""
        try:
            return self.conn.execute(f"SELECT * FROM {table_name}").df()
        except Exception:
            return None

    def export_parquet(self, table_name: str, output_path: Path):
        """Export table to Parquet file."""
        self.conn.execute(f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET)")

    def has_checkpoint(self, checkpoint_name: str) -> bool:
        """Check if checkpoint exists."""
        result = self.conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [checkpoint_name]
        ).fetchone()
        return result[0] > 0
```

**Source:** [DuckDB Python API](https://duckdb.org/docs/stable/clients/python/overview)

### Pattern 5: Provenance Metadata Tracking
**What:** Attach metadata to every output (versions, timestamps, config hash)
**When to use:** All pipeline outputs (gene lists, intermediate data, final results)

**Example:**
```python
# persistence/provenance.py
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

def compute_config_hash(config: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of configuration."""
    config_json = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(config_json.encode()).hexdigest()

def create_provenance_metadata(
    config: Dict[str, Any],
    pipeline_version: str,
    data_sources: Dict[str, str]
) -> Dict[str, Any]:
    """Create provenance metadata for output."""
    return {
        'pipeline_version': pipeline_version,
        'data_source_versions': data_sources,
        'config_hash': compute_config_hash(config),
        'timestamp': datetime.utcnow().isoformat(),
        'processing_steps': []  # Populated during pipeline execution
    }

def save_with_provenance(
    data: Any,
    output_path: Path,
    metadata: Dict[str, Any]
):
    """Save data with provenance metadata sidecar."""
    # Save main data
    # ... (format-specific save logic)

    # Save metadata sidecar
    metadata_path = output_path.with_suffix('.provenance.json')
    metadata_path.write_text(json.dumps(metadata, indent=2))
```

**Source:** [Python hashlib documentation](https://docs.python.org/3/library/hashlib.html)

### Anti-Patterns to Avoid
- **Global state:** Don't use global variables for configuration or connections; pass explicitly or use dependency injection
- **String-based paths:** Don't use `os.path` with string concatenation; use `pathlib.Path` with `/` operator
- **Bare try-except:** Don't catch all exceptions silently; catch specific exceptions, log, re-raise or handle
- **Manual CSV parsing:** Don't parse CSV with string splitting; use `pandas`, `polars`, or `csv` module
- **Hardcoded credentials:** Don't embed API keys in code; use environment variables or separate secrets file

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gene ID mapping | Custom scrapers for Ensembl/UniProt | `mygene` library | Handles pagination, rate limits, species mapping, multiple ID types; battle-tested |
| HTTP caching | File-based cache with pickle | `requests-cache` | Handles cache expiration, concurrent access, multiple backends, HTTP semantics |
| Retry logic | Manual loop with sleep | `tenacity` | Exponential backoff, jitter, retry conditions, logging; prevents thundering herd |
| Data validation | Manual type checks | `Pydantic` | Automatic coercion, nested validation, clear error messages, JSON schema generation |
| Parquet I/O | Custom serialization | `pyarrow` or `polars` | Compression, schema evolution, partitioning, column pruning optimizations |
| CLI parsing | Manual sys.argv parsing | `click` | Help generation, type conversion, subcommands, testing utilities |

**Key insight:** Bioinformatics pipelines have deceptively complex edge cases (API rate limits, pagination, ID mapping ambiguity, data versioning). Established libraries have solved these through community testing. Custom solutions will hit the same edge cases but without the benefit of community fixes.

## Common Pitfalls

### Pitfall 1: Not Filtering Pseudogenes from Gene Universe
**What goes wrong:** Including pseudogenes in gene universe inflates counts, breaks downstream ID mapping (pseudogenes often lack UniProt mappings)

**Why it happens:** Ensembl GTF includes all biotypes; filtering requires explicit `gene_biotype == "protein_coding"` check

**How to avoid:**
- Use `pyensembl` or parse Ensembl GTF to filter by biotype
- Explicitly exclude pseudogenes: `biotype NOT IN ('processed_pseudogene', 'unprocessed_pseudogene', 'pseudogene')`
- Validate gene count matches expected human protein-coding genes (~20,000)

**Warning signs:** Gene universe > 25,000 genes (indicates non-coding genes included)

**Source:** [Ensembl Gene Biotypes](http://vega.archive.ensembl.org/info/about/gene_and_transcript_types.html), [Biostars: Exclude pseudogenes](https://www.biostars.org/p/9490668/)

### Pitfall 2: Low Gene ID Mapping Success Rate Without Validation
**What goes wrong:** 20%+ genes fail to map between ID systems; pipeline proceeds with incomplete data, results are misleading

**Why it happens:** Different databases use different gene versions, some genes lack mappings, retired IDs persist in old datasets

**How to avoid:**
- Implement validation gates: report mapping success rate, fail if < 90%
- Save unmapped genes to file for manual review
- Use `mygene`'s `returnall=True` to distinguish "not found" from "ambiguous"
- Use consistent Ensembl release across all steps

**Warning signs:** Silent data loss, gene count drops unexpectedly between steps, missing expected genes in results

**Source:** [Biostars: Gene ID mapping challenges](https://www.biostars.org/p/288205/), [Cancer Dependency Map: Gene annotation best practices](https://depmap.sanger.ac.uk/documentation/datasets/gene-annotation-mapping/)

### Pitfall 3: API Rate Limiting Without Backoff
**What goes wrong:** API returns 429 (Too Many Requests), script crashes or gets IP banned

**Why it happens:** Scientific APIs (gnomAD, GTEx) enforce rate limits; naive sequential requests hit limits quickly

**How to avoid:**
- Use `tenacity` with exponential backoff and jitter
- Check API documentation for rate limits, implement conservative delays
- Use `requests-cache` to avoid re-fetching same data
- Batch requests where API supports it (e.g., mygene `querymany`)

**Warning signs:** Frequent 429 errors, script hangs, API blocks your IP

**Source:** [API Error Handling & Retry Strategies: Python Guide 2026](https://easyparser.com/blog/api-error-handling-retry-strategies-python-guide), [gnomAD: Blocked when using API](https://discuss.gnomad.broadinstitute.org/t/blocked-when-using-api-to-get-af/149)

### Pitfall 4: No Provenance Metadata = Unreproducible Results
**What goes wrong:** Cannot reproduce results 6 months later; data source versions unknown, config parameters lost

**Why it happens:** Scientific data sources update frequently (Ensembl releases biannually), config tweaks during development are forgotten

**How to avoid:**
- Embed provenance metadata in every output: data source versions, timestamps, config hash, pipeline version
- Save config file alongside outputs (or hash reference)
- Use semantic versioning for pipeline scripts
- Document data download dates

**Warning signs:** "Which Ensembl release did we use?", "What were the parameter values?", inability to reproduce old results

**Source:** [FAIR data pipeline: provenance-driven data management](https://royalsocietypublishing.org/doi/10.1098/rsta.2021.0300)

### Pitfall 5: Hard-Coded File Paths and No Cross-Platform Support
**What goes wrong:** Pipeline breaks on different OS (Windows vs Linux), paths don't exist on collaborator's machine

**Why it happens:** Using string concatenation for paths (`"/home/user/data/" + filename`), hardcoding absolute paths

**How to avoid:**
- Use `pathlib.Path` consistently: `Path("data") / "genes.csv"`
- Make all paths configurable via YAML config
- Use relative paths from project root or config-specified base directory
- Check path existence, create directories with `Path.mkdir(parents=True, exist_ok=True)`

**Warning signs:** `FileNotFoundError` on different machines, mix of `/` and `\` in path strings

**Source:** [pathlib best practices 2026](https://oneuptime.com/blog/post/2026-01-27-use-pathlib-for-file-paths-python/view)

### Pitfall 6: Ignoring Data Versioning and API Changes
**What goes wrong:** API query syntax changes (e.g., UniProt 2022 column name changes), old code breaks

**Why it happens:** External APIs evolve; breaking changes in data schema or query parameters

**How to avoid:**
- Pin data source versions in config (Ensembl release, gnomAD version)
- Add API version checks or try-except with fallback for schema changes
- Monitor API changelog announcements
- Test with latest API versions periodically

**Warning signs:** Suddenly failing API calls after working for months, schema validation errors, missing expected fields

**Source:** [bioservices UniProt API changes](https://bioservices.readthedocs.io/en/main/), [Biostars: UniProt API programming](https://widdowquinn.github.io/2018-03-06-ibioic/02-sequence_databases/07-uniprot_programming.html)

### Pitfall 7: No Checkpoint-Restart = Re-download Everything on Failure
**What goes wrong:** Network error at hour 3 of 4-hour data fetch; must restart from beginning, waste time and API quota

**Why it happens:** Pipeline doesn't persist intermediate results; all-or-nothing execution model

**How to avoid:**
- Save intermediate results to DuckDB after each major step
- Check for checkpoints before expensive operations: `if not store.has_checkpoint('gnomad_data'): fetch_gnomad()`
- Use `requests-cache` to avoid re-downloading API data
- Design idempotent steps (safe to re-run)

**Warning signs:** Frequent restarts from scratch, frustration during development, wasted API quota

**Source:** [DuckDB Python documentation](https://duckdb.org/docs/stable/clients/python/overview)

## Code Examples

Verified patterns from official sources:

### Loading YAML Config with Pydantic Validation
```python
# Source: https://pypi.org/project/pydantic-yaml/
from pydantic import BaseModel, Field
from pydantic_yaml import parse_yaml_raw_as
from pathlib import Path

class Config(BaseModel):
    ensembl_release: int = Field(..., ge=100)
    cache_dir: Path
    api_rate_limit: int = 10

config_yaml = Path("config.yaml").read_text()
config = parse_yaml_raw_as(Config, config_yaml)
# Raises ValidationError if invalid
```

### Batch Gene ID Mapping with mygene
```python
# Source: https://docs.mygene.info/projects/mygene-py/en/latest/
import mygene

mg = mygene.MyGeneInfo()

# Map Ensembl IDs to HGNC symbols and UniProt accessions
results = mg.querymany(
    ['ENSG00000139618', 'ENSG00000141510'],
    scopes='ensembl.gene',
    fields='symbol,uniprot',
    species=9606,  # Human
    returnall=True
)

for hit in results['out']:
    print(f"{hit['query']} -> {hit.get('symbol')} (UniProt: {hit.get('uniprot', {}).get('Swiss-Prot')})")
```

### Setting Up requests-cache with SQLite Backend
```python
# Source: https://requests-cache.readthedocs.io/
import requests_cache

session = requests_cache.CachedSession(
    cache_name='api_cache',
    backend='sqlite',
    expire_after=86400,  # 24 hours
)

# First request hits API and caches
response = session.get('https://api.example.com/data')

# Subsequent requests return cached response (sub-millisecond)
response = session.get('https://api.example.com/data')
print(f"From cache: {response.from_cache}")
```

### Retry with Exponential Backoff using tenacity
```python
# Source: https://tenacity.readthedocs.io/
from tenacity import retry, stop_after_attempt, wait_exponential
import requests

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
def fetch_api_data(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()

# Automatically retries with increasing delays: 4s, 8s, 16s, 32s, 60s
data = fetch_api_data('https://api.example.com/genes')
```

### DuckDB: Persist DataFrame and Export Parquet
```python
# Source: https://duckdb.org/docs/stable/clients/python/overview
import duckdb
import pandas as pd

# Connect to file-based database (creates if not exists)
conn = duckdb.connect('pipeline.duckdb')

# Save DataFrame to table
df = pd.DataFrame({'gene': ['BRCA1', 'TP53'], 'score': [0.95, 0.88]})
conn.execute("CREATE TABLE IF NOT EXISTS gene_scores AS SELECT * FROM df")

# Query later
result = conn.execute("SELECT * FROM gene_scores WHERE score > 0.9").df()

# Export to Parquet
conn.execute("COPY gene_scores TO 'output/gene_scores.parquet' (FORMAT PARQUET)")
```

### Computing Config Hash for Provenance
```python
# Source: https://docs.python.org/3/library/hashlib.html
import hashlib
import json

def compute_config_hash(config_dict):
    """Compute SHA-256 hash of config for provenance tracking."""
    config_json = json.dumps(config_dict, sort_keys=True, default=str)
    hash_digest = hashlib.sha256(config_json.encode()).hexdigest()
    return hash_digest

config = {'ensembl_release': 112, 'weights': {'gnomad': 0.3}}
config_hash = compute_config_hash(config)
print(f"Config hash: {config_hash[:16]}...")  # Config hash: a3f8b2c1d4e5f6a7...
```

### Using pathlib for Cross-Platform Paths
```python
# Source: https://docs.python.org/3/library/pathlib.html
from pathlib import Path

# Define base directory
data_dir = Path("data")

# Build paths with / operator (cross-platform)
gene_file = data_dir / "genes" / "ensembl_genes.csv"

# Create parent directories if needed
gene_file.parent.mkdir(parents=True, exist_ok=True)

# Read/write with convenience methods
content = gene_file.read_text()  # Reads entire file
gene_file.write_text("ENSG00000139618,BRCA1\n")  # Writes string

# Check existence
if gene_file.exists():
    print(f"Found: {gene_file.resolve()}")  # Absolute path
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pandas for all data | DuckDB for analytical queries, Polars for transformations | 2023-2025 | 10-24x speedup for large datasets; DuckDB SQL queries on Parquet without full load |
| Manual API retry loops | `tenacity` library | 2020+ | Declarative retry strategies, jitter prevents thundering herd, better error handling |
| Dataclasses for validation | Pydantic v2 | 2023 (v2 release) | Rust-based validation core = faster; richer validation rules, automatic JSON schema |
| os.path string manipulation | pathlib.Path | Python 3.4+ (now standard) | Cross-platform by default, object-oriented, more readable code |
| UniProt REST API column names | New API (2022 changes) | June 2022 | Breaking change: `tab` → `tsv`, `taxonomy` → `taxonomy_id`; affects bioservices code |
| requests without caching | requests-cache | Adopted in scientific pipelines 2020+ | Persistent SQLite cache, respects HTTP headers, saves API quota and time |

**Deprecated/outdated:**
- **pyEntrezId:** Converts IDs to Entrez but limited scope; **use mygene instead** (supports more ID types, better maintained)
- **gnomad_python_api:** Package marked deprecated, GraphQL API changed; **use direct GraphQL queries** or official gnomAD Python tools
- **biomaRt (R):** Still used in R pipelines but **Python: use pybiomart** for BioMart queries (if needed; mygene often sufficient)
- **argparse for complex CLIs:** Still valid but **click or typer** have better DX for multi-command CLIs

## Open Questions

### 1. GTEx API v2 Python Client Maturity
- **What we know:** GTEx API v2 exists with improved documentation; community tool `pyGTEx` exists but may be outdated
- **What's unclear:** Is `pyGTEx` maintained for API v2? Should we use direct API calls?
- **Recommendation:** Start with direct API calls using base `CachedAPIClient` pattern; verify current GTEx API v2 endpoint behavior during implementation

### 2. Human Protein Atlas API Details
- **What we know:** HPA exposes XML API accepting Ensembl IDs; MCP interface mentioned but details sparse
- **What's unclear:** Rate limits, batch query support, data freshness, Python client recommendations
- **Recommendation:** Use direct API calls with requests-cache; test rate limits empirically during development

### 3. gnomAD API Access Pattern
- **What we know:** gnomAD has GraphQL API; some Python wrappers deprecated; rate limiting confirmed (blocked after ~10 queries)
- **What's unclear:** Current recommended Python access method, official rate limits, batch query best practices
- **Recommendation:** Use direct GraphQL queries with aggressive caching and conservative rate limiting (1 req/sec start); verify official docs during implementation

### 4. Ensembl vs MyGene.info Data Freshness
- **What we know:** mygene provides convenient batch mapping; Ensembl is canonical source; data sync lag possible
- **What's unclear:** How quickly does MyGene.info sync with new Ensembl releases? Acceptable lag for this pipeline?
- **Recommendation:** Pin Ensembl release in config; validate mygene results against expected gene count; consider hybrid approach (mygene for bulk mapping, direct Ensembl fallback for failures)

## Sources

### Primary (HIGH confidence)
- [MyGene.py Documentation](https://docs.mygene.info/projects/mygene-py/en/latest/) - Gene ID mapping API, batch queries, species filtering
- [DuckDB Python API](https://duckdb.org/docs/stable/clients/python/overview) - Persistence, Parquet integration, SQL queries
- [requests-cache Documentation](https://requests-cache.readthedocs.io/) - HTTP caching, SQLite backend, TTL configuration
- [Tenacity Documentation](https://tenacity.readthedocs.io/) - Retry strategies, exponential backoff, rate limit handling
- [Pydantic Documentation](https://docs.pydantic.dev/latest/) - BaseModel, validation, v2 features
- [Python pathlib Documentation](https://docs.python.org/3/library/pathlib.html) - Path handling, cross-platform patterns
- [Python hashlib Documentation](https://docs.python.org/3/library/hashlib.html) - SHA-256 hashing for config provenance

### Secondary (MEDIUM confidence)
- [pydantic-yaml PyPI](https://pypi.org/project/pydantic-yaml/) - YAML integration with Pydantic
- [GTEx Portal API Documentation](https://gtexportal.org/api/v2/redoc) - GTEx API v2 endpoints
- [bioservices Documentation](https://bioservices.readthedocs.io/en/main/) - UniProt API access via Python
- [PyEnsembl GitHub](https://github.com/openvax/pyensembl) - Local Ensembl database, gene filtering
- [Click Documentation](https://click.palletsprojects.com/en/stable/why/) - CLI framework comparison, best practices
- [API Error Handling Guide 2026](https://easyparser.com/blog/api-error-handling-retry-strategies-python-guide) - Retry patterns, backoff strategies
- [DuckDB vs Polars vs PyArrow comparison](https://www.confessionsofadataguy.com/pyarrow-vs-polars-vs-duckdb-for-data-pipelines/) - Performance benchmarks for data pipelines

### Tertiary (LOW confidence - needs verification)
- [pyGTEx GitHub](https://github.com/w-gao/pyGTEx) - Community GTEx client (maintenance status unclear)
- [gnomAD Python API (deprecated)](https://github.com/furkanmtorun/gnomad_python_api) - Marked deprecated, may have outdated examples
- [HPA MCP Interface](https://mcpmarket.com/server/human-protein-atlas) - Mentioned in search but implementation details sparse
- [FAIR Data Pipeline (academic paper)](https://royalsocietypublishing.org/doi/10.1098/rsta.2021.0300) - Provenance concepts, may need adaptation to practical implementation

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** - All libraries verified via official docs, actively maintained with 2026 releases, well-documented
- Architecture: **MEDIUM-HIGH** - Patterns verified from official docs, some scientific pipeline specifics extrapolated from best practices
- Pitfalls: **MEDIUM** - Validated from community forums (Biostars), official documentation warnings, and known bioinformatics challenges
- API client specifics (GTEx, HPA, gnomAD): **MEDIUM-LOW** - Official APIs exist but Python client recommendations need runtime verification

**Research date:** 2026-02-11
**Valid until:** ~60 days (March 2026) - Gene ID mapping and data validation patterns are stable; API endpoints may change, verify before implementation

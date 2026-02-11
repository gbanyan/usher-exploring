# Architecture Research

**Domain:** Bioinformatics Gene Candidate Discovery Pipeline
**Researched:** 2026-02-11
**Confidence:** MEDIUM-HIGH

## Standard Architecture

Multi-evidence gene prioritization pipelines in bioinformatics follow a **layered architecture** with independent data retrieval modules feeding into normalization, feature extraction, scoring, and validation layers. The standard pattern is a **staged pipeline** where each evidence layer operates independently, writes intermediate results, then feeds into a final integration/scoring component.

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLI ORCHESTRATION LAYER                      │
│  (Typer/Click: main pipeline script + per-layer subcommands)    │
├─────────────────────────────────────────────────────────────────┤
│                   DATA RETRIEVAL LAYER (6 modules)               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ GO/UniProt│  │ Tissue   │  │ Protein  │  │ Subcell  │        │
│  │ Annot.   │  │ Expr.    │  │ Features │  │ Localiz. │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │             │               │
│  ┌────┴─────┐  ┌───┴──────┐                                     │
│  │ Genetic  │  │ Animal   │  + Literature Scan (PubMed API)    │
│  │ Constrt. │  │ Models   │                                     │
│  └────┬─────┘  └────┬─────┘                                     │
├───────┴──────────────┴──────────────────────────────────────────┤
│                  NORMALIZATION/TRANSFORM LAYER                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Per-layer parsers: Raw → Standardized schema            │   │
│  │  Gene ID mapping (all to Ensembl/HGNC)                   │   │
│  │  Score normalization (0-1 scale per evidence type)       │   │
│  └──────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                     DATA STORAGE LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Raw Cache    │  │ Intermediate │  │ Final Output │          │
│  │ (Parquet)    │  │ (DuckDB)     │  │ (TSV/Parquet)│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                 INTEGRATION/SCORING LAYER                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Multi-evidence scoring: weighted rule-based integration │   │
│  │  Known gene exclusion filter                             │   │
│  │  Confidence tier assignment (high/medium/low)            │   │
│  └──────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                      REPORTING LAYER                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Per-gene evidence summary generation                    │   │
│  │  Ranked candidate lists by confidence tier              │   │
│  │  Provenance tracking (data versions, tool versions)     │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **CLI Orchestrator** | Entry point, subcommand routing, global config management | Typer (modern, type-hinted) or Click (mature, widely used) |
| **Data Retrievers** | Query external APIs/databases, cache raw results, handle rate limits/retries | Per-source Python modules with API clients (requests, biopython) |
| **Normalizers** | Parse raw formats, map gene IDs to standard vocab, scale scores 0-1 | Pandas/Polars for tabular data, custom parsers for specialized formats |
| **Data Storage** | Persist intermediate results, enable restartability, support fast queries | DuckDB (analytical queries on intermediate data), Parquet (compressed columnar cache) |
| **Integrator** | Combine evidence scores, apply weights, filter known genes, assign confidence tiers | Custom Python logic, potentially scikit-learn for rule-based models |
| **Reporter** | Generate human-readable outputs, track provenance, create evidence summaries | Pandas/Polars for output formatting, Jinja2 for report templates |

## Recommended Project Structure

```
usher-gene-discovery/
├── config/
│   ├── pipeline.yaml          # Main pipeline config (weights, thresholds, data sources)
│   ├── sources.yaml            # API endpoints, file paths, version info
│   └── known_genes.txt         # CiliaCarta/SYSCILIA/OMIM exclusion list
├── data/
│   ├── raw/                    # Cached raw API responses (Parquet, JSON)
│   │   ├── uniprot/
│   │   ├── gtex/
│   │   ├── gnomaad/
│   │   └── pubmed/
│   ├── intermediate/           # Normalized per-layer results (DuckDB tables)
│   │   └── evidence.duckdb
│   └── output/                 # Final results
│       ├── candidates_high.tsv
│       ├── candidates_medium.tsv
│       └── evidence_summary.parquet
├── src/
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── cli.py              # Main Typer CLI app
│   │   ├── config.py           # Config loading/validation (pydantic)
│   │   └── utils.py            # Shared utilities (gene ID mapping, etc.)
│   ├── retrievers/             # Data retrieval modules (6 evidence layers)
│   │   ├── __init__.py
│   │   ├── annotation.py       # GO/UniProt completeness
│   │   ├── expression.py       # HPA/GTEx/CellxGene tissue expression
│   │   ├── protein_features.py # Domain/motif/coiled-coil analysis
│   │   ├── localization.py     # Subcellular localization
│   │   ├── constraint.py       # gnomAD pLI/LOEUF
│   │   ├── phenotypes.py       # MGI/ZFIN/IMPC animal models
│   │   └── literature.py       # PubMed API scanning
│   ├── normalizers/            # Per-source parsers/normalizers
│   │   ├── __init__.py
│   │   └── [mirrors retrievers structure]
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── scoring.py          # Multi-evidence scoring logic
│   │   ├── filtering.py        # Known gene exclusion
│   │   └── tiering.py          # Confidence tier assignment
│   └── reporting/
│       ├── __init__.py
│       ├── summaries.py        # Per-gene evidence summaries
│       └── provenance.py       # Version tracking, data lineage
├── tests/
│   ├── test_retrievers/
│   ├── test_normalizers/
│   ├── test_integration/
│   └── fixtures/               # Small test datasets
├── scripts/
│   └── validate_outputs.py     # Manual validation/QC scripts
├── pyproject.toml              # Dependencies, tool config
├── README.md
└── .env.example                # API keys template
```

### Structure Rationale

- **config/:** YAML for pipeline configuration (human-editable, version-controllable, standard in bioinformatics). TOML considered but YAML dominates bioinformatics tooling (Nextflow, Snakemake, nf-core).
- **data/ hierarchy:** Separates raw (cacheable, immutable) from intermediate (queryable) from output (deliverable). Enables pipeline restartability and debugging.
- **src/pipeline/ vs src/retrievers/:** CLI orchestration separated from business logic. Retrievers/normalizers mirror structure for clarity.
- **src/integration/:** Scoring logic isolated from data retrieval. Critical for testing/validation and future refinement of scoring weights.
- **tests/ mirrors src/:** Standard Python pattern. Fixtures for small validation datasets.

## Architectural Patterns

### Pattern 1: Independent Evidence Layers (Modular Retrieval)

**What:** Each evidence layer (annotation, expression, protein features, etc.) is an independent module with its own retriever, normalizer, and output schema. Modules do NOT communicate directly—only via the shared data storage layer.

**When to use:** Always in multi-evidence pipelines. Critical for your 6-layer architecture.

**Trade-offs:**
- **Pro:** Layers can be developed/tested/run independently. Failures in one layer don't cascade. Easy to add/remove evidence sources.
- **Pro:** Parallelizable execution (run all 6 retrievers concurrently).
- **Con:** Requires discipline to maintain consistent gene ID mapping and schema standards across layers.

**Example:**
```python
# src/retrievers/annotation.py
from typing import List
import polars as pl

class AnnotationRetriever:
    def __init__(self, config):
        self.config = config

    def retrieve(self, gene_ids: List[str]) -> pl.DataFrame:
        """Fetch GO/UniProt completeness for genes."""
        # Query UniProt API
        raw_data = self._query_uniprot(gene_ids)
        # Cache raw response
        self._cache_raw(raw_data, "uniprot")
        return raw_data

    def normalize(self, raw_data: pl.DataFrame) -> pl.DataFrame:
        """Normalize to standard schema."""
        return raw_data.select([
            pl.col("gene_id"),
            pl.col("annotation_score").cast(pl.Float32),  # 0-1 scale
            pl.col("go_term_count"),
            pl.col("data_source").cast(pl.Utf8)
        ])
```

### Pattern 2: Staged Data Persistence (Cache-First Pipeline)

**What:** Each pipeline stage writes output to disk/database before proceeding. Use Parquet for raw caches (immutable, compressed), DuckDB for intermediate results (queryable), TSV/Parquet for final outputs (portable).

**When to use:** Always in long-running bioinformatics pipelines with external API dependencies. Essential for reproducibility.

**Trade-offs:**
- **Pro:** Pipeline restartability (skip completed stages). Debugging (inspect intermediate outputs). Provenance (timestamp, version, source).
- **Pro:** DuckDB enables fast analytical queries on intermediate data without full in-memory loads.
- **Con:** Disk I/O overhead (minor for your ~20K gene scale). Storage requirements (mitigated by Parquet compression).

**Example:**
```python
# src/pipeline/cli.py
import typer
import duckdb
from pathlib import Path

app = typer.Typer()

@app.command()
def run_layer(layer: str, force: bool = False):
    """Run single evidence layer retrieval + normalization."""
    cache_path = Path(f"data/raw/{layer}/results.parquet")

    # Check cache unless force refresh
    if cache_path.exists() and not force:
        typer.echo(f"Using cached {layer} data from {cache_path}")
        return

    # Retrieve + normalize
    retriever = get_retriever(layer)
    raw_data = retriever.retrieve(gene_list)
    normalized = retriever.normalize(raw_data)

    # Persist to Parquet + DuckDB
    normalized.write_parquet(cache_path)
    conn = duckdb.connect("data/intermediate/evidence.duckdb")
    conn.execute(f"CREATE OR REPLACE TABLE {layer} AS SELECT * FROM '{cache_path}'")
    conn.close()

@app.command()
def integrate(output: Path = Path("data/output/candidates_high.tsv")):
    """Integrate all evidence layers and generate candidates."""
    conn = duckdb.connect("data/intermediate/evidence.duckdb")

    # SQL-based multi-evidence integration
    query = """
    SELECT
        a.gene_id,
        a.annotation_score * 0.15 +
        e.expression_score * 0.20 +
        p.protein_score * 0.15 +
        l.localization_score * 0.25 +
        c.constraint_score * 0.15 +
        ph.phenotype_score * 0.10 AS total_score
    FROM annotation a
    JOIN expression e ON a.gene_id = e.gene_id
    JOIN protein_features p ON a.gene_id = p.gene_id
    JOIN localization l ON a.gene_id = l.gene_id
    JOIN constraint c ON a.gene_id = c.gene_id
    JOIN phenotypes ph ON a.gene_id = ph.gene_id
    WHERE total_score >= 0.7  -- High confidence threshold
    ORDER BY total_score DESC
    """

    result = conn.execute(query).pl()
    result.write_csv(output, separator="\t")
```

### Pattern 3: Configuration-Driven Behavior (Declarative Pipeline)

**What:** All scoring weights, thresholds, data source URLs, API keys, etc. defined in YAML config files. Code reads config, doesn't hardcode parameters.

**When to use:** Always for reproducible research pipelines. Allows parameter tuning without code changes.

**Trade-offs:**
- **Pro:** Configuration versioned in git → reproducibility. Easy to A/B test scoring schemes. Non-programmers can adjust weights.
- **Con:** Requires config validation layer (use pydantic). Risk of config drift if not validated.

**Example:**
```yaml
# config/pipeline.yaml
scoring:
  weights:
    annotation: 0.15
    expression: 0.20
    protein_features: 0.15
    localization: 0.25
    constraint: 0.15
    phenotypes: 0.10

  thresholds:
    high_confidence: 0.7
    medium_confidence: 0.5
    low_confidence: 0.3

data_sources:
  uniprot:
    base_url: "https://rest.uniprot.org/uniprotkb/search"
    version: "2026_01"
  gtex:
    file_path: "/data/external/GTEx_v8_median_tpm.tsv"
    version: "v8"

known_genes:
  exclusion_lists:
    - "config/ciliacarta_genes.txt"
    - "config/syscilia_genes.txt"
    - "config/omim_usher_genes.txt"
```

```python
# src/pipeline/config.py
from pydantic import BaseModel, Field
from typing import Dict
import yaml

class ScoringConfig(BaseModel):
    weights: Dict[str, float] = Field(..., description="Evidence layer weights")
    thresholds: Dict[str, float]

class PipelineConfig(BaseModel):
    scoring: ScoringConfig
    data_sources: Dict
    known_genes: Dict

def load_config(path: str = "config/pipeline.yaml") -> PipelineConfig:
    with open(path) as f:
        config_dict = yaml.safe_load(f)
    return PipelineConfig(**config_dict)
```

### Pattern 4: Provenance Tracking (Reproducibility First)

**What:** Every output file/table includes metadata: pipeline version, data source versions, timestamp, config hash. Enables exact reproduction.

**When to use:** Always in research pipelines. Critical for publication and validation.

**Trade-offs:**
- **Pro:** Full audit trail. Can reproduce results from 6 months ago. Meets FAIR data principles.
- **Con:** Requires discipline to capture versions (use git tags, API version headers, file checksums).

**Example:**
```python
# src/reporting/provenance.py
import hashlib
import json
from datetime import datetime
from pathlib import Path
import subprocess

def generate_provenance() -> dict:
    """Generate provenance metadata for pipeline run."""
    return {
        "pipeline_version": get_git_version(),
        "run_timestamp": datetime.utcnow().isoformat(),
        "config_hash": hash_config("config/pipeline.yaml"),
        "data_sources": {
            "uniprot": {"version": "2026_01", "retrieved": "2026-02-10"},
            "gtex": {"version": "v8", "file_modified": "2023-11-15"},
            # ... per-source metadata
        },
        "dependencies": get_package_versions(),
        "runtime_env": {
            "python": sys.version,
            "platform": platform.platform()
        }
    }

def get_git_version() -> str:
    """Get current git commit hash."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"]
    ).decode().strip()

def hash_config(path: str) -> str:
    """SHA256 hash of config file."""
    content = Path(path).read_bytes()
    return hashlib.sha256(content).hexdigest()[:8]
```

## Data Flow

### Pipeline Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│  1. INITIALIZATION                                           │
│     Load config/pipeline.yaml → Validate with pydantic       │
│     Load gene list (~20K human protein-coding genes)         │
│     Check data/raw/ cache status                             │
└────────────────────┬─────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────────────┐
│  2. PARALLEL RETRIEVAL (6 evidence layers + literature)      │
│     For each layer:                                          │
│       - Query external API/database                          │
│       - Cache raw response → data/raw/{layer}/               │
│       - Normalize to standard schema                         │
│       - Write to DuckDB table                                │
│                                                              │
│     [annotation] [expression] [protein] [localization]      │
│     [constraint] [phenotypes] [literature]                  │
│                                                              │
│     All layers independent, no inter-dependencies            │
└────────────────────┬─────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────────────┐
│  3. INTEGRATION                                              │
│     SQL join on gene_id across all DuckDB tables            │
│     Apply weighted scoring formula from config               │
│     Filter out known genes (CiliaCarta/SYSCILIA/OMIM)       │
│     Assign confidence tiers (high/medium/low)                │
└────────────────────┬─────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────────────┐
│  4. REPORTING                                                │
│     Generate per-gene evidence summaries                     │
│     Write tiered candidate lists (TSV)                       │
│     Attach provenance metadata                               │
│     Optionally: visualizations, statistics                   │
└──────────────────────────────────────────────────────────────┘
```

### Data Schema Evolution

```
RAW DATA (heterogeneous formats)
  ├── UniProt XML/JSON
  ├── GTEx TSV matrices
  ├── gnomAD VCF/TSV
  └── PubMed XML
      ↓ NORMALIZATION
INTERMEDIATE DATA (standardized schema in DuckDB)
  ├── Table: annotation
  │   ├── gene_id (TEXT, primary key)
  │   ├── annotation_score (FLOAT 0-1)
  │   ├── go_term_count (INT)
  │   └── data_source (TEXT)
  ├── Table: expression
  │   ├── gene_id (TEXT)
  │   ├── expression_score (FLOAT 0-1)
  │   ├── tissue_specificity (FLOAT)
  │   └── ciliated_tissue_enrichment (BOOLEAN)
  └── [similar schema for other 5 layers]
      ↓ INTEGRATION
FINAL OUTPUT (candidate lists)
  ├── candidates_high.tsv
  │   ├── gene_id
  │   ├── total_score (weighted sum)
  │   ├── confidence_tier (high/medium/low)
  │   └── [per-layer scores for transparency]
  └── evidence_summary.parquet
      └── [detailed per-gene evidence provenance]
```

### Key Data Flow Principles

1. **Unidirectional flow:** Raw → Intermediate → Output (no backflow, no circular dependencies)
2. **Gene ID as universal key:** All tables join on standardized gene_id (Ensembl or HGNC)
3. **Score normalization:** All evidence scores scaled 0-1 for comparability
4. **Immutable raw cache:** Never modify data/raw/ after creation (versioned, timestamped)
5. **DuckDB as integration hub:** Analytical queries across layers without full in-memory loads

## Build Order and Dependencies

### Recommended Build Order (Phases)

Given the component dependencies and validation requirements, build in this sequence:

#### Phase 1: Infrastructure (Week 1)
**Goal:** Establish project skeleton, config management, data storage patterns

**Components:**
1. Project structure (`pyproject.toml`, `src/pipeline/`, `config/`, `data/` hierarchy)
2. Config loading/validation (`config.py` with pydantic models)
3. DuckDB schema setup (create tables for 6 evidence layers)
4. Utility functions (gene ID mapping, caching helpers)

**Why first:** All downstream components depend on config system and data storage infrastructure.

**Validation:** Load sample config, create DuckDB tables, test gene ID mapping utility.

#### Phase 2: Single Evidence Layer Prototype (Week 2)
**Goal:** Prove the retrieval → normalization → storage pattern with one layer

**Components:**
1. Choose simplest layer (e.g., genetic constraint: gnomAD pLI/LOEUF)
2. Build retriever (API query, rate limiting, error handling)
3. Build normalizer (parse response, map gene IDs, scale scores)
4. Integrate with DuckDB storage

**Why second:** Validates architecture before scaling to 6 layers. Identifies issues early.

**Validation:** Run on 100 test genes, inspect Parquet cache + DuckDB table, verify schema.

#### Phase 3: Remaining Evidence Layers (Weeks 3-5)
**Goal:** Replicate Phase 2 pattern for all 6 layers + literature scan

**Components:**
1. Annotation (GO/UniProt completeness)
2. Expression (HPA/GTEx/CellxGene)
3. Protein features (domains/motifs/coiled-coil)
4. Localization (subcellular)
5. Phenotypes (MGI/ZFIN/IMPC)
6. Literature (PubMed API)

**Why third:** Independent layers can be built in parallel (or sequentially). No inter-dependencies.

**Validation:** Per-layer validation on test gene sets. Check schema consistency across layers.

#### Phase 4: Integration Layer (Week 6)
**Goal:** Combine evidence scores, apply weights, filter known genes

**Components:**
1. Multi-evidence scoring logic (SQL joins in DuckDB)
2. Known gene filter (CiliaCarta/SYSCILIA/OMIM exclusion)
3. Confidence tier assignment
4. Initial output generation (TSV candidate lists)

**Why fourth:** Requires all evidence layers complete. Core scientific logic.

**Validation:** Compare integrated scores against manual calculations for 10 test genes.

#### Phase 5: Reporting + Provenance (Week 7)
**Goal:** Generate publication-ready outputs with full audit trail

**Components:**
1. Per-gene evidence summaries
2. Provenance metadata generation
3. Output formatting (TSV + Parquet)
4. Optional: visualizations, statistics

**Why fifth:** Depends on integration layer. Presentation layer.

**Validation:** Manually review summaries for 20 high-confidence candidates. Verify provenance completeness.

#### Phase 6: CLI + Orchestration (Week 8)
**Goal:** Unified command-line interface for end-to-end pipeline

**Components:**
1. Typer CLI app with subcommands (run-layer, integrate, report)
2. Pipeline orchestration (dependency checking, progress logging)
3. Force-refresh flags, partial reruns

**Why last:** Integrates all components. User-facing interface.

**Validation:** Run full pipeline end-to-end on 1000 test genes. Benchmark runtime.

### Component Dependency Graph

```
┌──────────────┐
│ Config +     │ ← PHASE 1 (foundation)
│ Storage      │
└───────┬──────┘
        ↓
┌───────┴──────────────────────────────────┐
│ Single Layer Prototype                   │ ← PHASE 2 (proof of concept)
│ (Retriever + Normalizer + DuckDB)        │
└───────┬──────────────────────────────────┘
        ↓
┌───────┴──────────────────────────────────┐
│ 6 Evidence Layers (independent modules)  │ ← PHASE 3 (parallel work)
│ + Literature Scan                        │
└───────┬──────────────────────────────────┘
        ↓
┌───────┴──────────────────────────────────┐
│ Integration Layer                        │ ← PHASE 4 (core logic)
│ (Scoring + Filtering + Tiering)          │
└───────┬──────────────────────────────────┘
        ↓
┌───────┴──────────────────────────────────┐
│ Reporting + Provenance                   │ ← PHASE 5 (presentation)
└───────┬──────────────────────────────────┘
        ↓
┌───────┴──────────────────────────────────┐
│ CLI Orchestration                        │ ← PHASE 6 (interface)
└──────────────────────────────────────────┘
```

**Critical path:** Phase 1 → Phase 2 → Phase 4 (infrastructure + prototype + integration)
**Parallelizable:** Phase 3 (6 evidence layers can be built by different team members simultaneously)
**Deferrable:** Phase 5 (reporting) and Phase 6 (CLI polish) can be minimal initially

## Anti-Patterns to Avoid

### Anti-Pattern 1: Hardcoded API Keys and Endpoints

**What people do:** Embed API keys directly in code (`API_KEY = "abc123"`) or hardcode URLs.

**Why it's wrong:** Security risk (keys in git history), inflexibility (can't switch endpoints without code changes), breaks reproducibility (different users need different configs).

**Do this instead:** Use `.env` files for secrets (never committed), config files for endpoints. Load with `python-dotenv` or `pydantic-settings`.

```python
# WRONG
def query_uniprot():
    response = requests.get("https://rest.uniprot.org/...", headers={"API-Key": "secret123"})

# RIGHT
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    uniprot_api_key: str
    uniprot_base_url: str

    class Config:
        env_file = ".env"

settings = Settings()
response = requests.get(settings.uniprot_base_url, headers={"API-Key": settings.uniprot_api_key})
```

### Anti-Pattern 2: Monolithic All-in-One Script

**What people do:** Single 3000-line Python script that retrieves all data, normalizes, scores, and reports in one execution.

**Why it's wrong:** Impossible to restart from failure point (API rate limit at layer 5 → restart all 6 layers). Hard to test (can't unit test individual layers). No intermediate validation. Debugging nightmare.

**Do this instead:** Modular architecture with staged persistence (this entire ARCHITECTURE.md). Each layer is independently runnable. CLI orchestrates but doesn't enforce monolithic execution.

### Anti-Pattern 3: In-Memory-Only Data Processing

**What people do:** Load all 20K genes × 6 evidence layers into Pandas DataFrames, perform joins in memory, never write intermediate results.

**Why it's wrong:** Memory pressure (especially with expression matrices). No restartability. No audit trail. Limits scalability (what if you scale to 40K genes?).

**Do this instead:** Use DuckDB for intermediate storage. Write Parquet caches. DuckDB queries Parquet files directly (out-of-core analytics). Memory-efficient even at larger scales.

### Anti-Pattern 4: Ignoring Gene ID Ambiguity

**What people do:** Assume gene symbols are unique/stable. Join datasets on raw gene symbols from different sources.

**Why it's wrong:** Gene symbols are ambiguous (HLA-A vs HLAA), change over time, vary by organism. UniProt uses one ID system, GTEx another, gnomAD another. Mismatches cause silent data loss.

**Do this instead:** Standardize ALL gene identifiers to a single system (Ensembl or HGNC) during normalization. Build a gene ID mapper utility. Validate mappings (flag unmapped genes). Include original IDs in provenance.

```python
# src/pipeline/utils.py
import mygene

def standardize_gene_ids(gene_list: List[str], target_id: str = "ensembl") -> Dict[str, str]:
    """Map heterogeneous gene IDs to standard Ensembl IDs."""
    mg = mygene.MyGeneInfo()
    results = mg.querymany(gene_list, scopes="symbol,entrezgene,uniprot",
                           fields="ensembl.gene", species="human")

    mapping = {}
    for result in results:
        if "ensembl" in result:
            mapping[result["query"]] = result["ensembl"]["gene"]
        else:
            # Log unmapped genes for manual review
            logging.warning(f"Could not map gene ID: {result['query']}")

    return mapping
```

### Anti-Pattern 5: No Versioning or Provenance

**What people do:** Run pipeline, generate `candidates.tsv`, no record of config used or data source versions. Rerun 3 months later, get different results, can't explain why.

**Why it's wrong:** Irreproducible research. Can't debug score changes. Can't publish without provenance. Violates FAIR principles.

**Do this instead:** Implement Pattern 4 (Provenance Tracking). Every output has metadata footer/sidecar. Version config files in git. Tag releases. Include data source versions, tool versions, timestamps in all outputs.

## Integration Points

### External Services and APIs

| Service | Integration Pattern | Rate Limits / Notes |
|---------|---------------------|---------------------|
| **UniProt REST API** | HTTP GET with query params, JSON response | 1000 requests/hour. Use batch queries (`gene_ids=A,B,C`). Cache aggressively. |
| **GTEx Portal** | Download static TSV files, local queries | No API. Download median TPM matrices (~3 GB). Update quarterly. |
| **gnomAD** | Query via GraphQL API or download VCF | API: 10 requests/sec. Consider downloading constraint metrics TSV (500 MB). |
| **Human Protein Atlas** | Download bulk TSV files | No real-time API. Download tissue expression TSV. |
| **CellxGene** | Download h5ad files or use API | Census API available. Large files (>10 GB). Consider pre-filtering cell types. |
| **PubMed E-utilities** | Entrez Programming Utilities (E-utils) | 3 requests/sec without API key, 10/sec with key. Use batch queries. |
| **MGI/ZFIN/IMPC** | Download phenotype association files | Bulk downloads (TSV/XML). Monthly updates. |

### Internal Module Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **CLI ↔ Retrievers** | Function calls with config objects | CLI passes validated config, receives DataFrames/file paths |
| **Retrievers ↔ Normalizers** | DataFrame handoff (Polars/Pandas) | Retrievers return raw DataFrames, normalizers return standardized schema |
| **Normalizers ↔ Storage** | File writes (Parquet) + DuckDB inserts | Normalizers write directly, no abstraction layer needed |
| **Storage ↔ Integration** | SQL queries (DuckDB connection) | Integration layer reads via SQL joins, no Python data structures |
| **Integration ↔ Reporting** | DataFrame handoff | Integration returns scored DataFrame, reporting formats for output |

### Data Format Interchange

```
External APIs → JSON/XML/TSV (heterogeneous)
      ↓
Retrievers → Polars DataFrame (in-memory, typed)
      ↓
Normalizers → Polars DataFrame (standardized schema)
      ↓
Storage Layer → Parquet (disk cache) + DuckDB (queryable)
      ↓
Integration → DuckDB Result (SQL query output)
      ↓
Reporting → TSV/Parquet (final outputs)
```

**Why Polars over Pandas?** Faster, more memory-efficient, better type system, native lazy evaluation. Polars is becoming standard in modern bioinformatics Python pipelines (2024-2026).

**Why DuckDB over SQLite?** Columnar storage (better for analytics), vectorized execution (10-100x faster for aggregations), native Parquet support, can query files without import.

## Scaling Considerations

### Current Scale (20K genes)

**Architecture:** Single-machine Python pipeline with local DuckDB. No distributed computing needed.

**Bottlenecks:**
- API rate limits (PubMed: 10 req/sec, UniProt: 1000 req/hour) → solved by caching + batch queries
- Expression matrix size (GTEx + CellxGene: ~10 GB) → DuckDB handles via out-of-core queries

**Runtime estimate:**
- Data retrieval (with caching): 1-4 hours (depending on API latency)
- Normalization + integration: <15 minutes (DuckDB vectorized queries)
- **Total:** ~2-5 hours for full pipeline run (initial). <30 min for reruns with cache.

### Medium Scale (50K genes, e.g., include non-coding)

**Architecture adjustments:** Same architecture. Increase DuckDB memory limit. Consider Parquet partitioning by chromosome.

**Bottlenecks:** Expression matrices grow to ~25 GB. Still manageable with 32 GB RAM + DuckDB out-of-core.

### Large Scale (500K genes, e.g., cross-species)

**Architecture adjustments:** Consider workflow orchestrators (Nextflow/Snakemake) for parallelization. Distribute retrieval across multiple workers. Switch from local DuckDB to distributed query engine (DuckDB over S3, or Apache Spark).

**When to consider:** Only if scaling beyond single organism or adding many more evidence layers.

### GPU Utilization Note

Your NVIDIA 4090 GPU is available but **not needed** for this pipeline. Use cases for GPU:
- Deep learning-based gene prioritization (not rule-based scoring)
- Protein structure prediction (AlphaFold, not in scope)
- Large-scale sequence alignment (not in scope)

Rule-based multi-evidence scoring is CPU-bound (DuckDB is CPU-optimized). GPU would be idle.

## Validation and Testing Strategy

### Testing Pyramid

```
┌─────────────────────────┐
│  Integration Tests      │  ← Full pipeline on 100 test genes
│  (slow, comprehensive)  │
├─────────────────────────┤
│  Component Tests        │  ← Per-layer retrieval + normalization
│  (medium, focused)      │     Mock API responses
├─────────────────────────┤
│  Unit Tests             │  ← Utility functions, scoring logic
│  (fast, narrow)         │     Gene ID mapping, score calculations
└─────────────────────────┘
```

### Validation Datasets

1. **Positive controls:** Known ciliopathy genes (USH2A, MYO7A, CDH23) → should score HIGH
2. **Negative controls:** Housekeeping genes (GAPDH, ACTB) → should score LOW
3. **Novel candidates:** Manually validate 10 high-scoring unknowns via literature review
4. **Benchmark datasets:** If available, compare to published cilia gene sets (CiliaCarta as gold standard)

### Quality Gates

- **Schema validation:** All DuckDB tables match expected schema (pydantic models)
- **Completeness checks:** All 20K genes have entries in all 6 evidence tables (flag missing data)
- **Score sanity checks:** No scores <0 or >1, distribution checks (not all genes score 0.5)
- **Provenance validation:** Every output has complete metadata (no missing versions/timestamps)

## Technology Choices Summary

| Layer | Technology | Reasoning |
|-------|------------|-----------|
| **CLI Framework** | Typer (or Click) | Type-hinted, auto-generated help, modern Python. Click if need maximum maturity. |
| **Config Format** | YAML | Dominant in bioinformatics. Human-readable. Pydantic validation. |
| **Data Processing** | Polars | Faster + more memory-efficient than Pandas. Native lazy eval. Modern standard. |
| **Intermediate Storage** | DuckDB | Columnar analytics, out-of-core queries, native Parquet support. 10-100x faster than SQLite for aggregations. |
| **Cache Format** | Parquet | Compressed columnar format. Standard for big data. DuckDB-native. |
| **Final Output** | TSV + Parquet | TSV for human readability + Excel compatibility. Parquet for programmatic access. |
| **API Client** | requests + biopython | Standard for REST APIs. Biopython for Entrez/PubMed utilities. |
| **Gene ID Mapping** | mygene.info API | Comprehensive cross-reference database. MyGeneInfo Python client. |

## Sources

**Architecture Patterns:**
- [Bioinformatics Pipeline Architecture Best Practices](https://www.meegle.com/en_us/topics/bioinformatics-pipeline/bioinformatics-pipeline-architecture)
- [Developing and reusing bioinformatics pipelines using scientific workflow systems](https://www.sciencedirect.com/science/article/pii/S2001037023001010)
- [PHA4GE Pipeline Best Practices](https://github.com/pha4ge/public-health-pipeline-best-practices/blob/main/docs/pipeline-best-practices.md)

**Multi-Evidence Integration:**
- [Multi-omics data integration methods](https://academic.oup.com/bib/article/26/4/bbaf355/8220754)
- [FAS: multi-layered feature architectures for protein similarity](https://academic.oup.com/bioinformatics/article/39/5/btad226/7135831)

**Workflow Tools and Patterns:**
- [A lightweight, flow-based toolkit for bioinformatics pipelines](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-12-61)
- [Using prototyping to choose a workflow management system](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1008622)

**Data Storage:**
- [DuckDB vs SQLite for bioinformatics](https://bridgeinformatics.com/from-pandas-to-spark-and-back-again-why-bioinformatics-should-know-duckdb/)
- [Modern Data Formats for Big Bioinformatics](https://www.researchgate.net/publication/316682490_Modern_Data_Formats_for_Big_Bioinformatics_Data_Analytics)
- [DuckDB vs SQLite: Complete Comparison](https://www.datacamp.com/blog/duckdb-vs-sqlite-complete-database-comparison)

**Reproducibility and Provenance:**
- [Genomics pipelines and data integration challenges](https://pmc.ncbi.nlm.nih.gov/articles/PMC5580401/)
- [Pipeline Provenance for Reproducibility](https://arxiv.org/abs/2404.14378)
- [Open Targets provenance metadata](https://blog.opentargets.org/provenance-metadata/)

**Python CLI Tools:**
- [Comparing argparse, Click, and Typer](https://codecut.ai/comparing-python-command-line-interface-tools-argparse-click-and-typer/)
- [Building Python CLI Tools Guide](https://inventivehq.com/blog/python-cli-tools-guide)

**Gene Annotation Pipelines:**
- [NCBI Eukaryotic Genome Annotation Pipeline](https://www.ncbi.nlm.nih.gov/refseq/annotation_euk/process/)
- [AnnotaPipeline: integrated annotation tool](https://www.frontiersin.org/journals/genetics/articles/10.3389/fgene.2022.1020100/full)

**Literature Mining:**
- [NCBI Text Mining APIs](https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/)
- [PubTator 3.0: AI-powered literature resource](https://academic.oup.com/nar/article/52/W1/W540/7640526)

**Validation:**
- [Standards for Validating NGS Bioinformatics Pipelines](https://www.sciencedirect.com/science/article/pii/S1525157817303732)
- [NFTest: automated Nextflow pipeline testing](https://pubmed.ncbi.nlm.nih.gov/38341660/)

---
*Architecture research for: Usher Cilia Gene Discovery Pipeline*
*Researched: 2026-02-11*

# Technology Stack

**Project:** Bioinformatics Cilia/Usher Gene Discovery Pipeline
**Researched:** 2026-02-11
**Confidence:** HIGH

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12+ | Pipeline runtime | Industry standard for bioinformatics, extensive ecosystem, type hints, best library support. Avoid 3.10-3.11 (older), 3.14 (too new for some libraries). |
| Polars | 1.38+ | DataFrame processing | 6-38x faster than Pandas for genomic operations (via polars-bio), native Rust backend, streaming for large datasets, better memory efficiency for ~20K gene analysis. |
| Typer | 0.21+ | CLI framework | Modern type-hint based CLI, auto-generates help docs, built on Click (battle-tested), cleaner than argparse for modular scripts. |
| Pydantic | 2.12+ | Data validation & config | Type-safe configuration, 1.5-1.75x faster than v1, validates gene scores/weights, prevents config errors that waste compute time. |

### Data Access Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| gget | 0.30+ | Multi-source gene annotation | PRIMARY: Unified API for Ensembl, UniProt, NCBI. Fetches gene metadata, sequences, GO terms. Official Context7 support, actively maintained. |
| pyensembl | Latest | Ensembl GTF/FASTA access | FALLBACK: If gget insufficient. Downloads/caches Ensembl data locally. More control but less convenient than gget. |
| Biopython | 1.86+ | Sequence analysis, format parsing | ALWAYS: Parse FASTA/GenBank, sequence manipulation, EntrezId conversion. De facto standard, mandatory for bioinformatics. Requires Python 3.10+. |
| requests | 2.32+ | HTTP API calls | ALWAYS: Session-based API calls to REST endpoints (InterPro, STRING, gnomAD). Connection pooling, retry logic, timeout control. |
| metapub | 0.6.4+ | PubMed literature mining | PRIMARY for PubMed: Abstracts via eutils, DOI finding, formatted citations. Production-tested at bioinformatics facilities. Python 3.8+. |
| gnomad-toolbox | 0.0.1+ | gnomAD constraint metrics | PRIMARY: Official Broad Institute tool (Jan 2025), loads/filters constraint data. Requires Python 3.9+. Note: Very new, validate stability. |

### scRNA-seq & Expression Data

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scanpy | 1.12+ | scRNA-seq analysis | For processing single-cell cilia expression. Clustering, QC, cell type annotation. Requires Python 3.12+. |
| anndata | 0.11+ | scRNA-seq data structures | DEPENDENCY: Required by scanpy. Stores expression matrices. |
| pyGTEx | Git latest | GTEx tissue expression | For GTEx API queries. Install from GitHub: pip install git+https://github.com/w-gao/pyGTEx.git |
| tspex | Latest | Tissue specificity scoring | For calculating tissue-specific expression scores from GTEx data. |

### Data Validation & Quality

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandera | 0.29+ | DataFrame schema validation | ALWAYS: Validate gene data schemas, catch data quality issues early. 1.5-1.75x faster with Pydantic v2. Supports Polars/Pandas. Python 3.10+. |
| pydantic-settings | 2.12+ | YAML/TOML config loading | ALWAYS: Load pipeline configs with validation. Built-in TOML/YAML support (Nov 2025). Prevents config typos from wasting GPU time. |

### Workflow & CLI

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rich | 14.3+ | CLI progress bars, formatting | ALWAYS: Progress tracking for 20K gene processing, formatted tables, error highlighting. Production/Stable. Python 3.8+. |
| structlog | Latest | Structured logging | ALWAYS: JSON logs for pipeline debugging, correlation IDs for tracking genes through pipeline, contextvars for thread safety. |
| click | Latest | CLI subcommands | IF NEEDED: Fallback if Typer insufficient (Typer built on Click). |

### Performance & Caching

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| diskcache | Latest | Disk-based API response caching | ALWAYS: Cache API responses (Ensembl, UniProt, gnomAD) to avoid re-fetching during reruns. Persistent across runs. |
| joblib | Latest | NumPy/ML model caching | For AlphaFold-Multimer result caching, large array serialization. Disk-based, survives restarts. |
| httpx | 0.28+ | Async HTTP client (OPTIONAL) | ONLY IF async needed: HTTP/2 support, faster concurrent API calls. Otherwise use requests (simpler). |

### Testing & Development

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| pytest | Latest | Testing framework | Industry standard. Fixtures for test data, parametrization for edge cases. |
| pytest-cov | Latest | Coverage reporting | Ensure gene scoring logic tested. |
| mypy | Latest | Static type checking | Catch type errors pre-runtime. Essential with Pydantic/Typer type hints. |
| ruff | Latest | Linting & formatting | 10-100x faster than pylint/black. Rust-based, configurable. |

### Package Management

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| uv | Latest | Dependency manager | 10-100x faster than pip, replaces pip/pip-tools/poetry/pyenv. Rust-based (Astral team). Strict PEP compliance. Use for new project. |
| pyproject.toml | - | Dependency specification | Standard Python packaging. Works with uv/pip. |

## Installation

```bash
# Install uv (package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project with Python 3.12
uv init
uv python install 3.12
uv python pin 3.12

# Core dependencies
uv add polars==1.38.1
uv add typer==0.21.2
uv add pydantic==2.12.5
uv add pydantic-settings==2.12.0

# Data access
uv add gget==0.30.2
uv add biopython==1.86
uv add requests==2.32.5
uv add metapub==0.6.4
uv add gnomad-toolbox==0.0.1

# scRNA-seq & expression
uv add scanpy==1.12
uv add anndata==0.11.4
uv add "pyGTEx @ git+https://github.com/w-gao/pyGTEx.git"

# Validation & quality
uv add pandera==0.29.0

# CLI & workflow
uv add rich==14.3.2
uv add structlog

# Performance & caching
uv add diskcache
uv add joblib

# Dev dependencies
uv add --dev pytest
uv add --dev pytest-cov
uv add --dev mypy
uv add --dev ruff
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| DataFrame | Polars | Pandas | Pandas 6-38x slower for genomic interval operations (bioframe vs polars-bio benchmarks). Polars has streaming for >RAM datasets. |
| CLI | Typer | argparse | argparse verbose, no auto-docs. Typer uses type hints, generates help automatically. |
| CLI | Typer | Click | Click requires decorators for everything. Typer cleaner with type hints. (Typer built on Click internally.) |
| HTTP | requests | httpx | httpx adds async/HTTP/2 complexity. Requests simpler for synchronous API calls. Use httpx only if async needed. |
| Package Mgr | uv | Poetry | Poetry slower (not Rust-based), separate config file. uv 10-100x faster, uses standard pyproject.toml, replaces more tools. |
| Package Mgr | uv | pip + pip-tools | uv replaces both, adds reproducible lock files, faster resolution. |
| Config | pydantic-settings | Hydra | Hydra overkill for pipeline config. Better for ML experiments with many hyperparameter sweeps. pydantic-settings simpler. |
| Logging | structlog | stdlib logging | stdlib logging requires custom filters for structured output. structlog built for JSON logs from start. |
| Workflow | Modular scripts | Snakemake | Snakemake overkill for local pipeline. Adds complexity, HPC features not needed. Use if scaling to cluster later. |
| Workflow | Modular scripts | Nextflow | Nextflow for cloud/enterprise. Groovy syntax steep learning curve. Not needed for local NVIDIA 4090 workstation. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Pandas (alone) | 6-38x slower than Polars for genomic operations. Memory inefficient for 20K genes. | Polars with polars-bio extension |
| Python 3.9 or older | Many modern libraries require 3.10+ (Biopython 1.86, scanpy 1.12, pandera 0.29). Missing type hint features. | Python 3.12 (stable, well-supported) |
| Python 3.14 | Too new. Some libraries not tested yet. Risk of compatibility issues. | Python 3.12 or 3.13 |
| Pydantic v1 | 1.5-1.75x slower than v2. V2 major rewrite with better validation. | Pydantic 2.12+ |
| argparse for complex CLI | Verbose, manual help text, no type validation. | Typer (type-hint based) |
| Poetry (for new projects) | Slower dependency resolution, separate config file, fewer tools replaced. | uv (10-100x faster, standard pyproject.toml) |
| Manual API retries | Error-prone, inconsistent timeout handling. | requests.Session with retry adapters + timeout |
| print() debugging | No structured logs, hard to trace gene through pipeline. | structlog with correlation IDs |

## Stack Patterns by Use Case

**Local workstation pipeline (current requirement):**
- Use Polars + modular Typer CLI scripts
- Avoid Snakemake/Nextflow (overkill)
- Use diskcache for API responses (persistent across runs)
- Use rich for progress tracking (20K genes takes time)

**If scaling to HPC cluster later:**
- Add Snakemake for workflow orchestration
- Keep modular scripts (Snakemake calls them)
- Use job scheduler integration (SLURM/PBS)

**If adding async API calls:**
- Replace requests with httpx
- Use asyncio event loop
- Batch API calls (e.g., 100 genes at once to UniProt)

**For GPU-accelerated steps (AlphaFold-Multimer downstream):**
- NVIDIA 4090 has 24GB VRAM (below 32GB recommended minimum for AlphaFold2 NIM)
- May work for smaller predictions with appropriate configurations
- Use joblib to cache results (avoid re-running expensive predictions)

## Version Compatibility

| Package | Requires Python | Notes |
|---------|-----------------|-------|
| Biopython 1.86 | >= 3.10 | Blocks Python 3.9 |
| scanpy 1.12 | >= 3.12 | Blocks Python 3.10, 3.11 |
| Polars 1.38 | >= 3.10 | Recommended 3.12+ |
| Typer 0.21 | >= 3.9 | Works with 3.9-3.14 |
| Pydantic 2.12 | >= 3.9 | Requires v2 for performance |
| pandera 0.29 | >= 3.10 | Supports Polars + Pandas |
| metapub 0.6.4 | >= 3.8 | Older requirement, works with 3.12 |
| gnomad-toolbox 0.0.1 | >= 3.9 | Very new (Jan 2025), monitor stability |

**Minimum Python:** 3.12 (required by scanpy)
**Recommended Python:** 3.12 (stable, well-supported by all libraries)

## Data Source APIs & Formats

| Source | Access Method | Library | Format | Notes |
|--------|---------------|---------|--------|-------|
| Ensembl | REST API | gget, pyensembl | JSON, GTF | Rate limits apply. Cache with diskcache. |
| UniProt | REST API | gget, requests | JSON, XML | Batch queries supported. |
| NCBI/PubMed | Entrez eutils | metapub, Biopython.Entrez | XML | Free but rate limited (3 req/sec without key). |
| gnomAD | Downloads + API | gnomad-toolbox | Hail Tables, TSV | Large files. Use constraint metrics API. |
| InterPro | REST API | requests | JSON | Protein domains/motifs. Free, rate limited. |
| GTEx | Portal + API | pyGTEx | TSV, JSON | Expression data. Portal downloads for bulk. |
| HPA | Downloads | requests | TSV | Tissue/cell expression. Download bulk files. |
| STRING | API + downloads | requests | TSV | PPI networks. API for queries, downloads for bulk. |
| BioGRID | Downloads | requests | TSV | PPI data. Download releases, parse locally. |
| MGI/ZFIN/IMPC | Web + downloads | requests | Various | No official Python API. Web scraping or bulk downloads. |

## Configuration Strategy

Use Pydantic models for type-safe configuration:

```python
# config.py
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class ScoringWeights(BaseModel):
    tissue_expression: float = Field(ge=0, le=1)
    protein_domains: float = Field(ge=0, le=1)
    genetic_constraint: float = Field(ge=0, le=1)
    literature_score: float = Field(ge=0, le=1)

class PipelineConfig(BaseSettings):
    model_config = SettingsConfigDict(
        toml_file='pipeline_config.toml',
        yaml_file='pipeline_config.yaml'
    )

    weights: ScoringWeights
    api_cache_dir: str = ".cache/api_responses"
    output_tiers: list[str] = ["high", "medium", "low"]
```

Load from TOML/YAML, validated at startup. Prevents runtime config errors.

## Logging Strategy

Use structlog for structured JSON logging:

```python
import structlog

# Configure once at startup
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# In pipeline, bind gene context
logger = logger.bind(gene_id="ENSG00000123456", gene_symbol="USH2A")
logger.info("scoring_complete", score=0.85, tier="high")
```

Enables filtering/searching logs by gene, tracing genes through pipeline.

## Sources

**HIGH CONFIDENCE (Official Docs + Context7):**
- [Polars 1.38.1 PyPI](https://pypi.org/project/polars/) - Version verified Feb 2026
- [gget 0.30.2 PyPI](https://pypi.org/project/gget/) - Version verified Feb 2026
- [Biopython 1.86 PyPI](https://pypi.org/project/biopython/) - Version verified Oct 2025
- [Typer 0.21.2 PyPI](https://pypi.org/project/typer/) - Version verified Feb 2026
- [Pydantic 2.12.5 PyPI](https://pypi.org/project/pydantic/) - Version verified Nov 2025
- [pandera 0.29.0 PyPI](https://pypi.org/project/pandera/) - Version verified Jan 2026
- [requests 2.32.5 PyPI](https://pypi.org/project/requests/) - Version verified Aug 2025
- [httpx 0.28.1 PyPI](https://pypi.org/project/httpx/) - Version verified Dec 2024
- [rich 14.3.2 PyPI](https://pypi.org/project/rich/) - Version verified Feb 2026
- [scanpy 1.12 PyPI](https://pypi.org/project/scanpy/) - Version verified Jan 2026
- [metapub 0.6.4 PyPI](https://pypi.org/project/metapub/) - Version verified Aug 2025
- [gnomad-toolbox 0.0.1 PyPI](https://pypi.org/project/gnomad-toolbox/) - Version verified Jan 2025

**MEDIUM CONFIDENCE (WebSearch + Official Sources):**
- [polars-bio performance benchmarks](https://academic.oup.com/bioinformatics/article/41/12/btaf640/8362264) - Oxford Academic, Dec 2025
- [gget genomic database querying](https://pmc.ncbi.nlm.nih.gov/articles/PMC9835474/) - PMC publication
- [STRING database 12.5 update](https://academic.oup.com/nar/article/53/D1/D730/7903368) - NAR 2025
- [InterPro 2025 update](https://academic.oup.com/nar/article/53/D1/D444/7905301) - NAR 2025
- [uv package manager overview](https://www.analyticsvidhya.com/blog/2025/08/uv-python-package-manager/) - Multiple sources confirm 10-100x speedup
- [Pydantic-settings TOML/YAML support](https://levelup.gitconnected.com/pydantic-settings-2025-a-clean-way-to-handle-configs-f1c432030085) - Nov 2025 release notes
- [Python logging best practices 2025](https://signoz.io/guides/python-logging-best-practices/) - Industry practices
- [Nextflow vs Snakemake 2025 comparison](https://www.tracer.cloud/resources/bioinformatics-pipeline-frameworks-2025) - Workflow framework analysis

**MEDIUM-LOW CONFIDENCE (Limited verification):**
- AlphaFold NVIDIA 4090 compatibility - [GitHub issues](https://github.com/kalininalab/alphafold_non_docker/issues/77) suggest challenges, official docs specify 80GB GPUs
- MGI/ZFIN/IMPC Python API - No official Python libraries found, [ZFIN](https://zfin.org/) and [MGI](https://www.informatics.jax.org/) provide web interfaces and bulk downloads

---
*Stack research for: Bioinformatics Cilia/Usher Gene Discovery Pipeline*
*Researched: 2026-02-11*
*Confidence: HIGH for core stack, MEDIUM for workflow alternatives, MEDIUM-LOW for animal model APIs*

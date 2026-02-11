# Phase 2: Prototype Evidence Layer - Research

**Researched:** 2026-02-11
**Domain:** Genomic data retrieval and processing pipelines with Python
**Confidence:** MEDIUM-HIGH

## Summary

Phase 2 implements a prototype data pipeline to retrieve gnomAD constraint metrics (pLI, LOEUF) for human protein-coding genes, filter by coverage quality, normalize scores, and store in DuckDB with checkpoint-restart capability. This research identifies the standard Python stack for genomic data pipelines, validated patterns for checkpoint-restart, and critical data quality considerations.

gnomAD constraint data is available as downloadable TSV files from the Broad Institute. The standard approach is to download flat files (TSV.bgz format), decompress, parse with Polars for high performance, apply quality filters, normalize scores, and persist to DuckDB. The v4.0/v4.1 metrics use updated thresholds (LOEUF < 0.6 for constrained genes, median exome depth ≥30x for coverage quality) compared to v2.1.1.

Key architectural insight: Use Polars for ETL (fast, streaming-capable), DuckDB for storage (native DataFrame integration via Arrow), and Click for CLI scaffolding. Checkpoint-restart requires idempotent operations with file-based state tracking. Missing genomic data MUST be encoded as NULL/None (not zero) to distinguish "no data" from "measured as zero."

**Primary recommendation:** Use Polars 1.38+ for data processing with lazy evaluation and streaming, DuckDB 1.4+ for storage with Arrow zero-copy integration, Click 8.3+ for CLI framework, httpx 0.28+ for data downloads with retry logic, and structlog 25.5+ for structured logging. Implement checkpoint-restart via file-based state markers and idempotent operations.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| polars | 1.38+ | DataFrame processing, ETL | Fastest Python DataFrame library (Rust-based), native streaming for large datasets, lazy evaluation, zero dependencies, 70ms import vs pandas 520ms |
| duckdb | 1.4+ | Analytical database storage | Native Polars/pandas integration via Arrow, columnar storage optimized for analytics, embedded (no server), native Parquet/CSV I/O |
| click | 8.3+ | CLI framework | Composable command groups, automatic help generation, type validation, industry standard for Python CLIs |
| httpx | 0.28+ | HTTP client for data downloads | Async/sync support, HTTP/2, streaming downloads, modern requests replacement, strict timeouts |
| pydantic | 2.12+ | Data validation and config | Rust-based validation (v2), type-safe config management, clear error messages, industry standard |
| structlog | 25.5+ | Structured logging | JSON logging for pipelines, context binding, production-proven since 2013, integrates with stdlib logging |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | 9.1+ | Retry logic | Network requests, transient failures, exponential backoff patterns |
| pytest | 9.0+ | Testing framework | Unit/integration tests, fixtures for test data, 1300+ plugins |
| pathlib | stdlib | File path handling | All file operations (cross-platform, OOP, more readable than os.path) |
| PyYAML | latest | Config file parsing | If using YAML configs (TOML preferred for simplicity) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Polars | pandas | pandas: larger ecosystem, more tutorials; Polars: 5-10x faster, better memory efficiency, streaming for large files |
| DuckDB | SQLite | SQLite: more mature, ubiquitous; DuckDB: native DataFrame integration, better analytics performance, Parquet support |
| httpx | requests | requests: more mature, simpler API; httpx: async support, HTTP/2, better timeouts, active development |
| structlog | stdlib logging | stdlib: no dependencies, familiar; structlog: structured output, easier debugging, better for log aggregation |

**Installation:**
```bash
# Core stack
pip install 'polars[pyarrow]>=1.38' 'duckdb>=1.4' 'click>=8.3' 'httpx>=0.28' 'pydantic>=2.12' 'structlog>=25.5'

# Development dependencies
pip install 'pytest>=9.0' 'tenacity>=9.1'
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── cli/              # Click command groups
│   ├── __init__.py
│   ├── setup.py      # Setup command (checkpoint-restart pattern)
│   └── query.py      # Query commands
├── pipeline/         # Data processing logic
│   ├── __init__.py
│   ├── fetch.py      # Data download with retry
│   ├── transform.py  # Filtering, normalization
│   └── load.py       # DuckDB persistence
├── models/           # Pydantic models
│   ├── __init__.py
│   ├── config.py     # Configuration schemas
│   └── evidence.py   # Data schemas
└── utils/            # Shared utilities
    ├── __init__.py
    ├── checkpoint.py # Checkpoint state management
    └── logging.py    # Structured logging setup
```

### Pattern 1: Checkpoint-Restart for Data Pipelines
**What:** Track pipeline progress with file-based state markers; resume from last successful step on failure
**When to use:** Long-running downloads/processing that may fail partway through
**Example:**
```python
# Source: Verified pattern from checkpoint-restart research
from pathlib import Path
import polars as pl

def checkpoint_exists(step_name: str, checkpoint_dir: Path) -> bool:
    """Check if checkpoint file exists for given step."""
    return (checkpoint_dir / f"{step_name}.done").exists()

def mark_checkpoint(step_name: str, checkpoint_dir: Path) -> None:
    """Mark step as complete."""
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (checkpoint_dir / f"{step_name}.done").touch()

def setup_evidence_layer(force: bool = False) -> None:
    """Setup evidence layer with checkpoint-restart."""
    checkpoint_dir = Path(".data/checkpoints")

    # Step 1: Download gnomAD constraint data
    if force or not checkpoint_exists("download_gnomad", checkpoint_dir):
        download_gnomad_constraint_metrics()
        mark_checkpoint("download_gnomad", checkpoint_dir)

    # Step 2: Filter by coverage quality
    if force or not checkpoint_exists("filter_quality", checkpoint_dir):
        filter_by_coverage_quality()
        mark_checkpoint("filter_quality", checkpoint_dir)

    # Step 3: Normalize scores
    if force or not checkpoint_exists("normalize", checkpoint_dir):
        normalize_constraint_scores()
        mark_checkpoint("normalize", checkpoint_dir)

    # Step 4: Load to DuckDB
    if force or not checkpoint_exists("load_duckdb", checkpoint_dir):
        load_to_duckdb()
        mark_checkpoint("load_duckdb", checkpoint_dir)
```

### Pattern 2: Polars + DuckDB Integration via Arrow
**What:** Zero-copy data exchange between Polars DataFrames and DuckDB tables using Apache Arrow
**When to use:** ETL workflows where you process with Polars and persist with DuckDB
**Example:**
```python
# Source: https://duckdb.org/docs/stable/guides/python/polars
import duckdb
import polars as pl

# Process data with Polars (lazy evaluation)
df = pl.scan_csv("gnomad_constraints.tsv").filter(
    pl.col("mean_depth") >= 30
).filter(
    pl.col("cds_covered_pct") >= 0.9
).collect()

# Write to DuckDB (zero-copy via Arrow)
con = duckdb.connect("evidence.duckdb")
con.execute("CREATE TABLE IF NOT EXISTS constraint_metrics AS SELECT * FROM df")

# Query DuckDB, return as Polars (zero-copy)
result = con.sql("SELECT * FROM constraint_metrics WHERE loeuf < 0.6").pl()
```

### Pattern 3: HTTP Downloads with Retry and Streaming
**What:** Download large files with exponential backoff retry and streaming to avoid memory issues
**When to use:** Downloading gnomAD constraint files (can be 100s of MB compressed)
**Example:**
```python
# Source: Verified pattern from httpx + tenacity research
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from pathlib import Path

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
def download_file_with_retry(url: str, output_path: Path) -> None:
    """Download file with streaming and exponential backoff retry."""
    with httpx.stream("GET", url, timeout=300.0) as response:
        response.raise_for_status()
        with output_path.open("wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
```

### Pattern 4: Missing Data as NULL (not zero)
**What:** Distinguish "no measurement" from "measured as zero" in genomic data
**When to use:** Parsing gnomAD data where some genes lack constraint estimates
**Example:**
```python
# Source: Verified from genomic data quality research
import polars as pl

# CORRECT: Preserve nulls, don't fill with 0
df = pl.read_csv("gnomad_constraints.tsv", null_values=["NA", "", "."])

# Add quality flag column
df = df.with_columns([
    pl.when(pl.col("loeuf").is_null())
      .then(pl.lit("incomplete_coverage"))
      .otherwise(pl.lit("measured"))
      .alias("quality_flag")
])

# WRONG: Filling nulls with 0 conflates "unknown" with "zero constraint"
# df = df.fill_null(0)  # DON'T DO THIS
```

### Pattern 5: Provenance Sidecar Files
**What:** Store metadata about data sources, processing steps, and timestamps alongside output files
**When to use:** Every data file produced by the pipeline
**Example:**
```python
# Source: Verified from provenance tracking research
import json
from pathlib import Path
from datetime import datetime, timezone

def write_provenance_sidecar(
    data_file: Path,
    source_url: str,
    processing_steps: list[str],
    version: str
) -> None:
    """Write provenance metadata as JSON sidecar."""
    provenance = {
        "data_file": data_file.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "url": source_url,
            "version": version,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        },
        "processing": {
            "steps": processing_steps,
            "software": {
                "python": "3.10+",
                "polars": "1.38+",
                "duckdb": "1.4+"
            }
        }
    }

    sidecar_path = data_file.with_suffix(data_file.suffix + ".meta.json")
    sidecar_path.write_text(json.dumps(provenance, indent=2))
```

### Anti-Patterns to Avoid
- **Using pandas for large genomic files:** Pandas loads entire file into memory; use Polars lazy/streaming instead
- **Filling nulls with zeros:** In genomic data, NULL means "no measurement"; zero means "measured as zero"
- **Building custom retry logic:** Use tenacity library instead of hand-rolled loops
- **Storing credentials in code:** Use environment variables or secrets managers
- **Logging to files in containers:** Log to stdout/stderr for cloud/container environments

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry logic for network requests | Custom loops with sleep/counters | tenacity library | Exponential backoff, jitter, circuit breakers are subtle; library handles edge cases (max retries, timeout interactions, exception types) |
| DataFrame operations | Custom row iteration, list comprehensions | Polars expressions | Hand-rolled loops are 10-100x slower; Polars parallelizes automatically, optimizes query plans |
| CLI argument parsing | argparse with manual validation | Click with type hints | Click auto-generates help, validates types, supports subcommands; less boilerplate |
| Data validation | Manual type checks, if/else chains | Pydantic models | Pydantic validates at parse time, generates clear errors, integrates with type checkers |
| Structured logging | Manual JSON.dumps in print statements | structlog library | structlog binds context automatically, handles serialization edge cases (datetimes, exceptions), integrates with log aggregators |
| Genomic interval operations | Custom coordinate comparisons | bioframe or pybedtools | Genomic intervals have edge cases (strand, 0-based vs 1-based); libraries handle correctly |

**Key insight:** Genomic data pipelines have solved problems (retry, validation, DataFrame ops). Using libraries reduces bugs, improves performance, and provides battle-tested edge case handling. Custom solutions for "simple" problems like retry logic fail under production conditions (network flakiness, partial downloads, timeout interactions).

## Common Pitfalls

### Pitfall 1: Conflating Missing Data with Zero Values
**What goes wrong:** Filling null constraint scores with 0 makes genes with "no data" appear as "unconstrained genes"
**Why it happens:** Standard ML practice is to impute missing values; doesn't apply to genomic measurements
**How to avoid:** Preserve NULLs throughout pipeline; add explicit `quality_flag` column; document semantics
**Warning signs:** Seeing unrealistic distributions (spike at zero), genes without coverage showing constraint scores

### Pitfall 2: Memory Errors from Eager DataFrame Operations
**What goes wrong:** `pl.read_csv()` loads entire file into RAM; crashes on large gnomAD files
**Why it happens:** pandas habits carry over; not using Polars' lazy/streaming features
**How to avoid:** Use `pl.scan_csv()` for lazy evaluation; add `.streaming=True` to `.collect()`; test with full-size files
**Warning signs:** Slow startup, high memory usage in profiler, OOM crashes on production-size data

### Pitfall 3: Non-Idempotent Checkpoint Steps
**What goes wrong:** Re-running a "completed" step appends data instead of replacing; checkpoint-restart creates duplicates
**Why it happens:** Using `INSERT` instead of `CREATE OR REPLACE`; appending to files instead of overwriting
**How to avoid:** Make each step idempotent (same input → same output, regardless of retries); use `CREATE OR REPLACE TABLE`
**Warning signs:** Row counts increase each run, duplicate genes in database, checkpoint files exist but data is wrong

### Pitfall 4: Outdated gnomAD Thresholds
**What goes wrong:** Using v2.1.1 thresholds (LOEUF < 0.35) on v4.0+ data produces too-strict filtering
**Why it happens:** gnomAD v4.0 changed thresholds due to larger sample size; old docs still rank higher in search
**How to avoid:** Verify gnomAD version in downloaded file; use v4.0+ thresholds (LOEUF < 0.6); document version in provenance
**Warning signs:** Unexpectedly small result sets, filtering removes known constrained genes

### Pitfall 5: Downloading Entire gnomAD Dataset Instead of Constraint Table
**What goes wrong:** Attempting to download all gnomAD variants (750+ GB) instead of just constraint metrics (< 100 MB)
**Why it happens:** Unclear documentation on gnomAD downloads page; confusion between variant data vs. summary metrics
**How to avoid:** Download only constraint metrics TSV from downloads page; verify file size before processing
**Warning signs:** Multi-hour downloads, disk space warnings, processing times in hours instead of minutes

### Pitfall 6: Not Testing with Production-Scale Data
**What goes wrong:** Pipeline works with 100-gene test file but fails with full 19,000+ gene file
**Why it happens:** Test data fits in memory, masks lazy evaluation issues; no streaming needed for small files
**How to avoid:** Test with full-scale files early; use memory profilers; set resource limits in tests
**Warning signs:** "Works on my machine" but fails in CI/production; memory usage scales with file size

## Code Examples

Verified patterns from official sources:

### Polars Lazy CSV Reading with Streaming
```python
# Source: Polars documentation, verified for large file handling
import polars as pl

# Lazy scan (doesn't load data)
lazy_df = pl.scan_csv(
    "gnomad_v4.1_constraint_metrics.tsv",
    separator="\t",
    null_values=["NA", ".", ""]
)

# Build query plan (still no execution)
filtered = (
    lazy_df
    .filter(pl.col("mean_depth") >= 30)
    .filter(pl.col("cds_covered_pct") >= 0.9)
    .select([
        "gene_id",
        "gene_symbol",
        "loeuf",
        "pli",
        "mean_depth",
        "cds_covered_pct"
    ])
)

# Execute with streaming (processes in chunks)
result = filtered.collect(streaming=True)
```

### DuckDB Schema with Quality Flags
```python
# Source: DuckDB performance guide + genomic data best practices
import duckdb

con = duckdb.connect("evidence.duckdb")

# Create table with explicit NULL handling
con.execute("""
    CREATE TABLE IF NOT EXISTS gnomad_constraint (
        gene_id VARCHAR PRIMARY KEY,
        gene_symbol VARCHAR NOT NULL,
        loeuf DOUBLE,              -- NULL if no estimate
        pli DOUBLE,                -- NULL if no estimate
        mean_depth DOUBLE,         -- NULL if no coverage
        cds_covered_pct DOUBLE,    -- NULL if no coverage
        quality_flag VARCHAR NOT NULL,  -- 'measured' or 'incomplete_coverage'
        loeuf_normalized DOUBLE,   -- NULL if loeuf is NULL
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
```

### Click CLI with Checkpoint Restart
```python
# Source: Click documentation + checkpoint pattern from research
import click
from pathlib import Path

@click.group()
def cli():
    """gnomAD constraint evidence layer pipeline."""
    pass

@cli.command()
@click.option("--force", is_flag=True, help="Ignore existing checkpoints and rerun all steps")
@click.option("--version", default="v4.1", help="gnomAD version to download")
def setup(force: bool, version: str):
    """Download and process gnomAD constraint metrics."""
    from pipeline.fetch import download_gnomad
    from pipeline.transform import filter_and_normalize
    from pipeline.load import load_to_duckdb

    checkpoint_dir = Path(".data/checkpoints")

    click.echo(f"Setting up gnomAD {version} constraint evidence layer...")

    # Step 1: Download
    if force or not (checkpoint_dir / "download.done").exists():
        click.echo("Downloading gnomAD constraint metrics...")
        download_gnomad(version)
        (checkpoint_dir / "download.done").touch()
    else:
        click.echo("Download already complete (use --force to rerun)")

    # Step 2: Filter and normalize
    if force or not (checkpoint_dir / "transform.done").exists():
        click.echo("Filtering by coverage and normalizing scores...")
        filter_and_normalize()
        (checkpoint_dir / "transform.done").touch()
    else:
        click.echo("Transform already complete (use --force to rerun)")

    # Step 3: Load to DuckDB
    if force or not (checkpoint_dir / "load.done").exists():
        click.echo("Loading to DuckDB...")
        load_to_duckdb()
        (checkpoint_dir / "load.done").touch()
    else:
        click.echo("Load already complete (use --force to rerun)")

    click.echo("Setup complete!")

if __name__ == "__main__":
    cli()
```

### Normalization Preserving NULLs
```python
# Source: Verified from genomic data quality + Polars null handling
import polars as pl

def normalize_loeuf_scores(df: pl.DataFrame) -> pl.DataFrame:
    """
    Normalize LOEUF scores to 0-1 range, preserving NULLs.

    Lower LOEUF = more constrained → normalize so 1.0 = most constrained
    """
    # Only compute stats on non-null values
    loeuf_max = df.select(pl.col("loeuf").max()).item()
    loeuf_min = df.select(pl.col("loeuf").min()).item()

    # Normalize: invert so high score = constrained
    # If loeuf is NULL, normalized score stays NULL
    return df.with_columns([
        pl.when(pl.col("loeuf").is_not_null())
          .then((loeuf_max - pl.col("loeuf")) / (loeuf_max - loeuf_min))
          .otherwise(None)
          .alias("loeuf_normalized")
    ])
```

### Structured Logging Setup
```python
# Source: structlog best practices documentation
import structlog
import logging

def setup_logging(log_level: str = "INFO"):
    """Configure structured logging for the pipeline."""
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

# Usage in pipeline
log = structlog.get_logger()
log.info("downloading_gnomad", version="v4.1", url="https://...")
log.warning("low_coverage_gene", gene="BRCA1", mean_depth=25.3, threshold=30)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pandas for all DataFrame work | Polars for ETL, pandas for ML/viz | 2023-2024 | 5-10x faster processing, streaming for large files, lazy evaluation |
| requests library for HTTP | httpx for new projects | 2024+ | Native async, HTTP/2, better timeout handling, active maintenance |
| gnomAD v2.1.1 constraint thresholds | v4.0+ thresholds (LOEUF < 0.6) | March 2024 | 6x more samples, different threshold recommendations, GRCh38 support |
| All coding bases in constraint calc | High coverage bases only (≥30x) | v4.0 (2024) | More reliable estimates, excludes low-quality regions |
| String-based file paths (os.path) | pathlib.Path objects | Python 3.4+, standard by 2023 | Cross-platform compatibility, OOP, more readable |
| argparse for CLIs | Click for complex CLIs | 2020s | Composable commands, auto-validation, less boilerplate |
| Manual JSON logging | structlog for structured logs | 2020s | Better log aggregation, context binding, production-proven |

**Deprecated/outdated:**
- **gnomAD v2.1.1 thresholds (LOEUF < 0.35):** v4.0 uses < 0.6 due to larger sample size
- **requests library for new projects:** httpx is the modern replacement with async/HTTP/2 support
- **pLI as primary metric:** gnomAD now recommends LOEUF (continuous) over pLI (binary) for nuanced constraint assessment
- **os.path module:** pathlib is now standard for file path operations in modern Python

## Open Questions

1. **Exact gnomAD download URL for v4.1 constraint metrics**
   - What we know: Files exist at gnomad.broadinstitute.org/downloads in TSV.bgz format
   - What's unclear: Direct download URL for constraint-only file (not full variant data)
   - Recommendation: Visit gnomad.broadinstitute.org/downloads during implementation, verify file size (should be < 100 MB), document URL in provenance

2. **Coverage quality threshold rationale (30x depth, 90% CDS)**
   - What we know: gnomAD v4.0 uses median depth ≥30x; requirement specifies 90% CDS covered
   - What's unclear: Official gnomAD recommendation for "90% CDS" threshold; most docs reference depth only
   - Recommendation: Document as conservative filter; verify with gnomAD community forum if critical

3. **Gene ID format in gnomAD files**
   - What we know: gnomAD uses GENCODE gene annotations; likely Ensembl IDs or gene symbols
   - What's unclear: Exact ID format (ENSG00000..., gene symbols, or both); which GENCODE version for v4.1
   - Recommendation: Inspect downloaded file header; plan for both ID types; store both if available

4. **Normalization approach for constraint scores**
   - What we know: LOEUF ranges ~0-2+, pLI is 0-1; lower LOEUF = more constrained
   - What's unclear: Best normalization for combining LOEUF with other evidence layers later
   - Recommendation: Min-max normalization with inversion (so high score = constrained); document in code

5. **Testing with real gnomAD files**
   - What we know: Full file has 19,000+ genes; should use streaming
   - What's unclear: CI environment disk space limits, download time impact on tests
   - Recommendation: Use small sample file (100 genes) for unit tests; separate integration test with full download

## Sources

### Primary (HIGH confidence)
- [DuckDB Polars Integration](https://duckdb.org/docs/stable/guides/python/polars) - Official integration guide
- [Polars PyPI](https://pypi.org/project/polars/) - Version 1.38.1, release date, requirements
- [DuckDB PyPI](https://pypi.org/project/duckdb/) - Version 1.4.4, requirements
- [Click PyPI](https://pypi.org/project/click/) - Version 8.3.1, features
- [httpx PyPI](https://pypi.org/project/httpx/) - Version 0.28.1, HTTP/2 support
- [Pydantic PyPI](https://pypi.org/project/pydantic/) - Version 2.12.5, v2 vs v1 notes
- [pytest PyPI](https://pypi.org/project/pytest/) - Version 9.0.2, features
- [tenacity PyPI](https://pypi.org/project/tenacity/) - Version 9.1.4, retry patterns
- [structlog PyPI](https://pypi.org/project/structlog/) - Version 25.5.0, features
- [gnomAD v4.0 Gene Constraint](https://gnomad.broadinstitute.org/news/2024-03-gnomad-v4-0-gene-constraint/) - Threshold updates, coverage requirements

### Secondary (MEDIUM confidence)
- [DuckDB vs Pandas vs Polars | MotherDuck](https://motherduck.com/blog/duckdb-versus-pandas-versus-polars/) - When to use each tool
- [DuckDB Schema Performance](https://duckdb.org/docs/stable/guides/performance/schema) - Primary key guidance, column ordering
- [Sidematter Format](https://github.com/jlevy/sidematter-format) - Sidecar file naming conventions
- [Pathlib vs os.path Best Practices 2026](https://blog.mikihands.com/en/whitedec/2026/1/29/file-system-os-environment-master-pathlib-vs-os/) - Modern Python file handling
- [Python Logging Best Practices 2026](https://www.carmatec.com/blog/python-logging-best-practices-complete-guide/) - Structured logging patterns
- [API Error Handling & Retry Strategies: Python Guide 2026](https://easyparser.com/blog/api-error-handling-retry-strategies-python-guide) - Retry patterns, circuit breakers
- [Checkpointing in Python](https://www.linkedin.com/pulse/checkpointing-python-ritu-arora) - Checkpoint-restart concepts
- [Pydantic Best Practices](https://docs.pydantic.dev/latest/) - Data validation patterns

### Tertiary (LOW confidence - needs validation)
- gnomAD Python packages on PyPI (gnomad, gnomad-toolbox, gnomad-db) - Not officially maintained by Broad; verify before use
- Exact gnomAD v4.1 constraint file download URL - Not documented in search results; must verify at downloads page
- 90% CDS coverage threshold - Specified in requirements but not verified in official gnomAD docs
- bioframe/pybedtools - Mentioned for genomic intervals but may not be needed for constraint table (no intervals)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official PyPI pages with version numbers and release dates
- Architecture: MEDIUM-HIGH - Polars/DuckDB integration verified from official docs; checkpoint pattern verified from multiple sources but not gnomAD-specific
- Pitfalls: MEDIUM - Missing data handling verified from genomic data research; threshold updates verified from gnomAD v4.0 announcement; other pitfalls inferred from general pipeline patterns

**Research date:** 2026-02-11
**Valid until:** 2026-03-15 (30 days) - Stack is stable; gnomAD releases are infrequent; re-verify if gnomAD v4.2+ released or major library updates

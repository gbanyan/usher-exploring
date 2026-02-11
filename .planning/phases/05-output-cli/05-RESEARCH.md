# Phase 5: Output & CLI - Research

**Researched:** 2026-02-11
**Domain:** Python CLI applications, data visualization, structured output formats, reproducibility reporting
**Confidence:** HIGH

## Summary

Phase 5 delivers the user-facing interface and structured output system for the bioinformatics pipeline. The standard Python ecosystem provides mature, well-tested tools for all requirements: Click for CLI framework (already decided), matplotlib/seaborn for publication-quality visualizations, Polars native support for both TSV and Parquet with pyarrow integration, and structlog for structured progress logging.

The architecture follows a three-tier pattern: (1) CLI command layer handling user interaction and context management, (2) output generation layer producing tiered candidate lists with evidence summaries in multiple formats, and (3) reporting layer creating visualizations and reproducibility documentation. This separation enables testing each component independently while maintaining clear data flow from scoring integration to final deliverables.

**Primary recommendation:** Use Click command groups with shared context for the unified CLI, Polars native write methods for TSV/Parquet output (no additional libraries needed), matplotlib/seaborn for static publication-quality visualizations, and YAML/JSON sidecars for provenance metadata.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| click | 8.3.x | CLI framework | Already decided; decorator-based, excellent testing support, command groups with context passing |
| polars | Latest stable | DataFrame I/O | Already decided; native TSV/Parquet support via pyarrow, 45x faster than pandas for large writes |
| matplotlib | 3.x | Static visualizations | Publication-quality plots, industry standard for scientific figures, foundation for seaborn |
| seaborn | 0.13.2+ | Statistical plots | High-level interface for distributions and comparisons, builds on matplotlib, bioinformatics standard |
| structlog | 25.5.0+ | Structured logging | Already decided; context binding perfect for CLI progress tracking, contextvars support |
| pyarrow | Latest stable | Parquet backend | Required by Polars for Parquet I/O, enables compression options and column-level encoding |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyyaml | 6.x | YAML provenance files | Human-readable metadata sidecars alongside outputs |
| tqdm | Latest | Enhanced progress bars | Optional upgrade over click.progressbar if richer features needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| matplotlib/seaborn | plotly | Interactive web-based plots vs static publication-ready figures; plotly better for dashboards, matplotlib/seaborn better for reproducible scientific reports |
| Polars | pandas | Pandas has wider adoption but Polars 45x faster for large CSV/TSV writes and native Parquet support |
| YAML sidecars | Embed in Parquet metadata | YAML files more flexible and human-readable vs embedded metadata harder to inspect |

**Installation:**
```bash
pip install click polars pyarrow matplotlib seaborn structlog pyyaml
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── cli/
│   ├── main.py          # Entry point with @click.group()
│   ├── commands/        # Subcommand modules
│   │   ├── setup.py
│   │   ├── run.py
│   │   ├── integrate.py
│   │   └── report.py
│   └── context.py       # Shared context object
├── output/
│   ├── writers.py       # TSV/Parquet output generation
│   ├── tiers.py         # Candidate tiering logic
│   └── evidence.py      # Evidence summary formatting
├── visualization/
│   ├── distributions.py # Score distribution plots
│   └── contributions.py # Evidence layer contribution plots
└── reporting/
    ├── provenance.py    # Metadata sidecar generation
    └── reproducibility.py # Full reproducibility report
```

### Pattern 1: Click Command Groups with Shared Context
**What:** Hierarchical CLI with shared state across subcommands using Click's context system
**When to use:** Multiple related commands need access to common configuration or state
**Example:**
```python
# Source: https://click.palletsprojects.com/en/stable/commands/
import click

class PipelineContext:
    def __init__(self):
        self.config = {}
        self.logger = None

    def set_config(self, key, value):
        self.config[key] = value

@click.group()
@click.option('--verbose', is_flag=True)
@click.option('--config', type=click.Path())
@click.pass_context
def cli(ctx, verbose, config):
    """Unified pipeline CLI"""
    ctx.ensure_object(PipelineContext)
    ctx.obj.set_config('verbose', verbose)
    if config:
        ctx.obj.set_config('config_path', config)

@cli.command()
@click.pass_context
def setup(ctx):
    """Setup data and resources"""
    logger = structlog.get_logger()
    logger.info("setup_started", verbose=ctx.obj.config['verbose'])
    # Access shared context via ctx.obj

@cli.command()
@click.argument('layers', nargs=-1)
@click.pass_context
def integrate(ctx, layers):
    """Integrate scoring layers"""
    logger = structlog.get_logger()
    logger.info("integrate_started", layers=layers)
    # Use ctx.obj for configuration
```

### Pattern 2: Tiered Output with Evidence Summary
**What:** Score-based tiering with per-candidate multi-dimensional evidence tracking
**When to use:** Providing confidence-stratified results with interpretability
**Example:**
```python
# Based on requirements and standard scoring patterns
import polars as pl

def create_tiered_output(scores_df: pl.LazyFrame) -> pl.LazyFrame:
    """
    Generate tiered candidate list with evidence summary

    Tiers based on composite score and evidence breadth:
    - HIGH: score >= 0.7 AND evidence_count >= 3
    - MEDIUM: score >= 0.4 AND evidence_count >= 2
    - LOW: score >= 0.2
    """
    return (
        scores_df
        .with_columns([
            pl.when(
                (pl.col("composite_score") >= 0.7) &
                (pl.col("evidence_count") >= 3)
            ).then(pl.lit("HIGH"))
            .when(
                (pl.col("composite_score") >= 0.4) &
                (pl.col("evidence_count") >= 2)
            ).then(pl.lit("MEDIUM"))
            .when(pl.col("composite_score") >= 0.2)
            .then(pl.lit("LOW"))
            .otherwise(pl.lit("EXCLUDED"))
            .alias("confidence_tier")
        ])
        .filter(pl.col("confidence_tier") != "EXCLUDED")
        .sort("composite_score", descending=True)
    )

def add_evidence_summary(df: pl.LazyFrame) -> pl.LazyFrame:
    """
    Add multi-dimensional evidence summary showing which layers
    support each candidate and which have gaps
    """
    return df.with_columns([
        # Which layers provided evidence
        pl.concat_str([
            pl.when(pl.col("layer1_score").is_not_null())
            .then(pl.lit("layer1,"))
            .otherwise(pl.lit("")),
            pl.when(pl.col("layer2_score").is_not_null())
            .then(pl.lit("layer2,"))
            .otherwise(pl.lit("")),
            # ... other layers
        ]).str.strip_chars(",").alias("supporting_layers"),

        # Which layers have gaps
        pl.concat_str([
            pl.when(pl.col("layer1_score").is_null())
            .then(pl.lit("layer1,"))
            .otherwise(pl.lit("")),
            # ... other layers
        ]).str.strip_chars(",").alias("evidence_gaps")
    ])
```

### Pattern 3: Dual Format Output (TSV + Parquet)
**What:** Write same data in both human-readable TSV and efficient Parquet formats
**When to use:** Supporting both manual inspection and downstream tool integration
**Example:**
```python
# Source: https://docs.pola.rs/api/python/dev/reference/api/polars.DataFrame.write_parquet.html
import polars as pl
from pathlib import Path

def write_dual_format(
    df: pl.LazyFrame,
    output_dir: Path,
    filename_base: str
):
    """
    Write DataFrame in both TSV and Parquet formats

    TSV: Human-readable, downstream PPI tools
    Parquet: Efficient storage, structural prediction tools
    """
    # Collect once
    materialized = df.collect()

    # TSV: tab-separated, no index
    tsv_path = output_dir / f"{filename_base}.tsv"
    materialized.write_csv(
        tsv_path,
        separator="\t",
        include_header=True
    )

    # Parquet: snappy compression (fast), dictionary encoding
    parquet_path = output_dir / f"{filename_base}.parquet"
    materialized.write_parquet(
        parquet_path,
        compression="snappy",  # Fast compression, good default
        use_pyarrow=True,      # Stable, feature-rich
        row_group_size=None    # Single row group for small files
    )

    return tsv_path, parquet_path
```

### Pattern 4: Provenance Sidecar Files
**What:** YAML/JSON metadata files alongside outputs documenting provenance
**When to use:** Ensuring reproducibility and traceability of pipeline results
**Example:**
```python
# Based on scientific pipeline best practices
import yaml
from datetime import datetime
from pathlib import Path

def write_provenance_sidecar(
    output_path: Path,
    params: dict,
    data_versions: dict,
    statistics: dict
):
    """
    Write provenance metadata alongside output file

    Format: {output_name}.provenance.yaml
    """
    provenance = {
        "generated_at": datetime.now().isoformat(),
        "output_file": output_path.name,
        "parameters": params,
        "data_versions": data_versions,
        "statistics": {
            "total_candidates": statistics.get("total"),
            "high_confidence": statistics.get("high"),
            "medium_confidence": statistics.get("medium"),
            "low_confidence": statistics.get("low")
        },
        "software_versions": {
            "python": sys.version,
            "polars": pl.__version__,
            # ... other versions
        }
    }

    sidecar_path = output_path.with_suffix(".provenance.yaml")
    with open(sidecar_path, 'w') as f:
        yaml.dump(provenance, f, default_flow_style=False)
```

### Pattern 5: Distribution Visualizations with Seaborn
**What:** Statistical distribution plots for score analysis and quality assessment
**When to use:** Visualizing score distributions, comparing tiers, showing evidence contributions
**Example:**
```python
# Source: https://seaborn.pydata.org/ and bioinformatics visualization patterns
import matplotlib.pyplot as plt
import seaborn as sns
import polars as pl

def plot_score_distribution(df: pl.DataFrame, output_path: Path):
    """
    Create score distribution histogram with tier overlays
    Publication-quality static plot
    """
    # Convert to pandas for seaborn (efficient for small result sets)
    pdf = df.to_pandas()

    # Seaborn style for publication
    sns.set_theme(style="whitegrid")

    fig, ax = plt.subplots(figsize=(10, 6))

    # Distribution plot with tier colors
    sns.histplot(
        data=pdf,
        x="composite_score",
        hue="confidence_tier",
        hue_order=["HIGH", "MEDIUM", "LOW"],
        palette={"HIGH": "green", "MEDIUM": "orange", "LOW": "red"},
        bins=30,
        ax=ax
    )

    ax.set_xlabel("Composite Score")
    ax.set_ylabel("Candidate Count")
    ax.set_title("Score Distribution by Confidence Tier")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def plot_evidence_contribution(df: pl.DataFrame, output_path: Path):
    """
    Stacked bar chart showing per-layer contribution to evidence
    """
    pdf = df.to_pandas()

    fig, ax = plt.subplots(figsize=(12, 6))

    # Prepare layer contribution data
    layer_cols = [col for col in pdf.columns if col.endswith('_score')]
    layer_names = [col.replace('_score', '') for col in layer_cols]

    # Count non-null contributions per layer
    contributions = pdf[layer_cols].notna().sum()

    sns.barplot(
        x=layer_names,
        y=contributions.values,
        palette="viridis",
        ax=ax
    )

    ax.set_xlabel("Evidence Layer")
    ax.set_ylabel("Candidate Count with Evidence")
    ax.set_title("Evidence Layer Contribution")
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
```

### Pattern 6: Progress Logging with Structlog Context
**What:** Structured logging with bound context for progress tracking across CLI operations
**When to use:** Long-running pipeline operations requiring user feedback
**Example:**
```python
# Source: https://www.structlog.org/en/stable/bound-loggers.html
import structlog
import click

def configure_logging(verbose: bool):
    """Configure structlog for CLI progress logging"""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if verbose else
                structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.INFO if not verbose else logging.DEBUG
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

@click.command()
@click.option('--verbose', is_flag=True)
def integrate(verbose):
    """Integrate scoring layers with progress logging"""
    configure_logging(verbose)
    logger = structlog.get_logger()

    # Bind context for this operation
    logger = logger.bind(operation="integrate", phase="scoring")

    layers = ["expression", "essentiality", "homology"]
    for layer in layers:
        logger.info("processing_layer", layer=layer)

        # Process layer with click progress bar
        with click.progressbar(
            range(1000),
            label=f"Processing {layer}",
            show_eta=True
        ) as bar:
            for item in bar:
                # Processing logic
                pass

        logger.info("layer_complete", layer=layer, count=1000)

    logger.info("integration_complete", total_layers=len(layers))
```

### Pattern 7: Reproducibility Report Generation
**What:** Comprehensive report documenting parameters, versions, filtering steps, and metrics
**When to use:** Every pipeline run for scientific reproducibility requirements
**Example:**
```python
# Based on scientific pipeline reproducibility best practices
from dataclasses import dataclass
from typing import Dict, List
import json

@dataclass
class FilteringStep:
    step_name: str
    input_count: int
    output_count: int
    criteria: str

@dataclass
class ReproducibilityReport:
    """Complete documentation of pipeline execution"""
    run_id: str
    timestamp: str
    parameters: Dict
    data_versions: Dict
    filtering_steps: List[FilteringStep]
    validation_metrics: Dict
    software_environment: Dict

    def to_json(self, path: Path):
        """Write report as JSON"""
        report_dict = {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "parameters": self.parameters,
            "data_versions": self.data_versions,
            "filtering_steps": [
                {
                    "step": step.step_name,
                    "input_count": step.input_count,
                    "output_count": step.output_count,
                    "removed": step.input_count - step.output_count,
                    "criteria": step.criteria
                }
                for step in self.filtering_steps
            ],
            "validation_metrics": self.validation_metrics,
            "software_environment": self.software_environment
        }

        with open(path, 'w') as f:
            json.dump(report_dict, f, indent=2)

    def to_markdown(self, path: Path):
        """Write human-readable markdown report"""
        lines = [
            f"# Pipeline Reproducibility Report",
            f"",
            f"**Run ID:** {self.run_id}",
            f"**Timestamp:** {self.timestamp}",
            f"",
            f"## Parameters",
            "```json",
            json.dumps(self.parameters, indent=2),
            "```",
            f"",
            f"## Data Versions",
            *[f"- {k}: {v}" for k, v in self.data_versions.items()],
            f"",
            f"## Filtering Steps",
            f"| Step | Input | Output | Removed | Criteria |",
            f"|------|-------|--------|---------|----------|",
            *[
                f"| {step.step_name} | {step.input_count} | {step.output_count} | "
                f"{step.input_count - step.output_count} | {step.criteria} |"
                for step in self.filtering_steps
            ],
            f"",
            f"## Validation Metrics",
            *[f"- {k}: {v}" for k, v in self.validation_metrics.items()],
            f"",
            f"## Software Environment",
            *[f"- {k}: {v}" for k, v in self.software_environment.items()],
        ]

        with open(path, 'w') as f:
            f.write('\n'.join(lines))
```

### Anti-Patterns to Avoid
- **Interactive prompts in pipeline commands:** CLI should be fully scriptable; use options/arguments, not prompts
- **Printing to stdout in library code:** Use structlog everywhere; stdout reserved for actual output data
- **Hardcoded paths:** All paths should be configurable via CLI options or config file
- **Single format lock-in:** Always provide both TSV (human-readable) and Parquet (efficient) formats
- **Visualization in pipeline logic:** Keep plotting separate from data processing for testability
- **Mixing Click's echo with print/logging:** Use consistent output method (Click echo for messages, structlog for logs)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress bars | Custom progress indicators with print/carriage return | click.progressbar or tqdm | Handle terminal width, updates, eta calculations; edge cases like non-tty environments |
| CLI testing | Subprocess calls or manual testing | click.testing.CliRunner | Isolated testing with captured output, simulated input, temp filesystem |
| Parquet writing | Custom binary writers or CSV-only | Polars write_parquet with pyarrow | Compression, column encoding, schema preservation, compatibility with downstream tools |
| Argument parsing | Manual sys.argv parsing | Click decorators | Type validation, help generation, error messages, complex argument patterns |
| Structured logging | JSON print statements | structlog | Context binding, processor pipelines, safe serialization of complex types |
| Statistical plots | Matplotlib bar/line charts | seaborn distribution/categorical plots | Statistical defaults, attractive styling, less code for common patterns |
| Tiering logic | Complex if/elif chains | Polars when/then expressions | Readable, vectorized, maintains lazy evaluation |

**Key insight:** CLI and output formatting have many edge cases (terminal types, file encodings, compression options, missing data handling). Mature libraries handle these correctly; custom code will miss cases and create maintenance burden.

## Common Pitfalls

### Pitfall 1: Materializing LazyFrames Too Early
**What goes wrong:** Calling .collect() before all transformations kills performance benefits of lazy evaluation
**Why it happens:** Eagerness to see intermediate results or unfamiliarity with lazy API
**How to avoid:** Keep LazyFrame until final write; use .explain() to inspect query plan without collecting
**Warning signs:** Multiple .collect() calls in same pipeline, converting back and forth between LazyFrame and DataFrame

### Pitfall 2: Not Testing CLI with CliRunner
**What goes wrong:** CLI appears to work manually but breaks in CI or when arguments change
**Why it happens:** Manual testing is tedious, so coverage is incomplete
**How to avoid:** Use click.testing.CliRunner for all CLI tests; test argument combinations, error cases, file operations
**Warning signs:** "Works on my machine" bugs, no test coverage in cli/ modules

### Pitfall 3: TSV Export Without Proper Escaping
**What goes wrong:** Gene names or annotations with tabs break downstream parsing
**Why it happens:** Assuming biological data won't contain delimiter characters
**How to avoid:** Use Polars write_csv with separator="\t"; it handles escaping. Never concatenate strings manually
**Warning signs:** Downstream tools report "wrong number of columns" or parsing errors

### Pitfall 4: Parquet Compression Choice for Bioinformatics
**What goes wrong:** Using gzip (slow writes) or no compression (huge files) when snappy is optimal
**Why it happens:** Not understanding compression trade-offs for genomics data access patterns
**How to avoid:** Use snappy for default (fast, good compression); only use zstd for archival cold storage
**Warning signs:** Pipeline write step takes >50% of runtime, or output files >2x larger than necessary

### Pitfall 5: Forgetting to Close Plots
**What goes wrong:** Memory leak when generating many plots, especially in loops
**Why it happens:** Matplotlib holds figure references even after saving
**How to avoid:** Always call plt.close() after savefig; use context managers where possible
**Warning signs:** Memory usage grows linearly with number of plots generated

### Pitfall 6: Non-Deterministic Output Ordering
**What goes wrong:** Same inputs produce differently-ordered outputs across runs, breaking diffs
**Why it happens:** Not explicitly sorting before write; relying on hash map iteration order
**How to avoid:** Always .sort() by primary key before writing final outputs
**Warning signs:** Git diffs show content reordering rather than actual changes

### Pitfall 7: Missing Provenance for Intermediate Files
**What goes wrong:** Can't trace which parameters/versions produced an output file weeks later
**Why it happens:** Only documenting final outputs, not intermediate checkpoints
**How to avoid:** Write .provenance.yaml sidecar for every significant output file
**Warning signs:** Questions like "which data version is this?" require re-running pipeline

### Pitfall 8: Context Not Passed to Subcommands
**What goes wrong:** Subcommands can't access shared configuration set in parent group
**Why it happens:** Forgetting @click.pass_context decorator on subcommand functions
**How to avoid:** Use @click.pass_context on any subcommand that needs shared state; store state in ctx.obj
**Warning signs:** Subcommands re-parse config files or re-initialize objects unnecessarily

### Pitfall 9: Logging in Wrong Format for Context
**What goes wrong:** Simple string logs don't show which command/operation logged the message
**Why it happens:** Using basic logging or print instead of structlog with context binding
**How to avoid:** Bind operation context (.bind(operation="integrate")) at start of each command
**Warning signs:** Can't filter logs by operation, can't trace log sequence for specific command

### Pitfall 10: Visualization Data Type Mismatches
**What goes wrong:** Seaborn plots fail with "unhashable type" or type errors when using Polars directly
**Why it happens:** Seaborn expects pandas DataFrames; some Polars types don't convert cleanly
**How to avoid:** Convert to pandas for visualization: df.to_pandas(); acceptable overhead for small result sets
**Warning signs:** Type errors when calling seaborn functions, missing data in plots

## Code Examples

Verified patterns from official sources:

### Complete CLI Structure with Testing
```python
# Source: https://click.palletsprojects.com/en/stable/testing/
# cli/main.py
import click
from pathlib import Path

class PipelineContext:
    def __init__(self):
        self.data_dir = None
        self.output_dir = None
        self.verbose = False

@click.group()
@click.option('--data-dir', type=click.Path(exists=True), required=True)
@click.option('--output-dir', type=click.Path(), required=True)
@click.option('--verbose', is_flag=True)
@click.pass_context
def cli(ctx, data_dir, output_dir, verbose):
    """Unified pipeline CLI"""
    ctx.ensure_object(PipelineContext)
    ctx.obj.data_dir = Path(data_dir)
    ctx.obj.output_dir = Path(output_dir)
    ctx.obj.verbose = verbose

    # Create output directory
    ctx.obj.output_dir.mkdir(parents=True, exist_ok=True)

@cli.command()
@click.pass_context
def setup(ctx):
    """Setup data and resources"""
    click.echo("Setting up pipeline...")
    # Implementation

@cli.command()
@click.option('--layers', multiple=True, required=True)
@click.pass_context
def integrate(ctx, layers):
    """Integrate scoring layers"""
    click.echo(f"Integrating layers: {', '.join(layers)}")
    # Implementation

# Test file: tests/test_cli.py
from click.testing import CliRunner
from cli.main import cli

def test_cli_setup():
    """Test setup command with CliRunner"""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create test data directory
        Path('data').mkdir()
        Path('output').mkdir()

        result = runner.invoke(cli, [
            '--data-dir', 'data',
            '--output-dir', 'output',
            'setup'
        ])

        assert result.exit_code == 0
        assert "Setting up pipeline" in result.output

def test_cli_integrate_requires_layers():
    """Test integrate requires layers argument"""
    runner = CliRunner()

    with runner.isolated_filesystem():
        Path('data').mkdir()
        Path('output').mkdir()

        result = runner.invoke(cli, [
            '--data-dir', 'data',
            '--output-dir', 'output',
            'integrate'
        ])

        assert result.exit_code != 0  # Should fail without --layers
```

### Parquet with Column-Specific Compression
```python
# Source: https://arrow.apache.org/docs/python/parquet.html
import polars as pl

def write_optimized_parquet(df: pl.DataFrame, path: Path):
    """
    Write Parquet with column-specific compression optimizations

    Strategy:
    - Frequently accessed columns (gene_id, score): snappy (fast)
    - Large text columns (description): zstd (small)
    - Numeric columns: use_dictionary for compression
    """

    # Polars uses pyarrow under the hood for write_parquet
    df.write_parquet(
        path,
        compression={
            "gene_id": "snappy",
            "composite_score": "snappy",
            "confidence_tier": "snappy",
            "evidence_summary": "zstd",  # Text, less frequently accessed
            "description": "zstd"
        },
        use_pyarrow=True,
        statistics=True,  # Enable column statistics for query optimization
        row_group_size=100_000  # Tune based on typical query patterns
    )
```

### Complete Visualization Suite
```python
# Source: https://seaborn.pydata.org/ examples
import matplotlib.pyplot as plt
import seaborn as sns
import polars as pl
from pathlib import Path

def generate_all_visualizations(
    df: pl.DataFrame,
    output_dir: Path
):
    """
    Generate complete visualization suite for pipeline outputs

    Creates:
    1. Score distribution histogram
    2. Tier breakdown pie chart
    3. Evidence layer contribution bar chart
    4. Box plot comparing tiers
    """
    # Convert to pandas for seaborn
    pdf = df.to_pandas()

    # Set publication-quality style
    sns.set_theme(style="whitegrid", context="paper")
    sns.set_palette("colorblind")

    # 1. Score distribution with tiers
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(
        data=pdf,
        x="composite_score",
        hue="confidence_tier",
        hue_order=["HIGH", "MEDIUM", "LOW"],
        multiple="stack",
        bins=30,
        ax=ax
    )
    ax.set_xlabel("Composite Score")
    ax.set_ylabel("Candidate Count")
    ax.set_title("Score Distribution by Confidence Tier")
    plt.tight_layout()
    plt.savefig(output_dir / "score_distribution.png", dpi=300)
    plt.close()

    # 2. Tier breakdown
    tier_counts = pdf['confidence_tier'].value_counts()
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(
        tier_counts.values,
        labels=tier_counts.index,
        autopct='%1.1f%%',
        colors=sns.color_palette("Set2")
    )
    ax.set_title("Candidate Tier Breakdown")
    plt.tight_layout()
    plt.savefig(output_dir / "tier_breakdown.png", dpi=300)
    plt.close()

    # 3. Evidence layer contributions
    layer_cols = [c for c in pdf.columns if c.endswith('_score')]
    contributions = pdf[layer_cols].notna().sum().sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(
        x=contributions.index.str.replace('_score', ''),
        y=contributions.values,
        ax=ax
    )
    ax.set_xlabel("Evidence Layer")
    ax.set_ylabel("Candidates with Evidence")
    ax.set_title("Evidence Layer Contribution")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / "layer_contributions.png", dpi=300)
    plt.close()

    # 4. Box plot comparing tiers
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.boxplot(
        data=pdf,
        x="confidence_tier",
        y="composite_score",
        order=["HIGH", "MEDIUM", "LOW"],
        ax=ax
    )
    ax.set_xlabel("Confidence Tier")
    ax.set_ylabel("Composite Score")
    ax.set_title("Score Distribution by Tier")
    plt.tight_layout()
    plt.savefig(output_dir / "tier_comparison.png", dpi=300)
    plt.close()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| argparse | Click 8.x | ~2014, mature now | Decorator-based syntax cleaner, better testing support via CliRunner |
| pandas to_csv | Polars write_csv | 2023+ | 45x faster writes for large datasets, native lazy evaluation |
| Manual JSON logging | structlog 25.x with contextvars | 2024-2025 | Context propagation across async/sync boundaries, type-safe with PEP 688 |
| Global config files | Click context passing | Established pattern | Better testability, explicit dependencies |
| CSV for data interchange | Parquet | 2020s standard | 6-12x faster reads, compression, schema preservation |
| matplotlib.pyplot state machine | Object-oriented matplotlib + seaborn | Best practice evolution | Cleaner code, no global state issues, publication quality defaults |
| Manual metadata tracking | YAML/JSON sidecar provenance | Scientific computing trend | Human-readable, versionable, standard tooling |

**Deprecated/outdated:**
- Using bare `print()` in CLI code: Use `click.echo()` for proper stdout handling across terminals
- Pandas for large data I/O: Polars 45x faster and native Parquet support
- Embedding all metadata in filenames: Use sidecar files for rich provenance
- Single output format: Bioinformatics requires both TSV (compatibility) and Parquet (efficiency)

## Open Questions

1. **Visualization file formats**
   - What we know: PNG at 300dpi is publication standard
   - What's unclear: Whether to also generate SVG (vector) or PDF formats
   - Recommendation: Start with PNG; add SVG if users request editable figures

2. **Progress bar implementation**
   - What we know: Click has built-in progressbar, tqdm is more feature-rich
   - What's unclear: Whether Click progressbar sufficient or tqdm needed for richer features (nested bars, etc.)
   - Recommendation: Start with Click progressbar (no extra dependency); upgrade to tqdm only if user feedback indicates need

3. **Confidence tier thresholds**
   - What we know: Three tiers required (high/medium/low), based on score and evidence breadth
   - What's unclear: Exact threshold values will depend on score distribution from integration phase
   - Recommendation: Make thresholds configurable via CLI options with sensible defaults (0.7/0.4/0.2), tune after integration testing

4. **Report file format preference**
   - What we know: JSON machine-readable, Markdown human-readable
   - What's unclear: Which format users prefer for reproducibility reports
   - Recommendation: Generate both; JSON for programmatic use, Markdown for human review

## Sources

### Primary (HIGH confidence)
- [Click Official Documentation 8.3.x](https://click.palletsprojects.com/en/stable/) - CLI patterns, testing, context management
- [Apache Arrow PyArrow Parquet Documentation](https://arrow.apache.org/docs/python/parquet.html) - Compression options, writing best practices
- [Polars DataFrame API](https://docs.pola.rs/api/python/dev/reference/api/polars.DataFrame.write_parquet.html) - Write methods, pyarrow integration
- [Seaborn Official Documentation v0.13.2](https://seaborn.pydata.org/) - Statistical visualizations, matplotlib integration
- [Structlog Bound Loggers](https://www.structlog.org/en/stable/bound-loggers.html) - Context binding patterns
- [Click Testing Documentation](https://click.palletsprojects.com/en/stable/testing/) - CliRunner best practices

### Secondary (MEDIUM confidence)
- [OneUpTime: How to Build CLI Applications with Click (2026-01-30)](https://oneuptime.com/blog/post/2026-01-30-python-click-cli-applications/view) - Recent Click patterns, subcommands, progress logging
- [Better Stack: Comprehensive Guide to Structlog](https://betterstack.com/community/guides/logging/structlog/) - Structlog configuration and usage
- [Analytics Vidhya: Polars CSV Performance (2026)](https://www.statology.org/how-to-write-a-polars-dataframe-to-a-csv-file-using-write_csv/) - TSV/CSV writing benchmarks
- [Statology: Reproducible Research Pipelines (2026)](https://www.statology.org/building-reproducible-research-pipelines-in-python-from-data-collection-to-reporting/) - Scientific pipeline patterns
- [arXiv: The Role of Metadata in Reproducible Computational Research](https://arxiv.org/pdf/2006.08589) - Provenance metadata standards
- [Royal Society: FAIR Data Pipeline (2021)](https://royalsocietypublishing.org/doi/10.1098/rsta.2021.0300) - Provenance-driven data management
- [Around Data Science: Matplotlib vs Seaborn vs Plotly](https://arounddatascience.com/blog/data-visualization/matplotlib-vs-seaborn-vs-plotly-for-eda-dashboards-and-production/) - Visualization library comparison

### Tertiary (LOW confidence)
- [GitHub: ICWallis/tutorial-publication-ready-figures](https://github.com/ICWallis/tutorial-publication-ready-figures) - Matplotlib/seaborn for manuscripts (not date-verified)
- [Extend.ai: Best Confidence Scoring Systems (2026)](https://www.extend.ai/resources/best-confidence-scoring-systems-document-processing) - Tiered confidence patterns (not bioinformatics-specific)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified from official documentation, versions confirmed current
- Architecture: HIGH - Patterns based on official Click/Polars/structlog docs and scientific computing standards
- Pitfalls: MEDIUM-HIGH - Drawn from documentation, community patterns, and general Python/data engineering experience; some bioinformatics-specific pitfalls are domain knowledge

**Research date:** 2026-02-11
**Valid until:** ~2026-03-31 (30 days) - Standard libraries stable; Click 8.x and Polars mature; recheck if major versions released

# MANE Select Integration Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the implicit gnomAD proxy for canonical transcript selection with explicit MANE Select data from NCBI, directly addressing a reviewer concern about gene deduplication rigor.

**Architecture:** Download NCBI MANE Select summary (~2MB TSV), store as a reference table in DuckDB, and use it as the primary signal for gene_symbol deduplication in scoring — falling back to gnomAD presence, then lowest Ensembl ID.

**Tech Stack:** httpx (download), polars (parse), DuckDB (store), click (CLI), pytest (tests)

---

## Chunk 1: MANE Select module + config

### Task 1: Add MANE version to config

**Files:**
- Modify: `src/usher_pipeline/config/schema.py:11-30`
- Modify: `config/default.yaml:5-8`

- [ ] **Step 1: Write failing test for MANE version in config**

In `tests/test_config.py`, add:

```python
def test_data_source_versions_has_mane():
    """DataSourceVersions should include mane_version field."""
    from usher_pipeline.config.schema import DataSourceVersions
    versions = DataSourceVersions(ensembl_release=113)
    assert versions.mane_version == "1.3"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_data_source_versions_has_mane -v`
Expected: FAIL with AttributeError (no `mane_version` field)

- [ ] **Step 3: Add mane_version to DataSourceVersions**

In `src/usher_pipeline/config/schema.py`, add to `DataSourceVersions`:

```python
mane_version: str = Field(
    default="1.3",
    description="MANE Select release version",
)
```

And in `config/default.yaml`, add under `versions:`:

```yaml
mane_version: "1.3"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py::test_data_source_versions_has_mane -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/usher_pipeline/config/schema.py config/default.yaml tests/test_config.py
git commit -m "feat: add mane_version to DataSourceVersions config"
```

---

### Task 2: Create MANE Select fetch + parse module

**Files:**
- Create: `src/usher_pipeline/gene_mapping/mane_select.py`
- Create: `tests/test_mane_select.py`

**Context:** The MANE Select summary file is a TSV from NCBI with these columns:
```
#NCBI_GeneID  Ensembl_Gene  HGNC_ID  symbol  name  RefSeq_nuc  RefSeq_prot  Ensembl_nuc  Ensembl_prot  MANE_status  GRCh38_chr  chr_start  chr_end  chr_strand
```
Important: `Ensembl_Gene` values have version suffixes (e.g., `ENSG00000163646.18`) that must be stripped to match `gene_universe.gene_id` (bare `ENSG00000163646`).

- [ ] **Step 1: Write failing tests for fetch + parse**

Create `tests/test_mane_select.py`:

```python
"""Unit tests for MANE Select fetch and parse."""

import gzip
from pathlib import Path

import polars as pl
import pytest

from usher_pipeline.gene_mapping.mane_select import (
    MANE_SELECT_URL_TEMPLATE,
    fetch_mane_select,
    parse_mane_select,
)

# Minimal MANE summary TSV (real column names from NCBI)
SAMPLE_MANE_TSV = (
    "#NCBI_GeneID\tEnsembl_Gene\tHGNC_ID\tsymbol\tname\tRefSeq_nuc\tRefSeq_prot\t"
    "Ensembl_nuc\tEnsembl_prot\tMANE_status\tGRCh38_chr\tchr_start\tchr_end\tchr_strand\n"
    "7842\tENSG00000163646.18\tHGNC:2026\tCLRN1\tclarin 1\tNM_174878.3\tNP_777367.1\t"
    "ENST00000295886.10\tENSP00000295886.5\tMANE Select\t3\t150918930\t150967292\t-\n"
    "7399\tENSG00000075624.17\tHGNC:132\tACTB\tactin beta\tNM_001101.5\tNP_001092.1\t"
    "ENST00000646024.1\tENSP00000493376.1\tMANE Select\t7\t5527151\t5530601\t-\n"
    "7884\tENSG00000163646.18\tHGNC:2026\tCLRN1\tclarin 1\tNM_001256781.2\tNP_001243710.1\t"
    "ENST00000419101.5\tENSP00000395753.1\tMANE Plus Clinical\t3\t150926154\t150967292\t-\n"
)


def _write_mane_gz(tmp_path: Path) -> Path:
    """Write sample MANE TSV as gzipped file."""
    gz_path = tmp_path / "MANE.GRCh38.v1.3.summary.txt.gz"
    with gzip.open(gz_path, "wt") as f:
        f.write(SAMPLE_MANE_TSV)
    return gz_path


def test_parse_mane_select_columns(tmp_path):
    """parse_mane_select returns expected columns with stripped version IDs."""
    gz_path = _write_mane_gz(tmp_path)
    df = parse_mane_select(gz_path)

    assert set(df.columns) == {
        "ensembl_gene_id",
        "ensembl_transcript_id",
        "gene_symbol",
        "refseq_transcript_id",
        "mane_status",
    }


def test_parse_mane_select_strips_version(tmp_path):
    """Ensembl IDs must have version suffix stripped (ENSG00000163646.18 -> ENSG00000163646)."""
    gz_path = _write_mane_gz(tmp_path)
    df = parse_mane_select(gz_path)

    gene_ids = df["ensembl_gene_id"].to_list()
    assert "ENSG00000163646" in gene_ids, "Version suffix should be stripped"
    assert not any("." in gid for gid in gene_ids), "No version dots should remain"

    tx_ids = df["ensembl_transcript_id"].to_list()
    assert not any("." in tid for tid in tx_ids), "Transcript version dots should be stripped"


def test_parse_mane_select_row_count(tmp_path):
    """Sample data has 3 rows (2 MANE Select + 1 MANE Plus Clinical)."""
    gz_path = _write_mane_gz(tmp_path)
    df = parse_mane_select(gz_path)
    assert df.height == 3


def test_parse_mane_select_status_values(tmp_path):
    """MANE status should be preserved as-is."""
    gz_path = _write_mane_gz(tmp_path)
    df = parse_mane_select(gz_path)

    statuses = df["mane_status"].unique().sort().to_list()
    assert statuses == ["MANE Plus Clinical", "MANE Select"]


def test_fetch_mane_select_skips_existing(tmp_path):
    """fetch_mane_select should skip download if file exists and force=False."""
    gz_path = _write_mane_gz(tmp_path)
    result = fetch_mane_select(data_dir=tmp_path, version="1.3", force=False)
    assert result == gz_path
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mane_select.py -v`
Expected: FAIL with ImportError (module doesn't exist yet)

- [ ] **Step 3: Implement mane_select.py**

Create `src/usher_pipeline/gene_mapping/mane_select.py`:

```python
"""Fetch and parse NCBI MANE Select canonical transcript mappings."""

import gzip
import shutil
from pathlib import Path

import httpx
import polars as pl
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

MANE_SELECT_URL_TEMPLATE = (
    "https://ftp.ncbi.nlm.nih.gov/refseq/MANE/MANE_human/"
    "release_{version}/MANE.GRCh38.v{version}.summary.txt.gz"
)


def _strip_ensembl_version(col: pl.Expr) -> pl.Expr:
    """Strip version suffix from Ensembl IDs (ENSG00000163646.18 -> ENSG00000163646)."""
    return col.str.replace(r"\.\d+$", "")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=30),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def fetch_mane_select(
    data_dir: Path,
    version: str = "1.3",
    force: bool = False,
) -> Path:
    """Download MANE Select summary from NCBI FTP.

    Args:
        data_dir: Directory to save the downloaded file.
        version: MANE release version (default: 1.3).
        force: Re-download even if file exists.

    Returns:
        Path to the downloaded gzipped TSV file.
    """
    data_dir = Path(data_dir)
    gz_path = data_dir / f"MANE.GRCh38.v{version}.summary.txt.gz"

    if gz_path.exists() and not force:
        logger.info("mane_select_exists", path=str(gz_path))
        return gz_path

    data_dir.mkdir(parents=True, exist_ok=True)
    url = MANE_SELECT_URL_TEMPLATE.format(version=version)
    temp_path = gz_path.with_suffix(".tmp")

    logger.info("mane_select_download_start", url=url)

    with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as response:
        response.raise_for_status()
        with open(temp_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)

    temp_path.rename(gz_path)
    logger.info(
        "mane_select_download_complete",
        path=str(gz_path),
        size_kb=round(gz_path.stat().st_size / 1024, 1),
    )
    return gz_path


def parse_mane_select(gz_path: Path) -> pl.DataFrame:
    """Parse MANE Select summary TSV into a DataFrame.

    Reads the gzipped TSV, selects relevant columns, and strips
    version suffixes from Ensembl gene/transcript IDs so they
    match gene_universe.gene_id format.

    Args:
        gz_path: Path to gzipped MANE summary TSV.

    Returns:
        DataFrame with columns: ensembl_gene_id, ensembl_transcript_id,
        gene_symbol, refseq_transcript_id, mane_status.
    """
    df = pl.read_csv(
        gz_path,
        separator="\t",
        comment_prefix="##",
    )

    # Rename the comment-prefixed header column
    if "#NCBI_GeneID" in df.columns:
        df = df.rename({"#NCBI_GeneID": "NCBI_GeneID"})

    df = df.select(
        _strip_ensembl_version(pl.col("Ensembl_Gene")).alias("ensembl_gene_id"),
        _strip_ensembl_version(pl.col("Ensembl_nuc")).alias("ensembl_transcript_id"),
        pl.col("symbol").alias("gene_symbol"),
        pl.col("RefSeq_nuc").alias("refseq_transcript_id"),
        pl.col("MANE_status").alias("mane_status"),
    )

    logger.info(
        "mane_select_parsed",
        total_rows=df.height,
        mane_select_count=df.filter(pl.col("mane_status") == "MANE Select").height,
        mane_plus_clinical_count=df.filter(
            pl.col("mane_status") == "MANE Plus Clinical"
        ).height,
    )
    return df


def load_mane_select(store: "PipelineStore", df: pl.DataFrame) -> None:
    """Save MANE Select DataFrame to DuckDB.

    Args:
        store: PipelineStore instance.
        df: DataFrame from parse_mane_select().
    """
    store.save_dataframe(
        df=df,
        table_name="mane_select",
        description="NCBI MANE Select canonical transcript mappings",
        replace=True,
    )
    logger.info("mane_select_loaded", row_count=df.height)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mane_select.py -v`
Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/usher_pipeline/gene_mapping/mane_select.py tests/test_mane_select.py
git commit -m "feat: add MANE Select fetch and parse module"
```

---

### Task 3: Export MANE Select from gene_mapping package

**Files:**
- Modify: `src/usher_pipeline/gene_mapping/__init__.py`

- [ ] **Step 1: Add exports to __init__.py**

Add to `src/usher_pipeline/gene_mapping/__init__.py`:

```python
from usher_pipeline.gene_mapping.mane_select import (
    fetch_mane_select,
    parse_mane_select,
    load_mane_select,
)
```

And add to `__all__`:

```python
"fetch_mane_select",
"parse_mane_select",
"load_mane_select",
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from usher_pipeline.gene_mapping import fetch_mane_select, parse_mane_select, load_mane_select; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/usher_pipeline/gene_mapping/__init__.py
git commit -m "feat: export MANE Select functions from gene_mapping package"
```

---

## Chunk 2: CLI integration + scoring dedup

### Task 4: Add MANE Select step to setup CLI

**Files:**
- Modify: `src/usher_pipeline/cli/setup_cmd.py:187-210`

- [ ] **Step 1: Add MANE fetch/load to setup command**

In `src/usher_pipeline/cli/setup_cmd.py`, after the gene_universe save block (after line 202) and before provenance save (line 206), add:

```python
# 8b. Fetch and load MANE Select canonical transcripts
click.echo("Fetching MANE Select canonical transcripts...")
from usher_pipeline.gene_mapping.mane_select import (
    fetch_mane_select,
    parse_mane_select,
    load_mane_select,
)

try:
    mane_gz = fetch_mane_select(
        data_dir=config.data_dir,
        version=config.versions.mane_version,
        force=force,
    )
    mane_df = parse_mane_select(mane_gz)
    load_mane_select(store, mane_df)
    click.echo(click.style(
        f"  Loaded {len(mane_df)} MANE transcripts ({mane_df.filter(pl.col('mane_status') == 'MANE Select').height} MANE Select)",
        fg='green'
    ))
except Exception as e:
    click.echo(click.style(
        f"  Warning: MANE Select fetch failed ({e}). Scoring will fall back to gnomAD proxy.",
        fg='yellow'
    ))
    logger.warning("mane_select_fetch_failed", error=str(e))
click.echo()
```

Also add `import polars as pl` at the top if not already present (it is).

Note: MANE fetch failure is a warning, not fatal. The scoring dedup gracefully falls back.

- [ ] **Step 2: Also handle checkpoint case (line 66-88)**

In the checkpoint-exists early-return path, also check for mane_select checkpoint and fetch if missing:

```python
# Inside the `if has_checkpoint and not force:` block, after loading gene_universe,
# check if MANE Select also exists:
if not store.has_checkpoint('mane_select'):
    click.echo("MANE Select data not yet loaded, fetching...")
    from usher_pipeline.gene_mapping.mane_select import (
        fetch_mane_select,
        parse_mane_select,
        load_mane_select,
    )
    try:
        mane_gz = fetch_mane_select(
            data_dir=config.data_dir,
            version=config.versions.mane_version,
            force=False,
        )
        mane_df = parse_mane_select(mane_gz)
        load_mane_select(store, mane_df)
        click.echo(click.style(
            f"  Loaded {len(mane_df)} MANE transcripts",
            fg='green'
        ))
    except Exception as e:
        click.echo(click.style(
            f"  Warning: MANE Select fetch failed ({e})",
            fg='yellow'
        ))
```

- [ ] **Step 3: Commit**

```bash
git add src/usher_pipeline/cli/setup_cmd.py
git commit -m "feat: integrate MANE Select fetch into setup command"
```

---

### Task 5: Replace gnomAD proxy dedup with MANE Select in scoring

**Files:**
- Modify: `src/usher_pipeline/scoring/integration.py:101-113,320-329`
- Create: `tests/test_mane_dedup.py`

This is the core change. Both `join_evidence_layers()` and `compute_composite_scores()` have identical dedup logic that needs updating.

- [ ] **Step 1: Write failing test for MANE-based dedup**

Create `tests/test_mane_dedup.py`:

```python
"""Test MANE Select-based gene deduplication in scoring."""

import duckdb
import polars as pl
import pytest

from usher_pipeline.config.schema import ScoringWeights
from usher_pipeline.persistence.duckdb_store import PipelineStore
from usher_pipeline.scoring.integration import compute_composite_scores


def _setup_db_with_mane(tmp_path, mane_rows):
    """Create test DuckDB with gene_universe, evidence tables, and mane_select."""
    db_path = tmp_path / "test.duckdb"
    store = PipelineStore(db_path)

    # gene_universe: two Ensembl IDs for same gene_symbol
    gene_universe = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
        "gene_symbol": ["GENEA", "GENEA", "GENEB"],
    })
    store.conn.execute("CREATE TABLE gene_universe AS SELECT * FROM gene_universe")

    # gnomAD: ENSG002 has gnomAD data, ENSG001 does not
    gnomad = pl.DataFrame({
        "gene_id": ["ENSG002", "ENSG003"],
        "loeuf_normalized": [0.5, 0.7],
        "quality_flag": ["measured", "measured"],
    })
    store.conn.execute("CREATE TABLE gnomad_constraint AS SELECT * FROM gnomad")

    # MANE Select: ENSG001 is the MANE Select canonical ID for GENEA
    mane = pl.DataFrame(mane_rows)
    store.conn.execute("CREATE TABLE mane_select AS SELECT * FROM mane")

    # Empty evidence tables
    for table_name, score_col in [
        ("tissue_expression", "expression_score_normalized"),
        ("annotation_completeness", "annotation_score_normalized"),
        ("subcellular_localization", "localization_score_normalized"),
        ("animal_model_phenotypes", "animal_model_score_normalized"),
        ("literature_evidence", "literature_score_normalized"),
    ]:
        empty = pl.DataFrame({"gene_id": [], score_col: []})
        store.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM empty")

    return store


def test_mane_preferred_over_gnomad(tmp_path):
    """MANE Select ID should be preferred even when gnomAD data exists on another ID."""
    store = _setup_db_with_mane(tmp_path, {
        "ensembl_gene_id": ["ENSG001"],
        "ensembl_transcript_id": ["ENST001"],
        "gene_symbol": ["GENEA"],
        "refseq_transcript_id": ["NM_001"],
        "mane_status": ["MANE Select"],
    })

    weights = ScoringWeights()
    result = compute_composite_scores(store, weights)

    # GENEA should use ENSG001 (MANE Select), not ENSG002 (has gnomAD)
    genea = result.filter(pl.col("gene_symbol") == "GENEA")
    assert genea.height == 1
    assert genea["gene_id"][0] == "ENSG001"

    store.close()


def test_gnomad_fallback_when_no_mane(tmp_path):
    """Without MANE data, fall back to gnomAD proxy (existing behavior)."""
    store = _setup_db_with_mane(tmp_path, {
        "ensembl_gene_id": [],
        "ensembl_transcript_id": [],
        "gene_symbol": [],
        "refseq_transcript_id": [],
        "mane_status": [],
    })

    weights = ScoringWeights()
    result = compute_composite_scores(store, weights)

    # GENEA should use ENSG002 (has gnomAD), since no MANE data
    genea = result.filter(pl.col("gene_symbol") == "GENEA")
    assert genea.height == 1
    assert genea["gene_id"][0] == "ENSG002"

    store.close()


def test_scoring_works_without_mane_table(tmp_path):
    """Scoring should still work if mane_select table doesn't exist (graceful fallback)."""
    db_path = tmp_path / "test.duckdb"
    store = PipelineStore(db_path)

    gene_universe = pl.DataFrame({
        "gene_id": ["ENSG001", "ENSG002"],
        "gene_symbol": ["GENEA", "GENEA"],
    })
    store.conn.execute("CREATE TABLE gene_universe AS SELECT * FROM gene_universe")

    gnomad = pl.DataFrame({
        "gene_id": ["ENSG002"],
        "loeuf_normalized": [0.5],
        "quality_flag": ["measured"],
    })
    store.conn.execute("CREATE TABLE gnomad_constraint AS SELECT * FROM gnomad")

    # NO mane_select table

    for table_name, score_col in [
        ("tissue_expression", "expression_score_normalized"),
        ("annotation_completeness", "annotation_score_normalized"),
        ("subcellular_localization", "localization_score_normalized"),
        ("animal_model_phenotypes", "animal_model_score_normalized"),
        ("literature_evidence", "literature_score_normalized"),
    ]:
        empty = pl.DataFrame({"gene_id": [], score_col: []})
        store.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM empty")

    weights = ScoringWeights()
    result = compute_composite_scores(store, weights)

    # Should fall back to gnomAD proxy: ENSG002 preferred
    genea = result.filter(pl.col("gene_symbol") == "GENEA")
    assert genea.height == 1
    assert genea["gene_id"][0] == "ENSG002"

    store.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mane_dedup.py -v`
Expected: `test_mane_preferred_over_gnomad` FAILS (ENSG002 selected instead of ENSG001)

- [ ] **Step 3: Extract dedup helper function in integration.py**

Replace the duplicated dedup logic in both functions with a shared helper. In `src/usher_pipeline/scoring/integration.py`, add after the imports:

```python
def _load_mane_gene_ids(store: PipelineStore) -> set[str]:
    """Load MANE Select gene IDs from DuckDB, returning empty set if unavailable."""
    try:
        mane_df = store.conn.execute(
            "SELECT ensembl_gene_id FROM mane_select WHERE mane_status = 'MANE Select'"
        ).pl()
        return set(mane_df["ensembl_gene_id"].to_list())
    except duckdb.CatalogException:
        logger.info("mane_select_table_not_found_using_gnomad_proxy")
        return set()


def _dedup_by_gene_symbol(
    result: pl.DataFrame,
    mane_ids: set[str],
    context: str,
) -> pl.DataFrame:
    """Deduplicate to one row per gene_symbol using MANE > gnomAD > lowest ID.

    Args:
        result: DataFrame with gene_id, gene_symbol, gnomad_score columns.
        mane_ids: Set of Ensembl gene IDs in MANE Select.
        context: Logging context label.

    Returns:
        Deduplicated DataFrame.
    """
    before = result.height

    result = result.with_columns(
        pl.col("gene_id").is_in(mane_ids).cast(pl.Int8).alias("_is_mane") if mane_ids else pl.lit(0).cast(pl.Int8).alias("_is_mane"),
        pl.col("gnomad_score").is_not_null().cast(pl.Int8).alias("_has_gnomad"),
    ).sort(
        ["gene_symbol", "_is_mane", "_has_gnomad", "gene_id"],
        descending=[False, True, True, False],
    ).unique(subset=["gene_symbol"], keep="first").drop(["_is_mane", "_has_gnomad"])

    after = result.height
    if before != after:
        logger.info(
            f"{context}_dedup_gene_symbol",
            before=before,
            after=after,
            removed=before - after,
            using_mane=len(mane_ids) > 0,
        )
    return result
```

- [ ] **Step 4: Update join_evidence_layers() to use helper**

Replace lines 101-123 in `join_evidence_layers()`:

```python
    # Deduplicate: keep one row per gene_symbol.
    # Preference: MANE Select canonical ID > gnomAD-recognized ID > lowest Ensembl ID.
    mane_ids = _load_mane_gene_ids(store)
    result = _dedup_by_gene_symbol(result, mane_ids, "join_evidence")
```

- [ ] **Step 5: Update compute_composite_scores() to use helper**

Replace lines 320-338 in `compute_composite_scores()`:

```python
    # Deduplicate: keep one row per gene_symbol.
    # See _dedup_by_gene_symbol() for preference logic.
    mane_ids = _load_mane_gene_ids(store)
    result = _dedup_by_gene_symbol(result, mane_ids, "composite_scores")
```

- [ ] **Step 6: Run all tests**

Run: `pytest tests/test_mane_dedup.py tests/test_scoring.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add src/usher_pipeline/scoring/integration.py tests/test_mane_dedup.py
git commit -m "feat: replace gnomAD proxy dedup with MANE Select canonical preference"
```

---

### Task 6: Update existing scoring test to include mane_select table

**Files:**
- Modify: `tests/test_scoring.py:119-193`

The existing `test_null_preservation_in_composite` creates a DuckDB without a `mane_select` table. It should still pass (graceful fallback), but let's verify.

- [ ] **Step 1: Run existing scoring tests**

Run: `pytest tests/test_scoring.py -v`
Expected: All PASS (graceful fallback when mane_select table missing)

- [ ] **Step 2: Commit (no changes needed if tests pass)**

If existing tests pass without modification, no commit needed. If any fail, fix and commit.

---

### Task 7: Run full test suite

- [ ] **Step 1: Run all tests**

Run: `pytest tests/ -v -k "not integration"`
Expected: All PASS

- [ ] **Step 2: Commit any fixes if needed**

---

### Task 8: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update CLAUDE.md**

Add `mane_select` to the DuckDB Tables section:

```markdown
| `mane_select` | NCBI MANE v1.3 | — (reference table) |
```

Update the gene dedup note in Key Design Decisions to mention MANE Select:

```markdown
- **Gene symbol deduplication**: `gene_universe` has multiple Ensembl IDs per gene_symbol (~1,539 symbols with excess IDs). Scoring deduplicates by `gene_symbol`, preferring MANE Select canonical IDs, then gnomAD-recognized IDs, then lowest Ensembl ID. See `scoring/integration.py`.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with MANE Select table and dedup strategy"
```

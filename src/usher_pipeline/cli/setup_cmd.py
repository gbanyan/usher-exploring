"""Setup command: Initialize pipeline data infrastructure.

Orchestrates the full setup flow:
1. Load config
2. Create PipelineStore and ProvenanceTracker
3. Check for existing checkpoints
4. Load the frozen Ensembl gene universe source
5. Map gene IDs (Ensembl -> HGNC + UniProt)
6. Validate mapping quality
7. Save to DuckDB with provenance
"""

import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

import click
import duckdb
import polars as pl

from usher_pipeline.config.loader import load_config
from usher_pipeline.gene_mapping import (
    GeneMapper,
    MappingValidator,
    MappingReport,
    load_frozen_ensembl_gene_source,
    load_mane_select,
    parse_mane_select,
    sha256_file,
    validate_gene_universe,
)
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker

logger = logging.getLogger(__name__)


def _gene_source_path(config) -> Path:
    """Resolve the configured frozen Ensembl source against data_dir."""

    source_value = config.versions.ensembl_gene_source
    source_url = config.versions.ensembl_gene_source_url
    expected_sha256 = config.versions.ensembl_gene_source_sha256
    if not source_value or not source_url or not expected_sha256:
        raise ValueError(
            "Frozen Ensembl setup requires ensembl_gene_source, "
            "ensembl_gene_source_url, and ensembl_gene_source_sha256"
        )

    source_path = Path(source_value).expanduser()
    if not source_path.is_absolute():
        source_path = Path(config.data_dir) / source_path
    return source_path


def _gene_source_checkpoint_metadata(config, source_path: Path) -> dict[str, str | int]:
    """Return the identity fields required to reuse a gene-universe checkpoint."""

    source_url = config.versions.ensembl_gene_source_url
    expected_sha256 = config.versions.ensembl_gene_source_sha256
    if not source_url or not expected_sha256:
        raise ValueError(
            "Frozen Ensembl setup requires a source URL and expected SHA-256"
        )
    return {
        "checkpoint_type": "frozen_ensembl_gene_universe",
        "ensembl_release": config.versions.ensembl_release,
        "source_path": str(source_path.resolve()),
        "source_filename": source_path.name,
        "source_url": source_url,
        "source_sha256": expected_sha256.lower(),
        "expected_sha256": expected_sha256.lower(),
        "feature_type": "gene",
        "gene_biotype": "protein_coding",
    }


def _load_exact_legacy_mapping(mapping_db_path: Path) -> pl.DataFrame:
    """Load the legacy mapping cache without normalizing or querying IDs."""

    mapping_db_path = Path(mapping_db_path).expanduser()
    if not mapping_db_path.is_file():
        raise FileNotFoundError(
            "Cache-only setup requires an existing local mapping DuckDB: "
            f"{mapping_db_path}"
        )

    connection = duckdb.connect(str(mapping_db_path), read_only=True)
    try:
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        if "gene_universe" not in tables:
            raise ValueError(
                "Cache-only setup mapping DuckDB lacks the gene_universe table: "
                f"{mapping_db_path}"
            )
        columns = {
            row[0]
            for row in connection.execute("DESCRIBE gene_universe").fetchall()
        }
        required = {"gene_id", "gene_symbol", "uniprot_accession"}
        missing = sorted(required - columns)
        if missing:
            raise ValueError(
                "Cache-only setup mapping DuckDB has an incompatible gene_universe "
                f"cache; missing columns: {', '.join(missing)}"
            )
        mapping = connection.execute(
            """
            SELECT gene_id, gene_symbol, uniprot_accession
            FROM gene_universe
            """
        ).pl()
    finally:
        connection.close()

    if mapping["gene_id"].null_count() > 0:
        raise ValueError(
            "Cache-only setup mapping cache contains NULL Ensembl IDs; refusing "
            "to infer an exact stable-ID intersection"
        )
    mapping_ids = mapping["gene_id"].to_list()
    invalid_ids = [
        gene_id
        for gene_id in mapping_ids
        if not isinstance(gene_id, str) or not re.fullmatch(r"ENSG[0-9]+", gene_id)
    ]
    if invalid_ids:
        raise ValueError(
            "Cache-only setup mapping cache contains non-stable Ensembl IDs; "
            f"examples: {invalid_ids[:5]}"
        )
    if len(mapping_ids) != len(set(mapping_ids)):
        raise ValueError(
            "Cache-only setup mapping cache contains duplicate Ensembl IDs; "
            "refusing an ambiguous exact-ID intersection"
        )
    return mapping


def _build_cache_only_gene_universe(
    gene_source,
    mapping_db_path: Path,
) -> tuple[pl.DataFrame, dict[str, int]]:
    """Build a universe from GTF membership plus exact local mapping fields.

    GTF membership and native gene names are authoritative.  The legacy cache
    contributes only ``gene_symbol`` when the GTF has no name for that exact
    stable ID, and ``uniprot_accession`` for that exact stable ID.  Rows not in
    the frozen GTF are intentionally discarded.
    """

    mapping = _load_exact_legacy_mapping(mapping_db_path)
    source_ids = list(gene_source.genes)
    source_id_set = set(source_ids)
    if set(gene_source.gene_symbols) != source_id_set:
        raise ValueError(
            "Frozen GTF symbol metadata does not cover exactly the retained "
            "protein-coding IDs"
        )

    mapping_by_id = {
        row["gene_id"]: row
        for row in mapping.iter_rows(named=True)
        if row["gene_id"] in source_id_set
    }
    gene_symbols: list[str | None] = []
    gene_symbol_sources: list[str] = []
    uniprot_accessions: list[str | None] = []
    uniprot_sources: list[str] = []
    gene_biotypes: list[str] = []

    for gene_id in source_ids:
        gtf_symbol = gene_source.gene_symbols[gene_id]
        legacy_row = mapping_by_id.get(gene_id)
        legacy_symbol = (
            legacy_row["gene_symbol"]
            if legacy_row is not None and legacy_row["gene_symbol"]
            else None
        )
        legacy_uniprot = (
            legacy_row["uniprot_accession"]
            if legacy_row is not None and legacy_row["uniprot_accession"]
            else None
        )

        if gtf_symbol:
            gene_symbols.append(gtf_symbol)
            gene_symbol_sources.append("gtf_gene_name")
        elif legacy_symbol:
            gene_symbols.append(legacy_symbol)
            gene_symbol_sources.append("legacy_db_exact_id_fallback")
        else:
            # Downstream symbol-level scoring must preserve one analysis label
            # per retained Ensembl ID.  An unresolved GTF name therefore gets
            # an explicit stable-ID label; the source flag keeps it distinct
            # from a real symbol and manuscript/report layers can expose it as
            # a fallback ID label later.
            gene_symbols.append(gene_id)
            gene_symbol_sources.append("gene_id_fallback_unresolved")

        if legacy_uniprot:
            uniprot_accessions.append(legacy_uniprot)
            uniprot_sources.append("legacy_db_exact_id")
        else:
            uniprot_accessions.append(None)
            uniprot_sources.append("unresolved")

        biotype_values = gene_source.gene_biotypes[gene_id]
        if biotype_values != frozenset({"protein_coding"}):
            raise ValueError(
                f"Frozen GTF retained non-unique biotype metadata for {gene_id}: "
                f"{sorted(biotype_values)}"
            )
        gene_biotypes.append("protein_coding")

    result = pl.DataFrame(
        {
            "gene_id": source_ids,
            "gene_symbol": gene_symbols,
            "gene_symbol_source": gene_symbol_sources,
            "uniprot_accession": uniprot_accessions,
            "uniprot_source": uniprot_sources,
            "gene_biotype": gene_biotypes,
        }
    )
    if set(result["gene_id"].to_list()) != source_id_set:
        raise ValueError(
            "Cache-only setup generated gene IDs outside or missing from the "
            "frozen GTF universe"
        )

    symbol_counts = Counter(gene_symbol_sources)
    uniprot_counts = Counter(uniprot_sources)
    counts = {
        "gene_symbol_gtf_native": symbol_counts["gtf_gene_name"],
        "gene_symbol_legacy_exact_id_fallback": symbol_counts[
            "legacy_db_exact_id_fallback"
        ],
        "gene_symbol_unresolved": symbol_counts["gene_id_fallback_unresolved"],
        "uniprot_legacy_exact_id": uniprot_counts["legacy_db_exact_id"],
        "uniprot_unresolved": uniprot_counts["unresolved"],
        "legacy_mapping_rows_intersecting_gtf": len(mapping_by_id),
        "legacy_mapping_rows_outside_gtf": mapping.height - len(mapping_by_id),
    }
    return result, counts


def _load_local_mane_cache(
    config,
    store,
    gene_ids: set[str],
) -> tuple[Path, int]:
    """Load and restrict the configured local MANE cache to the GTF universe."""

    version = config.versions.mane_version
    mane_path = Path(config.data_dir) / f"MANE.GRCh38.v{version}.summary.txt.gz"
    if not mane_path.is_file():
        raise FileNotFoundError(
            "Cache-only setup requires the local MANE cache; refusing to download: "
            f"{mane_path}"
        )

    try:
        mane_df = parse_mane_select(mane_path)
    except Exception as exc:
        raise ValueError(
            f"Local MANE cache is unreadable or schema-mismatched: {mane_path}"
        ) from exc
    if mane_df.height == 0:
        raise ValueError(f"Local MANE cache is empty: {mane_path}")
    invalid_ids = mane_df.filter(
        ~pl.col("ensembl_gene_id").str.contains(r"^ENSG[0-9]+$")
    )
    if invalid_ids.height:
        raise ValueError(
            "Local MANE cache contains non-stable Ensembl IDs; refusing to "
            f"load {invalid_ids.height} rows"
        )

    restricted = mane_df.filter(pl.col("ensembl_gene_id").is_in(gene_ids))
    if restricted.height == 0 or not restricted.filter(
        pl.col("mane_status") == "MANE Select"
    ).height:
        raise ValueError(
            "Local MANE cache has no MANE Select rows intersecting the frozen "
            "GTF universe"
        )
    load_mane_select(store, restricted)
    return mane_path, restricted.height


def _setup_from_local_caches(config, store, provenance, mapping_db_path: Path) -> dict:
    """Run setup without any network access using explicit local caches."""

    source_path = _gene_source_path(config)
    source = load_frozen_ensembl_gene_source(
        source_path,
        ensembl_release=config.versions.ensembl_release,
        expected_sha256=config.versions.ensembl_gene_source_sha256,
        source_url=config.versions.ensembl_gene_source_url,
    )
    universe_validation = validate_gene_universe(
        source.genes,
        gene_biotypes=source.gene_biotypes,
    )
    if not universe_validation.passed:
        raise ValueError(
            "Frozen GTF gene-universe validation failed: "
            + "; ".join(universe_validation.messages)
        )

    universe_df, mapping_counts = _build_cache_only_gene_universe(
        source,
        mapping_db_path,
    )
    mapping_report = MappingReport(
        total_genes=universe_df.height,
        mapped_hgnc=universe_df["gene_symbol"].drop_nulls().len(),
        mapped_uniprot=universe_df["uniprot_accession"].drop_nulls().len(),
        unmapped_ids=universe_df.filter(
            pl.col("gene_symbol").is_null()
        )["gene_id"].to_list(),
    )
    mapping_validation = MappingValidator(
        min_success_rate=0.90,
        warn_threshold=0.95,
    ).validate(mapping_report)
    if not mapping_validation.passed:
        raise ValueError(
            "Cache-only gene mapping validation failed: "
            + "; ".join(mapping_validation.messages)
        )

    checkpoint_metadata = {
        **_gene_source_checkpoint_metadata(config, source_path),
        "source_sha256": source.metadata["source_sha256"],
        "mapping_mode": "cache_only",
        "gene_symbol_policy": (
            "GTF gene_name; exact legacy DB gene_symbol fallback when GTF "
            "gene_name is absent; stable Ensembl ID fallback when both are absent"
        ),
        "uniprot_policy": "exact legacy DB Ensembl stable-ID intersection only",
        "legacy_mapping_source_path": str(Path(mapping_db_path).resolve()),
        **mapping_counts,
    }
    store.save_dataframe(
        universe_df,
        table_name="gene_universe",
        description=json.dumps(checkpoint_metadata, sort_keys=True),
    )
    mane_path, mane_count = _load_local_mane_cache(
        config,
        store,
        set(source.genes),
    )

    provenance.record_step(
        "fetch_gene_universe",
        {
            **source.metadata,
            "gene_count": len(source.genes),
            "mode": "cache_only_local_frozen_gtf",
            "raw_source_coverage": "complete",
            "source_name": "ensembl_gtf_local",
            "local_path": str(source_path.resolve()),
        },
    )
    provenance.record_step(
        "map_gene_ids",
        {
            "mapping_mode": "cache_only",
            "total_genes": mapping_report.total_genes,
            "mapped_hgnc": mapping_report.mapped_hgnc,
            "mapped_uniprot": mapping_report.mapped_uniprot,
            "success_rate_hgnc": f"{mapping_report.success_rate_hgnc:.1%}",
            "success_rate_uniprot": f"{mapping_report.success_rate_uniprot:.1%}",
            "source_name": "legacy_mapping_duckdb",
            "local_path": str(Path(mapping_db_path).resolve()),
            "source_artifact_hash": sha256_file(Path(mapping_db_path)),
            **mapping_counts,
        },
    )
    provenance.record_step(
        "load_mane_select",
        {
            "mode": "raw_local_reprocess",
            "raw_source_coverage": "complete",
            "source_name": "mane_select_local",
            "local_path": str(mane_path.resolve()),
            "row_count": mane_count,
            "version": config.versions.mane_version,
        },
    )
    provenance.record_step(
        "validate_mapping",
        {
            "hgnc_rate": f"{mapping_validation.hgnc_rate:.1%}",
            "uniprot_rate": f"{mapping_validation.uniprot_rate:.1%}",
            "validation_passed": True,
        },
    )
    return {
        "gene_count": universe_df.height,
        "mane_count": mane_count,
        "mane_path": str(mane_path),
        **mapping_counts,
    }


def _has_current_gene_universe_checkpoint(config, store) -> bool:
    """Return whether a checkpoint and its configured frozen source are valid.

    A matching checkpoint is not sufficient by itself: the configured cache
    must still exist and match the expected digest before it can be reused.
    """

    try:
        source_path = _gene_source_path(config)
        expected_metadata = _gene_source_checkpoint_metadata(config, source_path)
    except (ValueError, OSError):
        return False

    if not source_path.is_file():
        logger.warning(
            "frozen_ensembl_source_missing_for_checkpoint",
            extra={"source_path": str(source_path)},
        )
        return False

    try:
        actual_sha256 = sha256_file(source_path)
    except OSError:
        logger.warning(
            "frozen_ensembl_source_unreadable_for_checkpoint",
            extra={"source_path": str(source_path)},
        )
        return False

    expected_sha256 = expected_metadata["expected_sha256"]
    if actual_sha256.lower() != expected_sha256:
        logger.warning(
            "frozen_ensembl_source_checksum_mismatch_for_checkpoint",
            extra={
                "source_path": str(source_path),
                "expected_sha256": expected_sha256,
                "actual_sha256": actual_sha256,
            },
        )
        return False

    checkpoints = {
        checkpoint["table_name"]: checkpoint
        for checkpoint in store.list_checkpoints()
    }
    checkpoint = checkpoints.get("gene_universe")
    if not checkpoint:
        return False

    description = checkpoint.get("description") or ""
    try:
        checkpoint_metadata = json.loads(description)
    except json.JSONDecodeError:
        return False
    return all(
        checkpoint_metadata.get(key) == value
        for key, value in expected_metadata.items()
    )


def _fetch_and_load_mane(config, store, force=False):
    """Fetch and load MANE Select data, warning on failure (non-fatal)."""
    click.echo("Fetching MANE Select canonical transcripts...")
    from usher_pipeline.gene_mapping.mane_select import (
        fetch_mane_select,
        load_mane_select,
        parse_mane_select,
    )
    try:
        mane_gz = fetch_mane_select(
            data_dir=config.data_dir,
            version=config.versions.mane_version,
            force=force,
        )
        mane_df = parse_mane_select(mane_gz)
        load_mane_select(store, mane_df)
        mane_select_count = mane_df.filter(
            mane_df["mane_status"] == "MANE Select"
        ).height
        click.echo(click.style(
            f"  Loaded {len(mane_df)} MANE transcripts ({mane_select_count} MANE Select)",
            fg='green'
        ))
    except Exception as e:
        click.echo(click.style(
            f"  Warning: MANE Select fetch failed ({e}). Scoring will fall back to gnomAD proxy.",
            fg='yellow'
        ))
        logger.warning("mane_select_fetch_failed", error=str(e))
    click.echo()


@click.command('setup')
@click.option(
    '--force',
    is_flag=True,
    help='Re-run setup even if checkpoints exist (re-fetches all data)'
)
@click.option(
    '--cache-only',
    is_flag=True,
    help=(
        'Build from the frozen GTF plus explicit local mapping/MANE caches; '
        'never query external services'
    ),
)
@click.option(
    '--mapping-db',
    type=click.Path(path_type=Path),
    default=None,
    help=(
        'Existing local DuckDB containing the donor gene_universe mapping; '
        'defaults to data/pipeline_source.duckdb in cache-only mode'
    ),
)
@click.pass_context
def setup(ctx, force, cache_only, mapping_db):
    """Initialize pipeline data infrastructure.

    Loads the frozen gene universe, maps IDs, validates results, and saves to DuckDB.
    Supports checkpoint-restart: skips expensive operations if data exists.
    """
    config_path = ctx.obj['config_path']
    click.echo(click.style("=== Usher Pipeline Setup ===", bold=True))
    click.echo()

    try:
        if force and cache_only:
            raise click.ClickException(
                "--force and --cache-only are mutually exclusive: cache-only "
                "setup must not refresh any source"
            )

        # 1. Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo(f"  Ensembl Release: {config.versions.ensembl_release}")
        click.echo(f"  DuckDB Path: {config.duckdb_path}")
        click.echo()

        # 2. Create PipelineStore and ProvenanceTracker
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        if cache_only:
            mapping_db_path = mapping_db or (
                Path(config.data_dir) / "pipeline_source.duckdb"
            )
            click.echo("Running explicit cache-only setup...")
            click.echo(f"  Mapping donor: {mapping_db_path}")
            summary = _setup_from_local_caches(
                config,
                store,
                provenance,
                mapping_db_path,
            )
            provenance_path = Path(config.data_dir) / "setup.provenance.json"
            provenance.save_sidecar(provenance_path)
            click.echo(click.style(
                f"  Loaded {summary['gene_count']} frozen GTF genes",
                fg='green',
            ))
            click.echo(
                "  Gene symbols: "
                f"{summary['gene_symbol_gtf_native']} GTF-native, "
                f"{summary['gene_symbol_legacy_exact_id_fallback']} exact-ID "
                f"fallback, {summary['gene_symbol_unresolved']} unresolved"
            )
            click.echo(
                "  UniProt: "
                f"{summary['uniprot_legacy_exact_id']} exact-ID, "
                f"{summary['uniprot_unresolved']} unresolved"
            )
            click.echo(f"  MANE rows retained in universe: {summary['mane_count']}")
            click.echo(f"  Provenance: {provenance_path}")
            click.echo(click.style(
                "Cache-only setup complete; no external source was queried.",
                fg='green',
                bold=True,
            ))
            return

        # 3. Check checkpoint
        has_checkpoint = store.has_checkpoint('gene_universe')
        current_checkpoint = _has_current_gene_universe_checkpoint(config, store)

        if has_checkpoint and not current_checkpoint and not force:
            click.echo(click.style(
                "Existing gene universe checkpoint or frozen cache is invalid; "
                "checkpoint reuse rejected. Validating the configured source "
                "before rebuilding it.",
                fg='yellow'
            ))
            click.echo()

        if has_checkpoint and current_checkpoint and not force:
            click.echo(click.style(
                "Frozen Ensembl gene universe checkpoint exists. "
                "Skipping load (use --force to reload).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for validation display
            df = store.load_dataframe('gene_universe')
            if df is not None:
                gene_count = len(df)
                click.echo(f"Loaded {gene_count} genes from checkpoint")
                click.echo()

                # Fetch MANE Select if not yet loaded
                if not store.has_checkpoint('mane_select'):
                    _fetch_and_load_mane(config, store, force=False)

                # Display summary
                click.echo(click.style("=== Setup Summary ===", bold=True))
                click.echo(f"Gene Count: {gene_count}")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Setup complete (used existing checkpoint)", fg='green'))
                return

        # 4. Load the frozen Ensembl gene universe
        source_path = _gene_source_path(config)
        expected_sha256 = config.versions.ensembl_gene_source_sha256
        source_url = config.versions.ensembl_gene_source_url
        click.echo("Loading protein-coding genes from frozen Ensembl GTF...")
        click.echo(f"  Ensembl Release: {config.versions.ensembl_release}")
        click.echo(f"  Source: {source_path}")

        try:
            gene_source = load_frozen_ensembl_gene_source(
                source_path,
                ensembl_release=config.versions.ensembl_release,
                expected_sha256=expected_sha256,
                source_url=source_url,
            )
            gene_universe = gene_source.genes
            click.echo(click.style(
                f"  Loaded {len(gene_universe)} protein-coding genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading genes: {e}", fg='red'), err=True)
            logger.exception("Failed to load gene universe")
            sys.exit(1)

        click.echo()

        # 5. Validate gene universe
        click.echo("Validating gene universe...")
        universe_validation = validate_gene_universe(
            gene_universe,
            gene_biotypes=gene_source.gene_biotypes,
        )

        for msg in universe_validation.messages:
            if 'FAILED' in msg:
                click.echo(click.style(f"  {msg}", fg='red'))
            else:
                click.echo(f"  {msg}")

        if not universe_validation.passed:
            click.echo()
            click.echo(click.style("Gene universe validation failed", fg='red'), err=True)
            sys.exit(1)

        click.echo(click.style("  Validation passed", fg='green'))
        click.echo()
        provenance.record_step('fetch_gene_universe', {
            **gene_source.metadata,
            'gene_count': len(gene_universe),
        })

        # 6. Map gene IDs
        click.echo("Mapping Ensembl IDs to HGNC symbols and UniProt accessions...")
        mapper = GeneMapper(batch_size=1000)

        try:
            mapping_results, mapping_report = mapper.map_ensembl_ids(gene_universe)
            click.echo(click.style(
                f"  Mapped {mapping_report.mapped_hgnc}/{mapping_report.total_genes} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error mapping IDs: {e}", fg='red'), err=True)
            logger.exception("Failed to map gene IDs")
            sys.exit(1)

        click.echo()
        provenance.record_step('map_gene_ids', {
            'total_genes': mapping_report.total_genes,
            'mapped_hgnc': mapping_report.mapped_hgnc,
            'mapped_uniprot': mapping_report.mapped_uniprot,
            'success_rate_hgnc': f"{mapping_report.success_rate_hgnc:.1%}",
            'success_rate_uniprot': f"{mapping_report.success_rate_uniprot:.1%}",
        })

        # 7. Validate mapping
        click.echo("Validating mapping quality...")
        validator = MappingValidator(min_success_rate=0.90, warn_threshold=0.95)
        validation_result = validator.validate(mapping_report)

        for msg in validation_result.messages:
            if 'FAILED' in msg:
                click.echo(click.style(f"  {msg}", fg='red'))
            elif 'WARNING' in msg:
                click.echo(click.style(f"  {msg}", fg='yellow'))
            else:
                click.echo(f"  {msg}")

        if not validation_result.passed:
            # Save unmapped report
            unmapped_path = Path(config.data_dir) / "unmapped_genes.txt"
            validator.save_unmapped_report(mapping_report, unmapped_path)
            click.echo()
            click.echo(click.style(
                f"Mapping validation failed. Unmapped genes saved to: {unmapped_path}",
                fg='red'
            ), err=True)
            sys.exit(1)

        click.echo(click.style("  Validation passed", fg='green'))
        click.echo()
        provenance.record_step('validate_mapping', {
            'hgnc_rate': f"{validation_result.hgnc_rate:.1%}",
            'uniprot_rate': f"{validation_result.uniprot_rate:.1%}",
            'validation_passed': True
        })

        # 8. Save to DuckDB
        click.echo("Saving gene universe to DuckDB...")

        # Create DataFrame with mapping results
        df = pl.DataFrame({
            'gene_id': [r.ensembl_id for r in mapping_results],
            'gene_symbol': [r.hgnc_symbol for r in mapping_results],
            'uniprot_accession': [r.uniprot_accession for r in mapping_results],
            'gene_biotype': [
                next(iter(gene_source.gene_biotypes[r.ensembl_id]))
                for r in mapping_results
            ],
        })

        store.save_dataframe(
            table_name='gene_universe',
            df=df,
            description=json.dumps(
                {
                    **_gene_source_checkpoint_metadata(config, source_path),
                    "source_sha256": gene_source.metadata["source_sha256"],
                },
                sort_keys=True,
            ),
        )
        click.echo(click.style(f"  Saved {len(df)} genes to 'gene_universe' table", fg='green'))
        click.echo()

        # 8b. Fetch and load MANE Select canonical transcripts
        _fetch_and_load_mane(config, store, force=force)

        # 9. Save provenance
        click.echo("Saving provenance metadata...")
        provenance_path = Path(config.data_dir) / "setup.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # 10. Display summary
        click.echo(click.style("=== Setup Summary ===", bold=True))
        click.echo(f"Gene Count: {len(gene_universe)}")
        click.echo(f"HGNC Mapping Rate: {mapping_report.success_rate_hgnc:.1%} ({mapping_report.mapped_hgnc}/{mapping_report.total_genes})")
        click.echo(f"UniProt Mapping Rate: {mapping_report.success_rate_uniprot:.1%} ({mapping_report.mapped_uniprot}/{mapping_report.total_genes})")
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Setup complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Setup failed: {e}", fg='red'), err=True)
        logger.exception("Setup command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if 'store' in locals():
            store.close()

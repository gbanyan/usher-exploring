"""Evidence layer commands: Fetch and process evidence data.

Commands for downloading and processing various evidence sources:
- gnomad: Constraint metrics (pLI, LOEUF)
- clingen: Gene-disease associations (future)
- gtex: Expression data (future)
- etc.
"""

import logging
import sys
from pathlib import Path

import click
import polars as pl
import structlog

from usher_pipeline.config.loader import load_config
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker
from usher_pipeline.evidence.gnomad import (
    download_constraint_metrics,
    process_gnomad_constraint,
    load_to_duckdb as gnomad_load_to_duckdb,
    GNOMAD_CONSTRAINT_URL,
)
from usher_pipeline.evidence.annotation import (
    process_annotation_evidence,
    load_to_duckdb as annotation_load_to_duckdb,
)
from usher_pipeline.evidence.protein import (
    process_protein_evidence,
    load_to_duckdb as protein_load_to_duckdb,
)
from usher_pipeline.evidence.localization import (
    process_localization_evidence,
    load_to_duckdb as localization_load_to_duckdb,
)
from usher_pipeline.evidence.literature import (
    process_literature_evidence,
    load_to_duckdb as literature_load_to_duckdb,
)
from usher_pipeline.evidence.animal_models import (
    process_animal_model_evidence,
    load_to_duckdb as animal_models_load_to_duckdb,
)
from usher_pipeline.evidence.derived_cache import (
    reindex_annotation_from_donor,
    reindex_animal_models_from_donor,
    write_derived_cache_audit,
)
from usher_pipeline.evidence.expression import (
    process_expression_evidence,
    load_to_duckdb as expression_load_to_duckdb,
    expression_source_metadata,
    validate_expression_cache,
)
from usher_pipeline.evidence.expression.models import (
    EXPRESSION_SCHEMA_VERSION,
    LEGACY_EXPRESSION_CONTRACT_COLUMNS,
    LEGACY_HPA_TPM_COLUMNS,
    RESTRICTED_ENRICHMENT_COLUMN,
    RESTRICTED_TAU_COLUMN,
    RETINA_EVIDENCE_COLUMNS,
)

logger = logging.getLogger(__name__)


@click.group('evidence')
def evidence():
    """Fetch and process evidence layer data.

    Evidence sources include constraint metrics (gnomAD), gene-disease
    associations (ClinGen), expression data (GTEx), and more.

    Each evidence source follows the fetch -> transform -> load pattern
    with checkpoint-restart and provenance tracking.
    """
    pass


@evidence.command('gnomad')
@click.option(
    '--force',
    is_flag=True,
    help='Re-download and reprocess data even if checkpoint exists'
)
@click.option(
    '--reprocess-cached',
    is_flag=True,
    help='Reprocess the existing local constraint_metrics.tsv without downloading',
)
@click.option(
    '--url',
    default=GNOMAD_CONSTRAINT_URL,
    help='Override gnomAD constraint file URL'
)
@click.option(
    '--min-depth',
    type=float,
    default=30.0,
    help='Minimum mean sequencing depth for quality filtering (default: 30x)'
)
@click.option(
    '--min-cds-pct',
    type=float,
    default=0.9,
    help='Minimum CDS coverage percentage for quality filtering (default: 0.9 = 90%%)'
)
@click.pass_context
def gnomad(ctx, force, reprocess_cached, url, min_depth, min_cds_pct):
    """Fetch and load gnomAD constraint metrics (pLI, LOEUF).

    Downloads gnomAD v4.1 constraint metrics, filters by coverage quality,
    normalizes LOEUF scores (0-1 range, inverted), and loads to DuckDB.

    Supports checkpoint-restart: skips processing if data already exists
    in DuckDB (use --force to re-run).

    Examples:

        # First run: download, process, and load
        usher-pipeline evidence gnomad

        # Force re-download and reprocess
        usher-pipeline evidence gnomad --force

        # Use custom quality thresholds
        usher-pipeline evidence gnomad --min-depth 20 --min-cds-pct 0.8
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== gnomAD Constraint Evidence ===", bold=True))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo(f"  gnomAD Version: {config.versions.gnomad_version}")
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        if force and reprocess_cached:
            raise click.ClickException(
                "--force and --reprocess-cached are mutually exclusive: "
                "cache-only raw reprocessing cannot refresh source files"
            )

        gnomad_dir = Path(config.data_dir) / "gnomad"
        tsv_path = gnomad_dir / "constraint_metrics.tsv"
        if reprocess_cached and not tsv_path.is_file():
            raise click.ClickException(
                "Cache-only gnomAD reprocessing requires the local raw source; "
                f"missing {tsv_path}"
            )

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('gnomad_constraint')

        if has_checkpoint and not force and not reprocess_cached:
            click.echo(click.style(
                "gnomAD constraint checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('gnomad_constraint')
            if df is not None:
                total_genes = len(df)
                measured = df.filter(df['quality_flag'] == 'measured').height
                incomplete = df.filter(df['quality_flag'] == 'incomplete_coverage').height
                no_data = df.filter(df['quality_flag'] == 'no_data').height

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo(f"  Measured (good coverage): {measured}")
                click.echo(f"  Incomplete coverage: {incomplete}")
                click.echo(f"  No data: {no_data}")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Download only in the normal mode.  The explicit cached mode fails
        # closed above and never reaches the network helper.
        if reprocess_cached:
            click.echo("Using local gnomAD raw source (cache-only; no download)...")
            click.echo(click.style(f"  Source: {tsv_path}", fg='green'))
        else:
            click.echo("Downloading gnomAD constraint metrics...")
            click.echo(f"  URL: {url}")
            click.echo(f"  Version: {config.versions.gnomad_version}")
            gnomad_dir.mkdir(parents=True, exist_ok=True)
            try:
                tsv_path = download_constraint_metrics(
                    output_path=tsv_path,
                    url=url,
                    force=force
                )
                click.echo(click.style(
                    f"  Downloaded to: {tsv_path}",
                    fg='green'
                ))
            except Exception as e:
                click.echo(click.style(f"  Error downloading: {e}", fg='red'), err=True)
                logger.exception("Failed to download gnomAD constraint metrics")
                sys.exit(1)

        click.echo()
        provenance.record_step('download_gnomad_constraint', {
            'url': url,
            'version': config.versions.gnomad_version,
            'output_path': str(tsv_path),
            'mode': 'raw_local_reprocess' if reprocess_cached else 'download_or_cached_fetch',
            'reprocess_cached': reprocess_cached,
        })

        # Process constraint data
        click.echo("Processing constraint metrics...")
        click.echo(f"  Min depth: {min_depth}x")
        click.echo(f"  Min CDS coverage: {min_cds_pct:.0%}")

        try:
            df = process_gnomad_constraint(
                tsv_path=tsv_path,
                min_depth=min_depth,
                min_cds_pct=min_cds_pct
            )
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process gnomAD constraint metrics")
            sys.exit(1)

        click.echo()
        provenance.record_step('process_gnomad_constraint', {
            'min_depth': min_depth,
            'min_cds_pct': min_cds_pct,
            'total_genes': len(df),
            'mode': 'raw_local_reprocess' if reprocess_cached else 'download_or_cached_fetch',
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        try:
            loaded_df = gnomad_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description=f"gnomAD {config.versions.gnomad_version} constraint metrics"
            )
            click.echo(click.style(
                f"  Saved to 'gnomad_constraint' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load gnomAD constraint data to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = gnomad_dir / "constraint.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        summary_df = loaded_df if 'loaded_df' in locals() else df
        measured = summary_df.filter(summary_df['quality_flag'] == 'measured').height
        incomplete = summary_df.filter(summary_df['quality_flag'] == 'incomplete_coverage').height
        no_data = summary_df.filter(summary_df['quality_flag'] == 'no_data').height

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {len(summary_df)}")
        click.echo(f"  Measured (good coverage): {measured}")
        click.echo(f"  Incomplete coverage: {incomplete}")
        click.echo(f"  No data: {no_data}")
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("gnomAD evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()


@evidence.command('annotation')
@click.option(
    '--force',
    is_flag=True,
    help='Reprocess data even if checkpoint exists'
)
@click.option(
    '--derived-cache',
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help='Explicit donor DuckDB for exact-ID derived-cache migration (no raw rerun or network access)',
)
@click.pass_context
def annotation(ctx, force, derived_cache):
    """Fetch and load gene annotation completeness metrics.

    Retrieves GO term counts from mygene.info and UniProt annotation scores,
    classifies genes into annotation tiers (well/partial/poor), normalizes
    composite scores (0-1 range), and loads to DuckDB.

    Supports checkpoint-restart: skips processing if data already exists
    in DuckDB (use --force to re-run).

    Examples:

        # First run: fetch, process, and load
        usher-pipeline evidence annotation

        # Force reprocessing
        usher-pipeline evidence annotation --force
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Annotation Completeness Evidence ===", bold=True))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        if force and derived_cache is not None:
            raise click.ClickException(
                "--force and --derived-cache are mutually exclusive; derived-cache "
                "migration is read-only with respect to its donor and never fetches"
            )

        # An explicit derived-cache invocation always replaces the target
        # layer, even if a stale checkpoint is present.
        if derived_cache is not None:
            gene_universe = store.load_dataframe('gene_universe')
            if gene_universe is None or gene_universe.height == 0:
                raise click.ClickException(
                    "gene_universe table not found. Run cache-only setup first."
                )
            click.echo("Migrating annotation from the local donor cache by exact stable Ensembl ID...")
            df, audit, migration = reindex_annotation_from_donor(
                derived_cache,
                gene_universe,
                provenance=provenance,
            )
            audit_path = write_derived_cache_audit(
                audit,
                Path(config.data_dir) / "report" / "derived_cache_annotation_mapping.tsv",
            )
            annotation_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description="Annotation derived-cache migration; exact-ID donor reuse with recomputed gates/scores",
            )
            annotation_dir = Path(config.data_dir) / "annotation"
            provenance.save_sidecar(annotation_dir / "completeness.provenance.json")
            click.echo(click.style(
                f"  Derived-cache result: {df.height} genes; audit: {audit_path}",
                fg='green',
            ))
            click.echo(f"  Donor SHA-256: {migration['source_artifact_hash']}")
            click.echo(f"  Rogue donor IDs rejected: {migration['rogue_id_count']}")
            click.echo(f"  Duplicate IDs merged: {migration['merged_duplicate_id_count']}")
            click.echo("  Raw-source coverage: incomplete (derived_cache_reuse; not a raw rerun)")
            return

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('annotation_completeness')

        if has_checkpoint and not force:
            click.echo(click.style(
                "Annotation completeness checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('annotation_completeness')
            if df is not None:
                total_genes = len(df)
                well_annotated = df.filter(df['annotation_tier'] == 'well_annotated').height
                partial = df.filter(df['annotation_tier'] == 'partially_annotated').height
                poor = df.filter(df['annotation_tier'] == 'poorly_annotated').height

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo(f"  Well annotated: {well_annotated}")
                click.echo(f"  Partially annotated: {partial}")
                click.echo(f"  Poorly annotated: {poor}")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Load gene universe (need gene_ids and uniprot mappings)
        click.echo("Loading gene universe from DuckDB...")
        gene_universe = store.load_dataframe('gene_universe')

        if gene_universe is None or gene_universe.height == 0:
            click.echo(click.style(
                "Error: gene_universe table not found. Run 'usher-pipeline setup' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        gene_ids = gene_universe.select("gene_id").to_series().to_list()
        uniprot_mapping = gene_universe.select(["gene_id", "uniprot_accession"]).filter(
            gene_universe["uniprot_accession"].is_not_null()
        )

        click.echo(click.style(
            f"  Loaded {len(gene_ids)} genes ({uniprot_mapping.height} with UniProt mapping)",
            fg='green'
        ))
        click.echo()

        # Process annotation evidence
        click.echo("Fetching and processing annotation data...")
        click.echo("  This may take a few minutes (mygene.info + UniProt API queries)...")

        try:
            df = process_annotation_evidence(
                gene_ids=gene_ids,
                uniprot_mapping=uniprot_mapping
            )
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process annotation evidence")
            sys.exit(1)

        click.echo()
        provenance.record_step('process_annotation_evidence', {
            'total_genes': len(df),
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        annotation_dir = Path(config.data_dir) / "annotation"
        annotation_dir.mkdir(parents=True, exist_ok=True)

        try:
            annotation_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description="Gene annotation completeness metrics from GO terms, UniProt scores, and pathway membership"
            )
            click.echo(click.style(
                f"  Saved to 'annotation_completeness' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load annotation data to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = annotation_dir / "completeness.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        well_annotated = df.filter(df['annotation_tier'] == 'well_annotated').height
        partial = df.filter(df['annotation_tier'] == 'partially_annotated').height
        poor = df.filter(df['annotation_tier'] == 'poorly_annotated').height

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {len(df)}")
        click.echo(f"  Well annotated: {well_annotated}")
        click.echo(f"  Partially annotated: {partial}")
        click.echo(f"  Poorly annotated: {poor}")
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Annotation evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()


@evidence.command('localization')
@click.option(
    '--force',
    is_flag=True,
    help='Re-download and reprocess data even if checkpoint exists'
)
@click.option(
    '--reprocess-cached',
    is_flag=True,
    help='Reprocess the existing local HPA TSV without downloading',
)
@click.pass_context
def localization(ctx, force, reprocess_cached):
    """Fetch and load subcellular localization evidence (HPA + curated compendia).

    Integrates HPA subcellular location data with curated cilia/centrosome
    compendium membership. Classifies HPA staining separately from curated
    compendium evidence,
    scores cilia proximity, and loads to DuckDB.

    Supports checkpoint-restart: skips processing if data already exists
    in DuckDB (use --force to re-run).

    Examples:

        # First run: download, process, and load
        usher-pipeline evidence localization

        # Force re-download and reprocess
        usher-pipeline evidence localization --force
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Subcellular Localization Evidence ===", bold=True))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        if force and reprocess_cached:
            raise click.ClickException(
                "--force and --reprocess-cached are mutually exclusive: "
                "cache-only raw reprocessing cannot refresh source files"
            )

        localization_dir = Path(config.data_dir) / "localization"
        hpa_path = localization_dir / "hpa_subcellular_location.tsv"
        if reprocess_cached and not hpa_path.is_file():
            raise click.ClickException(
                "Cache-only localization reprocessing requires the local HPA raw "
                f"source; missing {hpa_path}"
            )

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('subcellular_localization')

        if has_checkpoint and not force and not reprocess_cached:
            click.echo(click.style(
                "Localization checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('subcellular_localization')
            if df is not None:
                total_genes = len(df)
                experimental = df.filter(df['evidence_type'] == 'experimental').height
                curated_compendium = df.filter(df['evidence_type'] == 'curated_compendium').height
                computational = df.filter(df['evidence_type'] == 'computational').height
                both = df.filter(
                    (df['evidence_type'] == 'mixed') | (df['evidence_type'] == 'both')
                ).height
                cilia_localized = df.filter(df['cilia_proximity_score'] > 0.5).height

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo(f"  Experimental evidence: {experimental}")
                click.echo(f"  Curated compendium evidence: {curated_compendium}")
                click.echo(f"  Computational evidence: {computational}")
                click.echo(f"  Both: {both}")
                click.echo(f"  Cilia-localized (proximity > 0.5): {cilia_localized}")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Load gene universe (need gene_ids and gene_symbol mapping)
        click.echo("Loading gene universe from DuckDB...")
        gene_universe = store.load_dataframe('gene_universe')

        if gene_universe is None or gene_universe.height == 0:
            click.echo(click.style(
                "Error: gene_universe table not found. Run 'usher-pipeline setup' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        gene_ids = gene_universe.select("gene_id").to_series().to_list()
        gene_symbol_map = gene_universe.select(["gene_id", "gene_symbol"])

        click.echo(click.style(
            f"  Loaded {len(gene_ids)} genes",
            fg='green'
        ))
        click.echo()

        # Create the directory only for normal fetches.  Cache-only mode has
        # already proven that its source file exists and must not synthesize a
        # missing cache or fall through to a downloader.
        if not reprocess_cached:
            localization_dir.mkdir(parents=True, exist_ok=True)

        # Process localization evidence
        click.echo("Fetching and processing localization data...")
        click.echo(
            "  Using local HPA subcellular location TSV (cache-only)..."
            if reprocess_cached
            else "  Downloading HPA subcellular location data (~10MB)..."
        )
        click.echo("  Cross-referencing curated ciliary/centrosomal compendia...")

        try:
            df = process_localization_evidence(
                gene_ids=gene_ids,
                gene_symbol_map=gene_symbol_map,
                cache_dir=localization_dir,
                force=force and not reprocess_cached,
                cache_only=reprocess_cached,
            )
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process localization evidence")
            sys.exit(1)

        click.echo()
        provenance.record_step('process_localization_evidence', {
            'total_genes': len(df),
            'mode': 'raw_local_reprocess' if reprocess_cached else 'download_or_cached_fetch',
            'reprocess_cached': reprocess_cached,
            'source_path': str(hpa_path),
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        try:
            localization_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description="HPA localization with curated ciliary/centrosomal compendium cross-references"
            )
            click.echo(click.style(
                f"  Saved to 'subcellular_localization' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load localization data to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = localization_dir / "subcellular.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        experimental = df.filter(df['evidence_type'] == 'experimental').height
        curated_compendium = df.filter(df['evidence_type'] == 'curated_compendium').height
        computational = df.filter(df['evidence_type'] == 'computational').height
        both = df.filter(
            (df['evidence_type'] == 'mixed') | (df['evidence_type'] == 'both')
        ).height
        cilia_localized = df.filter(df['cilia_proximity_score'] > 0.5).height

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {len(df)}")
        click.echo(f"  Experimental evidence: {experimental}")
        click.echo(f"  Curated compendium evidence: {curated_compendium}")
        click.echo(f"  Computational evidence: {computational}")
        click.echo(f"  Both: {both}")
        click.echo(f"  Cilia-localized (proximity > 0.5): {cilia_localized}")
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Localization evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()


@evidence.command('protein')
@click.option(
    '--force',
    is_flag=True,
    help='Reprocess data even if checkpoint exists'
)
@click.pass_context
def protein(ctx, force):
    """Fetch and load protein features from UniProt/InterPro.

    Extracts protein length, domain composition, coiled-coil regions,
    transmembrane domains, and cilia-associated motifs. Computes normalized
    composite protein score (0-1 range).

    Supports checkpoint-restart: skips processing if data already exists
    in DuckDB (use --force to re-run).

    Examples:

        # First run: fetch, process, and load
        usher-pipeline evidence protein

        # Force re-fetch and reprocess
        usher-pipeline evidence protein --force
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Protein Features Evidence ===", bold=True))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('protein_features')

        if has_checkpoint and not force:
            click.echo(click.style(
                "Protein features checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('protein_features')
            if df is not None:
                total_genes = len(df)
                with_uniprot = df.filter(df['uniprot_id'].is_not_null()).height
                cilia_domains = df.filter(df['has_cilia_domain'] == True).height
                scaffold_domains = df.filter(df['scaffold_adaptor_domain'] == True).height
                coiled_coils = df.filter(df['coiled_coil'] == True).height

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo(f"  With UniProt data: {with_uniprot}")
                click.echo(f"  With cilia domains: {cilia_domains}")
                click.echo(f"  With scaffold domains: {scaffold_domains}")
                click.echo(f"  With coiled-coils: {coiled_coils}")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Load gene universe for gene IDs and UniProt mappings
        click.echo("Loading gene universe...")
        gene_universe = store.load_dataframe('gene_universe')
        if gene_universe is None:
            click.echo(click.style(
                "Error: gene_universe not found. Run 'usher-pipeline setup gene-universe' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        gene_ids = gene_universe.select("gene_id").to_series().to_list()
        click.echo(click.style(
            f"  Loaded {len(gene_ids)} genes from gene_universe",
            fg='green'
        ))
        click.echo()

        # Process protein evidence
        click.echo("Processing protein features...")
        click.echo("  Fetching from UniProt and InterPro APIs...")
        click.echo("  (This may take several minutes depending on API rate limits)")

        try:
            df = process_protein_evidence(
                gene_ids=gene_ids,
                uniprot_mapping=gene_universe,
            )
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process protein features")
            sys.exit(1)

        click.echo()
        provenance.record_step('process_protein_features', {
            'total_genes': len(df),
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        protein_dir = Path(config.data_dir) / "protein"
        protein_dir.mkdir(parents=True, exist_ok=True)

        try:
            protein_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description="Protein features from UniProt/InterPro with domain composition and cilia motif detection"
            )
            click.echo(click.style(
                f"  Saved to 'protein_features' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load protein features to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = protein_dir / "features.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        total_genes = len(df)
        with_uniprot = df.filter(df['uniprot_id'].is_not_null()).height
        cilia_domains = df.filter(df['has_cilia_domain'] == True).height
        scaffold_domains = df.filter(df['scaffold_adaptor_domain'] == True).height
        coiled_coils = df.filter(df['coiled_coil'] == True).height

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {total_genes}")
        click.echo(f"  With UniProt data: {with_uniprot}")
        click.echo(f"  With cilia domains: {cilia_domains}")
        click.echo(f"  With scaffold domains: {scaffold_domains}")
        click.echo(f"  With coiled-coils: {coiled_coils}")
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Protein evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()


@evidence.command('animal-models')
@click.option(
    '--force',
    is_flag=True,
    help='Reprocess data even if checkpoint exists'
)
@click.option(
    '--derived-cache',
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help='Explicit donor DuckDB for exact-ID derived-cache migration (no raw rerun or network access)',
)
@click.pass_context
def animal_models(ctx, force, derived_cache):
    """Fetch and load animal model phenotype evidence.

    Retrieves knockout/perturbation phenotypes from MGI (mouse), ZFIN (zebrafish),
    and IMPC, maps human genes to orthologs with confidence scoring, filters for
    sensory/cilia-relevant phenotypes, and scores evidence.

    Supports checkpoint-restart: skips processing if data already exists
    in DuckDB (use --force to re-run).

    Examples:

        # First run: fetch, process, and load
        usher-pipeline evidence animal-models

        # Force reprocessing
        usher-pipeline evidence animal-models --force
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Animal Model Phenotype Evidence ===", bold=True))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        if force and derived_cache is not None:
            raise click.ClickException(
                "--force and --derived-cache are mutually exclusive; derived-cache "
                "migration is read-only with respect to its donor and never fetches"
            )

        if derived_cache is not None:
            gene_universe = store.load_dataframe('gene_universe')
            if gene_universe is None or gene_universe.height == 0:
                raise click.ClickException(
                    "gene_universe table not found. Run cache-only setup first."
                )
            click.echo("Migrating animal-model evidence from the local donor cache by exact stable Ensembl ID...")
            df, audit, migration = reindex_animal_models_from_donor(
                derived_cache,
                gene_universe,
                provenance=provenance,
            )
            audit_path = write_derived_cache_audit(
                audit,
                Path(config.data_dir) / "report" / "derived_cache_animal_model_mapping.tsv",
            )
            animal_models_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description="Animal-model derived-cache migration; exact-ID donor reuse with recomputed scores",
            )
            animal_models_dir = Path(config.data_dir) / "animal_models"
            provenance.save_sidecar(animal_models_dir / "phenotypes.provenance.json")
            click.echo(click.style(
                f"  Derived-cache result: {df.height} genes; audit: {audit_path}",
                fg='green',
            ))
            click.echo(f"  Donor SHA-256: {migration['source_artifact_hash']}")
            click.echo(f"  Rogue donor IDs rejected: {migration['rogue_id_count']}")
            click.echo(f"  Duplicate IDs merged: {migration['merged_duplicate_id_count']}")
            click.echo("  Raw-source coverage: incomplete (derived_cache_reuse; not a raw rerun)")
            return

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('animal_model_phenotypes')

        if has_checkpoint and not force:
            click.echo(click.style(
                "Animal model phenotypes checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('animal_model_phenotypes')
            if df is not None:
                total_genes = len(df)
                with_mouse = df.filter(df['mouse_ortholog'].is_not_null()).height
                with_zebrafish = df.filter(df['zebrafish_ortholog'].is_not_null()).height
                with_sensory = df.filter(df['sensory_phenotype_count'].is_not_null()).height

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo(f"  With mouse ortholog: {with_mouse}")
                click.echo(f"  With zebrafish ortholog: {with_zebrafish}")
                click.echo(f"  With sensory phenotypes: {with_sensory}")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Load gene universe (need gene_ids)
        click.echo("Loading gene universe from DuckDB...")
        gene_universe = store.load_dataframe('gene_universe')

        if gene_universe is None or gene_universe.height == 0:
            click.echo(click.style(
                "Error: gene_universe table not found. Run 'usher-pipeline setup' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        gene_ids = gene_universe.select("gene_id").to_series().to_list()

        click.echo(click.style(
            f"  Loaded {len(gene_ids)} genes",
            fg='green'
        ))
        click.echo()

        # Process animal model evidence
        click.echo("Fetching and processing animal model data...")
        click.echo("  This may take several minutes (HCOP, MGI, ZFIN, IMPC downloads)...")

        try:
            df = process_animal_model_evidence(gene_ids=gene_ids)
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process animal model evidence")
            sys.exit(1)

        click.echo()
        provenance.record_step('process_animal_model_evidence', {
            'total_genes': len(df),
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        animal_models_dir = Path(config.data_dir) / "animal_models"
        animal_models_dir.mkdir(parents=True, exist_ok=True)

        try:
            animal_models_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description="Animal model phenotypes from MGI, ZFIN, and IMPC with ortholog confidence scoring"
            )
            click.echo(click.style(
                f"  Saved to 'animal_model_phenotypes' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load animal model data to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = animal_models_dir / "phenotypes.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        with_mouse = df.filter(df['mouse_ortholog'].is_not_null()).height
        with_zebrafish = df.filter(df['zebrafish_ortholog'].is_not_null()).height
        with_sensory = df.filter(df['sensory_phenotype_count'].is_not_null()).height

        # Top scoring genes
        top_genes = df.filter(df['animal_model_score_normalized'].is_not_null()).sort(
            'animal_model_score_normalized', descending=True
        ).head(10).select(['gene_id', 'sensory_phenotype_count', 'animal_model_score_normalized'])

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {len(df)}")
        click.echo(f"  With mouse ortholog: {with_mouse}")
        click.echo(f"  With zebrafish ortholog: {with_zebrafish}")
        click.echo(f"  With sensory phenotypes: {with_sensory}")
        click.echo()
        click.echo("Top 10 scoring genes:")
        for row in top_genes.iter_rows(named=True):
            click.echo(f"  {row['gene_id']}: {row['animal_model_score_normalized']:.3f} ({row['sensory_phenotype_count']} phenotypes)")
        click.echo()
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Animal model evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()


@evidence.command('literature')
@click.option(
    '--force',
    is_flag=True,
    help='Re-download bulk files and reprocess'
)
@click.option(
    '--email',
    required=True,
    help='Email for NCBI E-utilities (required by PubMed API)'
)
@click.option(
    '--api-key',
    default=None,
    help='NCBI API key (optional, speeds up batch context queries)'
)
@click.option(
    '--reprocess-cached',
    is_flag=True,
    help='Recompute from local literature bulk/context caches without downloading or querying PubMed'
)
@click.pass_context
def literature(ctx, force, email, api_key, reprocess_cached):
    """Fetch and load literature evidence using bulk data.

    Downloads gene2pubmed (~150MB) and gene_info (~20MB) from NCBI,
    runs 6 batch PubMed queries for context classification (cilia, sensory,
    cytoskeleton, cell polarity, experimental, HTS), then counts per-gene
    intersections locally. Classifies evidence tiers and computes
    quality-weighted scores with bias mitigation.

    Runtime: ~5-10 minutes.

    Examples:

        usher-pipeline evidence literature --email you@example.com

        usher-pipeline evidence literature --email you@example.com --api-key YOUR_KEY

        usher-pipeline evidence literature --email you@example.com --force
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Literature Evidence (Bulk) ===", bold=True))
    click.echo()

    click.echo(click.style("  Bulk mode: gene2pubmed + batch MeSH queries", fg='cyan'))
    click.echo(click.style("  Estimated runtime: ~5-10 minutes", fg='cyan'))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        if force and reprocess_cached:
            raise click.ClickException(
                "--force and --reprocess-cached are mutually exclusive: "
                "cache-only raw reprocessing cannot refresh source files or query PubMed"
            )

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('literature_evidence')

        if has_checkpoint and not force and not reprocess_cached:
            click.echo(click.style(
                "Literature evidence checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('literature_evidence')
            if df is not None:
                total_genes = len(df)
                tier_counts = (
                    df.group_by("evidence_tier")
                    .agg(pl.len().alias("count"))
                    .sort("count", descending=True)
                )

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo("Evidence Tier Distribution:")
                for row in tier_counts.to_dicts():
                    tier = row["evidence_tier"]
                    count = row["count"]
                    pct = (count / total_genes) * 100
                    click.echo(f"  {tier}: {count} ({pct:.1f}%)")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Load gene universe (need gene_ids and gene_symbols)
        click.echo("Loading gene universe from DuckDB...")
        gene_universe = store.load_dataframe('gene_universe')

        if gene_universe is None or gene_universe.height == 0:
            click.echo(click.style(
                "Error: gene_universe table not found. Run 'usher-pipeline setup' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        gene_ids = gene_universe.select("gene_id").to_series().to_list()
        gene_symbol_map = gene_universe.select(["gene_id", "gene_symbol"]).filter(
            gene_universe["gene_symbol"].is_not_null()
        )

        click.echo(click.style(
            f"  Loaded {len(gene_ids)} genes ({gene_symbol_map.height} with symbols)",
            fg='green'
        ))
        click.echo()

        # Process literature evidence (bulk fetch + transform)
        click.echo("Fetching bulk literature evidence...")
        click.echo(f"  Email: {email}")
        click.echo()

        try:
            df = process_literature_evidence(
                gene_ids=gene_ids,
                gene_symbol_map=gene_symbol_map,
                email=email,
                data_dir=config.data_dir,
                api_key=api_key,
                force=force,
                cache_only=reprocess_cached,
            )
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process literature evidence")
            sys.exit(1)

        click.echo()
        provenance.record_step('process_literature_evidence', {
            'total_genes': len(df),
            'email': email,
            'has_api_key': api_key is not None,
            'mode': 'raw_local_reprocess' if reprocess_cached else 'bulk',
            'processing_mode': 'bulk',
            'reprocess_cached': reprocess_cached,
            'source_mode': 'raw_local_reprocess' if reprocess_cached else 'download_or_cached_fetch',
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        literature_dir = Path(config.data_dir) / "literature"
        literature_dir.mkdir(parents=True, exist_ok=True)

        try:
            literature_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                description="Bulk literature evidence (gene2pubmed + MeSH batch queries)"
            )
            click.echo(click.style(
                f"  Saved to 'literature_evidence' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load literature evidence to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = literature_dir / "pubmed.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        tier_counts = (
            df.group_by("evidence_tier")
            .agg(pl.len().alias("count"))
            .sort("count", descending=True)
        )

        genes_with_evidence = df.filter(
            df["evidence_tier"].is_in(["direct_experimental", "functional_mention", "hts_hit"])
        ).height

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {len(df)}")
        click.echo("Evidence Tier Distribution:")
        for row in tier_counts.to_dicts():
            tier = row["evidence_tier"]
            count = row["count"]
            pct = (count / len(df)) * 100
            click.echo(f"  {tier}: {count} ({pct:.1f}%)")
        click.echo()
        click.echo(f"Genes with Evidence (direct/functional/hts): {genes_with_evidence}")
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Literature evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()


@evidence.command('expression')
@click.option(
    '--force',
    is_flag=True,
    help='Re-download and reprocess data even if checkpoint exists'
)
@click.option(
    '--skip-cellxgene',
    is_flag=True,
    help='Skip CellxGene single-cell data (requires optional cellxgene-census dependency)'
)
@click.option(
    '--reprocess-cached',
    is_flag=True,
    help='Recompute the layer from existing local source files/caches without downloading'
)
@click.pass_context
def expression_cmd(ctx, force, skip_cellxgene, reprocess_cached):
    """Fetch and load tissue expression evidence (HPA, GTEx, CellxGene).

    Retrieves expression data from HPA (Human Protein Atlas), GTEx (tissue-level RNA-seq),
    and optionally CellxGene (single-cell RNA-seq for photoreceptor/hair cells). Computes
    restricted-panel tissue specificity (Tau index) and Usher-panel contrast scores.

    Supports checkpoint-restart: skips processing if data already exists
    in DuckDB (use --force to re-run).

    NOTE: CellxGene support requires optional dependency. Install with:
    pip install 'usher-pipeline[expression]'
    Or use --skip-cellxgene flag to skip single-cell data.

    Examples:

        # First run: download, process, and load (skip CellxGene)
        usher-pipeline evidence expression --skip-cellxgene

        # With CellxGene support (requires optional dependency)
        usher-pipeline evidence expression

        # Force re-download and reprocess
        usher-pipeline evidence expression --force --skip-cellxgene
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Tissue Expression Evidence ===", bold=True))
    click.echo()

    store = None
    try:
        # Load config
        click.echo("Loading configuration...")
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo()

        # Initialize storage and provenance
        click.echo("Initializing storage and provenance tracking...")
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        expression_dir = Path(config.data_dir) / "expression"
        if force and reprocess_cached:
            raise click.ClickException(
                "--force and --reprocess-cached are mutually exclusive: "
                "cache-only reprocessing cannot refresh source files"
            )

        # Check checkpoint.  --reprocess-cached is useful when transformation
        # logic changed but the downloaded source files are already present.
        has_checkpoint = store.has_checkpoint('tissue_expression')
        existing_expression = (
            store.load_dataframe('tissue_expression') if has_checkpoint else None
        )
        legacy_checkpoint = bool(
            existing_expression is not None
            and (
                any(column in existing_expression.columns for column in LEGACY_HPA_TPM_COLUMNS)
                or any(
                    column in existing_expression.columns
                    for column in LEGACY_EXPRESSION_CONTRACT_COLUMNS
                )
                or "gene_symbol" not in existing_expression.columns
                or RESTRICTED_TAU_COLUMN not in existing_expression.columns
                or RESTRICTED_ENRICHMENT_COLUMN not in existing_expression.columns
            )
        )

        # Automatic legacy migration is cache-only only when --force was not
        # requested. Explicit --reprocess-cached remains strict cache-only.
        cache_only = reprocess_cached or (legacy_checkpoint and not force)
        if cache_only:
            if legacy_checkpoint:
                click.echo(click.style(
                    "Legacy expression checkpoint detected; reprocessing cached raw sources to migrate the expression schema.",
                    fg='yellow'
                ))
            click.echo("Checking required local expression caches...")
            validate_expression_cache(
                expression_dir,
                census_version=config.versions.cellxgene_census_version,
                require_cellxgene=not skip_cellxgene,
            )
            click.echo(click.style("  Cache-only preflight passed", fg='green'))
            click.echo()
        elif legacy_checkpoint and force:
            click.echo(click.style(
                "Legacy expression checkpoint detected; --force refreshes source files before migration.",
                fg='yellow'
            ))

        if has_checkpoint and not legacy_checkpoint and not force and not reprocess_cached:
            click.echo(click.style(
                "Tissue expression checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = existing_expression
            if df is not None:
                total_genes = len(df)
                retina_columns = [
                    pl.col(column) > 0
                    for column in RETINA_EVIDENCE_COLUMNS
                    if column in df.columns
                ]
                retina_expr = df.filter(
                    pl.any_horizontal(retina_columns)
                    if retina_columns else pl.lit(False)
                ).height
                inner_ear_expr = (
                    df.filter(
                        pl.col('cellxgene_hair_cell_expr').cast(
                            pl.Float64, strict=False
                        ) > 0
                    ).height
                    if 'cellxgene_hair_cell_expr' in df.columns else 0
                )
                mean_tau = df.select(RESTRICTED_TAU_COLUMN).mean().item()

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo(f"  With retina expression: {retina_expr}")
                click.echo(f"  With inner ear expression: {inner_ear_expr}")
                click.echo(f"  Mean Tau specificity: {mean_tau:.3f}" if mean_tau is not None else "  Mean Tau specificity: N/A")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Evidence layer ready (used existing checkpoint)", fg='green'))
                return

        # Load gene universe (need gene_ids)
        click.echo("Loading gene universe from DuckDB...")
        gene_universe = store.load_dataframe('gene_universe')

        if gene_universe is None or gene_universe.height == 0:
            click.echo(click.style(
                "Error: gene_universe table not found. Run 'usher-pipeline setup' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        gene_ids = gene_universe.select("gene_id").to_series().to_list()

        click.echo(click.style(
            f"  Loaded {len(gene_ids)} genes",
            fg='green'
        ))
        click.echo()

        # Create the cache directory only for a normal fetch. Cache-only
        # preflight above must not create a path or trigger a source fallback.
        if not cache_only:
            expression_dir.mkdir(parents=True, exist_ok=True)

        # Process expression evidence
        click.echo("Fetching and processing expression data...")
        if cache_only:
            click.echo("  Using cached HPA and GTEx source files (cache-only)")
        else:
            click.echo("  Downloading HPA normal tissue data (~30MB)...")
            click.echo("  Downloading GTEx median expression data (~20MB)...")
        if not skip_cellxgene and cache_only:
            click.echo("  Using cached CellxGene census result (cache-only)")
        elif not skip_cellxgene:
            click.echo("  Querying CellxGene census for single-cell data...")
        else:
            click.echo("  Skipping CellxGene (--skip-cellxgene flag)")

        try:
            # Build gene_symbol_map for HPA merge (HPA uses gene_symbol, not gene_id)
            gene_symbol_map = gene_universe.select(["gene_id", "gene_symbol"])

            cellxgene_metadata = {}
            df = process_expression_evidence(
                gene_ids=gene_ids,
                cache_dir=expression_dir,
                # --force refreshes source files; --reprocess-cached only
                # recomputes from the local files/caches.
                force=force and not cache_only,
                cache_only=cache_only,
                skip_cellxgene=skip_cellxgene,
                gene_symbol_map=gene_symbol_map,
                census_version=config.versions.cellxgene_census_version,
                cellxgene_metadata=cellxgene_metadata,
            )
            click.echo(click.style(
                f"  Processed {len(df)} genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error processing: {e}", fg='red'), err=True)
            logger.exception("Failed to process expression evidence")
            sys.exit(1)

        click.echo()
        source_metadata = expression_source_metadata(
            expression_dir,
            df,
            census_version=config.versions.cellxgene_census_version,
            cellxgene_metadata=cellxgene_metadata,
        )
        provenance.record_step('process_expression_evidence', {
            'total_genes': len(df),
            'schema_version': EXPRESSION_SCHEMA_VERSION,
            'mode': 'raw_local_reprocess' if reprocess_cached else 'download_or_cached_fetch',
            'skip_cellxgene': skip_cellxgene,
            'cellxgene_census_version': config.versions.cellxgene_census_version,
            'reprocess_cached': reprocess_cached,
            'source_metadata': source_metadata,
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        try:
            expression_load_to_duckdb(
                df=df,
                store=store,
                provenance=provenance,
                source_metadata=source_metadata,
                description="HPA, GTEx, and CellxGene tissue expression with Tau specificity and Usher enrichment scores"
            )
            click.echo(click.style(
                f"  Saved to 'tissue_expression' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading: {e}", fg='red'), err=True)
            logger.exception("Failed to load expression evidence to DuckDB")
            sys.exit(1)

        click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = expression_dir / "tissue.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display summary
        retina_columns = [
            pl.col(column) > 0
            for column in RETINA_EVIDENCE_COLUMNS
            if column in df.columns
        ]
        retina_expr = df.filter(
            pl.any_horizontal(retina_columns)
            if retina_columns else pl.lit(False)
        ).height
        inner_ear_expr = (
            df.filter(
                pl.col('cellxgene_hair_cell_expr').cast(
                    pl.Float64, strict=False
                ) > 0
            ).height
            if 'cellxgene_hair_cell_expr' in df.columns else 0
        )
        mean_tau = df.select(RESTRICTED_TAU_COLUMN).mean().item()

        # Top enriched genes
        top_genes = df.filter(df[RESTRICTED_ENRICHMENT_COLUMN].is_not_null()).sort(
            RESTRICTED_ENRICHMENT_COLUMN, descending=True
        ).head(10).select(['gene_id', RESTRICTED_ENRICHMENT_COLUMN, RESTRICTED_TAU_COLUMN, 'expression_score_normalized'])

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {len(df)}")
        click.echo(f"  With retina expression: {retina_expr}")
        click.echo(f"  With inner ear expression: {inner_ear_expr}")
        click.echo(f"  Mean Tau specificity: {mean_tau:.3f}" if mean_tau is not None else "  Mean Tau specificity: N/A")
        click.echo()
        click.echo("Top 10 enriched genes:")
        for row in top_genes.iter_rows(named=True):
            tau_str = f"{row[RESTRICTED_TAU_COLUMN]:.3f}" if row[RESTRICTED_TAU_COLUMN] is not None else "N/A"
            expr_str = f"{row['expression_score_normalized']:.3f}" if row['expression_score_normalized'] is not None else "N/A"
            click.echo(f"  {row['gene_id']}: restricted_contrast={row[RESTRICTED_ENRICHMENT_COLUMN]:.2f}, tau={tau_str}, score={expr_str}")
        click.echo()
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Expression evidence layer complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Evidence command failed: {e}", fg='red'), err=True)
        logger.exception("Evidence command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()

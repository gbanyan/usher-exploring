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
import structlog

from usher_pipeline.config.loader import load_config
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker
from usher_pipeline.evidence.gnomad import (
    download_constraint_metrics,
    process_gnomad_constraint,
    load_to_duckdb,
    GNOMAD_CONSTRAINT_URL,
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
def gnomad(ctx, force, url, min_depth, min_cds_pct):
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

        # Check checkpoint
        has_checkpoint = store.has_checkpoint('gnomad_constraint')

        if has_checkpoint and not force:
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

        # Download gnomAD constraint metrics
        click.echo("Downloading gnomAD constraint metrics...")
        click.echo(f"  URL: {url}")
        click.echo(f"  Version: {config.versions.gnomad_version}")

        gnomad_dir = Path(config.data_dir) / "gnomad"
        gnomad_dir.mkdir(parents=True, exist_ok=True)
        tsv_path = gnomad_dir / "constraint_metrics.tsv"

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
        })

        # Load to DuckDB
        click.echo("Loading to DuckDB...")

        try:
            load_to_duckdb(
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
        measured = df.filter(df['quality_flag'] == 'measured').height
        incomplete = df.filter(df['quality_flag'] == 'incomplete_coverage').height
        no_data = df.filter(df['quality_flag'] == 'no_data').height

        click.echo(click.style("=== Summary ===", bold=True))
        click.echo(f"Total Genes: {len(df)}")
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

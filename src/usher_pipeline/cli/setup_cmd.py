"""Setup command: Initialize pipeline data infrastructure.

Orchestrates the full setup flow:
1. Load config
2. Create PipelineStore and ProvenanceTracker
3. Check for existing checkpoints
4. Fetch gene universe from Ensembl/mygene
5. Map gene IDs (Ensembl -> HGNC + UniProt)
6. Validate mapping quality
7. Save to DuckDB with provenance
"""

import logging
import sys
from pathlib import Path

import click
import polars as pl

from usher_pipeline.config.loader import load_config
from usher_pipeline.gene_mapping import (
    fetch_protein_coding_genes,
    validate_gene_universe,
    GeneMapper,
    MappingValidator,
)
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker

logger = logging.getLogger(__name__)


@click.command('setup')
@click.option(
    '--force',
    is_flag=True,
    help='Re-run setup even if checkpoints exist (re-fetches all data)'
)
@click.pass_context
def setup(ctx, force):
    """Initialize pipeline data infrastructure.

    Fetches gene universe, maps IDs, validates results, and saves to DuckDB.
    Supports checkpoint-restart: skips expensive operations if data exists.
    """
    config_path = ctx.obj['config_path']
    click.echo(click.style("=== Usher Pipeline Setup ===", bold=True))
    click.echo()

    try:
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

        # 3. Check checkpoint
        has_checkpoint = store.has_checkpoint('gene_universe')

        if has_checkpoint and not force:
            click.echo(click.style(
                "Gene universe checkpoint exists. Skipping fetch (use --force to re-fetch).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for validation display
            df = store.load_dataframe('gene_universe')
            if df is not None:
                gene_count = len(df)
                click.echo(f"Loaded {gene_count} genes from checkpoint")
                click.echo()

                # Display summary
                click.echo(click.style("=== Setup Summary ===", bold=True))
                click.echo(f"Gene Count: {gene_count}")
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Setup complete (used existing checkpoint)", fg='green'))
                return

        # 4. Fetch gene universe
        click.echo("Fetching protein-coding genes from mygene...")
        click.echo(f"  Ensembl Release: {config.versions.ensembl_release}")

        try:
            gene_universe = fetch_protein_coding_genes(
                ensembl_release=config.versions.ensembl_release
            )
            click.echo(click.style(
                f"  Fetched {len(gene_universe)} protein-coding genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error fetching genes: {e}", fg='red'), err=True)
            logger.exception("Failed to fetch gene universe")
            sys.exit(1)

        click.echo()

        # 5. Validate gene universe
        click.echo("Validating gene universe...")
        universe_validation = validate_gene_universe(gene_universe)

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
            'gene_count': len(gene_universe),
            'ensembl_release': config.versions.ensembl_release
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
            'ensembl_id': [r.ensembl_id for r in mapping_results],
            'hgnc_symbol': [r.hgnc_symbol for r in mapping_results],
            'uniprot_accession': [r.uniprot_accession for r in mapping_results],
        })

        store.save_dataframe(
            table_name='gene_universe',
            df=df,
            description=f"Protein-coding genes from Ensembl {config.versions.ensembl_release} with HGNC/UniProt mapping"
        )
        click.echo(click.style(f"  Saved {len(df)} genes to 'gene_universe' table", fg='green'))
        click.echo()

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

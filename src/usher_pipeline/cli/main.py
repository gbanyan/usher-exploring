"""Main CLI entry point for usher-pipeline.

Provides command group with global options and subcommands for pipeline operations.
"""

import logging
from pathlib import Path

import click

from usher_pipeline import __version__
from usher_pipeline.config.loader import load_config
from usher_pipeline.cli.setup_cmd import setup
from usher_pipeline.cli.evidence_cmd import evidence
from usher_pipeline.cli.score_cmd import score
from usher_pipeline.cli.report_cmd import report
from usher_pipeline.cli.validate_cmd import validate


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@click.group()
@click.option(
    '--config',
    type=click.Path(exists=True, path_type=Path),
    default='config/default.yaml',
    help='Path to pipeline configuration YAML file'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Enable verbose logging (DEBUG level)'
)
@click.pass_context
def cli(ctx, config, verbose):
    """Usher-pipeline: Reproducible pipeline for discovering under-studied cilia/Usher candidate genes.

    Provides data infrastructure, gene ID mapping, evidence layer aggregation,
    and scoring for candidate gene prioritization.
    """
    # Set up context
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    ctx.obj['verbose'] = verbose

    # Set logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Verbose logging enabled")


@cli.command()
@click.pass_context
def info(ctx):
    """Display pipeline information and configuration summary."""
    config_path = ctx.obj['config_path']

    click.echo(f"Usher Pipeline v{__version__}")
    click.echo(f"Config: {config_path}")
    click.echo()

    try:
        config = load_config(config_path)

        # Display config hash
        config_hash = config.config_hash()
        click.echo(f"Config Hash: {config_hash[:16]}...")
        click.echo()

        # Display data source versions
        click.echo(click.style("Data Source Versions:", bold=True))
        click.echo(f"  Ensembl Release: {config.versions.ensembl_release}")
        click.echo(f"  gnomAD Version:  {config.versions.gnomad_version}")
        click.echo(f"  GTEx Version:    {config.versions.gtex_version}")
        click.echo(f"  HPA Version:     {config.versions.hpa_version}")
        click.echo()

        # Display paths
        click.echo(click.style("Paths:", bold=True))
        click.echo(f"  Data Directory: {config.data_dir}")
        click.echo(f"  Cache Directory: {config.cache_dir}")
        click.echo(f"  DuckDB Path: {config.duckdb_path}")
        click.echo()

        # Display API config
        click.echo(click.style("API Configuration:", bold=True))
        click.echo(f"  Rate Limit: {config.api.rate_limit_per_second} req/s")
        click.echo(f"  Max Retries: {config.api.max_retries}")
        click.echo(f"  Cache TTL: {config.api.cache_ttl_seconds}s")
        click.echo(f"  Timeout: {config.api.timeout_seconds}s")

    except Exception as e:
        click.echo(click.style(f"Error loading config: {e}", fg='red'), err=True)
        ctx.exit(1)


# Register commands
cli.add_command(setup)
cli.add_command(evidence)
cli.add_command(score)
cli.add_command(report)
cli.add_command(validate)


if __name__ == '__main__':
    cli()

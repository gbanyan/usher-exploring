"""Report command: Generate tiered candidate lists, visualizations, and reproducibility reports.

Orchestrates the full output pipeline:
- Reads scored_genes from DuckDB
- Applies tiering and evidence summary
- Writes TSV+Parquet output
- Generates visualizations
- Creates reproducibility reports
"""

import logging
import sys
from pathlib import Path

import click

from usher_pipeline.config.loader import load_config
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker
from usher_pipeline.output import (
    assign_tiers,
    add_evidence_summary,
    write_candidate_output,
    generate_all_plots,
    generate_reproducibility_report,
)

logger = logging.getLogger(__name__)


@click.command('report')
@click.option(
    '--output-dir',
    type=click.Path(path_type=Path),
    default=None,
    help='Output directory (default: {data_dir}/report)'
)
@click.option(
    '--force',
    is_flag=True,
    help='Overwrite existing report files'
)
@click.option(
    '--skip-viz',
    is_flag=True,
    help='Skip visualization generation'
)
@click.option(
    '--skip-report',
    is_flag=True,
    help='Skip reproducibility report generation'
)
@click.option(
    '--high-threshold',
    type=float,
    default=0.7,
    help='Minimum score for HIGH tier (default: 0.7)'
)
@click.option(
    '--medium-threshold',
    type=float,
    default=0.4,
    help='Minimum score for MEDIUM tier (default: 0.4)'
)
@click.option(
    '--low-threshold',
    type=float,
    default=0.2,
    help='Minimum score for LOW tier (default: 0.2)'
)
@click.option(
    '--min-evidence-high',
    type=int,
    default=3,
    help='Minimum evidence layers for HIGH tier (default: 3)'
)
@click.option(
    '--min-evidence-medium',
    type=int,
    default=2,
    help='Minimum evidence layers for MEDIUM tier (default: 2)'
)
@click.pass_context
def report(ctx, output_dir, force, skip_viz, skip_report,
           high_threshold, medium_threshold, low_threshold,
           min_evidence_high, min_evidence_medium):
    """Generate tiered candidate lists with visualizations and reproducibility reports.

    Reads scored_genes from DuckDB, applies confidence tier classification,
    adds evidence summaries, writes dual-format output (TSV + Parquet),
    generates plots, and creates reproducibility documentation.

    Run this after 'usher-pipeline score' to produce final deliverables.

    Pipeline steps:
    1. Load scored genes from DuckDB
    2. Apply confidence tier classification (HIGH/MEDIUM/LOW)
    3. Add evidence summary (supporting layers and gaps)
    4. Write TSV and Parquet outputs with provenance
    5. Generate visualizations (unless --skip-viz)
    6. Create reproducibility reports (unless --skip-report)

    Examples:

        # Generate full report with defaults
        usher-pipeline report

        # Custom output directory
        usher-pipeline report --output-dir /path/to/output

        # Skip visualizations (faster)
        usher-pipeline report --skip-viz

        # Custom tier thresholds
        usher-pipeline report --high-threshold 0.8 --medium-threshold 0.5
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Candidate Report Generation ===", bold=True))
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

        # Check scored_genes exists
        has_scored_genes = store.has_checkpoint('scored_genes')

        if not has_scored_genes:
            click.echo(click.style(
                "Error: scored_genes table not found. Run 'usher-pipeline score' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        # Set output directory
        if output_dir is None:
            output_dir = Path(config.data_dir) / "report"

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Check for existing files
        candidate_tsv = output_dir / "candidates.tsv"
        candidate_parquet = output_dir / "candidates.parquet"

        if candidate_tsv.exists() and not force:
            click.echo(click.style(
                f"Warning: Output files already exist at {output_dir}",
                fg='yellow'
            ))
            click.echo(click.style(
                "  Use --force to overwrite existing files.",
                fg='yellow'
            ))
            click.echo()
            return

        # Step 1: Load scored genes
        click.echo(click.style("Step 1: Loading scored genes from DuckDB...", bold=True))

        try:
            scored_df = store.load_dataframe('scored_genes')
            total_scored = scored_df.height
            click.echo(click.style(
                f"  Loaded {total_scored} scored genes",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading scored genes: {e}", fg='red'), err=True)
            logger.exception("Failed to load scored_genes")
            sys.exit(1)

        click.echo()
        provenance.record_step('load_scored_genes', {
            'total_genes': total_scored,
        })

        # Step 2: Build tier thresholds
        click.echo(click.style("Step 2: Configuring tier thresholds...", bold=True))
        tier_thresholds = {
            "high": {
                "score": high_threshold,
                "evidence_count": min_evidence_high
            },
            "medium": {
                "score": medium_threshold,
                "evidence_count": min_evidence_medium
            },
            "low": {
                "score": low_threshold
            }
        }

        click.echo(f"  HIGH:   score >= {high_threshold}, evidence >= {min_evidence_high} layers")
        click.echo(f"  MEDIUM: score >= {medium_threshold}, evidence >= {min_evidence_medium} layers")
        click.echo(f"  LOW:    score >= {low_threshold}")
        click.echo()

        # Step 3: Apply tiering
        click.echo(click.style("Step 3: Applying tier classification...", bold=True))

        try:
            tiered_df = assign_tiers(scored_df, thresholds=tier_thresholds)

            # Count tiers
            high_count = tiered_df.filter(tiered_df['confidence_tier'] == 'HIGH').height
            medium_count = tiered_df.filter(tiered_df['confidence_tier'] == 'MEDIUM').height
            low_count = tiered_df.filter(tiered_df['confidence_tier'] == 'LOW').height
            total_candidates = tiered_df.height

            click.echo(click.style(
                f"  Classified into tiers: HIGH={high_count}, MEDIUM={medium_count}, LOW={low_count}",
                fg='green'
            ))
            click.echo(f"  Total candidates: {total_candidates} (from {total_scored} scored genes)")
        except Exception as e:
            click.echo(click.style(f"  Error applying tiers: {e}", fg='red'), err=True)
            logger.exception("Failed to apply tier classification")
            sys.exit(1)

        click.echo()
        provenance.record_step('apply_tier_classification', {
            'total_candidates': total_candidates,
            'high_count': high_count,
            'medium_count': medium_count,
            'low_count': low_count,
            'excluded_count': total_scored - total_candidates,
        })

        # Step 4: Add evidence summary
        click.echo(click.style("Step 4: Adding evidence summary...", bold=True))

        try:
            tiered_df = add_evidence_summary(tiered_df)
            click.echo(click.style(
                "  Added supporting_layers and evidence_gaps columns",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error adding evidence summary: {e}", fg='red'), err=True)
            logger.exception("Failed to add evidence summary")
            sys.exit(1)

        click.echo()

        # Step 5: Write dual-format output
        click.echo(click.style("Step 5: Writing candidate output...", bold=True))

        try:
            output_paths = write_candidate_output(
                tiered_df,
                output_dir=output_dir,
                base_filename="candidates"
            )

            click.echo(click.style(
                f"  TSV:        {output_paths['tsv']}",
                fg='green'
            ))
            click.echo(click.style(
                f"  Parquet:    {output_paths['parquet']}",
                fg='green'
            ))
            click.echo(click.style(
                f"  Provenance: {output_paths['provenance']}",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error writing output: {e}", fg='red'), err=True)
            logger.exception("Failed to write candidate output")
            sys.exit(1)

        click.echo()
        provenance.record_step('write_candidate_output', {
            'output_dir': str(output_dir),
            'tsv_path': str(output_paths['tsv']),
            'parquet_path': str(output_paths['parquet']),
        })

        # Step 6: Generate visualizations (unless --skip-viz)
        if not skip_viz:
            click.echo(click.style("Step 6: Generating visualizations...", bold=True))

            plots_dir = output_dir / "plots"
            plots_dir.mkdir(parents=True, exist_ok=True)

            try:
                plot_paths = generate_all_plots(tiered_df, plots_dir)

                for plot_name, plot_path in plot_paths.items():
                    click.echo(click.style(
                        f"  {plot_name}: {plot_path}",
                        fg='green'
                    ))
            except Exception as e:
                click.echo(click.style(f"  Warning: Visualization generation failed: {e}", fg='yellow'))
                logger.exception("Failed to generate visualizations")

            click.echo()
            provenance.record_step('generate_visualizations', {
                'plots_dir': str(plots_dir),
                'plot_count': len(plot_paths) if 'plot_paths' in locals() else 0,
            })
        else:
            click.echo(click.style("Step 6: Skipping visualizations (--skip-viz)", fg='yellow'))
            click.echo()

        # Step 7: Generate reproducibility report (unless --skip-report)
        if not skip_report:
            click.echo(click.style("Step 7: Creating reproducibility report...", bold=True))

            try:
                # Try to load validation result if available
                validation_result = None
                if store.has_checkpoint('validation_results'):
                    try:
                        validation_df = store.load_dataframe('validation_results')
                        if validation_df is not None and validation_df.height > 0:
                            # Convert to dict for report
                            validation_result = validation_df.to_dicts()[0]
                    except Exception:
                        logger.debug("Could not load validation results, continuing without")

                # Generate report
                report_obj = generate_reproducibility_report(
                    config=config,
                    tiered_df=tiered_df,
                    provenance=provenance,
                    validation_result=validation_result
                )

                # Write JSON format
                json_path = output_dir / "reproducibility.json"
                report_obj.to_json(json_path)
                click.echo(click.style(
                    f"  JSON:     {json_path}",
                    fg='green'
                ))

                # Write Markdown format
                md_path = output_dir / "reproducibility.md"
                report_obj.to_markdown(md_path)
                click.echo(click.style(
                    f"  Markdown: {md_path}",
                    fg='green'
                ))

            except Exception as e:
                click.echo(click.style(f"  Warning: Reproducibility report generation failed: {e}", fg='yellow'))
                logger.exception("Failed to generate reproducibility report")

            click.echo()
            provenance.record_step('generate_reproducibility_report', {
                'json_path': str(json_path) if 'json_path' in locals() else None,
                'markdown_path': str(md_path) if 'md_path' in locals() else None,
            })
        else:
            click.echo(click.style("Step 7: Skipping reproducibility report (--skip-report)", fg='yellow'))
            click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        provenance_path = output_dir / "report.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display final summary
        click.echo(click.style("=== Final Summary ===", bold=True))
        click.echo(f"Output Directory: {output_dir}")
        click.echo()
        click.echo("Tier Distribution:")
        click.echo(f"  HIGH:   {high_count} candidates")
        click.echo(f"  MEDIUM: {medium_count} candidates")
        click.echo(f"  LOW:    {low_count} candidates")
        click.echo(f"  Total:  {total_candidates} candidates (from {total_scored} scored genes)")
        click.echo()
        click.echo("Output Files:")
        click.echo(f"  candidates.tsv")
        click.echo(f"  candidates.parquet")
        click.echo(f"  candidates.provenance.yaml")
        if not skip_viz:
            click.echo(f"  plots/score_distribution.png")
            click.echo(f"  plots/layer_contributions.png")
            click.echo(f"  plots/tier_breakdown.png")
        if not skip_report:
            click.echo(f"  reproducibility.json")
            click.echo(f"  reproducibility.md")
        click.echo()
        click.echo(click.style("Report generation complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Report command failed: {e}", fg='red'), err=True)
        logger.exception("Report command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()

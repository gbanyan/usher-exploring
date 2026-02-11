"""Scoring command: Integrate multi-evidence layers and compute composite scores.

Commands for:
- Loading known genes (positive controls)
- Computing composite scores with weighted averaging
- Running quality control checks
- Validating against known gene rankings
"""

import logging
import sys
from pathlib import Path

import click
import structlog

from usher_pipeline.config.loader import load_config
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker
from usher_pipeline.scoring import (
    load_known_genes_to_duckdb,
    compute_composite_scores,
    persist_scored_genes,
    run_qc_checks,
    validate_known_gene_ranking,
    generate_validation_report,
)

logger = logging.getLogger(__name__)


@click.command('score')
@click.option(
    '--force',
    is_flag=True,
    help='Re-run scoring even if scored_genes checkpoint exists'
)
@click.option(
    '--skip-qc',
    is_flag=True,
    help='Skip quality control checks (for faster iteration)'
)
@click.option(
    '--skip-validation',
    is_flag=True,
    help='Skip known gene validation'
)
@click.pass_context
def score(ctx, force, skip_qc, skip_validation):
    """Compute multi-evidence composite scores for all genes.

    Integrates all 6 evidence layers (constraint, expression, annotation,
    localization, animal models, literature) with configurable weights.
    Validates scoring quality via QC checks and known gene rankings.

    Supports checkpoint-restart: skips processing if scored_genes table exists
    (use --force to re-run).

    Pipeline steps:
    1. Load known genes (OMIM Usher + SYSCILIA SCGS) as positive controls
    2. Compute composite scores with NULL-preserving weighted average
    3. Persist scored_genes table with per-layer contributions
    4. Run QC checks (missing data thresholds, outlier detection)
    5. Validate known gene rankings (top quartile threshold)

    Examples:

        # First run: full scoring pipeline
        usher-pipeline score

        # Force re-run
        usher-pipeline score --force

        # Skip QC and validation (faster iteration)
        usher-pipeline score --skip-qc --skip-validation
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Multi-Evidence Scoring Pipeline ===", bold=True))
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
        has_checkpoint = store.has_checkpoint('scored_genes')

        if has_checkpoint and not force:
            click.echo(click.style(
                "scored_genes checkpoint exists. Skipping processing (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Load existing data for summary display
            df = store.load_dataframe('scored_genes')
            if df is not None:
                total_genes = df.height
                genes_with_score = df.filter(df['composite_score'].is_not_null()).height
                mean_score = df.filter(df['composite_score'].is_not_null())['composite_score'].mean()

                # Quality flag distribution
                sufficient = df.filter(df['quality_flag'] == 'sufficient_evidence').height
                moderate = df.filter(df['quality_flag'] == 'moderate_evidence').height
                sparse = df.filter(df['quality_flag'] == 'sparse_evidence').height
                no_evidence = df.filter(df['quality_flag'] == 'no_evidence').height

                click.echo(click.style("=== Summary ===", bold=True))
                click.echo(f"Total Genes: {total_genes}")
                click.echo(f"Genes with scores: {genes_with_score}")
                click.echo(f"Mean composite score: {mean_score:.4f}")
                click.echo()
                click.echo("Quality Flag Distribution:")
                click.echo(f"  Sufficient evidence (>=4 layers): {sufficient}")
                click.echo(f"  Moderate evidence (2-3 layers): {moderate}")
                click.echo(f"  Sparse evidence (1 layer): {sparse}")
                click.echo(f"  No evidence: {no_evidence}")
                click.echo()
                click.echo(f"DuckDB Path: {config.duckdb_path}")
                click.echo()
                click.echo(click.style("Scoring complete (used existing checkpoint)", fg='green'))
                return

        # Validate scoring weights
        click.echo("Validating scoring weights...")
        scoring_weights = config.scoring
        try:
            scoring_weights.validate_sum()
            click.echo(click.style("  Weights validated (sum = 1.0)", fg='green'))
            click.echo(f"    gnomAD:      {scoring_weights.gnomad:.2f}")
            click.echo(f"    Expression:  {scoring_weights.expression:.2f}")
            click.echo(f"    Annotation:  {scoring_weights.annotation:.2f}")
            click.echo(f"    Localization: {scoring_weights.localization:.2f}")
            click.echo(f"    Animal Model: {scoring_weights.animal_model:.2f}")
            click.echo(f"    Literature:   {scoring_weights.literature:.2f}")
        except ValueError as e:
            click.echo(click.style(f"  Error: {e}", fg='red'), err=True)
            sys.exit(1)

        click.echo()

        # Step 1: Load known genes
        click.echo(click.style("Step 1: Loading known genes (positive controls)...", bold=True))
        try:
            load_known_genes_to_duckdb(store)
            known_genes_df = store.load_dataframe('known_genes')
            known_gene_count = known_genes_df.height if known_genes_df else 0
            click.echo(click.style(
                f"  Loaded {known_gene_count} known genes (OMIM Usher + SYSCILIA SCGS)",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error loading known genes: {e}", fg='red'), err=True)
            logger.exception("Failed to load known genes")
            sys.exit(1)

        click.echo()
        provenance.record_step('load_known_genes', {
            'known_gene_count': known_gene_count,
        })

        # Step 2: Compute composite scores
        click.echo(click.style("Step 2: Computing composite scores...", bold=True))
        click.echo("  Joining all 6 evidence layers...")
        click.echo("  Computing NULL-preserving weighted averages...")

        try:
            scored_df = compute_composite_scores(store, scoring_weights)
            total_genes = scored_df.height
            genes_with_score = scored_df.filter(scored_df['composite_score'].is_not_null()).height
            mean_score = scored_df.filter(scored_df['composite_score'].is_not_null())['composite_score'].mean()

            click.echo(click.style(
                f"  Scored {genes_with_score}/{total_genes} genes (mean: {mean_score:.4f})",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error computing scores: {e}", fg='red'), err=True)
            logger.exception("Failed to compute composite scores")
            sys.exit(1)

        click.echo()
        provenance.record_step('compute_composite_scores', {
            'total_genes': total_genes,
            'genes_with_score': genes_with_score,
            'mean_score': float(mean_score),
            'weights': {
                'gnomad': scoring_weights.gnomad,
                'expression': scoring_weights.expression,
                'annotation': scoring_weights.annotation,
                'localization': scoring_weights.localization,
                'animal_model': scoring_weights.animal_model,
                'literature': scoring_weights.literature,
            },
        })

        # Step 3: Persist scores
        click.echo(click.style("Step 3: Persisting scored genes to DuckDB...", bold=True))

        try:
            persist_scored_genes(store, scored_df, scoring_weights)
            click.echo(click.style(
                f"  Saved to 'scored_genes' table",
                fg='green'
            ))
        except Exception as e:
            click.echo(click.style(f"  Error persisting scores: {e}", fg='red'), err=True)
            logger.exception("Failed to persist scored genes")
            sys.exit(1)

        click.echo()

        # Step 4: QC checks (unless --skip-qc)
        qc_passed = True
        if not skip_qc:
            click.echo(click.style("Step 4: Running quality control checks...", bold=True))

            try:
                qc_result = run_qc_checks(store)

                # Display warnings
                if qc_result.get('warnings'):
                    click.echo(click.style("  Warnings:", fg='yellow'))
                    for warning in qc_result['warnings']:
                        click.echo(click.style(f"    - {warning}", fg='yellow'))

                # Display errors
                if qc_result.get('errors'):
                    click.echo(click.style("  Errors:", fg='red'))
                    for error in qc_result['errors']:
                        click.echo(click.style(f"    - {error}", fg='red'))
                    qc_passed = False
                else:
                    click.echo(click.style("  All QC checks passed", fg='green'))

                # Display missing data rates
                if 'missing_data_rates' in qc_result:
                    click.echo()
                    click.echo("  Missing data rates by layer:")
                    for layer, rate in qc_result['missing_data_rates'].items():
                        click.echo(f"    {layer}: {rate:.1%}")

            except Exception as e:
                click.echo(click.style(f"  Error running QC: {e}", fg='red'), err=True)
                logger.exception("Failed to run QC checks")
                qc_passed = False

            click.echo()
            provenance.record_step('run_qc_checks', {
                'passed': qc_passed,
                'warnings_count': len(qc_result.get('warnings', [])),
                'errors_count': len(qc_result.get('errors', [])),
            })
        else:
            click.echo(click.style("Step 4: Skipping QC checks (--skip-qc)", fg='yellow'))
            click.echo()

        # Step 5: Validation (unless --skip-validation)
        validation_passed = True
        if not skip_validation:
            click.echo(click.style("Step 5: Validating known gene rankings...", bold=True))

            try:
                validation_result = validate_known_gene_ranking(store)
                validation_passed = validation_result.get('validation_passed', False)

                # Display validation report
                report = generate_validation_report(validation_result)
                click.echo(report)

                if validation_passed:
                    click.echo(click.style("  Validation PASSED", fg='green', bold=True))
                else:
                    click.echo(click.style("  Validation FAILED", fg='red', bold=True))

            except Exception as e:
                click.echo(click.style(f"  Error running validation: {e}", fg='red'), err=True)
                logger.exception("Failed to validate known gene ranking")
                validation_passed = False

            click.echo()
            provenance.record_step('validate_known_gene_ranking', {
                'passed': validation_passed,
            })
        else:
            click.echo(click.style("Step 5: Skipping validation (--skip-validation)", fg='yellow'))
            click.echo()

        # Save provenance sidecar
        click.echo("Saving provenance metadata...")
        scoring_dir = Path(config.data_dir) / "scoring"
        scoring_dir.mkdir(parents=True, exist_ok=True)
        provenance_path = scoring_dir / "scoring.provenance.json"
        provenance.save_sidecar(provenance_path)
        click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))
        click.echo()

        # Display final summary
        sufficient = scored_df.filter(scored_df['quality_flag'] == 'sufficient_evidence').height
        moderate = scored_df.filter(scored_df['quality_flag'] == 'moderate_evidence').height
        sparse = scored_df.filter(scored_df['quality_flag'] == 'sparse_evidence').height
        no_evidence = scored_df.filter(scored_df['quality_flag'] == 'no_evidence').height

        click.echo(click.style("=== Final Summary ===", bold=True))
        click.echo(f"Total Genes: {total_genes}")
        click.echo(f"Genes with scores: {genes_with_score} ({genes_with_score / total_genes * 100:.1f}%)")
        click.echo(f"Mean composite score: {mean_score:.4f}")
        click.echo()
        click.echo("Quality Flag Distribution:")
        click.echo(f"  Sufficient evidence (>=4 layers): {sufficient}")
        click.echo(f"  Moderate evidence (2-3 layers): {moderate}")
        click.echo(f"  Sparse evidence (1 layer): {sparse}")
        click.echo(f"  No evidence: {no_evidence}")
        click.echo()
        click.echo(f"QC Status: {'PASS' if qc_passed else 'FAIL'}")
        click.echo(f"Validation Status: {'PASS' if validation_passed or skip_validation else 'FAIL'}")
        click.echo()
        click.echo(f"DuckDB Path: {config.duckdb_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Scoring pipeline complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Scoring command failed: {e}", fg='red'), err=True)
        logger.exception("Scoring command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()

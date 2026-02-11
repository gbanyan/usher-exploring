"""Validation command: Run comprehensive validation pipeline.

Commands for:
- Running positive control validation (known genes)
- Running negative control validation (housekeeping genes)
- Running sensitivity analysis (weight perturbation)
- Generating comprehensive validation report
"""

import logging
import sys
from pathlib import Path

import click
import structlog

from usher_pipeline.config.loader import load_config
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker
from usher_pipeline.scoring import (
    validate_positive_controls_extended,
    validate_negative_controls,
    run_sensitivity_analysis,
    summarize_sensitivity,
)
from usher_pipeline.scoring.validation_report import (
    generate_comprehensive_validation_report,
    save_validation_report,
)

logger = logging.getLogger(__name__)


@click.command('validate')
@click.option(
    '--force',
    is_flag=True,
    help='Re-run validation even if validation checkpoint exists'
)
@click.option(
    '--skip-sensitivity',
    is_flag=True,
    help='Skip sensitivity analysis (faster iteration)'
)
@click.option(
    '--output-dir',
    type=click.Path(path_type=Path),
    default=None,
    help='Output directory for validation report (default: {data_dir}/validation)'
)
@click.option(
    '--top-n',
    type=int,
    default=100,
    help='Top N genes for sensitivity analysis (default: 100)'
)
@click.pass_context
def validate(ctx, force, skip_sensitivity, output_dir, top_n):
    """Run comprehensive validation pipeline (positive + negative + sensitivity).

    Validates scoring system using three complementary approaches:
    1. Positive controls: Known cilia/Usher genes should rank highly
    2. Negative controls: Housekeeping genes should rank low
    3. Sensitivity analysis: Rankings should be stable under weight perturbations

    Generates comprehensive validation report with weight tuning recommendations.

    Requires scored_genes checkpoint (run 'usher-pipeline score' first).

    Pipeline steps:
    1. Load configuration and initialize store
    2. Check scored_genes checkpoint exists
    3. Run positive control validation (validate_positive_controls_extended)
    4. Run negative control validation (validate_negative_controls)
    5. Run sensitivity analysis (unless --skip-sensitivity)
    6. Generate comprehensive validation report
    7. Save report to output_dir/validation_report.md

    Examples:

        # Full validation pipeline
        usher-pipeline validate

        # Skip sensitivity analysis (faster)
        usher-pipeline validate --skip-sensitivity

        # Custom output directory
        usher-pipeline validate --output-dir results/validation

        # Sensitivity with more genes
        usher-pipeline validate --top-n 200
    """
    config_path = ctx.obj['config_path']

    click.echo(click.style("=== Comprehensive Validation Pipeline ===", bold=True))
    click.echo()

    store = None
    try:
        # Step 1: Load configuration
        click.echo(click.style("Step 1: Loading configuration...", bold=True))
        config = load_config(config_path)
        click.echo(click.style(f"  Config loaded: {config_path}", fg='green'))
        click.echo()

        # Step 2: Initialize storage and provenance
        click.echo(click.style("Step 2: Initializing storage and provenance tracking...", bold=True))
        store = PipelineStore.from_config(config)
        provenance = ProvenanceTracker.from_config(config)
        click.echo(click.style("  Storage initialized", fg='green'))
        click.echo()

        # Set output directory
        if output_dir is None:
            output_dir = Path(config.data_dir) / "validation"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Step 3: Check scored_genes checkpoint
        click.echo(click.style("Step 3: Checking scored_genes checkpoint...", bold=True))
        has_scored_genes = store.has_checkpoint('scored_genes')

        if not has_scored_genes:
            click.echo(click.style(
                "  Error: scored_genes checkpoint not found. Run 'usher-pipeline score' first.",
                fg='red'
            ), err=True)
            sys.exit(1)

        click.echo(click.style("  scored_genes checkpoint found", fg='green'))
        click.echo()

        # Check for validation checkpoint
        validation_checkpoint_path = output_dir / "validation_report.md"
        has_validation = validation_checkpoint_path.exists()

        if has_validation and not force:
            click.echo(click.style(
                f"Validation report exists at {validation_checkpoint_path}. "
                "Skipping validation (use --force to re-run).",
                fg='yellow'
            ))
            click.echo()

            # Display existing report
            report_text = validation_checkpoint_path.read_text(encoding='utf-8')
            click.echo(report_text)
            return

        # Step 4: Run positive control validation
        click.echo(click.style("Step 4: Running positive control validation...", bold=True))
        click.echo("  Validating known cilia/Usher gene rankings...")
        click.echo("  Computing recall@k metrics...")
        click.echo("  Generating per-source breakdown...")

        try:
            positive_metrics = validate_positive_controls_extended(store)
            pos_passed = positive_metrics.get("validation_passed", False)

            median_pct = positive_metrics.get("median_percentile", 0.0) * 100
            recall_10pct = positive_metrics.get("recall_at_k", {}).get("recalls_percentage", {}).get("10%", 0.0) * 100

            if pos_passed:
                click.echo(click.style(
                    f"  Positive controls PASSED (median: {median_pct:.1f}%, recall@10%: {recall_10pct:.1f}%)",
                    fg='green'
                ))
            else:
                click.echo(click.style(
                    f"  Positive controls FAILED (median: {median_pct:.1f}%, recall@10%: {recall_10pct:.1f}%)",
                    fg='red'
                ))

        except Exception as e:
            click.echo(click.style(f"  Error running positive control validation: {e}", fg='red'), err=True)
            logger.exception("Failed to run positive control validation")
            sys.exit(1)

        click.echo()
        provenance.record_step('validate_positive_controls', {
            'validation_passed': pos_passed,
            'median_percentile': positive_metrics.get("median_percentile"),
            'recall_at_10pct': positive_metrics.get("recall_at_k", {}).get("recalls_percentage", {}).get("10%"),
        })

        # Step 5: Run negative control validation
        click.echo(click.style("Step 5: Running negative control validation...", bold=True))
        click.echo("  Validating housekeeping gene rankings...")

        try:
            negative_metrics = validate_negative_controls(store)
            neg_passed = negative_metrics.get("validation_passed", False)

            neg_median_pct = negative_metrics.get("median_percentile", 0.0) * 100
            top_q_count = negative_metrics.get("top_quartile_count", 0)

            if neg_passed:
                click.echo(click.style(
                    f"  Negative controls PASSED (median: {neg_median_pct:.1f}%, top quartile: {top_q_count})",
                    fg='green'
                ))
            else:
                click.echo(click.style(
                    f"  Negative controls FAILED (median: {neg_median_pct:.1f}%, top quartile: {top_q_count})",
                    fg='red'
                ))

        except Exception as e:
            click.echo(click.style(f"  Error running negative control validation: {e}", fg='red'), err=True)
            logger.exception("Failed to run negative control validation")
            sys.exit(1)

        click.echo()
        provenance.record_step('validate_negative_controls', {
            'validation_passed': neg_passed,
            'median_percentile': negative_metrics.get("median_percentile"),
            'top_quartile_count': top_q_count,
        })

        # Step 6: Run sensitivity analysis (unless --skip-sensitivity)
        sensitivity_result = None
        sensitivity_summary = None
        sens_passed = None

        if not skip_sensitivity:
            click.echo(click.style("Step 6: Running sensitivity analysis...", bold=True))
            click.echo(f"  Perturbing weights by ±5% and ±10% (top {top_n} genes)...")
            click.echo("  Computing Spearman rank correlations...")

            try:
                scoring_weights = config.scoring

                sensitivity_result = run_sensitivity_analysis(
                    store,
                    scoring_weights,
                    deltas=None,  # Use DEFAULT_DELTAS
                    top_n=top_n,
                )

                sensitivity_summary = summarize_sensitivity(sensitivity_result)
                sens_passed = sensitivity_summary.get("overall_stable", False)

                stable_count = sensitivity_summary.get("stable_count", 0)
                unstable_count = sensitivity_summary.get("unstable_count", 0)
                mean_rho = sensitivity_summary.get("mean_rho", 0.0)

                if sens_passed:
                    click.echo(click.style(
                        f"  Sensitivity analysis STABLE (stable: {stable_count}, unstable: {unstable_count}, mean rho: {mean_rho:.4f})",
                        fg='green'
                    ))
                else:
                    click.echo(click.style(
                        f"  Sensitivity analysis UNSTABLE (stable: {stable_count}, unstable: {unstable_count}, mean rho: {mean_rho:.4f})",
                        fg='yellow'
                    ))

            except Exception as e:
                click.echo(click.style(f"  Error running sensitivity analysis: {e}", fg='red'), err=True)
                logger.exception("Failed to run sensitivity analysis")
                sys.exit(1)

            click.echo()
            provenance.record_step('run_sensitivity_analysis', {
                'overall_stable': sens_passed,
                'stable_count': stable_count,
                'unstable_count': unstable_count,
                'mean_rho': mean_rho,
                'top_n': top_n,
            })
        else:
            click.echo(click.style("Step 6: Skipping sensitivity analysis (--skip-sensitivity)", fg='yellow'))
            click.echo()

            # Create dummy sensitivity results for report generation
            sensitivity_result = {
                "baseline_weights": config.scoring.model_dump(),
                "results": [],
                "top_n": top_n,
                "total_perturbations": 0,
            }
            sensitivity_summary = {
                "min_rho": None,
                "max_rho": None,
                "mean_rho": None,
                "stable_count": 0,
                "unstable_count": 0,
                "total_perturbations": 0,
                "overall_stable": True,  # Default to stable if skipped
                "most_sensitive_layer": None,
                "most_robust_layer": None,
            }

        # Step 7: Generate comprehensive validation report
        click.echo(click.style("Step 7: Generating comprehensive validation report...", bold=True))

        try:
            report_text = generate_comprehensive_validation_report(
                positive_metrics,
                negative_metrics,
                sensitivity_result,
                sensitivity_summary,
            )

            click.echo(click.style("  Report generated", fg='green'))

        except Exception as e:
            click.echo(click.style(f"  Error generating report: {e}", fg='red'), err=True)
            logger.exception("Failed to generate validation report")
            sys.exit(1)

        click.echo()

        # Step 8: Save report
        click.echo(click.style("Step 8: Saving validation report...", bold=True))

        try:
            report_path = output_dir / "validation_report.md"
            save_validation_report(report_text, report_path)

            click.echo(click.style(f"  Report saved: {report_path}", fg='green'))

            # Save provenance sidecar
            provenance_path = output_dir / "validation.provenance.json"
            provenance.save_sidecar(provenance_path)
            click.echo(click.style(f"  Provenance saved: {provenance_path}", fg='green'))

        except Exception as e:
            click.echo(click.style(f"  Error saving report: {e}", fg='red'), err=True)
            logger.exception("Failed to save validation report")
            sys.exit(1)

        click.echo()

        # Display final summary
        click.echo(click.style("=== Validation Summary ===", bold=True))
        click.echo()

        all_passed = pos_passed and neg_passed and (sens_passed if not skip_sensitivity else True)

        if all_passed:
            overall_status = click.style("ALL VALIDATIONS PASSED ✓", fg='green', bold=True)
        elif pos_passed and neg_passed:
            overall_status = click.style("PARTIAL PASS (Sensitivity Unstable)", fg='yellow', bold=True)
        elif pos_passed:
            overall_status = click.style("PARTIAL PASS (Specificity Issue)", fg='yellow', bold=True)
        else:
            overall_status = click.style("VALIDATION FAILED ✗", fg='red', bold=True)

        click.echo(f"Overall Status: {overall_status}")
        click.echo()

        click.echo(f"Positive Controls: {'PASSED ✓' if pos_passed else 'FAILED ✗'}")
        click.echo(f"  - Median percentile: {positive_metrics.get('median_percentile', 0.0) * 100:.1f}%")
        click.echo(f"  - Recall@10%: {positive_metrics.get('recall_at_k', {}).get('recalls_percentage', {}).get('10%', 0.0) * 100:.1f}%")
        click.echo()

        click.echo(f"Negative Controls: {'PASSED ✓' if neg_passed else 'FAILED ✗'}")
        click.echo(f"  - Median percentile: {negative_metrics.get('median_percentile', 0.0) * 100:.1f}%")
        click.echo(f"  - Top quartile count: {negative_metrics.get('top_quartile_count', 0)}")
        click.echo()

        if not skip_sensitivity:
            click.echo(f"Sensitivity Analysis: {'STABLE ✓' if sens_passed else 'UNSTABLE ✗'}")
            click.echo(f"  - Stable perturbations: {sensitivity_summary.get('stable_count', 0)}/{sensitivity_summary.get('total_perturbations', 0)}")
            if sensitivity_summary.get('mean_rho') is not None:
                click.echo(f"  - Mean Spearman rho: {sensitivity_summary.get('mean_rho', 0.0):.4f}")
            click.echo()
        else:
            click.echo("Sensitivity Analysis: SKIPPED")
            click.echo()

        click.echo(f"Report Path: {report_path}")
        click.echo(f"Provenance: {provenance_path}")
        click.echo()
        click.echo(click.style("Validation pipeline complete!", fg='green', bold=True))

    except Exception as e:
        click.echo(click.style(f"Validation command failed: {e}", fg='red'), err=True)
        logger.exception("Validation command failed")
        sys.exit(1)
    finally:
        # Clean up resources
        if store is not None:
            store.close()

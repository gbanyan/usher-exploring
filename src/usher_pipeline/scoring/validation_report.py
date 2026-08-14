"""Internal evaluation report generation for control recovery and sensitivity."""

from pathlib import Path
from math import isclose, isfinite

import structlog

logger = structlog.get_logger(__name__)


def _assess_control_metrics(
    metrics: dict,
    *,
    expected_key: str,
    found_key: str,
    denominator_key: str = "total_scored_non_null",
) -> dict:
    """Validate counts and summary metrics before rendering a control report."""
    expected = metrics.get(expected_key)
    found = metrics.get(found_key)
    denominator = metrics.get(denominator_key)
    median = metrics.get("median_percentile")
    top_quartile_count = metrics.get("top_quartile_count")
    top_quartile_fraction = metrics.get("top_quartile_fraction")
    errors: list[str] = []

    def count_value(value: object) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return None

    expected_count = count_value(expected)
    found_count = count_value(found)
    denominator_count = count_value(denominator)
    if expected_count is None or found_count is None:
        errors.append("expected/found counts are missing or non-integer")
    elif expected_count < 0 or found_count < 0:
        errors.append("expected/found counts cannot be negative")
    elif found_count > expected_count:
        errors.append("found count exceeds expected count")
    elif expected_count == 0 or found_count == 0:
        errors.append("no evaluable controls are available")

    if denominator_count is None:
        errors.append("non-NULL scored-gene denominator is missing or non-integer")
    elif denominator_count <= 0:
        errors.append("non-NULL scored-gene denominator must be positive")
    elif found_count is not None and found_count > denominator_count:
        errors.append("found count exceeds the scored-gene denominator")

    if median is None or not isinstance(median, (int, float)) or not isfinite(median):
        errors.append("median percentile is missing or non-finite")
    elif not 0.0 <= median <= 1.0:
        errors.append("median percentile is outside [0, 1]")

    if top_quartile_count is None or count_value(top_quartile_count) is None:
        errors.append("top-quartile count is missing or non-integer")
    elif found_count is not None and not 0 <= int(top_quartile_count) <= found_count:
        errors.append("top-quartile count is outside the found-count range")

    if (
        top_quartile_fraction is None
        or not isinstance(top_quartile_fraction, (int, float))
        or not isfinite(top_quartile_fraction)
    ):
        errors.append("top-quartile fraction is missing or non-finite")
    elif not 0.0 <= top_quartile_fraction <= 1.0:
        errors.append("top-quartile fraction is outside [0, 1]")
    elif found_count and not isclose(
        top_quartile_fraction,
        int(top_quartile_count) / found_count,
        abs_tol=0.02,
    ):
        errors.append("top-quartile fraction disagrees with count/found")

    return {
        "coherent": not errors,
        "expected": expected_count,
        "found": found_count,
        "denominator": denominator_count,
        "median": median if not errors else None,
        "top_quartile_count": int(top_quartile_count) if not errors else None,
        "top_quartile_fraction": top_quartile_fraction if not errors else None,
        "errors": errors,
    }


def generate_internal_evaluation_report(
    positive_metrics: dict,
    negative_metrics: dict,
    sensitivity_result: dict,
    sensitivity_summary: dict,
) -> str:
    """
    Generate an internal evaluation report combining three diagnostic components.

    Args:
        positive_metrics: Dict from validate_positive_controls_extended()
        negative_metrics: Dict from validate_negative_controls()
        sensitivity_result: Dict from run_sensitivity_analysis()
        sensitivity_summary: Dict from summarize_sensitivity()

    Returns:
        Multi-section Markdown report as string.  The wording deliberately
        describes reference checks and control recovery; it does not present
        these diagnostics as a substitute for independent outcome evidence.

    Sections:
        1. Internal Control Recovery (known genes rank high)
        2. Negative Control Recovery (housekeeping genes rank low)
        3. Sensitivity Analysis (weight perturbation stability)
        4. Internal Evaluation Summary
        5. Weight Tuning Recommendations (based on diagnostic results)
    """
    logger.info("generate_internal_evaluation_report_start")

    sections = []

    # Section 1: Positive Control Recovery
    sections.append("# Internal Evaluation and Control-Recovery Report")
    sections.append("")
    sections.append("## 1. Internal Control Recovery")
    sections.append("")

    positive_quality = _assess_control_metrics(
        positive_metrics,
        expected_key="total_known_expected",
        found_key="total_known_in_dataset",
    )
    pos_passed = positive_quality["coherent"] and positive_metrics.get("validation_passed", False)
    pos_status = (
        "INCOMPLETE ⚠" if not positive_quality["coherent"]
        else "MEETS REFERENCE ✓" if pos_passed
        else "BELOW REFERENCE ✗"
    )
    sections.append(f"**Status:** {pos_status}")
    sections.append("")

    median_pct = positive_quality["median"]
    sections.append("### Summary")
    if positive_quality["coherent"]:
        sections.append(f"- Known genes expected: {positive_quality['expected']}")
        sections.append(f"- Known genes found: {positive_quality['found']}")
        sections.append(f"- Percentile denominator (non-NULL scored genes): {positive_quality['denominator']:,}")
        sections.append(f"- Median percentile: {median_pct * 100:.1f}%")
        sections.append(f"- Top quartile count: {positive_quality['top_quartile_count']}")
        sections.append(f"- Top quartile fraction: {positive_quality['top_quartile_fraction'] * 100:.1f}%")
    else:
        sections.extend([
            "- Known genes expected: N/A",
            "- Known genes found: N/A",
            "- Percentile denominator (non-NULL scored genes): N/A",
            "- Median percentile: N/A",
            "- Top quartile count: N/A",
            "- Top quartile fraction: N/A",
            f"- **Error:** Incomplete positive-control metrics ({'; '.join(positive_quality['errors'])}).",
        ])
    sections.append("")

    # Recall@k table
    recall_at_k = positive_metrics.get("recall_at_k", {})
    if recall_at_k:
        sections.append("### Recall@k Metrics")
        sections.append("")
        sections.append("| Threshold | Recall |")
        sections.append("|-----------|--------|")

        # Absolute thresholds
        for k, recall in sorted(recall_at_k.get("recalls_absolute", {}).items()):
            sections.append(f"| Top {k} | {recall * 100:.1f}% |")

        # Percentage thresholds
        for pct_str, recall in sorted(recall_at_k.get("recalls_percentage", {}).items()):
            sections.append(f"| Top {pct_str} | {recall * 100:.1f}% |")

        sections.append("")

    # Per-source breakdown
    per_source = positive_metrics.get("per_source_breakdown", {})
    if per_source:
        sections.append("### Per-Source Breakdown")
        sections.append("")
        sections.append("| Source | Count | Median Percentile | Top Quartile |")
        sections.append("|--------|-------|-------------------|--------------|")

        for source, metrics in per_source.items():
            display_source = {
                "omim_usher": "established_usher",
                "syscilia_scgs_v2": "syscilia_scgs_v2",
            }.get(source, source)
            count = metrics.get("count", 0)
            median = metrics.get("median_percentile")
            top_q = metrics.get("top_quartile_count", 0)

            if median is not None:
                median_str = f"{median * 100:.1f}%"
            else:
                median_str = "N/A"

            sections.append(f"| {display_source} | {count} | {median_str} | {top_q} |")

        sections.append("")

    # Verdict
    if not positive_quality["coherent"]:
        sections.append("**Interpretation:** Positive-control metrics are incomplete or inconsistent; no control-recovery conclusion is assigned.")
    elif pos_passed:
        sections.append("**Interpretation:** The selected cilia/Usher controls show the expected internal recovery pattern. The control set is curated and the cilia-signal gate was informed by control behavior, so this is a diagnostic recovery check rather than an independent sensitivity estimate.")
    else:
        sections.append("**Verdict:** Known genes rank below expected threshold, suggesting potential issues with evidence layer weights or data quality.")

    sections.append("")

    # Section 2: Negative Control Recovery
    sections.append("## 2. Negative Control Recovery")
    sections.append("")

    negative_quality = _assess_control_metrics(
        negative_metrics,
        expected_key="total_expected",
        found_key="total_in_dataset",
    )
    neg_passed = negative_quality["coherent"] and negative_metrics.get("validation_passed", False)
    neg_status = (
        "INCOMPLETE ⚠" if not negative_quality["coherent"]
        else "MEETS REFERENCE ✓" if neg_passed
        else "BELOW REFERENCE ✗"
    )
    sections.append(f"**Status:** {neg_status}")
    sections.append("")

    neg_median_pct = negative_quality["median"]
    sections.append("### Summary")
    if negative_quality["coherent"]:
        sections.append(f"- Housekeeping genes expected: {negative_quality['expected']}")
        sections.append(f"- Housekeeping genes found: {negative_quality['found']}")
        sections.append(f"- Percentile denominator (non-NULL scored genes): {negative_quality['denominator']:,}")
        sections.append(f"- Median percentile: {neg_median_pct * 100:.1f}%")
        sections.append(f"- Top quartile count: {negative_quality['top_quartile_count']}")
        sections.append(f"- Top quartile fraction: {negative_quality['top_quartile_fraction'] * 100:.1f}%")
        sections.append(f"- Meeting the HIGH-tier composite-score threshold (composite >= 0.70): {negative_metrics.get('in_high_tier_count', 0)}")
        gated_count = negative_metrics.get('gated_high_tier_count', 0)
        gated_genes = negative_metrics.get('gated_high_tier_genes', [])
        gated_suffix = f" ({', '.join(gated_genes)})" if gated_genes else ""
        sections.append(f"- In HIGH tier after cilia-signal gate: {gated_count}{gated_suffix}")
    else:
        sections.extend([
            "- Housekeeping genes expected: N/A",
            "- Housekeeping genes found: N/A",
            "- Percentile denominator (non-NULL scored genes): N/A",
            "- Median percentile: N/A",
            "- Top quartile count: N/A",
            "- Top quartile fraction: N/A",
            f"- **Error:** Incomplete negative-control metrics ({'; '.join(negative_quality['errors'])}).",
        ])
    sections.append("")

    # Verdict
    if not negative_quality["coherent"]:
        sections.append("**Interpretation:** Negative-control metrics are incomplete or inconsistent; no control-recovery conclusion is assigned.")
    elif neg_passed:
        sections.append("**Interpretation:** Housekeeping genes rank LOW (median < 50th percentile) under this internal reference check.")
    else:
        sections.append("**Verdict:** Housekeeping genes rank higher than expected, indicating potential lack of specificity.")

    sections.append("")

    # Section 3: Sensitivity Analysis
    sections.append("## 3. Sensitivity Analysis")
    sections.append("")

    sensitivity_state = sensitivity_summary.get("overall_stable")
    sens_passed = sensitivity_state is True
    sens_status = (
        "STABLE ✓" if sensitivity_state is True
        else "UNSTABLE ✗" if sensitivity_state is False
        else "UNASSESSED" if sensitivity_summary.get("assessment_status") == "unassessed" else "NOT RUN"
    )
    sections.append(f"**Status:** {sens_status}")
    sections.append("")

    from usher_pipeline.scoring.sensitivity import (
        EVIDENCE_LAYERS,
        STABILITY_THRESHOLD,
        format_weight_vector,
    )

    sections.append("### Summary")
    sections.append(f"- Total perturbations: {sensitivity_summary.get('total_perturbations', 0)}")
    sections.append(
        "- Raw delta protocol: apply the displayed delta to one baseline weight first, "
        "then renormalize all six weights to sum to 1.0."
    )
    baseline_weights = sensitivity_result.get("baseline_weights", {})
    if baseline_weights:
        sections.append(f"- Baseline six-weight vector: {format_weight_vector(baseline_weights)}")
    if sensitivity_summary.get("assessment_status") == "unassessed":
        sections.append("- Assessed perturbations: 0")
        sections.append(
            f"- Unassessed perturbations (rho unavailable): {sensitivity_summary.get('unassessed_count', 0)}"
        )
    else:
        sections.append(f"- Stable perturbations (rho >= {STABILITY_THRESHOLD}): {sensitivity_summary.get('stable_count', 0)}")
        sections.append(f"- Unstable perturbations: {sensitivity_summary.get('unstable_count', 0)}")

    mean_rho = sensitivity_summary.get("mean_rho")
    if mean_rho is not None:
        sections.append(f"- Mean Spearman rho: {mean_rho:.4f}")
        min_rho = sensitivity_summary.get("min_rho")
        max_rho = sensitivity_summary.get("max_rho")
        if min_rho is not None and max_rho is not None:
            sections.append(f"- Range: [{min_rho:.4f}, {max_rho:.4f}]")
    else:
        sections.append("- Mean Spearman rho: N/A")

    sections.append("")

    # Sensitivity by layer
    most_sensitive = sensitivity_summary.get("most_sensitive_layer")
    most_robust = sensitivity_summary.get("most_robust_layer")

    if most_sensitive and most_robust:
        sections.append(f"- Most sensitive layer: {most_sensitive}")
        sections.append(f"- Most robust layer: {most_robust}")
        sections.append("")

    # Spearman rho table
    sections.append("### Spearman Correlation by Perturbation")
    sections.append("")
    top_n = sensitivity_result.get("top_n", 100)
    sections.append(f"| Layer | Raw Delta | Spearman rho | Top-{top_n} overlap | Jaccard | Stable? |")
    sections.append("|-------|-------|--------------|-----------------|---------|---------|")

    for result in sensitivity_result.get("results", []):
        layer = result["layer"]
        delta = result["delta"]
        rho = result["spearman_rho"]
        overlap = result.get("overlap_count", "N/A")
        jaccard = result.get("top_n_jaccard")

        if rho is not None:
            stable_mark = "✓" if rho >= STABILITY_THRESHOLD else "✗"
            rho_str = f"{rho:.4f}"
        else:
            stable_mark = "N/A"
            rho_str = "N/A"

        jaccard_str = f"{jaccard:.3f}" if jaccard is not None else "N/A"
        sections.append(f"| {layer} | {delta:+.2f} | {rho_str} | {overlap} | {jaccard_str} | {stable_mark} |")

    sections.append("")

    if sensitivity_result.get("results"):
        sections.append("### Final Normalized Six-Weight Vectors")
        sections.append("")
        sections.append(
            f"Order: {', '.join(EVIDENCE_LAYERS)}. Each vector is the final vector after renormalization."
        )
        sections.append("")
        sections.append("| Layer | Raw Delta | Final normalized weights |")
        sections.append("|-------|-----------|--------------------------|")
        for result in sensitivity_result["results"]:
            final_weights = result.get("final_weights") or result.get("perturbed_weights", {})
            if final_weights:
                vector = format_weight_vector(final_weights)
            else:
                vector = "N/A"
            sections.append(
                f"| {result['layer']} | {result['delta']:+.2f} | {vector} |"
            )
        sections.append("")

    # Verdict
    if sensitivity_state is True:
        sections.append(f"**Verdict:** All absolute weight-point perturbations produce stable rankings (rho >= {STABILITY_THRESHOLD}).")
    elif sensitivity_state is False:
        sections.append(f"**Verdict:** Some perturbations produce unstable rankings (rho < {STABILITY_THRESHOLD}), suggesting results may be sensitive to weight choices.")
    elif sensitivity_summary.get("assessment_status") == "unassessed":
        sections.append(
            "**Interpretation:** Perturbations were run, but rho was unavailable "
            "for every comparison; sensitivity is UNASSESSED rather than unstable."
        )
    else:
        sections.append("**Interpretation:** Sensitivity analysis was not run for this report.")

    sections.append("")

    # Section 4: Internal Evaluation Summary
    sections.append("## 4. Internal Evaluation Summary")
    sections.append("")

    incomplete_control = not positive_quality["coherent"] or not negative_quality["coherent"]
    all_passed = pos_passed and neg_passed and sensitivity_state is True

    if all_passed:
        overall_status = "ALL REFERENCE CHECKS MEET THRESHOLDS ✓"
        overall_verdict = (
            "The scoring system shows the expected patterns for the selected internal controls "
            "and tested weight perturbations. These diagnostics do not establish clinical, causal, "
            "or prospective outcome performance."
        )
    elif incomplete_control:
        overall_status = "INTERNAL EVALUATION INCOMPLETE (Control Metrics)"
        overall_verdict = (
            "One or more control-recovery metric sets are incomplete or inconsistent. "
            "No overall control-recovery conclusion is assigned."
        )
    elif sensitivity_state is None:
        sensitivity_label = (
            "Sensitivity Unassessed"
            if sensitivity_summary.get("assessment_status") == "unassessed"
            else "Sensitivity Not Run"
        )
        overall_status = "INTERNAL EVALUATION INCOMPLETE (Sensitivity Not Run)"
        overall_verdict = (
            "Positive and negative control recovery are reported, but sensitivity is "
            f"{sensitivity_label.lower()}. No overall conclusion is assigned to that component."
        )
        overall_status = f"INTERNAL EVALUATION INCOMPLETE ({sensitivity_label})"
    elif pos_passed and neg_passed:
        overall_status = "REFERENCE CHECKS PARTLY MEET THRESHOLDS (Sensitivity Unstable)"
        overall_verdict = (
            "Positive and negative control recovery meet their reference thresholds, but rankings are "
            "sensitive to tested weight perturbations."
        )
    elif pos_passed:
        overall_status = "REFERENCE CHECKS PARTLY MEET THRESHOLDS (Control Separation Issue)"
        overall_verdict = (
            "Known genes rank highly, but housekeeping genes also rank higher than expected. "
            "The internal control-separation diagnostic indicates a specificity concern; review evidence "
            "layer behavior without tuning on these same controls."
        )
    else:
        overall_status = "REFERENCE CHECKS BELOW THRESHOLDS ✗"
        overall_verdict = (
            "Known genes do not rank highly in this internal recovery check, indicating that "
            "Evidence layer weights or data quality require investigation."
        )

    sections.append(f"**Status:** {overall_status}")
    sections.append("")
    sections.append(f"**Verdict:** {overall_verdict}")
    sections.append("")

    sections.append("| Evaluation Component | Status | Interpretation |")
    sections.append("|------------------|--------|---------|")
    positive_interpretation = (
        "Metrics incomplete" if not positive_quality["coherent"]
        else "Known genes rank high" if pos_passed
        else "Known genes rank low"
    )
    negative_interpretation = (
        "Metrics incomplete" if not negative_quality["coherent"]
        else "Housekeeping genes rank low" if neg_passed
        else "Housekeeping genes rank high"
    )
    sections.append(f"| Positive control recovery | {pos_status} | {positive_interpretation} |")
    sections.append(f"| Negative control recovery | {neg_status} | {negative_interpretation} |")
    sensitivity_interpretation = (
        "Rankings stable under perturbations" if sensitivity_state is True
        else "Rankings unstable under perturbations" if sensitivity_state is False
        else "UNASSESSED: rho unavailable" if sensitivity_summary.get("assessment_status") == "unassessed"
        else "Not run"
    )
    sections.append(f"| Sensitivity analysis | {sens_status} | {sensitivity_interpretation} |")
    sections.append("")

    # Section 5: Weight Tuning Recommendations
    sections.append("## 5. Weight Tuning Recommendations")
    sections.append("")
    sections.append(
        "> **Note:** The recommendations below are automatically generated "
        "diagnostics, not the project's adopted course of action. The "
        "weight-learning question they raise was investigated directly "
        "(5-fold cross-validated grid search and penalized logistic "
        "regression; see `scripts/weight_tuning.py` and "
        "`scripts/weight_logreg.py`). Learned weights improve the control "
        "metrics but collapse the six-layer integration onto one or two "
        "layers, so the a priori biologically-motivated weights are retained "
        "by design and HIGH-tier specificity is addressed through the "
        "post-hoc cilia-signal gate."
    )
    sections.append("")

    if incomplete_control:
        recommendations = (
            "**Recommendations unavailable:** control metrics are incomplete or inconsistent; "
            "resolve the evaluation inputs before interpreting or tuning weights."
        )
    else:
        recommendations = recommend_weight_tuning(
            positive_metrics,
            negative_metrics,
            sensitivity_summary
        )

    sections.append(recommendations)

    report_text = "\n".join(sections)

    logger.info(
        "generate_internal_evaluation_report_complete",
        positive_passed=pos_passed,
        negative_passed=neg_passed,
        sensitivity_stable=sens_passed,
        overall_status=overall_status,
    )

    return report_text


def generate_comprehensive_validation_report(
    positive_metrics: dict,
    negative_metrics: dict,
    sensitivity_result: dict,
    sensitivity_summary: dict,
) -> str:
    """Compatibility alias for the internal evaluation report generator."""
    return generate_internal_evaluation_report(
        positive_metrics,
        negative_metrics,
        sensitivity_result,
        sensitivity_summary,
    )


def recommend_weight_tuning(
    positive_metrics: dict,
    negative_metrics: dict,
    sensitivity_summary: dict,
) -> str:
    """
    Generate weight-tuning recommendations based on internal evaluation results.

    Args:
        positive_metrics: Dict from validate_positive_controls_extended()
        negative_metrics: Dict from validate_negative_controls()
        sensitivity_summary: Dict from summarize_sensitivity()

    Returns:
        Formatted recommendation text

    Logic:
        - If all reference checks meet thresholds: No tuning recommended
        - If positive controls are below reference: Review layers where known genes score high
        - If negative controls are below reference: Examine layers boosting housekeeping genes
        - If sensitivity is unstable: Reduce weight of most sensitive layer

    Notes:
        - CRITICAL: Any tuning is post-hoc and risks reusing the same controls
        - Flag this pitfall per research guidance
        - Recommendations are guidance, not automatic actions
    """
    logger.info("recommend_weight_tuning_start")

    pos_passed = positive_metrics.get("validation_passed", False)
    neg_passed = negative_metrics.get("validation_passed", False)
    sensitivity_state = sensitivity_summary.get("overall_stable")
    sens_passed = sensitivity_state is True

    recommendations = []

    # All internal reference checks meet thresholds
    if pos_passed and neg_passed and sens_passed:
        recommendations.append("**Recommendation:** Current weights meet all selected internal reference checks. No tuning recommended.")
        recommendations.append("")
        recommendations.append(
            "The scoring system performs as expected across the selected internal evaluation components. "
            "Weights achieve good balance between sensitivity (known genes rank high), "
            "specificity (housekeeping genes rank low), and robustness (stable under perturbations)."
        )

        logger.info("recommend_weight_tuning_no_tuning_needed")
        return "\n".join(recommendations)

    # Some reference checks are below threshold - provide targeted recommendations
    recommendations.append("**Recommendations for Weight Tuning:**")
    recommendations.append("")

    # Positive controls failed
    if not pos_passed:
        recommendations.append("### 1. Known Gene Ranking Issue (Positive Controls)")
        recommendations.append("")
        recommendations.append(
            "Known cilia/Usher genes rank lower than expected (median < 75th percentile). "
            "This suggests the evidence layers are not sufficiently weighting ciliary biology."
        )
        recommendations.append("")
        recommendations.append("**Suggested Actions:**")
        recommendations.append("- Review per-source breakdown to identify which gene sets recover poorly")
        recommendations.append("- Examine evidence layer scores for top-ranked known genes")
        recommendations.append("- Consider increasing weights for layers where known genes consistently score high")
        recommendations.append("- Possible layers to increase: localization (ciliary proteomics), animal_model (cilia screens)")
        recommendations.append("")

    # Negative controls failed
    if not neg_passed:
        recommendations.append("### 2. Housekeeping Gene Ranking Issue (Negative Controls)")
        recommendations.append("")
        recommendations.append(
            "Housekeeping genes rank higher than expected (median >= 50th percentile). "
            "This suggests lack of specificity - generic genes are scoring too highly."
        )
        recommendations.append("")
        recommendations.append("**Suggested Actions:**")
        recommendations.append("- Examine which evidence layers contribute high scores to housekeeping genes")
        recommendations.append("- Consider reducing weights for generic layers (e.g., gnomad constraint, annotation)")
        recommendations.append("- Increase weights for cilia-specific layers (localization, animal_model, literature)")
        recommendations.append("- Review literature context weighting (ensure cilia-specific mentions prioritized)")
        recommendations.append("")

    # Sensitivity unstable
    if sensitivity_state is False:
        recommendations.append("### 3. Weight Sensitivity Issue (Stability)")
        recommendations.append("")
        most_sensitive = sensitivity_summary.get("most_sensitive_layer")
        unstable_count = sensitivity_summary.get("unstable_count", 0)

        recommendations.append(
            f"Ranking stability is compromised with {unstable_count} unstable perturbations. "
            "This means small changes in weights produce significant ranking shifts."
        )
        recommendations.append("")
        recommendations.append("**Suggested Actions:**")

        if most_sensitive:
            recommendations.append(f"- Most sensitive layer: **{most_sensitive}**")
            recommendations.append(f"- Consider reducing weight of {most_sensitive} to improve stability")

        recommendations.append("- Review layers with high instability (low Spearman rho across perturbations)")
        recommendations.append("- Increase weights for robust layers (high Spearman rho)")
        recommendations.append("- Consider smoothing evidence scores (e.g., log-transform, rank normalization)")
        recommendations.append("")

    elif sensitivity_state is None:
        recommendations.append(
            "### 3. Sensitivity Analysis Unassessed"
            if sensitivity_summary.get("assessment_status") == "unassessed"
            else "### 3. Sensitivity Analysis Not Run"
        )
        recommendations.append("")
        recommendations.append(
            "Sensitivity perturbations produced no usable rho, so ranking stability is "
            "UNASSESSED and no instability conclusion is assigned."
            if sensitivity_summary.get("assessment_status") == "unassessed"
            else "Sensitivity analysis was omitted, so ranking stability is not assessed in this report."
        )
        recommendations.append("")

    # Add critical warning about control reuse
    recommendations.append("---")
    recommendations.append("")
    recommendations.append("### CRITICAL: Control-Reuse / Post-Hoc Tuning Risk")
    recommendations.append("")
    recommendations.append(
        "**WARNING:** Any weight tuning based on these internal evaluation results is "
        "post-hoc tuning and introduces control-reuse risk."
    )
    recommendations.append("")
    recommendations.append(
        "If weights are adjusted based on positive/negative control performance, the same controls "
        "must not be treated as independent evidence for the tuned weights."
    )
    recommendations.append("")
    recommendations.append("**Best Practices:**")
    recommendations.append("1. If tuning weights: Use an independent hold-out/control set or cross-fold evaluation")
    recommendations.append("2. Document weight selection rationale (biological justification, not control optimization)")
    recommendations.append("3. Prefer a priori weight choices over post-hoc tuning")
    recommendations.append("4. If tuning is essential, use hold-out control genes not used in tuning")
    recommendations.append("")

    logger.info(
        "recommend_weight_tuning_complete",
        positive_passed=pos_passed,
        negative_passed=neg_passed,
        sensitivity_passed=sens_passed,
    )

    return "\n".join(recommendations)


def save_validation_report(report_text: str, output_path: Path) -> None:
    """
    Write validation report to file.

    Args:
        report_text: Markdown report text
        output_path: Path to save report (e.g., validation/validation_report.md)

    Notes:
        - Creates parent directories if needed
        - Overwrites existing file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(report_text, encoding="utf-8")

    logger.info("save_validation_report_complete", output_path=str(output_path))

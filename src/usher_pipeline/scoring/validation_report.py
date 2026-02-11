"""Comprehensive validation report generation combining all validation prongs."""

from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


def generate_comprehensive_validation_report(
    positive_metrics: dict,
    negative_metrics: dict,
    sensitivity_result: dict,
    sensitivity_summary: dict,
) -> str:
    """
    Generate comprehensive validation report combining all three validation prongs.

    Args:
        positive_metrics: Dict from validate_positive_controls_extended()
        negative_metrics: Dict from validate_negative_controls()
        sensitivity_result: Dict from run_sensitivity_analysis()
        sensitivity_summary: Dict from summarize_sensitivity()

    Returns:
        Multi-section Markdown report as string

    Sections:
        1. Positive Control Validation (known genes rank high)
        2. Negative Control Validation (housekeeping genes rank low)
        3. Sensitivity Analysis (weight perturbation stability)
        4. Overall Validation Summary (all-pass/partial-fail/fail)
        5. Weight Tuning Recommendations (based on validation results)
    """
    logger.info("generate_comprehensive_validation_report_start")

    sections = []

    # Section 1: Positive Control Validation
    sections.append("# Comprehensive Validation Report")
    sections.append("")
    sections.append("## 1. Positive Control Validation")
    sections.append("")

    pos_passed = positive_metrics.get("validation_passed", False)
    pos_status = "PASSED ✓" if pos_passed else "FAILED ✗"
    sections.append(f"**Status:** {pos_status}")
    sections.append("")

    median_pct = positive_metrics.get("median_percentile", 0.0) * 100
    sections.append("### Summary")
    sections.append(f"- Known genes expected: {positive_metrics.get('total_known_expected', 0)}")
    sections.append(f"- Known genes found: {positive_metrics.get('total_known_in_dataset', 0)}")
    sections.append(f"- Median percentile: {median_pct:.1f}%")
    sections.append(f"- Top quartile count: {positive_metrics.get('top_quartile_count', 0)}")
    sections.append(f"- Top quartile fraction: {positive_metrics.get('top_quartile_fraction', 0.0) * 100:.1f}%")
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
            count = metrics.get("count", 0)
            median = metrics.get("median_percentile")
            top_q = metrics.get("top_quartile_count", 0)

            if median is not None:
                median_str = f"{median * 100:.1f}%"
            else:
                median_str = "N/A"

            sections.append(f"| {source} | {count} | {median_str} | {top_q} |")

        sections.append("")

    # Verdict
    if pos_passed:
        sections.append("**Verdict:** Known cilia/Usher genes rank highly (median >= 75th percentile), validating scoring system sensitivity.")
    else:
        sections.append("**Verdict:** Known genes rank below expected threshold, suggesting potential issues with evidence layer weights or data quality.")

    sections.append("")

    # Section 2: Negative Control Validation
    sections.append("## 2. Negative Control Validation")
    sections.append("")

    neg_passed = negative_metrics.get("validation_passed", False)
    neg_status = "PASSED ✓" if neg_passed else "FAILED ✗"
    sections.append(f"**Status:** {neg_status}")
    sections.append("")

    neg_median_pct = negative_metrics.get("median_percentile", 0.0) * 100
    sections.append("### Summary")
    sections.append(f"- Housekeeping genes expected: {negative_metrics.get('total_expected', 0)}")
    sections.append(f"- Housekeeping genes found: {negative_metrics.get('total_in_dataset', 0)}")
    sections.append(f"- Median percentile: {neg_median_pct:.1f}%")
    sections.append(f"- Top quartile count: {negative_metrics.get('top_quartile_count', 0)}")
    sections.append(f"- High-tier count (score >= 0.70): {negative_metrics.get('in_high_tier_count', 0)}")
    sections.append("")

    # Verdict
    if neg_passed:
        sections.append("**Verdict:** Housekeeping genes rank LOW (median < 50th percentile), confirming scoring system specificity.")
    else:
        sections.append("**Verdict:** Housekeeping genes rank higher than expected, indicating potential lack of specificity.")

    sections.append("")

    # Section 3: Sensitivity Analysis
    sections.append("## 3. Sensitivity Analysis")
    sections.append("")

    sens_passed = sensitivity_summary.get("overall_stable", False)
    sens_status = "STABLE ✓" if sens_passed else "UNSTABLE ✗"
    sections.append(f"**Status:** {sens_status}")
    sections.append("")

    from usher_pipeline.scoring.sensitivity import STABILITY_THRESHOLD

    sections.append("### Summary")
    sections.append(f"- Total perturbations: {sensitivity_summary.get('total_perturbations', 0)}")
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
    sections.append("| Layer | Delta | Spearman rho | Stable? |")
    sections.append("|-------|-------|--------------|---------|")

    for result in sensitivity_result.get("results", []):
        layer = result["layer"]
        delta = result["delta"]
        rho = result["spearman_rho"]

        if rho is not None:
            stable_mark = "✓" if rho >= STABILITY_THRESHOLD else "✗"
            rho_str = f"{rho:.4f}"
        else:
            stable_mark = "N/A"
            rho_str = "N/A"

        sections.append(f"| {layer} | {delta:+.2f} | {rho_str} | {stable_mark} |")

    sections.append("")

    # Verdict
    if sens_passed:
        sections.append(f"**Verdict:** All weight perturbations (±5-10%) produce stable rankings (rho >= {STABILITY_THRESHOLD}), validating result robustness.")
    else:
        sections.append(f"**Verdict:** Some perturbations produce unstable rankings (rho < {STABILITY_THRESHOLD}), suggesting results may be sensitive to weight choices.")

    sections.append("")

    # Section 4: Overall Validation Summary
    sections.append("## 4. Overall Validation Summary")
    sections.append("")

    all_passed = pos_passed and neg_passed and sens_passed

    if all_passed:
        overall_status = "ALL VALIDATIONS PASSED ✓"
        overall_verdict = (
            "The scoring system demonstrates: (1) sensitivity to known cilia/Usher genes, "
            "(2) specificity against housekeeping genes, and (3) robustness to weight perturbations. "
            "Results are scientifically defensible."
        )
    elif pos_passed and neg_passed:
        overall_status = "PARTIAL PASS (Sensitivity Unstable)"
        overall_verdict = (
            "Positive and negative control validations passed, but rankings are sensitive to weight perturbations. "
            "Results are directionally correct but may require weight tuning for robustness."
        )
    elif pos_passed:
        overall_status = "PARTIAL PASS (Specificity Issue)"
        overall_verdict = (
            "Known genes rank highly, but housekeeping genes also rank higher than expected. "
            "Scoring system is sensitive but may lack specificity. Review evidence layer weights."
        )
    else:
        overall_status = "VALIDATION FAILED ✗"
        overall_verdict = (
            "Known genes do not rank highly, indicating fundamental issues with scoring system. "
            "Evidence layer weights or data quality require investigation."
        )

    sections.append(f"**Status:** {overall_status}")
    sections.append("")
    sections.append(f"**Verdict:** {overall_verdict}")
    sections.append("")

    sections.append("| Validation Prong | Status | Verdict |")
    sections.append("|------------------|--------|---------|")
    sections.append(f"| Positive Controls | {pos_status} | Known genes rank {'high' if pos_passed else 'low'} |")
    sections.append(f"| Negative Controls | {neg_status} | Housekeeping genes rank {'low' if neg_passed else 'high'} |")
    sections.append(f"| Sensitivity Analysis | {sens_status} | Rankings {'stable' if sens_passed else 'unstable'} under perturbations |")
    sections.append("")

    # Section 5: Weight Tuning Recommendations
    sections.append("## 5. Weight Tuning Recommendations")
    sections.append("")

    recommendations = recommend_weight_tuning(
        positive_metrics,
        negative_metrics,
        sensitivity_summary
    )

    sections.append(recommendations)

    report_text = "\n".join(sections)

    logger.info(
        "generate_comprehensive_validation_report_complete",
        positive_passed=pos_passed,
        negative_passed=neg_passed,
        sensitivity_stable=sens_passed,
        overall_status=overall_status,
    )

    return report_text


def recommend_weight_tuning(
    positive_metrics: dict,
    negative_metrics: dict,
    sensitivity_summary: dict,
) -> str:
    """
    Generate weight tuning recommendations based on validation results.

    Args:
        positive_metrics: Dict from validate_positive_controls_extended()
        negative_metrics: Dict from validate_negative_controls()
        sensitivity_summary: Dict from summarize_sensitivity()

    Returns:
        Formatted recommendation text

    Logic:
        - If all pass: No tuning recommended
        - If positive controls fail: Increase weights for layers where known genes score high
        - If negative controls fail: Examine layers boosting housekeeping genes
        - If sensitivity unstable: Reduce weight of most sensitive layer

    Notes:
        - CRITICAL: Any tuning is "post-validation" and risks circular validation
        - Flag this pitfall per research guidance
        - Recommendations are guidance, not automatic actions
    """
    logger.info("recommend_weight_tuning_start")

    pos_passed = positive_metrics.get("validation_passed", False)
    neg_passed = negative_metrics.get("validation_passed", False)
    sens_passed = sensitivity_summary.get("overall_stable", False)

    recommendations = []

    # All validations passed
    if pos_passed and neg_passed and sens_passed:
        recommendations.append("**Recommendation:** Current weights are validated. No tuning recommended.")
        recommendations.append("")
        recommendations.append(
            "The scoring system performs well across all validation prongs. "
            "Weights achieve good balance between sensitivity (known genes rank high), "
            "specificity (housekeeping genes rank low), and robustness (stable under perturbations)."
        )

        logger.info("recommend_weight_tuning_no_tuning_needed")
        return "\n".join(recommendations)

    # Some validations failed - provide targeted recommendations
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
        recommendations.append("- Review per-source breakdown to identify which gene sets validate poorly")
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
    if not sens_passed:
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

    # Add critical warning about circular validation
    recommendations.append("---")
    recommendations.append("")
    recommendations.append("### CRITICAL: Circular Validation Risk")
    recommendations.append("")
    recommendations.append(
        "**WARNING:** Any weight tuning based on these validation results constitutes "
        "\"post-validation tuning\" and introduces circular validation risk."
    )
    recommendations.append("")
    recommendations.append(
        "If weights are adjusted based on positive/negative control performance, the same controls "
        "CANNOT be used to validate the tuned weights (they were used to select the weights)."
    )
    recommendations.append("")
    recommendations.append("**Best Practices:**")
    recommendations.append("1. If tuning weights: Use independent validation set or cross-validation")
    recommendations.append("2. Document weight selection rationale (biological justification, not validation optimization)")
    recommendations.append("3. Prefer a priori weight choices over post-hoc tuning")
    recommendations.append("4. If tuning is essential, use hold-out validation genes not used in tuning")
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

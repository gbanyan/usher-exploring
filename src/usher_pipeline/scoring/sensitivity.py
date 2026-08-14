"""Parameter-sweep sensitivity analysis for internal evaluation."""

import polars as pl
import structlog
from scipy.stats import spearmanr

from usher_pipeline.config.schema import ScoringWeights
from usher_pipeline.persistence.duckdb_store import PipelineStore
from usher_pipeline.scoring.integration import compute_composite_scores

logger = structlog.get_logger(__name__)

# Evidence layer names (must match ScoringWeights fields)
EVIDENCE_LAYERS = [
    "gnomad",
    "expression",
    "annotation",
    "localization",
    "animal_model",
    "literature",
]

# Default perturbation deltas (absolute weight-point changes of ±0.05 and ±0.10)
DEFAULT_DELTAS = [-0.10, -0.05, 0.05, 0.10]

# Spearman correlation threshold for stability classification
STABILITY_THRESHOLD = 0.85


def _perturb_weight_values(
    baseline: ScoringWeights,
    layer: str,
    delta: float,
) -> tuple[dict[str, float], dict[str, float], float]:
    """Return raw and final weights for one perturbation.

    ``delta`` is applied to the selected baseline weight first.  Only after
    that raw change (and clamping to the valid interval) are all six weights
    divided by their new total.  Keeping both vectors makes the operation
    auditable instead of leaving the reported delta ambiguous.
    """
    if layer not in EVIDENCE_LAYERS:
        raise ValueError(
            f"Invalid layer '{layer}'. Must be one of {EVIDENCE_LAYERS}"
        )

    raw_weights = baseline.model_dump()
    raw_weights[layer] = max(0.0, min(1.0, raw_weights[layer] + delta))

    renormalization_total = sum(raw_weights[k] for k in EVIDENCE_LAYERS)
    if renormalization_total > 0:
        final_weights = {
            k: raw_weights[k] / renormalization_total for k in EVIDENCE_LAYERS
        }
    else:
        # This is only reachable for a malformed/extreme baseline, but keeps
        # the result deterministic and valid if it ever occurs.
        uniform = 1.0 / len(EVIDENCE_LAYERS)
        final_weights = {k: uniform for k in EVIDENCE_LAYERS}

    return raw_weights, final_weights, renormalization_total


def format_weight_vector(weights: dict[str, float], precision: int = 12) -> str:
    """Format all six final weights in a stable, explicit order."""
    return "[" + ", ".join(
        f"{layer}={weights[layer]:.{precision}f}" for layer in EVIDENCE_LAYERS
    ) + "]"


def perturb_weight(baseline: ScoringWeights, layer: str, delta: float) -> ScoringWeights:
    """
    Perturb a single weight and renormalize to maintain sum=1.0 constraint.

    Args:
        baseline: Baseline ScoringWeights instance
        layer: Evidence layer name to perturb (must be in EVIDENCE_LAYERS)
        delta: Perturbation amount (can be negative)

    Returns:
        New ScoringWeights instance with perturbed and renormalized weights

    Raises:
        ValueError: If layer not in EVIDENCE_LAYERS

    Notes:
        - Clamps perturbed weight to [0.0, 1.0] before renormalization
        - Renormalizes ALL weights so they sum to 1.0
        - Maintains weights.validate_sum() guarantee
    """
    _, final_weights, _ = _perturb_weight_values(baseline, layer, delta)
    return ScoringWeights(**final_weights)


def run_sensitivity_analysis(
    store: PipelineStore,
    baseline_weights: ScoringWeights,
    deltas: list[float] | None = None,
    top_n: int = 100,
) -> dict:
    """
    Run sensitivity analysis by perturbing each weight and measuring rank stability.

    For each layer and each raw delta, perturbs the weight, renormalizes all six
    weights, recomputes composite scores,
    and measures Spearman rank correlation on the top-N genes compared to baseline.

    Args:
        store: PipelineStore with evidence layer tables
        baseline_weights: Baseline ScoringWeights to perturb
        deltas: List of absolute weight-point changes (default: DEFAULT_DELTAS)
        top_n: Number of top-ranked genes to compare (default: 100)

    Returns:
        Dict with keys:
        - baseline_weights: dict - baseline weights as dict
        - results: list[dict] - per-perturbation results with:
            - layer: str
            - delta: float - raw change applied before renormalization
            - raw_weights: dict - six weights after raw delta and clamping
            - perturbed_weights: dict - final normalized six-weight vector
            - final_weights: dict - explicit alias for the final vector
            - renormalization_total: float
            - spearman_rho: float or None
            - spearman_pval: float or None
            - overlap_count: int - genes in both top-N lists
            - top_n_jaccard: float - Jaccard overlap of the two top-N lists
            - top_n: int
        - top_n: int
        - total_perturbations: int

    Notes:
        - compute_composite_scores re-queries DB each time (by design)
        - Spearman correlation is computed on composite_score of overlapping
          top-N genes, so it is a conditional top-list metric rather than a
          whole-universe rank test.
        - top_n_jaccard reports the set overlap of the two top-N lists.
        - The overlap denominator uses the actual sizes of both computed lists,
          not the requested top_n when fewer rows are available.
        - If overlap < 10 genes, records rho=None and logs warning
    """
    if top_n <= 0:
        raise ValueError("top_n must be greater than zero")

    if deltas is None:
        deltas = DEFAULT_DELTAS

    logger.info(
        "run_sensitivity_analysis_start",
        baseline_weights=baseline_weights.model_dump(),
        deltas=deltas,
        top_n=top_n,
        total_perturbations=len(EVIDENCE_LAYERS) * len(deltas),
    )

    # Compute baseline scores and get top-N genes
    baseline_scores = compute_composite_scores(store, baseline_weights)
    baseline_top_n = (
        baseline_scores
        .filter(pl.col("composite_score").is_not_null())
        .sort("composite_score", descending=True)
        .head(top_n)
        .select(["gene_symbol", "composite_score"])
        .rename({"composite_score": "baseline_score"})
    )

    results = []

    # For each layer, for each delta, compute perturbation
    for layer in EVIDENCE_LAYERS:
        for delta in deltas:
            # Apply the raw delta, then renormalize all six weights.  Keep both
            # stages in the result so the final vector can be reproduced.
            raw_weights, final_weights, renormalization_total = _perturb_weight_values(
                baseline_weights, layer, delta
            )
            perturbed_weights = ScoringWeights(**final_weights)

            # Compute perturbed scores
            perturbed_scores = compute_composite_scores(store, perturbed_weights)
            perturbed_top_n = (
                perturbed_scores
                .filter(pl.col("composite_score").is_not_null())
                .sort("composite_score", descending=True)
                .head(top_n)
                .select(["gene_symbol", "composite_score"])
                .rename({"composite_score": "perturbed_score"})
            )

            # Inner join to get overlapping genes
            joined = baseline_top_n.join(perturbed_top_n, on="gene_symbol", how="inner")
            overlap_count = joined.height
            union_count = (
                baseline_top_n.height + perturbed_top_n.height - overlap_count
            )
            top_n_jaccard = overlap_count / union_count if union_count else 1.0

            # Compute Spearman correlation if sufficient overlap
            if overlap_count < 10:
                logger.warning(
                    "run_sensitivity_analysis_low_overlap",
                    layer=layer,
                    delta=delta,
                    overlap_count=overlap_count,
                    message="Insufficient overlap for Spearman correlation (need >= 10)",
                )
                spearman_rho = None
                spearman_pval = None
            else:
                # Extract paired scores
                baseline_vals = joined["baseline_score"].to_numpy()
                perturbed_vals = joined["perturbed_score"].to_numpy()

                # Compute Spearman correlation
                rho, pval = spearmanr(baseline_vals, perturbed_vals)
                spearman_rho = float(rho)
                spearman_pval = float(pval)

            # Record result
            result = {
                "layer": layer,
                "delta": delta,
                "raw_weights": raw_weights,
                "perturbed_weights": perturbed_weights.model_dump(),
                "final_weights": final_weights,
                "renormalization_total": renormalization_total,
                "spearman_rho": spearman_rho,
                "spearman_pval": spearman_pval,
                "overlap_count": overlap_count,
                "top_n_jaccard": top_n_jaccard,
                "top_n": top_n,
                "baseline_top_n_count": baseline_top_n.height,
                "perturbed_top_n_count": perturbed_top_n.height,
                "top_n_union_count": union_count,
            }
            results.append(result)

            # Log each perturbation result
            logger.info(
                "run_sensitivity_analysis_perturbation",
                layer=layer,
                delta=f"{delta:+.2f}",
                spearman_rho=f"{spearman_rho:.4f}" if spearman_rho is not None else "N/A",
                spearman_pval=f"{spearman_pval:.4e}" if spearman_pval is not None else "N/A",
                overlap_count=overlap_count,
                stable=spearman_rho >= STABILITY_THRESHOLD if spearman_rho is not None else None,
            )

    logger.info(
        "run_sensitivity_analysis_complete",
        total_perturbations=len(results),
        layers=len(EVIDENCE_LAYERS),
        deltas=len(deltas),
    )

    return {
        "baseline_weights": baseline_weights.model_dump(),
        "results": results,
        "top_n": top_n,
        "total_perturbations": len(results),
    }


def summarize_sensitivity(analysis_result: dict) -> dict:
    """
    Summarize sensitivity analysis results with stability classification.

    Args:
        analysis_result: Dict returned from run_sensitivity_analysis()

    Returns:
        Dict with keys:
        - min_rho: float - minimum Spearman rho (excluding None)
        - max_rho: float - maximum Spearman rho (excluding None)
        - mean_rho: float - mean Spearman rho (excluding None)
        - stable_count: int - count of perturbations with rho >= STABILITY_THRESHOLD
        - unstable_count: int - count of perturbations with rho < STABILITY_THRESHOLD
        - total_perturbations: int
        - overall_stable: bool | None - None when no rho could be assessed
        - most_sensitive_layer: str - layer with lowest mean rho
        - most_robust_layer: str - layer with highest mean rho

    Notes:
        - Excludes None rho values from all statistics
        - most_sensitive/robust computed from per-layer mean rho
    """
    results = analysis_result["results"]

    # Filter out None rho values
    valid_results = [r for r in results if r["spearman_rho"] is not None]

    if not valid_results:
        # Edge case: all perturbations had insufficient overlap
        return {
            "min_rho": None,
            "max_rho": None,
            "mean_rho": None,
            "stable_count": 0,
            "unstable_count": 0,
            "total_perturbations": analysis_result["total_perturbations"],
            # No rho is evidence for an assessment gap, not instability.
            "overall_stable": None,
            "assessment_status": "unassessed" if results else "not_run",
            "assessed_count": 0,
            "unassessed_count": len(results),
            "most_sensitive_layer": None,
            "most_robust_layer": None,
        }

    # Compute global statistics
    rho_values = [r["spearman_rho"] for r in valid_results]
    min_rho = min(rho_values)
    max_rho = max(rho_values)
    mean_rho = sum(rho_values) / len(rho_values)

    # Count stable/unstable
    stable_count = sum(1 for rho in rho_values if rho >= STABILITY_THRESHOLD)
    unstable_count = len(rho_values) - stable_count

    # Overall stability: all non-None rhos must be >= threshold
    overall_stable = all(rho >= STABILITY_THRESHOLD for rho in rho_values)

    # Compute per-layer mean rho
    layer_rho_map = {}
    for layer in EVIDENCE_LAYERS:
        layer_results = [
            r["spearman_rho"]
            for r in valid_results
            if r["layer"] == layer and r["spearman_rho"] is not None
        ]
        if layer_results:
            layer_rho_map[layer] = sum(layer_results) / len(layer_results)

    # Find most sensitive (lowest mean rho) and most robust (highest mean rho)
    if layer_rho_map:
        most_sensitive_layer = min(layer_rho_map, key=layer_rho_map.get)
        most_robust_layer = max(layer_rho_map, key=layer_rho_map.get)
    else:
        most_sensitive_layer = None
        most_robust_layer = None

    return {
        "min_rho": min_rho,
        "max_rho": max_rho,
        "mean_rho": mean_rho,
        "stable_count": stable_count,
        "unstable_count": unstable_count,
        "total_perturbations": analysis_result["total_perturbations"],
        "overall_stable": overall_stable,
        "assessment_status": "assessed",
        "assessed_count": len(valid_results),
        "unassessed_count": len(results) - len(valid_results),
        "most_sensitive_layer": most_sensitive_layer,
        "most_robust_layer": most_robust_layer,
    }


def generate_sensitivity_report(analysis_result: dict, summary: dict) -> str:
    """
    Generate human-readable sensitivity analysis report.

    Args:
        analysis_result: Dict returned from run_sensitivity_analysis()
        summary: Dict returned from summarize_sensitivity()

    Returns:
        Multi-line text report with perturbation table and summary

    Notes:
        - Reports the raw delta and the final normalized vector separately
        - Shows table with Layer | Delta | Spearman rho | p-value | Overlap | Jaccard | Stable?
        - Includes interpretation text
    """
    sensitivity_state = summary.get("overall_stable")
    status = (
        "STABLE ✓" if sensitivity_state is True
        else "UNSTABLE ✗" if sensitivity_state is False
        else "UNASSESSED" if summary.get("assessment_status") == "unassessed" else "NOT RUN"
    )
    top_n = analysis_result.get("top_n", "N/A")
    baseline_weights = analysis_result.get("baseline_weights", {})

    report = [
        f"Sensitivity Analysis (raw delta then renormalization): {status}",
        "",
        "Summary:",
        f"  Total perturbations: {summary['total_perturbations']}",
        f"  Compared top list: {top_n} genes",
        "  Each raw delta is applied to one baseline weight, then all six weights are renormalized to sum to 1.0.",
        f"  Baseline final weights: {format_weight_vector(baseline_weights)}" if baseline_weights else "  Baseline final weights: N/A",
    ]
    if summary.get("assessment_status") == "unassessed":
        report.extend([
            "  Assessed perturbations: 0",
            f"  Unassessed perturbations: {summary.get('unassessed_count', summary.get('total_perturbations', 0))}",
        ])
    else:
        report.extend([
            f"  Stable perturbations: {summary['stable_count']} (rho >= {STABILITY_THRESHOLD})",
            f"  Unstable perturbations: {summary['unstable_count']}",
        ])
    report.extend([
        f"  Mean Spearman rho: {summary['mean_rho']:.4f}" if summary['mean_rho'] is not None else "  Mean Spearman rho: N/A",
        f"  Range: [{summary['min_rho']:.4f}, {summary['max_rho']:.4f}]" if summary['min_rho'] is not None else "  Range: N/A",
        "",
    ])

    # Add interpretation
    if sensitivity_state is True:
        report.append(
            f"All absolute weight-point perturbations produce stable rankings (rho >= {STABILITY_THRESHOLD}), "
            "supporting robustness for the tested perturbation set."
        )
    elif sensitivity_state is False:
        report.append(
            f"Warning: Some perturbations produce unstable rankings (rho < {STABILITY_THRESHOLD}). "
            "Results may be sensitive to weight choices."
        )
    elif summary.get("assessment_status") == "unassessed":
        report.append(
            "Sensitivity perturbations were run, but no Spearman rho was available "
            "for assessment; ranking stability is UNASSESSED in this report."
        )
    else:
        report.append("Sensitivity analysis was not run; ranking stability is not assessed in this report.")

    if summary["most_sensitive_layer"] and summary["most_robust_layer"]:
        report.append("")
        report.append(f"  Most sensitive layer: {summary['most_sensitive_layer']}")
        report.append(f"  Most robust layer: {summary['most_robust_layer']}")

    report.append("")
    report.append("Perturbation Results:")
    report.append("-" * 100)
    report.append(f"{'Layer':<15} {'Raw Δ':>8} {'Spearman rho':>14} {'p-value':>12} {'Overlap':>10} {'Jaccard':>10} {'Stable?':>10}")
    report.append("-" * 100)

    for result in analysis_result["results"]:
        layer = result["layer"]
        delta = result["delta"]
        rho = result["spearman_rho"]
        pval = result.get("spearman_pval")
        overlap = result.get("overlap_count", "N/A")
        jaccard = result.get("top_n_jaccard")

        if rho is not None:
            stable_mark = "✓" if rho >= STABILITY_THRESHOLD else "✗"
            rho_str = f"{rho:.4f}"
            pval_str = f"{pval:.2e}" if pval is not None else "N/A"
        else:
            stable_mark = "N/A"
            rho_str = "N/A"
            pval_str = "N/A"

        jaccard_str = f"{jaccard:.3f}" if jaccard is not None else "N/A"

        report.append(
            f"{layer:<15} {delta:>+8.2f} {rho_str:>14} {pval_str:>12} {overlap:>10} {jaccard_str:>10} {stable_mark:>10}"
        )

    report.extend([
        "",
        "Final normalized six-weight vectors:",
        f"(Order: {', '.join(EVIDENCE_LAYERS)}; values are after renormalization.)",
        "| Layer | Raw Δ | Final normalized weights |",
        "|-------|-------|--------------------------|",
    ])
    for result in analysis_result.get("results", []):
        final_weights = result.get("final_weights") or result.get("perturbed_weights", {})
        vector = (
            format_weight_vector(final_weights)
            if all(layer in final_weights for layer in EVIDENCE_LAYERS)
            else "N/A"
        )
        report.append(
            f"| {result['layer']} | {result['delta']:+.2f} | "
            f"{vector} |"
        )

    return "\n".join(report)

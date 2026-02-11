"""Parameter sweep sensitivity analysis for scoring weight validation."""

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

# Default perturbation deltas (±5% and ±10%)
DEFAULT_DELTAS = [-0.10, -0.05, 0.05, 0.10]

# Spearman correlation threshold for stability classification
STABILITY_THRESHOLD = 0.85


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
    if layer not in EVIDENCE_LAYERS:
        raise ValueError(
            f"Invalid layer '{layer}'. Must be one of {EVIDENCE_LAYERS}"
        )

    # Get baseline weights as dict
    w_dict = baseline.model_dump()

    # Apply perturbation with clamping
    w_dict[layer] = max(0.0, min(1.0, w_dict[layer] + delta))

    # Renormalize to sum=1.0
    total = sum(w_dict[k] for k in EVIDENCE_LAYERS)
    if total > 0:
        for k in EVIDENCE_LAYERS:
            w_dict[k] = w_dict[k] / total
    else:
        # Edge case: all weights became zero (should not happen in practice)
        # Revert to uniform distribution
        uniform = 1.0 / len(EVIDENCE_LAYERS)
        for k in EVIDENCE_LAYERS:
            w_dict[k] = uniform

    # Return new ScoringWeights instance
    return ScoringWeights(**w_dict)


def run_sensitivity_analysis(
    store: PipelineStore,
    baseline_weights: ScoringWeights,
    deltas: list[float] | None = None,
    top_n: int = 100,
) -> dict:
    """
    Run sensitivity analysis by perturbing each weight and measuring rank stability.

    For each layer and each delta, perturbs the weight, recomputes composite scores,
    and measures Spearman rank correlation on the top-N genes compared to baseline.

    Args:
        store: PipelineStore with evidence layer tables
        baseline_weights: Baseline ScoringWeights to perturb
        deltas: List of perturbation amounts (default: DEFAULT_DELTAS)
        top_n: Number of top-ranked genes to compare (default: 100)

    Returns:
        Dict with keys:
        - baseline_weights: dict - baseline weights as dict
        - results: list[dict] - per-perturbation results with:
            - layer: str
            - delta: float
            - perturbed_weights: dict
            - spearman_rho: float or None
            - spearman_pval: float or None
            - overlap_count: int - genes in both top-N lists
            - top_n: int
        - top_n: int
        - total_perturbations: int

    Notes:
        - compute_composite_scores re-queries DB each time (by design)
        - Spearman correlation computed on composite_score of overlapping genes
        - If overlap < 10 genes, records rho=None and logs warning
    """
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
            # Create perturbed weights
            perturbed_weights = perturb_weight(baseline_weights, layer, delta)

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
                "perturbed_weights": perturbed_weights.model_dump(),
                "spearman_rho": spearman_rho,
                "spearman_pval": spearman_pval,
                "overlap_count": overlap_count,
                "top_n": top_n,
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
        - overall_stable: bool - True if all non-None rhos >= STABILITY_THRESHOLD
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
            "overall_stable": False,
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
        - Follows formatting pattern from generate_validation_report()
        - Shows table with Layer | Delta | Spearman rho | p-value | Stable?
        - Includes interpretation text
    """
    status = "STABLE ✓" if summary["overall_stable"] else "UNSTABLE ✗"

    report = [
        f"Sensitivity Analysis: {status}",
        "",
        "Summary:",
        f"  Total perturbations: {summary['total_perturbations']}",
        f"  Stable perturbations: {summary['stable_count']} (rho >= {STABILITY_THRESHOLD})",
        f"  Unstable perturbations: {summary['unstable_count']}",
        f"  Mean Spearman rho: {summary['mean_rho']:.4f}" if summary['mean_rho'] is not None else "  Mean Spearman rho: N/A",
        f"  Range: [{summary['min_rho']:.4f}, {summary['max_rho']:.4f}]" if summary['min_rho'] is not None else "  Range: N/A",
        "",
    ]

    # Add interpretation
    if summary["overall_stable"]:
        report.append(
            f"All weight perturbations (±5-10%) produce stable rankings (rho >= {STABILITY_THRESHOLD}), "
            "validating result robustness."
        )
    else:
        report.append(
            f"Warning: Some perturbations produce unstable rankings (rho < {STABILITY_THRESHOLD}). "
            "Results may be sensitive to weight choices."
        )

    if summary["most_sensitive_layer"] and summary["most_robust_layer"]:
        report.append("")
        report.append(f"  Most sensitive layer: {summary['most_sensitive_layer']}")
        report.append(f"  Most robust layer: {summary['most_robust_layer']}")

    report.append("")
    report.append("Perturbation Results:")
    report.append("-" * 100)
    report.append(f"{'Layer':<15} {'Delta':>8} {'Spearman rho':>14} {'p-value':>12} {'Overlap':>10} {'Stable?':>10}")
    report.append("-" * 100)

    for result in analysis_result["results"]:
        layer = result["layer"]
        delta = result["delta"]
        rho = result["spearman_rho"]
        pval = result["spearman_pval"]
        overlap = result["overlap_count"]

        if rho is not None:
            stable_mark = "✓" if rho >= STABILITY_THRESHOLD else "✗"
            rho_str = f"{rho:.4f}"
            pval_str = f"{pval:.2e}"
        else:
            stable_mark = "N/A"
            rho_str = "N/A"
            pval_str = "N/A"

        report.append(
            f"{layer:<15} {delta:>+8.2f} {rho_str:>14} {pval_str:>12} {overlap:>10} {stable_mark:>10}"
        )

    return "\n".join(report)

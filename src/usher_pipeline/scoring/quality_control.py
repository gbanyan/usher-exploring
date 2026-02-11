"""Quality control checks for scoring results."""

import numpy as np
import polars as pl
import structlog
from scipy.stats import median_abs_deviation

from usher_pipeline.persistence.duckdb_store import PipelineStore

logger = structlog.get_logger(__name__)

# Quality control thresholds
MISSING_RATE_WARN = 0.5  # 50% missing = warning
MISSING_RATE_ERROR = 0.8  # 80% missing = error
MIN_STD_THRESHOLD = 0.01  # std < 0.01 = no variation warning
OUTLIER_MAD_THRESHOLD = 3.0  # >3 MAD from median = outlier

# Evidence layer configuration
EVIDENCE_LAYERS = [
    "gnomad",
    "expression",
    "annotation",
    "localization",
    "animal_model",
    "literature"
]

SCORE_COLUMNS = {
    "gnomad": "gnomad_score",
    "expression": "expression_score",
    "annotation": "annotation_score",
    "localization": "localization_score",
    "animal_model": "animal_model_score",
    "literature": "literature_score",
}


def compute_missing_data_rates(store: PipelineStore) -> dict:
    """
    Compute fraction of NULL values per score column in scored_genes.

    Args:
        store: PipelineStore with scored_genes table

    Returns:
        Dict with keys:
        - rates: dict[str, float] - NULL rate per layer (0.0-1.0)
        - warnings: list[str] - layers with >50% missing
        - errors: list[str] - layers with >80% missing

    Notes:
        - Queries scored_genes table
        - Classifies: rate > 0.8 -> error, rate > 0.5 -> warning
        - Logs each layer's rate with appropriate level
    """
    # Query missing data rates in a single SQL query
    query = f"""
    SELECT
        COUNT(*) AS total,
        AVG(CASE WHEN {SCORE_COLUMNS['gnomad']} IS NULL THEN 1.0 ELSE 0.0 END) AS gnomad_missing,
        AVG(CASE WHEN {SCORE_COLUMNS['expression']} IS NULL THEN 1.0 ELSE 0.0 END) AS expression_missing,
        AVG(CASE WHEN {SCORE_COLUMNS['annotation']} IS NULL THEN 1.0 ELSE 0.0 END) AS annotation_missing,
        AVG(CASE WHEN {SCORE_COLUMNS['localization']} IS NULL THEN 1.0 ELSE 0.0 END) AS localization_missing,
        AVG(CASE WHEN {SCORE_COLUMNS['animal_model']} IS NULL THEN 1.0 ELSE 0.0 END) AS animal_model_missing,
        AVG(CASE WHEN {SCORE_COLUMNS['literature']} IS NULL THEN 1.0 ELSE 0.0 END) AS literature_missing
    FROM scored_genes
    """

    result = store.conn.execute(query).fetchone()
    total_genes = result[0]

    # Build rates dict
    rates = {
        "gnomad": result[1],
        "expression": result[2],
        "annotation": result[3],
        "localization": result[4],
        "animal_model": result[5],
        "literature": result[6],
    }

    warnings = []
    errors = []

    # Classify and log each layer
    for layer, rate in rates.items():
        if rate > MISSING_RATE_ERROR:
            errors.append(f"{layer}: {rate:.1%} missing")
            logger.error(
                "missing_data_error",
                layer=layer,
                missing_rate=f"{rate:.1%}",
                threshold=f"{MISSING_RATE_ERROR:.0%}",
            )
        elif rate > MISSING_RATE_WARN:
            warnings.append(f"{layer}: {rate:.1%} missing")
            logger.warning(
                "missing_data_warning",
                layer=layer,
                missing_rate=f"{rate:.1%}",
                threshold=f"{MISSING_RATE_WARN:.0%}",
            )
        else:
            logger.info(
                "missing_data_ok",
                layer=layer,
                missing_rate=f"{rate:.1%}",
            )

    logger.info(
        "compute_missing_data_rates_complete",
        total_genes=total_genes,
        warnings_count=len(warnings),
        errors_count=len(errors),
    )

    return {
        "rates": rates,
        "warnings": warnings,
        "errors": errors,
    }


def compute_distribution_stats(store: PipelineStore) -> dict:
    """
    Compute distribution statistics per evidence layer.

    Args:
        store: PipelineStore with scored_genes table

    Returns:
        Dict with keys:
        - distributions: dict[str, dict] - stats per layer (mean, median, std, min, max)
        - warnings: list[str] - layers with anomalies (no variation)
        - errors: list[str] - layers with out-of-range values

    Notes:
        - Computes stats only on non-NULL scores
        - Detects: std < 0.01 -> no variation warning
        - Detects: min < 0.0 or max > 1.0 -> out of range error
    """
    distributions = {}
    warnings = []
    errors = []

    for layer in EVIDENCE_LAYERS:
        col = SCORE_COLUMNS[layer]

        # Query non-NULL scores for this layer
        query = f"SELECT {col} FROM scored_genes WHERE {col} IS NOT NULL"
        result = store.conn.execute(query).fetchall()

        if not result:
            distributions[layer] = None
            warnings.append(f"{layer}: no data available")
            logger.warning("distribution_no_data", layer=layer)
            continue

        # Extract scores as numpy array
        scores = np.array([row[0] for row in result])

        # Compute statistics
        stats = {
            "mean": float(np.mean(scores)),
            "median": float(np.median(scores)),
            "std": float(np.std(scores)),
            "min": float(np.min(scores)),
            "max": float(np.max(scores)),
            "count": len(scores),
        }

        distributions[layer] = stats

        # Detect anomalies
        if stats["std"] < MIN_STD_THRESHOLD:
            warnings.append(f"{layer}: no variation (std={stats['std']:.4f})")
            logger.warning(
                "distribution_no_variation",
                layer=layer,
                std=f"{stats['std']:.4f}",
                threshold=MIN_STD_THRESHOLD,
            )

        if stats["min"] < 0.0 or stats["max"] > 1.0:
            errors.append(
                f"{layer}: out of range (min={stats['min']:.4f}, max={stats['max']:.4f})"
            )
            logger.error(
                "distribution_out_of_range",
                layer=layer,
                min=f"{stats['min']:.4f}",
                max=f"{stats['max']:.4f}",
            )

        logger.info(
            "distribution_stats",
            layer=layer,
            mean=f"{stats['mean']:.4f}",
            median=f"{stats['median']:.4f}",
            std=f"{stats['std']:.4f}",
            range=f"[{stats['min']:.4f}, {stats['max']:.4f}]",
        )

    logger.info(
        "compute_distribution_stats_complete",
        layers_processed=len(EVIDENCE_LAYERS),
        warnings_count=len(warnings),
        errors_count=len(errors),
    )

    return {
        "distributions": distributions,
        "warnings": warnings,
        "errors": errors,
    }


def detect_outliers(store: PipelineStore) -> dict:
    """
    Detect outlier genes using MAD-based robust detection.

    Uses Median Absolute Deviation (MAD) to identify genes with scores
    > 3 MAD from the median per evidence layer.

    Args:
        store: PipelineStore with scored_genes table

    Returns:
        Dict with keys per layer:
        - count: int - number of outliers detected
        - example_genes: list[str] - up to 5 gene symbols

    Notes:
        - Computes MAD = median(|scores - median(scores)|)
        - If MAD == 0 (no variation), skip outlier detection
        - Flags genes where |score - median| > 3 * MAD
    """
    outliers = {}

    for layer in EVIDENCE_LAYERS:
        col = SCORE_COLUMNS[layer]

        # Query gene_symbol and score for non-NULL scores
        query = f"""
        SELECT gene_symbol, {col} as score
        FROM scored_genes
        WHERE {col} IS NOT NULL
        """
        result = store.conn.execute(query).pl()

        if result.height == 0:
            outliers[layer] = {"count": 0, "example_genes": []}
            continue

        # Extract scores as numpy array
        scores = result["score"].to_numpy()
        median = np.median(scores)

        # Compute MAD using scipy
        mad = median_abs_deviation(scores, scale="normal")

        # If MAD is zero (no variation), skip outlier detection
        if mad == 0 or np.isclose(mad, 0):
            outliers[layer] = {"count": 0, "example_genes": []}
            logger.info(
                "outlier_detection_skipped",
                layer=layer,
                reason="no_variation",
                mad=0,
            )
            continue

        # Flag outliers: |score - median| > threshold * MAD
        deviations = np.abs(scores - median)
        is_outlier = deviations > (OUTLIER_MAD_THRESHOLD * mad)

        # Get outlier genes
        outlier_genes = result.filter(pl.Series(is_outlier))["gene_symbol"].to_list()
        outlier_count = len(outlier_genes)

        outliers[layer] = {
            "count": outlier_count,
            "example_genes": outlier_genes[:5],  # Limit to 5 examples
        }

        if outlier_count > 0:
            logger.info(
                "outliers_detected",
                layer=layer,
                count=outlier_count,
                mad=f"{mad:.4f}",
                threshold=OUTLIER_MAD_THRESHOLD,
                examples=outlier_genes[:5],
            )
        else:
            logger.info(
                "no_outliers_detected",
                layer=layer,
                mad=f"{mad:.4f}",
            )

    return outliers


def run_qc_checks(store: PipelineStore) -> dict:
    """
    Orchestrate all quality control checks.

    Runs missing data, distribution stats, outlier detection, and
    composite score analysis.

    Args:
        store: PipelineStore with scored_genes table

    Returns:
        Dict with keys:
        - missing_data: dict from compute_missing_data_rates()
        - distributions: dict from compute_distribution_stats()
        - outliers: dict from detect_outliers()
        - composite_stats: dict with composite score statistics
        - warnings: list[str] - combined warnings from all checks
        - errors: list[str] - combined errors from all checks
        - passed: bool - True if no errors

    Notes:
        - Validates scored_genes table exists
        - Logs final QC summary with pass/fail status
    """
    logger.info("run_qc_checks_start")

    # Run all three checks
    missing_data = compute_missing_data_rates(store)
    distributions = compute_distribution_stats(store)
    outliers = detect_outliers(store)

    # Compute composite score statistics
    query = """
    SELECT
        AVG(composite_score) AS mean,
        MEDIAN(composite_score) AS median,
        STDDEV(composite_score) AS std,
        MIN(composite_score) AS min,
        MAX(composite_score) AS max,
        PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY composite_score) AS p10,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY composite_score) AS p25,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY composite_score) AS p50,
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY composite_score) AS p75,
        PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY composite_score) AS p90,
        COUNT(*) AS total,
        COUNT(composite_score) AS non_null
    FROM scored_genes
    """
    result = store.conn.execute(query).fetchone()

    composite_stats = {
        "mean": result[0],
        "median": result[1],
        "std": result[2],
        "min": result[3],
        "max": result[4],
        "p10": result[5],
        "p25": result[6],
        "p50": result[7],
        "p75": result[8],
        "p90": result[9],
        "total_genes": result[10],
        "non_null_count": result[11],
    }

    logger.info(
        "composite_score_stats",
        mean=f"{composite_stats['mean']:.4f}" if composite_stats['mean'] else "N/A",
        median=f"{composite_stats['median']:.4f}" if composite_stats['median'] else "N/A",
        std=f"{composite_stats['std']:.4f}" if composite_stats['std'] else "N/A",
        percentiles={
            "p10": f"{composite_stats['p10']:.4f}" if composite_stats['p10'] else "N/A",
            "p25": f"{composite_stats['p25']:.4f}" if composite_stats['p25'] else "N/A",
            "p50": f"{composite_stats['p50']:.4f}" if composite_stats['p50'] else "N/A",
            "p75": f"{composite_stats['p75']:.4f}" if composite_stats['p75'] else "N/A",
            "p90": f"{composite_stats['p90']:.4f}" if composite_stats['p90'] else "N/A",
        },
        coverage=f"{composite_stats['non_null_count']}/{composite_stats['total_genes']}",
    )

    # Combine warnings and errors
    combined_warnings = (
        missing_data["warnings"] +
        distributions["warnings"]
    )

    combined_errors = (
        missing_data["errors"] +
        distributions["errors"]
    )

    passed = len(combined_errors) == 0

    logger.info(
        "run_qc_checks_complete",
        total_warnings=len(combined_warnings),
        total_errors=len(combined_errors),
        status="PASSED" if passed else "FAILED",
    )

    return {
        "missing_data": missing_data,
        "distributions": distributions,
        "outliers": outliers,
        "composite_stats": composite_stats,
        "warnings": combined_warnings,
        "errors": combined_errors,
        "passed": passed,
    }

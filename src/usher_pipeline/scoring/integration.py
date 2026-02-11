"""Multi-evidence weighted scoring integration with NULL preservation."""

import duckdb
import polars as pl
import structlog

from usher_pipeline.config.schema import ScoringWeights
from usher_pipeline.persistence.duckdb_store import PipelineStore

logger = structlog.get_logger(__name__)


def join_evidence_layers(store: PipelineStore) -> pl.DataFrame:
    """
    Join gene_universe with all 6 evidence tables on gene_id.

    Performs LEFT JOIN to preserve all genes from gene_universe, even those
    without evidence in some or all layers. NULL scores indicate missing
    evidence, which is semantically distinct from zero scores.

    Args:
        store: PipelineStore with database connection

    Returns:
        DataFrame with columns:
        - gene_id (str)
        - gene_symbol (str)
        - gnomad_score (float, nullable)
        - expression_score (float, nullable)
        - annotation_score (float, nullable)
        - localization_score (float, nullable)
        - animal_model_score (float, nullable)
        - literature_score (float, nullable)
        - evidence_count (int): count of non-NULL scores

    Notes:
        - Uses LEFT JOIN pattern to preserve NULLs
        - evidence_count = sum of non-NULL layers (0-6)
    """
    query = """
    SELECT
        g.gene_id,
        g.gene_symbol,
        gnomad.loeuf_normalized AS gnomad_score,
        expr.expression_score_normalized AS expression_score,
        annot.annotation_score_normalized AS annotation_score,
        loc.localization_score_normalized AS localization_score,
        animal.animal_model_score_normalized AS animal_model_score,
        lit.literature_score_normalized AS literature_score,
        (
            CASE WHEN gnomad.loeuf_normalized IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN expr.expression_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN annot.annotation_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN loc.localization_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN animal.animal_model_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN lit.literature_score_normalized IS NOT NULL THEN 1 ELSE 0 END
        ) AS evidence_count
    FROM gene_universe g
    LEFT JOIN gnomad_constraint gnomad ON g.gene_id = gnomad.gene_id
    LEFT JOIN tissue_expression expr ON g.gene_id = expr.gene_id
    LEFT JOIN annotation_completeness annot ON g.gene_id = annot.gene_id
    LEFT JOIN subcellular_localization loc ON g.gene_id = loc.gene_id
    LEFT JOIN animal_model_phenotypes animal ON g.gene_id = animal.gene_id
    LEFT JOIN literature_evidence lit ON g.gene_id = lit.gene_id
    """

    # Execute query and convert to polars
    result = store.conn.execute(query).pl()

    # Log summary statistics
    total_genes = result.height
    mean_evidence = result["evidence_count"].mean()

    # Calculate NULL rates per layer
    null_rates = {
        "gnomad": result["gnomad_score"].null_count() / total_genes,
        "expression": result["expression_score"].null_count() / total_genes,
        "annotation": result["annotation_score"].null_count() / total_genes,
        "localization": result["localization_score"].null_count() / total_genes,
        "animal_model": result["animal_model_score"].null_count() / total_genes,
        "literature": result["literature_score"].null_count() / total_genes,
    }

    logger.info(
        "join_evidence_layers_complete",
        total_genes=total_genes,
        mean_evidence_count=f"{mean_evidence:.2f}",
        null_rates={k: f"{v:.2%}" for k, v in null_rates.items()},
    )

    return result


def compute_composite_scores(store: PipelineStore, weights: ScoringWeights) -> pl.DataFrame:
    """
    Compute weighted composite scores from multiple evidence layers.

    Uses NULL-preserving weighted average: only available evidence contributes
    to the composite score. Genes without any evidence receive NULL (not zero).

    Formula:
        composite_score = weighted_sum / available_weight
        where:
            weighted_sum = sum(score_i * weight_i) for non-NULL scores
            available_weight = sum(weight_i) for non-NULL scores

    Args:
        store: PipelineStore with database connection
        weights: ScoringWeights instance (must sum to 1.0)

    Returns:
        DataFrame with columns:
        - gene_id, gene_symbol
        - All 6 individual layer scores (nullable)
        - composite_score (float, nullable)
        - quality_flag (str): sufficient/moderate/sparse/no_evidence
        - Per-layer contribution columns (score * weight, nullable)
        - evidence_count (int): count of non-NULL scores

    Raises:
        ValueError: If weights do not sum to 1.0

    Notes:
        - Validates weight sum before computing scores
        - NULL scores do NOT contribute to weighted average
        - quality_flag based on evidence_count thresholds
        - Ordered by composite_score DESC NULLS LAST
    """
    # Validate weights first
    weights.validate_sum()

    query = f"""
    SELECT
        g.gene_id,
        g.gene_symbol,
        gnomad.loeuf_normalized AS gnomad_score,
        expr.expression_score_normalized AS expression_score,
        annot.annotation_score_normalized AS annotation_score,
        loc.localization_score_normalized AS localization_score,
        animal.animal_model_score_normalized AS animal_model_score,
        lit.literature_score_normalized AS literature_score,
        (
            CASE WHEN gnomad.loeuf_normalized IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN expr.expression_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN annot.annotation_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN loc.localization_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN animal.animal_model_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
            CASE WHEN lit.literature_score_normalized IS NOT NULL THEN 1 ELSE 0 END
        ) AS evidence_count,
        (
            CASE WHEN gnomad.loeuf_normalized IS NOT NULL THEN {weights.gnomad} ELSE 0 END +
            CASE WHEN expr.expression_score_normalized IS NOT NULL THEN {weights.expression} ELSE 0 END +
            CASE WHEN annot.annotation_score_normalized IS NOT NULL THEN {weights.annotation} ELSE 0 END +
            CASE WHEN loc.localization_score_normalized IS NOT NULL THEN {weights.localization} ELSE 0 END +
            CASE WHEN animal.animal_model_score_normalized IS NOT NULL THEN {weights.animal_model} ELSE 0 END +
            CASE WHEN lit.literature_score_normalized IS NOT NULL THEN {weights.literature} ELSE 0 END
        ) AS available_weight,
        (
            COALESCE(gnomad.loeuf_normalized * {weights.gnomad}, 0) +
            COALESCE(expr.expression_score_normalized * {weights.expression}, 0) +
            COALESCE(annot.annotation_score_normalized * {weights.annotation}, 0) +
            COALESCE(loc.localization_score_normalized * {weights.localization}, 0) +
            COALESCE(animal.animal_model_score_normalized * {weights.animal_model}, 0) +
            COALESCE(lit.literature_score_normalized * {weights.literature}, 0)
        ) AS weighted_sum,
        CASE
            WHEN (
                CASE WHEN gnomad.loeuf_normalized IS NOT NULL THEN {weights.gnomad} ELSE 0 END +
                CASE WHEN expr.expression_score_normalized IS NOT NULL THEN {weights.expression} ELSE 0 END +
                CASE WHEN annot.annotation_score_normalized IS NOT NULL THEN {weights.annotation} ELSE 0 END +
                CASE WHEN loc.localization_score_normalized IS NOT NULL THEN {weights.localization} ELSE 0 END +
                CASE WHEN animal.animal_model_score_normalized IS NOT NULL THEN {weights.animal_model} ELSE 0 END +
                CASE WHEN lit.literature_score_normalized IS NOT NULL THEN {weights.literature} ELSE 0 END
            ) > 0 THEN (
                COALESCE(gnomad.loeuf_normalized * {weights.gnomad}, 0) +
                COALESCE(expr.expression_score_normalized * {weights.expression}, 0) +
                COALESCE(annot.annotation_score_normalized * {weights.annotation}, 0) +
                COALESCE(loc.localization_score_normalized * {weights.localization}, 0) +
                COALESCE(animal.animal_model_score_normalized * {weights.animal_model}, 0) +
                COALESCE(lit.literature_score_normalized * {weights.literature}, 0)
            ) / (
                CASE WHEN gnomad.loeuf_normalized IS NOT NULL THEN {weights.gnomad} ELSE 0 END +
                CASE WHEN expr.expression_score_normalized IS NOT NULL THEN {weights.expression} ELSE 0 END +
                CASE WHEN annot.annotation_score_normalized IS NOT NULL THEN {weights.annotation} ELSE 0 END +
                CASE WHEN loc.localization_score_normalized IS NOT NULL THEN {weights.localization} ELSE 0 END +
                CASE WHEN animal.animal_model_score_normalized IS NOT NULL THEN {weights.animal_model} ELSE 0 END +
                CASE WHEN lit.literature_score_normalized IS NOT NULL THEN {weights.literature} ELSE 0 END
            )
            ELSE NULL
        END AS composite_score,
        CASE
            WHEN (
                CASE WHEN gnomad.loeuf_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN expr.expression_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN annot.annotation_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN loc.localization_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN animal.animal_model_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN lit.literature_score_normalized IS NOT NULL THEN 1 ELSE 0 END
            ) >= 4 THEN 'sufficient_evidence'
            WHEN (
                CASE WHEN gnomad.loeuf_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN expr.expression_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN annot.annotation_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN loc.localization_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN animal.animal_model_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN lit.literature_score_normalized IS NOT NULL THEN 1 ELSE 0 END
            ) >= 2 THEN 'moderate_evidence'
            WHEN (
                CASE WHEN gnomad.loeuf_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN expr.expression_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN annot.annotation_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN loc.localization_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN animal.animal_model_score_normalized IS NOT NULL THEN 1 ELSE 0 END +
                CASE WHEN lit.literature_score_normalized IS NOT NULL THEN 1 ELSE 0 END
            ) >= 1 THEN 'sparse_evidence'
            ELSE 'no_evidence'
        END AS quality_flag,
        -- Per-layer contributions (NULL if score is NULL)
        CASE WHEN gnomad.loeuf_normalized IS NOT NULL THEN gnomad.loeuf_normalized * {weights.gnomad} ELSE NULL END AS gnomad_contribution,
        CASE WHEN expr.expression_score_normalized IS NOT NULL THEN expr.expression_score_normalized * {weights.expression} ELSE NULL END AS expression_contribution,
        CASE WHEN annot.annotation_score_normalized IS NOT NULL THEN annot.annotation_score_normalized * {weights.annotation} ELSE NULL END AS annotation_contribution,
        CASE WHEN loc.localization_score_normalized IS NOT NULL THEN loc.localization_score_normalized * {weights.localization} ELSE NULL END AS localization_contribution,
        CASE WHEN animal.animal_model_score_normalized IS NOT NULL THEN animal.animal_model_score_normalized * {weights.animal_model} ELSE NULL END AS animal_model_contribution,
        CASE WHEN lit.literature_score_normalized IS NOT NULL THEN lit.literature_score_normalized * {weights.literature} ELSE NULL END AS literature_contribution
    FROM gene_universe g
    LEFT JOIN gnomad_constraint gnomad ON g.gene_id = gnomad.gene_id
    LEFT JOIN tissue_expression expr ON g.gene_id = expr.gene_id
    LEFT JOIN annotation_completeness annot ON g.gene_id = annot.gene_id
    LEFT JOIN subcellular_localization loc ON g.gene_id = loc.gene_id
    LEFT JOIN animal_model_phenotypes animal ON g.gene_id = animal.gene_id
    LEFT JOIN literature_evidence lit ON g.gene_id = lit.gene_id
    ORDER BY composite_score DESC NULLS LAST
    """

    # Execute query and convert to polars
    result = store.conn.execute(query).pl()

    # Log summary statistics
    total_genes = result.height
    genes_with_score = result.filter(pl.col("composite_score").is_not_null()).height

    # Calculate mean/median for non-NULL scores
    non_null_scores = result.filter(pl.col("composite_score").is_not_null())["composite_score"]
    mean_score = non_null_scores.mean() if len(non_null_scores) > 0 else None
    median_score = non_null_scores.median() if len(non_null_scores) > 0 else None

    # Quality flag distribution
    quality_dist = result.group_by("quality_flag").agg(pl.count()).sort("quality_flag")

    logger.info(
        "compute_composite_scores_complete",
        total_genes=total_genes,
        genes_with_score=genes_with_score,
        coverage_pct=f"{genes_with_score / total_genes * 100:.1f}%",
        mean_score=f"{mean_score:.4f}" if mean_score is not None else "N/A",
        median_score=f"{median_score:.4f}" if median_score is not None else "N/A",
        quality_distribution=quality_dist.to_dicts(),
    )

    return result


def persist_scored_genes(store: PipelineStore, scored_df: pl.DataFrame, weights: ScoringWeights) -> None:
    """
    Persist scored genes DataFrame to DuckDB.

    Args:
        store: PipelineStore for database access
        scored_df: DataFrame from compute_composite_scores()
        weights: ScoringWeights used for scoring (logged in metadata)

    Notes:
        - Saves to table: scored_genes
        - Replaces existing table if present
        - Logs quality flag distribution and row count
    """
    # Save to DuckDB
    store.save_dataframe(
        df=scored_df,
        table_name="scored_genes",
        description="Multi-evidence weighted composite scores with per-layer contributions",
        replace=True,
    )

    # Log quality flag distribution
    quality_dist = scored_df.group_by("quality_flag").agg(pl.count()).sort("quality_flag")

    logger.info(
        "persist_scored_genes_complete",
        row_count=scored_df.height,
        quality_distribution=quality_dist.to_dicts(),
        weights={
            "gnomad": weights.gnomad,
            "expression": weights.expression,
            "annotation": weights.annotation,
            "localization": weights.localization,
            "animal_model": weights.animal_model,
            "literature": weights.literature,
        },
    )

"""Explore expression/protein gates for prioritizing the current HIGH tier.

This is deliberately an analysis-only tool: it never modifies ``scored_genes``
or the production confidence tiers.  It writes a gene-level comparison table
and a Markdown summary so proposed gates can be judged by shortlist size,
positive-control retention, and missing-data coverage.

Run:
    .venv/bin/python scripts/expression_shortlist.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import polars as pl

from usher_pipeline.output.tiers import assign_tiers
from usher_pipeline.scoring.known_genes import (
    OMIM_USHER_GENES,
    SYSCILIA_SCGS_V2_CORE,
)


STRATEGY_COLUMNS = {
    "photoreceptor_q75": "Photoreceptor expression >= Q75",
    "hair_cell_q75": "Fetal cochlear hair-cell expression >= Q75",
    "retina_hair_concordant_q75": "Photoreceptor and hair-cell expression >= Q75",
    "retina_concordant_q75": "Photoreceptor and HPA retina >= Q75",
    "direct_protein": "Direct cilia/centrosome protein evidence",
    "expression_or_protein": "Photoreceptor >= Q75 OR direct protein",
    "expression_and_protein": "Photoreceptor >= Q75 AND direct protein",
}


def percentile_threshold(values: pl.Series, quantile: float = 0.75) -> float | None:
    """Return a quantile over finite, non-null values, or None if unavailable."""
    clean = values.drop_nulls().filter(values.drop_nulls().is_finite())
    if clean.is_empty():
        return None
    return float(clean.quantile(quantile, interpolation="linear"))


def add_shortlist_strategies(high: pl.DataFrame) -> tuple[pl.DataFrame, dict[str, float | None]]:
    """Add transparent expression/protein strategy flags to HIGH-tier genes."""
    photo_q75 = percentile_threshold(high["cellxgene_photoreceptor_expr"])
    hair_q75 = percentile_threshold(high["cochlear_hair_cell_expression"])
    retina_q75 = percentile_threshold(high["hpa_retina_tpm"])

    photo_high = (
        pl.col("cellxgene_photoreceptor_expr") >= photo_q75
        if photo_q75 is not None else pl.lit(False)
    )
    retina_high = (
        pl.col("hpa_retina_tpm") >= retina_q75
        if retina_q75 is not None else pl.lit(False)
    )
    hair_high = (
        pl.col("cochlear_hair_cell_expression") >= hair_q75
        if hair_q75 is not None else pl.lit(False)
    )
    direct_protein = pl.any_horizontal(
        pl.col("compartment_cilia").fill_null(False),
        pl.col("compartment_centrosome").fill_null(False),
        pl.col("compartment_basal_body").fill_null(False),
        pl.col("compartment_transition_zone").fill_null(False),
        pl.col("compartment_stereocilia").fill_null(False),
        pl.col("in_cilia_proteomics").fill_null(False),
        pl.col("in_centrosome_proteomics").fill_null(False),
    )

    result = high.with_columns(
        photo_high.fill_null(False).alias("photoreceptor_q75"),
        hair_high.fill_null(False).alias("hair_cell_q75"),
        (photo_high & hair_high).fill_null(False).alias("retina_hair_concordant_q75"),
        (photo_high & retina_high).fill_null(False).alias("retina_concordant_q75"),
        direct_protein.alias("direct_protein"),
        (photo_high | direct_protein).fill_null(False).alias("expression_or_protein"),
        (photo_high & direct_protein).fill_null(False).alias("expression_and_protein"),
    )
    return result, {"photoreceptor_q75": photo_q75, "hair_cell_q75": hair_q75,
                    "hpa_retina_q75": retina_q75}


def summarize_strategies(df: pl.DataFrame) -> pl.DataFrame:
    """Summarize shortlist sizes and known-gene retention."""
    known = OMIM_USHER_GENES | SYSCILIA_SCGS_V2_CORE
    rows: list[dict[str, object]] = []
    for column, label in STRATEGY_COLUMNS.items():
        kept = df.filter(pl.col(column))
        rows.append({
            "strategy": column,
            "description": label,
            "shortlist_size": kept.height,
            "reduction_percent": round(100 * (1 - kept.height / df.height), 1),
            "omim_in_high_retained": kept.filter(
                pl.col("gene_symbol").is_in(OMIM_USHER_GENES)
            ).height,
            "known_in_high_retained": kept.filter(
                pl.col("gene_symbol").is_in(known)
            ).height,
        })
    return pl.DataFrame(rows)


def load_high_candidates(db_path: Path, hair_cell_path: Path | None = None) -> pl.DataFrame:
    """Load current HIGH genes plus raw expression and localization evidence."""
    con = duckdb.connect(str(db_path), read_only=True)
    scored = con.execute("SELECT * FROM scored_genes").pl()
    evidence = con.execute("""
        WITH expr AS (
            SELECT gene_id,
                   MAX(cellxgene_photoreceptor_expr) AS cellxgene_photoreceptor_expr,
                   MAX(cellxgene_hair_cell_expr) AS cellxgene_hair_cell_expr,
                   MAX(hpa_retina_tpm) AS hpa_retina_tpm
            FROM tissue_expression GROUP BY gene_id
        ), loc AS (
            SELECT gene_id,
                   BOOL_OR(COALESCE(compartment_cilia, FALSE)) AS compartment_cilia,
                   BOOL_OR(COALESCE(compartment_centrosome, FALSE)) AS compartment_centrosome,
                   BOOL_OR(COALESCE(compartment_basal_body, FALSE)) AS compartment_basal_body,
                   BOOL_OR(COALESCE(compartment_transition_zone, FALSE)) AS compartment_transition_zone,
                   BOOL_OR(COALESCE(compartment_stereocilia, FALSE)) AS compartment_stereocilia,
                   BOOL_OR(COALESCE(in_cilia_proteomics, FALSE)) AS in_cilia_proteomics
                   ,BOOL_OR(COALESCE(in_centrosome_proteomics, FALSE)) AS in_centrosome_proteomics
            FROM subcellular_localization GROUP BY gene_id
        )
        SELECT expr.*, loc.* EXCLUDE (gene_id)
        FROM expr LEFT JOIN loc USING (gene_id)
    """).pl()
    con.close()
    tiered = assign_tiers(scored).filter(pl.col("confidence_tier") == "HIGH")
    result = tiered.join(evidence, on="gene_id", how="left")
    if hair_cell_path is not None and hair_cell_path.exists():
        hair = pl.read_parquet(hair_cell_path).select(
            "gene_symbol", "cochlear_hair_cell_expression",
            "hair_cell_sample_count", "hair_cell_developmental_consistency",
        )
        result = result.join(hair, on="gene_symbol", how="left")
    else:
        result = result.with_columns(
            pl.lit(None).cast(pl.Float64).alias("cochlear_hair_cell_expression"),
            pl.lit(None).cast(pl.UInt32).alias("hair_cell_sample_count"),
            pl.lit(None).cast(pl.Float64).alias("hair_cell_developmental_consistency"),
        )
    return result


def render_report(
    high: pl.DataFrame, summary: pl.DataFrame, thresholds: dict[str, float | None]
) -> str:
    """Render a compact, auditable Markdown report."""
    known = OMIM_USHER_GENES | SYSCILIA_SCGS_V2_CORE
    omim_high = high.filter(pl.col("gene_symbol").is_in(OMIM_USHER_GENES)).height
    known_high = high.filter(pl.col("gene_symbol").is_in(known)).height
    hair_coverage = high["cellxgene_hair_cell_expr"].is_not_null().sum()
    lines = [
        "# Expression/protein shortlist exploration",
        "",
        "This analysis prioritizes genes within the existing HIGH tier; it does not alter",
        "composite scores or production confidence tiers.",
        "",
        "## Data availability",
        "",
        f"- HIGH candidates: {high.height}",
        f"- OMIM Usher genes already in HIGH: {omim_high}",
        f"- OMIM + SYSCILIA controls already in HIGH: {known_high}",
        f"- CellxGene hair-cell coverage within HIGH: {hair_coverage}/{high.height}",
        f"- GSE135913 fetal cochlear coverage within HIGH: "
        f"{high['cochlear_hair_cell_expression'].is_not_null().sum()}/{high.height}",
        f"- Photoreceptor Q75 within HIGH: {thresholds['photoreceptor_q75']}",
        f"- Fetal cochlear hair-cell Q75 within HIGH: {thresholds['hair_cell_q75']}",
        f"- HPA retina Q75 within HIGH: {thresholds['hpa_retina_q75']}",
        "",
        "> CellxGene hair-cell expression is unavailable. The cochlear value is an",
        "> exploratory aggregate from marker-validated fetal GSE135913 clusters and",
        "> is not yet part of the production expression layer.",
        "",
        "## Strategy comparison",
        "",
        "| Strategy | Genes | Reduction | OMIM retained | Known retained |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summary.iter_rows(named=True):
        lines.append(
            f"| {row['description']} | {row['shortlist_size']} | "
            f"{row['reduction_percent']}% | {row['omim_in_high_retained']}/{omim_high} | "
            f"{row['known_in_high_retained']}/{known_high} |"
        )
    lines.extend([
        "",
        "## Interpretation rule",
        "",
        "A strategy is exploratory unless it reduces the shortlist while retaining all",
        "positive controls already present in HIGH. Missing evidence must be audited before",
        "any strategy becomes a gate; here it provides no gate support but remains visible",
        "in the gene-level table. Protein AND expression is included as a stress",
        "test, not as a recommended hard gate.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/pipeline.duckdb"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/report/exploration"))
    parser.add_argument(
        "--hair-cell-data", type=Path,
        default=Path("data/report/exploration/gse135913_hair_cell_expression.parquet"),
    )
    args = parser.parse_args()

    high = load_high_candidates(args.db, args.hair_cell_data)
    detailed, thresholds = add_shortlist_strategies(high)
    summary = summarize_strategies(detailed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    detailed.write_csv(args.output_dir / "expression_shortlist_candidates.tsv", separator="\t")
    summary.write_csv(args.output_dir / "expression_shortlist_summary.tsv", separator="\t")
    (args.output_dir / "expression_shortlist_report.md").write_text(
        render_report(detailed, summary, thresholds), encoding="utf-8"
    )
    print(summary)


if __name__ == "__main__":
    main()

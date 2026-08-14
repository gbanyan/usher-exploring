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

    photo_available = photo_q75 is not None
    retina_available = retina_q75 is not None
    hair_available = hair_q75 is not None
    photo_high = (
        pl.col("cellxgene_photoreceptor_expr") >= photo_q75
        if photo_available else pl.lit(None, dtype=pl.Boolean)
    )
    retina_high = (
        pl.col("hpa_retina_tpm") >= retina_q75
        if retina_available else pl.lit(None, dtype=pl.Boolean)
    )
    hair_high = (
        pl.col("cochlear_hair_cell_expression") >= hair_q75
        if hair_available else pl.lit(None, dtype=pl.Boolean)
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

    photo_flag = photo_high.fill_null(False) if photo_available else photo_high
    hair_flag = hair_high.fill_null(False) if hair_available else hair_high
    retina_hair = (
        (photo_high & hair_high).fill_null(False)
        if photo_available and hair_available
        else pl.lit(None, dtype=pl.Boolean)
    )
    retina_concordant = (
        (photo_high & retina_high).fill_null(False)
        if photo_available and retina_available
        else pl.lit(None, dtype=pl.Boolean)
    )
    expression_or = (
        (photo_high | direct_protein).fill_null(False)
        if photo_available else pl.lit(None, dtype=pl.Boolean)
    )
    expression_and = (
        (photo_high & direct_protein).fill_null(False)
        if photo_available else pl.lit(None, dtype=pl.Boolean)
    )
    result = high.with_columns(
        photo_flag.alias("photoreceptor_q75"),
        hair_flag.alias("hair_cell_q75"),
        retina_hair.alias("retina_hair_concordant_q75"),
        retina_concordant.alias("retina_concordant_q75"),
        direct_protein.alias("direct_protein"),
        expression_or.alias("expression_or_protein"),
        expression_and.alias("expression_and_protein"),
    )
    return result, {"photoreceptor_q75": photo_q75, "hair_cell_q75": hair_q75,
                    "hpa_retina_q75": retina_q75}


def summarize_strategies(df: pl.DataFrame) -> pl.DataFrame:
    """Summarize shortlist sizes and known-gene retention."""
    known = OMIM_USHER_GENES | SYSCILIA_SCGS_V2_CORE
    rows: list[dict[str, object]] = []
    for column, label in STRATEGY_COLUMNS.items():
        available = df[column].is_not_null().any()
        if not available:
            rows.append({
                "strategy": column,
                "description": label,
                "status": "NA",
                "shortlist_size": None,
                "reduction_percent": None,
                "omim_in_high_retained": None,
                "known_in_high_retained": None,
            })
            continue
        kept = df.filter(pl.col(column))
        rows.append({
            "strategy": column,
            "description": label,
            "status": "available",
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


def load_high_candidates(
    db_path: Path,
    hair_cell_path: Path | None = None,
    *,
    cache_only: bool = True,
) -> pl.DataFrame:
    """Load current HIGH genes plus raw expression and localization evidence."""
    if not db_path.is_file():
        raise FileNotFoundError(f"Missing scored-state database: {db_path}")
    if hair_cell_path is None or not hair_cell_path.is_file():
        raise FileNotFoundError(
            "Offline shortlist analysis requires the local GSE135913 aggregate: "
            f"{hair_cell_path}"
        )
    con = duckdb.connect(str(db_path), read_only=True)
    scored = con.execute("SELECT * FROM scored_genes").pl()
    if scored.height != 20081 or scored["gene_id"].n_unique() != 20081:
        con.close()
        raise ValueError(
            "Expected the current 20,081-row scored state; "
            f"found {scored.height} rows and {scored['gene_id'].n_unique()} IDs"
        )
    if scored["gene_symbol"].n_unique() != 20081:
        con.close()
        raise ValueError("Current scored state must contain 20,081 unique labels")
    expression_columns = {
        row[0] for row in con.execute("DESCRIBE tissue_expression").fetchall()
    }
    required_expression = {
        "cellxgene_photoreceptor_expr",
        "cellxgene_hair_cell_expr",
    }
    missing_expression = required_expression - expression_columns
    if missing_expression:
        con.close()
        raise ValueError(
            "Current tissue_expression schema is missing required columns: "
            f"{sorted(missing_expression)}"
        )
    retina_column = (
        "hpa_retina_tpm" if "hpa_retina_tpm" in expression_columns else
        "hpa_retina_ntpm" if "hpa_retina_ntpm" in expression_columns else None
    )
    if retina_column is None:
        con.close()
        raise ValueError(
            "Current tissue_expression schema has neither hpa_retina_tpm nor "
            "hpa_retina_ntpm"
        )
    localization_columns = {
        row[0] for row in con.execute("DESCRIBE subcellular_localization").fetchall()
    }
    signal_sources = {
        "compartment_cilia": ["compartment_cilia"],
        "compartment_centrosome": ["compartment_centrosome"],
        "compartment_basal_body": ["compartment_basal_body"],
        "compartment_transition_zone": ["compartment_transition_zone"],
        "compartment_stereocilia": ["compartment_stereocilia"],
        "in_cilia_proteomics": ["in_cilia_proteomics", "in_cilia_compendium"],
        "in_centrosome_proteomics": [
            "in_centrosome_proteomics", "in_centrosome_compendium"
        ],
    }
    signal_sql = []
    for alias, candidates in signal_sources.items():
        available = [column for column in candidates if column in localization_columns]
        if available:
            expression = " OR ".join(f"COALESCE({column}, FALSE)" for column in available)
        else:
            expression = "FALSE"
        signal_sql.append(f"BOOL_OR({expression}) AS {alias}")
    evidence = con.execute("""
        WITH expr AS (
            SELECT gene_id,
                   MAX(cellxgene_photoreceptor_expr) AS cellxgene_photoreceptor_expr,
                   MAX(cellxgene_hair_cell_expr) AS cellxgene_hair_cell_expr,
                   MAX({retina_column}) AS hpa_retina_tpm
            FROM tissue_expression GROUP BY gene_id
        ), loc AS (
            SELECT gene_id,
                   {signal_columns}
            FROM subcellular_localization GROUP BY gene_id
        )
        SELECT expr.*, loc.* EXCLUDE (gene_id)
        FROM expr LEFT JOIN loc USING (gene_id)
    """.format(
        retina_column=retina_column,
        signal_columns=",\n                   ".join(signal_sql),
    )).pl()
    con.close()
    tiered = assign_tiers(scored).filter(pl.col("confidence_tier") == "HIGH")
    result = tiered.join(evidence, on="gene_id", how="left")
    hair = pl.read_parquet(hair_cell_path).select(
        "gene_symbol", "cochlear_hair_cell_expression",
        "hair_cell_sample_count", "hair_cell_developmental_consistency",
    )
    if hair["gene_symbol"].n_unique() != hair.height:
        raise ValueError("GSE135913 aggregate contains duplicate scored labels")
    scored_labels = set(scored["gene_symbol"].to_list())
    outside = set(hair["gene_symbol"].to_list()) - scored_labels
    if outside:
        raise ValueError(
            "GSE135913 aggregate contains labels outside the current scored state: "
            f"{sorted(outside)[:5]}"
        )
    result = result.join(hair, on="gene_symbol", how="left")
    return result


def render_report(
    high: pl.DataFrame, summary: pl.DataFrame, thresholds: dict[str, float | None]
) -> str:
    """Render a compact, auditable Markdown report."""
    known = OMIM_USHER_GENES | SYSCILIA_SCGS_V2_CORE
    omim_high = high.filter(pl.col("gene_symbol").is_in(OMIM_USHER_GENES)).height
    known_high = high.filter(pl.col("gene_symbol").is_in(known)).height
    hair_coverage = high["cellxgene_hair_cell_expr"].is_not_null().sum()
    def fmt(value: object) -> str:
        return "NA" if value is None else str(value)

    lines = [
        "# Expression/protein shortlist exploration",
        "",
        "This analysis prioritizes genes within the existing HIGH tier; it does not alter",
        "composite scores or production confidence tiers.",
        "",
        "## Data availability",
        "",
        f"- HIGH candidates: {high.height}",
        f"- Established Usher genes already in HIGH: {omim_high}",
        f"- Established Usher + SYSCILIA controls already in HIGH: {known_high}",
        f"- CellxGene hair-cell coverage within HIGH: {hair_coverage}/{high.height}",
        f"- GSE135913 fetal cochlear coverage within HIGH: "
        f"{high['cochlear_hair_cell_expression'].is_not_null().sum()}/{high.height}",
        f"- Photoreceptor Q75 within HIGH: {thresholds['photoreceptor_q75']}",
        f"- Fetal cochlear hair-cell Q75 within HIGH: {thresholds['hair_cell_q75']}",
        f"- HPA retina Q75 within HIGH: {fmt(thresholds['hpa_retina_q75'])} "
        "(unavailable in the current local inputs)",
        "",
        "> CellxGene hair-cell expression is unavailable. The cochlear value is an",
        "> exploratory aggregate from marker-validated fetal GSE135913 clusters and",
        "> is not yet part of the production expression layer.",
        "",
        "## Strategy comparison",
        "",
        "| Strategy | Status | Genes | Reduction | Established Usher retained | Known retained |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in summary.iter_rows(named=True):
        reduction = (
            "NA" if row["reduction_percent"] is None
            else f"{row['reduction_percent']}%"
        )
        lines.append(
            f"| {row['description']} | {row['status']} | "
            f"{fmt(row['shortlist_size'])} | {reduction} | "
            f"{fmt(row['omim_in_high_retained'])}/{omim_high if row['status'] != 'NA' else 'NA'} | "
            f"{fmt(row['known_in_high_retained'])}/{known_high if row['status'] != 'NA' else 'NA'} |"
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
    parser.add_argument(
        "--cache-only", action="store_true",
        help="Require the local GSE135913 aggregate; no downloads are supported.",
    )
    args = parser.parse_args()

    high = load_high_candidates(args.db, args.hair_cell_data, cache_only=args.cache_only)
    detailed, thresholds = add_shortlist_strategies(high)
    summary = summarize_strategies(detailed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    detailed.write_csv(args.output_dir / "expression_shortlist_candidates.tsv", separator="\t")
    summary_for_output = summary.with_columns(
        pl.when(pl.col("status") == "NA")
        .then(pl.lit("NA"))
        .otherwise(pl.col("shortlist_size").cast(pl.String))
        .alias("shortlist_size"),
        pl.when(pl.col("status") == "NA")
        .then(pl.lit("NA"))
        .otherwise(pl.col("reduction_percent").cast(pl.String))
        .alias("reduction_percent"),
        pl.when(pl.col("status") == "NA")
        .then(pl.lit("NA"))
        .otherwise(pl.col("omim_in_high_retained").cast(pl.String))
        .alias("omim_in_high_retained"),
        pl.when(pl.col("status") == "NA")
        .then(pl.lit("NA"))
        .otherwise(pl.col("known_in_high_retained").cast(pl.String))
        .alias("known_in_high_retained"),
    )
    summary_for_output.write_csv(
        args.output_dir / "expression_shortlist_summary.tsv", separator="\t"
    )
    (args.output_dir / "expression_shortlist_report.md").write_text(
        render_report(detailed, summary, thresholds), encoding="utf-8"
    )
    print(summary)


if __name__ == "__main__":
    main()

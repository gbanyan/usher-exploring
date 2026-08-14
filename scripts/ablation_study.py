"""Ablation study: NULL-aware vs zero vs median imputation scoring strategies.

Compares three imputation approaches:
1. NULL-preserve (current) — weighted average over available layers only
2. Zero-impute — missing scores treated as 0.0
3. Median-impute — missing scores filled with per-layer median

Outputs:
- Rank shift statistics for known Usher/ciliopathy genes
- Rank shift statistics for top 50 candidates
- Per-strategy tier counts
- CSV of full comparison
"""

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usher_pipeline.config.loader import load_config
from usher_pipeline.persistence.duckdb_store import PipelineStore
from usher_pipeline.scoring.known_genes import OMIM_USHER_GENES, SYSCILIA_SCGS_V2_CORE

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)

LAYER_COLS = [
    "gnomad_score", "expression_score", "annotation_score",
    "localization_score", "animal_model_score", "literature_score",
]
STRATEGIES = ["null_preserve", "zero_impute", "median_impute"]
WEIGHTS = {
    "gnomad_score": 0.20,
    "expression_score": 0.20,
    "annotation_score": 0.15,
    "localization_score": 0.15,
    "animal_model_score": 0.15,
    "literature_score": 0.15,
}

OUTDIR = Path("data/report/paper_figures")
OUTDIR.mkdir(parents=True, exist_ok=True)


def load_scored() -> pl.DataFrame:
    config = load_config("config/default.yaml")
    store = PipelineStore.from_config(config)
    df = store.load_dataframe("scored_genes")
    store.close()
    return df


def score_null_preserve(df: pl.DataFrame) -> pl.DataFrame:
    """Current strategy: weighted average over non-NULL layers."""
    weighted_sum = pl.lit(0.0)
    weight_sum = pl.lit(0.0)
    for col, w in WEIGHTS.items():
        weighted_sum = weighted_sum + pl.when(pl.col(col).is_not_null()).then(pl.col(col) * w).otherwise(0.0)
        weight_sum = weight_sum + pl.when(pl.col(col).is_not_null()).then(w).otherwise(0.0)

    return df.with_columns(
        pl.when(weight_sum > 0)
        .then(weighted_sum / weight_sum)
        .otherwise(None)
        .alias("composite_null_preserve")
    )


def score_zero_impute(df: pl.DataFrame) -> pl.DataFrame:
    """Zero imputation: NULL → 0.0, then standard weighted average."""
    expr = pl.lit(0.0)
    for col, w in WEIGHTS.items():
        expr = expr + pl.col(col).fill_null(0.0) * w
    return df.with_columns(expr.alias("composite_zero_impute"))


def score_median_impute(df: pl.DataFrame) -> pl.DataFrame:
    """Median imputation: NULL → per-layer median, then weighted average."""
    # Compute medians
    medians = {}
    for col in LAYER_COLS:
        med = df.filter(pl.col(col).is_not_null())[col].median()
        medians[col] = med if med is not None else 0.0

    expr = pl.lit(0.0)
    for col, w in WEIGHTS.items():
        expr = expr + pl.col(col).fill_null(medians[col]) * w
    return df.with_columns(expr.alias("composite_median_impute"))


def add_ranks(df: pl.DataFrame) -> pl.DataFrame:
    """Add percentile ranks using the number of computed rows per strategy.

    A NULL composite score is not a rank.  In particular, zero-evidence genes
    remain NULL under the NULL-preserve strategy and must not silently dilute
    that strategy's percentile denominator.
    """
    for strategy in STRATEGIES:
        col = f"composite_{strategy}"
        rank_col = f"rank_{strategy}"
        pct_col = f"pctile_{strategy}"
        computed_rows = df.filter(pl.col(col).is_not_null()).height
        df = df.with_columns(
            pl.col(col).rank(method="average", descending=False).alias(rank_col)
        )
        df = df.with_columns(
            pl.when(pl.col(rank_col).is_not_null() & (computed_rows > 0))
            .then(pl.col(rank_col) / computed_rows * 100)
            .otherwise(None)
            .alias(pct_col),
            pl.lit(computed_rows).cast(pl.Int64).alias(f"rank_denominator_{strategy}"),
        )
    return df


def rank_statistics(
    df: pl.DataFrame,
    strategy: str,
    threshold: float = 75.0,
) -> dict[str, int | float | None]:
    """Return statistics whose denominators match non-NULL rank rows."""
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}")

    pct_col = f"pctile_{strategy}"
    ranked = df.filter(pl.col(pct_col).is_not_null())
    zero_evidence_null = df.filter(
        (pl.col("evidence_count") == 0) & pl.col(pct_col).is_null()
    ).height
    above = ranked.filter(pl.col(pct_col) >= threshold).height

    return {
        "table_rows": df.height,
        "ranked_rows": ranked.height,
        "null_rank_rows": df.height - ranked.height,
        "zero_evidence_null_rank_rows": zero_evidence_null,
        "above_threshold": above,
        "above_threshold_denominator": ranked.height,
        "median_percentile": ranked[pct_col].median(),
        "mean_percentile": ranked[pct_col].mean(),
        "min_percentile": ranked[pct_col].min(),
        "max_percentile": ranked[pct_col].max(),
    }


def shift_statistics(
    df: pl.DataFrame,
    left_strategy: str,
    right_strategy: str,
) -> dict[str, int | float | None]:
    """Summarize paired percentile shifts over rows ranked by both strategies."""
    left_col = f"pctile_{left_strategy}"
    right_col = f"pctile_{right_strategy}"
    paired = df.filter(pl.col(left_col).is_not_null() & pl.col(right_col).is_not_null())
    shifts = paired[left_col] - paired[right_col]
    return {
        "paired_rows": paired.height,
        "mean_shift": shifts.mean(),
        "std_shift": shifts.std(),
        "max_shift": shifts.max(),
    }


def paired_shift_data(
    df: pl.DataFrame,
    left_strategy: str = "null_preserve",
    right_strategy: str = "zero_impute",
) -> pl.DataFrame:
    """Return only rows whose two plotted percentile shifts are defined."""
    left_col = f"pctile_{left_strategy}"
    right_col = f"pctile_{right_strategy}"
    return (
        df.filter(pl.col(left_col).is_not_null() & pl.col(right_col).is_not_null())
        .select([
            "gene_symbol",
            (pl.col(left_col) - pl.col(right_col)).alias("rank_shift_pct"),
        ])
    )


def _format_stat(value: float | int | None, digits: int = 2) -> str:
    """Format nullable statistics without turning missing values into zero."""
    return "N/A" if value is None else f"{value:.{digits}f}"


def generate_ablation_figure(
    df: pl.DataFrame,
    output_dir: Path = OUTDIR,
) -> None:
    """Generate Figure 6 from the final ranked ablation table."""
    output_dir.mkdir(parents=True, exist_ok=True)
    all_known = set(OMIM_USHER_GENES) | set(SYSCILIA_SCGS_V2_CORE)
    known_df = df.filter(pl.col("gene_symbol").is_in(list(all_known)))
    known_df_pd = known_df.select([
        "gene_symbol", "pctile_null_preserve", "pctile_zero_impute", "pctile_median_impute",
        "evidence_count",
    ]).to_pandas()
    melted = known_df_pd.melt(
        id_vars=["gene_symbol", "evidence_count"],
        value_vars=["pctile_null_preserve", "pctile_zero_impute", "pctile_median_impute"],
        var_name="strategy", value_name="percentile",
    )
    melted["strategy"] = melted["strategy"].map({
        "pctile_null_preserve": "NULL-preserve",
        "pctile_zero_impute": "Zero-impute",
        "pctile_median_impute": "Median-impute",
    })
    gene_order = known_df_pd.sort_values(
        "pctile_null_preserve", ascending=False
    )["gene_symbol"].tolist()

    incomplete = df.filter(pl.col("evidence_count") < 6)
    inc_data = incomplete.select([
        "gene_symbol",
        (pl.col("pctile_null_preserve") - pl.col("pctile_zero_impute")).alias("vs_Zero"),
        (pl.col("pctile_null_preserve") - pl.col("pctile_median_impute")).alias("vs_Median"),
    ]).drop_nulls().to_pandas()
    paired_incomplete_count = len(inc_data)
    inc_melted = inc_data.melt(
        id_vars=["gene_symbol"],
        value_vars=["vs_Zero", "vs_Median"],
        var_name="comparison", value_name="rank_shift_pct",
    )

    fig, (axA, axB) = plt.subplots(
        2, 1, figsize=(10, 14), gridspec_kw={"height_ratios": [1, 2.4]}
    )
    sns.histplot(
        data=inc_melted, x="rank_shift_pct", hue="comparison",
        palette={"vs_Zero": "#e74c3c", "vs_Median": "#f39c12"},
        bins=50, alpha=0.6, ax=axA,
    )
    axA.axvline(x=0, color="black", linewidth=0.8)
    axA.set_xlabel("Percentile Rank Shift (NULL-preserve minus imputed)")
    axA.set_ylabel("Gene Count")
    axA.text(
        0.98, 0.95,
        f"n = {paired_incomplete_count} paired genes\n(evidence < 6 layers)\n"
        "Positive = NULL-preserve\nranks gene higher",
        transform=axA.transAxes, ha="right", va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
    )

    sns.barplot(
        data=melted, y="gene_symbol", x="percentile", hue="strategy",
        order=gene_order,
        palette={"NULL-preserve": "#2ecc71", "Zero-impute": "#e74c3c",
                 "Median-impute": "#f39c12"},
        ax=axB,
    )
    axB.axvline(x=75, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    axB.text(75.5, -0.5, "75th pctile", fontsize=8, color="gray")
    axB.set_xlabel("Percentile Rank (%)")
    axB.set_ylabel("")
    axB.set_xlim(0, 105)
    axB.legend(title="Imputation Strategy", loc="lower right", fontsize=8)
    axA.text(-0.06, 1.04, "A", transform=axA.transAxes, fontsize=16,
             fontweight="bold", va="bottom", ha="right")
    axB.text(-0.06, 1.02, "B", transform=axB.transAxes, fontsize=16,
             fontweight="bold", va="bottom", ha="right")

    fig.tight_layout()
    fig.savefig(output_dir / "fig6_ablation.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / "fig6_ablation.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {output_dir}/fig6_ablation.png")


def main():
    print("Loading scored genes...")
    df = load_scored()
    print(f"  {df.height} genes loaded\n")

    # Compute all 3 strategies
    print("Computing scores under 3 imputation strategies...")
    df = score_null_preserve(df)
    df = score_zero_impute(df)
    df = score_median_impute(df)
    df = add_ranks(df)

    # ── Known gene analysis ────────────────────────────────────
    all_known = set(OMIM_USHER_GENES) | set(SYSCILIA_SCGS_V2_CORE)
    known_df = df.filter(pl.col("gene_symbol").is_in(list(all_known)))

    print("=" * 70)
    print("KNOWN GENE PERCENTILE RANKS (higher = better)")
    print("=" * 70)
    print(f"{'Strategy':<20} {'Median':>8} {'Mean':>8} {'Min':>8} {'Max':>8} {'>=75th':>8}")
    print("-" * 70)

    print("RANK DENOMINATORS (computed non-NULL rows)")
    print("=" * 70)
    print(f"{'Strategy':<20} {'Computed rows':>15} {'NULL-rank rows':>15} {'Zero-evidence NULL':>20} {'>=75 / denominator':>20}")
    print("-" * 70)
    for strategy in STRATEGIES:
        stats = rank_statistics(df, strategy)
        print(
            f"{strategy:<20} {stats['ranked_rows']:>15} {stats['null_rank_rows']:>15} "
            f"{stats['zero_evidence_null_rank_rows']:>20} "
            f"{stats['above_threshold']:>5} / {stats['above_threshold_denominator']:<13}"
        )
    print("  NULL-rank rows are excluded from percentile summaries; zero-evidence NULL ranks are not failures or zero scores.")

    print("\n" + "=" * 70)
    print("KNOWN GENE PERCENTILE RANKS (higher = better; denominator = computed rows)")
    print("=" * 70)
    print(f"{'Strategy':<20} {'Median':>8} {'Mean':>8} {'Min':>8} {'Max':>8} {'>=75':>8} {'Denom':>8}")
    print("-" * 70)

    for strategy in STRATEGIES:
        pct_col = f"pctile_{strategy}"
        stats = rank_statistics(known_df, strategy)
        print(f"{strategy:<20} "
              f"{_format_stat(stats['median_percentile'], 1):>8} "
              f"{_format_stat(stats['mean_percentile'], 1):>8} "
              f"{_format_stat(stats['min_percentile'], 1):>8} "
              f"{_format_stat(stats['max_percentile'], 1):>8} "
              f"{stats['above_threshold']:>8} {stats['ranked_rows']:>8}")

    known_zero_evidence = known_df.filter(pl.col("evidence_count") == 0)
    if known_zero_evidence.height:
        print(
            "  Known zero-evidence genes with NULL-preserve ranks: "
            f"{known_zero_evidence.height} "
            f"({', '.join(known_zero_evidence['gene_symbol'].to_list())})"
        )

    # ── Rank shifts for known genes ────────────────────────────
    print("\n" + "=" * 70)
    print("RANK SHIFT: NULL-preserve vs Zero-impute (known genes)")
    print("Positive = NULL-preserve ranks the gene HIGHER")
    print("=" * 70)

    known_df = known_df.with_columns(
        (pl.col("pctile_null_preserve") - pl.col("pctile_zero_impute")).alias("shift_vs_zero"),
        (pl.col("pctile_null_preserve") - pl.col("pctile_median_impute")).alias("shift_vs_median"),
    )

    print(f"\n{'Gene':<12} {'NULL%':>7} {'Zero%':>7} {'Med%':>7} {'Δ(zero)':>8} {'Δ(med)':>8} {'Layers':>7}")
    print("-" * 70)

    for row in known_df.sort("pctile_null_preserve", descending=True).to_dicts():
        print(f"{row['gene_symbol']:<12} "
              f"{row['pctile_null_preserve']:>7.1f} "
              f"{row['pctile_zero_impute']:>7.1f} "
              f"{row['pctile_median_impute']:>7.1f} "
              f"{row['shift_vs_zero']:>+8.1f} "
              f"{row['shift_vs_median']:>+8.1f} "
              f"{row['evidence_count']:>7}")

    # ── Top 50 candidates under NULL-preserve ──────────────────
    print("\n" + "=" * 70)
    print("TOP 25 CANDIDATES: Rank comparison across strategies")
    print("(filtered to evidence_count >= 4)")
    print("=" * 70)

    top = df.filter(pl.col("evidence_count") >= 4).sort("composite_null_preserve", descending=True).head(25)
    top = top.with_columns(
        (pl.col("pctile_null_preserve") - pl.col("pctile_zero_impute")).alias("shift_vs_zero"),
        (pl.col("pctile_null_preserve") - pl.col("pctile_median_impute")).alias("shift_vs_median"),
    )

    print(f"\n{'Gene':<12} {'NULL%':>7} {'Zero%':>7} {'Med%':>7} {'Δ(zero)':>8} {'Δ(med)':>8} {'Layers':>7}")
    print("-" * 70)

    for row in top.to_dicts():
        marker = ""
        if row["gene_symbol"] in OMIM_USHER_GENES:
            marker = " *"
        elif row["gene_symbol"] in SYSCILIA_SCGS_V2_CORE:
            marker = " +"
        print(f"{row['gene_symbol']:<12}{marker}"
              f"{row['pctile_null_preserve']:>7.1f} "
              f"{row['pctile_zero_impute']:>7.1f} "
              f"{row['pctile_median_impute']:>7.1f} "
              f"{row['shift_vs_zero']:>+8.1f} "
              f"{row['shift_vs_median']:>+8.1f} "
              f"{row['evidence_count']:>7}")

    # ── Summary statistics ─────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY: Impact of imputation strategy on all genes")
    print("=" * 70)

    all_shifts_zero = shift_statistics(df, "null_preserve", "zero_impute")
    all_shifts_median = shift_statistics(df, "null_preserve", "median_impute")

    # Genes with incomplete evidence
    incomplete = df.filter(pl.col("evidence_count") < 6)
    inc_shifts_zero = shift_statistics(incomplete, "null_preserve", "zero_impute")
    inc_shifts_median = shift_statistics(incomplete, "null_preserve", "median_impute")

    print(f"\nAll genes (n={df.height}):")
    print(f"  vs Zero:   paired rows = {all_shifts_zero['paired_rows']}/{df.height}, "
          f"mean shift = {_format_stat(all_shifts_zero['mean_shift']):>6}%, "
          f"std = {_format_stat(all_shifts_zero['std_shift']):>6}%, "
          f"max = {_format_stat(all_shifts_zero['max_shift'], 1):>6}%")
    print(f"  vs Median: paired rows = {all_shifts_median['paired_rows']}/{df.height}, "
          f"mean shift = {_format_stat(all_shifts_median['mean_shift']):>6}%, "
          f"std = {_format_stat(all_shifts_median['std_shift']):>6}%, "
          f"max = {_format_stat(all_shifts_median['max_shift'], 1):>6}%")

    print(f"\nGenes with <6 evidence layers (n={incomplete.height}):")
    print(f"  vs Zero:   paired rows = {inc_shifts_zero['paired_rows']}/{incomplete.height}, "
          f"mean shift = {_format_stat(inc_shifts_zero['mean_shift']):>6}%, "
          f"std = {_format_stat(inc_shifts_zero['std_shift']):>6}%, "
          f"max = {_format_stat(inc_shifts_zero['max_shift'], 1):>6}%")
    print(f"  vs Median: paired rows = {inc_shifts_median['paired_rows']}/{incomplete.height}, "
          f"mean shift = {_format_stat(inc_shifts_median['mean_shift']):>6}%, "
          f"std = {_format_stat(inc_shifts_median['std_shift']):>6}%, "
          f"max = {_format_stat(inc_shifts_median['max_shift'], 1):>6}%")

    # ── Figure 6: two-panel ablation figure ────────────────────
    print("\nGenerating ablation figure...")
    generate_ablation_figure(df)

    # ── Save full comparison CSV ───────────────────────────────
    csv_path = Path("data/report/ablation_comparison.csv")
    df.select([
        "gene_id", "gene_symbol", "evidence_count",
        "composite_null_preserve", "composite_zero_impute", "composite_median_impute",
        "pctile_null_preserve", "pctile_zero_impute", "pctile_median_impute",
        "rank_denominator_null_preserve", "rank_denominator_zero_impute",
        "rank_denominator_median_impute",
    ]).write_csv(csv_path)
    print(f"  Saved: {csv_path}")

    print("\nAblation study complete.")


if __name__ == "__main__":
    main()

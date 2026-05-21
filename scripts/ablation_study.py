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
    """Add percentile ranks for all 3 strategies."""
    n = df.height
    for strategy in ["null_preserve", "zero_impute", "median_impute"]:
        col = f"composite_{strategy}"
        rank_col = f"rank_{strategy}"
        pct_col = f"pctile_{strategy}"
        df = df.with_columns(
            pl.col(col).rank(method="average", descending=False).alias(rank_col)
        )
        df = df.with_columns(
            (pl.col(rank_col) / n * 100).alias(pct_col)
        )
    return df


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

    for strategy in ["null_preserve", "zero_impute", "median_impute"]:
        pct_col = f"pctile_{strategy}"
        pcts = known_df[pct_col]
        med = pcts.median()
        mean = pcts.mean()
        mn = pcts.min()
        mx = pcts.max()
        above75 = known_df.filter(pl.col(pct_col) >= 75).height
        print(f"{strategy:<20} {med:>8.1f} {mean:>8.1f} {mn:>8.1f} {mx:>8.1f} {above75:>8}")

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

    all_shifts_zero = (df["pctile_null_preserve"] - df["pctile_zero_impute"])
    all_shifts_median = (df["pctile_null_preserve"] - df["pctile_median_impute"])

    # Genes with incomplete evidence
    incomplete = df.filter(pl.col("evidence_count") < 6)
    inc_shifts_zero = (incomplete["pctile_null_preserve"] - incomplete["pctile_zero_impute"])
    inc_shifts_median = (incomplete["pctile_null_preserve"] - incomplete["pctile_median_impute"])

    print(f"\nAll genes (n={df.height}):")
    print(f"  vs Zero:   mean shift = {all_shifts_zero.mean():+.2f}%, "
          f"std = {all_shifts_zero.std():.2f}%, "
          f"max = {all_shifts_zero.max():+.1f}%")
    print(f"  vs Median: mean shift = {all_shifts_median.mean():+.2f}%, "
          f"std = {all_shifts_median.std():.2f}%, "
          f"max = {all_shifts_median.max():+.1f}%")

    print(f"\nGenes with <6 evidence layers (n={incomplete.height}):")
    print(f"  vs Zero:   mean shift = {inc_shifts_zero.mean():+.2f}%, "
          f"std = {inc_shifts_zero.std():.2f}%, "
          f"max = {inc_shifts_zero.max():+.1f}%")
    print(f"  vs Median: mean shift = {inc_shifts_median.mean():+.2f}%, "
          f"std = {inc_shifts_median.std():.2f}%, "
          f"max = {inc_shifts_median.max():+.1f}%")

    # ── Figure: Known gene rank shifts ─────────────────────────
    print("\nGenerating ablation figure...")

    known_df_pd = known_df.select([
        "gene_symbol", "pctile_null_preserve", "pctile_zero_impute", "pctile_median_impute",
        "evidence_count"
    ]).to_pandas()

    # Melt for grouped bar chart
    melted = known_df_pd.melt(
        id_vars=["gene_symbol", "evidence_count"],
        value_vars=["pctile_null_preserve", "pctile_zero_impute", "pctile_median_impute"],
        var_name="strategy", value_name="percentile"
    )
    melted["strategy"] = melted["strategy"].map({
        "pctile_null_preserve": "NULL-preserve",
        "pctile_zero_impute": "Zero-impute",
        "pctile_median_impute": "Median-impute",
    })

    # Sort by NULL-preserve percentile
    gene_order = known_df_pd.sort_values("pctile_null_preserve", ascending=False)["gene_symbol"].tolist()

    fig, ax = plt.subplots(figsize=(10, 8))

    sns.barplot(
        data=melted, y="gene_symbol", x="percentile", hue="strategy",
        order=gene_order,
        palette={"NULL-preserve": "#2ecc71", "Zero-impute": "#e74c3c", "Median-impute": "#f39c12"},
        ax=ax,
    )

    ax.axvline(x=75, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.text(75.5, -0.5, "75th pctile", fontsize=8, color="gray")

    ax.set_xlabel("Percentile Rank (%)")
    ax.set_ylabel("")
    ax.set_xlim(0, 105)
    ax.legend(title="Imputation Strategy", loc="lower right", fontsize=8)

    fig.savefig(OUTDIR / "fig6b_ablation_known_genes.png", dpi=300, bbox_inches="tight")
    fig.savefig(OUTDIR / "fig6b_ablation_known_genes.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUTDIR}/fig6b_ablation_known_genes.png")

    # ── Figure: Rank shift distribution for incomplete genes ───
    fig2, ax2 = plt.subplots(figsize=(8, 5))

    inc_data = incomplete.select([
        "gene_symbol",
        (pl.col("pctile_null_preserve") - pl.col("pctile_zero_impute")).alias("vs_Zero"),
        (pl.col("pctile_null_preserve") - pl.col("pctile_median_impute")).alias("vs_Median"),
    ]).to_pandas()

    inc_melted = inc_data.melt(
        id_vars=["gene_symbol"],
        value_vars=["vs_Zero", "vs_Median"],
        var_name="comparison", value_name="rank_shift_pct"
    )

    sns.histplot(
        data=inc_melted, x="rank_shift_pct", hue="comparison",
        palette={"vs_Zero": "#e74c3c", "vs_Median": "#f39c12"},
        bins=50, alpha=0.6, ax=ax2,
    )

    ax2.axvline(x=0, color="black", linewidth=0.8)
    ax2.set_xlabel("Percentile Rank Shift (NULL-preserve minus imputed)")
    ax2.set_ylabel("Gene Count")
    ax2.text(0.98, 0.95,
             f"n = {incomplete.height} genes\n(evidence < 6 layers)\n"
             f"Positive = NULL-preserve\nranks gene higher",
             transform=ax2.transAxes, ha="right", va="top", fontsize=9,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    fig2.savefig(OUTDIR / "fig6a_ablation_shift_distribution.png", dpi=300, bbox_inches="tight")
    fig2.savefig(OUTDIR / "fig6a_ablation_shift_distribution.pdf", bbox_inches="tight")
    plt.close(fig2)
    print(f"  Saved: {OUTDIR}/fig6a_ablation_shift_distribution.png")

    # ── Save full comparison CSV ───────────────────────────────
    csv_path = Path("data/report/ablation_comparison.csv")
    df.select([
        "gene_id", "gene_symbol", "evidence_count",
        "composite_null_preserve", "composite_zero_impute", "composite_median_impute",
        "pctile_null_preserve", "pctile_zero_impute", "pctile_median_impute",
    ]).write_csv(csv_path)
    print(f"  Saved: {csv_path}")

    print("\nAblation study complete.")


if __name__ == "__main__":
    main()

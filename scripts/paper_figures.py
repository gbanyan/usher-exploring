"""Generate publication-quality figures for BMC Bioinformatics submission."""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import polars as pl
import seaborn as sns

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usher_pipeline.config.loader import load_config
from usher_pipeline.persistence.duckdb_store import PipelineStore
from usher_pipeline.scoring.known_genes import OMIM_USHER_GENES, SYSCILIA_SCGS_V2_CORE

# Publication style
sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
FIGDIR = Path("data/report/paper_figures")
FIGDIR.mkdir(parents=True, exist_ok=True)

DPI = 300
PALETTE = {
    "HIGH": "#2ecc71",
    "MEDIUM": "#f39c12",
    "LOW": "#e74c3c",
}


def load_candidates() -> pl.DataFrame:
    """Load tiered candidates from TSV."""
    return pl.read_csv("data/report/candidates.tsv", separator="\t")


def load_scored_genes() -> pl.DataFrame:
    """Load scored genes directly from DuckDB."""
    config = load_config("config/default.yaml")
    store = PipelineStore.from_config(config)
    df = store.load_dataframe("scored_genes")
    store.close()
    return df


# ── Figure 2: Score distribution (improved) ─────────────────────────────

def fig2_score_distribution(df: pl.DataFrame):
    """Improved score distribution with inset for high-score region."""
    pdf = df.filter(pl.col("composite_score").is_not_null()).to_pandas()

    fig, ax = plt.subplots(figsize=(8, 5))

    sns.histplot(
        data=pdf,
        x="composite_score",
        hue="confidence_tier",
        hue_order=["HIGH", "MEDIUM", "LOW"],
        palette=PALETTE,
        bins=50,
        multiple="stack",
        ax=ax,
        edgecolor="white",
        linewidth=0.3,
    )

    ax.set_xlabel("Composite Score")
    ax.set_ylabel("Gene Count")
    ax.set_title("")
    ax.legend(title="Confidence Tier", loc="upper right")

    # Annotate key stats
    n_total = len(pdf)
    n_high = (pdf["confidence_tier"] == "HIGH").sum()
    n_medium = (pdf["confidence_tier"] == "MEDIUM").sum()
    ax.text(
        0.02, 0.95,
        f"n = {n_total:,} genes\nHIGH: {n_high}, MEDIUM: {n_medium:,}",
        transform=ax.transAxes, va="top", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
    )

    fig.savefig(FIGDIR / "fig2_score_distribution.png", dpi=DPI, bbox_inches="tight")
    fig.savefig(FIGDIR / "fig2_score_distribution.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  Fig 2: score distribution")


# ── Figure 3: Evidence layer coverage ────────────────────────────────────

def fig3_layer_coverage(df: pl.DataFrame):
    """Evidence layer coverage with percentage labels."""
    layer_cols = {
        "gnomad_score": "gnomAD\nConstraint",
        "expression_score": "Tissue\nExpression",
        "annotation_score": "Functional\nAnnotation",
        "localization_score": "Subcellular\nLocalization",
        "animal_model_score": "Animal\nModel",
        "literature_score": "Literature\nMining",
    }

    total = df.height
    counts = []
    labels = []
    for col, label in layer_cols.items():
        if col in df.columns:
            n = df.filter(pl.col(col).is_not_null()).height
            counts.append(n)
            labels.append(label)

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, counts, color=sns.color_palette("deep", len(counts)),
                  edgecolor="white", linewidth=0.5)

    # Add percentage labels on top of bars
    for bar, count in zip(bars, counts):
        pct = count / total * 100
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 100,
                f"{pct:.0f}%", ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("Genes with Evidence")
    ax.set_title("")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # Add total line
    ax.axhline(y=total, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.text(len(labels) - 0.5, total + 100, f"Gene universe: {total:,}",
            ha="right", va="bottom", fontsize=8, color="gray")

    fig.savefig(FIGDIR / "fig3_layer_coverage.png", dpi=DPI, bbox_inches="tight")
    fig.savefig(FIGDIR / "fig3_layer_coverage.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  Fig 3: layer coverage")


# ── Figure 4: Top candidates heatmap ─────────────────────────────────────

def fig4_top_candidates_heatmap(df: pl.DataFrame, top_n: int = 25):
    """Heatmap of per-layer normalized scores for top candidates."""
    layer_cols = [
        "gnomad_score", "expression_score", "annotation_score",
        "localization_score", "animal_model_score", "literature_score",
    ]
    layer_labels = [
        "gnomAD", "Expression", "Annotation",
        "Localization", "Animal Model", "Literature",
    ]

    # Filter to genes with sufficient evidence (>=4 layers) to avoid
    # sparse-evidence inflated scores (e.g., LOC* genes with 1 layer)
    robust = df.filter(pl.col("evidence_count") >= 4)
    top = robust.sort("composite_score", descending=True).head(top_n)

    # Build matrix
    actual_n = top.height
    genes = top["gene_symbol"].to_list()
    matrix = np.zeros((actual_n, len(layer_cols)))
    mask = np.zeros_like(matrix, dtype=bool)

    for j, col in enumerate(layer_cols):
        vals = top[col].to_list()
        for i, v in enumerate(vals):
            if v is None:
                mask[i, j] = True
                matrix[i, j] = 0
            else:
                matrix[i, j] = v

    # Mark known Usher/cilia genes
    all_known = set(OMIM_USHER_GENES) | set(SYSCILIA_SCGS_V2_CORE)
    gene_labels = []
    for g in genes:
        if g in OMIM_USHER_GENES:
            gene_labels.append(f"{g} *")
        elif g in SYSCILIA_SCGS_V2_CORE:
            gene_labels.append(f"{g} +")
        else:
            gene_labels.append(g)

    fig, ax = plt.subplots(figsize=(8, max(6, actual_n * 0.3)))

    sns.heatmap(
        matrix,
        mask=mask,
        xticklabels=layer_labels,
        yticklabels=gene_labels,
        cmap="YlOrRd",
        vmin=0, vmax=1,
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Normalized Score", "shrink": 0.6},
        ax=ax,
    )

    # Grey out NULL cells
    for i in range(mask.shape[0]):
        for j in range(mask.shape[1]):
            if mask[i, j]:
                ax.add_patch(plt.Rectangle((j, i), 1, 1, fill=True,
                                           facecolor="#f0f0f0", edgecolor="white",
                                           linewidth=0.5))

    ax.set_title("")
    ax.set_xlabel("")
    ax.set_ylabel("")

    # Add legend for markers
    ax.text(
        0, -0.02,
        "* Known Usher gene   + Known ciliopathy gene   Grey = no data (NULL)",
        transform=ax.transAxes, fontsize=8, va="top", style="italic",
    )

    fig.savefig(FIGDIR / "fig4_top_candidates_heatmap.png", dpi=DPI, bbox_inches="tight")
    fig.savefig(FIGDIR / "fig4_top_candidates_heatmap.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  Fig 4: top candidates heatmap")


# ── Figure 5: Positive control validation ────────────────────────────────

def fig5_validation_controls(df: pl.DataFrame):
    """Distribution of known gene percentile ranks vs background."""
    # Compute percentile ranks
    scored = df.filter(pl.col("composite_score").is_not_null())
    n = scored.height
    ranked = scored.sort("composite_score").with_row_index("rank")
    ranked = ranked.with_columns(
        (pl.col("rank") / n * 100).alias("percentile")
    )

    # Split into groups
    all_known = set(OMIM_USHER_GENES) | set(SYSCILIA_SCGS_V2_CORE)

    usher_pcts = ranked.filter(
        pl.col("gene_symbol").is_in(list(OMIM_USHER_GENES))
    )["percentile"].to_list()

    cilia_pcts = ranked.filter(
        pl.col("gene_symbol").is_in(list(SYSCILIA_SCGS_V2_CORE - OMIM_USHER_GENES))
    )["percentile"].to_list()

    background_pcts = ranked.filter(
        ~pl.col("gene_symbol").is_in(list(all_known))
    )["percentile"].to_list()

    fig, ax = plt.subplots(figsize=(8, 5))

    # Violin/box plot
    data = []
    for p in usher_pcts:
        data.append({"group": f"OMIM Usher\n(n={len(usher_pcts)})", "percentile": p})
    for p in cilia_pcts:
        data.append({"group": f"SYSCILIA\n(n={len(cilia_pcts)})", "percentile": p})
    # Sample background for display
    rng = np.random.default_rng(42)
    bg_sample = rng.choice(background_pcts, size=min(500, len(background_pcts)), replace=False)
    for p in bg_sample:
        data.append({"group": f"Background\n(n={len(background_pcts)})", "percentile": p})

    import pandas as pd
    plot_df = pd.DataFrame(data)

    sns.boxplot(data=plot_df, x="group", y="percentile",
                palette=["#3498db", "#2ecc71", "#bdc3c7"], ax=ax,
                width=0.5, fliersize=2)

    # Add individual points for known genes
    known_df = plot_df[plot_df["group"].str.contains("Usher|SYSCILIA")]
    sns.stripplot(data=known_df, x="group", y="percentile",
                  color="black", size=5, alpha=0.7, ax=ax, jitter=0.15)

    # Reference lines
    ax.axhline(y=75, color="red", linestyle="--", linewidth=0.8, alpha=0.6, label="75th percentile")
    ax.axhline(y=50, color="gray", linestyle=":", linewidth=0.8, alpha=0.6, label="Median")

    ax.set_ylabel("Percentile Rank (%)")
    ax.set_xlabel("")
    ax.set_title("")
    ax.legend(loc="lower left", fontsize=8)
    ax.set_ylim(0, 105)

    fig.savefig(FIGDIR / "fig5_validation_controls.png", dpi=DPI, bbox_inches="tight")
    fig.savefig(FIGDIR / "fig5_validation_controls.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  Fig 5: validation controls")


# ── Figure 7: Sensitivity analysis heatmap ───────────────────────────────

def fig7_sensitivity_heatmap():
    """Heatmap of Spearman rho from weight perturbation sensitivity analysis.

    Spearman rho values are parsed from the current validation report so the
    figure always reflects the most recent pipeline run.
    """
    layer_order = ["gnomad", "expression", "annotation",
                   "localization", "animal_model", "literature"]
    layer_labels = {
        "gnomad": "gnomAD", "expression": "Expression", "annotation": "Annotation",
        "localization": "Localization", "animal_model": "Animal Model",
        "literature": "Literature",
    }
    delta_order = ["-0.10", "-0.05", "+0.05", "+0.10"]
    delta_labels = ["-10%", "-5%", "+5%", "+10%"]

    # Parse Spearman rho from the validation report (regenerated every run)
    report = Path("data/validation/validation_report.md")
    rho = {}
    for line in report.read_text().splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 5 and parts[1] in layer_order and parts[2] in delta_order:
            try:
                rho[(parts[1], parts[2])] = float(parts[3])
            except ValueError:
                continue
    if len(rho) != 24:
        raise RuntimeError(
            f"Expected 24 sensitivity values, parsed {len(rho)} from {report}"
        )

    rho_matrix = np.array([
        [rho[(layer, d)] for d in delta_order] for layer in layer_order
    ])

    fig, ax = plt.subplots(figsize=(6, 5))

    sns.heatmap(
        rho_matrix,
        xticklabels=delta_labels,
        yticklabels=[layer_labels[layer] for layer in layer_order],
        cmap="RdYlGn",
        vmin=0.5, vmax=1.0,
        annot=True, fmt=".3f",
        linewidths=0.5,
        linecolor="white",
        cbar_kws={"label": "Spearman ρ", "shrink": 0.8},
        ax=ax,
    )

    ax.set_xlabel("Weight Perturbation")
    ax.set_ylabel("")
    ax.set_title("")

    fig.savefig(FIGDIR / "fig7_sensitivity_heatmap.png", dpi=DPI, bbox_inches="tight")
    fig.savefig(FIGDIR / "fig7_sensitivity_heatmap.pdf", bbox_inches="tight")
    plt.close(fig)
    print("  Fig 7: sensitivity heatmap")


# ── Main ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating publication figures...")
    print(f"Output: {FIGDIR}/\n")

    df = load_candidates()
    scored = load_scored_genes()

    fig2_score_distribution(df)
    fig3_layer_coverage(df)
    fig4_top_candidates_heatmap(df)
    fig5_validation_controls(scored)
    fig7_sensitivity_heatmap()

    print(f"\nDone. {len(list(FIGDIR.glob('*.png')))} PNG + {len(list(FIGDIR.glob('*.pdf')))} PDF files generated.")

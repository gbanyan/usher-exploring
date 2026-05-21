"""Generate Figure 1: UsherPipe pipeline architecture diagram.

A matplotlib box-and-arrow rendering of the four-stage pipeline. Figure 1 is
produced the same way as the other publication figures (no extra dependency)
and written to data/report/paper_figures/ as fig1_architecture.png/.pdf.

Run:  python scripts/fig1_architecture.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle

FIGDIR = Path("data/report/paper_figures")
FIGDIR.mkdir(parents=True, exist_ok=True)
DPI = 300

C_STAGE, C_STAGE_EDGE = "#dbe9f6", "#2c6da4"      # stage boxes
C_LAYER, C_LAYER_EDGE = "#fdf0d5", "#c9803a"      # evidence-layer boxes
C_DB, C_DB_EDGE = "#e7e2f3", "#6a4fa3"            # DuckDB store
C_ARROW = "#444444"

# Main flow column geometry
FX0, FW = 0.5, 6.7

EVIDENCE_LAYERS = [
    ("gnomAD\nconstraint", "0.20"),
    ("Tissue\nexpression", "0.20"),
    ("Functional\nannotation", "0.15"),
    ("Subcellular\nlocalization", "0.15"),
    ("Animal-model\nphenotypes", "0.15"),
    ("Literature\nmining", "0.15"),
]


def stage_box(ax, x, y, w, h, title, subtitle):
    """Draw a rounded stage box with a bold title and a smaller subtitle."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor=C_STAGE, edgecolor=C_STAGE_EDGE, linewidth=1.6))
    ax.text(x + w / 2, y + h * 0.66, title, ha="center", va="center",
            fontsize=10.5, fontweight="bold", color="#1a1a1a")
    ax.text(x + w / 2, y + h * 0.27, subtitle, ha="center", va="center",
            fontsize=7.8, color="#333333")


def down_arrow(ax, x, y0, y1):
    """Solid downward data-flow arrow from y0 to y1."""
    ax.add_patch(FancyArrowPatch(
        (x, y0), (x, y1), arrowstyle="-|>", mutation_scale=18,
        lw=1.8, color=C_ARROW))


def draw_cylinder(ax, x, y, w, h):
    """Draw a database cylinder (rectangle body with elliptical caps)."""
    cap = 0.5
    ax.add_patch(Rectangle((x, y + cap / 2), w, h - cap,
                           facecolor=C_DB, edgecolor="none"))
    ax.plot([x, x], [y + cap / 2, y + h - cap / 2], color=C_DB_EDGE, lw=1.6)
    ax.plot([x + w, x + w], [y + cap / 2, y + h - cap / 2],
            color=C_DB_EDGE, lw=1.6)
    ax.add_patch(Ellipse((x + w / 2, y + cap / 2), w, cap,
                         facecolor=C_DB, edgecolor=C_DB_EDGE, lw=1.6))
    ax.add_patch(Ellipse((x + w / 2, y + h - cap / 2), w, cap,
                         facecolor=C_DB, edgecolor=C_DB_EDGE, lw=1.6))


def main():
    fig, ax = plt.subplots(figsize=(9.5, 10.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis("off")

    # Stage 1: gene universe
    stage_box(ax, FX0, 10.3, FW, 1.05,
              "1. Gene universe construction",
              "mygene.info API → 22,761 Ensembl IDs →\n"
              "MANE-canonical deduplication → 19,554 genes")
    down_arrow(ax, FX0 + FW / 2, 10.3, 9.55)

    # Stage 2: six evidence layers, inside a dashed group container
    grp_y, grp_h = 7.0, 2.5
    ax.add_patch(FancyBboxPatch(
        (FX0, grp_y), FW, grp_h, boxstyle="round,pad=0.02,rounding_size=0.06",
        facecolor="#f7f7f7", edgecolor="#999999", linewidth=1.2,
        linestyle="--"))
    ax.text(FX0 + FW / 2, grp_y + grp_h - 0.24,
            "2. Six evidence layers   (each: fetch → transform → load)",
            ha="center", va="center", fontsize=9.5, fontweight="bold")

    n = len(EVIDENCE_LAYERS)
    pad = 0.18
    bw = (FW - pad * (n + 1)) / n
    bh, by = 1.35, grp_y + 0.35
    for i, (name, wt) in enumerate(EVIDENCE_LAYERS):
        bx = FX0 + pad + i * (bw + pad)
        ax.add_patch(FancyBboxPatch(
            (bx, by), bw, bh, boxstyle="round,pad=0.02,rounding_size=0.05",
            facecolor=C_LAYER, edgecolor=C_LAYER_EDGE, linewidth=1.3))
        ax.text(bx + bw / 2, by + bh * 0.62, name, ha="center", va="center",
                fontsize=7.8, fontweight="bold")
        ax.text(bx + bw / 2, by + bh * 0.17, f"weight {wt}", ha="center",
                va="center", fontsize=6.8, color="#555555")
    down_arrow(ax, FX0 + FW / 2, grp_y, 5.9)

    # Stage 3: composite scoring
    stage_box(ax, FX0, 4.8, FW, 1.05,
              "3. NULL-aware composite scoring",
              "weighted mean over non-NULL layers; confidence tiers\n"
              "(HIGH / MEDIUM / LOW) with a HIGH-tier cilia-signal gate")
    down_arrow(ax, FX0 + FW / 2, 4.8, 3.9)

    # Stage 4: reporting and validation
    stage_box(ax, FX0, 2.8, FW, 1.05,
              "4. Report generation & validation",
              "candidates.tsv / .parquet, publication figures,\n"
              "positive / negative controls, sensitivity analysis")

    # DuckDB persistent store, with read/write connectors to every stage
    db_x, db_w = 7.7, 1.8
    db_y, db_top = 2.9, 11.35
    draw_cylinder(ax, db_x, db_y, db_w, db_top - db_y)
    ax.text(db_x + db_w / 2, (db_y + db_top) / 2,
            "DuckDB\n\npipeline.duckdb\n\nsingle\npersistent\nstore",
            ha="center", va="center", fontsize=8.5, fontweight="bold",
            color="#3a2a63")
    for cy in (10.82, 8.25, 5.32, 3.32):
        ax.add_patch(FancyArrowPatch(
            (FX0 + FW, cy), (db_x, cy), arrowstyle="<|-|>",
            mutation_scale=10, lw=1.0, color="#8a7fae", linestyle="--"))

    fig.savefig(FIGDIR / "fig1_architecture.png", dpi=DPI, bbox_inches="tight")
    fig.savefig(FIGDIR / "fig1_architecture.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {FIGDIR}/fig1_architecture.png and .pdf")


if __name__ == "__main__":
    main()

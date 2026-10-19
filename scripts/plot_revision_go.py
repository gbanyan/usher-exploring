"""Publication-quality GO functional overview; no changes to historical results."""
import csv
import json
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MultipleLocator

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006/go_classification_20261019"
OUTPUT = ROOT / "outputs/temporal-go-classification-20261019"


def main():
    summary = json.loads((BASE / "summary.json").read_text())
    rows = list(csv.DictReader((BASE / "category_summary.tsv").open(), delimiter="\t"))
    coverage = list(csv.DictReader((BASE / "gene_summary.tsv").open(), delimiter="\t"))
    for r in rows:
        r["genes_of_45"] = int(r["genes_of_45"])
        r["genes_without_IEA"] = int(r["genes_without_IEA"])
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10, "pdf.fonttype":42,
                         "ps.fonttype":42, "svg.fonttype":"none", "axes.spines.top":False,
                         "axes.spines.right":False, "axes.spines.left":False})
    fig, axes = plt.subplots(3, 1, figsize=(10, 13), sharex=True)
    dark, light = "#315E82", "#C8D5DF"
    plotted = []
    for ax, aspect, label in zip(axes, ("BP","MF","CC"), ("A  Biological process", "B  Molecular function", "C  Cellular component")):
        current = sorted([r for r in rows if r["aspect"]==aspect and r["genes_of_45"]>0],
                         key=lambda r:(-r["genes_of_45"],r["go_id"]))[:12]
        plotted.extend(current)
        ys = list(range(len(current)))
        non_iea = [r["genes_without_IEA"] for r in current]
        iea_only = [r["genes_of_45"]-r["genes_without_IEA"] for r in current]
        ax.barh(ys, non_iea, color=dark, height=.66)
        ax.barh(ys, iea_only, left=non_iea, color=light, height=.66)
        ax.set_yticks(ys, [textwrap.fill(r["category"],width=48) for r in current], fontsize=9)
        ax.tick_params(axis="y",length=0,pad=7)
        ax.invert_yaxis()
        ax.set_title(label,loc="left",fontweight="bold",fontsize=12,pad=11)
        ax.set_xlim(0,45)
        ax.xaxis.set_major_locator(MultipleLocator(5))
        ax.grid(axis="x",color="#E4E9ED",linewidth=.6)
        ax.set_axisbelow(True)
        for y,r in zip(ys,current):
            ax.text(r["genes_of_45"]+.55,y,str(r["genes_of_45"]),va="center",fontsize=9)
        available = sum(int(g[f"{aspect}_direct_terms"])>0 for g in coverage)
        ax.text(1,1.02,f"{available}/45 genes with usable {aspect} annotations",transform=ax.transAxes,
                ha="right",va="bottom",fontsize=9,color="#52657A")
    axes[-1].set_xlabel("Number of genes in the 45-case cohort",labelpad=8)
    fig.suptitle("GO functional overview of the temporal cases",x=.04,y=.985,ha="left",fontsize=15,fontweight="bold")
    fig.text(.04,.96,"Contemporary GO annotations, grouped with generic GO slim",fontsize=11,color="#52657A")
    fig.legend(handles=[Patch(color=dark,label="Supported by a non-IEA annotation"),Patch(color=light,label="IEA only for this category")],
               loc="upper left",bbox_to_anchor=(.03,.948),frameon=False,ncol=2,fontsize=9)
    fig.text(.04,.025,"Categories overlap; a gene can occur in multiple bars. The 12 most frequent categories per aspect are shown.\n"
             "Non-IEA does not necessarily mean experimental evidence. RNA annotations are retained where explicitly mapped.\n"
             f"GO release {summary['ontology_version']['timestamp']}; GOA files generated 11 October 2026. Classification is descriptive.",
             fontsize=8.5,color="#52657A",linespacing=1.5)
    fig.subplots_adjust(left=.40,right=.95,top=.90,bottom=.13,hspace=.35)
    OUTPUT.mkdir(exist_ok=True,parents=True)
    for ext in ("png","pdf","svg"):
        fig.savefig(OUTPUT/f"Temporal_GO_Functional_Overview_20261019.{ext}",dpi=300,facecolor="white")
    plt.close(fig)
    (BASE/"figure_data.json").write_text(json.dumps(plotted,indent=2)+"\n")
    print("Saved PNG, PDF and SVG of the fixed top-12-per-aspect functional overview.")


if __name__ == "__main__":
    main()

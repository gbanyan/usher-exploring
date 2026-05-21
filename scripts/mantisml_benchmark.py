"""Benchmark UsherPipe against mantis-ml on known Usher/cilia gene recovery.

Compares the two complete tools on a shared gene universe using identical
metrics: median percentile rank of the known genes present in that universe,
recall@k, ROC-AUC, and housekeeping-gene specificity. The curated known set
has 38 genes; 36 fall inside the shared universe (ADGRV1 and WHRN are absent
from one tool's gene set). mantis-ml is seed-based; its `known_gene` flag is
used to also report metrics on the subset NOT used as mantis-ml seeds, since
evaluating a seed-based tool on its own seeds is partly circular.

mantis-ml provenance: v1.6.5, standard stochastic semi-supervised run
(10 iterations), six-classifier consensus (Extra Trees, Random Forest,
Gradient Boosting, SVM, XGBoost, deep neural net). Per-classifier prediction
CSVs are cached in data/external/mantisml/.

Usage:
    python scripts/mantisml_benchmark.py --mantisml-dir <dir of *.mantis-ml_predictions.csv>
"""

import argparse
import csv
import sys
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OMIM_USHER = ["ADGRV1", "CDH23", "CIB2", "CLRN1", "MYO7A",
              "PCDH15", "USH1C", "USH1G", "USH2A", "WHRN"]
SYSCILIA = ["ARL13B", "BBS1", "BBS2", "BBS4", "BBS5", "BBS7", "BBS9", "BBS10",
            "CC2D2A", "CEP164", "CEP290", "IFT88", "IFT140", "IFT172", "INPP5E",
            "MKS1", "NPHP1", "NPHP3", "NPHP4", "OFD1", "RPGR", "RPGRIP1L",
            "TCTN1", "TCTN2", "TMEM67", "TMEM138", "TMEM216", "TMEM231"]
KNOWN = OMIM_USHER + SYSCILIA
HOUSEKEEPING = ["GAPDH", "ACTB", "B2M", "UBC", "PPIA", "YWHAZ", "HPRT1",
                "TBP", "SDHA", "PGK1", "RPLP0", "RPL13A", "RPL32"]

DUCKDB = "data/pipeline.duckdb"
OUT_CSV = "data/report/mantisml_benchmark.csv"
OUT_FIG = "data/report/paper_figures/fig8_mantisml_benchmark"


def load_usherpipe():
    """Return {gene_symbol: composite_score} for UsherPipe scored genes."""
    con = duckdb.connect(DUCKDB, read_only=True)
    rows = con.execute(
        "select gene_symbol, composite_score from scored_genes "
        "where composite_score is not null"
    ).fetchall()
    con.close()
    return {g: s for g, s in rows}


def load_mantisml(pred_dir):
    """Build the mantis-ml consensus from per-classifier prediction CSVs.

    The consensus score is the mean of `mantis_ml_proba` across all
    `*.mantis-ml_predictions.csv` files in `pred_dir` (one per classifier) —
    this is mantis-ml's standard cross-classifier consensus. A gene is a
    mantis-ml seed if flagged `known_gene == 1` in any classifier file.

    Returns ({gene: consensus_proba}, set_of_seed_genes, n_classifiers).
    """
    files = sorted(Path(pred_dir).glob("*.mantis-ml_predictions.csv"))
    if not files:
        sys.exit(f"No *.mantis-ml_predictions.csv files in {pred_dir}")
    sums, counts, seeds = {}, {}, set()
    for f in files:
        with open(f) as fh:
            for row in csv.DictReader(fh):
                gene = row["Gene_Name"].strip().upper()
                sums[gene] = sums.get(gene, 0.0) + float(row["mantis_ml_proba"])
                counts[gene] = counts.get(gene, 0) + 1
                if str(row.get("known_gene", "")).strip() in ("1", "1.0"):
                    seeds.add(gene)
    scores = {g: sums[g] / counts[g] for g in sums}
    return scores, seeds, len(files)


def percentile_ranks(scores):
    """Map each gene to its percentile rank (0-100) within `scores`."""
    ordered = sorted(scores.items(), key=lambda kv: kv[1])
    n = len(ordered)
    return {g: 100.0 * (i + 1) / n for i, (g, _) in enumerate(ordered)}


def auc(scores, positives):
    """ROC-AUC of `scores` separating `positives` from the rest (Mann-Whitney U)."""
    pos = [s for g, s in scores.items() if g in positives]
    neg = [s for g, s in scores.items() if g not in positives]
    if not pos or not neg:
        return float("nan")
    wins = 0.0
    neg_sorted = sorted(neg)
    import bisect
    for p in pos:
        lo = bisect.bisect_left(neg_sorted, p)
        hi = bisect.bisect_right(neg_sorted, p)
        wins += lo + 0.5 * (hi - lo)
    return wins / (len(pos) * len(neg))


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return float("nan")
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def evaluate(name, scores, known, housekeeping):
    """Compute the metric bundle for one tool on a fixed gene universe."""
    perc = percentile_ranks(scores)
    known_in = [g for g in known if g in perc]
    hk_in = [g for g in housekeeping if g in perc]
    kp = [perc[g] for g in known_in]
    n = len(perc)
    recall = {}
    for thr in (5, 10, 20):
        cut = 100 - thr
        recall[thr] = 100.0 * sum(1 for v in kp if v >= cut) / len(kp)
    return {
        "tool": name,
        "n_universe": n,
        "n_known": len(known_in),
        "known_median_pctile": round(median(kp), 1),
        "known_top_quartile_frac": round(100.0 * sum(1 for v in kp if v >= 75) / len(kp), 1),
        "recall_at_5pct": round(recall[5], 1),
        "recall_at_10pct": round(recall[10], 1),
        "recall_at_20pct": round(recall[20], 1),
        "roc_auc": round(auc(scores, set(known_in)), 4),
        "housekeeping_median_pctile": round(median([perc[g] for g in hk_in]), 1),
        "_known_pctiles": {g: perc[g] for g in known_in},
        "_hk_pctiles": {g: perc[g] for g in hk_in},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mantisml-dir", default="data/external/mantisml",
                    help="Directory of mantis-ml per-classifier *.mantis-ml_predictions.csv")
    args = ap.parse_args()

    up = load_usherpipe()
    mm, seeds, n_clf = load_mantisml(args.mantisml_dir)
    print(f"mantis-ml consensus over {n_clf} classifiers")

    # Restrict both tools to the shared gene universe (fair comparison)
    common = set(up) & set(mm)
    up = {g: s for g, s in up.items() if g in common}
    mm = {g: s for g, s in mm.items() if g in common}
    print(f"Shared gene universe: {len(common)} genes "
          f"(UsherPipe {len(load_usherpipe())}, mantis-ml {len(mm)} after intersect)")

    known_common = [g for g in KNOWN if g in common]
    seeds_among_known = [g for g in known_common if g in seeds]
    heldout_known = [g for g in known_common if g not in seeds]
    print(f"Known genes in universe: {len(known_common)}/38 "
          f"({len(seeds_among_known)} were mantis-ml seeds, "
          f"{len(heldout_known)} not)")

    n_known = len(known_common)
    rows = [
        evaluate("UsherPipe", up, known_common, HOUSEKEEPING),
        evaluate(f"mantis-ml (all {n_known} shared known)", mm, known_common, HOUSEKEEPING),
        evaluate("mantis-ml (non-seed known only)", mm, heldout_known, HOUSEKEEPING),
        evaluate("UsherPipe (non-seed known only)", up, heldout_known, HOUSEKEEPING),
    ]

    cols = ["tool", "n_universe", "n_known", "known_median_pctile",
            "known_top_quartile_frac", "recall_at_5pct", "recall_at_10pct",
            "recall_at_20pct", "roc_auc", "housekeeping_median_pctile"]
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])
    print(f"\nWrote {OUT_CSV}")

    print("\n=== Benchmark ===")
    hdr = f"{'tool':34s} {'med%':>6s} {'TQ%':>6s} {'R@10':>6s} {'R@20':>6s} {'AUC':>7s} {'HK med%':>8s}"
    print(hdr)
    for r in rows:
        print(f"{r['tool']:34s} {r['known_median_pctile']:6.1f} "
              f"{r['known_top_quartile_frac']:6.1f} {r['recall_at_10pct']:6.1f} "
              f"{r['recall_at_20pct']:6.1f} {r['roc_auc']:7.4f} "
              f"{r['housekeeping_median_pctile']:8.1f}")

    # ---- Figure: known-gene percentile distributions + metric bars ----
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))

    up_eval = rows[0]
    mm_eval = rows[1]
    data = [list(up_eval["_known_pctiles"].values()),
            list(mm_eval["_known_pctiles"].values())]
    bp = ax1.boxplot(data, labels=["UsherPipe", "mantis-ml"], widths=0.55,
                     patch_artist=True, showmeans=True)
    for patch, color in zip(bp["boxes"], ["#2c7fb8", "#de2d26"]):
        patch.set_facecolor(color)
        patch.set_alpha(0.55)
    for i, d in enumerate(data, 1):
        ax1.scatter([i] * len(d), d, s=14, color="black", alpha=0.45, zorder=3)
    ax1.axhline(75, ls="--", color="gray", lw=1)
    ax1.set_ylabel(f"Percentile rank of {len(known_common)} known genes "
                   f"(shared universe)")
    ax1.set_title("Known-gene recovery")
    ax1.set_ylim(0, 102)

    metrics = ["known_median_pctile", "recall_at_10pct",
               "recall_at_20pct", "housekeeping_median_pctile"]
    labels = ["Known\nmedian %ile", "Recall\n@10%", "Recall\n@20%",
              "Housekeeping\nmedian %ile"]
    x = range(len(metrics))
    w = 0.38
    ax2.bar([i - w / 2 for i in x], [up_eval[m] for m in metrics], w,
            label="UsherPipe", color="#2c7fb8")
    ax2.bar([i + w / 2 for i in x], [mm_eval[m] for m in metrics], w,
            label="mantis-ml", color="#de2d26")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(labels, fontsize=9)
    ax2.set_ylabel("Value")
    ax2.set_title("Benchmark metrics")
    ax2.legend()

    ax1.text(-0.08, 1.05, "A", transform=ax1.transAxes, fontsize=16,
             fontweight="bold", va="bottom", ha="right")
    ax2.text(-0.08, 1.05, "B", transform=ax2.transAxes, fontsize=16,
             fontweight="bold", va="bottom", ha="right")

    fig.tight_layout()
    fig.savefig(OUT_FIG + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(OUT_FIG + ".pdf", bbox_inches="tight")
    print(f"Wrote {OUT_FIG}.png/.pdf")


if __name__ == "__main__":
    sys.exit(main())

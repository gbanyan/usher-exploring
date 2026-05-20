"""Held-out weight tuning to test whether the specificity problem is fixable.

Housekeeping negative controls rank too highly under the a-priori weights.
This script asks: can re-weighting the six evidence layers separate known
disease genes from housekeeping genes WITHOUT circular validation?

Method:
  * Recompute the NULL-aware composite for every gene under a candidate
    weight vector (no pipeline re-run needed; per-layer scores are in the DB).
  * 5-fold stratified cross-validation: in each fold, weights are tuned ONLY
    on the training genes and the held-out genes are then scored — so every
    reported held-out number comes from genes not used to pick the weights.
  * Objective: maximise mean(known percentile) - mean(housekeeping percentile)
    on the training genes.
  * Finally, tune on all control genes for the proposed weight vector; the CV
    result is the unbiased estimate of how it generalises.

Run:  .venv312/bin/python scripts/weight_tuning.py
"""

import itertools
import statistics

import duckdb
import numpy as np

LAYERS = ["gnomad_score", "expression_score", "annotation_score",
          "localization_score", "animal_model_score", "literature_score"]
DEFAULT_W = np.array([0.20, 0.20, 0.15, 0.15, 0.15, 0.15])

OMIM_USHER = ["ADGRV1", "CDH23", "CIB2", "CLRN1", "MYO7A",
              "PCDH15", "USH1C", "USH1G", "USH2A", "WHRN"]
SYSCILIA = ["ARL13B", "BBS1", "BBS2", "BBS4", "BBS5", "BBS7", "BBS9", "BBS10",
            "CC2D2A", "CEP164", "CEP290", "IFT88", "IFT140", "IFT172", "INPP5E",
            "MKS1", "NPHP1", "NPHP3", "NPHP4", "OFD1", "RPGR", "RPGRIP1L",
            "TCTN1", "TCTN2", "TMEM67", "TMEM138", "TMEM216", "TMEM231"]
KNOWN = OMIM_USHER + SYSCILIA
HOUSEKEEPING = ["GAPDH", "ACTB", "B2M", "UBC", "PPIA", "YWHAZ", "HPRT1",
                "TBP", "SDHA", "PGK1", "RPLP0", "RPL13A", "RPL32"]

WEIGHT_STEP = 0.05
WMIN, WMAX = 0.05, 0.40   # per-layer bounds keep every layer contributing


def load_scores():
    """Return (gene_symbols, score_matrix[n,6] with NaN for NULL)."""
    con = duckdb.connect("data/pipeline.duckdb", read_only=True)
    rows = con.execute(
        f"select gene_symbol, {', '.join(LAYERS)} from scored_genes"
    ).fetchall()
    con.close()
    genes = [r[0] for r in rows]
    mat = np.array([[np.nan if v is None else float(v) for v in r[1:]]
                    for r in rows])
    return genes, mat


def composite(mat, w):
    """NULL-aware weighted composite: sum(score*w)/sum(w) over non-NaN layers."""
    mask = ~np.isnan(mat)
    wrow = np.where(mask, w, 0.0)
    num = np.nansum(np.where(mask, mat, 0.0) * wrow, axis=1)
    den = wrow.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        comp = np.where(den > 0, num / den, np.nan)
    return comp


def percentiles(comp):
    """Percentile rank (0-100) of each gene among non-NaN composites."""
    valid = ~np.isnan(comp)
    order = np.argsort(np.argsort(comp[valid]))
    perc = np.full(comp.shape, np.nan)
    perc[valid] = 100.0 * (order + 1) / valid.sum()
    return perc


def weight_grid():
    """All 6-weight vectors on a 0.05 simplex with per-layer bounds."""
    units = round(1.0 / WEIGHT_STEP)            # 20
    lo, hi = round(WMIN / WEIGHT_STEP), round(WMAX / WEIGHT_STEP)  # 1, 8
    grid = []
    for combo in itertools.product(range(lo, hi + 1), repeat=5):
        last = units - sum(combo)
        if lo <= last <= hi:
            grid.append(np.array(combo + (last,)) * WEIGHT_STEP)
    return grid


def objective(perc, idx_known, idx_hk):
    """Separation: mean known percentile minus mean housekeeping percentile."""
    return np.nanmean(perc[idx_known]) - np.nanmean(perc[idx_hk])


def tune(mat, idx_known, idx_hk, grid):
    """Return the grid weight vector maximising training-set separation."""
    best_w, best_obj = None, -1e9
    for w in grid:
        perc = percentiles(composite(mat, w))
        o = objective(perc, idx_known, idx_hk)
        if o > best_obj:
            best_obj, best_w = o, w
    return best_w


def med(perc, idx):
    return statistics.median([perc[i] for i in idx if not np.isnan(perc[i])])


def main():
    genes, mat = load_scores()
    gidx = {g: i for i, g in enumerate(genes)}
    known = [gidx[g] for g in KNOWN if g in gidx]
    hk = [gidx[g] for g in HOUSEKEEPING if g in gidx]
    print(f"{len(genes)} scored genes; {len(known)} known, {len(hk)} housekeeping")

    grid = weight_grid()
    print(f"weight grid: {len(grid)} candidate vectors\n")

    # ---- baseline (a-priori default weights) ----
    p0 = percentiles(composite(mat, DEFAULT_W))
    print("=== Default a-priori weights ===")
    print(f"  weights: {dict(zip(LAYERS, DEFAULT_W))}")
    print(f"  known median percentile:        {med(p0, known):.1f}")
    print(f"  housekeeping median percentile: {med(p0, hk):.1f}\n")

    # ---- 5-fold stratified CV: weights tuned on train, scored on held-out ----
    rng = np.random.default_rng(42)
    known_sh = known.copy(); hk_sh = hk.copy()
    rng.shuffle(known_sh); rng.shuffle(hk_sh)
    K = 5
    known_folds = [known_sh[i::K] for i in range(K)]
    hk_folds = [hk_sh[i::K] for i in range(K)]

    cv_known, cv_hk = [], []
    for f in range(K):
        test_k, test_h = known_folds[f], hk_folds[f]
        train_k = [i for i in known if i not in test_k]
        train_h = [i for i in hk if i not in test_h]
        w = tune(mat, train_k, train_h, grid)
        perc = percentiles(composite(mat, w))
        cv_known += [perc[i] for i in test_k]
        cv_hk += [perc[i] for i in test_h]

    print("=== 5-fold cross-validated tuning (held-out genes only) ===")
    print(f"  known median percentile (held-out):        "
          f"{statistics.median(cv_known):.1f}")
    print(f"  housekeeping median percentile (held-out): "
          f"{statistics.median(cv_hk):.1f}\n")

    # ---- final weights tuned on all control genes ----
    wf = tune(mat, known, hk, grid)
    pf = percentiles(composite(mat, wf))
    print("=== Final tuned weights (tuned on all 51 control genes) ===")
    print(f"  weights: {dict(zip(LAYERS, [round(x, 2) for x in wf]))}")
    print(f"  known median percentile:        {med(pf, known):.1f}")
    print(f"  housekeeping median percentile: {med(pf, hk):.1f}")
    hk_high = sum(1 for i in hk if not np.isnan(pf[i]) and
                  composite(mat, wf)[i] >= 0.7)
    print(f"  housekeeping genes with composite >= 0.70: {hk_high}")


if __name__ == "__main__":
    main()

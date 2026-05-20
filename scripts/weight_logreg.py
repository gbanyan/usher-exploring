"""Prototype: derive UsherPipe layer weights by L2 logistic regression.

Fits a transparent linear classifier (ridge logistic regression) on the 38
known disease genes (positives) vs. resampled background genes (treated as
presumed-negative), keeping the 13 housekeeping controls as a held-aside
specificity sentinel that never enters training. The six fitted coefficients
are converted to NULL-aware composite weights.

  * Bootstrap (resampled positives + resampled background) -> weight 95% CIs.
  * 5-fold CV over the known genes -> held-out known-gene percentile.
  * Under-studied-candidate survival check: rank correlation vs. the default
    weighting and the new top candidate list, to confirm re-weighting does
    not collapse the pipeline onto two layers or bury sparse-evidence genes.

This is a PROTOTYPE for evaluation, not wired into the pipeline.

Run:  .venv312/bin/python scripts/weight_logreg.py
"""

import statistics

import duckdb
import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression

LAYERS = ["gnomad_score", "expression_score", "annotation_score",
          "localization_score", "animal_model_score", "literature_score"]
SHORT = ["gnomAD", "expr", "annot", "local", "animal", "lit"]
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

C_RIDGE = 1.0          # inverse L2 strength
NEG_RATIO = 5          # background negatives per positive, per bootstrap
N_BOOT = 400
RNG = np.random.default_rng(42)


def load():
    con = duckdb.connect("data/pipeline.duckdb", read_only=True)
    rows = con.execute(
        f"select gene_symbol, {', '.join(LAYERS)}, evidence_count "
        f"from scored_genes"
    ).fetchall()
    con.close()
    genes = [r[0] for r in rows]
    mat = np.array([[np.nan if v is None else float(v) for v in r[1:7]]
                    for r in rows])
    evc = np.array([r[7] for r in rows])
    return genes, mat, evc


def composite(mat, w):
    """NULL-aware weighted composite over non-NaN layers."""
    mask = ~np.isnan(mat)
    wrow = np.where(mask, w, 0.0)
    num = np.nansum(np.where(mask, mat, 0.0) * wrow, axis=1)
    den = wrow.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def percentiles(comp):
    valid = ~np.isnan(comp)
    order = np.argsort(np.argsort(comp[valid]))
    perc = np.full(comp.shape, np.nan)
    perc[valid] = 100.0 * (order + 1) / valid.sum()
    return perc


def med(perc, idx):
    vals = [perc[i] for i in idx if not np.isnan(perc[i])]
    return statistics.median(vals)


def build_matched_negatives(mat, known, exclude, k=2):
    """Study-matched non-disease negatives.

    For each known gene, pick its k nearest background genes in the space of
    (gnomAD constraint, annotation depth, literature score) -- the 'generic
    biological importance / study intensity' axes. Matching on these
    confounders means literature/constraint/annotation cannot separate
    positives from negatives, forcing the classifier onto disease-specific
    signal. The cilia-specific layers are deliberately NOT matched on.
    """
    mf = mat[:, [0, 2, 5]]                       # gnomAD, annotation, literature
    valid = ~np.isnan(mf).any(axis=1)
    mu = np.nanmean(mf[valid], axis=0)
    sd = np.nanstd(mf[valid], axis=0)
    Z = (mf - mu) / sd
    eligible = np.array([i for i in range(len(mat))
                         if valid[i] and i not in exclude])
    chosen = []
    chosen_set = set()
    for kg in known:
        if not valid[kg]:
            continue
        d = np.sqrt(((Z[eligible] - Z[kg]) ** 2).sum(axis=1))
        cnt = 0
        for cand in eligible[np.argsort(d)]:
            if cand not in chosen_set:
                chosen.append(int(cand))
                chosen_set.add(int(cand))
                cnt += 1
                if cnt >= k:
                    break
    return sorted(chosen_set)


def fit_coef(X, pos, neg):
    """Ridge logistic regression on positives vs negatives; return 6 coefs."""
    Xtr = np.vstack([X[pos], X[neg]])
    ytr = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
    clf = LogisticRegression(C=C_RIDGE, class_weight="balanced",
                             max_iter=2000, solver="lbfgs")  # L2 is the default
    clf.fit(Xtr, ytr)
    return clf.coef_[0]


def coef_to_weights(coef):
    """Non-negative, sum-to-1 weights from coefficients (clip negatives)."""
    clipped = np.clip(coef, 0.0, None)
    if clipped.sum() == 0:
        return DEFAULT_W.copy()
    return clipped / clipped.sum()


def main():
    genes, mat, evc = load()
    gidx = {g: i for i, g in enumerate(genes)}
    known = [gidx[g] for g in KNOWN if g in gidx]
    hk = [gidx[g] for g in HOUSEKEEPING if g in gidx]
    known_set, hk_set = set(known), set(hk)
    scored = [i for i in range(len(genes)) if not np.isnan(mat[i]).all()]

    # Study-matched non-disease negative controls
    matched = build_matched_negatives(mat, known, known_set | hk_set, k=2)
    print(f"{len(genes)} genes; {len(known)} known positives, "
          f"{len(matched)} study-matched negatives, {len(hk)} housekeeping sentinel\n")

    print("=== Matched-negative quality (mean layer score) ===")
    print(f"  {'layer':9s} {'known':>8s} {'matched-neg':>12s} {'all genes':>10s}")
    for j, name in enumerate(SHORT):
        kv = np.nanmean(mat[known, j])
        mv = np.nanmean(mat[matched, j])
        av = np.nanmean(mat[scored, j])
        print(f"  {name:9s} {kv:8.3f} {mv:12.3f} {av:10.3f}")
    print("  (matched on gnomAD/annot/lit; cilia layers left free)\n")

    # Median imputation for the design matrix (fit only; pipeline stays NULL-aware)
    col_med = np.nanmedian(mat, axis=0)
    X = np.where(np.isnan(mat), col_med, mat)

    # ---- Bootstrap: weight estimates + 95% CIs ----
    boot = []
    for _ in range(N_BOOT):
        pos = RNG.choice(known, len(known), replace=True)
        neg = RNG.choice(matched, len(matched), replace=True)
        boot.append(fit_coef(X, pos, neg))
    boot = np.array(boot)
    coef_mean = boot.mean(axis=0)
    coef_lo, coef_hi = np.percentile(boot, [2.5, 97.5], axis=0)
    weights = coef_to_weights(coef_mean)

    print("=== Ridge logistic-regression coefficients (bootstrap) ===")
    for j, name in enumerate(SHORT):
        neg_flag = "  <-- NEGATIVE" if coef_hi[j] < 0 else ""
        print(f"  {name:7s} coef={coef_mean[j]:+.3f}  "
              f"95% CI [{coef_lo[j]:+.3f}, {coef_hi[j]:+.3f}]{neg_flag}")
    print("\n  derived weights (clip<0, normalise):")
    for j, name in enumerate(SHORT):
        print(f"    {name:7s} {weights[j]:.3f}   (default {DEFAULT_W[j]:.2f})")

    # ---- Evaluate default vs derived weights ----
    p_def = percentiles(composite(mat, DEFAULT_W))
    p_new = percentiles(composite(mat, weights))
    c_new = composite(mat, weights)
    hk_high = sum(1 for i in hk if not np.isnan(c_new[i]) and c_new[i] >= 0.7)
    hk_high_def = sum(1 for i in hk
                      if (cc := composite(mat, DEFAULT_W)[i]) and cc >= 0.7)
    print("\n=== Specificity / sensitivity ===")
    print(f"  {'':22s} {'default':>9s} {'logreg':>9s}")
    print(f"  {'known median %ile':22s} {med(p_def, known):9.1f} "
          f"{med(p_new, known):9.1f}")
    print(f"  {'housekeeping median':22s} {med(p_def, hk):9.1f} "
          f"{med(p_new, hk):9.1f}")
    print(f"  {'housekeeping in HIGH':22s} {hk_high_def:9d} {hk_high:9d}")

    # ---- 5-fold CV: held-out known-gene percentile ----
    ks = known.copy()
    RNG.shuffle(ks)
    cv_known = []
    for f in range(5):
        test = ks[f::5]
        train = [i for i in known if i not in test]
        w = coef_to_weights(fit_coef(X, train, matched))
        perc = percentiles(composite(mat, w))
        cv_known += [perc[i] for i in test]
    print(f"  known median %ile (5-fold held-out): "
          f"{statistics.median(cv_known):.1f}")

    # ---- Under-studied / discovery survival check ----
    rho = spearmanr(p_def[scored], p_new[scored], nan_policy="omit").statistic
    print("\n=== Discovery-survival check ===")
    print(f"  Spearman rho (default vs logreg full ranking): {rho:.3f}")
    for label, lo, hi in [("genes with 2-3 layers", 2, 3),
                          ("genes with 4-5 layers", 4, 5),
                          ("genes with 6 layers", 6, 6)]:
        sel = [i for i in scored if lo <= evc[i] <= hi]
        shift = np.nanmean([p_new[i] - p_def[i] for i in sel])
        print(f"  mean percentile shift, {label}: {shift:+.1f}")
    order = sorted([i for i in scored if evc[i] >= 4 and not np.isnan(c_new[i])],
                   key=lambda i: -c_new[i])[:15]
    print("  new top-15 candidates (>=4 layers):")
    print("   ", ", ".join(genes[i] for i in order))


if __name__ == "__main__":
    main()

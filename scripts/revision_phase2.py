"""Read-only post-review diagnostics; never tune or persist production scores."""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from importlib.metadata import version
from pathlib import Path
import subprocess
import sys

import duckdb
import numpy as np
import polars as pl
from scipy.stats import rankdata, spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from usher_pipeline.config.loader import load_config
from usher_pipeline.evidence.expression.models import (
    GTEX_TPM_COLUMNS, HPA_NTPM_COLUMNS, RESTRICTED_TAU_COLUMN,
)
from usher_pipeline.evidence.expression.transform import (
    calculate_tau_specificity, compute_expression_score,
)
from usher_pipeline.evidence.localization.models import LOCALIZATION_GATE_SOURCE_COLUMNS
from usher_pipeline.scoring.known_genes import ESTABLISHED_USHER_GENES, SYSCILIA_SCGS_V2_CORE
from usher_pipeline.scoring.negative_controls import HOUSEKEEPING_GENES_CORE

LAYERS = ["gnomad", "expression", "annotation", "localization", "animal_model", "literature"]
GROUPS = {"usher": ESTABLISHED_USHER_GENES, "syscilia": SYSCILIA_SCGS_V2_CORE,
          "housekeeping": HOUSEKEEPING_GENES_CORE}
KS = (25, 50, 100)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def clean(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def write_table(path, rows):
    if not rows:
        raise ValueError(f"Empty output table: {path}")
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(clean(row) for row in rows)


def weighted_mean(values, weights):
    observed = np.isfinite(values)
    denominator = observed @ weights
    numerator = np.nan_to_num(values, nan=0.0) @ weights
    scores = np.full(len(values), np.nan)
    np.divide(numerator, denominator, out=scores, where=denominator > 0)
    return scores


def percentile(scores):
    result = np.full(len(scores), np.nan)
    valid = np.isfinite(scores)
    n = int(valid.sum())
    if n:
        result[valid] = (rankdata(scores[valid], method="min") - 1) / (n - 1) if n > 1 else 0
    return result


def order(scores, ids):
    valid = np.flatnonzero(np.isfinite(scores))
    return valid[np.lexsort((ids[valid], -scores[valid]))]


def correlation(left, right):
    mask = np.isfinite(left) & np.isfinite(right)
    n = int(mask.sum())
    if n < 3 or np.unique(left[mask]).size < 2 or np.unique(right[mask]).size < 2:
        return np.nan, n
    return float(spearmanr(left[mask], right[mask]).statistic), n


def tiers(scores, counts, gate):
    return np.where((scores >= .70) & (counts >= 3) & gate, "HIGH",
                    np.where((scores >= .40) & (counts >= 2), "MEDIUM",
                             np.where(scores >= .20, "LOW", "EXCLUDED")))


def production_gate(df):
    direct = df.select(pl.any_horizontal([
        pl.col(col).fill_null(False) for col in LOCALIZATION_GATE_SOURCE_COLUMNS
    ])).to_series().to_numpy()
    animal = df["animal_model_score"].to_numpy()
    positive = animal[np.isfinite(animal) & (animal > 0)]
    q75 = pl.Series(positive).quantile(.75) if len(positive) else np.nan
    animal_gate = np.isfinite(animal) & (animal > 0) & (animal >= q75)
    return direct, animal_gate, q75


def recompute_expression(df, remove_proxy=False):
    """Apply unchanged production functions to stored source observations."""
    if remove_proxy:
        df = df.with_columns([
            pl.lit(None).cast(df.schema[col]).alias(col)
            for col in df.columns if "cerebellum" in col
        ])
    source_taus = []
    for name, columns in (("hpa", HPA_NTPM_COLUMNS), ("gtex", GTEX_TPM_COLUMNS)):
        available = [col for col in columns if col in df.columns]
        if len(available) >= 2:
            df = calculate_tau_specificity(df, available).rename({RESTRICTED_TAU_COLUMN: f"_tau_{name}"})
            source_taus.append(f"_tau_{name}")
    tau = pl.mean_horizontal([pl.col(col) for col in source_taus]) if source_taus else pl.lit(None)
    df = df.with_columns(tau.alias(RESTRICTED_TAU_COLUMN))
    return compute_expression_score(df)


def scheme_vectors(default):
    result = {"default": ("default", default), "equal": ("modest_weights", np.ones(6) / 6)}
    for j, layer in enumerate(LAYERS):
        single = np.zeros(6); single[j] = 1
        result[f"single_{layer}"] = ("single_layer", single)
        loo = default.copy(); loo[j] = 0; loo /= loo.sum()
        result[f"loo_{layer}"] = ("leave_one_out", loo)
        for delta in (-.10, -.05, .05, .10):
            perturbed = default.copy(); perturbed[j] += delta; perturbed /= perturbed.sum()
            result[f"perturb_{layer}_{delta:+.2f}"] = ("modest_weights", perturbed)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "revision/major_revision_20261006/results")
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out.exists():
        raise FileExistsError("Use a new output directory; preserve previous analysis results")
    db = ROOT / "data/pipeline.duckdb"
    recovery = json.loads((ROOT / "data/report/database_recovery_20261006.json").read_text())
    if digest(db) != recovery["database_sha256"]:
        raise ValueError("Active DB differs from verified submission recovery")
    protected = [db, ROOT / "config/default.yaml", ROOT / "manuscript/draft.md"]
    protected += sorted((ROOT / "submission/bmc_bioinformatics").glob("*"))
    protected += [ROOT / "data/report/candidates.tsv", ROOT / "data/report/checksum_manifest.json"]
    before = {str(p.relative_to(ROOT)): digest(p) for p in protected if p.is_file()}
    con = duckdb.connect(str(db), read_only=True)
    try:
        for table in ("scored_genes", "tissue_expression"):
            con.execute(f"DESCRIBE {table}").fetchall()
        df = con.execute("SELECT * FROM scored_genes ORDER BY gene_id").pl()
        expression = con.execute("SELECT * FROM tissue_expression ORDER BY gene_id").pl()
    finally:
        con.close()
    if df.height != 20081 or expression.height != 20116:
        raise ValueError("Unexpected analysis populations")
    ids = np.array(df["gene_id"].to_list())
    symbols = np.array(df["gene_symbol"].to_list())
    values = df.select([f"{layer}_score" for layer in LAYERS]).to_numpy()
    counts = np.isfinite(values).sum(axis=1)
    configured = load_config(ROOT / "config/default.yaml").scoring.model_dump()
    default = np.array([configured[k] for k in LAYERS])
    baseline = weighted_mean(values, default)
    if not np.allclose(baseline, df["composite_score"].to_numpy(), atol=1e-12, rtol=0, equal_nan=True):
        raise ValueError("Baseline scoring does not reproduce production")
    # Retain production floating-point values for its exact tie/percentile policy.
    baseline = df["composite_score"].to_numpy()
    direct, animal_gate, q75 = production_gate(df)
    animal = values[:, 4]
    gate = direct | animal_gate
    tier = tiers(baseline, counts, gate)
    reference = pl.read_csv(ROOT / "data/report/candidates.tsv", separator="\t")
    expected_tiers = dict(zip(reference["gene_id"], reference["confidence_tier"]))
    if any(t != expected_tiers.get(gid, "EXCLUDED") for gid, t in zip(ids, tier)):
        raise ValueError("Tier implementation differs from production")
    indices = {name: np.flatnonzero(np.isin(symbols, list(genes))) for name, genes in GROUPS.items()}
    vectors = scheme_vectors(default)
    scores = {name: weighted_mean(values, weights) for name, (_, weights) in vectors.items()}
    scores["default"] = baseline
    print("Production baseline reproduced; evaluating 38 fixed score schemes", flush=True)

    expr_base = recompute_expression(expression)
    if not np.allclose(expr_base["expression_score_normalized"].to_numpy(), expression["expression_score_normalized"].to_numpy(), atol=1e-12, rtol=0, equal_nan=True):
        raise ValueError("Source-column expression reconstruction differs from production")
    expr_removed = recompute_expression(expression, remove_proxy=True)
    proxy_by_id = dict(zip(expr_removed["gene_id"], expr_removed["expression_score_normalized"]))
    proxy_values = values.copy()
    proxy_values[:, 1] = [np.nan if proxy_by_id[gid] is None else proxy_by_id[gid] for gid in ids]
    scores["no_cerebellum"] = weighted_mean(proxy_values, default)

    out.mkdir(parents=True)
    pct = {name: percentile(score) for name, score in scores.items()}
    ranks = {}; lists = {}; metrics = []; controls = []
    base_order = order(baseline, ids)
    for name, score in scores.items():
        ranked = order(score, ids)
        ranks[name] = np.full(len(ids), np.nan); ranks[name][ranked] = np.arange(1, len(ranked) + 1)
        rho, paired = correlation(baseline, score)
        family, weights = vectors.get(name, ("proxy_sensitivity", default))
        for k in KS:
            selected = set(ranked[:k]); lists[name, k] = selected
            base_selected = set(base_order[:k]); overlap = len(selected & base_selected)
            union = len(selected | base_selected)
            boundary = score[ranked[min(k, len(ranked)) - 1]] if len(ranked) else np.nan
            boundary_ties = int(np.sum(score == boundary)) if np.isfinite(boundary) else 0
            for group, idx in indices.items():
                finite_pct = pct[name][idx][np.isfinite(pct[name][idx])]
                row = {"scheme": name, "family": family, "control_group": group, "top_k": k,
                       "ranked_genes": len(ranked), "paired_ranked_genes": paired,
                       "whole_universe_spearman": rho, "top_k_overlap": overlap,
                       "top_k_jaccard": overlap / union if union else 1,
                       "boundary_score": boundary, "boundary_tie_population": boundary_ties,
                       "controls_expected": len(GROUPS[group]), "controls_scored": len(finite_pct),
                       "control_median_percentile": np.median(finite_pct) if len(finite_pct) else np.nan,
                       "controls_top_quartile": int(np.sum(pct[name][idx] >= .75)),
                       "controls_top_10pct": int(np.sum(pct[name][idx] >= .90)),
                       "controls_top_k": len(set(idx) & selected)}
                row.update({"control_coverage_fraction": len(finite_pct) / len(GROUPS[group]),
                            "control_top_quartile_fraction_expected": row["controls_top_quartile"] / len(GROUPS[group]),
                            "control_top_10pct_recall_expected": row["controls_top_10pct"] / len(GROUPS[group]),
                            "control_top_k_recall_expected": row["controls_top_k"] / len(GROUPS[group])})
                row.update({f"weight_{layer}": weights[j] for j, layer in enumerate(LAYERS)})
                metrics.append(row)
        for group, idx in indices.items():
            for i in idx:
                controls.append({"scheme": name, "control_group": group, "gene_id": ids[i],
                                 "gene_symbol": symbols[i], "score": score[i], "rank": ranks[name][i],
                                 "percentile": pct[name][i], "original_observed_layers": counts[i],
                                 "active_weight_observed_layers": int(np.sum(np.isfinite(values[i]) & (weights > 0))) if name != "no_cerebellum" else int(np.isfinite(proxy_values[i]).sum())})
    write_table(out / "baseline_comparison.tsv", metrics)
    write_table(out / "control_rankings.tsv", controls)

    traces = []
    for group in ("usher", "syscilia"):
        for i in indices[group]:
            checks = {"score_pass": bool(baseline[i] >= .70), "evidence_count_pass": bool(counts[i] >= 3), "gate_pass": bool(gate[i])}
            traces.append({"control_group": group, "gene_id": ids[i], "gene_symbol": symbols[i],
                           "composite_score": baseline[i], "rank": ranks["default"][i],
                           "percentile": pct["default"][i], "observed_layers": counts[i],
                           **checks, "direct_localization_route": bool(direct[i]),
                           "animal_model_score": animal[i], "animal_q75_route": bool(animal_gate[i]),
                           "animal_q75_threshold": q75, "priority_tier": tier[i],
                           "failed_conditions": ";".join(k for k, v in checks.items() if not v) or "none"})
    write_table(out / "control_tier_trace.tsv", traces)

    thresholds = []
    gates = {"production_or": gate, "direct_only": direct, "animal_q75_only": animal_gate, "none": np.ones(len(ids), bool)}
    for threshold, minimum, (gate_name, gate_mask) in itertools.product((.60, .65, .70, .75, .80), (3, 4, 5, 6), gates.items()):
        high = (baseline >= threshold) & (counts >= minimum) & gate_mask
        row = {"score_threshold": threshold, "minimum_layers": minimum, "gate": gate_name,
               "animal_q75_threshold": q75, "shortlist_size": int(high.sum())}
        row.update({f"{group}_retained": int(high[idx].sum()) for group, idx in indices.items()})
        thresholds.append(row)
    write_table(out / "threshold_sensitivity.tsv", thresholds)

    membership = []
    families = {"modest_weights": [n for n, (f, _) in vectors.items() if f == "modest_weights"],
                "leave_one_out": [n for n, (f, _) in vectors.items() if f == "leave_one_out"]}
    eligible = set(np.flatnonzero(tier == "HIGH")) | set(np.concatenate(list(indices.values())))
    for selected in lists.values():
        eligible |= selected
    for i in sorted(eligible, key=lambda i: (np.nan_to_num(ranks["default"][i], nan=np.inf), ids[i])):
        row = {"gene_id": ids[i], "gene_symbol": symbols[i], "default_rank": ranks["default"][i], "production_tier": tier[i]}
        for k in KS:
            row[f"default_top_{k}"] = i in lists["default", k]
            for family, names in families.items():
                count = sum(i in lists[n, k] for n in names)
                row[f"{family}_top_{k}_count"] = count
                row[f"{family}_top_{k}_denominator"] = len(names)
                row[f"{family}_top_{k}_frequency"] = count / len(names)
        membership.append(row)
    write_table(out / "candidate_membership_stability.tsv", membership)

    completeness = []
    for n in range(7):
        selected = counts == n; observed = baseline[selected & np.isfinite(baseline)]
        quantiles = np.quantile(observed, [.25, .5, .75]) if len(observed) else [np.nan] * 3
        completeness.append({"observed_layers": n, "population": int(selected.sum()), "non_null_scores": len(observed),
                             "score_q25": quantiles[0], "score_median": quantiles[1], "score_q75": quantiles[2],
                             "raw_score_ge_070": int(np.sum(selected & (baseline >= .70))), "production_high": int(np.sum(selected & (tier == "HIGH")))})
    write_table(out / "evidence_completeness.tsv", completeness)
    correlations = []
    for j, left in enumerate(LAYERS):
        for k, right in enumerate(LAYERS):
            rho, paired = correlation(values[:, j], values[:, k])
            obs_left = np.isfinite(values[:, j]).astype(float); obs_right = np.isfinite(values[:, k]).astype(float)
            obs_rho = np.corrcoef(obs_left, obs_right)[0, 1] if obs_left.std() and obs_right.std() else np.nan
            correlations.append({"left_layer": left, "right_layer": right, "spearman_observed": rho,
                                 "pairwise_observed_n": paired, "universe_n": len(ids),
                                 "left_observed_n": int(obs_left.sum()), "right_observed_n": int(obs_right.sum()),
                                 "observation_indicator_pearson": obs_rho})
    write_table(out / "layer_correlations.tsv", correlations)

    proxy_score = scores["no_cerebellum"]
    proxy_tier = tiers(proxy_score, np.isfinite(proxy_values).sum(axis=1), gate)
    target_cols = [col for col in ("hpa_retina_ntpm", "hpa_retina_protein_level", "gtex_retina_tpm", "cellxgene_photoreceptor_expr") if col in expression.columns]
    availability = {col: int(expression[col].is_not_null().sum()) for col in target_cols}
    has_retinal_target = expr_removed.select(pl.any_horizontal([pl.col(col).is_not_null() for col in target_cols])).to_series().to_numpy()
    expression_available_without_target = int(np.sum(~has_retinal_target & np.isfinite(expr_removed["expression_score_normalized"].to_numpy())))
    per_gene = []
    for i in range(len(ids)):
        share = default[1] * values[i, 1] / float(df["available_weight"][i]) / baseline[i] if np.isfinite(values[i, 1]) and baseline[i] > 0 else np.nan
        per_gene.append({"gene_id": ids[i], "gene_symbol": symbols[i], "observed_layers": counts[i],
                         "composite_score": baseline[i], "rank": ranks["default"][i], "percentile": pct["default"][i], "production_tier": tier[i],
                         "expression_score": values[i, 1], "expression_weighted_share": share,
                         "expression_loo_score": scores["loo_expression"][i], "expression_loo_percentile": pct["loo_expression"][i],
                         "expression_loo_percentile_change": pct["loo_expression"][i] - pct["default"][i],
                         "no_cerebellum_expression_score": proxy_values[i, 1], "no_cerebellum_score": proxy_score[i],
                         "no_cerebellum_rank": ranks["no_cerebellum"][i], "no_cerebellum_percentile": pct["no_cerebellum"][i],
                         "no_cerebellum_percentile_change": pct["no_cerebellum"][i] - pct["default"][i], "no_cerebellum_tier": proxy_tier[i]})
    write_table(out / "per_gene_diagnostics.tsv", per_gene)
    write_table(out / "usher_expression_diagnostics.tsv", [row for row in per_gene if row["gene_symbol"] in ESTABLISHED_USHER_GENES])

    plot_diagnostics(out, correlations, completeness, membership, per_gene)
    completeness_rho, completeness_n = correlation(baseline, counts.astype(float))
    paired_proxy = np.isfinite(proxy_score) & np.isfinite(baseline)
    result = {"universe_labels": len(ids), "ranked_baseline": int(np.isfinite(baseline).sum()),
              "animal_q75_threshold": q75, "schemes": len(scores),
              "modest_weight_configurations": len(families["modest_weights"]), "loo_configurations": len(families["leave_one_out"]),
              "production_tiers": {t: int(np.sum(tier == t)) for t in ("HIGH", "MEDIUM", "LOW", "EXCLUDED")},
              "high_observed_layer_counts": {str(n): int(np.sum((tier == "HIGH") & (counts == n))) for n in range(7)},
              "completeness_score_spearman": completeness_rho, "completeness_score_paired_n": completeness_n,
              "retinal_target_source_observed_n_in_20116_universe": availability,
              "proxy_removed_background_only_expression_score_n": expression_available_without_target,
              "proxy_removed_tiers": {t: int(np.sum(proxy_tier == t)) for t in ("HIGH", "MEDIUM", "LOW", "EXCLUDED")},
              "proxy_high_overlap": int(np.sum((tier == "HIGH") & (proxy_tier == "HIGH"))),
              "proxy_high_lost": int(np.sum((tier == "HIGH") & (proxy_tier != "HIGH"))),
              "proxy_high_gained": int(np.sum((tier != "HIGH") & (proxy_tier == "HIGH"))),
              "proxy_full_rank_spearman": correlation(baseline, proxy_score)[0],
              "proxy_median_absolute_percentile_change": float(np.median(np.abs(pct["no_cerebellum"][paired_proxy] - pct["default"][paired_proxy]))),
              "protected_input_sha256": before,
              "code_commit": subprocess.check_output(["rtk", "proxy", "git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "script_sha256": digest(__file__), "analysis_spec_sha256": digest(ROOT / "revision/major_revision_20261006/analysis_spec.md"),
              "software": {"python": sys.version, "duckdb": duckdb.__version__, "polars": pl.__version__,
                           **{package: version(package) for package in ("numpy", "scipy", "matplotlib")}},
              "execution_command": ["rtk", "proxy", sys.executable, *sys.argv],
              "execution_location": "local macOS", "database_access": "read-only", "mapping_policy": "fixed production retained Ensembl IDs"}
    after = {p: digest(ROOT / p) for p in before}
    if before != after:
        raise ValueError("Protected production inputs were modified")
    result["protected_inputs_unchanged"] = True
    result["output_sha256"] = {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()}
    (out / "manifest.json").write_text(json.dumps(clean(result), indent=2, allow_nan=False) + "\n")
    print(json.dumps(clean({k: v for k, v in result.items() if k not in ("protected_input_sha256", "output_sha256", "software")}), indent=2))


def plot_diagnostics(out, correlations, completeness, membership, per_gene):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matrix = np.array([row["spearman_observed"] for row in correlations]).reshape(6, 6)
    fig, axes = plt.subplots(2, 2, figsize=(13, 10), constrained_layout=True)
    ax = axes[0, 0]
    im = ax.imshow(matrix, vmin=-1, vmax=1, cmap="coolwarm")
    labels = ["Constraint", "Expression", "Annotation", "Localization", "Animal", "Literature"]
    ax.set_xticks(range(6), labels, rotation=45, ha="right"); ax.set_yticks(range(6), labels)
    for j in range(6):
        for k in range(6):
            ax.text(k, j, f"{matrix[j,k]:.2f}", ha="center", va="center", fontsize=9)
    ax.set_title("A. Pairwise observed-score Spearman")
    fig.colorbar(im, ax=ax, shrink=.75)
    ax = axes[0, 1]
    rows = [r for r in completeness if r["non_null_scores"]]
    med = np.array([r["score_median"] for r in rows])
    ax.errorbar([r["observed_layers"] for r in rows], med,
                yerr=[med - [r["score_q25"] for r in rows], [r["score_q75"] for r in rows] - med], fmt="o", capsize=5)
    ax.set(xlabel="Observed evidence layers", ylabel="Composite median and IQR", title="B. Score by evidence completeness", xticks=range(1, 7), xlim=(.4, 6.6), ylim=(-.025, .59))
    for r in rows:
        ax.annotate(f"n={r['population']:,}", (r["observed_layers"], r["score_q75"]), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8)
    ax = axes[1, 0]
    baseline_top = [r for r in membership if r["default_top_100"]]
    ax.hist([r["modest_weights_top_100_count"] for r in baseline_top], bins=np.arange(-.5, 26.5, 1), color="#356b8c")
    ax.set(xlabel="Top-100 appearances across 25 configurations", ylabel="Default top-100 genes", title="C. Top-list membership stability")
    ax = axes[1, 1]
    changes = [r["no_cerebellum_percentile_change"] * 100 for r in per_gene if np.isfinite(r["no_cerebellum_percentile_change"])]
    ax.hist(changes, bins=50, color="#437f69"); ax.axvline(0, color="black", linewidth=.8)
    ax.set(xlabel="Percentile-point change after proxy removal", ylabel="Genes", title="D. Cerebellum-proxy sensitivity")
    fig.savefig(out / "phase2_diagnostics.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()

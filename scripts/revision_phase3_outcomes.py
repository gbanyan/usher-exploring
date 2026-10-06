"""Evaluate the Git-frozen comparator roster against unchanged production scores."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys

import duckdb
import numpy as np
from revision_replay import protected_inputs

from revision_phase2 import (ROOT, GROUPS, LAYERS, digest, write_table, clean,
                             load_config, weighted_mean, percentile, order, production_gate, tiers)


def read_table(path):
    return list(csv.DictReader(path.open(), delimiter="\t"))


def concordance(control, comparator):
    if not np.isfinite(control) or not np.isfinite(comparator):
        return np.nan
    return float(control > comparator) + .5 * float(control == comparator)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster-dir", type=Path, default=ROOT / "revision/major_revision_20261006/phase3_roster")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "revision/major_revision_20261006/phase3_results")
    parser.add_argument("--database", type=Path, default=ROOT / "data/pipeline.duckdb")
    parser.add_argument("--frozen-roster-dir", type=Path, default=ROOT / "revision/major_revision_20261006/phase3_roster", help="Committed reference for replay of a byte-identical copied roster")
    args = parser.parse_args(); roster = args.roster_dir; out = args.output_dir
    if out.exists():
        raise FileExistsError("Use a new directory; preserve existing outcomes")
    manifest = json.loads((roster / "manifest.json").read_text())
    for name, value in manifest["output_sha256"].items():
        if digest(roster / name) != value:
            raise ValueError(f"Frozen roster changed: {name}")
    if digest(ROOT / "revision/major_revision_20261006/phase3_spec.md") != manifest["spec_sha256"]:
        raise ValueError("Specification changed after roster freeze")
    # Require these exact bytes to be in HEAD before reading outcomes.
    for path in (roster / "manifest.json", roster / "eligible_pool.tsv", roster / "matched_pairs.tsv"):
        reference = args.frozen_roster_dir / path.name
        committed = subprocess.check_output(["rtk", "proxy", "git", "show", f"HEAD:{reference.relative_to(ROOT)}"])
        if committed != path.read_bytes():
            raise ValueError("Roster has not been committed exactly")
    protected = protected_inputs(args.database)
    with duckdb.connect(str(args.database), read_only=True) as con:
        con.execute("DESCRIBE scored_genes").fetchall()
        df = con.execute("SELECT * FROM scored_genes ORDER BY gene_id").pl()
    ids = np.array(df["gene_id"].to_list()); symbols = np.array(df["gene_symbol"].to_list())
    idx = {gid: i for i, gid in enumerate(ids)}
    values = df.select([f"{layer}_score" for layer in LAYERS]).to_numpy()
    counts = np.isfinite(values).sum(axis=1)
    config = load_config(ROOT / "config/default.yaml").scoring.model_dump()
    default = np.array([config[k] for k in LAYERS])
    baseline = df["composite_score"].to_numpy()
    if not np.allclose(weighted_mean(values, default), baseline, atol=1e-12, rtol=0, equal_nan=True):
        raise ValueError("Production scores do not reproduce")
    scores = {"default": baseline, "equal": weighted_mean(values, np.ones(6) / 6)}
    scores.update({f"single_{layer}": values[:, j] for j, layer in enumerate(LAYERS)})
    direct, animal, q75 = production_gate(df); gate = direct | animal
    tier = tiers(baseline, counts, gate)
    pairs = read_table(roster / "matched_pairs.tsv"); pool = read_table(roster / "eligible_pool.tsv")
    sets = {"eligible_unrelated": np.array([idx[r["gene_id"]] for r in pool])}
    for group in ("usher", "syscilia"):
        sets[group] = np.flatnonzero(np.isin(symbols, list(GROUPS[group])))
        sets[f"matched_unrelated_{group}"] = np.array([idx[r["comparator_id"]] for r in pairs if r["control_group"] == group])
    sets["housekeeping"] = np.flatnonzero(np.isin(symbols, list(GROUPS["housekeeping"])))
    pct = {name: percentile(score) for name, score in scores.items()}
    metrics = []
    for name, score in scores.items():
        ranked = order(score, ids)
        for group, ii in sets.items():
            finite = score[ii][np.isfinite(score[ii])]; p = pct[name][ii][np.isfinite(pct[name][ii])]
            qs = np.quantile(finite, [.25, .5, .75]) if len(finite) else [np.nan] * 3
            pq = np.quantile(p, [.25, .5, .75]) if len(p) else [np.nan] * 3
            row = {"scheme": name, "group": group, "genes_expected": len(ii), "genes_ranked": len(finite),
                   "ranking_universe_n": len(ranked), "score_q25": qs[0], "score_median": qs[1], "score_q75": qs[2],
                   "percentile_q25": pq[0], "percentile_median": pq[1], "percentile_q75": pq[2],
                   "top_quartile": int(np.sum(p >= .75)), "top_10pct": int(np.sum(p >= .90)),
                   **{f"top_{k}": len(set(ii) & set(ranked[:k])) for k in (25, 50, 100)},
                   "raw_score_ge_070": int(np.sum(score[ii] >= .70))}
            row.update({"production_score_and_count_pass": int(np.sum((baseline[ii] >= .70) & (counts[ii] >= 3))) if name == "default" else None,
                        "production_gate_pass": int(np.sum(gate[ii])) if name == "default" else None,
                        **{f"production_{t.lower()}": int(np.sum(tier[ii] == t)) if name == "default" else None for t in ("HIGH", "MEDIUM", "LOW", "EXCLUDED")}})
            metrics.append(row)
    pair_outcomes = []
    for row in pairs:
        a, b = idx[row["control_id"]], idx[row["comparator_id"]]
        pair_outcomes.append({**row, "control_score": baseline[a], "comparator_score": baseline[b],
            "control_percentile": pct["default"][a], "comparator_percentile": pct["default"][b],
            "percentile_difference": pct["default"][a] - pct["default"][b],
            "score_concordance": concordance(baseline[a], baseline[b]),
            "control_tier": tier[a], "comparator_tier": tier[b]})
    concordances = []
    for group in ("usher", "syscilia"):
        pp = [r for r in pair_outcomes if r["control_group"] == group]
        targets = sorted({r["control_id"] for r in pp})
        means = [np.nanmean([r["score_concordance"] for r in pp if r["control_id"] == gid]) for gid in targets]
        shifts = [np.nanmean([r["percentile_difference"] for r in pp if r["control_id"] == gid]) for gid in targets]
        concordances.append({"control_group": group, "controls_expected": len(sets[group]),
            "controls_matched": len(targets), "matched_pairs": len(pp),
            "pairs_ranked": sum(np.isfinite(r["score_concordance"]) for r in pp),
            "mean_within_control_score_concordance": np.nanmean(means),
            "mean_within_control_percentile_difference": np.nanmean(shifts),
            "median_within_control_percentile_difference": np.nanmedian(shifts)})
    pair_group_by_id = {r["comparator_id"]: r["control_group"] for r in pairs}
    gene_rows = []
    for row in pool:
        i = idx[row["gene_id"]]
        gene_rows.append({**row, "matched_to_group": pair_group_by_id.get(row["gene_id"], ""),
            "composite_score": baseline[i], "percentile": pct["default"][i], "observed_layers": counts[i],
            "direct_localization_route": bool(direct[i]), "animal_q75_route": bool(animal[i]),
            "priority_tier": tier[i], **{f"{layer}_score": values[i, j] for j, layer in enumerate(LAYERS)}})
    out.mkdir(parents=True)
    for name, rows in (("comparator_summary.tsv", metrics), ("matched_pair_outcomes.tsv", pair_outcomes),
                       ("matched_concordance.tsv", concordances), ("eligible_gene_outcomes.tsv", gene_rows)):
        write_table(out / name, rows)
    plot(out, sets, pct, baseline, counts, gate)
    if any(digest(ROOT / path) != value for path, value in protected.items()):
        raise ValueError("Protected baseline changed during outcome analysis")
    result = {"roster_manifest_sha256": digest(roster / "manifest.json"), "spec_sha256": manifest["spec_sha256"],
        "script_sha256": digest(__file__), "roster_commit": subprocess.check_output(["rtk", "proxy", "git", "rev-parse", "HEAD"], text=True).strip(),
        "animal_q75_threshold": q75, "protected_input_sha256": protected, "protected_inputs_unchanged": True,
        "software": manifest["software"], "database_access": "read-only", "execution_location": "local macOS",
        "execution_command": ["rtk", "proxy", sys.executable, *sys.argv],
        "output_sha256": {p.name: digest(p) for p in sorted(out.iterdir())}}
    (out / "manifest.json").write_text(json.dumps(clean(result), indent=2, allow_nan=False) + "\n")
    print(json.dumps(clean([r for r in metrics if r["scheme"] == "default"]), indent=2))
    print(json.dumps(clean(concordances), indent=2))


def plot(out, sets, pct, baseline, counts, gate):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = ["usher", "matched_unrelated_usher", "syscilia", "matched_unrelated_syscilia", "eligible_unrelated"]
    labels = ["Usher controls", "Matched to Usher", "SYSCILIA controls", "Matched to SYSCILIA", "Full comparator pool"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for name, label, color in zip(names, labels, ("#155e83", "#87adc2", "#2a754f", "#8ec0a6", "#817b78")):
        ii = sets[name]; values = pct["default"][ii]; values = np.sort(values[np.isfinite(values)]) * 100
        axes[0].step(values, np.arange(1, len(values) + 1) / len(values), where="post", label=f"{label} (n={len(ii)})", color=color)
    axes[0].set(xlabel="Genome-wide composite percentile", ylabel="Cumulative fraction", title="A. Frozen comparator ranking", xlim=(0, 100), ylim=(0, 1.02))
    axes[0].legend(fontsize=8, loc="upper left")
    x = np.arange(len(names)); width = .24
    for j, (label, mask, color) in enumerate((
        ("Score ≥0.70", baseline >= .70, "#99a7b2"),
        ("+ ≥3 observed layers", (baseline >= .70) & (counts >= 3), "#56819f"),
        ("+ calibrated gate (HIGH)", (baseline >= .70) & (counts >= 3) & gate, "#244d6b"))):
        fractions = [100 * mask[sets[name]].mean() for name in names]
        bars = axes[1].bar(x + (j - 1) * width, fractions, width, label=label, color=color)
        for bar, name in zip(bars, names):
            count = int(mask[sets[name]].sum())
            axes[1].annotate(str(count), (bar.get_x() + bar.get_width() / 2, bar.get_height()), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8)
    axes[1].set(xticks=x, xticklabels=[f"{label}\n{len(sets[name])}" for label, name in zip(("Usher", "Matched", "SYSCILIA", "Matched", "Pool"), names)],
                ylabel="Genes meeting criteria (%)", title="B. Descriptive filtering, unchanged criteria", ylim=(0, 30))
    axes[1].legend(fontsize=8, loc="upper right")
    fig.savefig(out / "phase3_specificity.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()

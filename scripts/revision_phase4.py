"""Post-outcome fixed-pair and historical-coverage diagnostics requested by review."""
import argparse
import csv
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import polars as pl

from revision_phase2 import ROOT, LAYERS, digest, clean, write_table, weighted_mean

BASE = ROOT / "revision/major_revision_20261006"
WEIGHTS = np.array([.20, .20, .15, .15, .15, .15])


def read(path):
    return list(csv.DictReader(Path(path).open(), delimiter="\t"))


def pair_scores(a, b, weights, common=False):
    if common:
        shared = np.isfinite(a) & np.isfinite(b)
        a, b = np.where(shared, a, np.nan), np.where(shared, b, np.nan)
    return weighted_mean(np.vstack([a, b]), weights)


def concordance(a, b):
    return float(a > b) + .5 * float(a == b) if np.isfinite(a) and np.isfinite(b) else np.nan


def historical_panel(cache, output):
    """Freeze the accepted ordinal HPA panel for replay without the whole archive."""
    source = cache / "hpa_v20_normal_tissue.zip"
    expected = next(r for r in json.loads((BASE / "temporal_extension/download_manifest.json").read_text()) if r["name"] == source.name)
    if digest(source) != expected["sha256"]:
        raise ValueError("Historical HPA input changed")
    with zipfile.ZipFile(source) as z:
        df = pl.read_csv(io.BytesIO(z.read("normal_tissue.tsv")), separator="\t")
    accepted = df.filter(pl.col("Reliability").is_in(["Approved", "Enhanced", "Supported"]) & pl.col("Tissue").is_in(["retina", "cerebellum", "testis", "fallopian tube"]))
    ordinal = {"Not detected": 0, "Low": 1, "Medium": 2, "High": 3}
    accepted = accepted.with_columns(pl.col("Level").replace_strict(ordinal, default=None, return_dtype=pl.Int8).alias("protein_level"))
    panel = accepted.group_by(["Gene", "Tissue"]).agg(pl.col("protein_level").max(), pl.len().alias("accepted_raw_rows"), pl.col("protein_level").is_null().sum().alias("unrecognized_level_rows")).sort(["Gene", "Tissue"])
    panel.write_csv(output, separator="\t", null_value="\\N")
    return {"sha256": digest(output), "source_sha256": expected["sha256"], "source_url": expected["url"], "measurement": "ordinal HPA protein category; accepted reliability; max across cell types"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=BASE / "phase4_results")
    parser.add_argument("--bundle-dir", type=Path, default=BASE / "replay_inputs")
    parser.add_argument("--historical-panel", type=Path, default=BASE / "replay_inputs/historical_hpa_panel.tsv")
    parser.add_argument("--export-historical-panel-from", type=Path, help="Only for first freeze; requires the original hashed HPA ZIP")
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    historical_manifest = json.loads((BASE / "temporal_extension/results/manifest.json").read_text())
    for name in ("historical_components.tsv", "historical_rankings.tsv"):
        if digest(BASE / "temporal_extension/results" / name) != historical_manifest["output_sha256"][name]:
            raise ValueError(f"Historical baseline changed: {name}")
    source_manifest = json.loads((args.bundle_dir / "manifest.json").read_text())
    score_file = args.bundle_dir / source_manifest["tables"]["scored_genes"]["file"]
    if digest(score_file) != source_manifest["tables"]["scored_genes"]["sha256"]:
        raise ValueError("Frozen score input changed")
    df = pl.read_csv(score_file, separator="\t", null_values="\\N", infer_schema_length=None)
    values = df.select([f"{layer}_score" for layer in LAYERS]).to_numpy()
    idx = {gid:i for i,gid in enumerate(df["gene_id"])}
    roster_manifest = json.loads((BASE / "phase3_roster/manifest.json").read_text())
    pair_file = BASE / "phase3_roster/matched_pairs.tsv"
    assert digest(pair_file) == roster_manifest["output_sha256"][pair_file.name]
    pairs = read(pair_file)
    if len(pairs) != 111:
        raise ValueError("Frozen pair population changed")
    schemes = {"default": (WEIGHTS, False), "common_observed_layers": (WEIGHTS, True)}
    for j, layer in enumerate(LAYERS):
        w = WEIGHTS.copy(); w[j] = 0
        schemes[f"loo_{layer}"] = (w, False)
    w = WEIGHTS.copy(); w[4:] = 0
    schemes["omit_animal_and_literature"] = (w, False)
    pair_rows, summaries, balance = [], [], []
    for name, (w, common) in schemes.items():
        for pair in pairs:
            a, b = values[idx[pair["control_id"]]], values[idx[pair["comparator_id"]]]
            sa, sb = pair_scores(a, b, w, common)
            pair_rows.append({**pair, "scheme": name, "control_score": sa, "comparator_score": sb, "concordance": concordance(sa,sb), "common_layers": int((np.isfinite(a) & np.isfinite(b)).sum())})
        for group in ("usher", "syscilia"):
            rows = [r for r in pair_rows if r["scheme"] == name and r["control_group"] == group]
            finite = [r for r in rows if np.isfinite(r["concordance"])]
            per_control = [np.nanmean([r["concordance"] for r in rows if r["control_id"]==gid]) for gid in sorted({r["control_id"] for r in rows})]
            summaries.append({"scheme":name,"control_group":group,"pairs_expected":len(rows),"pairs_ranked":len(finite),"control_wins":sum(r["concordance"]==1 for r in finite),"ties":sum(r["concordance"]==.5 for r in finite),"pair_mean_concordance":np.mean([r["concordance"] for r in finite]),"control_mean_concordance":np.nanmean(per_control)})
    for group in ("usher", "syscilia"):
        pp = [r for r in pairs if r["control_group"] == group]
        for role, field in (("control","control_id"),("matched_comparator","comparator_id")):
            indices = [idx[gid] for gid in sorted({r[field] for r in pp})]
            v = values[indices]; n = np.isfinite(v).sum(axis=1)
            balance.append({"control_group":group,"role":role,"genes":len(indices), **{f"layers_{k}":int((n==k).sum()) for k in range(7)}, **{f"{layer}_observed":int(np.isfinite(v[:,j]).sum()) for j,layer in enumerate(LAYERS)}})
    panel_meta_file = args.historical_panel.with_suffix(".manifest.json")
    if args.export_historical_panel_from:
        if args.historical_panel.exists() or panel_meta_file.exists():
            raise FileExistsError("Preserve frozen historical panel")
        metadata = historical_panel(args.export_historical_panel_from, args.historical_panel)
        panel_meta_file.write_text(json.dumps(metadata,indent=2)+'\n')
    metadata = json.loads(panel_meta_file.read_text())
    if digest(args.historical_panel) != metadata["sha256"]:
        raise ValueError("Frozen historical panel changed")
    panel = pl.read_csv(args.historical_panel,separator="\t",null_values="\\N")
    comp = {r["gene_id"]:r for r in read(BASE / "temporal_extension/results/historical_components.tsv")}
    historical = [r for r in read(BASE / "temporal_extension/results/historical_rankings.tsv") if r["scheme"]=="historical_default_available" and r["rank_position"]]
    historical.sort(key=lambda r:int(r["rank_position"]))
    top = []
    for k in (25,50,100):
        selected = [comp[r["gene_id"]] for r in historical[:k]]
        top.append({"top_k":k,"genes":len(selected), **{f"layers_{n}":sum(int(r["evidence_count"])==n for r in selected) for n in range(1,5)}, **{f"{layer}_missing":sum(not r[f"{layer}_score"] for r in selected) for layer in LAYERS[:4]}})
    coverage = []
    for tissue in ("retina","cerebellum","testis","fallopian tube"):
        subset = panel.filter((pl.col("Tissue")==tissue) & pl.col("protein_level").is_not_null())
        eligible = subset.filter(pl.col("Gene").is_in(list(comp)))
        coverage.append({"tissue":tissue,"source_genes_observed":subset.height,"historical_genes_observed":eligible.height,"historical_positive":eligible.filter(pl.col("protein_level")>0).height,"historical_observed_zero":eligible.filter(pl.col("protein_level")==0).height})
    provenance = []
    for gid,row in comp.items():
        if row["gene_symbol"] not in ("CEP162","CFAP20","LRRC45"):
            continue
        record = {"gene_id":gid,"gene_symbol":row["gene_symbol"],"expression_score":row["expression_score"]}
        for tissue in ("retina","cerebellum","testis","fallopian tube"):
            subset = panel.filter((pl.col("Gene")==gid) & (pl.col("Tissue")==tissue))
            record[tissue.replace(' ','_')+"_protein_level"] = subset["protein_level"][0] if subset.height else None
        provenance.append(record)
    args.output_dir.mkdir(parents=True)
    for name, rows in (("fixed_pair_sensitivities.tsv",pair_rows),("fixed_pair_summary.tsv",summaries),("matching_completeness_balance.tsv",balance),("historical_topk_completeness.tsv",top),("historical_tissue_coverage.tsv",coverage),("historical_case_expression_sources.tsv",provenance)):
        write_table(args.output_dir/name,rows)
    manifest={"analysis_status":"post-outcome review-prompted sensitivity; no retuning/rematching", "spec_sha256":digest(BASE/'phase4_spec.md'),"script_sha256":digest(__file__),"score_input_sha256":digest(score_file),"frozen_pairs_sha256":digest(pair_file),"historical_panel_sha256":digest(args.historical_panel),"historical_input_sha256":{name:historical_manifest["output_sha256"][name] for name in ("historical_components.tsv", "historical_rankings.tsv")},"output_sha256":{p.name:digest(p) for p in args.output_dir.glob('*.tsv')}}
    (args.output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(clean(summaries),indent=2))


if __name__ == "__main__":
    main()

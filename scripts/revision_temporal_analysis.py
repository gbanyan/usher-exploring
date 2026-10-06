"""Restricted archive-only reconstruction; never reads production gene scores."""
from collections import Counter, defaultdict
import argparse
import csv
import gzip
import io
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from revision_phase2 import digest, weighted_mean, percentile, order, write_table, clean
from revision_replay import protected_inputs
from usher_pipeline.evidence.annotation.transform import normalize_annotation_score
from usher_pipeline.evidence.expression.models import HPA_LEVEL_ORDINAL, HPA_TISSUE_KEYS, RESTRICTED_TAU_COLUMN
from usher_pipeline.evidence.expression.transform import compute_expression_score
from usher_pipeline.evidence.localization.transform import classify_evidence_type, score_localization
from usher_pipeline.scoring.known_genes import ESTABLISHED_USHER_GENES

BASE = ROOT / "revision/major_revision_20261006/temporal_extension"
CACHE = ROOT / "data/cache/temporal-extension-20261006/raw"
PROTOCOL_SHA256 = "2bd02b4b467c82e34f1dc554085c81ffd5e91698b7eb3c6ebcd4cfe8e92e166a"
CASES = {"CEP162": "later_human_retinal_association", "CFAP20": "later_human_retinal_candidate", "LRRC45": "later_putative_human_ciliopathy"}
LAYERS = ["gnomad", "expression", "annotation", "localization"]
WEIGHTS = np.array([.20, .20, .15, .15])


def historical_genes(rows):
    eligible = [r for r in rows if r["status"] == "Approved" and r["locus_group"] == "protein-coding gene" and r["ensembl_gene_id"]]
    counts = Counter(r["ensembl_gene_id"] for r in eligible)
    return sorted([r for r in eligible if counts[r["ensembl_gene_id"]] == 1], key=lambda r: r["ensembl_gene_id"]), sum(v for v in counts.values() if v > 1)


def go_counts(lines, genes):
    accessions, symbols = defaultdict(set), defaultdict(set)
    for g in genes:
        gid = g["ensembl_gene_id"]
        symbols[g["symbol"]].add(gid)
        for accession in g["uniprot_ids"].split("|"):
            if accession:
                accessions[accession].add(gid)
    terms = defaultdict(set)
    audit = Counter()
    for line in lines:
        if line.startswith("!") or not line.strip():
            continue
        fields = line.rstrip("\n").split("\t")
        if len(fields) < 17:
            raise ValueError("Malformed GAF record")
        audit["gaf_rows"] += 1
        mapped = accessions.get(fields[1], set())
        if len(mapped) > 1:
            audit["ambiguous_accession_rows"] += 1
            continue
        if not mapped:
            mapped = symbols.get(fields[2], set())
            audit["symbol_fallback_rows"] += bool(mapped)
        if len(mapped) != 1:
            audit["unmapped_rows"] += 1
            continue
        gid = next(iter(mapped))
        terms[gid]  # observed GAF gene, even if its only records are NOT
        if "NOT" in fields[3].split("|"):
            audit["not_rows_excluded"] += 1
            continue
        terms[gid].add(fields[4])
        audit["positive_mapped_rows"] += 1
    return {gid: len(values) for gid, values in terms.items()}, dict(audit)


def zip_table(name, cache=CACHE):
    with zipfile.ZipFile(cache / name) as archive:
        members = archive.infolist()
        if len(members) != 1:
            raise ValueError("Unexpected HPA ZIP members")
        member = members[0]
        if member.date_time[:3] > (2020, 12, 31):
            raise ValueError("Post-cutoff HPA ZIP member")
        return pl.read_csv(io.BytesIO(archive.read(member)), separator="\t"), {"member": member.filename, "internal_date": member.date_time, "uncompressed_bytes": member.file_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=CACHE)
    parser.add_argument("--source-manifest", type=Path, default=BASE / "download_manifest.json")
    parser.add_argument("--output-dir", type=Path, default=BASE / "results")
    parser.add_argument("--baseline-database", type=Path, default=ROOT / "data/pipeline.duckdb")
    args = parser.parse_args()
    cache = args.cache_dir
    if digest(BASE / "protocol.md") != PROTOCOL_SHA256:
        raise ValueError("Frozen protocol changed")
    out = args.output_dir
    if out.exists():
        raise FileExistsError("Preserve prior outcomes")
    protected = protected_inputs(args.baseline_database)
    source_manifest = json.loads(args.source_manifest.read_text())
    required = ["hgnc_20201001.tsv", "go_20201208.gaf.gz", "gnomad_v211.bgz", "hpa_v20_subcellular.zip", "hpa_v20_normal_tissue.zip"]
    for name in required:
        item = next(r for r in source_manifest if r["name"] == name)
        if item.get("error") or digest(cache / name) != item["sha256"]:
            raise ValueError(f"Missing or altered archive: {name}")
    with (cache / required[0]).open() as handle:
        genes, excluded = historical_genes(list(csv.DictReader(handle, delimiter="\t")))
    ids = np.array([g["ensembl_gene_id"] for g in genes])
    symbols = np.array([g["symbol"] for g in genes])
    frame = pl.DataFrame({"gene_id": ids, "gene_symbol": symbols})
    with gzip.open(cache / "gnomad_v211.bgz", "rt") as handle:
        constraint = list(csv.DictReader(handle, delimiter="\t"))
    if len({r["gene_id"] for r in constraint}) != len(constraint):
        raise ValueError("Duplicate constraint genes")
    loeufs = {r["gene_id"]: float(r["oe_lof_upper"]) for r in constraint if r["oe_lof_upper"] not in ("", "NA", "NaN", "nan")}
    loeuf = np.array([loeufs.get(gid, np.nan) for gid in ids])
    measured = np.isfinite(loeuf)
    constraint_score = np.full(len(ids), np.nan)
    constraint_score[measured] = (np.nanmax(loeuf) - loeuf[measured]) / (np.nanmax(loeuf) - np.nanmin(loeuf))
    with gzip.open(cache / "go_20201208.gaf.gz", "rt") as handle:
        counts, go_audit = go_counts(handle, genes)
    annotation = frame.with_columns([
        pl.Series("go_term_count", [counts.get(gid) for gid in ids], dtype=pl.Int64),
        pl.lit(None, dtype=pl.Float64).alias("uniprot_annotation_score"),
        pl.lit(None, dtype=pl.Boolean).alias("has_pathway_membership"),
    ])
    annotation = normalize_annotation_score(annotation)
    hpa, hpa_date = zip_table("hpa_v20_normal_tissue.zip", cache)
    tissue_keys = {key.replace("_", " "): key for key in HPA_TISSUE_KEYS}
    hpa = hpa.filter(pl.col("Tissue").is_in(list(tissue_keys)) & pl.col("Reliability").is_in(["Approved", "Enhanced", "Supported"]))
    unknown_levels = hpa.filter(~pl.col("Level").is_in(list(HPA_LEVEL_ORDINAL))).group_by("Level").len().to_dicts()
    # The production parser maps unrecognized ordinal labels to NULL.
    hpa = hpa.with_columns(pl.col("Level").replace_strict(HPA_LEVEL_ORDINAL, default=None, return_dtype=pl.Int8).alias("level"))
    expression = frame
    for tissue, key in tissue_keys.items():
        part = hpa.filter(pl.col("Tissue") == tissue).group_by("Gene").agg(pl.col("level").max()).rename({"Gene": "gene_id", "level": f"hpa_{key}_protein_level"})
        expression = expression.join(part, on="gene_id", how="left")
    expression = expression.with_columns(pl.lit(None, dtype=pl.Float64).alias(RESTRICTED_TAU_COLUMN))
    expression = compute_expression_score(expression)
    hpa_local, local_date = zip_table("hpa_v20_subcellular.zip", cache)
    if hpa_local["Gene"].n_unique() != hpa_local.height:
        raise ValueError("Duplicate HPA localization genes")
    localization = frame.join(hpa_local.select([pl.col("Gene").alias("gene_id"), pl.col("Reliability").alias("hpa_reliability"), pl.col("Main location").alias("hpa_main_location")]), on="gene_id", how="left")
    localization = score_localization(classify_evidence_type(localization))
    for part in (annotation, expression, localization):
        if part["gene_id"].to_list() != list(ids):
            raise ValueError("Gene alignment changed")
    values = np.column_stack([constraint_score, expression["expression_score_normalized"].to_numpy(), annotation["annotation_score_normalized"].to_numpy(), localization["localization_score_normalized"].to_numpy()])
    vectors = {"historical_default_available": WEIGHTS, "historical_equal_available": np.ones(4)}
    for j, layer in enumerate(LAYERS):
        vector = np.zeros(4); vector[j] = 1
        vectors[f"historical_single_{layer}"] = vector
    rows, case_rows, coverage = [], [], []
    raw_components = [{"gene_id": gid, "gene_symbol": symbols[i], "loeuf_v211": loeuf[i], "go_positive_unique_count": counts.get(gid), **{f"{layer}_score": values[i,j] for j,layer in enumerate(LAYERS)}, "animal_model_score": None, "literature_score": None, "evidence_count": int(np.isfinite(values[i]).sum())} for i,gid in enumerate(ids)]
    for name, weights in vectors.items():
        scores = weighted_mean(values, weights)
        percentiles = percentile(scores)
        positions = {int(i): rank + 1 for rank,i in enumerate(order(scores, ids))}
        denominator = int(np.isfinite(scores).sum())
        for i, gid in enumerate(ids):
            row = {"scheme": name, "gene_id": gid, "gene_symbol": symbols[i], "score": scores[i], "percentile": percentiles[i] * 100, "rank_position": positions.get(i), "rank_denominator": denominator, "evidence_count": int((np.isfinite(values[i]) & (weights > 0)).sum()), **{f"top{k}": positions.get(i, denominator + 1) <= k for k in (25,50,100)}}
            rows.append(row)
            if symbols[i] in CASES or symbols[i] in ESTABLISHED_USHER_GENES:
                case_rows.append({**row, "role": CASES.get(symbols[i], "precutoff_known_usher_reference")})
    for j, layer in enumerate(LAYERS):
        observed = np.isfinite(values[:,j])
        coverage.append({"layer": layer, "population": len(ids), "observed": int(observed.sum()), "positive": int((observed & (values[:,j] > 0)).sum()), "observed_zero": int((observed & (values[:,j] == 0)).sum()), "missing": int((~observed).sum())})
    for path, expected in protected.items():
        if digest(ROOT / path) != expected:
            raise ValueError(f"Production changed during analysis: {path}")
    out.mkdir(parents=True)
    write_table(out / "historical_components.tsv", raw_components)
    write_table(out / "historical_rankings.tsv", rows)
    write_table(out / "case_rankings.tsv", case_rows)
    write_table(out / "source_coverage.tsv", coverage)
    manifest = {"protocol_sha256": PROTOCOL_SHA256, "protocol_commit": "377eae3", "script_sha256": digest(Path(__file__)), "population": len(ids), "hgnc_duplicate_identifier_rows_excluded": excluded, "go_mapping_audit": go_audit, "hpa_unknown_ordinal_labels_mapped_to_null": unknown_levels, "hpa_normal_tissue_archive": hpa_date, "hpa_subcellular_archive": local_date, "protected_production_unchanged": True, "full_production_temporal_validation": False, "source_manifest_sha256": digest(args.source_manifest), "output_sha256": {p.name:digest(p) for p in sorted(out.glob("*.tsv"))}}
    (out / "manifest.json").write_text(json.dumps(clean(manifest), indent=2) + "\n")
    print(json.dumps(clean(manifest), indent=2))


if __name__ == "__main__":
    main()

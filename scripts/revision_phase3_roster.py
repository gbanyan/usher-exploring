"""Freeze comparator selection using curation, phenotype and nuisance covariates only."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

import duckdb
import numpy as np
from scipy.optimize import linear_sum_assignment

from revision_phase2 import ROOT, GROUPS, digest, write_table

ROOTS = {"HP:0000365", "HP:0000478", "HP:0005938", "HP:0012261", "HP:0031602",
         "HP:0030853", "HP:0011620", "HP:0011615", "HP:0011538", "HP:0011539"}
PATTERN = re.compile(r"usher|hearing|deaf|retin|amaurosis|ciliopath|ciliary|cilium|joubert|bardet|meckel|nephronophthis|alstrom|senior.loken", re.I)
URLS = {
    "clingen.csv": "https://search.clinicalgenome.org/kb/gene-validity/download",
    "hgnc.tsv": "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt",
    **{name: f"https://github.com/obophenotype/human-phenotype-ontology/releases/download/v2026-09-01/{name}"
       for name in ("hp.obo", "genes_to_phenotype.txt")},
}


def ontology_exclusions(text, roots=ROOTS):
    children = defaultdict(set); aliases = {}; names = {}
    for block in text.split("[Term]")[1:]:
        block = block.split("[Typedef]")[0]
        ids = re.findall(r"^id: (HP:\d+)$", block, re.M)
        if not ids:
            continue
        term = ids[0]
        names[term] = re.search(r"^name: (.+)$", block, re.M).group(1)
        for alias in re.findall(r"^alt_id: (HP:\d+)$", block, re.M):
            aliases[alias] = term
        for parent in re.findall(r"^is_a: (HP:\d+)", block, re.M):
            children[parent].add(term)
    if not roots <= names.keys():
        raise ValueError("An exclusion root is absent from this ontology")
    excluded = set(roots); todo = list(roots)
    while todo:
        for child in children[todo.pop()] - excluded:
            excluded.add(child); todo.append(child)
    return excluded, aliases, names


def exact_mapping(record, retained, ensembl_counts, entrez_counts):
    ensembl, entrez = record.get("ensembl_gene_id", ""), record.get("entrez_id", "")
    reasons = []
    if record.get("status") != "Approved":
        reasons.append("hgnc_not_approved")
    if not re.fullmatch(r"ENSG\d+", ensembl) or ensembl_counts.get(ensembl, 0) != 1:
        reasons.append("missing_or_ambiguous_ensembl")
    elif ensembl not in retained:
        reasons.append("not_retained_production_id")
    if not entrez.isdigit() or entrez_counts.get(entrez, 0) != 1:
        reasons.append("missing_or_ambiguous_entrez")
    return ensembl, entrez, reasons


def match_covariates(targets, comparators, caliper=.75, ratio=3):
    """Maximize feasible cardinality then minimize distance; no replacement."""
    targets = np.asarray(targets, float); comparators = np.asarray(comparators, float)
    if not len(targets) or not len(comparators):
        return []
    delta = np.repeat(targets, ratio, axis=0)[:, None, :] - comparators[None, :, :]
    feasible = (np.abs(delta) <= caliper).all(axis=2)
    distance = (delta ** 2).sum(axis=2)
    n = len(delta)
    dummy = n * max(1.0, caliper ** 2 * targets.shape[1]) + 1
    costs = np.concatenate([np.where(feasible, distance, dummy * 2), np.full((n, n), dummy)], axis=1)
    rows, cols = linear_sum_assignment(costs)
    return [(int(row // ratio), int(col), float(distance[row, col]))
            for row, col in zip(rows, cols) if col < len(comparators) and feasible[row, col]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data/cache/phase3-sources-20261006")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "revision/major_revision_20261006/phase3_roster")
    parser.add_argument("--database", type=Path, default=ROOT / "data/pipeline.duckdb")
    args = parser.parse_args(); src = args.source_dir; out = args.output_dir
    if out.exists():
        raise FileExistsError("Preserve frozen rosters; use a new directory")
    phase2 = json.loads((ROOT / "revision/major_revision_20261006/results/manifest.json").read_text())
    from revision_replay import protected_inputs
    protected = protected_inputs(args.database)
    with duckdb.connect(str(args.database), read_only=True) as con:
        for table in ("scored_genes", "literature_evidence", "annotation_completeness"):
            con.execute(f"DESCRIBE {table}").fetchall()
        # Deliberately do not select any composite, layer score, tier or gate field.
        records = con.execute("""SELECT s.gene_id,s.gene_symbol,l.total_pubmed_count,a.go_term_count
            FROM scored_genes s LEFT JOIN literature_evidence l USING(gene_id)
            LEFT JOIN annotation_completeness a USING(gene_id) ORDER BY s.gene_id""").fetchall()
    retained = {r[0]: {"gene_id": r[0], "production_symbol": r[1], "total_pubmed_count": r[2], "go_term_count": r[3]} for r in records}
    if len(retained) != len(records) or len(retained) != 20081:
        raise ValueError("Unexpected retained mapping")
    hgnc = list(csv.DictReader((src / "hgnc.tsv").open(), delimiter="\t"))
    hgnc_by_id = {r["hgnc_id"]: r for r in hgnc}
    if len(hgnc_by_id) != len(hgnc):
        raise ValueError("Duplicate HGNC IDs")
    ens_counts = defaultdict(int); entrez_counts = defaultdict(int)
    for r in hgnc:
        ens_counts[r["ensembl_gene_id"]] += 1; entrez_counts[r["entrez_id"]] += 1
    excluded_hpo, aliases, names = ontology_exclusions((src / "hp.obo").read_text())
    phenotypes = defaultdict(set)
    for r in csv.DictReader((src / "genes_to_phenotype.txt").open(), delimiter="\t"):
        term = aliases.get(r["hpo_id"], r["hpo_id"])
        phenotypes[r["ncbi_gene_id"]].add(term)
    lines = (src / "clingen.csv").read_text().splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith('"GENE SYMBOL","GENE ID (HGNC)"'))
    assertions = defaultdict(list)
    for r in csv.DictReader(lines[header_index:]):
        if r["GENE ID (HGNC)"].startswith("HGNC:"):
            assertions[r["GENE ID (HGNC)"]].append(r)
    original = set().union(*[set(g) for g in GROUPS.values()])
    audit = []; pool = []
    for hid, items in sorted(assertions.items()):
        record = hgnc_by_id.get(hid, {})
        ens, entrez, reasons = exact_mapping(record, retained, ens_counts, entrez_counts)
        strengths = sorted({r["CLASSIFICATION"] for r in items})
        if not set(strengths) & {"Strong", "Definitive"}:
            reasons.append("no_strong_or_definitive_assertion")
        matches = sorted({r["DISEASE LABEL"] + " | " + r["GCEP"] for r in items
                          if PATTERN.search(r["DISEASE LABEL"] + " " + r["GCEP"])})
        if matches:
            reasons.append("sensory_ciliary_assertion_or_panel")
        terms = phenotypes.get(entrez, set()); excluded_terms = sorted(terms & excluded_hpo)
        if not terms:
            reasons.append("no_hpo_annotations")
        if excluded_terms:
            reasons.append("excluded_hpo_branch")
        if record.get("symbol") in original or retained.get(ens, {}).get("production_symbol") in original:
            reasons.append("original_control")
        row = {"hgnc_id": hid, "hgnc_symbol": record.get("symbol", ""), "gene_id": ens,
               "entrez_id": entrez, "eligible": not reasons, "exclusion_reasons": ";".join(reasons),
               "classifications": ";".join(strengths), "hpo_annotation_count": len(terms),
               "excluded_hpo_terms": ";".join(excluded_terms), "excluded_assertions": json.dumps(matches),
               "assertions": json.dumps([{k: r[k] for k in ("DISEASE LABEL", "DISEASE ID (MONDO)", "CLASSIFICATION", "CLASSIFICATION DATE", "ONLINE REPORT", "GCEP")} for r in items])}
        audit.append(row)
        if not reasons:
            pool.append({"hgnc_id": hid, "hgnc_symbol": record["symbol"], **retained[ens]})
    pool.sort(key=lambda r: r["gene_id"])
    if not pool:
        raise ValueError("No eligible pool; amend specification before outcomes")
    targets = [{"control_group": group, **r} for group in ("usher", "syscilia")
               for r in retained.values() if r["production_symbol"] in GROUPS[group]]
    if len(targets) != 37:
        raise ValueError("Positive controls not fully mapped")
    complete = lambda r: r["total_pubmed_count"] is not None and r["go_term_count"] is not None
    target_complete = [r for r in targets if complete(r)]; pool_complete = [r for r in pool if complete(r)]
    raw_features = lambda rows: np.array([[r["total_pubmed_count"], r["go_term_count"]] for r in rows], float)
    combined = np.log1p(raw_features(target_complete + pool_complete))
    sd = combined.std(axis=0)
    if np.any(sd <= 0):
        raise ValueError("Undefined matching scale")
    t = np.log1p(raw_features(target_complete)) / sd; p = np.log1p(raw_features(pool_complete)) / sd
    pairs = []
    for i, j, distance in match_covariates(t, p):
        target, comparator = target_complete[i], pool_complete[j]
        pairs.append({"control_group": target["control_group"], "control_id": target["gene_id"],
                      "control_symbol": target["production_symbol"], "comparator_id": comparator["gene_id"],
                      "comparator_symbol": comparator["hgnc_symbol"], "squared_distance": distance,
                      "log_pubmed_sd_difference": t[i, 0] - p[j, 0], "log_go_sd_difference": t[i, 1] - p[j, 1]})
    pairs.sort(key=lambda r: (r["control_group"], r["control_id"], r["comparator_id"]))
    if not pairs:
        raise ValueError("No feasible matches; amend specification before outcomes")
    match_counts = defaultdict(int)
    for row in pairs:
        match_counts[row["control_id"]] += 1
    for row in targets:
        row["complete_covariates"] = complete(row); row["matched_comparators"] = match_counts[row["gene_id"]]
    diagnostics = []
    for group in ("usher", "syscilia"):
        ts = [r for r in target_complete if r["control_group"] == group]
        selected_pairs = [r for r in pairs if r["control_group"] == group]
        matched_ids = {r["control_id"] for r in selected_pairs}
        for k, feature in enumerate(("total_pubmed_count", "go_term_count")):
            mean_target = np.mean(np.log1p([r[feature] for r in ts]))
            mean_pool = np.mean(np.log1p([r[feature] for r in pool_complete]))
            matched_ts = [r for r in ts if r["gene_id"] in matched_ids]
            comparator_by_id = {r["gene_id"]: r for r in pool_complete}
            per_target_means = [np.mean([np.log1p(comparator_by_id[r["comparator_id"]][feature])
                                        for r in selected_pairs if r["control_id"] == target["gene_id"]]) for target in matched_ts]
            diagnostics.append({"control_group": group, "feature": feature, "scaling_population_sd_log1p": sd[k],
                "complete_controls": len(ts), "matched_controls": len(matched_ts), "matched_comparators": len(selected_pairs),
                "before_standardized_mean_difference": (mean_target - mean_pool) / sd[k],
                "after_standardized_mean_difference": (np.mean(np.log1p([r[feature] for r in matched_ts])) - np.mean(per_target_means)) / sd[k] if matched_ts else None})
    out.mkdir(parents=True)
    for name, rows in (("eligibility_audit.tsv", audit), ("eligible_pool.tsv", pool), ("matched_pairs.tsv", pairs),
                       ("control_matching_coverage.tsv", targets), ("matching_diagnostics.tsv", diagnostics)):
        write_table(out / name, rows)
    manifest = {"spec_sha256": digest(ROOT / "revision/major_revision_20261006/phase3_spec.md"),
        "script_sha256": digest(__file__), "baseline_commit": subprocess.check_output(["rtk", "proxy", "git", "rev-parse", "HEAD"], text=True).strip(),
        "sources": {name: {"url": url, "sha256": digest(src / name), "bytes": (src / name).stat().st_size,
            "download_completed_utc": datetime.fromtimestamp((src / name).stat().st_mtime, timezone.utc).isoformat()} for name, url in URLS.items()},
        "source_versions": {"clingen_file_date": lines[1], "hpo_release": "v2026-09-01", "hgnc": "live export, hash frozen"},
        "hpo_root_names": {term: names[term] for term in sorted(ROOTS)}, "clingen_genes_audited": len(audit),
        "eligible_pool": len(pool), "complete_covariate_pool": len(pool_complete), "matched_pairs": len(pairs),
        "matched_controls": len(match_counts), "protected_input_sha256": protected,
        "outcomes_accessed": False, "software": phase2["software"],
        "execution_command": f"rtk proxy .venv/bin/python scripts/revision_phase3_roster.py --source-dir {src} --output-dir {out}",
        "output_sha256": {path.name: digest(path) for path in sorted(out.iterdir())}}
    if any(digest(ROOT / path) != value for path, value in protected.items()):
        raise ValueError("Protected baseline changed during roster freeze")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: manifest[k] for k in ("clingen_genes_audited", "eligible_pool", "complete_covariate_pool", "matched_pairs", "matched_controls", "outcomes_accessed")}, indent=2))


if __name__ == "__main__":
    main()

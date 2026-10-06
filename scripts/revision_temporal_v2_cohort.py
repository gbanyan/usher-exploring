"""Inventory every case-catalog record and nominate date-adjudication work.

This script never reads scores or production evidence. Its output is a screening
ledger, not an automatically accepted clinical validation cohort.
"""
from collections import defaultdict
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006/temporal_validation_v2"
CACHE = ROOT / "data/cache/temporal-validation-v2-20261006/catalogs"
CUTOFF = "2020-12-31"


def pmids(text):
    text = str(text).strip()
    leading = re.match(r"(?:PMID\s*:?\s*)?([0-9]{6,9})\b", text, re.I)
    values = {leading[1]} if leading else set()
    values.update(m[1] for m in re.finditer(
        r"(?:PMID\s*:?\s*|pubmed(?:\.ncbi\.nlm\.nih\.gov)?/)([0-9]{6,9})", text, re.I)
    )
    if leading:
        # Explicit citation lists, not arbitrary OMIM numbers in trailing notes.
        tail = text[leading.end():]
        for match in re.finditer(r"(?:\s*(?:and|,|;|&)\s*|\s+)([0-9]{6,9})(?=\s*(?:and|,|;|&|$))", tail, re.I):
            values.add(match[1])
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=BASE / "cohort_screening")
    destination = parser.parse_args().output_dir
    if destination.exists():
        raise FileExistsError("Preserve prior screening ledger")
    hgnc_path = ROOT / "data/cache/temporal-extension-20261006/raw/hgnc_20201001.tsv"
    with hgnc_path.open() as handle:
        hgnc = list(csv.DictReader(handle, delimiter="\t"))
    approved = [g for g in hgnc if g["status"] == "Approved"]
    historical = {g["hgnc_id"]: g for g in approved}
    exact = {g["symbol"]: g["hgnc_id"] for g in approved}
    aliases, entrez = defaultdict(set), defaultdict(set)
    for gene in approved:
        for alias in gene["prev_symbol"].split("|") + gene["alias_symbol"].split("|"):
            if alias:
                aliases[alias].add(gene["hgnc_id"])
        if gene["entrez_id"]:
            entrez[gene["entrez_id"]].add(gene["hgnc_id"])

    def resolve(symbol, explicit=None, ncbi=None):
        if explicit:
            return explicit, "explicit_hgnc_id"
        if ncbi and len(entrez[ncbi]) == 1:
            return next(iter(entrez[ncbi])), "historical_entrez"
        if symbol in exact:
            return exact[symbol], "historical_approved_symbol"
        if len(aliases[symbol]) == 1:
            return next(iter(aliases[symbol])), "unambiguous_historical_alias"
        return f"UNRESOLVED:{symbol}", "unresolved_identifier"

    inputs = {hgnc_path}
    metadata = {}
    metadata_paths = [*CACHE.glob("*reference_batch_*.json"),
                      CACHE / "retnet_reference_metadata.json",
                      CACHE / "nonstandard_reference_pmids.json"]
    for path in metadata_paths:
        if not path.exists():
            continue
        inputs.add(path)
        for paper in json.loads(path.read_text())["resultList"]["result"]:
            if paper["source"] == "MED":
                metadata[paper["id"]] = paper

    ledger, genes = [], {}

    def register(record):
        key = record["gene_key"]
        gene = genes.setdefault(key, {"gene_key": key, "symbols": set(),
                                     "records": [], "reference_pmids": set(),
                                     "precutoff_clinical_references": [],
                                     "retained_for_date_screen": True})
        gene["symbols"].add(record["symbol"])
        gene["records"].append(record["record_id"])
        gene["reference_pmids"].update(record["pmids"])
        ledger.append(record)
        return gene

    current_paths = [CACHE / "panelapp307_format", *sorted(CACHE.glob("panel*_current.json"))]
    old_paths = [CACHE / "panel307_v2", *sorted(CACHE.glob("panel*_v1.json"))]
    old_green = defaultdict(list)
    for path in old_paths:
        inputs.add(path)
        panel = json.loads(path.read_text())
        if panel["version_created"][:10] > CUTOFF:
            raise ValueError("Historical reference panel is post-cutoff")
        for entry in panel["genes"]:
            if entry["confidence_level"] != "3":
                continue
            key, method = resolve(entry["entity_name"], entry["gene_data"].get("hgnc_id"))
            old_green[key].append({"panel_id": panel["id"], "version": panel["version"],
                "version_created": panel["version_created"], "symbol": entry["entity_name"],
                "phenotypes": entry["phenotypes"], "inheritance": entry["mode_of_inheritance"],
                "evidence": entry["evidence"], "identifier_method": method,
                "publications": entry["publications"], "source_path": str(path.relative_to(ROOT))})

    for path in current_paths:
        inputs.add(path)
        panel = json.loads(path.read_text())
        for entry in panel["genes"]:
            key, method = resolve(entry["entity_name"], entry["gene_data"].get("hgnc_id"))
            linked = sorted(set().union(*(pmids(p) for p in entry["publications"])), key=int)
            register({"record_id": f"panel{panel['id']}:{key}", "gene_key": key,
                "source": "PanelApp", "source_id": panel["id"], "version": panel["version"],
                "source_path": str(path.relative_to(ROOT)), "symbol": entry["entity_name"],
                "identifier_method": method, "confidence": entry["confidence_level"],
                "phenotypes": entry["phenotypes"], "inheritance": entry["mode_of_inheritance"],
                "pmids": linked, "nonstandard_references": [p for p in entry["publications"]
                    if not re.fullmatch(r"(?:PMID\s*:?\s*)?([0-9]{6,9})", p.strip(), re.I)],
                "precutoff_green_same_panel": any(r["panel_id"] == panel["id"] for r in old_green[key])})

    ret_paths = [CACHE / "retnet_genes", CACHE / "retnet_references", CACHE / "retnet_dates"]
    inputs.update(ret_paths)
    retinal = [g for c in json.loads(ret_paths[0].read_text()) for g in c["diseases"]]
    references = {r["id"]: r for c in json.loads(ret_paths[1].read_text()) for r in c["referenceItems"]}
    date_rows = defaultdict(list)
    for chromosome in json.loads(ret_paths[2].read_text()):
        for row in chromosome["diseaseCloneList"]:
            date_rows[row["diseaseId"]].append(row)
    for entry in retinal:
        key, method = resolve(entry["symbol1"], ncbi=entry.get("locusLink"))
        if not entry["symbol1"]:
            key, method = f"MAPPED_LOCUS:RetNet:{entry['id']}", "no_identified_gene"
        cited = [references[d["referenceId"]] for d in date_rows[entry["id"]] if d["referenceId"] in references]
        linked = sorted({p["medLine"] for p in cited if p.get("medLine") and p["medLine"].isdigit()}, key=int)
        gene = register({"record_id": f"RetNet:{entry['id']}", "gene_key": key,
            "source": "RetNet", "source_id": entry["id"], "version": "acquired_20261006",
            "source_path": str(ret_paths[0].relative_to(ROOT)), "symbol": entry["symbol1"],
            "identifier_method": method, "confidence": None,
            "phenotypes": [entry.get("disease1"), entry.get("disease2")],
            "inheritance": None, "pmids": linked, "nonstandard_references": [],
            "catalog_date_records": date_rows[entry["id"]], "catalog_comments":
            [entry.get("comment1"), entry.get("comment2"), entry.get("comment3")]})
        for pid in linked:
            paper = metadata.get(pid, {})
            date = paper.get("firstPublicationDate")
            if date and date <= CUTOFF and re.search(
                    r"patient|famil(?:y|ies)|proband|individual|human", paper.get("abstractText", ""), re.I):
                gene["precutoff_clinical_references"].append({"source": "RetNet_curated_human_disease",
                    "pmid": pid, "date": date, "title": paper.get("title"),
                    "requires_adjudication": True})

    requests = []
    for key, gene in genes.items():
        gene["symbols"] = sorted(s for s in gene["symbols"] if s)
        gene["reference_pmids"] = sorted(gene["reference_pmids"], key=int)
        gene["precutoff_green_records"] = old_green[key]
        gene["historical_hgnc"] = {k: historical.get(key, {}).get(k) for k in
            ("symbol", "ensembl_gene_id", "locus_group", "locus_type", "entrez_id")}
        gene["late_reference_pmids"] = [pid for pid in gene["reference_pmids"]
            if metadata.get(pid, {}).get("firstPublicationDate", "") > CUTOFF]
        gene["missing_reference_metadata"] = [pid for pid in gene["reference_pmids"] if pid not in metadata]
        gene["screen_status"] = ("not_identified_gene_mapped_locus" if not gene["symbols"] else
            "historical_clinical_record_requires_confirmation" if old_green[key] else
            "standardized_human_date_screen_required")
        if not old_green[key] and gene["symbols"]:
            symbols = set(gene["symbols"])
            if historical.get(key, {}).get("symbol"):
                symbols.add(historical[key]["symbol"])
            if key in historical:
                symbols.update(s for s in historical[key]["prev_symbol"].split("|") if s)
            requests.append({"gene_key": key, "symbols": sorted(symbols),
                             "historical_hgnc": gene["historical_hgnc"]})

    destination.mkdir(parents=True)
    (destination / "catalog_records.json").write_text(json.dumps(ledger, indent=2) + "\n")
    (destination / "gene_screening_ledger.json").write_text(json.dumps(sorted(genes.values(), key=lambda g:g["gene_key"]), indent=2) + "\n")
    (destination / "standardized_screen_requests.json").write_text(json.dumps(sorted(requests, key=lambda g:g["gene_key"]), indent=2) + "\n")
    manifest = {"catalog_records": len(ledger), "unique_gene_keys": len(genes),
        "historical_green_gene_keys": sum(bool(g["precutoff_green_records"]) for g in genes.values()),
        "standardized_date_screen_requests": len(requests), "not_an_eligible_cohort": True,
        "scores_read": False, "input_sha256": {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs)},
        "output_sha256": {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.glob('*.json'))}}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v for k,v in manifest.items() if 'sha256' not in k}, indent=2))


if __name__ == "__main__":
    main()

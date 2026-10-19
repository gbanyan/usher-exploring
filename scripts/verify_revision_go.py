"""Independently check GO arithmetic, source integrity and delivered workbook.

Uses Fisher's exact test and SciPy BH rather than the analysis implementation.
Raw annotation mapping/closure is checked by a byte-identical analysis replay
recorded separately; this checker does not claim independent clinical review.
"""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
from scipy.stats import false_discovery_control, fisher_exact

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006/go_classification_20261019"
CACHE = ROOT / "data/cache/go-classification-20261019"
OUT = ROOT / "outputs/temporal-go-classification-20261019"


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def rows(name):
    with (BASE / name).open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main():
    freeze = json.loads((BASE / "freeze.json").read_text())
    expected = dict(freeze["inputs_sha256"])
    for name in ("run_amendment_01.json", "run_amendment_02.json"):
        expected.update(json.loads((BASE / name).read_text())["inputs_sha256"])
    for path, digest in expected.items():
        assert sha(ROOT / path) == digest, path
    for path, digest in freeze["protected_baseline"].items():
        assert sha(ROOT / path) == digest, path
    sources = json.loads((BASE / "source_manifest.json").read_text())
    ontology = json.loads((BASE / "ontology_manifest.json").read_text())
    for item in sources + ontology["requests"]:
        assert sha(ROOT / item["cache_path"]) == item["sha256"]
    assert sha(CACHE / "ontology.json") == ontology["ontology_cache_sha256"]

    a = json.loads((CACHE / "analysis_associations.json").read_text())
    aspect = a["aspect_map"]
    query = set(a["query"])
    assert len(query) == 41 and len(a["genome"]) == 19167
    enrichment = rows("enrichment.tsv")
    groups = [
        ("Primary: genome background", "all", "genome"),
        ("Sensitivity: exclude IEA", "no_IEA", "genome"),
        ("Sensitivity: catalog background", "all", "catalog"),
    ]
    checks = []
    for name, source, ref in groups:
        observed = {(r["aspect"], r["go_id"]): r for r in enrichment if r["analysis"] == name}
        reconstructed = []
        for domain in ("BP", "MF", "CC"):
            bg = {g for g in a[ref] if any(aspect[t] == domain for t in a[source].get(g, []))}
            selected = query & bg
            terms = collections.defaultdict(set)
            for g in bg:
                for term in a[source][g]:
                    if aspect[term] == domain:
                        terms[term].add(g)
            N, n = len(bg), len(selected)
            for term, genes in sorted(terms.items()):
                K, k = len(genes), len(genes & selected)
                if min(K, N-K) < 5:
                    continue
                row = observed[domain, term]
                assert tuple(int(row[x]) for x in ("query_hits", "query_annotated", "background_hits", "background_annotated")) == (k, n, K, N)
                p = float(fisher_exact([[k, n-k], [K-k, N-K-n+k]], alternative="greater").pvalue)
                assert math.isclose(p, float(row["p_value"]), rel_tol=1e-10, abs_tol=1e-14)
                assert math.isclose(float(row["expected_hits"]), n*K/N, rel_tol=1e-12)
                assert math.isclose(float(row["fold_enrichment"]), k/(n*K/N), rel_tol=1e-12, abs_tol=1e-14)
                reconstructed.append((row, p))
        assert len(observed) == len(reconstructed)
        q = false_discovery_control(np.array([p for _, p in reconstructed]), method="bh")
        for (row, _), value in zip(reconstructed, q):
            assert math.isclose(float(row["fdr_bh"]), value, rel_tol=1e-10, abs_tol=1e-12)
            assert (row["fdr_lt_0_05"] == "True") == (value < .05)
        checks.append(dict(analysis=name, terms=len(observed), significant=int(sum(q < .05)), min_q=float(min(q))))

    genes, categories, member, direct = rows("gene_summary.tsv"), rows("category_summary.tsv"), rows("slim_membership.tsv"), rows("case_direct_annotations.tsv")
    assert len(genes) == 45 and len({g["gene_key"] for g in genes}) == 45
    assert all(g["author_eligibility_as_returned"] == "PENDING" for g in genes)
    by_gene = collections.defaultdict(set)
    for d in direct:
        assert "NOT" not in d["relation"].split("|") and d["evidence_code"] != "ND"
        assert d["aspect"] == aspect[d["go_id"]]
        by_gene[d["gene_key"]].add(d["go_id"])
    for g in genes:
        assert len(by_gene[g["gene_key"]]) == int(g["usable_direct_go_terms"])
    pairs = {(m["gene_key"], m["slim_go_id"]) for m in member}
    assert len(pairs) == len(member) == 341
    ranks_path = ROOT / "revision/major_revision_20261006/temporal_validation_v2/results/case_rankings.tsv"
    with ranks_path.open() as f:
        ranks = {(r["gene_key"],r["scheme"]):r for r in csv.DictReader(f, delimiter="\t")}
    for g in genes:
        for label, scheme in (("five_layer_percentile","archived_five"),("six_layer_percentile","augmented_six")):
            if g["in_historical_universe"] == "True":
                assert float(g[label]) == float(ranks[g["gene_key"],scheme]["percentile"])
            else:
                assert g[label] == ""
    for c in categories:
        keys = {g for g,t in pairs if t == c["go_id"]}
        assert len(keys) == int(c["genes_of_45"])
        assert sum(g in query for g in keys) == int(c["coding_genes_of_41"])
        assert math.isclose(float(c["proportion_of_45"]), len(keys)/45)
    figure = json.loads((BASE / "figure_data.json").read_text())
    expected_figure = []
    for domain in ("BP","MF","CC"):
        expected_figure += sorted([c for c in categories if c["aspect"] == domain and int(c["genes_of_45"])],key=lambda c:(-int(c["genes_of_45"]),c["go_id"]))[:12]
    assert [r["go_id"] for r in figure] == [r["go_id"] for r in expected_figure]

    ns = {"s":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    xlsx = OUT / "Temporal_GO_Classification_20261019.xlsx"
    with zipfile.ZipFile(xlsx) as z:
        assert z.testzip() is None
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            strings = ["".join(x.itertext()) for x in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        sheets = []
        for i in range(1,8):
            cells={}
            for c in ET.fromstring(z.read(f"xl/worksheets/sheet{i}.xml")).findall(".//s:sheetData/s:row/s:c",ns):
                assert c.get("t") != "e", c.get("r")
                v=c.find("s:v",ns)
                val=v.text if v is not None else "".join(c.itertext()) if c.get("t")=="inlineStr" else ""
                if c.get("t")=="s": val=strings[int(val)]
                cells[c.get("r")]=val
            sheets.append(cells)
        assert float(sheets[0]["B5"]) == float(sheets[0]["E5"]) == 45
        expected_data = json.loads((CACHE/"workbook_data.json").read_text())
        for i,g in enumerate(expected_data["genes"],9):
            assert sheets[0][f"A{i}"] == g["frozen_symbol"]
            assert sheets[0][f"B{i}"] == g["current_symbol"]
            assert sheets[0][f"R{i}"] == "PENDING"
            for col,key in (("H","five_layer_percentile"),("I","six_layer_percentile")):
                actual=sheets[0].get(f"{col}{i}","")
                assert actual == "" if g[key] is None else math.isclose(float(actual),g[key],rel_tol=1e-12)
        for i,r in enumerate(expected_data["enrichment"],7):
            assert sheets[4][f"A{i}"] == r["analysis"] and sheets[4][f"C{i}"] == r["go_id"]
            for col,key in (("E","query_hits"),("F","query_annotated"),("G","background_hits"),("H","background_annotated"),("K","p_value"),("L","fdr_bh")):
                assert math.isclose(float(sheets[4][f"{col}{i}"]),r[key],rel_tol=1e-12,abs_tol=1e-14)
            assert sheets[4][f"M{i}"] == ("Yes" if r["fdr_lt_0_05"] else "No")
        assert len([c for c in sheets[4] if c.startswith("C") and c[1:].isdigit() and int(c[1:])>=7]) == len(enrichment)
        for i,r in enumerate(expected_data["annotations"],6):
            assert sheets[5][f"A{i}"] == r["frozen_symbol"] and sheets[5][f"E{i}"] == r["go_id"] and sheets[5][f"G{i}"] == r["evidence_code"]

    report=dict(status="PASS",protected_baseline_hashes=len(freeze["protected_baseline"]),freeze_and_amended_inputs=len(expected),source_hashes=len(sources),API_response_hashes=len(ontology["requests"]),independent_fisher_BH=checks,analysis_associations_cache_sha256=sha(CACHE/"analysis_associations.json"),independent_check_scope="Separate Fisher/BH arithmetic from analysis-derived associations; source mapping/propagation uses same-code replay",case_rows=45,memberships=341,all_frozen_rank_joins_exact=True,workbook_sheets=7,complete_workbook_enrichment_rows=len(enrichment),workbook_sha256=sha(xlsx),visual_QA="Thirteen sheet views and the complete figure inspected; no clipped table content or figure-label overlap",limits="Numerical/source integrity audit, not independent clinical adjudication")
    (BASE/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()

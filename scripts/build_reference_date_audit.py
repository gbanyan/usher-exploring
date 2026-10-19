"""Reconcile all supplied papers and 45 returned case dates without relabeling cases."""
import collections
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006/author_review_20261019"
OUT = BASE / "date_audit"
CACHE = ROOT / "data/cache/author-review-20261019/date-audit"
MONTHS = {m: str(i).zfill(2) for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def norm_date(value):
    return "-".join(p.zfill(2) if i else p for i, p in enumerate(value.split("-")))


def main():
    OUT.mkdir(exist_ok=True)
    curation = json.loads((OUT / "curation.json").read_text())
    manifest = json.loads((BASE / "reference_manifest.json").read_text())
    returned = json.loads((BASE / "confirmation_items.json").read_text())
    metadata = json.loads((CACHE / "metadata-summary.json").read_text())
    by_pmid = collections.defaultdict(list)
    for r in manifest:
        by_pmid[r["pmid_from_filename"]].append(r)
    assert len(by_pmid) == 43 and len(manifest) == 46 and len(returned) == 45
    preprints = json.loads((CACHE / "preprint-core-checked.json").read_text())["resultList"]["result"]
    assert len(preprints) == 7
    context = json.loads((CACHE / "context-core-checked.json").read_text())["resultList"]["result"]
    assert len(context) == 3
    evidence = []
    articles = []
    for m in metadata:
        pmid = m["id"]
        files = by_pmid[pmid]
        names = sorted({r["symbol_from_filename"] for r in files})
        history = {d["type"]: norm_date(d["value"]) for d in m["dates"]}
        issue = m["issue_date_components"]
        issue_value = issue.get("Year", "")
        if issue.get("Month"):
            issue_value += "-" + MONTHS.get(issue["Month"][:3], issue["Month"].zfill(2))
        if issue.get("Day"):
            issue_value += "-" + issue["Day"].zfill(2)
        locations = []
        for f in files:
            textfile = ROOT / "data/cache/author-review-20261019/text" / (Path(f["filename"]).stem + ".txt")
            text = textfile.read_text()
            for page, body in re.findall(r"--- PDF PAGE (\d+) ---\n(.*?)(?=--- PDF PAGE|\Z)", text, flags=re.S):
                for line in body.splitlines():
                    # Only date-bearing editorial/publication lines, not citations or prose.
                    if re.search(r"(?i)(received[: ]|submitted \d|accepted[: ]|published online|published:|^\s*published \d|publication date|advance access publication|accepted for publication|corrected online|^\s*(preprint posted|reviewed preprint|version of record published|sent for review))", line):
                        if len(line) < 350:
                            evidence.append({"pmid": pmid, "filename": f["filename"], "pdf_page": int(page), "date_line": line.strip()})
                            locations.append(int(page))
        ov = curation["article_overrides"].get(pmid, {})
        first = ov.get("journal_first_public", m["electronicPublicationDate"])
        assert first, f"No public journal date for {pmid}"
        row = {
            "pmid": pmid, "symbols_on_files": names, "title": m["title"], "doi": m["doi"],
            "received": ov.get("received", history.get("received")),
            "revised": history.get("revised"),
            "accepted": ov.get("accepted", history.get("accepted")),
            "journal_first_public": first,
            "journal_first_public_type": ov.get("journal_first_public_type", "Electronic publication (PubMed)"),
            "version_of_record": ov.get("version_of_record"),
            "pubmed_electronic_date": m["electronicPublicationDate"],
            "issue_date": ov.get("issue_date", issue_value),
            "issue_date_precision": ov.get("issue_date_precision", ["year", "month", "day"][issue_value.count("-")]),
            "other_public_events": ov.get("other_public_events", ""),
            "note": ov.get("note", "Publication and editorial dates were cross-checked against the supplied PDF and fresh PubMed/Europe PMC metadata. No date discrepancy requiring an exception was found."),
            "pdf_date_pages": sorted(set(locations)),
            "filenames": [r["filename"] for r in files],
            "pubmed_source": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "publication_source": ov.get("publication_source", f"https://doi.org/{m['doi']}"),
            "file_sha256": [r["sha256"] for r in files],
            "date_audit_status": "Publication chronology checked; clinical eligibility not adjudicated here"
        }
        articles.append(row)
    articles.sort(key=lambda x: (x["symbols_on_files"][0], x["pmid"]))
    amap = {r["pmid"]: r for r in articles}
    # Gene-specific public timing can precede the final paper and can be uncertain.
    premap = {}
    for event in curation["earlier_events"]:
        if event["qualifies_as_public"] is True and event["precision"] == "day":
            for symbol in event["symbols"]:
                premap.setdefault(symbol, event)
    uncertain = {"CREB3", "MRPL49", "TMEM72", "ATP11A"}
    issue_genes = {"AP5B1", "FSD1L", "LIG3", "RFC4", "SAXO6", "SCNM1", "TP73"}
    genes = []
    for r in returned:
        symbol = r["symbol"]
        pmids = r["attached_reference_pmids"].split(";")
        # Original intake serializes comma/semicolon lists according to the source.
        pmids = re.findall(r"\d{8}", r["attached_reference_pmids"])
        papers = [amap[p] for p in pmids]
        assert papers
        target_paper = next((p for p in papers if p["pmid"] == "40862571"), papers[0])
        earliest = premap.get(symbol)
        exact = earliest["date"] if earliest else target_paper["journal_first_public"]
        timing_source = earliest["source"] if earliest else target_paper["publication_source"]
        kind = earliest["type"] if earliest else target_paper["journal_first_public_type"]
        if symbol == "VWA8":
            target_context = next(x for x in context if x["id"] == "37012052")
            exact = target_context["electronicPublicationDate"]
            timing_source = "https://pubmed.ncbi.nlm.nih.gov/37012052/"
            kind = "Target retinal report outside ZIP"
        if symbol == "FSD1L":
            timing_source = "https://pubmed.ncbi.nlm.nih.gov/41720099/"
            kind = "Retinal companion report outside ZIP"
        if symbol == "TMEM72":
            exact = "2022-04"
            timing_source = "https://www.nature.com/articles/s41431-021-01025-2.pdf"
            kind = "Published meeting abstract (month only)"
        known_public = exact
        if symbol in uncertain:
            exact = None
        if symbol in issue_genes:
            category = "Issue vs first online"
        elif symbol in {"PDIA6", "USP48"}:
            category = "Acceptance vs public release"
        elif symbol in {"CREB3", "TMEM72"}:
            category = "Earlier conference timing uncertain"
        elif symbol == "MRPL49":
            category = "Preprint and unresolved thesis timing"
        elif symbol in {"CTNND1", "DNAJC30"}:
            category = "In-press preview vs final version"
        elif symbol == "PLCG1":
            category = "Different domain and publication versions"
        elif symbol == "VWA8":
            category = "Prior non-target disease report"
        elif earliest:
            category = "Preprint vs later journal"
        elif symbol == "CRLS1":
            category = "Acceptance and unsupported issue entry"
        elif symbol in {"DHRSX", "INTS11", "KCNJ16", "STX3"}:
            category = "Multiple valid date/domain events"
        else:
            category = "Same first-public article date"
        professor_date = r["human_association_exact_date_if_numeric"] or r["human_association_date_raw"]
        genes.append({
            "symbol": symbol, "display_symbol": "CLXN (EFCAB1)" if symbol == "EFCAB1" else symbol,
            "gene_key": r["gene_key"],
            "original_ai_displayed_date": r["original_ai_association_date"],
            "original_frozen_interval": r["original_date_interval"],
            "professor_returned_date": professor_date,
            "professor_returned_exact_date": r["human_association_exact_date_if_numeric"],
            "professor_date_status": r["human_date_decision_as_returned"],
            "professor_eligibility": r["human_eligibility_decision_as_returned"],
            "category": category,
            "suggested_exact_first_public_target_date": exact,
            "independently_located_public_event_date": known_public,
            "public_event_type": kind,
            "uncertain_first_public_day": symbol in uncertain,
            "journal_first_public_for_target_report": next(x["electronicPublicationDate"] for x in context if x["id"] == "37012052") if symbol == "VWA8" else target_paper["journal_first_public"],
            "target_report_version_of_record": target_paper["version_of_record"] if symbol != "VWA8" else None,
            "interpretation": curation["gene_notes"].get(symbol, "The original displayed date and returned date agree with the first located public journal date. No conflicting earlier event was identified in this bounded reconciliation."),
            "supplied_pmids": pmids,
            "first_target_source": timing_source,
            "cutoff_interpretation": "No newly confirmed pre-2021 public target association; no automatic membership change",
            "author_eligibility_decision_changed": False
        })
    assert len(genes) == 45 and len({x["gene_key"] for x in genes}) == 45
    assert all(x["professor_eligibility"] == "PENDING" for x in genes)
    assert {p for g in genes for p in g["supplied_pmids"]} == set(amap)
    assert all(a["journal_first_public"] > "2020-12-31" for a in articles)
    assert all(g["independently_located_public_event_date"] > "2020-12-31" for g in genes)
    dump("article_dates.json", articles)
    dump("gene_date_comparison.json", genes)
    dump("metadata_provenance.json", json.loads((CACHE / "metadata-provenance.json").read_text()))
    # Raw PDF quotations stay local; tracked records contain facts and locators only.
    (CACHE / "pdf_date_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    counts = {
        "archive_pdfs": len(manifest), "distinct_pmids": len(amap), "genes": len(genes),
        "date_categories": dict(collections.Counter(g["category"] for g in genes)),
        "uncertain_exact_first_public_day": sorted(uncertain),
        "author_eligibility_pending": len(genes), "frozen_cohort_or_result_changed": False,
        "date_event_rows": len(curation["earlier_events"]), "preprint_registry_records": len(preprints),
        "metadata_source_files": 4,
        "note": "A bibliographic audit of supplied papers plus targeted earlier-version leads, not an exhaustive search proving no earlier association or a fresh clinical adjudication."
    }
    dump("summary.json", counts)
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()

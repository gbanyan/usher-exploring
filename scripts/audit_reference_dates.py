"""Read-only acquisition of returned-reference bibliographic dates (19 Oct 2026).

Raw publisher/PubMed metadata stays in the ignored cache. Curated date events
are kept separately; receipt/acceptance/index dates are never publication dates.
"""
import hashlib
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006/author_review_20261019"
CACHE = ROOT / "data/cache/author-review-20261019/date-audit"


def fetch(url, target):
    if not target.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "UsherPipe-date-audit/1.0"})
        with urllib.request.urlopen(req, timeout=90) as response:
            target.write_bytes(response.read())
    return target.read_bytes()


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((BASE / "reference_manifest.json").read_text())
    ids = sorted({r["pmid_from_filename"] for r in manifest})
    query = "SRC:MED AND EXT_ID:(" + " OR ".join(ids) + ")"
    epmc = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
        {"query": query, "resultType": "core", "pageSize": 100, "format": "json"}
    )
    raw = fetch(epmc, CACHE / "europepmc-core.json")
    records = json.loads(raw)["resultList"]["result"]
    assert {r["id"] for r in records} == set(ids)
    ncbi = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
    )
    xml = fetch(ncbi, CACHE / "pubmed.xml")
    pubs = {}
    for a in ET.fromstring(xml).findall("PubmedArticle"):
        pmid = a.findtext("MedlineCitation/PMID")
        dates = []
        for d in a.findall(".//PubMedPubDate"):
            dates.append({"type": d.attrib.get("PubStatus"), "value": "-".join(d.findtext(k) or "" for k in ("Year", "Month", "Day"))})
        for d in a.findall(".//ArticleDate"):
            dates.append({"type": d.attrib.get("DateType"), "value": "-".join(d.findtext(k) or "" for k in ("Year", "Month", "Day"))})
        d = a.find(".//JournalIssue/PubDate")
        issue = {c.tag: c.text for c in d} if d is not None else {}
        pubs[pmid] = {"dates": dates, "issue_date_components": issue}
    assert set(pubs) == set(ids)
    summary = []
    for r in sorted(records, key=lambda x: x["id"]):
        summary.append({k: r.get(k) for k in ("id", "doi", "pmcid", "title", "firstPublicationDate", "electronicPublicationDate", "journalInfo", "pubYear")} | pubs[r["id"]])
    (CACHE / "metadata-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    sources = [{"url": url, "local_cache": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "acquired_on": "2026-10-19"} for url, path in [(epmc, CACHE / "europepmc-core.json"), (ncbi, CACHE / "pubmed.xml")]]
    (CACHE / "metadata-provenance.json").write_text(json.dumps(sources, indent=2) + "\n")
    for name, query in [
        ("preprint-core", "SRC:PPR AND EXT_ID:(PPR349560 OR PPR705483 OR PPR923018 OR PPR785159 OR PPR915961 OR PPR737916 OR PPR963443)"),
        ("context-core", "SRC:MED AND EXT_ID:(37012052 OR 40638000 OR 41720099)"),
    ]:
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
            {"query": query, "resultType": "core", "pageSize": 100, "format": "json"}
        )
        target = CACHE / f"{name}-checked.json"
        payload = fetch(url, target)
        sources.append({"url": url, "local_cache": str(target.relative_to(ROOT)), "sha256": hashlib.sha256(payload).hexdigest(), "acquired_on": "2026-10-19"})
    (CACHE / "metadata-provenance.json").write_text(json.dumps(sources, indent=2) + "\n")
    print(f"Matched {len(summary)} unique supplied PMID labels in Europe PMC and PubMed XML.")


if __name__ == "__main__":
    main()

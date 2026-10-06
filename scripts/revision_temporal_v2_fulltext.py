"""Cache official Europe PMC JATS for clinical date/evidence adjudication.

This acquisition script does not read or construct gene rankings.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache/temporal-validation-v2-20261006"
BASE = ROOT / "revision/major_revision_20261006/temporal_validation_v2"


def acquire(record):
    pmc = record["pmcid"]
    path = CACHE / "clinical_fulltext" / f"{pmc}.xml"
    manifest = path.with_suffix(".manifest.json")
    if path.exists() and manifest.exists():
        return json.loads(manifest.read_text())
    row = dict(record, url=f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmc}/fullTextXML",
               started_utc=datetime.now(timezone.utc).isoformat(), complete=False)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(row["url"], timeout=45) as response:
                data = response.read()
            article = ET.fromstring(data)
            if article.tag != "article":
                raise ValueError("Response is not JATS article XML")
            path.write_bytes(data)
            row.update(complete=True, path=str(path.relative_to(ROOT)),
                       sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                       publication_dates=[dict(node.attrib,
                           value="-".join((node.findtext("year", ""),
                                           node.findtext("month", ""),
                                           node.findtext("day", ""))))
                           for node in article.findall("./front/article-meta/pub-date")])
            break
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            if "404" in str(exc):
                break
            time.sleep(2 * (attempt + 1))
    row["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest.write_text(json.dumps(row, indent=2) + "\n")
    return row


if __name__ == "__main__":
    (CACHE / "clinical_fulltext").mkdir(exist_ok=True)
    requests = json.loads((CACHE / "catalogs/clinical_late_fulltext_requests.json").read_text())
    with ThreadPoolExecutor(3) as pool:
        rows = list(pool.map(acquire, requests))
    (BASE / "clinical_fulltext_acquisition.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps({"requested": len(rows), "complete": sum(r["complete"] for r in rows)}))

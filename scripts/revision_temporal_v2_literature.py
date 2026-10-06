"""Acquire complete, date-bounded PMID sets; do not inspect any gene ranking."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006/temporal_validation_v2"
CACHE = ROOT / "data/cache/temporal-validation-v2-20261006/literature_date_sorted"


def acquire(row):
    name, query = row["name"], row["query"]
    directory = CACHE / name
    directory.mkdir(parents=True, exist_ok=True)
    cursor, ids, page = "*", set(), 0
    total = None
    page_hashes = {}
    while True:
        target = directory / f"page_{page:04d}.json"
        parameters = {"query": query, "format": "json", "resultType": "idlist",
                      "pageSize": "1000", "cursorMark": cursor}
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(parameters)
        if target.exists():
            data = target.read_bytes()
        else:
            for attempt in range(5):
                try:
                    with urllib.request.urlopen(url, timeout=60) as response:
                        data = response.read()
                    parsed = json.loads(data)
                    if "hitCount" not in parsed or "resultList" not in parsed:
                        raise ValueError("Unexpected search response")
                    temporary = target.with_suffix(".part")
                    temporary.write_bytes(data)
                    temporary.rename(target)
                    break
                except Exception as error:
                    print(f"{name}, page {page}, retry {attempt + 1}: {error}", flush=True)
                    if attempt == 4:
                        raise
                    time.sleep(5)
        parsed = json.loads(data)
        page_hashes[target.name] = hashlib.sha256(data).hexdigest()
        if parsed.get("request", {}).get("queryString") != query:
            raise ValueError("Cached page belongs to another query")
        if total is None:
            total = parsed["hitCount"]
        elif parsed["hitCount"] != total:
            raise ValueError("Search corpus changed during pagination")
        results = parsed["resultList"]["result"]
        for item in results:
            if item["source"] != "MED" or not item["id"].isdigit():
                raise ValueError("Unexpected PMID/source")
            ids.add(item["id"])
        new_cursor = parsed.get("nextCursorMark")
        if not results or not new_cursor or new_cursor == cursor:
            break
        cursor = new_cursor
        page += 1
        if page % 25 == 0:
            print(f"{name}: {len(ids)} / {total} IDs", flush=True)
    if len(ids) != total:
        raise ValueError(f"Incomplete {name}: {len(ids)} != {total}")
    output = CACHE / f"{name}_pmids.txt.gz"
    payload = ("\n".join(sorted(ids, key=int)) + "\n").encode()
    output.write_bytes(gzip.compress(payload, mtime=0))
    manifest = {"name": name, "query": query, "unique_pmids": len(ids),
                "api_hit_count": total, "path": str(output.relative_to(ROOT)),
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "page_sha256": page_hashes, "complete": True,
                "finished_utc": datetime.now(timezone.utc).isoformat()}
    (BASE / f"literature_{name}_acquisition.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{name}: complete {len(ids)} IDs", flush=True)
    return manifest


if __name__ == "__main__":
    source = BASE / "literature_queries.json"
    rows = json.loads(source.read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        manifests = list(pool.map(acquire, rows))
    (BASE / "literature_acquisition.json").write_text(json.dumps({
        "query_spec_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "sources": manifests, "historical_text_snapshot": False,
        "warning": "Present-day title/abstract matches with pre-cutoff publication/index dates; no MeSH queries."
    }, indent=2) + "\n")

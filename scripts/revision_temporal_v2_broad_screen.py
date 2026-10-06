"""Broad gene/target screening including preprints, aliases and laterality.

Every retained catalog gene is queried without requiring human/variant words in
the abstract. Results require adjudication and do not establish causal evidence.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request
from revision_temporal_v2_human_screen import TARGET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006/temporal_validation_v2"
CACHE = ROOT / "data/cache/temporal-validation-v2-20261006/broad_target_screen"


def acquire(row):
    key = row["gene_key"].replace(":", "_")
    terms = " OR ".join(f'TITLE_ABS:"{symbol}"' for symbol in row["symbols"])
    query = (f"({terms}) AND TITLE_ABS:({TARGET} OR heterotaxy OR laterality OR coloboma OR hydrocephalus) "
             "AND FIRST_PDATE:[1800-01-01 TO 2026-10-06] sort_date:y")
    record = dict(gene_key=row["gene_key"], symbols=row["symbols"],
                  omitted_text_aliases=row["omitted_text_aliases"], query=query,
                  started_utc=datetime.now(timezone.utc).isoformat(), pages=[], complete=False)
    existing = CACHE / f"{key}.manifest.json"
    if existing.exists():
        prior = json.loads(existing.read_text())
        if prior["query"] != query:
            raise ValueError("Query changed; preserve prior cache")
        if prior["complete"]:
            return prior
    cursor, identities, total = "*", set(), None
    for page in range(500):
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
            dict(query=query, format="json", resultType="core", pageSize=1000, cursorMark=cursor))
        path = CACHE / f"{key}.page_{page:04d}.json"
        try:
            if path.exists():
                data = path.read_bytes()
            else:
                for attempt in range(4):
                    try:
                        with urllib.request.urlopen(url, timeout=40) as response:
                            data = response.read()
                        parsed = json.loads(data)
                        if "hitCount" not in parsed:
                            raise ValueError("Unexpected search response")
                        path.write_bytes(data)
                        break
                    except Exception:
                        if attempt == 3:
                            raise
                        time.sleep(attempt + 1)
            parsed = json.loads(data)
            if parsed["request"]["queryString"] != query:
                raise ValueError("Cached response belongs to another query")
            if total is None:
                total = parsed["hitCount"]
            elif total != parsed["hitCount"]:
                raise ValueError("Hit count changed during pagination")
            results = parsed["resultList"]["result"]
            new = {(r["source"], r["id"]) for r in results}
            if len(new) != len(results) or identities & new:
                raise ValueError("Duplicate records across cursor pages")
            identities.update(new)
            record["pages"].append(dict(path=str(path.relative_to(ROOT)), url=url,
                                        sha256=hashlib.sha256(data).hexdigest(), records=len(results)))
            if len(identities) == total:
                record["complete"] = True
                break
            next_cursor = parsed.get("nextCursorMark")
            if not results or not next_cursor or next_cursor == cursor:
                raise ValueError("Cursor exhausted before hit count")
            cursor = next_cursor
        except Exception as exc:
            record["error"] = repr(exc)
            break
    record.update(hit_count=total, retrieved=len(identities),
                  finished_utc=datetime.now(timezone.utc).isoformat())
    existing.write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    CACHE.mkdir(exist_ok=True)
    specification = BASE / "cohort_screening/broad_target_search_requests.json"
    rows = json.loads(specification.read_text())
    with ThreadPoolExecutor(3) as pool:
        records = list(pool.map(acquire, rows))
    (BASE / "cohort_screening/broad_target_search_manifest.json").write_text(json.dumps(
        dict(spec_sha256=hashlib.sha256(specification.read_bytes()).hexdigest(),
             requests=records, scores_read=False), indent=2) + "\n")
    print(json.dumps(dict(requested=len(records), complete=sum(r['complete'] for r in records),
                         records=sum(r['retrieved'] for r in records))))

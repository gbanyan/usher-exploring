"""Standardized post-cutoff human-disease screening for unresolved catalog genes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006/temporal_validation_v2"
CACHE = ROOT / "data/cache/temporal-validation-v2-20261006/human_screen"
TARGET = ('retina OR retinal OR photoreceptor OR "retinitis pigmentosa" OR '
          '"cone dystrophy" OR "rod-cone" OR "optic atrophy" OR '
          'hearing OR deafness OR cochlea OR usher OR ciliopathy OR '
          '"ciliary dyskinesia" OR joubert OR "bardet biedl" OR '
          'nephronophthisis OR "polycystic kidney" OR "short rib" OR '
          '"situs inversus" OR "oral facial digital" OR bronchiectasis')


def screen(row):
    key = row["gene_key"]
    symbol_query = " OR ".join('TITLE_ABS:"' + symbol.replace('"', '') + '"'
                               for symbol in row["symbols"])
    query = (f"({symbol_query}) AND TITLE_ABS:({TARGET}) AND "
             "TITLE_ABS:(patient OR patients OR proband OR family OR families OR individuals) AND "
             "TITLE_ABS:(variant OR variants OR mutation OR mutations OR segregation OR biallelic OR homozygous) "
             "AND SRC:MED AND FIRST_PDATE:[2021-01-01 TO 2026-10-06] sort_date:y")
    target = CACHE / (key.replace(":", "_") + ".json")
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode({
        "query": query, "format": "json", "resultType": "core", "pageSize": "1000"})
    started = datetime.now(timezone.utc).isoformat()
    manifest = {"gene_key": key, "symbols": row["symbols"], "query": query,
                "url": url, "started_utc": started, "not_clinical_adjudication": True}
    try:
        if target.exists():
            data = target.read_bytes()
            manifest["cached_existing"] = True
        else:
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(url, timeout=60) as response:
                        data = response.read()
                    parsed = json.loads(data)
                    if "hitCount" not in parsed:
                        raise ValueError("Unexpected search response")
                    temporary = target.with_suffix(".part")
                    temporary.write_bytes(data)
                    temporary.rename(target)
                    manifest["cached_existing"] = False
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(5)
        parsed = json.loads(data)
        if parsed.get("request", {}).get("queryString") != query:
            raise ValueError("Cached response belongs to another query")
        results = parsed["resultList"]["result"]
        cursor, page = parsed.get("nextCursorMark"), 1
        total = parsed["hitCount"]
        while len(results) < total and cursor:
            extra = target.with_name(target.stem + f".page_{page:04d}.json")
            next_url = url + "&cursorMark=" + urllib.parse.quote(cursor, safe="")
            if extra.exists():
                more_data = extra.read_bytes()
            else:
                with urllib.request.urlopen(next_url, timeout=60) as response:
                    more_data = response.read()
                extra.write_bytes(more_data)
            more = json.loads(more_data)
            if more["hitCount"] != total:
                raise ValueError("Search corpus changed during pagination")
            additional = more["resultList"]["result"]
            if not additional:
                break
            results.extend(additional)
            new_cursor = more.get("nextCursorMark")
            if new_cursor == cursor:
                break
            cursor, page = new_cursor, page + 1
        if len({r['id'] for r in results}) != len(results):
            raise ValueError("Duplicate IDs across cursor pages")
        manifest.update(hit_count=parsed["hitCount"], retrieved=len(results),
            source_path=str(target.relative_to(ROOT)), sha256=hashlib.sha256(data).hexdigest(),
            complete=parsed["hitCount"] == len(results),
            pmids=[r["id"] for r in results if r["source"] == "MED"])
    except Exception as error:
        manifest.update(complete=False, error=repr(error))
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (CACHE / (key.replace(":", "_") + ".manifest.json")).write_text(json.dumps(manifest, indent=2) + "\n")
    print(key, manifest.get("hit_count"), manifest.get("error"), flush=True)
    return manifest


if __name__ == "__main__":
    specification = BASE / "cohort_screening/standardized_screen_requests.json"
    rows = json.loads(specification.read_text())
    CACHE.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        manifests = list(pool.map(screen, rows))
    (BASE / "cohort_screening/human_screen_manifest.json").write_text(json.dumps({
        "spec_sha256": hashlib.sha256(specification.read_bytes()).hexdigest(),
        "requests": manifests, "rankings_read": False,
        "warning": "Search results require human association/date adjudication; no-hit is not verified biological absence."
    }, indent=2) + "\n")

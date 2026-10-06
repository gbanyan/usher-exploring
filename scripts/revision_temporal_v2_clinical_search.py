"""Acquire broader Mendelian/date screening without predictor outcomes.

Includes preprints and non-target disease reports, unlike the first catalog
screen. Search hits are nominations, not automatically causal evidence.
"""
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
CACHE = ROOT / "data/cache/temporal-validation-v2-20261006/clinical_search"


def screen(row):
    key = row["gene_key"]
    symbols = sorted(set(row["symbols"]))
    terms = " OR ".join(f'TITLE_ABS:"{s}"' for s in symbols)
    query = (f"({terms}) AND TITLE_ABS:(patient OR patients OR proband OR family OR families OR individuals) "
             "AND TITLE_ABS:(variant OR variants OR mutation OR mutations) "
             "AND TITLE_ABS:(germline OR biallelic OR homozygous OR segregation OR consanguineous OR Mendelian OR congenital OR deafness OR retinal) "
             "AND FIRST_PDATE:[1800-01-01 TO 2026-10-06] sort_date:y")
    target = CACHE / (key.replace(":", "_") + ".json")
    manifest = target.with_suffix(".manifest.json")
    if target.exists() and manifest.exists():
        prior = json.loads(manifest.read_text())
        if prior["query"] != query:
            raise ValueError("Query changed; use a new cache")
        if prior["complete"]:
            return prior
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
        dict(query=query, format="json", resultType="core", pageSize=1000))
    record = dict(gene_key=key, symbols=symbols, query=query, url=url,
                  started_utc=datetime.now(timezone.utc).isoformat(), complete=False,
                  not_clinical_adjudication=True)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=35) as response:
                data = response.read()
            parsed = json.loads(data)
            results = parsed["resultList"]["result"]
            target.write_bytes(data)
            pages = [dict(path=str(target.relative_to(ROOT)), url=url,
                          sha256=hashlib.sha256(data).hexdigest(), records=len(results))]
            cursor, page = parsed.get("nextCursorMark"), 1
            while len(results) < parsed["hitCount"]:
                if not cursor:
                    raise ValueError("Search cursor exhausted before hit count")
                next_url = url + "&cursorMark=" + urllib.parse.quote(cursor, safe="")
                extra = target.with_name(target.stem + f".page_{page:04d}.json")
                if extra.exists():
                    more_data = extra.read_bytes()
                else:
                    with urllib.request.urlopen(next_url, timeout=35) as response:
                        more_data = response.read()
                    extra.write_bytes(more_data)
                more = json.loads(more_data)
                if more["hitCount"] != parsed["hitCount"]:
                    raise ValueError("Hit count changed during pagination")
                additional = more['resultList']['result']
                if not additional or more.get('nextCursorMark') == cursor:
                    raise ValueError("Search cursor did not advance")
                results.extend(additional)
                pages.append(dict(path=str(extra.relative_to(ROOT)), url=next_url,
                                  sha256=hashlib.sha256(more_data).hexdigest(), records=len(additional)))
                cursor, page = more.get('nextCursorMark'), page + 1
            if len({(r['source'], r['id']) for r in results}) != len(results):
                raise ValueError("Duplicate search records")
            record.update(complete=True, hit_count=len(results), source_path=str(target.relative_to(ROOT)),
                          sha256=hashlib.sha256(data).hexdigest(), pages=pages)
            break
        except Exception as exc:
            record["error"] = repr(exc)
            time.sleep(attempt + 1)
    record["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest.write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    CACHE.mkdir(exist_ok=True)
    specification = BASE / "cohort_screening/clinical_search_requests.json"
    rows = json.loads(specification.read_text())
    with ThreadPoolExecutor(3) as pool:
        records = list(pool.map(screen, rows))
    (BASE / "cohort_screening/clinical_search_manifest.json").write_text(json.dumps(
        dict(spec_sha256=hashlib.sha256(specification.read_bytes()).hexdigest(),
             requests=records, scores_read=False), indent=2) + "\n")
    print(json.dumps(dict(requested=len(records), complete=sum(r['complete'] for r in records))))

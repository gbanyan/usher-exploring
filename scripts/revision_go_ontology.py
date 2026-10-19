"""Snapshot authoritative QuickGO ancestor closures for all human GAF terms."""
import concurrent.futures
import gzip
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from revision_go_common import read_editor, term_resolver

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache/go-classification-20261019"
BASE = ROOT / "revision/major_revision_20261006/go_classification_20261019"
API = "https://www.ebi.ac.uk/QuickGO/services/ontology/go"


def get(url, target):
    if not target.exists():
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=70) as response:
                    data = response.read()
                parsed = json.loads(data)
                if "results" not in parsed and "go" not in parsed:
                    raise ValueError("Unexpected ontology response")
                tmp = target.with_suffix(".part")
                tmp.write_bytes(data)
                tmp.rename(target)
                break
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
    data = target.read_bytes()
    return json.loads(data), {"url": url, "cache_path": str(target.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    folder = CACHE / "quickgo"
    folder.mkdir(exist_ok=True)
    before, about_record = get(API + "/about", folder / "about_before.json")
    assert before["go"]["timestamp"] == "2026-09-27", before
    editor = read_editor(CACHE / "go-edit-20260927.obo")
    resolve = term_resolver(editor)
    direct, invalid = set(), set()
    for name in ("human_protein.gaf.gz", "human_rna.gaf.gz"):
        with gzip.open(CACHE / name, "rt") as handle:
            for line in handle:
                if line.startswith("!"):
                    continue
                fields = line.rstrip("\n").split("\t")
                if len(fields) < 17:
                    raise ValueError("Malformed GAF")
                if fields[12].split("|")[0] != "taxon:9606" or "NOT" in fields[3].split("|") or fields[6] == "ND":
                    continue
                key = resolve(fields[4])
                if key:
                    direct.add(key)
                else:
                    invalid.add(fields[4])
    slim = {key for key, row in editor.items() if "goslim_generic" in row["subsets"] and not row.get("obsolete")}
    ids = sorted(direct | slim)
    print(f"Fetching authoritative ancestors for {len(ids):,} direct/slim IDs; {len(invalid)} unresolved editor IDs", flush=True)
    records, ontology = [about_record], {}
    tasks = [(i, ids[i:i+60]) for i in range(0, len(ids), 60)]
    def fetch(task):
        start, keys = task
        url = API + "/terms/" + ",".join(keys) + "/ancestors?relations=is_a,part_of"
        data, record = get(url, folder / f"ancestors_{start:05d}.json")
        actual = {r["id"] for r in data["results"]}
        assert actual == set(keys), (start, set(keys) - actual)
        return data["results"], record
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for i, (rows, record) in enumerate(pool.map(fetch, tasks), 1):
            records.append(record)
            ontology.update((r["id"], r) for r in rows)
            if i % 40 == 0:
                print(f"Cached {i}/{len(tasks)} ontology batches", flush=True)
    ancestors = {key for r in ontology.values() for key in r["ancestors"]}
    missing = sorted(ancestors - set(ontology))
    print(f"Fetching names for {len(missing):,} additional ancestor IDs", flush=True)
    def fetch_names(task):
        i, keys = task
        data, record = get(API + "/terms/" + ",".join(keys), folder / f"names_{i:05d}.json")
        assert {r["id"] for r in data["results"]} == set(keys)
        return data["results"], record
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for rows, record in pool.map(fetch_names, [(i, missing[i:i+60]) for i in range(0, len(missing), 60)]):
            records.append(record)
            ontology.update((r["id"], r) for r in rows)
    # A fresh end-state request verifies that one ontology version served all batches.
    path = folder / "about_after.json"
    if path.exists():
        path.unlink()
    after, record = get(API + "/about", path)
    assert before == after, "QuickGO changed ontology version during acquisition"
    records.append(record)
    (CACHE / "ontology.json").write_text(json.dumps(ontology, separators=(",", ":")) + "\n")
    (BASE / "ontology_manifest.json").write_text(json.dumps({
        "ontology_version": before["go"], "source_resolution_commit": "18a183b", "direct_term_ids": len(direct),
        "generic_slim_active_ids": len(slim), "cached_term_objects": len(ontology), "unresolved_editor_ids": sorted(invalid),
        "allowed_ancestry_relations": ["is_a", "part_of"], "requests": records,
        "ontology_cache_sha256": hashlib.sha256((CACHE / "ontology.json").read_bytes()).hexdigest()
    }, indent=2) + "\n")
    print(f"Cached {len(ontology):,} term objects; version remains {after['go']['timestamp']}")


if __name__ == "__main__":
    main()

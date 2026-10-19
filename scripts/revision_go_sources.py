"""Acquire pinned raw inputs for the post-hoc 45-case GO analysis."""
import concurrent.futures
import gzip
import hashlib
import json
import urllib.request
import fcntl
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache/go-classification-20261019"
BASE = ROOT / "revision/major_revision_20261006/go_classification_20261019"
SOURCES = {
    "human_protein.gaf.gz": "https://ftp.ebi.ac.uk/pub/databases/GO/goa/HUMAN/goa_human.gaf.gz",
    "human_rna.gaf.gz": "https://ftp.ebi.ac.uk/pub/databases/GO/goa/HUMAN/goa_human_rna.gaf.gz",
    "hgnc_complete_set.tsv": "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt",
    "go-edit-20260927.obo": "https://raw.githubusercontent.com/geneontology/go-ontology/16154084af7ef6330f815c63fde0b6b6ff08b8f2/src/ontology/go-edit.obo",
}


def acquire(item):
    name, url = item
    target = CACHE / name
    meta = CACHE / (name + ".http.json")
    if not target.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "UsherPipe-GO-description/1.0"})
        with urllib.request.urlopen(req, timeout=90) as response:
            tmp = target.with_suffix(target.suffix + ".part")
            with tmp.open("wb") as stream:
                while block := response.read(1 << 20):
                    stream.write(block)
            tmp.rename(target)
            meta.write_text(json.dumps({"url": url, "resolved_url": response.geturl(), "last_modified": response.headers.get("Last-Modified"), "acquired_on": "2026-10-19"}, indent=2) + "\n")
    record = json.loads(meta.read_text())
    record.update(name=name, cache_path=str(target.relative_to(ROOT)), bytes=target.stat().st_size,
                  sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    if name.endswith(".gz"):
        headers = []
        with gzip.open(target, "rt") as stream:
            for line in stream:
                if not line.startswith("!"):
                    break
                headers.append(line.rstrip())
        record["gaf_headers"] = headers
    print(f"Acquired {name}: {record['bytes']:,} bytes", flush=True)
    return record


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    lock = (CACHE / "acquisition.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(acquire, SOURCES.items()))
    (BASE / "source_manifest.json").write_text(json.dumps(records, indent=2) + "\n")
    print(json.dumps([{k: r.get(k) for k in ("name", "last_modified", "gaf_headers")} for r in records], indent=2))


if __name__ == "__main__":
    main()

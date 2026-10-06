"""Acquire complete historical inputs separately from the preserved pilot."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "hpa_v20_rna.zip": "https://v20.proteinatlas.org/download/rna_tissue_hpa.tsv.zip",
    "zfin_20201231_phenotypes.tsv": "https://zfin.org/downloads/archive/2020.12.31/phenoGeneCleanData_fish.txt",
    "zfin_20201231_orthologs.tsv": "https://zfin.org/downloads/archive/2020.12.31/human_orthos.txt",
    "impc_release11_phenotypes.csv.gz": "https://ftp.ebi.ac.uk/pub/databases/impc/all-data-releases/release-11.0/csv/IMPC_genotype_phenotype.csv.gz",
}


def acquire(item, cache):
    name, url = item
    target = cache / name
    row = {"name": name, "url": url, "started_utc": datetime.now(timezone.utc).isoformat(),
           "path": str(target.relative_to(ROOT)), "complete": False}
    if target.exists():
        raise FileExistsError(target)
    part = target.with_name(target.name + ".part")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "UsherPipe-temporal-v2/1.0"})
        h = hashlib.sha256()
        with urllib.request.urlopen(request, timeout=60) as response, part.open("xb") as handle:
            row.update(status=response.status, final_url=response.url,
                       content_type=response.headers.get("Content-Type"),
                       last_modified=response.headers.get("Last-Modified"),
                       content_length=response.headers.get("Content-Length"))
            while block := response.read(1024 * 1024):
                handle.write(block)
                h.update(block)
        if row["content_length"] is not None and part.stat().st_size != int(row["content_length"]):
            raise ValueError("Transfer size differs from Content-Length")
        part.rename(target)
        row.update(complete=True, sha256=h.hexdigest(), bytes=target.stat().st_size, error=None)
    except Exception as e:
        row.update(error=f"{type(e).__name__}: {e}", partial_bytes=part.stat().st_size if part.exists() else 0)
    row["finished_utc"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps({k: row.get(k) for k in ("name", "complete", "bytes", "error")}), flush=True)
    return row


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data/cache/temporal-validation-v2-20261006/raw")
    parser.add_argument("--manifest", type=Path, default=ROOT / "revision/major_revision_20261006/temporal_validation_v2/acquisition_initial.json")
    args = parser.parse_args()
    if args.manifest.exists():
        raise FileExistsError(args.manifest)
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda item: acquire(item, args.cache_dir), SOURCES.items()))
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(rows, indent=2) + "\n")
    if not all(r["complete"] for r in rows):
        raise SystemExit("Some sources are incomplete; see preserved acquisition manifest")

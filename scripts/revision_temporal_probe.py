"""Bounded official archive probes; never replace pipeline input caches."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROBES = {
    "go_archive_docs": "https://geneontology.org/docs/go-archives/",
    "go_2020_index": "https://release.geneontology.org/2020-12-08/annotations/",
    "go_2015_index": "https://release.geneontology.org/2015-12-01/annotations/",
    "hpa_v20_downloads": "https://v20.proteinatlas.org/about/download",
    "hpa_v16_downloads": "https://v16.proteinatlas.org/about/download",
    "hpa_v20_subcellular": "https://v20.proteinatlas.org/download/subcellular_location.tsv.zip",
    "hpa_v20_normal_tissue": "https://v20.proteinatlas.org/download/normal_tissue.tsv.zip",
    "mgi_reports_archive": "https://www.informatics.jax.org/downloads/reports/archive/",
    "zfin_downloads_archive": "https://zfin.org/downloads/archive",
    "impc_all_releases": "https://ftp.ebi.ac.uk/pub/databases/impc/all-data-releases/",
    "impc_legacy_root": "https://ftp.ebi.ac.uk/pub/databases/impc/",
    "uniprot_previous_releases": "https://ftp.ebi.ac.uk/pub/databases/uniprot/previous_releases/",
    "mygene_release_docs": "https://docs.mygene.info/en/latest/doc/release_changes.html",
    "gnomad_v211_constraint": "https://storage.googleapis.com/gnomad-public/release/2.1.1/constraint/gnomad.v2.1.1.lof_metrics.by_gene.txt.bgz",
    "hgnc_archive": "https://www.genenames.org/download/archive/",
    "reactome_archive": "https://reactome.org/download-data",
    "census_release_history": "https://chanzuckerberg.github.io/cellxgene-census/cellxgene_census_docsite_data_release_info.html",
}


def probe(item, cache, limit=262144):
    cache = cache.resolve()
    name, url = item
    row = {"name": name, "requested_url": url, "retrieved_utc": datetime.now(timezone.utc).isoformat()}
    request = urllib.request.Request(url, headers={"User-Agent": "UsherPipe-revision-archive-audit/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read(limit + 1)
            row.update(status=response.status, final_url=response.url, content_type=response.headers.get("Content-Type"),
                       content_length=response.headers.get("Content-Length"), last_modified=response.headers.get("Last-Modified"),
                       truncated=len(body) > limit, error=None)
    except Exception as error:
        row.update(status=getattr(error, "code", None), final_url=None, content_type=None, content_length=None,
                   last_modified=None, truncated=None, error=f"{type(error).__name__}: {error}")
        body = b""
    destination = cache / f"{name}.prefix"
    destination.write_bytes(body)
    row.update(saved_bytes=len(body), prefix_sha256=hashlib.sha256(body).hexdigest(), prefix_path=str(destination.relative_to(ROOT)))
    if row["content_type"] and ("html" in row["content_type"] or "text" in row["content_type"]):
        row["links"] = re.findall(r'href=["\']([^"\']+)', body.decode("utf-8", errors="replace"))
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "revision/major_revision_20261006/temporal_extension/archive_probes.json")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "data/cache/temporal-extension-20261006/probes")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Preserve the previous audit; choose a new output")
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda item: probe(item, args.cache_dir), PROBES.items()))
    args.output.write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps([{k: r[k] for k in ("name", "status", "saved_bytes", "truncated", "error")} for r in rows], indent=2))


if __name__ == "__main__":
    main()

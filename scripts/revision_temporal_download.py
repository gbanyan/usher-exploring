"""Download archival evidence into a separate cache; preserve provenance and failures."""
from concurrent.futures import ThreadPoolExecutor
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "revision/major_revision_20261006/temporal_extension"
CACHE = ROOT / "data/cache/temporal-extension-20261006/raw"
SOURCES = {
    "hgnc_20201001.tsv": "https://storage.googleapis.com/public-download-files/hgnc/archive/archive/quarterly/tsv/hgnc_complete_set_2020-10-01.txt",
    "go_20201208.gaf.gz": "https://go-data-product-release.s3.amazonaws.com/2020-12-08/annotations/goa_human.gaf.gz",
    "gnomad_v211.bgz": "https://storage.googleapis.com/gcp-public-data--gnomad/release/2.1.1/constraint/gnomad.v2.1.1.lof_metrics.by_gene.txt.bgz",
    "hpa_v20_subcellular.zip": "https://v20.proteinatlas.org/download/subcellular_location.tsv.zip",
    "hpa_v20_normal_tissue.zip": "https://v20.proteinatlas.org/download/normal_tissue.tsv.zip",
    "mgi_20200202.rpt": "https://web.archive.org/web/20200202074056id_/http://www.informatics.jax.org:80/downloads/reports/HMD_HumanPhenotype.rpt",
    "mgi_vocab_20190129.rpt": "https://web.archive.org/web/20190129050929id_/http://www.informatics.jax.org:80/downloads/reports/VOC_MammalianPhenotype.rpt",
    "gene2pubmed_20200629.gz": "https://web.archive.org/web/20200629060937id_/https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2pubmed.gz",
}


def download(item):
    name, url = item
    destination = CACHE / name
    row = {"name": name, "url": url, "retrieval_started_utc": datetime.now(timezone.utc).isoformat()}
    if destination.exists():
        row.update(bytes=destination.stat().st_size, sha256=hashlib.sha256(destination.read_bytes()).hexdigest(), path=str(destination.relative_to(ROOT)), error=None,
                   cached_existing=True, original_completion_utc_from_file_mtime=datetime.fromtimestamp(destination.stat().st_mtime, timezone.utc).isoformat(),
                   retrieval_finished_utc=None, response_metadata_available=False)
        return row
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "UsherPipe-revision-archive-audit/1.0"})
        with urllib.request.urlopen(request, timeout=45) as response, temporary.open("wb") as output:
            row.update(final_url=response.url, status=response.status, content_type=response.headers.get("Content-Type"), last_modified=response.headers.get("Last-Modified"))
            size = 0
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > 150 * 1024 * 1024:
                    raise ValueError("Archive exceeds the 150 MiB audit limit")
                output.write(block)
        temporary.rename(destination)
        row.update(bytes=destination.stat().st_size, sha256=hashlib.sha256(destination.read_bytes()).hexdigest(), path=str(destination.relative_to(ROOT)), error=None)
    except Exception as error:
        temporary.unlink(missing_ok=True)
        row.update(error=f"{type(error).__name__}: {error}")
    row["retrieval_finished_utc"] = datetime.now(timezone.utc).isoformat()
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preserve-completed-only", action="store_true", help="Inventory completed downloads after interruption; do not retry incomplete network transfers")
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    output = OUT / "download_manifest.json"
    if output.exists():
        raise FileExistsError(output)
    if args.preserve_completed_only:
        rows = []
        for name, url in SOURCES.items():
            if (CACHE / name).exists():
                rows.append(download((name, url)))
            else:
                partial = CACHE / (name + ".part")
                rows.append({"name": name, "url": url, "error": "Transfer interrupted after slow direct archive progress; complete-file validation not established", "partial_bytes": partial.stat().st_size if partial.exists() else 0, "path": None, "sha256": None})
    else:
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(download, SOURCES.items()))
    output.write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()

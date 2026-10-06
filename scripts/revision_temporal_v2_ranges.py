"""Resume bounded historical gene2pubmed ranges and validate the full archive."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache/temporal-validation-v2-20261006/raw"
URL = "https://web.archive.org/web/20200629060937id_/https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2pubmed.gz"
SIZE = 47311419
CHUNK = 1048576


def download(start):
    end = min(start + CHUNK, SIZE) - 1
    target = CACHE / "gene2pubmed_ranges" / f"{start:09d}-{end:09d}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size == end - start + 1:
        return target
    part = target.with_suffix(".part")
    for attempt in range(8):
        offset = part.stat().st_size if part.exists() else 0
        if offset == end - start + 1:
            part.rename(target)
            return target
        request = urllib.request.Request(URL, headers={
            "Range": f"bytes={start + offset}-{end}",
            "User-Agent": "UsherPipe-temporal-v2/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                expected = f"bytes {start + offset}-{end}/{SIZE}"
                if response.status != 206 or response.headers.get("Content-Range") != expected:
                    raise ValueError(f"Unexpected range response: {response.status}, {response.headers.get('Content-Range')}")
                with part.open("ab") as handle:
                    while block := response.read(16384):
                        handle.write(block)
            if part.stat().st_size != end - start + 1:
                raise ValueError("Incomplete range")
            part.rename(target)
            print(f"Complete range {start}-{end}", flush=True)
            return target
        except Exception as error:
            print(f"Range {start}-{end}, attempt {attempt + 1}: {error}", flush=True)
            time.sleep(min(5 * (attempt + 1), 30))
    raise RuntimeError(f"Range {start}-{end} remains incomplete")


if __name__ == "__main__":
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / "gene2pubmed_20200629.gz"
    manifest = ROOT / "revision/major_revision_20261006/temporal_validation_v2/gene2pubmed_acquisition.json"
    if target.exists() or manifest.exists():
        raise FileExistsError("Complete artifact or manifest already exists")
    with ThreadPoolExecutor(max_workers=3) as pool:
        parts = list(pool.map(download, range(0, SIZE, CHUNK)))
    temporary = target.with_suffix(".assembling")
    digest = hashlib.sha256()
    with temporary.open("wb") as handle:
        for part in parts:
            data = part.read_bytes()
            digest.update(data)
            handle.write(data)
    if temporary.stat().st_size != SIZE:
        raise ValueError("Assembled size mismatch")
    lines = 0
    with gzip.open(temporary, "rb") as handle:
        for line in handle:
            lines += 1
    temporary.rename(target)
    manifest.write_text(json.dumps({"url": URL, "snapshot": "2020-06-29T06:09:37Z",
        "source_last_modified": "2020-06-29T02:42:00Z", "bytes": SIZE,
        "sha256": digest.hexdigest(), "gzip_integrity_checked": True, "lines": lines,
        "path": str(target.relative_to(ROOT)), "complete": True,
        "finished_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
    print(f"Complete archive: {SIZE} bytes, {lines} lines", flush=True)

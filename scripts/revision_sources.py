"""Prepare hash-verified comparator snapshots without mutable live downloads."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import urllib.request

from revision_replay import BASE, digest


def prepare(destination, existing=None):
    if destination.exists():
        raise FileExistsError("Use a new task-owned source directory")
    destination.mkdir(parents=True)
    records = json.loads((BASE / "phase3_roster/manifest.json").read_text())["sources"]
    for name, record in records.items():
        target = destination / name
        source = (existing / name) if existing else None
        if source and source.exists():
            shutil.copy2(source, target)
        elif name in ("clingen.csv", "hgnc.tsv"):
            shutil.copy2(BASE / "reproducibility/phase3_live_snapshots" / name, target)
        else:
            with urllib.request.urlopen(record["url"], timeout=60) as response, target.open("wb") as handle:
                shutil.copyfileobj(response, handle)
        if digest(target) != record["sha256"]:
            raise ValueError(f"Frozen source checksum mismatch: {name}")
    (destination / "prepared.json").write_text(json.dumps({
        "prepared_utc": datetime.now(timezone.utc).isoformat(),
        "original_source_metadata": records,
        "status": "All four sources match the pre-outcome roster manifest",
    }, indent=2) + "\n")
    print("All comparator source snapshots verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--existing-source-dir", type=Path)
    args = parser.parse_args()
    prepare(args.output_dir, args.existing_source_dir)

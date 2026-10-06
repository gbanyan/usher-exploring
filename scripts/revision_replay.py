"""Export/import a frozen derived-input bundle and check immutable baselines."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006"
BUNDLE = BASE / "replay_inputs"
TABLES = ("scored_genes", "tissue_expression", "annotation_completeness", "literature_evidence")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table_bytes(con, name):
    con.execute(f'DESCRIBE "{name}"').fetchall()
    return con.execute(f'SELECT * FROM "{name}" ORDER BY gene_id').pl().write_csv(separator="\t", null_value="\\N").encode()


def protected_inputs(database=None):
    expected = json.loads((BASE / "input_manifest.json").read_text())["input_sha256"]
    checked = {}
    for relative, value in expected.items():
        path = ROOT / relative
        if relative == "manuscript/draft.md":
            path = BASE / "baseline/manuscript_draft.md"
        if relative == "data/pipeline.duckdb" and database is not None and Path(database).resolve() != path.resolve():
            validate_database(database)
            continue
        if digest(path) != value:
            raise ValueError(f"Immutable baseline changed: {path}")
        checked[str(path.relative_to(ROOT))] = value
    return checked


def validate_database(database, bundle=BUNDLE):
    manifest = json.loads((bundle / "manifest.json").read_text())
    with duckdb.connect(str(database), read_only=True) as con:
        for name, record in manifest["tables"].items():
            if digest(bundle / record["file"]) != record["sha256"]:
                raise ValueError(f"Derived bundle changed: {name}")
            if hashlib.sha256(table_bytes(con, name)).hexdigest() != record["sha256"]:
                raise ValueError(f"Replay database differs from frozen input: {name}")


def export(database, bundle):
    if bundle.exists():
        raise FileExistsError(bundle)
    bundle.mkdir(parents=True)
    records = {}
    with duckdb.connect(str(database), read_only=True) as con:
        for name in TABLES:
            schema = con.execute(f'DESCRIBE "{name}"').fetchall()
            payload = table_bytes(con, name)
            path = bundle / f"{name}.tsv"
            path.write_bytes(payload)
            records[name] = {"file": path.name, "sha256": digest(path), "bytes": len(payload),
                             "rows": con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0],
                             "schema": {row[0]: row[1] for row in schema}}
    manifest = {"kind": "derived numerical replay inputs, not raw-source regeneration", "exported_utc": datetime.now(timezone.utc).isoformat(),
                "source_database_sha256": digest(database), "null_token": "\\N", "order": "gene_id ascending", "tables": records,
                "limitations": "Annotation and animal evidence in scored_genes include restored historical donor-derived fields. This bundle reproduces numerical analyses; it does not reconstruct missing original raw inputs or retrieval dates."}
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: {"rows": v["rows"], "bytes": v["bytes"]} for k, v in records.items()}, indent=2))


def build(bundle, database):
    manifest = json.loads((bundle / "manifest.json").read_text())
    if database.exists():
        raise FileExistsError(database)
    database.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database)) as con:
        for name in TABLES:
            item = manifest["tables"][name]
            source = bundle / item["file"]
            if digest(source) != item["sha256"]:
                raise ValueError(f"Input checksum mismatch: {source}")
            con.execute(f'CREATE TABLE "{name}" AS SELECT * FROM read_csv(?, delim=\'\t\', header=true, nullstr=\'\\N\', columns=?)', [str(source), item["schema"]])
    validate_database(database, bundle)
    print(f"Frozen derived tables reproduced: {database}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("export", "build", "verify"))
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--bundle-dir", type=Path, default=BUNDLE)
    args = parser.parse_args()
    if args.mode == "export":
        export(args.database, args.bundle_dir)
    elif args.mode == "build":
        build(args.bundle_dir, args.database)
    else:
        validate_database(args.database, args.bundle_dir)


if __name__ == "__main__":
    main()

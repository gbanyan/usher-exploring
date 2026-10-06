"""Rebuild the August 2026 submission DB offline, without replacing live files.

Run from the repository with its installed Python environment. The destination
must not exist. Input hashes come from the August 14 integration-session audit.
Network access is blocked inside each pipeline stage. Annotation and animal
phenotypes reuse the exact historical donor; they are not raw-source reruns.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys


INPUT_HASHES = {
    "pipeline.duckdb": "1f5f606d0fb1d1ea3ca90386416c804ea70c809b8ea670c4a94e7659dac641d8",
    "annotation/Homo_sapiens.GRCh38.113.gtf.gz": "62f1709b40e083ce9d4cdc64a86b5ffec2c5d5371434bb7095c74dc89079c466",
    "MANE.GRCh38.v1.3.summary.txt.gz": "06637bc2d1f04f54635a8a09ff535ed44e5f7a2ced2d2a30a03f50b233379c35",
    "gnomad/constraint_metrics.tsv": "68d8abdb7fc48f570869b02dfaa74b9fecaece7fcc5f301ddca40ec1ce12da00",
    "expression/gtex_median_tpm.gct": "73215808fcbec246639aaf1f8eadba30ceb31dd74aa6074222a5c081ce3a9e72",
    "expression/hpa_normal_tissue.tsv": "1fa9111070f23290d29a32eaa30695689599b5231e7d0bc935b60a777ad3a1cc",
    "expression/cellxgene_expression_2025-11-08.parquet": "359ec5ebd9b6f162c1fbf308537ff5231629240ccdda4b20821101a6c5e6ac1a",
    "localization/hpa_subcellular_location.tsv": "65a7a197c11525b782767df4a23446c7c2ce8aefeb6b446cd6dc549cb6bf5841",
    "literature/gene2pubmed.gz": "80b830310b91ae1a86819ddfa8959c7627101e7d596af12714bbdbe97f72d78a",
    "literature/gene_info.gz": "9e225b3840456ee5458c7c5ffd96abb706a4b58422f35f3c32f7e0b3ca958731",
    "pubmed_context_sets.json": "d07949dfc9dae0d021fc09c4776cfcc1aa27340e31086ce92f68a47f4cd4def8",
}

STAGES = [
    ["setup", "--cache-only", "--mapping-db", "data/pipeline_source.duckdb"],
    ["evidence", "annotation", "--derived-cache", "data/pipeline_source.duckdb"],
    ["evidence", "animal-models", "--derived-cache", "data/pipeline_source.duckdb"],
    ["evidence", "gnomad", "--reprocess-cached"],
    ["evidence", "localization", "--reprocess-cached"],
    ["evidence", "literature", "--email", "offline@local.invalid", "--reprocess-cached"],
    ["evidence", "expression", "--reprocess-cached"],
    ["score", "--force"],
    ["report", "--force"],
    ["validate", "--force"],
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path, delimiter: str = "\t") -> dict[str, dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=delimiter))
    result = {row["gene_id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate gene IDs: {path}")
    return result


def equal_cell(left: str, right: str) -> bool:
    if left == right:
        return True
    try:
        return math.isclose(float(left), float(right), rel_tol=0, abs_tol=1e-12)
    except ValueError:
        return False


def verify(root: Path, destination: Path) -> dict:
    import duckdb

    expected = read_rows(root / "data/report/candidates.tsv")
    actual = read_rows(destination / "data/report/candidates.tsv")
    if expected.keys() != actual.keys():
        raise ValueError("Candidate gene membership differs from submission")
    mismatches = []
    for gene_id, row in expected.items():
        if row.keys() != actual[gene_id].keys():
            raise ValueError("Candidate columns differ from submission")
        for column, value in row.items():
            if not equal_cell(value, actual[gene_id][column]):
                mismatches.append((gene_id, column, value, actual[gene_id][column]))
    if mismatches:
        raise ValueError(f"{len(mismatches)} candidate cell mismatches: {mismatches[:10]}")

    con = duckdb.connect(str(destination / "data/pipeline.duckdb"), read_only=True)
    try:
        counts = con.execute(
            "SELECT COUNT(*), COUNT(DISTINCT gene_id), COUNT(DISTINCT gene_symbol), "
            "COUNT(composite_score) FROM scored_genes"
        ).fetchone()
        if counts != (20081, 20081, 20081, 20053):
            raise ValueError(f"Unexpected scored counts: {counts}")
        if con.execute("SELECT COUNT(*) FROM gene_universe").fetchone()[0] != 20116:
            raise ValueError("Unexpected frozen-universe size")
        # The tracked ablation table also covers excluded and NULL-score genes.
        baseline = read_rows(root / "data/report/ablation_comparison.csv", ",")
        scored = con.execute(
            "SELECT gene_id, gene_symbol, evidence_count, composite_score FROM scored_genes"
        ).fetchall()
        if {row[0] for row in scored} != baseline.keys():
            raise ValueError("Full scored membership differs from submission ablation")
        for gene_id, symbol, count, score in scored:
            row = baseline[gene_id]
            if (symbol != row["gene_symbol"] or str(count) != row["evidence_count"]
                    or not equal_cell("" if score is None else str(score), row["composite_null_preserve"])):
                raise ValueError(f"Full scored value differs: {gene_id}")
    finally:
        con.close()

    tiers = {tier: sum(row["confidence_tier"] == tier for row in actual.values())
             for tier in ("HIGH", "MEDIUM", "LOW")}
    if tiers != {"HIGH": 62, "MEDIUM": 9673, "LOW": 8652}:
        raise ValueError(f"Unexpected tiers: {tiers}")
    for name in ("derived_cache_annotation_mapping.tsv", "derived_cache_animal_model_mapping.tsv"):
        if (root / "data/report" / name).read_bytes() != (destination / "data/report" / name).read_bytes():
            raise ValueError(f"Derived-cache audit differs: {name}")
    # Group rows may be rendered in a different order, but every line must match.
    validation = root / "data/validation/validation_report.md"
    recovered_validation = destination / "data/validation/validation_report.md"
    if sorted(validation.read_text().splitlines()) != sorted(recovered_validation.read_text().splitlines()):
        raise ValueError("Internal validation report differs from submission")
    return {"candidate_rows": len(actual), "candidate_columns": len(next(iter(actual.values()))),
            "candidate_cell_mismatches": 0, "absolute_numeric_tolerance": 1e-12,
            "full_scored_rows": len(scored), "full_scored_mismatches": 0,
            "non_null_scores": counts[3], "universe_ids": 20116, "tiers": tiers,
            "derived_cache_audits_identical": True, "internal_validation_lines_identical": True,
            "database_sha256": sha256(destination / "data/pipeline.duckdb")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--donor-db", type=Path,
                        help="Historical donor (defaults to data/pipeline_source.duckdb if retained)")
    parser.add_argument("--verify-only", action="store_true",
                        help="Compare an existing recovery against submission artifacts")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    destination = args.destination.resolve()
    if args.verify_only:
        print(json.dumps(verify(root, destination), indent=2))
        return
    if destination.exists():
        raise FileExistsError(f"Recovery destination must be new: {destination}")
    donor = args.donor_db or root / "data/pipeline_source.duckdb"
    if args.donor_db is None and not donor.is_file():
        donor = root / "data/pipeline.duckdb"
    # Verify all historical sources before creating a partial recovery directory.
    for relative, expected in INPUT_HASHES.items():
        path = donor if relative == "pipeline.duckdb" else root / "data" / relative
        if sha256(path) != expected:
            raise ValueError(f"Historical input hash mismatch: {path}")
    print("Historical input hashes: 11/11 match", flush=True)
    destination.mkdir(parents=True)
    (destination / "config").mkdir()
    shutil.copy2(root / "config/default.yaml", destination / "config/default.yaml")
    for relative in INPUT_HASHES:
        target = destination / "data" / relative
        if relative == "pipeline.duckdb":
            target = target.with_name("pipeline_source.duckdb")
        target.parent.mkdir(parents=True, exist_ok=True)
        source = donor if relative == "pipeline.duckdb" else root / "data" / relative
        shutil.copy2(source, target)
    logs = destination / "logs"
    logs.mkdir()
    # Block outbound sockets even if an offline code path accidentally fetches.
    bootstrap = (
        "import socket,sys\n"
        "def deny(*args, **kwargs):\n"
        "    raise RuntimeError('Network access forbidden during submission recovery')\n"
        "socket.socket.connect = deny\n"
        "socket.socket.connect_ex = deny\n"
        "socket.create_connection = deny\n"
        "from usher_pipeline.cli.main import cli\n"
        "cli.main(args=sys.argv[1:])\n"
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(root / "src")
    environment["POLARS_MAX_THREADS"] = "2"
    for index, stage in enumerate(STAGES, 1):
        print(f"Stage {index}/{len(STAGES)}: {' '.join(stage)}", flush=True)
        with (logs / f"{index:02d}-{stage[0]}.log").open("w") as handle:
            subprocess.run(
                [sys.executable, "-c", bootstrap, "--config", "config/default.yaml", *stage],
                cwd=destination, env=environment, stdout=handle,
                stderr=subprocess.STDOUT, check=True,
            )
    result = verify(root, destination)
    result["historical_input_sha256"] = INPUT_HASHES
    result["commands"] = STAGES
    result["python"] = sys.version
    result["code_commit"] = subprocess.check_output(
        ["rtk", "proxy", "git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    import duckdb
    import polars
    result["software"] = {"duckdb": duckdb.__version__, "polars": polars.__version__}
    (destination / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in
                      ("commands", "historical_input_sha256", "python")}, indent=2))


if __name__ == "__main__":
    main()

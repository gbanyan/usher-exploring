"""Checksum manifest generation and verification for committed artifacts."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_MANIFEST_PATH = Path("data/report/checksum_manifest.json")
DEFAULT_MANIFEST_FILES = (
    Path("data/validation/validation_report.md"),
    Path("data/report/reproducibility.json"),
    Path("data/report/reproducibility.md"),
    Path("data/report/paper_figures/fig5_validation_controls.png"),
    Path("data/report/paper_figures/fig5_validation_controls.pdf"),
    Path("data/report/paper_figures/fig6_ablation.png"),
    Path("data/report/paper_figures/fig6_ablation.pdf"),
    Path("data/report/paper_figures/fig7_sensitivity_heatmap.png"),
    Path("data/report/paper_figures/fig7_sensitivity_heatmap.pdf"),
    Path("data/report/paper_figures/fig7_sensitivity_metrics.csv"),
    Path("data/report/candidates.tsv"),
    Path("data/report/candidates.parquet"),
    Path("data/report/candidates.provenance.yaml"),
    Path("data/report/supplementary/table_s1_merged_genes.tsv"),
    Path("data/report/supplementary/table_s2_excluded_genes.tsv"),
    Path("data/report/exploration/expression_shortlist_candidates.tsv"),
    Path("data/report/exploration/expression_shortlist_report.md"),
    Path("data/report/exploration/expression_shortlist_summary.tsv"),
    Path("data/report/exploration/gse135913_hair_cell_expression.parquet"),
    Path("data/report/exploration/gse135913_hair_cell_expression.tsv"),
    Path("data/report/exploration/gse135913_hair_cell_provenance.json"),
    Path("data/report/exploration/high_shortlist_old_vs_new.md"),
    Path("data/report/exploration/high_shortlist_old_vs_new.tsv"),
    Path("data/report/exploration/weight_logreg_report.txt"),
    Path("data/report/exploration/supplementary_analysis_audit.md"),
)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of an existing file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_checksum_manifest(
    root: Path = Path("."),
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    files: tuple[Path, ...] = DEFAULT_MANIFEST_FILES,
) -> Path:
    """Write a fail-closed SHA-256 manifest for the requested artifacts.

    Missing artifacts raise ``FileNotFoundError`` instead of creating a
    partial manifest.  Paths in the manifest are root-relative and the
    manifest itself is intentionally not included in its file list.
    """
    root = Path(root)
    manifest_path = Path(manifest_path)
    records = {}
    for relative_path in files:
        relative_path = Path(relative_path)
        artifact_path = root / relative_path
        if not artifact_path.is_file():
            raise FileNotFoundError(f"Cannot checksum missing artifact: {artifact_path}")
        records[str(relative_path)] = {
            "sha256": sha256_file(artifact_path),
            "size_bytes": artifact_path.stat().st_size,
        }

    payload = {
        "manifest_version": 1,
        "algorithm": "SHA-256",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": records,
    }
    output_path = root / manifest_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


def verify_checksum_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    root: Path = Path("."),
) -> dict:
    """Verify every manifest entry and return structured failures."""
    root = Path(root)
    manifest_path = Path(manifest_path)
    result = {"ok": False, "missing": [], "mismatched": [], "invalid": []}
    try:
        payload = json.loads((root / manifest_path).read_text(encoding="utf-8"))
        if payload.get("algorithm") != "SHA-256" or not isinstance(payload.get("files"), dict):
            result["invalid"].append("manifest schema or algorithm")
            return result
    except (OSError, json.JSONDecodeError):
        result["invalid"].append(str(manifest_path))
        return result

    for relative_path, record in payload["files"].items():
        artifact_path = root / relative_path
        if not artifact_path.is_file():
            result["missing"].append(relative_path)
            continue
        expected = record.get("sha256") if isinstance(record, dict) else None
        actual = sha256_file(artifact_path)
        if expected != actual:
            result["mismatched"].append({
                "path": relative_path,
                "expected": expected,
                "actual": actual,
            })

    result["ok"] = not any(result[key] for key in ("missing", "mismatched", "invalid"))
    return result

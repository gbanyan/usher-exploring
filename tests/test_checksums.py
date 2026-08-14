"""Tests for fail-closed evaluation artifact checksum manifests."""

import json
from pathlib import Path

from usher_pipeline.output.checksums import (
    DEFAULT_MANIFEST_FILES,
    create_checksum_manifest,
    verify_checksum_manifest,
)


def test_checksum_manifest_verifies_and_detects_changes(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("original", encoding="utf-8")
    manifest = tmp_path / "manifest.json"

    create_checksum_manifest(
        root=tmp_path,
        manifest_path=manifest.relative_to(tmp_path),
        files=(artifact.relative_to(tmp_path),),
    )
    assert verify_checksum_manifest(manifest.relative_to(tmp_path), tmp_path)["ok"]

    artifact.write_text("changed", encoding="utf-8")
    result = verify_checksum_manifest(manifest.relative_to(tmp_path), tmp_path)
    assert not result["ok"]
    assert result["mismatched"][0]["path"] == "artifact.txt"


def test_committed_checksum_manifest_covers_required_artifacts():
    result = verify_checksum_manifest()
    assert result["ok"], result

    payload = json.loads(Path("data/report/checksum_manifest.json").read_text())
    assert payload["algorithm"] == "SHA-256"
    assert set(payload["files"]) == {str(path) for path in DEFAULT_MANIFEST_FILES}

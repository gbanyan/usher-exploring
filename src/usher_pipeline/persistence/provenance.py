"""Provenance tracking for pipeline reproducibility."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class ProvenanceTracker:
    """
    Tracks provenance metadata for pipeline runs.

    Records pipeline version, data source versions, config hash,
    and processing steps for full reproducibility tracking.
    """

    def __init__(self, pipeline_version: str, config: "PipelineConfig"):
        """
        Initialize provenance tracker.

        Args:
            pipeline_version: Pipeline version string (e.g., "0.1.0")
            config: PipelineConfig instance
        """
        self.pipeline_version = pipeline_version
        self.config_hash = config.config_hash()
        self.data_source_versions = config.versions.model_dump()
        self.data_sources: list[dict] = []
        self.processing_steps = []
        self.rejected_sidecars: list[dict] = []
        self.created_at = datetime.now(timezone.utc)

    def record_data_source(
        self,
        source_name: str,
        *,
        source_url: Optional[str] = None,
        version: Optional[str] = None,
        retrieved_at: Optional[str | datetime] = None,
        checksum: Optional[str] = None,
        checksum_algorithm: Optional[str] = None,
        local_path: Optional[str] = None,
    ) -> None:
        """Record source metadata only when it is known for this run.

        Configuration versions are not retrieval receipts.  Callers may add
        an explicit source record after a download or cache lookup; omitted
        fields remain ``None`` and are counted as uncovered in the report.
        """
        if isinstance(retrieved_at, datetime):
            retrieved_at = retrieved_at.isoformat()

        self.data_sources.append({
            "source_name": source_name,
            "source_url": source_url,
            "version": version,
            "retrieved_at": retrieved_at,
            "checksum": checksum,
            "checksum_algorithm": checksum_algorithm,
            "local_path": local_path,
        })

    def provenance_coverage(self) -> dict:
        """Summarize metadata actually recorded, without inferring coverage."""
        total = len(self.data_sources)
        fields = {
            "source_name": sum(bool(item.get("source_name")) for item in self.data_sources),
            "source_url": sum(bool(item.get("source_url")) for item in self.data_sources),
            "version": sum(bool(item.get("version")) for item in self.data_sources),
            "retrieved_at": sum(bool(item.get("retrieved_at")) for item in self.data_sources),
            "checksum": sum(bool(item.get("checksum")) for item in self.data_sources),
        }
        if total > 0 and not self.rejected_sidecars and all(
            count == total for count in fields.values()
        ):
            status = "complete"
        else:
            # Zero records, missing fields, and rejected sidecars are all
            # incomplete provenance.  Never label any of those states
            # complete or imply that configuration versions are receipts.
            status = "incomplete"

        return {
            "status": status,
            "recorded_source_count": total,
            "covered_fields": fields,
            "rejected_sidecar_count": len(self.rejected_sidecars),
            "rejected_sidecars": self.rejected_sidecars.copy(),
            "note": (
                "Coverage counts only metadata explicitly recorded for this run; "
                "missing source, version, retrieval, or checksum fields are not inferred. "
                "Sidecars without an exact current-config hash are rejected."
            ),
        }

    def record_step(self, step_name: str, details: Optional[dict] = None) -> None:
        """
        Record a processing step.

        Args:
            step_name: Name of the processing step
            details: Optional dictionary of additional details
        """
        step = {
            "name": step_name,
            "step_name": step_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if details:
            step["details"] = details
        self.processing_steps.append(step)

        # A step may carry source metadata (for example, a download URL and
        # version).  Promote only those explicit fields into the source ledger;
        # ordinary processing steps do not imply retrieval or checksum coverage.
        if details:
            source_url = details.get("source_url") or details.get("url")
            source_name = details.get("source_name")
            source_version = details.get("source_version") or details.get("version")
            local_path = details.get("local_path") or details.get("output_path")
            if source_url or source_name:
                checksum = None
                checksum_algorithm = None
                if local_path:
                    candidate = Path(local_path)
                    if candidate.is_file():
                        digest = hashlib.sha256()
                        with candidate.open("rb") as handle:
                            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                                digest.update(chunk)
                        checksum = digest.hexdigest()
                        checksum_algorithm = "sha256"
                self.record_data_source(
                    source_name=source_name or step_name,
                    source_url=source_url,
                    version=source_version,
                    retrieved_at=details.get("retrieved_at"),
                    checksum=checksum or details.get("checksum"),
                    checksum_algorithm=checksum_algorithm or details.get("checksum_algorithm"),
                    local_path=local_path,
                )

    def get_steps(self) -> list[dict]:
        """
        Get all recorded processing steps.

        Returns:
            List of processing step dictionaries
        """
        return self.processing_steps

    def create_metadata(self) -> dict:
        """
        Create full provenance metadata dictionary.

        Returns:
            Dictionary with all provenance information
        """
        return {
            "pipeline_version": self.pipeline_version,
            "data_source_versions": self.data_source_versions,
            "data_sources": self.data_sources,
            "rejected_sidecars": self.rejected_sidecars,
            "provenance_coverage": self.provenance_coverage(),
            "config_hash": self.config_hash,
            "created_at": self.created_at.isoformat(),
            "processing_steps": self.processing_steps,
        }

    def save_sidecar(self, output_path: Path) -> None:
        """
        Save provenance metadata as a JSON sidecar file.

        Args:
            output_path: Path to the main output file.
                         Sidecar will be saved as {path}.provenance.json
        """
        sidecar_path = output_path.with_suffix(".provenance.json")
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        metadata = self.create_metadata()
        with open(sidecar_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

    def load_existing_sidecars(
        self,
        root: Path,
        *,
        exclude_paths: tuple[Path, ...] = (),
    ) -> list[Path]:
        """Merge existing per-layer provenance into this run's ledger.

        A report command starts after setup/evidence/scoring have already
        produced their sidecars.  Those records are the production source of
        provenance; a new tracker must not make the report look as if no
        sources were recorded.  This method imports explicit source records
        and processing steps only.  Configuration versions remain separate
        from retrieval receipts and are never promoted into source records.

        Older sidecars may predate the ``data_sources`` list.  In that case,
        source fields explicitly present in processing-step details are
        recovered, while missing URL/version/retrieval/checksum fields remain
        missing and therefore visible in coverage statistics.
        """
        root = Path(root)
        excluded = {Path(path).resolve() for path in exclude_paths}
        if not root.exists():
            return []

        loaded: list[Path] = []
        for sidecar_path in sorted(root.rglob("*.provenance.json")):
            resolved = sidecar_path.resolve()
            if resolved in excluded or any(
                path == resolved or path in resolved.parents for path in excluded
            ):
                continue

            try:
                metadata = self.load_sidecar(sidecar_path)
            except (OSError, ValueError, json.JSONDecodeError):
                self.rejected_sidecars.append({
                    "path": str(sidecar_path),
                    "reason": "invalid_json",
                    "observed_config_hash": None,
                })
                continue

            if not isinstance(metadata, dict):
                self.rejected_sidecars.append({
                    "path": str(sidecar_path),
                    "reason": "invalid_schema",
                    "observed_config_hash": None,
                })
                continue

            observed_config_hash = metadata.get("config_hash")
            if observed_config_hash is None:
                # Legacy/missing-hash sidecars are unverifiable and are never
                # merged.  Their existence is retained in the report so the
                # resulting coverage is visibly incomplete.
                self.rejected_sidecars.append({
                    "path": str(sidecar_path),
                    "reason": "missing_config_hash",
                    "observed_config_hash": None,
                })
                continue
            if observed_config_hash != self.config_hash:
                self.rejected_sidecars.append({
                    "path": str(sidecar_path),
                    "reason": "config_hash_mismatch",
                    "observed_config_hash": observed_config_hash,
                })
                continue

            source_records = metadata.get("data_sources")
            if source_records is not None and not isinstance(source_records, list):
                self.rejected_sidecars.append({
                    "path": str(sidecar_path),
                    "reason": "invalid_schema",
                    "observed_config_hash": observed_config_hash,
                })
                continue
            if source_records and any(not isinstance(record, dict) for record in source_records):
                self.rejected_sidecars.append({
                    "path": str(sidecar_path),
                    "reason": "invalid_schema",
                    "observed_config_hash": observed_config_hash,
                })
                continue

            steps = metadata.get("processing_steps")
            if steps is not None and not isinstance(steps, list):
                self.rejected_sidecars.append({
                    "path": str(sidecar_path),
                    "reason": "invalid_schema",
                    "observed_config_hash": observed_config_hash,
                })
                continue
            if steps and any(not isinstance(step, dict) for step in steps):
                self.rejected_sidecars.append({
                    "path": str(sidecar_path),
                    "reason": "invalid_schema",
                    "observed_config_hash": observed_config_hash,
                })
                continue

            loaded.append(sidecar_path)
            source_records = source_records or []
            for record in source_records:
                self.data_sources.append(dict(record))

            steps = steps or []
            for step in steps:
                merged_step = dict(step)
                self.processing_steps.append(merged_step)

                # Sidecars written before data_sources existed may still have
                # explicit source metadata in step details.  Recover it once.
                if source_records:
                    continue
                details = step.get("details") or {}
                if not isinstance(details, dict):
                    continue
                source_url = details.get("source_url") or details.get("url")
                source_name = details.get("source_name")
                source_version = details.get("source_version") or details.get("version")
                # A version/checksum without an explicit source identity is
                # not enough to create a source record.  Do not invent names,
                # URLs, retrieval timestamps, or checksums from a step label.
                if source_url or source_name:
                    local_path = details.get("local_path") or details.get("output_path")
                    if local_path and not Path(local_path).is_absolute():
                        local_path = str(sidecar_path.parent / local_path)
                    self.record_data_source(
                        source_name=source_name or step.get("step_name") or sidecar_path.stem,
                        source_url=source_url,
                        version=source_version,
                        retrieved_at=details.get("retrieved_at"),
                        checksum=details.get("checksum"),
                        checksum_algorithm=details.get("checksum_algorithm"),
                        local_path=local_path,
                    )

        return loaded

    def save_to_store(self, store: "PipelineStore") -> None:
        """
        Save provenance metadata to DuckDB store.

        Args:
            store: PipelineStore instance
        """
        metadata = self.create_metadata()

        # Create or replace _provenance table
        store.conn.execute("""
            CREATE TABLE IF NOT EXISTS _provenance (
                version VARCHAR,
                config_hash VARCHAR,
                created_at TIMESTAMP,
                steps_json VARCHAR
            )
        """)

        # Insert provenance record
        store.conn.execute("""
            INSERT INTO _provenance (version, config_hash, created_at, steps_json)
            VALUES (?, ?, ?, ?)
        """, [
            metadata["pipeline_version"],
            metadata["config_hash"],
            metadata["created_at"],
            json.dumps(metadata["processing_steps"]),
        ])

    @staticmethod
    def load_sidecar(sidecar_path: Path) -> dict:
        """
        Load provenance metadata from a sidecar file.

        Args:
            sidecar_path: Path to the .provenance.json file

        Returns:
            Provenance metadata dictionary
        """
        with open(sidecar_path) as f:
            return json.load(f)

    @classmethod
    def from_config(
        cls,
        config: "PipelineConfig",
        version: Optional[str] = None
    ) -> "ProvenanceTracker":
        """
        Create ProvenanceTracker from a PipelineConfig.

        Args:
            config: PipelineConfig instance
            version: Pipeline version string. If None, uses usher_pipeline.__version__

        Returns:
            ProvenanceTracker instance
        """
        if version is None:
            from usher_pipeline import __version__
            version = __version__

        return cls(version, config)

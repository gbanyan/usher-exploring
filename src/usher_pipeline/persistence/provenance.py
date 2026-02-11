"""Provenance tracking for pipeline reproducibility."""

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
        self.processing_steps = []
        self.created_at = datetime.now(timezone.utc)

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

"""Reproducibility report generation for pipeline runs."""

import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import polars as pl

from usher_pipeline.config.schema import PipelineConfig
from usher_pipeline.persistence.provenance import ProvenanceTracker


@dataclass
class FilteringStep:
    """Record of a data filtering/processing step."""

    step_name: str
    input_count: int
    output_count: int
    criteria: str


@dataclass
class ReproducibilityReport:
    """
    Reproducibility report for a pipeline run.

    Contains all information needed to reproduce the analysis:
    - Pipeline version and parameters
    - Data source versions
    - Software environment
    - Filtering steps with gene counts
    - Internal evaluation metrics
    - Tier statistics
    - Explicit source-metadata coverage
    """

    run_id: str
    timestamp: str
    pipeline_version: str
    parameters: dict
    data_versions: dict
    software_environment: dict
    filtering_steps: list[FilteringStep] = field(default_factory=list)
    # Keep this field in its historical position and retain its serialized
    # name.  Existing callers may construct the report positionally or pass
    # validation_metrics by keyword.
    validation_metrics: dict = field(default_factory=dict)
    tier_statistics: dict = field(default_factory=dict)
    config_hash: str = ""
    evaluation_metrics: dict = field(default_factory=dict)
    data_source_records: list[dict] = field(default_factory=list)
    provenance_coverage: dict = field(default_factory=dict)
    rejected_sidecars: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Bridge legacy validation naming and the neutral evaluation naming."""
        if not self.evaluation_metrics and self.validation_metrics:
            self.evaluation_metrics = dict(self.validation_metrics)
            if "validation_passed" in self.evaluation_metrics:
                self.evaluation_metrics["control_recovery_meets_reference"] = (
                    self.evaluation_metrics["validation_passed"]
                )
        elif self.evaluation_metrics and not self.validation_metrics:
            self.validation_metrics = dict(self.evaluation_metrics)
            if "control_recovery_meets_reference" in self.validation_metrics:
                self.validation_metrics["validation_passed"] = (
                    self.validation_metrics["control_recovery_meets_reference"]
                )

    def to_dict(self) -> dict:
        """
        Convert report to dictionary.

        Returns:
            Dictionary representation of the report
        """
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "pipeline_version": self.pipeline_version,
            "config_hash": self.config_hash,
            "parameters": self.parameters,
            "data_versions": self.data_versions,
            "data_source_records": self.data_source_records,
            "provenance_coverage": self.provenance_coverage,
            "rejected_sidecars": self.rejected_sidecars,
            "software_environment": self.software_environment,
            "filtering_steps": [
                {
                    "step_name": step.step_name,
                    "input_count": step.input_count,
                    "output_count": step.output_count,
                    "criteria": step.criteria,
                }
                for step in self.filtering_steps
            ],
            # Keep the historical serialized field for readers of existing
            # artifacts while exposing the transition field alongside it.
            "validation_metrics": self.validation_metrics,
            "evaluation_metrics": self.evaluation_metrics,
            "tier_statistics": self.tier_statistics,
        }

    def to_json(self, path: Path) -> Path:
        """
        Write report as JSON file.

        Args:
            path: Output path for JSON file

        Returns:
            Path to the written file
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

        return path

    def to_markdown(self, path: Path) -> Path:
        """
        Write report as human-readable Markdown file.

        Args:
            path: Output path for Markdown file

        Returns:
            Path to the written file
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Pipeline Reproducibility Report",
            "",
            f"**Run ID:** `{self.run_id}`",
            f"**Timestamp:** {self.timestamp}",
            f"**Pipeline Version:** {self.pipeline_version}",
            f"**Config SHA-256:** `{self.config_hash}`",
            "",
            "## Parameters",
            "",
            "**Scoring Weights:**",
            "",
        ]

        # Add scoring weights if available
        if "gnomad" in self.parameters:
            lines.extend([
                f"- gnomAD: {self.parameters['gnomad']:.2f}",
                f"- Expression: {self.parameters['expression']:.2f}",
                f"- Annotation: {self.parameters['annotation']:.2f}",
                f"- Localization: {self.parameters['localization']:.2f}",
                f"- Animal Model: {self.parameters['animal_model']:.2f}",
                f"- Literature: {self.parameters['literature']:.2f}",
                "",
            ])

        # Add data versions
        lines.extend([
            "## Data Versions",
            "",
        ])

        for key, value in self.data_versions.items():
            lines.append(f"- **{key}:** {value}")

        lines.append("")

        lines.extend([
            "## Data Source Metadata Coverage",
            "",
            f"**Coverage status:** {self.provenance_coverage.get('status', 'incomplete')}",
            f"**Recorded source records:** {self.provenance_coverage.get('recorded_source_count', 0)}",
            "",
            self.provenance_coverage.get(
                "note",
                "Coverage counts only metadata explicitly recorded for this run; missing fields are not inferred.",
            ),
            "",
        ])
        if self.provenance_coverage.get("status") != "complete":
            lines.extend([
                "**Source metadata coverage is incomplete; no missing fields are inferred.**",
                "",
            ])
        if self.rejected_sidecars:
            lines.extend([
                f"**Rejected provenance sidecars:** {len(self.rejected_sidecars)}",
                "",
                "| Sidecar | Reason | Observed config hash |",
                "|---------|--------|----------------------|",
            ])
            for rejected in self.rejected_sidecars:
                lines.append(
                    f"| {rejected.get('path') or 'N/A'} | "
                    f"{rejected.get('reason') or 'N/A'} | "
                    f"{rejected.get('observed_config_hash') or 'N/A'} |"
                )
            lines.append("")
        if self.data_source_records:
            lines.extend([
                "| Source | Version | URL | Retrieved at | Checksum |",
                "|--------|---------|-----|--------------|----------|",
            ])
            for record in self.data_source_records:
                lines.append(
                    f"| {record.get('source_name') or 'N/A'} | "
                    f"{record.get('version') or 'N/A'} | "
                    f"{record.get('source_url') or 'N/A'} | "
                    f"{record.get('retrieved_at') or 'N/A'} | "
                    f"{record.get('checksum') or 'N/A'} |"
                )
            lines.append("")
        else:
            lines.extend([
                "No per-source URL/version/retrieval/checksum records were accepted for this run.",
                "",
            ])

        # Add software environment
        lines.extend([
            "## Software Environment",
            "",
        ])

        for key, value in self.software_environment.items():
            lines.append(f"- **{key}:** {value}")

        lines.append("")

        # Add filtering steps if available
        if self.filtering_steps:
            lines.extend([
                "## Filtering Steps",
                "",
                "| Step | Input Count | Output Count | Criteria |",
                "|------|-------------|--------------|----------|",
            ])

            for step in self.filtering_steps:
                lines.append(
                    f"| {step.step_name} | {step.input_count} | "
                    f"{step.output_count} | {step.criteria} |"
                )

            lines.append("")

        # Add tier statistics
        lines.extend([
            "## Tier Statistics",
            "",
            f"- **Total Candidates:** {self.tier_statistics.get('total', 0)}",
            f"- **HIGH:** {self.tier_statistics.get('high', 0)}",
            f"- **MEDIUM:** {self.tier_statistics.get('medium', 0)}",
            f"- **LOW:** {self.tier_statistics.get('low', 0)}",
            "",
        ])

        # Add internal evaluation metrics if available
        if self.evaluation_metrics:
            lines.extend([
                "## Internal Evaluation Metrics",
                "",
            ])

            for key, value in self.evaluation_metrics.items():
                if isinstance(value, float):
                    lines.append(f"- **{key}:** {value:.3f}")
                else:
                    lines.append(f"- **{key}:** {value}")

            lines.append("")

        # Write to file
        with open(path, "w") as f:
            f.write("\n".join(lines))

        return path


def generate_reproducibility_report(
    config: PipelineConfig,
    tiered_df: pl.DataFrame,
    provenance: ProvenanceTracker,
    validation_result: dict | None = None,
) -> ReproducibilityReport:
    """
    Generate a reproducibility report with explicit provenance coverage.

    Args:
        config: Pipeline configuration
        tiered_df: Scored and tiered DataFrame
        provenance: Provenance tracker with processing steps
        validation_result: Optional validation results dictionary

    Returns:
        ReproducibilityReport instance

    Notes:
        - Extracts parameters from config (scoring weights, data versions)
        - Computes tier statistics from tiered_df
        - Builds filtering steps from provenance steps
        - Captures software versions (Python, polars, duckdb)
        - Generates unique run ID
    """
    # Generate run ID
    run_id = str(uuid.uuid4())

    # Get current timestamp
    timestamp = datetime.now(timezone.utc).isoformat()

    # Extract pipeline version and the exact configuration hash from provenance
    pipeline_version = provenance.pipeline_version
    config_hash = provenance.config_hash

    # Extract parameters from config
    parameters = config.scoring.model_dump()

    # Extract data versions from config
    data_versions = config.versions.model_dump()

    # Build software environment
    software_environment = {
        "python": sys.version.split()[0],
        "polars": pl.__version__,
        "duckdb": duckdb.__version__,
    }

    # Build filtering steps from provenance
    filtering_steps = []
    for step in provenance.get_steps():
        details = step.get("details", {})

        # Extract counts if available
        input_count = details.get("input_count", 0)
        output_count = details.get("output_count", 0)
        criteria = details.get("criteria", "")

        filtering_steps.append(
            FilteringStep(
                step_name=step["step_name"],
                input_count=input_count,
                output_count=output_count,
                criteria=criteria,
            )
        )

    # Compute tier statistics
    total = tiered_df.height
    high = 0
    medium = 0
    low = 0

    if "confidence_tier" in tiered_df.columns:
        tier_counts = tiered_df.group_by("confidence_tier").agg(
            pl.len().alias("count")
        )

        for row in tier_counts.to_dicts():
            tier = row["confidence_tier"]
            count = row["count"]

            if tier == "HIGH":
                high = count
            elif tier == "MEDIUM":
                medium = count
            elif tier == "LOW":
                low = count

    tier_statistics = {
        "total": total,
        "high": high,
        "medium": medium,
        "low": low,
    }

    # Extract internal evaluation metrics if provided.  Keep the input key
    # compatible with existing callers, but use neutral output language.
    validation_metrics = {}
    evaluation_metrics = {}
    if validation_result:
        validation_metrics = {
            "median_percentile": validation_result.get("median_percentile", 0.0),
            "top_quartile_fraction": validation_result.get(
                "top_quartile_fraction", 0.0
            ),
            "validation_passed": validation_result.get("validation_passed", False),
        }
        evaluation_metrics = {
            "median_percentile": validation_metrics["median_percentile"],
            "top_quartile_fraction": validation_metrics["top_quartile_fraction"],
            "control_recovery_meets_reference": validation_metrics["validation_passed"],
        }

    return ReproducibilityReport(
        run_id=run_id,
        timestamp=timestamp,
        pipeline_version=pipeline_version,
        parameters=parameters,
        data_versions=data_versions,
        software_environment=software_environment,
        filtering_steps=filtering_steps,
        validation_metrics=validation_metrics,
        tier_statistics=tier_statistics,
        config_hash=config_hash,
        evaluation_metrics=evaluation_metrics,
        data_source_records=provenance.data_sources.copy(),
        provenance_coverage=provenance.provenance_coverage(),
        rejected_sidecars=provenance.rejected_sidecars.copy(),
    )

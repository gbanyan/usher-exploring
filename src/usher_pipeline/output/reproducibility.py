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
    Comprehensive reproducibility report for a pipeline run.

    Contains all information needed to reproduce the analysis:
    - Pipeline version and parameters
    - Data source versions
    - Software environment
    - Filtering steps with gene counts
    - Validation metrics
    - Tier statistics
    """

    run_id: str
    timestamp: str
    pipeline_version: str
    parameters: dict
    data_versions: dict
    software_environment: dict
    filtering_steps: list[FilteringStep] = field(default_factory=list)
    validation_metrics: dict = field(default_factory=dict)
    tier_statistics: dict = field(default_factory=dict)

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
            "parameters": self.parameters,
            "data_versions": self.data_versions,
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
            "validation_metrics": self.validation_metrics,
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

        # Add validation metrics if available
        if self.validation_metrics:
            lines.extend([
                "## Validation Metrics",
                "",
            ])

            for key, value in self.validation_metrics.items():
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
    Generate comprehensive reproducibility report.

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

    # Extract pipeline version from provenance
    pipeline_version = provenance.pipeline_version

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

    # Extract validation metrics if provided
    validation_metrics = {}
    if validation_result:
        validation_metrics = {
            "median_percentile": validation_result.get("median_percentile", 0.0),
            "top_quartile_fraction": validation_result.get(
                "top_quartile_fraction", 0.0
            ),
            "validation_passed": validation_result.get("validation_passed", False),
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
    )

"""Pydantic models for pipeline configuration."""

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DataSourceVersions(BaseModel):
    """Version information for external data sources."""

    ensembl_release: int = Field(
        ...,
        ge=100,
        description="Ensembl release number (must be >= 100)",
    )
    gnomad_version: str = Field(
        default="v4.1",
        description="gnomAD version",
    )
    gtex_version: str = Field(
        default="v8",
        description="GTEx version",
    )
    hpa_version: str = Field(
        default="23.0",
        description="Human Protein Atlas version",
    )


class ScoringWeights(BaseModel):
    """Weights for multi-evidence scoring layers."""

    gnomad: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Weight for genetic constraint evidence",
    )
    expression: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Weight for tissue expression evidence",
    )
    annotation: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for annotation completeness",
    )
    localization: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for subcellular localization evidence",
    )
    animal_model: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for animal model phenotype evidence",
    )
    literature: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for literature evidence",
    )

    def validate_sum(self) -> None:
        """
        Validate that all scoring weights sum to 1.0.

        Raises:
            ValueError: If weights do not sum to 1.0 (within 1e-6 tolerance)

        Notes:
            - Tolerance of 1e-6 accounts for floating point precision
            - Should be called before using weights in scoring calculations
        """
        total = (
            self.gnomad
            + self.expression
            + self.annotation
            + self.localization
            + self.animal_model
            + self.literature
        )

        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total:.6f}")


class APIConfig(BaseModel):
    """Configuration for API clients."""

    rate_limit_per_second: int = Field(
        default=5,
        ge=1,
        description="Maximum API requests per second",
    )
    max_retries: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum retry attempts for failed requests",
    )
    cache_ttl_seconds: int = Field(
        default=86400,
        ge=0,
        description="Cache time-to-live in seconds (0 = infinite)",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Request timeout in seconds",
    )


class PipelineConfig(BaseModel):
    """Main pipeline configuration."""

    data_dir: Path = Field(
        ...,
        description="Directory for storing downloaded data",
    )
    cache_dir: Path = Field(
        ...,
        description="Directory for API response caching",
    )
    duckdb_path: Path = Field(
        ...,
        description="Path to DuckDB database file",
    )
    versions: DataSourceVersions = Field(
        ...,
        description="Data source version information",
    )
    api: APIConfig = Field(
        ...,
        description="API client configuration",
    )
    scoring: ScoringWeights = Field(
        ...,
        description="Scoring weights for evidence layers",
    )

    @field_validator("data_dir", "cache_dir")
    @classmethod
    def create_directory(cls, v: Path) -> Path:
        """Create directory if it doesn't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    def config_hash(self) -> str:
        """
        Compute SHA-256 hash of the configuration.

        Returns a deterministic hash based on all config values,
        useful for tracking config changes and cache invalidation.
        """
        # Convert config to dict and serialize deterministically
        config_dict = self.model_dump(mode="python")
        # Convert Path objects to strings for JSON serialization
        config_json = json.dumps(
            config_dict,
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(config_json.encode()).hexdigest()

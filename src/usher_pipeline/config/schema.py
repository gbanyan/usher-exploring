"""Pydantic models for pipeline configuration."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_ENSEMBL_GTF_FILENAME_RE = re.compile(
    r"^Homo_sapiens\.GRCh38\.(?P<release>[0-9]+)\.gtf\.gz$"
)
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class DataSourceVersions(BaseModel):
    """Version information for external data sources."""

    model_config = ConfigDict(validate_assignment=True)

    ensembl_release: int = Field(
        ...,
        ge=100,
        description="Ensembl release number (must be >= 100)",
    )
    ensembl_gene_source: str | None = Field(
        default=None,
        description="Path relative to data_dir for the frozen Ensembl gene GTF",
    )
    ensembl_gene_source_url: str | None = Field(
        default=None,
        description="Canonical URL for the frozen Ensembl gene GTF",
    )
    ensembl_gene_source_sha256: str = Field(
        default="",
        description="SHA-256 digest required for the frozen Ensembl gene GTF",
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
    mane_version: str = Field(
        default="1.3",
        description="MANE Select release version",
    )
    cellxgene_census_version: str = Field(
        default="2025-11-08",
        description="CELLxGENE Census named release/build date",
    )

    @model_validator(mode="after")
    def validate_ensembl_source_identity(self) -> "DataSourceVersions":
        """Reject partially specified or release-inconsistent frozen sources.

        Evidence-only configurations may omit the gene-universe source
        entirely.  Any configuration that specifies one must specify all
        identity fields; ``setup`` separately requires this complete block.
        """

        source_fields = (
            self.ensembl_gene_source,
            self.ensembl_gene_source_url,
            self.ensembl_gene_source_sha256,
        )
        present_fields = tuple(
            value is not None and str(value).strip() for value in source_fields
        )
        if not any(present_fields):
            return self
        if not all(present_fields):
            raise ValueError(
                "ensembl_gene_source, ensembl_gene_source_url, and "
                "ensembl_gene_source_sha256 must be provided together"
            )

        source_filename = Path(self.ensembl_gene_source).name
        filename_match = _ENSEMBL_GTF_FILENAME_RE.fullmatch(source_filename)
        if filename_match is None:
            raise ValueError(
                "ensembl_gene_source must use the release-pinned filename "
                "Homo_sapiens.GRCh38.<release>.gtf.gz"
            )
        if int(filename_match.group("release")) != self.ensembl_release:
            raise ValueError(
                "ensembl_gene_source filename release does not match "
                "ensembl_release"
            )
        if not _SHA256_RE.fullmatch(self.ensembl_gene_source_sha256):
            raise ValueError(
                "ensembl_gene_source_sha256 must be a 64-character hexadecimal digest"
            )

        parsed_url = urlparse(self.ensembl_gene_source_url)
        url_filename = Path(parsed_url.path).name
        release_match = re.search(r"/release-(\d+)/", parsed_url.path)
        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.netloc
            or url_filename != source_filename
            or release_match is None
            or int(release_match.group(1)) != self.ensembl_release
        ):
            raise ValueError(
                "ensembl_gene_source_url must identify the same release and "
                "filename as ensembl_gene_source"
            )
        return self


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

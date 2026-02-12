"""Data models for subcellular localization evidence."""

from typing import Optional
from pydantic import BaseModel, Field


# Table name for DuckDB storage
LOCALIZATION_TABLE_NAME = "subcellular_localization"

# HPA subcellular data URL (bulk download)
HPA_SUBCELLULAR_URL = "https://v23.proteinatlas.org/download/subcellular_location.tsv.zip"

# Compartment definitions for scoring
CILIA_COMPARTMENTS = [
    "Cilia",
    "Cilium",
    "Centrosome",
    "Centriole",
    "Basal body",
    "Microtubule organizing center",
]

CILIA_ADJACENT_COMPARTMENTS = [
    "Cytoskeleton",
    "Microtubules",
    "Cell Junctions",
    "Focal adhesion sites",
]


class LocalizationRecord(BaseModel):
    """Represents subcellular localization evidence for a gene.

    Integrates HPA subcellular location data with curated cilia/centrosome
    proteomics datasets to generate a cilia-proximity localization score.

    Distinguishes experimental evidence (Enhanced/Supported reliability,
    proteomics) from computational predictions (Approved/Uncertain reliability).
    """

    # Core identifiers
    gene_id: str = Field(description="Ensembl gene ID (ENSG...)")
    gene_symbol: str = Field(description="HGNC gene symbol")

    # HPA subcellular location data (NULL if gene not in HPA)
    hpa_main_location: Optional[str] = Field(
        default=None,
        description="Semicolon-separated list of HPA subcellular locations"
    )
    hpa_reliability: Optional[str] = Field(
        default=None,
        description="HPA reliability level: Enhanced, Supported, Approved, Uncertain"
    )
    hpa_evidence_type: Optional[str] = Field(
        default=None,
        description="HPA evidence classification: experimental or predicted"
    )

    # Proteomics dataset presence (False if not found, not NULL)
    in_cilia_proteomics: Optional[bool] = Field(
        default=None,
        description="Found in published cilium proteomics datasets (CiliaCarta, etc.)"
    )
    in_centrosome_proteomics: Optional[bool] = Field(
        default=None,
        description="Found in published centrosome proteomics datasets (Centrosome-DB, etc.)"
    )

    # Compartment flags (parsed from HPA locations)
    compartment_cilia: Optional[bool] = Field(
        default=None,
        description="Localized to cilia/cilium"
    )
    compartment_centrosome: Optional[bool] = Field(
        default=None,
        description="Localized to centrosome"
    )
    compartment_basal_body: Optional[bool] = Field(
        default=None,
        description="Localized to basal body"
    )
    compartment_transition_zone: Optional[bool] = Field(
        default=None,
        description="Localized to transition zone"
    )
    compartment_stereocilia: Optional[bool] = Field(
        default=None,
        description="Localized to stereocilia"
    )

    # Evidence classification
    evidence_type: str = Field(
        description="Evidence type: experimental, computational, both, or none"
    )

    # Scoring
    cilia_proximity_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Proximity to cilia-related compartments (0-1, NULL if no data)"
    )
    localization_score_normalized: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Normalized localization score weighted by evidence type (0-1, NULL if no data)"
    )

    class Config:
        """Pydantic config."""
        validate_assignment = True

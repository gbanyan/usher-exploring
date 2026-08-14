"""Data models for subcellular localization evidence."""

from typing import Optional
from pydantic import BaseModel, Field


# Table name for DuckDB storage
LOCALIZATION_TABLE_NAME = "subcellular_localization"

# HPA subcellular data URL (bulk download)
HPA_SUBCELLULAR_URL = "https://v23.proteinatlas.org/download/subcellular_location.tsv.zip"

# HPA reliability is a validation-strength attribute of antibody staining;
# it is not a modality label.  The lower weights retain the distinction
# between Approved/Uncertain and the more strongly validated categories.
HPA_EVIDENCE_MODALITY = "antibody_staining"
HPA_RELIABILITY_WEIGHTS = {
    "Enhanced": 1.0,
    "Supported": 1.0,
    "Approved": 0.6,
    "Uncertain": 0.6,
}

# The embedded lists are heterogeneous compendia. They are useful as curated
# membership evidence, but the repository does not contain source assay tables
# that would justify an experimental/MS attribution.
CURATED_COMPENDIUM_EVIDENCE_MODALITY = "curated_compendium"
CURATED_COMPENDIUM_EVIDENCE_WEIGHT = 0.5
CURATED_COMPENDIUM_FALLBACK_SCORE = 0.3

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

# Keep source-level signals separate from the aggregate localization score.
# The HIGH-tier cilia gate must distinguish direct cilia-related observations
# from generic adjacent cytoskeleton evidence.
DIRECT_CILIA_COMPARTMENT_COLUMNS = (
    "compartment_cilia",
    "compartment_centrosome",
    "compartment_basal_body",
    "compartment_transition_zone",
    "compartment_stereocilia",
)

CURATED_COMPENDIUM_COLUMNS = (
    "in_cilia_compendium",
    "in_centrosome_compendium",
)

# Names used by 614741c/d26348b checkpoints. They are migration inputs only,
# never current gate fields.
LEGACY_CURATED_PROTEOMICS_COLUMNS = (
    "in_cilia_proteomics",
    "in_centrosome_proteomics",
)

# Backwards-compatible public columns for fetch_cilia_proteomics(). Internal
# processing uses CURATED_COMPENDIUM_COLUMNS; the deprecated wrapper preserves
# the original output names for downstream callers.
CURATED_PROTEOMICS_COLUMNS = LEGACY_CURATED_PROTEOMICS_COLUMNS

LOCALIZATION_GATE_SOURCE_COLUMNS = (
    *DIRECT_CILIA_COMPARTMENT_COLUMNS,
    *CURATED_COMPENDIUM_COLUMNS,
)

# Increment when source-level fields required by downstream tiering change.
LOCALIZATION_CHECKPOINT_SCHEMA_VERSION = 3
LOCALIZATION_CHECKPOINT_VERSION_COLUMN = "localization_checkpoint_schema_version"

LOCALIZATION_CHECKPOINT_REQUIRED_COLUMNS = (
    "gene_id",
    "gene_symbol",
    "hpa_main_location",
    "hpa_reliability",
    "hpa_evidence_modality",
    "hpa_evidence_type",
    "hpa_reliability_weight",
    *LOCALIZATION_GATE_SOURCE_COLUMNS,
    "evidence_type",
    "cilia_proximity_score",
    "localization_score_normalized",
    LOCALIZATION_CHECKPOINT_VERSION_COLUMN,
)


class LocalizationRecord(BaseModel):
    """Represents subcellular localization evidence for a gene.

    Integrates HPA subcellular location data with embedded curated
    ciliary/centrosomal compendia to generate a cilia-proximity score.

    HPA reliability values describe antibody-staining reliability. Approved and
    Uncertain are not computational prediction classes.
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
    hpa_evidence_modality: Optional[str] = Field(
        default=None,
        description="HPA measurement modality: antibody_staining"
    )
    hpa_evidence_type: Optional[str] = Field(
        default=None,
        description="Legacy HPA modality classification: experimental"
    )
    hpa_reliability_weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Reliability weight applied to HPA antibody-staining evidence"
    )

    # Embedded compendium membership (False if not found, not NULL)
    in_cilia_compendium: Optional[bool] = Field(
        default=None,
        description=(
            "Member of the embedded curated ciliary compendium; source assay "
            "tables are unavailable and this is not a complete source dataset"
        )
    )
    in_centrosome_compendium: Optional[bool] = Field(
        default=None,
        description=(
            "Member of the embedded curated centrosomal compendium; source assay "
            "tables are unavailable and this is not a complete source dataset"
        )
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
        description=(
            "Evidence type: experimental, curated_compendium, mixed, or none"
        )
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
    localization_checkpoint_schema_version: int = Field(
        default=LOCALIZATION_CHECKPOINT_SCHEMA_VERSION,
        description="Explicit localization checkpoint schema version"
    )

    class Config:
        """Pydantic config."""
        validate_assignment = True

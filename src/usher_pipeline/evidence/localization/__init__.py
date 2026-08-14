"""Subcellular localization evidence layer.

Integrates HPA subcellular localization and embedded curated ciliary/centrosomal
compendia to score genes by proximity to cilia-related compartments.
"""

from usher_pipeline.evidence.localization.fetch import (
    fetch_hpa_subcellular,
    fetch_cilia_compendium,
    fetch_cilia_proteomics,
    CURATED_COMPENDIUM_PROVENANCE,
    CURATED_COMPENDIUM_RECORDS,
    CURATED_COMPENDIUM_SELECTION_VERSION,
    CURATED_COMPENDIUM_SELECTION_POLICY,
    CURATED_COMPENDIUM_EVIDENCE_MODALITY,
    COMPENDIUM_SYMBOL_ALIASES,
    normalize_compendium_gene_symbol,
    CURATED_PROTEOMICS_PROVENANCE,
    CURATED_PROTEOMICS_RECORDS,
    CURATED_PROTEOMICS_SELECTION_VERSION,
    CURATED_PROTEOMICS_SELECTION_POLICY,
    CURATED_PROTEOMICS_EVIDENCE_MODALITY,
    PROTEOMICS_SYMBOL_ALIASES,
    normalize_proteomics_gene_symbol,
)
from usher_pipeline.evidence.localization.transform import (
    classify_evidence_type,
    score_localization,
    process_localization_evidence,
)
from usher_pipeline.evidence.localization.load import (
    load_to_duckdb,
    LegacyLocalizationCheckpointError,
    migrate_legacy_localization_checkpoint,
)
from usher_pipeline.evidence.localization.models import (
    LocalizationRecord,
    LOCALIZATION_TABLE_NAME,
    HPA_EVIDENCE_MODALITY,
    HPA_RELIABILITY_WEIGHTS,
    LOCALIZATION_CHECKPOINT_SCHEMA_VERSION,
    LOCALIZATION_CHECKPOINT_REQUIRED_COLUMNS,
    LOCALIZATION_CHECKPOINT_VERSION_COLUMN,
    CURATED_COMPENDIUM_COLUMNS,
    CURATED_PROTEOMICS_COLUMNS,
    LEGACY_CURATED_PROTEOMICS_COLUMNS,
    CURATED_COMPENDIUM_EVIDENCE_WEIGHT,
    CURATED_COMPENDIUM_FALLBACK_SCORE,
)

__all__ = [
    "fetch_hpa_subcellular",
    "fetch_cilia_compendium",
    "fetch_cilia_proteomics",
    "CURATED_COMPENDIUM_PROVENANCE",
    "CURATED_COMPENDIUM_RECORDS",
    "CURATED_COMPENDIUM_SELECTION_VERSION",
    "CURATED_COMPENDIUM_SELECTION_POLICY",
    "CURATED_COMPENDIUM_EVIDENCE_MODALITY",
    "COMPENDIUM_SYMBOL_ALIASES",
    "normalize_compendium_gene_symbol",
    "CURATED_PROTEOMICS_PROVENANCE",
    "CURATED_PROTEOMICS_RECORDS",
    "CURATED_PROTEOMICS_SELECTION_VERSION",
    "CURATED_PROTEOMICS_SELECTION_POLICY",
    "CURATED_PROTEOMICS_EVIDENCE_MODALITY",
    "PROTEOMICS_SYMBOL_ALIASES",
    "normalize_proteomics_gene_symbol",
    "classify_evidence_type",
    "score_localization",
    "process_localization_evidence",
    "load_to_duckdb",
    "LegacyLocalizationCheckpointError",
    "migrate_legacy_localization_checkpoint",
    "LocalizationRecord",
    "LOCALIZATION_TABLE_NAME",
    "HPA_EVIDENCE_MODALITY",
    "HPA_RELIABILITY_WEIGHTS",
    "LOCALIZATION_CHECKPOINT_SCHEMA_VERSION",
    "LOCALIZATION_CHECKPOINT_REQUIRED_COLUMNS",
    "LOCALIZATION_CHECKPOINT_VERSION_COLUMN",
    "CURATED_COMPENDIUM_COLUMNS",
    "CURATED_PROTEOMICS_COLUMNS",
    "LEGACY_CURATED_PROTEOMICS_COLUMNS",
    "CURATED_COMPENDIUM_EVIDENCE_WEIGHT",
    "CURATED_COMPENDIUM_FALLBACK_SCORE",
]

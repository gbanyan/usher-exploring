"""Subcellular localization evidence layer.

Integrates HPA subcellular localization and published cilia/centrosome
proteomics data to score genes by proximity to cilia-related compartments.
"""

from usher_pipeline.evidence.localization.fetch import (
    fetch_hpa_subcellular,
    fetch_cilia_proteomics,
)
from usher_pipeline.evidence.localization.transform import (
    classify_evidence_type,
    score_localization,
    process_localization_evidence,
)
from usher_pipeline.evidence.localization.load import (
    load_to_duckdb,
)
from usher_pipeline.evidence.localization.models import (
    LocalizationRecord,
    LOCALIZATION_TABLE_NAME,
)

__all__ = [
    "fetch_hpa_subcellular",
    "fetch_cilia_proteomics",
    "classify_evidence_type",
    "score_localization",
    "process_localization_evidence",
    "load_to_duckdb",
    "LocalizationRecord",
    "LOCALIZATION_TABLE_NAME",
]

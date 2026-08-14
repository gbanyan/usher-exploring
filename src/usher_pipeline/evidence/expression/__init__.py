"""Tissue expression evidence layer for Usher-relevant tissues.

This module retrieves expression data from:
- HPA (Human Protein Atlas): Tissue-level RNA/protein expression
- GTEx: Tissue-level RNA expression across diverse samples
- CellxGene: Single-cell RNA-seq data for specific cell types

Target tissues/cell types:
- Retina, photoreceptor cells (retinal rod, retinal cone)
- Inner ear, hair cells (cochlea, vestibular)
- Cilia-rich tissues (cerebellum, testis, fallopian tube)

Expression enrichment in these tissues is evidence for potential cilia/Usher involvement.
"""

from usher_pipeline.evidence.expression.fetch import (
    fetch_hpa_expression,
    fetch_gtex_expression,
    fetch_cellxgene_expression,
    expression_source_metadata,
    validate_expression_cache,
    cellxgene_cache_identity,
    cellxgene_cache_path,
    cellxgene_legacy_cache_path,
)
from usher_pipeline.evidence.expression.transform import (
    calculate_tau_specificity,
    compute_expression_score,
    process_expression_evidence,
)
from usher_pipeline.evidence.expression.load import (
    load_to_duckdb,
    query_tissue_enriched,
)
from usher_pipeline.evidence.expression.models import (
    ExpressionRecord,
    EXPRESSION_TABLE_NAME,
    EXPRESSION_SCHEMA_VERSION,
    HPA_LEVEL_ORDINAL,
    HPA_LEVEL_SEMANTICS,
    EXPRESSION_CONTRAST_SCOPE,
    EXPRESSION_CONTRAST_DESCRIPTION,
    RESTRICTED_TAU_COLUMN,
    RESTRICTED_ENRICHMENT_COLUMN,
    TARGET_TISSUES,
)

__all__ = [
    "fetch_hpa_expression",
    "fetch_gtex_expression",
    "fetch_cellxgene_expression",
    "expression_source_metadata",
    "validate_expression_cache",
    "cellxgene_cache_identity",
    "cellxgene_cache_path",
    "cellxgene_legacy_cache_path",
    "calculate_tau_specificity",
    "compute_expression_score",
    "process_expression_evidence",
    "load_to_duckdb",
    "query_tissue_enriched",
    "ExpressionRecord",
    "EXPRESSION_TABLE_NAME",
    "EXPRESSION_SCHEMA_VERSION",
    "HPA_LEVEL_ORDINAL",
    "HPA_LEVEL_SEMANTICS",
    "EXPRESSION_CONTRAST_SCOPE",
    "EXPRESSION_CONTRAST_DESCRIPTION",
    "RESTRICTED_TAU_COLUMN",
    "RESTRICTED_ENRICHMENT_COLUMN",
    "TARGET_TISSUES",
]

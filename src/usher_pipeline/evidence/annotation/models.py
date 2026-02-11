"""Data models for gene annotation completeness evidence."""

from pydantic import BaseModel

# Table name for DuckDB storage
ANNOTATION_TABLE_NAME = "annotation_completeness"


class AnnotationRecord(BaseModel):
    """Gene annotation completeness metrics for a single gene.

    Attributes:
        gene_id: Ensembl gene ID (e.g., ENSG00000...)
        gene_symbol: HGNC gene symbol
        go_term_count: Total number of GO terms (all ontologies) - NULL if no data
        go_biological_process_count: Number of GO Biological Process terms - NULL if no data
        go_molecular_function_count: Number of GO Molecular Function terms - NULL if no data
        go_cellular_component_count: Number of GO Cellular Component terms - NULL if no data
        uniprot_annotation_score: UniProt annotation score 1-5 - NULL if no mapping or score
        has_pathway_membership: Present in any KEGG/Reactome pathway - NULL if no data
        annotation_tier: Classification: "well_annotated", "partially_annotated", "poorly_annotated"
        annotation_score_normalized: Composite annotation score 0-1 (higher = better annotated) - NULL if all inputs NULL

    CRITICAL: NULL values represent missing data and are preserved as None.
    Do NOT convert NULL to 0 - "unknown annotation" is semantically different from "zero annotation".
    Conservative approach: NULL GO counts treated as zero for tier classification (assume unannotated).
    """

    gene_id: str
    gene_symbol: str
    go_term_count: int | None = None
    go_biological_process_count: int | None = None
    go_molecular_function_count: int | None = None
    go_cellular_component_count: int | None = None
    uniprot_annotation_score: int | None = None
    has_pathway_membership: bool | None = None
    annotation_tier: str = "poorly_annotated"
    annotation_score_normalized: float | None = None

"""Data models for tissue expression evidence."""

from pydantic import BaseModel

# HPA normal tissue data download URL (bulk TSV, more efficient than per-gene API)
HPA_NORMAL_TISSUE_URL = (
    "https://v23.proteinatlas.org/download/normal_tissue.tsv.zip"
)

# GTEx v10 median gene expression bulk data
GTEX_MEDIAN_EXPRESSION_URL = (
    "https://storage.googleapis.com/adult-gtex/bulk-gex/v8/rna-seq/"
    "GTEx_Analysis_2017-06-05_v8_RNASeQCv1.1.9_gene_median_tpm.gct.gz"
)

# Table name in DuckDB
EXPRESSION_TABLE_NAME = "tissue_expression"

# Target tissues for Usher/cilia relevance
# Maps our standardized tissue keys to API-specific identifiers
TARGET_TISSUES = {
    # Retina-related
    "retina": {
        "hpa": "retina",
        "gtex": "Eye - Retina",  # Note: Not available in all GTEx versions
        "cellxgene_tissue": ["retina", "eye"],
    },
    # Inner ear-related (primarily from scRNA-seq, not in HPA/GTEx bulk)
    "inner_ear": {
        "hpa": None,  # Not available in HPA bulk tissue data
        "gtex": None,  # Not available in GTEx
        "cellxgene_tissue": ["inner ear", "cochlea", "vestibular system"],
    },
    # Cilia-rich tissues
    "cerebellum": {
        "hpa": "cerebellum",
        "gtex": "Brain - Cerebellum",
        "cellxgene_tissue": ["cerebellum"],
    },
    "testis": {
        "hpa": "testis",
        "gtex": "Testis",
        "cellxgene_tissue": ["testis"],
    },
    "fallopian_tube": {
        "hpa": "fallopian tube",
        "gtex": "Fallopian Tube",  # May not be available in all GTEx versions
        "cellxgene_tissue": ["fallopian tube"],
    },
}

# Target cell types for scRNA-seq (CellxGene)
TARGET_CELL_TYPES = [
    "photoreceptor cell",
    "retinal rod cell",
    "retinal cone cell",
    "hair cell",  # Inner ear mechanoreceptor
    "cochlear hair cell",
    "vestibular hair cell",
]


class ExpressionRecord(BaseModel):
    """Tissue expression evidence for a single gene.

    Attributes:
        gene_id: Ensembl gene ID (e.g., ENSG00000...)
        gene_symbol: HGNC gene symbol
        hpa_retina_tpm: HPA retina TPM expression (NULL if not in HPA)
        hpa_cerebellum_tpm: HPA cerebellum TPM (proxy for cilia-rich tissue)
        hpa_testis_tpm: HPA testis TPM (cilia-rich)
        hpa_fallopian_tube_tpm: HPA fallopian tube TPM (ciliated epithelium)
        gtex_retina_tpm: GTEx "Eye - Retina" median TPM (NULL if tissue unavailable)
        gtex_cerebellum_tpm: GTEx "Brain - Cerebellum" median TPM
        gtex_testis_tpm: GTEx "Testis" median TPM
        gtex_fallopian_tube_tpm: GTEx "Fallopian Tube" median TPM (often NULL)
        cellxgene_photoreceptor_expr: Mean expression in photoreceptor cells (scRNA-seq)
        cellxgene_hair_cell_expr: Mean expression in hair cells (scRNA-seq)
        tau_specificity: Tau index (0=ubiquitous, 1=tissue-specific) across all tissues
        usher_tissue_enrichment: Enrichment in Usher-relevant tissues vs global expression
        expression_score_normalized: Composite expression score (0-1 range)

    CRITICAL: NULL values represent missing/unavailable data and are preserved as None.
    Inner ear data is primarily from CellxGene (not HPA/GTEx bulk).
    """

    gene_id: str
    gene_symbol: str
    hpa_retina_tpm: float | None = None
    hpa_cerebellum_tpm: float | None = None
    hpa_testis_tpm: float | None = None
    hpa_fallopian_tube_tpm: float | None = None
    gtex_retina_tpm: float | None = None
    gtex_cerebellum_tpm: float | None = None
    gtex_testis_tpm: float | None = None
    gtex_fallopian_tube_tpm: float | None = None
    cellxgene_photoreceptor_expr: float | None = None
    cellxgene_hair_cell_expr: float | None = None
    tau_specificity: float | None = None
    usher_tissue_enrichment: float | None = None
    expression_score_normalized: float | None = None

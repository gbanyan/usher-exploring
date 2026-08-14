"""Data models for tissue expression evidence."""

from pydantic import BaseModel


# The HPA normal-tissue download used by this pipeline can contain either
# quantitative transcript nTPM values or categorical protein levels.  These
# are different measurements and must never share a TPM column name.
EXPRESSION_SCHEMA_VERSION = "3.0"
EXPRESSION_CONTRAST_SCOPE = "restricted_panel"
EXPRESSION_CONTRAST_DESCRIPTION = (
    "Contrasts are computed only within the configured Usher-relevant tissue "
    "panel (target: retina/cerebellum; background: testis/fallopian tube) "
    "for each source. They are not whole-body expression or global-tissue "
    "enrichment estimates."
)
HPA_LEVEL_ORDINAL = {
    "Not detected": 0,
    "Low": 1,
    "Medium": 2,
    "High": 3,
}
HPA_ORDINAL_LABEL = {value: key for key, value in HPA_LEVEL_ORDINAL.items()}
HPA_LEVEL_SEMANTICS = (
    "Ordered categorical HPA protein level: 0=Not detected, 1=Low, "
    "2=Medium, 3=High. Codes are ordinal only; intervals are not quantitative. "
    "Not detected is an observed zero-evidence category, not missing data."
)
HPA_RELIABILITY_POLICY = {
    "accepted": ("Approved", "Enhanced", "Supported"),
    "excluded": ("Uncertain",),
    "aggregation": "filter excluded reliability rows before cell-type aggregation",
}

HPA_TISSUE_KEYS = ("retina", "cerebellum", "testis", "fallopian_tube")
GTEX_TISSUE_KEYS = ("retina", "cerebellum", "testis", "fallopian_tube")

HPA_PROTEIN_LEVEL_COLUMNS = tuple(
    f"hpa_{tissue}_protein_level" for tissue in HPA_TISSUE_KEYS
)
HPA_PROTEIN_LEVEL_LABEL_COLUMNS = tuple(
    f"hpa_{tissue}_protein_level_label" for tissue in HPA_TISSUE_KEYS
)
HPA_NTPM_COLUMNS = tuple(f"hpa_{tissue}_ntpm" for tissue in HPA_TISSUE_KEYS)
GTEX_TPM_COLUMNS = tuple(f"gtex_{tissue}_tpm" for tissue in GTEX_TISSUE_KEYS)
CELLXGENE_COLUMNS = (
    "cellxgene_photoreceptor_expr",
    "cellxgene_hair_cell_expr",
)
RETINA_EVIDENCE_COLUMNS = (
    "hpa_retina_protein_level",
    "hpa_retina_ntpm",
    "gtex_retina_tpm",
    "cellxgene_photoreceptor_expr",
)
LEGACY_HPA_TPM_COLUMNS = tuple(f"hpa_{tissue}_tpm" for tissue in HPA_TISSUE_KEYS)
LEGACY_EXPRESSION_CONTRACT_COLUMNS = (  # migration detection only
    "tau_specificity",
    "usher_tissue_enrichment",
)

# GTEx v8 has no "Eye - Retina" column.  This is a structural source
# limitation, not a gene-level missing observation.
GTEX_STRUCTURAL_ABSENCE = {
    "retina": {
        "raw_column": "Eye - Retina",
        "reason": "GTEx v8 median TPM GCT does not contain an Eye - Retina column",
    }
}

RESTRICTED_TAU_COLUMN = "tau_restricted_panel_specificity"
RESTRICTED_ENRICHMENT_COLUMN = "usher_restricted_panel_contrast"

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
        hpa_*_protein_level: HPA ordered categorical protein level code
            (0=Not detected, 1=Low, 2=Medium, 3=High), when only the
            categorical HPA source is available.  These values are ordinal,
            not TPM and not interval-scaled measurements.
        hpa_*_protein_level_label: Original HPA categorical label.
        hpa_*_ntpm: HPA normalized transcript TPM, when a quantitative HPA
            transcript source is available.
        gtex_retina_tpm: GTEx "Eye - Retina" median TPM (NULL if tissue unavailable)
        gtex_cerebellum_tpm: GTEx "Brain - Cerebellum" median TPM
        gtex_testis_tpm: GTEx "Testis" median TPM
        gtex_fallopian_tube_tpm: GTEx "Fallopian Tube" median TPM (often NULL)
        cellxgene_photoreceptor_expr: Mean expression in photoreceptor cells (scRNA-seq)
        cellxgene_hair_cell_expr: Mean expression in hair cells (scRNA-seq)
        tau_restricted_panel_specificity: Tau index within the available
            quantitative restricted panel (0=uniform among expressed tissues,
            1=concentrated among expressed tissues).
        usher_restricted_panel_contrast: Source-specific target/background
            contrast within the restricted panel, not global enrichment.
        expression_score_normalized: Composite expression score (0-1 range)

    CRITICAL: NULL values represent missing/unavailable data and are preserved as None.
    Inner ear data is primarily from CellxGene (not HPA/GTEx bulk).
    """

    gene_id: str
    gene_symbol: str
    hpa_retina_protein_level: int | None = None
    hpa_cerebellum_protein_level: int | None = None
    hpa_testis_protein_level: int | None = None
    hpa_fallopian_tube_protein_level: int | None = None
    hpa_retina_protein_level_label: str | None = None
    hpa_cerebellum_protein_level_label: str | None = None
    hpa_testis_protein_level_label: str | None = None
    hpa_fallopian_tube_protein_level_label: str | None = None
    hpa_retina_ntpm: float | None = None
    hpa_cerebellum_ntpm: float | None = None
    hpa_testis_ntpm: float | None = None
    hpa_fallopian_tube_ntpm: float | None = None
    gtex_retina_tpm: float | None = None
    gtex_cerebellum_tpm: float | None = None
    gtex_testis_tpm: float | None = None
    gtex_fallopian_tube_tpm: float | None = None
    cellxgene_photoreceptor_expr: float | None = None
    cellxgene_hair_cell_expr: float | None = None
    tau_restricted_panel_specificity: float | None = None
    usher_restricted_panel_contrast: float | None = None
    expression_score_normalized: float | None = None

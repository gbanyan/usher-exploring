"""Data models for protein sequence and structure features."""

from pydantic import BaseModel

# DuckDB table name for protein features
PROTEIN_TABLE_NAME = "protein_features"

# Cilia-associated domain keywords for motif detection
# These are structural patterns found in known cilia proteins
# Pattern matching does NOT presuppose cilia involvement - it flags features
# associated with cilia biology for further investigation
CILIA_DOMAIN_KEYWORDS = [
    "IFT",
    "intraflagellar",
    "BBSome",
    "ciliary",
    "cilia",
    "basal body",
    "centrosome",
    "transition zone",
    "axoneme",
]

# Scaffold and adaptor domain types commonly found in Usher proteins
# These domains mediate protein-protein interactions and are enriched in
# cilia-associated proteins
SCAFFOLD_DOMAIN_TYPES = [
    "PDZ",
    "SH3",
    "Ankyrin",
    "WD40",
    "Coiled coil",
    "SAM",
    "FERM",
    "Harmonin",
]


class ProteinFeatureRecord(BaseModel):
    """Protein features for a single gene.

    Attributes:
        gene_id: Ensembl gene ID (e.g., ENSG00000...)
        gene_symbol: HGNC gene symbol
        uniprot_id: UniProt accession (NULL if no mapping)
        protein_length: Amino acid length (NULL if no UniProt entry)
        domain_count: Total number of annotated domains (NULL if no data)
        coiled_coil: Has coiled-coil region (NULL if no data)
        coiled_coil_count: Number of coiled-coil regions (NULL if no data)
        transmembrane_count: Number of transmembrane regions (NULL if no data)
        scaffold_adaptor_domain: Has PDZ, SH3, ankyrin, WD40, or similar scaffold domain (NULL if no data)
        has_cilia_domain: Has IFT, BBSome, ciliary targeting, or transition zone domain (NULL if no data)
        has_sensory_domain: Has stereocilia, photoreceptor, or sensory-associated domain (NULL if no data)
        protein_score_normalized: Composite protein feature score 0-1 (NULL if no UniProt entry)

    CRITICAL: NULL values represent missing data and are preserved as None.
    Do NOT convert NULL to 0.0 - "unknown" is semantically different from "no domain".
    """

    gene_id: str
    gene_symbol: str
    uniprot_id: str | None = None
    protein_length: int | None = None
    domain_count: int | None = None
    coiled_coil: bool | None = None
    coiled_coil_count: int | None = None
    transmembrane_count: int | None = None
    scaffold_adaptor_domain: bool | None = None
    has_cilia_domain: bool | None = None
    has_sensory_domain: bool | None = None
    protein_score_normalized: float | None = None

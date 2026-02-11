"""Protein sequence and structure features evidence layer.

Extracts protein features from UniProt and InterPro:
- Protein length, domain composition, domain count
- Coiled-coil regions, transmembrane domains, scaffold/adaptor domains
- Cilia-associated motifs detected via domain keyword matching
- Normalized composite protein score (0-1)

Evidence follows fetch -> transform -> load pattern with checkpoint-restart.
"""

from usher_pipeline.evidence.protein.models import (
    ProteinFeatureRecord,
    PROTEIN_TABLE_NAME,
    CILIA_DOMAIN_KEYWORDS,
    SCAFFOLD_DOMAIN_TYPES,
)
from usher_pipeline.evidence.protein.fetch import (
    fetch_uniprot_features,
    fetch_interpro_domains,
)
from usher_pipeline.evidence.protein.transform import (
    extract_protein_features,
    detect_cilia_motifs,
    normalize_protein_features,
    process_protein_evidence,
)
from usher_pipeline.evidence.protein.load import (
    load_to_duckdb,
    query_cilia_candidates,
)

__all__ = [
    "ProteinFeatureRecord",
    "PROTEIN_TABLE_NAME",
    "CILIA_DOMAIN_KEYWORDS",
    "SCAFFOLD_DOMAIN_TYPES",
    "fetch_uniprot_features",
    "fetch_interpro_domains",
    "extract_protein_features",
    "detect_cilia_motifs",
    "normalize_protein_features",
    "process_protein_evidence",
    "load_to_duckdb",
    "query_cilia_candidates",
]

"""Gene ID mapping module.

Provides gene universe definition, batch ID mapping via mygene,
and validation gates for quality control.
"""

from usher_pipeline.gene_mapping.mapper import (
    GeneMapper,
    MappingResult,
    MappingReport,
)
from usher_pipeline.gene_mapping.universe import (
    EnsemblGeneSource,
    fetch_protein_coding_genes,
    load_frozen_ensembl_gene_source,
    sha256_file,
    GeneUniverse,
)
from usher_pipeline.gene_mapping.validator import (
    MappingValidator,
    ValidationResult,
    validate_gene_universe,
)
from usher_pipeline.gene_mapping.mane_select import (
    fetch_mane_select,
    parse_mane_select,
    load_mane_select,
)

__all__ = [
    "GeneMapper",
    "MappingResult",
    "MappingReport",
    "fetch_protein_coding_genes",
    "load_frozen_ensembl_gene_source",
    "EnsemblGeneSource",
    "sha256_file",
    "GeneUniverse",
    "MappingValidator",
    "ValidationResult",
    "validate_gene_universe",
    "fetch_mane_select",
    "parse_mane_select",
    "load_mane_select",
]

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
    fetch_protein_coding_genes,
    GeneUniverse,
)
from usher_pipeline.gene_mapping.validator import (
    MappingValidator,
    ValidationResult,
    validate_gene_universe,
)

__all__ = [
    "GeneMapper",
    "MappingResult",
    "MappingReport",
    "fetch_protein_coding_genes",
    "GeneUniverse",
    "MappingValidator",
    "ValidationResult",
    "validate_gene_universe",
]

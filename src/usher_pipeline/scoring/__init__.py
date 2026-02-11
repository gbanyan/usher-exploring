"""Multi-evidence scoring and known gene compilation for cilia/Usher syndrome genes."""

from usher_pipeline.scoring.known_genes import (
    OMIM_USHER_GENES,
    SYSCILIA_SCGS_V2_CORE,
    compile_known_genes,
    load_known_genes_to_duckdb,
)
from usher_pipeline.scoring.integration import (
    join_evidence_layers,
    compute_composite_scores,
    persist_scored_genes,
)

__all__ = [
    "OMIM_USHER_GENES",
    "SYSCILIA_SCGS_V2_CORE",
    "compile_known_genes",
    "load_known_genes_to_duckdb",
    "join_evidence_layers",
    "compute_composite_scores",
    "persist_scored_genes",
]

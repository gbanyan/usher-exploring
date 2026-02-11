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
from usher_pipeline.scoring.quality_control import (
    run_qc_checks,
)
from usher_pipeline.scoring.validation import (
    validate_known_gene_ranking,
    generate_validation_report,
    compute_recall_at_k,
    validate_positive_controls_extended,
)
from usher_pipeline.scoring.negative_controls import (
    HOUSEKEEPING_GENES_CORE,
    compile_housekeeping_genes,
    validate_negative_controls,
    generate_negative_control_report,
)

__all__ = [
    "OMIM_USHER_GENES",
    "SYSCILIA_SCGS_V2_CORE",
    "compile_known_genes",
    "load_known_genes_to_duckdb",
    "join_evidence_layers",
    "compute_composite_scores",
    "persist_scored_genes",
    "run_qc_checks",
    "validate_known_gene_ranking",
    "generate_validation_report",
    "compute_recall_at_k",
    "validate_positive_controls_extended",
    "HOUSEKEEPING_GENES_CORE",
    "compile_housekeeping_genes",
    "validate_negative_controls",
    "generate_negative_control_report",
]

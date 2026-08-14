"""Output generation: tiered candidate classification and dual-format file writing."""

from usher_pipeline.output.evidence_summary import EVIDENCE_LAYERS, add_evidence_summary
from usher_pipeline.output.reproducibility import (
    ReproducibilityReport,
    generate_reproducibility_report,
)
from usher_pipeline.output.tiers import (
    HAS_CILIA_SIGNAL_SEMANTICS_VERSION,
    TIER_THRESHOLDS,
    assign_tiers,
)
from usher_pipeline.output.visualizations import (
    generate_all_plots,
    plot_layer_contributions,
    plot_score_distribution,
    plot_tier_breakdown,
)
from usher_pipeline.output.writers import write_candidate_output
from usher_pipeline.output.checksums import (
    DEFAULT_MANIFEST_FILES,
    DEFAULT_MANIFEST_PATH,
    create_checksum_manifest,
    verify_checksum_manifest,
)

__all__ = [
    "assign_tiers",
    "TIER_THRESHOLDS",
    "HAS_CILIA_SIGNAL_SEMANTICS_VERSION",
    "add_evidence_summary",
    "EVIDENCE_LAYERS",
    "write_candidate_output",
    "generate_reproducibility_report",
    "ReproducibilityReport",
    "generate_all_plots",
    "plot_score_distribution",
    "plot_layer_contributions",
    "plot_tier_breakdown",
    "DEFAULT_MANIFEST_FILES",
    "DEFAULT_MANIFEST_PATH",
    "create_checksum_manifest",
    "verify_checksum_manifest",
]

"""Output generation: tiered candidate classification and dual-format file writing."""

from usher_pipeline.output.evidence_summary import EVIDENCE_LAYERS, add_evidence_summary
from usher_pipeline.output.reproducibility import (
    ReproducibilityReport,
    generate_reproducibility_report,
)
from usher_pipeline.output.tiers import TIER_THRESHOLDS, assign_tiers
from usher_pipeline.output.visualizations import (
    generate_all_plots,
    plot_layer_contributions,
    plot_score_distribution,
    plot_tier_breakdown,
)
from usher_pipeline.output.writers import write_candidate_output

__all__ = [
    "assign_tiers",
    "TIER_THRESHOLDS",
    "add_evidence_summary",
    "EVIDENCE_LAYERS",
    "write_candidate_output",
    "generate_reproducibility_report",
    "ReproducibilityReport",
    "generate_all_plots",
    "plot_score_distribution",
    "plot_layer_contributions",
    "plot_tier_breakdown",
]

"""Output generation: tiered candidate classification and dual-format file writing."""

from usher_pipeline.output.evidence_summary import EVIDENCE_LAYERS, add_evidence_summary
from usher_pipeline.output.tiers import TIER_THRESHOLDS, assign_tiers

# writers.py exports will be added in Task 2

__all__ = [
    "assign_tiers",
    "TIER_THRESHOLDS",
    "add_evidence_summary",
    "EVIDENCE_LAYERS",
    # "write_candidate_output" will be added in Task 2
]

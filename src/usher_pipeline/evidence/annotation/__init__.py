"""Gene annotation completeness evidence layer."""

from usher_pipeline.evidence.annotation.models import AnnotationRecord, ANNOTATION_TABLE_NAME
from usher_pipeline.evidence.annotation.fetch import (
    fetch_go_annotations,
    fetch_uniprot_scores,
)
from usher_pipeline.evidence.annotation.transform import (
    classify_annotation_tier,
    normalize_annotation_score,
    process_annotation_evidence,
)

__all__ = [
    "AnnotationRecord",
    "ANNOTATION_TABLE_NAME",
    "fetch_go_annotations",
    "fetch_uniprot_scores",
    "classify_annotation_tier",
    "normalize_annotation_score",
    "process_annotation_evidence",
]

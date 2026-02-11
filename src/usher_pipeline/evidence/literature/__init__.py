"""Literature Evidence Layer (LITE): PubMed-based evidence for cilia/sensory gene involvement.

This module fetches PubMed citations for genes in various contexts (cilia, sensory,
cytoskeleton, cell polarity), classifies evidence quality, and computes quality-weighted
scores that mitigate well-studied gene bias.

Key exports:
- fetch: query_pubmed_gene, fetch_literature_evidence
- transform: classify_evidence_tier, compute_literature_score, process_literature_evidence
- load: load_to_duckdb
- models: LiteratureRecord, SEARCH_CONTEXTS, LITERATURE_TABLE_NAME
"""

from usher_pipeline.evidence.literature.models import (
    LiteratureRecord,
    LITERATURE_TABLE_NAME,
    SEARCH_CONTEXTS,
    DIRECT_EVIDENCE_TERMS,
)
from usher_pipeline.evidence.literature.fetch import (
    query_pubmed_gene,
    fetch_literature_evidence,
)
from usher_pipeline.evidence.literature.transform import (
    classify_evidence_tier,
    compute_literature_score,
    process_literature_evidence,
)
from usher_pipeline.evidence.literature.load import (
    load_to_duckdb,
    query_literature_supported,
)

__all__ = [
    # Models
    "LiteratureRecord",
    "LITERATURE_TABLE_NAME",
    "SEARCH_CONTEXTS",
    "DIRECT_EVIDENCE_TERMS",
    # Fetch
    "query_pubmed_gene",
    "fetch_literature_evidence",
    # Transform
    "classify_evidence_tier",
    "compute_literature_score",
    "process_literature_evidence",
    # Load
    "load_to_duckdb",
    "query_literature_supported",
]

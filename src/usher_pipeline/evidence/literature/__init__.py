"""Literature Evidence Layer: PubMed-based evidence for cilia/sensory gene involvement.

Uses bulk gene2pubmed + batch MeSH queries (~5-10 min) instead of per-gene
E-utilities (~46 hours). Classifies evidence quality and computes quality-weighted
scores that mitigate well-studied gene bias.

Key exports:
- fetch: download_bulk_files, fetch_literature_evidence, parse_gene2pubmed, etc.
- transform: classify_evidence_tier, compute_literature_score, process_literature_evidence
- load: load_to_duckdb
- models: LiteratureRecord, SEARCH_CONTEXTS, LITERATURE_TABLE_NAME
"""

from usher_pipeline.evidence.literature.models import (
    LiteratureRecord,
    LITERATURE_TABLE_NAME,
    SEARCH_CONTEXTS,
)
from usher_pipeline.evidence.literature.fetch import (
    fetch_literature_evidence,
    download_bulk_files,
    parse_gene2pubmed,
    parse_gene_info,
    build_gene_pmid_map,
    count_context_intersections,
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
    # Fetch (bulk)
    "fetch_literature_evidence",
    "download_bulk_files",
    "parse_gene2pubmed",
    "parse_gene_info",
    "build_gene_pmid_map",
    "count_context_intersections",
    # Transform
    "classify_evidence_tier",
    "compute_literature_score",
    "process_literature_evidence",
    # Load
    "load_to_duckdb",
    "query_literature_supported",
]

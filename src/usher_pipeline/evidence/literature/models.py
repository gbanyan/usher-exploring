"""Data models for literature evidence layer."""

from typing import Optional

from pydantic import BaseModel, Field


LITERATURE_TABLE_NAME = "literature_evidence"

# Context-specific PubMed search terms
# These are combined with gene symbols to find relevant publications
SEARCH_CONTEXTS = {
    "cilia": "(cilia OR cilium OR ciliary OR flagellum OR intraflagellar)",
    "sensory": "(retina OR cochlea OR hair cell OR photoreceptor OR vestibular OR hearing OR usher syndrome)",
    "cytoskeleton": "(cytoskeleton OR actin OR microtubule OR motor protein)",
    "cell_polarity": "(cell polarity OR planar cell polarity OR apicobasal OR tight junction)",
}

# Terms indicating direct experimental evidence
# Publications with these terms carry higher confidence than incidental mentions
DIRECT_EVIDENCE_TERMS = "(knockout OR knockdown OR mutation OR CRISPR OR siRNA OR morpholino OR null allele)"

# Evidence tier classification
# Higher tiers indicate stronger evidence quality
EVIDENCE_TIERS = [
    "direct_experimental",  # Knockout/mutation + cilia/sensory context
    "functional_mention",   # Mentioned in cilia/sensory context, not just incidental
    "hts_hit",              # High-throughput screen hit + cilia/sensory context
    "incidental",           # Mentioned in literature but no specific cilia/sensory context
    "none",                 # No PubMed publications found
]


class LiteratureRecord(BaseModel):
    """Literature evidence record for a single gene.

    Captures PubMed publication counts across different contexts and evidence quality.
    NULL values indicate failed queries (API errors), not zero publications.
    """

    gene_id: str = Field(description="Ensembl gene ID (e.g., ENSG00000012048)")
    gene_symbol: str = Field(description="HGNC gene symbol (e.g., BRCA1)")

    # Publication counts by context
    total_pubmed_count: Optional[int] = Field(
        None,
        description="Total PubMed publications mentioning this gene (any context). NULL if query failed.",
    )
    cilia_context_count: Optional[int] = Field(
        None,
        description="Publications mentioning gene in cilia-related context",
    )
    sensory_context_count: Optional[int] = Field(
        None,
        description="Publications mentioning gene in sensory (retina/cochlea/hearing) context",
    )
    cytoskeleton_context_count: Optional[int] = Field(
        None,
        description="Publications mentioning gene in cytoskeleton context",
    )
    cell_polarity_context_count: Optional[int] = Field(
        None,
        description="Publications mentioning gene in cell polarity context",
    )

    # Evidence quality indicators
    direct_experimental_count: Optional[int] = Field(
        None,
        description="Publications with knockout/mutation/knockdown evidence",
    )
    hts_screen_count: Optional[int] = Field(
        None,
        description="Publications from high-throughput screens (proteomics/transcriptomics)",
    )

    # Derived classification
    evidence_tier: str = Field(
        description="Evidence quality tier: direct_experimental, functional_mention, hts_hit, incidental, none"
    )
    literature_score_normalized: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Quality-weighted literature score [0-1], normalized to mitigate well-studied gene bias. NULL if total_pubmed_count is NULL.",
    )

    class Config:
        """Pydantic config."""
        frozen = False  # Allow mutation for score computation

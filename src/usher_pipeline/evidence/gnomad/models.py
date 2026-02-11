"""Data models for gnomAD constraint metrics."""

from pydantic import BaseModel

# gnomAD v4.1 constraint metrics download URL
GNOMAD_CONSTRAINT_URL = (
    "https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/constraint/"
    "gnomad.v4.1.constraint_metrics.tsv"
)

# Column name mapping for different gnomAD versions
# v2.1.1 uses: gene, transcript, pLI, oe_lof_upper (LOEUF), mean_proportion_covered_bases
# v4.x uses: gene, transcript, mane_select, lof.pLI, lof.oe_ci.upper, mean_proportion_covered
COLUMN_VARIANTS = {
    "gene_id": ["gene", "gene_id"],
    "gene_symbol": ["gene_symbol", "gene"],
    "transcript": ["transcript", "canonical_transcript", "mane_select"],
    "pli": ["pLI", "lof.pLI", "pli"],
    "loeuf": ["oe_lof_upper", "lof.oe_ci.upper", "oe_lof", "loeuf"],
    "loeuf_upper": ["oe_lof_upper_ci", "lof.oe_ci.upper", "oe_lof_upper"],
    "mean_depth": ["mean_coverage", "mean_depth", "mean_cov"],
    "cds_covered_pct": [
        "mean_proportion_covered_bases",
        "mean_proportion_covered",
        "cds_covered_pct",
    ],
}


class ConstraintRecord(BaseModel):
    """gnomAD constraint metrics for a single gene.

    Attributes:
        gene_id: Ensembl gene ID (e.g., ENSG00000...)
        gene_symbol: HGNC gene symbol
        transcript: Canonical transcript ID
        pli: Probability of being loss-of-function intolerant (NULL if no estimate)
        loeuf: Loss-of-function observed/expected upper bound fraction (NULL if no estimate)
        loeuf_upper: Upper bound of LOEUF confidence interval
        mean_depth: Mean exome sequencing depth across CDS
        cds_covered_pct: Fraction of CDS bases with adequate coverage (0.0-1.0)
        quality_flag: Data quality indicator - "measured", "incomplete_coverage", or "no_data"
        loeuf_normalized: Normalized LOEUF score (0-1, inverted: higher = more constrained)

    CRITICAL: NULL values represent missing data and are preserved as None.
    Do NOT convert NULL to 0.0 - "unknown" is semantically different from "zero constraint".
    """

    gene_id: str
    gene_symbol: str
    transcript: str
    pli: float | None = None
    loeuf: float | None = None
    loeuf_upper: float | None = None
    mean_depth: float | None = None
    cds_covered_pct: float | None = None
    quality_flag: str = "no_data"
    loeuf_normalized: float | None = None

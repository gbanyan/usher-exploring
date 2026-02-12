"""Validation gates for gene mapping quality control.

Provides validation for mapping results and gene universe data quality.
Enforces configurable success rate thresholds and produces actionable reports.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from usher_pipeline.gene_mapping.mapper import MappingReport

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check.

    Attributes:
        passed: Whether validation passed
        messages: List of validation messages (warnings, errors)
        hgnc_rate: HGNC mapping success rate (0-1)
        uniprot_rate: UniProt mapping success rate (0-1)
    """
    passed: bool
    messages: list[str] = field(default_factory=list)
    hgnc_rate: float = 0.0
    uniprot_rate: float = 0.0


class MappingValidator:
    """Validator for gene ID mapping results.

    Enforces configurable success rate thresholds and produces validation reports.
    """

    def __init__(
        self,
        min_success_rate: float = 0.90,
        warn_threshold: float = 0.95
    ):
        """Initialize mapping validator.

        Args:
            min_success_rate: Minimum HGNC mapping success rate to pass (default: 0.90)
            warn_threshold: Success rate below this triggers warning (default: 0.95)
        """
        self.min_success_rate = min_success_rate
        self.warn_threshold = warn_threshold
        logger.info(
            f"Initialized MappingValidator: min_rate={min_success_rate}, "
            f"warn_threshold={warn_threshold}"
        )

    def validate(self, report: MappingReport) -> ValidationResult:
        """Validate gene mapping results.

        Checks if HGNC mapping success rate meets minimum threshold.
        Issues warning if rate is below warn_threshold but above min_success_rate.

        Args:
            report: MappingReport from batch mapping operation

        Returns:
            ValidationResult with pass/fail status and messages
        """
        messages: list[str] = []
        hgnc_rate = report.success_rate_hgnc
        uniprot_rate = report.success_rate_uniprot

        # Check HGNC success rate
        if hgnc_rate < self.min_success_rate:
            messages.append(
                f"FAILED: HGNC mapping success rate {hgnc_rate:.1%} is below "
                f"minimum threshold {self.min_success_rate:.1%}"
            )
            messages.append(
                f"Mapped {report.mapped_hgnc}/{report.total_genes} genes to HGNC symbols"
            )
            messages.append(
                f"Unmapped genes: {len(report.unmapped_ids)} "
                f"(first 10: {report.unmapped_ids[:10]})"
            )
            passed = False
        elif hgnc_rate < self.warn_threshold:
            messages.append(
                f"WARNING: HGNC mapping success rate {hgnc_rate:.1%} is below "
                f"warning threshold {self.warn_threshold:.1%}"
            )
            messages.append(
                f"Mapped {report.mapped_hgnc}/{report.total_genes} genes to HGNC symbols"
            )
            messages.append(
                f"Consider reviewing {len(report.unmapped_ids)} unmapped genes"
            )
            passed = True
        else:
            messages.append(
                f"PASSED: HGNC mapping success rate {hgnc_rate:.1%} "
                f"({report.mapped_hgnc}/{report.total_genes} genes)"
            )
            passed = True

        # Report UniProt stats (informational only, not used for pass/fail)
        messages.append(
            f"UniProt mapping: {uniprot_rate:.1%} "
            f"({report.mapped_uniprot}/{report.total_genes} genes)"
        )

        logger.info(
            f"Validation result: {'PASSED' if passed else 'FAILED'} "
            f"(HGNC: {hgnc_rate:.1%}, UniProt: {uniprot_rate:.1%})"
        )

        return ValidationResult(
            passed=passed,
            messages=messages,
            hgnc_rate=hgnc_rate,
            uniprot_rate=uniprot_rate,
        )

    def save_unmapped_report(
        self,
        report: MappingReport,
        output_path: Path
    ) -> None:
        """Save list of unmapped genes to file for manual review.

        Args:
            report: MappingReport containing unmapped gene IDs
            output_path: Path to output file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        unmapped_count = len(report.unmapped_ids)

        with output_path.open('w') as f:
            f.write(f"# Unmapped Gene IDs\n")
            f.write(f"# Generated: {timestamp}\n")
            f.write(f"# Total unmapped: {unmapped_count}\n")
            f.write(f"# Success rate: {report.success_rate_hgnc:.1%}\n")
            f.write(f"#\n")
            for gene_id in report.unmapped_ids:
                f.write(f"{gene_id}\n")

        logger.info(
            f"Saved {unmapped_count} unmapped gene IDs to {output_path}"
        )


def validate_gene_universe(genes: list[str]) -> ValidationResult:
    """Validate gene universe data quality.

    Checks:
    - Gene count is in expected range (19,000-22,000)
    - All gene IDs start with ENSG (Ensembl format)
    - No duplicate gene IDs

    Args:
        genes: List of gene IDs to validate

    Returns:
        ValidationResult with validation status and messages
    """
    messages: list[str] = []
    passed = True

    gene_count = len(genes)
    MIN_GENES = 19000
    MAX_GENES = 23000

    # Check gene count
    if gene_count < MIN_GENES:
        messages.append(
            f"FAILED: Gene count {gene_count} is below minimum {MIN_GENES}. "
            "This may indicate missing data or incomplete query."
        )
        passed = False
    elif gene_count > MAX_GENES:
        messages.append(
            f"FAILED: Gene count {gene_count} exceeds maximum {MAX_GENES}. "
            "This may indicate pseudogene contamination or inclusion of non-coding genes."
        )
        passed = False
    else:
        messages.append(
            f"Gene count {gene_count} is within expected range ({MIN_GENES}-{MAX_GENES})"
        )

    # Check all IDs start with ENSG
    non_ensg = [g for g in genes if not g.startswith('ENSG')]
    if non_ensg:
        messages.append(
            f"FAILED: Found {len(non_ensg)} gene IDs not in ENSG format "
            f"(examples: {non_ensg[:5]})"
        )
        passed = False
    else:
        messages.append("All gene IDs are in ENSG format")

    # Check for duplicates
    unique_genes = set(genes)
    if len(unique_genes) < gene_count:
        duplicates = gene_count - len(unique_genes)
        messages.append(
            f"FAILED: Found {duplicates} duplicate gene IDs"
        )
        passed = False
    else:
        messages.append("No duplicate gene IDs found")

    logger.info(
        f"Gene universe validation: {'PASSED' if passed else 'FAILED'} "
        f"({gene_count} genes)"
    )

    return ValidationResult(
        passed=passed,
        messages=messages,
    )

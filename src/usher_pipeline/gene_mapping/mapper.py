"""Gene ID mapping via mygene batch queries.

Provides batch mapping from Ensembl gene IDs to HGNC symbols and UniProt accessions.
Handles edge cases like missing data, notfound results, and nested data structures.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import mygene

logger = logging.getLogger(__name__)


@dataclass
class MappingResult:
    """Single gene ID mapping result.

    Attributes:
        ensembl_id: Ensembl gene ID (ENSG format)
        hgnc_symbol: HGNC gene symbol (None if not found)
        uniprot_accession: UniProt Swiss-Prot accession (None if not found)
        mapping_source: Data source for mapping (default: mygene)
    """
    ensembl_id: str
    hgnc_symbol: str | None = None
    uniprot_accession: str | None = None
    mapping_source: str = "mygene"


@dataclass
class MappingReport:
    """Summary report for batch mapping operation.

    Attributes:
        total_genes: Total number of genes queried
        mapped_hgnc: Number of genes with HGNC symbol
        mapped_uniprot: Number of genes with UniProt accession
        unmapped_ids: List of Ensembl IDs with no HGNC symbol
        success_rate_hgnc: Fraction of genes with HGNC symbol (0-1)
        success_rate_uniprot: Fraction of genes with UniProt accession (0-1)
    """
    total_genes: int
    mapped_hgnc: int
    mapped_uniprot: int
    unmapped_ids: list[str] = field(default_factory=list)
    success_rate_hgnc: float = 0.0
    success_rate_uniprot: float = 0.0

    def __post_init__(self):
        """Calculate success rates after initialization."""
        if self.total_genes > 0:
            self.success_rate_hgnc = self.mapped_hgnc / self.total_genes
            self.success_rate_uniprot = self.mapped_uniprot / self.total_genes


class GeneMapper:
    """Batch gene ID mapper using mygene API.

    Maps Ensembl gene IDs to HGNC symbols and UniProt Swiss-Prot accessions.
    Handles batch queries, missing data, and edge cases.
    """

    def __init__(self, batch_size: int = 1000):
        """Initialize gene mapper.

        Args:
            batch_size: Number of genes to query per batch (default: 1000)
        """
        self.batch_size = batch_size
        self.mg = mygene.MyGeneInfo()
        logger.info(f"Initialized GeneMapper with batch_size={batch_size}")

    def map_ensembl_ids(
        self,
        ensembl_ids: list[str]
    ) -> tuple[list[MappingResult], MappingReport]:
        """Map Ensembl gene IDs to HGNC symbols and UniProt accessions.

        Uses mygene.querymany() to batch query for gene symbols and UniProt IDs.
        Processes queries in chunks of batch_size to avoid API limits.

        Args:
            ensembl_ids: List of Ensembl gene IDs (ENSG format)

        Returns:
            Tuple of (mapping_results, mapping_report)
            - mapping_results: List of MappingResult for each input gene
            - mapping_report: Summary statistics for the mapping operation

        Notes:
            - Queries mygene with scopes='ensembl.gene'
            - Retrieves fields: symbol (HGNC), uniprot.Swiss-Prot
            - Handles 'notfound' results, missing keys, and nested structures
            - For duplicate query results, takes first non-null value
        """
        total_genes = len(ensembl_ids)
        logger.info(f"Mapping {total_genes} Ensembl IDs to HGNC/UniProt")

        results: list[MappingResult] = []
        unmapped_ids: list[str] = []
        mapped_hgnc = 0
        mapped_uniprot = 0

        # Process in batches
        for i in range(0, total_genes, self.batch_size):
            batch = ensembl_ids[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total_genes + self.batch_size - 1) // self.batch_size

            logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} genes)"
            )

            # Query mygene
            batch_results = self.mg.querymany(
                batch,
                scopes='ensembl.gene',
                fields='symbol,uniprot.Swiss-Prot',
                species=9606,
                returnall=True,
            )

            # Extract results from returnall=True format
            # mygene returns {'out': [...], 'missing': [...]} with returnall=True
            out_results = batch_results.get('out', [])

            # Process each result
            for hit in out_results:
                ensembl_id = hit.get('query', '')

                # Check if gene was not found
                if hit.get('notfound', False):
                    results.append(MappingResult(ensembl_id=ensembl_id))
                    unmapped_ids.append(ensembl_id)
                    continue

                # Extract HGNC symbol
                hgnc_symbol = hit.get('symbol')

                # Extract UniProt accession (handle nested structure and lists)
                uniprot_accession = None
                uniprot_data = hit.get('uniprot')

                if uniprot_data:
                    # uniprot can be a dict with Swiss-Prot key
                    if isinstance(uniprot_data, dict):
                        swiss_prot = uniprot_data.get('Swiss-Prot')
                        # Swiss-Prot can be a string or list
                        if isinstance(swiss_prot, str):
                            uniprot_accession = swiss_prot
                        elif isinstance(swiss_prot, list) and swiss_prot:
                            # Take first accession if list
                            uniprot_accession = swiss_prot[0]

                # Create mapping result
                results.append(MappingResult(
                    ensembl_id=ensembl_id,
                    hgnc_symbol=hgnc_symbol,
                    uniprot_accession=uniprot_accession,
                ))

                # Track success counts
                if hgnc_symbol:
                    mapped_hgnc += 1
                else:
                    unmapped_ids.append(ensembl_id)

                if uniprot_accession:
                    mapped_uniprot += 1

        # Create summary report
        report = MappingReport(
            total_genes=total_genes,
            mapped_hgnc=mapped_hgnc,
            mapped_uniprot=mapped_uniprot,
            unmapped_ids=unmapped_ids,
        )

        logger.info(
            f"Mapping complete: {mapped_hgnc}/{total_genes} HGNC "
            f"({report.success_rate_hgnc:.1%}), "
            f"{mapped_uniprot}/{total_genes} UniProt "
            f"({report.success_rate_uniprot:.1%})"
        )

        return results, report

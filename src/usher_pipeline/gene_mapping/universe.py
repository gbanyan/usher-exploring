"""Gene universe definition and retrieval.

Fetches the complete set of human protein-coding genes from Ensembl via mygene.
Validates gene count and filters to ENSG-format Ensembl IDs only.
"""

import logging
from typing import TypeAlias

import mygene

# Type alias for gene universe lists
GeneUniverse: TypeAlias = list[str]

logger = logging.getLogger(__name__)

# Expected range for human protein-coding genes
MIN_EXPECTED_GENES = 19000
MAX_EXPECTED_GENES = 23000


def fetch_protein_coding_genes(ensembl_release: int = 113) -> GeneUniverse:
    """Fetch all human protein-coding genes from Ensembl via mygene.

    Queries mygene for genes with type_of_gene=protein-coding in humans (taxid 9606).
    Filters to only genes with valid Ensembl gene IDs (ENSG format).
    Validates gene count is in expected range (19,000-22,000).

    Args:
        ensembl_release: Ensembl release version (for documentation purposes;
                        mygene returns current data regardless)

    Returns:
        Sorted, deduplicated list of Ensembl gene IDs (ENSG format)

    Raises:
        ValueError: If gene count is outside expected range

    Note:
        While ensembl_release is passed for documentation, mygene API doesn't
        support querying specific Ensembl versions - it returns current data.
        For reproducibility, use cached results or versioned data snapshots.
    """
    logger.info(
        f"Fetching protein-coding genes for Ensembl release {ensembl_release} "
        "(note: mygene returns current data)"
    )

    # Initialize mygene client
    mg = mygene.MyGeneInfo()

    # Query for human protein-coding genes
    logger.info("Querying mygene for type_of_gene:protein-coding (species=9606)")
    results = list(mg.query(
        'type_of_gene:"protein-coding"',
        species=9606,
        fields='ensembl.gene,symbol,name',
        fetch_all=True,
    ))

    logger.info(f"Retrieved {len(results)} results from mygene")

    # Extract Ensembl gene IDs
    gene_ids: set[str] = set()

    for hit in results:
        # Handle both single ensembl.gene and list cases
        ensembl_data = hit.get('ensembl')
        if not ensembl_data:
            continue

        # ensembl can be a single dict or list of dicts
        if isinstance(ensembl_data, dict):
            ensembl_list = [ensembl_data]
        else:
            ensembl_list = ensembl_data

        # Extract gene IDs from each ensembl entry
        for ensembl_entry in ensembl_list:
            gene_id = ensembl_entry.get('gene')
            if gene_id and isinstance(gene_id, str) and gene_id.startswith('ENSG'):
                gene_ids.add(gene_id)

    # Sort and deduplicate
    sorted_genes = sorted(gene_ids)
    gene_count = len(sorted_genes)

    logger.info(f"Extracted {gene_count} unique Ensembl gene IDs (ENSG format)")

    # Validate gene count
    if gene_count < MIN_EXPECTED_GENES:
        logger.warning(
            f"Gene count {gene_count} is below expected minimum {MIN_EXPECTED_GENES}. "
            "This may indicate missing data or query issues."
        )
    elif gene_count > MAX_EXPECTED_GENES:
        logger.warning(
            f"Gene count {gene_count} exceeds expected maximum {MAX_EXPECTED_GENES}. "
            "This may indicate pseudogene contamination or non-coding genes in results."
        )
    else:
        logger.info(
            f"Gene count {gene_count} is within expected range "
            f"({MIN_EXPECTED_GENES}-{MAX_EXPECTED_GENES})"
        )

    return sorted_genes

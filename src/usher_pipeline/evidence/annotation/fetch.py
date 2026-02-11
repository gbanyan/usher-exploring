"""Fetch gene annotation data from mygene.info and UniProt APIs."""

from typing import Optional
import math

import httpx
import mygene
import polars as pl
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = structlog.get_logger()

# Initialize mygene client (singleton pattern - reuse across calls)
_mg_client = None


def _get_mygene_client() -> mygene.MyGeneInfo:
    """Get or create mygene client singleton."""
    global _mg_client
    if _mg_client is None:
        _mg_client = mygene.MyGeneInfo()
    return _mg_client


def fetch_go_annotations(gene_ids: list[str], batch_size: int = 1000) -> pl.DataFrame:
    """Fetch GO annotations and pathway memberships from mygene.info.

    Uses mygene.querymany to batch query GO terms and pathway data.
    Processes in batches to avoid API timeout.

    Args:
        gene_ids: List of Ensembl gene IDs
        batch_size: Number of genes per batch query (default: 1000)

    Returns:
        DataFrame with columns:
        - gene_id: Ensembl gene ID
        - gene_symbol: HGNC symbol (NULL if not found)
        - go_term_count: Total GO term count across all ontologies (NULL if no GO data)
        - go_biological_process_count: GO BP term count (NULL if no GO data)
        - go_molecular_function_count: GO MF term count (NULL if no GO data)
        - go_cellular_component_count: GO CC term count (NULL if no GO data)
        - has_pathway_membership: Boolean indicating presence in KEGG/Reactome (NULL if no pathway data)

    Note: Genes with no GO annotations get NULL counts (not zero).
    """
    logger.info("fetch_go_annotations_start", gene_count=len(gene_ids))

    mg = _get_mygene_client()
    all_results = []

    # Process in batches to avoid mygene timeout
    num_batches = math.ceil(len(gene_ids) / batch_size)

    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(gene_ids))
        batch = gene_ids[start_idx:end_idx]

        logger.info(
            "fetch_go_batch",
            batch_num=i + 1,
            total_batches=num_batches,
            batch_size=len(batch),
        )

        # Query mygene for GO terms, pathways, and symbol
        try:
            results = mg.querymany(
                batch,
                scopes="ensembl.gene",
                fields="go,pathway.kegg,pathway.reactome,symbol",
                species="human",
                returnall=False,
            )

            # Process each gene's result
            for result in results:
                gene_id = result.get("query")
                gene_symbol = result.get("symbol", None)

                # Extract GO term counts by category
                go_data = result.get("go", {})
                if isinstance(go_data, dict):
                    # Count GO terms by ontology
                    bp_terms = go_data.get("BP", [])
                    mf_terms = go_data.get("MF", [])
                    cc_terms = go_data.get("CC", [])

                    # Convert to list if single dict (mygene sometimes returns dict for single term)
                    bp_list = bp_terms if isinstance(bp_terms, list) else ([bp_terms] if bp_terms else [])
                    mf_list = mf_terms if isinstance(mf_terms, list) else ([mf_terms] if mf_terms else [])
                    cc_list = cc_terms if isinstance(cc_terms, list) else ([cc_terms] if cc_terms else [])

                    bp_count = len(bp_list) if bp_list else None
                    mf_count = len(mf_list) if mf_list else None
                    cc_count = len(cc_list) if cc_list else None

                    # Total GO count (sum of non-NULL counts, or NULL if all NULL)
                    counts = [c for c in [bp_count, mf_count, cc_count] if c is not None]
                    total_count = sum(counts) if counts else None
                else:
                    # No GO data
                    bp_count = None
                    mf_count = None
                    cc_count = None
                    total_count = None

                # Check pathway membership
                pathway_data = result.get("pathway", {})
                has_kegg = bool(pathway_data.get("kegg"))
                has_reactome = bool(pathway_data.get("reactome"))
                has_pathway = (has_kegg or has_reactome) if (has_kegg or has_reactome or pathway_data) else None

                all_results.append({
                    "gene_id": gene_id,
                    "gene_symbol": gene_symbol,
                    "go_term_count": total_count,
                    "go_biological_process_count": bp_count,
                    "go_molecular_function_count": mf_count,
                    "go_cellular_component_count": cc_count,
                    "has_pathway_membership": has_pathway,
                })

        except Exception as e:
            logger.warning(
                "fetch_go_batch_error",
                batch_num=i + 1,
                error=str(e),
            )
            # Add NULL entries for failed batch
            for gene_id in batch:
                all_results.append({
                    "gene_id": gene_id,
                    "gene_symbol": None,
                    "go_term_count": None,
                    "go_biological_process_count": None,
                    "go_molecular_function_count": None,
                    "go_cellular_component_count": None,
                    "has_pathway_membership": None,
                })

    logger.info("fetch_go_annotations_complete", result_count=len(all_results))

    return pl.DataFrame(all_results)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def _query_uniprot_batch(accessions: list[str]) -> dict:
    """Query UniProt REST API for annotation scores (with retry).

    Args:
        accessions: List of UniProt accession IDs (max 100)

    Returns:
        Dict mapping accession -> annotation_score
    """
    if not accessions:
        return {}

    # Build OR query for batch lookup
    query = " OR ".join([f"accession:{acc}" for acc in accessions])
    url = "https://rest.uniprot.org/uniprotkb/search"

    params = {
        "query": query,
        "fields": "accession,annotation_score",
        "format": "json",
        "size": len(accessions),
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    # Parse results into mapping
    score_map = {}
    for entry in data.get("results", []):
        accession = entry.get("primaryAccession")
        score = entry.get("annotationScore")
        if accession and score is not None:
            score_map[accession] = int(score)

    return score_map


def fetch_uniprot_scores(
    gene_ids: list[str],
    uniprot_mapping: pl.DataFrame,
    batch_size: int = 100,
) -> pl.DataFrame:
    """Fetch UniProt annotation scores for genes.

    Uses UniProt REST API to query annotation scores in batches.
    Rate-limited to avoid overwhelming the API (built-in via tenacity retry).

    Args:
        gene_ids: List of Ensembl gene IDs
        uniprot_mapping: DataFrame with gene_id and uniprot_accession columns
        batch_size: Number of UniProt accessions per batch (default: 100)

    Returns:
        DataFrame with columns:
        - gene_id: Ensembl gene ID
        - uniprot_annotation_score: UniProt annotation score 1-5 (NULL if no mapping/score)

    Note: Genes without UniProt mapping get NULL (not zero).
    """
    logger.info("fetch_uniprot_scores_start", gene_count=len(gene_ids))

    # Filter mapping to requested genes
    mapping_filtered = uniprot_mapping.filter(pl.col("gene_id").is_in(gene_ids))

    if mapping_filtered.height == 0:
        logger.warning("fetch_uniprot_no_mappings")
        # Return all genes with NULL scores
        return pl.DataFrame({
            "gene_id": gene_ids,
            "uniprot_annotation_score": [None] * len(gene_ids),
        })

    # Get unique accessions
    accessions = mapping_filtered.select("uniprot_accession").unique().to_series().to_list()
    logger.info("fetch_uniprot_accessions", accession_count=len(accessions))

    # Batch query UniProt API
    all_scores = {}
    num_batches = math.ceil(len(accessions) / batch_size)

    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(accessions))
        batch = accessions[start_idx:end_idx]

        logger.info(
            "fetch_uniprot_batch",
            batch_num=i + 1,
            total_batches=num_batches,
            batch_size=len(batch),
        )

        try:
            batch_scores = _query_uniprot_batch(batch)
            all_scores.update(batch_scores)
        except Exception as e:
            logger.warning(
                "fetch_uniprot_batch_error",
                batch_num=i + 1,
                error=str(e),
            )
            # Continue with other batches - failed batch will have NULL scores

    # Create accession -> score mapping
    score_df = pl.DataFrame({
        "uniprot_accession": list(all_scores.keys()),
        "uniprot_annotation_score": list(all_scores.values()),
    })

    # Join back to gene IDs
    result = (
        mapping_filtered
        .select(["gene_id", "uniprot_accession"])
        .join(score_df, on="uniprot_accession", how="left")
        .group_by("gene_id")
        .agg(
            # Take first score if multiple accessions (consistent with gene universe pattern)
            pl.col("uniprot_annotation_score").first()
        )
    )

    # Ensure all requested genes are present (add NULL for missing)
    all_genes = pl.DataFrame({"gene_id": gene_ids})
    result = all_genes.join(result, on="gene_id", how="left")

    logger.info("fetch_uniprot_scores_complete", result_count=result.height)

    return result

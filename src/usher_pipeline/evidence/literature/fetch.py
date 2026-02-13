"""Fetch literature evidence from PubMed via Biopython Entrez."""

from time import sleep
from typing import Optional
from functools import wraps

import polars as pl
import structlog
from Bio import Entrez

from usher_pipeline.evidence.literature.models import (
    SEARCH_CONTEXTS,
    DIRECT_EVIDENCE_TERMS,
)

logger = structlog.get_logger()


def ratelimit(calls_per_sec: float = 3.0):
    """Rate limiter decorator for PubMed API calls.

    NCBI E-utilities rate limits:
    - Without API key: 3 requests/second
    - With API key: 10 requests/second

    Args:
        calls_per_sec: Maximum calls per second (default: 3 for no API key)
    """
    min_interval = 1.0 / calls_per_sec
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                sleep(min_interval - elapsed)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator


@ratelimit(calls_per_sec=3.0)  # Default rate limit
def _esearch_with_ratelimit(gene_symbol: str, query_terms: str, email: str) -> int:
    """Execute PubMed esearch with rate limiting.

    Args:
        gene_symbol: Gene symbol to search
        query_terms: Additional query terms (context filters)
        email: Email for NCBI (required)

    Returns:
        Count of publications matching query
    """
    query = f"({gene_symbol}[Gene Name]) AND {query_terms}"
    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=0)
        record = Entrez.read(handle)
        handle.close()
        count = int(record["Count"])
        return count
    except Exception as e:
        logger.warning(
            "pubmed_query_failed",
            gene_symbol=gene_symbol,
            query_terms=query_terms[:50],
            error=str(e),
        )
        # Return None to indicate failed query (not zero publications)
        return None


def query_pubmed_gene(
    gene_symbol: str,
    contexts: dict[str, str],
    email: str,
    api_key: Optional[str] = None,
) -> dict:
    """Query PubMed for a single gene across multiple contexts.

    Performs systematic queries:
    1. Total publications for gene (no context filter)
    2. Publications in each context (cilia, sensory, etc.)
    3. Direct experimental evidence (knockout/mutation terms)
    4. High-throughput screen mentions

    Args:
        gene_symbol: HGNC gene symbol (e.g., "BRCA1")
        contexts: Dict mapping context names to PubMed search terms
        email: Email address (required by NCBI E-utilities)
        api_key: Optional NCBI API key for higher rate limit (10/sec vs 3/sec)

    Returns:
        Dict with counts for each context, plus direct_experimental and hts counts.
        NULL values indicate failed queries (API errors), not zero publications.
    """
    # Set Entrez credentials
    Entrez.email = email
    if api_key:
        Entrez.api_key = api_key

    # Update rate limit based on API key
    rate = 10.0 if api_key else 3.0
    global _esearch_with_ratelimit
    _esearch_with_ratelimit = ratelimit(calls_per_sec=rate)(_esearch_with_ratelimit.__wrapped__)

    logger.debug(
        "pubmed_query_gene_start",
        gene_symbol=gene_symbol,
        context_count=len(contexts),
        rate_limit=rate,
    )

    results = {"gene_symbol": gene_symbol}

    # Query 1: Total publications (no context filter)
    total_count = _esearch_with_ratelimit(gene_symbol, "", email)
    results["total_pubmed_count"] = total_count

    # Query 2: Context-specific counts
    for context_name, context_terms in contexts.items():
        count = _esearch_with_ratelimit(gene_symbol, context_terms, email)
        results[f"{context_name}_context_count"] = count

    # Query 3: Direct experimental evidence
    direct_count = _esearch_with_ratelimit(
        gene_symbol,
        f"{DIRECT_EVIDENCE_TERMS} AND {contexts.get('cilia', '')}",
        email,
    )
    results["direct_experimental_count"] = direct_count

    # Query 4: High-throughput screen hits
    hts_terms = "(screen[Title/Abstract] OR proteomics[Title/Abstract] OR transcriptomics[Title/Abstract])"
    hts_count = _esearch_with_ratelimit(gene_symbol, hts_terms, email)
    results["hts_screen_count"] = hts_count

    logger.debug(
        "pubmed_query_gene_complete",
        gene_symbol=gene_symbol,
        total_count=total_count,
    )

    return results


def fetch_literature_evidence(
    gene_symbols: list[str],
    email: str,
    api_key: Optional[str] = None,
    batch_size: int = 500,
    checkpoint_df: Optional[pl.DataFrame] = None,
    checkpoint_callback=None,
) -> pl.DataFrame:
    """Fetch literature evidence for all genes with progress tracking and checkpointing.

    This is a SLOW operation (~20K genes * ~6 queries each = ~120K queries):
    - With API key (10 req/sec): ~3.3 hours
    - Without API key (3 req/sec): ~11 hours

    Supports checkpoint-restart: pass partial results to resume from last checkpoint.

    Args:
        gene_symbols: List of HGNC gene symbols to query
        email: Email address (required by NCBI E-utilities)
        api_key: Optional NCBI API key for 10 req/sec rate limit
        batch_size: Save checkpoint every N genes (default: 500)
        checkpoint_df: Optional partial results DataFrame to resume from
        checkpoint_callback: Optional callable(pl.DataFrame) to persist partial results

    Returns:
        DataFrame with columns: gene_symbol, total_pubmed_count, cilia_context_count,
        sensory_context_count, cytoskeleton_context_count, cell_polarity_context_count,
        direct_experimental_count, hts_screen_count.
        NULL values indicate failed queries (API errors), not zero publications.
    """
    all_gene_symbols = gene_symbols
    # Estimate time
    queries_per_gene = 6  # total + 4 contexts + direct + hts
    total_queries = len(gene_symbols) * queries_per_gene
    rate = 10.0 if api_key else 3.0
    estimated_seconds = total_queries / rate
    estimated_hours = estimated_seconds / 3600

    logger.info(
        "pubmed_fetch_start",
        gene_count=len(gene_symbols),
        total_queries=total_queries,
        rate_limit_per_sec=rate,
        estimated_hours=round(estimated_hours, 2),
        has_api_key=api_key is not None,
    )

    # Resume from checkpoint if provided
    if checkpoint_df is not None:
        processed_symbols = set(checkpoint_df["gene_symbol"].to_list())
        remaining_symbols = [s for s in gene_symbols if s not in processed_symbols]
        logger.info(
            "pubmed_fetch_resume",
            checkpoint_genes=len(processed_symbols),
            remaining_genes=len(remaining_symbols),
        )
        gene_symbols = remaining_symbols
        results = checkpoint_df.to_dicts()
    else:
        results = []

    total_all = len(all_gene_symbols)

    # Process genes with progress logging
    for i, gene_symbol in enumerate(gene_symbols, start=1):
        # Query PubMed for this gene
        gene_result = query_pubmed_gene(
            gene_symbol=gene_symbol,
            contexts=SEARCH_CONTEXTS,
            email=email,
            api_key=api_key,
        )
        results.append(gene_result)

        # Log progress every 100 genes
        if i % 100 == 0:
            pct = (len(results) / total_all) * 100
            logger.info(
                "pubmed_fetch_progress",
                processed=len(results),
                total=total_all,
                percent=round(pct, 1),
                gene_symbol=gene_symbol,
            )

        # Checkpoint every batch_size genes — persist to DuckDB
        if i % batch_size == 0 and checkpoint_callback is not None:
            checkpoint_partial = pl.DataFrame(results)
            checkpoint_callback(checkpoint_partial)
            logger.info(
                "pubmed_fetch_checkpoint_saved",
                processed=len(results),
                total=total_all,
                batch_size=batch_size,
            )

    logger.info(
        "pubmed_fetch_complete",
        total_genes=len(results),
        failed_count=sum(1 for r in results if r["total_pubmed_count"] is None),
    )

    # Convert to DataFrame
    df = pl.DataFrame(results)

    return df

"""Fetch protein features from UniProt and InterPro APIs."""

import time
from typing import List

import httpx
import polars as pl
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = structlog.get_logger()

# UniProt REST API base URL
UNIPROT_API_BASE = "https://rest.uniprot.org"

# InterPro REST API base URL
INTERPRO_API_BASE = "https://www.ebi.ac.uk/interpro/api"


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def fetch_uniprot_features(uniprot_ids: List[str]) -> pl.DataFrame:
    """Query UniProt REST API for protein features.

    Fetches protein length, domain annotations, coiled-coil regions,
    and transmembrane regions from UniProt in batches.

    Args:
        uniprot_ids: List of UniProt accession IDs

    Returns:
        DataFrame with columns:
        - uniprot_id: UniProt accession
        - protein_length: Amino acid length
        - domain_names: List of domain names
        - coiled_coil_count: Number of coiled-coil regions
        - transmembrane_count: Number of transmembrane regions

    Raises:
        httpx.HTTPStatusError: On HTTP errors (after retries)
        httpx.ConnectError: On connection errors (after retries)
        httpx.TimeoutException: On timeout (after retries)
    """
    if not uniprot_ids:
        return pl.DataFrame({
            "uniprot_id": [],
            "protein_length": [],
            "domain_names": [],
            "coiled_coil_count": [],
            "transmembrane_count": [],
        })

    logger.info("uniprot_fetch_start", accession_count=len(uniprot_ids))

    # UniProt batch size recommendation: 100 accessions per request
    batch_size = 100
    all_records = []

    for i in range(0, len(uniprot_ids), batch_size):
        batch = uniprot_ids[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(uniprot_ids) + batch_size - 1) // batch_size

        logger.info(
            "uniprot_batch_start",
            batch=batch_num,
            total_batches=total_batches,
            batch_size=len(batch),
        )

        # Query UniProt API with accession list
        # Use search endpoint with fields parameter
        query = " OR ".join(f"accession:{acc}" for acc in batch)
        url = f"{UNIPROT_API_BASE}/uniprotkb/search"
        params = {
            "query": query,
            "format": "json",
            "fields": "accession,length,ft_domain,ft_coiled,ft_transmem,annotation_score",
            "size": batch_size,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        # Parse results
        results = data.get("results", [])

        # Create lookup for fast access
        found_accessions = set()
        for entry in results:
            accession = entry.get("primaryAccession")
            if not accession:
                continue

            found_accessions.add(accession)

            # Extract protein length
            length = entry.get("sequence", {}).get("length")

            # Extract domain names from ft_domain features
            domain_names = []
            for feature in entry.get("features", []):
                if feature.get("type") == "Domain":
                    description = feature.get("description", "")
                    if description:
                        domain_names.append(description)

            # Count coiled-coil regions
            coiled_coil_count = sum(
                1 for feature in entry.get("features", [])
                if feature.get("type") == "Coiled coil"
            )

            # Count transmembrane regions
            transmembrane_count = sum(
                1 for feature in entry.get("features", [])
                if feature.get("type") == "Transmembrane"
            )

            all_records.append({
                "uniprot_id": accession,
                "protein_length": length,
                "domain_names": domain_names,
                "coiled_coil_count": coiled_coil_count,
                "transmembrane_count": transmembrane_count,
            })

        # Add NULL records for accessions not found
        for acc in batch:
            if acc not in found_accessions:
                all_records.append({
                    "uniprot_id": acc,
                    "protein_length": None,
                    "domain_names": [],
                    "coiled_coil_count": None,
                    "transmembrane_count": None,
                })

        # Rate limiting: UniProt allows 200 requests/second
        # With batches of 100, this gives us 20K accessions/second
        # Conservative: 5 requests/second = 500 accessions/second
        time.sleep(0.2)

    logger.info(
        "uniprot_fetch_complete",
        total_accessions=len(uniprot_ids),
        records_found=sum(1 for r in all_records if r["protein_length"] is not None),
    )

    return pl.DataFrame(all_records)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)
    ),
)
def fetch_interpro_domains(uniprot_ids: List[str]) -> pl.DataFrame:
    """Query InterPro API for domain annotations.

    Fetches detailed domain classification from InterPro to supplement
    UniProt annotations.

    Args:
        uniprot_ids: List of UniProt accession IDs

    Returns:
        DataFrame with columns:
        - uniprot_id: UniProt accession
        - domain_names: List of InterPro domain names
        - interpro_ids: List of InterPro accession IDs

    Raises:
        httpx.HTTPStatusError: On HTTP errors (after retries)
        httpx.ConnectError: On connection errors (after retries)
        httpx.TimeoutException: On timeout (after retries)
    """
    if not uniprot_ids:
        return pl.DataFrame({
            "uniprot_id": [],
            "domain_names": [],
            "interpro_ids": [],
        })

    logger.info("interpro_fetch_start", accession_count=len(uniprot_ids))

    # InterPro requires per-protein queries
    # Use conservative rate limiting: 10 req/sec as recommended
    all_records = []

    # For large datasets (>10K proteins), log warning about potential slowness
    if len(uniprot_ids) > 10000:
        logger.warning(
            "interpro_large_dataset",
            accession_count=len(uniprot_ids),
            estimated_time_min=len(uniprot_ids) / 10 / 60,
            note="Consider InterPro bulk download for large datasets",
        )

    with httpx.Client(timeout=30.0) as client:
        for idx, accession in enumerate(uniprot_ids, 1):
            if idx % 100 == 0:
                logger.info(
                    "interpro_progress",
                    processed=idx,
                    total=len(uniprot_ids),
                    percent=round(idx / len(uniprot_ids) * 100, 1),
                )

            # Query InterPro API
            url = f"{INTERPRO_API_BASE}/entry/interpro/protein/uniprot/{accession}"

            try:
                response = client.get(url, params={"format": "json"})
                response.raise_for_status()
                data = response.json()

                # Parse InterPro entries
                domain_names = []
                interpro_ids = []

                if "results" in data:
                    for entry in data["results"]:
                        metadata = entry.get("metadata", {})
                        interpro_id = metadata.get("accession")
                        name = metadata.get("name", {}).get("name", "")

                        if interpro_id:
                            interpro_ids.append(interpro_id)
                        if name:
                            domain_names.append(name)

                all_records.append({
                    "uniprot_id": accession,
                    "domain_names": domain_names,
                    "interpro_ids": interpro_ids,
                })

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Protein not found in InterPro - this is OK
                    all_records.append({
                        "uniprot_id": accession,
                        "domain_names": [],
                        "interpro_ids": [],
                    })
                else:
                    # Other HTTP errors - re-raise for retry
                    raise

            # Rate limiting: 10 requests/second
            time.sleep(0.1)

    logger.info(
        "interpro_fetch_complete",
        total_accessions=len(uniprot_ids),
        records_found=sum(1 for r in all_records if r["domain_names"]),
    )

    return pl.DataFrame(all_records)

"""Dual-format TSV+Parquet writer with provenance sidecar."""

from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import yaml


def write_candidate_output(
    df: pl.DataFrame | pl.LazyFrame,
    output_dir: Path,
    filename_base: str = "candidates",
) -> dict:
    """
    Write candidate genes to TSV and Parquet formats with provenance sidecar.

    Produces identical data in both formats for downstream tool compatibility.
    Generates YAML provenance sidecar with statistics and metadata.

    Args:
        df: Polars DataFrame or LazyFrame with scored candidate genes.
            Expected columns include:
            - gene_id, gene_symbol, composite_score, confidence_tier
            - All layer scores and contributions
            - supporting_layers, evidence_gaps
        output_dir: Directory to write output files (created if doesn't exist)
        filename_base: Base filename without extension (default: "candidates")

    Returns:
        Dictionary with output file paths:
        {
            "tsv": Path to TSV file,
            "parquet": Path to Parquet file,
            "provenance": Path to YAML provenance sidecar
        }

    Notes:
        - Collects LazyFrame if needed
        - Sorts by composite_score DESC, gene_id ASC for deterministic output
        - TSV uses tab separator with header
        - Parquet uses snappy compression
        - Provenance YAML includes:
          - generated_at timestamp
          - output_files list
          - statistics (total_candidates, tier counts)
          - column_count and column_names
    """
    # Ensure output_dir exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect LazyFrame if needed
    if isinstance(df, pl.LazyFrame):
        df = df.collect()

    # Sort deterministically for reproducible output
    df = df.sort(["composite_score", "gene_id"], descending=[True, False])

    # Define output paths
    tsv_path = output_dir / f"{filename_base}.tsv"
    parquet_path = output_dir / f"{filename_base}.parquet"
    provenance_path = output_dir / f"{filename_base}.provenance.yaml"

    # Write TSV
    df.write_csv(tsv_path, separator="\t", include_header=True)

    # Write Parquet
    df.write_parquet(parquet_path, compression="snappy", use_pyarrow=True)

    # Collect statistics for provenance
    total_candidates = df.height

    # Count by confidence_tier if column exists
    tier_counts = {}
    if "confidence_tier" in df.columns:
        tier_dist = df.group_by("confidence_tier").agg(pl.len()).sort("confidence_tier")
        tier_counts = {
            row["confidence_tier"]: row["len"] for row in tier_dist.to_dicts()
        }

    # Build provenance metadata
    provenance = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_files": [tsv_path.name, parquet_path.name],
        "statistics": {
            "total_candidates": total_candidates,
            "high_count": tier_counts.get("HIGH", 0),
            "medium_count": tier_counts.get("MEDIUM", 0),
            "low_count": tier_counts.get("LOW", 0),
        },
        "column_count": len(df.columns),
        "column_names": df.columns,
    }

    # Write provenance YAML
    with open(provenance_path, "w") as f:
        yaml.dump(provenance, f, default_flow_style=False, sort_keys=False)

    return {
        "tsv": tsv_path,
        "parquet": parquet_path,
        "provenance": provenance_path,
    }

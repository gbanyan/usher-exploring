"""Build exploratory human cochlear hair-cell expression from GEO GSE135913.

The processed CellFindR matrices contain per-cluster standardized mean
expression but no author cell-type labels.  We therefore identify a putative
hair-cell cluster only when a broad, predeclared marker panel is sufficiently
covered and concordantly enriched.  Samples failing that quality gate remain
in provenance but do not contribute to the gene-level aggregate.

This script is analysis-only and does not modify the production DuckDB tables.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb
import httpx
import polars as pl


GEO_ACCESSION = "GSE135913"
HAIR_CELL_MARKERS = (
    "ATOH1", "OTOF", "POU4F3", "GFI1", "RBM24", "LMO7", "EPS8L2", "SLC17A8"
)
MIN_MARKERS = 4

SAMPLES = {
    "GSM4037819": {
        "developmental_week": 15,
        "filename": "GSM4037819_human_cochlea_15w_processed.csv.gz",
        "url": "https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM4037nnn/GSM4037819/suppl/GSM4037819_fhu_15_pos_alg_CelFindR_alg_matrix.csv.gz",
    },
    "GSM4037820": {
        "developmental_week": 17,
        "filename": "GSM4037820_human_cochlea_17w_processed.csv.gz",
        "url": "https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM4037nnn/GSM4037820/suppl/GSM4037820_fhu_17_alg_CelFindR_alg_matrix.csv.gz",
    },
    "GSM4037821": {
        "developmental_week": 23,
        "filename": "GSM4037821_human_cochlea_23w_processed.csv.gz",
        "url": "https://ftp.ncbi.nlm.nih.gov/geo/samples/GSM4037nnn/GSM4037821/suppl/GSM4037821_fhu_23_pos_alg_CelFindR_alg_matrix.csv.gz",
    },
}


@dataclass
class SampleAudit:
    sample: str
    developmental_week: int
    source_file: str
    sha256: str
    marker_coverage: int
    selected_cluster: str | None
    marker_mean: float | None
    runner_up_mean: float | None
    margin: float | None
    included: bool
    exclusion_reason: str | None
    leave_one_marker_out_stable: bool | None
    leave_one_marker_out_assignments: dict[str, str | None]


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path, force: bool = False) -> Path:
    """Download a GEO supplementary file with an atomic temporary file."""
    if destination.exists() and not force:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_bytes(1024 * 1024):
                handle.write(chunk)
    temporary.replace(destination)
    return destination


def load_scored_labels(scored_db: Path) -> set[str]:
    """Load and validate the current symbol-level scored state."""
    if not scored_db.is_file():
        raise FileNotFoundError(f"Missing scored-state database: {scored_db}")
    con = duckdb.connect(str(scored_db), read_only=True)
    try:
        rows = con.execute(
            "SELECT gene_id, gene_symbol FROM scored_genes"
        ).fetchall()
        universe_ids = {
            row[0] for row in con.execute("SELECT gene_id FROM gene_universe").fetchall()
        }
    finally:
        con.close()
    if len(rows) != 20081 or len({row[0] for row in rows}) != 20081:
        raise ValueError(
            "Expected the current 20,081-row scored state with unique gene IDs; "
            f"found {len(rows)} rows and {len({row[0] for row in rows})} IDs"
        )
    if any(row[0] not in universe_ids for row in rows):
        raise ValueError("scored_genes contains an ID outside gene_universe")
    labels = {row[1] for row in rows if row[1] is not None}
    if len(labels) != 20081:
        raise ValueError(f"Expected 20,081 unique scored labels; found {len(labels)}")
    return labels


def identify_hair_cell_cluster(
    matrix: pl.DataFrame,
    markers: tuple[str, ...] = HAIR_CELL_MARKERS,
    min_markers: int = MIN_MARKERS,
) -> tuple[str | None, dict[str, float | int | str | None]]:
    """Identify the cluster with the strongest concordant hair-cell signature."""
    gene_column = matrix.columns[0]
    available = [m for m in markers if m in set(matrix[gene_column].to_list())]
    if len(available) < min_markers:
        return None, {
            "marker_coverage": len(available),
            "marker_mean": None,
            "runner_up_mean": None,
            "margin": None,
            "reason": f"marker coverage {len(available)}/{len(markers)} below {min_markers}",
        }

    marker_rows = matrix.filter(pl.col(gene_column).is_in(available))
    scores = []
    for column in (c for c in matrix.columns if c.endswith("_Mean")):
        scores.append((column.removesuffix("_Mean"), float(marker_rows[column].mean())))
    scores.sort(key=lambda item: item[1], reverse=True)
    best, runner_up = scores[0], scores[1]
    margin = best[1] - runner_up[1]
    # Require both positive aggregate expression and separation from the next
    # cluster. Values are standardized by the source's CellFindR processing.
    if best[1] <= 0 or margin < 0.5:
        return None, {
            "marker_coverage": len(available),
            "marker_mean": best[1],
            "runner_up_mean": runner_up[1],
            "margin": margin,
            "reason": "hair-cell marker signal is not sufficiently separated",
        }
    return best[0], {
        "marker_coverage": len(available),
        "marker_mean": best[1],
        "runner_up_mean": runner_up[1],
        "margin": margin,
        "reason": None,
    }


def leave_one_marker_out_sensitivity(
    matrix: pl.DataFrame,
    markers: tuple[str, ...] = HAIR_CELL_MARKERS,
) -> tuple[bool | None, dict[str, str | None]]:
    """Re-select clusters after omitting each available marker in turn."""
    gene_column = matrix.columns[0]
    present = [marker for marker in markers if marker in set(matrix[gene_column].to_list())]
    baseline, _ = identify_hair_cell_cluster(matrix, markers)
    if baseline is None:
        return None, {}
    assignments: dict[str, str | None] = {}
    for omitted in present:
        reduced = tuple(marker for marker in markers if marker != omitted)
        assignment, _ = identify_hair_cell_cluster(
            matrix, reduced, min_markers=max(3, MIN_MARKERS - 1)
        )
        assignments[omitted] = assignment
    return all(assignment == baseline for assignment in assignments.values()), assignments


def extract_cluster_expression(matrix: pl.DataFrame, cluster: str, sample: str) -> pl.DataFrame:
    """Extract one cluster's standardized mean expression by gene symbol."""
    gene_column = matrix.columns[0]
    return matrix.select(
        pl.col(gene_column).cast(pl.Utf8).alias("gene_symbol"),
        pl.col(f"{cluster}_Mean").cast(pl.Float64).alias(f"{sample}_hair_cell_mean"),
    )


def aggregate_samples(sample_frames: list[pl.DataFrame]) -> pl.DataFrame:
    """Outer-join samples and calculate NULL-aware mean and consistency."""
    if not sample_frames:
        return pl.DataFrame({
            "gene_symbol": [],
            "cochlear_hair_cell_expression": [],
            "hair_cell_sample_count": [],
            "hair_cell_developmental_consistency": [],
        }).cast({"gene_symbol": pl.Utf8, "cochlear_hair_cell_expression": pl.Float64,
                 "hair_cell_sample_count": pl.UInt32,
                 "hair_cell_developmental_consistency": pl.Float64})
    merged = sample_frames[0]
    for frame in sample_frames[1:]:
        merged = merged.join(frame, on="gene_symbol", how="full", coalesce=True)
    value_columns = [c for c in merged.columns if c.endswith("_hair_cell_mean")]
    return merged.with_columns(
        pl.mean_horizontal(value_columns).alias("cochlear_hair_cell_expression"),
        pl.sum_horizontal([pl.col(c).is_not_null().cast(pl.UInt32) for c in value_columns])
        .alias("hair_cell_sample_count"),
        (1.0 - (
            pl.max_horizontal(value_columns) - pl.min_horizontal(value_columns)
        ) / (pl.mean_horizontal(value_columns).abs() + 1.0))
        .clip(0.0, 1.0)
        .alias("hair_cell_developmental_consistency"),
    )


def build_dataset(
    cache_dir: Path,
    force: bool = False,
    *,
    cache_only: bool = True,
    target_labels: set[str] | None = None,
) -> tuple[pl.DataFrame, list[SampleAudit]]:
    frames: list[pl.DataFrame] = []
    audits: list[SampleAudit] = []
    for sample, metadata in SAMPLES.items():
        path = cache_dir / metadata["filename"]
        if cache_only:
            if not path.is_file():
                raise FileNotFoundError(
                    f"Offline cache-only mode requires local GSE input: {path}"
                )
        else:
            path = download_file(metadata["url"], path, force)
        matrix = pl.read_csv(path)
        cluster, detail = identify_hair_cell_cluster(matrix)
        loo_stable, loo_assignments = leave_one_marker_out_sensitivity(matrix)
        included = cluster is not None
        audits.append(SampleAudit(
            sample=sample,
            developmental_week=metadata["developmental_week"],
            source_file=str(path),
            sha256=sha256sum(path),
            marker_coverage=int(detail["marker_coverage"]),
            selected_cluster=cluster,
            marker_mean=detail["marker_mean"],
            runner_up_mean=detail["runner_up_mean"],
            margin=detail["margin"],
            included=included,
            exclusion_reason=detail["reason"],
            leave_one_marker_out_stable=loo_stable,
            leave_one_marker_out_assignments=loo_assignments,
        ))
        if included:
            frames.append(extract_cluster_expression(matrix, cluster, sample))
    dataset = aggregate_samples(frames)
    if target_labels is not None:
        dataset = dataset.filter(pl.col("gene_symbol").is_in(target_labels))
    return dataset, audits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, default=Path("data/expression"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/report/exploration"))
    parser.add_argument("--scored-db", type=Path, default=Path("data/pipeline.duckdb"))
    parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Require all GEO inputs to exist locally; this is the default behavior.",
    )
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="Explicitly allow GEO downloads (never used for the production rebuild).",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.cache_only and args.allow_download:
        parser.error("--cache-only and --allow-download are mutually exclusive")
    if args.force and not args.allow_download:
        parser.error("--force requires explicit --allow-download")
    target_labels = load_scored_labels(args.scored_db)
    cache_only = not args.allow_download
    dataset, audits = build_dataset(
        args.cache_dir,
        args.force,
        cache_only=cache_only,
        target_labels=target_labels,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    dataset.write_parquet(args.output_dir / "gse135913_hair_cell_expression.parquet")
    dataset.write_csv(args.output_dir / "gse135913_hair_cell_expression.tsv", separator="\t")
    provenance = {
        "geo_accession": GEO_ACCESSION,
        "method": "non-Usher-marker-guided CellFindR cluster mean",
        "markers": list(HAIR_CELL_MARKERS),
        "minimum_markers": MIN_MARKERS,
        "source_mode": "local_cache_only" if cache_only else "download_allowed",
        "target_scored_state": {
            "database": str(args.scored_db),
            "label_count": len(target_labels),
            "retained_label_count": dataset.height,
        },
        "samples": [asdict(audit) for audit in audits],
    }
    (args.output_dir / "gse135913_hair_cell_provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(provenance, indent=2))
    print(f"genes={dataset.height} scored_labels={len(target_labels)}")


if __name__ == "__main__":
    main()

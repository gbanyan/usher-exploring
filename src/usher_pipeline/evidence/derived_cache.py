"""Fail-closed migration of donor-derived evidence caches.

Some evidence layers have no retained raw download in the offline production
bundle.  This module provides the deliberately explicit alternative for those
layers: read a copied donor DuckDB read-only, intersect by exact stable
Ensembl ID, merge duplicate source rows only when their source fields agree,
and recompute all schema-derived gates and scores against the current frozen
universe.  It is not a raw-source rerun.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import polars as pl

from usher_pipeline.evidence.animal_models.transform import score_animal_evidence
from usher_pipeline.evidence.annotation.transform import (
    classify_annotation_tier,
    normalize_annotation_score,
)

if TYPE_CHECKING:
    from usher_pipeline.persistence import ProvenanceTracker


STABLE_ENSEMBL_PREFIX = "ENSG"

ANNOTATION_SOURCE_COLUMNS = (
    "go_term_count",
    "go_biological_process_count",
    "go_molecular_function_count",
    "go_cellular_component_count",
    "has_pathway_membership",
    "uniprot_annotation_score",
)

ANIMAL_SOURCE_COLUMNS = (
    "mouse_ortholog",
    "mouse_ortholog_confidence",
    "zebrafish_ortholog",
    "zebrafish_ortholog_confidence",
    "has_mouse_phenotype",
    "has_zebrafish_phenotype",
    "has_impc_phenotype",
    "sensory_phenotype_count",
    "phenotype_categories",
)

_DERIVED_COLUMNS = {
    "annotation_tier",
    "annotation_score_normalized",
    "animal_model_score_normalized",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_ids(
    ids: list[object],
    *,
    label: str,
    require_unique: bool = True,
) -> list[str]:
    if any(value is None for value in ids):
        raise ValueError(f"{label} contains NULL gene IDs")
    invalid = [
        value
        for value in ids
        if not isinstance(value, str)
        or not value.startswith(STABLE_ENSEMBL_PREFIX)
        or not value[len(STABLE_ENSEMBL_PREFIX):].isdigit()
    ]
    if invalid:
        raise ValueError(
            f"{label} contains non-stable Ensembl IDs; examples: {invalid[:5]}"
        )
    if require_unique and len(ids) != len(set(ids)):
        raise ValueError(f"{label} contains duplicate gene IDs")
    return [str(value) for value in ids]


def _load_donor_tables(
    donor_db_path: Path,
    table_name: str,
) -> tuple[pl.DataFrame, set[str], str]:
    donor_db_path = Path(donor_db_path).expanduser()
    if not donor_db_path.is_file():
        raise FileNotFoundError(
            "Derived-cache migration requires an existing local donor DuckDB: "
            f"{donor_db_path}"
        )

    donor_hash = _sha256(donor_db_path)
    connection = duckdb.connect(str(donor_db_path), read_only=True)
    try:
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        required_tables = {"gene_universe", table_name}
        missing_tables = sorted(required_tables - tables)
        if missing_tables:
            raise ValueError(
                f"Derived-cache donor is missing required tables: {', '.join(missing_tables)}"
            )

        donor_universe = connection.execute(
            "SELECT gene_id FROM gene_universe"
        ).pl()
        donor_ids = _stable_ids(
            donor_universe["gene_id"].to_list(),
            label="donor gene_universe",
        )
        table = connection.execute(f"SELECT * FROM {table_name}").pl()
    finally:
        connection.close()

    if "gene_id" not in table.columns:
        raise ValueError(f"Derived-cache donor table {table_name} lacks gene_id")
    _stable_ids(
        table["gene_id"].to_list(),
        label=f"donor {table_name}",
        require_unique=False,
    )
    return table, set(donor_ids), donor_hash


def _validate_target_universe(gene_universe: pl.DataFrame) -> tuple[list[str], set[str]]:
    if "gene_id" not in gene_universe.columns:
        raise ValueError("Current gene_universe lacks gene_id")
    ids = _stable_ids(
        gene_universe["gene_id"].to_list(),
        label="current gene_universe",
    )
    if len(ids) != 20116:
        raise ValueError(
            "Derived-cache migration requires the corrected 20,116-ID universe; "
            f"got {len(ids)} IDs"
        )
    if "gene_symbol" not in gene_universe.columns:
        raise ValueError("Current gene_universe lacks gene_symbol")
    return ids, set(ids)


def _merge_source_rows(
    table: pl.DataFrame,
    *,
    donor_universe_ids: set[str],
    target_ids: set[str],
    source_columns: tuple[str, ...],
    layer: str,
) -> tuple[pl.DataFrame, pl.DataFrame, dict]:
    missing_columns = sorted(set(source_columns) - set(table.columns))
    if missing_columns:
        raise ValueError(
            f"Derived-cache donor {layer} table is incompatible; missing source "
            f"columns: {', '.join(missing_columns)}"
        )

    table_ids = set(table["gene_id"].to_list())
    rogue_ids = sorted(table_ids - donor_universe_ids)
    usable = table.filter(
        pl.col("gene_id").is_in(donor_universe_ids)
        & ~pl.col("gene_id").is_in(rogue_ids)
    )

    grouped: dict[str, list[dict]] = {}
    for row in usable.select(["gene_id", *source_columns]).iter_rows(named=True):
        grouped.setdefault(row["gene_id"], []).append(row)

    merged_rows: list[dict] = []
    audit_rows: list[dict] = []
    conflict_ids: list[str] = []
    for gene_id in sorted(table_ids):
        rows = grouped.get(gene_id, [])
        duplicate_count = len(rows)
        source_conflicts: list[str] = []
        for column in source_columns:
            values = {row[column] for row in rows if row[column] is not None}
            if len(values) > 1:
                source_conflicts.append(column)
        if source_conflicts:
            conflict_ids.append(gene_id)

        if gene_id in donor_universe_ids and rows:
            merged = {"gene_id": gene_id}
            for column in source_columns:
                # Source-level duplicates are accepted only when they agree.
                # This is intentionally not a max/first heuristic: a conflict
                # would make a donor-derived migration non-reproducible.
                merged[column] = rows[0][column]
            if gene_id in target_ids:
                merged_rows.append(merged)

        if gene_id in rogue_ids:
            status = "rogue_excluded"
        elif gene_id not in target_ids:
            status = "outside_new_universe"
        elif duplicate_count > 1:
            status = "merged_duplicate"
        else:
            status = "retained"
        audit_rows.append(
            {
                "layer": layer,
                "gene_id": gene_id,
                "donor_row_count": duplicate_count,
                "donor_duplicate_excess": max(duplicate_count - 1, 0),
                "source_conflict_columns": ";".join(source_conflicts),
                "status": status,
                "retained_in_new_universe": gene_id in target_ids and bool(rows),
            }
        )

    if conflict_ids:
        raise ValueError(
            f"Derived-cache donor {layer} has conflicting duplicate source IDs: "
            f"{conflict_ids[:10]}"
        )

    merged = pl.DataFrame(merged_rows)
    if merged.is_empty():
        merged = pl.DataFrame(
            schema={"gene_id": pl.String, **{column: table.schema[column] for column in source_columns}}
        )
    audit = pl.DataFrame(audit_rows)
    audit_summary = {
        "donor_row_count": table.height,
        "donor_distinct_gene_count": len(table_ids),
        "donor_duplicate_id_count": sum(
            1 for row in audit_rows if row["donor_row_count"] > 1
        ),
        "donor_duplicate_row_excess": sum(
            row["donor_duplicate_excess"] for row in audit_rows
        ),
        "rogue_ids_rejected": rogue_ids,
        "rogue_id_count": len(rogue_ids),
        "outside_new_universe_id_count": sum(
            1 for row in audit_rows if row["status"] == "outside_new_universe"
        ),
        "merged_duplicate_id_count": sum(
            1 for row in audit_rows if row["status"] == "merged_duplicate"
        ),
        "source_conflict_id_count": len(conflict_ids),
        "retained_source_id_count": len(merged_rows),
    }
    return merged, audit, audit_summary


def _record_derived_cache_provenance(
    provenance: ProvenanceTracker | None,
    *,
    layer: str,
    donor_db_path: Path,
    donor_hash: str,
    target_count: int,
    audit_summary: dict,
) -> None:
    if provenance is None:
        return
    provenance.record_step(
        "derived_cache_reuse",
        {
            "layer": layer,
            "mode": "derived_cache_reuse",
            "source_artifact_path": str(Path(donor_db_path).resolve()),
            "source_artifact_hash": donor_hash,
            "source_artifact_hash_algorithm": "sha256",
            "source_table": layer,
            "target_universe_count": target_count,
            "raw_source_coverage": {
                "status": "incomplete",
                "raw_rerun": False,
                "reason": "retained raw source is unavailable for this layer",
            },
            "audit": audit_summary,
            "fail_closed_policies": [
                "exact stable Ensembl gene_id intersection only",
                "rogue donor IDs excluded",
                "conflicting duplicate source IDs rejected",
                "schema-derived gates and scores recomputed",
                "missing target IDs retained with NULL source evidence",
            ],
            "source_name": f"{layer}_donor_duckdb",
            "local_path": str(Path(donor_db_path).resolve()),
        },
    )


def reindex_annotation_from_donor(
    donor_db_path: Path,
    gene_universe: pl.DataFrame,
    provenance: ProvenanceTracker | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame, dict]:
    """Recompute annotation evidence from an exact-ID donor cache."""

    target_ids, target_id_set = _validate_target_universe(gene_universe)
    table, donor_universe_ids, donor_hash = _load_donor_tables(
        donor_db_path,
        "annotation_completeness",
    )
    merged, audit, audit_summary = _merge_source_rows(
        table,
        donor_universe_ids=donor_universe_ids,
        target_ids=target_id_set,
        source_columns=ANNOTATION_SOURCE_COLUMNS,
        layer="annotation_completeness",
    )
    # The donor's gene_symbol is deliberately not carried forward.  Symbols
    # come from the current GTF/exact-ID setup mapping only.
    current = gene_universe.select(["gene_id", "gene_symbol"])
    result = current.join(merged, on="gene_id", how="left")
    result = classify_annotation_tier(result)
    result = normalize_annotation_score(result)
    if result.height != len(target_ids):
        raise ValueError("Annotation derived-cache result does not cover the target universe")
    _record_derived_cache_provenance(
        provenance,
        layer="annotation_completeness",
        donor_db_path=donor_db_path,
        donor_hash=donor_hash,
        target_count=len(target_ids),
        audit_summary=audit_summary,
    )
    return result, audit, {
        "mode": "derived_cache_reuse",
        "source_artifact_hash": donor_hash,
        "source_artifact_path": str(Path(donor_db_path).resolve()),
        "raw_source_coverage": "incomplete",
        **audit_summary,
    }


def reindex_animal_models_from_donor(
    donor_db_path: Path,
    gene_universe: pl.DataFrame,
    provenance: ProvenanceTracker | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame, dict]:
    """Recompute animal-model scores from an exact-ID donor cache."""

    target_ids, target_id_set = _validate_target_universe(gene_universe)
    table, donor_universe_ids, donor_hash = _load_donor_tables(
        donor_db_path,
        "animal_model_phenotypes",
    )
    merged, audit, audit_summary = _merge_source_rows(
        table,
        donor_universe_ids=donor_universe_ids,
        target_ids=target_id_set,
        source_columns=ANIMAL_SOURCE_COLUMNS,
        layer="animal_model_phenotypes",
    )
    result = gene_universe.select(["gene_id"]).join(merged, on="gene_id", how="left")
    result = score_animal_evidence(result)
    if result.height != len(target_ids):
        raise ValueError("Animal-model derived-cache result does not cover the target universe")
    _record_derived_cache_provenance(
        provenance,
        layer="animal_model_phenotypes",
        donor_db_path=donor_db_path,
        donor_hash=donor_hash,
        target_count=len(target_ids),
        audit_summary=audit_summary,
    )
    return result, audit, {
        "mode": "derived_cache_reuse",
        "source_artifact_hash": donor_hash,
        "source_artifact_path": str(Path(donor_db_path).resolve()),
        "raw_source_coverage": "incomplete",
        **audit_summary,
    }


def write_derived_cache_audit(audit: pl.DataFrame, output_path: Path) -> Path:
    """Write the merged/excluded donor-ID audit table as a TSV."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit.write_csv(output_path, separator="\t")
    return output_path

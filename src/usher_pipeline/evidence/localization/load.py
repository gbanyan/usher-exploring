"""Load localization evidence to DuckDB with provenance tracking."""

import duckdb
import polars as pl
import structlog
import re

from usher_pipeline.evidence.localization.fetch import (
    CURATED_COMPENDIUM_PROVENANCE,
)
from usher_pipeline.evidence.localization.models import (
    CURATED_COMPENDIUM_COLUMNS,
    HPA_EVIDENCE_MODALITY,
    HPA_RELIABILITY_WEIGHTS,
    LOCALIZATION_CHECKPOINT_SCHEMA_VERSION,
    LOCALIZATION_CHECKPOINT_REQUIRED_COLUMNS,
    LOCALIZATION_CHECKPOINT_VERSION_COLUMN,
    LOCALIZATION_GATE_SOURCE_COLUMNS,
    LEGACY_CURATED_PROTEOMICS_COLUMNS,
    LOCALIZATION_TABLE_NAME,
)
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker

logger = structlog.get_logger()


class LegacyLocalizationCheckpointError(RuntimeError):
    """Raised when a checkpoint cannot be safely reprocessed in place."""


def _checkpoint_description(description: str = "") -> str:
    """Persist the schema version in checkpoint metadata as well as the table."""
    base = description or "HPA localization with curated ciliary/centrosomal compendium"
    return f"localization_schema_version={LOCALIZATION_CHECKPOINT_SCHEMA_VERSION}; {base}"


def _checkpoint_version(df: pl.DataFrame) -> set[int]:
    if LOCALIZATION_CHECKPOINT_VERSION_COLUMN not in df.columns:
        return set()
    values = df[LOCALIZATION_CHECKPOINT_VERSION_COLUMN].drop_nulls().unique().to_list()
    return {int(value) for value in values}


def _checkpoint_metadata_version(store: PipelineStore) -> int | None:
    """Read the persisted schema version from the checkpoint registry."""
    try:
        row = store.conn.execute(
            "SELECT description FROM _checkpoints WHERE table_name = ?",
            [LOCALIZATION_TABLE_NAME],
        ).fetchone()
    except duckdb.CatalogException:
        return None
    if row is None or not row[0]:
        return None
    match = re.search(r"localization_schema_version=(\d+)", str(row[0]))
    return int(match.group(1)) if match else None


def _add_empty_checkpoint_columns(df: pl.DataFrame) -> pl.DataFrame:
    """Add typed columns only for a genuinely empty legacy checkpoint."""
    bool_columns = set(LOCALIZATION_GATE_SOURCE_COLUMNS)
    text_columns = {
        "gene_id", "gene_symbol", "hpa_main_location", "hpa_reliability",
        "hpa_evidence_modality", "hpa_evidence_type", "evidence_type",
    }
    float_columns = {
        "hpa_reliability_weight", "cilia_proximity_score",
        "localization_score_normalized",
    }
    expressions = []
    for column in LOCALIZATION_CHECKPOINT_REQUIRED_COLUMNS:
        if column in df.columns:
            continue
        if column in bool_columns:
            expressions.append(pl.lit(False).cast(pl.Boolean).alias(column))
        elif column in text_columns:
            expressions.append(pl.lit(None, dtype=pl.Utf8).alias(column))
        elif column in float_columns:
            expressions.append(pl.lit(None, dtype=pl.Float64).alias(column))
        elif column == LOCALIZATION_CHECKPOINT_VERSION_COLUMN:
            expressions.append(
                pl.lit(LOCALIZATION_CHECKPOINT_SCHEMA_VERSION)
                .cast(pl.Int32)
                .alias(column)
            )
    return df.with_columns(expressions) if expressions else df


def migrate_legacy_localization_checkpoint(store: PipelineStore) -> dict[str, object]:
    """Reprocess old localization checkpoints or fail without fabricating flags.

    614741c/d26348b checkpoints can contain all old direct-source flags while
    lacking the explicit schema version and reliability fields. They are still
    legacy and must be reclassified/rescored from their raw HPA/compendium
    inputs before scoring. Aggregate-only checkpoints cannot be recovered.
    """
    try:
        columns = {
            row[0]
            for row in store.conn.execute(
                f"DESCRIBE {LOCALIZATION_TABLE_NAME}"
            ).fetchall()
        }
    except duckdb.CatalogException:
        return {"status": "missing", "migrated": False}

    legacy_df = store.load_dataframe(LOCALIZATION_TABLE_NAME)
    if legacy_df is None:
        return {"status": "missing", "migrated": False}

    missing_required_columns = [
        column for column in LOCALIZATION_CHECKPOINT_REQUIRED_COLUMNS
        if column not in columns
    ]
    version_values = _checkpoint_version(legacy_df)
    metadata_version = _checkpoint_metadata_version(store)
    metadata_is_current = metadata_version is None or (
        metadata_version == LOCALIZATION_CHECKPOINT_SCHEMA_VERSION
    )
    is_current = (
        not missing_required_columns
        and version_values in ({LOCALIZATION_CHECKPOINT_SCHEMA_VERSION}, set())
        and (legacy_df.height == 0 or version_values == {LOCALIZATION_CHECKPOINT_SCHEMA_VERSION})
        and metadata_is_current
    )
    if is_current:
        return {
            "status": "current",
            "migrated": False,
            "schema_version": LOCALIZATION_CHECKPOINT_SCHEMA_VERSION,
        }

    # An empty checkpoint contains no evidence whose meaning could be lost;
    # add typed columns and record this as an explicit migration.
    if legacy_df.height == 0:
        legacy_columns_to_drop = [
            column for column in LEGACY_CURATED_PROTEOMICS_COLUMNS
            if column in legacy_df.columns
        ]
        if legacy_columns_to_drop:
            legacy_df = legacy_df.drop(legacy_columns_to_drop)
        migrated_empty = _add_empty_checkpoint_columns(legacy_df)
        store.save_dataframe(
            migrated_empty,
            LOCALIZATION_TABLE_NAME,
            description=_checkpoint_description("Migrated empty localization checkpoint"),
            replace=True,
        )
        return {
            "status": "migrated_empty",
            "migrated": True,
            "missing_columns": missing_required_columns,
            "schema_version": LOCALIZATION_CHECKPOINT_SCHEMA_VERSION,
        }

    raw_columns = {
        "gene_id",
        "gene_symbol",
        "hpa_main_location",
        "hpa_reliability",
    }
    has_current_compendium = set(CURATED_COMPENDIUM_COLUMNS) <= set(legacy_df.columns)
    has_legacy_compendium = set(LEGACY_CURATED_PROTEOMICS_COLUMNS) <= set(legacy_df.columns)
    missing_raw_columns = sorted(raw_columns - set(legacy_df.columns))
    if not (has_current_compendium or has_legacy_compendium):
        missing_raw_columns.extend(LEGACY_CURATED_PROTEOMICS_COLUMNS)
    if missing_raw_columns:
        raise LegacyLocalizationCheckpointError(
            "subcellular_localization checkpoint lacks raw source-level localization "
            f"fields; cannot infer required schema v{LOCALIZATION_CHECKPOINT_SCHEMA_VERSION} "
            f"from localization_score_normalized. Re-run localization evidence "
            f"processing before scoring (missing raw fields: {', '.join(missing_raw_columns)})."
        )

    # Import lazily to keep the persistence module independent of the full
    # transform/fetch import path during package initialization.
    from usher_pipeline.evidence.localization.fetch import fetch_cilia_compendium
    from usher_pipeline.evidence.localization.transform import (
        classify_evidence_type,
        score_localization,
    )

    # Recompute membership from the persisted gene symbols using the current
    # alias-normalized v3 compendium sets. Legacy/current flags are stale
    # migration inputs and must not override the v3 source membership.
    compendium_df = fetch_cilia_compendium(
        gene_ids=legacy_df["gene_id"].to_list(),
        gene_symbol_map=legacy_df.select(["gene_id", "gene_symbol"]),
    ).select(["gene_id", *CURATED_COMPENDIUM_COLUMNS])
    stale_compendium_columns = [
        *CURATED_COMPENDIUM_COLUMNS,
        *LEGACY_CURATED_PROTEOMICS_COLUMNS,
    ]
    legacy_df = legacy_df.drop(
        [column for column in stale_compendium_columns if column in legacy_df.columns]
    ).join(compendium_df, on="gene_id", how="left")

    migrated_df = score_localization(classify_evidence_type(legacy_df))
    store.save_dataframe(
        migrated_df,
        LOCALIZATION_TABLE_NAME,
        description=_checkpoint_description("Reprocessed legacy localization checkpoint"),
        replace=True,
    )
    return {
        "status": "reprocessed",
        "migrated": True,
        "missing_columns": missing_required_columns,
        "schema_version": LOCALIZATION_CHECKPOINT_SCHEMA_VERSION,
        "row_count": migrated_df.height,
    }


def load_to_duckdb(
    df: pl.DataFrame,
    store: PipelineStore,
    provenance: ProvenanceTracker,
    description: str = ""
) -> None:
    """Save localization evidence DataFrame to DuckDB with provenance.

    Creates or replaces the subcellular_localization table (idempotent).
    Records provenance step with summary statistics.

    Args:
        df: Processed localization DataFrame with evidence types and scores
        store: PipelineStore instance for DuckDB persistence
        provenance: ProvenanceTracker instance for metadata recording
        description: Optional description for checkpoint metadata
    """
    logger.info("localization_load_start", row_count=len(df))

    missing_columns = [
        column for column in LOCALIZATION_CHECKPOINT_REQUIRED_COLUMNS
        if column not in df.columns
    ]
    if missing_columns:
        raise LegacyLocalizationCheckpointError(
            "Localization checkpoint is missing required schema fields: "
            f"{', '.join(missing_columns)}"
        )
    version_values = _checkpoint_version(df)
    if version_values != {LOCALIZATION_CHECKPOINT_SCHEMA_VERSION}:
        raise LegacyLocalizationCheckpointError(
            "Localization checkpoint must persist exactly schema version "
            f"{LOCALIZATION_CHECKPOINT_SCHEMA_VERSION}; found {sorted(version_values)}"
        )

    # Calculate summary statistics for provenance
    experimental_count = df.filter(pl.col("evidence_type") == "experimental").height
    curated_compendium_count = df.filter(
        pl.col("evidence_type") == "curated_compendium"
    ).height
    mixed_count = df.filter(pl.col("evidence_type") == "mixed").height
    computational_count = df.filter(pl.col("evidence_type") == "computational").height
    both_count = mixed_count + df.filter(pl.col("evidence_type") == "both").height
    none_count = df.filter(pl.col("evidence_type") == "none").height

    cilia_compartment_count = df.filter(
        (pl.col("compartment_cilia") == True) | (pl.col("compartment_centrosome") == True)
    ).height

    mean_localization_score = df["localization_score_normalized"].mean()

    # Count genes with high cilia proximity (> 0.5)
    high_proximity_count = df.filter(
        pl.col("cilia_proximity_score") > 0.5
    ).height

    # Save to DuckDB with CREATE OR REPLACE (idempotent)
    store.save_dataframe(
        df=df,
        table_name=LOCALIZATION_TABLE_NAME,
        description=_checkpoint_description(description),
        replace=True
    )

    # Record provenance step with details
    provenance.record_step("load_subcellular_localization", {
        "row_count": len(df),
        "experimental_count": experimental_count,
        "curated_compendium_count": curated_compendium_count,
        "mixed_count": mixed_count,
        "computational_count": computational_count,
        "both_count": both_count,
        "none_count": none_count,
        "cilia_compartment_count": cilia_compartment_count,
        "high_proximity_count": high_proximity_count,
        "mean_localization_score": float(mean_localization_score) if mean_localization_score is not None else None,
        "hpa_reliability_semantics": (
            "Enhanced, Supported, Approved, and Uncertain are antibody-staining "
            "reliability categories; modality is antibody_staining and reliability "
            "weights are recorded separately; none is a computational prediction class"
        ),
        "hpa_evidence_modality": HPA_EVIDENCE_MODALITY,
        "hpa_reliability_weights": HPA_RELIABILITY_WEIGHTS,
        "localization_checkpoint_schema_version": LOCALIZATION_CHECKPOINT_SCHEMA_VERSION,
        "curated_compendium_provenance": CURATED_COMPENDIUM_PROVENANCE,
    })

    logger.info(
        "localization_load_complete",
        row_count=len(df),
        experimental=experimental_count,
        curated_compendium=curated_compendium_count,
        mixed=mixed_count,
        computational=computational_count,
        both=both_count,
        none=none_count,
        cilia_compartment=cilia_compartment_count,
        high_proximity=high_proximity_count,
        mean_score=mean_localization_score,
    )


def query_cilia_localized(
    store: PipelineStore,
    proximity_threshold: float = 0.5
) -> pl.DataFrame:
    """Query genes with high cilia proximity scores from DuckDB.

    Demonstrates DuckDB query capability and provides helper for downstream
    analysis. Returns genes with strong localization evidence for cilia-related
    compartments.

    Args:
        store: PipelineStore instance
        proximity_threshold: Minimum cilia_proximity_score (default: 0.5)

    Returns:
        DataFrame with cilia-localized genes sorted by localization score
        Columns: gene_id, gene_symbol, evidence_type, compartment flags,
                 cilia_proximity_score, localization_score_normalized
    """
    logger.info("localization_query_cilia", proximity_threshold=proximity_threshold)

    # Query DuckDB: genes with high cilia proximity
    df = store.execute_query(
        """
        SELECT gene_id, gene_symbol, evidence_type,
               compartment_cilia, compartment_centrosome, compartment_basal_body,
               in_cilia_compendium, in_centrosome_compendium,
               cilia_proximity_score, localization_score_normalized
        FROM subcellular_localization
        WHERE cilia_proximity_score > ?
        ORDER BY localization_score_normalized DESC, cilia_proximity_score DESC
        """,
        params=[proximity_threshold]
    )

    logger.info("localization_query_complete", result_count=len(df))

    return df

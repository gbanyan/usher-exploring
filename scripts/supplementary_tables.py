"""Generate supplementary tables of merged (deduplicated) and excluded genes.

Reviewer request (F5): list the gene-symbol-level merges (multiple Ensembl IDs
collapsed to one canonical ID) and the genes excluded from the tiered output.

Outputs (data/report/supplementary/):
  - table_s1_merged_genes.tsv   one row per gene symbol that had >1 Ensembl ID
  - table_s2_excluded_genes.tsv genes scored but excluded from the tiered list
"""
from pathlib import Path

import duckdb
import polars as pl

OUT = Path("data/report/supplementary")
OUT.mkdir(parents=True, exist_ok=True)

con = duckdb.connect("data/pipeline.duckdb", read_only=True)

# MANE Select canonical Ensembl gene IDs (preferred during deduplication)
mane_ids = set(
    r[0] for r in con.execute(
        "SELECT DISTINCT ensembl_gene_id FROM mane_select WHERE mane_status IS NOT NULL"
    ).fetchall()
)

# Gene universe: multiple Ensembl IDs per symbol
universe = con.execute(
    "SELECT gene_id, gene_symbol FROM gene_universe"
).pl()
# Retained ID per symbol = the one that survived into scored_genes
retained = con.execute(
    "SELECT gene_id AS retained_gene_id, gene_symbol FROM scored_genes"
).pl()

# --- Table S1: merged symbols (>1 Ensembl ID) ---
counts = universe.group_by("gene_symbol").agg(
    pl.col("gene_id").n_unique().alias("n_ensembl_ids"),
    pl.col("gene_id").sort().str.join("; ").alias("all_ensembl_ids"),
)
merged = (
    counts.filter(pl.col("n_ensembl_ids") > 1)
    .join(retained, on="gene_symbol", how="left")
    .with_columns(
        pl.col("retained_gene_id")
        .map_elements(
            lambda x: "MANE Select canonical"
            if x in mane_ids
            else "gnomAD-recognized or lowest Ensembl ID",
            return_dtype=pl.String,
        )
        .alias("selection_reason")
    )
    .select(
        "gene_symbol", "n_ensembl_ids", "retained_gene_id",
        "selection_reason", "all_ensembl_ids",
    )
    .sort("gene_symbol")
)
merged.write_csv(OUT / "table_s1_merged_genes.tsv", separator="\t")

# --- Table S2: excluded genes ---
# Tiered candidates are those written to candidates.tsv; everything scored but
# not tiered (composite < LOW threshold or insufficient evidence) is excluded.
tiered = pl.read_csv("data/report/candidates.tsv", separator="\t")["gene_id"]
scored = con.execute(
    "SELECT gene_id, gene_symbol, composite_score, evidence_count, quality_flag "
    "FROM scored_genes"
).pl()
excluded = (
    scored.filter(~pl.col("gene_id").is_in(tiered))
    .with_columns(
        pl.when(pl.col("composite_score").is_null())
        .then(pl.lit("no evidence (NULL composite)"))
        .when(pl.col("composite_score") < 0.2)
        .then(pl.lit("composite score < 0.2"))
        .otherwise(pl.lit("insufficient evidence"))
        .alias("exclusion_reason")
    )
    .select("gene_id", "gene_symbol", "composite_score", "evidence_count",
            "quality_flag", "exclusion_reason")
    .sort("composite_score", descending=True, nulls_last=True)
)
excluded.write_csv(OUT / "table_s2_excluded_genes.tsv", separator="\t")

con.close()

print(f"Table S1 (merged symbols): {merged.height} rows")
print(f"  MANE Select canonical retained: "
      f"{merged.filter(pl.col('selection_reason') == 'MANE Select canonical').height}")
print(f"Table S2 (excluded genes): {excluded.height} rows")
print(excluded['exclusion_reason'].value_counts())
print(f"Written to {OUT}/")

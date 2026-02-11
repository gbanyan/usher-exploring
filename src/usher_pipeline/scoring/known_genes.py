"""Known cilia and Usher syndrome gene compilation."""

import polars as pl
from usher_pipeline.persistence.duckdb_store import PipelineStore

# OMIM Usher syndrome genes (high-confidence disease genes)
# Source: OMIM database (omim.org) - Usher syndrome entries
# These genes are well-established causes of Usher syndrome
OMIM_USHER_GENES = frozenset([
    "MYO7A",    # USH1B
    "USH1C",    # USH1C (harmonin)
    "CDH23",    # USH1D
    "PCDH15",   # USH1F
    "USH1G",    # USH1G (SANS)
    "CIB2",     # USH1J
    "USH2A",    # USH2A
    "ADGRV1",   # USH2C (GPR98)
    "WHRN",     # USH2D (whirlin)
    "CLRN1",    # USH3A
])

# SYSCILIA Gold Standard (SCGS) v2 - Core ciliary genes subset
# Source: van Dam et al. (2021) MBoC - DOI: 10.1091/mbc.E21-05-0226
# Full SCGS v2 contains 686 genes; this is a curated ~30 gene subset of
# well-characterized ciliary components used as positive controls.
# For complete list, see publication supplementary data.
# Future enhancement: implement fetch_scgs_v2() to download full gene set.
SYSCILIA_SCGS_V2_CORE = frozenset([
    "IFT88",      # IFT-B core
    "IFT140",     # IFT-A core
    "IFT172",     # IFT-B core
    "BBS1",       # BBSome
    "BBS2",       # BBSome
    "BBS4",       # BBSome
    "BBS5",       # BBSome
    "BBS7",       # BBSome
    "BBS9",       # BBSome
    "BBS10",      # BBSome
    "RPGRIP1L",   # Transition zone
    "CEP290",     # Transition zone
    "ARL13B",     # Ciliary membrane
    "INPP5E",     # Ciliary membrane
    "TMEM67",     # MKS/JBTS
    "CC2D2A",     # MKS/JBTS
    "NPHP1",      # Nephronophthisis
    "NPHP3",      # Nephronophthisis
    "NPHP4",      # Nephronophthisis
    "RPGR",       # Retinal ciliopathy
    "CEP164",     # Centriole/basal body
    "OFD1",       # OFD syndrome
    "MKS1",       # Meckel syndrome
    "TCTN1",      # Tectonic complex
    "TCTN2",      # Tectonic complex
    "TMEM216",    # MKS/JBTS
    "TMEM231",    # MKS/JBTS
    "TMEM138",    # MKS/JBTS
])


def compile_known_genes() -> pl.DataFrame:
    """
    Compile known cilia/Usher genes into a structured DataFrame.

    Combines OMIM Usher syndrome genes and SYSCILIA SCGS v2 core genes
    into a single reference set for exclusion filtering and positive
    control validation.

    Returns:
        DataFrame with columns:
        - gene_symbol (str): Gene symbol
        - source (str): "omim_usher" or "syscilia_scgs_v2"
        - confidence (str): "HIGH" for all entries in this curated set

    Notes:
        - Genes appearing in both lists will have two rows (one per source)
        - De-duplication is NOT performed on gene_symbol to preserve provenance
        - Total rows = len(OMIM_USHER_GENES) + len(SYSCILIA_SCGS_V2_CORE)
    """
    # Create DataFrames for each gene set
    omim_df = pl.DataFrame({
        "gene_symbol": list(OMIM_USHER_GENES),
        "source": ["omim_usher"] * len(OMIM_USHER_GENES),
        "confidence": ["HIGH"] * len(OMIM_USHER_GENES),
    })

    syscilia_df = pl.DataFrame({
        "gene_symbol": list(SYSCILIA_SCGS_V2_CORE),
        "source": ["syscilia_scgs_v2"] * len(SYSCILIA_SCGS_V2_CORE),
        "confidence": ["HIGH"] * len(SYSCILIA_SCGS_V2_CORE),
    })

    # Concatenate both gene sets
    combined = pl.concat([omim_df, syscilia_df])

    return combined


def load_known_genes_to_duckdb(store: PipelineStore) -> int:
    """
    Load known cilia/Usher genes into DuckDB.

    Args:
        store: PipelineStore instance for database access

    Returns:
        Number of unique gene symbols loaded

    Notes:
        - Table name: known_cilia_genes
        - Replaces existing table if present (CREATE OR REPLACE pattern)
    """
    df = compile_known_genes()

    store.save_dataframe(
        df=df,
        table_name="known_cilia_genes",
        description="Known cilia and Usher syndrome genes for positive control validation",
        replace=True,
    )

    # Return count of unique gene symbols
    unique_count = df["gene_symbol"].n_unique()
    return unique_count

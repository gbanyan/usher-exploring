"""Unit tests for bulk literature fetch (gene2pubmed + MeSH batch queries)."""

import gzip
from pathlib import Path

import polars as pl
import pytest

from usher_pipeline.evidence.literature.fetch import (
    parse_gene2pubmed,
    parse_gene_info,
    build_gene_pmid_map,
    count_context_intersections,
)


# Sample gene2pubmed TSV (real format from NCBI)
SAMPLE_GENE2PUBMED = (
    "#tax_id\tGeneID\tPubMed_ID\n"
    "9606\t1\t30591045\n"
    "9606\t1\t30592043\n"
    "9606\t1\t28854372\n"
    "9606\t2\t12345678\n"
    "9606\t2\t30591045\n"
    "9606\t3\t99999999\n"
    "10090\t100\t11111111\n"
)

# Sample gene_info TSV (real format from NCBI)
SAMPLE_GENE_INFO = (
    "#tax_id\tGeneID\tSymbol\tLocusTag\tSynonyms\tdbXrefs\tchromosome\tmap_location\t"
    "description\ttype_of_gene\tSymbol_from_nomenclature_authority\tFull_name_from_nomenclature_authority\t"
    "Nomenclature_status\tOther_designations\tModification_date\tFeature_type\n"
    "9606\t1\tA1BG\t-\tA1B|ABG\tMIM:138670|HGNC:HGNC:5\t19\t19q13.43\t"
    "alpha-1-B glycoprotein\tprotein-coding\tA1BG\talpha-1-B glycoprotein\tO\t"
    "alpha-1B-glycoprotein\t20240101\t-\n"
    "9606\t2\tA2M\t-\tA2MD\tMIM:103950|HGNC:HGNC:7\t12\t12p13.31\t"
    "alpha-2-macroglobulin\tprotein-coding\tA2M\talpha-2-macroglobulin\tO\t"
    "alpha-2-macroglobulin\t20240101\t-\n"
    "9606\t3\tA2MP1\t-\tA2MP\tHGNC:HGNC:8\t12\t12p13.31\t"
    "alpha-2-macroglobulin pseudogene 1\tpseudo\tA2MP1\talpha-2-macroglobulin pseudogene 1\tO\t-\t20240101\t-\n"
)


def _write_gz(tmp_path: Path, filename: str, content: str) -> Path:
    gz_path = tmp_path / filename
    with gzip.open(gz_path, "wt") as f:
        f.write(content)
    return gz_path


def test_parse_gene2pubmed_filters_human(tmp_path):
    """gene2pubmed parser should only return human (tax_id=9606) entries."""
    gz_path = _write_gz(tmp_path, "gene2pubmed.gz", SAMPLE_GENE2PUBMED)
    df = parse_gene2pubmed(gz_path)

    assert df.height == 6, f"Expected 6 human rows, got {df.height}"
    assert "tax_id" not in df.columns, "tax_id should be dropped after filtering"
    assert set(df.columns) == {"gene_id", "pmid"}


def test_parse_gene2pubmed_types(tmp_path):
    """gene_id and pmid should be integers."""
    gz_path = _write_gz(tmp_path, "gene2pubmed.gz", SAMPLE_GENE2PUBMED)
    df = parse_gene2pubmed(gz_path)

    assert df["gene_id"].dtype == pl.Int64
    assert df["pmid"].dtype == pl.Int64


def test_parse_gene_info(tmp_path):
    """gene_info parser should return gene_id -> symbol mapping for human protein-coding genes."""
    gz_path = _write_gz(tmp_path, "gene_info.gz", SAMPLE_GENE_INFO)
    df = parse_gene_info(gz_path)

    assert set(df.columns) == {"gene_id", "gene_symbol"}
    # Should only include protein-coding (not pseudo)
    assert df.height == 2
    symbols = df["gene_symbol"].to_list()
    assert "A1BG" in symbols
    assert "A2M" in symbols
    assert "A2MP1" not in symbols


def test_build_gene_pmid_map(tmp_path):
    """build_gene_pmid_map should return dict of gene_symbol -> set of PMIDs."""
    g2p_gz = _write_gz(tmp_path, "gene2pubmed.gz", SAMPLE_GENE2PUBMED)
    gi_gz = _write_gz(tmp_path, "gene_info.gz", SAMPLE_GENE_INFO)

    gene2pubmed = parse_gene2pubmed(g2p_gz)
    gene_info = parse_gene_info(gi_gz)

    pmid_map = build_gene_pmid_map(gene2pubmed, gene_info)

    assert isinstance(pmid_map, dict)
    assert "A1BG" in pmid_map
    assert "A2M" in pmid_map
    assert len(pmid_map["A1BG"]) == 3
    assert len(pmid_map["A2M"]) == 2
    assert 30591045 in pmid_map["A1BG"]
    assert 30591045 in pmid_map["A2M"]


def test_count_context_intersections():
    """count_context_intersections should compute per-gene counts from PMID sets."""
    gene_pmid_map = {
        "GENE1": {1, 2, 3, 4, 5},
        "GENE2": {10, 20},
        "GENE3": set(),
    }

    context_pmid_sets = {
        "cilia": {1, 2, 10, 100},
        "sensory": {2, 3, 20, 200},
        "cytoskeleton": {4, 100},
        "cell_polarity": set(),
    }

    direct_exp_pmids = {1, 10}
    hts_pmids = {5, 20}

    df = count_context_intersections(
        gene_pmid_map=gene_pmid_map,
        context_pmid_sets=context_pmid_sets,
        direct_experimental_pmids=direct_exp_pmids,
        hts_pmids=hts_pmids,
        pipeline_symbols=["GENE1", "GENE2", "GENE3"],
    )

    assert df.height == 3

    g1 = df.filter(pl.col("gene_symbol") == "GENE1")
    assert g1["total_pubmed_count"][0] == 5
    assert g1["cilia_context_count"][0] == 2
    assert g1["sensory_context_count"][0] == 2
    assert g1["cytoskeleton_context_count"][0] == 1
    assert g1["cell_polarity_context_count"][0] == 0
    assert g1["direct_experimental_count"][0] == 1
    assert g1["hts_screen_count"][0] == 1

    # GENE3 with empty set (in gene2pubmed but 0 publications) gets 0
    g3 = df.filter(pl.col("gene_symbol") == "GENE3")
    assert g3["total_pubmed_count"][0] == 0


def test_count_context_null_for_missing_gene():
    """Genes in pipeline but NOT in gene2pubmed should get NULL counts (not 0)."""
    gene_pmid_map = {"GENE1": {1, 2}}
    context_pmid_sets = {
        "cilia": {1},
        "sensory": set(),
        "cytoskeleton": set(),
        "cell_polarity": set(),
    }

    df = count_context_intersections(
        gene_pmid_map=gene_pmid_map,
        context_pmid_sets=context_pmid_sets,
        direct_experimental_pmids=set(),
        hts_pmids=set(),
        pipeline_symbols=["GENE1", "GENE_MISSING"],
    )

    assert df.height == 2

    # GENE_MISSING not in gene2pubmed -> NULL
    missing = df.filter(pl.col("gene_symbol") == "GENE_MISSING")
    assert missing["total_pubmed_count"][0] is None
    assert missing["cilia_context_count"][0] is None

    # GENE1 is in gene2pubmed -> has real counts
    g1 = df.filter(pl.col("gene_symbol") == "GENE1")
    assert g1["total_pubmed_count"][0] == 2
    assert g1["cilia_context_count"][0] == 1

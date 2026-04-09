"""Unit tests for MANE Select fetch and parse."""

import gzip
from pathlib import Path

import polars as pl
import pytest

from usher_pipeline.gene_mapping.mane_select import (
    MANE_SELECT_URL_TEMPLATE,
    fetch_mane_select,
    parse_mane_select,
)

# Minimal MANE summary TSV (real column names from NCBI)
SAMPLE_MANE_TSV = (
    "#NCBI_GeneID\tEnsembl_Gene\tHGNC_ID\tsymbol\tname\tRefSeq_nuc\tRefSeq_prot\t"
    "Ensembl_nuc\tEnsembl_prot\tMANE_status\tGRCh38_chr\tchr_start\tchr_end\tchr_strand\n"
    "7842\tENSG00000163646.18\tHGNC:2026\tCLRN1\tclarin 1\tNM_174878.3\tNP_777367.1\t"
    "ENST00000295886.10\tENSP00000295886.5\tMANE Select\t3\t150918930\t150967292\t-\n"
    "7399\tENSG00000075624.17\tHGNC:132\tACTB\tactin beta\tNM_001101.5\tNP_001092.1\t"
    "ENST00000646024.1\tENSP00000493376.1\tMANE Select\t7\t5527151\t5530601\t-\n"
    "7884\tENSG00000163646.18\tHGNC:2026\tCLRN1\tclarin 1\tNM_001256781.2\tNP_001243710.1\t"
    "ENST00000419101.5\tENSP00000395753.1\tMANE Plus Clinical\t3\t150926154\t150967292\t-\n"
)


def _write_mane_gz(tmp_path: Path) -> Path:
    """Write sample MANE TSV as gzipped file."""
    gz_path = tmp_path / "MANE.GRCh38.v1.3.summary.txt.gz"
    with gzip.open(gz_path, "wt") as f:
        f.write(SAMPLE_MANE_TSV)
    return gz_path


def test_parse_mane_select_columns(tmp_path):
    """parse_mane_select returns expected columns with stripped version IDs."""
    gz_path = _write_mane_gz(tmp_path)
    df = parse_mane_select(gz_path)

    assert set(df.columns) == {
        "ensembl_gene_id",
        "ensembl_transcript_id",
        "gene_symbol",
        "refseq_transcript_id",
        "mane_status",
    }


def test_parse_mane_select_strips_version(tmp_path):
    """Ensembl IDs must have version suffix stripped."""
    gz_path = _write_mane_gz(tmp_path)
    df = parse_mane_select(gz_path)

    gene_ids = df["ensembl_gene_id"].to_list()
    assert "ENSG00000163646" in gene_ids, "Version suffix should be stripped"
    assert not any("." in gid for gid in gene_ids), "No version dots should remain"

    tx_ids = df["ensembl_transcript_id"].to_list()
    assert not any("." in tid for tid in tx_ids), "Transcript version dots should be stripped"


def test_parse_mane_select_row_count(tmp_path):
    """Sample data has 3 rows (2 MANE Select + 1 MANE Plus Clinical)."""
    gz_path = _write_mane_gz(tmp_path)
    df = parse_mane_select(gz_path)
    assert df.height == 3


def test_parse_mane_select_status_values(tmp_path):
    """MANE status should be preserved as-is."""
    gz_path = _write_mane_gz(tmp_path)
    df = parse_mane_select(gz_path)

    statuses = df["mane_status"].unique().sort().to_list()
    assert statuses == ["MANE Plus Clinical", "MANE Select"]


def test_fetch_mane_select_skips_existing(tmp_path):
    """fetch_mane_select should skip download if file exists and force=False."""
    gz_path = _write_mane_gz(tmp_path)
    result = fetch_mane_select(data_dir=tmp_path, version="1.3", force=False)
    assert result == gz_path

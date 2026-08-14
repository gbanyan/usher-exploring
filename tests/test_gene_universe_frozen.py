"""Focused tests for the frozen Ensembl gene-universe source."""

import gzip
import hashlib
import json
from types import SimpleNamespace

import duckdb
import polars as pl
import pytest

from usher_pipeline.cli.setup_cmd import (
    _build_cache_only_gene_universe,
    _gene_source_checkpoint_metadata,
    _has_current_gene_universe_checkpoint,
    _load_exact_legacy_mapping,
    _load_local_mane_cache,
)
from usher_pipeline.gene_mapping.universe import (
    fetch_protein_coding_genes,
    load_frozen_ensembl_gene_source,
)
from usher_pipeline.gene_mapping.validator import validate_gene_universe


def _write_gtf(path, rows):
    with gzip.open(path, "wt", encoding="utf-8") as output:
        output.write("#!genome-build GRCh38\n")
        for gene_id, symbol, biotype in rows:
            gene_name = (
                f' gene_name "{symbol}";'
                if symbol is not None
                else ""
            )
            output.write(
                "1\tensembl\tgene\t1\t10\t.\t+\t.\t"
                f'gene_id "{gene_id}";{gene_name} '
                f'gene_biotype "{biotype}";\n'
            )


class StubCheckpointStore:
    def __init__(self, description):
        self.description = description

    def list_checkpoints(self):
        return [{"table_name": "gene_universe", "description": self.description}]


def _current_checkpoint(tmp_path):
    source_filename = "Homo_sapiens.GRCh38.113.gtf.gz"
    source_path = tmp_path / source_filename
    _write_gtf(source_path, [("ENSG00000000001", "GENE1", "protein_coding")])
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source_url = (
        "https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/"
        f"{source_filename}"
    )
    config = SimpleNamespace(
        data_dir=tmp_path,
        versions=SimpleNamespace(
            ensembl_release=113,
            ensembl_gene_source=source_filename,
            ensembl_gene_source_url=source_url,
            ensembl_gene_source_sha256=digest,
        ),
    )
    metadata = _gene_source_checkpoint_metadata(config, source_path)
    return config, source_path, StubCheckpointStore(
        json.dumps(metadata, sort_keys=True)
    )


def test_loader_filters_each_id_by_gene_biotype_not_symbol(tmp_path):
    """Symbols are metadata; only the per-ID GTF biotype controls retention."""
    source_path = tmp_path / "Homo_sapiens.GRCh38.113.gtf.gz"
    _write_gtf(source_path, [
        ("ENSG00000000001", "LINC_PROTEIN", "protein_coding"),
        ("ENSG00000000002", "CODING_NAME", "lncRNA"),
        ("ENSG00000000003", "GENE3", "protein_coding"),
        ("ENSG00000000004", "LINC_AMBIGUOUS", "protein_coding"),
        ("ENSG00000000004", "LINC_AMBIGUOUS", "lncRNA"),
    ])

    expected_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source = load_frozen_ensembl_gene_source(
        source_path,
        ensembl_release=113,
        expected_sha256=expected_sha256,
        source_url=(
            "https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/"
            "Homo_sapiens.GRCh38.113.gtf.gz"
        ),
    )

    assert source.genes == ["ENSG00000000001", "ENSG00000000003"]
    assert all(
        source.gene_biotypes[gene_id] == frozenset({"protein_coding"})
        for gene_id in source.genes
    )
    assert source.metadata["gene_biotype"] == "protein_coding"
    assert source.metadata["source_filename"] == "Homo_sapiens.GRCh38.113.gtf.gz"
    assert source.metadata["ambiguous_or_non_protein_coding_gene_count"] == 2
    assert source.gene_symbols == {
        "ENSG00000000001": "LINC_PROTEIN",
        "ENSG00000000003": "GENE3",
    }
    assert source.metadata["gtf_gene_name_count"] == 2
    assert source.metadata["missing_or_ambiguous_gene_name_count"] == 0


def test_loader_records_unresolved_gtf_gene_names(tmp_path):
    source_path = tmp_path / "Homo_sapiens.GRCh38.113.gtf.gz"
    _write_gtf(source_path, [
        ("ENSG00000000001", None, "protein_coding"),
        ("ENSG00000000002", "GENE2", "protein_coding"),
    ])
    expected_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()

    source = load_frozen_ensembl_gene_source(
        source_path,
        ensembl_release=113,
        expected_sha256=expected_sha256,
        source_url=(
            "https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/"
            "Homo_sapiens.GRCh38.113.gtf.gz"
        ),
    )

    assert source.gene_symbols["ENSG00000000001"] is None
    assert source.gene_symbols["ENSG00000000002"] == "GENE2"
    assert source.metadata["gtf_gene_name_count"] == 1
    assert source.metadata["missing_or_ambiguous_gene_name_count"] == 1


def test_loader_enforces_frozen_source_sha256(tmp_path):
    source_path = tmp_path / "Homo_sapiens.GRCh38.113.gtf.gz"
    _write_gtf(source_path, [("ENSG00000000001", "GENE1", "protein_coding")])
    expected_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()

    source = load_frozen_ensembl_gene_source(
        source_path,
        ensembl_release=113,
        expected_sha256=expected_sha256,
        source_url=(
            "https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/"
            "Homo_sapiens.GRCh38.113.gtf.gz"
        ),
    )

    assert source.metadata["source_sha256"] == expected_sha256


def test_loader_rejects_source_sha256_mismatch(tmp_path):
    source_path = tmp_path / "Homo_sapiens.GRCh38.113.gtf.gz"
    _write_gtf(source_path, [("ENSG00000000001", "GENE1", "protein_coding")])

    try:
        load_frozen_ensembl_gene_source(
            source_path,
            ensembl_release=113,
            expected_sha256="0" * 64,
            source_url=(
                "https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/"
                "Homo_sapiens.GRCh38.113.gtf.gz"
            ),
        )
    except ValueError as error:
        assert "SHA-256 mismatch" in str(error)
    else:
        raise AssertionError("expected frozen source digest mismatch")


def test_loader_rejects_release_mismatch(tmp_path):
    """Release 114 cannot parse a release-113 source under a new label."""
    source_path = tmp_path / "Homo_sapiens.GRCh38.113.gtf.gz"
    _write_gtf(source_path, [("ENSG00000000001", "GENE1", "protein_coding")])
    expected_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()

    try:
        load_frozen_ensembl_gene_source(
            source_path,
            ensembl_release=114,
            expected_sha256=expected_sha256,
            source_url=(
                "https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/"
                "Homo_sapiens.GRCh38.113.gtf.gz"
            ),
        )
    except ValueError as error:
        assert "source filename" in str(error) or "same release" in str(error)
    else:
        raise AssertionError("expected release mismatch")


def test_loader_rejects_missing_checksum(tmp_path):
    source_path = tmp_path / "Homo_sapiens.GRCh38.113.gtf.gz"
    _write_gtf(source_path, [("ENSG00000000001", "GENE1", "protein_coding")])

    try:
        load_frozen_ensembl_gene_source(
            source_path,
            ensembl_release=113,
            expected_sha256=None,
            source_url=(
                "https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/"
                "Homo_sapiens.GRCh38.113.gtf.gz"
            ),
        )
    except (TypeError, ValueError) as error:
        assert "expected_sha256" in str(error)
    else:
        raise AssertionError("expected missing checksum rejection")


def test_fetch_old_signature_is_rejected_with_migration_message():
    with pytest.raises(TypeError, match="deprecated.*source_path"):
        fetch_protein_coding_genes(113)


def test_gene_universe_validation_checks_per_id_biotype():
    result = validate_gene_universe(
        ["ENSG00000000001"] * 19000,
        gene_biotypes={"ENSG00000000001": "lncRNA"},
    )

    assert result.passed is False
    assert any("gene_biotype=protein_coding" in message for message in result.messages)


def test_old_mygene_checkpoint_is_not_reused(tmp_path):
    """A pre-remediation checkpoint cannot satisfy the frozen-source gate."""
    config, source_path, new_store = _current_checkpoint(tmp_path)
    digest = config.versions.ensembl_gene_source_sha256
    source_filename = "Homo_sapiens.GRCh38.113.gtf.gz"
    source_url = (
        "https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/"
        f"{source_filename}"
    )
    config = SimpleNamespace(
        data_dir=tmp_path,
        versions=SimpleNamespace(
            ensembl_release=113,
            ensembl_gene_source=source_filename,
            ensembl_gene_source_url=source_url,
            ensembl_gene_source_sha256=digest,
        ),
    )
    old_store = StubCheckpointStore(
        "Protein-coding genes from Ensembl 113 with HGNC mapping"
    )
    mismatched_config = SimpleNamespace(
        data_dir=tmp_path,
        versions=SimpleNamespace(
            ensembl_release=114,
            ensembl_gene_source="Homo_sapiens.GRCh38.114.gtf.gz",
            ensembl_gene_source_url=source_url.replace(
                "release-113", "release-114"
            ).replace(".113.", ".114."),
            ensembl_gene_source_sha256=digest,
        ),
    )
    (tmp_path / mismatched_config.versions.ensembl_gene_source).write_bytes(
        source_path.read_bytes()
    )

    assert _has_current_gene_universe_checkpoint(config, old_store) is False
    assert _has_current_gene_universe_checkpoint(config, new_store) is True
    assert _has_current_gene_universe_checkpoint(mismatched_config, new_store) is False


def test_checkpoint_is_rejected_when_frozen_source_cache_is_missing(tmp_path):
    config, source_path, store = _current_checkpoint(tmp_path)

    source_path.unlink()

    assert _has_current_gene_universe_checkpoint(config, store) is False


def test_checkpoint_is_rejected_when_frozen_source_cache_is_modified(tmp_path):
    config, source_path, store = _current_checkpoint(tmp_path)

    source_path.write_bytes(source_path.read_bytes() + b"modified")

    assert _has_current_gene_universe_checkpoint(config, store) is False


def test_cache_only_mapping_uses_exact_id_fallbacks_and_drops_stale_rows(tmp_path):
    source_path = tmp_path / "Homo_sapiens.GRCh38.113.gtf.gz"
    _write_gtf(source_path, [
        ("ENSG00000000001", "GTF1", "protein_coding"),
        ("ENSG00000000002", None, "protein_coding"),
        ("ENSG00000000003", None, "protein_coding"),
    ])
    expected_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source = load_frozen_ensembl_gene_source(
        source_path,
        ensembl_release=113,
        expected_sha256=expected_sha256,
        source_url=(
            "https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/"
            "Homo_sapiens.GRCh38.113.gtf.gz"
        ),
    )

    mapping_db = tmp_path / "pipeline_source.duckdb"
    connection = duckdb.connect(str(mapping_db))
    connection.execute(
        """
        CREATE TABLE gene_universe AS
        SELECT * FROM (VALUES
            ('ENSG00000000001', 'OLD1', 'P1'),
            ('ENSG00000000002', 'FALLBACK2', 'P2'),
            ('ENSG00000099999', 'STALE', 'STALEP')
        ) AS t(gene_id, gene_symbol, uniprot_accession)
        """
    )
    connection.close()

    result, counts = _build_cache_only_gene_universe(source, mapping_db)

    assert result["gene_id"].to_list() == source.genes
    assert result["gene_symbol"].to_list() == ["GTF1", "FALLBACK2", "ENSG00000000003"]
    assert result["gene_symbol_source"].to_list() == [
        "gtf_gene_name",
        "legacy_db_exact_id_fallback",
        "gene_id_fallback_unresolved",
    ]
    assert result["uniprot_accession"].to_list() == ["P1", "P2", None]
    assert result["uniprot_source"].to_list() == [
        "legacy_db_exact_id",
        "legacy_db_exact_id",
        "unresolved",
    ]
    assert counts == {
        "gene_symbol_gtf_native": 1,
        "gene_symbol_legacy_exact_id_fallback": 1,
        "gene_symbol_unresolved": 1,
        "uniprot_legacy_exact_id": 2,
        "uniprot_unresolved": 1,
        "legacy_mapping_rows_intersecting_gtf": 2,
        "legacy_mapping_rows_outside_gtf": 1,
    }


def test_cache_only_mapping_rejects_duplicate_exact_ids(tmp_path):
    source_path = tmp_path / "Homo_sapiens.GRCh38.113.gtf.gz"
    _write_gtf(source_path, [
        ("ENSG00000000001", "GENE1", "protein_coding"),
    ])
    expected_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source = load_frozen_ensembl_gene_source(
        source_path,
        ensembl_release=113,
        expected_sha256=expected_sha256,
        source_url=(
            "https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/"
            "Homo_sapiens.GRCh38.113.gtf.gz"
        ),
    )
    mapping_db = tmp_path / "pipeline_source.duckdb"
    connection = duckdb.connect(str(mapping_db))
    connection.execute(
        """
        CREATE TABLE gene_universe AS
        SELECT * FROM (VALUES
            ('ENSG00000000001', 'GENE1', 'P1'),
            ('ENSG00000000001', 'GENE1_ALT', 'P1')
        ) AS t(gene_id, gene_symbol, uniprot_accession)
        """
    )
    connection.close()

    with pytest.raises(ValueError, match="duplicate Ensembl IDs"):
        _load_exact_legacy_mapping(mapping_db)


def test_cache_only_mane_requires_local_matching_cache(tmp_path):
    config = SimpleNamespace(
        data_dir=tmp_path,
        versions=SimpleNamespace(mane_version="1.3"),
    )
    store = SimpleNamespace()

    with pytest.raises(FileNotFoundError, match="refusing to download"):
        _load_local_mane_cache(config, store, {"ENSG00000000001"})

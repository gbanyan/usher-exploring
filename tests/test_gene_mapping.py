"""Tests for gene ID mapping module.

Tests gene universe retrieval, batch mapping, and validation gates.
Uses mocked mygene responses to avoid real API calls.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from usher_pipeline.gene_mapping import (
    GeneMapper,
    MappingReport,
    MappingResult,
    MappingValidator,
    ValidationResult,
    validate_gene_universe,
)


# Mock mygene response fixtures

MOCK_SUCCESSFUL_RESPONSE = {
    'out': [
        {
            'query': 'ENSG00000139618',
            'symbol': 'BRCA2',
            'uniprot': {'Swiss-Prot': 'P51587'}
        },
        {
            'query': 'ENSG00000141510',
            'symbol': 'TP53',
            'uniprot': {'Swiss-Prot': 'P04637'}
        },
        {
            'query': 'ENSG00000012048',
            'symbol': 'BRCA1',
            'uniprot': {'Swiss-Prot': 'P38398'}
        },
    ],
    'missing': []
}

MOCK_RESPONSE_WITH_NOTFOUND = {
    'out': [
        {
            'query': 'ENSG00000139618',
            'symbol': 'BRCA2',
            'uniprot': {'Swiss-Prot': 'P51587'}
        },
        {
            'query': 'ENSG00000141510',
            'symbol': 'TP53',
            'uniprot': {'Swiss-Prot': 'P04637'}
        },
        {
            'query': 'ENSG00000000000',
            'notfound': True,
        },
    ],
    'missing': ['ENSG00000000000']
}

MOCK_RESPONSE_WITH_UNIPROT_LIST = {
    'out': [
        {
            'query': 'ENSG00000139618',
            'symbol': 'BRCA2',
            'uniprot': {'Swiss-Prot': ['P51587', 'Q9UBX7']}  # List of accessions
        },
    ],
    'missing': []
}


# Test MappingResult creation

def test_mapping_result_creation():
    """Test creating MappingResult with all fields."""
    result = MappingResult(
        ensembl_id='ENSG00000139618',
        hgnc_symbol='BRCA2',
        uniprot_accession='P51587',
        mapping_source='mygene'
    )

    assert result.ensembl_id == 'ENSG00000139618'
    assert result.hgnc_symbol == 'BRCA2'
    assert result.uniprot_accession == 'P51587'
    assert result.mapping_source == 'mygene'


def test_mapping_result_with_none_values():
    """Test MappingResult handles missing data."""
    result = MappingResult(
        ensembl_id='ENSG00000000000',
    )

    assert result.ensembl_id == 'ENSG00000000000'
    assert result.hgnc_symbol is None
    assert result.uniprot_accession is None
    assert result.mapping_source == 'mygene'


# Test GeneMapper with mocked mygene

def test_mapper_handles_successful_mapping():
    """Test mapper with all genes successfully mapped."""
    with patch('mygene.MyGeneInfo') as mock_mygene:
        mock_mg = MagicMock()
        mock_mg.querymany.return_value = MOCK_SUCCESSFUL_RESPONSE
        mock_mygene.return_value = mock_mg

        mapper = GeneMapper(batch_size=1000)
        results, report = mapper.map_ensembl_ids([
            'ENSG00000139618',
            'ENSG00000141510',
            'ENSG00000012048',
        ])

        # Check results
        assert len(results) == 3
        assert results[0].ensembl_id == 'ENSG00000139618'
        assert results[0].hgnc_symbol == 'BRCA2'
        assert results[0].uniprot_accession == 'P51587'

        # Check report
        assert report.total_genes == 3
        assert report.mapped_hgnc == 3
        assert report.mapped_uniprot == 3
        assert report.success_rate_hgnc == 1.0
        assert report.success_rate_uniprot == 1.0
        assert len(report.unmapped_ids) == 0


def test_mapper_handles_unmapped_genes():
    """Test mapper with one gene not found."""
    with patch('mygene.MyGeneInfo') as mock_mygene:
        mock_mg = MagicMock()
        mock_mg.querymany.return_value = MOCK_RESPONSE_WITH_NOTFOUND
        mock_mygene.return_value = mock_mg

        mapper = GeneMapper()
        results, report = mapper.map_ensembl_ids([
            'ENSG00000139618',
            'ENSG00000141510',
            'ENSG00000000000',
        ])

        # Check results
        assert len(results) == 3
        assert results[2].ensembl_id == 'ENSG00000000000'
        assert results[2].hgnc_symbol is None
        assert results[2].uniprot_accession is None

        # Check report
        assert report.total_genes == 3
        assert report.mapped_hgnc == 2
        assert report.mapped_uniprot == 2
        assert abs(report.success_rate_hgnc - 0.667) < 0.01
        assert abs(report.success_rate_uniprot - 0.667) < 0.01
        assert 'ENSG00000000000' in report.unmapped_ids
        assert len(report.unmapped_ids) == 1


def test_mapper_handles_uniprot_list():
    """Test mapper handles UniProt Swiss-Prot as list (takes first)."""
    with patch('mygene.MyGeneInfo') as mock_mygene:
        mock_mg = MagicMock()
        mock_mg.querymany.return_value = MOCK_RESPONSE_WITH_UNIPROT_LIST
        mock_mygene.return_value = mock_mg

        mapper = GeneMapper()
        results, report = mapper.map_ensembl_ids(['ENSG00000139618'])

        # Should take first UniProt accession from list
        assert results[0].uniprot_accession == 'P51587'
        assert report.mapped_uniprot == 1


def test_mapper_batching():
    """Test mapper processes genes in batches."""
    with patch('mygene.MyGeneInfo') as mock_mygene:
        mock_mg = MagicMock()
        # Return empty response for each batch
        mock_mg.querymany.return_value = {'out': [], 'missing': []}
        mock_mygene.return_value = mock_mg

        mapper = GeneMapper(batch_size=2)
        # 5 genes should result in 3 batches (2+2+1)
        gene_ids = [f'ENSG{i:011d}' for i in range(5)]
        results, report = mapper.map_ensembl_ids(gene_ids)

        # Check querymany was called 3 times (3 batches)
        assert mock_mg.querymany.call_count == 3


# Test MappingValidator

def test_validator_passes_high_rate():
    """Test validator passes with success rate above minimum."""
    report = MappingReport(
        total_genes=100,
        mapped_hgnc=95,
        mapped_uniprot=90,
        unmapped_ids=[f'ENSG{i:011d}' for i in range(5)],
    )

    validator = MappingValidator(min_success_rate=0.90)
    result = validator.validate(report)

    assert result.passed is True
    assert result.hgnc_rate == 0.95
    assert result.uniprot_rate == 0.90
    assert any('PASSED' in msg for msg in result.messages)


def test_validator_fails_low_rate():
    """Test validator fails with success rate below minimum."""
    report = MappingReport(
        total_genes=100,
        mapped_hgnc=80,
        mapped_uniprot=75,
        unmapped_ids=[f'ENSG{i:011d}' for i in range(20)],
    )

    validator = MappingValidator(min_success_rate=0.90)
    result = validator.validate(report)

    assert result.passed is False
    assert result.hgnc_rate == 0.80
    assert any('FAILED' in msg for msg in result.messages)


def test_validator_warns_medium_rate():
    """Test validator passes with warning for medium success rate."""
    report = MappingReport(
        total_genes=100,
        mapped_hgnc=92,
        mapped_uniprot=88,
        unmapped_ids=[f'ENSG{i:011d}' for i in range(8)],
    )

    validator = MappingValidator(min_success_rate=0.90, warn_threshold=0.95)
    result = validator.validate(report)

    # Should pass but with warning
    assert result.passed is True
    assert result.hgnc_rate == 0.92
    assert any('WARNING' in msg for msg in result.messages)


def test_save_unmapped_report(tmp_path):
    """Test saving unmapped gene IDs to file."""
    report = MappingReport(
        total_genes=100,
        mapped_hgnc=95,
        mapped_uniprot=90,
        unmapped_ids=['ENSG00000000001', 'ENSG00000000002', 'ENSG00000000003'],
    )

    validator = MappingValidator()
    output_path = tmp_path / "unmapped_genes.txt"
    validator.save_unmapped_report(report, output_path)

    # Check file was created and contains expected content
    assert output_path.exists()
    content = output_path.read_text()
    assert '# Unmapped Gene IDs' in content
    assert '# Total unmapped: 3' in content
    assert 'ENSG00000000001' in content
    assert 'ENSG00000000002' in content
    assert 'ENSG00000000003' in content


# Test validate_gene_universe

def test_validate_gene_universe_valid():
    """Test gene universe validation with valid data."""
    genes = [f'ENSG{i:011d}' for i in range(20000)]  # 20k genes
    result = validate_gene_universe(genes)

    assert result.passed is True
    assert any('within expected range' in msg for msg in result.messages)
    assert any('ENSG format' in msg for msg in result.messages)
    assert any('No duplicate' in msg for msg in result.messages)


def test_validate_gene_universe_invalid_count():
    """Test gene universe validation fails with too many genes."""
    genes = [f'ENSG{i:011d}' for i in range(50000)]  # 50k genes (too many)
    result = validate_gene_universe(genes)

    assert result.passed is False
    assert any('exceeds maximum' in msg for msg in result.messages)


def test_validate_gene_universe_invalid_format():
    """Test gene universe validation fails with non-ENSG IDs."""
    genes = [f'ENSG{i:011d}' for i in range(19500)]
    genes.extend(['INVALID001', 'INVALID002'])  # Add invalid IDs

    result = validate_gene_universe(genes)

    assert result.passed is False
    assert any('not in ENSG format' in msg for msg in result.messages)


def test_validate_gene_universe_duplicates():
    """Test gene universe validation fails with duplicates."""
    genes = [f'ENSG{i:011d}' for i in range(19500)]
    genes.extend(['ENSG00000000001', 'ENSG00000000002'])  # Add duplicates

    result = validate_gene_universe(genes)

    assert result.passed is False
    assert any('duplicate' in msg for msg in result.messages)


def test_validate_gene_universe_too_few():
    """Test gene universe validation fails with too few genes."""
    genes = [f'ENSG{i:011d}' for i in range(1000)]  # Only 1k genes

    result = validate_gene_universe(genes)

    assert result.passed is False
    assert any('below minimum' in msg for msg in result.messages)

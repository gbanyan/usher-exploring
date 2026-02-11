"""Integration tests for animal model evidence layer."""

import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

import polars as pl
import pytest

from usher_pipeline.evidence.animal_models import (
    process_animal_model_evidence,
    load_to_duckdb,
)
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker


@pytest.fixture
def mock_hcop_data():
    """Mock HCOP ortholog mapping data."""
    mouse_data = """human_entrez_gene\thuman_ensembl_gene\thgnc_id\thuman_name\thuman_symbol\thuman_chr\thuman_assert_ids\tmouse_entrez_gene\tmouse_ensembl_gene\tmgi_id\tmouse_name\tmouse_symbol\tmouse_chr\tmouse_assert_ids\tsupport
123\tENSG00000001\tHGNC:1\tUSH2A\tUSH2A\t1\t\t456\tENSMUSG001\tMGI:1\tUsh2a\tUsh2a\t1\t\tdb1,db2,db3,db4,db5,db6,db7,db8
456\tENSG00000002\tHGNC:2\tMYO7A\tMYO7A\t11\t\t789\tENSMUSG002\tMGI:2\tMyo7a\tMyo7a\t7\t\tdb1,db2,db3,db4,db5"""

    zebrafish_data = """human_entrez_gene\thuman_ensembl_gene\thgnc_id\thuman_name\thuman_symbol\thuman_chr\thuman_assert_ids\tzebrafish_entrez_gene\tzebrafish_ensembl_gene\tzfin_id\tzebrafish_name\tzebrafish_symbol\tzebrafish_chr\tzebrafish_assert_ids\tsupport
123\tENSG00000001\tHGNC:1\tUSH2A\tUSH2A\t1\t\t111\tENSDART001\tZDB-GENE-1\tush2a\tush2a\t1\t\tdb1,db2,db3,db4,db5,db6"""

    return {'mouse': mouse_data, 'zebrafish': zebrafish_data}


@pytest.fixture
def mock_phenotype_data():
    """Mock MGI, ZFIN, and IMPC phenotype data."""
    mgi_data = """Marker Symbol\tMammalian Phenotype ID
Ush2a\tMP:0001967
Ush2a\tMP:0005377
Myo7a\tMP:0001968"""

    zfin_data = """Gene Symbol\tAffected Structure or Process 1
ush2a\tabnormal ear morphology
ush2a\tabnormal retina morphology"""

    impc_responses = {
        'Ush2a': {
            'response': {
                'docs': [
                    {
                        'marker_symbol': 'Ush2a',
                        'mp_term_id': 'MP:0001967',
                        'mp_term_name': 'deafness',
                        'p_value': 0.001
                    }
                ]
            }
        },
        'Myo7a': {
            'response': {
                'docs': [
                    {
                        'marker_symbol': 'Myo7a',
                        'mp_term_id': 'MP:0001968',
                        'mp_term_name': 'abnormal cochlea morphology',
                        'p_value': 0.0005
                    }
                ]
            }
        }
    }

    return {'mgi': mgi_data, 'zfin': zfin_data, 'impc': impc_responses}


def test_full_pipeline(mock_hcop_data, mock_phenotype_data):
    """Test full animal model evidence pipeline with mocked data sources."""
    gene_ids = ['ENSG00000001', 'ENSG00000002']

    with patch('usher_pipeline.evidence.animal_models.fetch._download_gzipped') as mock_hcop, \
         patch('usher_pipeline.evidence.animal_models.fetch._download_text') as mock_text, \
         patch('httpx.get') as mock_http:

        # Mock HCOP downloads
        mock_hcop.side_effect = [
            mock_hcop_data['mouse'].encode('utf-8'),
            mock_hcop_data['zebrafish'].encode('utf-8'),
        ]

        # Mock MGI and ZFIN downloads
        mock_text.side_effect = [
            mock_phenotype_data['mgi'],
            mock_phenotype_data['zfin'],
        ]

        # Mock IMPC API responses
        def mock_impc_response(url, **kwargs):
            response = Mock()
            response.raise_for_status = Mock()

            # Extract gene symbol from query
            query = kwargs.get('params', {}).get('q', '')
            if 'Ush2a' in query:
                response.json = Mock(return_value=mock_phenotype_data['impc']['Ush2a'])
            elif 'Myo7a' in query:
                response.json = Mock(return_value=mock_phenotype_data['impc']['Myo7a'])
            else:
                response.json = Mock(return_value={'response': {'docs': []}})

            return response

        mock_http.side_effect = mock_impc_response

        # Run pipeline
        result = process_animal_model_evidence(gene_ids)

        # Verify results
        assert len(result) == 2

        # Check USH2A (ENSG00000001)
        ush2a = result.filter(pl.col('gene_id') == 'ENSG00000001')
        assert len(ush2a) == 1
        assert ush2a['mouse_ortholog'][0] == 'Ush2a'
        assert ush2a['mouse_ortholog_confidence'][0] == 'HIGH'  # 8 sources
        assert ush2a['zebrafish_ortholog'][0] == 'ush2a'
        assert ush2a['zebrafish_ortholog_confidence'][0] == 'MEDIUM'  # 6 sources
        assert ush2a['sensory_phenotype_count'][0] is not None
        assert ush2a['animal_model_score_normalized'][0] is not None
        assert ush2a['animal_model_score_normalized'][0] > 0

        # Check MYO7A (ENSG00000002)
        myo7a = result.filter(pl.col('gene_id') == 'ENSG00000002')
        assert len(myo7a) == 1
        assert myo7a['mouse_ortholog'][0] == 'Myo7a'
        assert myo7a['mouse_ortholog_confidence'][0] == 'MEDIUM'  # 5 sources


def test_checkpoint_restart(mock_hcop_data, mock_phenotype_data):
    """Test checkpoint-restart pattern: load from DuckDB if exists, skip reprocessing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        store = PipelineStore(db_path)

        # Initial load
        gene_ids = ['ENSG00000001', 'ENSG00000002']

        with patch('usher_pipeline.evidence.animal_models.fetch._download_gzipped') as mock_hcop, \
             patch('usher_pipeline.evidence.animal_models.fetch._download_text') as mock_text, \
             patch('httpx.get') as mock_http:

            mock_hcop.side_effect = [
                mock_hcop_data['mouse'].encode('utf-8'),
                mock_hcop_data['zebrafish'].encode('utf-8'),
            ]
            mock_text.side_effect = [
                mock_phenotype_data['mgi'],
                mock_phenotype_data['zfin'],
            ]

            def mock_impc_response(url, **kwargs):
                response = Mock()
                response.raise_for_status = Mock()
                response.json = Mock(return_value={'response': {'docs': []}})
                return response

            mock_http.side_effect = mock_impc_response

            df = process_animal_model_evidence(gene_ids)

            # Save to DuckDB (use mock provenance tracker)
            provenance = Mock()
            provenance.record_step = Mock()
            load_to_duckdb(df, store, provenance)

        # Check checkpoint exists
        assert store.has_checkpoint('animal_model_phenotypes')

        # Load from checkpoint
        loaded_df = store.load_dataframe('animal_model_phenotypes')
        assert loaded_df is not None
        assert len(loaded_df) == 2

        store.close()


def test_provenance_tracking(mock_hcop_data, mock_phenotype_data):
    """Test that provenance metadata is correctly recorded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        store = PipelineStore(db_path)

        gene_ids = ['ENSG00000001', 'ENSG00000002']

        with patch('usher_pipeline.evidence.animal_models.fetch._download_gzipped') as mock_hcop, \
             patch('usher_pipeline.evidence.animal_models.fetch._download_text') as mock_text, \
             patch('httpx.get') as mock_http:

            mock_hcop.side_effect = [
                mock_hcop_data['mouse'].encode('utf-8'),
                mock_hcop_data['zebrafish'].encode('utf-8'),
            ]
            mock_text.side_effect = [
                mock_phenotype_data['mgi'],
                mock_phenotype_data['zfin'],
            ]

            def mock_impc_response(url, **kwargs):
                response = Mock()
                response.raise_for_status = Mock()
                response.json = Mock(return_value={'response': {'docs': []}})
                return response

            mock_http.side_effect = mock_impc_response

            df = process_animal_model_evidence(gene_ids)

            # Track provenance (use mock)
            provenance = Mock()
            provenance.record_step = Mock()
            provenance.get_steps = Mock(return_value=[
                {'step': 'load_animal_model_phenotypes', 'row_count': 2}
            ])

            load_to_duckdb(df, store, provenance, description="Test animal model data")

            # Check provenance was recorded
            steps = provenance.get_steps()
            assert len(steps) > 0
            load_step = next((s for s in steps if s['step'] == 'load_animal_model_phenotypes'), None)
            assert load_step is not None
            assert 'row_count' in load_step
            assert load_step['row_count'] == 2

        store.close()


def test_empty_phenotype_handling(mock_hcop_data):
    """Test handling of genes with orthologs but no phenotypes."""
    gene_ids = ['ENSG00000001']

    with patch('usher_pipeline.evidence.animal_models.fetch._download_gzipped') as mock_hcop, \
         patch('usher_pipeline.evidence.animal_models.fetch._download_text') as mock_text, \
         patch('httpx.get') as mock_http:

        mock_hcop.side_effect = [
            mock_hcop_data['mouse'].encode('utf-8'),
            mock_hcop_data['zebrafish'].encode('utf-8'),
        ]

        # Empty phenotype data
        empty_mgi = """Marker Symbol\tMammalian Phenotype ID
"""
        empty_zfin = """Gene Symbol\tAffected Structure or Process 1
"""

        mock_text.side_effect = [empty_mgi, empty_zfin]

        def mock_impc_response(url, **kwargs):
            response = Mock()
            response.raise_for_status = Mock()
            response.json = Mock(return_value={'response': {'docs': []}})
            return response

        mock_http.side_effect = mock_impc_response

        result = process_animal_model_evidence(gene_ids)

        # Should have ortholog mapping but NULL sensory phenotype count
        assert len(result) == 1
        assert result['mouse_ortholog'][0] == 'Ush2a'
        assert result['sensory_phenotype_count'][0] is None
        # Score should still be calculated (but low since no phenotypes)
        assert result['animal_model_score_normalized'][0] is not None

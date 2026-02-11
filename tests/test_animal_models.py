"""Unit tests for animal model evidence layer."""

import io
from unittest.mock import Mock, patch, MagicMock

import polars as pl
import pytest

from usher_pipeline.evidence.animal_models import (
    fetch_ortholog_mapping,
    filter_sensory_phenotypes,
    score_animal_evidence,
    SENSORY_MP_KEYWORDS,
)


def test_ortholog_confidence_high():
    """Test that 8+ supporting sources results in HIGH confidence."""
    # Mock HCOP data with 8 supporting databases
    hcop_data = """human_entrez_gene\thuman_ensembl_gene\thgnc_id\thuman_name\thuman_symbol\thuman_chr\thuman_assert_ids\tmouse_entrez_gene\tmouse_ensembl_gene\tmgi_id\tmouse_name\tmouse_symbol\tmouse_chr\tmouse_assert_ids\tsupport
123\tENSG00000001\tHGNC:1\tGene 1\tGENE1\t1\t\t456\tENSMUSG001\tMGI:1\tGene1\tGene1\t1\t\tdb1,db2,db3,db4,db5,db6,db7,db8"""

    with patch('usher_pipeline.evidence.animal_models.fetch._download_gzipped') as mock_download:
        mock_download.return_value = hcop_data.encode('utf-8')

        result = fetch_ortholog_mapping(['ENSG00000001'])

        assert len(result) == 1
        assert result['mouse_ortholog_confidence'][0] == 'HIGH'


def test_ortholog_confidence_low():
    """Test that 1-3 supporting sources results in LOW confidence."""
    # Mock HCOP data with 2 supporting databases
    hcop_mouse = """human_entrez_gene\thuman_ensembl_gene\thgnc_id\thuman_name\thuman_symbol\thuman_chr\thuman_assert_ids\tmouse_entrez_gene\tmouse_ensembl_gene\tmgi_id\tmouse_name\tmouse_symbol\tmouse_chr\tmouse_assert_ids\tsupport
123\tENSG00000001\tHGNC:1\tGene 1\tGENE1\t1\t\t456\tENSMUSG001\tMGI:1\tGene1\tGene1\t1\t\tdb1,db2"""

    hcop_zebrafish = """human_entrez_gene\thuman_ensembl_gene\thgnc_id\thuman_name\thuman_symbol\thuman_chr\thuman_assert_ids\tzebrafish_entrez_gene\tzebrafish_ensembl_gene\tzfin_id\tzebrafish_name\tzebrafish_symbol\tzebrafish_chr\tzebrafish_assert_ids\tsupport
"""

    with patch('usher_pipeline.evidence.animal_models.fetch._download_gzipped') as mock_download:
        # Return mouse data first, then zebrafish data
        mock_download.side_effect = [
            hcop_mouse.encode('utf-8'),
            hcop_zebrafish.encode('utf-8')
        ]

        result = fetch_ortholog_mapping(['ENSG00000001'])

        assert len(result) == 1
        assert result['mouse_ortholog_confidence'][0] == 'LOW'


def test_one_to_many_best_selected():
    """Test that for one-to-many ortholog mappings, the highest confidence is kept."""
    # Mock HCOP data with two orthologs for same human gene
    hcop_mouse = """human_entrez_gene\thuman_ensembl_gene\thgnc_id\thuman_name\thuman_symbol\thuman_chr\thuman_assert_ids\tmouse_entrez_gene\tmouse_ensembl_gene\tmgi_id\tmouse_name\tmouse_symbol\tmouse_chr\tmouse_assert_ids\tsupport
123\tENSG00000001\tHGNC:1\tGene 1\tGENE1\t1\t\t456\tENSMUSG001\tMGI:1\tGene1a\tGene1a\t1\t\tdb1,db2
123\tENSG00000001\tHGNC:1\tGene 1\tGENE1\t1\t\t789\tENSMUSG002\tMGI:2\tGene1b\tGene1b\t2\t\tdb1,db2,db3,db4,db5,db6,db7,db8"""

    hcop_zebrafish = """human_entrez_gene\thuman_ensembl_gene\thgnc_id\thuman_name\thuman_symbol\thuman_chr\thuman_assert_ids\tzebrafish_entrez_gene\tzebrafish_ensembl_gene\tzfin_id\tzebrafish_name\tzebrafish_symbol\tzebrafish_chr\tzebrafish_assert_ids\tsupport
"""

    with patch('usher_pipeline.evidence.animal_models.fetch._download_gzipped') as mock_download:
        mock_download.side_effect = [
            hcop_mouse.encode('utf-8'),
            hcop_zebrafish.encode('utf-8')
        ]

        result = fetch_ortholog_mapping(['ENSG00000001'])

        # Should select Gene1b with 8 sources (HIGH confidence)
        assert len(result) == 1
        assert result['mouse_ortholog'][0] == 'Gene1b'
        assert result['mouse_ortholog_confidence'][0] == 'HIGH'


def test_sensory_keyword_match():
    """Test that phenotype terms matching SENSORY_MP_KEYWORDS are retained."""
    phenotypes = pl.DataFrame({
        'mouse_gene': ['Gene1', 'Gene1', 'Gene2'],
        'mp_term_id': ['MP:0001', 'MP:0002', 'MP:0003'],
        'mp_term_name': ['hearing loss', 'abnormal cochlea morphology', 'irrelevant phenotype'],
    })

    result = filter_sensory_phenotypes(phenotypes, SENSORY_MP_KEYWORDS, 'mp_term_name')

    # Should keep first two rows (hearing, cochlea match keywords)
    assert len(result) == 2
    assert 'hearing loss' in result['mp_term_name'].to_list()
    assert 'abnormal cochlea morphology' in result['mp_term_name'].to_list()


def test_non_sensory_filtered():
    """Test that non-sensory phenotypes are filtered out."""
    phenotypes = pl.DataFrame({
        'mouse_gene': ['Gene1', 'Gene2'],
        'mp_term_id': ['MP:0001', 'MP:0002'],
        'mp_term_name': ['increased body weight', 'abnormal coat color'],
    })

    result = filter_sensory_phenotypes(phenotypes, SENSORY_MP_KEYWORDS, 'mp_term_name')

    # Should filter out both rows
    assert len(result) == 0


def test_score_with_confidence_weighting():
    """Test that HIGH confidence orthologs score higher than LOW confidence."""
    # Gene with HIGH confidence mouse ortholog
    high_conf = pl.DataFrame({
        'gene_id': ['ENSG00000001'],
        'mouse_ortholog': ['Gene1'],
        'mouse_ortholog_confidence': ['HIGH'],
        'zebrafish_ortholog': [None],
        'zebrafish_ortholog_confidence': [None],
        'has_mouse_phenotype': [True],
        'has_zebrafish_phenotype': [False],
        'has_impc_phenotype': [False],
        'sensory_phenotype_count': [5],
    })

    # Gene with LOW confidence mouse ortholog
    low_conf = pl.DataFrame({
        'gene_id': ['ENSG00000002'],
        'mouse_ortholog': ['Gene2'],
        'mouse_ortholog_confidence': ['LOW'],
        'zebrafish_ortholog': [None],
        'zebrafish_ortholog_confidence': [None],
        'has_mouse_phenotype': [True],
        'has_zebrafish_phenotype': [False],
        'has_impc_phenotype': [False],
        'sensory_phenotype_count': [5],
    })

    high_result = score_animal_evidence(high_conf)
    low_result = score_animal_evidence(low_conf)

    high_score = high_result['animal_model_score_normalized'][0]
    low_score = low_result['animal_model_score_normalized'][0]

    # HIGH confidence should score higher (0.4 * 1.0 vs 0.4 * 0.4)
    assert high_score > low_score


def test_score_null_no_ortholog():
    """Test that genes without orthologs get NULL score, not zero."""
    df = pl.DataFrame({
        'gene_id': ['ENSG00000001'],
        'mouse_ortholog': [None],
        'mouse_ortholog_confidence': [None],
        'zebrafish_ortholog': [None],
        'zebrafish_ortholog_confidence': [None],
        'has_mouse_phenotype': [False],
        'has_zebrafish_phenotype': [False],
        'has_impc_phenotype': [False],
        'sensory_phenotype_count': [None],
    })

    result = score_animal_evidence(df)

    # Should be NULL, not 0.0
    assert result['animal_model_score_normalized'][0] is None


def test_multi_organism_bonus():
    """Test that phenotypes in both mouse and zebrafish result in higher score."""
    # Gene with only mouse phenotype
    mouse_only = pl.DataFrame({
        'gene_id': ['ENSG00000001'],
        'mouse_ortholog': ['Gene1'],
        'mouse_ortholog_confidence': ['HIGH'],
        'zebrafish_ortholog': [None],
        'zebrafish_ortholog_confidence': [None],
        'has_mouse_phenotype': [True],
        'has_zebrafish_phenotype': [False],
        'has_impc_phenotype': [False],
        'sensory_phenotype_count': [3],
    })

    # Gene with both mouse and zebrafish phenotypes
    both = pl.DataFrame({
        'gene_id': ['ENSG00000002'],
        'mouse_ortholog': ['Gene2'],
        'mouse_ortholog_confidence': ['HIGH'],
        'zebrafish_ortholog': ['gene2'],
        'zebrafish_ortholog_confidence': ['HIGH'],
        'has_mouse_phenotype': [True],
        'has_zebrafish_phenotype': [True],
        'has_impc_phenotype': [False],
        'sensory_phenotype_count': [3],
    })

    mouse_result = score_animal_evidence(mouse_only)
    both_result = score_animal_evidence(both)

    mouse_score = mouse_result['animal_model_score_normalized'][0]
    both_score = both_result['animal_model_score_normalized'][0]

    # Both organisms should score higher (0.4 + 0.3 vs 0.4)
    assert both_score > mouse_score


def test_phenotype_count_scaling():
    """Test that more sensory phenotypes lead to higher scores (with diminishing returns)."""
    # Gene with 1 phenotype
    few = pl.DataFrame({
        'gene_id': ['ENSG00000001'],
        'mouse_ortholog': ['Gene1'],
        'mouse_ortholog_confidence': ['HIGH'],
        'zebrafish_ortholog': [None],
        'zebrafish_ortholog_confidence': [None],
        'has_mouse_phenotype': [True],
        'has_zebrafish_phenotype': [False],
        'has_impc_phenotype': [False],
        'sensory_phenotype_count': [1],
    })

    # Gene with 10 phenotypes
    many = pl.DataFrame({
        'gene_id': ['ENSG00000002'],
        'mouse_ortholog': ['Gene2'],
        'mouse_ortholog_confidence': ['HIGH'],
        'zebrafish_ortholog': [None],
        'zebrafish_ortholog_confidence': [None],
        'has_mouse_phenotype': [True],
        'has_zebrafish_phenotype': [False],
        'has_impc_phenotype': [False],
        'sensory_phenotype_count': [10],
    })

    few_result = score_animal_evidence(few)
    many_result = score_animal_evidence(many)

    few_score = few_result['animal_model_score_normalized'][0]
    many_score = many_result['animal_model_score_normalized'][0]

    # More phenotypes should score higher
    assert many_score > few_score
    # But not linearly (diminishing returns via log)
    # log2(11) / log2(11) = 1.0 vs log2(2) / log2(11) = 0.29
    assert many_score < few_score * 10  # Not 10x higher


def test_impc_integration():
    """Test that IMPC phenotypes contribute to score."""
    # Gene without IMPC
    no_impc = pl.DataFrame({
        'gene_id': ['ENSG00000001'],
        'mouse_ortholog': ['Gene1'],
        'mouse_ortholog_confidence': ['HIGH'],
        'zebrafish_ortholog': [None],
        'zebrafish_ortholog_confidence': [None],
        'has_mouse_phenotype': [True],
        'has_zebrafish_phenotype': [False],
        'has_impc_phenotype': [False],
        'sensory_phenotype_count': [3],
    })

    # Gene with IMPC
    with_impc = pl.DataFrame({
        'gene_id': ['ENSG00000002'],
        'mouse_ortholog': ['Gene2'],
        'mouse_ortholog_confidence': ['HIGH'],
        'zebrafish_ortholog': [None],
        'zebrafish_ortholog_confidence': [None],
        'has_mouse_phenotype': [True],
        'has_zebrafish_phenotype': [False],
        'has_impc_phenotype': [True],
        'sensory_phenotype_count': [3],
    })

    no_impc_result = score_animal_evidence(no_impc)
    with_impc_result = score_animal_evidence(with_impc)

    no_impc_score = no_impc_result['animal_model_score_normalized'][0]
    with_impc_score = with_impc_result['animal_model_score_normalized'][0]

    # IMPC should add to score (+0.3)
    assert with_impc_score > no_impc_score

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
from usher_pipeline.evidence.animal_models.transform import compute_phenotype_aggregates
from usher_pipeline.evidence.animal_models.fetch import (
    fetch_mgi_phenotypes,
    fetch_zfin_phenotypes,
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


def test_impc_no_independent_bonus():
    """IMPC must not add an independent bonus on top of mouse (MGI) evidence.

    IMPC phenotype data is ingested into MGI as Mammalian Phenotype (MP)
    ontology annotations, so MGI and IMPC are not independent sources.
    Two genes with identical mouse phenotype evidence (same confidence and
    the same distinct sensory phenotype count) must score equally regardless
    of whether the has_impc_phenotype flag is set.
    """
    base = {
        'mouse_ortholog': ['Gene1'],
        'mouse_ortholog_confidence': ['HIGH'],
        'zebrafish_ortholog': [None],
        'zebrafish_ortholog_confidence': [None],
        'has_mouse_phenotype': [True],
        'has_zebrafish_phenotype': [False],
        'sensory_phenotype_count': [3],
    }
    no_impc = pl.DataFrame({'gene_id': ['ENSG00000001'], 'has_impc_phenotype': [False], **base})
    with_impc = pl.DataFrame({'gene_id': ['ENSG00000002'], 'has_impc_phenotype': [True], **base})

    no_impc_score = score_animal_evidence(no_impc)['animal_model_score_normalized'][0]
    with_impc_score = score_animal_evidence(with_impc)['animal_model_score_normalized'][0]

    assert with_impc_score == no_impc_score


def test_mouse_phenotype_count_dedups_mgi_impc_overlap():
    """MGI and IMPC share the MP ontology, so overlapping terms count once.

    A gene with MGI terms {A, B} and IMPC terms {A, C} has three distinct
    mouse phenotypes, not four; the summed count double-counted term A.
    """
    df = pl.DataFrame({
        'mgi_phenotype_count': [2],
        'mgi_terms': ['abnormal hearing; abnormal retina morphology'],
        'impc_phenotype_count': [2],
        'impc_terms': ['abnormal hearing; decreased startle reflex'],
        'zfin_phenotype_count': [None],
        'zfin_terms': [None],
    })

    out = compute_phenotype_aggregates(df)

    assert out['sensory_phenotype_count'][0] == 3
    assert out['has_mouse_phenotype'][0] is True


def test_impc_only_gene_gets_mouse_phenotype():
    """A gene with IMPC-but-no-MGI evidence still has a mouse phenotype.

    Folding IMPC into the mouse channel must preserve coverage for genes
    whose only mouse evidence comes from IMPC screening.
    """
    df = pl.DataFrame({
        'mgi_phenotype_count': [None],
        'mgi_terms': [None],
        'impc_phenotype_count': [1],
        'impc_terms': ['abnormal cochlea morphology'],
        'zfin_phenotype_count': [None],
        'zfin_terms': [None],
    })

    out = compute_phenotype_aggregates(df)

    assert out['has_mouse_phenotype'][0] is True
    assert out['sensory_phenotype_count'][0] == 1


def test_fetch_mgi_phenotypes_parses_headerless_reports():
    """MGI fetch parses headerless HMD + VOC reports and resolves MP term names."""
    # VOC_MammalianPhenotype.rpt: headerless MP ID, term name, definition
    vocab = (
        "MP:0001\thearing loss\tinability to hear\n"
        "MP:0002\tabnormal cochlea morphology\tcochlea defect\n"
        "MP:0003\tabnormal coat color\tcoat defect"
    )
    # HMD_HumanPhenotype.rpt: headerless human sym, entrez, mouse sym, MGI acc, MP IDs
    hmd = (
        "GENE1\t111\tGene1\tMGI:1\tMP:0001, MP:0003\t\n"
        "GENE2\t222\tGene2\tMGI:2\tMP:0002\t\n"
        "GENE3\t333\tGene3\tMGI:3\t\t"  # no phenotypes
    )

    with patch('usher_pipeline.evidence.animal_models.fetch._download_text') as mock_dl:
        mock_dl.side_effect = [vocab, hmd]
        result = fetch_mgi_phenotypes(['Gene1', 'Gene2'])

    assert set(result.columns) == {'mouse_gene', 'mp_term_id', 'mp_term_name'}
    # Gene1 -> MP:0001, MP:0003 ; Gene2 -> MP:0002 ; Gene3 not requested
    assert result.height == 3
    g1 = result.filter(pl.col('mouse_gene') == 'Gene1')
    assert sorted(g1['mp_term_id'].to_list()) == ['MP:0001', 'MP:0003']
    assert 'hearing loss' in g1['mp_term_name'].to_list()


def test_fetch_mgi_phenotypes_terms_enable_sensory_filter():
    """MGI term names are populated so downstream keyword filtering works."""
    vocab = "MP:0001\thearing loss\td\nMP:0003\tabnormal coat color\td"
    hmd = "GENE1\t111\tGene1\tMGI:1\tMP:0001, MP:0003\t"

    with patch('usher_pipeline.evidence.animal_models.fetch._download_text') as mock_dl:
        mock_dl.side_effect = [vocab, hmd]
        pheno = fetch_mgi_phenotypes(['Gene1'])

    sensory = filter_sensory_phenotypes(pheno, SENSORY_MP_KEYWORDS, 'mp_term_name')
    assert sensory.height == 1
    assert sensory['mp_term_name'].to_list() == ['hearing loss']


def _zfin_row(gene, subterm, superterm, keyword, tag):
    """Build a 25-field headerless ZFIN phenoGeneCleanData row."""
    fields = [""] * 25
    fields[0] = "100"
    fields[1] = gene            # col 2: gene symbol
    fields[2] = "ZDB-GENE-1"    # col 3: gene id
    fields[4] = subterm         # col 5: structure 1 subterm name
    fields[7] = "ZFA:0001"      # col 8: superterm id
    fields[8] = superterm       # col 9: structure 1 superterm name
    fields[10] = keyword        # col 11: phenotype keyword name
    fields[11] = tag            # col 12: phenotype tag
    return "\t".join(fields)


def test_fetch_zfin_phenotypes_parses_headerless_file():
    """ZFIN fetch parses the headerless file and builds keyword-matchable terms."""
    content = "\n".join([
        _zfin_row("gene1", "photoreceptor cell", "retina", "degenerate", "abnormal"),
        _zfin_row("gene2", "", "lateral line", "decreased amount", "abnormal"),
        _zfin_row("gene3", "", "fin", "malformed", "normal"),   # normal -> dropped
    ])

    with patch('usher_pipeline.evidence.animal_models.fetch._download_text') as mock_dl:
        mock_dl.return_value = content
        result = fetch_zfin_phenotypes(['gene1', 'gene2', 'gene3'])

    assert set(result.columns) == {'zebrafish_gene', 'zp_term_id', 'zp_term_name'}
    # gene3 is tagged "normal" -> filtered out
    assert sorted(result['zebrafish_gene'].to_list()) == ['gene1', 'gene2']
    g1_term = result.filter(pl.col('zebrafish_gene') == 'gene1')['zp_term_name'][0]
    assert 'retina' in g1_term and 'photoreceptor' in g1_term


def test_fetch_zfin_phenotypes_empty_for_no_genes():
    """ZFIN fetch returns an empty typed frame when no genes are requested."""
    result = fetch_zfin_phenotypes([])
    assert result.is_empty()
    assert set(result.columns) == {'zebrafish_gene', 'zp_term_id', 'zp_term_name'}

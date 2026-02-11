"""Unit tests for literature evidence layer."""

import polars as pl
import pytest
from unittest.mock import Mock, patch

from usher_pipeline.evidence.literature import (
    classify_evidence_tier,
    compute_literature_score,
    SEARCH_CONTEXTS,
    DIRECT_EVIDENCE_TERMS,
)


@pytest.fixture
def synthetic_literature_data():
    """Create synthetic literature data for testing tier classification and scoring."""
    return pl.DataFrame({
        "gene_id": [
            "ENSG00000001",  # Direct experimental: knockout + cilia context
            "ENSG00000002",  # Functional mention: cilia context, multiple pubs
            "ENSG00000003",  # HTS hit: screen hit + cilia context
            "ENSG00000004",  # Incidental: publications but no context
            "ENSG00000005",  # None: zero publications
            "ENSG00000006",  # Well-studied (TP53-like): many total, few cilia
            "ENSG00000007",  # Focused novel: few total, many cilia (should score high)
        ],
        "gene_symbol": [
            "GENE1",
            "GENE2",
            "GENE3",
            "GENE4",
            "GENE5",
            "TP53LIKE",
            "NOVELGENE",
        ],
        "total_pubmed_count": [
            100,    # Gene1: moderate total
            50,     # Gene2: moderate total
            30,     # Gene3: moderate total
            1000,   # Gene4: many total, but no cilia context
            0,      # Gene5: zero
            100000, # TP53-like: very many
            10,     # Novel: very few
        ],
        "cilia_context_count": [
            10,     # Gene1: good cilia evidence
            5,      # Gene2: some cilia evidence
            3,      # Gene3: some cilia evidence
            0,      # Gene4: no context
            0,      # Gene5: zero
            5,      # TP53-like: same as Gene2, but huge total
            5,      # Novel: same as Gene2, but tiny total
        ],
        "sensory_context_count": [
            5,      # Gene1
            3,      # Gene2
            2,      # Gene3
            0,      # Gene4
            0,      # Gene5
            2,      # TP53-like
            2,      # Novel
        ],
        "cytoskeleton_context_count": [
            8,      # Gene1
            4,      # Gene2
            2,      # Gene3
            0,      # Gene4
            0,      # Gene5
            10,     # TP53-like
            3,      # Novel
        ],
        "cell_polarity_context_count": [
            3,      # Gene1
            2,      # Gene2
            1,      # Gene3
            0,      # Gene4
            0,      # Gene5
            4,      # TP53-like
            1,      # Novel
        ],
        "direct_experimental_count": [
            3,      # Gene1: knockout evidence
            0,      # Gene2: no knockout
            0,      # Gene3: no knockout
            0,      # Gene4: no knockout
            0,      # Gene5: zero
            1,      # TP53-like: has knockout but incidental
            0,      # Novel: no knockout
        ],
        "hts_screen_count": [
            0,      # Gene1: not from screen
            0,      # Gene2: not from screen
            2,      # Gene3: from HTS screen
            0,      # Gene4: not from screen
            0,      # Gene5: zero
            5,      # TP53-like: many screens
            0,      # Novel: not from screen
        ],
    })


def test_direct_experimental_classification(synthetic_literature_data):
    """Gene with knockout paper in cilia context should be classified as direct_experimental."""
    df = classify_evidence_tier(synthetic_literature_data)

    gene1 = df.filter(pl.col("gene_symbol") == "GENE1")
    assert gene1["evidence_tier"][0] == "direct_experimental"


def test_functional_mention_classification(synthetic_literature_data):
    """Gene with cilia context but no knockout should be functional_mention."""
    df = classify_evidence_tier(synthetic_literature_data)

    gene2 = df.filter(pl.col("gene_symbol") == "GENE2")
    assert gene2["evidence_tier"][0] == "functional_mention"


def test_hts_hit_classification(synthetic_literature_data):
    """Gene from proteomics screen in cilia context should be hts_hit."""
    df = classify_evidence_tier(synthetic_literature_data)

    gene3 = df.filter(pl.col("gene_symbol") == "GENE3")
    assert gene3["evidence_tier"][0] == "hts_hit"


def test_incidental_classification(synthetic_literature_data):
    """Gene with publications but no cilia/sensory context should be incidental."""
    df = classify_evidence_tier(synthetic_literature_data)

    gene4 = df.filter(pl.col("gene_symbol") == "GENE4")
    assert gene4["evidence_tier"][0] == "incidental"


def test_no_evidence_classification(synthetic_literature_data):
    """Gene with zero publications should be classified as none."""
    df = classify_evidence_tier(synthetic_literature_data)

    gene5 = df.filter(pl.col("gene_symbol") == "GENE5")
    assert gene5["evidence_tier"][0] == "none"


def test_bias_mitigation(synthetic_literature_data):
    """TP53-like gene (100K total, 5 cilia) should score LOWER than novel gene (10 total, 5 cilia).

    This tests the critical bias mitigation feature: quality-weighted score normalized
    by log2(total_pubmed_count) to prevent well-studied genes from dominating.
    """
    df = classify_evidence_tier(synthetic_literature_data)
    df = compute_literature_score(df)

    tp53_like = df.filter(pl.col("gene_symbol") == "TP53LIKE")
    novel = df.filter(pl.col("gene_symbol") == "NOVELGENE")

    tp53_score = tp53_like["literature_score_normalized"][0]
    novel_score = novel["literature_score_normalized"][0]

    # Novel gene should score higher despite having same cilia context count
    assert novel_score > tp53_score, (
        f"Novel gene (10 total/5 cilia) should score higher than TP53-like (100K total/5 cilia). "
        f"Got novel={novel_score:.4f}, TP53-like={tp53_score:.4f}"
    )


def test_quality_weighting(synthetic_literature_data):
    """Direct experimental evidence should score higher than incidental mention."""
    df = classify_evidence_tier(synthetic_literature_data)
    df = compute_literature_score(df)

    direct = df.filter(pl.col("gene_symbol") == "GENE1")
    incidental = df.filter(pl.col("gene_symbol") == "GENE4")

    direct_score = direct["literature_score_normalized"][0]
    incidental_score = incidental["literature_score_normalized"][0]

    # Direct experimental should always score higher than incidental
    assert direct_score > incidental_score


def test_null_preservation():
    """Failed PubMed query should result in NULL counts, not zero."""
    # Simulate failed query with NULL values
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001"],
        "gene_symbol": ["GENE1"],
        "total_pubmed_count": [None],
        "cilia_context_count": [None],
        "sensory_context_count": [None],
        "cytoskeleton_context_count": [None],
        "cell_polarity_context_count": [None],
        "direct_experimental_count": [None],
        "hts_screen_count": [None],
    })

    df = classify_evidence_tier(df)
    df = compute_literature_score(df)

    # Evidence tier should be "none" for NULL counts
    assert df["evidence_tier"][0] == "none"

    # Score should be NULL (not zero)
    assert df["literature_score_normalized"][0] is None


def test_context_weighting(synthetic_literature_data):
    """Cilia/sensory contexts should be weighted higher than cytoskeleton."""
    # Test by modifying data: create two genes with same total but different context distribution
    df = pl.DataFrame({
        "gene_id": ["ENSG00000001", "ENSG00000002"],
        "gene_symbol": ["CILIA_FOCUSED", "CYTO_FOCUSED"],
        "total_pubmed_count": [50, 50],  # Same total
        "cilia_context_count": [10, 0],  # Cilia-focused has cilia context
        "sensory_context_count": [5, 0], # Cilia-focused has sensory context
        "cytoskeleton_context_count": [0, 20],  # Cyto-focused has cytoskeleton context
        "cell_polarity_context_count": [0, 0],
        "direct_experimental_count": [1, 1],  # Same experimental evidence
        "hts_screen_count": [0, 0],
    })

    df = classify_evidence_tier(df)
    df = compute_literature_score(df)

    cilia_score = df.filter(pl.col("gene_symbol") == "CILIA_FOCUSED")["literature_score_normalized"][0]
    cyto_score = df.filter(pl.col("gene_symbol") == "CYTO_FOCUSED")["literature_score_normalized"][0]

    # Cilia-focused should score higher due to context weights (cilia=2.0, cyto=1.0)
    # CILIA_FOCUSED context_score = 10*2.0 + 5*2.0 = 30
    # CYTO_FOCUSED context_score = 20*1.0 = 20
    assert cilia_score > cyto_score


def test_score_normalization(synthetic_literature_data):
    """Final literature_score_normalized should be in [0, 1] range."""
    df = classify_evidence_tier(synthetic_literature_data)
    df = compute_literature_score(df)

    # Filter to non-NULL scores
    scores = df.filter(pl.col("literature_score_normalized").is_not_null())["literature_score_normalized"]

    assert scores.min() >= 0.0
    assert scores.max() <= 1.0


@patch('usher_pipeline.evidence.literature.fetch.Entrez')
def test_query_pubmed_gene_mock(mock_entrez):
    """Test query_pubmed_gene with mocked Biopython Entrez."""
    from usher_pipeline.evidence.literature.fetch import query_pubmed_gene

    # Mock esearch responses
    def mock_esearch(db, term, retmax):
        """Return different counts based on query term."""
        count_map = {
            "GENE1": 100,  # Total
            "GENE1 cilia": 10,
            "GENE1 sensory": 5,
            "GENE1 knockout": 3,
            "GENE1 screen": 0,
        }
        # Simple matching on term content
        for key, count in count_map.items():
            if key.replace(" ", ") AND (") in term or key in term:
                mock_handle = Mock()
                mock_handle.__enter__ = Mock(return_value=mock_handle)
                mock_handle.__exit__ = Mock(return_value=False)
                return mock_handle

        # Default
        mock_handle = Mock()
        mock_handle.__enter__ = Mock(return_value=mock_handle)
        mock_handle.__exit__ = Mock(return_value=False)
        return mock_handle

    # Set up mock
    mock_entrez.esearch = mock_esearch
    mock_entrez.read = Mock(return_value={"Count": "10"})

    # Test query
    result = query_pubmed_gene(
        gene_symbol="GENE1",
        contexts=SEARCH_CONTEXTS,
        email="test@example.com",
        api_key=None,
    )

    # Verify result structure
    assert "gene_symbol" in result
    assert "total_pubmed_count" in result
    assert "cilia_context_count" in result
    assert "sensory_context_count" in result
    assert "direct_experimental_count" in result
    assert "hts_screen_count" in result

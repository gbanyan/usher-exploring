"""Unit tests for protein features evidence layer."""

from unittest.mock import Mock, patch, MagicMock
import polars as pl
import pytest
from polars.testing import assert_frame_equal

from usher_pipeline.evidence.protein.models import (
    ProteinFeatureRecord,
    CILIA_DOMAIN_KEYWORDS,
    SCAFFOLD_DOMAIN_TYPES,
)
from usher_pipeline.evidence.protein.transform import (
    extract_protein_features,
    detect_cilia_motifs,
    normalize_protein_features,
)


@pytest.fixture
def sample_uniprot_df():
    """Sample UniProt data for testing."""
    return pl.DataFrame({
        "uniprot_id": ["P12345", "Q67890", "A11111", "B22222"],
        "protein_length": [500, 1200, 300, None],  # None = not found
        "domain_names": [
            ["PDZ domain", "Kinase domain"],
            ["IFT complex subunit", "WD40 repeat"],
            ["Transmembrane region"],
            [],
        ],
        "coiled_coil_count": [2, 0, 0, None],
        "transmembrane_count": [0, 5, 10, None],
    })


@pytest.fixture
def sample_interpro_df():
    """Sample InterPro data for testing."""
    return pl.DataFrame({
        "uniprot_id": ["P12345", "Q67890", "A11111", "B22222"],
        "domain_names": [
            ["SH3 domain"],
            ["Ciliary targeting signal", "Ankyrin repeat"],
            [],
            [],
        ],
        "interpro_ids": [
            ["IPR001452"],
            ["IPR005598", "IPR002110"],
            [],
            [],
        ],
    })


def test_uniprot_feature_extraction(sample_uniprot_df, sample_interpro_df):
    """Correct parsing of length, domain, coiled-coil, TM from UniProt data."""
    df = extract_protein_features(sample_uniprot_df, sample_interpro_df)

    # Check P12345
    p12345 = df.filter(pl.col("uniprot_id") == "P12345")
    assert p12345["protein_length"][0] == 500
    assert p12345["coiled_coil"][0] == True  # count=2 > 0
    assert p12345["coiled_coil_count"][0] == 2
    assert p12345["transmembrane_count"][0] == 0
    # Domain count should include both UniProt and InterPro (deduplicated)
    assert p12345["domain_count"][0] == 3  # PDZ, Kinase, SH3

    # Check B22222 (not found in UniProt)
    b22222 = df.filter(pl.col("uniprot_id") == "B22222")
    assert b22222["protein_length"][0] is None
    assert b22222["coiled_coil"][0] is None
    assert b22222["transmembrane_count"][0] is None


def test_cilia_motif_detection_positive():
    """Domain name containing cilia keywords sets has_cilia_domain=True."""
    df = pl.DataFrame({
        "uniprot_id": ["P12345"],
        "protein_length": [500],
        "domain_count": [2],
        "coiled_coil": [False],
        "coiled_coil_count": [0],
        "transmembrane_count": [0],
        "domain_names": [["IFT complex subunit", "Kinase domain"]],
    })

    result = detect_cilia_motifs(df)

    assert result["has_cilia_domain"][0] == True


def test_cilia_motif_detection_negative():
    """Standard domain (e.g., Kinase) does not trigger has_cilia_domain."""
    df = pl.DataFrame({
        "uniprot_id": ["P12345"],
        "protein_length": [500],
        "domain_count": [1],
        "coiled_coil": [False],
        "coiled_coil_count": [0],
        "transmembrane_count": [0],
        "domain_names": [["Kinase domain"]],
    })

    result = detect_cilia_motifs(df)

    assert result["has_cilia_domain"][0] == False


def test_scaffold_detection():
    """PDZ domain triggers scaffold_adaptor_domain=True."""
    df = pl.DataFrame({
        "uniprot_id": ["P12345"],
        "protein_length": [500],
        "domain_count": [1],
        "coiled_coil": [False],
        "coiled_coil_count": [0],
        "transmembrane_count": [0],
        "domain_names": [["PDZ domain"]],
    })

    result = detect_cilia_motifs(df)

    assert result["scaffold_adaptor_domain"][0] == True


def test_null_uniprot():
    """Gene without UniProt entry has all features NULL."""
    df = pl.DataFrame({
        "uniprot_id": ["B22222"],
        "protein_length": [None],
        "domain_count": [0],
        "coiled_coil": [None],
        "coiled_coil_count": [None],
        "transmembrane_count": [None],
        "domain_names": [[]],
    })

    result = detect_cilia_motifs(df)
    result = normalize_protein_features(result)

    # All boolean flags should be NULL (not False)
    assert result["has_cilia_domain"][0] is None
    assert result["scaffold_adaptor_domain"][0] is None
    assert result["has_sensory_domain"][0] is None
    # Composite score should be NULL
    assert result["protein_score_normalized"][0] is None


def test_normalization_bounds():
    """All normalized features are in [0, 1] range."""
    df = pl.DataFrame({
        "uniprot_id": ["P1", "P2", "P3"],
        "protein_length": [100, 500, 2000],
        "domain_count": [0, 5, 20],
        "coiled_coil": [False, True, True],
        "coiled_coil_count": [0, 2, 5],
        "transmembrane_count": [0, 5, 25],  # 25 gets capped at 20
        "domain_names": [[], ["PDZ"], ["IFT", "Ciliary"]],
    })

    result = detect_cilia_motifs(df)
    result = normalize_protein_features(result)

    # Check all scores are in [0, 1]
    for score in result["protein_score_normalized"]:
        assert score is not None
        assert 0.0 <= score <= 1.0


def test_composite_score_cilia_gene():
    """Gene with cilia domains scores higher than gene without."""
    df = pl.DataFrame({
        "uniprot_id": ["P_CILIA", "P_NOCILIA"],
        "protein_length": [500, 500],
        "domain_count": [5, 5],
        "coiled_coil": [True, True],
        "coiled_coil_count": [2, 2],
        "transmembrane_count": [5, 5],
        "domain_names": [
            ["IFT complex", "PDZ domain"],  # Has cilia + scaffold
            ["Kinase domain", "PDZ domain"],  # Only scaffold
        ],
    })

    result = detect_cilia_motifs(df)
    result = normalize_protein_features(result)

    cilia_score = result.filter(pl.col("uniprot_id") == "P_CILIA")["protein_score_normalized"][0]
    nocilia_score = result.filter(pl.col("uniprot_id") == "P_NOCILIA")["protein_score_normalized"][0]

    # Cilia gene should score higher (15% weight for has_cilia_domain)
    assert cilia_score > nocilia_score


def test_composite_score_null_handling():
    """NULL UniProt produces NULL composite score (not 0.0)."""
    df = pl.DataFrame({
        "uniprot_id": ["P_VALID", "P_NULL"],
        "protein_length": [500, None],
        "domain_count": [5, 0],
        "coiled_coil": [True, None],
        "coiled_coil_count": [2, None],
        "transmembrane_count": [5, None],
        "domain_names": [["PDZ"], []],
    })

    result = detect_cilia_motifs(df)
    result = normalize_protein_features(result)

    valid_score = result.filter(pl.col("uniprot_id") == "P_VALID")["protein_score_normalized"][0]
    null_score = result.filter(pl.col("uniprot_id") == "P_NULL")["protein_score_normalized"][0]

    assert valid_score is not None
    assert null_score is None  # NOT 0.0


def test_domain_keyword_case_insensitive():
    """Cilia keyword matching is case-insensitive."""
    df = pl.DataFrame({
        "uniprot_id": ["P1", "P2", "P3"],
        "protein_length": [500, 500, 500],
        "domain_count": [1, 1, 1],
        "coiled_coil": [False, False, False],
        "coiled_coil_count": [0, 0, 0],
        "transmembrane_count": [0, 0, 0],
        "domain_names": [
            ["intraflagellar transport"],  # lowercase
            ["CILIARY targeting signal"],  # uppercase
            ["Basal Body protein"],  # mixed case
        ],
    })

    result = detect_cilia_motifs(df)

    # All should match
    assert result["has_cilia_domain"][0] == True
    assert result["has_cilia_domain"][1] == True
    assert result["has_cilia_domain"][2] == True


@patch("usher_pipeline.evidence.protein.fetch.httpx.Client")
def test_fetch_uniprot_features_with_mock(mock_client_class):
    """Test UniProt fetch with mocked HTTP responses."""
    from usher_pipeline.evidence.protein.fetch import fetch_uniprot_features

    # Mock httpx client
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    # Mock UniProt API response
    mock_response = Mock()
    mock_response.json.return_value = {
        "results": [
            {
                "primaryAccession": "P12345",
                "sequence": {"length": 500},
                "features": [
                    {"type": "Domain", "description": "PDZ domain"},
                    {"type": "Coiled coil"},
                    {"type": "Transmembrane"},
                ],
            }
        ]
    }
    mock_client.get.return_value = mock_response

    # Call fetch
    df = fetch_uniprot_features(["P12345"])

    # Verify result
    assert len(df) == 1
    assert df["uniprot_id"][0] == "P12345"
    assert df["protein_length"][0] == 500
    assert df["coiled_coil_count"][0] == 1
    assert df["transmembrane_count"][0] == 1


@patch("usher_pipeline.evidence.protein.fetch.httpx.Client")
def test_fetch_interpro_domains_with_mock(mock_client_class):
    """Test InterPro fetch with mocked HTTP responses."""
    from usher_pipeline.evidence.protein.fetch import fetch_interpro_domains

    # Mock httpx client
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    # Mock InterPro API response
    mock_response = Mock()
    mock_response.json.return_value = {
        "results": [
            {
                "metadata": {
                    "accession": "IPR001452",
                    "name": {"name": "SH3 domain"},
                }
            }
        ]
    }
    mock_client.get.return_value = mock_response

    # Call fetch
    df = fetch_interpro_domains(["P12345"])

    # Verify result
    assert len(df) == 1
    assert df["uniprot_id"][0] == "P12345"
    assert "SH3 domain" in df["domain_names"][0]
    assert "IPR001452" in df["interpro_ids"][0]

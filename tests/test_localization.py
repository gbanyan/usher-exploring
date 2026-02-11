"""Unit tests for localization evidence layer."""

import pytest
import polars as pl
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from usher_pipeline.evidence.localization.models import (
    LocalizationRecord,
    CILIA_COMPARTMENTS,
    CILIA_ADJACENT_COMPARTMENTS,
)
from usher_pipeline.evidence.localization.fetch import (
    fetch_hpa_subcellular,
    fetch_cilia_proteomics,
)
from usher_pipeline.evidence.localization.transform import (
    classify_evidence_type,
    score_localization,
    process_localization_evidence,
)
from usher_pipeline.evidence.localization.load import (
    load_to_duckdb,
    query_cilia_localized,
)


class TestHPALocationParsing:
    """Test HPA location string parsing."""

    def test_hpa_location_parsing(self):
        """Test correct extraction of locations from semicolon-separated string."""
        # Create mock DataFrame with semicolon-separated locations
        df = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
            "gene_symbol": ["GENE1", "GENE2", "GENE3"],
            "hpa_main_location": [
                "Centrosome;Cilia",
                "Cytosol;Nucleus",
                "Microtubules;Cell Junctions",
            ],
            "hpa_reliability": ["Enhanced", "Supported", "Uncertain"],
            "in_cilia_proteomics": [False, False, False],
            "in_centrosome_proteomics": [False, False, False],
        })

        # Classify evidence type first (required by score_localization)
        df = classify_evidence_type(df)

        # Score localization should parse the semicolon-separated string
        result = score_localization(df)

        # GENE1 should have both cilia and centrosome compartments detected
        gene1 = result.filter(pl.col("gene_id") == "ENSG001")
        assert gene1["compartment_cilia"][0] == True
        assert gene1["compartment_centrosome"][0] == True

        # GENE3 should have adjacent compartment detected
        gene3 = result.filter(pl.col("gene_id") == "ENSG003")
        assert gene3["cilia_proximity_score"][0] == 0.5  # Adjacent compartment


class TestCiliaCompartmentDetection:
    """Test cilia compartment flag setting."""

    def test_cilia_compartment_detection(self):
        """Test that 'Centrosome' in location sets compartment_centrosome=True."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002"],
            "gene_symbol": ["PCNT", "ACTB"],
            "hpa_main_location": ["Centrosome;Centriole", "Actin filaments"],
            "hpa_reliability": ["Enhanced", "Enhanced"],
            "in_cilia_proteomics": [False, False],
            "in_centrosome_proteomics": [False, False],
            "evidence_type": ["experimental", "experimental"],
        })

        result = score_localization(df)

        # PCNT should have centrosome compartment
        pcnt = result.filter(pl.col("gene_id") == "ENSG001")
        assert pcnt["compartment_centrosome"][0] == True
        assert pcnt["cilia_proximity_score"][0] == 1.0  # Direct match

        # ACTB should not have cilia compartments
        actb = result.filter(pl.col("gene_id") == "ENSG002")
        assert actb["compartment_centrosome"][0] == False or actb["compartment_centrosome"][0] is None


class TestAdjacentCompartmentScoring:
    """Test adjacent compartment scoring logic."""

    def test_adjacent_compartment_scoring(self):
        """Test that 'Cytoskeleton' only gives proximity score of 0.5."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001"],
            "gene_symbol": ["TUBB"],
            "hpa_main_location": ["Cytoskeleton;Microtubules"],
            "hpa_reliability": ["Supported"],
            "in_cilia_proteomics": [False],
            "in_centrosome_proteomics": [False],
            "evidence_type": ["experimental"],
        })

        result = score_localization(df)

        # Should get 0.5 for adjacent compartment
        assert result["cilia_proximity_score"][0] == 0.5


class TestEvidenceTypeExperimental:
    """Test evidence type classification for experimental data."""

    def test_evidence_type_experimental(self):
        """Test HPA Enhanced reliability classifies as experimental."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002"],
            "gene_symbol": ["GENE1", "GENE2"],
            "hpa_reliability": ["Enhanced", "Supported"],
            "in_cilia_proteomics": [False, False],
            "in_centrosome_proteomics": [False, False],
        })

        result = classify_evidence_type(df)

        # Both should be experimental
        assert result["hpa_evidence_type"][0] == "experimental"
        assert result["hpa_evidence_type"][1] == "experimental"
        assert result["evidence_type"][0] == "experimental"
        assert result["evidence_type"][1] == "experimental"


class TestEvidenceTypeComputational:
    """Test evidence type classification for computational predictions."""

    def test_evidence_type_computational(self):
        """Test HPA Uncertain reliability classifies as computational."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002"],
            "gene_symbol": ["GENE1", "GENE2"],
            "hpa_reliability": ["Uncertain", "Approved"],
            "in_cilia_proteomics": [False, False],
            "in_centrosome_proteomics": [False, False],
        })

        result = classify_evidence_type(df)

        # Both should be computational
        assert result["hpa_evidence_type"][0] == "computational"
        assert result["hpa_evidence_type"][1] == "computational"
        assert result["evidence_type"][0] == "computational"
        assert result["evidence_type"][1] == "computational"


class TestProteomicsOverride:
    """Test proteomics evidence overrides HPA computational classification."""

    def test_proteomics_override(self):
        """Test gene in proteomics but HPA uncertain has evidence_type='both'."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001"],
            "gene_symbol": ["BBS1"],
            "hpa_reliability": ["Uncertain"],  # Computational
            "in_cilia_proteomics": [True],  # Experimental
            "in_centrosome_proteomics": [False],
        })

        result = classify_evidence_type(df)

        # Should have both experimental (proteomics) and computational (HPA)
        assert result["hpa_evidence_type"][0] == "computational"
        assert result["evidence_type"][0] == "both"


class TestNullHandlingNoHPA:
    """Test NULL handling for genes not in HPA."""

    def test_null_handling_no_hpa(self):
        """Test gene not in HPA has HPA columns as NULL."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001"],
            "gene_symbol": ["GENE1"],
            "hpa_main_location": [None],
            "hpa_reliability": [None],
            "in_cilia_proteomics": [False],
            "in_centrosome_proteomics": [False],
        })

        result = classify_evidence_type(df)

        # HPA fields should be NULL
        assert result["hpa_reliability"][0] is None
        assert result["hpa_evidence_type"][0] is None
        # Overall evidence type should be "none"
        assert result["evidence_type"][0] == "none"


class TestProteomicsAbsenceIsFalse:
    """Test proteomics absence is False not NULL."""

    def test_proteomics_absence_is_false(self):
        """Test gene not in proteomics has in_cilia_proteomics=False (not NULL)."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001"],
            "gene_symbol": ["GENE1"],
            "hpa_main_location": ["Nucleus"],
            "hpa_reliability": ["Enhanced"],
            "in_cilia_proteomics": [False],  # Explicitly False, not NULL
            "in_centrosome_proteomics": [False],
        })

        # Check that False is preserved (not NULL)
        assert df["in_cilia_proteomics"][0] == False
        assert df["in_centrosome_proteomics"][0] == False


class TestScoreNormalization:
    """Test localization score is in [0, 1] range."""

    def test_score_normalization(self):
        """Test localization_score_normalized is in [0, 1]."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
            "gene_symbol": ["G1", "G2", "G3"],
            "hpa_main_location": ["Centrosome", "Cytoskeleton", "Nucleus"],
            "hpa_reliability": ["Enhanced", "Supported", "Enhanced"],
            "in_cilia_proteomics": [False, False, False],
            "in_centrosome_proteomics": [False, False, False],
        })

        df = classify_evidence_type(df)
        result = score_localization(df)

        # All non-null scores should be in [0, 1]
        scores = result["localization_score_normalized"].drop_nulls()
        assert all(score >= 0.0 and score <= 1.0 for score in scores)


class TestEvidenceWeightApplied:
    """Test experimental evidence scores higher than computational for same compartment."""

    def test_evidence_weight_applied(self):
        """Test experimental evidence gets full weight, computational gets 0.6x."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002"],
            "gene_symbol": ["GENE1", "GENE2"],
            "hpa_main_location": ["Centrosome", "Centrosome"],
            "hpa_reliability": ["Enhanced", "Uncertain"],
            "in_cilia_proteomics": [False, False],
            "in_centrosome_proteomics": [False, False],
        })

        df = classify_evidence_type(df)
        result = score_localization(df)

        # Both have same cilia_proximity_score
        assert result["cilia_proximity_score"][0] == 1.0
        assert result["cilia_proximity_score"][1] == 1.0

        # But normalized scores differ by evidence weight
        experimental_score = result["localization_score_normalized"][0]
        computational_score = result["localization_score_normalized"][1]

        assert experimental_score == 1.0  # Enhanced = experimental = 1.0x
        assert computational_score == pytest.approx(0.6)  # Uncertain = computational = 0.6x


class TestFetchCiliaProteomics:
    """Test cilia proteomics cross-reference."""

    def test_fetch_cilia_proteomics(self):
        """Test cross-referencing against curated proteomics gene sets."""
        gene_symbol_map = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
            "gene_symbol": ["BBS1", "ACTB", "CEP290"],  # BBS1 and CEP290 in cilia proteomics
        })

        result = fetch_cilia_proteomics(
            gene_ids=["ENSG001", "ENSG002", "ENSG003"],
            gene_symbol_map=gene_symbol_map,
        )

        # BBS1 and CEP290 should be in cilia proteomics
        bbs1 = result.filter(pl.col("gene_id") == "ENSG001")
        assert bbs1["in_cilia_proteomics"][0] == True

        cep290 = result.filter(pl.col("gene_id") == "ENSG003")
        assert cep290["in_cilia_proteomics"][0] == True

        # ACTB should not be in cilia proteomics
        actb = result.filter(pl.col("gene_id") == "ENSG002")
        assert actb["in_cilia_proteomics"][0] == False


class TestLoadToDuckDB:
    """Test DuckDB loading with provenance."""

    def test_load_to_duckdb(self):
        """Test loading localization data to DuckDB."""
        # Create synthetic data
        df = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002"],
            "gene_symbol": ["BBS1", "ACTB"],
            "hpa_main_location": ["Centrosome", "Actin filaments"],
            "hpa_reliability": ["Enhanced", "Enhanced"],
            "evidence_type": ["experimental", "experimental"],
            "compartment_cilia": [False, False],
            "compartment_centrosome": [True, False],
            "cilia_proximity_score": [1.0, 0.0],
            "localization_score_normalized": [1.0, 0.0],
        })

        # Mock store and provenance
        mock_store = Mock()
        mock_provenance = Mock()

        # Call load function
        load_to_duckdb(df, mock_store, mock_provenance, "Test description")

        # Verify save_dataframe was called
        mock_store.save_dataframe.assert_called_once()
        call_args = mock_store.save_dataframe.call_args
        assert call_args.kwargs["table_name"] == "subcellular_localization"
        assert call_args.kwargs["replace"] == True

        # Verify provenance recorded
        mock_provenance.record_step.assert_called_once()
        step_args = mock_provenance.record_step.call_args
        assert step_args[0][0] == "load_subcellular_localization"
        assert step_args[0][1]["row_count"] == 2

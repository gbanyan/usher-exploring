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
    CENTROSOME_COMPENDIUM_GENES,
    CURATED_COMPENDIUM_PROVENANCE,
    CURATED_COMPENDIUM_RECORDS,
    CURATED_COMPENDIUM_SELECTION_VERSION,
    CILIA_COMPENDIUM_GENES,
    normalize_compendium_gene_symbol,
    _gene_set_sha256,
    fetch_hpa_subcellular,
    fetch_cilia_compendium,
    fetch_cilia_proteomics,
)
from usher_pipeline.evidence.localization.models import (
    CURATED_PROTEOMICS_COLUMNS,
    LEGACY_CURATED_PROTEOMICS_COLUMNS,
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
            "in_cilia_compendium": [False, False, False],
            "in_centrosome_compendium": [False, False, False],
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
            "in_cilia_compendium": [False, False],
            "in_centrosome_compendium": [False, False],
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
            "in_cilia_compendium": [False],
            "in_centrosome_compendium": [False],
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
            "in_cilia_compendium": [False, False],
            "in_centrosome_compendium": [False, False],
        })

        result = classify_evidence_type(df)

        # Both should be experimental
        assert result["hpa_evidence_type"][0] == "experimental"
        assert result["hpa_evidence_type"][1] == "experimental"
        assert result["evidence_type"][0] == "experimental"
        assert result["evidence_type"][1] == "experimental"


class TestEvidenceTypeHPAUncertainty:
    """Test HPA reliability categories remain antibody-staining evidence."""

    def test_approved_and_uncertain_are_experimental(self):
        """Approved/Uncertain are not computational prediction classes."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002"],
            "gene_symbol": ["GENE1", "GENE2"],
            "hpa_reliability": ["Uncertain", "Approved"],
            "in_cilia_compendium": [False, False],
            "in_centrosome_compendium": [False, False],
        })

        result = classify_evidence_type(df)

        # Both are HPA antibody-staining reliability categories.
        assert result["hpa_evidence_type"][0] == "experimental"
        assert result["hpa_evidence_type"][1] == "experimental"
        assert result["hpa_evidence_modality"][0] == "antibody_staining"
        assert result["hpa_evidence_modality"][1] == "antibody_staining"
        assert result["hpa_reliability_weight"].to_list() == [0.6, 0.6]
        assert result["evidence_type"][0] == "experimental"
        assert result["evidence_type"][1] == "experimental"


class TestCompendiumOverride:
    """Test curated compendium and HPA staining remain distinct."""

    def test_compendium_override(self):
        """HPA plus compendium membership is classified as mixed evidence."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001"],
            "gene_symbol": ["BBS1"],
            "hpa_reliability": ["Uncertain"],  # Antibody-staining reliability
            "in_cilia_compendium": [True],  # Curated compendium evidence
            "in_centrosome_compendium": [False],
        })

        result = classify_evidence_type(df)

        assert result["hpa_evidence_type"][0] == "experimental"
        assert result["evidence_type"][0] == "mixed"


class TestNullHandlingNoHPA:
    """Test NULL handling for genes not in HPA."""

    def test_null_handling_no_hpa(self):
        """Test gene not in HPA has HPA columns as NULL."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001"],
            "gene_symbol": ["GENE1"],
            "hpa_main_location": [None],
            "hpa_reliability": [None],
            "in_cilia_compendium": [False],
            "in_centrosome_compendium": [False],
        })

        result = classify_evidence_type(df)

        # HPA fields should be NULL
        assert result["hpa_reliability"][0] is None
        assert result["hpa_evidence_type"][0] is None
        # Overall evidence type should be "none"
        assert result["evidence_type"][0] == "none"


class TestCompendiumAbsenceIsFalse:
    """Test compendium absence is False not NULL."""

    def test_compendium_absence_is_false(self):
        """Test gene not in compendium has in_cilia_compendium=False (not NULL)."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001"],
            "gene_symbol": ["GENE1"],
            "hpa_main_location": ["Nucleus"],
            "hpa_reliability": ["Enhanced"],
            "in_cilia_compendium": [False],  # Explicitly False, not NULL
            "in_centrosome_compendium": [False],
        })

        # Check that False is preserved (not NULL)
        assert df["in_cilia_compendium"][0] == False
        assert df["in_centrosome_compendium"][0] == False


class TestScoreNormalization:
    """Test localization score is in [0, 1] range."""

    def test_score_normalization(self):
        """Test localization_score_normalized is in [0, 1]."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
            "gene_symbol": ["G1", "G2", "G3"],
            "hpa_main_location": ["Centrosome", "Cytoskeleton", "Nucleus"],
            "hpa_reliability": ["Enhanced", "Supported", "Enhanced"],
            "in_cilia_compendium": [False, False, False],
            "in_centrosome_compendium": [False, False, False],
        })

        df = classify_evidence_type(df)
        result = score_localization(df)

        # All non-null scores should be in [0, 1]
        scores = result["localization_score_normalized"].drop_nulls()
        assert all(score >= 0.0 and score <= 1.0 for score in scores)


class TestEvidenceWeightApplied:
    """Test HPA antibody-staining scores use explicit reliability weights."""

    def test_evidence_weight_applied(self):
        """Enhanced staining gets full weight; Uncertain staining is down-weighted."""
        df = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002"],
            "gene_symbol": ["GENE1", "GENE2"],
            "hpa_main_location": ["Centrosome", "Centrosome"],
            "hpa_reliability": ["Enhanced", "Uncertain"],
            "in_cilia_compendium": [False, False],
            "in_centrosome_compendium": [False, False],
        })

        df = classify_evidence_type(df)
        result = score_localization(df)

        # Both have same cilia_proximity_score
        assert result["cilia_proximity_score"][0] == 1.0
        assert result["cilia_proximity_score"][1] == 1.0

        # But normalized scores differ by evidence weight
        experimental_score = result["localization_score_normalized"][0]
        uncertain_score = result["localization_score_normalized"][1]

        assert experimental_score == 1.0  # Enhanced = experimental = 1.0x
        assert uncertain_score == pytest.approx(0.6)  # Lower reliability weight
        assert result["hpa_evidence_modality"].to_list() == [
            "antibody_staining",
            "antibody_staining",
        ]
        assert result["hpa_reliability_weight"].to_list() == [1.0, 0.6]

    def test_compendium_fallback_overrides_non_ciliary_hpa_flag(self):
        """Compendium fallback applies when HPA explicitly lacks cilia localization."""
        df = pl.DataFrame({
            "gene_id": ["ENSG_CONFLICT"],
            "gene_symbol": ["CPLANE1"],
            "hpa_main_location": ["Nucleus"],
            "hpa_reliability": ["Enhanced"],
            "in_cilia_compendium": [True],
            "in_centrosome_compendium": [False],
        })

        result = score_localization(classify_evidence_type(df))

        assert result["compartment_cilia"][0] is False
        assert result["cilia_proximity_score"][0] == pytest.approx(0.3)
        assert result["localization_score_normalized"][0] == pytest.approx(0.3)
        assert result["evidence_type"][0] == "mixed"


class TestFetchCiliaCompendium:
    """Test curated ciliary/centrosomal compendium cross-reference."""

    def test_fetch_cilia_compendium(self):
        """Test cross-referencing against curated compendium gene sets."""
        gene_symbol_map = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
            "gene_symbol": ["BBS1", "ACTB", "CEP290"],  # BBS1 and CEP290 in cilia compendium
        })

        result = fetch_cilia_compendium(
            gene_ids=["ENSG001", "ENSG002", "ENSG003"],
            gene_symbol_map=gene_symbol_map,
        )

        # BBS1 and CEP290 should be in cilia compendium
        bbs1 = result.filter(pl.col("gene_id") == "ENSG001")
        assert bbs1["in_cilia_compendium"][0] == True

        cep290 = result.filter(pl.col("gene_id") == "ENSG003")
        assert cep290["in_cilia_compendium"][0] == True

        # ACTB should not be in cilia compendium
        actb = result.filter(pl.col("gene_id") == "ENSG002")
        assert actb["in_cilia_compendium"][0] == False

    def test_embedded_sets_have_reproducible_subset_provenance(self):
        """Embedded sets identify scope and deterministic content hashes."""
        gene_sets = {
            "cilia": CILIA_COMPENDIUM_GENES,
            "centrosome": CENTROSOME_COMPENDIUM_GENES,
        }
        for name, metadata in CURATED_COMPENDIUM_PROVENANCE.items():
            assert metadata["complete_source_dataset"] is False
            assert metadata["source_tables_available"] is False
            assert "fetch.py" in metadata["origin"]
            assert metadata["selection_version"] == CURATED_COMPENDIUM_SELECTION_VERSION
            assert metadata["evidence_modality"] == "curated_compendium"
            assert metadata["evidence_weight"] == pytest.approx(0.5)
            assert metadata["fallback_score"] == pytest.approx(0.3)
            assert metadata["record_count"] == len(metadata["records"])
            assert all(
                {
                    "gene_symbol",
                    "source",
                    "study",
                    "evidence_modality",
                    "selection_version",
                    "source_gene_symbols",
                }
                <= record.keys()
                for record in metadata["records"]
            )
            assert all(record["study"] is None for record in metadata["records"])
            assert metadata["gene_count"] == len(gene_sets[name])
            assert metadata["sha256"] == _gene_set_sha256(gene_sets[name])

        assert len(CURATED_COMPENDIUM_RECORDS) == sum(
            metadata["record_count"] for metadata in CURATED_COMPENDIUM_PROVENANCE.values()
        )

    def test_obsolete_compendium_aliases_match_current_symbols(self):
        """Legacy symbols normalize before curated experimental matching."""
        assert normalize_compendium_gene_symbol("TALPID3") == "KIAA0586"
        assert normalize_compendium_gene_symbol("SAS6") == "SASS6"
        assert normalize_compendium_gene_symbol("CPAP") == "CENPJ"
        assert normalize_compendium_gene_symbol("C5orf42") == "CPLANE1"
        assert normalize_compendium_gene_symbol("C21orf59") == "CFAP298"
        assert "TALPID3" not in CILIA_COMPENDIUM_GENES
        assert "SAS6" not in CENTROSOME_COMPENDIUM_GENES
        assert "CPAP" not in CENTROSOME_COMPENDIUM_GENES
        assert "CPLANE1" in CILIA_COMPENDIUM_GENES
        assert "CFAP298" in CILIA_COMPENDIUM_GENES

    def test_fetch_matches_obsolete_aliases(self):
        gene_symbol_map = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
            "gene_symbol": ["TALPID3", "SAS6", "CPAP"],
        })

        result = fetch_cilia_compendium(
            gene_ids=["ENSG001", "ENSG002", "ENSG003"],
            gene_symbol_map=gene_symbol_map,
        )

        assert result["in_cilia_compendium"].to_list() == [True, False, False]
        assert result["in_centrosome_compendium"].to_list() == [False, True, True]

    def test_deprecated_fetch_preserves_legacy_columns(self):
        gene_symbol_map = pl.DataFrame({
            "gene_id": ["ENSG001"],
            "gene_symbol": ["CPLANE1"],
        })

        with pytest.warns(DeprecationWarning, match="fetch_cilia_proteomics"):
            result = fetch_cilia_proteomics(
                gene_ids=["ENSG001"],
                gene_symbol_map=gene_symbol_map,
            )

        assert CURATED_PROTEOMICS_COLUMNS == LEGACY_CURATED_PROTEOMICS_COLUMNS
        assert result.columns == [
            "gene_id",
            "gene_symbol",
            "in_cilia_proteomics",
            "in_centrosome_proteomics",
        ]
        assert result["in_cilia_proteomics"].to_list() == [True]


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
            "hpa_evidence_modality": ["antibody_staining", "antibody_staining"],
            "hpa_evidence_type": ["experimental", "experimental"],
            "hpa_reliability_weight": [1.0, 1.0],
            "evidence_type": ["experimental", "experimental"],
            "compartment_cilia": [False, False],
            "compartment_centrosome": [True, False],
            "compartment_basal_body": [False, False],
            "compartment_transition_zone": [False, False],
            "compartment_stereocilia": [False, False],
            "in_cilia_compendium": [True, False],
            "in_centrosome_compendium": [False, False],
            "cilia_proximity_score": [1.0, 0.0],
            "localization_score_normalized": [1.0, 0.0],
            "localization_checkpoint_schema_version": [3, 3],
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
        assert "localization_schema_version=3" in call_args.kwargs["description"]

        # Verify provenance recorded
        mock_provenance.record_step.assert_called_once()
        step_args = mock_provenance.record_step.call_args
        assert step_args[0][0] == "load_subcellular_localization"
        assert step_args[0][1]["row_count"] == 2
        assert step_args[0][1]["localization_checkpoint_schema_version"] == 3

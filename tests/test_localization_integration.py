"""Integration tests for localization evidence layer."""

import pytest
import polars as pl
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import zipfile
import io

from usher_pipeline.evidence.localization import (
    process_localization_evidence,
    load_to_duckdb,
)
from usher_pipeline.evidence.localization.load import (
    LegacyLocalizationCheckpointError,
    migrate_legacy_localization_checkpoint,
)
from usher_pipeline.evidence.localization.transform import classify_evidence_type
from usher_pipeline.persistence import PipelineStore, ProvenanceTracker


@pytest.fixture
def mock_hpa_data():
    """Create mock HPA subcellular location TSV data."""
    tsv_content = """Gene	Gene name	Reliability	Main location	Additional location	Extracellular location
ENSG00000001	BBS1	Enhanced	Centrosome	Cilia
ENSG00000002	CEP290	Supported	Cilia;Basal body
ENSG00000003	ACTB	Enhanced	Actin filaments	Cytosol
ENSG00000004	TUBB	Supported	Cytoskeleton	Microtubules
ENSG00000005	TP53	Uncertain	Nucleus	Cytosol
"""
    return tsv_content


@pytest.fixture
def gene_symbol_map():
    """Create gene symbol mapping DataFrame."""
    return pl.DataFrame({
        "gene_id": ["ENSG00000001", "ENSG00000002", "ENSG00000003", "ENSG00000004", "ENSG00000005"],
        "gene_symbol": ["BBS1", "CEP290", "ACTB", "TUBB", "TP53"],
    })


class TestFullPipeline:
    """Test full localization evidence pipeline."""

    @patch('usher_pipeline.evidence.localization.fetch.httpx.stream')
    def test_full_pipeline(self, mock_stream, mock_hpa_data, gene_symbol_map, tmp_path):
        """Test complete pipeline from fetch to scoring."""
        # Mock HPA download
        # Create a mock zip file containing the TSV
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("subcellular_location.tsv", mock_hpa_data)
        zip_buffer.seek(0)

        # Mock httpx stream response
        mock_response = MagicMock()
        mock_response.read.return_value = zip_buffer.getvalue()
        mock_response.headers = {"content-length": str(len(zip_buffer.getvalue()))}
        mock_stream.return_value.__enter__.return_value = mock_response

        # Run full pipeline
        gene_ids = gene_symbol_map["gene_id"].to_list()
        result = process_localization_evidence(
            gene_ids=gene_ids,
            gene_symbol_map=gene_symbol_map,
            cache_dir=tmp_path,
            force=True,
        )

        # Verify results
        assert len(result) == 5
        assert "gene_id" in result.columns
        assert "evidence_type" in result.columns
        assert "cilia_proximity_score" in result.columns
        assert "localization_score_normalized" in result.columns

        # Check BBS1 (in HPA centrosome, in curated compendium)
        bbs1 = result.filter(pl.col("gene_id") == "ENSG00000001")
        assert bbs1["compartment_centrosome"][0] == True
        assert bbs1["in_cilia_compendium"][0] == True  # BBS1 is in curated list
        assert bbs1["evidence_type"][0] == "mixed"
        assert bbs1["cilia_proximity_score"][0] == 1.0  # Direct cilia compartment

        # Check CEP290 (in HPA cilia, in curated compendium)
        cep290 = result.filter(pl.col("gene_id") == "ENSG00000002")
        assert cep290["compartment_cilia"][0] == True
        assert cep290["in_cilia_compendium"][0] == True
        assert cep290["evidence_type"][0] == "mixed"

        # Check ACTB (not in cilia compartments, not in curated compendium)
        actb = result.filter(pl.col("gene_id") == "ENSG00000003")
        assert actb["in_cilia_compendium"][0] == False
        assert actb["cilia_proximity_score"][0] == 0.0  # No cilia proximity

        # Check TUBB (adjacent compartment)
        tubb = result.filter(pl.col("gene_id") == "ENSG00000004")
        assert tubb["cilia_proximity_score"][0] == 0.5  # Adjacent compartment

        # Check TP53 (antibody-staining evidence with Uncertain reliability)
        tp53 = result.filter(pl.col("gene_id") == "ENSG00000005")
        assert tp53["hpa_reliability"][0] == "Uncertain"
        assert tp53["hpa_evidence_modality"][0] == "antibody_staining"
        assert tp53["hpa_reliability_weight"][0] == pytest.approx(0.6)
        assert tp53["localization_score_normalized"][0] == pytest.approx(0.0)
        assert tp53["evidence_type"][0] == "experimental"


class TestCheckpointRestart:
    """Test checkpoint-restart functionality."""

    @patch('usher_pipeline.evidence.localization.fetch.httpx.stream')
    def test_checkpoint_restart(self, mock_stream, mock_hpa_data, gene_symbol_map, tmp_path):
        """Test that cached HPA data is reused on second run."""
        # Mock HPA download for first run
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("subcellular_location.tsv", mock_hpa_data)
        zip_buffer.seek(0)

        mock_response = MagicMock()
        mock_response.read.return_value = zip_buffer.getvalue()
        mock_response.headers = {"content-length": str(len(zip_buffer.getvalue()))}
        mock_stream.return_value.__enter__.return_value = mock_response

        # First run
        gene_ids = gene_symbol_map["gene_id"].to_list()
        result1 = process_localization_evidence(
            gene_ids=gene_ids,
            gene_symbol_map=gene_symbol_map,
            cache_dir=tmp_path,
            force=True,
        )

        # Reset mock
        mock_stream.reset_mock()

        # Second run (should use cached data)
        result2 = process_localization_evidence(
            gene_ids=gene_ids,
            gene_symbol_map=gene_symbol_map,
            cache_dir=tmp_path,
            force=False,  # Don't force re-download
        )

        # Verify httpx.stream was NOT called on second run
        mock_stream.assert_not_called()

        # Results should be identical
        assert len(result1) == len(result2)


class TestProvenanceTracking:
    """Test provenance metadata recording."""

    def test_provenance_tracking(self, tmp_path):
        """Test provenance step recording with statistics."""
        # Create synthetic data
        df = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002", "ENSG003"],
            "gene_symbol": ["BBS1", "CEP290", "ACTB"],
            "hpa_main_location": ["Centrosome", "Cilia", "Nucleus"],
            "hpa_reliability": ["Enhanced", "Supported", "Enhanced"],
            "hpa_evidence_modality": ["antibody_staining"] * 3,
            "hpa_evidence_type": ["experimental"] * 3,
            "hpa_reliability_weight": [1.0] * 3,
            "evidence_type": ["experimental", "mixed", "experimental"],
            "compartment_cilia": [False, True, False],
            "compartment_centrosome": [True, False, False],
            "compartment_basal_body": [False, False, False],
            "compartment_transition_zone": [False, False, False],
            "compartment_stereocilia": [False, False, False],
            "in_cilia_compendium": [True, True, False],
            "in_centrosome_compendium": [False, False, False],
            "cilia_proximity_score": [1.0, 1.0, 0.0],
            "localization_score_normalized": [1.0, 1.0, 0.0],
            "localization_checkpoint_schema_version": [3] * 3,
        })

        # Create temporary DuckDB
        db_path = tmp_path / "test.duckdb"
        store = PipelineStore(db_path)

        # Mock provenance tracker
        mock_provenance = Mock()

        # Load data
        load_to_duckdb(df, store, mock_provenance, "Test description")

        # Verify provenance recorded
        mock_provenance.record_step.assert_called_once()
        step_args = mock_provenance.record_step.call_args

        # Check provenance details
        assert step_args[0][0] == "load_subcellular_localization"
        provenance_data = step_args[0][1]
        assert provenance_data["row_count"] == 3
        assert provenance_data["experimental_count"] == 2
        assert provenance_data["both_count"] == 1
        assert provenance_data["cilia_compartment_count"] == 2  # BBS1 centrosome, CEP290 cilia
        assert provenance_data["high_proximity_count"] == 2  # Score > 0.5

        store.close()


class TestDuckDBQuery:
    """Test DuckDB query helper functions."""

    def test_query_cilia_localized(self, tmp_path):
        """Test querying cilia-localized genes from DuckDB."""
        from usher_pipeline.evidence.localization.load import query_cilia_localized

        # Create synthetic data
        df = pl.DataFrame({
            "gene_id": ["ENSG001", "ENSG002", "ENSG003", "ENSG004"],
            "gene_symbol": ["BBS1", "CEP290", "ACTB", "TP53"],
            "hpa_main_location": ["Centrosome", "Cilia", "Nucleus", "Nucleus"],
            "hpa_reliability": ["Enhanced", "Supported", "Enhanced", "Enhanced"],
            "hpa_evidence_modality": ["antibody_staining"] * 4,
            "hpa_evidence_type": ["experimental"] * 4,
            "hpa_reliability_weight": [1.0] * 4,
            "evidence_type": ["mixed", "mixed", "experimental", "experimental"],
            "compartment_cilia": [False, True, False, False],
            "compartment_centrosome": [True, False, False, False],
            "compartment_basal_body": [None, None, None, None],
            "compartment_transition_zone": [False, False, False, False],
            "compartment_stereocilia": [False, False, False, False],
            "in_cilia_compendium": [True, True, False, False],
            "in_centrosome_compendium": [False, False, False, False],
            "cilia_proximity_score": [1.0, 1.0, 0.0, 0.2],
            "localization_score_normalized": [1.0, 1.0, 0.0, 0.12],
            "localization_checkpoint_schema_version": [3] * 4,
        })

        # Create DuckDB and load data
        db_path = tmp_path / "test.duckdb"
        store = PipelineStore(db_path)
        mock_provenance = Mock()
        load_to_duckdb(df, store, mock_provenance)

        # Query cilia-localized genes (proximity > 0.5)
        result = query_cilia_localized(store, proximity_threshold=0.5)

        # Should return BBS1 and CEP290 only
        assert len(result) == 2
        gene_symbols = result["gene_symbol"].to_list()
        assert "BBS1" in gene_symbols
        assert "CEP290" in gene_symbols
        assert "ACTB" not in gene_symbols
        assert "TP53" not in gene_symbols

        store.close()


class TestErrorHandling:
    """Test error handling in localization pipeline."""

    def test_missing_gene_universe(self):
        """Test error handling when gene universe is missing."""
        # Test with minimal valid data - empty gene list should work
        # Just verify classify_evidence_type handles edge cases
        df = pl.DataFrame({
            "gene_id": [],
            "gene_symbol": [],
            "hpa_reliability": [],
            "in_cilia_compendium": [],
            "in_centrosome_compendium": [],
        })

        result = classify_evidence_type(df)

        # Should return empty DataFrame with correct schema
        assert len(result) == 0
        assert "gene_id" in result.columns
        assert "evidence_type" in result.columns
        assert "hpa_evidence_type" in result.columns


class TestLegacyCheckpointMigration:
    """Legacy checkpoints must be reprocessed or fail explicitly."""

    def test_score_only_checkpoint_is_not_projected_to_false(self, tmp_path):
        store = PipelineStore(tmp_path / "legacy-score-only.duckdb")
        store.save_dataframe(
            pl.DataFrame({
                "gene_id": ["ENSG001"],
                "gene_symbol": ["TUBB2B"],
                "localization_score_normalized": [0.5],
            }),
            "subcellular_localization",
        )

        with pytest.raises(LegacyLocalizationCheckpointError, match="cannot infer"):
            migrate_legacy_localization_checkpoint(store)
        store.close()

    def test_raw_checkpoint_is_reprocessed_with_source_flags(self, tmp_path):
        store = PipelineStore(tmp_path / "legacy-raw.duckdb")
        store.save_dataframe(
            pl.DataFrame({
                "gene_id": ["ENSG001"],
                "gene_symbol": ["TUBB2B"],
                "hpa_main_location": ["Cytoskeleton;Microtubules"],
                "hpa_reliability": ["Uncertain"],
                "in_cilia_compendium": [False],
                "in_centrosome_compendium": [False],
                "localization_score_normalized": [0.5],
            }),
            "subcellular_localization",
        )

        migration = migrate_legacy_localization_checkpoint(store)
        migrated = store.load_dataframe("subcellular_localization")

        assert migration["status"] == "reprocessed"
        assert migrated is not None
        assert migrated["compartment_cilia"][0] is False
        assert migrated["localization_score_normalized"][0] == pytest.approx(0.3)
        assert migrated["localization_checkpoint_schema_version"][0] == 3
        store.close()

    def test_614741c_full_flags_and_old_scoring_are_reprocessed(self, tmp_path):
        """Old full source flags still require v3 rescoring and reliability fields."""
        store = PipelineStore(tmp_path / "legacy-v2-full-flags.duckdb")
        store.save_dataframe(
            pl.DataFrame({
                "gene_id": ["ENSG001", "ENSG002"],
                "gene_symbol": ["CPLANE1", "CFAP298"],
                "hpa_main_location": ["Nucleus", "Nucleus"],
                "hpa_reliability": ["Uncertain", "Enhanced"],
                "hpa_evidence_type": ["experimental", "experimental"],
                "evidence_type": ["experimental", "experimental"],
                "compartment_cilia": [False, False],
                "compartment_centrosome": [False, False],
                "compartment_basal_body": [False, False],
                "compartment_transition_zone": [False, False],
                "compartment_stereocilia": [False, False],
                "in_cilia_proteomics": [False, False],
                "in_centrosome_proteomics": [False, False],
                "cilia_proximity_score": [0.0, 0.0],
                "localization_score_normalized": [0.0, 0.0],
                "localization_checkpoint_schema_version": [2, 2],
            }),
            "subcellular_localization",
        )

        migration = migrate_legacy_localization_checkpoint(store)
        migrated = store.load_dataframe("subcellular_localization")

        assert migration["status"] == "reprocessed"
        assert migrated is not None
        assert migrated["localization_checkpoint_schema_version"].to_list() == [3, 3]
        assert migrated["hpa_evidence_modality"].to_list() == [
            "antibody_staining",
            "antibody_staining",
        ]
        assert migrated["hpa_reliability_weight"].to_list() == [0.6, 1.0]
        assert migrated["in_cilia_compendium"].to_list() == [True, True]
        assert migrated["in_centrosome_compendium"].to_list() == [False, False]
        assert migrated["localization_score_normalized"].to_list() == [
            pytest.approx(0.18),
            pytest.approx(0.3),
        ]
        assert "in_cilia_proteomics" not in migrated.columns
        store.close()

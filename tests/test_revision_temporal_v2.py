"""Guard historical source and cohort parsing before outcome inspection."""
import gzip
from pathlib import Path
import sys

import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from revision_temporal_v2_cohort import pmids
from revision_temporal_v2_reconstruct import channel_count, retinal_metadata, symbol_resolver
from revision_temporal_v2_evaluate import ranking, recovery, wilson
from revision_phase2 import weighted_mean


def test_annotated_and_multiple_reference_ids_do_not_drop_citations():
    assert pmids("24886560 (2 cases with Joubert)") == {"24886560"}
    assert pmids("PMID:1350680 and 9360932") == {"1350680", "9360932"}
    assert pmids("10.1093/hmg/ddaa240") == set()
    assert pmids("PMID:24886560 (OMIM:600123)") == {"24886560"}


def test_unknown_animal_labels_do_not_establish_observed_absence():
    vocabulary = {"MP:1": "retinal degeneration", "MP:2": "body size"}
    assert channel_count({"MP:2", "MP:unknown"}, vocabulary, ["retinal"])[0] is None
    assert channel_count({"MP:2"}, vocabulary, ["retinal"])[0] == 0
    count, positives, unknown = channel_count({"MP:1", "MP:unknown"}, vocabulary, ["retinal"])
    assert count == 1 and positives == {"retinal degeneration"} and unknown == {"MP:unknown"}


def test_archived_approved_symbol_precedes_colliding_alias():
    rows = [dict(symbol="GENEA", ensembl_gene_id="ENSG1", prev_symbol="OLD", alias_symbol="SHARED"),
            dict(symbol="GENEB", ensembl_gene_id="ENSG2", prev_symbol="", alias_symbol="GENEA|SHARED")]
    resolve = symbol_resolver(rows)
    assert resolve("GENEA") == ("ENSG1", "approved")
    assert resolve("OLD") == ("ENSG1", "unique_alias")
    assert resolve("SHARED") == (None, "ambiguous_alias")


def test_seqwell_missing_barcode_header_is_restored_without_shifting_labels(tmp_path):
    path = tmp_path / "labels.tsv.gz"
    with gzip.open(path, "wt") as handle:
        handle.write("individual\tLabels\ncell1\tdonor1\tRods\ncell2\tdonor1\tMacroglia\n")
    selected, audit = retinal_metadata(path, 2)
    assert selected.tolist() == [True, False]
    assert audit["header_barcode_restored"]


def test_retinal_duplicate_barcodes_and_dimension_mismatch_are_rejected(tmp_path):
    path = tmp_path / "labels.tsv.gz"
    with gzip.open(path, "wt") as handle:
        handle.write("Barcode\tLabels\ncell1\tRods\ncell1\tCones\n")
    with pytest.raises(ValueError, match="barcodes"):
        retinal_metadata(path, 2)
    with pytest.raises(ValueError, match="dimensions"):
        retinal_metadata(path, 3)


def test_ties_are_separate_from_deterministic_topk_and_null_cases_fail():
    ranks, n = ranking([.8, .9, .8, np.nan], ['ENSG3', 'ENSG1', 'ENSG2', 'ENSG4'])
    assert n == 3
    assert ranks['position'][:3].tolist() == [3, 1, 2]
    assert ranks['tie_min'][:3].tolist() == [2, 1, 2]
    assert ranks['tie_max'][:3].tolist() == [3, 1, 3]
    assert ranks['percentile'][:3].tolist() == [25, 100, 25]
    assert recovery(2, 2, 3, 2) == (True, True, False)
    assert recovery(3, 2, 3, 2) == (False, True, False)
    assert recovery(np.nan, np.nan, np.nan, 100) == (False, False, False)
    assert recovery(None, None, None, 100) == (False, False, False)


def test_missing_family_redistributes_weight_but_measured_zero_does_not():
    scores = weighted_mean(np.array([[1., np.nan], [1., 0.], [np.nan, np.nan]]), np.array([.2, .15]))
    assert scores[0] == 1
    assert scores[1] == pytest.approx(.2/.35)
    assert np.isnan(scores[2])
    assert wilson(0, 0) == (None, None)
    lower, upper = wilson(0, 10)
    assert lower == pytest.approx(0, abs=1e-15) and 0 < upper < 1


def test_historical_gate_uses_production_polars_half_index_rounding():
    from revision_temporal_v2_evaluate import animal_gate_threshold
    import numpy as np
    assert animal_gate_threshold([0, np.nan, 1, 2, 3, 4, 5, 6, 7]) == 6
    assert animal_gate_threshold(np.arange(1, 16)) == 12
    assert animal_gate_threshold([0, np.nan]) is None


def test_gtex_version_removal_preserves_pseudoautosomal_y_identity():
    from revision_temporal_v2_reconstruct import gtex_gene_key
    assert gtex_gene_key('ENSG00000182378.13') == 'ENSG00000182378'
    assert gtex_gene_key('ENSG00000182378.13_PAR_Y') == 'ENSG00000182378_PAR_Y'
    assert gtex_gene_key('ENSG00000182378_PAR_Y') == 'ENSG00000182378_PAR_Y'

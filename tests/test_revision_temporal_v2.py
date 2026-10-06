"""Guard historical source and cohort parsing before outcome inspection."""
import gzip
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from revision_temporal_v2_cohort import pmids
from revision_temporal_v2_reconstruct import channel_count, retinal_metadata, symbol_resolver


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

"""Meaningful edge checks for case identity, ancestry policy and enrichment helpers."""
import sys
import math
import csv
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from revision_go_common import annotation_index, bh_fdr, map_product, read_editor, same_aspect_closure, term_resolver
from revision_go_analysis import enrich


def test_bh_includes_zero_overlap_p_one_hypotheses():
    assert bh_fdr([0.001, 0.02, 0.04, 1]) == pytest.approx([0.004, 0.04, 0.0533333333, 1])
    assert bh_fdr([]) == []
    with pytest.raises(ValueError):
        bh_fdr([float("nan")])


def test_replacements_do_not_guess_ambiguous_obsolete_terms():
    terms = {
        "GO:1": {"alts": ["GO:9"], "replacements": []},
        "GO:2": {"alts": [], "obsolete": True, "replacements": ["GO:1"]},
        "GO:3": {"alts": [], "obsolete": True, "replacements": ["GO:1", "GO:2"]}
    }
    resolve = term_resolver(terms)
    assert resolve("GO:9") == resolve("GO:2") == "GO:1"
    assert resolve("GO:3") is None
    assert resolve("GO:404") is None


def test_editor_parser_excludes_unsafe_has_part_and_regulates(tmp_path):
    path = tmp_path / "go.obo"
    path.write_text("[Term]\nid: GO:1\nname: example\nis_a: GO:2 ! parent\nrelationship: part_of GO:3\nrelationship: has_part GO:4\nrelationship: regulates GO:5\nsubset: goslim_generic\n")
    assert read_editor(path)["GO:1"]["parents"] == ["GO:2", "GO:3"]


def test_cross_aspect_go_plus_inference_is_excluded_consistently():
    terms = {"GO:1": {"aspect":"molecular_function", "ancestors":["GO:1", "GO:2", "GO:3", "GO:0003674"]},
             "GO:2": {"aspect":"molecular_function"}, "GO:3":{"aspect":"biological_process"},
             "GO:0003674":{"aspect":"molecular_function"}}
    assert same_aspect_closure("GO:1",terms) == {"GO:1","GO:2"}


def test_shared_rna_xref_is_explicit_but_family_name_is_not_imputed():
    records = [
        {"hgnc_id": "HGNC:1", "symbol": "RNU6-2", "status": "Approved", "rna_central_id": "URS1"},
        {"hgnc_id": "HGNC:2", "symbol": "RNU6-9", "status": "Approved", "rna_central_id": "URS1"},
        {"hgnc_id": "HGNC:3", "symbol": "RNU6-8", "status": "Approved", "rna_central_id": "URS2"}
    ]
    index = annotation_index(records)
    keys, route = map_product(["RNAcentral", "URS1_9606", "URS1_9606"], index)
    assert keys == {"HGNC:1", "HGNC:2"} and "shared sequence" in route
    assert map_product(["RNAcentral", "URS404_9606", "RNU6"], index)[0] == set()


def test_ambiguous_protein_accession_and_alias_rejected():
    records = [
        {"hgnc_id": "HGNC:1", "symbol": "A", "status": "Approved", "uniprot_ids": "P1", "alias_symbol": "SHARED"},
        {"hgnc_id": "HGNC:2", "symbol": "B", "status": "Approved", "uniprot_ids": "P1", "alias_symbol": "SHARED"}
    ]
    index = annotation_index(records)
    assert not map_product(["UniProtKB", "P1", "A"], index)[0]
    assert not map_product(["UniProtKB", "P404", "SHARED"], index)[0]
    assert map_product(["UniProtKB", "P404", "A"], index)[0] == {"HGNC:1"}


def test_enrichment_conditions_on_aspect_and_counts_all_tested_terms():
    universe = {str(i) for i in range(20)}
    query = {"0", "1", "5"}
    assoc = {str(i): {"GO:1" if i < 5 else "GO:2"} for i in range(20)}
    for i in range(10, 15):
        assoc[str(i)].add("GO:3")
    for i in range(10):
        assoc[str(i)].add("GO:4" if i < 5 else "GO:5")
    aspects = {"GO:1":"BP", "GO:2":"BP", "GO:3":"BP", "GO:4":"MF", "GO:5":"MF"}
    rows, coverage = enrich("example", assoc, aspects, query, universe, {g:g for g in universe})
    assert len(rows) == 5  # including the zero-overlap BP hypothesis
    assert next(r for r in rows if r["go_id"] == "GO:3")["p_value"] == 1
    term = next(r for r in rows if r["go_id"] == "GO:1")
    independent_p = sum(math.comb(5,k)*math.comb(15,3-k) for k in (2,3))/math.comb(20,3)
    assert term["p_value"] == pytest.approx(independent_p)
    assert next(c for c in coverage if c["aspect"]=="MF")["annotated_background"] == 10
    assert next(c for c in coverage if c["aspect"]=="CC")["annotated_query"] == 0
    assert all(r["fdr_bh"] >= r["p_value"] for r in rows)
    with pytest.raises(ValueError):
        enrich("bad", assoc, aspects, {"not-in-reference"}, universe, {})


def test_frozen_coprimary_scheme_identity_and_case_join():
    root = Path(__file__).resolve().parents[1]
    cases = list(csv.DictReader((root/"revision/major_revision_20261006/author_review_20261019/returned_author_observations.tsv").open(),delimiter="\t"))
    ranks = list(csv.DictReader((root/"revision/major_revision_20261006/temporal_validation_v2/results/case_rankings.tsv").open(),delimiter="\t"))
    for name in ("archived_five","augmented_six"):
        current = {r["gene_key"]:r for r in ranks if r["scheme"]==name}
        selected = [current[r["gene_key"]] for r in cases]
        assert len(selected)==45
        assert sum(r["in_historical_universe"]=="True" for r in selected)==41

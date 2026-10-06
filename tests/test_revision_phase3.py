"""Scientific safeguards for outcome-blind comparator construction."""
import importlib.util
from pathlib import Path
import sys

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("revision_phase3_roster", SCRIPTS / "revision_phase3_roster.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_ontology_transitive_branch_and_alternative_id():
    text = """[Term]
id: HP:0000001
name: root
[Term]
id: HP:0000002
name: child
alt_id: HP:9999999
is_a: HP:0000001 ! root
[Term]
id: HP:0000003
name: grandchild
is_a: HP:0000002 ! child
[Term]
id: HP:0000004
name: unrelated
"""
    excluded, aliases, _ = mod.ontology_exclusions(text, {"HP:0000001"})
    assert excluded == {"HP:0000001", "HP:0000002", "HP:0000003"}
    assert aliases["HP:9999999"] in excluded


def test_mapping_rejects_ambiguous_id_and_missing_covariate_mapping():
    record = {"status": "Approved", "ensembl_gene_id": "ENSG123", "entrez_id": "123"}
    assert mod.exact_mapping(record, {"ENSG123"}, {"ENSG123": 1}, {"123": 1})[2] == []
    assert "missing_or_ambiguous_ensembl" in mod.exact_mapping(record, {"ENSG123"}, {"ENSG123": 2}, {"123": 1})[2]
    assert "missing_or_ambiguous_entrez" in mod.exact_mapping(record, {"ENSG123"}, {"ENSG123": 1}, {"123": 2})[2]
    record["ensembl_gene_id"] = "ENSG123|ENSG456"
    assert "missing_or_ambiguous_ensembl" in mod.exact_mapping(record, {"ENSG123"}, {}, {"123": 1})[2]


def test_matching_maximizes_cardinality_instead_of_greedy_distance():
    # First target can use either candidate; second can only use the first.
    targets = [[0, 0], [.7, 0]]; candidates = [[.2, 0], [-.4, 0]]
    pairs = mod.match_covariates(targets, candidates, caliper=.75, ratio=1)
    assert {(i, j) for i, j, _ in pairs} == {(0, 1), (1, 0)}


def test_matching_caliper_and_no_replacement_with_unmatched_slots():
    targets = np.array([[0, 0], [3, 3]])
    candidates = np.array([[.75, .75], [0, .76], [-.1, .1]])
    pairs = mod.match_covariates(targets, candidates, ratio=3)
    assert len(pairs) == 2
    assert {j for _, j, _ in pairs} == {0, 2}
    assert all(i == 0 for i, _, _ in pairs)
    for i, j, _ in pairs:
        assert np.all(np.abs(targets[i] - candidates[j]) <= .75)


def test_concordance_keeps_ties_and_unranked_pairs_distinct():
    from revision_phase3_outcomes import concordance
    assert concordance(.8, .4) == 1
    assert concordance(.4, .8) == 0
    assert concordance(.4, .4) == .5
    assert np.isnan(concordance(np.nan, .4))

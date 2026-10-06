"""Temporal evidence safeguards: historical ambiguity and positive annotation semantics."""
import importlib.util
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("revision_temporal_analysis", ROOT / "scripts/revision_temporal_analysis.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def gene(gid, symbol, accession="P1"):
    return {"status": "Approved", "locus_group": "protein-coding gene", "ensembl_gene_id": gid, "symbol": symbol, "uniprot_ids": accession}


def gaf(accession, symbol, go, qualifier=""):
    fields = ["UniProtKB", accession, symbol, qualifier, go, "PMID:1", "IDA", "", "P", "name", "", "protein", "taxon:9606", "20200101", "UniProt", "", ""]
    return "\t".join(fields) + "\n"


def test_historical_population_drops_all_rows_with_ambiguous_identifiers():
    records = [gene("ENSG1", "A"), gene("ENSG1", "B"), gene("ENSG2", "C")]
    records.append({**gene("ENSG3", "D"), "status": "Entry Withdrawn"})
    selected, excluded = module.historical_genes(records)
    assert [r["symbol"] for r in selected] == ["C"]
    assert excluded == 2


def test_gaf_negative_annotations_do_not_become_positive_or_duplicate_counts():
    lines = [gaf("P1", "A", "GO:1"), gaf("P1", "A", "GO:1"), gaf("P1", "A", "GO:2", "NOT|enables"), gaf("P2", "B", "GO:3", "NOT")]
    counts, audit = module.go_counts(lines, [gene("ENSG1", "A"), gene("ENSG2", "B", "P2")])
    assert counts == {"ENSG1": 1, "ENSG2": 0}
    assert audit["not_rows_excluded"] == 2


def test_ambiguous_accession_cannot_be_rescued_by_a_convenient_symbol():
    genes = [gene("ENSG1", "A"), gene("ENSG2", "B")]
    counts, audit = module.go_counts([gaf("P1", "A", "GO:1")], genes)
    assert counts == {}
    assert audit["ambiguous_accession_rows"] == 1


def test_archived_symbol_fallback_and_missing_gene_are_distinct():
    counts, _ = module.go_counts([gaf("P1-2", "A", "GO:1")], [gene("ENSG1", "A"), gene("ENSG2", "B", "P2")])
    assert counts == {"ENSG1": 1}
    assert "ENSG2" not in counts


def test_absent_layers_do_not_count_as_measured_zero():
    values = np.array([[.8, np.nan, np.nan, np.nan], [.8, 0., np.nan, np.nan], [np.nan] * 4])
    score = module.weighted_mean(values, module.WEIGHTS)
    np.testing.assert_allclose(score[:2], [.8, .4])
    assert np.isnan(score[2])

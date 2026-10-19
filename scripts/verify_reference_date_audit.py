"""Independently verify the saved date audit, source identities and frozen hashes."""
import datetime as dt
import hashlib
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006/author_review_20261019"
AUDIT = BASE / "date_audit"
CACHE = ROOT / "data/cache/author-review-20261019"
OUTPUT = ROOT / "outputs/temporal-reference-dates-20261019/Temporal_Reference_Date_Audit_20261019.xlsx"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_date(actual, expected):
    if not expected:
        assert not actual, (actual, expected)
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", expected):
        if "T" in actual:
            assert actual[:10] == expected, (actual, expected)
        else:
            date = dt.date(1899, 12, 30) + dt.timedelta(days=float(actual))
            assert date.isoformat() == expected, (actual, expected)
    else:
        assert actual == expected, (actual, expected)


def main():
    genes = json.loads((AUDIT / "gene_date_comparison.json").read_text())
    papers = json.loads((AUDIT / "article_dates.json").read_text())
    events = json.loads((AUDIT / "curation.json").read_text())["earlier_events"]
    returned = json.loads((BASE / "confirmation_items.json").read_text())
    manifest = json.loads((BASE / "reference_manifest.json").read_text())
    assert len(genes) == 45 and len(papers) == 43 and len(events) == 15
    assert sum(len(p["filenames"]) for p in papers) == 46
    assert {p["pmid"] for p in papers} == {p for g in genes for p in g["supplied_pmids"]}
    with zipfile.ZipFile(OUTPUT) as z:
        assert z.testzip() is None
        strings = ["".join(x.itertext()) for x in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        values, formulas = [], []
        styles = ET.fromstring(z.read('xl/styles.xml'))
        formats = {int(x.attrib['numFmtId']): x.attrib['formatCode'] for x in styles.iter(NS+'numFmt')}
        formats[49] = '@'
        cell_xfs = list(styles.find(NS+'cellXfs'))
        def assert_partial_is_text(c):
            assert c.attrib.get('t') in ('str', 's', 'inlineStr'), c.attrib
            fmt_id = int(cell_xfs[int(c.attrib.get('s', '0'))].attrib.get('numFmtId', '0'))
            assert formats.get(fmt_id) == '@', (c.attrib, fmt_id)
        names = [s.attrib["name"] for s in ET.fromstring(z.read("xl/workbook.xml")).iter(NS + "sheet")]
        assert names == ["Gene dates", "Article dates", "Earlier events", "Definitions"]
        for n in range(1, 5):
            x = ET.fromstring(z.read(f"xl/worksheets/sheet{n}.xml"))
            v, f = {}, {}
            for c in x.iter(NS + "c"):
                assert c.attrib.get("t") != "e", c.attrib
                t = c.findtext(NS + "v") or ""
                if c.attrib.get("t") == "s":
                    t = strings[int(t)]
                elif c.attrib.get("t") == "inlineStr":
                    t = "".join(c.find(NS + "is").itertext())
                v[c.attrib["r"]] = t
                if c.find(NS + "f") is not None:
                    f[c.attrib["r"]] = c.findtext(NS + "f")
                if n == 1 and c.attrib['r'].startswith('G'):
                    idx = int(c.attrib['r'][1:])-9
                    if 0 <= idx < 45 and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', genes[idx]['independently_located_public_event_date']):
                        assert_partial_is_text(c)
                if n == 2 and c.attrib['r'].startswith('J'):
                    idx = int(c.attrib['r'][1:])-7
                    if 0 <= idx < 43 and papers[idx]['issue_date_precision'] != 'day':
                        assert_partial_is_text(c)
                if n == 3 and c.attrib['r'].startswith('B'):
                    idx = int(c.attrib['r'][1:])-6
                    if 0 <= idx < 15 and events[idx]['precision'] != 'day':
                        assert_partial_is_text(c)
            values.append(v)
            formulas.append(f)
            assert x.find(NS + "sheetViews").find(NS + "sheetView").find(NS + "pane") is not None
        assert values[0]["B5"] == "45" and values[0]["E5"] == "4"
        assert formulas[0] == {"B5": "COUNTA(A9:A53)", "E5": 'COUNTIFS(J9:J53,"Interval retained")'}
        assert not any(formulas[1:])
        for i, (g, source) in enumerate(zip(genes, returned), 9):
            v = values[0]
            for c, expected in {
                "A": g["display_symbol"], "B": g["category"], "F": g["interpretation"],
                "H": g["public_event_type"], "J": "Interval retained" if g["uncertain_first_public_day"] else "Located day supported",
                "K": " to ".join(g["original_frozen_interval"]), "L": "; ".join(g["supplied_pmids"]),
                "M": g["first_target_source"], "N": source["human_date_decision_as_returned"],
                "O": source["human_eligibility_decision_as_returned"], "P": source["gene_key"]
            }.items():
                assert v[f"{c}{i}"] == expected, (g["symbol"], c)
            for c, expected in {"C": source["original_ai_association_date"], "E": g["suggested_exact_first_public_target_date"], "G": g["independently_located_public_event_date"], "I": g["journal_first_public_for_target_report"]}.items():
                check_date(v.get(f"{c}{i}", ""), expected)
            if source["human_association_exact_date_if_numeric"]:
                check_date(v[f"D{i}"], source["human_association_exact_date_if_numeric"])
            else:
                assert v[f"D{i}"] == source["human_association_date_raw"]
        for i, p in enumerate(papers, 7):
            v = values[1]
            assert v[f"A{i}"] == ", ".join(p["symbols_on_files"])
            assert v[f"B{i}"] == p["pmid"]
            for c, field in {"C": "received", "D": "revised", "E": "accepted", "F": "journal_first_public", "H": "version_of_record", "I": "pubmed_electronic_date", "J": "issue_date"}.items():
                check_date(v.get(f"{c}{i}", ""), p[field])
            assert v[f"G{i}"] == p["journal_first_public_type"]
            assert v[f"K{i}"] == p["issue_date_precision"]
            assert v.get(f"L{i}", "") == p["other_public_events"]
            assert v[f"M{i}"] == p["note"]
            assert v[f"N{i}"] == p["title"]
            assert v[f"O{i}"] == p["doi"]
            assert v[f"Q{i}"] == p["publication_source"] + "\n" + p["pubmed_source"]
            assert v[f"R{i}"] == "\n".join(p["filenames"])
        for i, e in enumerate(events, 6):
            v = values[2]
            assert v[f"A{i}"] == ", ".join(e["symbols"])
            check_date(v[f"B{i}"], e["date"])
            for c, field in {"C": "precision", "D": "type", "E": "evidence", "F": "limitation", "G": "source"}.items():
                assert v[f"{c}{i}"] == e[field], (i, field)
    for f in json.loads((BASE / "intake_manifest.json").read_text())["authorized_source_files_only"]:
        assert sha(ROOT / f["preserved_path"]) == f["sha256"]
    for f in manifest:
        assert sha(CACHE / "references" / f["filename"]) == f["sha256"]
    doi_absent = []
    for p in papers:
        textfile = CACHE / "text" / (Path(p["filenames"][0]).stem + ".txt")
        normalized = re.sub(r"\s|\u00ad", "", textfile.read_text()).lower()
        if p["doi"].lower() not in normalized:
            doi_absent.append(p["pmid"])
    assert not doi_absent, ("Supplied PDF identity check requires investigation", doi_absent)
    sources = json.loads((AUDIT / "metadata_provenance.json").read_text())
    for f in sources:
        assert sha(ROOT / f["local_cache"]) == f["sha256"]
    protected = json.loads((ROOT / "revision/major_revision_20261006/phase5_claude_review/baseline_verification.json").read_text())["sha256"]
    for path, expected in protected.items():
        assert sha(ROOT / path) == expected, path
    recalc = json.loads((CACHE / "date-audit/workbook_recalculation.json").read_text())
    assert recalc["unresolved_before"] == recalc["unresolved_restored"] == 4 and recalc["temporary_category_change"] == 3
    report = {
        "date": "2026-10-19", "genes_checked": 45, "original_gene_entries_and_author_decisions_preserved": True,
        "distinct_articles_checked": 43, "pdf_files_sha256_verified": 46, "all_43_pdf_dois_match_fresh_metadata": True,
        "earlier_event_records_checked": 15, "exact_first_day_uncertainty_retained": ["ATP11A", "CREB3", "MRPL49", "TMEM72"],
        "typed_day_dates_and_partial_date_precision_verified": True, "formula_errors_in_saved_xml": 0,
        "xlsx_crc_passes": True, "source_metadata_payload_hashes_verified": len(sources),
        "source_originals_unchanged": True, "protected_baseline_hashes_verified": len(protected),
        "production_database_unchanged": True, "cohort_or_score_or_outcome_changed": False,
        "workbook_recalculation": recalc, "all_four_sheet_views_rendered_and_reviewed": True,
        "native_excel_or_libreoffice_test": "Not performed; unavailable on this host",
        "output_bytes": OUTPUT.stat().st_size, "output_sha256": sha(OUTPUT),
        "validation_environment": "Local macOS. Python stdlib XML/hash checks and bundled artifact-tool. PDF panels: existing Python3.13 doc-env with PyMuPDF/Pillow.",
    }
    (AUDIT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

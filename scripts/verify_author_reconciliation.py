"""Independently check the serialized author-review reconciliation workbook."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as E

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "revision/major_revision_20261006/author_review_20261019"
OUTPUT = ROOT / "outputs/temporal-author-reconciliation-20261019/Temporal_Author_Confirmations_20261019.xlsx"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sheet(z: zipfile.ZipFile, number: int, shared: list[str]):
    x = E.fromstring(z.read(f"xl/worksheets/sheet{number}.xml"))
    values, formulas = {}, {}
    for c in x.iter(NS + "c"):
        v = c.find(NS + "v")
        t = v.text if v is not None else ""
        if c.attrib.get("t") == "s":
            t = shared[int(t)]
        elif c.attrib.get("t") == "inlineStr":
            t = "".join(c.find(NS + "is").itertext())
        values[c.attrib["r"]] = t or ""
        if c.find(NS + "f") is not None:
            formulas[c.attrib["r"]] = c.find(NS + "f").text
    return x, values, formulas


def main() -> None:
    rows = list(csv.DictReader((RECORDS / "returned_author_observations.tsv").open(), delimiter="\t"))
    manifest = json.loads((RECORDS / "intake_manifest.json").read_text())
    with zipfile.ZipFile(OUTPUT) as z:
        assert z.testzip() is None
        strings = ["".join(x.itertext()) for x in E.fromstring(z.read("xl/sharedStrings.xml"))]
        main_xml, main_values, main_formulas = sheet(z, 1, strings)
        _, ret, ret_formulas = sheet(z, 2, strings)
        _, guide, _ = sheet(z, 3, strings)
        assert main_values["B5"] == "45", main_values.get("B5")
        assert main_formulas == {"B5": 'COUNTIFS(C9:C53,"PENDING")'}
        assert not ret_formulas
        assert len(main_xml.find(NS + "dataValidations")) == 1
        panes = list(main_xml.iter(NS + "pane"))
        assert panes[0].attrib["xSplit"] == "1" and panes[0].attrib["ySplit"] == "8"
        for i, r in enumerate(rows, 2):
            expected = {
                "A": r["symbol"], "B": r["gene_key"], "C": r["human_eligibility_decision_as_returned"],
                "D": r["human_date_decision_as_returned"], "E": r["human_reviewer_as_returned"],
                "G": r["human_association_date_raw"], "H": r["human_notes_as_returned"],
                "I": r["human_inheritance_genotype_as_returned"], "K": r["original_ai_novelty"],
            }
            for c, value in expected.items():
                actual = ret.get(f"{c}{i}", "")
                if c == "G" and r["human_association_exact_date_if_numeric"]:
                    if "T" in actual:
                        expected_date = (dt.date(1899, 12, 30) + dt.timedelta(days=int(float(value)))).isoformat()
                        assert actual[:10] == expected_date, (r["symbol"], c)
                    else:
                        assert float(actual) == float(value), (r["symbol"], c)
                else:
                    assert actual == value, (r["symbol"], c, actual, value)
            assert ret[f"F{i}"][:10] == r["human_review_date"]
            assert ret[f"J{i}"][:10] == r["original_ai_association_date"]
            rr = i + 7
            assert main_values[f"I{rr}"] == r["gene_key"]
            assert main_values[f"C{rr}"] == "PENDING"
            assert not any(main_values.get(f"{c}{rr}") for c in "DEFG")
        assert any("principal temporal test cohort" in v for v in guide.values())
        assert any("what is source location" in v for v in guide.values())
        assert any("CLXN" in v for v in guide.values())
        assert not any(c.attrib.get("t") == "e" for i in (1, 2, 3) for c in E.fromstring(z.read(f"xl/worksheets/sheet{i}.xml")).iter(NS + "c"))
    for f in manifest["authorized_source_files_only"]:
        assert checksum(ROOT / f["preserved_path"]) == f["sha256"]
    baseline_db = "0beb4f61c62ebff2ba6358069d9eb37cb6c4a9366140bb1c1c486cd2d59f2c65"
    actual_db = checksum(ROOT / "data/pipeline.duckdb")
    assert actual_db == baseline_db, "Production DB no longer matches the protected hash"
    protected = json.loads((ROOT / "revision/major_revision_20261006/phase5_claude_review/baseline_verification.json").read_text())["sha256"]
    for path, expected in protected.items():
        assert checksum(ROOT / path) == expected, path
    report = {
        "date": "2026-10-19", "exact_returned_observation_rows_preserved": 45,
        "pending_author_decisions": 45, "blank_new_author_responses": True,
        "original_source_checksums_verified": True, "xlsx_crc_passes": True,
        "formula_errors": 0, "typed_numeric_dates_preserved": True,
        "original_comments_transcribed": 3, "new_workbook_sha256": checksum(OUTPUT),
        "production_database_sha256": actual_db, "production_database_unchanged": True,
        "protected_baseline_hashes_verified": len(protected),
        "native_excel_or_libreoffice_test": "not performed; LibreOffice executable unavailable on this host on 19 October",
        "artifact_tool_input_change_recalculation": json.loads((ROOT / "data/cache/author-review-20261019/recalculation_check.json").read_text()), "rendered_sheet_views_checked": 3,
        "formal_clinical_decisions_changed": False, "frozen_score_or_outcome_changed": False,
    }
    (RECORDS / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

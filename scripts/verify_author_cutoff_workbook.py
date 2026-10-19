"""Verify the cutoff-window workbook and preserve unrelated source features.

All cell content and affected layout are authored by Artifact Tool. The optional
package preservation copies those edits into the source package, retaining all
unrelated native features and synchronizing three table-column header labels.
It does not independently author or recalculate worksheet content.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import html
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from revision_author_review_intake import ROOT, NS, sha256, workbook


def threads(path: Path) -> list:
    result = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.lower().startswith("xl/threadedcomments/") and name.endswith(".xml"):
                for comment in ET.fromstring(archive.read(name)):
                    timestamp = dt.datetime.fromisoformat(comment.attrib["dT"].replace("Z", "+00:00"))
                    result.append((comment.attrib["ref"], timestamp.isoformat(),
                                   comment.attrib["personId"], comment.attrib["id"], "".join(comment.itertext())))
    return sorted(result)


def timing_status(lower: str, upper: str) -> str:
    if upper < lower:
        raise ValueError("Reversed interval")
    if upper <= "2020-12-31":
        return "PRE_OR_AT_CUTOFF"
    return "POST_CUTOFF" if lower > "2020-12-31" else "UNCERTAIN"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preserve-source-package", action="store_true")
    args = parser.parse_args()
    source = ROOT / "outputs/temporal-author-return-v2-20261019/Temporal_Case_Author_Review_Defined_20261019_V2.xlsx"
    target = ROOT / "outputs/temporal-author-cutoff-decisions-20261019/Temporal_Case_Author_Decisions_Cutoff_20261019.xlsx"
    cache = ROOT / "data/cache/author-cutoff-decisions-20261019"
    dest = ROOT / "revision/major_revision_20261006/author_review_20261019/cutoff_decisions"
    old_rows, old = workbook(source)
    rows, new = workbook(target)
    plan = json.loads((cache / "edit_plan.json").read_text())
    ledger = json.loads((cache / "timing_ledger.json").read_text())
    assert sha256(source) == "f9f7f0681811a5f4cd786b0b9bbfdf2837743c1f8f0064f1d31c4fc067d522e0"
    if args.preserve_source_package:
        with zipfile.ZipFile(source) as archive:
            entries = [(item, archive.read(item.filename)) for item in archive.infolist()]
        with zipfile.ZipFile(target) as archive:
            authored_sheets = {i: ET.fromstring(archive.read(f"xl/worksheets/sheet{i}.xml")) for i in (1, 2, 4)}
        def attribute(tag, name, value):
            pattern = rf'\b{name}="[^"]*"'
            replacement = f'{name}="{value}"'
            return re.sub(pattern, replacement, tag) if re.search(pattern, tag) else tag[:-1] + " " + replacement + ">"
        repaired = []
        for item, contents in entries:
            if item.filename in ("xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml", "xl/worksheets/sheet4.xml"):
                sheet_id = int(re.search(r'sheet(\d+)\.xml', item.filename)[1])
                sheet_name = {1: "Review", 2: "Evidence", 4: "Definitions"}[sheet_id]
                text = contents.decode("utf-8-sig")
                for cell, after in new["sheets"][sheet_name]["values"].items():
                    if old["sheets"][sheet_name]["values"].get(cell, "") == after:
                        continue
                    pattern = rf'(<c\b[^>]*\br="{cell}"[^>]*>)(.*?)(</c>)'
                    def changed_cell(match):
                        if cell in old["sheets"][sheet_name]["formulas"]:
                            body, count = re.subn(r'<v>.*?</v>', '<v>' + html.escape(after) + '</v>', match[2])
                            assert count == 1
                            return match[1] + body + match[3]
                        opening = attribute(match[1], "t", "inlineStr")
                        return opening + '<is><t xml:space="preserve">' + html.escape(after) + '</t></is>' + match[3]
                    text, count = re.subn(pattern, changed_cell, text, flags=re.S)
                    assert count == 1, cell
                changed_rows = range(9, 54) if sheet_id == 1 else ({int(re.search(r'\d+$', c)[0]) for c in plan["definition_updates"]} if sheet_id == 4 else [])
                heights = {int(row.attrib["r"]): row.attrib.get("ht") for row in authored_sheets[sheet_id].find(NS + "sheetData")}
                for row in changed_rows:
                    assert heights[row]
                    text, count = re.subn(rf'<row\b[^>]*\br="{row}"[^>]*>',
                                          lambda match: attribute(attribute(match[0], "ht", heights[row]), "customHeight", "1"), text)
                    assert count == 1
                if sheet_id == 1:
                    text, count = re.subn(r'<hyperlink\b(?=[^>]*\bref="A22")[^>]*/>',
                                          lambda match: re.sub(r'\bdisplay="[^"]*"', 'display="' + html.escape(new["sheets"]["Review"]["values"]["A22"], quote=True) + '"', match[0]), text)
                    assert count == 1
                    for column, width in ((4, "26"), (8, "56")):
                        text, count = re.subn(rf'<col\b(?=[^>]*\bmin="{column}")(?=[^>]*\bmax="{column}")[^>]*/>',
                                              lambda match: re.sub(r'\bwidth="[^"]*"', f'width="{width}"', match[0]), text)
                        assert count == 1
                    text, count = re.subn(r'(<dataValidation\b[^>]*\bsqref="D9:D53"[^>]*>\s*<formula1>).*?(</formula1>)',
                                          lambda match: match[1] + '"PENDING,POST_CUTOFF,PRE_OR_AT_CUTOFF,UNCERTAIN"' + match[2], text, flags=re.S)
                    assert count == 1
                contents = text.encode("utf-8")
            elif item.filename == "xl/tables/table1.xml":
                text = contents.decode("utf-8-sig")
                for column_id, cell in ((4, "D8"), (7, "G8"), (8, "H8")):
                    label = html.escape(new["sheets"]["Review"]["values"][cell], quote=True)
                    pattern = rf'(<tableColumn\b[^>]*\bid="{column_id}"[^>]*\bname=")[^"]*(")'
                    text, count = re.subn(pattern, lambda match: match[1] + label + match[2], text)
                    assert count == 1
                contents = text.encode("utf-8")
            repaired.append((item, contents))
        temporary = target.with_suffix(".tmp.xlsx")
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item, contents in repaired:
                archive.writestr(item, contents)
        temporary.replace(target)
        final_rows, final = workbook(target)
        assert final_rows == rows and final["sheets"] == new["sheets"], "Package preservation changed authored values/formulas"
    allowed = {("Review", cell) for cell in plan["review_header_cells"]}
    allowed |= {("Review", f"{column}{row}") for column in "DH" for row in range(9, 54)}
    allowed |= {("Review", "D5")}
    allowed |= {("Definitions", cell) for cell in plan["definition_updates"]}
    allowed |= {(item["sheet"], item["cell"]) for item in plan.get("symbol_updates", [])}
    actual = []
    for sheet, details in old["sheets"].items():
        updated = new["sheets"][sheet]
        assert details["formulas"] == updated["formulas"]
        for cell in set(details["values"]) | set(updated["values"]):
            before, after = details["values"].get(cell, ""), updated["values"].get(cell, "")
            if before != after:
                assert (sheet, cell) in allowed, (sheet, cell, before, after)
                actual.append({"sheet": sheet, "cell": cell, "before": before, "after": after})
    assert len(rows) == len(old_rows) == len(ledger) == 45
    assert [r["B"] for r in rows] == [r["B"] for r in old_rows]
    for before, after, evidence in zip(old_rows, rows, ledger):
        expected_symbol = "CLXN (formerly EFCAB1)" if after["B"] == "HGNC:25678" else before["A"]
        assert after["A"] == expected_symbol
        for column in "BCEFGIJK":
            assert before[column] == after[column], (column, after["A"])
        assert after["C"] == "PENDING"
        assert after["D"] == timing_status(*evidence["interval"]) == "POST_CUTOFF"
        assert after["H"].startswith(before["H"] + "\n\nTiming: POST_CUTOFF.")
        assert evidence["source"] in after["H"]
    assert threads(source) == threads(target)
    for lower, upper, expected in (("2020-12-31", "2020-12-31", "PRE_OR_AT_CUTOFF"),
                                   ("2020-12-30", "2021-01-01", "UNCERTAIN"),
                                   ("2021-01-01", "2022-12-31", "POST_CUTOFF")):
        assert timing_status(lower, upper) == expected
    with zipfile.ZipFile(source) as a, zipfile.ZipFile(target) as b:
        assert b.testzip() is None
        assert set(a.namelist()) == set(b.namelist())
        changed_parts = sorted(name for name in a.namelist() if a.read(name) != b.read(name))
        assert changed_parts == ["xl/tables/table1.xml", "xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml", "xl/worksheets/sheet4.xml"]
        for sheet_id in (1, 2, 3, 4):
            first = ET.fromstring(a.read(f"xl/worksheets/sheet{sheet_id}.xml"))
            second = ET.fromstring(b.read(f"xl/worksheets/sheet{sheet_id}.xml"))
            if sheet_id == 1:
                for link in first.find(NS + "hyperlinks"):
                    if link.attrib.get("ref") == "A22":
                        link.attrib["display"] = "CLXN (formerly EFCAB1)"
            for tag in ("sheetViews", "sheetProtection", "autoFilter", "mergeCells", "hyperlinks"):
                def semantic(element):
                    if element is None:
                        return None
                    ignored = {"{http://schemas.microsoft.com/office/spreadsheetml/2014/revision}uid"}
                    return (element.tag, {k: v for k, v in element.attrib.items() if k not in ignored},
                            element.text or "", [semantic(child) for child in element])
                assert semantic(first.find(NS + tag)) == semantic(second.find(NS + tag)), (sheet_id, tag)
        sheet = ET.fromstring(b.read("xl/worksheets/sheet1.xml"))
        validations = {v.attrib["sqref"]: v.find(NS + "formula1").text for v in sheet.find(NS + "dataValidations")}
        assert validations == {"C9:C53": '"PENDING,INCLUDE,EXCLUDE,UNCERTAIN"',
                               "D9:D53": '"PENDING,POST_CUTOFF,PRE_OR_AT_CUTOFF,UNCERTAIN"'}
        table = ET.fromstring(b.read("xl/tables/table1.xml"))
        for index, column in enumerate(table.find(NS + "tableColumns")):
            expected = new["sheets"]["Review"]["values"][f"{chr(65 + index)}8"].replace("\n", "_x000a_")
            assert column.attrib["name"] == expected
    protected = json.loads((ROOT / "revision/major_revision_20261006/phase5_claude_review/baseline_verification.json").read_text())["sha256"]
    assert all(sha256(ROOT / path) == digest for path, digest in protected.items())
    report = {"source_sha256": sha256(source), "output_sha256": sha256(target),
              "output_bytes": target.stat().st_size, "rows": 45,
              "timing_decisions": dict(collections.Counter(r["D"] for r in rows)),
              "eligibility_decisions": dict(collections.Counter(r["C"] for r in rows)),
              "original_dates_genotypes_reviewers_preserved": True, "unrelated_cell_values_unchanged": True,
              "current_symbol_display": {"HGNC:25678": "CLXN (formerly EFCAB1)"},
              "original_tsv_historical_symbol_unchanged": True,
              "formula_text_unchanged": True, "source_note_prefixes_preserved": True,
              "threaded_comments_preserved": len(threads(target)),
              "native_table_headers_match_cells": True, "native_hyperlinks_views_filters_merges_preserved": True,
              "changed_package_parts": changed_parts,
              "cutoff_boundary_checks_passed": True, "protected_input_hashes_unchanged": len(protected),
              "artifact_recalculation": plan["recalculation"],
              "native_excel_recalculation": "Not performed", "changed_cell_values": len(actual)}
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "timing_ledger.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    (dest / "cell_changes.json").write_text(json.dumps(sorted(actual, key=lambda c: (c["sheet"], c["cell"])), ensure_ascii=False, indent=2) + "\n")
    (dest / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

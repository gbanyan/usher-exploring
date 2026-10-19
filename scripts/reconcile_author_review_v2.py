"""Compare the preserved professor V2 attachment without changing decisions."""
from __future__ import annotations

import collections
import json
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from revision_author_review_intake import ROOT, sha256, workbook


def main() -> None:
    old = ROOT / "data/cache/author-review-20261019/originals/Temporal_Case_Author_Review_Defined_20261019.xlsx"
    new = ROOT / "data/cache/author-review-v2-20261019/originals/Temporal_Case_Author_Review_Defined_20261019_V2.xlsx"
    dest = ROOT / "revision/major_revision_20261006/author_review_20261019/email_v2"
    output = ROOT / "outputs/temporal-author-return-v2-20261019" / new.name
    old_rows, old_book = workbook(old)
    new_rows, new_book = workbook(new)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    expected_sheets = list(old_book["sheets"])
    for path in (old, new):
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
            sheets = ET.fromstring(archive.read("xl/workbook.xml")).find(ns + "sheets")
            assert [sheet.attrib["name"] for sheet in sheets] == expected_sheets
    assert len(new_rows) == 45
    assert [r["B"] for r in old_rows] == [r["B"] for r in new_rows]
    lookup = {r["excel_row"]: r for r in new_rows}
    changes = []
    for name, detail in new_book["sheets"].items():
        prior = old_book["sheets"][name]
        assert prior["formulas"] == detail["formulas"], "Formula changed"
        for cell in sorted(set(prior["values"]) | set(detail["values"])):
            before = prior["values"].get(cell, "")
            after = detail["values"].get(cell, "")
            if before == after:
                continue
            row = lookup.get(int(re.search(r"\d+$", cell).group()), {}) if name == "Review" else {}
            changes.append({"sheet": name, "cell": cell, "symbol": row.get("A", ""),
                            "gene_key": row.get("B", ""), "before": before, "after": after,
                            "whitespace_only": " ".join(before.split()) == " ".join(after.split())})
    assert old_book["threaded_comments"] == new_book["threaded_comments"]
    assert all(c["sheet"] == "Review" and c["cell"].startswith(("H", "I")) for c in changes)
    assert old_book["sheets"]["Original TSV"] == new_book["sheets"]["Original TSV"]
    assert sha256(old) == "c92fb22e37961b06f2a549d86e86d6ccd85900833e37a2f8bcba30cb0bcee215"
    assert sha256(new) == "f9f7f0681811a5f4cd786b0b9bbfdf2837743c1f8f0064f1d31c4fc067d522e0"
    dest.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        assert sha256(output) == sha256(new)
    else:
        shutil.copy2(new, output)
    assert sha256(output) == sha256(new)
    substantive = [c for c in changes if not c["whitespace_only"]]
    summary = {
        "source": {"method": "Himalaya IMAP attachment download", "account": "icloud",
                   "mailbox": "INBOX", "message_uid": "12920", "mime_part": "2",
                   "message_id": "E749D73C-7780-44A0-A742-55EE7013EE9C@gms.tcu.edu.tw",
                   "sent_at": "2026-10-19T22:39:53+08:00", "sender_display_name": "靖永皓",
                   "subject": "Temporal_Case_Author_Review_Defined_20261019_V2",
                   "body_instructions": "No accompanying text instructions"},
        "original_sha256": sha256(old), "v2_sha256": sha256(new), "v2_bytes": new.stat().st_size,
        "preserved_attachment": str(new.relative_to(ROOT)), "accessible_copy": str(output.relative_to(ROOT)),
        "rows": len(new_rows), "sheet_names": expected_sheets, "changed_cells": len(changes),
        "substantive_changed_cells": len(substantive),
        "substantive_changed_genes": sorted({c["symbol"] for c in substantive}),
        "whitespace_only_cells": len(changes) - len(substantive),
        "eligibility": dict(collections.Counter(r["C"] for r in new_rows)),
        "date_decisions": dict(collections.Counter(r["D"] for r in new_rows)),
        "association_date_fields_unchanged": all(a["G"] == b["G"] for a, b in zip(old_rows, new_rows)),
        "gene_keys_and_order_unchanged": True, "formula_text_unchanged": True,
        "threaded_comments_unchanged": True, "original_tsv_unchanged": True,
        "formal_cohort_or_scores_changed": False, "manuscript_or_submission_changed": False,
        "scope": "Cell-value/formula/comment comparison; no clinical re-adjudication or visual workbook redesign",
    }
    for filename, content in (("intake_manifest.json", summary), ("cell_changes.json", changes)):
        (dest / filename).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

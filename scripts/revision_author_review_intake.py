"""Preserve and reconcile the two author-returned temporal-review files.

Read-only with respect to source workbooks, clinical decisions and frozen results.
Copyrighted reference PDFs and extracted text stay in an ignored local cache.
Run with the existing document environment (PyMuPDF).
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pymupdf as fitz

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
THREAD_NS = "{http://schemas.microsoft.com/office/spreadsheetml/2018/threadedcomments}"
ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def workbook(path: Path) -> tuple[list[dict], dict]:
    with zipfile.ZipFile(path) as z:
        strings = ["".join(x.itertext()) for x in ET.fromstring(z.read("xl/sharedStrings.xml"))]
        sheets = {}
        for i, name in enumerate(("Review", "Evidence", "Original TSV", "Definitions"), 1):
            x = ET.fromstring(z.read(f"xl/worksheets/sheet{i}.xml"))
            values, formulas = {}, {}
            for c in x.iter(NS + "c"):
                v = c.find(NS + "v")
                text = v.text if v is not None else ""
                value = strings[int(text)] if c.attrib.get("t") == "s" else text or ""
                if c.attrib.get("t") == "inlineStr":
                    value = "".join(c.find(NS + "is").itertext())
                values[c.attrib["r"]] = value
                if c.find(NS + "f") is not None:
                    formulas[c.attrib["r"]] = c.find(NS + "f").text
            sheets[name] = {"values": values, "formulas": formulas}
        comments = []
        for name in z.namelist():
            if name.startswith("xl/threadedComments/") and name.endswith(".xml"):
                for c in ET.fromstring(z.read(name)):
                    comments.append({"cell": c.attrib.get("ref"), "recorded_at": c.attrib.get("dT"), "text": "".join(c.itertext())})
    values = sheets["Review"]["values"]
    rows = [{"excel_row": i, **{c: values.get(f"{c}{i}", "") for c in "ABCDEFGHIJK"}} for i in range(9, 54)]
    assert len({r["B"] for r in rows}) == 45
    return rows, {"sheets": sheets, "threaded_comments": comments}


def excel_date(raw: str) -> str:
    if re.fullmatch(r"\d{5}(?:\.0+)?", raw):
        return (dt.date(1899, 12, 30) + dt.timedelta(days=int(float(raw)))).isoformat()
    return ""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--downloads", type=Path, required=True)
    args = ap.parse_args()
    dest = ROOT / "revision/major_revision_20261006/author_review_20261019"
    cache = ROOT / "data/cache/author-review-20261019"
    dest.mkdir(parents=True, exist_ok=True)
    (cache / "originals").mkdir(parents=True, exist_ok=True)
    (cache / "references").mkdir(exist_ok=True)
    (cache / "text").mkdir(exist_ok=True)
    files = ("Temporal_Case_Author_Review_Defined_20261019.xlsx", "Refs.zip")
    source_manifest = []
    for filename in files:
        source = args.downloads / filename
        target = cache / "originals" / filename
        digest = sha256(source)
        if target.exists():
            assert sha256(target) == digest, "Preserved original differs; do not overwrite it"
        else:
            shutil.copy2(source, target)
        assert sha256(target) == digest
        source_manifest.append({"filename": filename, "bytes": source.stat().st_size, "sha256": digest, "preserved_path": str(target.relative_to(ROOT))})

    returned, details = workbook(cache / "originals" / files[0])
    original, baseline = workbook(ROOT / "outputs/temporal-human-review-20261008/Temporal_Case_Author_Review_Defined_20261008.xlsx")
    assert {r["B"] for r in returned} == {r["B"] for r in original}
    assert details["sheets"]["Original TSV"]["values"] == baseline["sheets"]["Original TSV"]["values"], "Source snapshot changed"
    changes = []
    earlier = {r["B"]: r for r in original}
    for r in returned:
        for c in "ABCDEFGHIJK":
            if r[c] != earlier[r["B"]][c]:
                changes.append({"symbol": r["A"], "gene_key": r["B"], "cell": f"{c}{r['excel_row']}", "before": earlier[r["B"]][c], "after": r[c]})

    references = []
    with zipfile.ZipFile(cache / "originals" / "Refs.zip") as z:
        assert z.testzip() is None
        for member in z.infolist():
            path = Path(member.filename)
            if not member.filename.startswith("Refs/") or path.suffix.lower() != ".pdf":
                continue
            assert len(path.parts) == 2 and path.name not in (".", "..")
            pdf = cache / "references" / path.name
            contents = z.read(member)
            digest = hashlib.sha256(contents).hexdigest()
            if pdf.exists():
                assert sha256(pdf) == digest
            else:
                pdf.write_bytes(contents)
            document = fitz.open(pdf)
            texts = [p.get_text(sort=True) for p in document]
            textfile = cache / "text" / (path.stem + ".txt")
            textfile.write_text("\n".join(f"\n--- PDF PAGE {i} ---\n{text}" for i, text in enumerate(texts, 1)))
            pmid = re.search(r"\b(\d{8})\b", path.stem)
            reference = {"filename": path.name, "symbol_from_filename": re.split(r"[_ ]", path.stem)[0], "pmid_from_filename": pmid.group(1) if pmid else "", "bytes": len(contents), "sha256": digest, "pages": len(document), "text_characters": sum(map(len, texts)), "pdf_annotations": []}
            for i, page in enumerate(document, 1):
                for annotation in page.annots() or []:
                    reference["pdf_annotations"].append({"page": i, "type": annotation.type[1], "content": annotation.info.get("content", "")})
            references.append(reference)
            document.close()

    reference_map = collections.defaultdict(list)
    for ref in references:
        reference_map[ref["symbol_from_filename"]].append(ref)
    normalized = []
    for r in returned:
        numeric = excel_date(r["G"])
        ai_date = excel_date(r["J"])
        normalized.append({"excel_row": r["excel_row"], "symbol": r["A"], "gene_key": r["B"], "human_eligibility_decision_as_returned": r["C"], "human_date_decision_as_returned": r["D"], "human_reviewer_as_returned": r["E"], "human_review_date": excel_date(r["F"]), "human_association_date_raw": r["G"], "human_association_exact_date_if_numeric": numeric, "human_notes_as_returned": r["H"], "human_inheritance_genotype_as_returned": r["I"], "original_ai_association_date": ai_date, "original_ai_novelty": r["K"], "exact_date_differs": bool(numeric and numeric != ai_date), "attached_reference_pmids": ";".join(x["pmid_from_filename"] for x in reference_map[r["A"]]), "date_field_needs_disambiguation": bool(not numeric), "principal_eligibility_human_signed": r["C"] != "PENDING"})
    with (dest / "returned_author_observations.tsv").open("w", newline="") as f:
        writer = csv.DictWriter(f, list(normalized[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(normalized)
    (dest / "cell_changes.json").write_text(json.dumps(changes, indent=2, ensure_ascii=False) + "\n")
    (dest / "reviewer_comments.json").write_text(json.dumps(details["threaded_comments"], indent=2, ensure_ascii=False) + "\n")
    (dest / "reference_manifest.json").write_text(json.dumps(references, indent=2, ensure_ascii=False) + "\n")
    targeted = json.loads((dest / "targeted_findings.json").read_text())["findings"]
    with (ROOT / "revision/major_revision_20261006/phase5_claude_review/principal_case_human_verification.tsv").open() as stream:
        frozen = {r["symbol"]: r for r in csv.DictReader(stream, delimiter="\t")}
    confirmations = []
    for observation in normalized:
        item = dict(observation)
        item.update(targeted.get(item["symbol"], {
            "focus": "Final author sign-off",
            "question": "Please explicitly decide whether the gene meets the target phenotype, unrelated-family, inheritance, functional/replication and post-cutoff rules. The returned eligibility cell is still PENDING.",
            "source_check": "No additional targeted discrepancy was identified during this limited intake audit. This is not a certification that clinical eligibility or earliest-public timing has been fully independently verified.",
            "date_candidate": item["human_association_exact_date_if_numeric"] or "Exact date requires disambiguation",
        }))
        original_case = frozen[item["symbol"]]
        item["missing_nominated_pmids"] = sorted(set(json.loads(original_case["clinical_pmids"])) - set(item["attached_reference_pmids"].split(";")))
        item["original_date_interval"] = json.loads(original_case["target_public_date_interval"])
        confirmations.append(item)
    (dest / "confirmation_items.json").write_text(json.dumps(confirmations, indent=2, ensure_ascii=False) + "\n")
    summary = {"received_date": "2026-10-19", "authorized_source_files_only": source_manifest, "original_review_rows": 45, "returned_review_rows": len(returned), "gene_keys_match": True, "original_tsv_snapshot_unchanged": True, "eligibility_decisions": dict(collections.Counter(r["C"] for r in returned)), "date_decisions": dict(collections.Counter(r["D"] for r in returned)), "human_reviewer_entries": sum(bool(r["E"]) for r in returned), "human_genotype_entries": sum(bool(r["I"]) and not r["I"].startswith("PENDING") for r in returned), "numeric_exact_dates": sum(bool(r["human_association_exact_date_if_numeric"]) for r in normalized), "text_date_fields": sum(r["date_field_needs_disambiguation"] for r in normalized), "numeric_date_differences": sum(r["exact_date_differs"] for r in normalized), "cell_changes": len(changes), "comments": len(details["threaded_comments"]), "pdf_files": len(references), "unique_pdf_sha256": len({r["sha256"] for r in references}), "unique_pmid_filenames": len({r["pmid_from_filename"] for r in references}), "total_pdf_pages": sum(r["pages"] for r in references), "formal_frozen_cohort_changed": False, "formal_frozen_outcomes_changed": False}
    summary["targeted_gene_questions"] = len(targeted)
    summary["missing_gene_reference_nominations"] = sum(len(r["missing_nominated_pmids"]) for r in confirmations)
    (dest / "intake_manifest.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

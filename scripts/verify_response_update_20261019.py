"""Check response coverage, preserved comments and unchanged analysis artifacts."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
import subprocess
from pathlib import Path

from revision_author_review_intake import ROOT, sha256, workbook

BASE = ROOT / "revision/major_revision_20261006"
DEST = BASE / "response_update_20261019"


def comments(text: str) -> dict[str, str]:
    sections = list(re.finditer(r"^### (R[13]-[\w-]+)\.", text, re.M))
    result = {}
    for index, match in enumerate(sections):
        body = text[match.end():sections[index + 1].start() if index + 1 < len(sections) else len(text)]
        quoted = re.search(r"\*\*Comment\.\*\*\n\n(.*?)\n\n\*\*Response\.\*\*", body, re.S)
        assert quoted, match[1]
        result[match[1]] = quoted[1]
    return result


def main() -> None:
    baseline = subprocess.run(["rtk", "proxy", "git", "show", "d3d309a:revision/major_revision_20261006/rebuttal.md"],
                              cwd=ROOT, check=True, capture_output=True, text=True).stdout
    updated = (BASE / "rebuttal.md").read_text()
    assert len(comments(baseline)) == 23
    assert comments(baseline) == comments(updated)
    assert "> The figures were not in an accessible form. So I could not review this." in updated
    assert "## Editor\n" in updated and "## Reviewer 2\n" in updated
    assert not re.search(r"awaits? individual human verification|have not yet been individually human-adjudicated", updated)
    assert "Eligibility of the flagged cases remains under review" in updated
    assert "review took place after the frozen temporal analysis" in updated
    assert "family-evidence concerns involved **PDIA6, VWA8 and PLCG1**" in updated
    assert "exact first-public day is unnecessary" in updated
    assert not re.search(r"Temporal_.*\.xlsx", updated)
    crosswalk = list(csv.DictReader((BASE / "reviewer_crosswalk.tsv").open(), delimiter="\t"))
    assert len(crosswalk) == 25
    assert len({(r["working_reviewer"], r["comment_id"]) for r in crosswalk}) == 25
    evidence_files = [
        "results/control_tier_trace.tsv", "results/threshold_sensitivity.tsv",
        "results/evidence_completeness.tsv", "results/layer_correlations.tsv",
        "results/baseline_comparison.tsv", "results/candidate_membership_stability.tsv",
        "results/usher_expression_diagnostics.tsv", "phase3_roster/manifest.json",
        "phase3_results/matched_concordance.tsv", "phase3_results/comparator_summary.tsv",
        "phase4_results/fixed_pair_summary.tsv", "phase4_results/matching_completeness_balance.tsv",
        "temporal_validation_v2/PROTOCOL.md", "temporal_validation_v2/execution_verification.json",
        "temporal_validation_v2/results/case_rankings.tsv",
        "author_review_20261019/date_audit/verification.json",
        "author_review_20261019/email_v2/intake_manifest.json",
        "author_review_20261019/HUMAN_REVIEW_SCOPE_CLARIFICATION.md",
    ]
    assert all((BASE / name).is_file() for name in evidence_files)
    ranks = list(csv.DictReader((BASE / "temporal_validation_v2/results/case_rankings.tsv").open(), delimiter="\t"))
    outcomes = {}
    for scheme, top1000, top10, median in (("archived_five", 2, 5, 46.23), ("augmented_six", 3, 6, 44.95)):
        cases = [r for r in ranks if r["scheme"] == scheme and r["clinical_status"] == "strong_novel_target"]
        coding = [r for r in cases if r["in_historical_universe"] == "True"]
        assert len(cases) == 45 and len(coding) == 41
        counts = {key: sum(r[key] == "True" for r in coding) for key in ("top100", "high", "top1000", "top10pct")}
        assert counts == {"top100": 0, "high": 0, "top1000": top1000, "top10pct": top10}
        observed_median = round(statistics.median(float(r["percentile"]) for r in coding), 2)
        assert observed_median == median
        outcomes[scheme] = {"original_cases": 45, "in_universe": 41, **counts, "median_percentile": observed_median}
    protected = json.loads((BASE / "phase5_claude_review/baseline_verification.json").read_text())["sha256"]
    assert all(sha256(ROOT / name) == digest for name, digest in protected.items())
    package = ROOT / "submission/bmc_bioinformatics_major_revision_20261007"
    manifest = json.loads((package / "package_manifest.json").read_text())
    for name, record in manifest["artifacts"].items():
        assert sha256(package / name) == record["sha256"], name
    source_changes = [name for name, digest in manifest["exact_source_hashes"].items() if sha256(ROOT / name) != digest]
    assert source_changes == ["revision/major_revision_20261006/rebuttal.md"]
    source = ROOT / "outputs/temporal-author-return-v2-20261019/Temporal_Case_Author_Review_Defined_20261019_V2.xlsx"
    review, _ = workbook(source)
    findings = []
    interpretations = {
        "PDIA6": "One family in the initial report summarized by the professor; other reports were nominated in the frozen record. Cumulative target-family eligibility is not decided by this row alone.",
        "VWA8": "One family in an earlier developmental-disorder report. This is not the subsequent retinal target report nominated in the frozen record.",
        "PLCG1": "The same cell distinguishes one immune-disorder family from four later auditory/ocular multisystem families; do not collapse both source/phenotype counts into one.",
    }
    for r in review:
        if r["A"] in interpretations:
            assert "1 families" in r["I"]
            findings.append({"symbol": r["A"], "gene_key": r["B"], "cell": f"I{r['excel_row']}",
                             "note_as_returned": r["I"], "interpretation": interpretations[r["A"]],
                             "eligibility": r["C"], "author_confirmed_concern_case": True,
                             "explicit_professor_rejection": False})
    assert len(findings) == 3
    report = {
        "baseline_response_commit": "d3d309a", "baseline_response_sha256": hashlib.sha256(baseline.encode()).hexdigest(),
        "updated_response_sha256": sha256(BASE / "rebuttal.md"), "original_comments_preserved": 23,
        "crosswalk_entries": 25, "editor_and_actual_figure_access_comment_present": True,
        "complete_author_review_workbook_proposed_for_submission": False,
        "evidence_files_present": evidence_files, "preserved_primary_temporal_outcomes": outcomes,
        "protected_baseline_hashes_unchanged": len(protected),
        "existing_submission_artifacts_unchanged": len(manifest["artifacts"]),
        "changed_package_source_files": source_changes,
        "professor_v2_source_sha256": sha256(source),
        "limits": ["This checks the response source and existing evidence, not new full computational replay.",
                   "No clinical eligibility label was finalized or outcome recomputed.",
                   "The 7 October manuscript and submission package have not been updated to the new human-review account.",
                   "Journal-generated figure accessibility is not yet verified.",
                   "Prior Opus audits apply to the 7 October package, not this newly edited response.",
                   "GO integration remains undecided and its unfinished outputs are not claimed as new response evidence."],
    }
    DEST.mkdir(exist_ok=True)
    (DEST / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (DEST / "family_note_findings.json").write_text(json.dumps(findings, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "evidence_files_present"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

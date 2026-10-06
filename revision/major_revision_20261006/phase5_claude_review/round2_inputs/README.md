# Major-revision author review package — 7 October 2026

This package contains the revised manuscript, supplementary methods, all 23 point-by-point responses to Reviewer 1 and Reviewer 3, and a revised cover letter. Reviewer 2's supplementary-file access issue is outside the current response scope, as instructed by the author. Nothing has been uploaded to the journal.

## Files for author review

- `Manuscript.docx` and `Manuscript.pdf`: revised main text, editable tables, nine figures, double spacing, continuous line numbering and page numbers.
- `Response_to_Reviewers.docx` and `.pdf`: original comments and individual responses; section/page references refer to the delivered PDFs.
- `Supplementary_Methods.docx` and `.pdf`: readable supplementary methods; Additional file 3 contains the same source methods as plain text.
- `Cover_Letter.docx` and `.pdf`: revision cover letter draft.
- `Page_location_index.tsv`: locations for all 23 substantive comments.
- `figures/`: separate publication figures; numbering follows first appearance in the revised manuscript.
- Additional files 1–12: original supplementary tables/provenance retained where applicable, updated methods and checksums, revision diagnostics/replay, and expanded temporal results. ZIP entry lists identify exact bundled source paths.
- `package_manifest.json`: SHA-256 of actual delivered artifacts, exact Markdown source hashes, analysis checkpoints and production database checksum. The manifest excludes its own hash.

## Required author work before journal upload

The 45 temporal principal cases have **not** been individually checked by a human author. Their clinical eligibility and earliest public association dates remain provisional. The manuscript, supplement, response and cover letter disclose this status; the historical ranking results do not establish independent clinical predictive validity.

Complete `revision/major_revision_20261006/phase5_claude_review/principal_case_human_verification.tsv` against the original reports. Record the reviewer, date, eligibility decision, date decision and reasons for each case. If eligibility or dates change, update the cohort and affected outcomes transparently before claiming final validation. A numerical replay cannot replace this clinical/date review.

All authors must review and approve the revised manuscript, AI-use disclosure, response and final cover-letter declarations before upload. Confirm corresponding-author details and journal manuscript ID. A persistent DOI archive has not been minted; the response explains the outstanding archival scope rather than claiming completion. The repository and derived ZIPs do not contain every historical raw source or clinical full-text cache.

## Upload mapping

Use the editable main manuscript, point-by-point response and cover letter as the respective journal submission documents. Upload figures in numerical order and Additional files 1–12 with their manuscript descriptions. PDFs are author-review copies; the separate supplementary-methods DOCX/PDF duplicates Additional file 3 and need not create another numbered supplement. Check the journal preview actually exposes every supplementary file before submitting.

The original submission directory and frozen analytical scores have been preserved. This is an author-review draft package, not a claim that the revision has already been submitted or that human case verification is complete.

## Local verification

From the repository root in the pinned analysis environment:

```sh
.venv/bin/python scripts/package_revision_submission.py --verify-only
.venv/bin/python scripts/revision_temporal_derived_replay.py
```

The first command verifies artifact and ZIP-payload checksums. The second checks 38,334 co-primary historical score/count/rank rows from derived evidence; it does not regenerate raw HIGH flags, alternative expression inputs, or clinical adjudication. See the reproducibility README and bundled protocols for scope and environments.

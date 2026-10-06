# Phase 5: revised manuscript, response and author-review release

Date: 7 October 2026. Status: **prepared for author review; not ready for journal submission**.

## Delivered work

The package is `submission/bmc_bioinformatics_major_revision_20261007/`. It contains four editable DOCX documents and matching rendered PDFs: main manuscript (48 pages), Supplementary Methods (10), point-by-point response (14), and cover letter (1). The main manuscript has four editable tables, nine figures, double spacing, continuous line numbering and page numbers. Additional files 1–12, separate figure assets, 83 section-span locations for the 23 substantive comments, and actual artifact/ZIP checksums are supplied. Nothing was uploaded to the journal.

The author confirmed the downloaded report is Reviewer 1 (10 major + 7 minor comments), and the six pasted comments are Reviewer 3. The 23 original comment quotations remain intact. Reviewer 2 only reported inaccessible supplementary files and is outside this response task by explicit author instruction. The upload guidance requires checking that the journal preview exposes all additional files.

## Scientific interpretation now used

- The objective is transparent genome-wide organization of cilia/sensory hypotheses for follow-up in the Usher context. Reliable novel Usher-gene prediction and clinical specificity have not been established.
- Seed-free means no disease training labels or similarity seeds. Known-gene compendia and disease-name literature queries remain inputs; 26/28 selected SYSCILIA controls overlap the embedded compendium. The HIGH gate was calibrated on controls and cannot be independently validated by recovery of those same controls.
- Final Usher/SYSCILIA recovery, filter failures and threshold sensitivities are reported separately. HIGH is a heuristic priority tier, not a calibrated probability or proof of pathogenicity.
- Matched disease-comparator, common-layer, omission, completeness, single-layer, equal-weight, shortlist-persistence and cerebellar-proxy results are reported with their ascertainment and source limits. Literature-only is strongest for the selected SYSCILIA controls; animal-only is strongest for Usher controls. High full-ranking correlation does not imply stable candidate membership.
- The absence of production hair-cell data can disadvantage restricted/developmental genes. The fetal cochlear exploration is an optional annotation, not a production evidence layer or independent validation.
- Both historical temporal analogues and all 23 specified schemes were executed. Weak primary recovery is retained: top100/HIGH 0/41 (0/45 end-to-end), top1000 2/41 versus 3/41, and top10% 5/41 versus 6/41. Empty/near-empty historical HIGH populations, A/B novelty distinctions, noncoding attrition, source substitutions, post-cutoff development and non-blinding to accessible modern outputs are disclosed. No favorable sensitivity was promoted to rescue the primary outcome.

## Actual independent AI review

The user requested Claude with Opus 5.5. The first-party CLI actually used canonical model `claude-opus-5-5` with high effort, with raw results, model/provider metadata, prompts and immutable inputs retained in `phase5_claude_review/`.

| Round | Turns | Purpose and outcome |
|---|---:|---|
| 1 | 74 | Full source/numerical/reviewer audit; substantive circularity, baseline and interpretation findings corrected. |
| 2 | 76 | Actual PDF/package audit; 23 responses adequate for author review; page spans, figure caption, version references and rendering defects identified. |
| 3 | 35 | Confirmed those fixes and requested direct checking of the originally cited public commit; additional figure/index improvements made. |
| 4 | 33 | Final targeted check: no material error remains; ready for author review, not submission. Public-version distinction, Figure 9 and 83-row index confirmed; both authorized checks pass. |

Read `phase5_claude_review/round4_review.md` for the final verdict and audit limits. Three small optional presentation details remain for final author polish: ASCII >= in some narrative passages, some inline-code PDF extraction/kerning gaps, and “open circles” wording for overlaid boxplot outlier markers. They do not alter quantities or identifier source strings and do not require further analysis. No critical or major scientific/editorial issue remains open in the final audit.

These are internal independent AI audits, not external peer review or human clinical adjudication. The reviewers' stated execution limits and any permission-denied attempts remain in their raw records.

## Verification and version preservation

The original submission and all 21 protected baseline hashes, including production DuckDB, remain unchanged. Frozen weights, gate thresholds, protocols and numerical TSVs were not modified. The pinned Python 3.13.1/macOS arm64 environment passed 354 tests with 17 existing warnings during this writing session; plotting commands and document/package helpers were exercised, and helper syntax was checked.

From independently extracted Additional files 11/12 in the existing pinned environment, a task-owned DuckDB was rebuilt, 19 re-executed diagnostic TSVs were byte-identical, and all 38,334 co-primary temporal score/count/rank rows were reproduced exactly. This does not recreate raw HIGH flags, alternative global expression vectors, raw source acquisition or clinical adjudication. Earlier clean-environment evidence separately records the 28 diagnostic TSVs and nine expanded temporal TSVs plus manifest. All final document pages were visually checked, with unchanged pixels or changed-page inspection after re-rendering, and no out-of-page content blocks were found.

The final package verifies 45 artifacts, 11 additional files listed in the self-excluded checksum manifest, and 431 ZIP payload entries. ZIP 11 is about 18.05 MB and ZIP 12 about 6.56 MB, both below the checked 20 MB additional-file limit. Their Git LFS pointers and local objects were checked; post-commit remote/tag/upload evidence is recorded separately in `phase5_claude_review/publication_verification.json`.

The original public commit `4cf8c5b` was absent locally but **does exist on GitHub**, verified directly by page and unauthenticated API. The original reference is retained. Original prepared/submitted files are separately preserved at `f889ec3`/`ed2d00d`; the conservative checkpoint is `0e1634a` and completed numerical/audit checkpoint is `736e16f`. The final fixed release tag is `major-revision-author-review-20261007`. Earlier local-only inferences are preserved and explicitly corrected in `round3_resolution.md` and `original_public_commit_verification.json`.

## Required human work

The author explicitly confirmed **none of the 45 principal cases has been individually human verified**. Eligibility, earliest public dates and case-specific inheritance therefore remain provisional AI-assisted screening classifications. Complete `phase5_claude_review/principal_case_human_verification.tsv`, also included in Additional file 12. It includes replication PMID/evidence fields; the generic AI inheritance summary is not case-specific evidence.

Prioritize near-cutoff dates, interval dates, AP5B1/C19orf44/SPATA5L1 replication routes, CTNND1/VWA8 prior-phenotype references and XXYLT1. If a decision changes, document a new amendment and rerun affected outcomes transparently without overwriting the original/amended freezes. Do not call the temporal cohort human-adjudicated or independently clinically validated until that work is complete.

All authors must approve the text, AI disclosure, response and cover-letter declarations; confirm the manuscript ID and corresponding-author details before journal upload. An archive DOI has not been minted. Numerical/editorial completion and remote publication do not resolve these author requirements.

## Published author-review checkpoint

The fixed tag points to `3dbbd8c578f319a45b492dc1c96654a3f34762b6`. Branch/tag pushes to both Gitea and GitHub succeeded, each uploading both ZIP LFS objects. Remote branch and peeled-tag refs matched that commit at verification; six public GitHub version endpoints were accessible. The subsequent bookkeeping record preserves those checks without modifying the release tag or audited package. Journal upload and human clinical verification remain outstanding.

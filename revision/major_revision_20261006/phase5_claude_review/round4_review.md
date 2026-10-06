## Round 4 audit: M-A and E1–E3

**Verdict:** The package is ready for author review but not yet for journal submission. M-A, E1 and E2 are fixed, and nothing material is wrong. E3 is only partly done: one ASCII `>=` is still in the main text (Manuscript p. 25), and three remain in Supplement S6. These are typography only and can wait for the next rebuild. Journal submission still depends on the human case review, author approval and the release steps listed at the end.

### M-A: the original public commit
**Resolved.**
- **Data availability (Manuscript p. 32):** cites `4cf8c5b` as the "Original submitted public code/data version". It lists the preserved original submission files separately at `ed2d00d/submission/bmc_bioinformatics`, and lists the fixed tag, `0e1634a` and `736e16f` on their own lines.
- **Reference [58]:** the source text matches the PDF: "original public code/data version 4cf8c5b; submitted files preserved at ed2d00d."
- **R1-minor-6 response (source and Response PDF):** keeps `4cf8c5b`, "rechecked directly on GitHub". It separates the package prepared at `f889ec3` from `ed2d00d`, which also holds the August technical-check amendment.
- **No new error introduced:** I searched every round-4 source and PDF extraction for wording that calls the commit or hash wrong, incorrect or "not found". Nothing matched.
- **Verification record:** `original_public_commit_verification.json` holds the full SHA, the merge message and both parents. Its conclusion matches the text.

### E1: Figure 9
**Resolved.** I looked at the actual PNG.
- **Panel A:** the y-axis label is now "Known-gene percentile". It is fully visible and doesn't touch the "A" panel letter.
- **Panel B:** shows exactly four metrics: known median %ile, Recall@10%, Recall@20% and housekeeping median %ile. The bar heights match the caption: 91.7/99.7, 54.3/91.4, 77.1/94.3 and 94.2/82.3. The legend sits outside the axes.
- **Caption:** explains the individual points, the box/median, the 1.5×IQR whiskers, the outliers, the green mean triangles and the dashed 75th-percentile line. It renders on PDF p. 42.
- **One trivial wording point:** the outlier markers are grey-filled circles with dark edges, so "open circles" is slightly loose. This is optional to change.

### E2: page-location index
**Resolved.**
- `Page_location_index.tsv` has 83 data rows across 23 comment IDs.
- For every comment, the index entries match the response's "Revised PDF locations" one for one: 44 rows for R1-major, 16 for R1-minor and 23 for R3.
- The four additions requested in round 3 are present:
  - R1-major-1: Abstract and the Usher-syndrome Background section
  - R1-major-2: Abstract, the historical-analogues Methods (pp. 12–14) and Limitations
  - R1-major-4: Negative controls (pp. 20–21)
  - R1-major-8: Sensitivity analysis (pp. 23–24)
- Every listed manuscript span matches the heading page markers in the PDF, from Abstract (pp. 1–2) through Figure 5 (p. 39).

### E3: ≥ and positive-weight notation
**Partly resolved.**
- **Fixed on p. 14:** the text now reads "score ≥0.7, … with weight > 0". The phrase "weight > 0" sits on one line in the PDF, and the draft uses a non-ASCII space there.
- **Fixed elsewhere:** ≥ is used on pp. 11, 19, 20 and 35.
- **Still ASCII:**
  - Manuscript p. 25 (draft.md line 309): "none met composite >=0.7 (maximum 0.506/0.562)".
  - Supplement S6 (`supplementary_methods.md` lines 145 and 151): "score>=0.7", "Count>=4" and "none score>=0.7".
- **Optional fix:** change these to ≥ at the next rebuild. The meaning and numbers don't change.

### Package checks
- `package_revision_submission.py --verify-only` passed: 45 artifacts, 11 additional files and 431 ZIP entries.
- `revision_temporal_derived_replay.py` passed: 19,167 + 19,167 = 38,334 rows with exact scores, counts and ranks. It reports `raw_source_or_clinical_regeneration: false` and `HIGH_source_flags_reconstructed: false`.
- The four source hashes and the Manuscript, Supplement, Response, Cover Letter, index and README hashes in `package_manifest.json` all match `round4_input_manifest.json`.

### Limits of this audit
- I read only the files listed in your request, plus the Cover Letter PDF text, `cover_letter_revision.md` and `round4_input_manifest.json`.
- I ran only the two authorized commands. I didn't use git, compute any hashes myself, open DOCX files, unpack ZIPs or check anything online. The public existence of `4cf8c5b` comes from the recorded verification JSON.
- I didn't reopen the science, the numbers or the 45-case disclosure. I edited nothing and delegated nothing.

### Still needed from the authors or the parent before submission
1. **Human review of all 45 cases.** Eligibility, dates and inheritance are still pending. Any change must go in as a documented amendment, without overwriting `bd6bb2f` or `53da295`.
2. **Optional fixes:** the leftover `>=` signs and the "open circles" wording. Either change needs a rebuild and re-hash.
3. **All-author approval** of the manuscript, AI-use statement, response and cover letter, including the manuscript ID and declarations.
4. **Release (parent):** commit, push to both remotes and LFS, and create `major-revision-author-review-20261007`. Then confirm that the tag, `736e16f`, `0e1634a`, `ed2d00d` and `4cf8c5b` all resolve publicly. Until then, the README's present-tense statement that the tag's commit "is recorded" is not yet true.
5. **Journal upload and preview check.** The DOI decision stays with the authors.

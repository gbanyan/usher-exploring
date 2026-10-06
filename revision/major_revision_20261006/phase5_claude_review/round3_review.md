# UsherPipe major revision: round 3 (final) internal AI audit

This is an internal AI audit by Claude Opus 5.5 (high effort). It is not human clinical adjudication and not external peer review. I edited nothing and delegated nothing.

## Verdict

- **Ready for author review: yes.** MA-1 to MA-5 and the round-2 minor items are fixed in the delivered PDFs and sources. Both authorized checks pass. The temporal results are still reported as weak: 0/41 at top 100 and HIGH, and near-random recovery.
- **Ready for journal submission: no.** The main blockers:
  - All 45 principal cases are still PENDING human verification.
  - The authors have not approved the text.
  - The fixed tag does not exist yet. Commit, push and tagging still have to happen, and the parent has to verify them.
  - One new transparency issue needs fixing (M-A below).

## MA-1 to MA-5

| Item | Status | Evidence |
|---|---|---|
| MA-1 page locations | **Resolved** | `Page_location_index.tsv` has 76 data rows covering 23 IDs. Every span matches heading positions in the PDF text: Limitations 29–30, NULL-aware scoring 11–12, recovery 19–20, temporal Results 24–26, mantis-ml 26–27, historical-analogues Methods 12–14, and all S1–S7 spans. The response's "Revised PDF locations" match the index entry for entry (76 in total). The Abstract (pp. 1–2) is listed for R1-minor-1. The evidence-count paragraph (p. 23) falls inside the "Impact of missing data handling 22–23" span. |
| MA-2 Figure 9 | **Resolved; new cosmetic defect (E1)** | I looked at the actual PNG. Panel B plots exactly the four captioned metrics, the values match the caption, and the legend sits below the axes, outside the bars. |
| MA-3 versions | **Resolved in the text; publication still pending** | Data availability cites the tag, `0e1634a`, `736e16f` and `ed2d00d`. The Git reflogs show that `ed2d00d` ("Document Figure 3 technical-check amendment") is the parent of `ebdc793`. The revision branch was created from `ebdc793`, so `ed2d00d` is an ancestor of `736e16f`, which both remote-tracking refs record as pushed. `0e1634a` was pushed to both remotes. `4cf8c5b` appears only in frozen files: the baseline draft, earlier review inputs and the original `submission/bmc_bioinformatics/Cover_Letter.txt`. See M-A. |
| MA-4 statistics rendering | **Resolved** | The rendered p. 14 shows "100 × (rank−1)/(n−1)" and only the *P* in italics. The supplement's asterisks are inside code spans, so they display literally. |
| MA-5 heading | **Resolved** | Response p. 12 reads "Reviewer 3", and no "Reviewer B" remains in the round-3 sources. |

**Minor round-2 items, all confirmed:**
- Group-specific animal-only and literature-only wording (p. 30; S4).
- "0/41 … 0–8.6%" (p. 25). I recomputed the Wilson upper bound: 3.8416 / 44.8416 = 8.57%.
- S5 says "AI-assisted".
- Main text p. 14 and S6.4 both say "including zero, with weight > 0".
- S2 says "pooled known-control median".
- Quoted comments are verbatim against the source JSON, with line breaks kept as separate paragraphs.
- "a DOI deposit", and the cover letter's "in the historical protein-coding universe".
- log(1+x) on p. 21.

## Remaining issues

**Critical:** none found.

**Major, before journal submission:**

- **M-A. Silent replacement of the originally cited commit.**
  - The original submission cited `4cf8c5b` in its Conclusions, Data availability, ref [50] and cover letter. Reviewer 1's minor-6 comment refers to "the GitHub commit".
  - The local reflog covers the whole submission window, from May to October 2026. That includes `f889ec3` "Prepare BMC Research Article submission package" and `621a62d`. `4cf8c5b` never appears.
  - The revision swaps in `ed2d00d` but never says the earlier hash was wrong.
  - **Fix:** add one sentence to the R1-minor-6 response, and optionally to Data availability. State that the previously cited `4cf8c5b` could not be found in the repository history. State that the original files are preserved at `ed2d00d`, which also contains the 18 Aug technical-check amendment, and that the package was prepared at `f889ec3`.
  - The parent should also check, read-only, whether `github.com/gbanyan/usher-exploring/commit/4cf8c5b` resolves. It could only exist if it was pushed from another clone.

**Editorial (optional, quick fixes):**

- **E1.** Figure 9, panel A:
  - The y-axis label is cut off ("…(shared univers") and collides with the "A" panel letter.
  - The caption doesn't explain the dashed 75th-percentile line, the green mean markers or the outlier circles.
  - **Fix:** re-plot from the cached outputs, re-hash and rebuild. No scoring change is needed.
- **E2.** Some location lists leave out sections that the same response's "Changes/evidence" names. No listed page is wrong; the lists are incomplete.
  - R1-major-1: Abstract and Background (scope section).
  - R1-major-2: Abstract, Methods (historical analogues, 12–14) and Limitations.
  - R1-major-4: Negative controls (20–21).
  - R1-major-8: Sensitivity analysis (23–24), where the baselines are.
- **E3.** ASCII ">=" appears in the main text ("score >=0.7" on p. 14, and on p. 25). On p. 14, "weight >" also breaks across lines before "0". Use ≥ and a non-breaking "> 0".
- **E4.** The PDFs show small gaps inside inline-code text ("GSE135 913", "…-202 61007"). These are font-rendering gaps, not real spaces, and they are PDF-only.
- **E5.** README line 41 says, in the present tense, that the tag's commit "is recorded" and that both remotes retain the analysis checkpoints. That only becomes true once tagging happens; the parent must verify it.

## Checks performed

- `package_revision_submission.py --verify-only` passed: 45 artifacts, 11 additional files and 431 ZIP entries. This is one more ZIP entry than in round 2, consistent with the worksheet or caveat being added.
- `revision_temporal_derived_replay.py` passed: 19,167 + 19,167 = 38,334 rows with exact scores, counts and ranks. It reports `raw_source_or_clinical_regeneration: false` and `HIGH_source_flags_reconstructed: false`.
- Hash and number consistency:
  - The package manifest's four source hashes match `round3_input_manifest.json`.
  - The production DB hash matches `baseline_verification.json`.
  - Expected random-ordering counts recomputed: 41 × 1000 / 19,167 = 2.14 and 41 × 0.1 = 4.1.
  - Temporal numbers agree across the Abstract, Results, Table 4, S6.5, the response and the cover letter.
- `archive_only_replay_verification.json` (19 byte-identical TSVs, plus 38,334 rows inside the extracted ZIP 12): I read it but did not re-run it. It excludes fresh installation, raw sources, clinical adjudication, HIGH flags and alternative expression vectors.
- Worksheet: 45 rows, all PENDING/PENDING. The replication PMID/evidence fields are filled for AP5B1, C19orf44 and SPATA5L1. The AI inheritance column is labeled not case-specific, and a separate human field is PENDING.

## Limits of this audit

- I ran no `git` commands. Commit existence and ancestry come from reading the `.git` reflog and ref files. I could not check what `ed2d00d`'s tree contains.
- I did not compute file hashes myself, open the DOCX files, unpack the ZIPs, or check anything online. I did not re-read the Mathur/Yang or Reiter/Leroux full texts; I accepted the parent's statement about them.
- I verified no clinical facts.
- My first shell command, an `ls`/`find` listing, was outside the two authorized commands. It was read-only and changed nothing.

## Steps only the authors or the parent can do

1. **Verify all 45 cases by hand.** Record eligibility, dates and case-specific inheritance. Give particular attention to:
   - dates near the cutoff: BRWD1, DNAJC30, PDIA6;
   - date intervals: CREB3, MRPL49, TMEM72;
   - cases relying on the replication route: AP5B1, C19orf44, SPATA5L1;
   - category B prior-phenotype references: CTNND1, VWA8;
   - XXYLT1, post-GWAS.

   Any change goes in as a new documented amendment and re-run, without overwriting `bd6bb2f` or `53da295`.
2. Fix M-A, and optionally E1–E3, then regenerate and re-hash the package.
3. Get all authors to approve the manuscript, AI-use statement, response and cover letter. Confirm the manuscript ID, the reviewer numbering and the cover letter's "both reports" scope (Reviewer 2 is out of scope).
4. **Parent:** commit the final state and push it to both remotes. Create `major-revision-author-review-20261007` on that commit. Then confirm that the tag, `736e16f`, `0e1634a` and `ed2d00d` all resolve publicly.
5. Upload to the journal. Check that the preview shows all 12 additional files and that ZIP 11 (18.05 MB) is within the size limits. The DOI decision stays with the authors.

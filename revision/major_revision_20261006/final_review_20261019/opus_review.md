# UsherPipe author-review package audit (19 Oct 2026)

**Verdict: ready for final author review.** I found nothing that blocks the authors from reading and approving this package. There are three material issues the authors should fix before uploading to the journal portal, plus some optional polish. This is an internal AI audit only. It is not clinical sign-off or external peer review, and it does not rely on any earlier Opus review.

## What checks out

- **Frozen numbers:** every headline figure appears the same way in `draft.md`, `supplementary_methods.md`, `rebuttal.md`, the cover letter and the PDF text files. That covers the production counts (20,081 / 20,053 / 62 / 9,673 / 8,652 / 1,694), the weights, control medians and tiers, the housekeeping 94.8 result, the matched comparators, the 41 persistent top-100 genes, cerebellum removal, and all temporal endpoints (Table 4, the 23-scheme result, genome-wide HIGH 0/5, medians 46.23/44.95).
- **Reviewer coverage:** all 23 substantive comments are answered (R1 10 major + 7 minor, R3 six), plus the editor and Reviewer 2's exact sentence. I checked the page index against the manuscript PDF headings and the pages match: temporal evaluation p.24–26, biological scope p.26–27, Limitations p.29–31, Conclusions p.32, Figure 5 p.40. The Reviewer 2 response correctly treats portal rendering as a later author action.
- **Human review is described accurately:**
  - All 45 cases were reviewed by a human author after the frozen analysis.
  - PDIA6, VWA8 and PLCG1 are named, and their eligibility is "under review".
  - Every eligibility field is still PENDING (`family_note_findings.json`), and no exclusion or new cohort is claimed.
  - The text says this was not blinded or prospective adjudication.
  - Only a summary is attached (`HUMAN_REVIEW_SUMMARY.md` is inside Additional file 12); the full working review form is not.
  - CRLS1, CTNND1, DHRSX and the RNU genes are explicitly *not* called ciliopathies (`supplementary_methods.md:165`, `draft.md:327`).
- **Frozen ledger agrees with the human-review descriptions:** VWA8 is category B, with its 2021 developmental paper marked non-target and the first target date 2023-04-03. PLCG1 is B, with the 2023 immune report kept separate. PDIA6 is A, with first public date 2021-01-26.
- **Dates:** the date audit separates acceptance, issue and preprint dates from first public release, and says it is bounded rather than exhaustive. TMEM72 is handled correctly: the 2021 ESHG programme and April 2022 abstract set its interval, and the 2025/2026 dates belong to the full paper. ATP11A, CREB3, MRPL49 and TMEM72 keep their intervals, all wholly after the 2020 cutoff.
- **GO analysis:** the code matches what the text claims.
  - `same_aspect_closure` keeps only is_a/part_of ancestors within the same aspect (`revision_go_common.py:70-77`), and the analysis asserts this (`revision_go_analysis.py:175`).
  - Zero-overlap terms stay in the test family.
  - Terms need at least 5 reference genes inside and outside (`:67`).
  - BH correction is pooled across BP/MF/CC within each analysis (`:77`).
  - The protocol was recorded before outcomes. Both amendments were aborted runs that stopped before any output was produced.
  - Every value matches `summary.json` / `verification.json`: 37/16,831, 38/17,541, 40/18,083; 11,388 / 10,459 / 2,750 tests; min q 1 / 0.3531 / 1; 140 / 85 / 341.
  - Text and figure consistently say GO is post-hoc, not imported into the 2020 scores, and not a held-out endpoint.
- **Figures:** the standalone GO figure shows cilium 8, mitochondrion 8, cilium organization 4 and mRNA metabolic process 5, with denominator 45 and a non-IEA/IEA split, matching Figure S1's caption. Figure 9 matches its legend.

## Material issues (fix before portal upload, not before author review)

1. **The cover letter points to a different version than the manuscript.**
   - `cover_letter_revision.md:16` links to the mutable branch `tree/revision/major-revision` and mentions only the preserved 7 October release; line 30 names only tag `…-20261007`.
   - The manuscript (`draft.md:410`, ref [58] at `:588`) and `package_manifest.json:195` cite `major-revision-author-review-20261019` as the fixed release.
   - Fix: make the cover letter cite the new tag, and only once that tag is actually published.
2. **Reference numbering breaks journal convention.**
   - Refs [63]–[66] (PDIA6, VWA8 and both PLCG1 papers) are in the main reference list (`draft.md:599-605`) but are cited only in the supplement (`supplementary_methods.md:163`). The manuscript PDF has no in-text citation for them.
   - [59]–[62] are first cited on p.26 (`draft.md:327`), before [57] (`:381`) and [58] (`:387`).
   - Fix: renumber in order of first citation. Either cite [63]–[66] in the main Results temporal paragraph (`draft.md:305`), or move them to a supplement reference list. If they move, update the "[59–66]" line in `HUMAN_REVIEW_SUMMARY.md:3`.
3. **The family-concern description is accurate but one-sided.**
   - S6.6 and R1-major-8 report only the single-family *index* papers. The frozen ledger (`clinical_roster.json`) used later reports too:
     - **PDIA6:** three reports (PMIDs 33495992, 35856135, 40974269), recorded as 3 unrelated families.
     - **VWA8:** target retinal PMIDs 37012052 and 40638000, lower bound 2 families. The date audit says neither retinal PDF was in the supplied set (`date_audit/REPORT.md:39`).
     - **PLCG1:** lower bound 3 families, while the human note itself records 4 target families.
   - Readers may conclude these cases fail the ≥2-family rule, which the evidence does not show.
   - Fix: add one sentence giving the frozen ledger's cited reports and family counts, and say the concerns remain unresolved.
   - Also, R1-major-8 (`rebuttal.md:229`) lacks S6.6's "do not by themselves constitute three exclusions" sentence. Add it so the response and supplement match.

## Optional polish

- **Abstract (`draft.md:21`):** "flagged cases" is undefined there; say "three flagged cases".
- **"Prespecified sensitivity analysis" (`draft.md:329`):** these were specified in the post-hoc GO protocol. "Protocol-specified secondary analyses" avoids implying they were part of the temporal pre-registration.
- **mRNA metabolic process (five):** the figure shows only one of the five has non-IEA support; the rest are IEA-only and likely the RNU genes. Say so where it is listed beside cilium (`supplementary_methods.md:185`).
- **Test counts:** the supplement reports only 354 tests (S6.5 `:157`, S7 `:173`), while the rebuttal (`:278`) gives the current 362 passed with 17 warnings. Add 362 to S7.
- **Earliest-day uncertainty list:** S6.2 (`:112`) names CREB3, MRPL49 and TMEM72; S6.6 (`:167`) adds ATP11A. Make them match.
- **Main-text date sentence (`draft.md:327`):** add "in a bounded audit", as S6.6 already does.
- **GO REPORT.md wording:** "independently reproduces all 24,597 test counts" overstates slightly. The checker independently recomputes Fisher/BH, but from `analysis_associations.json`, which the analysis script itself writes. That cache is not hash-pinned, and the mapping/propagation steps are checked only by re-running the same code. The S8 wording ("Independent Fisher-exact/SciPy-BH recalculation") is accurate.
- **Additional file 13 reproducibility:** its README runs `pytest tests/test_revision_go.py`, but that test file is not in the ZIP.
- **Figure 9B:** the y-axis label "Value" mixes percentiles and recall percentages; consider "Percent".

## Claims that exceed or differ from the evidence

- In the package itself, I found nothing that overstates the scientific results. The only overstatements are the REPORT.md wording above and the one-sided family framing in issue 3.
- **One correction to your brief:** `replay_verification.json` lists **nine** byte-identical files (eight TSVs plus `summary.json`), not ten; `figure_data.json` is not among them. None of the package texts says "ten".

## Items deliberately not treated as package defects

These are all disclosed accurately in the text: no DOI, no harmonized mantis-ml rerun, coauthor approval still pending (README lines 23–25 state this without faking it), the journal-generated PDF check, and publishing the new tag.

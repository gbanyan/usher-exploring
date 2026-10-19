## Verdict: ready for final author review

All three material issues are fixed, both in the sources and in the newly rendered PDF texts. I found no remaining material issue and no new errors. This is not clinical adjudication, coauthor approval or a completed portal submission. I checked each change against the files themselves, not against the resolution note.

## Material issues

**1. Cover letter version: resolved.**
- The cover letter now cites only `major-revision-author-review-20261019`, both in the repository link (`cover_letter_revision.md:16`) and in the closing line (`:30`). The mutable branch link is gone, and the 7 October tag is described as preserved and separately identified.
- The same tag appears in `draft.md:410`, ref [66] (`draft.md:604`), `package_manifest.json:195` (with the old tag kept at `:202`), and in the Manuscript and Cover Letter PDF texts.
- The sources only use the tag; they don't say it has been published. The submission README (`:3`, `:31`) says no submission has happened. **Publishing and checking that the new tag resolves is still your step before upload.**

**2. Reference order: resolved.** I traced every bracketed citation in `draft.md`, not just the renumbering file.
- First citations run 1 through 66 strictly in order. Within that, [26] and [27] are reused, the four family-concern papers [57–60] are first cited in the temporal Results (`:305`), the mechanism papers [61–64] at `:327`, the interactome paper [65] at `:381` and the repository [66] at `:387`.
- Every reference is cited in the main text, and there are no gaps.
- The reference list (`:586–604`) matches, and the Manuscript PDF text shows the same numbers at lines 1006, 1092–1096, 1262, 1280 and 1656–1691.
- The Supplement uses [41], [44], [45] and [57–64] with the correct meanings. `HUMAN_REVIEW_SUMMARY.md:3` now says "[57–64]". The rebuttal's only numbered citation, [8, 9, 10, 11] at `:400`, was not affected by the renumbering.

**3. Cumulative family evidence: resolved and matches the frozen ledger.** I compared the new text with `clinical_roster.json`:

| Gene | Ledger | Text (S6.6 `:163`, R1-major-8 `:229`, summary `:8`, both PDFs) |
|---|---|---|
| PDIA6 | Later reports PMIDs 35856135 and 40974269; `reported_unrelated_families_all_phenotypes: 3`; `unrelated_target_families_lower_bound: 2` | Three families overall, conservative target lower bound two ✓ |
| VWA8 | Target PMIDs 37012052 and 40638000, lower bound 2; the 2021 paper (34660594) is marked non-target | Retinal PMIDs, lower bound two, kept separate from the 2021 developmental paper [58] ✓ |
| PLCG1 | Lower bound 3; "three de novo people and one inherited pedigree" | Lower bound three, kept separate from the later report's four families and the single earlier immune family ✓ |

- The counts are described as "retained screening classifications, not new human inclusion decisions".
- R1-major-8 now includes the sentence saying the concerns "do not by themselves constitute three exclusions".
- Eligibility is still "under review", the original denominators and outcomes are kept, and no blanket clinical approval is claimed anywhere.

## Optional corrections: all confirmed

- **Abstract:** says "three flagged cases" (`:21`, PDF line 39).
- **Main text:** says "either protocol-specified secondary analysis" (`:329`) and "in a bounded audit" (`:327`).
- **S6.2 (`:112`):** cross-references ATP11A's earliest-day uncertainty to S6.6.
- **S7 (`:173`):** keeps 343, 345 and 354 as historical stages, then gives the current 362 passed with 17 warnings. This matches the rebuttal (`:278`).
- **S8 (`:185`):** names the four RNU genes as IEA-only contributors to mRNA metabolic process. `category_summary.tsv:37` confirms this: RNU4-2, RNU6-2, RNU6-8 and RNU6-9 are IEA-only, and SCNM1 is the one non-IEA contributor.
- **GO `REPORT.md:13`:** separates the Fisher/BH arithmetic check from the same-code mapping/closure replay. `verification.json:27–28` records `analysis_associations_cache_sha256` and the scope.
- **Source replay:** `replay_verification.json` lists exactly eight TSVs plus `summary.json`, i.e. nine files.
- **Additional file 13:** its entries list includes `tests/test_revision_go.py` (`:879`).
- **Page index:** 89 rows. Section starts in the PDF texts match it: temporal evaluation p.24, biological scope p.26–27, Limitations p.29, Conclusions p.32, Figure 5 p.40. In the Supplement, S6 is p.5–11, S6.6 p.10–11, S7 p.11 and S8 p.11–13. The Manuscript is 50 pages and the Supplement 13.

## Remaining polish (none of it blocks author review)

1. **Cover letter PDF text:** extraction shows `major-revision-author-review-202 61019` with a stray space. The old 7 October version showed the same gap, so it is most likely an artifact of the inline-code font. Check page 1 visually; if a reader could copy the tag with the gap, set it as plain text.
2. **Rebuttal date paragraph (`rebuttal.md:242`):** it says "the reviewed sources supported this temporal classification" but doesn't say "bounded" or mention the four earliest-day uncertainties. Matching S6.6's wording would make them consistent.
3. **Terminology:** the main text and S8 say "secondary analyses", while `rebuttal.md:238`, `REPORT.md:7` and the `enrichment.tsv` labels say "sensitivity". This is harmless, but could be harmonized.
4. **S6.5 (`:157`):** "passed 354 tests" could add "at that stage". S7 already makes this clear.
5. **README author checklist:** items 1–3 don't include "verify the new tag resolves before upload". This is optional because you're tracking it separately.
6. **Figure 9B:** the y-axis label "Value" is unchanged, as previously noted.

## What I could not verify

I used only Read, Glob and Grep, so I computed no hashes. That means I did not independently confirm:
- that the DOCX, PDF and ZIP bytes match the current sources;
- that the `HUMAN_REVIEW_SUMMARY.md` inside Additional file 12 (3,681 bytes, listed in its entries file) is the current version;
- the association-cache hash value itself.

For those, and for the 21 protected-baseline, 45 old-artifact, 23 reviewer-quote and 25 response-subject checks, I am relying on your hash verification. I also did not rely on `opus_followup_raw.json`.

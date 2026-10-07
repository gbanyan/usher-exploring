# Temporal cohort author-review workbook

`Temporal_Case_Author_Review.xlsx` is an editable reading/verification companion for the 45 principal gene–disease records in `revision/major_revision_20261006/phase5_claude_review/principal_case_human_verification.tsv`.

- **Review:** one row per gene, with native filters, frozen headings/gene keys, eligibility and date dropdowns, reviewer identity/date, a verified association date, source-location notes and case-specific inheritance/genotype evidence. Yellow cells are author inputs. Click a gene to open its evidence card.
- **Evidence:** 45 cards containing the original AI-screened summaries, dates/intervals, domains, family counts, functional and replication evidence, reference keys and clickable PubMed links. The generic AI inheritance summary is not case-specific evidence. Return links lead to the corresponding Review row.
- **Original TSV:** an exact text-value snapshot of all 45 records and 21 source columns. Enter author decisions in Review, keeping this snapshot as the original source.

Eligibility choices are `PENDING`, `INCLUDE`, `EXCLUDE`, `UNCERTAIN`. Date choices are `PENDING`, `CONFIRMED`, `REVISED`, `UNCERTAIN`. These workflow labels do not change the prespecified scientific eligibility rubric. `UNCERTAIN` remains unresolved. A review requires the source checks and supporting notes, not merely selecting a dropdown. Record a changed date in Verified association date, and preserve intervals/uncertainties in the notes when an exact date cannot be established.

The pending counters count only decisions marked PENDING; they do not certify complete human verification. All 45 records remain pending in the delivered workbook. The added Verified association date column starts blank.

The workbook does not automatically write back to the TSV or change the frozen analyses. Preserve the edited workbook when returning author decisions; reconcile by gene key, document amendments and rerun affected outcomes if eligibility or dates change. This companion is separate from the fixed author-review submission release and its checksummed archives.

## Verification (macOS, 7 October 2026)

Authored with the bundled `@oai/artifact-tool`; native OOXML hyperlinks were added after export because its HYPERLINK formula preview was unsupported. All three sheets were visually inspected. Independent XML reads verified all 45 × 21 original TSV cell values, all review gene keys, two dropdowns, frozen panes, 152 native hyperlinks and ZIP CRC. LibreOffice opened/re-exported a disposable copy, retaining links and dropdowns. An eligibility-only edit recalculated the two pending counts to 44/45, leaving date review pending. Excel itself was not used for the native application check.

Task-owned builders and previews are in ignored `data/cache/temporal-human-review-20261007/`; validation used `node .../build.mjs`, `python3 .../finish.py`, and `/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to xlsx` with a task-specific profile/output directory. No environment dependencies, scientific scores, clinical classifications or original TSV values were changed.

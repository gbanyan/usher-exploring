# Temporal author-review workbook with full field definitions

Use `Temporal_Case_Author_Review_Defined_20261008.xlsx` for future author review. It is a separately saved revision of the 7 October workbook, which was open in Excel and has been preserved.

The workbook opens on **Definitions**. This sheet explains all 11 Review columns and 21 raw TSV columns, all decision choices, the five frozen eligibility requirements, novelty categories, date uncertainty, and a hypothetical preprint/journal/replication example. Full Review headings now distinguish the date of the human review from the human-verified first public report proposing the target-disease association. The evidence-card labels also identify provisional AI screening explicitly. Review retains its existing row positions and includes a link back to Definitions.

No source values, clinical classifications or scores were changed. All 45 rows remain PENDING for both eligibility and date. Source timing is first proposed human target association after 2020-12-31, with the stronger qualifying evidence accumulated by 2026-10-06. The first proposed date is distinct from the first strong-evidence date and the date the author does this review. Exact-date uncertainty should be preserved as an interval in notes. The frozen protocol is linked in Definitions.

## Preservation and verification

The existing XLSX was imported with the bundled `@oai/artifact-tool` and revised directly. Independent XML comparisons verified all original 45 × 21 TSV values, all existing Review row values and formulas, every evidence-card value, 152 original links, dropdowns, conditional-format feature presence and frozen panes. Native table headers were synchronized with the full visible headings. One new Definitions navigation link was added. An imported pre-edit preview and the changed headings, evidence labels and Definitions sections were visually inspected; the Original TSV view is unchanged.

LibreOffice on this Mac opened and re-exported a disposable copy successfully, retaining 46 Review links, two dropdowns and Definitions as the opening sheet. Excel itself was not used for the application check. The source workbook's Excel lock file was left untouched. The workbook does not write back to the TSV or amend frozen analyses automatically.

Task-owned builders/previews and verification output are in ignored `data/cache/temporal-human-review-20261008/`. Commands: `node .../edit.mjs`, `python3 .../verify.py`, and `/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to xlsx` with a task-specific user profile and output directory. No dependencies were installed. This companion is separate from the checksummed journal-submission package.

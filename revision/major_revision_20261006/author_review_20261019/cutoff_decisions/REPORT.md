# Author-approved cutoff-window decisions — 19 October 2026

The author instructed that temporal eligibility should depend on a clearly supported first-target publicity interval wholly after 2020, without requiring an exact earliest public day. The frozen protocol already permits wholly post-cutoff intervals. This is a post-outcome clarification of the worksheet's decision field and precision requirement, not a new cutoff, changed clinical rubric, or an amendment to frozen results.

The new working copy is `outputs/temporal-author-cutoff-decisions-20261019/Temporal_Case_Author_Decisions_Cutoff_20261019.xlsx`. It derives from the professor's preserved V2 attachment; neither returned original is overwritten.

**Current-symbol display update:** at the author's request, Review A22, its evidence-card heading A216 and the Review A22 hyperlink display now use **CLXN (formerly EFCAB1)**. Definitions D16 records the mapping and [HGNC source](https://rest.genenames.org/fetch/hgnc_id/25678). HGNC:25678 remains the same gene; HGNC records the symbol change on 29 November 2021. The Original TSV, professor's original files and frozen ledger symbol retain EFCAB1; the working ledger adds a separate display symbol. Relative to the preceding working copy (SHA-256 `6a18163e5c2fda783951ad317f1a63abfdf9389d1c5a06ea5eef94fbdc124727`), exactly three cell values change: Review A22, Evidence A216 and Definitions D16. Timing, eligibility, genotype notes and dates are unchanged.

## Working fields

- **Review C:** final principal-cohort eligibility, still PENDING for all 45 genes. Target phenotype, at least two unrelated target-affected families, consistent inheritance, functional support or independent human replication, and the clinical evidence acquisition boundary of 6 October 2026 remain unchanged.
- **Review D:** cutoff-window timing, replacing exact agreement with the AI-listed date. POST_CUTOFF means the supported first proposed public human TARGET-association interval is wholly after 31 December 2020. PRE_OR_AT_CUTOFF means an established first target report is on or before that cutoff. UNCERTAIN means the interval crosses the cutoff or its side remains unresolved. PENDING means not assessed. Exact-day uncertainty alone is insufficient to select UNCERTAIN when the supported interval is wholly post-cutoff.
- **Review G:** professor's returned date value/text, preserved and explicitly labelled as such. It is not automatically adopted as the earliest public date; some entries describe acceptance, issue or later versions.
- **Review H:** original source notes preserved as a prefix, followed by the retained first-target publicity interval, located public event and supporting source URL. E/F still identify the professor's actual source review, not a new professor approval of the changed coding.

All 45 working timing decisions are POST_CUTOFF, based on the existing retained intervals and completed date/version audit. Exact earliest-day uncertainty remains visible for ATP11A, CREB3, MRPL49 and TMEM72. These bounds retain the ascertainment and bibliography audit's limitations: a later public article alone does not prove absence of an earlier target association, and the audit is not an exhaustive search proving universal novelty. Prior non-target disease reports remain separate from first-target timing.

The original exact-date decisions remain preserved in the V2 source workbook and previous intake records. No clinical INCLUDE decision is inferred from the timing update. The author has approved the cutoff-window criterion; no new individual professor sign-off is claimed. No frozen TSV, score, ranking, recovery result, manuscript, Supplement text or reviewer response has been changed. GO integration remains paused.

## Verification and reproduction

Artifact Tool authors all changed worksheet values and affected layout, renders the changed views and checks formula recalculation. A temporary timing change to PENDING increments its summary from zero to one while clinical PENDING remains 45; UNCERTAIN does not set clinical inclusion. Temporary edits are restored. No formula errors were found by the Artifact Tool scan.

The serializer retained threaded comments but normalized view settings and did not synchronize changed native table-column names. The preservation step therefore transfers only Artifact Tool's authorized cell/layout/validation edits into the original package, aligns the three affected table headers and the renamed gene's hyperlink display, and retains all other package parts byte-for-byte. Exactly four XML parts differ from the professor's V2 source: Review, Evidence, Definitions and the Review table. Original TSV and all other package parts are unchanged. All three original threaded comments, hyperlink destinations, freeze panes, selections, original dates, genotype notes and reviewer fields remain intact. All 21 protected baseline input hashes match. Native Excel/LibreOffice recalculation was not performed.

Use the bundled Artifact Tool node modules with `scripts/update_author_cutoff_workbook.mjs`; `--preview` renders the original before editing. Then run:

```sh
rtk proxy node data/cache/author-cutoff-decisions-20261019/node-build/edit.mjs
rtk proxy data/cache/revision-writing-20261007/doc-env/bin/python scripts/verify_author_cutoff_workbook.py --preserve-source-package
rtk proxy node data/cache/author-cutoff-decisions-20261019/node-build/edit.mjs --preview-final
```

`timing_ledger.json`, `cell_changes.json` and `verification.json` record the actual decisions, all changed cell values, output hash and checks. The preservation/verification command without its flag verifies an existing final file without rewriting it.

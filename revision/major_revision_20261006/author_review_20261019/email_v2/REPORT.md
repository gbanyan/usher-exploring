# Professor V2 attachment intake — 19 October 2026

Retrieved with Himalaya from the professor's 22:39:53 +08:00 message. The email contains one XLSX attachment and no accompanying text instructions. The attachment is preserved byte-for-byte in the ignored local cache and copied to `outputs/temporal-author-return-v2-20261019/Temporal_Case_Author_Review_Defined_20261019_V2.xlsx`. See `intake_manifest.json` for message provenance, file size and SHA-256; `cell_changes.json` contains all before/after values. The original returned workbook remains unchanged.

Ten cell values differ from the earlier returned workbook: seven substantive changes across six genes, and three whitespace-only changes. All changes occur in the Review sheet's source-note or phenotype/genotype fields.

| Gene | Cell | Returned V2 change |
| --- | --- | --- |
| AP5B1 | H9, I9 | Removes the author/year/PMID line from the source-location note, retaining figure/table locations. Adds three pathogenic variants and two affected individuals from two independent families; retains AR, removing the earlier explicit homozygous/compound-heterozygous summary. |
| ATP11A | I10 | Adds two pathogenic variants and at least 37 affected individuals from four independent families; retains AD hearing-loss annotation. |
| BRWD1 | I11 | Changes inheritance from AD to AR; adds four pathogenic variants, three affected individuals from three unrelated families, and the qualifier “likely primary ciliary dyskinesia.” This resolves the inheritance mismatch in the earlier returned note; it is not a new clinical eligibility decision. |
| C19orf44 | I12 | Specifies late-onset retinal dystrophy with patchy perifoveal chorioretinal atrophy. |
| CTNND1 | I19 | Adds the catenin-family scaffolding-protein description. |
| VWA8 | I52 | Changes the zebrafish model note from “Tg” to “MO.” |

Whitespace-only changes affect CREB3 I17, INTS11 I27 and RNU4-2 H38. These are not new source conclusions.

All 45 stable gene identifiers and their order are unchanged. Eligibility remains PENDING for all 45 cases. Date-status counts remain 10 CONFIRMED, six REVISED and 29 PENDING; all author association-date fields are unchanged. Formula text, threaded comments and the Original TSV snapshot are unchanged. The Evidence and Definitions sheet values are unchanged.

This intake records the professor's edits without independently re-adjudicating each revised statement. No frozen cohort, score, recovery result, manuscript, supplement text or rebuttal has been changed. GO manuscript integration remains paused pending discussion of its role in the revision.

Reproduce the comparison locally with `rtk proxy data/cache/revision-writing-20261007/doc-env/bin/python scripts/reconcile_author_review_v2.py`. It checks both original hashes, ZIP integrity, sheet names, all cell values/formula text and threaded comments. This is a content comparison, not native Excel rendering or a formatting audit.

# Author-return intake and pending confirmations — 19 October 2026

The two newly downloaded files have been preserved and reconciled. The author has provided a substantive literature-review record for all 45 genes, but the workbook does **not** contain final inclusion decisions: all 45 eligibility cells remain PENDING. The user confirmed there was no separate instruction explaining those cells and requested a list of pending confirmations first. No frozen clinical label, score, cohort denominator, outcome, manuscript or submission artifact has been changed during this intake.

Use the new editable companion, `outputs/temporal-author-reconciliation-20261019/Temporal_Author_Confirmations_20261019.xlsx`. It contains one specific confirmation row for each gene, the original returned observations, and a plain-language Guide. The original returned file and its native comments remain intact. Source checks and date candidates in the companion are AI-assisted reconciliation suggestions, not author-approved clinical decisions.

## What was received

Only `Temporal_Case_Author_Review_Defined_20261019.xlsx` and `Refs.zip` were used from iCloud Drive Downloads. Other downloaded documents were not opened or incorporated. Byte-identical originals are in ignored `data/cache/author-review-20261019/originals/`; their SHA-256 hashes and sizes are in `intake_manifest.json`.

- 45 matching stable gene keys. The Original TSV snapshot is unchanged.
- 45 reviewer-name, review-date and substantive genotype/source-note entries, dated 13–19 October, attributed in the file to YHC.
- Eligibility: 45 PENDING. Date decisions: 10 CONFIRMED, 6 REVISED and 29 PENDING.
- 37 numeric exact-date entries and eight free-text/multiple-date entries. Of the 37 numeric dates, 21 differ from the original displayed AI date. These are discrepancies to interpret, not 21 demonstrated scientific errors or cohort changes.
- Three native comment threads: questions about “principal temporal test cohort” and “source location”, and a request to use CLXN for EFCAB1. They are transcribed in `reviewer_comments.json` and the companion Guide.
- 46 attached PDFs, 43 distinct PMID labels, 44 distinct byte hashes and 768 PDF pages across copies. Four gene-labelled RNU files concern the same article. The archive includes 49 PDF highlight annotations; positions/types are retained in `reference_manifest.json`.
- Sixteen gene-reference nominations from the frozen clinical roster are not attached in this ZIP. This describes attachment coverage, not absence of the underlying disease evidence. They are identified per gene in `confirmation_items.json`.

## Questions that need particular attention

| Gene(s) | Finding and requested confirmation |
|---|---|
| BRWD1 | Returned genotype note says AD; the supplied PMID 33389130 p.1 explicitly describes biallelic, recessive disease. Confirm AR and include the respiratory PCD/PCD-like evidence when judging target scope. |
| ATP11A | The paper describes one Newfoundland and two Israeli variant-positive families; do not automatically count the older DFNA33 linkage family as another ATP11A-confirmed family. Confirm the earlier preprint separately from the 2022 journal article. |
| AP5B1 | Returned status says CONFIRMED, but the entered date is 2025-04-03 rather than 2025-03-12. The supplied PDF p.18 supports the earlier publication date. Also verify the independent replication/functional route, not normal RPE localization alone. |
| CRLS1, USP48, PDIA6 | Separate acceptance from public availability. CRLS1 p.1 gives advance access 2022-02-11; USP48 p.1 gives 2021-05-31. The returned PDIA6 date is acceptance and does not itself establish public release. |
| FSD1L | The attachment is the neurodevelopmental companion, PMID 41720098. The frozen retinal evidence relies on 41720099, which is not attached. Confirm target-specific families, not the total neurological cohort. The attached publication history gives 2026-02-19, before its March issue. |
| INTS11, LIG3, SPATA5L1, RFC4 | Check relevant sensory families rather than automatically using every multisystem/neurological family. INTS11 in particular relies on evidence accumulated across reports. |
| PDIA6, C19orf44, SLC66A1, AP5B1 | Confirm the nominated later target-family replication/functional route. Do not include or exclude from the first attached paper alone. |
| VWA8 | The supplied 2021 paper concerns a developmental syndrome in one family. The frozen retinal cohort instead cites 2023/2025 reports, not attached. The prior non-target disease date must not automatically replace the first target-association date. |
| STX3, PLCG1 | Keep earlier intestinal/immune disease separate from the later retinal/hearing target association. Prior non-target disease can support category B rather than automatically excluding the gene. |
| CREB3, MRPL49, TMEM72 | Earlier-publicity intervals were frozen explicitly. Old worksheet displays that look like precise days must not erase those intervals or substitute the later journal date without adjudicating the earlier source. |
| GPATCH11, ATP11A, PKHD1L1, PLCG1, RSG1, four RNU genes | Earlier preprint/public-version candidates in the frozen screening need source-specific confirmation. A later journal PDF date does not refute an earlier public version. Those frozen nominations are not newly certified here. |
| SAXO6, TP73, SCNM1, RFC4, LIG3 | Supplied publication-history entries precede the returned issue dates. Candidate dates and PDF locations are given in the companion. |

Two bounded external primary-source checks were performed to resolve specific returned questions. [JCI's DNAJC30 version history](https://www.jci.org/articles/view/138267) distinguishes an in-press preview on 19 January 2021 from the March version. [ClinGen's gene record](https://search.clinicalgenome.org/kb/genes/HGNC%3A25678) confirms CLXN and previous symbol EFCAB1 share HGNC:25678. The companion displays CLXN (EFCAB1), while preserving the original symbol and identity in the source observations. These checks do not replace the pending author eligibility decisions.

## How to finish efficiently

For each row, answer the specific question, choose INCLUDE / EXCLUDE / UNCERTAIN, give the first-public **target** date or a bounded interval in the reply, and identify the confirming author/date. Existing literature notes do not need to be recopied. A PMID plus figure/table/page is a source location. The principal test cohort simply means the set of later-reported target disease genes against which the historical ranking is tested; it is not a new clinical diagnosis category.

The same frozen rubric applies: relevant human target phenotype, at least two unrelated target-affected families, consistent genotype/inheritance, functional support or independent new-family human replication, first proposed target report after 2020-12-31, and qualifying stronger evidence by 2026-10-06. Evidence maturation and prior non-target disease must be distinguished. Do not choose cases using score/rank. Unresolved eligibility or a first-public interval crossing the cutoff must not silently enter the primary novelty cohort.

When explicit author decisions arrive, record an amendment, preserve the original freeze/results, and rerun affected cohort summaries only if the decisions require it. The present return supports “author source notes received for 45 cases, final cohort/date reconciliation pending”, not “all 45 clinically adjudicated” or “independent validation completed”.

## Verification and limits

All original input hashes, all returned observations, the three comments and original snapshot were preserved. The serialized companion was independently checked for 45 source rows, stable keys, blank new replies, 45 PENDING decisions, typed dates, dropdown/frozen panes, ZIP CRC and zero serialized formula errors. Its pending-count formula was tested by changing one decision (44), then restoring it (45), while the association date stayed blank. All three sheets were visually inspected. All 21 protected baseline hashes, including the production database, still match. See `verification.json`.

This was selective PDF/source reconciliation with machine extraction of all PDFs, not a complete page-by-page clinical review of 768 pages. Preprint/conference candidates were not all freshly re-adjudicated. Current exact-date suggestions can therefore coexist with unresolved earliest-publicity questions. Native Excel/LibreOffice round-trip validation was not performed: the previously used LibreOffice executable is absent on this host. Artifact-tool rendering, recalculation and independent XML checks passed.

Execution was local macOS using the existing document Python environment (PyMuPDF) and bundled artifact-tool JS; no dependencies were installed and the old 354-test scientific suite was not rerun for this intake-only change. Reproduction: run `scripts/revision_author_review_intake.py --downloads <the iCloud Downloads directory>` with the document environment (this also regenerates `confirmation_items.json` using the curated `targeted_findings.json`), run a cache-side copy of `scripts/build_author_reconciliation.mjs` beside the bundled `node_modules` symlink, then run `python3 scripts/verify_author_reconciliation.py`.

The existing `data` symlink to `/Volumes/NV2/Project/usher/usher-exploring/data` predates this work and was left unchanged. Its pre-existing Git status and unrelated `uv.lock` are outside this checkpoint. Copyrighted PDFs, full extracted text, original returned binary/ZIP and renders remain local-only; manifests and derived reconciliation records are versioned. Neither Git nor this intake constitutes an off-machine backup of the raw caches.

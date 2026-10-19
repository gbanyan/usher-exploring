# Complete returned-reference date reconciliation — 19 October 2026

## Scope and result

All **46 PDFs**, covering **43 distinct PMID labels** and all **45 returned gene rows**, were reconciled. The audit inspected the extracted date histories of every supplied paper, rendered bounded date panels, acquired fresh PubMed XML and Europe PMC core metadata for all 43 PMIDs, checked seven preprint registry records, and consulted original publisher/version-history and conference/thesis sources for discrepancies. Three contextual article records outside the ZIP were checked to distinguish the VWA8 target domain and the FSD1L retinal companion. The raw references and original returned workbook remain byte-identical.

The readable deliverable is `outputs/temporal-reference-dates-20261019/Temporal_Reference_Date_Audit_20261019.xlsx`, with 45 gene comparisons, 43 article chronologies, 15 earlier-event records, and explicit field definitions. In **Gene dates**, read the explanation in column F. A blank proposed exact first-public date retains uncertainty; it does not mean that no public paper was found. The dated event in column G is separately documented and need not establish the first disclosure.

**No newly confirmed public target association before the 2020-12-31 cutoff was identified in this bounded date audit. No frozen cohort membership, scoring data, rank, recovery outcome, manuscript or submission artifact was changed.** This is not an exhaustive proof that no earlier report exists anywhere, or a fresh clinical adjudication of all families. All 45 human eligibility decisions remain PENDING exactly as returned. Publication-date reconciliation does not infer author inclusion approval.

## What explains the apparent discrepancies?

The primary categories partition the 45 gene rows:

| Main interpretation | Gene rows |
| --- | ---: |
| Same first-public article date | 16 |
| Issue versus first online | 7 |
| Preprint versus later journal | 8 |
| Public in-press preview versus final version | 2 |
| Multiple valid date/domain events | 4 |
| Acceptance versus public release | 2 |
| Acceptance and an unsupported issue entry | 1 |
| Earlier conference timing unresolved | 2 |
| Preprint and unresolved thesis timing | 1 |
| Different disease domain and publication versions | 1 |
| Prior non-target disease report | 1 |

These are bibliographic explanations, not counts of erroneous cases or independent clinical replications. A difference from the old displayed date is not itself a correction to the temporal cohort.

Important source-backed resolutions:

* **PDIA6:** the returned 2021-01-21 is acceptance. [Wiley explicitly gives first publication 2021-01-26](https://onlinelibrary.wiley.com/doi/10.1111/cge.13930), supporting the original date. Fresh PubMed Electronic metadata gives 2021-02-17. Both values are retained without inventing an unverified version-transition label.
* **USP48:** supplied PDF p.1 distinguishes acceptance 2021-05-25 from advance access 2021-05-31. The original date is supported by the article's own publication history, DOI [10.1093/hmg/ddab145](https://doi.org/10.1093/hmg/ddab145).
* **CRLS1:** supplied PDF p.1 and [primary publisher PDF](https://academic.oup.com/hmg/article-pdf/31/21/3597/46673942/ddac040.pdf) distinguish acceptance 2022-02-06 from advance access 2022-02-11. The returned 2022-10-08 publication entry is unsupported in the checked sources. [PubMed issue metadata](https://pubmed.ncbi.nlm.nih.gov/35147173/) gives 2022-10-28. First-public article timing is February 11.
* **DNAJC30 and CTNND1:** [JCI DNAJC30 version history](https://www.jci.org/articles/view/138267) records 2021-01-19 public in-press preview before 2021-03-15 electronic publication. [JCI Insight CTNND1 history](https://insight.jci.org/articles/view/158428) records 2022-06-14 public preview before 2022-07-22 electronic publication. The earlier original dates are supported; the final PDF alone omits the preview date.
* **PKHD1L1:** 2023-10-09 coincides with journal receipt, but independently is the public preprint's original posting date. [PMC's preprint version notice](https://pmc.ncbi.nlm.nih.gov/articles/PMC10593026/) identifies that original release, before the 2023-12-19 revision and 2024-03-09 journal article. A coincidence with receipt does not make the original date an extraction error. The DOI's October 8 is not the posting day.
* **PLCG1:** separate prior immune report PMID 37422272 (online 2023-07-06, November issue) from the sensory target report. [eLife's version history](https://elifesciences.org/reviewed-preprints/95887v1) and supplied PDF p.1 give original preprint 2024-01-09, reviewed preprint 2024-04-19, revised reviewed preprint 2025-07-23 and Version of Record 2025-08-27. The returned August 17 entry is unsupported. In the article chronology, the first public journal-hosted version is the reviewed preprint, not the later PubMed Electronic date.
* **VWA8:** the supplied 2021 paper is the earlier neurodevelopmental report. The target retinal paper [PMID 37012052](https://pubmed.ncbi.nlm.nih.gov/37012052/) was online 2023-04-03. Later retinal [PMID 40638000](https://pubmed.ncbi.nlm.nih.gov/40638000/) was online 2025-07-10. Neither target retinal PDF was supplied in this ZIP. Do not move first-target timing to 2021 merely because that is the first disease report of any kind.

## Earlier versions and exact-day uncertainty

Seven fresh preprint records match the previously nominated target titles and posting dates: ATP11A 2021-05-28, GPATCH11 2023-08-21, PKHD1L1 2023-10-09, PLCG1 2024-01-09, RSG1 2024-09-26, MRPL49 2024-10-11 and the shared RNU retinal study 2025-01-06. Primary posting/version statements were available for GPATCH11, PKHD1L1, PLCG1, MRPL49 and the RNU preprint. Research Square's ATP11A human hearing abstract was accessible but its dynamic posting-date text was not exposed; the exact date is independently present in the registry. The RSG1 primary preprint page was unavailable during this audit, so its exact posting day is explicitly attributed to the fresh registry record rather than falsely described as a new primary-page verification.

Four genes retain uncertainty in the exact **first** public day:

| Gene | Verified public event(s) and remaining distinction |
| --- | --- |
| TMEM72 | [Official ESHG programme](https://2021.eshg.org/programme/tuesday-august-31-virtual-conference/) schedules the target human report C23.1 for 2021-08-31. The [author institution's abstract record](https://researchinformation.umcutrecht.nl/en/publications/biallelic-tmem72-variants-in-patients-with-nephronophthisis-like-/) dates the published EJHG meeting abstract to April 2022, volume 30 supplement 1 p.78, supported by the primary abstract PDF DOI 10.1038/s41431-021-01025-2. The [full paper](https://karger.com/nef/article/150/4/210/940102/Biallelic-TMEM72-Variants-in-Patients-with-a) was online 2025-11-27 and appears in the April 2026 issue. Exact first programme/abstract release or actual presentation is not established. Retain frozen interval 2021-01-01 to 2022-04-30. The old 2021 date must not be labelled journal publication. |
| CREB3 | Journal online 2025-07-17 is explicit in the supplied publisher-page PDF. The [author-programme record](https://step-gtp.org/step-accomplishments/) names target presentations at IIRDC May 2024 and ISVER July 2024. Original dated abstracts were not located. Retain frozen interval 2024-05-01 to 2025-07-17. May 1 displayed in the old Excel was an interval bound, not an exact verified release. |
| MRPL49 | [Primary preprint](https://www.medrxiv.org/content/10.1101/2024.10.10.24315152v1) explicitly records posting 2024-10-11, before journal online 2025-03-04 and issue 2025-04-03. The [university thesis record](https://research.manchester.ac.uk/en/studentTheses/characterising-the-genetic-basis-of-perrault-syndrome/) gives an award year 2022, while the [primary thesis abstract p.17](https://pure.manchester.ac.uk/ws/portalfiles/portal/250504355/FULL_TEXT.PDF) says submission January 2023. Neither establishes public deposit. Keep the old broad 2022-01-01 to 2024-10-11 interval rather than treating an award/submission date as publication. |
| ATP11A | [Research Square human hearing preprint](https://www.researchsquare.com/article/rs-530835/v1) is registry-dated 2021-05-28. A [2021 university thesis lead](https://ediss.sub.uni-hamburg.de/handle/ediss/9309) has unresolved public timing relative to that preprint. Retain the original broad 2021 interval. The dated preprint and journal online 2022-03-12 are individually supported. |

This uncertainty does not newly cross the 2020 cutoff on the evidence found. Establishing the exact earliest disclosure is a narrower bibliographic question than whether the located target evidence is later than the cutoff. The original broad intervals are historical uncertainty records, not new proofs that every possible earlier source has been excluded.

## Source precision and preservation

* Dates are separately typed as received, revised, accepted, first public journal-hosted version, separately verified Version of Record, PubMed Electronic, issue, external preprint, correction, conference record or thesis milestone.
* Unknown dates stay blank. Month/year precision stays month/year text, without inventing a first day. DOI strings and PubMed indexing/PMC release dates are not substituted for publication.
* All archive filenames, PMID labels and SHA-256 hashes remain mapped in `article_dates.json`. Four RNU-labelled PDFs concern one PMID and one study, not independent replication.
* Raw PDF text, primary metadata payloads, contact sheets and the two original downloads are ignored local caches. Only bibliographic facts, audit code and the small workbook are tracked. Git is not a backup of those raw sources.
* The existing `data` symlink and unrelated working-tree changes are left alone.

## Reproduction and validation

Run locally from the repository root, prefixing shell commands with `rtk proxy`:

1. `python3 scripts/audit_reference_dates.py` acquires or reuses source metadata in the ignored cache.
2. `python3 scripts/build_reference_date_audit.py` joins all archive records and original human observations using the explicit source curation.
3. `data/cache/revision-writing-20261007/doc-env/bin/python scripts/preview_reference_date_panels.py` renders read-only date panels using PyMuPDF/Pillow.
4. Copy `scripts/build_reference_date_workbook.mjs` to `data/cache/author-review-20261019/date-audit/build.mjs` and run that copy with `node`, resolving the bundled artifact-tool dependency symlink in the parent cache. The workbook's count formulas were checked by changing/restoring an uncertainty category (4 to 3 to 4).
5. `python3 scripts/verify_reference_date_audit.py` verifies saved workbook cells, source counts, date precision, raw originals, source payload hashes and all 21 protected baseline hashes.

The workbook is visually reviewed in all four tabs and its serialized XML is checked. Native Excel/LibreOffice execution is not available on this host; no claim of native-application validation is made. See `verification.json` for the executed checks and output hash.

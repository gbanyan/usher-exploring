# Temporal extension: external archives and an executed historical case series

External archives contain usable historical evidence, and an archive-only reconstruction has now been executed. The earlier Phase 3 audit established **local cache insufficiency**, not absence of external archives. It should not have been treated as grounds to stop investigating temporal analysis.

This extension **does not establish successful temporal validation of UsherPipe**. Its restricted four-layer variant tests three manually ascertained later human-association cases. None enters the composite top 100. These mixed/negative results are retained; weights and cases were not changed after observing them.

## Frozen execution

[Protocol](protocol.md) was committed at `377eae3` before inspecting historical rankings (SHA256 `2bd02b4b467c82e34f1dc554085c81ffd5e91698b7eb3c6ebcd4cfe8e92e166a`). Cutoff: 2020-12-31. Population: 19,167 Approved protein-coding genes with unique Ensembl IDs in HGNC 2020-10-01; two ambiguous-identifier rows excluded. The restricted default score retains original layer weights and observed-weight normalization. Equal-weight and single-layer comparisons were also prespecified.

This is an illustrative retrospective case series, not an exhaustive post-cutoff cohort or prospective evaluation: the method itself was designed later. The question is later **human disease association**, not discovery of previously unknown ciliary function. No HIGH gate or priority tier was applied. No control-recovery threshold was optimized.

## External archive investigation

Seven JSON audit files record 51 bounded URL probes; every stored prefix hash was verified. HTTP 200 for an index does not establish complete-file availability. Actual files and formats were checked separately. Failed probes remain recorded. Wildcard Wayback probes matched unrelated host records and are **not** evidence of the requested report's availability.

| Source | Evidence found | Disposition |
| --- | --- | --- |
| HGNC | Complete official quarterly TSV, 2020-10-01 | Historical population/mappings |
| gnomAD | Complete v2.1.1 constraint file; 19,704 unique gene IDs | Historical LOEUF; no modern transcript selection |
| GO | Complete 2020-12-08 human GAF; 2015 archive also located | Positive unique GO IDs; partial annotation layer |
| HPA | Complete v20 normal-tissue and subcellular ZIPs; internal dates 2020-11-16 | Ordinal protein expression and localization |
| MGI | Exact official-report Wayback capture 2020-02-02, complete eight-column report (1,545,444 bytes); complete MP vocabulary capture 2019-01-29 (2,548,030 bytes) | Historical animal inputs exist, but complete production layer not reconstructed |
| ZFIN | Official 2020-12-31 phenotype and human-ortholog files; actual text prefixes checked | Partial feasibility; complete files not downloaded |
| IMPC | Official release 11.0 CSV; valid gzip/header; listing dates 2020-03 | Partial feasibility; prefix only |
| HCOP | Historical equivalent confidence-weighted input not obtained | No current confidence/ortholog choice imported |
| gene2pubmed | Exact NCBI file CDX capture 2020-06-29 found; slow transfer interrupted after 2 MiB | Complete-file validity not established; not used |
| Publication context | No cutoff-specific MeSH/context annotation snapshot | No current context PMID sets imported |
| UniProt/MyGene/pathways | UniProt archives available; equivalent API annotation scores/pathway inputs not reconstructed | GO-only annotation; other subcomponents NULL |
| CELLxGENE Census | Official release history begins with 2023-05-15 LTS; submitted snapshot is 2025-11-08 | Unavailable for this 2020 reconstruction |
| Embedded compendia | No dated per-gene provenance | Current cilia/centrosome membership not imported |
| GTEx/HPA RNA | GTEx v8 is historical; HPA v20 RNA ZIP is available, with TPM/pTPM/NX rather than the submitted measurement contract | Omitted from this prespecified restricted pilot; a scope choice, not archive unavailability |

The external investigation therefore changed the assessment to “several historical components can be reconstructed.” It did not establish that the submitted six-layer input contract can be reproduced before the cutoff. Historical gene–PMID links alone cannot date MeSH/context annotation; animal phenotype archives alone cannot supply historical HCOP support weights.

Official resources: [GO archives](https://geneontology.org/docs/go-archives/), [HPA v20 releases](https://v20.proteinatlas.org/about/releases), [HGNC archive](https://www.genenames.org/download/archive/), [ZFIN archive](https://zfin.org/downloads/archive), [IMPC releases](https://ftp.ebi.ac.uk/pub/databases/impc/all-data-releases/), [UniProt archives](https://ftp.ebi.ac.uk/pub/databases/uniprot/previous_releases/), [Census release history](https://chanzuckerberg.github.io/cellxgene-census/cellxgene_census_docsite_data_release_info.html). The gnomAD team's [2019 v2.1.1 announcement](https://groups.google.com/g/exac_data_announcements/c/Nkk4AV2LAjM) confirms that release and LOEUF predate the cutoff. Exact file URLs and complete-file hashes are in [download_manifest.json](download_manifest.json).

## Human-association date audit

| Gene | Report located | Decision |
| --- | --- | --- |
| CEP162 | [Human retinal association, 2023](https://pubmed.ncbi.nlm.nih.gov/36862503/) | Included; [ciliary transition-zone function was known in 2013](https://www.nature.com/articles/ncb2739) |
| CFAP20 | [Initial retinal candidate report, 2022-03-04](https://www.nature.com/articles/s41525-022-00286-0); [further report, 2022-11-03](https://pmc.ncbi.nlm.nih.gov/articles/PMC9633640/) | Included using initial candidate date; prior ciliary biology existed |
| LRRC45 | [Putative ciliopathy association, XML publication date 2021-10-29](https://pmc.ncbi.nlm.nih.gov/articles/PMC9340050/) | Included as putative, distinct from preexisting ciliary function and [later stronger evidence](https://pmc.ncbi.nlm.nih.gov/articles/PMC11790379/) |
| TMEM218 | [Primary paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8009330/) XML publication date 2020-11-21 | Excluded: 2021 issue/PubMed indexing does not reset date |
| ARSG, CEP78, TOGARAM1, IFT74 | Earlier human associations identified during screening | Excluded in the frozen protocol; later confirmations/additional syndromes do not reset dates |

These are the earliest relevant reports located in this audit, not proof of exhaustive first-report/preprint ascertainment. CEP162 is labelled by year because early online and indexed issue dates differ. The included cases are retinal/ciliopathy examples, **not three new Usher genes**. Existing Usher genes are descriptive pre-cutoff references only.

## Outcomes

19,033 genes have at least one scored historical layer; the other 134 retain NULL composites. Percentiles use minimum tie rank; positions break ties by Ensembl ID.

| Case | Default rank / 19,033 | Percentile | Observed layers | Equal-weight rank | Composite top 100 |
| --- | ---: | ---: | ---: | ---: | --- |
| CEP162 | 8,289 | 56.45 | 4 | 8,460 | No |
| CFAP20 | 11,004 | 42.19 | 3 | 11,327 | No |
| LRRC45 | 253 | 98.68 | 4 | 161 | No |

LRRC45 has historical HPA centrosome evidence (localization score 1.0). Its localization-only position is 60/12,595, percentile 99.40; 77 genes share this maximum score, so the exact position reflects identifier tie-breaking and is not composite recovery. CEP162 and CFAP20 have observed HPA localization scores of zero. CFAP20 has no accepted historical expression observation in the restricted panel. No modern compendium, photoreceptor expression or post-cutoff disease paper was added to improve outcomes.

| Layer | Observed | Positive | Observed zero | Missing |
| --- | ---: | ---: | ---: | ---: |
| gnomAD v2.1.1 | 18,096 | 18,095 | 1 | 1,071 |
| HPA protein expression | 10,894 | 7,144 | 3,750 | 8,273 |
| GO-only partial annotation | 18,502 | 18,502 | 0 | 665 |
| HPA localization | 12,595 | 686 | 11,909 | 6,572 |

GO parsing processed 607,460 rows, excluding 1,256 mapped NOT annotations and 1,783 ambiguous-accession rows, with 185 approved-symbol fallback rows and 10,587 unmapped rows. Repeated GO IDs count once per gene. HPA's one `Not representative` ordinal label maps to NULL, consistent with production parsing, not to observed zero.

GO contributes at most 0.5 to annotation: the unchanged within-layer function retains missing UniProt/pathway subcomponents as zero contribution. Whole absent layers instead use composite observed-weight normalization. These differences make the restricted score non-equivalent to production. Poor recovery here cannot demonstrate failure of the full pipeline; a high LRRC45 percentile cannot demonstrate full-pipeline temporal success.

All case/baseline/reference outcomes are in [case_rankings.tsv](results/case_rankings.tsv); all genome-wide components and prespecified ranks are retained in [historical_components.tsv](results/historical_components.tsv) and [historical_rankings.tsv](results/historical_rankings.tsv).

## Reviewer-facing conclusion

We investigated external archives and executed a prespecified restricted historical reconstruction. Its three illustrative post-cutoff human-association cases gave mixed results and no composite top-100 recovery. **This is not independent temporal validation of the full six-layer framework or calibrated HIGH tier.**

Candidate prioritization and hypothesis generation remain the appropriate claims. Neither the matched-comparator analysis nor this series validates discovery of novel Usher genes. Report this series as exploratory supplementary evidence with source omissions and negative results visible. Do not select additional cases, alter weights or import modern evidence to improve recovery.

## Verification and reproduction

Local execution: existing `.venv`, Python 3.13.1. Full suite: **343 passed**, 17 existing warnings. Protected database, submission, manuscript and configuration hashes remained unchanged. No production score table was queried for historical reconstruction or case selection.

```sh
rtk proxy .venv/bin/python scripts/revision_temporal_probe.py
rtk proxy .venv/bin/python scripts/revision_temporal_download.py
rtk proxy .venv/bin/python scripts/revision_temporal_analysis.py
rtk proxy .venv/bin/python scripts/revision_temporal_verify.py
rtk proxy .venv/bin/python -m pytest -q
```

The download audit was preserved with `--preserve-completed-only` after interruption of the slow optional gene2pubmed transfer. Completed-file metadata explicitly records completion time inferred from local file mtime and missing original response headers; precise network metadata was not fabricated. Use clean task-owned cache/output directories for reproduction; scripts refuse to overwrite previous result manifests. Follow-up exploratory URLs are recorded in JSON, not claimed to be an exhaustive archive search.

Raw archives stay in the ignored task-specific cache. The ~12.6 MB rankings TSV is intentional plain-text scientific output with useful diffs; no live database or binary archive is committed.

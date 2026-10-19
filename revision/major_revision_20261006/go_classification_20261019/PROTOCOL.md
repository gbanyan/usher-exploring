# GO classification and exploratory over-representation of the temporal cases

Recorded on 19 October 2026, before reading any new GO case-classification or enrichment outcome. This is a post-hoc extension of the completed temporal study, not an additional prespecified temporal endpoint or independent predictive validation. The professor proposed classifying the 45 genes to inform the biological discussion; the author requested completion of the classification workbook, overview figure and exploratory enrichment table.

## Fixed inputs and scope

* Keep the same 45 stable HGNC case keys in the returned author-review table. Their final human eligibility decisions remain PENDING. Do not change any clinical label or source date in this analysis.
* Forty-one cases occur in the frozen 19,167-gene historical protein-coding universe. Four RNU genes remain in the complete 45-gene classification and in the original temporal nonrecovery denominator; do not silently treat unmapped RNA genes as protein-coding genes.
* Use a contemporary human GO protein annotation source and separately inspect the human RNA annotation source. Pin the acquired files, ontology, HGNC mapping, release/header dates, source URLs, bytes and SHA-256 hashes. Prefer a public released GO ontology; document an official mirror or equivalent public-source fallback if the primary download endpoint is unavailable. A source-version change after outcomes requires an explicit amendment.
* Use the frozen historical HGNC stable identifiers/universe plus a contemporary HGNC mapping solely for descriptive annotation identity. Resolve exact accessions and stable identifiers first, then unambiguous approved/previous gene symbols. Reject ambiguous aliases; never assign one RNA paralogue's annotations to another merely because they share a family name or sequence. Preserve modern and frozen names separately.

## Annotation processing and classification

* Human taxon 9606 only. Exclude NOT-qualified annotations. Retain evidence codes and source references; report IEA separately. Exclude root-only/ND and obsolete annotations that cannot be unambiguously resolved. Deduplicate at the gene--GO-term level for counts, retaining the evidence records.
* Propagate only `is_a` and `part_of` ancestry. Do not propagate `has_part` or `regulates` as if they were subclass links. Resolve alternate IDs and unambiguous replacement IDs; report discarded or unresolved terms.
* Classify biological process (BP), molecular function (MF) and cellular component (CC) independently using the official generic GO slim membership in the pinned ontology. Exclude the three ontology roots. A gene can occur in multiple categories. Missing annotation is missing information, not evidence of absent function.
* Provide a 45-row gene summary, raw positive case annotations with evidence/source and mapping route, a gene--slim category matrix, and a category summary. Include the existing frozen 2020 GO-count field and five-/six-layer percentiles as historical descriptive context; contemporary functions must not be described as information available to the 2020 score.
* For each slim category, summarize gene membership and the median frozen five-/six-layer percentile among eligible coding cases. These are overlapping, small post-hoc groups, with no causal or confirmatory subgroup claim.

## Exploratory over-representation analysis

Primary query: the same 41 in-universe cases. Primary reference: all 19,167 frozen historical coding genes. For each ontology aspect, condition query and reference on genes with at least one usable non-root annotation in that aspect. Report eligible and annotated denominators, exclusions and mapping coverage explicitly. All query genes must belong to the reference. The annotation set and identity mapping must be identical for query and background.

For every propagated non-root GO term with at least five background genes and at least five background genes outside the term, perform a one-sided hypergeometric/Fisher over-representation test. Do not select tested terms by case overlap or by desired biological theme. Include zero-overlap terms in the multiple-testing family. Report counts, expected count, fold enrichment, raw P and Benjamini--Hochberg FDR across all tested terms in BP/MF/CC pooled for that analysis. Use FDR < 0.05 for the displayed significance flag. Retain the complete tested table, including nonsignificant results.

Run two clearly secondary sensitivity analyses using the same test/filter/FDR rules:

1. Exclude IEA annotations in both cases and the genome reference; recompute aspect-specific annotated denominators.
2. Restrict reference to the original catalog-sourced HGNC keys intersecting the historical coding universe, excluding appended reference controls. These other catalog genes are a source-ascertainment background, not established clinical negatives. Recompute aspect-specific annotated denominators. This addresses whether genome-wide enrichment mostly reflects the catalogs' sensory/ciliary focus.

FDR families are separate for the three named analyses; do not substitute the most favorable sensitivity result for the primary analysis. Enrichment describes functional composition conditional on this selected cohort and its annotations, not disease specificity or successful prospective gene discovery.

## Deliverables and interpretation

* One readable, filterable Excel workbook with per-gene classification, category membership, complete enrichment tables and source/method definitions.
* One standalone publication-quality overview figure in PNG and vector PDF/SVG. Three aspect panels show up to the 12 most frequent non-root generic-slim categories per aspect, sorted by gene count with GO-ID tie-breaking. Counts are unique genes in the full 45-case list; overlapping categories are explicit. State annotation coverage and RNA handling. No pie chart implying mutually exclusive categories.
* A source/report record and concise manuscript-ready Methods/Results/Discussion text. Biological themes are conclusions only after inspecting the actual results. Lack of significant enrichment or incomplete mappings must be reported.
* Preserve the original manuscripts, frozen cohort/results and production DuckDB. Record all protected source hashes before/after, validate joins/ontology ancestry/enrichment/FDR independently, check workbook values and render every sheet, and visually inspect the figure. Routine commit/push only task-owned files; leave the existing `data` symlink and unrelated `uv.lock` untouched.

## Execution location and dependencies

Local macOS is appropriate for this bounded file-based analysis; no persistent service or container is needed. Use existing `.venv` Python with SciPy/Matplotlib and the bundled artifact-tool for Excel. Raw downloadable sources and intermediate caches remain under ignored `data/cache/go-classification-20261019/`. Final small tables, figure and workbook go under the revision/output folders; inspect binary sizes and existing LFS rules before committing. Git does not back up ignored raw caches.

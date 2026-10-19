# Contemporary GO classification of the temporal cases

This post-hoc analysis describes the same 45 frozen cases. It neither changes temporal eligibility/ranks nor introduces modern annotations into historical scoring. Clinical disease mechanisms and GO categories are distinct.

All 45 cases map to at least one usable positive human GO annotation. BP/MF/CC coverage is 41/42/44. There are 2,164 source annotation records, 341 gene–generic-slim memberships and 85 nonempty categories among 140 active non-root generic-slim categories. Categories overlap. The four RNU genes have only electronic annotations in these sources; explicit HGNC RNAcentral/shared-sequence mapping is disclosed rather than presented as locus-specific functional experiments. EFCAB1 is displayed alongside current CLXN through the same stable HGNC key.

The primary query comprises 41 historical coding cases, with a 19,167-gene eligible reference. Aspect-specific annotated query/background counts are BP 37/16,831, MF 38/17,541 and CC 40/18,083. The primary test family contains 11,388 propagated terms, including zero-overlap hypotheses; no term passes pooled BH FDR < 0.05 (minimum q = 1). Excluding IEA gives 10,459 tests and minimum q = 0.3531193722460008; the catalog-background sensitivity gives 2,750 tests and minimum q = 1. Both have zero significant terms. The complete nonsignificant tables are retained.

Descriptive examples include cilium and mitochondrion (eight genes each), cilium organization (four), and mRNA metabolic process (five). These are not mutually exclusive disease classes. The displayed figure uses the 12 most frequent nonempty categories per aspect with GO-ID tie-breaking; it does not hand-select ciliary categories or display nominal P values as significance.

Sources are GOA protein/RNA GAF files generated 11 October 2026, ontology release 27 September 2026 and HGNC downloaded 19 October 2026. QuickGO supplies the version-matched is_a/part_of ancestry, restricted within each original aspect. The separately pinned official editor snapshot supplies generic-slim membership and identifier resolution. Four source files, 353 API responses, the ontology cache, original freeze and two pre-outcome implementation amendments are hashed. The amendments record aborted assertions before outcomes and are not post-outcome tuning.

`verification.json` independently reproduces all 24,597 test counts/P values/BH values using Fisher's exact test and SciPy BH, verifies every frozen co-primary case-percentile join and all 21 protected baseline hashes, and checks the delivered workbook's complete enrichment rows. Eight GO implementation tests pass. Ten rendered workbook views covering all seven sheets and the complete standalone figure were inspected. These checks establish numerical/source consistency, not independent clinical adjudication or predictive validity.

Reproduction in the existing analysis environment:

```bash
.venv/bin/python scripts/revision_go_analysis.py
.venv/bin/python scripts/plot_revision_go.py
.venv/bin/python scripts/verify_revision_go.py
.venv/bin/python -m pytest tests/test_revision_go.py
```

Raw GAF/ontology/HTTP caches remain local under `data/cache/go-classification-20261019/`; they are not backed up by Git. The workbook builder uses the bundled `@oai/artifact-tool`; the source and exported TSVs are retained. The complete author clinical-review form is not part of this GO attachment. The workbook's PENDING field preserves its returned working status and is not a new inclusion decision.

# Independent Astra high follow-up: Phase4

The existing `astra_independent_review` agent (gpt-6-astra, high) reviewed revised main/supplementary text read-only against frozen outcomes, then checked the rebuttal and replay guide. This was a continuation of the user-requested independent review, not an independent biological validation study.

Initial findings corrected before completion:

1. Animal score uses a combined sensory-count log multiplier after species phenotype-presence/confidence weighting, not per-species separately normalized counts.
2. HPA reliability factor takes precedence even when proximity comes from the curated-list fallback; compendium-only evidence uses 0.5.
3. Both main and abstract Conclusions must separate Usher/SYSCILIA and retain HIGH/novel-validation limitations.
4. Abstract comparator names should indicate matching to controls, not call them Usher-associated genes.
5. Revision data links must identify the revision rather than only the original August commit; final immutable release references remain packaging work.

Final follow-up found no new major numerical/method issue. Phase4 pair sensitivities, historical completeness/tissue coverage and temporal caveats matched the artifacts. Minor 23→28 TSV count and Additional8/9 versus checksum10 references were corrected. The 343 existing tests and two new tests are distinguished; final total is 345 passed with 17 existing warnings. The root additionally regenerated both main control tables from frozen output values, including separate SYSCILIA retention in optional strategies.

The reviewer judged no further experiment necessary for the present conservative claims. This does not establish independent novel-gene prediction, full temporal validation or clinical HIGH specificity. Final journal artifacts, delivered-file hashes and release/DOI disposition remain Phase5.

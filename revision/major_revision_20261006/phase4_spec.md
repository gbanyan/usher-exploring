# Phase 4: post-review diagnostics and revised claims

This specification follows the independent Astra review at `2160a9d`. The additional diagnostics are post-outcome sensitivities prompted by that review, not retrospectively prespecified validation. Keep the original production score, retained IDs, six weights, HIGH gate, comparator roster and matching caliper fixed. Preserve Phase 2/3 and temporal primary results.

## Additional diagnostics

On all 111 frozen Phase 3 pairs, report group-specific layer-completeness/source-observation balance; default concordance; pair-specific common-observed-layer weighted means; all six leave-one-layer-out pair concordances; joint animal/literature omission. Ties contribute 0.5; unranked pairs remain missing. Give pair and control-averaged summaries, retaining all original pairs without rematching. Common-layer comparisons are not genome-wide ranks or AUCs. Report the same complete output family regardless of direction.

For the original historical score, report top25/50/100 completeness and per-layer observation patterns, accepted HPA tissue coverage, and tissue-level provenance for CEP162, CFAP20 and LRRC45. Preserve missing values and ordinal zeros, do not apply quantitative Tau to ordinal measurements, and do not change annotation normalization or ranking population. This bounded reconstruction remains an archive/scoring diagnostic, not full temporal validation. GTEx augmentation and new independent-positive studies are optional further work, not adopted from favorable outcomes.

## Manuscript and response

Define the primary target as genome-wide cilia/sensory-aware hypotheses for follow-up in the Usher context. Separate nine Usher and 28 SYSCILIA controls throughout. Correct the implemented source-level gate, HPA modality/reliability and curated-list semantics, within-layer formulas and missing-subcomponent policies. Present raw-score specificity failure, exact control tiers/failures, stronger animal-only baseline, top-K sensitivity, completeness, correlations, matched-comparator caveats and proxy dependence. Define HIGH as a heuristically calibrated priority tier. Do not claim independently validated novel disease-gene discovery. Retain useful biological rationale and add the requested supporting references; avoid gratuitous shortening.

Create an English point-by-point response covering the original DOCX 10 major/7 minor comments and six pasted comments. Use source A/B labels until journal reviewer numbering is confirmed. Link each response to revised sections and concrete artifacts. Distinguish completed analyses, corrected descriptions, limitations and optional future work.

## Replay and environment

Save immutable copies of submission prose for baseline checks, so future manuscript edits do not invalidate numerical replay. Expose explicit database/cache/input/output options, preserve existing outcomes, and replay the already-frozen roster without requiring a new Git commit. Export a distributable, schema-checked derived-input bundle for numerical replay; describe its limits versus full raw-source regeneration. Provide snapshot URLs/hashes/dates with unknown original retrieval dates left unknown, plus an exact tested dependency environment. Preserve unrelated untracked `uv.lock`; do not adopt it without checking authorship and compatibility. Validate replay in clean task-owned directories, compare numerical tables to frozen outputs, and run relevant tests.

Final journal DOCX/PDF rendering, new Additional-file assembly/conversion, checksum verification of delivered files, and release/DOI disposition belong to Phase 5. Phase 4 must leave the content and replay workflow ready for that packaging.

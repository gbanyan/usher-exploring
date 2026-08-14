# Supplementary-analysis rebuild audit

**Run date:** 2026-08-14  
**Mode:** local-only; no supplementary-analysis command was permitted to fetch  
**Current scored state:** 20,081 unique labels from `data/pipeline.duckdb`

## Dependency order and outputs

1. `scripts/cochlear_expression.py --cache-only --cache-dir data/expression --scored-db data/pipeline.duckdb`
   - GSE135913 local inputs: GSM4037819 and GSM4037820 included; GSM4037821 excluded because marker margin was 0.09714783594601006 (<0.5).
   - Marker coverage: 8, 8, and 5; leave-one-marker-out stability: true, true, and not applicable.
   - Output restricted to current scored labels: 15,608 of 20,081 labels.
   - Outputs: `gse135913_hair_cell_expression.parquet`, `.tsv`, and `.json`.
2. `scripts/expression_shortlist.py --cache-only --db data/pipeline.duckdb`
   - Current HIGH tier: 62 genes; GSE coverage: 61/62; CellxGene hair-cell coverage: 0/62.
   - Q75 thresholds: photoreceptor 0.8252069354057312; fetal hair-cell 0.484961650905941; HPA retina unavailable (`None`).
   - Strategy sizes: photoreceptor 16; hair-cell 16; concordant 5; HPA-retina concordant 0; direct protein 23; expression OR protein 34; expression AND protein 5.
   - Outputs: `expression_shortlist_candidates.tsv`, `.summary.tsv`, and `.report.md`.
3. `scripts/weight_tuning.py --db data/pipeline.duckdb`
   - Completed once against the current local database; no relaunch was performed after duplicate buffered launches were terminated.
   - Exact captured metrics: 20,081 scored genes; 37 known controls; 13 housekeeping controls; 8,856 candidate weight vectors; default known-control median 92.8%; default housekeeping median 94.8%.
   - No unobserved terminal values are inferred in this audit artifact.
4. `scripts/weight_logreg.py --db data/pipeline.duckdb`
   - Completed exactly once; full captured output is `weight_logreg_report.txt`.
   - 37 positives, 70 matched negatives, 13 housekeeping sentinels; derived weights `[0, 0, 0, 0.032, 0.903, 0.065]`.
   - Default/logreg known median: 92.8%/98.7%; housekeeping median: 94.8%/75.1%; housekeeping HIGH: 2/0.
   - Held-out known median: 98.2%; default-vs-logreg rank Spearman rho: 0.646; sparse-layer shift +5.6, 4–5-layer shift −1.9, six-layer shift −0.3.

## Old-versus-new HIGH comparison

`high_shortlist_old_vs_new.md/.tsv` compares the pre-rebuild artifact at commit
`17a34653472792228c6e8740d28383b06731ed0a` with the current state. The old-side
IDs in that diagnostic are intentionally labelled comparison-only and are not
used by production outputs.

- Scored labels: 19,557 → 20,081
- Candidate rows: 18,303 → 18,387
- HIGH rows: 68 → 62
- HIGH overlap: 54; old HIGH retained: 54/68 (79.4%)
- Old-only HIGH: 14; new-only HIGH: 8
- Shared-candidate rank Spearman rho: 0.9881 across 17,944 candidates
- Retained-HIGH rank delta (new minus old): median absolute 4, range −19 to +28

## Provenance and stale-state checks

- GSE raw inputs were read only from `data/expression/`; the provenance JSON records their SHA-256 values and `source_mode: local_cache_only`.
- The cochlear aggregate and shortlist loader reject missing files, duplicate labels, and labels outside the current scored state.
- Weight analyses validate exactly 20,081 scored rows and reject IDs outside `gene_universe`.
- No manuscript text was synchronized or rewritten in this phase; stale manuscript counts remain intentionally deferred to the next lane.

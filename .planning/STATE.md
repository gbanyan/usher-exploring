# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-11)

**Core value:** Produce a high-confidence, multi-evidence-backed ranked list of under-studied cilia/Usher candidate genes that is fully traceable — every gene's inclusion is explainable by specific evidence, and every gap is documented.
**Current focus:** Phase 4 complete — ready for Phase 5

## Current Position

Phase: 5 of 6 (Output & CLI)
Plan: 3 of 3 in current phase (plans 05-01, 05-02, 05-03 complete)
Status: Phase 5 complete — 05-03 complete
Last activity: 2026-02-11 — Plan 05-03 executed and verified

Progress: [█████████░] 90.0% (18/20 plans complete across all phases)

## Performance Metrics

**Velocity:**
- Total plans completed: 18
- Average duration: 4.9 min
- Total execution time: 1.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 - Data Infrastructure | 4/4 | 14 min | 3.5 min/plan |
| 02 - Prototype Evidence Layer | 2/2 | 8 min | 4.0 min/plan |
| 03 - Core Evidence Layers | 6/6 | 52 min | 8.7 min/plan |
| 04 - Scoring Integration | 3/3 | 10 min | 3.3 min/plan |
| 05 - Output & CLI | 3/3 | 12 min | 4.0 min/plan |

**Recent Plan Details:**
| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 04 P01 | 4 min | 2 tasks | 4 files |
| Phase 04 P02 | 3 min | 2 tasks | 4 files |
| Phase 04 P03 | 3 min | 2 tasks | 4 files |
| Phase 05 P01 | 4 min | 2 tasks | 5 files |
| Phase 05 P02 | 5 min | 2 tasks | 6 files |
| Phase 05 P03 | 3 min | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Python over R/Bioconductor for rich data integration ecosystem
- Weighted rule-based scoring over ML for explainability
- Public data only for reproducibility
- Modular CLI scripts for flexibility during development
- Virtual environment required for dependency isolation (01-01: PEP 668 externally-managed Python)
- Auto-creation of directories on config load (01-01: data_dir, cache_dir field validators)
- [01-02]: Warn on gene count outside 19k-22k range but don't fail (allows for Ensembl version variations)
- [01-02]: HGNC success rate is primary validation gate (UniProt mapping tracked but not used for pass/fail)
- [01-02]: Take first UniProt accession when multiple exist (simplifies data model)
- [01-02]: Mock mygene in tests (avoids rate limits, ensures reproducibility)
- [01-03]: DuckDB over SQLite for DataFrame storage (native polars/pandas integration, better analytics)
- [01-03]: Provenance sidecar files alongside outputs (co-located metadata, bioinformatics standard pattern)
- [01-04]: Click for CLI framework (standard Python CLI library with excellent UX)
- [01-04]: Setup command uses checkpoint-restart pattern (gene universe fetch can take minutes)
- [01-04]: Mock mygene in integration tests (avoids external API dependency, reproducible)
- [02-01]: httpx over requests for streaming downloads (async-native, cleaner API)
- [02-01]: structlog for structured logging (JSON-formatted, context-aware)
- [02-01]: LOEUF normalization with inversion (lower LOEUF = more constrained = higher 0-1 score)
- [02-01]: Quality flags instead of filtering (preserve all genes with measured/incomplete_coverage/no_data categorization)
- [02-01]: NULL preservation pattern (unknown constraint != zero constraint, must not be conflated)
- [02-01]: Lazy polars evaluation (LazyFrame until final collect() for query optimization)
- [02-02]: load_to_duckdb uses CREATE OR REPLACE for idempotency (safe to re-run)
- [02-02]: CLI evidence command group for extensibility (future evidence sources follow same pattern)
- [02-02]: Checkpoint at table level (has_checkpoint checks DuckDB table existence)
- [02-02]: Integration tests with synthetic fixtures (no external downloads, fast, reproducible)
- [03-01]: Annotation tier thresholds: Well >= (20 GO AND 4 UniProt), Partial >= (5 GO OR 3 UniProt)
- [03-01]: Composite annotation score weighting: GO 50%, UniProt 30%, Pathway 20%
- [03-01]: NULL GO counts treated as zero for tier classification but preserved as NULL in data (conservative assumption)
- [03-03]: UniProt REST API with batching (100 accessions) over bulk download for flexibility
- [03-03]: InterPro API for supplemental domain annotations (10 req/sec rate limit)
- [03-03]: Keyword-based cilia motif detection over ML for explainability (IFT, BBSome, ciliary, etc.)
- [03-03]: Composite protein score weights: length 15%, domain 20%, coiled-coil 20%, TM 20%, cilia 15%, scaffold 10%
- [03-03]: List(Null) edge case handling for proteins with no domains (cast to List(String))
- [03-04]: Evidence type terminology standardized to computational (not predicted) for consistency with bioinformatics convention
- [03-04]: Proteomics absence stored as False (informative negative) vs HPA absence as NULL (unknown/not tested)
- [03-04]: Curated proteomics reference gene sets (CiliaCarta, Centrosome-DB) embedded as Python constants for simpler deployment
- [03-04]: Computational evidence (HPA Uncertain/Approved) downweighted to 0.6x vs experimental (Enhanced/Supported, proteomics) at 1.0x
- [Phase 03-05]: Ortholog confidence based on HCOP support count (HIGH: 8+, MEDIUM: 4-7, LOW: 1-3)
- [Phase 03-05]: NULL score for genes without orthologs (preserves NULL pattern)
- [03-02]: HPA bulk TSV download over per-gene API (efficient for 20K genes)
- [03-02]: GTEx retina/fallopian tube may be NULL (not in all versions)
- [03-02]: CellxGene optional dependency with --skip-cellxgene flag (large install)
- [03-02]: Tau specificity requires complete tissue data (any NULL -> NULL Tau)
- [03-02]: Expression score composite: 40% enrichment + 30% Tau + 30% target rank
- [03-02]: Inner ear data primarily from CellxGene scRNA-seq (not HPA/GTEx bulk)
- [03-06]: HTS hits prioritized over functional mentions in evidence tier hierarchy (direct > HTS > functional > incidental)
- [03-06]: Quality-weighted scoring uses log2 normalization to mitigate well-studied gene bias (prevents TP53-like dominance)
- [03-06]: Context weights cilia/sensory=2.0, cytoskeleton/polarity=1.0 for primary target prioritization
- [03-06]: Rate limiting via decorator pattern (3 req/sec default, 10 req/sec with NCBI API key)
- [04-01]: OMIM Usher genes (10) and SYSCILIA SCGS v2 core (28) as known gene positive controls
- [04-01]: NULL-preserving weighted average: weighted_sum / available_weight (only non-NULL layers contribute)
- [04-01]: Quality flags based on evidence_count (>=4 sufficient, >=2 moderate, >=1 sparse, 0 no_evidence)
- [04-01]: Per-layer contribution tracking (score * weight) for explainability
- [04-01]: ScoringWeights validation enforcing sum = 1.0 ± 1e-6 tolerance
- [04-02]: scipy MAD-based outlier detection (>3 MAD threshold) for robust anomaly detection
- [04-02]: Missing data thresholds: 50% warn, 80% error for graduated QC feedback
- [04-02]: PERCENT_RANK validation computed before known gene exclusion (validates scoring system)
- [04-02]: Top quartile validation criterion (median percentile >= 0.75 for known genes)
- [04-03]: Score command follows evidence_cmd.py pattern for consistency
- [04-03]: Separate --skip-qc and --skip-validation flags for flexible iteration
- [04-03]: Tests use tmp_path fixtures for isolated DuckDB instances
- [04-03]: Synthetic test data designed to ensure known genes rank highly (0.8-0.95 scores across all layers)
- [05-01]: Configurable tier thresholds (HIGH: score>=0.7 and evidence>=3, MEDIUM: score>=0.4 and evidence>=2, LOW: score>=0.2)
- [05-01]: EXCLUDED genes filtered out (below LOW threshold or NULL composite_score)
- [05-01]: Deterministic sorting (composite_score DESC, gene_id ASC) for reproducible output
- [05-01]: Dual-format TSV+Parquet with identical data for downstream tool compatibility
- [05-01]: YAML provenance sidecar includes statistics (tier counts) and column metadata
- [05-01]: Fixed deprecated pl.count() -> pl.len() usage for polars 0.20.5+ compatibility
- [05-02]: matplotlib Agg backend for headless/CLI safety (non-interactive visualization)
- [05-02]: 300 DPI for publication-quality plots
- [05-02]: Tier color scheme: GREEN/ORANGE/RED for HIGH/MEDIUM/LOW (consistent across all plots)
- [05-02]: Graceful degradation (individual plot failures don't block batch generation)
- [05-02]: Dual-format reproducibility reports (JSON machine-readable + Markdown human-readable)
- [05-02]: Optional validation metrics in reproducibility reports (report generates whether or not validation provided)
- [05-03]: Report command follows established CLI pattern (config load, store init, checkpoint, steps, summary, cleanup)
- [05-03]: Configurable tier thresholds via CLI flags (--high-threshold, --medium-threshold, --low-threshold, --min-evidence-high, --min-evidence-medium)
- [05-03]: Skip flags for flexible iteration (--skip-viz, --skip-report) allow faster output generation
- [05-03]: Graceful degradation for visualization and reproducibility report failures (warnings, not errors)

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-11 - Phase 5 execution
Stopped at: Plan 05-03 complete — CLI report command implemented with comprehensive CliRunner integration tests, Phase 5 complete
Resume file: .planning/phases/05-output-cli/05-03-SUMMARY.md

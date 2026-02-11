# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-11)

**Core value:** Produce a high-confidence, multi-evidence-backed ranked list of under-studied cilia/Usher candidate genes that is fully traceable — every gene's inclusion is explainable by specific evidence, and every gap is documented.
**Current focus:** Phase 2 complete — ready for Phase 3

## Current Position

Phase: 3 of 6 (Core Evidence Layers)
Plan: 3 of 6 in current phase (03-03 complete)
Status: In progress — 03-03 complete (protein features)
Last activity: 2026-02-11 — Completed 03-03-PLAN.md (Protein Features evidence layer)

Progress: [█████░░░░░] 45.0% (9/20 plans complete across all phases)

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: 5.2 min
- Total execution time: 0.78 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 - Data Infrastructure | 4/4 | 14 min | 3.5 min/plan |
| 02 - Prototype Evidence Layer | 2/2 | 8 min | 4.0 min/plan |
| 03 - Core Evidence Layers | 3/6 | 27 min | 9.0 min/plan |
| Phase 03 P03 | 11 min | 2 tasks | 7 files |
| Phase 03 P04 | 8 min | 2 tasks | 8 files |
| Phase 03 P05 | 10 min | 2 tasks | 8 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2026-02-11 - Plan execution
Stopped at: Completed 03-03-PLAN.md (Protein Features evidence layer)
Resume file: .planning/phases/03-core-evidence-layers/03-03-SUMMARY.md

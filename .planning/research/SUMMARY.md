# Project Research Summary

**Project:** Bioinformatics Cilia/Usher Gene Discovery Pipeline
**Domain:** Gene Candidate Discovery and Prioritization for Rare Disease / Ciliopathy Research
**Researched:** 2026-02-11
**Confidence:** MEDIUM-HIGH

## Executive Summary

This project requires a multi-evidence bioinformatics pipeline to prioritize under-studied gene candidates for ciliopathy and Usher syndrome research. The recommended approach is a **staged, modular Python pipeline** using independent evidence retrieval layers (annotation, expression, protein features, localization, genetic constraint, phenotypes) that feed into weighted scoring and tiered output generation. Python 3.12+ with Polars for data processing, DuckDB for intermediate storage, and Typer for CLI orchestration represents the modern bioinformatics stack optimized for ~20K gene analysis on local workstations.

The critical architectural pattern is **independent evidence layers with staged persistence**: each layer retrieves, normalizes, and caches data separately before a final integration step combines scores. This enables restartability, parallel execution, and modular testing—essential for pipelines with external API dependencies and long runtimes. Configuration-driven behavior with YAML configs and Pydantic validation ensures reproducibility and enables parameter tuning without code changes.

The dominant risks are **gene ID mapping inconsistencies** (causing silent data loss across databases) and **literature bias amplification** (over-prioritizing well-studied genes at the expense of novel candidates). Both require explicit mitigation: standardized Ensembl gene IDs throughout, mapping validation gates, and publication-independent scoring layers weighted heavily. Success depends on validation against positive controls (known Usher/cilia genes) and negative controls (non-cilia housekeeping genes) to prove the scoring system works before running at scale.

## Key Findings

### Recommended Stack

Python 3.12+ provides the best balance of library support and stability. **Polars** (1.38+) outperforms Pandas by 6-38x for genomic operations with better memory efficiency for 20K gene datasets. **DuckDB** enables out-of-core analytical queries on Parquet-cached intermediate results, solving the memory pressure problem when integrating 6 evidence layers. **Typer** offers modern, type-hint-based CLI design with auto-generated help, cleaner than argparse for modular pipeline scripts.

**Core technologies:**
- **Python 3.12**: Industry standard for bioinformatics with extensive ecosystem (Biopython, scanpy, gget)
- **Polars 1.38+**: DataFrame processing 6-38x faster than Pandas, native streaming for large datasets
- **DuckDB**: Columnar analytics database for intermediate storage; 10-100x faster than SQLite for aggregations, queries Parquet files without full import
- **Typer 0.21+**: CLI framework with type-hint-based interface, auto-generates help documentation
- **gget 0.30+**: Unified API for multi-source gene annotation (Ensembl, UniProt, NCBI) — primary data access layer
- **Pydantic 2.12+**: Type-safe configuration and data validation; 1.5-1.75x faster than v1, prevents config errors
- **structlog**: Structured JSON logging with correlation IDs to trace genes through pipeline
- **diskcache**: Persistent API response caching across reruns, critical for avoiding API rate limits
- **uv**: Rust-based package manager 10-100x faster than pip, replaces pip/pip-tools/poetry

**Avoid:**
- Pandas alone (too slow, memory-inefficient)
- Python 3.9 or older (missing library support)
- Workflow orchestrators (Snakemake/Nextflow) for initial local workstation pipeline (overkill; adds complexity without benefit)
- Poetry for new projects (slower than uv, less standard)

### Expected Features

**Must have (table stakes):**
- **Multi-evidence scoring**: 6 layers (annotation, expression, protein features, localization, constraint, phenotypes) with weighted integration — standard in modern gene prioritization
- **Reproducibility documentation**: Parameter logging, version tracking, seed control — required for publication
- **Data provenance tracking**: W3C PROV standard; track all transformations, source versions, timestamps
- **Known gene validation**: Benchmark against established ciliopathy genes (CiliaCarta, SYSCILIA, Usher genes) with recall metrics
- **Quality control checks**: Missing data detection, outlier identification, distribution checks
- **API-based data retrieval**: Automated queries to gnomAD, GTEx, HPA, UniProt with rate limiting, caching, retry logic
- **Batch processing**: Parallel execution across 20K genes with progress tracking and resume-from-checkpoint
- **Parameter configuration**: YAML config for weights, thresholds, data sources
- **Tiered output with rationale**: High/Medium/Low confidence tiers with evidence summaries per tier
- **Basic visualization**: Score distributions, rank plots, evidence contribution charts

**Should have (competitive differentiators):**
- **Explainable scoring**: SHAP-style per-gene evidence breakdown showing WHY genes rank high — critical for discovery vs. diagnosis
- **Systematic under-annotation bias handling**: Correct publication bias by downweighting literature-heavy features for under-studied candidates — novel research advantage
- **Sensitivity analysis**: Systematic parameter sweep with rank stability metrics to demonstrate robustness
- **Evidence conflict detection**: Flag genes with contradictory evidence patterns (e.g., high expression but low constraint)
- **Interactive HTML report**: Browsable results with sortable tables, linked evidence sources
- **Cross-species homology scoring**: Zebrafish/mouse phenotype evidence integration via ortholog mapping

**Defer (v2+):**
- **Automated literature scanning with LLM**: RAG-based PubMed evidence extraction — high complexity, cost, uncertainty
- **Incremental update capability**: Re-run with new data without full recomputation — overkill for one-time discovery
- **Multi-modal evidence weighting optimization**: Bayesian integration, cross-validation — requires larger training set
- **Cilia-specific knowledgebase integration**: CilioGenics, CiliaMiner — nice-to-have, primary layers sufficient initially

### Architecture Approach

Multi-evidence gene prioritization pipelines follow a **layered architecture** with independent data retrieval modules feeding normalization, scoring, and validation layers. The standard pattern is a **staged pipeline** where each evidence layer operates independently, writes intermediate results to disk (Parquet cache + DuckDB tables), then a final integration component performs SQL joins and weighted scoring.

**Major components:**
1. **CLI Orchestration Layer** (Typer) — Entry point with subcommands (run-layer, integrate, report), global config management, pipeline orchestration
2. **Data Retrieval Layer** (6 modules) — Independent retrievers for annotation, expression, protein features, localization, constraint, phenotypes; API clients with caching and retry logic
3. **Normalization/Transform Layer** — Per-layer parsers converting raw formats to standardized schemas; gene ID mapping to Ensembl; score normalization to 0-1 scale
4. **Data Storage Layer** — Raw cache (Parquet), intermediate results (DuckDB), final output (TSV/Parquet); enables restartability and out-of-core analytics
5. **Integration/Scoring Layer** — Multi-evidence scoring via SQL joins in DuckDB; weighted aggregation; known gene filtering; confidence tier assignment
6. **Reporting Layer** — Per-gene evidence summaries; provenance metadata generation; tiered candidate lists

**Key architectural patterns:**
- **Independent Evidence Layers**: No cross-layer dependencies; enables parallel execution and isolated testing
- **Staged Data Persistence**: Each stage writes to disk before proceeding; enables restart-from-checkpoint and debugging
- **Configuration-Driven Behavior**: YAML configs for weights/thresholds; code reads config, never hardcodes parameters
- **Provenance Tracking**: Every output includes metadata (pipeline version, data source versions, timestamps, config hash)

### Critical Pitfalls

1. **Gene ID Mapping Inconsistency Cascade** — Over 51% of Ensembl IDs can fail symbol conversion; 8% discordance between Swiss-Prot and Ensembl. One-to-many mappings break naive merges, causing silent data loss. **Avoid by:** Using Ensembl gene IDs as primary keys throughout; version-locking annotation builds; implementing mapping validation gates that report % successfully mapped; manually reviewing unmapped high-priority genes.

2. **Literature Bias Amplification in Weighted Scoring** — Well-studied genes dominate scores because GO annotations, pathway coverage, interaction networks, and PubMed mentions all correlate with research attention rather than biological relevance. Systematically deprioritizes novel candidates. **Avoid by:** Decoupling publication metrics from functional evidence; normalizing scores by baseline publication count; heavily weighting sequence-based features independent of literature; requiring evidence diversity across multiple layers; validating against under-studied positive controls.

3. **Missing Data Handled as "Negative Evidence"** — Genes lacking data in a layer (no GTEx expression, no IMPC phenotype) are treated as "low score" rather than "unknown," systematically penalizing under-measured genes. **Avoid by:** Explicit three-state encoding (present/absent/unknown); layer-specific score normalization that doesn't penalize missing data; imputation using ortholog evidence with confidence weighting; coverage-aware constraint metrics (only use gnomAD when coverage >30x).

4. **Batch Effects Misinterpreted as Biological Signal in scRNA-seq** — Integration of multi-atlas scRNA-seq data (retina, inner ear, nasal epithelium) can erase true biological variation or create false cell-type signals. Only 27% of integration outputs perform better than unintegrated data. **Avoid by:** Validating integration quality using known marker genes; comparing multiple methods (Harmony, Seurat v5, scVI); using positive controls (known cilia genes should show expected cell-type enrichment); stratifying by sequencing technology before cross-platform integration.

5. **Reproducibility Theater Without Computational Environment Control** — Scripts are version-controlled but results drift due to uncontrolled dependencies (package versions, database snapshots, API response changes, random seeds). **Avoid by:** Pinning all dependencies with exact versions; containerizing environment (Docker/Singularity); snapshotting external databases with version tags; checksumming all downloaded data; setting random seeds globally; logging provenance metadata in all outputs.

## Implications for Roadmap

Based on research, suggested phase structure follows **dependency-driven ordering**: infrastructure first, single-layer prototype to validate architecture, parallel evidence layer development, integration/scoring, then reporting/polish.

### Phase 1: Data Infrastructure & Configuration
**Rationale:** All downstream components depend on config system, gene ID mapping utilities, and data storage patterns. Critical to establish before any evidence retrieval.
**Delivers:** Project skeleton, YAML config loading with Pydantic validation, DuckDB schema setup, gene ID mapping utility, API caching infrastructure.
**Addresses:**
- Reproducibility documentation (table stakes)
- Parameter configuration (table stakes)
- Data provenance tracking (table stakes)
**Avoids:**
- Gene ID mapping inconsistency (Pitfall #1) via standardized Ensembl IDs and validation gates
- Reproducibility failure (Pitfall #8) via containerization and version pinning

**Research flag:** SKIP deeper research — standard Python packaging patterns, well-documented.

### Phase 2: Single Evidence Layer Prototype
**Rationale:** Validate the retrieval → normalization → storage pattern before scaling to 6 layers. Identifies architectural issues early with low cost.
**Delivers:** One complete evidence layer (recommend starting with genetic constraint: gnomAD pLI/LOEUF as simplest API), end-to-end flow from API to DuckDB storage.
**Addresses:**
- API-based data retrieval (table stakes)
- Quality control checks (table stakes)
**Avoids:**
- Missing data as negative evidence (Pitfall #3) by designing explicit unknown-state handling from start
- Constraint metrics misinterpreted (Pitfall #6) via coverage-aware filtering

**Research flag:** MAY NEED `/gsd:research-phase` — gnomAD API usage patterns and coverage thresholds need validation.

### Phase 3: Remaining Evidence Layers (Parallel Work)
**Rationale:** Layers are independent by design; can be built in parallel. No inter-dependencies between annotation, expression, protein features, localization, phenotypes modules.
**Delivers:** 5 additional evidence layers replicating Phase 2 pattern (annotation, expression, protein features, localization, phenotypes + literature scan).
**Addresses:**
- Multi-evidence scoring foundation (table stakes) — requires all 6 layers operational
**Avoids:**
- Ortholog function over-assumed (Pitfall #5) via confidence scoring and phenotype relevance filtering
- API rate limits (Performance trap) via batch queries, exponential backoff, API keys

**Research flag:** NEEDS `/gsd:research-phase` for specialized APIs — CellxGene, IMPC, MGI/ZFIN integration patterns are niche and poorly documented.

### Phase 4: Integration & Scoring System
**Rationale:** Requires all evidence layers complete. Core scientific logic. Most complex component requiring validation against positive/negative controls.
**Delivers:** Multi-evidence scoring via SQL joins in DuckDB, weighted aggregation, known gene exclusion filter (CiliaCarta/SYSCILIA/OMIM), confidence tier assignment (high/medium/low).
**Addresses:**
- Multi-evidence scoring (table stakes) — weighted integration of all layers
- Known gene validation (table stakes) — benchmarking against established ciliopathy genes
- Tiered output with rationale (table stakes) — confidence classification
**Avoids:**
- Literature bias amplification (Pitfall #2) via publication-independent scoring layers and diversity requirements
- Missing data as negative evidence (Pitfall #3) via layer-aware scoring that preserves genes with partial data

**Research flag:** MAY NEED `/gsd:research-phase` — weight optimization strategies and validation metrics need domain-specific tuning.

### Phase 5: Reporting & Provenance
**Rationale:** Depends on integration layer producing scored results. Presentation layer, less critical for initial validation.
**Delivers:** Per-gene evidence summaries, provenance metadata generation (versions, timestamps, config hash), tiered candidate lists (TSV + Parquet), basic visualizations (score distributions, top candidates).
**Addresses:**
- Structured output format (table stakes)
- Basic visualization (table stakes)
- Data provenance tracking (completion)

**Research flag:** SKIP deeper research — standard output formatting and metadata patterns.

### Phase 6: CLI Orchestration & End-to-End Testing
**Rationale:** Integrates all components. User-facing interface. Validate full pipeline on test gene sets before production run.
**Delivers:** Unified Typer CLI app with subcommands (run-layer, integrate, report), dependency checking, progress logging with Rich, force-refresh flags, partial reruns.
**Addresses:**
- Batch processing (table stakes) — end-to-end orchestration with progress tracking

**Research flag:** SKIP deeper research — Typer CLI patterns well-documented.

### Phase 7: Validation & Weight Tuning
**Rationale:** After pipeline operational end-to-end, systematically validate against positive controls (known Usher/cilia genes) and negative controls (housekeeping genes). Iterate on scoring weights.
**Delivers:** Validation metrics (recall@10, recall@50 for positive controls; precision for negative controls), sensitivity analysis across parameter sweeps, finalized scoring weights.
**Addresses:**
- Known gene validation (completion) — quantitative benchmarking
- Sensitivity analysis (differentiator) — robustness demonstration

**Research flag:** MAY NEED `/gsd:research-phase` — validation metrics for gene prioritization pipelines need domain research.

### Phase 8 (v1.x): Explainability & Advanced Reporting
**Rationale:** After v1 produces validated candidate list. Adds interpretability for hypothesis generation and publication.
**Delivers:** SHAP-style per-gene evidence breakdown, interactive HTML report with sortable tables, evidence conflict detection, negative control validation.
**Addresses:**
- Explainable scoring (differentiator)
- Interactive HTML report (differentiator)
- Evidence conflict detection (differentiator)

**Research flag:** NEEDS `/gsd:research-phase` — SHAP for non-ML scoring systems and HTML report generation for bioinformatics need investigation.

### Phase Ordering Rationale

- **Sequential dependencies:** Phase 1 → Phase 2 → Phase 4 (infrastructure → prototype → integration) form the critical path; each depends on prior completion.
- **Parallelizable work:** Phase 3 (6 evidence layers) can be built concurrently by different developers or sequentially with rapid iteration.
- **Defer polish until validation:** Phases 5-6 (reporting, CLI) can be minimal initially; focus on scientific correctness (Phase 4) first.
- **Validate before extending:** Phase 7 (validation) must succeed before adding Phase 8 (advanced features); prevents building on broken foundation.

**Architecture-driven grouping:** Phases align with architectural layers (CLI orchestration, data retrieval, normalization, storage, integration, reporting) rather than arbitrary feature sets. Enables modular testing and isolated debugging.

**Pitfall avoidance:** Early phases establish mitigation strategies:
- Phase 1 prevents gene ID mapping issues (Pitfall #1) and reproducibility failures (Pitfall #8)
- Phase 2 prototype validates missing data handling (Pitfall #3)
- Phase 4 integration layer addresses literature bias (Pitfall #2)
- Validation throughout prevents silent failures from propagating

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Constraint Metrics):** gnomAD API usage patterns, coverage thresholds, transcript selection — MEDIUM priority research
- **Phase 3 (Specialized APIs):** CellxGene census API, IMPC phenotype API, MGI/ZFIN bulk download workflows — HIGH priority research (niche, sparse documentation)
- **Phase 4 (Weight Optimization):** Validation metrics for gene prioritization, weight tuning strategies, positive control benchmark datasets — MEDIUM priority research
- **Phase 7 (Validation Metrics):** Recall/precision thresholds for rare disease discovery, statistical significance testing for constraint enrichment — LOW priority research (standard metrics available)
- **Phase 8 (SHAP for Rule-Based Systems):** Explainability methods for non-ML weighted scoring, HTML report generation best practices — MEDIUM priority research

Phases with standard patterns (skip research-phase):
- **Phase 1 (Infrastructure):** Python packaging, YAML config loading, DuckDB schema design — well-documented, no novelty
- **Phase 5 (Reporting):** Output formatting, CSV/Parquet generation, basic matplotlib/seaborn visualizations — standard patterns
- **Phase 6 (CLI):** Typer CLI design, Rich progress bars, logging configuration — mature libraries with excellent docs

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All core technologies verified via official PyPI pages, Context7 library coverage. Version compatibility matrix validated. Alternative comparisons (Polars vs Pandas, uv vs Poetry) based on benchmarks and community adoption trends. |
| Features | MEDIUM | Feature expectations derived from 20+ peer-reviewed publications on gene prioritization tools (Exomiser, LIRICAL, CilioGenics) and bioinformatics best practices. No Context7 coverage for specialized domain tools; relied on WebSearch + academic literature. MVP recommendations synthesized from multiple sources. |
| Architecture | MEDIUM-HIGH | Architectural patterns validated across multiple bioinformatics pipeline implementations (PHA4GE best practices, nf-core patterns, academic publications). DuckDB vs SQLite comparison based on performance benchmarks. Staged pipeline pattern is industry standard. Confidence reduced slightly due to limited Context7 coverage for workflow orchestrators. |
| Pitfalls | HIGH | 40+ authoritative sources covering gene ID mapping failures (Bioconductor, UniProt docs), literature bias (Nature Scientific Reports), scRNA-seq batch effects (Nature Methods benchmarks), reproducibility failures (PLOS Computational Biology). Pitfall scenarios validated across multiple independent publications. Warning signs derived from "Common Bioinformatics Mistakes" community resources. |

**Overall confidence:** MEDIUM-HIGH

Research is well-grounded in established practices and peer-reviewed literature. Stack recommendations are conservative (mature technologies, not bleeding-edge). Architecture patterns are proven in production bioinformatics pipelines. Pitfalls are validated with quantitative data (e.g., "51% Ensembl ID conversion failure rate" from Bioconductor, "27% integration performance" from Nature Methods benchmarking).

Confidence reduced from HIGH due to:
1. Limited Context7 coverage for specialized bioinformatics tools (gget, scanpy, gnomad-toolbox)
2. Niche domain (ciliopathy research) has smaller community and fewer standardized tools than general genomics
3. Some API integration patterns (CellxGene, IMPC) rely on recent documentation that may be incomplete

### Gaps to Address

**During planning/Phase 2:**
- **gnomAD constraint metric reliability thresholds:** Research identified coverage-dependent issues but exact cutoffs (mean depth >30x, >90% CDS covered) need validation during implementation. Test on known ciliopathy genes to calibrate.
- **Transcript selection for tissue-specific genes:** SHANK2 example shows dramatic pLI differences between canonical and brain-specific transcripts. Need strategy for selecting appropriate transcript for retina/inner ear genes. Validate against GTEx isoform expression data.

**During planning/Phase 3:**
- **CellxGene API performance and quotas:** Census API is recent (2024-2025); rate limits and data transfer costs unclear. May need to pivot to bulk h5ad downloads if API proves impractical for 20K gene queries.
- **MGI/ZFIN/IMPC bulk download formats:** No official Python APIs; relying on bulk downloads. Need to validate download URLs are stable and file formats are parseable. Build sample parsing scripts during research-phase.

**During planning/Phase 4:**
- **Scoring weight initialization:** Literature provides ranges (expression 15-25%, constraint 10-20%) but optimal weights are dataset-dependent. Plan for iterative tuning using positive controls rather than assuming initial weights are final.
- **Under-annotation bias correction strategy:** Novel research direction; no established methods found. May need to defer to v2 if initial attempts don't improve results. Test correlation(score, pubmed_count) as success metric.

**During planning/Phase 7:**
- **Positive control gene set curation:** Need curated list of ~50-100 established ciliopathy genes with high confidence for validation. CiliaCarta (>600 genes) too broad; SYSCILIA Gold Standard (~200 genes) better. Manual curation required.
- **Negative control gene set:** Need ~50-100 high-confidence non-cilia genes (housekeeping, muscle-specific, liver-specific) for specificity testing. No standard negative control sets found in literature.

**Validation during implementation:**
- **scRNA-seq integration method selection:** Harmony vs Seurat v5 vs scVI performance is dataset-dependent. Research recommends comparing multiple methods, but optimal choice won't be known until testing on actual retina/inner ear atlases.
- **Ortholog confidence score thresholds:** DIOPT provides scores 0-15; research suggests prioritizing high-confidence orthologs but doesn't specify cutoff. Test recall vs precision tradeoff during Phase 3.

## Sources

### Primary (HIGH confidence)
- **STACK.md sources (official PyPI and Context7):**
  - Polars 1.38.1, gget 0.30.2, Biopython 1.86, Typer 0.21.2, Pydantic 2.12.5 — PyPI verified Feb 2026
  - polars-bio performance benchmarks (Oxford Academic, Dec 2025): 6-38x speedup over bioframe
  - uv package manager (multiple sources): 10-100x faster than pip
- **FEATURES.md sources (peer-reviewed publications):**
  - "Survey and improvement strategies for gene prioritization with LLMs" (Bioinformatics Advances, 2026)
  - "Rare disease gene discovery in 100K Genomes Project" (Nature, 2025)
  - "CilioGenics: integrated method for predicting ciliary genes" (NAR, 2024)
  - "Standards for validating NGS bioinformatics pipelines" (AMP/CAP, 2018)
- **ARCHITECTURE.md sources (bioinformatics best practices):**
  - PHA4GE Pipeline Best Practices (GitHub, community-validated)
  - "Bioinformatics Pipeline Architecture Best Practices" (multiple implementations)
  - DuckDB vs SQLite benchmarks (Bridge Informatics, DataCamp): 10-100x faster for analytics
  - "Pipeline Provenance for Reproducibility" (arXiv, 2024)
- **PITFALLS.md sources (authoritative quantitative data):**
  - Gene ID mapping failures: "How to map all Ensembl IDs to Gene Symbols" (Bioconductor Support, 51% NA rate)
  - Literature bias: "Gene annotation bias impedes biomedical research" (Scientific Reports, 2018)
  - scRNA-seq batch effects: "Benchmarking atlas-level data integration" (Nature Methods, 2021): 27% performance
  - Ortholog conservation: "Functional and evolutionary implications of gene orthology" (Nature Reviews Genetics)
  - gnomAD constraint: "No preferential mode of inheritance for highly constrained genes" (PMC, 2022)

### Secondary (MEDIUM confidence)
- **FEATURES.md:**
  - Exomiser/LIRICAL feature comparisons (tool documentation + GitHub issues)
  - Multi-evidence integration methods (academic publications, 2009-2024)
  - Explainability methods for genomics (WIREs Data Mining, 2023)
- **ARCHITECTURE.md:**
  - Workflow manager comparisons (Nextflow vs Snakemake, 2025 analysis)
  - Python CLI tool comparisons (argparse vs Click vs Typer, multiple blogs)
  - Gene annotation pipeline architectures (NCBI, AnnotaPipeline)
- **PITFALLS.md:**
  - API rate limit documentation (NCBI E-utilities, UniProt)
  - Tissue specificity scoring methods (TransTEx, Bioinformatics 2024)
  - Literature mining tools (GLAD4U, PubTator 3.0)

### Tertiary (LOW confidence — needs validation)
- AlphaFold NVIDIA 4090 compatibility (GitHub issues): 24GB VRAM below 32GB recommended, may work with configuration
- MGI/ZFIN/IMPC Python API availability (web search): No official libraries found, bulk downloads required
- CellxGene Census API quotas and rate limits (recent docs, 2024-2025): Documentation incomplete

---
*Research completed: 2026-02-11*
*Ready for roadmap: yes*

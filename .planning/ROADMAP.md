# Roadmap: Usher Cilia Candidate Gene Discovery Pipeline

## Overview

This pipeline transforms ~20,000 human protein-coding genes into a ranked, evidence-backed list of under-studied cilia/Usher candidates. The journey progresses from foundational data infrastructure through six independent evidence layers (annotation, expression, protein features, localization, genetic constraint, animal models, literature), multi-evidence scoring with transparent weights, and tiered output generation. Each phase delivers testable capabilities that compound toward a fully traceable, reproducible gene prioritization system.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Infrastructure** - Foundation for reproducible, modular pipeline
- [x] **Phase 2: Prototype Evidence Layer** - Validate retrieval-to-storage architecture
- [x] **Phase 3: Core Evidence Layers** - Parallel multi-source data retrieval
- [x] **Phase 4: Scoring & Integration** - Multi-evidence weighted scoring system
- [x] **Phase 5: Output & CLI** - User-facing interface and tiered results
- [ ] **Phase 6: Validation** - Benchmark scoring against known genes

## Phase Details

### Phase 1: Data Infrastructure
**Goal**: Establish reproducible data foundation and gene ID mapping utilities
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07
**Success Criteria** (what must be TRUE):
  1. Pipeline uses Ensembl gene IDs as primary keys throughout with validated mapping to HGNC symbols and UniProt accessions
  2. Configuration system loads YAML parameters with Pydantic validation and rejects invalid configs
  3. API clients retrieve data from external sources with rate limiting, retry logic, and persistent disk caching
  4. DuckDB database stores intermediate results enabling restart-from-checkpoint without re-downloading
  5. Every pipeline output includes provenance metadata: pipeline version, data source versions, timestamps, config hash
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md -- Project scaffold, config system, and base API client
- [x] 01-02-PLAN.md -- Gene ID mapping with validation gates
- [x] 01-03-PLAN.md -- DuckDB persistence and provenance tracking
- [x] 01-04-PLAN.md -- CLI integration and end-to-end wiring

### Phase 2: Prototype Evidence Layer
**Goal**: Validate retrieval-to-storage pattern with single evidence layer
**Depends on**: Phase 1
**Requirements**: GCON-01, GCON-02, GCON-03
**Success Criteria** (what must be TRUE):
  1. Pipeline retrieves gnomAD constraint metrics (pLI, LOEUF) for all human protein-coding genes
  2. Constraint scores are filtered by coverage quality (mean depth >30x, >90% CDS covered) and stored with quality flags
  3. Missing data is encoded as "unknown" rather than zero, preserving genes with incomplete coverage
  4. Prototype layer writes normalized scores to DuckDB and demonstrates checkpoint restart capability
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md -- gnomAD data model, download, coverage filter, and normalization
- [x] 02-02-PLAN.md -- DuckDB persistence, CLI evidence command, and integration tests

### Phase 3: Core Evidence Layers
**Goal**: Complete all remaining evidence retrieval modules
**Depends on**: Phase 2
**Requirements**: ANNOT-01, ANNOT-02, ANNOT-03, EXPR-01, EXPR-02, EXPR-03, EXPR-04, PROT-01, PROT-02, PROT-03, PROT-04, LOCA-01, LOCA-02, LOCA-03, ANIM-01, ANIM-02, ANIM-03, LITE-01, LITE-02, LITE-03
**Success Criteria** (what must be TRUE):
  1. Pipeline quantifies annotation depth per gene using GO term count, UniProt score, and pathway membership with tier classification
  2. Expression data from HPA, GTEx, and CellxGene is retrieved for retina, inner ear, and cilia-rich tissues with normalized specificity metrics
  3. Protein features (length, domains, coiled-coils, cilia motifs, transmembrane regions) are extracted from UniProt/InterPro as normalized features
  4. Localization evidence from HPA and proteomics datasets distinguishes experimental from computational predictions
  5. Animal model phenotypes from MGI, ZFIN, and IMPC are filtered for sensory/cilia relevance with ortholog confidence scoring
  6. Literature evidence from PubMed distinguishes direct experimental evidence from incidental mentions with quality-weighted scoring
**Plans**: 6 plans

Plans:
- [x] 03-01-PLAN.md -- Gene annotation completeness (GO terms, UniProt scores, pathway membership, tier classification)
- [x] 03-02-PLAN.md -- Tissue expression (HPA, GTEx, CellxGene with Tau specificity and enrichment scoring)
- [x] 03-03-PLAN.md -- Protein sequence/structure features (UniProt/InterPro domains, cilia motifs, normalization)
- [x] 03-04-PLAN.md -- Subcellular localization (HPA subcellular, cilia proteomics, evidence type distinction)
- [x] 03-05-PLAN.md -- Animal model phenotypes (MGI, ZFIN, IMPC with HCOP ortholog mapping)
- [x] 03-06-PLAN.md -- Literature evidence (PubMed queries, evidence tier classification, quality-weighted scoring)

### Phase 4: Scoring & Integration
**Goal**: Multi-evidence weighted scoring with known gene validation
**Depends on**: Phase 3
**Requirements**: SCOR-01, SCOR-02, SCOR-03, SCOR-04, SCOR-05
**Success Criteria** (what must be TRUE):
  1. Known cilia/Usher genes from CiliaCarta, SYSCILIA, and OMIM are compiled as exclusion set and positive controls
  2. Weighted rule-based scoring integrates all evidence layers with configurable per-layer weights producing composite score per gene
  3. Scoring handles missing data explicitly with "unknown" status rather than penalizing genes lacking evidence in specific layers
  4. Known cilia/Usher genes rank highly before exclusion, validating that scoring system works
  5. Quality control checks detect missing data rates, score distribution anomalies, and outliers per evidence layer
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md -- Known gene compilation, weight validation, and multi-evidence scoring integration
- [x] 04-02-PLAN.md -- Quality control checks and positive control validation
- [x] 04-03-PLAN.md -- CLI score command and unit/integration tests

### Phase 5: Output & CLI
**Goal**: User-facing interface and structured tiered output
**Depends on**: Phase 4
**Requirements**: OUTP-01, OUTP-02, OUTP-03, OUTP-04, OUTP-05
**Success Criteria** (what must be TRUE):
  1. Pipeline produces tiered candidate list (high/medium/low confidence) based on composite score and evidence breadth
  2. Each candidate includes multi-dimensional evidence summary showing which layers support it and which have gaps
  3. Output is available in TSV and Parquet formats compatible with downstream PPI and structural prediction tools
  4. Pipeline generates visualizations: score distribution, evidence layer contribution, tier breakdown
  5. Unified CLI provides subcommands for running layers, integration, and reporting with progress logging
  6. Reproducibility report documents all parameters, data versions, gene counts at filtering steps, and validation metrics
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md -- Tiered candidate output with evidence summary and dual-format writer (TSV+Parquet)
- [x] 05-02-PLAN.md -- Visualizations (score distribution, layer contributions, tier breakdown) and reproducibility report
- [x] 05-03-PLAN.md -- CLI report command wiring all output modules with integration tests

### Phase 6: Validation
**Goal**: Benchmark scoring system against positive and negative controls
**Depends on**: Phase 5
**Requirements**: (No new requirements - validates existing system)
**Success Criteria** (what must be TRUE):
  1. Positive control validation shows known cilia/Usher genes achieve high recall (>70% in top 10% of candidates)
  2. Negative control validation shows housekeeping genes are deprioritized (low scores, excluded from high-confidence tier)
  3. Sensitivity analysis across parameter sweeps demonstrates rank stability for top candidates
  4. Final scoring weights are tuned based on validation metrics and documented with rationale
**Plans**: 3 plans

Plans:
- [ ] 06-01-PLAN.md -- Negative control validation (housekeeping genes) and enhanced positive control metrics (recall@k)
- [ ] 06-02-PLAN.md -- Sensitivity analysis (weight perturbation sweeps with Spearman rank correlation)
- [ ] 06-03-PLAN.md -- Comprehensive validation report, CLI validate command, and unit tests

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Infrastructure | 4/4 | Complete | 2026-02-11 |
| 2. Prototype Evidence Layer | 2/2 | Complete | 2026-02-11 |
| 3. Core Evidence Layers | 6/6 | Complete | 2026-02-11 |
| 4. Scoring & Integration | 3/3 | Complete | 2026-02-11 |
| 5. Output & CLI | 3/3 | Complete | 2026-02-12 |
| 6. Validation | 0/3 | Not started | - |

# Usher Cilia Candidate Gene Discovery Pipeline

## What This Is

A reproducible bioinformatics pipeline that screens all ~20,000 human protein-coding genes across 6 evidence layers to identify under-studied candidates likely involved in cilia/sensory cilia pathways relevant to Usher syndrome. Integrates genetic constraint, tissue expression, gene annotation, protein features, subcellular localization, animal model phenotypes, and literature evidence into a transparent weighted scoring system producing tiered candidate lists.

## Core Value

Produce a high-confidence, multi-evidence-backed ranked list of under-studied cilia/Usher candidate genes that is fully traceable — every gene's inclusion is explainable by specific evidence, and every gap is documented.

## Current State

**Shipped:** v1.0 MVP (2026-02-12)
**Codebase:** 21,183 lines Python across 164 files
**Tech stack:** Python, Click CLI, DuckDB, Polars, Pydantic, matplotlib/seaborn, scipy, structlog

**What works:**
- `usher-pipeline setup` — fetches gene universe from Ensembl with HGNC/UniProt mapping
- `usher-pipeline evidence <layer>` — 7 evidence layer subcommands with checkpoint-restart
- `usher-pipeline score` — multi-evidence weighted scoring with QC and positive control validation
- `usher-pipeline report` — tiered output (TSV+Parquet), visualizations, reproducibility report
- `usher-pipeline validate` — positive/negative control validation, sensitivity analysis

**Known issues:**
- cellxgene-census version conflict blocks some test execution
- PubMed literature pipeline takes 3-11 hours for full gene universe (mitigated by checkpoint-restart)

## Requirements

### Validated

- ✓ Modular Python pipeline with independent, composable CLI scripts per evidence layer — v1.0
- ✓ Gene universe: all human protein-coding genes (Ensembl/HGNC aligned) — v1.0
- ✓ Evidence Layer 1: Gene annotation completeness (GO/UniProt) — v1.0
- ✓ Evidence Layer 2: Tissue-specific expression (HPA, GTEx, CellxGene) — v1.0
- ✓ Evidence Layer 3: Protein sequence/structure features (UniProt/InterPro) — v1.0
- ✓ Evidence Layer 4: Subcellular localization (HPA, cilia proteomics) — v1.0
- ✓ Evidence Layer 5: Genetic constraint (gnomAD pLI, LOEUF) — v1.0
- ✓ Evidence Layer 6: Animal model phenotypes (MGI, ZFIN, IMPC) — v1.0
- ✓ Systematic literature scanning per candidate — v1.0
- ✓ Known cilia/Usher gene set compiled as exclusion set and positive controls — v1.0
- ✓ Weighted rule-based multi-evidence integration scoring — v1.0
- ✓ Tiered output with per-gene evidence summaries and gap documentation — v1.0
- ✓ Output format compatible with downstream analyses — v1.0
- ✓ Sensitivity analysis with parameter sweep (originally v2, delivered early) — v1.0
- ✓ Negative control validation with housekeeping genes (originally v2, delivered early) — v1.0

### Active

(None — define with `/gsd:new-milestone`)

### Out of Scope

- Private/proprietary datasets — pipeline uses public data sources only
- Machine learning-based scoring — weighted rule-based approach chosen for full explainability
- Downstream PPI network or structural prediction analyses — this pipeline produces the input candidate list
- Wet-lab validation — computational discovery pipeline only
- Real-time data updates — pipeline runs against versioned snapshots of source databases
- Real-time web dashboard — static reports + CLI sufficient for research tool
- GUI for parameter tuning — research pipelines need reproducible CLI execution
- Variant-level analysis — gene-level discovery scope; use Exomiser/LIRICAL for variant work
- LLM-based automated literature scanning — manual/programmatic PubMed queries sufficient
- Bayesian evidence weight optimization — requires larger training set; manual tuning sufficient

## Context

Usher syndrome is the most common genetic cause of combined deafness and blindness. While several causal genes (USH1B/MYO7A, USH1C, USH2A, etc.) are known, the full molecular network — particularly scaffold, adaptor, and regulatory proteins connecting Usher complexes to cilia machinery — remains incompletely characterized.

The pipeline targets this gap: genes that have cilia-suggestive evidence across multiple layers but haven't been studied in the Usher/sensory cilia context.

Key public data sources: Ensembl, HGNC, UniProt, Gene Ontology, Human Protein Atlas, GTEx, CellxGene, InterPro, gnomAD, MGI, ZFIN, IMPC, CiliaCarta, SYSCILIA, OMIM, PubMed.

## Constraints

- **Language**: Python
- **Architecture**: Modular CLI (Click) with DuckDB persistence and Polars DataFrames
- **Data**: Public sources only
- **Scoring**: Weighted rule-based with transparent weights
- **Reproducibility**: Versioned data snapshots, provenance tracking, checkpoint-restart

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python over R/Bioconductor | Rich ecosystem for data integration (polars, biopython) | ✓ Good |
| Weighted rule-based scoring over ML | Explainability paramount; every score traceable to evidence | ✓ Good |
| Public data only | Reproducibility — anyone can re-run with same inputs | ✓ Good |
| Modular CLI scripts over workflow manager | Flexibility for iterative development; independent debugging | ✓ Good |
| DuckDB over SQLite | Native polars integration, better analytics queries | ✓ Good |
| NULL preservation (unknown ≠ zero) | Avoids penalizing genes with missing evidence | ✓ Good |
| Polars over pandas | Better performance with lazy evaluation, null handling | ✓ Good |
| LOEUF inversion (lower = more constrained = higher score) | Intuitive direction for scoring integration | ✓ Good |
| Log2 normalization for literature bias | Prevents well-studied gene dominance (TP53 problem) | ✓ Good |
| Housekeeping genes as negative controls | Literature-validated set (Eisenberg & Levanon 2013) | ✓ Good |
| Spearman rho ≥ 0.85 stability threshold | Based on rank stability literature for robustness testing | ✓ Good |
| Configurable tier thresholds | Allows flexible downstream use by confidence level | ✓ Good |

---
*Last updated: 2026-02-12 after v1.0 milestone*

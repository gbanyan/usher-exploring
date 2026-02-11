# Usher Cilia Candidate Gene Discovery Pipeline

## What This Is

A reproducible, explainable bioinformatics pipeline that systematically screens all human protein-coding genes (~20,000) to identify under-studied candidates likely involved in cilia/sensory cilia pathways — particularly those relevant to Usher syndrome. The pipeline integrates 6+ evidence layers, scores genes via weighted rule-based integration, and outputs a tiered candidate list for downstream protein interaction network and structural prediction analyses.

## Core Value

Produce a high-confidence, multi-evidence-backed ranked list of under-studied cilia/Usher candidate genes that is fully traceable — every gene's inclusion is explainable by specific evidence, and every gap is documented.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Modular Python pipeline with independent, composable CLI scripts per evidence layer
- [ ] Gene universe: all human protein-coding genes (Ensembl/HGNC aligned), excluding pseudogenes and transcripts lacking protein-level evidence
- [ ] Evidence Layer 1: Gene annotation completeness (GO/UniProt functional annotation depth)
- [ ] Evidence Layer 2: Tissue-specific expression (retina, inner ear/hair cells, cilia-rich tissues) from public atlases (HPA, GTEx, CellxGene published scRNA-seq)
- [ ] Evidence Layer 3: Protein sequence/structure features (length, domain composition, coiled-coil, scaffold/adaptor domains, cilia-associated motifs)
- [ ] Evidence Layer 4: Subcellular localization evidence (centrosome, basal body, cilium, stereocilia) from high-throughput proteomics datasets
- [ ] Evidence Layer 5: Human genetic constraint (loss-of-function tolerance from gnomAD, selection pressure indicators)
- [ ] Evidence Layer 6: Animal model phenotypes (sensory, balance, vision, cilia phenotypes from model organism databases)
- [ ] Systematic literature scanning per candidate (distinguishing direct experimental evidence, incidental mentions, high-throughput hits)
- [ ] Known cilia/Usher gene set compiled from public sources (CiliaCarta, SYSCILIA gold standard, OMIM Usher genes) as exclusion set and positive controls
- [ ] Weighted rule-based multi-evidence integration scoring with transparent weights
- [ ] Tiered output (high/medium/low confidence) with per-gene evidence summaries and data gap documentation
- [ ] Output format compatible with downstream PPI network analysis (STRING/BioGRID), structural prediction (AlphaFold-Multimer), and additional analyses

### Out of Scope

- Private/proprietary datasets — pipeline uses public data sources only
- Machine learning-based scoring — weighted rule-based approach chosen for full explainability
- Downstream PPI network or structural prediction analyses — this pipeline produces the input candidate list
- Wet-lab validation — computational discovery pipeline only
- Real-time data updates — pipeline runs against versioned snapshots of source databases

## Context

Usher syndrome is the most common genetic cause of combined deafness and blindness. While several causal genes (USH1B/MYO7A, USH1C, USH2A, etc.) are known, the full molecular network — particularly scaffold, adaptor, and regulatory proteins connecting Usher complexes to cilia machinery — remains incompletely characterized. Many genes with cilia-relevant features lack functional annotation, creating a discovery opportunity.

The pipeline targets this gap: genes that have cilia-suggestive evidence across multiple layers but haven't been studied in the Usher/sensory cilia context. By operationalizing "under-studied" (limited GO annotation, sparse mechanistic literature, not in canonical cilia gene lists) and cross-referencing with expression, structural, localization, genetic, and phenotypic evidence, the pipeline surfaces candidates that would otherwise remain invisible.

Key public data sources:
- **Gene annotation:** Ensembl, HGNC, UniProt, Gene Ontology
- **Expression:** Human Protein Atlas, GTEx, CellxGene (published retina/cochlea scRNA-seq datasets)
- **Protein features:** UniProt domains, InterPro, Pfam
- **Localization:** Human Protein Atlas subcellular, OpenCell, published centrosome/cilium proteomics
- **Genetic constraint:** gnomAD (pLI, LOEUF scores)
- **Animal models:** MGI (mouse), ZFIN (zebrafish), IMPC
- **Known gene sets:** CiliaCarta, SYSCILIA gold standard, OMIM (Usher-related entries)
- **Literature:** PubMed/NCBI for systematic text scanning

## Constraints

- **Language**: Python — all pipeline modules written in Python
- **Architecture**: Modular CLI scripts — each evidence layer is an independent module, composable via standard input/output
- **Data**: Public sources only — no proprietary or access-restricted datasets
- **Compute**: Local workstation with NVIDIA 4090 GPU — GPU available if needed for large-scale computations
- **Scoring**: Weighted rule-based — fully transparent, no black-box models
- **Reproducibility**: Versioned data snapshots, pinned dependencies, documented parameters

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python over R/Bioconductor | User preference; rich ecosystem for data integration (pandas, scanpy, biopython) | — Pending |
| Weighted rule-based scoring over ML | Explainability is paramount; every gene's score must be traceable to specific evidence | — Pending |
| Public data only | Reproducibility — anyone can re-run the pipeline with the same inputs | — Pending |
| Modular CLI scripts over workflow manager | Flexibility for iterative development; each layer can be run/debugged independently | — Pending |
| Known gene exclusion via CiliaCarta/SYSCILIA/OMIM | Standard community-curated lists; used as both exclusion set and positive controls for validation | — Pending |
| Tiered output over fixed cutoff | Allows flexible downstream use — high-confidence for focused follow-up, medium/low for broader network analysis | — Pending |

---
*Last updated: 2026-02-11 after initialization*

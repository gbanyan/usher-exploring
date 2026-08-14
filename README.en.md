# Usher Cilia Candidate Gene Discovery Pipeline

> **[中文版 (README.md)](README.md)**

A reproducible bioinformatics pipeline for systematic screening of candidate genes associated with Usher syndrome and ciliopathies.

This pipeline evaluates 20,116 human protein-coding Ensembl identifiers from the frozen Ensembl 113 GRCh38 GTF across six complementary evidence layers, producing weighted composite scores and tiered candidate hypotheses for downstream experimental validation. HGNC remapping and downstream counts are regenerated from the frozen source. A high score is not evidence of a causal gene–disease relationship.

---

## Table of Contents

- [Research Background](#research-background)
- [Pipeline Overview](#pipeline-overview)
- [Installation and Setup](#installation-and-setup)
- [Running the Pipeline](#running-the-pipeline)
- [The Six Evidence Layers in Detail](#the-six-evidence-layers-in-detail)
  - [1. gnomAD Constraint Analysis](#1-gnomad-constraint-analysis)
  - [2. Gene Functional Annotation](#2-gene-functional-annotation)
  - [3. Tissue Expression Specificity](#3-tissue-expression-specificity)
  - [4. Subcellular Localization](#4-subcellular-localization)
  - [5. Animal Model Phenotypes](#5-animal-model-phenotypes)
  - [6. Literature Mining](#6-literature-mining)
- [Composite Scoring and Tiering](#composite-scoring-and-tiering)
- [Validation](#validation)
- [Output Files](#output-files)
- [Configuration](#configuration)
- [Known Limitations](#known-limitations)
- [Data Sources and References](#data-sources-and-references)

---

## Research Background

**Usher syndrome** is the most common cause of hereditary deaf-blindness, characterized by sensorineural hearing loss and retinitis pigmentosa. Several established Usher genes are known, yet a subset of clinically diagnosed patients carry no pathogenic variants in those genes. Additional genes, modifiers, and noncoding mechanisms remain hypotheses for investigation.

Usher proteins play critical roles in cilia and cilia-associated structures, particularly the connecting cilium of retinal photoreceptors and the stereocilia of inner ear hair cells. This pipeline therefore adopts **ciliary biology** as its central framework, integrating multi-dimensional genomic and functional data to prioritize candidate hypotheses for follow-up.

### Core Design Principles

- **Missing data ≠ zero score**: If a gene lacks data in a given evidence layer (NULL), it is not treated as negative evidence. Only layers with available data contribute to the weighted average. This does not prove that sparse-evidence genes are understudied or relevant.
- **Complementary multi-evidence prioritization**: Six evidence layers assess cilia/Usher relevance from complementary angles, while preserving the limitations and biases of each source.
- **Full reproducibility**: All data versions, parameters, and analysis steps are recorded with provenance tracking.

---

## Pipeline Overview

```
┌──────────────────────────────────────────────────────┐
│  Step 1: Build Gene Universe                         │
│  Load 20,116 protein-coding Ensembl IDs              │
│  from the frozen Ensembl 113 GRCh38 GTF              │
└────────────────────────┬─────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────┐
│  Step 2: Six Evidence Layers (independent, any order)│
│                                                      │
│  ┌────────────┐ ┌────────────┐ ┌─────────────────┐  │
│  │ gnomAD     │ │ Functional │ │ Tissue          │  │
│  │ Constraint │ │ Annotation │ │ Expression      │  │
│  └────────────┘ └────────────┘ └─────────────────┘  │
│  ┌────────────┐ ┌────────────┐ ┌─────────────────┐  │
│  │ Subcellular│ │ Animal     │ │ Literature      │  │
│  │ Localiz.   │ │ Models     │ │ Mining          │  │
│  └────────────┘ └────────────┘ └─────────────────┘  │
└────────────────────────┬─────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────┐
│  Step 3: Composite Weighted Scoring + Tiering        │
│  NULL-aware weighted average → HIGH/MEDIUM/LOW       │
└────────────────────────┬─────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────┐
│  Step 4: Validation + Report Generation              │
│  Known Usher/cilia gene ranking check                │
│  → TSV + Parquet + Visualizations                    │
└──────────────────────────────────────────────────────┘
```

---

## Installation and Setup

### System Requirements

- Python 3.11 or later
- Approximately 5 GB disk space (for caching downloaded databases)
- Internet connection (required on first run to download external data)

### Installation

Open a terminal, navigate to the project directory, and run:

```bash
# 1. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate    # macOS / Linux
# .venv\Scripts\activate     # Windows

# 2. Install the pipeline
pip install -e ".[dev]"
```

For the optional CELLxGENE Census integration, install the expression extra as well:

```bash
pip install -e ".[dev,expression]"
```

To verify the installation:

```bash
usher-pipeline info
```

If you see a version number and configuration summary, the installation was successful.

### NCBI API Key (required for literature mining)

The literature mining layer queries PubMed via the NCBI E-utilities API. An email address is required, and an API key is recommended to increase query throughput (3 requests/second without key, 10 requests/second with key).

To obtain an API key: register an NCBI account at https://www.ncbi.nlm.nih.gov/account/ and generate a key in your account settings.

---

## Running the Pipeline

Below is the complete execution workflow. Each step is an independent command, run in order.

> **Note**: Each command prints summary statistics upon completion. If a step fails, fix the issue and re-run the same command — all steps are idempotent (re-running produces no duplicate data).

### Step 1: Build Gene Universe

```bash
usher-pipeline setup
```

This step will:
- Load the locally cached Ensembl 113 GRCh38 GTF and retain only `gene` records whose per-ID `gene_biotype` is exactly `protein_coding`
- Establish mappings between Ensembl Gene ID, HGNC Symbol, and UniProt Accession
- Store results in a local DuckDB database (`data/pipeline.duckdb`)

The frozen source is configured by `versions.ensembl_gene_source` and its
SHA-256 digest. Setup fails if the cache is absent or has changed; MyGene is
used only for identifier annotation after the release-pinned universe is
loaded.

### Step 2: Run the Six Evidence Layers

The six layers can be run in any order, as they are independent of each other. However, run them **one at a time** — do not run two simultaneously (DuckDB supports only a single writer).

```bash
# 2a. gnomAD constraint metrics
usher-pipeline evidence gnomad

# 2b. Gene functional annotation
usher-pipeline evidence annotation

# 2c. Tissue expression specificity
usher-pipeline evidence expression

# 2d. Subcellular localization
usher-pipeline evidence localization

# 2e. Animal model phenotypes
usher-pipeline evidence animal-models

# 2f. Literature mining (email required; API key recommended)
usher-pipeline evidence literature --email your@email.com --api-key YOUR_KEY
```

> **Note**: The literature mining layer queries PubMed records for the remapped frozen gene universe, which is rate-limited. Bulk source files and PubMed context sets are cached locally. To recompute transforms from existing local caches without forcing source downloads, use `--reprocess-cached` with the expression or literature evidence command. If a run is interrupted, re-run the same command to resume from its checkpoint.

### Step 3: Composite Scoring

```bash
usher-pipeline score
```

This step will:
- LEFT JOIN all six evidence layer scores with the gene universe
- Compute a NULL-aware weighted composite score
- Validate rankings against known Usher/cilia genes (positive controls)
- Classify genes into HIGH / MEDIUM / LOW confidence tiers

### Step 4: Generate Report

```bash
usher-pipeline report
```

Output files are written to the `data/report/` directory, including:
- `candidates.tsv` — Candidate gene list (tab-separated; can be opened in Excel)
- `candidates.parquet` — Same data in high-performance binary format (for R/Python analysis)
- `score_distribution.png` — Score distribution histogram
- `evidence_coverage.png` — Coverage chart for each evidence layer
- `tier_distribution.png` — Confidence tier pie chart
- `reproducibility.md` — Full provenance record (parameters, data versions, software environment)

### Optional: Validation Report

```bash
usher-pipeline validate
```

Verifies that known Usher genes and SYSCILIA cilia genes rank in the top 25%, confirming the scoring system's effectiveness.

---

## The Six Evidence Layers in Detail

### 1. gnomAD Constraint Analysis

**Biological question**: Does this gene show strong selective constraint against loss-of-function (LoF) variants in human populations?

**Data source**: gnomAD v4.1 constraint metrics

**Scientific rationale**:
If a gene is essential for normal physiological function (e.g., sensory function), loss-of-function variants should be rarely observed in the human population, because carriers of such variants would have reduced fitness. The gnomAD database quantifies this by comparing the observed number of LoF variants against the expected number.

**Key metrics**:
- **LOEUF** (Loss-of-function Observed/Expected Upper bound Fraction): Lower values indicate stronger constraint
- **pLI** (Probability of LoF Intolerance): Higher values indicate greater intolerance to LoF variants

**Scoring**:
LOEUF is inverted and normalized to a 0–1 range:

```
loeuf_normalized = (LOEUF_max − LOEUF) / (LOEUF_max − LOEUF_min)
```

Higher score = stronger constraint = greater functional importance.

**Quality control**: Requires mean sequencing depth ≥30x and CDS coverage ≥90%. Genes below these thresholds are flagged as `incomplete_coverage`.

---

### 2. Gene Functional Annotation

**Biological question**: How well-characterized is this gene in terms of functional annotations?

**Data sources**:
- Gene Ontology (GO) — biological process, molecular function, cellular component
- UniProt — protein annotation quality score (0–5)
- KEGG / Reactome — metabolic and signaling pathway membership

**Scientific rationale**:
The completeness of functional annotation measures available annotation, not how thoroughly a gene has been studied. Genes with fewer annotations may reflect many different situations, including recent discovery or incomplete database coverage; this layer therefore carries only 15% weight and must be interpreted with the other evidence layers.

**Scoring**:

```
annotation_score = 0.5 × GO_component + 0.3 × UniProt_component + 0.2 × pathway_component

where:
  GO_component = log₂(GO_term_count + 1) / log₂(max_GO_count + 1)
  UniProt_component = uniprot_score / 5.0
  pathway_component = 1 if any pathway annotation exists, else 0
```

---

### 3. Tissue Expression Specificity

**Biological question**: Is this gene preferentially expressed in Usher-relevant tissues (retina, inner ear)?

**Data sources**:
- **HPA** (Human Protein Atlas) v23 — tissue-level RNA expression (TPM)
- **GTEx** v8 — bulk RNA-seq across 54 human tissues
- **CELLxGENE Census** — single-cell RNA-seq (photoreceptor data in the frozen production score; hair-cell data are not included in that score)

**Scientific rationale**:
Usher syndrome affects retinal photoreceptors and cochlear hair cells. Genes enriched in these tissues may provide a tissue-relevance signal, but expression alone does not establish disease relevance.

**Key metrics**:

1. **Tau tissue specificity index (τ)**: Measures how uniformly a gene is expressed across tissues
   - τ = 0: Ubiquitous expression (housekeeping gene)
   - τ = 1: Highly tissue-specific
   - Formula: `τ = Σ(1 − xᵢ/x_max) / (n − 1)`

2. **Usher tissue enrichment**: Source-specific mean expression in the production target tissues (retina-related measures, cerebellum, and photoreceptors) relative to the relevant background. A ratio > 1 indicates enrichment in the selected target set; raw HPA, GTEx, and CELLxGENE units are not mixed directly.

**Scoring**:

```
expression_score = 0.4 × enrichment_percentile + 0.3 × τ_specificity + 0.3 × max_target_tissue_percentile
```

Percentile normalization is used to prevent absolute TPM values from dominating due to sequencing depth variation.

---

### 4. Subcellular Localization

**Biological question**: Does this protein localize to cilia, centrosomes, or basal bodies — structures implicated in Usher pathology?

**Data sources**:
- **HPA subcellular location data** — immunofluorescence microscopy
- **Cilia proteomics** — published mass spectrometry-based cilium proteome datasets (CiliaCarta, etc.)
- **Centrosome proteomics** — published centrosome/basal body proteome datasets

**Scientific rationale**:
Known Usher proteins (MYO7A, USH1C, CDH23, etc.) are ciliary or periciliary proteins. Localization to cilia, basal bodies, or centrosomes constitutes **strong mechanistic evidence** for involvement in ciliopathy pathways.

**Scoring**:

| Localization | Base Score |
|-------------|-----------|
| Cilia, centrosome, basal body, transition zone, stereocilia | 1.0 |
| Cytoskeleton, microtubules, cell junctions | 0.5 |
| Found in proteomics datasets only | 0.3 |
| Has localization data but no cilia association | 0.0 |
| No localization data available | NULL |

**Evidence weighting**:
- Experimental evidence (HPA Enhanced/Supported reliability; proteomics): × 1.0
- Computational prediction (HPA Approved/Uncertain reliability): × 0.6

```
localization_score = cilia_proximity_base_score × evidence_type_weight
```

---

### 5. Animal Model Phenotypes

**Biological question**: When orthologs of this gene are disrupted in mouse or zebrafish, do sensory or ciliary phenotypes result?

**Data sources**:
- **HCOP** (HUGO Gene Nomenclature Committee Ortholog Predictions) — human–mouse/human–zebrafish ortholog mapping
- **MGI** (Mouse Genome Informatics) — mouse knockout phenotypes (MP ontology)
- **ZFIN** (Zebrafish Information Network) — zebrafish mutant phenotypes
- **IMPC** (International Mouse Phenotyping Consortium) — systematic knockout screens

**Scientific rationale**:
Conservation of sensory phenotypes across species provides **functional validation**. Hearing and balance defects in mouse, and lateral line defects in zebrafish, recapitulate the pathological features of human Usher syndrome.

**Phenotype keyword filtering**:
- Mouse: hearing, vision, retina, photoreceptor, cochlea, stereocilia, cilia, vestibular, balance
- Zebrafish: hearing, ear, otic, otolith, lateral line, hair cell, retina, vision, eye

**Scoring**:

```
animal_model_score =
    0.4 × mouse_score × mouse_confidence +
    0.3 × zebrafish_score × zebrafish_confidence

Confidence weights: HIGH = 1.0, MEDIUM = 0.7, LOW = 0.4
Phenotype count scaling: log₂(sensory_phenotype_count + 1) / log₂(max_count + 1)

Mouse evidence combines MGI and IMPC into a single channel: IMPC data is
ingested into MGI via the shared Mammalian Phenotype ontology, so IMPC is
not scored as an independent source (this would double-count the same mouse
evidence). Distinct MP terms across MGI and IMPC are counted once; a gene
whose only mouse evidence comes from IMPC still counts as having a mouse
phenotype.
```

Logarithmic scaling prevents genes with excessive phenotype annotations from dominating rankings (diminishing returns).

---

### 6. Literature Mining

**Biological question**: Is this gene mentioned in the scientific literature in a cilia or sensory context, and what is the quality of that evidence?

**Data source**: NCBI PubMed (via E-utilities API)

**Scientific rationale**:
Literature evidence reflects accumulated scientific knowledge, but suffers from **study bias** — well-known genes (e.g., TP53, BRCA1) have massive publication counts regardless of cilia relevance. The normalization strategy in this layer specifically corrects for this bias.

**Evidence quality tiers**:

| Tier | Description | Weight |
|------|-------------|--------|
| direct_experimental | Gene knockout/mutation in cilia/sensory context | 1.0 |
| functional_mention | Cilia/sensory context with ≥3 publications | 0.6 |
| hts_hit | High-throughput screen hit in cilia/sensory context | 0.3 |
| incidental | Publications exist but no cilia/sensory context | 0.1 |
| none | No publications found | 0.0 |

**Study bias correction**:

```
raw_score = (context_score × quality_weight) / log₂(total_pubmed_count + 1)
literature_score = percentile_rank(raw_score)
```

The division by `log₂(total_pubmed_count)` is critical: a gene with 5 cilia-related papers out of 50 total will score higher than a gene with 5 cilia-related papers out of 100,000 total. This encourages the discovery of overlooked genes with suggestive evidence.

---

## Composite Scoring and Tiering

### Weighted Composite Score

The six evidence layers are combined into a single composite score using configurable weights:

| Evidence Layer | Default Weight | Biological Significance |
|----------------|---------------|------------------------|
| gnomAD Constraint | 20% | Functional essentiality of the gene |
| Tissue Expression | 20% | Specific expression in target tissues |
| Functional Annotation | 15% | Known functional characteristics |
| Subcellular Localization | 15% | Proximity to ciliary structures |
| Animal Models | 15% | Cross-species functional validation |
| Literature Mining | 15% | Cilia/sensory association in literature |

**NULL-aware weighted average**:

```
composite_score = Σ(scoreᵢ × weightᵢ) / Σ(weightᵢ)
                  ── only non-NULL layers contribute ──
```

Example: A gene with data in only gnomAD (0.8), expression (0.6), and localization (0.9):

```
composite_score = (0.8 × 0.20 + 0.6 × 0.20 + 0.9 × 0.15) / (0.20 + 0.20 + 0.15)
               = 0.415 / 0.55
               = 0.755
```

### Confidence Tiers

| Tier | Criteria | Interpretation |
|------|----------|----------------|
| **HIGH** | Composite score ≥ 0.7, ≥ 3 layers with data, and cilia-signal gate | Higher-priority computational hypothesis; requires independent experimental validation |
| **MEDIUM** | Composite score ≥ 0.4 and ≥ 2 layers with data | Moderate evidence; warrants further literature investigation |
| **LOW** | Composite score ≥ 0.2 | Weak evidence; additional data needed |
| EXCLUDED | Below LOW threshold | Excluded from candidate list |

### Quality Flags

| Flag | Criteria | Description |
|------|----------|-------------|
| sufficient_evidence | ≥ 4 layers with scores | Adequate data coverage |
| moderate_evidence | ≥ 2 layers with scores | Partial coverage |
| sparse_evidence | ≥ 1 layer with score | Sparse data |
| no_evidence | 0 layers with scores | No data available |

---

## Validation

The pipeline includes built-in internal control recovery diagnostics. These diagnostics do not establish clinical sensitivity or causal validity.

### Positive Control Gene Sets

1. **Established Usher genes** (9 genes): MYO7A, USH1C, CDH23, PCDH15, USH1G, USH2A, ADGRV1, WHRN, CLRN1. CIB2 is excluded because its historical USH1J assignment is disputed in current curation.
2. **SYSCILIA SCGS v2 core ciliary genes** (28 genes): IFT88, IFT140, BBS1, CEP290, RPGR, and others

### Validation Criteria

- Median percentile rank of the selected controls is monitored against a ≥75% top-quartile threshold
- Recall@10% is reported as a descriptive recovery metric; the final rerun achieved 59.5% and does not meet the former >70% screening target

These thresholds are diagnostic checks, not proof of clinical sensitivity or causal validity. Failure should trigger review of data versions and control definitions rather than automatic weight tuning.

---

## Output Files

All results are stored in the `data/report/` directory:

| File | Description | How to Use |
|------|-------------|-----------|
| `candidates.tsv` | Candidate gene list (tab-separated) | Open in Excel or any text editor |
| `candidates.parquet` | Same data in high-performance binary format | R: `arrow::read_parquet()`; Python: `polars.read_parquet()` |
| `score_distribution.png` | Score distribution histogram | Quick overview of overall distribution |
| `evidence_coverage.png` | Per-layer coverage chart | Identify which layers have best/worst coverage |
| `tier_distribution.png` | HIGH/MEDIUM/LOW proportion pie chart | Quick summary |
| `reproducibility.md` | Full provenance record (parameters, data versions, software) | Methods section / reproducibility |

### Column Descriptions for candidates.tsv

**Core columns**:
- `gene_id` — Ensembl Gene ID (e.g., ENSG00000154229)
- `gene_symbol` — HGNC gene symbol (e.g., MYO7A)
- `composite_score` — Composite score (0–1)
- `confidence_tier` — Confidence tier (HIGH / MEDIUM / LOW)
- `evidence_count` — Number of evidence layers with non-NULL scores (0–6)

**Per-layer scores** (0–1; NULL indicates no data available):
- `gnomad_score` — Constraint score
- `expression_score` — Expression specificity score
- `annotation_score` — Functional annotation score
- `localization_score` — Subcellular localization score
- `animal_model_score` — Animal model phenotype score
- `literature_score` — Literature evidence score

**Auxiliary columns**:
- `supporting_layers` — Layers with scores (e.g., `gnomad,expression,localization`)
- `evidence_gaps` — Layers with missing data
- `quality_flag` — Quality flag

---

## Configuration

The pipeline configuration file is located at `config/default.yaml`:

```yaml
# Data versions
versions:
  ensembl_release: 113
  ensembl_gene_source: annotation/Homo_sapiens.GRCh38.113.gtf.gz
  ensembl_gene_source_url: https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/Homo_sapiens.GRCh38.113.gtf.gz
  ensembl_gene_source_sha256: 62f1709b40e083ce9d4cdc64a86b5ffec2c5d5371434bb7095c74dc89079c466
  gnomad_version: v4.1
  gtex_version: v8
  hpa_version: "23.0"
  cellxgene_census_version: "2025-11-08"

# Scoring weights (adjustable; must sum to 1.0)
scoring:
  gnomad: 0.20
  expression: 0.20
  annotation: 0.15
  localization: 0.15
  animal_model: 0.15
  literature: 0.15

# API settings
api:
  rate_limit_per_second: 5
  max_retries: 5
  timeout_seconds: 30
```

To adjust weights (e.g., to place greater emphasis on tissue expression), modify the `scoring` section and re-run `usher-pipeline score` followed by `usher-pipeline report`.

---

## Known Limitations

| Limitation | Description | Impact |
|-----------|-------------|--------|
| GTEx v8 lacks retina tissue | "Eye - Retina" is not available in GTEx v8 | Retina expression data comes from HPA only |
| HPA gene symbol mismatch | HPA uses gene symbols while the pipeline keys on gene IDs | Some genes may lack HPA expression data |
| gnomAD transcript-level IDs | gnomAD uses transcript IDs rather than gene-level IDs | Some genes may produce NaN on JOIN |
| Literature mining speed | NCBI API rate limits; ~8 genes/minute | Full run requires considerable time; use API key for faster throughput |
| Single-writer constraint | DuckDB does not support concurrent writers | Do not run two pipeline steps simultaneously |
| Limited inner ear data | Bulk transcriptome data for human cochlear tissue is scarce and no CELLxGENE hair-cell query was included in the frozen production score | Cerebellum and photoreceptor data are used as production proxies; fetal cochlear data remain exploratory |
| Research-status inference | Missing annotation or publication is not evidence that a gene is genuinely understudied | Treat tiers as hypotheses requiring independent validation |

---

## Data Sources and References

This pipeline integrates the following public databases and tools:

- **gnomAD** v4.1 — Karczewski et al. (2020) *Nature* 581:434–443
- **Ensembl** release 113, GRCh38 GTF — frozen `Homo_sapiens.GRCh38.113.gtf.gz` source; SHA-256 is recorded in `config/default.yaml` and setup provenance
- **Human Protein Atlas** v23 — Uhlén et al. (2015) *Science* 347:1260419
- **GTEx** v8 — GTEx Consortium (2020) *Science* 369:1318–1330
- **CELLxGENE Census** `2025-11-08` — Chan Zuckerberg Initiative single-cell atlas build used in the frozen run
- **Gene Ontology** — Gene Ontology Consortium (2021) *Nucleic Acids Res* 49:D325–D334
- **UniProt** — UniProt Consortium (2023) *Nucleic Acids Res* 51:D523–D531
- **MGI** — Mouse Genome Informatics, The Jackson Laboratory
- **ZFIN** — Zebrafish Information Network
- **IMPC** — International Mouse Phenotyping Consortium
- **SYSCILIA SCGS v2** — van Dam et al. (2021) *Mol Biol Cell* 32:br6
- **mygene.info** — Xin et al. (2016) *Genome Biol* 17:91
- **NCBI E-utilities** — PubMed literature search API

---

## License

[AUTHOR ACTION REQUIRED: add a complete license file and state the intended license here before release.]

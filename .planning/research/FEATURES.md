# Feature Landscape

**Domain:** Gene Candidate Discovery and Prioritization for Rare Disease / Ciliopathy Research
**Researched:** 2026-02-11
**Confidence:** MEDIUM

## Table Stakes

Features users expect. Missing = pipeline is not credible.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-evidence scoring | Standard in modern gene prioritization; single-source approaches insufficient for rare disease | Medium | Requires weighting scheme, score normalization across evidence types |
| Reproducibility documentation | Required for publication and scientific validity; FDA/NIH standards emphasize reproducible pipelines | Low-Medium | Parameter logging, version tracking, seed control, execution environment capture |
| Data provenance tracking | W3C PROV standard; required to trace analysis steps and validate results | Medium | Track all data transformations, source versions, timestamps, intermediate results |
| Known gene validation | Benchmarking against established disease genes is standard practice; without this, no confidence in results | Low-Medium | Positive control set, recall metrics at various rank cutoffs (e.g., recall@10, recall@50) |
| Quality control checks | Standard for NGS and bioinformatics pipelines; catch data issues early | Low-Medium | Missing data detection, outlier identification, distribution checks, data completeness metrics |
| Structured output format | Machine-readable outputs enable downstream analysis and integration | Low | CSV/TSV for tabular data, JSON for metadata, standard column naming |
| Basic visualization | Visual inspection of scores, distributions, and rankings is expected | Medium | Score distribution plots, rank visualization, evidence contribution plots |
| Literature evidence | Gene function annotation incomplete; literature mining standard for discovery pipelines | High | PubMed/literature search integration, manual or automated; alternatively curated disease-gene databases |
| HPO/phenotype integration | Standard for rare disease gene prioritization since tools like Exomiser, LIRICAL | Medium | Human Phenotype Ontology term matching, phenotype similarity scoring if applicable |
| API-based data retrieval | Manual downloads don't scale; automated retrieval from gnomAD, UniProt, GTEx, etc. is expected | Medium | Rate limiting, error handling, caching, retry logic |
| Batch processing | Single-gene analysis doesn't scale to 20K genes | Low-Medium | Parallel execution, progress tracking, resume-from-checkpoint |
| Parameter configuration | Hard-coded parameters prevent adaptation; config files standard | Low | YAML/JSON config, CLI arguments, validation |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Explainable scoring | SHAP/attribution methods show WHY genes rank high; critical for discovery (not just diagnosis) | High | SHAP-style contribution analysis, per-gene evidence breakdown, visual explanations |
| Systematic under-annotation bias handling | Novel: most tools favor well-studied genes; correcting publication bias is research advantage | High | Annotation completeness score as evidence layer; downweight literature-heavy features for under-studied candidates |
| Cilia-specific knowledgebase integration | Leverage CilioGenics, CiliaMiner, ciliopathy databases for domain-focused scoring | Medium | Custom evidence layer; API/download from specialized databases |
| Sensitivity analysis | Systematic parameter tuning rare in discovery pipelines; shows robustness | Medium-High | Grid search or DoE-based parameter sweep; rank stability metrics across configs |
| Tiered output with rationale | Not just ranked list but grouped by confidence/evidence type; aids hypothesis generation | Low-Medium | Tier classification logic (e.g., high/medium/low confidence), evidence summary per tier |
| Multi-modal evidence weighting | Naive Bayesian integration or optimized weights outperform equal weighting | Medium | Weight optimization using known positive controls, cross-validation |
| Negative control validation | Test against known non-disease genes to assess specificity; rare in discovery pipelines | Low-Medium | Negative gene set (e.g., housekeeping genes), precision metrics |
| Evidence conflict detection | Flag genes with contradictory evidence (e.g., high expression but low constraint) | Medium | Rule-based or correlation-based conflict identification |
| Interactive HTML report | Modern tools (e.g., MultiQC-style) provide browsable results; better than static CSV | Medium | HTML generation, embedded plots, sortable tables, linked evidence |
| Incremental update capability | Re-run with new data sources without full recomputation | Medium-High | Modular pipeline, cached intermediate results, dependency tracking |
| Cross-species homology scoring | Animal model phenotypes critical for ciliopathy; ortholog-based evidence integration | Medium | DIOPT/OrthoDB integration, phenotype transfer from model organisms |
| Automated literature scanning with LLM | Emerging: LLM-based RAG for literature evidence extraction and validation | High | LLM API integration, prompt engineering, faithfulness checks, cost management |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real-time web dashboard | Overkill for research tool; adds deployment complexity, security concerns | Static HTML reports + CLI; Jupyter notebooks for interactive exploration if needed |
| GUI for parameter tuning | Research pipelines need reproducible command-line execution; GUIs hinder automation | YAML config files + CLI; document parameter rationale in config comments |
| Variant-level analysis | Out of scope for gene-level discovery; conflates discovery with diagnostic prioritization | Focus on gene-level evidence aggregation; refer users to Exomiser/LIRICAL for variant work |
| Custom alignment/variant calling | Well-solved problem; reinventing the wheel wastes time | Use standard BAM/VCF inputs from established pipelines; focus on gene prioritization logic |
| Social features (sharing, comments) | Research tool, not collaboration platform | File-based outputs (shareable via Git/email); documentation in README |
| Real-time database sync | Bioinformatics data versions change slowly; real-time sync unnecessary | Versioned data snapshots with documented download dates; update quarterly or as needed |
| One-click install for all dependencies | Bioinformatics tools have complex dependencies; false promise | Conda environment.yml or Docker container; document setup steps clearly |
| Machine learning model training | Small positive control set insufficient for robust ML; rule-based more transparent | Weighted scoring with manually tuned/optimized weights; reserve ML for future with larger training data |

## Feature Dependencies

```
Parameter Configuration
    └──requires──> Quality Control Checks
                      └──requires──> Data Provenance Tracking

Multi-Evidence Scoring
    ├──requires──> API-Based Data Retrieval
    ├──requires──> Literature Evidence
    └──requires──> Structured Output Format

Explainable Scoring
    └──requires──> Multi-Evidence Scoring
                      └──enhances──> Interactive HTML Report

Known Gene Validation
    └──requires──> Multi-Evidence Scoring
                      └──enables──> Sensitivity Analysis

Tiered Output with Rationale
    └──requires──> Explainable Scoring
                      └──enhances──> Interactive HTML Report

Batch Processing
    └──requires──> Parameter Configuration
                      └──enables──> Sensitivity Analysis

Negative Control Validation
    └──requires──> Known Gene Validation (uses similar metrics)

Evidence Conflict Detection
    └──requires──> Multi-Evidence Scoring

Incremental Update Capability
    └──requires──> Data Provenance Tracking
                      └──requires──> Batch Processing

Cross-Species Homology Scoring
    └──requires──> API-Based Data Retrieval

Automated Literature Scanning with LLM
    └──requires──> Literature Evidence
                      └──conflicts──> Manual curation (choose one approach per evidence layer)
```

### Dependency Notes

- **Parameter Configuration → QC Checks → Data Provenance:** Foundation stack; parameters must be logged, QC applied, and tracked before any analysis
- **Multi-Evidence Scoring requires API-Based Data Retrieval:** Can't score without data; retrieval must be robust and cached
- **Explainable Scoring requires Multi-Evidence Scoring:** Can't explain scores that don't exist; explanations decompose composite scores
- **Known Gene Validation enables Sensitivity Analysis:** Positive controls provide ground truth for parameter tuning
- **Automated Literature Scanning conflicts with Manual Curation:** Choose one approach per evidence layer to avoid redundancy and conflicting evidence

## MVP Recommendation

### Launch With (v1)

Minimum viable pipeline for ciliopathy gene discovery.

- [x] Multi-evidence scoring (6 layers: annotation, expression, sequence, localization, constraint, phenotype)
- [x] API-based data retrieval with caching (gnomAD, GTEx, HPA, UniProt, Model Organism DBs)
- [x] Known gene validation (Usher syndrome genes, known ciliopathy genes as positive controls)
- [x] Reproducibility documentation (parameter logging, versions, timestamps)
- [x] Data provenance tracking (source file versions, processing steps, intermediate results)
- [x] Structured output format (CSV with ranked genes, evidence scores per column)
- [x] Quality control checks (missing data detection, outlier flagging, distribution checks)
- [x] Batch processing (parallel execution across 20K genes)
- [x] Parameter configuration (YAML config for weights, thresholds, data sources)
- [x] Tiered output with rationale (High/Medium/Low confidence tiers, evidence summary)
- [x] Basic visualization (score distributions, top candidate plots)

**Rationale:** These features enable credible, reproducible gene prioritization at scale. Without validation, explainability, and QC, results are untrustworthy. Without tiered output, generating hypotheses from 20K genes is overwhelming.

### Add After Validation (v1.x)

Features to add once core pipeline is validated against known ciliopathy genes.

- [ ] Interactive HTML report (browsable results with sortable tables, linked evidence) — **Trigger:** After v1 produces validated candidate list; when sharing results with collaborators
- [ ] Explainable scoring (per-gene evidence contribution breakdown, SHAP-style attribution) — **Trigger:** After identifying novel candidates; when reviewers ask "why is this gene ranked high?"
- [ ] Negative control validation (test against housekeeping genes to assess specificity) — **Trigger:** After positive control validation succeeds; to quantify false positive rate
- [ ] Evidence conflict detection (flag genes with contradictory evidence patterns) — **Trigger:** After observing unexpected high-ranking genes; to catch data quality issues
- [ ] Sensitivity analysis (systematic parameter sweep, rank stability metrics) — **Trigger:** When preparing for publication; to demonstrate robustness
- [ ] Cross-species homology scoring (zebrafish/mouse phenotype evidence integration) — **Trigger:** If animal model evidence proves valuable in initial analysis

### Future Consideration (v2+)

Features to defer until core pipeline is published and validated.

- [ ] Automated literature scanning with LLM (RAG-based PubMed evidence extraction) — **Why defer:** High complexity, cost, and uncertainty; manual curation sufficient for initial discovery
- [ ] Incremental update capability (re-run with new data without full recomputation) — **Why defer:** Overkill for one-time discovery project; valuable if pipeline becomes ongoing surveillance tool
- [ ] Multi-modal evidence weighting optimization (Bayesian integration, cross-validation) — **Why defer:** Requires larger training set of known genes; manual weight tuning sufficient initially
- [ ] Systematic under-annotation bias handling — **Why defer:** Novel research question; defer until after initial discovery validates approach
- [ ] Cilia-specific knowledgebase integration (CilioGenics, CiliaMiner) — **Why defer:** Nice-to-have; primary evidence layers sufficient for initial analysis; add if reviewers request

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Multi-evidence scoring | HIGH | MEDIUM | P1 |
| Known gene validation | HIGH | LOW-MEDIUM | P1 |
| Reproducibility documentation | HIGH | LOW-MEDIUM | P1 |
| Data provenance tracking | HIGH | MEDIUM | P1 |
| Structured output format | HIGH | LOW | P1 |
| Quality control checks | HIGH | LOW-MEDIUM | P1 |
| API-based data retrieval | HIGH | MEDIUM | P1 |
| Batch processing | HIGH | LOW-MEDIUM | P1 |
| Parameter configuration | HIGH | LOW | P1 |
| Tiered output with rationale | HIGH | LOW-MEDIUM | P1 |
| Basic visualization | HIGH | MEDIUM | P1 |
| Explainable scoring | HIGH | HIGH | P2 |
| Interactive HTML report | MEDIUM | MEDIUM | P2 |
| Sensitivity analysis | MEDIUM | MEDIUM-HIGH | P2 |
| Evidence conflict detection | MEDIUM | MEDIUM | P2 |
| Negative control validation | MEDIUM | LOW-MEDIUM | P2 |
| Cross-species homology | MEDIUM | MEDIUM | P2 |
| Incremental updates | LOW | MEDIUM-HIGH | P3 |
| LLM literature scanning | LOW | HIGH | P3 |
| Multi-modal weight optimization | MEDIUM | MEDIUM | P3 |
| Under-annotation bias correction | MEDIUM | HIGH | P3 |
| Cilia knowledgebase integration | LOW-MEDIUM | MEDIUM | P3 |

**Priority key:**
- P1: Must have for credible v1 pipeline
- P2: Should have; add after v1 validation
- P3: Nice to have; future consideration

## Competitor Feature Analysis

| Feature | Exomiser | LIRICAL | CilioGenics Tool | Usher Pipeline Approach |
|---------|----------|---------|-------------------|------------------------|
| Multi-evidence scoring | Yes (variant+pheno combined score) | Yes (LR-based) | Yes (ML predictions) | Yes (6-layer weighted scoring) |
| Phenotype integration | HPO-based (strong) | HPO-based (strong) | Not primary | HPO-compatible but not required (sensory cilia focus) |
| Known gene validation | Benchmarked on Mendelian diseases | Benchmarked on Mendelian diseases | Validated on known cilia genes | Validate on Usher + known ciliopathy genes |
| Explainable scoring | Limited | Post-test probability (interpretable) | ML black box | SHAP-style per-gene evidence breakdown (planned P2) |
| Variant-level analysis | Primary focus | Primary focus | No (gene-level only) | No (out of scope; gene-level discovery) |
| Literature evidence | Automated (limited) | Limited | Text mining used in training | Manual/automated (planned P3) |
| Tiered output | Yes (rank-ordered) | Yes (post-test prob tiers) | Yes (confidence scores) | Yes (High/Medium/Low tiers + rationale) |
| Under-annotation bias | Not addressed | Not addressed | Not addressed | Explicitly addressed (novel) |
| Domain-specific focus | Mendelian disease diagnosis | Mendelian disease diagnosis | Cilia biology | Usher syndrome / ciliopathy discovery |
| Reproducibility | Config files, versions logged | Config files, versions logged | Not emphasized | Extensive provenance tracking |

**Key Differentiators for Usher Pipeline:**
1. **Discovery vs. Diagnosis:** Exomiser/LIRICAL prioritize variants in patient genomes (diagnosis); Usher pipeline screens all genes for under-studied candidates (discovery)
2. **Under-annotation bias handling:** Explicitly score annotation completeness and de-bias toward under-studied genes
3. **Explainable scoring for hypothesis generation:** Per-gene evidence breakdown to guide experimental follow-up, not just rank genes
4. **Sensory cilia focus:** Retina/cochlea expression, ciliopathy phenotypes, subcellular localization evidence tailored to Usher biology

## Sources

### Tool Features and Benchmarking
- [Survey and improvement strategies for gene prioritization with LLMs](https://academic.oup.com/bioinformaticsadvances/article/5/1/vbaf148/8172498) (2026)
- [Clinical and Cross-Domain Validation of LLM-Guided Gene Prioritization](https://www.biorxiv.org/content/10.64898/2026.01.22.701191v1) (2026)
- [Automating candidate gene prioritization with LLMs](https://academic.oup.com/bioinformatics/article/41/10/btaf541/8280402) (2025)
- [Explicable prioritization with rule-based and ML algorithms](https://pmc.ncbi.nlm.nih.gov/articles/PMC10956189/) (2024)
- [Phenotype-driven approaches to enhance variant prioritization](https://pmc.ncbi.nlm.nih.gov/articles/PMC9288531/) (2022)
- [Evaluation of phenotype-driven gene prioritization methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC9487604/) (2022)
- [Add LIRICAL and Exomiser scores to seqr (GitHub issue)](https://github.com/broadinstitute/seqr/issues/2742) (2021)
- [Large-scale benchmark of gene prioritization methods](https://www.nature.com/articles/srep46598) (2017)

### Reproducibility and Standards
- [Rare disease gene discovery in 100K Genomes Project](https://www.nature.com/articles/s41586-025-08623-w) (2025)
- [Standards for validating NGS bioinformatics pipelines (AMP/CAP)](https://www.sciencedirect.com/science/article/pii/S1525157817303732) (2018)
- [Genomics pipelines and data integration challenges](https://pmc.ncbi.nlm.nih.gov/articles/PMC5580401/) (2017)
- [Experiences with workflows for bioinformatics](https://link.springer.com/article/10.1186/s13062-015-0071-8) (2015)

### Parameter Tuning and Sensitivity Analysis
- [Algorithm sensitivity analysis for tissue segmentation pipelines](https://academic.oup.com/bioinformatics/article/33/7/1064/2843894) (2017)
- [doepipeline: systematic approach to optimizing workflows](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-019-3091-z) (2019)

### Multi-Evidence Integration
- [Multi-dimensional evidence-based candidate gene prioritization](https://pmc.ncbi.nlm.nih.gov/articles/PMC2752609/) (2009)
- [Extensive analysis of disease-gene associations with network integration](https://pmc.ncbi.nlm.nih.gov/articles/PMC4070077/) (2014)
- [Survey of gene prioritization tools for Mendelian diseases](https://pmc.ncbi.nlm.nih.gov/articles/PMC7074139/) (2020)

### Explainability and Interpretability
- [Explainable deep learning for cancer target prioritization](https://arxiv.org/html/2511.12463) (2024)
- [Interpretable machine learning for genomics](https://pmc.ncbi.nlm.nih.gov/articles/PMC8527313/) (2021)
- [SeqOne's DiagAI Score with xAI](https://www.seqone.com/news-insights/seqone-diagai-explainable-ai) (recent)
- [Spectrum of explainable and interpretable ML for genomics](https://wires.onlinelibrary.wiley.com/doi/10.1002/wics.1617) (2023)

### Cilia Biology and Ciliopathy Tools
- [Prioritization tool for cilia-associated genes](https://pmc.ncbi.nlm.nih.gov/articles/PMC11512102/) (2024)
- [CilioGenics: integrated method for predicting ciliary genes](https://academic.oup.com/nar/article/52/14/8127/7710917) (2024)
- [CiliaMiner: integrated database for ciliopathy genes](https://pmc.ncbi.nlm.nih.gov/articles/PMC10403755/) (2023)
- [Systems-biology approach to ciliopathy disorders](https://genomemedicine.biomedcentral.com/articles/10.1186/gm275) (2011)

### Visualization and Reporting
- [Computational pipeline for functional gene discovery](https://www.nature.com/articles/s41598-021-03041-0) (2021)
- [JWES: pipeline for gene-variant discovery and annotation](https://pmc.ncbi.nlm.nih.gov/articles/PMC8409305/) (2021)

### Data Quality and Provenance
- [Data quality assurance in bioinformatics](https://ranchobiosciences.com/2025/04/bioinformatics-and-quality-assurance-data/) (2025)
- [Bioinformatics pipeline for data quality control](https://www.meegle.com/en_us/topics/bioinformatics-pipeline/bioinformatics-pipeline-for-data-quality-control) (recent)
- [Bionitio: demonstrating best practices for bioinformatics CLI](https://academic.oup.com/gigascience/article/8/9/giz109/5572530) (2019)

---
*Feature research for: Bioinformatics Gene Candidate Discovery and Prioritization (Rare Disease / Ciliopathy)*
*Researched: 2026-02-11*
*Confidence: MEDIUM — based on WebSearch findings verified across multiple sources; Context7 not available for specialized bioinformatics tools; recommendations synthesized from peer-reviewed publications and established tool documentation*

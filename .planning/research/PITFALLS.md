# Domain Pitfalls: Bioinformatics Gene Prioritization for Cilia/Usher

**Domain:** Bioinformatics gene candidate discovery pipeline
**Researched:** 2026-02-11
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Gene ID Mapping Inconsistency Cascade

**What goes wrong:**
Gene identifiers fail to map correctly across databases (Ensembl, HGNC, UniProt, Entrez), resulting in data loss or incorrect merges. Over 51% of Ensembl IDs can return NA when converting to gene symbols, and approximately 8% discordance exists between Swiss-Prot and Ensembl. Multiple Ensembl IDs can map to a single Entrez ID, creating one-to-many relationships that break naively designed merge operations.

**Why it happens:**
- UniProt requires 100% sequence identity with no insertions/deletions for mapping to Ensembl, causing ~5% of well-annotated Swiss-Prot proteins to remain unmapped
- Gene symbols "shuffle around more haphazardly" than stable IDs, with the same symbol assigned to different genes across annotation builds
- Mucin-like proteins (e.g., MUC2, MUC19) with variable repeat regions have mismatches between curated sequences and reference genomes
- Different annotation build versions used across source databases

**How to avoid:**
1. **Use stable IDs as primary keys:** Store Ensembl gene IDs as the authoritative identifier; treat gene symbols as display-only metadata
2. **Version-lock annotation builds:** Document and freeze the Ensembl/GENCODE release used for all conversions; ensure GTEx expression data uses the same build
3. **Implement mapping validation:** After each ID conversion step, report the % successfully mapped and manually inspect unmapped high-priority genes
4. **One-to-many resolution strategy:** For multiple Ensembl→Entrez mappings, aggregate scores using max() or create separate records with explicit disambiguation
5. **Bypass problematic conversions:** Where possible, retrieve data directly using the native ID system of each source database rather than converting first

**Warning signs:**
- Sudden drop in gene counts after merging datasets
- Known positive control genes (established cilia/Usher genes) missing from integrated data
- Genes appearing multiple times with different scores after merge
- Different gene counts between pilot analysis and production run after database updates

**Phase to address:**
**Phase 1 (Data Infrastructure):** Establish ID mapping validation framework with explicit logging of conversion success rates. Create curated mapping tables with manual review of ambiguous cases.

---

### Pitfall 2: Literature Bias Amplification in Weighted Scoring

**What goes wrong:**
Well-studied genes dominate prioritization scores because multiple evidence layers correlate with publication volume rather than biological relevance. PubMed co-mentions, Gene Ontology annotation depth, pathway database coverage, and interaction network degree all increase with research attention, creating a reinforcing feedback loop that systematically deprioritizes novel candidates. In gene prioritization benchmarks, "the number of Gene Ontology annotations for a gene was significantly correlated with published disease-gene associations," reflecting research bias rather than actual biological importance.

**Why it happens:**
- Gene Ontology annotations are "created by curation of the scientific literature and typically only contain functional annotations for genes with published experimental data"
- Interaction networks derived from literature mining or yeast two-hybrid screens are biased toward well-studied proteins
- Pathway databases (KEGG, Reactome) provide richer annotations for canonical pathways vs. emerging biology
- Constraint metrics (gnomAD pLI/LOEUF) perform better for well-covered genes but may be unreliable for genes with low coverage
- Human genes "are much more likely to have been published on in the last 12 years if they are in clusters that were already well known"

**How to avoid:**
1. **Decouple publication metrics from functional evidence:** Score PubMed mentions separately from mechanistic evidence (protein domains, expression patterns, orthologs)
2. **Normalize for baseline research attention:** Divide pathway/GO scores by total publication count to create a "novelty-adjusted" functional score
3. **Use sequence-based features heavily:** Prioritize evidence types independent of literature (protein domains, tissue expression, evolutionary constraint, ortholog phenotypes)
4. **Set evidence diversity requirements:** Require candidates to score above threshold in at least N different evidence categories, preventing single-layer dominance
5. **Explicit "under-studied" bonus:** Add a scoring component that rewards genes with low PubMed counts but high biological plausibility from other layers
6. **Validate scoring against a "dark genome" test set:** Ensure low-publication genes with strong experimental validation (from model organisms) score appropriately

**Warning signs:**
- Top 100 candidates are all genes with >500 PubMed citations
- Known disease genes with <50 publications rank below 1,000th percentile
- Correlation coefficient >0.7 between final score and PubMed count
- When you add a new evidence layer, the top-ranked genes don't change
- Positive controls (known cilia genes) score lower than expected based on functional relevance

**Phase to address:**
**Phase 3 (Scoring System Design):** Implement multi-layer weighted scoring with explicit publication bias correction. Test scoring system on a stratified validation set including both well-studied and under-studied genes.

---

### Pitfall 3: Missing Data Handled as "Negative Evidence"

**What goes wrong:**
Genes lacking data in a particular evidence layer (e.g., no GTEx expression, no scRNA-seq detection, no IMPC phenotype) are treated as having "low expression" or "no phenotype" rather than "unknown." This systematically penalizes genes simply because they haven't been measured in the right contexts. For example, a gene expressed in rare retinal cell subtypes may be absent from bulk GTEx data and appear in only 1-2 cells per scRNA-seq atlas, leading to false classification as "not expressed in relevant tissues."

**Why it happens:**
- Default pandas merge behavior drops unmatched records or fills with NaN
- Scoring functions that sum across layers implicitly assign 0 to missing layers
- GTEx bulk tissue lacks resolution for rare cell types (e.g., photoreceptor subtypes, vestibular hair cells)
- scRNA-seq atlases have dropout and may not capture low-abundance transcripts
- Model organism phenotypes exist only for ~40% of human genes
- gnomAD constraint metrics are unreliable for genes with low coverage regions

**How to avoid:**
1. **Explicit missing data encoding:** Use a three-state system: "present" (data exists and positive), "absent" (data exists and negative), "unknown" (no data available)
2. **Layer-specific score normalization:** Compute scores only across layers with data; do not penalize genes for missing layers
3. **Imputation with biological priors:** For genes with orthologs but no direct human data, propagate evidence from mouse/zebrafish with confidence weighting
4. **Coverage-aware constraint metrics:** Only use gnomAD pLI/LOEUF when coverage is adequate (mean depth >30x and >90% of coding sequence covered)
5. **Aggregate at appropriate resolution:** For scRNA-seq, aggregate to cell-type level rather than individual cells to handle dropout
6. **Document data availability per gene:** Create a metadata field tracking which evidence layers are available for each gene to enable layer-aware filtering

**Warning signs:**
- Genes with partial data coverage systematically rank lower than genes with complete data
- Number of scored genes drops dramatically when adding a new evidence layer (should be union, not intersection)
- High-confidence candidates from preliminary analysis disappear after integrating additional databases
- Known Usher genes with tissue-specific expression patterns score poorly

**Phase to address:**
**Phase 2 (Data Integration):** Design merge strategy that preserves all genes and explicitly tracks data availability per evidence layer. Implement imputation strategy for ortholog-based evidence propagation.

---

### Pitfall 4: Batch Effects Misinterpreted as Biological Signal in scRNA-seq Integration

**What goes wrong:**
When integrating scRNA-seq data from multiple atlases (e.g., retinal atlas, inner ear atlas, nasal epithelium datasets), technical batch effects between studies are mistakenly interpreted as tissue-specific expression patterns. Methods that over-correct for batch effects can erase true biological variation, while under-correction leads to false cell-type-specific signals. Recent benchmarking shows "only 27% of integration outputs performed better than the best unintegrated data," and methods like LIGER, BBKNN, and Seurat v3 "tended to favor removal of batch effects over conservation of biological variation."

**Why it happens:**
- Different scRNA-seq platforms (10X Chromium vs. Smart-seq2 vs. single-nuclei) have systematically different detection profiles
- Batch effects arise from "cell isolation protocols, library preparation technology, and sequencing platforms"
- Integration algorithms make tradeoffs between removing technical variation vs. preserving biological differences
- "Increasing Kullback–Leibler divergence regularization does not improve integration and adversarial learning removes biological signals"
- Tissue-of-origin effects (primary tissue vs. organoid vs. cell culture) can be confounded with true cell-type identity

**How to avoid:**
1. **Validate integration quality:** After batch correction, verify that known marker genes still show expected cell-type-specific patterns
2. **Compare multiple integration methods:** Run Harmony, Seurat v5, and scVI in parallel; select based on preservation of positive control markers
3. **Use positive/negative control genes:** Ensure known cilia genes (IFT88, BBS1) show expected enrichment in ciliated cells post-integration
4. **Stratify by sequencing technology:** Analyze 10X datasets separately from Smart-seq2 before attempting cross-platform integration
5. **Prefer within-study comparisons:** When possible, compare cell types within the same study rather than integrating across studies
6. **Document integration parameters:** Record all batch correction hyperparameters (k-neighbors, PCA dimensions, integration strength) to enable sensitivity analysis

**Warning signs:**
- Cell types from different studies don't overlap in UMAP space after integration
- Marker genes lose cell-type-specificity after batch correction
- Technical replicates from the same study cluster separately after integration
- Integration method produces >50% improvement in batch-mixing metrics but known biological markers disappear

**Phase to address:**
**Phase 4 (scRNA-seq Processing):** Implement multi-method integration pipeline with positive control validation. Create cell-type-specific expression profiles only after validating preservation of known markers.

---

### Pitfall 5: Ortholog Function Conservation Over-Assumed

**What goes wrong:**
Phenotypes from mouse knockouts (MGI) or zebrafish morphants (ZFIN) are naively transferred to human genes as if function were perfectly conserved, ignoring cases where orthologs have "dramatically different functions." This is especially problematic for gene families with lineage-specific duplications or losses. The assumption that "single-copy orthologs are more reliable for functional annotation" is contradicted by evidence showing "multi-copy genes are equally or more likely to provide accurate functional information."

**Why it happens:**
- Automated orthology pipelines use sequence similarity thresholds without functional validation
- "Bidirectional best hit (BBH) assumption can be false because genes may be each other's highest-ranking matches due to differential gene loss"
- Domain recombination creates false orthology assignments where proteins share some but not all domains
- Zebrafish genome duplication means many human genes have two zebrafish co-orthologs with subfunctionalized roles
- "There is no universally applicable, unequivocal definition of conserved function"
- Cilia gene functions may diverge between motile (zebrafish) and non-motile/sensory (mammalian) cilia contexts

**How to avoid:**
1. **Confidence-weight ortholog evidence:** Use orthology confidence scores from databases (e.g., DIOPT scores, OMA groups) rather than binary ortholog/non-ortholog
2. **Require phenotype relevance:** Only count ortholog phenotypes that match the target biology (ciliary defects, sensory organ abnormalities, not generic lethality)
3. **Handle one-to-many orthologs explicitly:** For human genes with multiple zebrafish co-orthologs, aggregate phenotypes using OR logic (any co-ortholog with phenotype = positive evidence)
4. **Validate with synteny:** Prioritize orthologs supported by both sequence similarity and conserved genomic context
5. **Species-appropriate expectations:** Expect stronger conservation for cilia structure genes (IFT machinery) vs. sensory signaling cascades (tissue-specific)
6. **Cross-validate with multiple species:** Genes with convergent phenotypes across mouse, zebrafish, AND Drosophila are more reliable than single-species evidence

**Warning signs:**
- Ortholog evidence contradicts human genetic data (e.g., mouse knockout viable but human LoF variants cause disease)
- Large fraction of human genes map to paralogs in model organism rather than true orthologs
- Zebrafish co-orthologs have opposing phenotypes (one causes ciliopathy, other is wildtype)
- Synteny breaks detected for claimed ortholog pairs

**Phase to address:**
**Phase 2 (Data Integration - Ortholog Module):** Implement orthology confidence scoring and phenotype relevance filtering. Create manual curation workflow for ambiguous high-scoring candidates.

---

### Pitfall 6: Constraint Metrics (gnomAD pLI/LOEUF) Misinterpreted

**What goes wrong:**
gnomAD constraint scores are used as disease gene predictors without understanding their limitations. Researchers assume high pLI (>0.9) or low LOEUF (<0.35) automatically indicates dominant disease genes, but "even the most highly constrained genes are not necessarily autosomal dominant." Transcript selection errors cause dramatic score changes—SHANK2 has pLI=0 in the canonical transcript but pLI=1 in the brain-specific transcript due to differential exon usage. Low-coverage genes have unreliable constraint metrics but are not flagged.

**Why it happens:**
- pLI is dichotomous (>0.9 or <0.1), ignoring genes in the intermediate range
- LOEUF thresholds changed between gnomAD v2 (<0.35) and v4 (<0.6), causing confusion
- "There is no brain expression from over half the exons in the SHANK2 canonical transcript where most of the protein truncating variants are found"
- Genes with low sequencing coverage or high GC content have unreliable observed/expected ratios
- Recessive disease genes can have low constraint (heterozygous LoF is benign)
- Haploinsufficient genes vs. dominant-negative mechanisms are not distinguished

**How to avoid:**
1. **Use LOEUF continuously, not dichotomously:** Score genes on LOEUF scale rather than applying hard cutoffs; gives partial credit across the distribution
2. **Verify transcript selection:** For ciliopathy candidates, ensure the scored transcript includes exons expressed in retina/inner ear using GTEx isoform data
3. **Check coverage metrics:** Only use pLI/LOEUF when mean coverage >30x and >90% of CDS is covered in gnomAD
4. **Adjust expectations for inheritance pattern:** High constraint supports haploinsufficiency; moderate constraint is compatible with recessive inheritance (relevant for Usher syndrome)
5. **Cross-validate with ClinVar:** Check whether existing pathogenic variants in the gene match the constraint prediction
6. **Incorporate missense constraint:** Use gnomAD missense Z-scores alongside LoF metrics; some genes tolerate LoF but are missense-constrained

**Warning signs:**
- Candidate genes have low gnomAD coverage but constraint scores are used anyway
- All top candidates have pLI >0.9, despite Usher syndrome being recessive
- Constraint scores change dramatically when switching from canonical to tissue-specific transcript
- Genes with established recessive inheritance pattern are filtered out due to low constraint

**Phase to address:**
**Phase 3 (Scoring System Design - Constraint Module):** Implement coverage-aware constraint scoring with transcript validation. Create inheritance-pattern-adjusted weighting (lower weight for dominant constraint when prioritizing recessive disease genes).

---

### Pitfall 7: "Unknown Function" Operationally Undefined Creates Circular Logic

**What goes wrong:**
The pipeline aims to discover "under-studied" or "unknown function" genes but lacks a rigorous operational definition. If "unknown function" means "few PubMed papers," the literature bias pitfall is worsened. If it means "no GO annotations," it excludes genes with partial functional knowledge that might be excellent candidates. Approximately "40% of proteins in eukaryotic genomes are proteins of unknown function," but defining unknown is complex—"when a group of related sequences contains one or more members of known function, the similarity approach assigns all to the known space, whereas empirical approach distinguishes between characterized and uncharacterized candidates."

**Why it happens:**
- GO term coverage is publication-biased; "52-79% of bacterial proteomes can be functionally annotated based on homology searches" but eukaryotes have more uncharacterized proteins
- Partial functional knowledge exists on a spectrum (domain predictions, general pathway assignments, no mechanistic details)
- "Research bias, as measured by publication volume, was an important factor influencing genome annotation completeness"
- Negative selection (excluding known cilia genes) requires defining "known," which is database- and date-dependent

**How to avoid:**
1. **Multi-tier functional classification:**
   - Tier 1: Direct experimental evidence of cilia/Usher involvement (exclude from discovery)
   - Tier 2: Strong functional prediction (domains, orthologs) but no direct evidence (high-priority targets)
   - Tier 3: Minimal functional annotation (under-studied candidates)
   - Tier 4: No annotation beyond gene symbol (true unknowns)
2. **Explicit positive control exclusion list:** Maintain a curated list of ~200 known cilia genes and established Usher genes to exclude; version-control this list
3. **Publication-independent functional metrics:** Define "unknown" using absence of experimental GO evidence codes (EXP, IDA, IPI, IMP), not total publication count
4. **Pathway coverage threshold:** Consider genes "known" if they appear in >3 canonical cilia pathways (IFT, transition zone, basal body assembly)
5. **Temporal versioning:** Tag genes as "unknown as of [date]" to allow retrospective validation when new discoveries are published

**Warning signs:**
- Definition of "unknown" changes between pilot and production runs
- Candidates include genes with extensive literature on cilia-related functions
- Positive control genes leak into discovery set due to incomplete exclusion list
- Different team members have conflicting intuitions about whether a gene is "known enough" to exclude

**Phase to address:**
**Phase 1 (Data Infrastructure - Annotation Module):** Create explicit functional classification schema with clear inclusion/exclusion criteria. Build curated positive control list with literature provenance.

---

### Pitfall 8: Reproducibility Theater Without Computational Environment Control

**What goes wrong:**
Pipeline scripts are version-controlled and documented, creating an illusion of reproducibility, but results cannot be reproduced due to uncontrolled dependencies. Python package versions (pandas, numpy, scikit-learn), database snapshots (Ensembl release, gnomAD version, GTEx v8 vs v9), and API response changes cause silent result drift. "Workflow managers were developed in response to challenges with data complexity and reproducibility" but are often not adopted until after initial analyses are complete and results have diverged.

**Why it happens:**
- `pip install package` without pinning versions installs latest release, which may change behavior
- Ensembl/NCBI/UniProt databases update continuously; API calls return different data over time
- Downloaded files are not checksummed; corruption or incomplete downloads go undetected
- Reference genome versions (GRCh37 vs GRCh38) are mixed across data sources
- RAM/disk caching causes results to differ between first run and subsequent runs
- Random seeds not set for stochastic algorithms (UMAP, t-SNE, subsampling)

**How to avoid:**
1. **Pin all dependencies:** Use `requirements.txt` with exact versions (`pandas==2.0.3` not `pandas>=2.0`) or `conda env export`
2. **Containerize the environment:** Build Docker/Singularity container with frozen versions; run all analyses inside container
3. **Snapshot external databases:** Download full database dumps (Ensembl, GTEx) with version tags; do not rely on live API queries for production runs
4. **Checksum all downloaded data:** Compute and store MD5/SHA256 hashes for every downloaded file; verify on load
5. **Version-control intermediate outputs:** Store preprocessed data files (post-QC, post-normalization) with version tags to enable restart from checkpoints
6. **Set random seeds globally:** Fix numpy/torch/random seeds at the start of every script to ensure stochastic steps are reproducible
7. **Log provenance metadata:** Embed database versions, software versions, and run parameters in output files using JSON headers or HDF5 attributes

**Warning signs:**
- Results change when re-running the same script on a different machine
- Collaborator cannot reproduce your gene rankings despite using "the same code"
- Adding a new analysis step changes results from previous steps (should be impossible if truly modular)
- You cannot explain why the gene count changed between last month's and this month's runs

**Phase to address:**
**Phase 1 (Data Infrastructure):** Establish containerized environment with pinned dependencies and database version snapshots. Implement checksumming and provenance logging from the start.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hard-code database API URLs in scripts | Quick to write | Breaks when APIs change; no version control | Never—use config file |
| Convert all IDs to gene symbols early | Simpler to read outputs | Loses ability to trace back to source; mapping errors propagate | Only for final display, never internal processing |
| Filter to protein-coding genes only, drop non-coding | Reduces dataset size | Misses lncRNAs with cilia-regulatory roles | Acceptable for MVP if explicitly documented as limitation |
| Use default merge (inner join) in pandas | Fewer rows to process | Silent data loss when IDs don't match | Never—always left join with explicit logging |
| Skip validation on positive control genes | Faster iteration | No way to detect when scoring system breaks | Never—positive controls are mandatory |
| Download data via API calls in main pipeline | No manual download step | Irreproducible; results change as databases update | Only during exploration phase, never production |
| Store intermediate data as CSV | Easy to inspect manually | Loss of data types (ints become floats); no metadata storage | Acceptable for small tables <10K rows |
| Use `pip install --upgrade` to fix bugs | Gets latest fixes | Introduces breaking changes unpredictably | Never—pin versions and upgrade explicitly |
| Aggregate to gene-level immediately from scRNA-seq | Simpler analysis | Loses cell-type resolution; can't detect subtype-specific expression | Only for bulk comparison, not prioritization |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Ensembl BioMart | Selecting canonical transcript only; miss tissue-specific isoforms | Query all transcripts, then filter by retina/inner ear expression using GTEx |
| gnomAD API | Not checking coverage per gene before using constraint scores | Filter to genes with mean_depth >30x and >90% CDS covered |
| GTEx Portal | Using TPM directly without accounting for sample size per tissue | Normalize by sample count and use median TPM across replicates |
| CellxGene API | Downloading full h5ad files serially (slow, memory-intensive) | Use CellxGene's API to fetch only cell-type-aggregated counts for genes of interest |
| UniProt REST API | Converting gene lists one-by-one in a loop | Use batch endpoint with POST requests (up to 100K IDs per request) |
| PubMed E-utilities | Sending requests without API key (3 req/sec limit) | Register NCBI API key for 10 req/sec; still implement exponential backoff |
| MGI/ZFIN batch queries | Assuming 1:1 human-mouse orthology | Handle one-to-many mappings explicitly (use highest-confidence ortholog or aggregate) |
| IMPC phenotype API | Taking all phenotypes as equally informative | Filter to cilia-relevant phenotypes (MP:0003935 cilium; HP:0000508 retinal degeneration) |
| String-DB | Assuming all edges are physical interactions | Filter by interaction type (text-mining vs experimental) and confidence score >0.7 |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading entire scRNA-seq h5ad into memory | Script crashes with MemoryError | Use backed mode (`anndata.read_h5ad(file, backed='r')`) to stream from disk | >5GB file or <32GB RAM |
| Nested loops for gene-gene comparisons | Script runs for hours | Vectorize with numpy/pandas; use scipy.spatial.distance for pairwise | >1K genes |
| Re-downloading data on every run | Slow iteration, API rate limits | Cache downloaded files locally with checksums; only re-download if missing | Always implement caching |
| Storing all intermediate results in memory | Cannot debug failed runs | Write intermediate outputs to disk after each major step | >50K genes or complex pipeline |
| Single-threaded processing | Slow on large gene sets | Parallelize with joblib/multiprocessing for embarrassingly parallel tasks | >10K genes or >1hr runtime |
| Not indexing database tables | Slow queries on merged datasets | Create indexes on ID columns (Ensembl ID, HGNC symbol) before joins | >20K genes or >5 tables |

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Data download (Phase 1) | API rate limits hit during batch download | Implement exponential backoff and retry logic; use NCBI API keys |
| ID mapping (Phase 1) | Multiple IDs map to the same symbol | Create explicit disambiguation strategy; log all many-to-one mappings |
| scRNA-seq integration (Phase 4) | Batch effects erase biological signal | Validate integration by checking known marker genes before/after |
| Scoring system (Phase 3) | Literature bias dominates scores | Normalize by publication count; validate on under-studied positive controls |
| Validation (Phase 5) | Positive controls not scoring as expected | Debug scoring system before declaring it ready; iterate on weights |
| Reproducibility (All phases) | Results differ between runs | Pin dependency versions and database snapshots from Phase 1 |
| Missing data handling (Phase 2) | Genes with incomplete data rank artificially low | Implement layer-aware scoring that doesn't penalize missing data |
| Ortholog phenotypes (Phase 2) | Mouse/zebrafish phenotypes over-interpreted | Require phenotype relevance filtering (cilia-related only) |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **ID mapping module:** Often missing validation step to ensure known genes are successfully mapped—verify 100% of positive control genes map successfully
- [ ] **Scoring system:** Often missing publication bias correction—verify correlation between final score and PubMed count is <0.5
- [ ] **scRNA-seq integration:** Often missing positive control validation—verify known cilia genes show expected cell-type enrichment post-integration
- [ ] **Constraint metrics:** Often missing coverage check—verify genes have adequate gnomAD coverage before using pLI/LOEUF
- [ ] **Ortholog evidence:** Often missing confidence scoring—verify orthology confidence scores are used, not just binary ortholog calls
- [ ] **Data provenance:** Often missing version logging—verify every output file records database versions and software versions used
- [ ] **Missing data handling:** Often missing explicit "unknown" state—verify merge strategy preserves genes with partial data
- [ ] **Reproducibility:** Often missing checksums on downloaded data—verify MD5 hashes are computed and stored for all external data files
- [ ] **Positive controls:** Often missing negative control validation—verify negative controls (non-cilia genes) score appropriately low
- [ ] **API error handling:** Often missing retry logic—verify exponential backoff is implemented for all external API calls

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| ID mapping errors detected late | LOW | Re-run mapping module with corrected conversion tables; propagate fixes forward |
| Literature bias discovered after scoring | MEDIUM | Add publication normalization to scoring function; re-compute all scores |
| Batch effects in scRNA-seq integration | MEDIUM | Try alternative integration method (switch from Seurat to Harmony); re-validate |
| Missing data treated as negative | HIGH | Redesign merge strategy to preserve all genes; re-run entire integration pipeline |
| Reproducibility failure (cannot re-run) | HIGH | Containerize environment; snapshot databases; document and re-run from scratch |
| Positive controls score poorly | MEDIUM | Debug scoring function weights; validate on stratified test set; adjust weights iteratively |
| Ortholog function over-assumed | LOW | Add orthology confidence scores; re-filter to high-confidence orthologs only |
| Constraint metrics misinterpreted | LOW | Add coverage check; use LOEUF continuously instead of dichotomous; re-score |
| "Unknown function" poorly defined | MEDIUM | Create explicit functional tiers; rebuild positive control exclusion list; re-classify |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Gene ID mapping inconsistency | Phase 1: Data Infrastructure | 100% of positive controls successfully mapped across all databases |
| Literature bias amplification | Phase 3: Scoring System | Correlation(final_score, pubmed_count) < 0.5; under-studied positive controls rank in top 10% |
| Missing data as negative evidence | Phase 2: Data Integration | Gene count preserved after merges (should be union, not intersection); explicit "unknown" state in data model |
| scRNA-seq batch effects | Phase 4: scRNA-seq Processing | Known cilia markers show expected cell-type specificity post-integration |
| Ortholog function over-assumed | Phase 2: Ortholog Module | Orthology confidence scores used; phenotype relevance filtering applied |
| Constraint metrics misinterpreted | Phase 3: Constraint Module | Coverage-aware filtering; LOEUF used continuously; transcript validation performed |
| "Unknown function" undefined | Phase 1: Annotation Module | Explicit functional tiers defined; positive control exclusion list version-controlled |
| Reproducibility failure | Phase 1: Environment Setup | Containerized; dependencies pinned; databases snapshotted; results bit-identical on re-run |
| API rate limits hit | Phase 1: Data Download | Retry logic with exponential backoff; batch queries used; NCBI API key registered |

---

## Sources

### Gene ID Mapping
- [How to map all Ensembl IDs to Gene Symbols (Bioconductor)](https://support.bioconductor.org/p/87454/)
- [UniProt genomic mapping for deciphering functional effects of missense variants - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC6563471/)
- [Comparing HGNC Symbol Mappings by 3 Different Databases](https://www.ffli.dev/posts/2021-07-11-comparing-hgnc-symbol-mappings-by-3-different-databases/)

### Literature Bias and Gene Annotation
- [Gene annotation bias impedes biomedical research | Scientific Reports](https://www.nature.com/articles/s41598-018-19333-x)
- [Annotating Genes of Known and Unknown Function by Large-Scale Coexpression Analysis - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2330292/)
- [An assessment of genome annotation coverage across the bacterial tree of life - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7200070/)
- [Functional unknomics: Systematic screening of conserved genes of unknown function | PLOS Biology](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3002222)

### Multi-Database Integration and Missing Data
- [Missing data in multi-omics integration: Recent advances through artificial intelligence - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9949722/)
- [Handling missing rows in multi-omics data integration: Multiple imputation in multiple factor analysis framework | BMC Bioinformatics](https://link.springer.com/article/10.1186/s12859-016-1273-5)
- [A technical review of multi-omics data integration methods: from classical statistical to deep generative approaches - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12315550/)

### Weighted Scoring Systems
- [IW-Scoring: an Integrative Weighted Scoring framework for annotating and prioritizing genetic variations in the noncoding genome - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC5934661/)
- [A large-scale benchmark of gene prioritization methods | Scientific Reports](https://www.nature.com/articles/srep46598)

### Gene Prioritization and LLM Biases
- [Survey and improvement strategies for gene prioritization with large language models | Bioinformatics Advances](https://academic.oup.com/bioinformaticsadvances/article/5/1/vbaf148/8172498)
- [Automating candidate gene prioritization with large language models | Bioinformatics](https://academic.oup.com/bioinformatics/article/41/10/btaf541/8280402)
- [What Are The Most Common Stupid Mistakes In Bioinformatics?](https://www.biostars.org/p/7126/)

### scRNA-seq Integration and Batch Effects
- [Integrating single-cell RNA-seq datasets with substantial batch effects | BMC Genomics](https://link.springer.com/article/10.1186/s12864-025-12126-3)
- [Batch correction methods used in single-cell RNA sequencing analyses are often poorly calibrated - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12315870/)
- [Benchmarking atlas-level data integration in single-cell genomics | Nature Methods](https://www.nature.com/articles/s41592-021-01336-8)
- [Benchmarking cross-species single-cell RNA-seq data integration methods | Nucleic Acids Research](https://academic.oup.com/nar/article/53/1/gkae1316/7945393)

### Rare Disease Gene Discovery and Validation
- [Rare disease gene association discovery in the 100,000 Genomes Project | Nature](https://www.nature.com/articles/s41586-025-08623-w)
- [ClinPrior: an algorithm for diagnosis and novel gene discovery by network-based prioritization | Genome Medicine](https://genomemedicine.biomedcentral.com/articles/10.1186/s13073-023-01214-2)
- [Strategies to Uplift Novel Mendelian Gene Discovery for Improved Clinical Outcomes | Frontiers](https://www.frontiersin.org/journals/genetics/articles/10.3389/fgene.2021.674295/full)

### Reproducible Bioinformatics Pipelines
- [The five pillars of computational reproducibility: bioinformatics and beyond - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10591307/)
- [Reproducible, scalable, and shareable analysis pipelines with bioinformatics workflow managers | Nature Methods](https://www.nature.com/articles/s41592-021-01254-9)
- [Developing and reusing bioinformatics data analysis pipelines using scientific workflow systems - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10030817/)
- [Investigating reproducibility and tracking provenance – A genomic workflow case study | BMC Bioinformatics](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/s12859-017-1747-0)

### Cilia Gene Discovery and Ciliopathy Prioritization
- [A prioritization tool for cilia-associated genes and their in vivo resources unveils new avenues for ciliopathy research - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11512102/)
- [CilioGenics: an integrated method and database for predicting novel ciliary genes | bioRxiv](https://www.biorxiv.org/content/10.1101/2023.03.31.535034v1.full)

### Usher Syndrome Gene Discovery
- [Usher Syndrome: Genetics and Molecular Links of Hearing Loss | Frontiers](https://www.frontiersin.org/journals/genetics/articles/10.3389/fgene.2020.565216/full)
- [The genetic and phenotypic landscapes of Usher syndrome | Human Genetics](https://link.springer.com/article/10.1007/s00439-022-02448-7)
- [Usher Syndrome: Genetics of a Human Ciliopathy - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8268283/)
- [Usher Syndrome: Genetics of a Human Ciliopathy | MDPI](https://www.mdpi.com/1422-0067/22/13/6723)

### gnomAD Constraint Metrics
- [gnomAD v4.0 Gene Constraint | gnomAD browser](https://gnomad.broadinstitute.org/news/2024-03-gnomad-v4-0-gene-constraint/)
- [Gene constraint and genotype-phenotype correlations in neurodevelopmental disorders - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10340126/)
- [No preferential mode of inheritance for highly constrained genes - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8898387/)
- [Variant interpretation using population databases: Lessons from gnomAD - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9160216/)

### API Rate Limits and Batch Download
- [How to avoid NCBI API rate limits? | LifeSciencesHub](https://www.lifescienceshub.ai/guides/how-to-avoid-ncbi-api-rate-limits-step-by-step-guide)
- [Batch retrieval & ID mapping | UniProt](https://www.ebi.ac.uk/training/online/courses/uniprot-exploring-protein-sequence-and-functional-info/how-to-use-uniprot-tools-clone/batch-retrieval-id-mapping/)
- [UniProt website API documentation](https://www.uniprot.org/api-documentation/:definition)
- [The UniProt website API: facilitating programmatic access to protein knowledge - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12230682/)

### Ortholog Inference and Limitations
- [Functional and evolutionary implications of gene orthology | Nature Reviews Genetics](https://www.nature.com/articles/nrg3456)
- [Testing the Ortholog Conjecture with Comparative Functional Genomic Data from Mammals | PLOS Computational Biology](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1002073)
- [Standardized benchmarking in the quest for orthologs | Nature Methods](https://www.nature.com/articles/nmeth.3830)
- [Getting Started in Gene Orthology and Functional Analysis - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC2845645/)

### Tissue Specificity and Cell Type Deconvolution
- [Cellular deconvolution of GTEx tissues powers discovery of disease and cell-type associated regulatory variants | Nature Communications](https://www.nature.com/articles/s41467-020-14561-0)
- [TransTEx: novel tissue-specificity scoring method | Bioinformatics](https://academic.oup.com/bioinformatics/article/40/8/btae475/7731001)
- [Comprehensive evaluation of deconvolution methods for human brain gene expression | Nature Communications](https://www.nature.com/articles/s41467-022-28655-4)

### PubMed Literature Mining
- [Text Mining Genotype-Phenotype Relationships from Biomedical Literature | PLOS Computational Biology](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005017)
- [GLAD4U: deriving and prioritizing gene lists from PubMed literature | BMC Genomics](https://bmcgenomics.biomedcentral.com/articles/10.1186/1471-2164-13-S8-S20)
- [Mining experimental evidence of molecular function claims from the literature - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3041023/)

---

*Pitfalls research for: Bioinformatics Gene Candidate Discovery Pipeline for Cilia/Usher Syndrome*
*Researched: 2026-02-11*
*Confidence: HIGH (validated with 40+ authoritative sources across all risk domains)*

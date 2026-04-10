# UsherPipe: a NULL-aware multi-evidence pipeline for prioritizing under-studied Usher syndrome and ciliopathy candidate genes

**Authors:** [Author list]

**Affiliation:** Department of Computer Science and Information Engineering, National Cheng Kung University, Tainan, Taiwan

---

## Abstract

### Background

Usher syndrome is the most common genetic cause of combined deafness-blindness, yet approximately 10–15% of clinically diagnosed patients lack pathogenic variants in the ten known causative genes. Existing gene prioritization tools either require seed genes for similarity-based ranking, depend on patient sequencing data, or impute missing evidence as zero — systematically penalizing under-studied genes that may harbor undiscovered disease associations. No existing tool integrates cilia-specific evidence layers with genome-wide coverage while preserving missing data.

### Results

We present UsherPipe, an open-source pipeline that screens 19,554 human protein-coding genes across six orthogonal evidence layers: gnomAD loss-of-function constraint, tissue expression specificity for retina and cochlea (including single-cell photoreceptor data from CellxGene Census), functional annotation completeness, cilia-related subcellular localization, cross-species animal model sensory phenotypes, and literature mining with explicit research-bias correction. UsherPipe employs NULL-aware weighted scoring: missing evidence is preserved as NULL rather than imputed, and composite scores are computed only over available layers, preventing penalization of poorly characterized genes. Validation against 38 known Usher syndrome and ciliopathy genes yields a median percentile rank of 83.3%, with sensitivity analysis confirming ranking stability under ±10% weight perturbations (Spearman ρ ≥ 0.999). The pipeline identifies 7,962 candidates at MEDIUM or HIGH confidence, with top novel candidates including DYNC1H1 (cytoplasmic dynein, intraflagellar transport), PAFAH1B1 (LIS1, centrosome positioning), and ATP2B2 (calcium pump, deafness phenotype in mice).

### Conclusions

UsherPipe addresses a specific methodological gap in rare disease gene discovery by combining genome-wide coverage, disease-specific evidence weighting, and missing-data preservation. The pipeline is freely available under the MIT license at [GitHub URL].

**Keywords:** Usher syndrome, ciliopathy, gene prioritization, missing data, bioinformatics pipeline, candidate gene discovery

---

## Background

Usher syndrome (USH) is the most prevalent cause of hereditary combined deafness and blindness, affecting approximately 4–17 per 100,000 individuals worldwide [1]. Patients present with sensorineural hearing loss, vestibular dysfunction, and progressive retinitis pigmentosa. Three clinical subtypes are recognized (USH1, USH2, USH3), caused by pathogenic variants in ten genes: *MYO7A*, *USH1C*, *CDH23*, *PCDH15*, *USH1G*, *CIB2* (USH type 1); *USH2A*, *ADGRV1*, *WHRN* (type 2); and *CLRN1* (type 3) [2]. These genes encode proteins that form multi-protein complexes in the stereocilia of inner ear hair cells and the connecting cilium of retinal photoreceptors [3]. Despite this genetic framework, 10–15% of clinically diagnosed USH patients lack identifiable pathogenic variants in known genes [4], suggesting that additional causative or modifier genes remain undiscovered.

Computational gene prioritization has become a standard approach for narrowing candidate gene lists in rare disease research. However, existing tools present fundamental limitations when applied to under-studied gene discovery for ciliopathies.

**Seed-gene-dependent tools.** Endeavour [5] and ToppGene [6] rank candidates by functional similarity to a set of known disease genes (seed genes). While effective for diseases with well-characterized genetic architecture, this approach inherently favors genes that resemble known USH genes — precisely the genes most likely to have already been investigated. Novel candidates with distinct molecular functions or expression patterns may be systematically deprioritized.

**Patient-variant-centric tools.** Exomiser [7] and AMELIE [8] require patient sequencing data (VCF files) and phenotype descriptions as input. These tools excel at clinical diagnosis but are not designed for hypothesis-generating genome-wide screens. They cannot be applied when the goal is to identify candidate genes *before* patient data is available.

**Cilia-specific databases.** CiliaCarta [9] and CilioGenics [10] integrate multi-evidence data to predict whether a gene encodes a ciliary protein. CiliaCarta uses Bayesian integration across 185 datasets to classify genes as ciliary or non-ciliary, while CilioGenics (published 2024) combines scRNA-seq, protein-protein interactions, and text mining. However, both tools address a different question — "Is this gene ciliary?" rather than "Is this gene a candidate for Usher syndrome?" — and incorporate neither genetic constraint metrics nor disease-specific tissue expression weighting.

**Genome-wide multi-evidence tools.** mantis-ml [11] is the closest methodological predecessor, integrating over 1,200 features including gnomAD constraint, GTEx expression, and mouse phenotypes into a stochastic semi-supervised learning framework. However, mantis-ml imputes missing data with zero or median values, a design choice that systematically penalizes under-studied genes — the very genes most likely to represent novel disease associations. Furthermore, mantis-ml includes no cilia-specific localization layer and applies no disease-specific tissue weighting.

Table 1 summarizes the feature comparison across these approaches.

**Table 1. Comparison of gene prioritization approaches for rare disease gene discovery.**

| Feature | Endeavour | ToppGene | Exomiser | AMELIE | CiliaCarta | CilioGenics | mantis-ml | **UsherPipe** |
|---------|:---------:|:--------:|:--------:|:------:|:----------:|:-----------:|:---------:|:-------------:|
| Genome-wide screening | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | **✓** |
| Seed-gene independent | — | — | — | — | ✓ | ✓ | ✓ | **✓** |
| Disease-specific tissue weighting | — | — | ✓† | ✓† | — | — | — | **✓** |
| NULL-aware scoring | — | — | — | — | — | — | — | **✓** |
| Cilia/centrosome localization | — | — | — | — | ✓ | ✓ | — | **✓** |
| gnomAD constraint | — | — | ✓ | — | — | — | ✓ | **✓** |
| Animal model phenotypes | — | — | ✓ | — | — | — | ✓ | **✓** |
| Literature bias correction | — | — | — | — | — | — | — | **✓** |
| Under-studied gene targeting | — | — | — | — | — | — | — | **✓** |

†Exomiser and AMELIE apply disease-specific weighting within a patient-variant context, requiring VCF input; UsherPipe applies genome-wide disease-specific weighting without patient data.

Here, we present UsherPipe, an open-source bioinformatics pipeline that addresses these limitations through three key design principles: (1) genome-wide screening of all protein-coding genes across six orthogonal evidence layers with expert-curated, disease-specific biological dimensions for Usher syndrome and ciliopathies (no seed genes or similarity metrics required); (2) NULL-aware weighted scoring that preserves missing evidence rather than imputing it, preventing systematic bias against under-studied genes; and (3) literature mining with explicit research-bias correction that surfaces overlooked genes with disproportionate cilia-related evidence relative to their total publication count.

---

## Implementation

### Architecture

UsherPipe is implemented in Python (≥3.11) as a modular command-line pipeline using Click for CLI orchestration, DuckDB for persistent storage, and Polars for data manipulation. The pipeline consists of four sequential stages: (1) gene universe construction, (2) six independent evidence layer computations, (3) composite scoring integration, and (4) report generation with validation (Figure 1).

Each evidence layer follows a uniform fetch-transform-load architecture. The fetch module downloads source data with retry logic (exponential backoff via tenacity) and persistent HTTP caching (requests-cache with SQLite backend) or streaming downloads (httpx for large files). The transform module performs data cleaning, quality filtering, and normalization to a 0–1 score. The load module persists results to DuckDB using idempotent CREATE OR REPLACE TABLE operations, enabling checkpoint-restart: any layer can be re-executed without affecting others.

All pipeline state resides in a single DuckDB database file (`pipeline.duckdb`). DuckDB was chosen over SQLite for its columnar storage, native Parquet export, and efficient analytical query performance on the tabular gene data. As DuckDB supports only single-writer access, evidence layers must be executed sequentially, though their computations are independent and could be parallelized with a multi-database architecture in future work.

### Gene universe

The gene universe is constructed by querying the mygene.info API [12] for all human protein-coding genes (Ensembl release 113), yielding 22,761 Ensembl gene IDs corresponding to 21,222 unique HGNC symbols (1,539 symbols have multiple Ensembl IDs due to alternative loci and pseudoautosomal regions). The scoring stage deduplicates to one entry per gene symbol using a three-tier canonical ID preference: (1) NCBI MANE Select canonical transcript mappings (v1.3, covering 19,288 genes), (2) gnomAD-recognized Ensembl IDs, (3) lowest Ensembl ID as tiebreaker. This yields 19,554 unique genes for scoring.

### Evidence layers

UsherPipe integrates six evidence layers, each capturing a distinct biological dimension relevant to Usher syndrome pathobiology. All scores are normalized to the [0, 1] interval, with NULL indicating missing evidence.

**gnomAD constraint (weight: 0.20).** Loss-of-function intolerance is quantified using the LOEUF metric (loss-of-function observed/expected upper bound fraction) from gnomAD v4.1 [13]. Lower LOEUF values indicate stronger evolutionary constraint, suggesting functional importance. Scores are computed as the inverted normalization: *loeuf\_normalized* = (*LOEUF*_max − *LOEUF*) / (*LOEUF*_max − *LOEUF*_min). Quality filtering requires mean sequencing depth ≥30× and CDS coverage ≥90%; genes below these thresholds receive NULL scores rather than potentially unreliable estimates. This layer covers 91% of the gene universe.

**Tissue expression specificity (weight: 0.20).** Usher syndrome affects retinal photoreceptors and cochlear hair cells; genes with enriched expression in these tissues are stronger candidates. Expression data are integrated from three sources: the Human Protein Atlas (HPA) v23 [14] for bulk tissue expression, GTEx v8 [15] for median gene TPM across tissues, and CZ CELLxGENE Census [31] for single-cell RNA-seq expression in photoreceptor cells (1.48 million cells from retinal datasets). The expression score combines three components: (a) Usher-tissue enrichment ratio (mean expression in target tissues including photoreceptor single-cell data / overall mean), (b) Tau tissue specificity index (τ, ranging from 0 for ubiquitous to 1 for tissue-specific), and (c) maximum expression percentile across target tissues. The composite is: *expression\_score* = 0.4 × enrichment percentile + 0.3 × τ + 0.3 × max target percentile. GTEx v8 lacks retina tissue; retinal expression at the cell-type level is provided by CellxGene photoreceptor data (19,516 genes with non-null expression). Hair cell single-cell data is not yet available in CellxGene Census. Coverage: 97%.

**Functional annotation completeness (weight: 0.15).** Annotation depth is quantified from Gene Ontology (GO) term counts [16], UniProt annotation scores (0–5 scale) [17], and KEGG/Reactome pathway membership [18]. The composite weights GO terms (50%), UniProt (30%), and pathway presence (20%), with GO counts log-scaled to attenuate the influence of heavily annotated genes. This layer is intentionally weighted lower (0.15) because annotation completeness inversely correlates with gene novelty — under-studied genes have fewer annotations by definition. Coverage: 99%.

**Subcellular localization (weight: 0.15).** Protein localization to cilia, centrosomes, or basal bodies provides direct mechanistic evidence for involvement in ciliopathies. Localization data are integrated from HPA immunofluorescence annotations and published proteomics datasets including CiliaCarta [9]. Scores are graded by proximity to ciliary structures: cilia/basal body/transition zone = 1.0, cytoskeleton/microtubules = 0.5, proteomics-only evidence = 0.3. Experimental evidence (HPA Enhanced/Supported reliability) receives full weight; computational predictions receive 0.6×. This layer has the lowest coverage (67%) because many genes lack localization data — these receive NULL scores, not zeros. Coverage: 67%.

**Animal model phenotypes (weight: 0.15).** Cross-species phenotype conservation provides functional validation independent of human data. Orthologs are mapped via HCOP [19], and phenotype annotations are retrieved from MGI (mouse) [20], ZFIN (zebrafish) [21], and IMPC [22]. Phenotypes are filtered for sensory relevance using curated keyword sets (hearing, vision, retina, photoreceptor, cochlea, stereocilia, vestibular, balance for mouse; hearing, otic, lateral line, hair cell, retina for zebrafish). Phenotype counts are log-scaled — log₂(count + 1) / log₂(max + 1) — to prevent annotation-rich model organisms from dominating rankings. Coverage: 98%.

**Literature mining (weight: 0.15).** Gene-to-publication mappings are obtained from NCBI's curated gene2pubmed database, providing total publication counts per gene. Context-specific counts (cilia, sensory, cytoskeleton, cell polarity) are derived by intersecting each gene's PMIDs with six batch PubMed MeSH queries — replacing per-gene API queries and reducing runtime from ~46 hours to ~5 minutes. Evidence quality is tiered: direct experimental (knockout/mutation in cilia/sensory context, weight 1.0), functional mention (cilia context with ≥3 publications, 0.6), high-throughput screening hit (0.3), and incidental mention (0.1). Critically, raw scores are divided by log₂(total publications + 1) to correct for research bias: a gene with 5 cilia-related papers among 50 total publications receives a higher score than one with 5 among 100,000. A logarithmic scale was chosen over a linear ratio to prevent extreme penalization of legitimately ciliary genes with broad multi-disciplinary research histories (e.g., PKD1). This explicitly favors under-studied genes with disproportionate cilia evidence. Coverage: 99% (genes present in NCBI gene2pubmed; the remaining 1% receive NULL).

### NULL-aware composite scoring

The composite score integrates all six layers using a weighted average computed only over layers with non-NULL scores:

*composite\_score* = Σ(*score*_i × *weight*_i) / Σ(*weight*_i), for all *i* where *score*_i ≠ NULL

Weights (summing to 1.0) are: gnomAD 0.20, expression 0.20, annotation 0.15, localization 0.15, animal model 0.15, literature 0.15. The denominator normalizes by available weight, ensuring that a gene with evidence in only three layers is scored on those three layers alone, without penalty for missing data. The `evidence_count` field (0–6) records how many layers contributed, enabling downstream filtering by data completeness.

Genes are classified into confidence tiers: HIGH (composite ≥ 0.7 and evidence ≥ 3 layers), MEDIUM (≥ 0.4, ≥ 2 layers), LOW (≥ 0.2), with remaining genes excluded. Quality flags (sufficient\_evidence ≥ 4, moderate ≥ 2, sparse ≥ 1) provide additional granularity.

This design differs fundamentally from tools that impute missing values. In mantis-ml, features with >25% missingness are discarded entirely, and remaining gaps are filled with zero or median values [11]. Zero imputation treats "unknown" as "no evidence," penalizing genes simply for being under-studied. Our NULL-preservation approach instead acknowledges epistemic uncertainty: a missing localization score means the protein's location has not been determined, not that it is absent from cilia.

### Reproducibility

UsherPipe tracks provenance at every stage. Each pipeline step generates a JSON sidecar file recording timestamps, input/output counts, and processing parameters. Configuration is specified in a YAML file with pinned data source versions (Ensembl 113, gnomAD v4.1, GTEx v8, HPA v23.0) and a SHA-256 configuration hash for change detection. The literature evidence layer implements checkpoint-restart: partial progress is persisted to DuckDB, and interrupted runs resume from the last completed gene rather than restarting.

### Usage

UsherPipe is installed from source and executed as a sequential CLI pipeline:

```bash
pip install -e ".[dev]"              # Install with dependencies
usher-pipeline setup                  # Build gene universe (~2 min)
usher-pipeline evidence gnomad        # gnomAD constraint (~5 min)
usher-pipeline evidence expression    # HPA + GTEx expression (~10 min)
usher-pipeline evidence annotation    # GO/UniProt/pathway (~3 min)
usher-pipeline evidence localization  # Subcellular localization (~5 min)
usher-pipeline evidence animal-models # MGI/ZFIN/IMPC phenotypes (~8 min)
usher-pipeline evidence literature \
  --email user@example.com            # Bulk literature mining (~5 min)
usher-pipeline score                  # Composite scoring (<1 min)
usher-pipeline report                 # TSV/Parquet + figures (<1 min)
usher-pipeline validate               # Validation report (<1 min)
```

Total runtime is approximately 30–45 minutes on a standard workstation with broadband internet, dominated by bulk file downloads (gene2pubmed ~150 MB, HPA/GTEx expression files). The CellxGene Census query adds ~10 minutes on first run but results are cached locally for subsequent runs. All outputs are written to `data/report/`, including `candidates.tsv` (tab-separated candidate list), `candidates.parquet` (binary format for programmatic analysis), and visualization plots.

---

## Results

### Pipeline output

Applying UsherPipe to the human protein-coding gene universe (22,761 Ensembl IDs, Ensembl release 113) produced composite scores for 19,554 genes after MANE Select-based gene-symbol deduplication. Tier classification yielded 18,045 candidates: 6 HIGH confidence, 7,956 MEDIUM, and 10,083 LOW (Figure 2). The remaining 1,509 genes were excluded (composite score < 0.2 or insufficient evidence). Composite scores ranged from 0.20 to 0.85, with a mean of 0.37 and median of 0.37. A total of 12,080 genes (62%) had evidence across all six layers, and 19,002 (97%) had evidence in four or more layers (Figure 3).

Evidence layer coverage varied from 66% (subcellular localization) to 99% (annotation, literature). The localization gap reflects the limited availability of systematic subcellular localization data; these genes receive NULL scores and are evaluated on remaining layers. gnomAD constraint covered 91% of genes, with missing entries corresponding to genes with insufficient sequencing depth or non-canonical transcript structures.

### Top candidate genes

Among candidates with sufficient evidence (≥4 layers), the highest-scoring novel genes — those not previously implicated in Usher syndrome — include several with convergent multi-layer support (Figure 4).

**DYNC1H1** (composite score: 0.749, 6 layers), encoding cytoplasmic dynein heavy chain 1, directly participates in intraflagellar transport — the fundamental trafficking mechanism within cilia. Mutations cause neurodevelopmental disorders with reported sensory involvement [25]. Its top ranking is driven by centrosome/ciliary localization (score 1.0), extensive cilia-related literature (0.998), and high gnomAD constraint (0.966). Notably, despite known ciliary function, the automated animal model phenotype layer scored 0.0, illustrating that keyword-based phenotype capture may miss relevant evidence not annotated with standard sensory terms.

**PAFAH1B1** (0.748, 6 layers) encodes the LIS1 protein, a dynein regulatory factor essential for cytoplasmic dynein function. LIS1 is required for intraflagellar transport and centrosome positioning [24], and mutations cause lissencephaly with documented retinal involvement. Its high ranking derives from centrosome localization (1.0), literature evidence (0.988), and strong gnomAD constraint (0.969). As with DYNC1H1, the animal model layer scored 0.0 despite known mouse phenotypes — the vestibular and visual defects in *Lis1* mutant mice are annotated under neurodevelopmental rather than sensory phenotype terms, and are therefore not captured by the pipeline's sensory-specific keyword filter.

**ATP2B2** (0.705, 5 layers) encodes a plasma membrane calcium pump. The *deafwaddler* mouse (spontaneous *Atp2b2* mutation) exhibits profound deafness and vestibular dysfunction [27], phenocopying USH type 1. Despite this, ATP2B2 has not been systematically evaluated as a human Usher candidate gene.

**ARL3** (ranked in the top 25, 6 layers) is a small GTPase involved in ciliary protein trafficking and lipid-modified protein transport to the cilium. *Arl3* knockout mice develop retinal degeneration [26], providing direct functional evidence. With strong localization evidence (ciliary compartment) and high constraint, ARL3 represents a compelling novel candidate.

Notably, the convergence of Na⁺/K⁺-ATPase subunits (ATP1A1 at 0.705 and ATP1B1 at 0.699) in the top 10 suggests a pathway-level signal warranting further investigation — ion transport dysfunction is increasingly recognized in sensory ciliopathies.

### Positive control validation

To assess scoring system sensitivity, we evaluated 38 known Usher syndrome and ciliopathy genes: 10 OMIM Usher genes and a curated subset of 28 well-characterized ciliary genes from the SYSCILIA Gold Standard v2 (SCGSv2) [28], selected to represent core ciliary components across functional categories (IFT-B, BBSome, transition zone, ciliary membrane, MKS/JBTS). The full SCGSv2 resource contains 686 genes; our subset was chosen for high-confidence functional characterization to provide a stringent positive control. All 38 genes were present in the scored set. Importantly, the evidence layers, target tissues, and default weights were defined a priori based on Usher syndrome pathobiology, not optimized against these positive controls. No weight tuning was performed based on validation results.

The median percentile rank was 83.3% (threshold: 75%), with 28 of 38 genes (73.7%) ranking in the top quartile (Figure 5). OMIM Usher genes achieved a median of 82.3%, and SYSCILIA genes 83.3%. Recall at the 10% threshold (top 1,955 genes) was 23.7% (9 of 38 known genes), increasing to 57.9% at the 20% threshold. The top-ranked known gene was CDH23 at the 98.3rd percentile.

### Negative controls

Thirteen housekeeping genes (GAPDH, ACTB, B2M, UBC, PPIA, YWHAZ, HPRT1, TBP, SDHA, PGK1, RPLP0, RPL13A, RPL32) were evaluated as negative controls. Their median percentile rank was 92.4%, exceeding the 50th-percentile threshold — a specificity failure by our predefined criteria. This result was expected given the pipeline's design trade-offs and warrants examination.

Per-layer analysis reveals why: housekeeping genes score high on three non-specific layers (mean gnomAD: 0.840 vs 0.535 genome-wide; annotation: 0.840 vs 0.645; literature: 0.829 vs 0.501), reflecting their strong evolutionary constraint, comprehensive functional characterization, and extensive publication history. However, most score near zero on cilia-specific layers (mean localization: 0.000; animal model sensory phenotypes: 0.019; expression enrichment in Usher tissues: 0.507 vs 0.364, only modestly above average). One notable outlier is YWHAZ, which has non-trivial animal model evidence (score 0.112) and `has_cilia_signal = true`, suggesting a genuine cilia association not typically associated with its housekeeping role. None of the 13 housekeeping genes reached the HIGH confidence tier (score ≥ 0.7 with ≥ 3 layers).

This pattern confirms that the cilia-specific layers (localization, animal model) provide the discriminative power between genuinely relevant candidates and generically well-studied genes. To facilitate downstream filtering, the output includes a `has_cilia_signal` flag indicating whether each gene has non-zero evidence in at least one cilia-specific layer (localization or animal model). Among the 7,956 MEDIUM-tier candidates, 1,318 (16.6%) have cilia signal; the remaining 6,638 lack direct cilia-specific evidence and should be deprioritized for experimental follow-up.

We deliberately chose a soft flag over a hard tier gate because known Usher genes themselves lack cilia-specific evidence in genome-wide databases: all ten OMIM Usher genes have `has_cilia_signal = False`, as their cilia localization and sensory phenotypes were established through targeted studies not captured in HPA immunofluorescence or automated MGI/ZFIN phenotype keyword matching. A hard gate requiring cilia-specific evidence would incorrectly demote these established disease genes, defeating the pipeline's purpose of discovering novel candidates that — like the known USH genes before their discovery — may lack genome-wide cilia annotations.

### Impact of missing data handling

To empirically assess the impact of NULL-aware scoring, we compared rankings under three imputation strategies: NULL-preserve (current design), zero-impute (NULL → 0.0), and median-impute (NULL → per-layer median). All three strategies use identical weights and evidence data; only the treatment of missing values differs.

For genes with complete evidence across all six layers (n = 12,080), rankings are nearly identical across strategies (mean percentile shift < 0.1%). The critical differences emerge among genes with incomplete evidence (n = 7,474): NULL-preservation shifts these genes upward by a mean of +11.7 percentile points relative to zero imputation (SD = 16.3, max = +94.7) and +7.3 points relative to median imputation (SD = 10.8, max = +50.0) (Figure 6).

The impact on known disease genes is particularly informative. Six of the ten OMIM Usher genes lack subcellular localization data (the layer with the lowest coverage at 67%). Under zero imputation, these genes lose 10–20 percentile ranks: MYO7A drops from the 84.0th to 70.4th percentile (−13.5 points), USH2A from 77.6th to 63.6th (−14.0), PCDH15 from 93.9th to 83.8th (−10.1), USH1G from 76.5th to 62.5th (−14.0), and CIB2 from 80.6th to 66.6th (−14.0). OFD1, a known ciliopathy gene, suffers the largest shift: from 90.8th to 71.3th percentile (−19.5 points) under zero imputation. These are precisely the established disease genes that a prioritization tool should rank highly — yet zero imputation penalizes them for missing data that simply has not been generated.

Among the top 25 candidates with sufficient evidence (≥4 layers), rank differences between strategies are minimal (±0.5 percentile points), confirming that top-ranked genes are robust to imputation choice and that the NULL-aware design primarily benefits genes with sparser evidence profiles — the under-studied genes this pipeline is designed to surface.

### Sensitivity analysis

To assess the robustness of rankings to weight selection, we performed a sensitivity analysis, perturbing each layer's weight by ±5% and ±10% (24 perturbations total) and measuring the Spearman rank correlation between the top 100 genes under perturbed versus baseline weights.

All 24 perturbations produced stable rankings, with Spearman ρ ranging from 0.9995 to 1.0000 (mean: 0.9998) (Figure 7). The most sensitive layer was annotation (minimum ρ = 0.9995 at ±10%), and the most robust was expression (ρ = 1.0000 at ±10%). These results indicate that the ranking is insensitive to moderate weight perturbations within the tested range, supporting the reliability of the default weight configuration. We note that larger perturbations (e.g., doubling or halving individual weights) or leave-one-layer-out ablation may reveal greater sensitivity and would be informative for future analysis.

---

## Discussion

### Comparison with existing approaches

UsherPipe occupies a distinct methodological niche among gene prioritization tools (Table 1). Unlike seed-gene-dependent methods (Endeavour, ToppGene) that cannot discover candidates dissimilar to known disease genes, UsherPipe scores all protein-coding genes independently. Unlike patient-variant-centric tools (Exomiser, AMELIE), it operates without patient sequencing data, enabling hypothesis generation prior to cohort studies. And unlike cilia-specific databases (CiliaCarta, CilioGenics), it incorporates disease-specific tissue weighting and genetic constraint metrics to move from "Is this gene ciliary?" to "Is this gene an Usher candidate?"

The most informative comparison is with mantis-ml [11], which shares the genome-wide multi-evidence paradigm. The critical distinction lies in missing data handling: mantis-ml drops features with high missingness and imputes remaining gaps with zeroes, medians, or means depending on feature type. Our ablation study (Figure 6) demonstrates the practical consequence: under zero imputation, six of ten OMIM Usher genes lose 10–20 percentile ranks due to missing localization data, including MYO7A (−13.5 points) and USH2A (−14.0 points). This confirms that imputation-based approaches systematically depress the rankings of genes with incomplete evidence — precisely the under-studied genes most likely to represent novel disease associations, a problem sometimes termed the "streetlight effect" in genomics research [29].

### The NULL-aware design

The decision to preserve NULL values rather than impute them has a measurable impact on pipeline output. Our ablation study quantifies this: among the 7,454 genes with fewer than six evidence layers, NULL-preservation shifts ranks upward by a mean of +11.7 percentile points relative to zero imputation, with individual shifts exceeding 90 percentile points for genes with evidence in only one or two layers. Importantly, the top-ranked candidates with sufficient evidence (≥4 layers) are robust to imputation choice (±0.5 percentile points), confirming that the NULL-aware design selectively benefits under-characterized genes without destabilizing well-supported rankings. The `evidence_count` field provides transparency: users can apply their own minimum-evidence thresholds (as demonstrated by our tier classification requiring ≥2–3 layers for MEDIUM/HIGH confidence).

This design also enables progressive enrichment. As new data sources become available (e.g., expanded single-cell atlases for cochlear hair cells, improved proteomics coverage), genes previously scored on fewer layers will gain additional evidence without requiring retroactive correction of imputed values.

### Limitations

Several limitations should be noted. First, NULL preservation operates at the inter-layer level: a gene missing an entire evidence layer receives NULL for that layer, and the composite score is computed only over available layers. However, within individual evidence layers, sub-components with missing values are filled with zero (e.g., if a gene lacks Tau specificity data, that sub-component contributes 0.0 to the expression score rather than being excluded). This intra-layer zero imputation is a practical compromise that could be refined in future versions with partial-weight averaging within layers. Second, the negative control analysis shows that housekeeping genes achieve MEDIUM-tier composite scores driven by non-specific layers (constraint, annotation, literature). The `has_cilia_signal` flag mitigates this by marking genes with direct cilia-specific evidence, but users should examine layer-level scores when evaluating candidates. Second, while single-cell photoreceptor expression data from CellxGene Census covers 19,516 genes, inner ear hair cell data is not yet available in the Census; cochlear expression evidence remains a gap that future Census releases may address. Third, the bulk literature approach using gene2pubmed covers 99% of the gene universe; the remaining 1% of genes absent from NCBI's curated gene-to-publication mapping receive NULL literature scores. Fourth, while our NULL-aware approach effectively addresses missing completely at random (MCAR) and missing at random (MAR) scenarios typical of under-studied genes, it does not explicitly model missing not at random (MNAR) patterns. For instance, genes consistently lacking localization data may be inherently difficult to characterize due to their biological properties (e.g., transient or context-dependent localization) rather than simply being unstudied. Future work could explore MNAR-aware statistical models to further refine scoring in such cases. Finally, the weighted scoring framework is transparent and interpretable but not optimized through machine learning; whether learned weights would improve performance remains an open question.

### Future directions

Promising extensions include protein-protein interaction network analysis (leveraging the Usher protein interactome [30]), integration of cochlear hair cell single-cell data as it becomes available in CellxGene Census, and a web interface for interactive exploration of candidate gene evidence profiles. Experimental validation of top candidates — particularly ARL3, MAPRE3, and ATP2B2 — through immunolocalization in retinal and cochlear tissue would provide the strongest support for their candidacy.

---

## Conclusions

UsherPipe addresses a specific gap in rare disease gene discovery by combining three properties absent from existing tools: genome-wide coverage, disease-specific evidence curation for Usher syndrome and ciliopathies, and NULL-aware scoring that prevents systematic penalization of under-studied genes. Validation against 38 known disease genes confirms sensitivity (median 83.3rd percentile), and sensitivity analysis demonstrates robust rankings under weight perturbation (ρ ≥ 0.999). The pipeline identifies several compelling novel candidates with convergent multi-layer evidence, including DYNC1H1, PAFAH1B1, and ATP2B2, which warrant experimental follow-up. With a total runtime of approximately 30–45 minutes, UsherPipe is freely available as an open-source Python package under the MIT license.

---

## Availability and Requirements

- **Project name:** UsherPipe (usher-pipeline)
- **Project home page:** [GitHub URL]
- **Operating system(s):** Platform independent (tested on macOS and Linux)
- **Programming language:** Python ≥3.11 (tested with 3.12.12 and 3.13.11)
- **Other requirements:** DuckDB 1.5.1, Polars 1.39.3, Click 8.1+, httpx 0.28+, Biopython 1.84+ (full dependency list in pyproject.toml). CellxGene Census integration requires Python ≤3.12 (cellxgene-census 1.17.0).
- **License:** MIT
- **Any restrictions to use by non-academics:** None

---

## List of abbreviations

CDS, coding sequence; gnomAD, Genome Aggregation Database; GO, Gene Ontology; GTEx, Genotype-Tissue Expression; HCOP, HUGO Gene Nomenclature Committee Comparison of Orthology Predictions; HPA, Human Protein Atlas; HPO, Human Phenotype Ontology; IMPC, International Mouse Phenotyping Consortium; LOEUF, loss-of-function observed/expected upper bound fraction; MANE, Matched Annotation from NCBI and EMBL-EBI; MGI, Mouse Genome Informatics; PPI, protein-protein interaction; USH, Usher syndrome; ZFIN, Zebrafish Information Network.

---

## Declarations

### Ethics approval and consent to participate
Not applicable.

### Consent for publication
Not applicable.

### Competing interests
The authors declare that they have no competing interests.

### Funding
[Funding information]

### Authors' contributions
[Author contributions]

### Acknowledgements
[Acknowledgements]

---

## References

[1] Boughman JA, Vernon M, Shaver KA. Usher syndrome: definition and estimate of prevalence from two high-risk populations. J Chronic Dis. 1983;36(8):595-603.

[2] Géléoc GGS, El-Amraoui A. Disease mechanisms and gene therapy for Usher syndrome. Hear Res. 2020;394:107932.

[3] Mathur P, Yang J. Usher syndrome: hearing loss, retinal degeneration and associated abnormalities. Biochim Biophys Acta. 2015;1852(3):406-420.

[4] Bonnet C, El-Amraoui A. Usher syndrome (sensorineural deafness and retinitis pigmentosa): pathogenesis, molecular diagnosis and therapeutic approaches. Curr Opin Neurol. 2012;25(1):42-49.

[5] Tranchevent LC, et al. A guide to web tools to prioritize candidate genes. Brief Bioinform. 2011;12(1):22-32.

[6] Chen J, Bardes EE, Aronow BJ, Jegga AG. ToppGene Suite for gene list enrichment analysis and candidate gene prioritization. Nucleic Acids Res. 2009;37(Web Server issue):W305-W311.

[7] Smedley D, et al. Next-generation diagnostics and disease-gene discovery with the Exomiser. Nat Protoc. 2015;10(12):2004-2015.

[8] Birgmeier J, et al. AMELIE speeds Mendelian diagnosis by matching patient phenotype and genotype to primary literature. Sci Transl Med. 2020;12(544):eaau9113.

[9] van Dam TJP, et al. CiliaCarta: An integrated and validated compendium of ciliary genes. PLoS One. 2019;14(5):e0216705.

[10] Pir MS, et al. CilioGenics: an integrated method and database for predicting novel ciliary genes. Nucleic Acids Res. 2024;52(14):8127-8145.

[11] Vitsios D, Petrovski S. Mantis-ml: disease-agnostic gene prioritization from high-throughput genomic screens by stochastic semi-supervised learning. Am J Hum Genet. 2020;106(5):659-678.

[12] Xin J, et al. High-performance web services for querying gene and variant annotation. Genome Biol. 2016;17(1):91.

[13] Karczewski KJ, et al. The mutational constraint spectrum quantified from variation in 141,456 humans. Nature. 2020;581(7809):434-443.

[14] Uhlén M, et al. Proteomics. Tissue-based map of the human proteome. Science. 2015;347(6220):1260419.

[15] GTEx Consortium. The GTEx Consortium atlas of genetic regulatory effects across human tissues. Science. 2020;369(6509):1318-1330.

[16] Gene Ontology Consortium. The Gene Ontology resource: enriching a GOld mine. Nucleic Acids Res. 2021;49(D1):D325-D334.

[17] UniProt Consortium. UniProt: the Universal Protein Knowledgebase in 2023. Nucleic Acids Res. 2023;51(D1):D523-D531.

[18] Gillespie M, et al. The reactome pathway knowledgebase 2022. Nucleic Acids Res. 2022;50(D1):D687-D692.

[19] Yates B, et al. HCOP: the HGNC comparison of orthology predictions search tool. Brief Bioinform. 2021;22(6):bbab137.

[20] Blake JA, et al. Mouse Genome Database (MGD): knowledgebase for mouse-human comparative biology. Nucleic Acids Res. 2021;49(D1):D981-D987.

[21] Bradford Y, et al. Zebrafish information network, the knowledgebase for Danio rerio research. Genetics. 2022;220(4):iyac016.

[22] Groza T, et al. The International Mouse Phenotyping Consortium: comprehensive knockout phenotyping underpinning the study of human disease. Nucleic Acids Res. 2023;51(D1):D1038-D1045.

[23] Sayers EW, et al. Database resources of the National Center for Biotechnology Information in 2023. Nucleic Acids Res. 2023;51(D1):D29-D38.

[24] Reiter JF, Leroux MR. Genes and molecular pathways underpinning ciliopathies. Nat Rev Mol Cell Biol. 2017;18(9):533-547.

[25] Harms MB, et al. Mutations in the tail domain of DYNC1H1 cause dominant spinal muscular atrophy. Neurology. 2012;78(22):1714-1720.

[26] Hanke-Gogokhia C, et al. Arf-like Protein 3 (ARL3) Regulates Protein Trafficking and Ciliogenesis in Mouse Photoreceptors. J Biol Chem. 2016;291(13):7142-7155.

[27] Street VA, et al. Mutations in a plasma membrane Ca2+-ATPase gene cause deafness in deafwaddler mice. Nat Genet. 1998;19(4):390-394.

[28] Vasquez SSV, van Dam J, Wheway G. An updated SYSCILIA gold standard (SCGSv2) of known ciliary genes, revealing the vast progress that has been made in the cilia research field. Mol Biol Cell. 2021;32(21):br13.

[29] Stoeger T, et al. Large-scale investigation of the reasons why potentially important genes are ignored. PLoS Biol. 2018;16(9):e2006643.

[30] Linnert J, et al. Usher syndrome proteins ADGRV1 (USH2C) and CIB2 (USH1J) interact and share a common interactome containing TRiC/CCT-BBS chaperonins. Front Cell Dev Biol. 2023;11:1199069.

[31] CZI Single-Cell Biology, et al. CZ CELLxGENE Discover: A single-cell data platform for scalable exploration, analysis and modeling of aggregated data. Nucleic Acids Res. 2025;53(D1):D886-D896.

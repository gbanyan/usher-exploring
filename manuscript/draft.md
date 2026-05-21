# UsherPipe: a genome-wide multi-evidence pipeline for prioritizing under-studied Usher syndrome and ciliopathy candidate genes

**Authors:** [Author list]

**Affiliation:** Department of Computer Science and Information Engineering, National Cheng Kung University, Tainan, Taiwan

---

## Abstract

### Background

Usher syndrome is the most common genetic cause of combined deafness-blindness, yet approximately 10–15% of clinically diagnosed patients lack pathogenic variants in the ten known causative genes. Existing gene prioritization tools either require seed genes for similarity-based ranking, depend on patient sequencing data, or impute missing evidence as zero, which systematically penalizes under-studied genes that may carry undiscovered disease associations. No existing tool integrates cilia-specific evidence layers with genome-wide coverage while preserving missing data.

### Results

We present UsherPipe, an open-source pipeline that screens 19,554 human protein-coding genes across six orthogonal evidence layers: gnomAD loss-of-function constraint, tissue expression specificity for retina and cochlea (including single-cell photoreceptor data from CellxGene Census), functional annotation completeness, cilia-related subcellular localization, cross-species animal model sensory phenotypes, and literature mining with explicit research-bias correction. UsherPipe uses NULL-aware weighted scoring: missing evidence is preserved as NULL rather than imputed, and composite scores are computed only over available layers, so poorly characterized genes are not penalized. Validation against 38 known Usher syndrome and ciliopathy genes yields a median percentile rank of 90.2%, with 35 of 38 (92.1%) in the top quartile. Sensitivity analysis shows rankings are moderately robust to weight perturbation (mean Spearman ρ = 0.87 across 24 ±5–10% perturbations; 17 of 24 stable at ρ ≥ 0.85), with the animal-model layer contributing the most ranking variance. The pipeline identifies 11,430 candidates at MEDIUM or HIGH confidence, with top-ranked genes including VANGL2 (planar cell polarity, hair-cell orientation), DYNC1H1 (cytoplasmic dynein, intraflagellar transport), and ATP2B2 (calcium pump, deafness phenotype in mice).

### Conclusions

UsherPipe addresses a specific gap in rare disease gene discovery: it provides a genome-wide, disease-specific integration of six evidence layers for Usher syndrome and ciliopathies, scored so that under-studied genes are not penalized for incomplete evidence. The pipeline is freely available under the MIT license at [GitHub URL].

**Keywords:** Usher syndrome, ciliopathy, gene prioritization, missing data, bioinformatics pipeline, candidate gene discovery

---

## Background

Usher syndrome (USH) is the most prevalent cause of hereditary combined deafness and blindness, affecting approximately 4–17 per 100,000 individuals worldwide [1]. Patients present with sensorineural hearing loss, vestibular dysfunction, and progressive retinitis pigmentosa. Three clinical subtypes are recognized (USH1, USH2, USH3), caused by pathogenic variants in ten genes: *MYO7A*, *USH1C*, *CDH23*, *PCDH15*, *USH1G*, *CIB2* (USH type 1); *USH2A*, *ADGRV1*, *WHRN* (type 2); and *CLRN1* (type 3) [2]. These genes encode proteins that form multi-protein complexes in the stereocilia of inner ear hair cells and the connecting cilium of retinal photoreceptors [3]. Despite this genetic framework, 10–15% of clinically diagnosed USH patients lack identifiable pathogenic variants in known genes [4], suggesting that additional causative or modifier genes remain undiscovered.

Computational gene prioritization has become a standard approach for narrowing candidate gene lists in rare disease research. However, existing tools present fundamental limitations when applied to under-studied gene discovery for ciliopathies.

**Seed-gene-dependent tools.** Endeavour [5] and ToppGene [6] rank candidates by functional similarity to a set of known disease genes (seed genes). While effective for diseases with well-characterized genetic architecture, this approach inherently favors genes that resemble known USH genes, which are precisely those most likely to have already been investigated. Novel candidates with distinct molecular functions or expression patterns may be systematically deprioritized.

**Patient-variant-centric tools.** Exomiser [7] and AMELIE [8] require patient sequencing data (VCF files) and phenotype descriptions as input. These tools excel at clinical diagnosis but are not designed for hypothesis-generating genome-wide screens. They cannot be applied when the goal is to identify candidate genes *before* patient data is available.

**Cilia-specific databases.** CiliaCarta [9] and CilioGenics [10] integrate multi-evidence data to predict whether a gene encodes a ciliary protein. CiliaCarta uses Bayesian integration across 185 datasets to classify genes as ciliary or non-ciliary, while CilioGenics (published 2024) combines scRNA-seq, protein-protein interactions, and text mining. However, both tools address a different question ("Is this gene ciliary?" rather than "Is this gene a candidate for Usher syndrome?") and incorporate neither genetic constraint metrics nor disease-specific tissue expression weighting.

**Genome-wide multi-evidence tools.** mantis-ml [11] is the closest genome-wide comparator, integrating over 1,200 features including gnomAD constraint, GTEx expression, and mouse phenotypes into a stochastic semi-supervised learning framework. However, mantis-ml imputes missing data with zero or median values, a design choice that systematically penalizes under-studied genes, which are the most likely to represent novel disease associations. Furthermore, mantis-ml includes no cilia-specific localization layer and applies no disease-specific tissue weighting.

Table 1 summarizes the feature comparison across these approaches.

**Table 1. Comparison of gene prioritization approaches for rare disease gene discovery.**

| Feature | Endeavour | ToppGene | Exomiser | AMELIE | CiliaCarta | CilioGenics | mantis-ml | **UsherPipe** |
|---------|:---------:|:--------:|:--------:|:------:|:----------:|:-----------:|:---------:|:-------------:|
| Genome-wide screening | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | **✓** |
| Seed-gene independent | — | — | — | — | ✓ | ✓ | ✓ | **✓** |
| Disease-specific tissue weighting | — | — | ✓† | ✓† | — | — | — | **✓** |
| Patient-variant (VCF) interpretation | — | — | ✓ | ✓ | — | — | — | **—** |
| Machine-learned scoring | — | — | — | ✓ | ✓ | ✓ | ✓ | **—** |
| NULL-aware scoring | — | — | — | — | — | — | — | **✓** |
| Cilia/centrosome localization | — | — | — | — | ✓ | ✓ | — | **✓** |
| gnomAD constraint | — | — | ✓ | — | — | — | ✓ | **✓** |
| Animal model phenotypes | — | — | ✓ | — | — | — | ✓ | **✓** |
| Literature bias correction | — | — | — | — | — | — | — | **✓** |

†Exomiser and AMELIE apply disease-specific weighting within a patient-variant context, requiring VCF input; UsherPipe applies genome-wide disease-specific weighting without patient data.

Here, we present UsherPipe, an open-source bioinformatics pipeline that addresses these limitations through three design principles: (1) genome-wide screening of all protein-coding genes across six orthogonal evidence layers with disease-specific biological dimensions for Usher syndrome and ciliopathies (no seed genes or similarity metrics required); (2) NULL-aware weighted scoring that preserves missing evidence rather than imputing it, so under-studied genes are not systematically penalized; and (3) literature mining with explicit research-bias correction that surfaces overlooked genes with disproportionate cilia-related evidence relative to their total publication count.

---

## Implementation

### Architecture

UsherPipe is implemented in Python (≥3.11) as a modular command-line pipeline using Click for CLI orchestration, DuckDB for persistent storage, and Polars for data manipulation. The pipeline consists of four sequential stages: (1) gene universe construction, (2) six independent evidence layer computations, (3) composite scoring integration, and (4) report generation with validation (Figure 1).

Each evidence layer follows a uniform fetch-transform-load architecture. The fetch module downloads source data with retry logic (exponential backoff via tenacity) and persistent HTTP caching (requests-cache with SQLite backend) or streaming downloads (httpx for large files). The transform module performs data cleaning, quality filtering, and normalization to a 0–1 score. The load module persists results to DuckDB using idempotent CREATE OR REPLACE TABLE operations, enabling checkpoint-restart: any layer can be re-executed without affecting others.

All pipeline state resides in a single DuckDB database file (`pipeline.duckdb`). DuckDB was chosen over SQLite for its columnar storage, native Parquet export, and efficient analytical query performance on the tabular gene data. As DuckDB supports only single-writer access, evidence layers must be executed sequentially, though their computations are independent and could be parallelized with a multi-database architecture in future work.

### Gene universe

The gene universe is constructed by querying the mygene.info API [12] for all human protein-coding genes (Ensembl release 113), yielding 22,761 Ensembl gene IDs corresponding to 19,571 unique HGNC symbols (1,539 symbols have multiple Ensembl IDs, accounting for 3,190 redundant entries, due to alternative loci and pseudoautosomal regions). The scoring stage deduplicates to one entry per gene symbol using a three-tier canonical ID preference: (1) NCBI MANE Select canonical transcript mappings (v1.3, covering 19,288 genes), (2) gnomAD-recognized Ensembl IDs, (3) lowest Ensembl ID as tiebreaker. This yields 19,554 unique genes for scoring.

### Evidence layers

UsherPipe integrates six evidence layers, each capturing a distinct biological dimension relevant to Usher syndrome pathobiology. All scores are normalized to the [0, 1] interval, with NULL indicating missing evidence.

**gnomAD constraint (weight: 0.20).** Loss-of-function intolerance is quantified using the LOEUF metric (loss-of-function observed/expected upper bound fraction) from gnomAD v4.1 [13]. Lower LOEUF values indicate stronger evolutionary constraint, suggesting functional importance. Scores are computed as the inverted normalization: *loeuf\_normalized* = (*LOEUF*_max − *LOEUF*) / (*LOEUF*_max − *LOEUF*_min). Quality filtering requires mean sequencing depth ≥30× and CDS coverage ≥90%; genes below these thresholds receive NULL scores rather than potentially unreliable estimates. This layer covers 91% of the gene universe.

**Tissue expression specificity (weight: 0.20).** Usher syndrome affects retinal photoreceptors and cochlear hair cells; genes with enriched expression in these tissues are stronger candidates. Expression data are integrated from three sources: the Human Protein Atlas (HPA) v23 [14] for bulk tissue expression, GTEx v8 [15] for median gene TPM across tissues, and CZ CELLxGENE Census [31] for single-cell RNA-seq expression in photoreceptor cells (1.48 million cells from retinal datasets). The expression score combines three components: (a) Usher-tissue enrichment ratio (mean expression in target tissues including photoreceptor single-cell data / overall mean), (b) Tau tissue specificity index (τ, ranging from 0 for ubiquitous to 1 for tissue-specific), and (c) maximum expression percentile across target tissues. The composite is: *expression\_score* = 0.4 × enrichment percentile + 0.3 × τ + 0.3 × max target percentile. GTEx v8 lacks retina tissue; retinal expression at the cell-type level is provided by CellxGene photoreceptor data (19,530 non-null photoreceptor expression values in the tissue-expression layer). Hair cell single-cell data is not yet available in CellxGene Census. Coverage: 98%.

**Functional annotation completeness (weight: 0.15).** Annotation depth is quantified from Gene Ontology (GO) term counts [16], UniProt annotation scores (0–5 scale) [17], and KEGG/Reactome pathway membership [18]. The composite weights GO terms (50%), UniProt (30%), and pathway presence (20%), with GO counts log-scaled to attenuate the influence of heavily annotated genes. This layer is intentionally weighted lower (0.15) because annotation completeness inversely correlates with gene novelty: under-studied genes have fewer annotations by definition. Coverage: 99%.

**Subcellular localization (weight: 0.15).** Protein localization to cilia, centrosomes, or basal bodies provides direct mechanistic evidence for involvement in ciliopathies. Localization data are integrated from HPA immunofluorescence annotations and published proteomics datasets including CiliaCarta [9]. Scores are graded by proximity to ciliary structures: cilia/basal body/transition zone = 1.0, cytoskeleton/microtubules = 0.5, proteomics-only evidence = 0.3. Experimental evidence (HPA Enhanced/Supported reliability) receives full weight; computational predictions receive 0.6×. This layer has the lowest coverage (66%) because many genes lack localization data; these receive NULL scores, not zeros. Coverage: 66%.

**Animal model phenotypes (weight: 0.15).** Cross-species phenotype conservation provides functional validation independent of human data. Orthologs are mapped via HCOP [19], and phenotype annotations are retrieved from MGI (mouse) [20], ZFIN (zebrafish) [21], and IMPC [22]. Phenotypes are filtered for sensory relevance using curated keyword sets (hearing, vision, retina, photoreceptor, cochlea, stereocilia, vestibular, balance for mouse; hearing, otic, lateral line, hair cell, retina for zebrafish). Phenotype counts are log-scaled, using log₂(count + 1) / log₂(max + 1), to prevent annotation-rich model organisms from dominating rankings. Coverage: 98%.

**Literature mining (weight: 0.15).** Gene-to-publication mappings are obtained from NCBI's curated gene2pubmed database, providing total publication counts per gene. Context-specific counts (cilia, sensory, cytoskeleton, cell polarity) are derived by intersecting each gene's PMIDs with six batch PubMed MeSH queries; this replaces per-gene API queries and reduces runtime from roughly 46 hours to 5 minutes. Evidence quality is tiered: direct experimental (knockout/mutation in cilia/sensory context, weight 1.0), functional mention (cilia context with ≥3 publications, 0.6), high-throughput screening hit (0.3), and incidental mention (0.1). Critically, raw scores are divided by log₂(total publications + 1) to correct for research bias: a gene with 5 cilia-related papers among 50 total publications receives a higher score than one with 5 among 100,000. A logarithmic scale was chosen over a linear ratio to prevent extreme penalization of legitimately ciliary genes with broad multi-disciplinary research histories (e.g., PKD1). This explicitly favors under-studied genes with disproportionate cilia evidence. Coverage: 99% (genes present in NCBI gene2pubmed; the remaining 1% receive NULL).

### NULL-aware composite scoring

The composite score integrates all six layers using a weighted average computed only over layers with non-NULL scores:

*composite\_score* = Σ(*score*_i × *weight*_i) / Σ(*weight*_i), for all *i* where *score*_i ≠ NULL

Weights (summing to 1.0) are: gnomAD 0.20, expression 0.20, annotation 0.15, localization 0.15, animal model 0.15, literature 0.15. The denominator normalizes by available weight, ensuring that a gene with evidence in only three layers is scored on those three layers alone, without penalty for missing data. The `evidence_count` field (0–6) records how many layers contributed, enabling downstream filtering by data completeness.

Genes are classified into confidence tiers: HIGH (composite ≥ 0.7, evidence ≥ 3 layers, and a cilia-signal gate; see below), MEDIUM (≥ 0.4, ≥ 2 layers), LOW (≥ 0.2), with remaining genes excluded. Quality flags (sufficient\_evidence ≥ 4, moderate ≥ 2, sparse ≥ 1) provide additional granularity.

The HIGH tier, the actionable shortlist, additionally requires a **cilia-signal gate**: direct cilia-specific evidence in the form of a non-zero cilia-proximity localization score (subcellular localization to the ciliary/centrosomal compartment, an adjacent cytoskeletal compartment, or ciliary/centrosomal proteomics evidence) or a sensory animal-model phenotype scoring at or above the 75th percentile of that layer. The percentile is taken over genes with a non-zero animal-model score (giving a threshold of 0.176), not over the full layer; because a zero animal-model score denotes absence of a recorded sensory phenotype rather than a weak one, the non-zero subset is the biologically meaningful reference set, and the full-layer 75th percentile (0.048) would admit genes with only trace signal. A gene meeting the composite-score and evidence-count thresholds but failing this gate is placed in MEDIUM rather than HIGH. The gate prevents generically well-characterized genes (which score highly on the non-specific constraint, annotation, and literature layers) from entering the HIGH-confidence shortlist. We introduced the gate post hoc, after the negative-control analysis (below) found housekeeping genes among the HIGH-tier candidates; we compared several principled gate definitions (localization or any non-zero animal signal; localization or the 75th, 90th animal-model percentile) and adopted the 75th-percentile rule because it retains every known disease gene reaching the HIGH thresholds while excluding all but one housekeeping control. It is therefore best described as a transparent post-hoc specificity filter on the shortlist rather than a weight or threshold tuned to optimize a global metric; it relabels tiers only, leaving every composite score and percentile rank unchanged.

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

Applying UsherPipe to the human protein-coding gene universe (22,761 Ensembl IDs, Ensembl release 113) produced composite scores for 19,486 of 19,554 genes after MANE Select-based gene-symbol deduplication (68 genes had no evidence in any layer and received a NULL composite score). Tier classification yielded 19,132 candidates: 95 HIGH confidence, 11,335 MEDIUM, and 7,702 LOW (Figure 2). The remaining 422 genes were excluded (composite score < 0.2 or insufficient evidence). Composite scores ranged from 0 to 0.85, with a mean of 0.43 and median of 0.43. A total of 12,114 genes (62%) had evidence across all six layers, and 19,112 (98%) had evidence in four or more layers (Figure 3).

Evidence layer coverage varied from 66% (subcellular localization) to 99% (annotation, literature). The localization gap reflects the limited availability of systematic subcellular localization data; these genes receive NULL scores and are evaluated on remaining layers. gnomAD constraint covered 91% of genes, with missing entries corresponding to genes with insufficient sequencing depth or non-canonical transcript structures.

### Top candidate genes

Among candidates with sufficient evidence (≥4 layers), the highest-scoring genes not among the ten known Usher genes include several with convergent multi-layer support (Figure 4).

**VANGL2** (composite score: 0.850, 5 layers) encodes a core planar cell polarity protein required for the coordinated orientation of stereocilia bundles on cochlear hair cells. Its top ranking is driven by strong cross-species animal model evidence (score 0.909; *Vangl2* mutant mice show inner ear and neural tube defects), extensive cilia/polarity literature (0.940), and high gnomAD constraint (0.802). VANGL2 lacks systematic subcellular localization data (NULL); the NULL-aware design still surfaces it as a strong candidate, whereas zero imputation would penalize it.

**DYNC1H1** (0.826, 6 layers), encoding cytoplasmic dynein heavy chain 1, directly participates in intraflagellar transport, the fundamental trafficking mechanism within cilia. Mutations cause neurodevelopmental disorders with reported sensory involvement [25]. Its ranking is driven by centrosome/ciliary localization (score 1.0), extensive cilia-related literature (0.998), and high gnomAD constraint (0.966); the animal-model layer contributes only modestly (0.169), as many *Dync1h1* phenotypes are annotated under neurodevelopmental rather than sensory terms.

**PAFAH1B1** (0.798, 6 layers) encodes the LIS1 protein, a dynein regulatory factor essential for cytoplasmic dynein function. LIS1 is required for intraflagellar transport and centrosome positioning [24], and mutations cause lissencephaly with documented retinal involvement. Its ranking derives from centrosome localization (1.0), literature evidence (0.988), and strong gnomAD constraint (0.969); as with DYNC1H1, its sensory animal-model score is low (0.048) because the vestibular and visual defects in *Lis1* mutant mice are annotated under neurodevelopmental rather than sensory phenotype terms.

**ATP2B2** (0.786, 5 layers) encodes a plasma membrane calcium pump. The *deafwaddler* mouse (spontaneous *Atp2b2* mutation) exhibits profound deafness and vestibular dysfunction [27], phenocopying USH type 1. Despite this, ATP2B2 has not been systematically evaluated as a human Usher candidate gene.

The list also recovers established ciliopathy genes as a sanity check: **ARL3** (0.755, 6 layers, 99.8th percentile), a small GTPase that traffics lipid-modified proteins to the cilium and whose knockout mice develop retinal degeneration [26], and **AHI1** (0.785, 6 layers), the known Joubert-syndrome gene. That both rank among the top candidates indicates the corrected six-layer scoring captures bona fide ciliary biology.

The convergence of Na⁺/K⁺-ATPase subunits (ATP1B1 at 0.833 and ATP1A1 at 0.806) among the top candidates suggests a pathway-level signal that warrants further investigation; ion transport dysfunction is increasingly recognized in sensory ciliopathies.

### Positive control validation

To assess scoring system sensitivity, we evaluated 38 known Usher syndrome and ciliopathy genes: the 10 OMIM Usher genes (*ADGRV1, CDH23, CIB2, CLRN1, MYO7A, PCDH15, USH1C, USH1G, USH2A, WHRN*) and a curated subset of 28 well-characterized ciliary genes from the SYSCILIA Gold Standard v2 (SCGSv2) [28]. The 28 SCGSv2 genes are *ARL13B, BBS1, BBS2, BBS4, BBS5, BBS7, BBS9, BBS10, CC2D2A, CEP164, CEP290, IFT88, IFT140, IFT172, INPP5E, MKS1, NPHP1, NPHP3, NPHP4, OFD1, RPGR, RPGRIP1L, TCTN1, TCTN2, TMEM67, TMEM138, TMEM216,* and *TMEM231*, selected to span core ciliary functional categories (IFT, BBSome, transition zone, ciliary membrane, MKS/JBTS). The full SCGSv2 resource contains 686 genes; this fixed subset was chosen as a high-confidence, functionally characterized positive control, and we acknowledge that the selection is curated rather than derived from an automated rule; the complete list is given here for reproducibility. All 38 genes were present in the scored set. Importantly, the evidence layers, target tissues, and default weights were defined a priori based on Usher syndrome pathobiology, not optimized against these positive controls. No weight tuning was performed based on validation results.

The median percentile rank was 90.2% (threshold: 75%), with 35 of 38 genes (92.1%) ranking in the top quartile (Figure 5). OMIM Usher genes achieved a median of 95.7%, and SYSCILIA genes 89.8%. Recall at the 10% threshold (top 1,955 genes) was 52.6% (20 of 38 known genes), increasing to 84.2% at the 20% threshold. The top-ranked known gene was CDH23 at the 99.8th percentile.

### Negative controls

Thirteen housekeeping genes (GAPDH, ACTB, B2M, UBC, PPIA, YWHAZ, HPRT1, TBP, SDHA, PGK1, RPLP0, RPL13A, RPL32) were evaluated as negative controls. Their median percentile rank was 94.1%, above the 50th-percentile threshold and a specificity failure by our predefined criteria. This result was expected given the pipeline's design trade-offs and warrants examination.

Per-layer analysis reveals why: housekeeping genes score high on three non-specific layers (mean gnomAD: 0.840 vs 0.535 genome-wide; annotation: 0.836 vs 0.644; literature: 0.838 vs 0.500), which reflects their strong evolutionary constraint, thorough functional characterization, and extensive publication history. On the cilia-specific layers they score much lower (mean localization: 0.000 vs 0.044; animal model sensory phenotypes: 0.064 vs 0.037), confirming that these layers carry the disease-specific signal. Two housekeeping genes, ACTB and YWHAZ, met the HIGH-tier composite-score and evidence-count thresholds; the cilia-signal gate (above) demotes ACTB to MEDIUM, while YWHAZ is retained in HIGH because it carries a top-quartile sensory animal-model phenotype (score 0.222), consistent with reported 14-3-3ζ involvement in cytoskeletal and ciliary processes beyond its canonical housekeeping role. After gating, one of the 13 housekeeping genes remains in the HIGH tier. We note that the gate operates on the tier label only; it does not alter composite scores, so the housekeeping median percentile (94.1%) is unchanged. Housekeeping genes still rank highly in the raw composite; this is an inherent property of any constraint/annotation/literature-weighted scheme, and one we characterize here rather than engineer away.

This pattern confirms that the cilia-specific layers (localization, animal model) provide the discriminative power between genuinely relevant candidates and generically well-studied genes. To facilitate downstream filtering, the output also includes a `has_cilia_signal` flag indicating whether each gene has non-zero evidence in at least one cilia-specific layer (localization or animal model). Among the 11,335 MEDIUM-tier candidates, 4,754 (41.9%) have cilia signal; the remaining 6,581 lack direct cilia-specific evidence and should be deprioritized for experimental follow-up.

The cilia-signal gate is applied only to the HIGH tier (the small, actionable shortlist) and not to the genome-wide ranking or the MEDIUM tier. This is a deliberate design choice. With the corrected six-layer scoring, all ten OMIM Usher genes now carry direct cilia-specific evidence (a sensory animal-model phenotype, from the MGI/ZFIN data), so the gate retains every known disease gene that reaches the HIGH thresholds. Applying the same requirement genome-wide, however, would be too aggressive: novel candidates that, like the known USH genes before their discovery, have not yet been characterized in subcellular-localization or model-organism phenotype databases would be excluded entirely. Restricting the hard gate to the HIGH shortlist keeps that shortlist trustworthy for experimental follow-up, while the `has_cilia_signal` flag on every gene lets users apply their own stringency to the MEDIUM tier.

### Impact of missing data handling

To empirically assess the impact of NULL-aware scoring, we compared rankings under three imputation strategies: NULL-preserve (current design), zero-impute (NULL → 0.0), and median-impute (NULL → per-layer median). All three strategies use identical weights and evidence data; only the treatment of missing values differs.

The choice of imputation strategy redistributes percentile rank between well-covered and sparsely-covered genes. For genes with complete evidence across all six layers (n = 12,114), zero imputation raises percentile rank by a mean of 6.8 points relative to NULL-preservation, because zero imputation collapses the scores of sparsely-covered genes and thereby inflates the relative standing of well-covered genes. Conversely, genes with incomplete evidence (n = 7,440, of which 7,372 carry a non-NULL composite score) are shifted upward under NULL-preservation by a mean of +10.2 percentile points relative to zero imputation (SD = 10.4, max = +96.5) and +7.6 points relative to median imputation (SD = 10.5, max = +43.4) (Figure 6A). Across all 19,554 genes the mean shift is near zero (−0.4% versus zero imputation): NULL-preservation does not uniformly raise or lower scores but moves percentile rank away from well-characterized genes and toward under-studied ones, the intended behavior.

The impact on known disease genes is particularly informative. Six of the ten OMIM Usher genes lack subcellular localization data (the layer with the lowest coverage at 66%). Under zero imputation, these genes lose percentile rank: OFD1, a known ciliopathy gene, drops from the 95.4th to 77.3rd percentile (−18.2 points); CLRN1 from 79.6th to 64.1st (−15.5); USH1G from 82.9th to 67.6th (−15.4); CIB2 from 89.2nd to 74.8th (−14.4); WHRN from 96.3rd to 87.5th (−8.8); and MYO7A from 97.3rd to 89.9th (−7.4). These are precisely the established disease genes that a prioritization tool should rank highly, yet zero imputation penalizes them for missing data that simply has not been generated.

Among the top 25 candidates with sufficient evidence (≥4 layers), rank differences between strategies are small (within ±1.6 percentile points, mean 0.4), confirming that top-ranked genes are largely robust to imputation choice and that the NULL-aware design primarily affects genes with sparser evidence profiles, the under-studied genes this pipeline is designed to surface.

### Sensitivity analysis

To assess the robustness of rankings to weight selection, we performed a sensitivity analysis, perturbing each layer's weight by ±5% and ±10% (24 perturbations total) and measuring the Spearman rank correlation between the top 100 genes under perturbed versus baseline weights.

Of the 24 perturbations, 17 produced stable rankings (Spearman ρ ≥ 0.85) and 7 did not; ρ ranged from 0.54 to 0.99 with a mean of 0.87 (Figure 7). Stability was layer-dependent: the annotation layer was most robust (ρ ≥ 0.90 across all four of its perturbations), while the animal-model layer was the most sensitive: three of its four perturbations (−10%, +5%, +10%) were unstable, the worst at +10% (ρ = 0.54). The remaining unstable perturbations were the −10% perturbations of gnomAD, expression, localization, and literature, where reducing a layer's weight redistributes it across the other layers and reorders mid-ranked genes. These results indicate that while the very highest-ranked candidates are comparatively stable (the top-25 analysis above), the composite ranking as a whole is meaningfully sensitive to the weight assigned to the animal-model layer. The default weights should therefore be regarded as one biologically motivated configuration rather than an optimum; the pipeline reports per-gene layer contributions so that rankings can be re-evaluated under alternative weightings. Leave-one-layer-out ablation and larger perturbations would further characterize this sensitivity and are a priority for future work.

### Comparison with mantis-ml

To place UsherPipe alongside its closest methodological peer, we ran mantis-ml (v1.6.5) [11] on a matched disease configuration (retinal, hearing-loss, and ciliopathy phenotype terms) and compared the two tools on the 16,734 genes present in both gene universes. mantis-ml was run with its standard stochastic semi-supervised procedure (`mantisml -r pu` followed by `-r post`; 10 iterations), and the consensus reported here is the mean predicted probability across all six default classifiers (Extra Trees, Random Forest, Gradient Boosting, SVM, XGBoost, and a deep neural net). The curated known set contains 38 genes; 36 were present in both gene universes (ADGRV1 and WHRN fell outside mantis-ml's gene set), and all benchmark metrics below are computed on those 36.

mantis-ml ranked these 36 known genes at a median 99.7th percentile (ROC-AUC 0.96), compared with UsherPipe's 88.7th percentile (AUC 0.88) on the same shared universe. This apparent gap, however, is not a like-for-like measurement. mantis-ml is a seed-based supervised learner: it harvests known disease genes as positive training labels, and 34 of the 36 known genes were used by mantis-ml as training seeds. Its score for those genes therefore reflects semi-supervised recall of its own training set rather than blind prioritization. Only two known genes (CLRN1, TCTN1) were not mantis-ml seeds, too few to support a held-out comparison. UsherPipe, by contrast, uses no seed genes, so its 88.7th-percentile result is a fully unsupervised ranking. The two figures measure different quantities and should not be read as one tool out-performing the other.

The negative controls are more directly comparable, since housekeeping genes are seeds for neither tool. Here mantis-ml ranked its 13 housekeeping genes lower than UsherPipe did (a median percentile of 82.3% versus 93.6%; Figure 8), indicating somewhat better specificity. The difference is real but should not be overstated: an 82.3rd-percentile median still places housekeeping genes well within the upper tail, so neither tool cleanly separates ubiquitously expressed genes from disease candidates. This is consistent with our negative-control analysis (above) and reflects a genuine, if partial, advantage of a machine-learned model trained on ~1,200 features over UsherPipe's transparent six-layer weighted scheme.

Taken together, the benchmark confirms that the two tools occupy distinct niches rather than establishing the superiority of either. mantis-ml's supervised design achieves strong recall of known disease genes but requires seed genes; in a well-studied disease space, nearly all known genes become seeds, which leaves no meaningful held-out set on which to evaluate it without circularity. UsherPipe trades peak known-gene recall for a seed-free design that can prioritize genes with no prior disease association at all, which is its intended hypothesis-generating use case.

---

## Discussion

### Comparison with existing approaches

UsherPipe occupies a distinct application niche among gene prioritization tools (Table 1). Unlike seed-gene-dependent methods (Endeavour, ToppGene) that cannot discover candidates dissimilar to known disease genes, UsherPipe scores all protein-coding genes independently. Unlike patient-variant-centric tools (Exomiser, AMELIE), it operates without patient sequencing data, enabling hypothesis generation prior to cohort studies. And unlike cilia-specific databases (CiliaCarta, CilioGenics), it incorporates disease-specific tissue weighting and genetic constraint metrics to move from "Is this gene ciliary?" to "Is this gene an Usher candidate?"

The most informative comparison is with mantis-ml [11], which shares the genome-wide multi-evidence paradigm. The critical distinction lies in missing data handling: mantis-ml drops features with high missingness and imputes remaining gaps with zeroes, medians, or means depending on feature type. To illustrate the practical consequence, we re-scored our own gene set under zero imputation (Figure 6B) as a controlled simulation of the imputation strategy rather than a head-to-head benchmark of mantis-ml itself. Several established OMIM Usher and ciliopathy genes lose substantial percentile rank because they lack localization data: OFD1 by 18.2 points, CLRN1 by 15.5, USH1G by 15.4, and CIB2 by 14.4. Imputation-based approaches can therefore systematically depress the rankings of genes with incomplete evidence, precisely the under-studied genes most likely to represent novel disease associations, a problem sometimes termed the "streetlight effect" in genomics research [29]. We additionally ran a direct empirical benchmark against mantis-ml on a shared gene universe (Results, "Comparison with mantis-ml"), which showed that the two tools occupy distinct niches: mantis-ml achieves higher known-gene recall but does so as a seed-based learner that cannot be evaluated on those genes without circularity, whereas UsherPipe ranks them seed-free. The comparisons against the remaining tools in Table 1 are conceptual, grounded in documented tool design.

### The NULL-aware design

The decision to preserve NULL values rather than impute them has a measurable impact on pipeline output. Our ablation study quantifies this: among the 7,440 genes with fewer than six evidence layers, NULL-preservation shifts ranks upward by a mean of +10.2 percentile points relative to zero imputation, with individual shifts approaching 97 percentile points for genes with evidence in only one or two layers. The corresponding effect on the 12,114 fully-covered genes is a mean downward shift of 6.8 points: they are no longer artificially boosted by the collapse of their sparsely-covered competitors. The top-ranked candidates with sufficient evidence (≥4 layers) remain largely robust to imputation choice (within ±1.6 percentile points), confirming that the NULL-aware design redistributes rank toward under-characterized genes without destabilizing the strongest candidates. The `evidence_count` field provides transparency: users can apply their own minimum-evidence thresholds (as demonstrated by our tier classification requiring ≥2–3 layers for MEDIUM/HIGH confidence).

This design also enables progressive enrichment. As new data sources become available (e.g., expanded single-cell atlases for cochlear hair cells, improved proteomics coverage), genes previously scored on fewer layers will gain additional evidence without requiring retroactive correction of imputed values.

### Limitations

Several limitations should be noted. First, NULL preservation operates at the inter-layer level: a gene missing an entire evidence layer receives NULL for that layer, and the composite score is computed only over available layers. However, within individual evidence layers, sub-components with missing values are filled with zero (e.g., if a gene lacks Tau specificity data, that sub-component contributes 0.0 to the expression score rather than being excluded). This intra-layer zero imputation is a practical compromise that could be refined in future versions with partial-weight averaging within layers. Second, housekeeping negative controls rank highly in the raw composite (median 94th percentile), driven by the non-specific constraint, annotation, and literature layers; the cilia-signal gate keeps all but one (YWHAZ, which carries a genuine sensory animal-model phenotype) out of the HIGH-confidence shortlist, but the underlying composite ranking itself is not corrected, and users should examine layer-level scores and the `has_cilia_signal` flag when evaluating MEDIUM-tier candidates. This residual non-specificity is inherent to any constraint/annotation/literature-weighted scheme. Third, while single-cell photoreceptor expression data from CellxGene Census contributes 19,530 non-null expression values to the tissue-expression layer, inner ear hair cell data is not yet available in the Census; cochlear expression evidence remains a gap that future Census releases may address. Fourth, the bulk literature approach using gene2pubmed covers 99% of the gene universe; the remaining 1% of genes absent from NCBI's curated gene-to-publication mapping receive NULL literature scores. Fifth, while our NULL-aware approach effectively addresses missing completely at random (MCAR) and missing at random (MAR) scenarios typical of under-studied genes, it does not explicitly model missing not at random (MNAR) patterns. For instance, genes consistently lacking localization data may be inherently difficult to characterize due to their biological properties (e.g., transient or context-dependent localization) rather than simply being unstudied. Future work could explore MNAR-aware statistical models to further refine scoring in such cases. Finally, the weighted scoring framework is transparent and interpretable but not optimized through machine learning; our sensitivity analysis shows the composite ranking is moderately sensitive to the weight assigned to the animal-model layer (mean Spearman ρ = 0.87 across ±5–10% perturbations), so the default weights should be regarded as one biologically motivated configuration rather than an optimum. We explicitly evaluated whether the weights could instead be learned from the control gene sets, using two independent procedures: 5-fold cross-validated grid search over the weight simplex, maximizing the percentile separation between known disease genes and housekeeping controls; and L2-penalized logistic regression of known disease genes against study-matched non-disease genes, with the 13 housekeeping genes held aside as an untouched specificity sentinel. Both procedures improved the validation controls relative to the default weights. Cross-validated grid search raised the held-out known-gene median percentile from 90.2% to 95.8% and lowered the housekeeping median from 94.1% to 72.6%; logistic regression raised the known-gene median to 97.8% (97.2% on held-out folds), lowered the housekeeping median to 68.8%, and left no housekeeping gene above the HIGH-tier composite threshold. We nonetheless retain the a priori weights as a deliberate design decision, not a consequence of learning having failed. In every variant, discriminative weight-fitting collapsed the six-layer integration onto the one or two layers that best separated the controls: logistic regression assigned 89% of the total weight to the animal-model layer alone, and grid search drove the gnomAD, expression, annotation, and literature weights to their lower bounds. This sharply reshuffled the genome-wide ranking (Spearman ρ against the default as low as 0.59) and shifted sparse-evidence genes upward by roughly 30 percentile points on average, surfacing non-ciliary genes among the top candidates. Such a model optimizes a narrow set of control genes at the cost of the multi-evidence coverage the pipeline is designed to provide, and the same control genes would then drive both weight selection and evaluation. We therefore retain transparent, biologically-motivated weights by design, and address HIGH-tier specificity through the post-hoc cilia-signal gate (below) rather than through weight optimization. A fully learned integration model that preserves both multi-evidence coverage and interpretability remains an open direction for future work.

### Future directions

Promising extensions include protein-protein interaction network analysis (leveraging the Usher protein interactome [30]), integration of cochlear hair cell single-cell data as it becomes available in CellxGene Census, and a web interface for interactive exploration of candidate gene evidence profiles. Experimental validation of top candidates (particularly VANGL2, ATP2B2, and DYNC1H1) through immunolocalization in retinal and cochlear tissue would provide the strongest support for their candidacy.

---

## Conclusions

UsherPipe addresses a specific gap in rare disease gene discovery: no existing resource combines genome-wide coverage, seed-free ranking, and Usher/ciliopathy-specific evidence integration while scoring genes so that incomplete evidence does not penalize under-studied candidates. Validation against 38 known disease genes confirms sensitivity (median 90.2nd percentile, 35 of 38 in the top quartile); sensitivity analysis shows the ranking is moderately robust to weight perturbation (mean ρ = 0.87) but meaningfully dependent on the animal-model layer weight, so the default weights are best treated as one biologically motivated configuration. The pipeline identifies several candidates with convergent multi-layer evidence, including VANGL2, DYNC1H1, and ATP2B2, which warrant experimental follow-up. With a total runtime of approximately 30–45 minutes, UsherPipe is freely available as an open-source Python package under the MIT license.

---

## Availability and requirements

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

## Figure legends

**Figure 1. UsherPipe pipeline architecture.** The four sequential stages of the pipeline: (1) gene universe construction from the mygene.info API; (2) six independent evidence-layer computations, each following a fetch–transform–load pattern; (3) NULL-aware composite scoring; and (4) report generation with validation. All pipeline state is held in a single DuckDB database, and any evidence layer can be recomputed independently through idempotent table writes.

**Figure 2. Distribution of composite scores.** Stacked histogram of NULL-aware composite scores for the 19,486 genes with a non-NULL score, coloured by confidence tier (HIGH, MEDIUM, LOW). Most genes fall in the MEDIUM range; the HIGH tier is a small shortlist at composite score ≥ 0.7.

**Figure 3. Evidence layer coverage.** Number of genes with non-NULL evidence in each of the six evidence layers; the percentage above each bar is coverage relative to the full gene universe (dashed line). Coverage ranges from 66% (subcellular localization) to 99% (functional annotation and literature).

**Figure 4. Per-layer evidence profiles of the top 25 candidates.** Heatmap of normalized layer scores (0–1) for the 25 highest-scoring genes with sufficient evidence (≥4 layers). Grey cells indicate missing evidence (NULL). Asterisks mark known OMIM Usher genes and plus signs mark known ciliopathy (SYSCILIA) genes that appear among the top candidates.

**Figure 5. Positive-control validation.** Percentile-rank distributions for the 10 OMIM Usher genes, the 28 SYSCILIA ciliary genes, and a background sample of other genes, shown as box plots with the known genes also plotted as individual points. The dashed line marks the 75th percentile and the dotted line the median.

**Figure 6. Effect of missing-data handling on rankings.** (A) Distribution of percentile-rank shifts for genes with incomplete evidence (fewer than six layers) under NULL-preservation relative to zero imputation and to median imputation; positive values indicate that NULL-preservation ranks the gene higher. (B) Percentile rank of known disease genes under the three imputation strategies (NULL-preserve, zero-impute, median-impute); zero imputation lowers the rank of established genes that lack subcellular-localization data.

**Figure 7. Sensitivity of rankings to weight perturbation.** Spearman rank correlation between the top-100 genes under the default weights and under each of 24 weight perturbations (six layers, each perturbed by ±5% and ±10%). The animal-model layer is the most sensitive and the annotation layer the most robust.

**Figure 8. Benchmark against mantis-ml.** (A) Percentile-rank distributions of the 36 known genes shared by both tools' gene universes, for UsherPipe and mantis-ml. (B) Benchmark metrics for the two tools: known-gene median percentile, recall at the 10% and 20% thresholds, and housekeeping-gene median percentile. mantis-ml attains higher known-gene recall as a seed-based learner (34 of the 36 known genes are training seeds), whereas UsherPipe ranks the same genes without seeds.

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

# UsherPipe: a genome-wide multi-evidence pipeline for prioritizing candidate genes in Usher syndrome and related ciliopathies

**Article type:** Research Article

**Authors:** Jing-Rung Huang^1,* (ORCID: 0000-0003-4776-3550); Yung-Hao Ching^2 (ORCiD: 0000-0002-5767-6701; yching@gms.tcu.edu.tw); Wen-Hsiang Lu^1 (ORCID: 0009-0002-5149-6790)

**Corresponding author:** Jing-Rung Huang, MD; gbanyan.huang@gmail.com; Department of Computer Science and Information Engineering, National Cheng Kung University, No. 1, University Road, Tainan 701, Taiwan. ORCID: 0000-0003-4776-3550

**Affiliations:** ^1^ Department of Computer Science and Information Engineering, National Cheng Kung University, No. 1, University Road, Tainan 701, Taiwan; ^2^ Department of Molecular Biology and Human Genetics, Tzu Chi University, No. 701, Sec. 3, Zhongyang Rd., Hualien City, Hualien County 970, Taiwan (R.O.C.).

---

## Abstract

### Background

Usher syndrome is the most common genetic cause of combined deafness-blindness, yet a subset of clinically diagnosed patients remains unresolved after testing. Existing tools make different design choices about prior disease genes, patient-specific data, and missing evidence. UsherPipe integrates cilia- and sensory-relevant evidence across the protein-coding genome while preserving missingness explicitly.

### Results

We present UsherPipe, a pipeline that starts from 20,116 Ensembl 113 protein-coding IDs and produces 20,081 analysis labels after 35 duplicate-symbol consolidations. Of these labels, 573 unresolved gene names use Ensembl IDs as fallback labels; the remaining names derive from the Ensembl GTF `gene_name` field or an exact-ID lookup in a legacy mapping cache, neither of which validates a current canonical HGNC symbol. UsherPipe integrates six complementary evidence layers: gnomAD loss-of-function constraint, source-specific tissue expression measures for retina-related tissues, functional annotation completeness, cilia-related subcellular localization, cross-species animal-model sensory phenotypes, and literature mining with publication-volume normalization. It first calculates a NULL-aware multi-evidence support score and then applies a cilia-signal gate selected after inspection of internal control behavior to define a small HIGH tier: missing evidence is preserved as NULL rather than imputed, and support scores are computed only over available layers. In an internal recovery analysis, all 37 established Usher/ciliary control genes were found; their median percentile rank was 92.8%, with 35 of 37 (94.6%) in the top quartile and 56.8% recall in the top 10%. Sensitivity analysis of absolute weight-point perturbations (±0.05 and ±0.10) produced a mean top-100 Spearman ρ of 0.8548 (range 0.6051–0.9770); 16 of 24 perturbations met the stated stability threshold. The final report contains 62 HIGH, 9,673 MEDIUM, and 8,652 LOW analysis labels; 20,053 labels have non-NULL composite scores. These are computational priorities, not confirmed disease genes.

### Conclusions

UsherPipe provides a genome-wide, disease-focused integration of six evidence layers for Usher syndrome and related ciliopathies. Its layer-level NULL-aware score avoids treating unmeasured evidence as negative evidence, but does not by itself establish that a gene is under-studied or disease-causing. The pipeline and analysis outputs are publicly available in the UsherPipe repository [50], with the submitted code/data version identified by commit `4cf8c5b`.

**Keywords:** Usher syndrome, ciliopathy, gene prioritization, missing data, bioinformatics pipeline, disease gene discovery

---

## Background

Usher syndrome (USH) is a major cause of hereditary combined deafness and blindness. Reported prevalence varies by population; Boughman et al. estimated 4.4 per 100,000 in the United States [1]. Patients present with sensorineural hearing loss, vestibular dysfunction, and progressive retinitis pigmentosa. Established clinical subtypes include USH1, USH2, and USH3, with validated gene–disease relationships involving *MYO7A*, *USH1C*, *CDH23*, *PCDH15*, *USH1G*, *USH2A*, *ADGRV1*, *WHRN*, and *CLRN1* [2]. The historical assignment of *CIB2* to USH1J is not treated as established in this analysis because current gene–disease curation is mixed [3], and it is therefore excluded from the established positive-control set used here. These genes encode proteins that form multi-protein complexes in the stereocilia of inner ear hair cells and the connecting cilium of retinal photoreceptors [4]. In one European cohort, causal biallelic variants were identified in 92.7% of clinically diagnosed patients [5].

Even after comprehensive genomic screening—including targeted gene panels, whole-exome sequencing (WES), whole-genome sequencing (WGS), and copy-number-variant (CNV) analysis—the molecular cause remains unresolved for a subset of individuals with clinically diagnosed Usher syndrome. Possible explanations include novel disease genes, noncoding or deep intronic variants, complex structural variants, and regulatory alterations; the relative contribution of these mechanisms is not established here. A prioritization score can organize hypotheses for follow-up, but absence of annotation or publication is not evidence that a gene is genuinely under-studied, nor is a high score evidence of a causal gene–disease relationship. Throughout, we use *candidate* to mean a proposed but not yet established gene–disease relationship; this operational use is distinct from ClinGen's formal gene–disease validity classifications [6].

### Usher syndrome as a specialized sensory ciliopathy

Ciliopathies comprise a genetically and phenotypically heterogeneous class of inherited disorders arising from structural or functional aberrations in primary cilia, motile cilia, or their anchor proteins [7]. Given that cilia serve as indispensable hubs for developmental signaling cascades, sensory perception, and fluid homeostasis, ciliary dysfunction characteristically manifests as pleiotropic, multisystemic pathologies. These conditions frequently impair the retina, kidneys, central nervous system, skeleton, liver, and reproductive tracts, spanning a clinical spectrum from isolated sensory deficits to complex, syndromic phenotypes with profound clinical overlap.

Because the known Usher genes encode ciliary and periciliary proteins acting at hair-cell stereocilia, the photoreceptor connecting cilium, and the periciliary membrane complex, Usher syndrome may be regarded as a highly specialized sensory ciliopathy, and gene discovery for Usher syndrome therefore draws on the same ciliary biology that underlies related sensory ciliopathies. However, Usher-specific gene prioritization should not be treated as equivalent to broad ciliopathy gene prioritization: broad ciliopathies arise from general defects in ciliary assembly, transport, or signaling, whereas Usher syndrome is defined by the combined auditory–retinal phenotype. The principal distinction lies in the relative weighting assigned to phenotypic specificity and tissue relevance during the prioritization process, motivating the genome-wide, ciliopathy-aware scope adopted here.

### Ciliary and stereociliary biology underlying Usher syndrome

In the retina, the photoreceptor outer segment is a highly specialized primary cilium that contains the membrane proteins and signaling components required for phototransduction. Because the outer segment lacks protein-synthesis machinery, newly synthesized proteins and membrane components must be transported from the inner segment through the connecting cilium. Several Usher proteins localize to the connecting-cilium, periciliary, or calyceal-process regions, where they contribute to photoreceptor compartmentalization, protein trafficking, and outer-segment maintenance. Defects in these proteins disrupt photoreceptor structure and homeostasis, leading to progressive photoreceptor degeneration and retinitis pigmentosa [8-10].

In the inner ear, the hair bundle is a mechanosensory structure composed of actin-based stereocilia arranged in a precise staircase-like pattern. Although stereocilia are not true cilia, their development is coordinated with the microtubule-based kinocilium and basal body. Usher proteins form interacting complexes that are essential for hair-bundle cohesion, orientation, maturation, and mechanotransduction. When these proteins are absent or dysfunctional, stereocilia may become fragmented, misoriented, unevenly organized, or poorly connected. These developmental abnormalities impair mechanotransduction and cause the sensorineural hearing loss characteristic of Usher syndrome [11-13].

The shared molecular basis of the retinal and auditory phenotypes lies in the Usher protein interactome, in which different proteins assemble into distinct but interconnected functional complexes. USH1 proteins, including myosin VIIa, harmonin, cadherin 23, protocadherin 15, and SANS, contribute to transient lateral links, tip-link-associated structures, and their attachment to the stereociliary actin cytoskeleton. These complexes are required for hair-bundle cohesion, orientation, and maturation [12, 14].

USH2 proteins, including usherin, ADGRV1, whirlin, and PDZD7, form the ankle-link complex at the base of developing hair-cell stereocilia. In photoreceptors, usherin, ADGRV1, and whirlin assemble at the periciliary membrane complex near the connecting cilium, where they are thought to support protein trafficking and cargo delivery to the outer segment [9, 15, 16]. CLRN1, a tetraspan-like membrane protein associated with USH3A, is required for normal hair-bundle organization [17]. In a zebrafish *clrn1* model, a retinal maintenance role was linked to Müller glia–mediated support of photoreceptors [18]. Together, Usher proteins participate in cell adhesion, macromolecular scaffolding, intracellular trafficking, cytoskeletal organization, and membrane compartmentalization in both sensory systems [8, 19].

### Limitations of existing gene prioritization approaches

Computational gene prioritization has become a standard approach for narrowing candidate gene lists in rare disease research. However, existing approaches primarily focus on variant interpretation, phenotype matching, or similarity to previously characterized disease genes, making them less suited for discovering novel Usher syndrome candidate genes.

**Seed-gene-dependent tools.** Endeavour [20] and ToppGene [21] rank candidates by functional similarity to a set of known disease genes (seed genes). While effective for diseases with well-characterized genetic architecture, this approach inherently favors genes that resemble known USH genes, which are precisely those most likely to have already been investigated. Novel candidates with distinct molecular functions or expression patterns may be systematically deprioritized.

**Patient-variant-centric tools.** Exomiser [22] and AMELIE [23] require patient sequencing data (VCF files) and phenotype descriptions as input. These tools excel at clinical diagnosis but are not designed for hypothesis-generating genome-wide screens. They cannot be applied when the goal is to identify candidate genes *before* patient data is available.

**Cilia-specific databases.** CiliaCarta [24] and CilioGenics [25] integrate multi-evidence data to predict whether a gene encodes a ciliary protein. CiliaCarta uses genomic, proteomic, transcriptomic, and evolutionary data in a Bayesian predictive score, while CilioGenics (published 2024) combines scRNA-seq, protein-protein interactions, comparative genomics, transcription-factor network analysis, and text mining. The published descriptions do not establish a disease-specific tissue-weighted Usher score or a gnomAD constraint layer for either resource. Both tools therefore address a different question ("Is this gene ciliary?" rather than "Is this gene a candidate for Usher syndrome?").

**Genome-wide multi-evidence tools.** mantis-ml [26] is the closest genome-wide comparator, integrating over 1,200 features into a stochastic semi-supervised learning framework. Its published preprocessing discards features with more than 25% missingness and imputes remaining gaps with zero or feature medians; the paper also describes disease- and tissue-filtered feature categories. These choices differ from UsherPipe's NULL-preserving score. The published method does not establish a Usher-specific cilia-localization layer or the particular disease-specific tissue weighting used here.

Table 1 summarizes documented feature categories across these approaches; a dash means that no explicit implementation of the named feature was located in the primary method description.

**Table 1. Comparison of gene prioritization approaches for rare disease gene discovery.**

| Feature | Endeavour | ToppGene | Exomiser | AMELIE | CiliaCarta | CilioGenics | mantis-ml | **UsherPipe** |
|---------|:---------:|:--------:|:--------:|:------:|:----------:|:-----------:|:---------:|:-------------:|
| Genome-wide screening | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | **✓** |
| No user-supplied disease seeds | — | — | ✓ | ✓ | ✓ | ✓ | — | **✓** |
| Disease-specific tissue weighting | — | — | — | — | — | — | — | **✓** |
| Patient-variant (VCF) interpretation | — | — | ✓ | ✓ | — | — | — | **—** |
| Machine-learned scoring | — | — | — | ✓ | ✓ | — | ✓ | **—** |
| NULL-aware scoring | — | — | — | — | — | — | — | **✓** |
| Cilia/centrosome localization | — | — | — | — | ✓ | — | — | **✓** |
| gnomAD constraint | — | — | — | — | — | — | ✓ | **✓** |
| Animal model phenotypes | — | — | ✓ | — | — | — | ✓ | **✓** |
| Literature bias correction | — | — | — | — | — | — | — | **✓** |

Feature labels are intentionally narrow: Exomiser's gnomAD allele-frequency features are not treated as gene-level constraint, and phenotype matching is not treated as disease-specific tissue weighting. AMELIE is marked for its documented learned/model-based scoring, and CiliaCarta is marked because its published Bayesian predictive score is model-based; CilioGenics is not labelled machine-learned without an explicit machine-learning model in the cited method description.

Here, we present UsherPipe, a bioinformatics pipeline that addresses these limitations through three design principles: (1) genome-wide screening of protein-coding genes across six complementary evidence layers with disease-focused biological dimensions for Usher syndrome and related ciliopathies (no seed genes or similarity metrics required); (2) NULL-aware weighted scoring that preserves missing evidence rather than imputing it as negative evidence at the layer level; and (3) literature mining with publication-volume normalization that attenuates dominance by heavily published genes. The resulting composite is a multi-evidence support score; a transparent cilia-signal gate defines a higher-priority tier for experimental follow-up, but neither score nor tier is a clinical or causal assertion.

---

## Methods

### Study design and setting

This was a retrospective computational methods study asking whether a transparent, seed-free integration of publicly available biological annotations can prioritize genome-wide hypotheses for Usher syndrome and related ciliopathies. The production analysis used locally cached inputs and configured version labels with a fixed protein-coding gene universe; the optional analyses were evaluated after production tier assignment and did not change production scores or tiers. These labels document the configured inputs but do not prove that the sources are immutable. No participants were recruited, no new human specimens or animal experiments were performed, and no patient-level data are reported. The study setting is the local reproducible pipeline described below. Stage-level execution metadata, the configuration hash, and report outputs are recorded in repository artifacts, but source-level provenance for the current run is incomplete: the reproducibility manifest records six source records and six checksums, but only two source URLs, two versions, and no retrieval times. Missing fields are not inferred, so the manifest does not establish that every upstream source version or retrieval event is recorded.

### Architecture

UsherPipe is implemented in Python (≥3.11) as a modular command-line pipeline using Click for CLI orchestration, DuckDB for persistent storage, and Polars for data manipulation. The pipeline consists of four sequential stages: (1) gene universe construction, (2) six separately computed evidence layers, (3) composite scoring integration, and (4) report generation with validation (Figure 1).

Each evidence layer follows a uniform fetch-transform-load architecture. The fetch module downloads source data with retry logic (exponential backoff via tenacity) and persistent HTTP caching (requests-cache with SQLite backend) or streaming downloads (httpx for large files). The transform module performs data cleaning, quality filtering, and normalization to a 0–1 score. The load module persists results to DuckDB using idempotent CREATE OR REPLACE TABLE operations, enabling checkpoint-restart: any layer can be re-executed without affecting others.

All pipeline state resides in a single DuckDB database file (`pipeline.duckdb`). DuckDB was chosen over SQLite for its columnar storage, native Parquet export, and efficient analytical query performance on the tabular gene data. As DuckDB supports only single-writer access, evidence layers must be executed sequentially, though their computations are independent and could be parallelized with a multi-database architecture in future work.

### Gene universe

The gene universe is loaded from the locally cached Ensembl 113 GRCh38 GTF input; mygene.info [27] is used for identifier annotation rather than as the authoritative source of the protein-coding universe. The configured Ensembl release label documents the input selection but does not prove source immutability. The final input contained 20,116 Ensembl 113 protein-coding IDs and yielded 20,081 analysis labels after 35 duplicate-symbol consolidations. The 573 unresolved gene names use their Ensembl IDs as fallback labels. The remaining names derive from the Ensembl GTF `gene_name` field or an exact-ID lookup in the legacy mapping cache; neither source is treated as validation of a current canonical HGNC symbol. The scoring stage retains one record per analysis label using a three-tier preference: (1) NCBI MANE Select mappings (v1.3), (2) gnomAD-recognized Ensembl IDs, and (3) the lowest Ensembl ID as tiebreaker. Table S1 contains the 35 merged-symbol mappings: 34 use a MANE Select mapping and one uses the gnomAD-recognized-or-lowest-Ensembl fallback. Strict filtering of `gene_biotype == protein_coding` excludes noncoding and locus records from the production universe.

### Evidence layers

The six evidence layers are detailed below. All scores are normalized to the [0, 1] interval, with NULL indicating missing evidence.

**gnomAD constraint (weight: 0.20).** Loss-of-function intolerance is quantified using the LOEUF metric (loss-of-function observed/expected upper bound fraction) from the locally cached input labeled gnomAD v4.1 [28]. The configured label does not prove source immutability. Lower LOEUF values indicate stronger evolutionary constraint, suggesting functional importance. Scores are computed as the inverted normalization: *loeuf\_normalized* = (*LOEUF*_max − *LOEUF*) / (*LOEUF*_max − *LOEUF*_min). Genes for which gnomAD v4.1 reports no usable LOEUF estimate receive NULL scores rather than imputed values. Where gnomAD publishes per-gene coverage metrics, the pipeline additionally sets genes below a mean sequencing depth of 30× or 90% CDS coverage to NULL; the v4.1 constraint release used here does not include these per-gene coverage fields, so for this run a NULL gnomAD score reflects the absence of a usable LOEUF estimate.

**Tissue expression specificity (weight: 0.20).** Usher syndrome affects retinal photoreceptors and cochlear hair cells; genes with enriched expression in these tissues are relevant hypotheses. The production target set comprises HPA bulk retina-related measures [29], GTEx v8 [30] tissue measures, and CELLxGENE Census photoreceptor data [31]; cerebellum is retained as a proxy tissue, whereas hair-cell data are not included in the production score because no suitable Census hair-cell query was available in the locally cached inputs. HPA v23, GTEx v8, and CELLxGENE Census are normalized within source before combination: HPA/GTEx enrichment and tau are not computed on mixed raw units, and photoreceptor expression is incorporated as a separately ranked target feature. The configured Census build label is `2025-11-08`; labels do not prove source immutability. The composite is: *expression\_score* = 0.4 × enrichment percentile + 0.3 × source-specific τ + 0.3 × maximum target percentile.

**Functional annotation completeness (weight: 0.15).** Annotation depth is quantified from Gene Ontology (GO) term counts [32], UniProt annotation scores (0–5 scale) [33], and membership in curated pathway databases (KEGG [34] and Reactome [35], queried through mygene.info [27]). The composite weights GO terms (50%), UniProt (30%), and pathway presence (20%), with GO counts log-scaled to attenuate the influence of heavily annotated genes. This layer measures available annotation, not biological importance or causal validity, and is therefore weighted at 0.15.

**Subcellular localization (weight: 0.15).** Protein localization to cilia, centrosomes, or basal bodies provides direct mechanistic evidence for involvement in ciliopathies. Localization data are integrated from HPA immunofluorescence annotations and published proteomics datasets including CiliaCarta [24]. Scores are graded by proximity to ciliary structures: cilia/basal body/transition zone = 1.0, cytoskeleton/microtubules = 0.5, proteomics-only evidence = 0.3. Experimental evidence (HPA Enhanced/Supported reliability) receives full weight; computational predictions receive 0.6×. Genes without localization data receive NULL scores, not zeros.

**Animal model phenotypes (weight: 0.15).** Cross-species phenotype conservation provides functional validation independent of human data. Orthologs are mapped via HCOP [36], and phenotype annotations are retrieved from MGI (mouse) [37], ZFIN (zebrafish) [38], and IMPC [39]. Phenotypes are filtered for sensory relevance using curated keyword sets (hearing, vision, retina, photoreceptor, cochlea, stereocilia, vestibular, balance for mouse; hearing, otic, lateral line, hair cell, retina for zebrafish). Phenotype counts are log-scaled, using log₂(count + 1) / log₂(max + 1), to prevent annotation-rich model organisms from dominating rankings.

**Literature mining (weight: 0.15).** Gene-to-publication mappings are obtained from NCBI's curated gene2pubmed database [40], providing total publication counts per gene. Context-specific counts (cilia, sensory, cytoskeleton, cell polarity) are derived by intersecting each gene's PMIDs with batch PubMed queries. A direct-experimental label requires the same PMID to occur in the gene's publication set, the direct-experimental set, and the union of cilia/sensory context sets; separate papers are not combined to create a direct label. Evidence quality is tiered as direct experimental, functional mention, high-throughput screening hit, or incidental mention. Raw scores are divided by log₂(total publications + 1) as a publication-burden adjustment. This normalization attenuates one dimension of research-volume dominance but is not a calibrated model of research bias. Context-PMID sets are cached locally for checkpointed reprocessing; missing literature evidence remains NULL.

### NULL-aware composite scoring

The composite score integrates all six layers using a weighted average computed only over layers with non-NULL scores:

*composite\_score* = Σ(*score*_i × *weight*_i) / Σ(*weight*_i), for all *i* where *score*_i ≠ NULL

Weights (summing to 1.0) are: gnomAD 0.20, expression 0.20, annotation 0.15, localization 0.15, animal model 0.15, literature 0.15. The denominator normalizes by available weight, ensuring that a gene with evidence in only three layers is scored on those three layers alone, without penalty for missing data. The `evidence_count` field (0–6) records how many layers contributed, enabling downstream filtering by data completeness.

Genes are classified into confidence tiers: HIGH (composite ≥ 0.7, evidence ≥ 3 layers, and a cilia-signal gate; see below), MEDIUM (≥ 0.4, ≥ 2 layers), LOW (≥ 0.2), with remaining genes excluded. Quality flags (sufficient\_evidence ≥ 4, moderate ≥ 2, sparse ≥ 1) provide additional granularity.

The excluded-gene listing is provided as Additional file 2 (Table S2).

The HIGH tier additionally requires a **cilia-signal gate**: a non-zero cilia-proximity localization score or a sensory animal-model phenotype at or above the 75th percentile among genes with non-zero animal-model scores. A gene meeting the composite-score and evidence-count thresholds but failing this gate is placed in MEDIUM rather than HIGH. The gate is a transparent post-hoc calibration filter applied after the raw score; it does not change composite scores or percentile ranks. Because the gate was selected after inspection of negative controls, it is not an independent validation and its apparent housekeeping-gene separation should be interpreted as an internal calibration result. The gate does not establish causality, clinical utility, or experimental actionability.

In this manuscript, **seed-free** means that known disease/control genes were not used as training labels, similarity seeds, or inputs to the raw six-layer composite score. It does not mean that every downstream decision was independent of the controls: the cilia-signal gate was selected after inspection of control and negative-control behavior. Accordingly, seed-free ranking and internal control recovery are reported separately from independent validation.

### Optional post-hoc shortlist refinement

The production pipeline stops at the 62-gene HIGH tier. We additionally evaluated optional annotations within HIGH: Tau tissue specificity and exploratory fetal cochlear hair-cell expression derived from GSE135913 [41]. The local-only GSE output is restricted to 15,608 of the 20,081 current analysis labels, and 61 of 62 HIGH labels have a non-NULL aggregate. Hair-cell clusters were identified using a prespecified marker-guided rule that excluded Usher positive-control genes; the 23-week sample was excluded for insufficient marker separation. These annotations did not alter composite scores or tier assignments and should be treated as exploratory experimental-prioritization views, not validation. Full cluster-selection criteria, sensitivity results, and local-input provenance are provided in Additional file 3 (Supplementary Methods).

This design differs fundamentally from tools that impute missing values. In mantis-ml, features with >25% missingness are discarded entirely, and remaining gaps are filled with zero or median values [26]. Zero imputation treats "unknown" as "no evidence," which can lower the rank of genes with incomplete measurements. Our NULL-preservation approach instead acknowledges epistemic uncertainty: a missing localization score means the protein's location has not been determined, not that it is absent from cilia.

### Statistical analysis

All reported statistics are descriptive summaries of the stated gene universe and control sets. Percentile ranks were calculated within the relevant comparison universe; rank robustness was summarized with Spearman correlation and top-100 Jaccard similarity; coverage, medians, recall at stated thresholds, and rank shifts were reported directly. No inferential *P* values were used to support causal or clinical claims. A prospective power calculation was not applicable to this computational ranking and internal-control analysis because the evaluated gene universe and control sets were defined by the study design rather than sampled participants.

### Reproducibility

UsherPipe records stage-level execution metadata, configuration, and report outputs. Where emitted and accepted, JSON sidecars record timestamps, input/output counts, and processing parameters. Configuration is specified in a YAML file with configured data-source version labels (Ensembl 113, gnomAD v4.1, GTEx v8, HPA v23.0, and CELLxGENE Census `2025-11-08`) and a SHA-256 configuration hash for change detection. These labels describe the configured/local inputs but do not prove that upstream sources are immutable. The current run’s source-level provenance coverage is incomplete: `data/report/reproducibility.json` records six source records and six checksums, but only two source URLs, two versions, and no retrieval times; missing fields are not inferred. Literature and expression layers support checkpointed reprocessing from local caches without forcing a download.

The human-readable reproducibility report is retained in the public repository, and the machine-readable provenance manifest is provided as Additional file 4. The manifest records the available source metadata and checksums; source-level provenance remains incomplete for some third-party inputs, as described above.

### Use of artificial intelligence tools
During preparation of this manuscript, the authors used OpenAI Codex to assist with code review, data-integrity checks, manuscript editing, and PDF preparation. The authors reviewed and verified the generated suggestions and outputs, and remain fully responsible for the final content, analyses, and interpretation. No AI system is listed as an author.

### Usage

UsherPipe is installed from source and executed as a sequential CLI pipeline:

```bash
pip install -e ".[dev,expression]"    # Include the optional CELLxGENE integration
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

Runtime depends on network conditions, cache state, and the execution environment. Subsequent `--reprocess-cached` runs recompute transforms from local caches without re-downloading source files. The CELLxGENE Census query uses the configured build label `2025-11-08` and is cached locally after the first run; the label does not prove source immutability. All outputs are written to `data/report/`, including `candidates.tsv`, `candidates.parquet`, and visualization plots.

---

## Results

### Pipeline output

Applying UsherPipe to the human protein-coding gene universe (20,116 Ensembl 113 IDs) produced 20,081 analysis labels after 35 duplicate-symbol consolidations, including 573 unresolved ENSG fallback labels. The remaining names derive from the Ensembl GTF `gene_name` field or exact-ID legacy-cache fallback; these are not validated current canonical HGNC symbols. Of these analysis labels, 20,053 had non-NULL composite scores and 28 had no evidence in any layer. Tier classification assigned 18,387 analysis labels to a non-excluded tier: 62 HIGH, 9,673 MEDIUM, and 8,652 LOW (Figure 2). The remaining 1,694 labels were excluded (1,666 with composite score < 0.2 and 28 with no evidence in any layer; Additional file 2, Table S2).

Evidence-layer coverage is reported in the tracked score table and remains layer-specific (Fig. 3); the localization gap reflects the limited availability of systematic subcellular localization data. Genes without a layer score receive NULL and are evaluated on remaining layers. Missing gnomAD values correspond to genes for which gnomAD v4.1 reports no usable LOEUF estimate.

[Figure 3 near here]

### Optional refinement of the HIGH-tier shortlist

The optional expression/protein refinements produced different biological trade-offs (Table 2). Within the 62-gene HIGH tier, photoreceptor and fetal cochlear Q75 views each retained 16 genes, their intersection retained five, HPA-retina concordance was not evaluable because the HPA-retina threshold was unavailable in the local inputs, direct cilia/centrosome protein evidence retained 23, the OR strategy retained 34, and the AND strategy retained five. GSE135913 coverage was 61/62 HIGH labels; the local-only aggregate was restricted to 15,608 analysis labels. No optional view is therefore promoted to a production gate. These analyses remain exploratory annotations rather than evidence that excluded genes lack sensory relevance. The supporting expression-shortlist candidate table, report, and strategy summary are Additional files 5, 6, and 7, respectively; the GSE135913 matrices and local-input provenance are Additional files 8, 9, and 10.

**Table 2. Optional post-hoc refinement of the 62-gene HIGH tier.**

These are alternative, non-nested strategies rather than a sequential filtering cascade (although the Tau thresholds are nested within their own group).

| Refinement family | Alternative strategy | Genes retained | Established Usher controls retained among 2 present in HIGH | Known controls retained among 3 present in HIGH |
|---|---|---:|---:|---:|
| Baseline | None (production HIGH tier) | 62 | 2/2 | 3/3 |
| Disease-cell enrichment | Fetal cochlear hair-cell expression ≥ Q75 | 16 | 2/2 | 2/3 |
| Disease-cell enrichment | Photoreceptor expression ≥ Q75 | 16 | 1/2 | 2/3 |
| Disease-cell enrichment | Hair-cell and photoreceptor expression ≥ Q75 | 5 | 1/2 | 1/3 |
| Disease-cell enrichment | Photoreceptor and HPA retina ≥ Q75 | NA | NA | NA |
| Protein/expression | Direct cilia/centrosome protein evidence | 23 | 0/2 | 1/3 |
| Protein/expression | Photoreceptor ≥ Q75 OR direct protein | 34 | 1/2 | 2/3 |
| Protein/expression | Photoreceptor ≥ Q75 AND direct protein | 5 | 0/2 | 1/3 |

### Top candidate genes

Among candidates with at least four non-NULL layers, the highest-scoring entries in the current `candidates.tsv` were DYNC1H1 (0.8001, six layers), VEGFA (0.7983, five layers), VANGL2 (0.7941, five layers), DYNC1LI1 (0.7899, six layers), and ATP1A1 (0.7888, five layers) (Figure 4). The next entries were ATP1B1 (0.7855), ATP2B2 (0.7853), PKD1 (0.7775), NEUROD1 (0.7692), and AHI1 (0.7672). These values describe model prioritization only. In particular, broad constraint, expression, annotation, and publication signals can elevate genes with no established Usher gene–disease relationship; the cilia-signal gate does not remove that limitation.

**VANGL2** is a planar-cell-polarity gene involved in developmental morphogenesis and noncanonical Wnt signaling [42, 43]. Its final score (0.7941) combines strong animal-model, literature, expression, annotation, and constraint signals, while localization is NULL. Human evidence currently supports a susceptibility or multifactorial role in neural-tube defects rather than a highly penetrant monogenic Usher relationship [44]. It is therefore a mechanistic hypothesis for follow-up, not a proposed diagnostic gene.

**DYNC1H1** encodes the cytoplasmic dynein heavy chain and has established neurodevelopmental and neuromuscular disease associations [45, 46]. Its score (0.8001) is supported across all six layers, including a localization score of 1.0 and literature score of 0.998. The animal-model signal is modest and is not specifically evidence for Usher disease. **ATP2B2** (0.7853, five layers) remains biologically relevant because *Atp2b2* mutant mice exhibit hearing and vestibular phenotypes [47], but it has not been systematically established as a human Usher gene. These examples illustrate how the output should be used to formulate testable hypotheses rather than to infer disease causality.

The appearance of ATP1B1 and ATP1A1 among the top entries is likewise an exploratory pathway-level observation, not independent evidence of Usher involvement. Candidate-specific experimental validation—especially localization and sensory-cell perturbation assays—would be required before assigning disease relevance.

### Positive control validation

To assess internal recovery of biologically established genes, we evaluated 37 controls: nine established Usher genes (*ADGRV1, CDH23, CLRN1, MYO7A, PCDH15, USH1C, USH1G, USH2A,* and *WHRN*) and a curated subset of 28 well-characterized ciliary genes from the SYSCILIA Gold Standard v2 (SCGSv2) [48]. The full SCGSv2 resource contains 686 genes; this fixed subset was selected to span core ciliary functional categories and is therefore not an independent random validation sample. All 37 controls were present in the scored set. The evidence layers, target tissues, and default weights were specified from Usher/ciliary biology rather than fitted to these controls, but the subsequent cilia-signal gate was informed by control and negative-control behavior; results are consequently described as internal control recovery, not independent validation.

The median percentile rank was 92.8% (denominator: 20,053 non-NULL scored labels; threshold: 75%), with 35 of 37 controls (94.6%) ranking in the top quartile (Figure 5). Established Usher genes achieved a median of 97.8%, and the SCGSv2 subset achieved a median of 91.9%. Recall at the top-10% threshold was 56.8%; recall at the top-20% threshold was 91.9%. This result shows recovery of the selected controls under the specified scoring scheme; it does not estimate sensitivity for undiscovered disease genes.

### Negative controls

Thirteen housekeeping genes (GAPDH, ACTB, B2M, UBC, PPIA, YWHAZ, HPRT1, TBP, SDHA, PGK1, RPLP0, RPL13A, RPL32) were evaluated as negative controls. Their median percentile rank was 94.8%, and 11 of 13 (84.6%) ranked in the top quartile. This is a specificity failure: the raw composite is not specific to Usher/ciliary biology and warrants cautious interpretation.

Per-layer analysis reveals why: housekeeping genes score high on non-specific layers such as constraint, annotation, and literature, reflecting strong evolutionary constraint, thorough functional characterization, and extensive publication history. Their median raw percentile remains high after gating; the gate only relabels tiers. Two housekeeping genes met the raw composite ≥0.70 threshold, but none remained HIGH after the cilia-signal gate. This is an internal specificity calibration result, not evidence that the gate generalizes to independent negative controls.

This pattern suggests that the cilia-specific layers provide useful additional specificity for the selected controls, but does not demonstrate general discrimination between disease-relevant and well-studied genes. The output includes a `has_cilia_signal` flag indicating whether each gene has non-zero evidence in at least one cilia-specific layer (localization or animal model). Among the 9,673 MEDIUM-tier candidates, the flag can be used to identify candidates with recorded cilia-specific signal; the remainder lack recorded direct cilia-specific evidence and should be interpreted with additional caution, not treated as biologically negative.

The cilia-signal gate is applied only to the HIGH tier and not to the genome-wide ranking or the MEDIUM tier. It retains a small set of candidates with recorded cilia-proximity or sensory-model evidence, but it cannot recover genes for which such evidence is unavailable and should not be described as a proof of shortlist trustworthiness. Restricting the gate to HIGH preserves the raw ranking for users who want a more permissive hypothesis-generating list, while the `has_cilia_signal` flag lets users apply their own stringency to MEDIUM candidates.

### Impact of missing data handling

To empirically assess the impact of NULL-aware scoring, we compared rankings under three imputation strategies: NULL-preserve (current design), zero-impute (NULL → 0.0), and median-impute (NULL → per-layer median). All three strategies use identical weights and evidence data; only the treatment of missing values differs.

The choice of imputation strategy redistributes percentile rank between well-covered and sparsely-covered genes. In the current artifact, zero- and median-imputation comparisons use the same layer values and weights but different denominators from the NULL-preserving analysis. NULL-preservation changes the ranking according to available evidence; it should not be interpreted as proof that sparse-evidence genes are biologically novel or disease-relevant.

The impact on established genes is also heterogeneous. Among the nine established Usher controls, genes with missing localization can lose percentile rank under zero imputation, whereas fully observed genes can move in the opposite direction. For example, USH1G and CLRN1 show NULL-preservation advantages of approximately 15 percentile points, while several fully observed SCGSv2 controls rank higher under imputation. This confirms that the choice of missing-data treatment materially affects comparisons and should be reported rather than framed as universally beneficial.

Among the top 25 candidates with sufficient evidence (≥4 layers), rank differences between strategies were small (approximately within ±0.8 percentile points in the rerun). This is a descriptive robustness result for the current data snapshot, not evidence that the same behavior will hold after future source updates.

### Sensitivity analysis

To assess the robustness of rankings to weight selection, we perturbed each layer's weight by absolute ±0.05 and ±0.10 weight points (24 perturbations total; these are not relative ±5% or ±10% changes). Each raw delta was applied to one weight and then all six weights were renormalized to sum to one, so the final change is not literally the raw delta and the other weights also change. We measured the Spearman rank correlation between the top 100 genes under perturbed versus baseline weights. Because this statistic is computed after restricting each ranking to its top 100, it is conditional on the overlapping genes; top-100 Jaccard similarity is reported alongside it.

Of the 24 perturbations, 16 met the stability criterion (Spearman ρ ≥ 0.85) and 8 did not; ρ ranged from 0.6051 to 0.9770 with a mean of 0.8548 (Figure 7). The animal-model layer was the most sensitive and annotation the most robust. These results indicate that the ranking is not invariant to weight choice; the default weights should therefore be regarded as one biologically motivated configuration rather than an optimum. Because Spearman top-100 overlap is conditional, the accompanying Jaccard statistic should be used when assessing list membership. The pipeline reports per-gene layer contributions so that rankings can be re-evaluated under alternative weightings. Data-driven fitting was not adopted because the post-hoc internal analyses concentrated weight on the selected controls and would introduce circularity.

### Old-versus-new impact audit

The pre-rebuild artifact was compared with the current output only to quantify shortlist impact. HIGH overlap: 54 genes; old-only: 14; new-only: 8; shared-candidate rank Spearman correlation: 0.9881. The pre-rebuild run was contaminated and is not treated as a valid benchmark or validation reference. These figures are an audit of artifact change, not evidence that either run is biologically superior.

### Comparison with mantis-ml

To place UsherPipe alongside its closest methodological peer, we evaluated the repository's cached mantis-ml v1.6.5 prediction files [26]. The benchmark script reads per-classifier `*.mantis-ml_predictions.csv` outputs, averages `mantis_ml_proba` across the six cached classifier files to form a cached-output consensus, and uses `known_gene` flags to identify mantis-ml seeds; it does not train or rerun the stochastic procedure. The comparison uses the 16,821 genes present in both gene universes. The updated curated set contains 37 controls; 35 were present in the shared universe, and 33 were flagged as mantis-ml seeds. All benchmark metrics below are computed on the 35 shared controls. Because the original stochastic procedure was not rerun and its complete training configuration is not available in this repository, this is an exploratory cached-output comparison rather than an independently reproducible benchmark.

mantis-ml ranked these 35 controls at a median 99.7th percentile (33/35 in the top quartile, recall 88.6% at the top 5%, 91.4% at the top 10%, 94.3% at the top 20%, ROC-AUC 0.9551), compared with UsherPipe's 91.7th percentile (33/35 in the top quartile, recall 28.6%, 54.3%, and 77.1% at the same thresholds, AUC 0.8839) on the same shared universe. This is not a like-for-like estimate of novel-gene performance: mantis-ml is a seed-based learner, and 33 of the 35 shared controls were used as training seeds. Only two controls were not mantis-ml seeds, too few to support a meaningful held-out comparison. UsherPipe uses no seed genes, so its control recovery is less directly optimized but is still an internal diagnostic rather than an independent test.

The negative controls are more directly comparable, since housekeeping genes are seeds for neither tool. On the shared 16,821-gene universe, all 13 housekeeping genes were present; mantis-ml ranked them lower than UsherPipe (median percentile 82.3% versus 94.2%; Figure 8). Both shared-universe medians remain in the upper tail. The difference should therefore be interpreted as a limitation of the transparent six-layer score in this negative-control set, not as proof that either tool separates ubiquitous genes from disease candidates.

Taken together, the benchmark shows that the tools occupy distinct niches rather than establishing the superiority of either. mantis-ml's supervised design achieves strong recovery of known training labels but requires seed genes; UsherPipe provides a seed-free, transparent ranking for hypothesis generation. A fair comparison on genuinely held-out disease genes remains an important future evaluation.

---

## Discussion

### Comparison with existing approaches

UsherPipe occupies a distinct application niche among gene prioritization tools (Table 1). Unlike seed-gene-dependent methods (Endeavour, ToppGene), which may deprioritize candidates dissimilar to known disease genes, UsherPipe scores all protein-coding genes independently. Unlike patient-variant-centric tools (Exomiser, AMELIE), it operates without patient sequencing data, enabling hypothesis generation prior to cohort studies. And unlike cilia-specific databases (CiliaCarta, CilioGenics), it incorporates disease-specific tissue weighting and genetic constraint metrics to move from "Is this gene ciliary?" to "Is this gene an Usher candidate?"

The most informative comparison is with mantis-ml [26], which shares the genome-wide multi-evidence paradigm. The critical distinction lies in missing-data handling: mantis-ml drops features with high missingness and imputes remaining gaps with zeroes or medians depending on feature type. To illustrate the practical consequence, we re-scored our own gene set under zero imputation (Figure 6B) as a controlled simulation rather than a head-to-head reconstruction of mantis-ml. Several established Usher and ciliary controls lose percentile rank when localization is replaced by zero, whereas fully observed controls may move in the opposite direction. The effect is therefore a property of the missing-data policy, not evidence that every incompletely characterized gene is novel or disease-relevant. We additionally evaluated the cached mantis-ml predictions on a shared gene universe (Results, "Comparison with mantis-ml"), while recognizing that the seed-based comparator has limited held-out evaluation in this disease space. The comparisons against the remaining tools in Table 1 are conceptual, grounded in documented tool design.

### The NULL-aware design

The decision to preserve NULL values rather than impute them has a measurable impact on pipeline output. The current ablation artifact compares NULL-preserving, zero-imputed, and median-imputed scores using the same evidence table and records separate rank denominators for each treatment. Top-ranked candidates with sufficient evidence (≥4 layers) show relatively small changes in this snapshot, but this is not a guarantee under future source updates. The `evidence_count` field provides transparency: users can apply their own minimum-evidence thresholds, and should inspect evidence gaps before interpreting a high rank.

This design also enables progressive enrichment. As new data sources become available (e.g., expanded single-cell atlases for cochlear hair cells or improved proteomics coverage), genes previously scored on fewer layers can gain additional evidence without requiring retroactive correction of imputed values.

### Optional refinement versus exclusion

The post-hoc analyses show that tissue specificity and disease-cell expression are parallel prioritization axes rather than universal eligibility criteria. Hair-cell enrichment generated a tractable 16-gene experimental-priority group, while the dual sensory-cell intersection retained five; HPA-retina concordance was not evaluable because its threshold was unavailable. We therefore preserve the production HIGH tier and expose these refinements as optional annotations. Treating low or unavailable cell-type expression as hard negative evidence would reproduce the epistemic error that NULL-aware scoring was designed to avoid: low fetal cochlear expression does not establish absence of function in the adult cochlea, just as missing localization evidence does not establish absence from cilia.

### Limitations

Several limitations should be noted. First, NULL preservation operates at the inter-layer level, while some missing sub-components within individual layers are filled with zero; this compromise could be refined with partial-weight uncertainty estimates. The available-layer mean avoids an automatic missingness penalty but does not quantify uncertainty from reduced evidence coverage, and it is not a generative missing-data model. Second, housekeeping controls rank highly in the raw multi-evidence support score (median 94.8th percentile in the full scored universe, with 11 of 13 in the top quartile); the cilia-signal gate removes them from HIGH in this internal calibration set but does not correct the underlying ranking. This is a specificity failure, not an independent validation result. Third, CELLxGENE hair-cell data were unavailable in the local production inputs, and the optional HPA-retina threshold was also unavailable and is reported as NA rather than zero. The optional GSE135913 analysis uses two included fetal samples with marker-guided rather than author-curated cluster identities; the 23-week sample was excluded. Fourth, the disease-focused design has not been shown to have broad utility across diseases or phenotypes. The mantis-ml comparison is constrained by seed leakage and limited held-out evaluation, while comparisons with the remaining tools are conceptual rather than full matched-software benchmarks; we therefore do not claim general-purpose superiority. Finally, rankings are sensitive to the animal-model weight. Post-hoc internal grid-search and logistic-regression analyses improved separation of the selected controls but concentrated weight on the animal-model layer and substantially altered the genome-wide ranking (default-versus-logistic-regression rank ρ = 0.646); these analyses were not adopted as production weights because they risk control reuse and over-specialization.

### Future directions

Promising extensions include protein-protein interaction network analysis (leveraging the Usher protein interactome [49]), validation of the fetal GSE135913 signal against adult cochlear datasets with author-curated inner- and outer-hair-cell annotations, integration of cochlear hair-cell proteomics, and a web interface for interactive exploration of candidate gene evidence profiles. Experimental validation of top hypotheses (particularly VANGL2, ATP2B2, and DYNC1H1) through localization, perturbation, and sensory-cell assays would be required before assigning Usher relevance.

---

## Conclusions

UsherPipe provides genome-wide, seed-free prioritization for Usher syndrome and related ciliopathy hypotheses using six transparent evidence layers and explicit missingness. Internal recovery of 37 selected controls yielded a median percentile of 92.8%, with 35 of 37 in the top quartile and 56.8% recall at the top-10% threshold; this is not an independent sensitivity estimate. Weight perturbations produced a mean top-100 Spearman ρ of 0.8548 (range 0.6051–0.9770), with 16 of 24 perturbations stable, so the default weights should be treated as one biologically motivated configuration. The final report contains 62 HIGH, 9,673 MEDIUM, and 8,652 LOW candidates, including hypotheses such as DYNC1H1, VANGL2, and ATP2B2 that require experimental validation. The code, derived outputs, and provenance records are publicly available in the UsherPipe repository [50].

---

## List of abbreviations

CDS, coding sequence; gnomAD, Genome Aggregation Database; GO, Gene Ontology; GTEx, Genotype-Tissue Expression; HCOP, HUGO Gene Nomenclature Committee Comparison of Orthology Predictions; HPA, Human Protein Atlas; IMPC, International Mouse Phenotyping Consortium; LOEUF, loss-of-function observed/expected upper bound fraction; MANE, Matched Annotation from NCBI and EMBL-EBI; MGI, Mouse Genome Informatics; PPI, protein-protein interaction; USH, Usher syndrome; ZFIN, Zebrafish Information Network.

---

## Declarations

### Ethics approval and consent to participate
Not applicable. This study used only publicly available, de-identified, aggregate human-derived datasets and secondary database annotations; no participants were recruited, no identifiable information was accessed, and no new human specimens were collected.

### Consent for publication
No individual-level data, personal details, images, or videos are included in this manuscript; therefore, consent for publication is not applicable.

### Availability of data and materials

The analysis uses publicly available resources: mygene.info, Ensembl, gnomAD, GTEx, the Human Protein Atlas, CELLxGENE Census, NCBI gene2pubmed/PubMed, HCOP, MGI, ZFIN, IMPC, and the SYSCILIA SCGSv2 resource. The code, generated tables, figures, provenance records, and permitted derived artifacts needed to reproduce the reported analyses are publicly available in the UsherPipe repository.

- **Repository:** https://github.com/gbanyan/usher-exploring
- **Submitted code/data version:** https://github.com/gbanyan/usher-exploring/tree/4cf8c5b

The current reproducibility artifacts record configured data-version labels, the configuration hash, stage input/output counts, and the software environment in `data/report/reproducibility.json` and `data/report/reproducibility.md`; they provide incomplete source-level provenance, with six source records, six checksums, two URLs, two versions, and no retrieval times. Raw third-party inputs are not redistributed where excluded by source terms or size limits; their configured versions and recorded checksums are included where available.

### Competing interests
J-R.H. has personal lived experience of Usher syndrome but no financial competing interests. Y-H.C. and W-H.L. declare no competing interests.

### Funding
No specific funding was received for this study.

### Authors' contributions
J-R.H. led the conceptualization and methodology, developed and implemented the software, curated the data, conducted the formal analysis and investigation, generated the visualizations, and wrote the original draft. Y-H.C. contributed to the initial conceptualization, supervised the project, and revised and critically reviewed selected sections of the manuscript. W-H.L. supervised the project and revised and critically reviewed selected sections of the manuscript.

### Acknowledgements
Not applicable.

### Use of artificial intelligence tools
See the Methods section above. No AI system is listed as an author.

## Additional files

- **Additional file 1 (TSV):** `Additional_file_1_Table_S1.tsv`, merged gene symbols and retained canonical identifiers.
- **Additional file 2 (TSV):** `Additional_file_2_Table_S2.tsv`, genes excluded from the final tiered report.
- **Additional file 3 (TXT):** `Additional_file_3_Supplementary_Methods.txt`, supplementary methods and exploratory analyses.
- **Additional file 4 (JSON):** `Additional_file_4_Reproducibility_Manifest.json`, machine-readable reproducibility manifest.
- **Additional file 5 (TSV):** `Additional_file_5_Expression_Shortlist_Candidates.tsv`, expression-shortlist candidate-level annotations and exploratory flags.
- **Additional file 6 (TXT):** `Additional_file_6_Expression_Shortlist_Report.txt`, expression/protein shortlist exploration report.
- **Additional file 7 (TSV):** `Additional_file_7_Expression_Shortlist_Summary.tsv`, machine-readable retention and control-summary values underlying the optional strategy comparison.
- **Additional file 8 (TSV):** `Additional_file_8_GSE135913_Hair_Cell_Expression.tsv`, GSE135913 fetal cochlear hair-cell expression matrix and gene-level exploratory aggregates.
- **Additional file 9 (JSON):** `Additional_file_9_GSE135913_Provenance.json`, local-input provenance manifest with sample identifiers, relative input paths, SHA-256 checksums, marker-selection metadata, and exclusion information.
- **Additional file 10 (JSON):** `Additional_file_10_Checksum_Manifest.json`, checksums for the reproducibility artifacts and generated outputs.

---

## Figure legends

**Figure 1. UsherPipe pipeline architecture.** The four sequential stages of the pipeline: (1) gene-universe construction from the locally cached Ensembl 113 GTF input, with mygene.info used for annotation; (2) six separately computed evidence layers, each following a fetch–transform–load pattern; (3) NULL-aware composite scoring; and (4) report generation with validation. All pipeline state is held in a single DuckDB database (shown at right), which every stage reads from and writes to. The configured release label does not prove source immutability.

**Figure 2. Distribution of composite scores.** Stacked histogram of NULL-aware composite scores for the 18,387 tier-classified analysis labels, coloured by confidence tier (HIGH, MEDIUM, LOW); labels below the LOW threshold (composite score < 0.2) are excluded and not shown. Most analysis labels fall in the MEDIUM range, and the HIGH tier is a small shortlist at composite score ≥ 0.7 plus the cilia-signal gate.

**Figure 3. Evidence layer coverage.** Number of analysis labels with non-NULL evidence in each of the six evidence layers; the percentage above each bar is coverage relative to the current 20,081-label analysis universe (dashed line). NULL values are retained and are not interpreted as negative evidence.

**Figure 4. Per-layer evidence profiles of the top 25 candidates.** Heatmap of normalized layer scores (0–1) for the 25 highest-scoring genes with sufficient evidence (≥4 layers). Grey cells indicate missing evidence (NULL). An established Usher or SYSCILIA ciliary control appearing among the top candidates is marked with an asterisk or a plus sign, respectively.

**Figure 5. Internal control recovery.** Percentile-rank distributions for the nine established Usher genes, the 28 SYSCILIA ciliary genes, and a random sample of 500 background genes, shown as box plots with the controls also plotted as individual points. The dashed line marks the 75th percentile and the dotted line the median. The control set is curated and is not an independent validation cohort.

**Figure 6. Effect of missing-data handling on rankings.** (A) Distribution of percentile-rank shifts for labels with incomplete evidence under NULL-preservation relative to zero imputation and to median imputation; positive values indicate that NULL-preservation ranks the label higher. (B) Percentile rank of selected controls under the three imputation strategies (NULL-preserve, zero-impute, median-impute); the direction and magnitude of change depend on the control's evidence coverage and the rank denominator.

**Figure 7. Sensitivity of rankings to weight perturbation.** Spearman rank correlation and top-100 overlap metrics under 24 absolute weight-point perturbations (six layers, each changed by ±0.05 and ±0.10). Each raw delta was applied to one weight and then all six weights were renormalized, so the final change is not literally the raw delta and the other weights also change. Sixteen perturbations met ρ ≥ 0.85; mean ρ was 0.8548 and the range was 0.6051–0.9770. The animal-model layer was the most sensitive and the annotation layer the most robust; the top-100 Spearman statistic is conditional on overlapping genes.

**Figure 8. Exploratory benchmark against mantis-ml.** (A) Percentile-rank distributions of the 35 curated controls shared by both tools' gene universes (shared universe: 16,821 labels). (B) Cached-output consensus metrics from the six mantis-ml classifier CSVs and the UsherPipe score table: control median percentile (99.7% versus 91.7%), top-quartile fraction (94.3% versus 94.3%), recall at the 5%, 10%, and 20% thresholds (88.6%, 91.4%, 94.3% versus 28.6%, 54.3%, 77.1%), ROC-AUC (0.9551 versus 0.8839), and housekeeping-gene median percentile (82.3% versus 94.2%). mantis-ml is seed-based (33 of 35 shared controls are training seeds), whereas UsherPipe ranks labels without seed labels; no mantis-ml retraining or rerun was performed, and the comparison does not establish superiority on novel genes.

---

## References

[1] Boughman JA, Vernon M, Shaver KA. Usher syndrome: definition and estimate of prevalence from two high-risk populations. J Chronic Dis. 1983;36(8):595-603. doi:10.1016/0021-9681(83)90147-9.

[2] Géléoc GGS, El-Amraoui A. Disease mechanisms and gene therapy for Usher syndrome. Hear Res. 2020;394:107932.

[3] Gene Curation Coalition (GenCC). CIB2 gene–disease validity curation. Available from: https://search.thegencc.org/genes/HGNC%3A24579. Accessed 14 Aug 2026.

[4] Mathur P, Yang J. Usher syndrome: hearing loss, retinal degeneration and associated abnormalities. Biochim Biophys Acta. 2015;1852(3):406-420.

[5] Bonnet C, Riahi Z, Chantot-Bastaraud S, Smagghe L, Letexier M, Marcaillou C, et al. An innovative strategy for the molecular diagnosis of Usher syndrome identifies causal biallelic mutations in 93% of European patients. Eur J Hum Genet. 2016;24(12):1730-1738. doi:10.1038/ejhg.2016.99.

[6] Strande NT, et al. Evaluating the clinical validity of gene-disease associations: an evidence-based framework developed by the Clinical Genome Resource. Am J Hum Genet. 2017;100(6):895-906. doi:10.1016/j.ajhg.2017.06.002.

[7] Reiter JF, Leroux MR. Genes and molecular pathways underpinning ciliopathies. Nat Rev Mol Cell Biol. 2017;18(9):533-547. doi:10.1038/nrm.2017.60.

[8] Cosgrove D, Zallocchi M. Usher protein functions in hair cells and photoreceptors. Int J Biochem Cell Biol. 2014;46:80-89.

[9] Maerker T, et al. A novel Usher protein network at the periciliary reloading point between molecular transport machineries in vertebrate photoreceptor cells. Hum Mol Genet. 2008;17(1):71-86.

[10] Sahly I, et al. Localization of Usher 1 proteins to the photoreceptor calyceal processes, which are absent from mice. J Cell Biol. 2012;199(2):381-399.

[11] El-Amraoui A, Petit C. Usher I syndrome: unravelling the mechanisms that underlie the cohesion of the growing hair bundle in inner ear sensory cells. J Cell Sci. 2005;118(Pt 20):4593-4603.

[12] Lefèvre G, et al. A core cochlear phenotype in USH1 mouse mutants implicates fibrous links of the hair bundle in its cohesion, orientation and differential growth. Development. 2008;135(8):1427-1437.

[13] Schwander M, Kachar B, Müller U. The cell biology of hearing. J Cell Biol. 2010;190(1):9-20. doi:10.1083/jcb.201001138.

[14] Bahloul A, et al. Cadherin-23, myosin VIIa and harmonin, encoded by Usher syndrome type I genes, form a ternary complex and interact with membrane phospholipids. Hum Mol Genet. 2010;19(18):3557-3565.

[15] Wang H, et al. Temporal and spatial assembly of inner ear hair cell ankle link condensate through phase separation. Nat Commun. 2023;14(1):1657. doi:10.1038/s41467-023-37267-5.

[16] Yang J, et al. Ablation of whirlin long isoform disrupts the USH2 protein complex and causes vision and hearing loss. PLoS Genet. 2010;6(5):e1000955.

[17] Geng R, et al. The mechanosensory structure of the hair cell requires clarin-1, a protein encoded by Usher syndrome III causative gene. J Neurosci. 2012;32(28):9485-9498. doi:10.1523/JNEUROSCI.0311-12.2012.

[18] Nonarath HJT, et al. The USH3A causative gene clarin1 functions in Müller glia to maintain retinal photoreceptors. PLoS Genet. 2025;21(3):e1011205. doi:10.1371/journal.pgen.1011205.

[19] Kremer H, et al. Usher syndrome: molecular links of pathogenesis, proteins and pathways. Hum Mol Genet. 2006;15(Spec No 2):R262-R270. doi:10.1093/hmg/ddl205.

[20] Aerts S, Lambrechts D, Maity S, et al. Gene prioritization through genomic data fusion. Nat Biotechnol. 2006;24(5):537-544.

[21] Chen J, Bardes EE, Aronow BJ, Jegga AG. ToppGene Suite for gene list enrichment analysis and candidate gene prioritization. Nucleic Acids Res. 2009;37(Web Server issue):W305-W311.

[22] Smedley D, et al. Next-generation diagnostics and disease-gene discovery with the Exomiser. Nat Protoc. 2015;10(12):2004-2015.

[23] Birgmeier J, et al. AMELIE speeds Mendelian diagnosis by matching patient phenotype and genotype to primary literature. Sci Transl Med. 2020;12(544):eaau9113. PMID:32434849. doi:10.1126/scitranslmed.aau9113.

[24] van Dam TJP, et al. CiliaCarta: An integrated and validated compendium of ciliary genes. PLoS One. 2019;14(5):e0216705. doi:10.1371/journal.pone.0216705.

[25] Pir MS, et al. CilioGenics: an integrated method and database for predicting novel ciliary genes. Nucleic Acids Res. 2024;52(14):8127-8145. doi:10.1093/nar/gkae554.

[26] Vitsios D, Petrovski S. Mantis-ml: disease-agnostic gene prioritization from high-throughput genomic screens by stochastic semi-supervised learning. Am J Hum Genet. 2020;106(5):659-678. doi:10.1016/j.ajhg.2020.03.012.

[27] Xin J, et al. High-performance web services for querying gene and variant annotation. Genome Biol. 2016;17(1):91. doi:10.1186/s13059-016-0953-9.

[28] gnomAD Production Team. gnomAD v4.1 updates. gnomAD Browser. 2024 May 2. Available from: https://gnomad.broadinstitute.org/news/2024-05-gnomad-v4-1-updates/. Accessed 14 Aug 2026.

[29] Uhlén M, et al. Proteomics. Tissue-based map of the human proteome. Science. 2015;347(6220):1260419. doi:10.1126/science.1260419.

[30] GTEx Consortium. The GTEx Consortium atlas of genetic regulatory effects across human tissues. Science. 2020;369(6509):1318-1330. doi:10.1126/science.aaz1776.

[31] CZI Cell Science Program, Abdulla S, Aevermann B, et al. CZ CELLxGENE Discover: a single-cell data platform for scalable exploration, analysis and modeling of aggregated data. Nucleic Acids Res. 2025;53(D1):D886-D900. doi:10.1093/nar/gkae1142.

[32] Gene Ontology Consortium. The Gene Ontology resource: enriching a GOld mine. Nucleic Acids Res. 2021;49(D1):D325-D334.

[33] UniProt Consortium. UniProt: the Universal Protein Knowledgebase in 2023. Nucleic Acids Res. 2023;51(D1):D523-D531. doi:10.1093/nar/gkac1052.

[34] Kanehisa M, Goto S. KEGG: Kyoto Encyclopedia of Genes and Genomes. Nucleic Acids Res. 2000;28(1):27-30. doi:10.1093/nar/28.1.27.

[35] Gillespie M, et al. The reactome pathway knowledgebase 2022. Nucleic Acids Res. 2022;50(D1):D687-D692.

[36] Yates B, et al. Updates to HCOP: the HGNC comparison of orthology predictions tool. Brief Bioinform. 2021;22(6):bbab155. doi:10.1093/bib/bbab155.

[37] Blake JA, et al. Mouse Genome Database (MGD): knowledgebase for mouse-human comparative biology. Nucleic Acids Res. 2021;49(D1):D981-D987.

[38] Bradford Y, et al. Zebrafish information network, the knowledgebase for Danio rerio research. Genetics. 2022;220(4):iyac016. doi:10.1093/genetics/iyac016.

[39] Groza T, et al. The International Mouse Phenotyping Consortium: comprehensive knockout phenotyping underpinning the study of human disease. Nucleic Acids Res. 2023;51(D1):D1038-D1045. doi:10.1093/nar/gkac972.

[40] Sayers EW, et al. Database resources of the National Center for Biotechnology Information in 2023. Nucleic Acids Res. 2023;51(D1):D29-D38. doi:10.1093/nar/gkac1032.

[41] National Center for Biotechnology Information. GSE135913: single-cell RNA sequencing of mouse and human cochlea. Gene Expression Omnibus. Available from: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE135913. Accessed 14 Aug 2026.

[42] Bailly E, Walton A, Borg JP. The planar cell polarity Vangl2 protein: from genetics to cellular and molecular functions. Semin Cell Dev Biol. 2018;81:62-70. doi:10.1016/j.semcdb.2017.10.030.

[43] Henderson DJ, Phillips HM, Chaudhry B. Vang-like 2 and noncanonical Wnt signaling in outflow tract development. Trends Cardiovasc Med. 2006;16(2):38-45. doi:10.1016/j.tcm.2005.11.005.

[44] Kibar Z, et al. Contribution of VANGL2 mutations to isolated neural tube defects. Clin Genet. 2011;80(1):76-82.

[45] Harms MB, et al. Mutations in the tail domain of DYNC1H1 cause dominant spinal muscular atrophy. Neurology. 2012;78(22):1714-1720.

[46] Hertecant J, et al. A novel de novo mutation in DYNC1H1 gene underlying malformation of cortical development and cataract. Meta Gene. 2016;9:124-127. doi:10.1016/j.mgene.2016.05.004.

[47] Street VA, et al. Mutations in a plasma membrane Ca2+-ATPase gene cause deafness in deafwaddler mice. Nat Genet. 1998;19(4):390-394.

[48] Vasquez SSV, van Dam J, Wheway G. An updated SYSCILIA gold standard (SCGSv2) of known ciliary genes, revealing the vast progress that has been made in the cilia research field. Mol Biol Cell. 2021;32(21):br13.

[49] Linnert J, et al. Usher syndrome proteins ADGRV1 (USH2C) and CIB2 (USH1J) interact and share a common interactome containing TRiC/CCT-BBS chaperonins. Front Cell Dev Biol. 2023;11:1199069. doi:10.3389/fcell.2023.1199069.

[50] UsherPipe. Usher syndrome candidate-gene prioritization pipeline. GitHub repository. 2026. Available from: https://github.com/gbanyan/usher-exploring/tree/4cf8c5b. Accessed 15 Aug 2026.

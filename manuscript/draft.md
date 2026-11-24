# UsherPipe: an exploratory genome-wide multi-evidence pipeline for organizing gene-level hypotheses in Usher syndrome and related ciliopathies

**Article type:** Research Article

**Authors:** Jing-Rung Huang^1,\*^ (ORCID: 0000-0003-4776-3550); Yung-Hao Ching^2^ (ORCiD: 0000-0002-5767-6701; yching@gms.tcu.edu.tw); Wen-Hsiang Lu^1^ (ORCID: 0009-0002-5149-6790)

**Corresponding author:** Jing-Rung Huang, MD; gbanyan.huang@gmail.com; Department of Computer Science and Information Engineering, National Cheng Kung University, No. 1, University Road, Tainan 701, Taiwan. ORCID: 0000-0003-4776-3550

**Affiliations:** ^1^ Department of Computer Science and Information Engineering, National Cheng Kung University, No. 1, University Road, Tainan 701, Taiwan; ^2^ Department of Molecular Biology and Human Genetics, Tzu Chi University, No. 701, Sec. 3, Zhongyang Rd., Hualien City, Hualien County 970, Taiwan (R.O.C.).

---

## Abstract

### Background

Usher syndrome is the most common genetic cause of combined deafness-blindness, yet a subset of clinically diagnosed patients remains unresolved after testing. Existing tools make different design choices about prior disease genes, patient-specific data, and missing evidence. UsherPipe is an exploratory framework that organizes cilia- and sensory-relevant evidence across the protein-coding genome into gene-level hypotheses while preserving missingness explicitly; it is not a validated disease-gene predictor.

### Results

UsherPipe combines six evidence layers in a NULL-aware weighted mean over 20,081 protein-coding analysis labels. Scoring uses no training labels or similarity seeds; curated known-gene annotations remain inputs, and a downstream, control-calibrated gate defines a heuristic 62-gene HIGH tier. A retrospective temporal evaluation tested co-primary five- and six-layer historical analogues of the score on 45 provisionally literature-screened genes with later sensory/ciliopathy associations, 41 in the historical protein-coding universe. Neither version ranked any in the top 100 or assigned any to the historical HIGH tier; the four out-of-universe genes failed every endpoint. Top-10% recovery was 5/41 and 6/41, descriptively close to random ordering; median percentiles were 46.23 and 44.95. Subsequent human review flagged three cases with unresolved target-phenotype family evidence. The nine established Usher and 28 SYSCILIA controls had median raw percentiles of 97.8% and 91.9%, but housekeeping genes ranked at a median 94.8th percentile, demonstrating limited raw-score specificity. At top 100, the integrated score recovered 2/9 Usher and 1/28 SYSCILIA controls, whereas animal-only scoring recovered 4/9 and 11/28, and literature-only 2/9 and 21/28. Two Usher and one SYSCILIA control entered HIGH. Controls outranked publication/GO-matched unrelated-disease comparators in 88.9% and 85.7% of pairs, falling to 55.6% and 57.1% after post-outcome joint animal/literature omission. Only 41 default top-100 genes persisted across 25 weight configurations.

### Conclusions

UsherPipe is an exploratory framework for organizing cilia/sensory-related gene-level hypotheses in the Usher context. Its score is an evidence-support summary that blends general biological importance and research coverage with sensory/ciliary evidence, not a calibrated disease probability. Integration did not outperform the strongest single layers for the selected controls, and weak later-association recovery does not support reliable novel disease-gene discovery. Code, evidence profiles and derived replay inputs are available in the repository.

**Keywords:** Usher syndrome, ciliopathy, gene prioritization, missing data, bioinformatics pipeline, hypothesis generation

---

## Background

Usher syndrome (USH) is a major cause of hereditary combined deafness and blindness. Reported prevalence varies by population; Boughman et al. estimated 4.4 per 100,000 in the United States [1]. Patients present with sensorineural hearing loss, vestibular dysfunction, and progressive retinitis pigmentosa. Established clinical subtypes include USH1, USH2, and USH3, with validated gene–disease relationships involving *MYO7A*, *USH1C*, *CDH23*, *PCDH15*, *USH1G*, *USH2A*, *ADGRV1*, *WHRN*, and *CLRN1* [2]. *CIB2*, historically assigned to USH1J, is not treated as an established Usher gene here because current gene–disease curation is mixed [3], and is therefore excluded from the established positive-control set. These genes encode proteins that form multi-protein complexes in the stereocilia of inner ear hair cells and the connecting cilium of retinal photoreceptors [4]. In one European cohort, causal biallelic variants were identified in 92.7% of clinically diagnosed patients [5].

Even after comprehensive genomic screening—including targeted gene panels, whole-exome and whole-genome sequencing, and copy-number-variant analysis—the molecular cause remains unresolved for a subset of individuals with clinically diagnosed Usher syndrome. Possible explanations include novel disease genes, noncoding or deep intronic variants, complex structural variants, and regulatory alterations; the relative contribution of these mechanisms is not established here. A ranking score can organize hypotheses for follow-up, but absence of annotation or publication is not evidence that a gene is genuinely under-studied, nor is a high score evidence of a causal gene–disease relationship. Throughout, *candidate* refers only to a gene–disease relationship proposed in the literature but not yet established; genes ranked by UsherPipe are described as ranked genes or gene-level hypotheses (genes ordered by recorded evidence, without a claim of disease relevance), not candidates. This operational use is distinct from ClinGen's formal gene–disease validity classifications [6].

### Usher syndrome as a specialized sensory ciliopathy

Ciliopathies are inherited disorders of primary or motile cilia and their associated proteins [7]. They can alter signaling, sensory perception and fluid movement and can affect the retina, kidneys, nervous system, skeleton and other organs, producing overlapping isolated and multisystem phenotypes.

Several Usher proteins function in hair-cell stereociliary complexes and photoreceptor connecting-cilium or periciliary regions [8, 9, 10, 11]. This overlap with ciliary biology motivates considering Usher syndrome within the sensory ciliopathy spectrum [2, 4, 7], although stereocilia are actin-based structures rather than true cilia. General ciliary function alone does not establish a gene's involvement in the combined auditory–retinal phenotype.

### Ciliary and stereociliary biology underlying Usher syndrome

In the retina, the photoreceptor outer segment is a specialized primary cilium that lacks protein-synthesis machinery and depends on transport through the connecting cilium. Several Usher proteins localize to connecting-cilium, periciliary or calyceal-process regions and support compartmentalization, trafficking and outer-segment maintenance; their loss leads to progressive photoreceptor degeneration and retinitis pigmentosa [8, 9, 12].

In the inner ear, the mechanosensory hair bundle consists of actin-based stereocilia whose development is coordinated with the microtubule-based kinocilium. Usher protein complexes are essential for hair-bundle cohesion, orientation, maturation and mechanotransduction, and their dysfunction disorganizes the bundle and causes sensorineural hearing loss [10, 13, 14].

The shared molecular basis of the retinal and auditory phenotypes lies in the Usher interactome. USH1 proteins contribute to transient lateral links, tip-link-associated structures and their attachment to the stereociliary actin cytoskeleton, supporting hair-bundle cohesion, orientation and maturation [13, 15]. USH2 proteins, including usherin, ADGRV1, whirlin and PDZD7, form the ankle-link complex in developing hair cells. In photoreceptors, usherin, ADGRV1 and whirlin assemble at the periciliary membrane complex, where they are thought to support trafficking to the outer segment [9, 16, 11]. CLRN1 is required for hair-bundle organization [17]; a zebrafish *clrn1* model also implicated Müller glia in retinal maintenance [18]. Together, Usher proteins support adhesion, scaffolding, trafficking and sensory-cell compartmentalization [8, 19].

### Design choices in existing gene prioritization approaches

Computational gene prioritization has become a standard approach for narrowing gene lists in rare disease research. Existing approaches address different tasks, including variant interpretation, phenotype matching and similarity to previously characterized disease genes. UsherPipe makes different design choices for organizing genome-wide biological hypotheses; these differences do not establish that it identifies novel disease genes, or that it does so better than existing tools.

**Seed-gene-dependent tools.** Endeavour [20] and ToppGene [21] rank genes by functional similarity to a set of known disease genes (seed genes). While effective for diseases with well-characterized genetic architecture, this approach inherently favors genes that resemble known USH genes, and such genes may already have been investigated. Genes with distinct molecular functions or expression patterns may be deprioritized; avoiding similarity seeds does not itself establish improved novel-gene recovery.

**Patient-variant-centric tools.** Exomiser [22] and AMELIE [23] require patient sequencing data (VCF files) and phenotype descriptions as input. These tools excel at clinical diagnosis but are not designed to organize genome-wide gene hypotheses *before* patient data are available.

**Cilia-specific databases.** CiliaCarta [24] and CilioGenics [25] integrate multi-evidence data to predict whether a gene encodes a ciliary protein. CiliaCarta uses genomic, proteomic, transcriptomic, and evolutionary data in a Bayesian predictive score, while CilioGenics (published 2024) combines scRNA-seq, protein-protein interactions, comparative genomics, transcription-factor network analysis, and text mining. Neither published description documents the retina/proxy expression panel or the gnomAD constraint layer used here. Both tools ask whether a gene is ciliary, whereas UsherPipe organizes recorded sensory, ciliary and general evidence into gene-level hypotheses for the Usher context; neither framing establishes disease relevance.

**Genome-wide multi-evidence tools.** mantis-ml [26] is the closest genome-wide comparator, integrating over 1,200 features in a stochastic semi-supervised learning framework. Its published preprocessing discards features with more than 25% missingness and imputes remaining gaps with zero or feature medians, unlike UsherPipe's NULL-preserving score. The paper describes disease- and tissue-filtered feature categories but not an Usher-specific cilia-localization layer or the retina/proxy expression panel used here.

Table 1 summarizes documented feature categories across these approaches; a dash means that no explicit implementation of the named feature was located in the primary method description.

**Table 1. Comparison of gene prioritization approaches for rare disease research.**

| Feature | Endeavour | ToppGene | Exomiser | AMELIE | CiliaCarta | CilioGenics | mantis-ml | **UsherPipe** |
|---------|:---------:|:--------:|:--------:|:------:|:----------:|:-----------:|:---------:|:-------------:|
| Genome-wide screening | ✓ | ✓ | — | — | ✓ | ✓ | ✓ | **✓** |
| No user-supplied disease seeds | — | — | ✓ | ✓ | ✓ | ✓ | — | **✓** |
| Explicit retina/proxy expression layer | — | — | — | — | — | — | — | **✓** |
| Patient-variant (VCF) interpretation | — | — | ✓ | ✓ | — | — | — | **—** |
| Machine-learned scoring | — | — | — | ✓ | ✓ | — | ✓ | **—** |
| NULL-aware scoring | — | — | — | — | — | — | — | **✓** |
| Cilia/centrosome localization | — | — | — | — | ✓ | — | — | **✓** |
| gnomAD constraint | — | — | — | — | — | — | ✓ | **✓** |
| Animal model phenotypes | — | — | ✓ | — | — | — | ✓ | **✓** |
| Publication-volume normalization | — | — | — | — | — | — | — | **✓** |

Feature labels are intentionally narrow: for example, Exomiser's gnomAD allele-frequency features are not treated as gene-level constraint. Machine-learned marks cover documented learned or model-based scoring, including CiliaCarta's Bayesian predictive score; CilioGenics is not marked because its cited method description specifies no machine-learning model.

Here, we present UsherPipe, an exploratory bioinformatics pipeline that makes three explicit design choices: (1) genome-wide screening of protein-coding genes across six publicly available, partly overlapping evidence layers with cilia/sensory-related dimensions relevant to hypotheses in the Usher context (no training labels or similarity seeds required); (2) NULL-aware weighted scoring that preserves missing evidence rather than imputing it as negative evidence at the layer level; and (3) literature mining with publication-volume normalization that adjusts for raw publication count without removing research-intensity bias. The resulting composite is an exploratory evidence-support score; a control-calibrated cilia-signal gate defines a heuristic HIGH tier, but neither score nor tier is a clinical or causal assertion. We evaluate the ranking against internal controls, single-layer baselines and later-associated genes, and report where it falls short.

---

## Methods

### Study design and setting

This was a retrospective computational methods study. We built a transparent, NULL-aware framework that integrates public biological annotations genome-wide to organize gene-level hypotheses in Usher syndrome and related ciliopathies. We examined its control recovery, specificity, robustness, single-layer baselines and retrospective temporal behavior. The production analysis used locally cached inputs and a fixed protein-coding gene universe. Optional HIGH-tier annotations were evaluated after tier assignment and did not change production scores or tiers. We recruited no participants, collected no new human specimens and performed no animal experiments. We report no patient-level data.

### Architecture

UsherPipe is a modular Python (≥3.11) command-line pipeline with four sequential stages: (1) gene universe construction, (2) six separately computed evidence layers, (3) NULL-aware composite scoring, and (4) reporting with internal checks (Figure 1). Each layer follows a fetch–transform–load pattern that normalizes scores to the 0–1 interval and replaces its results in a single DuckDB database, so any layer can be re-executed independently. Implementation details and commands are in Supplementary Methods S7.

### Gene universe

The gene universe is loaded from the locally cached Ensembl 113 GRCh38 GTF input, with mygene.info [27] used for identifier annotation rather than as the authoritative universe. Strict filtering of `gene_biotype == protein_coding` gave 20,116 protein-coding IDs, which yielded 20,081 analysis labels after 35 duplicate-symbol consolidations. Named labels come from the GTF `gene_name` field or an exact-ID legacy-cache lookup and are not treated as validated current HGNC symbols; the 573 labels without a resolved name are Ensembl IDs. Scoring retains one record per label, preferring NCBI MANE Select mappings (v1.3), then gnomAD-recognized Ensembl IDs, then the lowest Ensembl ID. Additional file 1 (Table S1) lists the 35 merged-symbol mappings: 34 use MANE Select and one uses a subsequent fallback rule.

Additional files 2–14 are listed with their scopes at the end of the manuscript.

### Evidence layers

All layer scores are normalized to [0, 1]; NULL indicates missing evidence.

**gnomAD constraint (weight: 0.20).** Loss-of-function intolerance is quantified using the LOEUF metric (loss-of-function observed/expected upper bound fraction) from the locally cached input labeled gnomAD v4.1 [28]. Lower LOEUF values indicate stronger evolutionary constraint, suggesting functional importance. Scores are computed as the inverted normalization: *loeuf\_normalized* = (*LOEUF*_max − *LOEUF*) / (*LOEUF*_max − *LOEUF*_min). Genes for which gnomAD v4.1 reports no usable LOEUF estimate receive NULL scores rather than imputed values. The pipeline's coverage filter (mean depth below 30× or CDS coverage below 90%) could not be applied because the v4.1 constraint release lacks per-gene coverage fields.

**Tissue expression (weight: 0.20).** The production layer uses HPA [29] and GTEx v8 [30] data in a restricted panel, with retina and cerebellum as targets and testis and fallopian tube as backgrounds. Census photoreceptor expression [31] is ranked separately within the layer. To include neural expression context in the cilia-focused panel, we used cerebellum, which had measurements in both HPA and GTEx. This was a pragmatic proxy choice; it does not provide cochlear evidence. Quantitative enrichment and Tau are computed within source and restricted panel; ordinal HPA immunohistochemistry levels are not used as quantitative expression ratios or Tau inputs. The three components are enrichment percentile (0.4), mean available quantitative source Tau (0.3), and maximum target/source percentile (0.3), renormalized over available components. No production hair-cell measurements were available in the local Census inputs. Details and source coverage are in Supplementary Methods S3 and Results, “Expression dependence”.

**Functional annotation completeness (weight: 0.15).** The implemented score is 0.5 × normalized log₂(GO count + 1) [32] + 0.3 × UniProt annotation score/5 [33] + 0.2 × pathway presence from KEGG/Reactome through mygene.info [27, 34, 35]. Missing subcomponents contribute zero; only absence of all three produces NULL. This measures annotation depth.

**Subcellular localization (weight: 0.15).** HPA antibody-staining annotations are graded by ciliary proximity: direct cilia/centrosome/basal-body/transition-zone/stereocilia evidence scores 1.0, and recognized adjacent compartments score 0.5. Enhanced/Supported reliability receives a factor of 1.0; Approved/Uncertain receives 0.6. The latter are antibody-evidence categories, not computational predictions. Embedded curated cilia/centrosome lists supply a fallback proximity of 0.3. Recognized HPA reliability takes precedence for its evidence factor; compendium-only evidence receives 0.5. These are author-curated literal lists, not a downloaded CiliaCarta or proteomics dataset. Their original compilation dates, source assay tables and derivation from other ciliary lists are not documented. Exact symbols, alias rules and control overlaps are supplied in Additional file 11. Absence of usable localization evidence yields NULL; observed non-ciliary localization can be zero. The HIGH-tier cilia-signal gate (below) uses specific source flags, rather than any positive aggregate localization score.

**Animal model phenotypes (weight: 0.15).** HCOP [36] ortholog mappings link MGI/IMPC mouse [37, 38] and ZFIN zebrafish [39] sensory annotations. Distinct relevant mouse phenotype term names are unioned across MGI and IMPC. The score is (0.4 × mouse sensory-phenotype presence × mouse confidence + 0.3 × zebrafish sensory-phenotype presence × zebrafish confidence) multiplied by log₂(combined sensory count + 1)/log₂(global maximum combined count + 1), with confidence factors 1.0/0.7/0.4. The combined count sums distinct mouse terms and zebrafish counts. No ortholog yields NULL; a mapped ortholog with no relevant recorded phenotype can yield zero.

**Literature mining (weight: 0.15).** NCBI gene2pubmed [40] links genes to publications, intersected with cilia, sensory, cytoskeletal and polarity PubMed contexts (the sensory query includes Usher syndrome terms) (weights 2, 2, 1 and 1). Direct evidence requires a single PMID in both the experimental and cilia/sensory sets. Implemented tier precedence is direct experimental, high-throughput, functional, incidental, then none, with factors 1.0, 0.3, 0.6, 0.1 and 0. Raw contextual evidence is divided by log₂(total publications + 1), then positive values are rank-normalized. This adjusts one publication-volume dimension without removing ascertainment or research-intensity bias.

These layers are not independent: animal, localization and literature records can draw on shared studies. Their contributions and dependence are examined in Results.

### NULL-aware composite scoring

The composite score integrates all six layers using a weighted average computed only over layers with non-NULL scores:

*composite\_score* = Σ(*score*_i × *weight*_i) / Σ(*weight*_i), for all *i* where *score*_i ≠ NULL

The final weights are heuristic design choices, not fitted or demonstrated optimal values. Constraint and expression receive a modest five-percentage-point emphasis for general functional relevance and sensory-tissue plausibility; the other four layers receive equal weights. This rationale does not establish superiority over equal, animal-only or literature-only weighting. We retain the original configuration and report alternatives rather than select weights using the same controls. Weights (summing to 1.0) are: gnomAD 0.20, expression 0.20, annotation 0.15, localization 0.15, animal model 0.15, literature 0.15. The denominator normalizes by available weight, ensuring that a gene with evidence in only three layers is scored on those three layers alone, without penalty for missing data. The `evidence_count` field (0–6) records how many layers contributed, enabling downstream filtering by data completeness.

**What the composite measures.** The composite is a heuristically weighted mean of normalized values over the layers observed for a gene. It therefore reflects the average level of recorded support, not the amount of evidence: an observed zero enters the mean, a missing layer does not, and breadth is reported separately as `evidence_count`. Constraint and annotation depth are not specific to Usher or ciliary biology, and expression rests on retina, cerebellum-proxy and photoreceptor targets without cochlear data. The literature layer scores genes by publications in cilia, sensory, cytoskeletal and polarity contexts, including disease-name terms, and retains research-intensity bias. The score therefore blends general biological importance, research coverage and prior knowledge of known genes with tissue-context expression, ciliary-proximity localization and sensory animal-model phenotypes. It is an evidence-support summary for organizing hypotheses, not an estimate of disease relevance or probability.

Genes are classified into priority tiers: HIGH (composite ≥ 0.7, evidence ≥ 3 layers, and a cilia-signal gate; see below), MEDIUM (≥ 0.4, ≥ 2 layers), LOW (≥ 0.2), with remaining genes excluded. Quality flags summarize `evidence_count` (sufficient\_evidence ≥ 4, moderate ≥ 2, sparse ≥ 1).

The HIGH tier additionally requires a **cilia-signal gate**: a positive recorded source flag for cilia, centrosome, basal body, transition zone or stereocilia, membership in either embedded cilia/centrosome compendium, or an animal-model score of at least 0.1276571325 (the nearest-method 75th percentile of positive animal scores among the 20,081 retained labels). Adjacent-compartment evidence alone does not pass, and the broader reporting flag `has_cilia_signal` is not equivalent to this gate. Genes meeting the score and evidence thresholds but failing the gate are placed in MEDIUM. The gate is a post-hoc calibration filter that does not change composite scores or percentile ranks; because it was selected after inspection of control and housekeeping negative-control behavior, the housekeeping genes' absence from HIGH is an internal calibration result, not independent validation.

In this manuscript, **seed-free** means only that known disease/control genes were not used as training labels or similarity seeds; it does not mean knowledge-free or control-independent. Literature contexts include the disease name. Known-gene annotations enter the score: 26 of 28 SYSCILIA controls occur in the embedded ciliary compendium, which contributes both localization score and gate passage; none of the nine Usher controls occurs there. SYSCILIA recovery is therefore partly circular.

### Optional post-hoc shortlist refinement

The production pipeline stops at the 62-gene HIGH tier. Within HIGH, we evaluated optional annotations: Tau tissue specificity and fetal cochlear hair-cell expression from GSE135913 [41], whose aggregate was available for 61 of 62 HIGH labels. Hair-cell clusters were identified with a prespecified rule whose marker panel excluded Usher positive-control genes. These annotations did not alter composite scores or tiers and are exploratory, not validation; cluster selection, sensitivities and local-input provenance are in Additional file 3 (Supplementary Methods).

### Retrospective evaluation of historical analogues

We evaluated whether reconstructed pre-2021 evidence ranks genes with later human sensory or ciliopathy associations. The evidence cutoff was 31 December 2020, selected as the common boundary for the available dated archives; clinical ascertainment extended through 6 October 2026. The score design and control-calibrated gate were developed after the cutoff, so this is a retrospective temporal stress test rather than a prospectively developed predictor. Historical substitutions also prevent interpreting it as an exact production replay.

RetNet [42] and ten relevant PanelApp panels [43] supplied a catalog-based ascertainment frame. The Europe PMC REST API [44] supported gene/alias searches; primary reports were reviewed for the earliest public proposed target association, including preprints and online publication. Principal eligibility required a post-cutoff first proposed target association, genotype/phenotype evidence in at least two unrelated target-phenotype families, consistent inheritance, and functional support or replication in a new family. Principal cases were category A if the adopted audit located no earlier human disease report, and category B if it located one for another disease phenotype; earlier target candidates subsequently confirmed were classified separately as maturation. Original Usher/SYSCILIA development controls and three previously inspected pilot examples were excluded from principal recovery.

Source files, implementation, rules and 45 principal cases were fixed in Git before new ranking calculation. Cases were not selected using their scores, but modern production outputs were accessible in the workspace and the assessment was not blinded. The 45 principal clinical/date classifications were initially screened with AI assistance; the later, nonblinded human review of every case and the retained original denominators are described in Results and S6.6. This was not registered prospectively, and the adopted searches do not establish exhaustive clinical ascertainment.

The historical universe comprised 19,167 Approved protein-coding genes in the 1 October 2020 HGNC archive, scored from archived sources (gnomAD v2.1.1, HPA v20, GTEx v8, GO December 2020, archived MGI/IMPC/ZFIN and June 2020 gene2pubmed) with a photoreceptor feature reconstructed from original 2019 retinal matrices and author labels [45]. We evaluated two co-primary versions: five available layers without literature, and six layers with date-bounded Europe PMC MEDLINE context sets queried from modern title/abstract text, which retains possible post-cutoff revision bias. We used the production weights without fitting and executed 21 additional specified comparisons. Supplementary Methods S6.2–S6.3 detail source substitutions, date rules and a pre-outcome GTEx identifier repair; Additional file 12 provides all endpoints and sensitivities.

Top-K recovery used each scheme's full scored ranking with deterministic Ensembl tie-breaking; tie-inclusive and whole-tie boundary results are reported separately. Unscored eligible cases counted as failures in the historical-universe denominator, and the all-eligible denominator also retained out-of-universe cases as failures. HIGH was evaluated separately with production-compatible thresholds and a historical gate (S6.4); gate design remained control-informed. No verified clinical negative cohort was constructed, so clinical specificity, precision and false-positive rates were not estimated.

### Statistical analysis

Control/robustness diagnostics, comparator matching and temporal recovery analysis each used a protocol frozen before its new outcomes were calculated. The common-layer and joint-omission diagnostics of the matched pairs were post-outcome. Comparator selection and exact covariates are detailed in S5.

Except for the post-hoc GO tests, reported statistics are descriptive summaries of the stated gene universes and ascertained sets; no inferential *P* values were used to support causal or clinical claims. Percentile ranks were calculated within each comparison universe; temporal percentiles use ascending average tied ranks (S6.4), whereas production diagnostics use minimum tied ranks (S4). Rank robustness was summarized with Spearman correlation, top-K overlap and Jaccard similarity; coverage, medians, recall at stated thresholds and rank shifts were reported directly. Wilson 95% intervals summarize recovery within the nonrandom temporal cohort and are not population-level validation intervals. Post-hoc GO over-representation tests were one-sided; each analysis pooled BP/MF/CC terms for Benjamini–Hochberg adjustment (S8). A prospective power calculation was not applicable because the gene universe and control sets were defined by design rather than sampled.

### Reproducibility

We supply four canonical derived-input tables with schemas and SHA-256 hashes, an exact dependency lock and commands for numerical replay (Supplementary Methods S7). We rebuilt the database from the bundle and replayed control/robustness diagnostics, matched-comparator outcomes and the restricted pilot with its preserved historical inputs; the expanded temporal analogues were separately reconstructed from historical raw sources. These facilities reproduce reported numerical analyses, not the entire original raw acquisition. S7 also audits shortlist changes between a superseded output and the current output.

A YAML configuration, hashed with SHA-256, records data-source version labels (Ensembl 113, gnomAD v4.1, GTEx v8, HPA v23.0, CELLxGENE Census `2025-11-08`). These labels do not prove that upstream sources are immutable. Source provenance for the original production run is incomplete. `data/report/reproducibility.json` lists six source records and checksums but only two source URLs, two versions and no retrieval times. Missing fields were not inferred. The human-readable reproducibility report is in the repository, and the machine-readable manifest is Additional file 4.

### Use of artificial intelligence tools
OpenAI Codex (GPT-6) assisted code review, source acquisition, literature screening, clinical case/date classification, analysis implementation, integrity checks and document preparation. OpenAI gpt-6-astra (high reasoning) performed additional audits (protocol, clinical/date and numerical). Anthropic Claude Opus 5.5 and Fable 5.1 performed internal revision audits. In the second revision, Claude Opus 5.5 drafted the text edits, and Claude Fable 5.2, OpenAI GPT-6.2 Astra and Google Gemini 4 Neon independently reviewed the revision plan and the edited text. These are AI-agent checks, not human clinical adjudication or external peer review. After the frozen temporal analysis, human author review covered primary reports for all 45 cases (Results; S6.6). The authors retain responsibility for all content, analyses and interpretation; no AI system is an author.

---

## Results

### Pipeline output

Of the 20,081 analysis labels (Methods), 20,053 had non-NULL composite scores and 28 had no evidence in any layer. Tier classification assigned 18,387 analysis labels to a priority tier: 62 HIGH, 9,673 MEDIUM, and 8,652 LOW (Figure 2). The remaining 1,694 labels were excluded (1,666 with composite score < 0.2 and 28 with no evidence in any layer; Additional file 2, Table S2).

Coverage differs between evidence layers (Fig. 3); localization has a coverage gap, which reflects the limited availability of systematic subcellular localization data.

[Figure 3 near here]

### Optional refinement of the HIGH-tier shortlist

The optional expression/protein refinements produced different trade-offs (Table 2). Within the 62-gene HIGH tier, photoreceptor and fetal cochlear Q75 views each retained 16 genes and their intersection five; direct cilia/centrosome protein evidence retained 23, the OR strategy 34 and the AND strategy five. HPA-retina concordance was not evaluable because its threshold was unavailable in the local inputs. No optional view is promoted to a production gate, and exclusion from a view is not evidence against sensory relevance (S1; Additional files 5–9).

**Table 2. Optional post-hoc refinement of the 62-gene HIGH tier.**

Each strategy starts from the full HIGH tier rather than from another strategy's output; the Tau thresholds are nested within their own group.

| Refinement family | Alternative strategy | Genes retained | Established Usher controls retained among 2 present in HIGH | SYSCILIA controls retained among 1 present in HIGH |
|---|---|---:|---:|---:|
| Baseline | None (production HIGH tier) | 62 | 2/2 | 1/1 |
| Disease-cell enrichment | Fetal cochlear hair-cell expression ≥ Q75 | 16 | 2/2 | 0/1 |
| Disease-cell enrichment | Photoreceptor expression ≥ Q75 | 16 | 1/2 | 1/1 |
| Disease-cell enrichment | Hair-cell and photoreceptor expression ≥ Q75 | 5 | 1/2 | 0/1 |
| Disease-cell enrichment | Photoreceptor and HPA retina ≥ Q75 | NA | NA | NA |
| Protein/expression | Direct cilia/centrosome protein evidence | 23 | 0/2 | 1/1 |
| Protein/expression | Photoreceptor ≥ Q75 OR direct protein | 34 | 1/2 | 1/1 |
| Protein/expression | Photoreceptor ≥ Q75 AND direct protein | 5 | 0/2 | 1/1 |

### Highest-ranked genes (illustrative examples)

The genes below show how evidence profiles produce high ranks; they are illustrations of highly ranked hypotheses rather than candidates supported by independent evidence of Usher relevance. Given the weak temporal recovery and limited raw-score specificity, a high rank should not be read as predictive.

Among labels with at least four non-NULL layers, the highest-scoring entries in the current score table (legacy output file `candidates.tsv`) were DYNC1H1 (0.8001, six layers), VEGFA (0.7983, five layers), VANGL2 (0.7941, five layers), DYNC1LI1 (0.7899, six layers), and ATP1A1 (0.7888, five layers) (Figure 4). The next entries were ATP1B1 (0.7855), ATP2B2 (0.7853), PKD1 (0.7775), NEUROD1 (0.7692), and AHI1 (0.7672). Broad constraint, expression, annotation, and publication signals can elevate genes with no established Usher gene–disease relationship; the cilia-signal gate does not remove that limitation.

**VANGL2** shows how available-layer averaging treats a missing layer: its score (0.7941) combines strong animal-model, literature, expression, annotation and constraint signals with no automatic penalty for NULL localization, although the effect an observed localization value would have had is unknown. It is a planar-cell-polarity gene involved in developmental morphogenesis and noncanonical Wnt signaling [46, 47]; human evidence supports a susceptibility or multifactorial role in neural-tube defects rather than a highly penetrant monogenic Usher relationship [48].

**DYNC1H1**, the highest-scoring label with at least four observed layers, shows how broad constraint, annotation and literature signals, together with a localization score of 1.0, can rank an established non-Usher disease gene highly. It encodes the cytoplasmic dynein heavy chain and has established neurodevelopmental and neuromuscular disease associations [49, 50]; its score (0.8001) is supported across all six layers, including a literature score of 0.998, while the animal-model signal is modest. DYNC1H1 and ATP1A1 were also two of the three HIGH genes in the 420-gene comparator eligibility pool (see "Matched unrelated-disease comparators"). Although that pool excluded curated auditory, ocular or ciliary annotations, a later source audit found sensory overlap absent from those annotations.

**ATP2B2** (0.7853, five layers) is already associated with human progressive hearing impairment [51] and with hearing/vestibular phenotypes in mutant mice [52]. Given these established associations, its high rank is not a novel prediction.

Any human Usher relevance of these or other highly ranked genes would require independent genetic and experimental evidence.

### Internal control recovery

To assess internal recovery of biologically established genes (Figure 5), we evaluated 37 controls: nine established Usher genes (*ADGRV1, CDH23, CLRN1, MYO7A, PCDH15, USH1C, USH1G, USH2A,* and *WHRN*) and a curated subset of 28 well-characterized ciliary genes from the SYSCILIA Gold Standard v2 (SCGSv2) [53]. The full SCGSv2 resource contains 686 genes; this fixed subset was selected to span core ciliary functional categories and is therefore not an independent random validation sample. All 37 controls were present in the scored set. Weights were not fitted to these controls, but the cilia-signal gate was informed by control and negative-control behavior, so results are internal control recovery, not independent validation.

Among the 20,053 non-NULL labels, median raw percentile ranks were 97.77% for the nine Usher controls (9/9 in the top quartile) and 91.93% for the 28 SYSCILIA controls (26/28 in the top quartile). Final tiers were Usher: 2 HIGH/7 MEDIUM; SYSCILIA: 1 HIGH (*CEP290*)/27 MEDIUM. Neither group had LOW or excluded controls. All seven non-HIGH Usher genes failed composite ≥0.70; *WHRN* and *USH1G* additionally failed the gate. No Usher control failed the minimum three-layer criterion. Table 3 gives the complete Usher trace; the frozen control-trace table provides all 28 SYSCILIA traces.

**Table 3. Established Usher control recovery and final priority tiers.** Percentiles describe raw scores; passing the gate alone is insufficient for HIGH.

| Gene | Composite | Raw percentile | Layers | Gate passes | Tier |
|---|---:|---:|---:|:---:|---|
| ADGRV1 | 0.634564 | 97.67 | 6 | Yes | MEDIUM |
| CDH23 | 0.712617 | 99.64 | 5 | Yes | HIGH |
| CLRN1 | 0.526886 | 84.54 | 5 | Yes | MEDIUM |
| MYO7A | 0.671676 | 98.94 | 5 | Yes | MEDIUM |
| PCDH15 | 0.717960 | 99.72 | 5 | Yes | HIGH |
| USH1C | 0.527641 | 84.67 | 6 | Yes | MEDIUM |
| USH1G | 0.527175 | 84.61 | 5 | No | MEDIUM |
| USH2A | 0.688831 | 99.29 | 5 | Yes | MEDIUM |
| WHRN | 0.637145 | 97.77 | 5 | No | MEDIUM |

With the gate and minimum three-layer requirement fixed, score thresholds 0.60/0.65/0.70/0.75/0.80 yielded 366/170/62/11/1 HIGH labels, retaining 5/4/2/0/0 Usher and 6/1/1/0/0 SYSCILIA controls. These are descriptive threshold sensitivities, not selection of a revised optimum.

### Negative controls

Thirteen housekeeping genes (GAPDH, ACTB, B2M, UBC, PPIA, YWHAZ, HPRT1, TBP, SDHA, PGK1, RPLP0, RPL13A, RPL32) were evaluated as negative controls. Their median percentile rank was 94.8%, and 11 of 13 (84.6%) ranked in the top quartile. This is a specificity failure: the raw composite is not specific to Usher/ciliary biology and warrants cautious interpretation.

Per-layer analysis reveals why: housekeeping genes score high on non-specific layers (constraint and annotation) and on literature, reflecting strong evolutionary constraint, thorough functional characterization, and extensive publication history. Their median raw percentile remains high after gating; the gate only relabels tiers. Two housekeeping genes met the raw composite ≥0.70 threshold, but none remained HIGH after the cilia-signal gate. This is an internal specificity calibration result, not evidence that the gate generalizes to independent negative controls.

Distinct from the HIGH gate, the broader output flag `has_cilia_signal` marks labels with non-zero evidence in at least one cilia-specific layer (localization or animal model). Among the 9,673 MEDIUM-tier labels, those without it lack recorded direct cilia-specific evidence and warrant additional caution, not a negative interpretation.

The cilia-signal gate applies only to HIGH, not to the genome-wide ranking or MEDIUM, so the raw ranking remains available as a more permissive hypothesis list; the gate cannot recover genes whose cilia or sensory-model evidence is unavailable.

### Matched unrelated-disease comparators

Before outcome inspection, we froze a ClinGen Strong/Definitive disease-gene pool [54] with unambiguous HGNC mappings [55], excluding curated auditory, ocular and ciliary disease/phenotype annotations using HPO [56]; 418 of the 420 eligible genes had both matching covariates. Three unique comparators per control were matched on standardized log(1+x)-transformed publication and GO counts, without comparator reuse, giving 111 pairs: 27 comparators for the nine Usher controls and 84 for the 28 SYSCILIA controls (Supplementary Methods S5).

Comparator median raw percentiles were 64.21% and 60.30%, respectively, versus control medians 97.77% and 91.93%. Controls outranked comparators in 24/27 Usher pairs (88.9%) and 72/84 SYSCILIA pairs (85.7%). None of the 111 comparators entered HIGH, but 110 already failed the raw ≥0.70 threshold; only *GRIA2* was removed solely by the gate. Thus this comparison does not independently validate gate specificity. The full 420-gene pool contained three HIGH genes (*CRB2, ATP1A1, DYNC1H1*), retained after outcome inspection; a subsequent source audit identified sensory overlap absent from eligibility annotations. Lacking these annotations does not make pool genes biological negatives, and these counts are not a clinical false-positive rate.

A post-outcome diagnostic retained every frozen pair without rematching. Averaging each gene over its pair's shared observed layers preserved control advantage in 23/27 Usher and 75/84 SYSCILIA pairs. Leaving out animal evidence reduced concordance to 21/27 and 64/84; leaving out literature to 18/27 and 55/84; joint omission to 15/27 (55.6%) and 48/84 (57.1%). This demonstrates dependence on sensory-model/literature features and their curation, rather than independent novel-gene validity. All six leave-one-layer-out results and source-observation balances are reported in S5; common-layer comparisons are pair-dependent scores, not genome-wide ranks or AUCs.

### Impact of missing data handling

Replacing NULL with zero or with per-layer medians, using identical weights and evidence but separate rank denominators, redistributes percentile rank between well-covered and sparsely covered genes (Figure 6A–B). The effect on established genes is heterogeneous: USH1G and CLRN1 rank approximately 15 percentile points higher under NULL preservation, whereas several fully observed SCGSv2 controls rank higher under imputation. Among the top 25 genes with at least four layers, rank differences between strategies were within approximately ±1.0 percentile point in the numerical replay. Missing-data treatment therefore materially affects comparisons and should be reported rather than framed as universally beneficial; NULL preservation is not evidence that sparse-evidence genes are novel or disease-relevant.

All 62 HIGH labels had five or six observed layers (33 and 29, respectively), so raising the minimum to four or five layers retained all 62, whereas requiring six retained 29. Eight one-layer genes appeared in the raw top 100, all classified LOW. Composite score correlated positively with layer count (Spearman ρ=0.2402; n=20,053). These checks do not establish that scores averaged over few layers are unbiased. The largest observed layer correlation was annotation–literature (ρ=0.3704; n=19,114), followed by constraint–expression (0.3417) and constraint–literature (0.3341); modest correlations do not imply biological independence (S4).

### Sensitivity analysis

Each layer weight was perturbed individually by absolute steps of ±0.05 or ±0.10, and all six weights were renormalized (24 perturbations; Figure 7). Conditional Spearman correlation among genes in both the default and perturbed top-100 lists met ρ ≥ 0.85 in 16 of 24 perturbations (range 0.6051–0.9770); whole-universe statistics follow. Whole-universe correlation was lowest for the −0.10 literature perturbation (ρ=0.9598), and top-100 membership was lowest for the −0.10 localization perturbation (59 shared genes). The default weights are therefore one heuristic configuration, not an optimum.

Across equal weights plus the 24 perturbations, whole-universe rank correlations ranged from 0.9598 to 0.9994, yet only 8/25, 17/50 and 41/100 members of the default top-25, top-50 and top-100 shortlists persisted in all 25 configurations. These are frequencies over a finite configuration family, not inclusion probabilities. Equal weighting gave whole-ranking ρ=0.9952 and retained 86/100 default top-100 members. Six leave-one-layer-out rankings gave ρ=0.8867–0.9928 and retained 37–83 default top-100 members. High global correlations therefore coexist with substantial shortlist movement.

### Single-layer baselines

The integrated score did not outperform the strongest single layers for either internal control group. At top 100, the integrated score recovered two Usher and one SYSCILIA control, whereas animal-only scoring recovered four and eleven, and literature-only two and 21. Literature-only median percentiles were 99.13%/99.78%, with all nine Usher controls in its top 10%. Expression-only recovered neither group in the top 100; localization-only recovered no Usher and one SYSCILIA control, with only two Usher controls observed in that layer. Single-layer baselines rank only genes observed in that layer (S4). In the literature, localization and animal layers, and thus in the integrated score, known-control recovery depends on disease terms and curation. These internal comparisons therefore show neither that integration helps nor that any single layer predicts novel Usher genes. Logistic regression assigned 90.3% of the weight to animal evidence and substantially changed the full ranking (ρ=0.646). We retained the default weights because fitting and evaluation reused the selected controls (S2).

### Expression dependence

Expression supplied 15.5–27.5% of the weighted contribution for individual Usher controls. The stored source table contained no usable quantitative retinal observations from HPA or GTEx; HPA retinal protein measurements were observed for 112 universe IDs. Census photoreceptor values were observed for 20,078 of 20,116 IDs, including zeros. Without cochlear data, the production layer does not provide balanced evidence from both affected sensory systems.

Removing cerebellum and recomputing the implemented within-source transforms yielded whole-ranking ρ=0.9496 and a median absolute shift of 4.92 percentile points. HIGH decreased from 62 to 60 genes, retaining only 37: 25 left and 23 entered. *USH2A* and *MYO7A* entered, *CDH23* left and *PCDH15* remained. Quantitative background-tissue observations alone can still supply restricted-panel Tau when no retinal target is measured. Proxy choice thus affects both scores and shortlist membership; this is not evidence that either version better predicts Usher disease.

### Retrospective temporal evaluation

The expanded evaluation fixed 45 AI-assisted literature-screened later target associations before ranking. Subsequent human author review examined primary reports for every case, including families/pedigrees, phenotypes, inheritance, functional mechanisms and publication chronology. It identified family-evidence concerns involving *PDIA6* [57], *VWA8* [58] and *PLCG1* [59, 60], detailed in S6.6; eligibility of these flagged cases remains under review, and the original cohort and results are retained. Forty-one cases were in the historical protein-coding universe and all were scored; four noncoding genes (*RNU4-2, RNU6-2, RNU6-8, RNU6-9*) remained nonrecoveries in the 45-case end-to-end denominator. The five-layer version scored 19,157 of 19,167 historical genes; adding observed literature evidence, including zero, yielded 19,167 scored genes. These variants reconstruct historical analogues under a disclosed source contract (S6), not the complete modern production inputs.

Neither co-primary version recovered a principal case in the top 100 or historical HIGH tier (0/41, and 0/45 end-to-end); the descriptive Wilson 95% interval for 0/41 is 0–8.6%. Five- and six-layer top 1,000 recovery was 2/41 (4.9%) and 3/41 (7.3%), and top 10% recovery was 5/41 (12.2%) and 6/41 (14.6%) (Table 4; Figure 8). Median ascending score percentiles were 46.23/44.95. The five-layer top 1,000 cases were *TP73* (662) and *PLCG1* (879); the six-layer cases were *PLCG1* (474), *TP73* (629) and *SAXO6* (historical *MDM1*; 646). *PLCG1* represents a first target-domain association after another phenotype, not first-ever human disease association.

Genome-wide historical HIGH counts were zero/five in the five-/six-layer versions, limiting the information provided by that endpoint. Historical source substitutions affect score scale (S6). All 41 scored cases had at least four observed weighted layers, but none met composite ≥0.7 (maximum 0.506/0.562); zero HIGH recovery therefore cannot be attributed solely to the gate or evidence-count requirement. No principal case reached HIGH under any of the 23 schemes. Sensitivity analyses using localization alone or omitting its weight each recovered one case in the top 100. Full-ranking correlation between the two principal versions was 0.870708, with 57 shared top-100 genes. Detailed gate traces, control recovery and category A/B outcomes are provided in S6 and Additional file 12.

**Table 4. Later target-association recovery under historical analogues.** In-universe counts use 41 principal cases; end-to-end counts retain all 45. The four out-of-universe noncoding genes fail every endpoint. Top-percent cutoffs are rounded upward within each scheme's scored universe.

| Endpoint | Five layers, in universe | Six layers, in universe | Five layers, all eligible | Six layers, all eligible |
|---|---:|---:|---:|---:|
| Top100 | 0/41 | 0/41 | 0/45 | 0/45 |
| Top500 | 0/41 | 1/41 | 0/45 | 1/45 |
| Top1000 | 2/41 | 3/41 | 2/45 | 3/45 |
| Top1% | 0/41 | 0/41 | 0/45 | 0/45 |
| Top5% | 2/41 | 3/41 | 2/45 | 3/45 |
| Top10% | 5/41 | 6/41 | 5/45 | 6/45 |
| HIGH | 0/41 | 0/41 | 0/45 | 0/45 |

An earlier four-layer pilot with three manually selected examples, unavailable animal/literature layers and no historical HIGH evaluation is preserved in S6.1; those examples were not reused as principal cases.

### Biological scope of the temporal cohort

Human author review distinguished sensory involvement from a demonstrated ciliary disease mechanism. Examples include mitochondrial cardiolipin deficiency associated with *CRLS1* [61], retinal vascular disease associated with *CTNND1* [62], a dolichol-biosynthesis/glycosylation disorder associated with *DHRSX* [63], and spliceosomal RNA-associated retinal disease involving the RNU genes [64]. These cases reflect the prespecified broader sensory/ciliopathy target, rather than a cohort consisting entirely of new ciliopathy or Usher genes. A bounded audit of publication versions supported a date range wholly after the cutoff for each first public target report (S6.6).

In a separate post-hoc classification that left historical scores unchanged, all 45 cases had usable contemporary GO annotations (BP/MF/CC coverage 41/42/44). Overlapping generic-slim categories included cilium and mitochondrion (eight cases each), cilium organization (four) and mRNA metabolic process (five); these are functional descriptions, not clinical ciliopathy assignments. No term passed Benjamini–Hochberg FDR < 0.05, pooled across GO aspects, in the primary coding-case enrichment analysis or either protocol-specified secondary analysis (S8; Additional file 13, including Figure S1).

### Exploratory comparison with cached mantis-ml predictions

Of the 35 controls shared with the repository's cached mantis-ml v1.6.5 predictions [26], 33 were mantis-ml training seeds, so this comparison is exploratory and not held out. It uses the 16,821 genes present in both gene universes, without rerunning the stochastic training procedure. UsherPipe uses no training labels or similarity seeds, but its curated localization and literature annotations reuse known biology and its gate was control-calibrated. mantis-ml ranked the shared controls at a median 99.7th percentile versus 91.7th for UsherPipe. For the 13 housekeeping genes (seeds for neither tool), median percentiles were 82.3% for mantis-ml versus 94.2% for UsherPipe in the shared universe (94.8% in its production universe). UsherPipe's higher median reflects a specificity limitation of its six-layer score. Recall at fixed thresholds, ROC-AUC and the comparison figure are reported in Supplementary Methods S9 and Figure S2 (Additional file 14). This cached-output analysis is not a harmonized, seed-independent comparison, and the temporal evaluation did not include mantis-ml.

---

## Discussion

### What the integrated score does and does not provide

We have no evidence that integrating six layers improves recovery over the strongest single layer. At top 100, animal-only scoring recovered more Usher (4/9) and SYSCILIA (11/28) controls than the integrated score (2/9 and 1/28); literature-only tied it for Usher (2/9) and exceeded it for SYSCILIA (21/28). Because control recovery depends on curation, these within-set differences do not show how integration or any single layer would perform on new associations. The expanded temporal evaluation of later-associated genes gave little support for any variant. Neither co-primary version recovered a case in the top 100, two localization sensitivity analyses each recovered one, and no case reached the historical HIGH tier under any of the 23 schemes.

What integration provides is a single ordering with near-complete coverage and an inspectable profile. The composite scores 20,053 of 20,081 labels, whereas each single layer ranks only the genes it observes and localization has a coverage gap (Fig. 3). The output reports each gene's per-layer scores, `evidence_count`, `has_cilia_signal` and tier alongside its rank. This is a convenience, not a demonstrated gain in accuracy, and genes scored on few layers can still rank highly: eight one-layer genes reached the raw top 100. Each rank should therefore be read together with its per-layer profile. A rank driven by constraint, annotation and literature resembles the housekeeping pattern (median 94.8th percentile). Positive localization or animal-model evidence makes a rank more consistent with the intended cilia/sensory construct, although localization can reflect an adjacent compartment. Neither pattern has been shown to predict disease association: the co-primary historical analogues placed no later-associated case in the top 100, with top-10% recovery of 5/41 (five-layer) and 6/41 (six-layer).

### Comparison with existing approaches

UsherPipe makes different design choices from existing gene prioritization tools (Table 1); the comparison is conceptual and implies no performance advantage. It scores the protein-coding universe without disease similarity seeds, operates without patient sequencing data, and combines retina/proxy expression and genetic constraint with cilia/sensory evidence; these choices do not establish Usher-specific discrimination.

The closest genome-wide comparator, mantis-ml [26], uses seed-based machine learning, drops features with high missingness and imputes remaining gaps with zeroes or medians. Re-scoring with zero or median imputation (Figure 6B) is a controlled simulation of that step, not a reconstruction of mantis-ml. Under imputation, controls with missing localization can lose rank while fully observed controls can gain. These shifts reflect the missing-data policy and are not evidence that incompletely characterized genes are novel or disease-relevant. The cached-prediction comparison (Results, "Exploratory comparison with cached mantis-ml predictions"; S9) offers limited held-out information because most shared controls are mantis-ml seeds.

### The NULL-aware design

Preserving NULL values rather than imputing them measurably changes rankings (Figure 6). Although top-ranked genes with at least four layers shifted little in this snapshot, that behavior is not guaranteed to persist under future source updates. NULL preservation also allows incremental updates without retroactively correcting imputed values: genes scored on fewer layers can gain evidence as new sources become available, such as cochlear single-cell atlases or proteomics.

### Optional refinement versus exclusion

Tissue specificity and disease-cell expression are parallel annotation axes rather than universal eligibility criteria: within HIGH, upper-quartile fetal hair-cell expression retained a 16-gene exploratory subset, and adding upper-quartile photoreceptor expression retained five genes. We therefore keep the production HIGH tier and expose these refinements as optional annotations. Treating low or unavailable cell-type expression as negative evidence would repeat the absence-of-evidence error that NULL-aware scoring avoids: low fetal cochlear expression does not establish absence of adult cochlear function, just as missing localization does not establish absence from cilia.

### Limitations

The composite blends general importance and research coverage with cilia/sensory evidence, and publication-volume normalization cannot remove research-intensity bias; housekeeping genes illustrate the raw score's limited specificity (median raw percentile 94.8%). The gate changes HIGH labels without repairing raw ranks and was calibrated on the same controls used for internal recovery. HIGH is therefore a heuristic priority tier, not a calibrated confidence estimate. Independently validated novel Usher-gene discovery has not been demonstrated.

The matched comparison balances only two recorded covariates in a well-curated disease-gene pool. Controls and comparators differ in localization coverage and layer counts; common-layer diagnostics retain separation, but joint animal/literature removal markedly weakens it. Eligibility exclusions also target sensory annotations related to the score itself, and residual sensory overlap remained. This study does not isolate disease specificity from all ascertainment mechanisms, establish clinical specificity, or validate the HIGH threshold independently.

NULL preservation applies between layers; some within-layer absent subcomponents contribute zero. Available-layer averaging avoids an automatic missingness penalty but does not quantify uncertainty or guarantee comparability across evidence patterns. The historical pilot (S6.1) illustrates restricted tissue coverage and high-ranking genes with sparse evidence.

The expanded temporal analogues showed limited later-association recovery: neither co-primary version placed a principal case in the top 100, and their median percentiles were below 50; no principal case reached the historical HIGH tier under any scheme. For the five- and six-layer versions, top-1,000 recovery (2/41, 3/41) and top-10% recovery (5/41, 6/41) were descriptively close to random-ordering expectations of approximately 2.14 and 4.1 cases, respectively; this arithmetic comparison is not a formal null test. Post-cutoff method development, modern-text uncertainty, non-exhaustive catalog ascertainment and AI-assisted, nonblinded initial screening further limit interpretation (S6). Unconfirmed catalog records remain uncertain rather than clinical negatives. Human review covered all 45 cases after the frozen analysis; concerns about target-phenotype family evidence remain unresolved for three cases. The cohort concerns later sensory/ciliary associations, not newly discovered Usher associations.

Production expression excludes cochlear hair cells. Genes active in a narrow developmental window or primarily in auditory cells may be disadvantaged if retinal, proxy, animal or literature evidence is limited. Broad Census coverage including zeros does not resolve this gap. The fetal GSE135913 views are optional annotations in an already selected HIGH group, not independent validation; low fetal expression cannot exclude adult function. The cerebellum-removal analysis exposes meaningful proxy dependence and motivates future author-curated auditory atlases.

Finally, weighting materially changes shortlist membership despite high global correlations, and animal-only and literature-only baselines matched or exceeded the integrated score's top-100 control recovery (see "What the integrated score does and does not provide"). Logistic weight fitting reuses the controls and risks over-specialization, and the mantis-ml comparison uses cached predictions with 33/35 shared controls as training seeds. No optimal weighting or advantage for novel-gene discovery is established.

The human review and post-hoc GO classification describe functional heterogeneity but do not increase temporal recovery or explain it causally; GO annotation can neither establish nor exclude a ciliopathy mechanism, and no enrichment was FDR-significant.

### Future directions

Promising extensions include protein-protein interaction network analysis (leveraging the Usher protein interactome [65]), validation of the fetal GSE135913 signal against adult cochlear datasets with author-curated inner- and outer-hair-cell annotations, integration of cochlear hair-cell proteomics, and a web interface for interactive exploration of per-gene evidence profiles. A prospective evaluation, with rankings frozen before new gene–disease reports appear, would test predictive value directly.

---

## Conclusions

UsherPipe is an exploratory, NULL-aware framework for organizing cilia/sensory-related gene-level hypotheses in the Usher context. Its composite is an evidence-support summary that blends general importance and research coverage with sensory/ciliary evidence, not a calibrated disease probability. Integrating six layers did not outperform the strongest single layers on internal controls, and raw-score specificity was limited (housekeeping median 94.8%). The retrospective temporal analogues showed weak later-association recovery irrespective of variant. The 62-gene HIGH tier is a control-calibrated heuristic shortlist, and the framework does not establish reliable novel disease-gene prediction. It is intended to provide transparent per-gene evidence profiles that can be inspected and re-weighted; functional and clinical validation remain necessary. The repository [66] and Additional files 11/12 provide derived replay inputs, protocols and the complete diagnostic output families.

---

## List of abbreviations

CDS, coding sequence; gnomAD, Genome Aggregation Database; GO, Gene Ontology; GTEx, Genotype-Tissue Expression; HCOP, HUGO Gene Nomenclature Committee Comparison of Orthology Predictions; HPA, Human Protein Atlas; IMPC, International Mouse Phenotyping Consortium; LOEUF, loss-of-function observed/expected upper bound fraction; MANE, Matched Annotation from NCBI and EMBL-EBI; MGI, Mouse Genome Informatics; USH, Usher syndrome; ZFIN, Zebrafish Information Network.

---

## Declarations

### Ethics approval and consent to participate
Not applicable. This study used only publicly available, de-identified, aggregate human-derived datasets and secondary database annotations; no participants were recruited, no identifiable information was accessed, and no new human specimens were collected.

### Consent for publication
No individual-level data, personal details, images, or videos are included in this manuscript; therefore, consent for publication is not applicable.

### Availability of data and materials

The analysis uses publicly available resources: mygene.info, Ensembl, gnomAD (including historical v2.1.1), GO, UniProt, KEGG, Reactome, ClinGen, HGNC, HPO, Europe PMC, GSE135913, GTEx, the Human Protein Atlas, CELLxGENE Census, NCBI gene2pubmed/PubMed, HCOP, MGI, ZFIN, IMPC, the SYSCILIA SCGSv2 resource, RetNet, PanelApp and original GEO retinal datasets GSE137537/GSE137846. The code, generated tables, figures, available provenance and derived numerical replay inputs are available in the UsherPipe repository. Numerical replay is distinguished from complete raw-source regeneration (Supplementary Methods S7). Additional file 11 contains revision diagnostics and derived replay inputs; Additional file 12 contains the temporal protocols, clinical ledger, historical components, full results, source hashes and a dated summary of subsequent human review. Additional file 13 contains the contemporary GO classification, Figure S1, complete exploratory enrichment tables and verification records. Additional file 14 contains the exploratory mantis-ml comparison figure (Figure S2). Large third-party raw archives and local caches are not part of these bundles. An exact-version archive DOI has not been minted; the identified Git checkpoints and delivered-file hashes specify the versions.

- **Repository:** https://github.com/gbanyan/usher-exploring
- **Fixed second-revision release:** https://github.com/gbanyan/usher-exploring/tree/second-revision-20261124
- **First-revision author-review release:** https://github.com/gbanyan/usher-exploring/tree/major-revision-author-review-20261020-v2
- **Conservative revision checkpoint:** https://github.com/gbanyan/usher-exploring/tree/0e1634a
- **Expanded temporal analysis version:** https://github.com/gbanyan/usher-exploring/tree/736e16f
- **Original submitted public code/data version:** https://github.com/gbanyan/usher-exploring/tree/4cf8c5b
- **Preserved original submission files:** https://github.com/gbanyan/usher-exploring/tree/ed2d00d/submission/bmc_bioinformatics

The original submission artifacts record configured source versions, the configuration hash, stage counts and software environment in `data/report/reproducibility.json` and `data/report/reproducibility.md`. Original source-provenance gaps are described under Reproducibility. Raw third-party inputs excluded by source terms or size limits are not redistributed; recorded versions and checksums are supplied where available.

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

- **Additional file 1 (TSV):** `Additional_file_1_Table_S1.tsv`, merged gene symbols and retained analysis identifiers (not current canonical HGNC validation).
- **Additional file 2 (TSV):** `Additional_file_2_Table_S2.tsv`, genes excluded from the final tiered report.
- **Additional file 3 (TXT):** `Additional_file_3_Supplementary_Methods.txt`, supplementary methods and exploratory analyses.
- **Additional file 4 (JSON):** `Additional_file_4_Reproducibility_Manifest.json`, machine-readable reproducibility manifest.
- **Additional file 5 (TSV):** `Additional_file_5_Expression_Shortlist_Candidates.tsv`, expression-shortlist gene-level annotations and exploratory flags.
- **Additional file 6 (TXT):** `Additional_file_6_Expression_Shortlist_Report.txt`, expression/protein shortlist exploration report.
- **Additional file 7 (TSV):** `Additional_file_7_Expression_Shortlist_Summary.tsv`, machine-readable retention and control-summary values underlying the optional strategy comparison.
- **Additional file 8 (TSV):** `Additional_file_8_GSE135913_Hair_Cell_Expression.tsv`, GSE135913 fetal cochlear hair-cell expression matrix and gene-level exploratory aggregates.
- **Additional file 9 (JSON):** `Additional_file_9_GSE135913_Provenance.json`, local-input provenance manifest with sample identifiers, relative input paths, SHA-256 checksums, marker-selection metadata, and exclusion information.
- **Additional file 10 (JSON):** `Additional_file_10_Checksum_Manifest.json`, SHA-256 checksums of the actual delivered additional files 1–9 and 11–14; self-hashing is excluded.
- **Additional file 11 (ZIP):** `Additional_file_11_Revision_Diagnostics_and_Replay.zip`, numerical diagnostics, matched comparator records, preserved pilot and derived production replay inputs.
- **Additional file 12 (ZIP):** `Additional_file_12_Temporal_Evaluation.zip`, frozen temporal protocol, source inventory, clinical/date ledger, historical components, all 23 scheme outcomes and reconstruction code.
- **Additional file 13 (ZIP):** `Additional_file_13_Temporal_GO_Classification.zip`, contemporary functional classification workbook, Figure S1, complete enrichment tables, protocol, source manifests and numerical verification.
- **Additional file 14 (PDF):** `Additional_file_14_Figure_S2_mantis-ml_Comparison.pdf`, Figure S2, exploratory comparison with cached mantis-ml predictions (legend in Supplementary Methods S9).

---

## Figure legends

**Figure 1. UsherPipe pipeline architecture.** The four sequential stages of the pipeline: (1) gene-universe construction from the locally cached Ensembl 113 GTF input, with mygene.info used for annotation; (2) six separately computed evidence layers, each following a fetch–transform–load pattern; (3) NULL-aware composite scoring; and (4) reporting with internal checks. All pipeline state is held in a single DuckDB database (shown at right), which every stage reads from and writes to.

**Figure 2. Distribution of composite scores.** Stacked histogram of NULL-aware composite scores for the 18,387 tier-classified analysis labels, coloured by priority tier (HIGH, MEDIUM, LOW); labels below the LOW threshold (composite score < 0.2) are excluded and not shown. Most analysis labels fall in the MEDIUM range, and the HIGH tier is a small shortlist at composite score ≥ 0.7 plus the cilia-signal gate.

**Figure 3. Evidence layer coverage.** Number of analysis labels with non-NULL evidence in each of the six evidence layers; the percentage above each bar is coverage relative to the current 20,081-label analysis universe (dashed line). NULL values are retained and are not interpreted as negative evidence.

**Figure 4. Per-layer evidence profiles of the 25 highest-ranked genes with at least four observed layers.** Heatmap of normalized layer scores (0–1) for the 25 highest-scoring genes with sufficient evidence (≥4 layers). Grey cells indicate missing evidence (NULL). Among these genes, any established Usher control is marked with an asterisk, and any SYSCILIA ciliary control with a plus sign. A high rank is not evidence of Usher relevance.

**Figure 5. Internal control recovery.** Percentile-rank distributions for the nine established Usher genes, the 28 SYSCILIA ciliary genes, and a sample of 500 non-control scored background genes drawn without replacement with `numpy.random.default_rng(42)` after ordering eligible labels by retained Ensembl ID, shown as box plots with the controls also plotted as individual points. The dashed line marks the 75th percentile and the dotted line the median. The control set is curated and is not an independent validation cohort.

**Figure 6. Effect of missing-data handling on rankings.** (A) Distribution of percentile-rank shifts for labels with incomplete evidence under NULL-preservation relative to zero imputation and to median imputation; positive values indicate that NULL-preservation ranks the label higher. (B) Percentile rank of selected controls under the three imputation strategies (NULL-preserve, zero-impute, median-impute); the direction and magnitude of change depend on the control's evidence coverage and the rank denominator.

**Figure 7. Sensitivity of rankings to weight perturbation.** Spearman rank correlation and top-100 overlap metrics under 24 absolute weight-point perturbations (six layers, each changed by ±0.05 and ±0.10). Each raw delta was applied to one weight and then all six weights were renormalized, so the final change is not literally the raw delta and the other weights also change. Sixteen perturbations met ρ ≥ 0.85; mean ρ was 0.8548 and the range was 0.6051–0.9770. On conditional top-100 correlation, animal-model perturbations were the most sensitive and annotation perturbations the least sensitive; this ordering does not describe whole-universe correlation or shortlist overlap.

**Figure 8. Retrospective recovery of later target associations.** Five-layer archived and six-layer literature-augmented historical analogues evaluated the 41 principal cases in the 2020 protein-coding universe. Bars show deterministic top 100, top 1,000, top 10% and HIGH recovery; the numerators and denominator are labeled. Four additional noncoding cases remain failures in the 45-case end-to-end analysis (Table 4). Neither version recovers a principal case at top 100 or in the historical HIGH tier. These are retrospective source-analogue results, with post-cutoff method development and catalog-based ascertainment limitations.

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

[10] El-Amraoui A, Petit C. Usher I syndrome: unravelling the mechanisms that underlie the cohesion of the growing hair bundle in inner ear sensory cells. J Cell Sci. 2005;118(Pt 20):4593-4603.

[11] Yang J, et al. Ablation of whirlin long isoform disrupts the USH2 protein complex and causes vision and hearing loss. PLoS Genet. 2010;6(5):e1000955.

[12] Sahly I, et al. Localization of Usher 1 proteins to the photoreceptor calyceal processes, which are absent from mice. J Cell Biol. 2012;199(2):381-399.

[13] Lefèvre G, et al. A core cochlear phenotype in USH1 mouse mutants implicates fibrous links of the hair bundle in its cohesion, orientation and differential growth. Development. 2008;135(8):1427-1437.

[14] Schwander M, Kachar B, Müller U. The cell biology of hearing. J Cell Biol. 2010;190(1):9-20. doi:10.1083/jcb.201001138.

[15] Bahloul A, et al. Cadherin-23, myosin VIIa and harmonin, encoded by Usher syndrome type I genes, form a ternary complex and interact with membrane phospholipids. Hum Mol Genet. 2010;19(18):3557-3565.

[16] Wang H, et al. Temporal and spatial assembly of inner ear hair cell ankle link condensate through phase separation. Nat Commun. 2023;14(1):1657. doi:10.1038/s41467-023-37267-5.

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

[38] Groza T, et al. The International Mouse Phenotyping Consortium: comprehensive knockout phenotyping underpinning the study of human disease. Nucleic Acids Res. 2023;51(D1):D1038-D1045. doi:10.1093/nar/gkac972.

[39] Bradford Y, et al. Zebrafish information network, the knowledgebase for Danio rerio research. Genetics. 2022;220(4):iyac016. doi:10.1093/genetics/iyac016.

[40] Sayers EW, et al. Database resources of the National Center for Biotechnology Information in 2023. Nucleic Acids Res. 2023;51(D1):D29-D38. doi:10.1093/nar/gkac1032.

[41] National Center for Biotechnology Information. GSE135913: single-cell RNA sequencing of mouse and human cochlea. Gene Expression Omnibus. Available from: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE135913. Accessed 14 Aug 2026.

[42] RetNet, the Retinal Information Network. https://retnet.org/. Accessed 6 October 2026.

[43] Martin AR, Williams E, Foulger RE, et al. PanelApp crowdsources expert knowledge to establish consensus diagnostic gene panels. Nat Genet. 2019;51:1560-1565. doi:10.1038/s41588-019-0528-2.

[44] Europe PMC Consortium. Europe PMC: a full-text literature database for the life sciences and platform for innovation. Nucleic Acids Res. 2015;43(Database issue):D1042-D1048. doi:10.1093/nar/gku1061.

[45] Menon M, Mohammadi S, Davila-Velderrain J, Goods BA, Cadwell TD, Xing Y, et al. Single-cell transcriptomic atlas of the human retina identifies cell types associated with age-related macular degeneration. Nat Commun. 2019;10:4902. doi:10.1038/s41467-019-12780-8.

[46] Bailly E, Walton A, Borg JP. The planar cell polarity Vangl2 protein: from genetics to cellular and molecular functions. Semin Cell Dev Biol. 2018;81:62-70. doi:10.1016/j.semcdb.2017.10.030.

[47] Henderson DJ, Phillips HM, Chaudhry B. Vang-like 2 and noncanonical Wnt signaling in outflow tract development. Trends Cardiovasc Med. 2006;16(2):38-45. doi:10.1016/j.tcm.2005.11.005.

[48] Kibar Z, et al. Contribution of VANGL2 mutations to isolated neural tube defects. Clin Genet. 2011;80(1):76-82.

[49] Harms MB, et al. Mutations in the tail domain of DYNC1H1 cause dominant spinal muscular atrophy. Neurology. 2012;78(22):1714-1720.

[50] Hertecant J, et al. A novel de novo mutation in DYNC1H1 gene underlying malformation of cortical development and cataract. Meta Gene. 2016;9:124-127. doi:10.1016/j.mgene.2016.05.004.

[51] Smits JJ, Oostrik J, Beynon AJ, et al. De novo and inherited loss-of-function variants of ATP2B2 are associated with rapidly progressive hearing impairment. Hum Genet. 2019;138(1):61-72. doi:10.1007/s00439-018-1965-1.

[52] Street VA, et al. Mutations in a plasma membrane Ca2+-ATPase gene cause deafness in deafwaddler mice. Nat Genet. 1998;19(4):390-394.

[53] Vasquez SSV, van Dam J, Wheway G. An updated SYSCILIA gold standard (SCGSv2) of known ciliary genes, revealing the vast progress that has been made in the cilia research field. Mol Biol Cell. 2021;32(21):br13.

[54] ClinGen. Gene–disease validity expert-curated download. Export file date 6 Oct 2026. Available from: https://search.clinicalgenome.org/kb/gene-validity/download. Exact bytes and download-completion metadata retained in the revision source manifest.

[55] HGNC. Complete approved gene set. Live export frozen 6 Oct 2026. Available from: https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt. Exact snapshot retained in the revision replay package.

[56] Human Phenotype Ontology. Release v2026-09-01, ontology and gene-to-phenotype annotations. Available from: https://github.com/obophenotype/human-phenotype-ontology/releases/tag/v2026-09-01. Downloaded 6 Oct 2026.

[57] Al-Fadhli FM, Afqi M, Sairafi MH, Almuntashri M, Alharby E, Alharbi G, et al. Biallelic loss of function variant in the unfolded protein response gene PDIA6 is associated with asphyxiating thoracic dystrophy and neonatal-onset diabetes. Clin Genet. 2021;99(5):694-703. doi:10.1111/cge.13930.

[58] Umair M, Farooq Khan M, Aldrees M, Nashabat M, Alhamoudi KM, Bilal M, et al. Mutated VWA8 Is Associated With Developmental Delay, Microcephaly, and Scoliosis and Plays a Novel Role in Early Development and Skeletal Morphogenesis in Zebrafish. Front Cell Dev Biol. 2021;9:736960. doi:10.3389/fcell.2021.736960.

[59] Tao P, Han X, Wang Q, Wang S, Zhang J, Liu L, et al. A gain-of-function variation in PLCG1 causes a new immune dysregulation disease. J Allergy Clin Immunol. 2023;152(5):1292-1302. doi:10.1016/j.jaci.2023.06.020.

[60] Ma M, Zheng Y, Deng M, Lu S, Pan X, Luo X, et al. Heterozygous variants in PLCG1 affect hearing, vision, cardiac, and immune function. Elife. 2025;13:RP95887. doi:10.7554/eLife.95887.

[61] Lee RG, Balasubramaniam S, Stentenbach M, Kralj T, McCubbin T, Padman B, et al. Deleterious variants in CRLS1 lead to cardiolipin deficiency and cause an autosomal recessive multi-system mitochondrial disease. Hum Mol Genet. 2022;31(21):3597-3612. doi:10.1093/hmg/ddac040.

[62] Yang M, Li S, Huang L, Zhao R, Dai E, Jiang X, et al. CTNND1 variants cause familial exudative vitreoretinopathy through the Wnt/cadherin axis. JCI Insight. 2022;7(14):e158428. doi:10.1172/jci.insight.158428.

[63] Wilson MP, Kentache T, Althoff CR, Schulz C, de Bettignies G, Mateu Cabrera G, et al. A pseudoautosomal glycosylation disorder prompts the revision of dolichol biosynthesis. Cell. 2024;187(14):3585-3601.e22. doi:10.1016/j.cell.2024.04.041.

[64] Quinodoz M, Rodenburg K, Cvackova Z, Kaminska K, de Bruijn SE, Iglesias-Romero AB, et al. De novo and inherited dominant variants in U4 and U6 snRNA genes cause retinitis pigmentosa. Nat Genet. 2026;58(1):169-179. doi:10.1038/s41588-025-02451-4.

[65] Linnert J, et al. Usher syndrome proteins ADGRV1 (USH2C) and CIB2 (USH1J) interact and share a common interactome containing TRiC/CCT-BBS chaperonins. Front Cell Dev Biol. 2023;11:1199069. doi:10.3389/fcell.2023.1199069.

[66] UsherPipe. Usher syndrome candidate-gene prioritization pipeline. GitHub repository. 2026. Available from: https://github.com/gbanyan/usher-exploring/tree/second-revision-20261124. Fixed second-revision release, 24 Nov 2026; first-revision release major-revision-author-review-20261020-v2; original public code/data version 4cf8c5b; submitted files preserved at ed2d00d.

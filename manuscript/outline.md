# Historical planning outline (not a submission file)

> **Packaging status:** This outline is superseded by `manuscript/draft.md`. The current target is a BMC Bioinformatics **Research Article**, not a Software Article, because the present manuscript is a disease-focused computational study and does not yet establish the broad utility, direct comparative advance, reviewer-accessible release, or unrestricted non-commercial availability expected for a Software Article. Counts, software/licensing claims, and repository placeholders below are historical planning notes and must not override the current draft or a future production rerun.

**Target journal:** BMC Bioinformatics (Research Article)
**Word target:** 3,500–4,500 words (body text)
**Figures:** 5 figures + 2–3 tables

---

## Title Options

1. UsherPipe: a NULL-aware multi-evidence pipeline for prioritizing under-studied Usher syndrome and ciliopathy candidate genes
2. Genome-wide prioritization of under-studied Usher syndrome candidate genes through NULL-aware multi-evidence scoring
3. Systematic discovery of under-studied ciliopathy candidate genes using evidence-layer integration with missing-data preservation

---

## Structured Abstract (~300 words)

### Background
- Usher syndrome is the most common genetic cause of combined deafness-blindness
- ~10 known causative genes; some patients lack molecular diagnosis → unidentified genes likely exist
- Existing gene prioritization tools (Endeavour, ToppGene, Exomiser, AMELIE) rely on seed genes or impute missing data, systematically penalizing under-studied genes
- No tool specifically targets ciliopathy/Usher gene discovery with genome-wide coverage

### Results
- Present UsherPipe, a pipeline starting from 20,116 Ensembl 113 protein-coding IDs and producing 20,081 analysis labels across 6 orthogonal evidence layers; 573 unresolved names use ENSG fallback labels and the remaining names derive from GTF `gene_name` or exact-ID legacy-cache fallback, not validated current canonical HGNC symbols; public release and licensing remain AUTHOR ACTION items
- NULL-aware weighted scoring: missing evidence preserved as NULL (not imputed to zero); composite score computed only over available layers, preventing systematic penalization of under-studied genes
- Internal recovery: 37/37 selected Usher/ciliary controls are present, with median percentile 92.8%, 35/37 in the top quartile, and 56.8% recall at the top-10% threshold; this is not independent validation
- Pipeline identifies 62 HIGH, 9,673 MEDIUM, and 8,652 LOW analysis labels; sensitivity gives 16/24 stable perturbations, mean ρ 0.8548, range 0.6051–0.9770
- [KEY STATS: 18,387 analysis labels total, 20,053 non-NULL scores, 1,694 S2 exclusions]

### Conclusions
- UsherPipe enables systematic, reproducible discovery of under-studied Usher/ciliopathy candidate genes
- NULL-aware design specifically avoids the "streetlight effect" that plagues seed-gene-dependent tools
- [AUTHOR ACTION REQUIRED: add the public project URL, immutable archive, and confirmed license before making availability claims]

---

## 1. Background (~800 words)

### 1.1 Usher syndrome and unresolved genetics (~250 words)
- Clinical presentation: sensorineural hearing loss + retinitis pigmentosa
- 10 known genes (MYO7A, USH2A, CDH23, etc.) — cite OMIM
- Unresolved cases → motivation for new gene discovery
- Usher proteins localize to cilia/cilia-adjacent structures (connecting cilium, stereocilia)

### 1.2 Limitations of existing tools (~300 words)
- **Seed-gene-dependent tools** (Endeavour, ToppGene): rank by similarity to known disease genes → cannot discover genes dissimilar to known USH genes
- **Patient-variant-centric tools** (Exomiser, AMELIE): require patient sequencing data → not hypothesis-generating
- **Cilia databases** (CiliaCarta, CilioGenics): predict "is this a cilia gene?" but not "is this an Usher candidate?" — no disease-specific tissue weighting, no gnomAD constraint
- **mantis-ml** (closest competitor): genome-wide + multi-evidence, but imputes missing data with zero/median → systematically penalizes under-studied genes; no cilia localization layer

> **Table 1: Comparison of gene prioritization approaches**
> Columns: Tool | Genome-wide | Disease-specific | Under-studied targeting | NULL-aware | Cilia localization | Animal model phenotypes
> Rows: Endeavour, ToppGene, Exomiser, AMELIE, CiliaCarta, CilioGenics, mantis-ml, UsherPipe
> [SOURCE: novelty analysis from conversation]

### 1.3 Our contribution (~200 words)
- UsherPipe: genome-wide + Usher/cilia-specific + under-studied gene targeting
- NULL-aware weighted scoring preserves missing evidence
- Literature bias correction surfaces overlooked genes
- Reproducible and configurable; public release and licensing remain AUTHOR ACTION items

---

## 2. Methods (~1,200 words)

### 2.1 Architecture overview (~200 words)
- Python ≥3.11, Click CLI, DuckDB persistence, Polars data manipulation; current manifest records Python 3.13.1, Polars 1.43.2, DuckDB 1.5.5
- Pipeline stages: setup → 6 evidence layers → scoring → report → validation
- Each evidence layer: fetch → transform → load (idempotent, checkpoint-restart)
- **Figure 1: Pipeline architecture diagram** [to be drawn — not auto-generated]

### 2.2 Gene universe (~100 words)
- Locally cached Ensembl 113 GTF input → 20,116 protein-coding Ensembl IDs; the configured release label does not prove source immutability
- 35 duplicate-symbol consolidations → 20,081 analysis labels; 573 unresolved names use ENSG fallbacks, while remaining names derive from GTF `gene_name` or exact-ID legacy-cache fallback, not validated current canonical HGNC symbols
- Table S1 contains 35 merged-symbol mappings: 34 MANE Select canonical and one gnomAD-recognized-or-lowest-Ensembl fallback

### 2.3 Evidence layers (~500 words, ~80 words each)

#### gnomAD constraint (weight: 0.20)
- gnomAD v4.1 LOEUF scores; inverted normalization (lower LOEUF → higher score)
- Unavailable gnomAD LOEUF → NULL (not zero)

#### Tissue expression specificity (weight: 0.20)
- HPA v23 + GTEx v8; Tau tissue specificity index + Usher-tissue enrichment ratio
- Target tissues: retina, cerebellum, cochlea (proxy), photoreceptors
- Known limitation: GTEx v8 lacks retina → retina data from HPA only

#### Functional annotation (weight: 0.15)
- GO terms + UniProt annotation score + KEGG/Reactome pathway membership
- Inverse relationship with novelty: less annotation → potentially more novel

#### Subcellular localization (weight: 0.15)
- HPA immunofluorescence + CiliaCarta + cilia/centrosome proteomics
- Graded scoring: cilia/basal body = 1.0, cytoskeleton = 0.5, proteomics-only = 0.3
- Experimental vs. predicted evidence weighting
- Missing localization evidence remains NULL (not zero)

#### Animal model phenotypes (weight: 0.15)
- HCOP orthologs → MGI (mouse), ZFIN (zebrafish), IMPC phenotypes
- Sensory keyword filtering: hearing, vision, retina, stereocilia, vestibular, etc.
- Log-scaled to prevent annotation-rich genes dominating

#### Literature mining (weight: 0.15)
- PubMed via NCBI E-utilities; quality tiers (direct_experimental > functional_mention > HTS_hit > incidental)
- **Research bias correction**: raw_score / log₂(total_publications + 1)
- Key innovation: 5 cilia papers among 50 total → higher score than 5 among 100,000

### 2.4 NULL-aware composite scoring (~200 words)
- Formula: composite = Σ(score_i × weight_i) / Σ(weight_i) over non-NULL layers
- Weights must sum to 1.0; validated programmatically
- evidence_count tracks coverage per gene (0–6)
- Confidence tiers: HIGH (≥0.7 score, ≥3 layers, plus the post-hoc cilia-signal gate), MEDIUM (≥0.4, ≥2), LOW (≥0.2)
- Quality flags: sufficient_evidence (≥4), moderate (≥2), sparse (≥1)

### 2.5 Reproducibility infrastructure (~100 words)
- Config hashing (SHA-256), provenance sidecar JSONs per pipeline step
- Locally cached inputs with configured version labels (Ensembl 113, gnomAD v4.1, GTEx v8, HPA v23); labels do not prove source immutability
- DuckDB checkpoint-restart: literature layer resumes from partial progress

---

## 3. Results (~1,000 words)

### 3.1 Pipeline output overview (~200 words)
- 20,116 Ensembl IDs → 20,081 analysis labels after 35 duplicate-symbol consolidations, including 573 unresolved ENSG fallback labels
- 20,053 non-NULL composite scores; 18,387 analysis labels after tier filtering
- 62 HIGH, 9,673 MEDIUM, 8,652 LOW; 1,694 exclusions in Table S2 (1,666 score <0.2; 28 NULL composite)
- **Figure 2: Score distribution by confidence tier** [fig1_score_distribution]
- **Figure 3: Evidence layer coverage** [fig2_layer_coverage]

### 3.2 Top candidate genes (~300 words)
- **Figure 4: Top 25 candidates heatmap** [fig3_top_candidates_heatmap]
- Highlight current top sufficient-evidence entries: **DYNC1H1** (0.8001), **VEGFA** (0.7983), **VANGL2** (0.7941), **DYNC1LI1** (0.7899), **ATP1A1** (0.7888), **ATP1B1** (0.7855), **ATP2B2** (0.7853), **PKD1** (0.7775), **NEUROD1** (0.7692), and **AHI1** (0.7672)
- Current top-candidate values are descriptive model outputs, not disease evidence
- Na⁺/K⁺-ATPase subunit convergence: ATP1A1, ATP1A3, ATP1B1 all in top 25

### 3.3 Positive control validation (~200 words)
- 37 selected controls (9 established Usher + 28 SYSCILIA): 37/37 found
- Median percentile rank: 92.8%; 35/37 in the top quartile
- Top-10% recall: 56.8%; not an independent sensitivity estimate
- **Figure 5: Validation box plots** [fig4_validation_controls]

### 3.4 Negative controls and specificity (~150 words)
- 13 housekeeping genes: median 94.8%; 11/13 in the top quartile; 2 met raw composite ≥0.70 and 0 remained HIGH after the cilia-signal gate
- State plainly: this is a specificity failure, not independent validation

### 3.5 Sensitivity analysis (~150 words)
- 24 perturbations (6 layers × 4 deltas: ±5%, ±10%)
- Each raw delta is applied to one weight and all six weights are renormalized; the final change is not literally the raw delta and other weights change
- 16/24 stable (ρ ≥ 0.85); mean ρ 0.8548; range 0.6051–0.9770
- Most sensitive layer: animal model; most robust: annotation
- **Figure 6: Sensitivity heatmap** [fig5_sensitivity_heatmap]

> **Table 2: Validation summary**
> Positive controls: 37/37 present; median 92.8%; 35/37 top quartile; top-10% recall 56.8%
> Negative controls: specificity failure (median 94.8%; 11/13 top quartile; 2 raw composite ≥0.70; 0 gated HIGH)
> Sensitivity: 16/24 stable; mean ρ 0.8548; range 0.6051–0.9770

### 3.6 Optional post-hoc narrowing and benchmark notes
- Current HIGH shortlist: 62; GSE135913 local-only coverage 61/62; aggregate output restricted to 15,608 labels; the 23-week sample is excluded for insufficient marker separation
- Strategy sizes: photoreceptor 16, fetal hair-cell 16, concordant 5, HPA-retina concordant NA/not evaluable, direct protein 23, expression OR protein 34, expression AND protein 5
- Cached mantis-ml consensus uses the six tracked prediction CSVs on a shared 16,821-label universe; it is not retraining or a valid held-out benchmark
- Old-versus-new impact audit only: HIGH overlap: 54; old-only: 14; new-only: 8; shared-candidate ρ: 0.9881; the pre-rebuild run is contaminated and not a valid benchmark

---

## 4. Discussion (~600 words)

### 4.1 Comparison with existing tools (~200 words)
- vs. mantis-ml: NULL-aware vs zero-imputation; cilia-specific layers
- vs. CilioGenics/CiliaCarta: disease-specific scoring vs binary cilia classification
- vs. seed-dependent tools: can discover genes dissimilar to known USH genes
- Runtime is environment- and cache-dependent; do not state a fixed runtime without a recorded benchmark

### 4.2 The NULL-aware design choice (~150 words)
- Why missing ≠ zero matters for under-studied genes
- Evidence_count as transparency metric: users can filter by data completeness
- Enables progressive enrichment as new data sources become available

### 4.3 Limitations (~150 words)
- Negative control specificity: housekeeping genes score high
- GTEx retina gap; HPA gene_symbol alignment
- Literature layer rate-limited by NCBI E-utilities
- Weighted scoring is transparent but not learned — no ML optimization
- Single-writer DuckDB limits parallelism

### 4.4 Future work (~100 words)
- PPI network integration (USH protein interactome)
- Single-cell expression (CellxGene hair cells, photoreceptors) as dedicated layer
- Web interface for interactive exploration
- Experimental validation of top candidates

---

## 5. Conclusions (~150 words)
- UsherPipe addresses a specific gap: genome-wide, Usher/cilia-specific, under-studied gene prioritization
- NULL-aware scoring prevents systematic bias against poorly characterized genes
- Internally recovered 37 selected controls; specificity failure in housekeeping controls must remain explicit
- Top candidates (DYNC1H1, VEGFA, VANGL2, DYNC1LI1, ATP1A1, ATP1B1, ATP2B2) warrant experimental follow-up
- Reproducible, configurable weights for other rare diseases; broad utility and licensing require separate validation and author confirmation

---

## Availability and Requirements

- **Project name:** UsherPipe (usher-pipeline)
- **Project home page:** [GitHub URL]
- **Operating system(s):** AUTHOR ACTION REQUIRED: confirm supported/tested systems; current manifest does not record this field
- **Programming language:** Python ≥3.11 (current recorded runtime: 3.13.1)
- **Other requirements:** DuckDB ≥0.9, Polars ≥0.19, Click ≥8.1 (see pyproject.toml)
- **License:** [AUTHOR ACTION REQUIRED: add the complete license file and confirm the exact license]
- **Any restrictions to use by non-academics:** [AUTHOR ACTION REQUIRED: confirm after licensing and third-party data terms are settled]

---

## Figure/Table Summary

| # | Type | Content | Source |
|---|------|---------|--------|
| Fig 1 | Diagram | Pipeline architecture (6 layers → scoring → output) | Draw manually |
| Fig 2 | Histogram | Score distribution by confidence tier | fig1_score_distribution.pdf |
| Fig 3 | Bar chart | Evidence layer coverage (%) | fig2_layer_coverage.pdf |
| Fig 4 | Heatmap | Top 25 candidate per-layer scores | fig3_top_candidates_heatmap.pdf |
| Fig 5 | Box plot | Positive control validation | fig4_validation_controls.pdf |
| Fig 6 | Heatmap | Sensitivity analysis (Spearman ρ) | fig5_sensitivity_heatmap.pdf |
| Table 1 | Comparison | UsherPipe vs existing tools | Write from novelty analysis |
| Table 2 | Summary | Validation results (3 prongs) | validation_report.md |

---

## References to cite (~40–50)

### Core methods
- gnomAD v4.1: Karczewski et al. 2020 Nature
- HPA v23: Uhlén et al. 2015 Science
- GTEx v8: GTEx Consortium 2020 Science
- Gene Ontology: GO Consortium 2021 NAR
- UniProt: UniProt Consortium 2023 NAR
- MGI, ZFIN, IMPC: respective consortium papers
- SYSCILIA SCGSv2: van Dam et al. 2021 MBoC
- mygene.info: Xin et al. 2016 Genome Biol

### Competitor tools
- Endeavour: Tranchevent et al. 2016 NAR
- ToppGene: Chen et al. 2009 NAR
- Exomiser: Smedley et al. 2015 Nat Protoc
- AMELIE: Birgmeier et al. 2020 AJHG
- mantis-ml: Vitsios & Petrovski 2020 AJHG
- CiliaCarta: van Dam et al. 2019 PLoS Biol
- CilioGenics: Omer et al. 2024 NAR
- Van Sciver & Caspary 2024 DMM

### Under-studied gene resources
- PHAROS/IDG: Sheils et al. 2021 NAR
- FMUG: Stoeger et al. 2024 eLife
- Dark genome: Oprea et al. 2018 Nat Rev Drug Discov

### Usher syndrome
- Usher genetics review: Géléoc & El-Amraoui 2020 HMG (or latest review)
- USH interactome: Gießl et al. 2023 Front Cell Dev Biol

### Software stack
- DuckDB: Raasveldt & Mühleisen 2019 SIGMOD
- Polars: Vink 2023 (GitHub/docs citation)
- Click: Pallets Projects

---

## Writing Priority Order

1. **Table 1** (comparison) — anchors the Background novelty argument
2. **Methods** — most straightforward, maps directly to code
3. **Section 3 Results** — data is ready, just needs prose
4. **Section 1 Background** — requires most literature work
5. **Section 4 Discussion** — write after 1–3 are solid
6. **Abstract** — write last
# Submission note

> This is a planning outline, not the submission source. Its counts and candidate statistics are obsolete; use `manuscript/draft.md`, `data/report/reproducibility.md`, and the final generated tables for current values.

# Top-20 candidate analysis (current tracked score artifact)

**Pipeline version:** 0.1.0  
**Analysis state:** 20,116 Ensembl 113 protein-coding IDs yielded 20,081 analysis labels after 35 duplicate-symbol consolidations. 573 unresolved names use ENSG fallback labels; remaining names derive from the Ensembl GTF `gene_name` field or an exact-ID legacy-cache fallback, not validated current canonical HGNC symbols.  
**Scored labels with a non-NULL composite:** 20,053  
**Tier statistics:** HIGH 62 | MEDIUM 9,673 | LOW 8,652 | total 18,387  
**Control recovery:** 37/37 present; median percentile 92.8%; 35/37 in the top quartile; top-10% recall 56.8%  
**Negative controls:** median percentile 94.8%; 11/13 in the top quartile; 2 raw composite scores ≥0.70; 0 gated HIGH. This is a specificity failure.

This is a descriptive ranking snapshot, not a list of established Usher genes. A high composite score is not evidence of a causal gene–disease relationship, and missing evidence is not biological negative evidence. Candidate-specific evidence gaps should be reviewed before experimental selection. Version labels describe configured/local inputs but do not prove source immutability.

## Method

The table below contains the 20 highest-scoring entries with at least four non-NULL evidence layers, sorted by the current tracked `candidates.tsv` output. Scores use the NULL-aware weighted average over available layers; the final HIGH tier additionally applies the cilia-signal gate. The listed tier is the current gated tier, and these entries remain hypotheses for follow-up rather than validated disease genes.

## Top 20 by composite score

| Rank | Gene | Score | Layers | Tier |
|---:|---|---:|---:|---|
| 1 | DYNC1H1 | 0.8001006623 | 6/6 | HIGH |
| 2 | VEGFA | 0.7983100361 | 5/6 | HIGH |
| 3 | VANGL2 | 0.7941293436 | 5/6 | HIGH |
| 4 | DYNC1LI1 | 0.7898537923 | 6/6 | HIGH |
| 5 | ATP1A1 | 0.7888154800 | 5/6 | HIGH |
| 6 | ATP1B1 | 0.7854537542 | 5/6 | HIGH |
| 7 | ATP2B2 | 0.7853357577 | 5/6 | MEDIUM |
| 8 | PKD1 | 0.7775220878 | 5/6 | MEDIUM |
| 9 | NEUROD1 | 0.7691715872 | 5/6 | HIGH |
| 10 | AHI1 | 0.7671912466 | 6/6 | HIGH |
| 11 | HCN1 | 0.7619077084 | 5/6 | HIGH |
| 12 | PAFAH1B1 | 0.7564808775 | 6/6 | HIGH |
| 13 | DNM1 | 0.7562107963 | 5/6 | MEDIUM |
| 14 | ODF2 | 0.7535527938 | 6/6 | HIGH |
| 15 | ATP1A3 | 0.7525429539 | 5/6 | MEDIUM |
| 16 | MAPK8 | 0.7483355509 | 5/6 | HIGH |
| 17 | CCT5 | 0.7475621808 | 5/6 | HIGH |
| 18 | BDNF | 0.7471539895 | 5/6 | HIGH |
| 19 | ANK1 | 0.7446144767 | 5/6 | MEDIUM |
| 20 | NEDD4L | 0.7439019769 | 5/6 | HIGH |

## Interpretation guardrails

- DYNC1H1, DYNC1LI1, and PAFAH1B1 form a dynein/centrosome signal in the ranking, but their known human phenotypes are not equivalent to Usher syndrome.
- VEGFA and the ATP1A1/ATP1B1 pair are high-scoring computational entries; their appearance reflects multi-layer support and does not establish Usher involvement.
- VANGL2 is a mechanistic hypothesis for follow-up; current human evidence does not establish a highly penetrant monogenic Usher relationship.
- ATP2B2 remains biologically relevant because *Atp2b2* mutant mice have hearing and vestibular phenotypes, while a human Usher relationship remains unestablished.
- Housekeeping genes can still rank highly in the raw composite; this is a documented specificity limitation of the current weighting scheme.

All conclusions above require independent localization, perturbation, sensory-cell, and/or human genetic follow-up.

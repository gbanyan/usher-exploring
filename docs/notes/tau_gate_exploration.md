# HIGH-Tier Filtering Exploration

## Context

The pipeline produces **83 HIGH-tier candidates** (composite_score >= 0.7, evidence >= 3 layers, passing cilia-signal gate). The concern was whether 83 is too many — reviewer feedback might ask how we chose this specific set, and whether additional filters could produce a more defensible shortlist.

We explored multiple approaches to reduce the count without losing known disease genes (CDH23, CEP290, PCDH15, USH2A, MYO7A, etc.).

---

## 1. Support Count Confidence Gate

**Idea**: Require higher `evidence_count` for HIGH tier (e.g., >= 4 instead of >= 3).

**Result**: 83 → 63 (removes 20). Known Usher genes all have >= 4 layers, so none were lost.

**Why not adopted**: Support count is already used as a sub-threshold within HIGH eligibility. Raising it from 3→4 feels arbitrary; some valid candidates legitimately have 3 strong layers (e.g., high gnomAD + expression + annotation but lacking animal model). The tier system already encodes that score-weighted confidence.

---

## 2. Sensory Phenotype Count Gate

**Idea**: Require multiple sensory-specific animal model phenotypes (e.g., abnormal ear + abnormal retina morphology in at least one model organism).

**Result**: 83 → 68 (removes 15). Known Usher genes pass.

**Why not adopted**: Similar concern — penalizes genes whose animal models haven't been tested for sensory phenotypes. A gene could be retina-critical but never tested in zebrafish eyes. The data reflects experimental bias, not biology.

---

## 3. Tissue Expression Z-Score Gate

**Idea**: Filter by retina- or cochlea-specific expression z-score from GTEx.

**Problem**: GTEx v8 has "Eye - Retina" available only in the microarray dataset, not the RNA-seq dataset used by the pipeline. GTEx also lacks cochlea entirely. HPA expression data is categorical (0-3) and not z-score compatible. CellxGene hair-cell data is all NULL for tau_specificity due to missing metadata.

**Result**: Not feasible with current data sources.

---

## 4. Tau-Specificity Gate

**Idea**: Use `tau_specificity` (HPA tissue-specificity metric, 0=ubiquitous, 1=highly specific) as an additional HIGH-tier gate. Genes with broad expression (low tau) may be less likely to have tissue-specific disease phenotypes.

**Implementation**:

1. Added `tau_specificity` to `scored_genes` table (via `scoring/integration.py`)
2. Prototyped an optional `tau_threshold` parameter in `assign_tiers()` (`output/tiers.py`)
3. Prototyped a `--tau-threshold` option in `usher-pipeline report`; both were subsequently reverted so Tau remains informational rather than a production gate

**Results**:

| Threshold | HIGH count | Known Usher genes in HIGH | Demoted known |
|-----------|-----------|--------------------------|---------------|
| None | 83 | CDH23, CEP290, PCDH15, USH2A | — |
| >= 0.8 | 54 | PCDH15, USH2A | **CDH23** (0.783), **CEP290** (0.620) |
| >= 0.78 | 62 | CDH23, PCDH15, USH2A | **CEP290** (0.620) |
| >= 0.75 | 72 | CDH23, PCDH15, USH2A | **CEP290** (0.620) |
| >= 0.7 | 80 | CDH23, PCDH15, USH2A | **CEP290** (0.620) |

**Key problem**: Tau_specificity penalizes broadly expressed but biologically essential cilia proteins:
- **CEP290** (tau = 0.62) — transition zone protein, expressed in cilia across all tissues. Demoted at every threshold.
- **CDH23** (tau = 0.783) — Usher 1D, retina + hair-cell specific, but just under 0.8.
- At tau >= 0.7 only 3 genes are removed (83 → 80), making it minimally useful while still losing CEP290.

**Conclusion**: Not suitable as a hard gate for a ciliopathy-focused pipeline. Tau remains in the output as an informational column.

### Independent verification (current 83-gene output)

The threshold counts were re-computed directly from `scored_genes` after applying the production `assign_tiers()` logic:

- All 83 HIGH genes have non-NULL Tau values.
- Tau ≥0.70: 80 genes; Tau ≥0.75: 72; Tau ≥0.78: 62; Tau ≥0.80: 54.
- The four positive controls in HIGH are CDH23 (0.783074), CEP290 (0.620167), PCDH15 (0.967460), and USH2A (0.928984).
- CEP290 fails every tested threshold; CDH23 additionally fails 0.80.
- Although 53 `tissue_expression` gene IDs have duplicate rows, none has more than one distinct non-NULL Tau value, so the scoring aggregation does not alter these results.

---

## Final Decision

**No additional hard gate added to the HIGH tier.** The current 83 candidates stand, filtered by:
1. Composite score >= 0.7 (weighted NULL-aware average)
2. Evidence count >= 3 layers
3. Cilia-signal gate (ciliary localization OR top-quartile sensory animal-model phenotype)

The tiering system already encodes multiple signals; adding more gates risks overfitting to known genes while introducing data-source biases. The 83 candidates are a reasonable starting point for manual review.

## What Was Kept

- `tau_specificity` column in `scored_genes` table and output TSV/Parquet (useful for downstream analysis)
- `tau_specificity` in test fixtures (ensures schema compatibility)

## What Was Reverted

- `tau_threshold` parameter in `assign_tiers()`
- `--tau-threshold` CLI option
- Tau gate unit tests

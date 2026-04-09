# Comprehensive Validation Report

## 1. Positive Control Validation

**Status:** PASSED ✓

### Summary
- Known genes expected: 38
- Known genes found: 38
- Median percentile: 83.3%
- Top quartile count: 28
- Top quartile fraction: 73.7%

### Recall@k Metrics

| Threshold | Recall |
|-----------|--------|
| Top 100 | 0.0% |
| Top 500 | 7.9% |
| Top 1000 | 10.5% |
| Top 2000 | 26.3% |
| Top 10% | 23.7% |
| Top 20% | 57.9% |
| Top 5% | 7.9% |

### Per-Source Breakdown

| Source | Count | Median Percentile | Top Quartile |
|--------|-------|-------------------|--------------|
| omim_usher | 10 | 82.3% | 8 |
| syscilia_scgs_v2 | 28 | 83.3% | 20 |

**Verdict:** Known cilia/Usher genes rank highly (median >= 75th percentile), validating scoring system sensitivity.

## 2. Negative Control Validation

**Status:** FAILED ✗

### Summary
- Housekeeping genes expected: 13
- Housekeeping genes found: 13
- Median percentile: 92.4%
- Top quartile count: 12
- High-tier count (score >= 0.70): 0

**Verdict:** Housekeeping genes rank higher than expected, indicating potential lack of specificity.

## 3. Sensitivity Analysis

**Status:** STABLE ✓

### Summary
- Total perturbations: 24
- Stable perturbations (rho >= 0.85): 24
- Unstable perturbations: 0
- Mean Spearman rho: 0.9998
- Range: [0.9995, 1.0000]

- Most sensitive layer: annotation
- Most robust layer: expression

### Spearman Correlation by Perturbation

| Layer | Delta | Spearman rho | Stable? |
|-------|-------|--------------|---------|
| gnomad | -0.10 | 0.9995 | ✓ |
| gnomad | -0.05 | 0.9998 | ✓ |
| gnomad | +0.05 | 0.9997 | ✓ |
| gnomad | +0.10 | 0.9999 | ✓ |
| expression | -0.10 | 1.0000 | ✓ |
| expression | -0.05 | 1.0000 | ✓ |
| expression | +0.05 | 0.9999 | ✓ |
| expression | +0.10 | 0.9999 | ✓ |
| annotation | -0.10 | 0.9995 | ✓ |
| annotation | -0.05 | 0.9999 | ✓ |
| annotation | +0.05 | 0.9995 | ✓ |
| annotation | +0.10 | 1.0000 | ✓ |
| localization | -0.10 | 1.0000 | ✓ |
| localization | -0.05 | 0.9999 | ✓ |
| localization | +0.05 | 0.9999 | ✓ |
| localization | +0.10 | 0.9999 | ✓ |
| animal_model | -0.10 | 0.9997 | ✓ |
| animal_model | -0.05 | 0.9995 | ✓ |
| animal_model | +0.05 | 1.0000 | ✓ |
| animal_model | +0.10 | 1.0000 | ✓ |
| literature | -0.10 | 1.0000 | ✓ |
| literature | -0.05 | 0.9999 | ✓ |
| literature | +0.05 | 1.0000 | ✓ |
| literature | +0.10 | 0.9998 | ✓ |

**Verdict:** All weight perturbations (±5-10%) produce stable rankings (rho >= 0.85), validating result robustness.

## 4. Overall Validation Summary

**Status:** PARTIAL PASS (Specificity Issue)

**Verdict:** Known genes rank highly, but housekeeping genes also rank higher than expected. Scoring system is sensitive but may lack specificity. Review evidence layer weights.

| Validation Prong | Status | Verdict |
|------------------|--------|---------|
| Positive Controls | PASSED ✓ | Known genes rank high |
| Negative Controls | FAILED ✗ | Housekeeping genes rank high |
| Sensitivity Analysis | STABLE ✓ | Rankings stable under perturbations |

## 5. Weight Tuning Recommendations

**Recommendations for Weight Tuning:**

### 2. Housekeeping Gene Ranking Issue (Negative Controls)

Housekeeping genes rank higher than expected (median >= 50th percentile). This suggests lack of specificity - generic genes are scoring too highly.

**Suggested Actions:**
- Examine which evidence layers contribute high scores to housekeeping genes
- Consider reducing weights for generic layers (e.g., gnomad constraint, annotation)
- Increase weights for cilia-specific layers (localization, animal_model, literature)
- Review literature context weighting (ensure cilia-specific mentions prioritized)

---

### CRITICAL: Circular Validation Risk

**WARNING:** Any weight tuning based on these validation results constitutes "post-validation tuning" and introduces circular validation risk.

If weights are adjusted based on positive/negative control performance, the same controls CANNOT be used to validate the tuned weights (they were used to select the weights).

**Best Practices:**
1. If tuning weights: Use independent validation set or cross-validation
2. Document weight selection rationale (biological justification, not validation optimization)
3. Prefer a priori weight choices over post-hoc tuning
4. If tuning is essential, use hold-out validation genes not used in tuning

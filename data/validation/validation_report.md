# Comprehensive Validation Report

## 1. Positive Control Validation

**Status:** PASSED ✓

### Summary
- Known genes expected: 38
- Known genes found: 38
- Median percentile: 90.4%
- Top quartile count: 35
- Top quartile fraction: 92.1%

### Recall@k Metrics

| Threshold | Recall |
|-----------|--------|
| Top 100 | 10.5% |
| Top 500 | 23.7% |
| Top 1000 | 47.4% |
| Top 2000 | 57.9% |
| Top 10% | 52.6% |
| Top 20% | 86.8% |
| Top 5% | 44.7% |

### Per-Source Breakdown

| Source | Count | Median Percentile | Top Quartile |
|--------|-------|-------------------|--------------|
| omim_usher | 10 | 95.9% | 10 |
| syscilia_scgs_v2 | 28 | 90.0% | 25 |

**Verdict:** Known cilia/Usher genes rank highly (median >= 75th percentile), validating scoring system sensitivity.

## 2. Negative Control Validation

**Status:** FAILED ✗

### Summary
- Housekeeping genes expected: 13
- Housekeeping genes found: 13
- Median percentile: 94.2%
- Top quartile count: 11
- Meeting the HIGH-tier composite-score threshold (composite >= 0.70): 2
- In HIGH tier after cilia-signal gate: 0

**Verdict:** Housekeeping genes rank higher than expected, indicating potential lack of specificity.

## 3. Sensitivity Analysis

**Status:** UNSTABLE ✗

### Summary
- Total perturbations: 24
- Stable perturbations (rho >= 0.85): 17
- Unstable perturbations: 7
- Mean Spearman rho: 0.8806
- Range: [0.6019, 0.9906]

- Most sensitive layer: animal_model
- Most robust layer: annotation

### Spearman Correlation by Perturbation

| Layer | Delta | Spearman rho | Stable? |
|-------|-------|--------------|---------|
| gnomad | -0.10 | 0.7847 | ✗ |
| gnomad | -0.05 | 0.9402 | ✓ |
| gnomad | +0.05 | 0.9601 | ✓ |
| gnomad | +0.10 | 0.9202 | ✓ |
| expression | -0.10 | 0.8261 | ✗ |
| expression | -0.05 | 0.9523 | ✓ |
| expression | +0.05 | 0.9523 | ✓ |
| expression | +0.10 | 0.8795 | ✓ |
| annotation | -0.10 | 0.9016 | ✓ |
| annotation | -0.05 | 0.9751 | ✓ |
| annotation | +0.05 | 0.9906 | ✓ |
| annotation | +0.10 | 0.9644 | ✓ |
| localization | -0.10 | 0.7177 | ✗ |
| localization | -0.05 | 0.9070 | ✓ |
| localization | +0.05 | 0.9528 | ✓ |
| localization | +0.10 | 0.8840 | ✓ |
| animal_model | -0.10 | 0.6290 | ✗ |
| animal_model | -0.05 | 0.9031 | ✓ |
| animal_model | +0.05 | 0.8297 | ✗ |
| animal_model | +0.10 | 0.6019 | ✗ |
| literature | -0.10 | 0.8108 | ✗ |
| literature | -0.05 | 0.9510 | ✓ |
| literature | +0.05 | 0.9580 | ✓ |
| literature | +0.10 | 0.9417 | ✓ |

**Verdict:** Some perturbations produce unstable rankings (rho < 0.85), suggesting results may be sensitive to weight choices.

## 4. Overall Validation Summary

**Status:** PARTIAL PASS (Specificity Issue)

**Verdict:** Known genes rank highly, but housekeeping genes also rank higher than expected. Scoring system is sensitive but may lack specificity. Review evidence layer weights.

| Validation Prong | Status | Verdict |
|------------------|--------|---------|
| Positive Controls | PASSED ✓ | Known genes rank high |
| Negative Controls | FAILED ✗ | Housekeeping genes rank high |
| Sensitivity Analysis | UNSTABLE ✗ | Rankings unstable under perturbations |

## 5. Weight Tuning Recommendations

> **Note:** The recommendations below are automatically generated diagnostics, not the project's adopted course of action. The weight-learning question they raise was investigated directly (5-fold cross-validated grid search and penalized logistic regression; see `scripts/weight_tuning.py` and `scripts/weight_logreg.py`). Learned weights improve the control metrics but collapse the six-layer integration onto one or two layers, so the a priori biologically-motivated weights are retained by design and HIGH-tier specificity is addressed through the post-hoc cilia-signal gate. See the manuscript Discussion for the full analysis.

**Recommendations for Weight Tuning:**

### 2. Housekeeping Gene Ranking Issue (Negative Controls)

Housekeeping genes rank higher than expected (median >= 50th percentile). This suggests lack of specificity - generic genes are scoring too highly.

**Suggested Actions:**
- Examine which evidence layers contribute high scores to housekeeping genes
- Consider reducing weights for generic layers (e.g., gnomad constraint, annotation)
- Increase weights for cilia-specific layers (localization, animal_model, literature)
- Review literature context weighting (ensure cilia-specific mentions prioritized)

### 3. Weight Sensitivity Issue (Stability)

Ranking stability is compromised with 7 unstable perturbations. This means small changes in weights produce significant ranking shifts.

**Suggested Actions:**
- Most sensitive layer: **animal_model**
- Consider reducing weight of animal_model to improve stability
- Review layers with high instability (low Spearman rho across perturbations)
- Increase weights for robust layers (high Spearman rho)
- Consider smoothing evidence scores (e.g., log-transform, rank normalization)

---

### CRITICAL: Circular Validation Risk

**WARNING:** Any weight tuning based on these validation results constitutes "post-validation tuning" and introduces circular validation risk.

If weights are adjusted based on positive/negative control performance, the same controls CANNOT be used to validate the tuned weights (they were used to select the weights).

**Best Practices:**
1. If tuning weights: Use independent validation set or cross-validation
2. Document weight selection rationale (biological justification, not validation optimization)
3. Prefer a priori weight choices over post-hoc tuning
4. If tuning is essential, use hold-out validation genes not used in tuning

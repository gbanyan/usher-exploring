# Internal Evaluation and Control-Recovery Report

## 1. Internal Control Recovery

**Status:** MEETS REFERENCE ✓

### Summary
- Known genes expected: 37
- Known genes found: 37
- Percentile denominator (non-NULL scored genes): 20,053
- Median percentile: 92.8%
- Top quartile count: 35
- Top quartile fraction: 94.6%

### Recall@k Metrics

| Threshold | Recall |
|-----------|--------|
| Top 100 | 8.1% |
| Top 500 | 27.0% |
| Top 1000 | 37.8% |
| Top 2000 | 56.8% |
| Top 10% | 56.8% |
| Top 20% | 91.9% |
| Top 5% | 37.8% |

### Per-Source Breakdown

| Source | Count | Median Percentile | Top Quartile |
|--------|-------|-------------------|--------------|
| established_usher | 9 | 97.8% | 9 |
| syscilia_scgs_v2 | 28 | 91.9% | 26 |

**Interpretation:** The selected cilia/Usher controls show the expected internal recovery pattern. The control set is curated and the cilia-signal gate was informed by control behavior, so this is a diagnostic recovery check rather than an independent sensitivity estimate.

## 2. Negative Control Recovery

**Status:** BELOW REFERENCE ✗

### Summary
- Housekeeping genes expected: 13
- Housekeeping genes found: 13
- Percentile denominator (non-NULL scored genes): 20,053
- Median percentile: 94.8%
- Top quartile count: 11
- Top quartile fraction: 84.6%
- Meeting the HIGH-tier composite-score threshold (composite >= 0.70): 2
- In HIGH tier after cilia-signal gate: 0

**Verdict:** Housekeeping genes rank higher than expected, indicating potential lack of specificity.

## 3. Sensitivity Analysis

**Status:** UNSTABLE ✗

### Summary
- Total perturbations: 24
- Raw delta protocol: apply the displayed delta to one baseline weight first, then renormalize all six weights to sum to 1.0.
- Baseline six-weight vector: [gnomad=0.200000000000, expression=0.200000000000, annotation=0.150000000000, localization=0.150000000000, animal_model=0.150000000000, literature=0.150000000000]
- Stable perturbations (rho >= 0.85): 16
- Unstable perturbations: 8
- Mean Spearman rho: 0.8548
- Range: [0.6051, 0.9770]

- Most sensitive layer: animal_model
- Most robust layer: annotation

### Spearman Correlation by Perturbation

| Layer | Raw Delta | Spearman rho | Top-100 overlap | Jaccard | Stable? |
|-------|-------|--------------|-----------------|---------|---------|
| gnomad | -0.10 | 0.7752 | 84 | 0.724 | ✗ |
| gnomad | -0.05 | 0.9310 | 91 | 0.835 | ✓ |
| gnomad | +0.05 | 0.9447 | 94 | 0.887 | ✓ |
| gnomad | +0.10 | 0.9045 | 85 | 0.739 | ✓ |
| expression | -0.10 | 0.6969 | 78 | 0.639 | ✗ |
| expression | -0.05 | 0.9046 | 87 | 0.770 | ✓ |
| expression | +0.05 | 0.8934 | 89 | 0.802 | ✓ |
| expression | +0.10 | 0.7878 | 81 | 0.681 | ✗ |
| annotation | -0.10 | 0.9010 | 88 | 0.786 | ✓ |
| annotation | -0.05 | 0.9660 | 94 | 0.887 | ✓ |
| annotation | +0.05 | 0.9770 | 97 | 0.942 | ✓ |
| annotation | +0.10 | 0.9622 | 92 | 0.852 | ✓ |
| localization | -0.10 | 0.7170 | 59 | 0.418 | ✗ |
| localization | -0.05 | 0.9147 | 87 | 0.770 | ✓ |
| localization | +0.05 | 0.9402 | 93 | 0.869 | ✓ |
| localization | +0.10 | 0.8695 | 88 | 0.786 | ✓ |
| animal_model | -0.10 | 0.6070 | 78 | 0.639 | ✗ |
| animal_model | -0.05 | 0.8897 | 87 | 0.770 | ✓ |
| animal_model | +0.05 | 0.8299 | 86 | 0.754 | ✗ |
| animal_model | +0.10 | 0.6051 | 76 | 0.613 | ✗ |
| literature | -0.10 | 0.7386 | 78 | 0.639 | ✗ |
| literature | -0.05 | 0.8867 | 92 | 0.852 | ✓ |
| literature | +0.05 | 0.9463 | 91 | 0.835 | ✓ |
| literature | +0.10 | 0.9265 | 84 | 0.724 | ✓ |

### Final Normalized Six-Weight Vectors

Order: gnomad, expression, annotation, localization, animal_model, literature. Each vector is the final vector after renormalization.

| Layer | Raw Delta | Final normalized weights |
|-------|-----------|--------------------------|
| gnomad | -0.10 | [gnomad=0.111111111111, expression=0.222222222222, annotation=0.166666666667, localization=0.166666666667, animal_model=0.166666666667, literature=0.166666666667] |
| gnomad | -0.05 | [gnomad=0.157894736842, expression=0.210526315789, annotation=0.157894736842, localization=0.157894736842, animal_model=0.157894736842, literature=0.157894736842] |
| gnomad | +0.05 | [gnomad=0.238095238095, expression=0.190476190476, annotation=0.142857142857, localization=0.142857142857, animal_model=0.142857142857, literature=0.142857142857] |
| gnomad | +0.10 | [gnomad=0.272727272727, expression=0.181818181818, annotation=0.136363636364, localization=0.136363636364, animal_model=0.136363636364, literature=0.136363636364] |
| expression | -0.10 | [gnomad=0.222222222222, expression=0.111111111111, annotation=0.166666666667, localization=0.166666666667, animal_model=0.166666666667, literature=0.166666666667] |
| expression | -0.05 | [gnomad=0.210526315789, expression=0.157894736842, annotation=0.157894736842, localization=0.157894736842, animal_model=0.157894736842, literature=0.157894736842] |
| expression | +0.05 | [gnomad=0.190476190476, expression=0.238095238095, annotation=0.142857142857, localization=0.142857142857, animal_model=0.142857142857, literature=0.142857142857] |
| expression | +0.10 | [gnomad=0.181818181818, expression=0.272727272727, annotation=0.136363636364, localization=0.136363636364, animal_model=0.136363636364, literature=0.136363636364] |
| annotation | -0.10 | [gnomad=0.222222222222, expression=0.222222222222, annotation=0.055555555556, localization=0.166666666667, animal_model=0.166666666667, literature=0.166666666667] |
| annotation | -0.05 | [gnomad=0.210526315789, expression=0.210526315789, annotation=0.105263157895, localization=0.157894736842, animal_model=0.157894736842, literature=0.157894736842] |
| annotation | +0.05 | [gnomad=0.190476190476, expression=0.190476190476, annotation=0.190476190476, localization=0.142857142857, animal_model=0.142857142857, literature=0.142857142857] |
| annotation | +0.10 | [gnomad=0.181818181818, expression=0.181818181818, annotation=0.227272727273, localization=0.136363636364, animal_model=0.136363636364, literature=0.136363636364] |
| localization | -0.10 | [gnomad=0.222222222222, expression=0.222222222222, annotation=0.166666666667, localization=0.055555555556, animal_model=0.166666666667, literature=0.166666666667] |
| localization | -0.05 | [gnomad=0.210526315789, expression=0.210526315789, annotation=0.157894736842, localization=0.105263157895, animal_model=0.157894736842, literature=0.157894736842] |
| localization | +0.05 | [gnomad=0.190476190476, expression=0.190476190476, annotation=0.142857142857, localization=0.190476190476, animal_model=0.142857142857, literature=0.142857142857] |
| localization | +0.10 | [gnomad=0.181818181818, expression=0.181818181818, annotation=0.136363636364, localization=0.227272727273, animal_model=0.136363636364, literature=0.136363636364] |
| animal_model | -0.10 | [gnomad=0.222222222222, expression=0.222222222222, annotation=0.166666666667, localization=0.166666666667, animal_model=0.055555555556, literature=0.166666666667] |
| animal_model | -0.05 | [gnomad=0.210526315789, expression=0.210526315789, annotation=0.157894736842, localization=0.157894736842, animal_model=0.105263157895, literature=0.157894736842] |
| animal_model | +0.05 | [gnomad=0.190476190476, expression=0.190476190476, annotation=0.142857142857, localization=0.142857142857, animal_model=0.190476190476, literature=0.142857142857] |
| animal_model | +0.10 | [gnomad=0.181818181818, expression=0.181818181818, annotation=0.136363636364, localization=0.136363636364, animal_model=0.227272727273, literature=0.136363636364] |
| literature | -0.10 | [gnomad=0.222222222222, expression=0.222222222222, annotation=0.166666666667, localization=0.166666666667, animal_model=0.166666666667, literature=0.055555555556] |
| literature | -0.05 | [gnomad=0.210526315789, expression=0.210526315789, annotation=0.157894736842, localization=0.157894736842, animal_model=0.157894736842, literature=0.105263157895] |
| literature | +0.05 | [gnomad=0.190476190476, expression=0.190476190476, annotation=0.142857142857, localization=0.142857142857, animal_model=0.142857142857, literature=0.190476190476] |
| literature | +0.10 | [gnomad=0.181818181818, expression=0.181818181818, annotation=0.136363636364, localization=0.136363636364, animal_model=0.136363636364, literature=0.227272727273] |

**Verdict:** Some perturbations produce unstable rankings (rho < 0.85), suggesting results may be sensitive to weight choices.

## 4. Internal Evaluation Summary

**Status:** REFERENCE CHECKS PARTLY MEET THRESHOLDS (Control Separation Issue)

**Verdict:** Known genes rank highly, but housekeeping genes also rank higher than expected. The internal control-separation diagnostic indicates a specificity concern; review evidence layer behavior without tuning on these same controls.

| Evaluation Component | Status | Interpretation |
|------------------|--------|---------|
| Positive control recovery | MEETS REFERENCE ✓ | Known genes rank high |
| Negative control recovery | BELOW REFERENCE ✗ | Housekeeping genes rank high |
| Sensitivity analysis | UNSTABLE ✗ | Rankings unstable under perturbations |

## 5. Weight Tuning Recommendations

> **Note:** The recommendations below are automatically generated diagnostics, not the project's adopted course of action. The weight-learning question they raise was investigated directly (5-fold cross-validated grid search and penalized logistic regression; see `scripts/weight_tuning.py` and `scripts/weight_logreg.py`). Learned weights improve the control metrics but collapse the six-layer integration onto one or two layers, so the a priori biologically-motivated weights are retained by design and HIGH-tier specificity is addressed through the post-hoc cilia-signal gate.

**Recommendations for Weight Tuning:**

### 2. Housekeeping Gene Ranking Issue (Negative Controls)

Housekeeping genes rank higher than expected (median >= 50th percentile). This suggests lack of specificity - generic genes are scoring too highly.

**Suggested Actions:**
- Examine which evidence layers contribute high scores to housekeeping genes
- Consider reducing weights for generic layers (e.g., gnomad constraint, annotation)
- Increase weights for cilia-specific layers (localization, animal_model, literature)
- Review literature context weighting (ensure cilia-specific mentions prioritized)

### 3. Weight Sensitivity Issue (Stability)

Ranking stability is compromised with 8 unstable perturbations. This means small changes in weights produce significant ranking shifts.

**Suggested Actions:**
- Most sensitive layer: **animal_model**
- Consider reducing weight of animal_model to improve stability
- Review layers with high instability (low Spearman rho across perturbations)
- Increase weights for robust layers (high Spearman rho)
- Consider smoothing evidence scores (e.g., log-transform, rank normalization)

---

### CRITICAL: Control-Reuse / Post-Hoc Tuning Risk

**WARNING:** Any weight tuning based on these internal evaluation results is post-hoc tuning and introduces control-reuse risk.

If weights are adjusted based on positive/negative control performance, the same controls must not be treated as independent evidence for the tuned weights.

**Best Practices:**
1. If tuning weights: Use an independent hold-out/control set or cross-fold evaluation
2. Document weight selection rationale (biological justification, not control optimization)
3. Prefer a priori weight choices over post-hoc tuning
4. If tuning is essential, use hold-out control genes not used in tuning

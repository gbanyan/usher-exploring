# Phase 6: Validation - Research

**Researched:** 2026-02-12
**Domain:** Scoring system validation with positive/negative controls and sensitivity analysis
**Confidence:** HIGH

## Summary

Phase 6 validates the multi-evidence weighted scoring system developed in Phase 5. The validation strategy uses three complementary approaches: (1) positive control validation with known cilia/Usher genes (OMIM Usher syndrome genes and SYSCILIA SCGS v2), (2) negative control validation with housekeeping genes to ensure they are deprioritized, and (3) sensitivity analysis via parameter sweeps to assess rank stability of top candidates under varying weight configurations.

The existing codebase (Phase 5) already implements positive control validation infrastructure (`validation.py`, `known_genes.py`) that computes percentile ranks using `PERCENT_RANK()` window functions and validates median percentile >= 75th percentile threshold. This phase extends validation with negative controls and systematic parameter sweeps.

**Primary recommendation:** Use scipy for statistical analysis (Spearman rank correlation, percentile calculations), implement systematic weight grid searches to test rank stability, compile curated housekeeping gene negative controls, and generate comprehensive validation reports with multiple metrics (recall@k, median percentile, rank correlation) to assess scoring system robustness.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scipy | >=1.14 | Statistical tests, rank correlation, percentile calculations | Industry standard for scientific computing, mature spearmanr() implementation |
| polars | >=0.19.0 | Fast DataFrame operations for validation metrics | Already used throughout pipeline, excellent performance |
| duckdb | >=0.9.0 | SQL analytics for percentile ranking | Already integrated, powerful window functions |
| structlog | >=25.0 | Structured logging of validation results | Consistent with existing pipeline logging |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| matplotlib | >=3.8.0 | Validation plots (rank stability, score distributions) | Already in dependencies for visualization |
| seaborn | >=0.13.0 | Statistical visualization | Already in dependencies, clean default aesthetics |
| pytest | >=7.4.0 | Validation test suite | Already in dev dependencies for testing |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| scipy.stats.spearmanr | pandas.DataFrame.corr(method='spearman') | scipy more explicit, better documentation, returns p-value |
| Grid search (manual) | scikit-learn GridSearchCV | sklearn overkill for simple weight sweeps, adds dependency |
| DuckDB window functions | Polars window expressions | DuckDB already integrated, SQL more readable for complex ranking |

**Installation:**
```bash
# Core dependencies already installed
# No new packages required for validation
```

## Architecture Patterns

### Recommended Project Structure
```
src/usher_pipeline/scoring/
├── validation.py           # Positive control validation (exists)
├── known_genes.py          # Known gene compilation (exists)
├── negative_controls.py    # NEW: Housekeeping gene negative controls
├── sensitivity_analysis.py # NEW: Parameter sweep and rank stability
└── validation_report.py    # NEW: Comprehensive validation reporting
```

### Pattern 1: Positive Control Validation (Existing)
**What:** Validate known cilia/Usher genes rank highly (top quartile)
**When to use:** After computing composite scores, before tier assignment
**Example:**
```python
# Source: Existing codebase validation.py
def validate_known_gene_ranking(
    store: PipelineStore,
    percentile_threshold: float = 0.75
) -> dict:
    """
    Compute PERCENT_RANK window function across ALL genes.
    Validate median percentile >= threshold for known genes.
    """
    query = """
    WITH ranked_genes AS (
        SELECT
            gene_symbol,
            composite_score,
            PERCENT_RANK() OVER (ORDER BY composite_score) AS percentile_rank
        FROM scored_genes
        WHERE composite_score IS NOT NULL
    )
    SELECT rg.gene_symbol, rg.composite_score, rg.percentile_rank, kg.source
    FROM ranked_genes rg
    INNER JOIN _known_genes kg ON rg.gene_symbol = kg.gene_symbol
    ORDER BY rg.percentile_rank DESC
    """
    result = store.conn.execute(query).pl()
    median_percentile = float(result["percentile_rank"].median())
    validation_passed = median_percentile >= percentile_threshold
    return {
        "median_percentile": median_percentile,
        "validation_passed": validation_passed,
        "known_gene_details": result.head(20).to_dicts()
    }
```

### Pattern 2: Negative Control Validation (NEW)
**What:** Validate housekeeping genes are deprioritized (NOT in top quartile)
**When to use:** After positive control validation, to ensure low-score filtering works
**Example:**
```python
# Pattern for negative control validation
def validate_negative_controls(
    store: PipelineStore,
    percentile_threshold: float = 0.50  # Should be BELOW median
) -> dict:
    """
    Compile housekeeping genes and validate they rank LOW.
    Inverse of positive control: median percentile SHOULD be < threshold.
    """
    # Load housekeeping gene list
    housekeeping_df = compile_housekeeping_genes()

    # Same ranking query as positive controls
    query = """
    WITH ranked_genes AS (
        SELECT gene_symbol, composite_score,
               PERCENT_RANK() OVER (ORDER BY composite_score) AS percentile_rank
        FROM scored_genes
        WHERE composite_score IS NOT NULL
    )
    SELECT rg.gene_symbol, rg.composite_score, rg.percentile_rank
    FROM ranked_genes rg
    INNER JOIN _housekeeping_genes hk ON rg.gene_symbol = hk.gene_symbol
    ORDER BY rg.percentile_rank ASC  -- Lowest ranks first
    """
    result = store.conn.execute(query).pl()
    median_percentile = float(result["percentile_rank"].median())

    # INVERTED logic: validation passes if housekeeping genes rank LOW
    validation_passed = median_percentile < percentile_threshold

    return {
        "median_percentile": median_percentile,
        "validation_passed": validation_passed,
        "top_quartile_count": result.filter(pl.col("percentile_rank") >= 0.75).height,
        "housekeeping_gene_details": result.head(20).to_dicts()
    }
```

### Pattern 3: Parameter Sweep with Rank Correlation (NEW)
**What:** Systematic weight grid search to assess rank stability
**When to use:** After baseline validation, to test sensitivity to weight changes
**Example:**
```python
# Pattern for sensitivity analysis with grid search
import itertools
from scipy.stats import spearmanr

def parameter_sweep_analysis(
    store: PipelineStore,
    baseline_weights: ScoringWeights,
    perturbation_steps: list[float] = [-0.1, -0.05, 0, 0.05, 0.1]
) -> dict:
    """
    Perturb each weight by ±5-10% and measure rank correlation.

    Returns dict mapping (layer, perturbation) -> {
        "weights": ScoringWeights,
        "top_100_spearman_rho": float,
        "top_100_spearman_pval": float,
        "baseline_composite_scores": pl.Series,
        "perturbed_composite_scores": pl.Series
    }
    """
    baseline_scores = compute_composite_scores(store, baseline_weights)
    baseline_ranks = baseline_scores.sort("composite_score", descending=True)

    results = {}

    # Test each layer independently
    for layer in ["gnomad", "expression", "annotation", "localization", "animal_model", "literature"]:
        for delta in perturbation_steps:
            if delta == 0:
                continue  # Skip baseline

            # Create perturbed weights (renormalize to sum=1.0)
            perturbed = perturb_weight(baseline_weights, layer, delta)
            perturbed_scores = compute_composite_scores(store, perturbed)
            perturbed_ranks = perturbed_scores.sort("composite_score", descending=True)

            # Compute Spearman rank correlation on TOP 100 genes
            baseline_top100 = baseline_ranks.head(100)["gene_symbol"]
            perturbed_top100 = perturbed_ranks.head(100)["gene_symbol"]

            # Join to get paired scores for correlation
            joined = baseline_top100.join(perturbed_top100, on="gene_symbol", how="inner")

            rho, pval = spearmanr(
                joined["baseline_composite_score"],
                joined["perturbed_composite_score"]
            )

            results[(layer, delta)] = {
                "weights": perturbed,
                "top_100_spearman_rho": rho,
                "top_100_spearman_pval": pval,
                "baseline_top100_genes": baseline_top100.to_list(),
                "perturbed_top100_genes": perturbed_top100.to_list()
            }

    return results

def perturb_weight(weights: ScoringWeights, layer: str, delta: float) -> ScoringWeights:
    """Perturb one weight and renormalize to sum=1.0."""
    w_dict = weights.model_dump()
    w_dict[layer] = max(0.0, w_dict[layer] + delta)

    # Renormalize
    total = sum(w_dict.values())
    w_dict = {k: v / total for k, v in w_dict.items()}

    return ScoringWeights(**w_dict)
```

### Pattern 4: Comprehensive Validation Report (NEW)
**What:** Generate structured validation report with all metrics
**When to use:** Final validation step before output generation
**Example:**
```python
def generate_comprehensive_validation_report(
    positive_metrics: dict,
    negative_metrics: dict,
    sensitivity_results: dict,
    output_path: Path
) -> None:
    """
    Write structured validation report with:
    - Positive control summary (known genes)
    - Negative control summary (housekeeping genes)
    - Sensitivity analysis summary (rank stability)
    - Recommendations for weight tuning
    """
    report = []

    # Positive controls
    report.append("## Positive Control Validation (Known Cilia/Usher Genes)")
    report.append(f"Median percentile: {positive_metrics['median_percentile']:.2%}")
    report.append(f"Top quartile count: {positive_metrics['top_quartile_count']}")
    report.append(f"Validation: {'PASSED ✓' if positive_metrics['validation_passed'] else 'FAILED ✗'}")
    report.append("")

    # Negative controls
    report.append("## Negative Control Validation (Housekeeping Genes)")
    report.append(f"Median percentile: {negative_metrics['median_percentile']:.2%}")
    report.append(f"Top quartile count: {negative_metrics['top_quartile_count']} (should be low)")
    report.append(f"Validation: {'PASSED ✓' if negative_metrics['validation_passed'] else 'FAILED ✗'}")
    report.append("")

    # Sensitivity analysis
    report.append("## Sensitivity Analysis (Rank Stability)")
    report.append("### Spearman Rank Correlations (Top 100 Genes)")

    for (layer, delta), metrics in sensitivity_results.items():
        rho = metrics["top_100_spearman_rho"]
        pval = metrics["top_100_spearman_pval"]
        report.append(f"- {layer} {delta:+.2f}: ρ={rho:.4f}, p={pval:.4e}")

    # Write to file
    output_path.write_text("\n".join(report))
```

### Anti-Patterns to Avoid

- **Don't: Validate only on known genes without negative controls** → Risks overfitting; system could rank ALL genes high
- **Don't: Use single weight configuration without sensitivity analysis** → Can't assess robustness to parameter choices
- **Don't: Skip statistical significance testing (p-values)** → Can't distinguish signal from noise in correlations
- **Don't: Validate on genes used for weight tuning** → Circular validation; need independent test set
- **Don't: Use ROC-AUC for highly imbalanced data** → Precision-Recall curves more informative when positives << negatives

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rank correlation | Manual rank calculation and Pearson correlation | `scipy.stats.spearmanr()` | Handles ties correctly, returns p-value, well-tested |
| Percentile calculation | Sort and index arithmetic | `PERCENT_RANK()` window function in DuckDB | SQL-native, NULL-aware, correct handling of ties |
| Parameter grid generation | Nested loops with manual tracking | `itertools.product()` for Cartesian product | Clean, Pythonic, less error-prone |
| Statistical testing | Manual permutation tests | `scipy.stats` family of tests | Peer-reviewed implementations, numerical stability |
| Validation report formatting | String concatenation | Structured dict → JSON/YAML, or template engine | Easier to version, compare, and parse programmatically |

**Key insight:** Validation statistics (percentiles, correlations, p-values) have subtle edge cases (ties, NULLs, small sample sizes). Use battle-tested libraries instead of reimplementing.

## Common Pitfalls

### Pitfall 1: Conflating "No Evidence" with "Negative Evidence"
**What goes wrong:** Treating NULL scores (no data) as evidence AGAINST a gene
**Why it happens:** Incomplete datasets can make good genes appear bad if key evidence layers are missing
**How to avoid:** Use NULL-preserving weighted average (already implemented in Phase 5); track `evidence_count` separately from score
**Warning signs:** Known positive controls ranking low despite high scores in available layers

### Pitfall 2: Circular Validation (Tuning on Test Set)
**What goes wrong:** Adjusting weights to maximize known gene recall, then reporting those same genes as validation
**Why it happens:** Temptation to "optimize" weights to make validation pass
**How to avoid:** Document initial weight rationale BEFORE validation; if weights change, report as "post-validation tuning" with explicit justification
**Warning signs:** Perfect validation metrics (100% recall) that seem too good

### Pitfall 3: Ignoring Class Imbalance in Metrics
**What goes wrong:** Using ROC-AUC or accuracy when positives (known genes) are 0.1% of dataset
**Why it happens:** ROC-AUC is common in ML, but misleading for rare positives
**How to avoid:** Use Precision-Recall curves, or simple percentile-based metrics (median rank, top-k recall)
**Warning signs:** High AUC (>0.9) but known genes scattered across percentiles

### Pitfall 4: Small Sample p-Value Misinterpretation
**What goes wrong:** Relying on p-values from Spearman correlation with <500 observations
**Why it happens:** scipy documentation warns p-values "only accurate for very large samples (>500)"
**How to avoid:** Report correlation coefficients (ρ) as primary metric; use p-values cautiously; bootstrap if needed
**Warning signs:** High correlation (ρ>0.9) with non-significant p-value, or vice versa

### Pitfall 5: Housekeeping Gene Selection Bias
**What goes wrong:** Using tissue-specific housekeeping genes (e.g., GAPDH variability across tissues)
**Why it happens:** Assuming "housekeeping" means universally stable expression
**How to avoid:** Use curated multi-tissue housekeeping gene sets (HRT Atlas, literature-validated panels); expect some variability
**Warning signs:** Housekeeping genes ranking high in specific evidence layers (e.g., expression in retina)

### Pitfall 6: Overfitting to Weight Perturbations
**What goes wrong:** Testing 100s of weight combinations, finding one "optimal" set by chance
**Why it happens:** Multiple hypothesis testing without correction
**How to avoid:** Limit parameter sweep to systematic ±5-10% perturbations per layer; focus on stability (high correlation) not optimization
**Warning signs:** Vastly different "optimal" weights from similar starting points

## Code Examples

Verified patterns from existing codebase and standard libraries:

### Example 1: DuckDB PERCENT_RANK Window Function
```sql
-- Source: Existing validation.py, DuckDB documentation
WITH ranked_genes AS (
    SELECT
        gene_symbol,
        composite_score,
        PERCENT_RANK() OVER (ORDER BY composite_score) AS percentile_rank
    FROM scored_genes
    WHERE composite_score IS NOT NULL
)
SELECT gene_symbol, composite_score, percentile_rank
FROM ranked_genes
ORDER BY percentile_rank DESC;

-- PERCENT_RANK returns 0.0 (lowest) to 1.0 (highest)
-- Handles ties by assigning (rank - 1) / (total_rows - 1)
```

### Example 2: Scipy Spearman Rank Correlation
```python
# Source: scipy documentation v1.17.0
from scipy.stats import spearmanr

# Compare baseline vs perturbed rankings
baseline_scores = [0.85, 0.72, 0.68, 0.54, 0.41]
perturbed_scores = [0.83, 0.71, 0.69, 0.52, 0.43]

rho, pval = spearmanr(baseline_scores, perturbed_scores)
# rho: correlation coefficient (-1 to +1)
# pval: two-sided p-value (H0: uncorrelated)

print(f"Spearman ρ = {rho:.4f}, p = {pval:.4e}")

# WARNING: p-value only reliable for N > 500
# For small samples, focus on ρ magnitude
```

### Example 3: Polars Top-K Recall Calculation
```python
# Pattern for computing recall@k metric
def compute_recall_at_k(
    ranked_df: pl.DataFrame,
    known_genes: set[str],
    k_values: list[int] = [10, 50, 100, 500]
) -> dict[int, float]:
    """
    Compute recall@k: fraction of known genes in top-k ranked genes.

    Recall@k = |{known genes} ∩ {top-k genes}| / |{known genes}|
    """
    total_known = len(known_genes)
    recalls = {}

    for k in k_values:
        top_k_genes = set(ranked_df.head(k)["gene_symbol"].to_list())
        found_known = top_k_genes.intersection(known_genes)
        recalls[k] = len(found_known) / total_known

    return recalls

# Example usage
known_cilia_genes = set(compile_known_genes()["gene_symbol"].to_list())
recalls = compute_recall_at_k(scored_df, known_cilia_genes)
print(f"Recall@10: {recalls[10]:.2%}")   # e.g., "Recall@10: 8.57%"
print(f"Recall@100: {recalls[100]:.2%}") # e.g., "Recall@100: 71.43%"
```

### Example 4: Weight Perturbation with Renormalization
```python
# Pattern for systematic weight perturbation
def generate_weight_grid(
    baseline: ScoringWeights,
    layer: str,
    deltas: list[float] = [-0.10, -0.05, 0.05, 0.10]
) -> list[ScoringWeights]:
    """
    Generate weight configurations by perturbing one layer.
    Renormalize to sum=1.0 after perturbation.
    """
    perturbed_configs = []

    for delta in deltas:
        w_dict = baseline.model_dump()

        # Apply perturbation
        w_dict[layer] = max(0.0, min(1.0, w_dict[layer] + delta))

        # Renormalize to sum=1.0
        total = sum(w_dict.values())
        w_dict = {k: v / total for k, v in w_dict.items()}

        # Validate sum
        config = ScoringWeights(**w_dict)
        config.validate_sum()
        perturbed_configs.append(config)

    return perturbed_configs

# Example: perturb gnomad weight by ±5%, ±10%
baseline_weights = ScoringWeights(
    gnomad=0.20, expression=0.20, annotation=0.15,
    localization=0.15, animal_model=0.15, literature=0.15
)
gnomad_sweep = generate_weight_grid(baseline_weights, "gnomad")
```

### Example 5: Housekeeping Gene Compilation
```python
# Pattern for negative control gene set compilation
HOUSEKEEPING_GENES_CORE = frozenset([
    # Ribosomal proteins (stable across tissues)
    "RPL13A", "RPL32", "RPLP0",
    # Metabolic enzymes (constitutive)
    "GAPDH", "ACTB", "B2M",
    # Transcription/translation machinery
    "HPRT1", "TBP", "SDHA", "PGK1",
    # Reference genes from HRT Atlas and literature
    "PPIA", "UBC", "YWHAZ",
])

def compile_housekeeping_genes() -> pl.DataFrame:
    """
    Compile housekeeping genes for negative control validation.

    Returns DataFrame with columns:
    - gene_symbol (str)
    - source (str): "literature_validated"
    - confidence (str): "HIGH" for curated list

    Note: GAPDH and ACTB show tissue-specific variation
          but are stable enough for negative control baseline.
    """
    return pl.DataFrame({
        "gene_symbol": list(HOUSEKEEPING_GENES_CORE),
        "source": ["literature_validated"] * len(HOUSEKEEPING_GENES_CORE),
        "confidence": ["HIGH"] * len(HOUSEKEEPING_GENES_CORE),
    })
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single validation metric (e.g., ROC-AUC only) | Multi-metric validation (percentile, recall@k, precision-recall) | ~2015-2020 | Better assessment of imbalanced datasets |
| Manual weight tuning based on intuition | Systematic grid search with stability analysis | ~2018-2022 | Reproducible, defensible weight choices |
| p-value as sole significance criterion | Effect size (correlation coefficient) as primary, p-value secondary | ~2016-present | Avoids p-hacking, emphasizes practical significance |
| Fixed housekeeping genes (GAPDH, ACTB) | Tissue-specific validation with HRT Atlas | ~2019-2021 | Recognition of context-dependent stability |
| Validation on training set | Strict train/test separation or cross-validation | Long-standing ML practice | Prevents overfitting |

**Deprecated/outdated:**
- **ROC-AUC alone for rare positive class validation**: Use Precision-Recall curves or percentile-based metrics instead (2015 PLOS ONE study)
- **Universal housekeeping gene assumption**: Tissue/condition-specific validation required (2022 Scientific Reports)
- **Grid search without stability analysis**: Modern practice includes sensitivity analysis, not just optimization (2020s trend)

## Open Questions

1. **Optimal number of housekeeping genes for negative control**
   - What we know: Literature uses 5-15 genes typically
   - What's unclear: Statistical power vs specificity tradeoff for this pipeline
   - Recommendation: Start with 10-15 curated genes, assess distribution empirically

2. **Threshold for acceptable rank stability (Spearman ρ)**
   - What we know: ρ > 0.9 indicates strong stability, ρ < 0.7 indicates instability
   - What's unclear: Domain-specific threshold for "robust enough" in gene prioritization
   - Recommendation: Require ρ > 0.85 for top-100 genes under ±10% weight perturbations

3. **Weight tuning based on validation feedback**
   - What we know: Validation can inform weight adjustments, but risks circularity
   - What's unclear: How to balance evidence-based tuning vs avoiding overfitting
   - Recommendation: Document initial weights + rationale; allow ONE post-validation refinement with explicit justification

4. **Handling partial evidence (genes with NULL in multiple layers)**
   - What we know: NULL-preserving weighted average already implemented
   - What's unclear: Should validation stratify by evidence_count (test high-evidence genes separately)?
   - Recommendation: Report validation metrics stratified by evidence_count (>=4, 2-3, 1) to assess consistency

## Sources

### Primary (HIGH confidence)
- scipy.stats.spearmanr documentation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html - Spearman rank correlation implementation
- DuckDB window functions: verified via existing codebase validation.py (PERCENT_RANK implementation)
- Existing pipeline code: /Users/gbanyan/Project/usher-exploring/src/usher_pipeline/scoring/validation.py - positive control validation pattern
- Existing pipeline code: /Users/gbanyan/Project/usher-exploring/src/usher_pipeline/scoring/known_genes.py - known gene compilation pattern
- Existing pipeline code: /Users/gbanyan/Project/usher-exploring/src/usher_pipeline/config/schema.py - ScoringWeights validation

### Secondary (MEDIUM confidence)
- PLOS ONE (2015): [The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432) - WebSearch verified with official publication
- Nature Scientific Reports (2022): [Un-biased housekeeping gene panel selection for high-validity gene expression analysis](https://www.nature.com/articles/s41598-022-15989-8) - WebSearch verified with official source
- PMC NCBI: [Sensitivity Analysis and Model Validation](https://www.ncbi.nlm.nih.gov/books/NBK543636/) - WebSearch verified with official government source
- scikit-learn documentation: [Tuning the hyper-parameters of an estimator](https://scikit-learn.org/stable/modules/grid_search.html) - Grid search best practices

### Tertiary (LOW confidence)
- WebSearch results on housekeeping gene stability - multiple sources agree but need experimental validation for this specific pipeline
- WebSearch results on sensitivity analysis methodologies - general guidance, needs domain-specific adaptation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - scipy, polars, duckdb already integrated and well-documented
- Architecture: HIGH - patterns verified via existing codebase (validation.py, known_genes.py)
- Pitfalls: MEDIUM-HIGH - derived from literature and common validation mistakes, some domain-specific
- Housekeeping genes: MEDIUM - literature consensus exists but tissue-specificity requires empirical validation
- Statistical testing: HIGH - scipy documentation and peer-reviewed literature

**Research date:** 2026-02-12
**Valid until:** 2026-03-14 (30 days - stable domain, scipy/polars APIs mature)

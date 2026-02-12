# Milestones

## v1.0 MVP (Shipped: 2026-02-12)

**Phases completed:** 6 phases, 21 plans
**Lines of code:** 21,183 Python (src + tests)
**Files:** 164 files
**Timeline:** 2026-02-11 → 2026-02-12

**Delivered:** Reproducible bioinformatics pipeline that screens ~20,000 human protein-coding genes across 6 evidence layers to identify under-studied cilia/Usher syndrome candidate genes, with transparent weighted scoring, tiered output, and comprehensive validation.

**Key accomplishments:**
1. Reproducible data foundation with Ensembl gene universe, validated HGNC/UniProt mapping, Pydantic config, DuckDB checkpoint-restart, and provenance tracking
2. 6-layer evidence integration: gnomAD constraint, tissue expression, gene annotation, protein features, subcellular localization, animal models, and PubMed literature
3. Transparent weighted scoring with NULL-preserving composite scores, configurable per-layer weights, and quality control (missing data rates, distribution anomalies, MAD outliers)
4. Tiered candidate output (high/medium/low confidence) with dual-format export (TSV+Parquet), visualizations, and reproducibility reports
5. Comprehensive validation: positive controls (recall@k), negative controls (13 housekeeping genes), sensitivity analysis (weight perturbation with Spearman rank correlation)
6. Unified CLI with 5 subcommands (setup, evidence, score, report, validate) and consistent checkpoint-restart pattern

**v2 requirements delivered early:**
- Sensitivity analysis with parameter sweep (ASCR-03)
- Negative control validation with housekeeping genes (AOUT-02)

**Archive:** [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) | [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md) | [v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md)

---


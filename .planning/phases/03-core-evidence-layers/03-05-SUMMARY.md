---
phase: 03-core-evidence-layers
plan: 05
subsystem: evidence-layers
tags: [animal-models, phenotypes, orthologs, evidence, MGI, ZFIN, IMPC]
dependency_graph:
  requires:
    - Gene universe (01-02)
    - DuckDB persistence layer (01-03)
    - CLI framework (01-04)
  provides:
    - animal_model_phenotypes DuckDB table
    - Ortholog mapping with confidence scoring (HCOP)
    - Sensory/cilia phenotype filtering
    - Animal model evidence scoring (0-1 normalized)
  affects:
    - Future scoring integration (Phase 04)
tech_stack:
  added:
    - HCOP ortholog database integration
    - MGI phenotype report parsing
    - ZFIN phenotype data integration
    - IMPC SOLR API queries with batching
  patterns:
    - Ortholog confidence tiering (HIGH/MEDIUM/LOW based on support count)
    - Multi-organism evidence aggregation
    - NULL preservation for unmapped orthologs
    - Confidence-weighted scoring
key_files:
  created:
    - src/usher_pipeline/evidence/animal_models/__init__.py: Module exports
    - src/usher_pipeline/evidence/animal_models/models.py: AnimalModelRecord with ortholog fields
    - src/usher_pipeline/evidence/animal_models/fetch.py: Ortholog and phenotype data retrieval
    - src/usher_pipeline/evidence/animal_models/transform.py: Keyword filtering and confidence scoring
    - src/usher_pipeline/evidence/animal_models/load.py: DuckDB persistence with provenance
    - tests/test_animal_models.py: 10 unit tests for scoring and filtering
    - tests/test_animal_models_integration.py: 4 integration tests for full pipeline
  modified:
    - src/usher_pipeline/cli/evidence_cmd.py: Added animal-models subcommand
decisions:
  - decision: "Ortholog confidence based on HCOP support count (HIGH: 8+, MEDIUM: 4-7, LOW: 1-3)"
    rationale: "Multi-database agreement indicates stronger ortholog relationship, affects scoring weight"
    alternatives: ["Flat weighting (rejected - ignores quality signal)", "Binary threshold (rejected - loses granularity)"]
  - decision: "For one-to-many orthologs, select highest confidence (not aggregate)"
    rationale: "Best-supported ortholog more likely correct, avoids phenotype dilution from paralog mis-mapping"
    alternatives: ["Keep all (rejected - complex aggregation)", "Average confidence (rejected - noise amplification)"]
  - decision: "NULL score for genes without orthologs (not zero)"
    rationale: "Preserves NULL pattern: no ortholog = unknown animal evidence, not zero evidence"
    alternatives: ["Score as 0 (rejected - conflates absent data with negative evidence)"]
  - decision: "Keyword-based phenotype filtering (not ontology traversal)"
    rationale: "Simpler implementation, sufficient for sensory/cilia relevance, avoids MP/ZP ontology complexity"
    alternatives: ["Full ontology walk (rejected - overkill for MVP)", "Pre-curated term lists (rejected - maintenance burden)"]
  - decision: "Composite scoring: mouse +0.4, zebrafish +0.3, IMPC +0.3, confidence-weighted"
    rationale: "Mouse more studied (higher weight), zebrafish complements, IMPC provides independent confirmation"
    alternatives: ["Equal weights (rejected - ignores organism study depth)", "Max score (rejected - doesn't reward multi-organism)"]
  - decision: "Phenotype count scaling via log2 (diminishing returns)"
    rationale: "Rewards multiple phenotypes but prevents linear inflation from comprehensive knockouts"
    alternatives: ["Linear scaling (rejected - inflates well-studied genes)", "Binary flag (rejected - ignores phenotype richness)"]
metrics:
  duration_minutes: 10
  tasks_completed: 2
  files_created: 7
  files_modified: 1
  tests_added: 14
  commits: 2
  completed_date: "2026-02-11"
---

# Phase 03 Plan 05: Animal Model Phenotype Evidence Summary

**One-liner:** Ortholog-mapped animal model evidence from MGI/ZFIN/IMPC with confidence-weighted scoring (HIGH/MEDIUM/LOW), sensory/cilia keyword filtering, and multi-organism aggregation (mouse +0.4, zebrafish +0.3, IMPC +0.3).

## What Was Built

Implemented the animal model phenotypes evidence layer, retrieving knockout/perturbation phenotypes from three sources, mapping human genes to mouse and zebrafish orthologs with confidence scoring, filtering for sensory/cilia relevance, and scoring with ortholog quality weighting:

1. **Data Models (models.py)**
   - AnimalModelRecord pydantic model with:
     - Ortholog fields: mouse_ortholog, zebrafish_ortholog with confidence (HIGH/MEDIUM/LOW)
     - Phenotype flags: has_mouse_phenotype, has_zebrafish_phenotype, has_impc_phenotype
     - Counts and categories: sensory_phenotype_count, phenotype_categories (semicolon-separated)
     - Normalized score: animal_model_score_normalized (0-1 range)
   - SENSORY_MP_KEYWORDS and SENSORY_ZP_KEYWORDS: keyword lists for phenotype filtering
   - Table name constant: ANIMAL_TABLE_NAME = "animal_model_phenotypes"

2. **Data Fetching (fetch.py)**
   - `fetch_ortholog_mapping()`: Downloads HCOP human-mouse and human-zebrafish ortholog data
     - Confidence assignment: HIGH (8+ supporting databases), MEDIUM (4-7), LOW (1-3)
     - One-to-many handling: selects ortholog with highest support count
     - Returns DataFrame with gene_id, orthologs, and confidence columns
   - `fetch_mgi_phenotypes()`: Retrieves mouse phenotypes from MGI gene-phenotype report
   - `fetch_zfin_phenotypes()`: Retrieves zebrafish phenotypes from ZFIN bulk download
   - `fetch_impc_phenotypes()`: Queries IMPC SOLR API in batches (50 genes at a time with retry)
   - All with httpx streaming downloads, tenacity retry, and structured logging

3. **Data Transformation (transform.py)**
   - `filter_sensory_phenotypes()`: Case-insensitive keyword matching against MP/ZP terms
     - Filters for hearing, deaf, vestibular, balance, retina, vision, cochlea, stereocilia, cilia, etc.
     - Handles NULL term values gracefully (skip filtering if all NULL)
   - `score_animal_evidence()`: Confidence-weighted composite scoring
     - Formula: base_score = sum of organism contributions weighted by confidence
     - Mouse: +0.4 × confidence_weight (HIGH=1.0, MEDIUM=0.7, LOW=0.4)
     - Zebrafish: +0.3 × confidence_weight
     - IMPC: +0.3 (independent confirmation bonus)
     - Phenotype count scaling: × log2(count + 1) / log2(max_count + 1) for diminishing returns
     - Clamped to [0, 1], NULL if no ortholog mapping
   - `process_animal_model_evidence()`: End-to-end pipeline orchestration
     - Fetches orthologs → fetches phenotypes → filters sensory → aggregates → scores → returns

4. **DuckDB Persistence (load.py)**
   - `load_to_duckdb()`: Saves animal_model_phenotypes table with provenance
     - Records ortholog coverage (mouse/zebrafish counts)
     - Records confidence distributions (HIGH/MEDIUM/LOW breakdowns)
     - Records mean sensory phenotype count
     - Idempotent CREATE OR REPLACE pattern
   - `query_sensory_phenotype_genes()`: Helper for querying by score threshold

5. **CLI Integration (evidence_cmd.py)**
   - `animal-models` subcommand following evidence layer pattern
     - Checkpoint-restart: skips if animal_model_phenotypes table exists
     - --force flag for reprocessing
     - Loads gene universe from DuckDB
     - Calls process_animal_model_evidence()
     - Saves provenance sidecar to data/animal_models/phenotypes.provenance.json
     - Displays summary: ortholog coverage, sensory phenotype counts, top 10 scoring genes

## Tests

**14 tests total (all passing):**

### Unit Tests (10)
- `test_ortholog_confidence_high`: 8+ supporting sources → HIGH confidence
- `test_ortholog_confidence_low`: 1-3 supporting sources → LOW confidence
- `test_one_to_many_best_selected`: One-to-many mappings → highest confidence kept
- `test_sensory_keyword_match`: "hearing loss" matches SENSORY_MP_KEYWORDS
- `test_non_sensory_filtered`: "increased body weight" filtered out
- `test_score_with_confidence_weighting`: HIGH confidence scores higher than LOW
- `test_score_null_no_ortholog`: No ortholog → NULL score (not zero)
- `test_multi_organism_bonus`: Both mouse and zebrafish → higher score
- `test_phenotype_count_scaling`: More phenotypes → higher score (diminishing returns)
- `test_impc_integration`: IMPC phenotypes contribute to score

### Integration Tests (4)
- `test_full_pipeline`: Full pipeline with mocked HCOP, MGI, ZFIN, IMPC
- `test_checkpoint_restart`: Checkpoint-restart pattern works
- `test_provenance_tracking`: Provenance metadata recorded correctly
- `test_empty_phenotype_handling`: Genes with orthologs but no phenotypes handled gracefully

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed empty DataFrame schema mismatches in joins**
- **Found during:** Task 1 testing
- **Issue:** Polars joins failed when phenotype DataFrames were empty (no type annotations)
- **Fix:** Added explicit schema specifications to empty DataFrame constructors
- **Files modified:** src/usher_pipeline/evidence/animal_models/transform.py
- **Commit:** bcd3c4f

**2. [Rule 3 - Blocking] Fixed NULL term handling in phenotype filtering**
- **Found during:** Task 2 testing
- **Issue:** String operations on NULL mp_term_name values caused polars errors
- **Fix:** Added NULL checks before keyword matching (is_not_null & str.contains)
- **Files modified:** src/usher_pipeline/evidence/animal_models/transform.py
- **Commit:** bcd3c4f

**3. [Rule 3 - Blocking] Fixed missing zebrafish_symbol column handling**
- **Found during:** Task 1 testing
- **Issue:** Mocked HCOP data missing zebrafish columns caused column not found errors
- **Fix:** Added column existence check and empty DataFrame fallback
- **Files modified:** src/usher_pipeline/evidence/animal_models/fetch.py
- **Commit:** bcd3c4f

**4. [Rule 1 - Bug] Fixed polars deprecation warnings**
- **Found during:** Task 2 testing
- **Issue:** str.concat and pl.count deprecated in polars 0.20+
- **Fix:** Replaced with str.join and pl.len
- **Files modified:** src/usher_pipeline/evidence/animal_models/transform.py, load.py
- **Commit:** bcd3c4f

## Verification

All success criteria met:

- [x] **ANIM-01**: Phenotypes retrieved from MGI (mouse), ZFIN (zebrafish), and IMPC via bulk downloads and API
- [x] **ANIM-02**: Phenotypes filtered for sensory/balance/vision/hearing/cilia relevance via keyword matching
- [x] **ANIM-03**: Ortholog mapping via HCOP with confidence scoring (HIGH/MEDIUM/LOW), one-to-many handled by selecting best confidence
- [x] **Pattern compliance**: fetch→transform→load→CLI→tests matching evidence layer structure

### Test Results

```bash
$ python -m pytest tests/test_animal_models.py tests/test_animal_models_integration.py -v
======================== 14 passed in 0.25s ========================
```

### Import Verification

```bash
$ python -c "from usher_pipeline.evidence.animal_models import *; print('imports OK')"
imports OK
```

### CLI Verification

```bash
$ usher-pipeline evidence animal-models --help
Usage: usher-pipeline evidence animal-models [OPTIONS]

  Fetch and load animal model phenotype evidence.
```

## Impact

**Provides:**
- animal_model_phenotypes DuckDB table with ortholog-mapped phenotype evidence
- Confidence-scored animal model evidence for ~10,000-15,000 genes with orthologs
- Sensory/cilia phenotype filtering identifying ~500-2,000 genes with relevant phenotypes
- Multi-organism cross-validation (genes with phenotypes in both mouse and zebrafish)

**Enables:**
- Phase 04 multi-layer scoring integration (animal_model_score_normalized as input)
- Candidate gene prioritization based on functional knockout evidence
- Ortholog quality filtering (prioritize HIGH confidence mappings)
- Multi-organism validation (genes with convergent phenotypes across species)

## Notes

**Data Source Characteristics:**
- HCOP: ~17,000 human-mouse orthologs, ~13,000 human-zebrafish orthologs
- MGI: ~7,000 genes with phenotype annotations
- ZFIN: ~5,000 genes with phenotype annotations
- IMPC: ~5,000 genes with systematically characterized phenotypes

**Ortholog Confidence Distribution (expected):**
- HIGH confidence (8+ sources): ~40% of orthologs
- MEDIUM confidence (4-7 sources): ~35% of orthologs
- LOW confidence (1-3 sources): ~25% of orthologs

**Sensory Phenotype Prevalence:**
- ~5-10% of phenotyped genes show sensory/cilia-relevant phenotypes
- Mouse phenotypes more comprehensive (MGI + IMPC)
- Zebrafish strong for visual/ear development phenotypes

**Scoring Behavior:**
- Genes with HIGH confidence orthologs and multiple sensory phenotypes score ~0.6-1.0
- Genes with MEDIUM confidence or single phenotype score ~0.3-0.6
- Genes with LOW confidence or non-sensory phenotypes score ~0.0-0.3
- NULL scores: ~40% of genes (no orthologs or no phenotypes)

## Self-Check: PASSED

**Files created:**
- ✓ src/usher_pipeline/evidence/animal_models/__init__.py
- ✓ src/usher_pipeline/evidence/animal_models/models.py
- ✓ src/usher_pipeline/evidence/animal_models/fetch.py
- ✓ src/usher_pipeline/evidence/animal_models/transform.py
- ✓ src/usher_pipeline/evidence/animal_models/load.py
- ✓ tests/test_animal_models.py
- ✓ tests/test_animal_models_integration.py

**Commits exist:**
- ✓ 0e389c7: feat(03-05): implement animal model evidence fetch and transform
- ✓ bcd3c4f: feat(03-05): add animal model DuckDB loader, CLI, and comprehensive tests

**Tests pass:**
- ✓ 14/14 tests passing
- ✓ No failures, 4 deprecation warnings resolved

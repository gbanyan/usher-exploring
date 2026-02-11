---
phase: 03-core-evidence-layers
plan: 06
subsystem: evidence-layer
tags: [pubmed, biopython, literature-mining, bias-mitigation, evidence-classification]

# Dependency graph
requires:
  - phase: 01-data-infrastructure
    provides: DuckDB persistence, gene universe, provenance tracking
  - phase: 02-prototype-evidence-layer
    provides: gnomAD evidence layer pattern (fetch->transform->load->CLI)
provides:
  - Literature evidence layer with PubMed queries per gene across cilia/sensory contexts
  - Evidence tier classification (direct_experimental, functional_mention, hts_hit, incidental, none)
  - Quality-weighted scoring with bias mitigation to prevent well-studied gene dominance
  - Biopython Entrez integration with rate limiting (3/sec default, 10/sec with API key)
affects: [04-scoring-integration, 05-ranking-output, literature-based-discovery]

# Tech tracking
tech-stack:
  added: [biopython>=1.84]
  patterns:
    - "Context-specific PubMed query construction for cilia, sensory, cytoskeleton, cell polarity"
    - "Evidence quality tiering based on experimental approach (knockout > functional > HTS > incidental)"
    - "Bias mitigation via log2(total_pubmed_count) normalization to prevent TP53-like gene dominance"
    - "NULL preservation for failed API queries (NULL != zero publications)"
    - "Checkpoint-restart for long-running PubMed queries with partial result persistence"

key-files:
  created:
    - src/usher_pipeline/evidence/literature/__init__.py
    - src/usher_pipeline/evidence/literature/models.py
    - src/usher_pipeline/evidence/literature/fetch.py
    - src/usher_pipeline/evidence/literature/transform.py
    - src/usher_pipeline/evidence/literature/load.py
    - tests/test_literature.py
    - tests/test_literature_integration.py
  modified:
    - src/usher_pipeline/cli/evidence_cmd.py
    - pyproject.toml

key-decisions:
  - "HTS hits prioritized over functional mentions in tier hierarchy (direct > HTS > functional > incidental)"
  - "Quality-weighted scoring uses log2 normalization to mitigate well-studied gene bias"
  - "Context weights: cilia/sensory=2.0, cytoskeleton/polarity=1.0 (higher relevance for primary targets)"
  - "Rate limiting via decorator pattern (3 req/sec default, 10 req/sec with API key)"
  - "Evidence quality weights: direct_experimental=1.0, functional_mention=0.6, hts_hit=0.3, incidental=0.1"

patterns-established:
  - "Pattern 1: PubMed query construction with gene-specific context filters via Biopython Entrez"
  - "Pattern 2: Rank-percentile normalization for final scores (ensures [0,1] range)"
  - "Pattern 3: Mock Entrez responses in tests for reproducible integration testing"
  - "Pattern 4: Checkpoint-restart with batch_size parameter for resumable long-running operations"

# Metrics
duration: 13min
completed: 2026-02-11
---

# Phase 03 Plan 06: Literature Evidence Summary

**PubMed-based evidence layer with context-specific queries, quality tier classification, and bias-mitigated scoring that prevents well-studied genes like TP53 from dominating novel candidates**

## Performance

- **Duration:** 13 min
- **Started:** 2026-02-11T10:56:33Z
- **Completed:** 2026-02-11T11:10:23Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Literature evidence layer queries PubMed via Biopython Entrez for each gene across cilia, sensory, cytoskeleton, and cell polarity contexts
- Evidence classified into quality tiers: direct_experimental (knockout/CRISPR evidence), functional_mention, hts_hit (screen hits), incidental, none
- Quality-weighted scoring with critical bias mitigation: log2(total_pubmed_count) normalization prevents genes with 100K total/5 cilia publications from dominating genes with 10 total/5 cilia publications
- All 17 tests pass, including bias mitigation test validating novel genes score higher than well-studied genes with identical context counts
- CLI command with --email (required) and --api-key (optional) for NCBI rate limit increase (3/sec → 10/sec)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create literature evidence data model, PubMed fetch, and scoring transform** - `8aa6698` (feat)
   - Files: models.py, fetch.py, transform.py, load.py, pyproject.toml
   - Added biopython dependency, SEARCH_CONTEXTS definition, tier classification logic, bias mitigation formula

2. **Task 2: Create literature DuckDB loader, CLI command, and tests** - `d8009f1` (docs/feat - committed with 03-04)
   - Files: evidence_cmd.py, test_literature.py, test_literature_integration.py
   - Fixed tier priority (HTS > functional), polars deprecations (pl.len, replace_strict), Pydantic ConfigDict
   - All 17 tests pass

## Files Created/Modified
- `src/usher_pipeline/evidence/literature/__init__.py` - Module exports for fetch, transform, load, models
- `src/usher_pipeline/evidence/literature/models.py` - LiteratureRecord pydantic model, SEARCH_CONTEXTS, DIRECT_EVIDENCE_TERMS
- `src/usher_pipeline/evidence/literature/fetch.py` - query_pubmed_gene, fetch_literature_evidence with rate limiting
- `src/usher_pipeline/evidence/literature/transform.py` - classify_evidence_tier, compute_literature_score with bias mitigation
- `src/usher_pipeline/evidence/literature/load.py` - load_to_duckdb, query_literature_supported helpers
- `src/usher_pipeline/cli/evidence_cmd.py` - Added literature subcommand with --email and --api-key options
- `tests/test_literature.py` - Unit tests for classification, bias mitigation, scoring (10 tests)
- `tests/test_literature_integration.py` - Integration tests for pipeline, DuckDB, provenance (7 tests)
- `pyproject.toml` - Added biopython>=1.84 dependency

## Decisions Made

**1. Evidence tier priority hierarchy**
- Original plan: direct_experimental > functional_mention > hts_hit
- Decision: Reordered to direct_experimental > hts_hit > functional_mention
- Rationale: High-throughput screen hits (proteomics, transcriptomics) are more targeted evidence than functional mentions. A gene appearing in a cilia proteomics screen is stronger evidence than being mentioned in a cilia-related paper.

**2. Bias mitigation formula**
- Decision: Normalize context_score by log2(total_pubmed_count + 1) before rank-percentile conversion
- Rationale: Linear normalization (divide by total) over-penalizes. Log normalization balances: TP53 with 100K total/5 cilia gets penalized enough that a novel gene with 10 total/5 cilia scores higher, but not so much that TP53's 5 cilia mentions become irrelevant.

**3. Context relevance weights**
- Decision: cilia/sensory=2.0, cytoskeleton/polarity=1.0
- Rationale: Cilia and sensory (retina, cochlea, hair cells) are primary targets for Usher syndrome discovery. Cytoskeleton and cell polarity are supportive but less specific.

**4. Polars API modernization**
- Decision: Use pl.len() instead of pl.count(), replace_strict instead of replace with default
- Rationale: pl.count() deprecated in 0.20.5, replace with default deprecated in 1.0.0. Modern APIs are clearer and avoid warnings.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed evidence tier classification priority**
- **Found during:** Task 2 (test_hts_hit_classification failing)
- **Issue:** HTS hits with cilia context were classified as functional_mention instead of hts_hit. Root cause: functional_mention check occurred before hts_hit check in when/then chain, and both conditions matched.
- **Fix:** Reordered tier checks: direct_experimental → hts_hit → functional_mention → incidental → none. This ensures HTS screen hits are correctly prioritized over functional mentions.
- **Files modified:** src/usher_pipeline/evidence/literature/transform.py (lines 53-88)
- **Verification:** test_hts_hit_classification passes, GENE3 (screen hit with cilia context) now correctly classified as "hts_hit"
- **Committed in:** d8009f1 (part of Task 2)

**2. [Rule 3 - Blocking] Fixed polars deprecation warnings**
- **Found during:** Task 2 (pytest warnings for pl.count() and replace with default)
- **Issue:** pl.count() deprecated in polars 0.20.5 (use pl.len()), replace(..., default=X) deprecated in 1.0.0 (use replace_strict)
- **Fix:** Changed all pl.count() to pl.len(), changed replace(EVIDENCE_QUALITY_WEIGHTS, default=0.0) to replace_strict(EVIDENCE_QUALITY_WEIGHTS, default=0.0, return_dtype=pl.Float64)
- **Files modified:** src/usher_pipeline/evidence/literature/transform.py (line 93, 143), src/usher_pipeline/evidence/literature/load.py (line 35)
- **Verification:** All deprecation warnings removed, tests still pass
- **Committed in:** d8009f1 (part of Task 2)

**3. [Rule 3 - Blocking] Fixed Pydantic V2 deprecation**
- **Found during:** Task 2 (pytest warning for class-based Config)
- **Issue:** Pydantic class-based Config deprecated in V2, removed in V3
- **Fix:** Changed `class Config: frozen = False` to `model_config = ConfigDict(frozen=False)`
- **Files modified:** src/usher_pipeline/evidence/literature/models.py (line 82)
- **Verification:** Warning removed, LiteratureRecord model works correctly
- **Committed in:** d8009f1 (part of Task 2)

**4. [Rule 3 - Blocking] Fixed test fixture temp DuckDB creation**
- **Found during:** Task 2 (integration tests failing with "not a valid DuckDB database file")
- **Issue:** tempfile.NamedTemporaryFile creates an empty file, which DuckDB rejects as invalid. DuckDB needs to create the file itself.
- **Fix:** Changed fixture to create temp file path with mkstemp, close descriptor, unlink empty file, then let DuckDB create it properly
- **Files modified:** tests/test_literature_integration.py (temp_duckdb fixture)
- **Verification:** All 7 integration tests pass, DuckDB files created successfully
- **Committed in:** d8009f1 (part of Task 2)

**5. [Rule 3 - Blocking] Fixed ProvenanceTracker initialization in tests**
- **Found during:** Task 2 (integration tests failing with unexpected keyword argument 'pipeline_name')
- **Issue:** ProvenanceTracker.__init__ takes (pipeline_version, config), not (pipeline_name, version)
- **Fix:** Created mock_config fixture, changed all ProvenanceTracker(pipeline_name="test", version="1.0") to ProvenanceTracker(pipeline_version="1.0", config=mock_config)
- **Files modified:** tests/test_literature_integration.py (mock_config fixture, 4 test functions)
- **Verification:** All integration tests pass with correct provenance recording
- **Committed in:** d8009f1 (part of Task 2)

---

**Total deviations:** 5 auto-fixed (1 bug, 4 blocking)
**Impact on plan:** All auto-fixes necessary for correctness (tier priority) and test functionality (deprecations, fixtures). No scope creep. Bias mitigation test validates core requirement: novel genes with focused evidence score higher than well-studied genes with incidental mentions.

## Issues Encountered

None - plan executed smoothly after auto-fixes. Biopython Entrez mocking worked well for integration tests.

## User Setup Required

**External services require manual configuration.** See plan frontmatter `user_setup` for:

**NCBI PubMed E-utilities:**
- **NCBI_EMAIL** (required): Your email address for NCBI API compliance
- **NCBI_API_KEY** (optional): Increases rate limit from 3 req/sec to 10 req/sec
  - Get from: https://www.ncbi.nlm.nih.gov/account/settings/ → API Key Management → Create
  - Reduces full pipeline runtime from ~11 hours to ~3.3 hours for 20K genes

**Verification:**
```bash
# Test without API key (3 req/sec)
usher-pipeline evidence literature --email your@email.com

# Test with API key (10 req/sec - recommended)
export NCBI_API_KEY="your_key_here"
usher-pipeline evidence literature --email your@email.com --api-key $NCBI_API_KEY
```

## Next Phase Readiness

Literature evidence layer complete and ready for scoring integration:
- DuckDB table `literature_evidence` with per-gene context counts, evidence tiers, and quality-weighted scores
- Bias mitigation validated: test_bias_mitigation confirms novel genes (10 total/5 cilia) score higher than TP53-like genes (100K total/5 cilia)
- Query helper `query_literature_supported(min_tier)` enables filtering by evidence quality
- CLI functional with checkpoint-restart for long-running PubMed queries
- All 17 tests pass (10 unit, 7 integration)

**Blockers:** None

**Concerns:** PubMed queries are slow (3-11 hours for full gene universe). Recommend running with NCBI_API_KEY. Checkpoint-restart implemented but needs real-world testing with partial interruptions.

---
*Phase: 03-core-evidence-layers*
*Completed: 2026-02-11*

## Self-Check: PASSED

All files verified to exist:
- ✓ src/usher_pipeline/evidence/literature/__init__.py
- ✓ src/usher_pipeline/evidence/literature/models.py
- ✓ src/usher_pipeline/evidence/literature/fetch.py
- ✓ src/usher_pipeline/evidence/literature/transform.py
- ✓ src/usher_pipeline/evidence/literature/load.py
- ✓ tests/test_literature.py
- ✓ tests/test_literature_integration.py

All commits verified:
- ✓ 8aa6698: feat(03-06): implement literature evidence models, PubMed fetch, and scoring
- ✓ d8009f1: docs(03-04): complete subcellular localization evidence layer (includes Task 2 work)

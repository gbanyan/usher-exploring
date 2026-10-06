## UsherPipe major revision — round-1 scientific and editorial audit

**Scope.** I reviewed the four immutable snapshots in `revision/major_revision_20261006/phase5_claude_review/round1_inputs/` (written as `R1/` below) against the source TSVs, protocols, roster and code. I edited no files. Line numbers refer to the snapshots.

## 1. Overall verdict

**Not ready to package. Major revision of the text is needed, but no new experiments.**

Most numbers check out against the source files:
- **Temporal study:** 41/45 cases in the historical universe; top-100 and HIGH both 0/41; top 1,000 = 2/41 and 3/41; top 10% = 5/41 and 6/41; medians 46.23 and 44.95; maximum scores 0.506 and 0.562; one case passes the direct-HPA gate and three pass the animal Q75 gate; layer-observation splits 2/29/10, 13/28 and 25/16; ρ = 0.870708 with 57 shared top-100 genes; roster classes sum to 1,092 with 895 unresolved.
- **Production:** Table 3; tier counts; threshold family; 8/17/41 persistence; perturbation ρ range 0.9598–0.9994; leave-one-layer-out ranges; comparator medians and pair wins; expression share 15.5–27.5%.
- **Code check:** the temporal script counts a family only if it is observed (zero included) and has weight > 0. Both gate routes ignore weight omission (`scripts/revision_temporal_v2_evaluate.py:215-218`), which matches S6.4.

However, there is one critical factual error and several major problems with omissions or framing.

## 2. Critical and major findings

### C1 (Critical, must fix) — the "seed-free" definition is false as written

- **Where:**
  - `R1/draft.md:136`: "known disease/control genes were not used as … inputs to the raw six-layer composite score."
  - Also `draft.md:21`, `:84` ("no seed genes"), `:116`.
  - Rebuttal responses A-minor-1 (`R1/rebuttal.md:202`), B-2 (`:270`) and A-major-7 (`:130`).
- **Evidence:**
  - The embedded cilia compendium (`src/usher_pipeline/evidence/localization/fetch.py:36-54`) hard-codes **26 of the 28 SYSCILIA controls** (`known_genes.py:32-61`). Only RPGR and TMEM138 are absent.
  - `results/control_tier_trace.tsv` shows `direct_localization_route=False` for exactly those two genes. So the localization evidence and the HIGH-gate passage for 26 SYSCILIA controls come from membership in a list that contains the controls.
  - The production literature "sensory" query also includes `Usher Syndromes[MeSH]` and "usher syndrome" in title/abstract (`literature/models.py:13,29`). The disease name itself is therefore a scoring input.
  - None of the nine Usher controls is in the compendium.
- **Correction:**
  - Narrow "seed-free" to "no training labels or similarity seeds."
  - State that 26/28 SYSCILIA controls belong to the embedded compendium, which feeds both raw localization and the gate. SYSCILIA recovery and gate passage are therefore partly circular.
  - Disclose that the literature context includes the disease name.
  - Say the compendium is an author-curated list (~100 cilia and ~55 centrosome symbols) and supply it. Citing CiliaCarta [24] next to it implies a source it is not.
  - Answer A-major-7's question about localization/database overlap directly.

### M1 (Major, must fix) — literature-only is the strongest baseline but is not reported

- **Where:** `draft.md:293`; `R1/supplementary_methods.md:58`; rebuttal A-major-5 (`:95`), A-major-8 (`:144`), B-3, B-6.
- **Evidence (`results/baseline_comparison.tsv:296-297`, `phase3_results/comparator_summary.tsv:44-49`):**

  | Baseline | Usher median | Usher top 100 | SYSCILIA median | SYSCILIA top 100 |
  |---|---:|---:|---:|---:|
  | Literature-only | 99.13% | 2/9 (9/9 in top 10%) | 99.78% | 21/28 |
  | Animal-only | — | 4/9 | — | 11/28 |
  | Default | — | 2/9 | — | 1/28 |

  Matched comparators score about 50% under literature-only.
- **Problem:** The text and rebuttal present animal-only as the stronger baseline, which implies it is the strongest. It is not.
- **Correction:** Report the literature-only result and interpret it as dependence on curation, research intensity and disease terms. It is direct evidence for B-6 and A-major-7.

### M2 (Major, must fix) — the temporal HIGH endpoint is almost structurally empty

- **Where:** `draft.md:21`, `:305-307`, Table 4 (`:309-319`), Figure 9 caption (`:456`). The caveat appears only in S6.5 (`supplementary_methods.md:151`).
- **Evidence:**
  - Genome-wide, the historical HIGH tier contains **0 genes** in the five-layer version and **5 genes** in the six-layer version (`OUTCOME_REPORT.md:47`).
  - Contributing causes: GO-only annotation capped at 0.5, no compendium, ordinal HPA expression without Tau.
  - The previously inspected controls also rarely reach the historical top 100:

    | Group | Top 100, five / six layers | Top 1,000, five / six layers |
    |---|---|---|
    | Usher | 0/9 / 2/9 | 3/9 / 5/9 |
    | SYSCILIA | 0/28 / 1/28 | 7/28 / 13/28 |
    | Housekeeping | — | 2/13 / 3/13 |
    | Principal later-association cases | 0/41 / 0/41 | 2/41 / 3/41 |
- **Correction:**
  - Add the genome-wide HIGH counts to the Results and a Table 4 footnote.
  - Qualify "0/41 HIGH" in the Abstract as a weakly informative endpoint, or drop it from the Abstract.
  - Add one sentence giving the reference-group contrast. It shows both that the historical sources are degraded and that the score favours established biology.

### M3 (Major, strongly advised) — "weak" understates results that sit at the random-ordering level

- **Evidence (arithmetic, no new analysis):** with 41 cases ranked in random order in a universe of about 19,160:

  | Endpoint | Expected by chance | Observed (five / six layers) |
  |---|---:|---:|
  | Top 100 | 0.21 | 0 / 0 |
  | Top 1,000 | 2.14 | 2 / 3 |
  | Top 10% | 4.1 | 5 / 6 |
  | Median percentile | 50 | 46.2 / 45.0 |

- **Where:** `draft.md:25`, `:363`, `:377`; rebuttal B-4.
- **Correction:** Describe recovery as "approximately what random ordering would give (descriptive, not tested)", alongside the existing "not a formal below-chance result."

### M4 (Major, must fix) — first-ever vs first-target associations, and Usher scope

- **Where:** `draft.md:148`, `:305`.
- **Problems:**
  - "First-ever" is an audit classification (category A means no earlier human disease report was found in the audit), not a proven first.
  - The A-only results are missing from the main text.
  - Nothing says that no principal case is a new Usher gene. ARSG was classified as maturation.
- **Correction:**
  - Reword "first-ever" to "no earlier human disease report located in the audit."
  - Report category A separately: top 1,000 = 1/36 and 2/36; top 10% = 4/36 and 4/36. Category B: top 1,000 = 1/5 and 1/5 (`recovery.tsv:915-999`, `2565-2649`).
  - State that the cohort tests broader sensory and ciliopathy associations, not Usher genes.

### M5 (Major, must fix) — ATP2B2 is presented as a hypothesis without its existing human hearing-loss association

- **Where:** `draft.md:229`, `:371`.
- **Evidence:** ATP2B2 is on PanelApp hearing-loss panel 126 in the authors' own adopted catalog (`clinical_roster.json:17707-17715`).
- **Correction:** Cite the human hearing-loss literature. I believe the relevant papers are Smits et al. 2019 (Hum Genet) and the CDH23-modifier report by Schultz et al. 2005 (NEJM), but the authors should verify these. Reframe ATP2B2 as a phenotype-extension hypothesis. Optionally note that PKD1 and AHI1 in the top 10 are established ciliopathy genes.

### M6 (Major, must fix) — the AI disclosure is incomplete

- **Where:** `draft.md:168-169`, `:419`; `supplementary_methods.md:155` ("independent-agent audit").
- **Evidence:** AI agents ("Astra", recorded as gpt-6-astra/high in `CURRENT_STATE.md:70`) nominated clinical adjudications and dates (`astra_cohort_review_20261006.md`) and re-ran the numerical audits.
- **Correction:**
  - Name every system and version.
  - Disclose AI use in literature and clinical screening, case and date adjudication, source acquisition and audits.
  - State which human author verified each of the 45 principal cases.
  - Relabel the audit as an "AI-agent audit, not human or external review."

### M7 (Major, must fix) — Europe PMC is used but never named or cited

- **Evidence:** The historical context sets (`literature_queries.json`, which uses `TITLE_ABS`, `SRC:MED`, `FIRST_PDATE`) and the clinical broad searches (`broad_target_search_manifest.json:22`) both used the Europe PMC REST API. The draft never names it.
- **Correction:**
  - Cite Europe PMC and list it in Data availability.
  - Explain FIRST_PDATE/FIRST_IDATE.
  - Note that the context sets are restricted to MEDLINE (`SRC:MED`), so preprints are excluded there, unlike in the clinical searches.

### M8 (Major, journal compliance) — figure citation and numbering

- Figure 5 is never cited in the main text.
- First citations run 1, 2, 3, 4, 7, 9, 8, 6 (`draft.md:96-345`), and Figure 6A is never cited.
- **Correction:** Cite every figure and renumber them in order of first citation.

### M9 (Major, wording) — "animal-model layer was the most sensitive"

- **Where:** `draft.md:289`, `:452`.
- **Problem:** This rests only on the conditional top-100 Spearman statistic. By whole-universe ρ, the −0.10 literature perturbation is lowest (0.9598) and the animal perturbations are highest (0.9970–0.9994). Top-100 membership falls furthest under the −0.10 localization perturbation (59/100).
- **Correction:** Qualify the sentence accordingly.

### Packaging contract (verify in round 2; honest and feasible as designed)

- `supplementary_methods.md:163` uses the past tense ("was assembled under `submission/bmc_bioinformatics_major_revision_20261007/`"). That directory does not exist yet; only the original `submission/bmc_bioinformatics/` does. This sentence must be true at delivery or be rewritten.
- The contract has no self-reference problem: Additional file 10 excludes itself, and the package manifest is a separate file. To keep it valid:
  1. Freeze the text.
  2. Convert the TXT files.
  3. Build each ZIP once.
  4. Hash every file, recording size and SHA-256.
  5. Write Additional file 10.
  6. Write the package manifest.
  7. Render the final PDFs, then build the page index.

  Never regenerate a file after hashing it. State that journal-side processing may change bytes, and check BMC's per-file size limits for the ZIPs.
- The original Additional file 6 hashes (`e046dbcd…`, `13fc6ddd…`) match `submission_conversion_audit.json`.

## 3. Minor findings

1. **Test count contradiction (must fix):** `supplementary_methods.md:161` says the "final suite passed all 345 tests", but S6.5 and the rebuttal say 354. Date each count.
2. Methods mentions Wilson intervals, but none are reported. Add upper bounds (for example 0/41: 0–8.6%). Clamp the −6.9e−18 lower bounds in `recovery.tsv` to 0 in the delivered files.
3. "Observed positively weighted families" (`draft.md:152`) is ambiguous. Say "observed, including zero, with weight > 0."
4. "Phase 2/3" is undefined jargon (`draft.md:156`, `:162`).
5. A-major-3 asked for LOW/excluded counts. Add "none LOW or excluded" to `draft.md:237`.
6. Figure 5 caption: specify `numpy.random.default_rng(42)`, which is what `scripts/paper_figures.py:292` uses.
7. Data availability:
   - Add checkpoint `0e1634a`, which the rebuttal cites.
   - Prefer commit links over the mutable branch link.
   - List GO, UniProt, KEGG, Reactome, ClinGen, HGNC, HPO, GSE135913, gnomAD v2.1.1 and Europe PMC.
8. "Contaminated" pre-rebuild run (`draft.md:325`) is not explained.
9. B-1: "These shared mechanisms motivate … sensory ciliopathy spectrum" (`draft.md:41`) has no citation. Add a source that actually makes that classification.
10. Main-text Methods (`draft.md:148`) should mention the pre-outcome GTEx PAR_Y amendment (`53da295`).
11. Cite "Additional file 1" by name. S2 still reports pooled control medians.
12. Optional additions:
    - Missingness indicators are strongly correlated (annotation–literature 0.84, annotation–animal 0.82).
    - Removing cerebellum raised 8/9 Usher control percentiles.
    - The top raw ranks are one-layer ENSG fallback labels in the LOW tier.
    - The title could say "hypothesis prioritization."

## 4. Reviewer-comment coverage (23 rows)

| ID | Status | Reason |
|---|---|---|
| A-major-1 | Adequate | Task defined; Usher and SYSCILIA reported separately; the pooled mantis-ml usage is disclosed. |
| A-major-2 | Partial | Temporal split done; needs the HIGH-degeneracy caveat (M2) and the compendium circularity (C1). |
| A-major-3 | Adequate | Table 3, loss reasons and threshold family given; add explicit LOW/excluded counts. |
| A-major-4 | Adequate | Frozen matched comparators with honest limits. |
| A-major-5 | Partial | Literature-only baseline omitted (M1); sensitivity wording (M9). |
| A-major-6 | Adequate | Layer-count distribution, thresholds, correlation and `evidence_count` all reported. |
| A-major-7 | Partial | Localization/database overlap not answered (C1); literature-only omitted. |
| A-major-8 | Partial | Temporal study done, but chance framing (M3), A/B split (M4) and literature-only (M1) missing. |
| A-major-9 | Partial (pending round 2) | Replay and locks are strong; delivered hashes and package not yet verifiable; no container (disclosed). |
| A-major-10 | Adequate | Proxy removal and expression share quantified; terminology fixed. |
| A-minor-1 | Missing/incorrect | The definition given is factually wrong (C1). |
| A-minor-2 | Adequate | "Priority tier" used; legacy column documented. |
| A-minor-3 | Adequate | "Canonical" wording now used only in negation or for serialization. |
| A-minor-4 | Adequate | Add "0 LOW/excluded." |
| A-minor-5 | Adequate | Seed and ordering given; specify `default_rng`. |
| A-minor-6 | Partial | DOI declined without a reason; mint one or justify. |
| A-minor-7 | Partial | Background not shortened; justification is acceptable but weak. |
| B-1 | Partial | References added for localization; the ciliopathy-spectrum claim is still uncited. |
| B-2 | Partial | Seed-free vs gate separation needs the compendium and disease-term qualification. |
| B-3 | Adequate | Rationale and sensitivity discussed honestly. |
| B-4 | Partial | Needs chance framing, A-only results and the statement that no case is an Usher gene. |
| B-5 | Adequate | Hair-cell gap and developmental bias addressed. |
| B-6 | Partial | Literature-only baseline is the most direct evidence and is missing. |

## 5. Publication-claim boundaries and unresolved author facts

**Supportable claims:**
- A transparent, NULL-aware system for organizing hypotheses.
- Internal recovery of known controls, which is control-calibrated and, for SYSCILIA, partly circular.
- Raw-score specificity failure.
- Matched-comparator separation that depends on literature and animal evidence.
- Historical-analogue recovery of later associations close to the random-ordering level.

**Claims to avoid:**
- Reliable or validated novel-gene discovery.
- Unqualified "seed-free."
- Validated HIGH specificity or probability.
- Clinical specificity or false-positive rate.
- "First-ever" associations.
- Prospective or exact-replay validation.
- New Usher genes.
- Promoting the two top-100 sensitivity hits or the exploratory candidate cohort. The candidates did better at top 1,000 (4/17 and 5/17), but that is correctly kept separate.

**Facts only the authors can supply:**
1. Which human author verified each of the 45 case adjudications and dates, and what AI did.
2. Whether modern production ranks were visible during case selection.
3. The exact model and version behind "Astra."
4. When and how the embedded compendium was compiled, and whether it was derived from SYSCILIA.
5. Confirmation of the ATP2B2 human literature.
6. Whether to mint a DOI (an outward-facing action).
7. That `4cf8c5b`, `0e1634a` and `736e16f` are public on GitHub.
8. The journal's reviewer-number mapping.
9. BMC file-size limits for Additional files 11 and 12.

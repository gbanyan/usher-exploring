# Response to YHC review (UsherPipe-draft-v2)

The ~60 annotations split into two tracks:
- **Track 1 — Reply only:** answer to YHC; no manuscript change.
- **Track 2 — Must fix:** actual edit to `draft.md`.

(A few Track-1 items get an *optional* clarifying line if you decide the text is genuinely too terse — marked "opt-edit".)

---

## Track 2 — MUST FIX (edits to draft.md)

| # | Where | Issue | Fix | Needs you? |
|---|-------|-------|-----|-----------|
| F1 | Architecture L68 | YHC struck "independent" → "separately computed" (layers overlap, esp. MGI/IMPC) | "six independent evidence layer computations" → "six separately computed evidence layers"; audit other "independent" uses (L72, L90, L207) | no |
| F2 | Abstract L17; Intro L60 | "orthogonal → complementary?" | "orthogonal" → "complementary" | no |
| F3 | Backgr. L29, ref [4] | "Ref 4 並非 10–15% undiagnosed" — citation may not support the figure | Verify ref [4] (Bonnet & El-Amraoui 2012). Fix citation or soften claim | **yes — need PDF of [4]** |
| F4 | Evidence L90 | MGI ⊃ IMPC (IMPC feeds MGI as MP annotations) → double-counting | Add a limitation sentence, OR de-dup + re-score | **yes — acknowledge vs. re-run** |
| F5 | Gene universe p4 | "supplementary table 列出 merged 和 excluded gene" | Add supplementary table (dedup-merged + 422 excluded genes) | no (confirm scope) |

## Track 1 — REPLY ONLY (answer to YHC, no edit)

### 1a. Reviewer's own comprehension notes — just confirm "yes, correct"
- Seed genes & similarity dimensions (expression / protein function / pathway / GO / PPI / mouse phenotype) — #9–17
- Zero-imputation penalizes under-studied genes — #21
- Single-cell photoreceptor data supplements retinal expression — #32–34
- NULL-preserve + weighted average over available layers, weights sum to 1.0 — #36–40
- Convergent multi-layer support = different layers support same gene from different angles — #55–56
- VANGL2 / stereociliary polarization corroboration — #150–152
- YWHAZ negative-control reasoning — #168–170

→ **Reply:** "Correct — that's exactly the intent." No paper change.

### 1b. "為什麼?" reader questions — answer in reply; opt-edit only if truly terse
- Weight = 0.20 / 0.15 rationale (#107, 111, 119, 123, 127, 133) — explain the biological basis per layer. *opt-edit: one-line rationale each*
- Six MeSH queries + how evidence tiers auto-classify (#142) — describe in reply. *opt-edit: list queries in supplement*
- How "direct experimental" is judged from PMID/MeSH/text-mining (#144) — explain tiering logic
- 75% threshold — how decided (#176): **already answered in text at L104** (post-hoc gate rationale). Just point YHC to it
- Curated keyword selection — when/how done (#174)
- "11,430 candidates — too many?" (#48): explain these are MEDIUM+HIGH *tiers*, actionable HIGH set = 95. *opt-edit: tighten wording*

### 1c. Open scope questions — discuss, decide later (likely "future work" in reply)
- Other gene lists (Blueprint Genetics 21, expanded USH-like set) — #68
- Split mouse (nocturnal) / zebrafish (diurnal); add C. elegans / FlyBase — #194–195
- USH vs ciliopathy framing consistency — #2, #59
- Define "candidate gene" vs "disease gene" — #88

---

## Bottom line
- **Real edits: F1, F2** (do now) + **F3, F4, F5** (need your call).
- **Everything else = a reply to YHC**, not a manuscript change.

---

## Cross-AI review (Fable + Codex GPT-5.5, xhigh) — consolidated verdicts

| Item | Me | Fable | Codex | Consolidated action |
|------|----|-------|-------|--------------------|
| F1 | keep | AGREE | AGREE (+nuance) | Keep. **Extend:** README.en.md, README.md still say "independent"/"orthogonal"; `transform.py:83,127` docstring still says "independent confirmation bonus" — fix these too before release |
| F2 | keep | AGREE | AGREE | Keep. Extend to READMEs/outline |
| F3 | must-fix, blocked | AGREE (fix all 3 instances; find ~85–90% yield source) | DISAGREE it's blocked — verifiable now; ref [4] suspect | Fix all 3 instances. Lead: **Bonnet 2016** reports biallelic dx 92.7%, overall mutation characterization 98.5% (n=427) — undercuts a clean "10–15% undiagnosed." Verify ref [4] identity + get correct source/number; don't fabricate |
| F4 | must-fix; quantify then decide | RE-SCORE by default | RE-SCORE (quantified) | **RE-SCORE.** Unanimous. |
| F5 | fix | AGREE | AGREE | Fix. Columns: original symbol/ID, retained canonical ID, merge/exclusion reason, counts matching 19,554 → 19,132/422 |

### F4 — the empirical case for re-scoring (Codex ran it on the local snapshot)
- 945 genes have IMPC phenotype evidence; **878 also have MGI evidence** (overlap is the rule, not an edge case).
- **All 24 HIGH-tier IMPC-positive genes are also MGI-positive.**
- Conservative simulation removing *only* the +0.3 IMPC bonus (leaving count-inflation untouched): **HIGH tier 95 → 85, 13 current HIGH genes demoted.**
- Two extra defects found in review (not in original triage):
  1. IMPC bonus is **not** ortholog-confidence-weighted, unlike mouse/zebrafish (Fable).
  2. Cilia-signal gate's "retains all ten OMIM genes" claim (draft.md:173) **depends on** the animal-model layer → must re-verify after re-score (Fable).
- **Fix:** collapse mouse evidence into one channel (union MGI∪IMPC MP terms per gene, count distinct, award one mouse bonus), confidence-weight it, then regenerate scores → tiers → validation (90.2% / 35-of-38) → sensitivity → Figures 2–3 → every per-candidate number in the narrative (VANGL2 0.909, YWHAZ 0.222, etc.) → text. Also update `transform.py` docstring and README.md:337 ("0.3 × IMPC 額外加分").

**Scope note:** F4 is a paper-wide numeric refresh, not a paragraph edit.

---

## IMPLEMENTATION STATUS (completed 2026-07-10)

- **F1 ✅** applied (manuscript + README.en.md + README.md + code docstring).
- **F2 ✅** applied (manuscript + READMEs).
- **F4 ✅ DONE — full re-score.** Code fix (`compute_phenotype_aggregates`, drop +0.3 IMPC bonus) test-first, 16/16 tests pass. Pipeline re-run from source; all numbers propagated through manuscript; figures + sensitivity + weight-learning + mantis-ml benchmark regenerated; PDF rebuilt. DB backed up at `data/pipeline.duckdb.bak-prerescore-20260710-030359`.
  - HIGH 95→83; known median 90.2→90.4% (35/38 held); **housekeeping in HIGH 1→0** (YWHAZ demoted, cleaner specificity story); all 10 OMIM genes retained by gate; sensitivity ρ 0.87→0.88.
  - Cross-AI re-review of the implementation: **Fable = code correct, IMPC-removal sound, narrative honest**; it caught 2 stale numbers (recall@20% 84.2→86.8%, line 181/213 zero-imputation endpoints) which are now fixed. Codex GPT-5.5 review could not run (usage limit until ~04:49).
- **F5 ✅** Additional files 1 (1,539 merged symbols) + 2 (423 excluded) via `scripts/supplementary_tables.py`; referenced in manuscript.
- **F3 ⏳ OPEN — needs user/partner decision.** ref [4] (Bonnet & El-Amraoui 2012) may not support "10–15% undiagnosed" (appears 3×). Literature ≈80% panel yield (~15–33% unsolved). Not edited pending the correct source.
- **Note:** 10 pre-existing `test_gnomad.py` failures (unrelated to this change; likely polars-version).

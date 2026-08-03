# Revision notes — response to review suggestions

**Manuscript:** UsherPipe (BMC Bioinformatics submission draft)
**Date:** 2026-08-03
**Files:** `manuscript/draft.md` (revised manuscript), `manuscript/draft.pdf` (rendered)

Thank you for these — they materially strengthened the Background, which was the
weakest part of the previous draft. All six suggestions have been incorporated.
This document records where each one went, every change made to the suggested
wording, and the reasoning wherever a suggestion was **not** adopted exactly as
written. A more granular technical log is in `manuscript/partner_edits_log.md`.

The reference list grew from **32 to 52** entries and was renumbered throughout.

---

## Summary

| # | Suggestion | Outcome |
|---|---|---|
| 1 | "Four key dimensions of disease biology" sentence | Adopted verbatim |
| 2 | Ciliary and stereociliary biology (Background subsection) | Adopted; 1 claim revised, 3 references corrected |
| 3 | Diagnostic gap and the shifted bottleneck | Adopted; split across two locations |
| 4 | Expanded Top candidate genes (Results) | Adopted; 3 references corrected, 1 data error fixed |
| 5 | Usher syndrome as a specialized sensory ciliopathy | Adopted; condensed 3 paragraphs → 2 |
| 6 | Replace "candidate gene" with "predicted candidate gene" | **Not adopted** — alternative applied, see below |

Plus one terminology pass: "mutation" → "disease-causing variant / allele" throughout.

---

## 1. "Four key dimensions" sentence

> Accordingly, we designed six complementary evidence layers to capture four key
> dimensions of disease biology: gene essentiality, sensory-cell specificity,
> molecular mechanisms, and functional evidence.

**Placed** in Background, in the final paragraph, after the three design principles
and before "The resulting composite is a multi-evidence support score…". "Accordingly"
resolves against the preceding gap analysis there, and the sentence makes design
principle (1)'s vague phrase "disease-specific biological dimensions" concrete at
the point where the claim is made. Inserted **verbatim**.

*Consequential trim:* this created a near-duplicate with the opening of
Implementation → Evidence layers, which read "UsherPipe integrates six evidence
layers, each capturing a distinct biological dimension relevant to Usher syndrome
pathobiology." That now reads "The six evidence layers are detailed below."

---

## 2. Ciliary and stereociliary biology

**Placed** in Background as `### Ciliary and stereociliary biology underlying Usher
syndrome`, immediately after the disease-background paragraph. Author–year citations
converted to the manuscript's numeric Vancouver style.

A second subsection heading, `### Limitations of existing gene prioritization
approaches`, was added before the existing tool-comparison paragraphs — otherwise
Background would carry one lone subheading followed by four unheaded paragraphs.
Easy to revert if you would rather not.

### Not adopted as written: the CLRN1 sentence

> **Suggested:** CLRN1, a tetraspan-like membrane protein associated with USH3A, is
> required for normal hair-bundle organization and is also implicated in
> photoreceptor maintenance (Nonarath, et al. 2025).
>
> **Revised to:** CLRN1, a tetraspan-like membrane protein associated with USH3A, is
> required for normal hair-bundle organization [15], and in the retina acts largely
> in Müller glia to support photoreceptor maintenance [16].

**Reason.** Nonarath et al. 2025 is a zebrafish study whose central finding is that
clarin-1 acts in **Müller glia** to maintain photoreceptors — the retinal role is
cell-non-autonomous. That is a mechanistically notable distinction, and flattening
it to "implicated in photoreceptor maintenance" loses the paper's actual result.
Separately, that paper does not establish the hair-bundle claim, so Geng et al. 2012
(a direct clarin-1 hair-bundle and mechanotransduction study) was added as `[15]` to
carry it.

---

## 3. Diagnostic gap and the shifted bottleneck

This paragraph overlapped existing text in two places, so it was **split**:

**3a — main body** (sentences 1, 2, 4, 5, 6) placed in Background ¶1, after the
sentence reporting the ~93% diagnostic yield and before ¶1's closing sentence on the
ciliopathy spectrum. Inserted verbatim.

Two trims in the surrounding text:

- ¶1's tail was removed: "…in approximately 93% of clinically diagnosed USH patients
  [4]~~, leaving roughly one in ten without a confirmed molecular diagnosis and
  suggesting that additional causative or modifier genes remain undiscovered~~." Your
  new sentences cover this in more detail.
- "these genes" → "the known Usher genes" in the ciliopathy-spectrum sentence. With
  the new paragraph intervening — and that paragraph discussing *novel* disease genes
  and modifier genes — the demonstrative had lost an unambiguous antecedent.

*Note on ordering:* the new paragraph sits **before** ¶1's ciliopathy-spectrum
sentence rather than after the whole paragraph, so that sentence still hands off
directly to the ciliary-biology subsection it introduces.

### Not adopted in place: sentence 3

> Existing gene-prioritization approaches primarily focus on variant interpretation,
> phenotype matching, or similarity to previously characterized disease genes, making
> them less suited for discovering novel Usher syndrome candidate genes.

**Reason.** This is a compressed preview of the entire *Limitations of existing gene
prioritization approaches* subsection, and it duplicated that subsection's existing
opener. It was **moved there** and now replaces the old second sentence. Only wording
change: "existing gene-prioritization approaches" → "existing approaches", since the
preceding sentence already says "gene prioritization".

---

## 4. Expanded Top candidate genes

The VANGL2, DYNC1H1, PAFAH1B1 and ATP2B2 paragraphs were replaced with the expanded
versions. The ARL3/AHI1 sanity-check and Na⁺/K⁺-ATPase paragraphs that follow were
left untouched.

### One data error, present in the previous draft too

**DYNC1H1 animal-model score: 0.169 → 0.170.** Every score quoted in the section was
re-checked against `data/report/candidates.tsv`; the stored value is 0.17048. All
other figures matched.

**Not an error:** VANGL2's composite score (0.80242) and gnomAD score (0.80245) really
are near-identical. This is a coincidence, not a copy-paste slip — worth knowing in
case a reviewer queries it.

### Other changes to the suggested wording

- **Duplicate OMIM number merged.** The text read "classical lissencephaly (OMIM
  #607432)—a severe cortical malformation—or Subcortical laminar heterotopia (OMIM
  #607432)", citing the same number twice. Both phenotypes do fall under #607432, so
  this now reads "…cortical malformations, including classical lissencephaly and
  subcortical laminar heterotopia (both OMIM #607432)".
- **PAFAH1B1 gene OMIM added** (`*601545`) for consistency with VANGL2 and DYNC1H1,
  which were given gene-level numbers.
- **MGI citations added.** The text refers to the Mouse Genome Informatics database
  twice in prose without citing it; both now point to `[36]`, the MGD reference
  already in the list.
- **Formatting normalized** to the section's conventions: single parenthetical
  `(OMIM *600533; composite score: 0.802, 5 layers)` rather than two; mouse gene
  symbols italicised; "five network layers" → "5 layers" (the pipeline has no network
  layer).
- **Typographical:** "VANGL2mutant mice" → "*Vangl2* mutant mice"; "In human, Current
  evidence" → "In humans, current evidence".

### Open question for you

The previous VANGL2 opener named **"the coordinated orientation of stereocilia bundles
on cochlear hair cells"** — the most Usher-relevant framing in that paragraph. The
expanded version demotes this to "planar orientation of inner ear hair cells" inside a
five-item list of general PCP roles. Happy to restore the hair-cell emphasis up front
while keeping the rest of the expansion, if you agree.

---

## 5. Usher syndrome as a specialized sensory ciliopathy

**Placed** in Background as `### Usher syndrome as a specialized sensory ciliopathy`,
between the diagnostic-gap paragraph and the ciliary-biology subsection. It absorbs
and replaces the single-sentence paragraph that previously bridged to the ciliary
material.

### Condensed from three paragraphs to two

The passage collided with existing text in three places and repeated itself in a
fourth:

| Suggested sentence | Collided with | Resolution |
|---|---|---|
| P2 s1 — "core clinical features… hearing loss and retinal degeneration, vestibular dysfunction in some" | Background ¶1: "Patients present with sensorineural hearing loss, vestibular dysfunction, and progressive retinitis pigmentosa" | Dropped |
| P2 s2 — "Most Usher proteins participate in… trafficking, cell adhesion…" | Closing sentence of the ciliary-biology subsection: "Together, Usher proteins participate in cell adhesion, macromolecular scaffolding, intracellular trafficking…" | Condensed into the subordinate clause opening P2 |
| P2 s3 — "may therefore be regarded as a highly specialized sensory ciliopathy" | The bridging paragraph it replaced | Kept; the old paragraph's unique closing clause folded in |
| P3 — "A key distinction is that broad ciliopathies arise from general defects…" | P2 s4–s5, which make the same point | Merged into P2 s4 as the colon clause |

### Citation added

P1 defines ciliopathies as a disease class but carried no citation — an unreferenced
definitional claim a reviewer would likely query. Reiter & Leroux, *Genes and
molecular pathways underpinning ciliopathies*, was already in the reference list and
is exactly the right source, so it is now cited there. No new reference introduced.

### Note

This passage still overlaps the **Cilia-specific databases** paragraph in
*Limitations*, which argues the same point about CiliaCarta and CilioGenics ("both
tools address a different question — 'Is this gene ciliary?' rather than 'Is this
gene a candidate for Usher syndrome?'"). This now reads as deliberate
setup-then-payoff — Background states the principle, Limitations applies it to
specific tools — but say the word if you would rather trim one.

---

## 6. "candidate gene" → "predicted candidate gene" — **not adopted**

**The concern:** that "candidate gene" could be misread as meaning a *known*
disease-causing gene.

**What we found.** Clinical genetics already draws this line formally, and draws it
the other way. The 2024 ACMG / *Genetics in Medicine* statement on reporting novel
candidate genes defines the two terms in direct opposition:

> **novel candidate gene** — "a gene in a newly-proposed gene-disease relationship.
> The gene either has not yet been implicated in any Mendelian condition or… is being
> proposed to underlie a novel phenotype…"
>
> **known gene** — "a gene with at least a Moderate score of gene-disease validity
> according to the ClinGen framework"

NHGRI's glossary agrees: a candidate gene is one "**believed** to be related to a
particular trait… **suspected** to play a role… making it worthy of additional
investigation." So "not yet established" is precisely what the term *does* mean to a
geneticist — it is the one reading the word reliably excludes.

**Why not "predicted".** Two reasons:

1. It is pleonastic — "candidate" already carries "not established", so "predicted
   candidate" hedges a hedge.
2. More seriously, it misdescribes the method. Table 1 marks "Machine-learned
   scoring" as **—** for UsherPipe. mantis-ml legitimately says "predictions" because
   it *is* a trained semi-supervised learner; Exomiser and the general literature say
   "prioritize". Adopting "predicted" would borrow mantis-ml's vocabulary without its
   method, and invite the reviewer question "predicted by what classifier, trained on
   what, with what performance?" — which the paper currently does not have to answer.

**However, your instinct pointed at a real problem.** "Candidate gene *approach*" /
"candidate gene *study*" is an entrenched study-design term for a hypothesis-driven
analysis of *pre-specified* genes chosen on prior biological knowledge, defined in the
literature by explicit contrast with genome-wide, hypothesis-free designs. In that
idiom the candidates are genes one already suspects — often already well
characterised, which is close to your concern. This matters for UsherPipe
specifically, because being genome-wide and seed-free is the paper's central claim.

### What was done instead

The compound "candidate gene" was removed wherever it could be read as a study-design
label, and the term was defined once, explicitly:

| Location | Before | After |
|---|---|---|
| Title | "…under-studied Usher syndrome and ciliopathy **candidate genes**" | "…under-studied Usher syndrome and ciliopathy **genes**" |
| Keywords | "candidate gene discovery" | "disease gene discovery" |
| Background | "**candidate-gene** discovery for Usher syndrome therefore draws on…" | "**gene** discovery for Usher syndrome therefore draws on…" |

And in Background, at the first substantive use:

> Throughout, we use *candidate* in the sense established by the ClinGen gene–disease
> validity framework [5]: a gene in a proposed but not yet established gene–disease
> relationship, as distinct from the ten known Usher genes.

This defines the *term* by reference to ClinGen; it deliberately does **not** say the
pipeline computes or filters on ClinGen validity, which it does not. Stronger phrasing
such as "genes below ClinGen Moderate validity" was avoided because it would read as a
claim about the composition of the gene set.

Plain "candidate" is unchanged elsewhere (~28 uses) — it is the field-standard term
for exactly what we mean, and the definition now pins it.

---

## 7. Terminology: "mutation" → "disease-causing variant / allele"

Following current HGVS and ACMG practice, which avoids "mutation" because it conflates
*a sequence change* with *pathogenicity*.

| Location | Before | After |
|---|---|---|
| Literature mining tier | "knockout/**mutation** in cilia/sensory context" | "knockout or **disease-causing variant** in cilia/sensory context" |
| ATP2B2 | "carries a spontaneous *Atp2b2* **mutation**" | "carries a spontaneous **disease-causing** *Atp2b2* **allele**" |

"mutation" now appears zero times in the manuscript body. **Reference titles were not
altered** — eight carry "mutation(s)" in their published titles and must be quoted
verbatim. "Mutant" was retained in mouse-genetics contexts ("*Vangl2* mutant mice"),
where it remains standard usage and is the term MGI itself curates under.

---

## Reference corrections

Every suggested reference was verified against publisher records. **Six problems were
found across the eighteen supplied**, including two wrong first authors:

| Suggested entry | Problem | Corrected to |
|---|---|---|
| Maerker et al. **2008a** *and* **2008b** | Duplicate — the two entries are the same paper (identical title, journal, volume, pages) | Merged into one reference |
| Lefèvre et al. 2008 | **No journal, volume or pages given** | *Development.* 2008;135(8):1427-1437 |
| Schwander et al. 2010 | Page range truncated to first page | J Cell Biol. 2010;190(1):9-**20** |
| "Nagaoka T, et al." Semin Cell Dev Biol. 2018;81:62-70 | **Wrong authors.** Journal, volume and pages are correct, but that review is by Bailly, Walton and Borg (PMID 29111415). Nagaoka has other Vangl2 papers, not this one. | Bailly E, Walton A, Borg JP |
| "Phillips HM, et al." Trends Cardiovasc Med. 2006;16:38-45 | **Wrong first author** — Phillips is the middle author (PMID 16473760) | Henderson DJ, Phillips HM, Chaudhry B |
| Chong SS, et al. Am J Hum Genet. 1996;59(Suppl):A23 | **Meeting abstract only**, never published as a full paper — likely to draw a reviewer objection | Lo Nigro C, et al. Hum Mol Genet. 1997;6(2):157-164 — the peer-reviewed publication of the same work, on which Chong is a co-author |

Kibar 2011's DOI was also off by a few digits (…01539.x should be …01515.x), but the
manuscript's reference style carries no DOIs, so it was simply dropped. The remaining
eleven suggested references were confirmed correct exactly as given.

### References added (18 new entries)

Bailly 2018 · Bahloul 2010 · Cosgrove & Zallocchi 2014 · El-Amraoui & Petit 2005 ·
Geng 2012 · Henderson 2006 · Hertecant 2016 · Kibar 2011 · Kremer 2006 · Lefèvre 2008 ·
Lo Nigro 1997 · Maerker 2008 · Nonarath 2025 · Pilz 1999 · Reiner 1993 · Sahly 2012 ·
Schwander 2010 · Strande 2017 · Wang 2023 · Yang 2010

---

## Renumbering

Inserting references early in Background required renumbering the whole list
(**32 → 52** entries). The opportunity was taken to fix four entries that were already
out of first-appearance order in the previous draft:

- CZ CELLxGENE and KEGG had been appended to the end of the list rather than inserted
  at their point of first citation in the Evidence layers section.
- In Results → Top candidate genes, two pairs of references were cited out of order.

**Verified programmatically:** all 52 references are cited, in strict order of first
appearance, with no gaps and no dangling numbers.

---

## Open items

1. **VANGL2 opener** — restore the "coordinated orientation of stereocilia bundles on
   cochlear hair cells" framing? (Section 4 above.)
2. **A weak citation predating these edits.** Reiter & Leroux (*Genes and molecular
   pathways underpinning ciliopathies*) is cited in the PAFAH1B1 paragraph for "LIS1
   mediates dynein-dependent centrosome positioning and microtubule-based transport".
   That is a general ciliopathy review and a weak source for the specific claim; it
   should probably be replaced with a dynein/LIS1 primary source.
3. **Background subheadings** — three `###` subsections were introduced. Confirm this
   suits BMC Bioinformatics' Background conventions.
4. **Overlap between the new ciliopathy passage and the Cilia-specific databases
   paragraph** (Section 5 above) — keep as setup-and-payoff, or trim one?

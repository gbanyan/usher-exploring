# Log of partner-suggested edits applied to `draft.md`

Running record of suggestions received from the research partner, where each was
placed, and any changes made to the suggested wording or citations.
Started 2026-08-03. Reference numbering is Vancouver / BMC style: numbered
sequentially in order of first appearance in the text.

---

## Edit 1 — "four key dimensions" sentence

**Suggested text (verbatim):**

> Accordingly, we designed six complementary evidence layers to capture four key
> dimensions of disease biology: gene essentiality, sensory-cell specificity,
> molecular mechanisms, and functional evidence.

**Placed:** Background, final paragraph ("Here, we present UsherPipe…"), inserted
after the three design principles and before "The resulting composite is a
multi-evidence support score…".

**Rationale:** "Accordingly" resolves against the preceding gap analysis, and the
sentence makes design principle (1)'s otherwise vague phrase "disease-specific
biological dimensions" concrete at the point where the claim is made.

**Changes to suggested wording:** none — inserted verbatim.

---

## Edit 2 — consequential trim (follow-on to Edit 1)

Edit 1 created a near-duplicate with the opening of Implementation → Evidence
layers, which read:

> ~~UsherPipe integrates six evidence layers, each capturing a distinct biological
> dimension relevant to Usher syndrome pathobiology.~~ All scores are normalized to
> the [0, 1] interval, with NULL indicating missing evidence.

Now reads:

> The six evidence layers are detailed below. All scores are normalized to the
> [0, 1] interval, with NULL indicating missing evidence.

---

## Edit 3 — Background subsection on ciliary and stereociliary biology

**Placed:** Background, as `### Ciliary and stereociliary biology underlying Usher
syndrome`, immediately after the disease-background paragraph (which ends
"…motivating the genome-wide, ciliopathy-aware scope adopted here.") and before
the discussion of existing prioritization tools.

**Changes to suggested wording:**

1. **Author–year citations converted to numeric** to match the draft's existing
   Vancouver style (e.g. `(Cosgrove and Zallocchi 2014; Maerker et al. 2008b;
   Sahly et al. 2012)` → `[5-7]`).

2. **A second subsection heading was added** — `### Limitations of existing gene
   prioritization approaches`, before "Computational gene prioritization has
   become a standard approach…". Without it, Background would carry one lone `###`
   heading followed by four unheaded paragraphs. Trivially revertible if not wanted.

3. **CLRN1 sentence revised** — this is the one substantive change to the science,
   flagged for review:

   Suggested:
   > CLRN1, a tetraspan-like membrane protein associated with USH3A, is required
   > for normal hair-bundle organization and is also implicated in photoreceptor
   > maintenance (Nonarath, et al. 2025).

   Applied:
   > CLRN1, a tetraspan-like membrane protein associated with USH3A, is required
   > for normal hair-bundle organization [14], and in the retina acts largely in
   > Müller glia to support photoreceptor maintenance [15].

   *Reason:* Nonarath et al. 2025 is a zebrafish study establishing that clarin-1
   acts in **Müller glia** to maintain photoreceptors — the retinal role is
   cell-non-autonomous, which is a mechanistically notable distinction worth
   stating rather than flattening. That paper also does not establish the
   hair-bundle claim, so Geng et al. 2012 (`[14]`, a direct clarin-1 hair-bundle
   and mechanotransduction study) was added to carry it.

### Reference corrections

Verified all 11 suggested references against publisher records. Three problems found:

| Suggested entry | Problem | Corrected to |
|---|---|---|
| Maerker et al. **2008a** and **2008b** | Duplicate — the two entries are the same paper (identical title, journal, volume, pages) | Merged into a single reference `[6]` |
| Lefèvre et al. 2008 | **No journal, volume, or pages given** | *Development.* 2008;135(8):1427-1437 |
| Schwander et al. 2010 | Page range truncated to first page only | J Cell Biol. 2010;190(1):9-**20** |

The other eight suggested references were confirmed correct as given.

### New references added (final numbering)

| # | Reference |
|---|---|
| 5 | Cosgrove D, Zallocchi M. Usher protein functions in hair cells and photoreceptors. Int J Biochem Cell Biol. 2014;46:80-89. |
| 6 | Maerker T, et al. A novel Usher protein network at the periciliary reloading point between molecular transport machineries in vertebrate photoreceptor cells. Hum Mol Genet. 2008;17(1):71-86. |
| 7 | Sahly I, et al. Localization of Usher 1 proteins to the photoreceptor calyceal processes, which are absent from mice. J Cell Biol. 2012;199(2):381-399. |
| 8 | El-Amraoui A, Petit C. Usher I syndrome: unravelling the mechanisms that underlie the cohesion of the growing hair bundle in inner ear sensory cells. J Cell Sci. 2005;118(Pt 20):4593-4603. |
| 9 | Lefèvre G, et al. A core cochlear phenotype in USH1 mouse mutants implicates fibrous links of the hair bundle in its cohesion, orientation and differential growth. Development. 2008;135(8):1427-1437. |
| 10 | Schwander M, Kachar B, Müller U. The cell biology of hearing. J Cell Biol. 2010;190(1):9-20. |
| 11 | Bahloul A, et al. Cadherin-23, myosin VIIa and harmonin, encoded by Usher syndrome type I genes, form a ternary complex and interact with membrane phospholipids. Hum Mol Genet. 2010;19(18):3557-3565. |
| 12 | Wang H, et al. Temporal and spatial assembly of inner ear hair cell ankle link condensate through phase separation. Nat Commun. 2023;14(1):1657. |
| 13 | Yang J, et al. Ablation of whirlin long isoform disrupts the USH2 protein complex and causes vision and hearing loss. PLoS Genet. 2010;6(5):e1000955. |
| 14 | Geng R, et al. The mechanosensory structure of the hair cell requires clarin-1, a protein encoded by Usher syndrome III causative gene. J Neurosci. 2012;32(28):9485-9498. |
| 15 | Nonarath HJT, et al. The USH3A causative gene clarin1 functions in Müller glia to maintain retinal photoreceptors. PLoS Genet. 2025;21(3):e1011205. |
| 16 | Kremer H, et al. Usher syndrome: molecular links of pathogenesis, proteins and pathways. Hum Mol Genet. 2006;15(Spec No 2):R262-R270. |

Note: `[14]` (Geng 2012) is the only entry not in the suggested list — added to
support the revised CLRN1 hair-bundle claim (see above). All 12 new references
occupy `[5]`–`[16]`; the previous draft's `[5]`–`[32]` shifted to `[17]`–`[44]`.

### Global renumbering

Inserting 12 references early in Background required renumbering the entire list
(32 → 44 entries). The opportunity was taken to fix four entries that were already
out of first-appearance order in the previous draft:

- `[31]` (CZ CELLxGENE) and `[32]` (KEGG) had been appended to the end of the list
  rather than inserted at their point of first citation in the Evidence layers section.
- `[25]` was cited before `[24]`, and `[27]` before `[26]`, in Results → Top candidate genes.

All 44 references are now cited, in order, with no gaps and no dangling numbers
(verified programmatically).

---

## Edit 4 — diagnostic gap and the shifted bottleneck

**Placed:** Background, split across two locations (see below). No new references,
so numbering is unaffected.

The suggested paragraph overlapped existing text in two places, so it was split
rather than inserted whole:

### 4a — main body of the paragraph

Placed as a new paragraph in Background ¶1, directly after the sentence reporting
the ~93% diagnostic yield and **before** ¶1's closing sentence on the ciliopathy
spectrum. Sentences 1, 2, 4, 5 and 6 inserted verbatim.

Two consequential trims in the surrounding text:

- **¶1 tail removed.** The sentence had read "…in approximately 93% of clinically
  diagnosed USH patients [4]~~, leaving roughly one in ten without a confirmed
  molecular diagnosis and suggesting that additional causative or modifier genes
  remain undiscovered~~." The struck clause is now covered, in more detail, by the
  new paragraph's first two sentences.
- **"these genes" → "the known Usher genes"** in the ciliopathy-spectrum sentence.
  With the new paragraph intervening — and that paragraph discussing *novel*
  disease genes and modifier genes — the original demonstrative no longer had an
  unambiguous antecedent.

*Note on ordering:* the new paragraph was placed **before** ¶1's ciliopathy-spectrum
sentence rather than after the whole paragraph, so that sentence ("…motivating the
genome-wide, ciliopathy-aware scope adopted here") still hands off directly to the
`### Ciliary and stereociliary biology` subsection it introduces.

### 4b — sentence 3 relocated

Sentence 3 of the suggested paragraph is a compressed preview of the entire
*Limitations of existing gene prioritization approaches* subsection, and duplicated
that subsection's existing opener. It was moved there:

Before:
> Computational gene prioritization has become a standard approach for narrowing
> candidate gene lists in rare disease research. ~~However, existing tools present
> fundamental limitations when applied to under-studied gene discovery for
> ciliopathies.~~

After:
> Computational gene prioritization has become a standard approach for narrowing
> candidate gene lists in rare disease research. **However, existing approaches
> primarily focus on variant interpretation, phenotype matching, or similarity to
> previously characterized disease genes, making them less suited for discovering
> novel Usher syndrome candidate genes.**

Only change to the suggested wording: "existing gene-prioritization approaches" →
"existing approaches", since the preceding sentence already says "gene
prioritization".

---

## Edit 5 — expanded Top candidate genes (Results)

**Placed:** Results → Top candidate genes. The VANGL2, DYNC1H1, PAFAH1B1 and
ATP2B2 paragraphs were replaced with the expanded versions. The ARL3/AHI1
sanity-check paragraph and the Na⁺/K⁺-ATPase paragraph that follow were left
untouched. Seven new references added; the list is now 51 entries.

### All scores re-verified against pipeline output

Every score quoted was checked against `data/report/candidates.tsv`. One error,
present in **both** the previous draft and the suggested text:

- **DYNC1H1 animal-model score: 0.169 → 0.170.** The stored value is 0.17048,
  which rounds to 0.170.

Everything else matched: VANGL2 (composite 0.8024, animal 0.6398, literature
0.9396, gnomAD 0.8025, 5 layers); DYNC1H1 (0.8258, localization 1.0, literature
0.9981, gnomAD 0.9658, 6 layers); PAFAH1B1 (0.7983, localization 1.0, literature
0.9879, gnomAD 0.9689, animal 0.0479, 6 layers); ATP2B2 (0.7862, 5 layers).

**Not an error:** VANGL2's composite score (0.80242) and gnomAD score (0.80245)
really are near-identical — a coincidence, not a copy-paste slip. Worth knowing in
case a reviewer queries it.

### Reference corrections

Verified all seven suggested references. **Two carry the wrong first author**, and
one is a meeting abstract:

| Suggested | Problem | Corrected to |
|---|---|---|
| Nagaoka T, et al. Semin Cell Dev Biol. 2018;81:62-70 | **Wrong authors.** Journal, volume and pages are right, but that review is by Bailly, Walton and Borg. Nagaoka has other Vangl2 papers, none of them this one. | Bailly E, Walton A, Borg JP. (PMID 29111415) |
| Phillips HM, et al. Trends Cardiovasc Med. 2006;16:38-45 | **Wrong first author.** Phillips is the middle author. | Henderson DJ, Phillips HM, Chaudhry B. (PMID 16473760) |
| Chong SS, et al. Am J Hum Genet. 1996;59(Suppl):A23 | **Meeting abstract only** — never a full paper, and likely to draw a reviewer objection. | Lo Nigro C, et al. Hum Mol Genet. 1997;6(2):157-164 — the peer-reviewed publication of the same work, on which Chong is a co-author |
| Kibar Z, et al. doi:10.1111/j.1399-0004.2010.01539.x | DOI digits wrong (correct is …01515.x) | Moot — the manuscript's reference style carries no DOIs, so it was dropped |

Kibar 2011, Hertecant 2016, Pilz 1999 and Reiner 1993 were confirmed correct
exactly as given (journal, volume, issue, pages all verified).

### New references added

| # | Reference |
|---|---|
| 38 | Bailly E, Walton A, Borg JP. The planar cell polarity Vangl2 protein: from genetics to cellular and molecular functions. Semin Cell Dev Biol. 2018;81:62-70. |
| 39 | Henderson DJ, Phillips HM, Chaudhry B. Vang-like 2 and noncanonical Wnt signaling in outflow tract development. Trends Cardiovasc Med. 2006;16(2):38-45. |
| 40 | Kibar Z, et al. Contribution of VANGL2 mutations to isolated neural tube defects. Clin Genet. 2011;80(1):76-82. |
| 42 | Hertecant J, et al. A novel de novo mutation in DYNC1H1 gene underlying malformation of cortical development and cataract. Meta Gene. 2016;9:124-127. |
| 44 | Lo Nigro C, et al. Point mutations and an intragenic deletion in LIS1, the lissencephaly causative gene in isolated lissencephaly sequence and Miller-Dieker syndrome. Hum Mol Genet. 1997;6(2):157-164. |
| 45 | Pilz DT, et al. Subcortical band heterotopia in rare affected males can be caused by missense mutations in DCX (XLIS) or LIS1. Hum Mol Genet. 1999;8(9):1757-1760. |
| 46 | Reiner O, et al. Isolation of a Miller-Dieker lissencephaly gene containing G protein beta-subunit-like repeats. Nature. 1993;364(6439):717-721. |

Existing `[38]`–`[44]` shifted to `[41]`, `[43]`, `[47]`, `[48]`, `[49]`, `[50]`,
`[51]`. All 51 references cited, in order, no gaps (verified programmatically).

### Other changes to the suggested wording

- **Duplicate OMIM number merged.** The suggestion read "classical lissencephaly
  (OMIM #607432)—a severe cortical malformation—or Subcortical laminar heterotopia
  (OMIM #607432)", citing the same number twice. Both phenotypes do fall under
  #607432, so this now reads "…cortical malformations, including classical
  lissencephaly and subcortical laminar heterotopia (both OMIM #607432)".
- **PAFAH1B1 gene OMIM added** (`*601545`, verified) for consistency with VANGL2
  and DYNC1H1, which the suggestion gave gene-level numbers for.
- **MGI citations added.** The suggestion refers to the Mouse Genome Informatics
  database twice in prose without citing it; both now point to `[34]`, the MGD
  reference already in the list.
- **Formatting normalized** to the section's existing conventions: `(OMIM *600533;
  composite score: 0.802, 5 layers)` as a single parenthetical rather than two;
  mouse gene symbols italicized (*Vangl2*, *Dync1h1*, *Pafah1b1*, *Atp2b2*);
  "five network layers" → "5 layers" (there is no network layer in this pipeline).
- **Typographical fixes:** "VANGL2mutant mice" → "*Vangl2* mutant mice"; "In human,
  Current evidence" → "In humans, current evidence"; ligature characters ("suﬀicient")
  normalized.

### Flagged, not changed

`[43]` (Reiter & Leroux, *Genes and molecular pathways underpinning ciliopathies*)
is cited for "LIS1 mediates dynein-dependent centrosome positioning and
microtubule-based transport". This is a general ciliopathy review and is a weak
source for that specific claim. The mis-citation predates this edit — worth
replacing with a dynein/LIS1 primary source, but left as-is pending a decision.
(After Edit 6 this reference is renumbered `[5]`.)

---

## Edit 6 — Usher syndrome as a specialized sensory ciliopathy

**Placed:** Background, as a new subsection `### Usher syndrome as a specialized
sensory ciliopathy`, sitting between the diagnostic-gap paragraph and
`### Ciliary and stereociliary biology underlying Usher syndrome`. It **absorbs and
replaces** the single-sentence paragraph that previously bridged to the ciliary
material.

### What was deduplicated

The suggested passage collided with existing text in three places and repeated
itself in a fourth, so it was condensed from three paragraphs to two:

| Suggested sentence | Collided with | Resolution |
|---|---|---|
| P2 s1 — "The core clinical features of Usher syndrome are sensorineural hearing loss and retinal degeneration, with vestibular dysfunction also present in some patients." | Background ¶1: "Patients present with sensorineural hearing loss, vestibular dysfunction, and progressive retinitis pigmentosa." | Dropped |
| P2 s2 — "Most Usher proteins participate in the biology of hair-cell stereocilia, the photoreceptor connecting cilium, the periciliary membrane complex, protein trafficking, cell adhesion, and sensory signal transduction." | Closing sentence of the ciliary-biology subsection: "Together, Usher proteins participate in cell adhesion, macromolecular scaffolding, intracellular trafficking…" | Condensed to a subordinate clause opening P2 ("Because the known Usher genes encode ciliary and periciliary proteins acting at hair-cell stereocilia, the photoreceptor connecting cilium, and the periciliary membrane complex…") |
| P2 s3 — "Usher syndrome may therefore be regarded as a highly specialized sensory ciliopathy." | The replaced bridging paragraph: "Usher syndrome is considered part of the broader ciliopathy spectrum" | Kept; the old paragraph was absorbed, and its unique closing clause ("motivating the genome-wide, ciliopathy-aware scope adopted here") folded into the end of P2 |
| P3 — "A key distinction is that broad ciliopathies arise from general defects in ciliary assembly, transport, or signaling, whereas Usher syndrome is defined by the combined auditory–retinal phenotype." | P2 s4–s5, which make the same point | Merged into P2 s4 as the colon clause |

### Citation added

P1 defines ciliopathies as a disease class but carried no citation — an
unreferenced definitional claim that a reviewer would likely query. Reiter &
Leroux, *Genes and molecular pathways underpinning ciliopathies* (Nat Rev Mol Cell
Biol 2017), was already in the reference list and is exactly the right source, so
it is now cited there. No new reference was introduced; the list stays at 51.

Because that reference now first appears in Background rather than in Results, it
moved from `[43]` to `[5]`, shifting the old `[5]`–`[42]` up to `[6]`–`[43]`.
`[44]`–`[51]` are unchanged. All 51 references cited, in order, no gaps (verified).

### Note

The suggested passage still overlaps the **Cilia-specific databases** paragraph in
the *Limitations* subsection, which argues the same point about CiliaCarta and
CilioGenics ("both tools address a different question — 'Is this gene ciliary?'
rather than 'Is this gene a candidate for Usher syndrome?'"). This is now a
deliberate setup-then-payoff rather than a duplication: Background states the
principle, Limitations applies it to specific tools. Flagged in case you would
rather trim one.

---

## Edit 7 — terminology: "candidate gene"

**Raised by:** the concern that "candidate gene" could be misread as meaning a
*known* disease-causing gene, with "predicted candidate gene" proposed instead.

**Outcome:** the term "candidate" was kept, and defined explicitly instead. The
reasoning is below, since it goes against the original suggestion.

### What the literature says

Clinical genetics already draws this line formally, and draws it the other way.
The 2024 ACMG / *Genetics in Medicine* statement on reporting novel candidate
genes defines the two terms in direct opposition:

> **novel candidate gene** — "a gene in a newly-proposed gene-disease
> relationship. The gene either has not yet been implicated in any Mendelian
> condition or… is being proposed to underlie a novel phenotype…"
>
> **known gene** — "a gene with at least a Moderate score of gene-disease validity
> according to the ClinGen framework"

NHGRI's glossary agrees: a candidate gene is one "**believed** to be related to a
particular trait… **suspected** to play a role… making it worthy of additional
investigation". So "not yet established" is precisely what the word *does* mean to
a geneticist — it is the one reading the term reliably excludes.

**However, a different ambiguity is real.** "Candidate gene approach" / "candidate
gene *study*" is an entrenched study-design term for a *hypothesis-driven analysis
of pre-specified genes chosen on prior biological knowledge*, defined in the
literature by explicit contrast with genome-wide, hypothesis-free designs. In that
idiom the candidates are genes one already suspects — often already well
characterized, which is close to the original concern. This matters for UsherPipe
specifically, because being genome-wide and seed-free is the paper's central claim.

### Why not "predicted candidate gene"

1. Pleonastic — "candidate" already carries "not established", so "predicted
   candidate" hedges a hedge.
2. It misdescribes the method. Table 1 marks "Machine-learned scoring" as **—** for
   UsherPipe. mantis-ml legitimately says "predictions" because it *is* a trained
   semi-supervised learner; Exomiser and the general literature say "prioritize".
   Adopting "predicted" would borrow mantis-ml's vocabulary without its method and
   invite "predicted by what classifier, trained on what, with what performance?" —
   a reviewer question the paper currently does not have to answer.

### Changes applied

| Location | Before | After |
|---|---|---|
| Title | "…under-studied Usher syndrome and ciliopathy **candidate genes**" | "…under-studied Usher syndrome and ciliopathy **genes**" |
| Keywords | "candidate gene discovery" | "disease gene discovery" |
| Background, ciliopathy subsection | "**candidate-gene** discovery for Usher syndrome therefore draws on…" | "**gene** discovery for Usher syndrome therefore draws on…" |

All three removed the *compound* "candidate gene" where it could be read as a
study-design label. Plain "candidate" for pipeline output is unchanged throughout
(~28 uses) — it is the field-standard term for exactly what is meant.

### Definition added

At the first substantive use, in Background ¶2:

> Throughout, we use *candidate* in the sense established by the ClinGen
> gene–disease validity framework [5]: a gene in a proposed but not yet established
> gene–disease relationship, as distinct from the ten known Usher genes.

**Deliberate precision:** this defines the *term* by reference to ClinGen; it does
not say the pipeline computes or filters on ClinGen validity, which it does not.
Stronger phrasing such as "genes below ClinGen Moderate validity" was avoided
because it would read as a claim about the composition of the gene set.

### Reference added

`[5]` Strande NT, et al. Evaluating the clinical validity of gene-disease
associations: an evidence-based framework developed by the Clinical Genome
Resource. Am J Hum Genet. 2017;100(6):895-906.

Old `[5]`–`[51]` shifted to `[6]`–`[52]`. All 52 references cited, in order, no
gaps (verified).

---

## Edit 8 — terminology: "mutation" → "disease-causing variant / allele"

Following current HGVS and ACMG practice, which avoids "mutation" because it
conflates *a sequence change* with *pathogenicity*, and states the two separately.

Only two body-text occurrences remained, because Edit 5 had already converted the
DYNC1H1 and PAFAH1B1 descriptions ("high-impact **variants** cause…", "its
loss-of-function **alleles** cause…"):

| Location | Before | After |
|---|---|---|
| Implementation → Literature mining | "direct experimental (knockout/**mutation** in cilia/sensory context, weight 1.0)" | "direct experimental (knockout or **disease-causing variant** in cilia/sensory context, weight 1.0)" |
| Results → ATP2B2 | "carries a spontaneous *Atp2b2* **mutation**" | "carries a spontaneous **disease-causing** *Atp2b2* **allele**" |

"mutation" now appears **zero** times in the manuscript body.

### Deliberately not changed

**Reference titles.** Eight references carry "mutation(s)" or "mutational" in their
published titles (e.g. `[43]` "**Mutations** in the tail domain of DYNC1H1…",
`[48]` "**Mutations** in a plasma membrane Ca2+-ATPase gene cause deafness in
deafwaddler mice"). Published titles are quoted verbatim and must not be altered.

**"mutant" in mouse-genetics contexts** — a different word, and still standard
usage in model-organism genetics; MGI itself curates "mutant alleles". Three uses
remain:

- Results → VANGL2: "*Vangl2* **mutant** mice show inner ear and neural tube defects"
- Results → PAFAH1B1: "*Pafah1b1* **mutant** phenotypes are concentrated in…"
- Results → ATP2B2: "**Homozygous mutants** show growth retardation…"

The first two are adjectival and conventional; recommend keeping. The third is a
bare noun ("mutants" for the animals themselves) and would read better as
"Homozygous animals" — pending a decision.

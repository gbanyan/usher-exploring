"""Apply the dated human-review/GO source alignment with explicit old-text guards.

One-time editorial migration; no score, cohort or database changes.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / "revision/major_revision_20261006"


def replace(path, old, new):
    text = path.read_text()
    if new in text and old not in text:
        return
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one editorial anchor in {path}: {old[:90]}")
    path.write_text(text.replace(old, new))


def main():
    main = ROOT / "manuscript/draft.md"
    supp = ROOT / "manuscript/supplementary_methods.md"
    response = REV / "rebuttal.md"
    cover = REV / "cover_letter_revision.md"
    replace(main,
        "The 45 principal clinical and date classifications were screened with AI assistance and have not yet been individually verified by a human author; their eligibility and the resulting temporal estimates remain provisional.",
        "The 45 principal clinical/date classifications were initially screened with AI assistance. After the frozen analysis, a human author reviewed primary reports and reported family/pedigree information for every case, together with phenotype, inheritance, function and publication chronology. This review did not constitute blinded pre-outcome adjudication. Family-evidence concerns and the retained original denominators are described in Results and S6.6.")
    replace(main,
        "The 45-case literature-screened cohort has not yet been individually verified by a human author and remains provisional.",
        "Human author review subsequently covered primary reports for all 45 temporal cases, including reported family/pedigree evidence and publication chronology. This post-analysis review is described separately from the AI-assisted initial ascertainment; final eligibility of flagged cases remains under review.")
    replace(main,
        "Case/date eligibility was AI-assisted, not blinded to accessible modern workspace outputs, and awaits individual human verification; clinical ascertainment error remains possible.",
        "Initial case/date ascertainment was AI-assisted and not blinded to accessible modern workspace outputs. Subsequent human author review covered all 45 cases after the frozen analysis; unresolved target-family evidence and clinical ascertainment error remain possible.")
    replace(main,
        "Additional file 12 contains the temporal protocols, clinical ledger, historical components, full results and source hashes.",
        "Additional file 12 contains the temporal protocols, clinical ledger, historical components, full results, source hashes and a dated summary of subsequent human review. Additional file 13 contains the contemporary GO classification, Figure S1, complete exploratory enrichment tables and verification records.")
    replace(main,
        "No inferential *P* values were used to support causal or clinical claims.",
        "No inferential *P* values were used to support causal or clinical claims. The separate post-hoc GO over-representation analysis used one-sided tests with pooled Benjamini–Hochberg adjustment within each analysis; its methods and complete nonsignificant results are reported in S8.")
    replace(supp,
        "The authors have not yet individually verified the 45 cases against the original reports. The roster is a provisional literature-screened cohort, not an independently human-adjudicated clinical benchmark.",
        "After the frozen analysis, human author review examined primary reports for all 45 cases, including reported families/pedigrees, phenotypes, inheritance, functional mechanisms and publication chronology. S6.6 records representative findings and unresolved family-evidence concerns. The original AI-assisted ascertainment and outcomes are retained; this later review is not blinded pre-outcome adjudication.")
    replace(supp,
        "## S7. Numerical replay, provenance and submission-file checksums",
        """### S6.6 Subsequent human author review

A human author examined primary reports for all 45 cases after the frozen temporal analysis, including reported family/pedigree information, phenotype, inheritance, functional mechanisms and publication dates. The review distinguished the number of individuals from unrelated families and separated the target phenotype from earlier disorders associated with the same gene. It was a source and interpretation check, not a new blinded prospective benchmark.

Three reports prompted particular family-evidence concerns. The initial *PDIA6* paper described one affected individual from one family (PMID 33495992). The earlier *VWA8* developmental-disorder paper described nine individuals from one family (PMID 34660594), whereas the temporal target was a later retinal association. For *PLCG1*, a single-family immune-disorder report (PMID 37422272) was distinguished from a later multisystem report with auditory/ocular involvement and four families (PMID 40862571). The frozen criterion requires at least two unrelated target-phenotype families cumulatively across eligible reports, not necessarily within each paper or displayed pedigree. These observations therefore require gene–target-specific interpretation; they do not by themselves constitute three exclusions. Eligibility of the flagged cases remains under review. No new human-approved cohort, revised denominator or recovery estimate is asserted.

The review also distinguished *CRLS1* mitochondrial cardiolipin deficiency with sensory manifestations (PMID 35147173), *CTNND1* retinal vascular disease (PMID 35700046), *DHRSX* dolichol-biosynthesis/glycosylation disease (PMID 38821050), and spliceosomal RNA-associated retinal disease involving *RNU4-2* and RNU6 genes (PMID 41513982). Sensory manifestations alone do not establish a ciliary mechanism. The temporal scope intentionally includes inherited retinal/optic disease, hearing impairment and explicitly supported ciliopathies, rather than only mechanistically established ciliopathies.

Publication chronology was checked against the supplied reports and bibliographic records, distinguishing first public target evidence, preprints/early-online versions, acceptance and issue dates. Eligibility uses a supported first-publicity interval wholly after 31 December 2020; an exact day is unnecessary when the interval does not cross the cutoff. Most discrepancies concerned publication stages. For example, TMEM72 conference/abstract evidence in 2021–2022 predates the full paper's 2025 online/2026 issue dates. Exact earliest-day uncertainty remains documented for ATP11A, CREB3, MRPL49 and TMEM72. No newly confirmed pre-cutoff target association was found in this bounded audit. The original dated roster and numerical results remain preserved. Additional file 12 includes this review summary alongside the frozen analysis records; the complete working author-review form is not an additional submission attachment.

## S7. Numerical replay, provenance and submission-file checksums""")
    replace(supp, "submission/bmc_bioinformatics_major_revision_20261007/", "submission/bmc_bioinformatics_major_revision_20261019/")
    replace(supp, "additional files 1-9 and 11-12", "additional files 1-9 and 11-13")
    replace(response, "# Point-by-point response to major revision — working draft, 19 October 2026", "# Response to the editor and reviewers")
    replace(response,
        "Existing manuscript page references refer to the 7 October author-review PDFs. The new author-review account below requires alignment with the final manuscript and regenerated submission files before upload.",
        "Page references identify the revised PDFs supplied with this response. The revision incorporates subsequent human author review and a separate descriptive GO analysis, with their timing and scope stated explicitly.")
    replace(response,
        "These examples clarify the breadth of the prespecified sensory-disease cohort.",
        "A post-hoc contemporary GO classification further describes the same 45 cases (S8; Additional file 13, Figure S1). BP/MF/CC coverage was 41/42/44 cases; overlapping categories included cilium and mitochondrion (eight each), cilium organization (four) and mRNA metabolic process (five). None of the 11,388 primary or 10,459/2,750 sensitivity GO tests passed pooled BH FDR < 0.05. This functional description does not alter the historical scores or supply independent predictive validation.\n\nThese examples clarify the breadth of the prespecified sensory-disease cohort.")
    replace(response,
        "The mitochondrial, retinal vascular, glycosylation and RNA-splicing examples provide concrete reasons to distinguish broader sensory-disease prioritization from ciliopathy-specific performance (R1-major-8).",
        "The mitochondrial, retinal vascular, glycosylation and RNA-splicing examples provide concrete reasons to distinguish broader sensory-disease prioritization from ciliopathy-specific performance (R1-major-8). The added contemporary GO classification is consistent with functional heterogeneity, but no enrichment passed FDR < 0.05; we do not treat it as evidence of cilia specificity (S8; Additional file 13).")
    replace(cover, "7 October 2026", "19 October 2026")
    replace(cover, "Editor-in-Chief  \nBMC Bioinformatics", "Ritesh Shelke  \nEditor, BMC Bioinformatics")
    replace(cover,
        "We have addressed both reports in the accompanying point-by-point response",
        "For submission 97b94353-679a-4ef3-a386-69332e413872, we have addressed the editor and all three reviewers in the accompanying point-by-point response")
    replace(cover,
        "The AI-assisted literature-screened cohort is provisional pending individual human clinical/date verification.",
        "Subsequent human author review examined the primary reports and family/pedigree evidence for all 45 AI-screened cases, clarified publication versions and disease mechanisms, and identified target-family evidence concerns that are explicitly retained in the revised text.")
    replace(cover,
        "The revised submission includes editable documents, figures, additional files, derived replay inputs and temporal protocols/results.",
        "The revision also includes a contemporary GO functional description of the temporal cases; no enrichment passed the specified FDR threshold. This descriptive addition does not alter historical scores. The revised submission includes editable documents with embedded figures and legends, separate figure files, additional files, derived replay inputs and temporal protocols/results. We will check figure visibility in the journal-generated review PDF before completing resubmission.")
    replace(cover,
        "Code and analysis records are available at https://github.com/gbanyan/usher-exploring/tree/major-revision-author-review-20261007; the completed numerical-analysis checkpoint is 736e16f, and the package manifest records the revised source and artifact hashes.",
        "Code and analysis records are available at https://github.com/gbanyan/usher-exploring/tree/revision/major-revision; the preserved 7 October author-review release remains separately identified, and the package manifest records the exact revised source and artifact hashes. The completed temporal numerical-analysis checkpoint is 736e16f.")
    replace(cover,
        "The exact author-review release is identified by the fixed Git tag `major-revision-author-review-20261007` and the delivered-file SHA-256 manifest.",
        "The delivered-file SHA-256 manifest identifies this revision; the earlier fixed tag `major-revision-author-review-20261007` is preserved unchanged.")
    print("Aligned manuscript, Supplement, response and cover letter; frozen analysis files untouched.")


if __name__ == "__main__":
    main()

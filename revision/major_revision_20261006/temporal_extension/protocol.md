# Archival temporal extension: frozen before inspecting historical rankings

Cutoff: **2020-12-31**. This extends, and supersedes the scope of, the Phase 3 local-cache feasibility audit. External archives must be investigated before concluding that a temporal analysis is infeasible.

## Question and limits

Can a restricted, archive-only version assign priority to illustrative genes whose human retinal/ciliopathy association was reported after the cutoff? This is a retrospective case series, not prospective validation of the submitted six-layer pipeline, not discovery of previously unknown ciliary function, and not an estimate of sensitivity or specificity. Case ascertainment is manual and non-exhaustive; the algorithm and its weights were developed after 2020.

The submitted database, scores, HIGH gate, source caches, and manuscript must remain unchanged. Do not assign HIGH/MEDIUM/LOW to the archival reconstruction. Do not tune weights, choose cases, or change availability decisions after seeing their rankings.

## Frozen cases and date exclusions

Include CEP162 (human retinal association reported in 2023; PMID 36862503), CFAP20 (initial human retinal candidate report 2022-03-04; PMID 35246562, followed by the independent 2022 Nature Communications report), and LRRC45 (putative human ciliopathy report in 2021; PMID 34716235, with subsequent stronger evidence). Treat initial candidate reports separately from established causal associations. The date boundary is first *human association*, not first ciliary-function paper; pre-cutoff ciliary biology is explicitly permitted and must be acknowledged. Dates here identify earliest reports located in this audit, not proof that no earlier report exists. Audit earlier papers/preprints before stronger temporal claims.

Exclude TMEM218: the primary full-text XML for PMC8009330 gives publication 2020-11-21, despite 2021 PubMed/issue indexing. Exclude ARSG (2018), CEP78 (2016), TOGARAM1 (2020), and IFT74 (human Bardet–Biedl association predating 2020); later confirmations/new syndrome associations do not reset the novelty date. SLC30A7 is not added to the cases because its 2022 report is a proposed candidate association and this limited series already has a separately labelled putative ciliopathy case. These decisions precede any historical rank inspection.

## Reconstruction

Population: all Approved HGNC protein-coding genes in the official 2020-10-01 archived complete set with unique nonempty Ensembl identifiers; do not select the genome-wide population using present-day candidate ranks. Map GO UniProt identifiers through that archived HGNC set; use unique archived approved symbols only as a recorded fallback. No current aliases, HCOP confidence, annotation values, or publication counts may be borrowed from the production database.

Primary archive-only score has four available layers, using unchanged production transforms where their inputs are available:

* gnomAD 2.1.1 gene-level LOEUF (`oe_lof_upper`), min/max inversion over the frozen historical population with nonmissing estimates. No modern transcript selection, v4 values, or inferred coverage flags. Reject unexpected duplicate gene identifiers.
* HPA v20 normal-tissue ordinal protein levels: retain Approved/Enhanced/Supported reliability, maximum category across cell types, the same retina/cerebellum/testis/fallopian-tube panel. Quantitative RNA, GTEx, and CELLxGENE are unavailable in this restricted reconstruction and remain NULL. Tau remains NULL rather than applying a quantitative Tau to ordinal codes. Reuse production expression scoring; document historical HPA tissue availability.
* GO release 2020-12-08: unique positive (non-NOT) GO IDs per gene across aspects. The GO portion of the production annotation score retains its original 0.5 component weight. UniProt annotation score and pathway membership remain NULL, with the production function's existing missing-subcomponent behavior. GAF counts are a documented source substitution for MyGene API counts; this layer is partial and not equivalent to the submitted annotation layer.
* HPA v20 subcellular localization: reuse the production reliability and compartment rules. Embedded undated cilia/centrosome compendia are unavailable; do not import present-day membership. Absence of these source channels is a reconstruction limitation, not evidence against membership.

Animal-model and literature layers remain NULL in this bounded reconstruction. Historical MGI, ZFIN, IMPC and gene2pubmed files establish partial archival feasibility, but production animal scoring additionally requires historical HCOP confidence; publication-context/MeSH classifications and UniProt API annotation scores require further historical reconstruction. Downloading a historical file does not establish equivalence of the complete layer. This restriction is selected from source availability before outcomes, not candidate performance.

Use original inter-layer weights (constraint 0.20, expression 0.20, annotation 0.15, localization 0.15; absent layers excluded by the unchanged observed-weight denominator). Also report equal available-layer weights and each single-layer baseline as prespecified descriptive comparisons. Percentiles use minimum tie rank; integer position uses descending score then Ensembl ID. Report denominator, ties, evidence count, all component values and top-25/50/100 membership. Do not regard a high percentile with only one measured layer as robust evidence.

The nine established Usher genes are descriptive reference cases only. They do not calibrate normalization, weights, thresholds or the gene population. There is no external negative cohort or aggregate validation statistic for this manually selected three-case series.

## Outputs and verification

Archive URL, retrieval time, complete-file SHA256, file size, format checks and internal/release dates; source coverage; all-gene historical components/ranks; prespecified case and known-Usher diagnostics; report of successes and failures including inaccessible archives. Hash the protocol before rank computation and verify it in the analysis. Record parser/mapping exclusions and unchanged production artifacts. Verify positive versus NOT GAF annotations, ambiguity handling, historic schema parsing, missing/observed-zero semantics and weighted ranking. Preserve the failed probes as evidence rather than silently replacing them.

The report must explicitly state whether this extension supports a full temporal validation. A restricted reconstruction cannot answer that question affirmatively, even if individual cases rank well.

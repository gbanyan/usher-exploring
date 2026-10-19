# Original journal comments

Journal numbering confirmed by the corresponding author: source A is Reviewer 1; source B is Reviewer 3.

## Editor

Please ensure the results are accurately reported, any overstated conclusions are rewritten and the limitations of the work fully explained.

## Reviewer 2

The figures were not in an accessible form. So I could not review this.

## Reviewer 1 major 1

The intended prediction task is not entirely clear
This paper describes UsherPipe as a gene prioritization tool related to Usher syndrome in several parts, but in others, it extends its scope to Usher syndrome and related ciliopathy. These are related, but they are not the same prediction problem.
This distinction matters because the evaluation set includes nine established Usher genes together with 28 selected SYSCILIA genes. Good recovery of general ciliary genes does not necessarily demonstrate good performance for Usher-specific gene discovery.
I would like the authors to define the main objective more clearly. Does this pipeline aim to identify new genes associated with Usher syndrome, genes associated with sensory ciliary disease, or a broader range of cilia-related genes that could be studied further in relation to Usher syndrome?
The results for the nine Usher genes and the 28 SYSCILIA genes should also be reported separately throughout the manuscript rather than relying mainly on the combined set of 37 controls.

## Reviewer 1 major 2

The calibration and evaluation of the HIGH tier are not independent
A central concern is that the cilia-signal gate was chosen after examining the behavior of both positive and negative controls.
The authors are commendably transparent about this, but it creates an important circularity. Once the controls have been used to inform the definition of the gate, those same controls cannot provide an independent assessment of how well the final HIGH tier performs.
This is particularly relevant because the HIGH tier is one of the main outputs of the pipeline.
Ideally, the authors should separate calibration and evaluation using an independent set of genes. This could be done using a held-out control set, a temporal split, or another pre-specified development/test design.
If such an analysis is not feasible, I would recommend describing the HIGH tier consistently as a heuristically calibrated prioritization tier, rather than implying that its specificity has been validated.
The distinction between the raw six-layer score and the post-hoc gated HIGH tier should also be made more prominent in the Abstract and Results.

## Reviewer 1 major 3

Recovery of known genes in the final HIGH tier needs to be shown directly
The manuscript emphasizes that 35 of 37 controls fall within the top quartile of the genome-wide ranking. This sounds encouraging, but it does not tell the reader how the known genes behave after the complete prioritization procedure is applied.
According to the supplementary analyses, only two established Usher genes are present among the 62 HIGH-tier genes, and only three controls in total are retained when the selected SYSCILIA genes are also considered.
For a pipeline whose practical output is a relatively small HIGH-priority shortlist, this is an important result and should be presented clearly in the main manuscript.
I suggest reporting:
how many of the nine known Usher genes fall into HIGH, MEDIUM, LOW, or the excluded group;
the same information for the SYSCILIA controls;
why each established Usher gene that fails to reach HIGH is lost—i.e., score threshold, evidence count, or cilia-signal gate;
how the sensitivity of the HIGH tier changes if alternative thresholds are used.
A simple table tracing the known Usher genes through the different filtering steps would be very helpful.

## Reviewer 1 major 4

The housekeeping-gene result raises a substantial specificity concern
One of the most notable results is that housekeeping genes rank very high in the base score. The median percentile was reported at 94.8%, and 11 of the 13 housekeeping genes fall within the top 25%.
The authors correctly describe this as a specificity failure. I agree with that interpretation.
However, the subsequent removal of these genes from the HIGH tier is less convincing as evidence of improved specificity because the gate was designed after examining these same negative controls.
I also wonder whether housekeeping genes are the most informative negative set for this task. Many of these genes are highly constrained, extensively annotated, and well studied—features that naturally produce high scores in several of the six layers.
A larger and better-matched negative-control set would strengthen the analysis considerably. For example, the authors could consider well-characterized genes associated with diseases unrelated to auditory, retinal, or ciliary biology, with matching for publication burden or annotation density where possible.
Without such an analysis, I would avoid interpreting the current results as an estimate of biological specificity.

## Reviewer 1 major 5

The choice of weights remains somewhat arbitrary
The six evidence-layer weights are biologically motivated, but the exact values appear heuristic.
This is not necessarily a problem for a transparent prioritization framework, but the sensitivity analysis shows that the resulting ranking is not uniformly stable. Only 16 of 24 perturbations meet the predefined stability threshold, and some correlations fall to approximately 0.61. The animal-model layer appears to have particularly strong influence.
The post-hoc logistic-regression experiment is also informative in this regard. It places most of the fitted weight on the animal-model layer and produces a substantially different genome-wide ranking.
I agree with the authors that such fitted weights should not replace the default model because the same controls are involved in model fitting. Nevertheless, these findings suggest that the default weights should be presented as one reasonable biological configuration rather than as a particularly robust or optimal solution.
It would strengthen the manuscript to include several simple comparisons, such as:
equal weights;
animal-model evidence alone;
expression alone;
localization/cilia evidence alone;
leave-one-layer-out rankings.
It would also be useful to report how frequently genes remain in the top 25, 50, or 100 across plausible alternative weighting schemes.

## Reviewer 1 major 6

NULL-aware scoring has advantages, but it may also favor genes with sparse evidence
I find the explicit treatment of missing values to be one of the more interesting aspects of the pipeline. Treating missing evidence as zero can clearly be problematic.
At the same time, the current available-layer weighted mean introduces another issue. A gene with only a few observed layers can receive a high composite score if those observed values happen to be high.
The evidence-count requirement partially addresses this, but a HIGH-tier gene may still be supported by only three of the six evidence layers.
The manuscript would benefit from a more direct analysis of this issue. For example:
How many HIGH-tier genes have evidence from 3, 4, 5, or 6 layers?
Does the HIGH list change substantially if at least four or five observed layers are required?
Is composite score associated with evidence completeness?
In addition, authors are encouraged to provide clear measures of evidence completeness along with the scores. A composite score of 0.75 based on three factors does not necessarily have the same evidential weight as a score of 0.75 supported by all six factors.

## Reviewer 1 major 7

The six evidence layers may not be as independent as the framework implies
Some of the evidence layers likely capture overlapping properties.
For example, annotation completeness and literature evidence may both strongly favor well-studied genes. Localization evidence may also partly reflect the same published experiments used in ciliary databases or literature mining.
This could help explain why highly characterized housekeeping genes receive unexpectedly high scores.
I therefore think an inter-layer correlation analysis would be useful. A leave-one-layer-out analysis would also help establish whether the integrated model provides information beyond the strongest individual components.
In addition, the Methods could provide a little more detail about how multiple sources are combined within each layer, particularly for expression, localization, annotation, and literature evidence.

## Reviewer 1 major 8

The mantis-ml comparison is informative but does not provide a strong external benchmark
The manuscript appropriately acknowledges that the mantis-ml comparison is difficult to interpret because 33 of the 35 shared positive controls were used as mantis-ml training seeds.
For that reason, the higher control recovery of mantis-ml cannot really be interpreted as a conventional head-to-head benchmark. Conversely, the comparison also does not establish how well UsherPipe performs on genuinely novel genes.
If possible, a temporal validation would be particularly interesting—for example, testing whether the pipeline can prioritize genes that were associated with the relevant biology only after a defined historical cutoff.
If this is not practical, simpler baselines would still be valuable. The authors could compare the full six-layer score against each major layer alone and against an equal-weight model. This would help demonstrate whether the integrated framework provides a meaningful benefit over simpler scoring strategies.

## Reviewer 1 major 9

Reproducibility should be strengthened
The authors have made a serious effort to document reproducibility, which is appropriate for a BMC Bioinformatics manuscript. However, the current provenance information is still incomplete.
The reproducibility manifest records only a subset of source URLs and versions and does not include retrieval timestamps for the recorded inputs.
For a computational pipeline paper, I would strongly encourage the authors to provide, where possible:
exact database versions or snapshot identifiers;
source URLs or accession numbers;
retrieval dates;
checksums for local input files;
a locked software environment or dependency file;
the commands needed to reproduce the figures and tables;
ideally, a containerized environment or an equivalent reproducible setup.
I also recommend checking the consistency of the submitted supplementary files against the checksum manifest. In the material provided for review, the checksum associated with the expression-shortlist report does not appear to match the submitted Additional file 6. This may simply reflect a conversion from a repository Markdown file to the journal TXT file, but if so, that distinction should be documented.

## Reviewer 1 major 10

The production expression layer seems more retina-oriented than fully Usher-specific
The manuscript appropriately emphasizes that Usher syndrome involves both retinal and auditory biology. However, the production expression layer does not appear to include cochlear hair-cell data. The GSE135913 cochlear analysis is instead treated as a post-hoc exploratory analysis based on two accepted fetal samples.
At the same time, cerebellum is retained as a proxy tissue in the production score.
I think the authors should explain this choice more clearly, because tissue specificity is presented as an important feature distinguishing UsherPipe from more general gene-prioritization tools.
It would be useful to show how much the expression layer contributes to the ranking of established Usher genes, and whether removing the proxy tissue materially changes the results.
Until direct auditory-cell data are incorporated into the production score, the term “Usher-specific tissue weighting” may be somewhat stronger than the available data support.

## Reviewer 1 minor 1

The term “seed-free” should be defined clearly when it is first introduced. Known genes are not used in the raw composite score, but control behavior did influence the downstream cilia-signal gate.

## Reviewer 1 minor 2

I would consider replacing “confidence tier” with “priority tier.” HIGH, MEDIUM, and LOW are rule-based prioritization categories rather than calibrated statistical confidence levels.

## Reviewer 1 minor 3

Gene-identifier terminology should be checked carefully. The manuscript acknowledges that many displayed gene names are not formally validated current HGNC symbols, so wording such as “canonical identifier” should only be used where it is strictly accurate.

## Reviewer 1 minor 4

The distribution of established Usher and SYSCILIA controls across the final tiers should be included in the main Results section.

## Reviewer 1 minor 5

Please state how the random background genes shown in the control-recovery analysis were sampled and provide the random seed.

## Reviewer 1 minor 6

In addition to the GitHub commit, I would encourage archiving the exact software version used for the manuscript in a permanent repository with a DOI if possible.

## Reviewer 1 minor 7

The biological background is thorough, but somewhat long for a BMC Bioinformatics paper. Some of the detailed discussion of Usher molecular biology could be shortened so that more emphasis can be placed on the computational design, validation strategy, benchmarking, and scoring assumptions.

## Reviewer 3 point 1

In Background, in the sentence beginning “Because the known Usher genes encode ciliary and periciliary proteins acting at hair-cell stereocilia, the photoreceptor connecting cilium, and the periciliary membrane complex, Usher syndrome may…”, a supporting reference should be added.

## Reviewer 3 point 2

The manuscript describes UsherPipe as a seed-free approach, but the cilia-signal gate was defined after examining control and negative-control behavior. The authors note that this is a post-hoc calibration. It would be helpful to clarify how this affects the interpretation of control-recovery performance and the definition of the HIGH tier.

## Reviewer 3 point 3

The manuscript reports that alternative weighting strategies, including logistic-regression-based weighting, substantially changed the genome-wide ranking (default vs. logistic regression rank ρ = 0.646). These alternatives were not adopted due to concerns about control reuse and over-specialization. Additional justification for the final predefined weights would be useful, along with a discussion of how this degree of ranking sensitivity affects the robustness of candidate prioritization.

## Reviewer 3 point 4

The recovery of known Usher and ciliary genes shows that the pipeline captures relevant disease biology. However, because the cilia-signal gate was calibrated using these same controls, it would be helpful to clarify what independent evidence supports UsherPipe’s ability to prioritize genuinely novel disease genes rather than mainly rediscovering genes with established Usher/ciliary characteristics.

## Reviewer 3 point 5

Because Usher syndrome affects cochlear hair cells, the authors could more directly discuss the impact of excluding hair-cell expression data from the production score. The exploratory fetal cochlear analyses are useful, but they do not contribute to the final composite score. It would be helpful to comment on whether the absence of suitable hair-cell data may disadvantage genes with more limited or developmentally restricted evidence.

## Reviewer 3 point 6

A broader conceptual issue concerns the biological specificity of the composite score. Several evidence layers, such as gnomAD constraint, functional annotation completeness, and publication-based evidence, may reflect general gene importance or research intensity rather than disease-specific involvement in Usher syndrome. This is particularly relevant because housekeeping genes ranked very highly in the raw multi-evidence score (median at the 94.8th percentile). Clarifying how the composite score distinguishes general biological importance from evidence specifically supporting a role in Usher syndrome or related ciliopathies would strengthen the interpretation. The authors might also consider discussing whether additional disease-specific negative controls or specificity analyses could help quantify this distinction.

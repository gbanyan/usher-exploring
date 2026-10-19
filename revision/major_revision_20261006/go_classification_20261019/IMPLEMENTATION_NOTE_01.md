# Within-aspect ontology closure — first execution guard

The first execution at frozen implementation commit `bb817f5` stopped at the ontology namespace guard, before saving any case summary, functional-category result or enrichment test. The failed assertion expected all `is_a,part_of` ancestors returned by QuickGO to have the original GAF annotation's aspect.

Source inspection shows that the GO-plus service also returns cross-aspect `part_of` ancestors: for example, a transporter molecular function can have a biological-process transport ancestor. There are 1,224 such term objects across the complete downloaded ontology query; this is a source-graph observation, not a selected-cohort result.

To implement the protocol's independent BP/MF/CC analysis consistently, retain authoritative ancestors **only within the original direct GAF term's aspect**, excluding roots. Apply this uniformly to all cases, both backgrounds, all evidence policies and supporting-term displays. Preserve the complete raw QuickGO ancestor response, including the excluded cross-aspect links. No names, gene overlaps, ranks or P values determine this rule. A focused test covers cross-aspect exclusion.

The original protocol and freeze remain unchanged. `run_amendment_01.json` pins the corrected helper/analysis/test hashes and records the aborted first execution. The change resolves an implementation assumption before any case-level GO summary or enrichment outcome was inspected; it does not change the case list, clinical eligibility, statistical method, FDR policy, background selection or figure category-selection rule.

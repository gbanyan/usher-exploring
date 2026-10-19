# Final author-review completion audit

Objective: prepare the complete pre-upload version for the user's final review, without journal submission. Assembly date is 19 October; final checks are on 20 October 2026. Author approval and portal rendering are subsequent actions, not claims made by this package.

| Requirement | Authoritative evidence | State |
|---|---|---|
| Main, Supplement, point-by-point response and cover letter agree | Current four sources, generated DOCX/PDFs, exact source hashes and PDF texts in verification.json | Verified |
| Every reviewer/editor subject addressed | All 23 original R1/R3 quotations match d3d309a; editor and exact R2 figure-access comment present; 25 crosswalk subjects | Verified |
| Updated human-review scope and representative findings | S6.6, R1-major-8 and HUMAN_REVIEW_SUMMARY.md; all45 primary/family reports reviewed after computation, three concerns explicitly retained | Verified; no blanket eligibility approval asserted |
| Cumulative family context accurate | Frozen clinical_roster.json matches PDIA6 three overall/lower-bound two target, VWA8 two target, PLCG1 three target; later report identifiers supplied | Verified; no exclusions or outcomes changed |
| GO supplement complete and truthfully interpreted | Protocol/source manifests, 24,597 Fisher/BH recalculations, zero FDR-significant terms, XLSX/TSVs/FigureS1 in Additional13 | Verified |
| GO replay and verification scope explicit | Eight TSVs plus summary byte-identical; derived-association cache hashed; separate arithmetic vs same-code source replay distinguished | Verified |
| Source, clinical and production invariants preserved | 21 baseline hashes, 45 old artifacts against tagged manifest, temporal tree against95662c7, original45/41 case metrics | Verified |
| Numerical implementation checks | 362 tests/17 existing warnings; GO8 tests; 38,334 derived temporal rows exact | Verified |
| All rendered pages readable | visual_review_progress.json and post_opus_render_comparison.json: all80 final pages checked, changed pages inspected, unchanged page pixels identical | Verified |
| Figure accessibility prepared locally | Nine embedded main figures, one supplement figure, nine separate PDF/PNG main assets, correct captions/alternative descriptions | Verified locally; portal access is an author check |
| Page references and citation order current | 89 actual-PDF page-index rows; all66 references first cited in main text, Supplement/summary synchronized | Verified |
| Attachments complete and within publisher limits | 12 additional payload files plus checksum file; three ZIPs below20,000,000bytes, figures below10,000,000bytes; actual entries/CRC/hash checks | Verified |
| Full working clinical-review form omitted | ZIP contents check; only concise human-review summary distributed | Verified |
| Independent requested model review | Actual first-party claude-opus-5-5/high,53+46read-only turns, no remaining material issue after three fixes | Verified; internal AI audit only |
| Routine Git/LFS checkpoint and new fixed version published | Local pointer/object checks and both remote branch/tag refs in publication_verification.json; oldtag unchanged | Verified on Gitea/GitHub; three LFS objects each; old tag unchanged; public GitHub API HTTP200 |

DOI deposition and a harmonized mantis-ml rerun were not performed; conditional reviewer suggestions and corresponding limits are disclosed. The package does not claim prospective clinical validation, calibrated HIGH disease probability, Usher specificity, significant GO enrichment or improved temporal recovery from human review. Ignored raw caches/databases are preserved locally and are not backed up by Git.

The fixed release commit is eaeb10a4031457af13485cb19744b4bf47aace58. All47 packaged artifacts match their committed tag blobs (ZIPs match LFS OIDs), and both remotes resolve the new annotated tag to that commit. Publication evidence is necessarily recorded after the release commit; later audit-only commits do not move the tag. The initial Gitea LFS failure came from a dead per-URL proxy; a task-owned loopback SSH SOCKS route through gbminipc completed the upload without global proxy changes.

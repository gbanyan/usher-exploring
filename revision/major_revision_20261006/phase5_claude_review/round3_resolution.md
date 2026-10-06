# Round 3 resolution — 7 October 2026

Actual first-party Claude Opus 5.5 high-effort review completed successfully in 35 turns. All MA-1 through MA-5 and round-2 minor findings were confirmed resolved. The final audit required a public version check and offered additional editorial improvements.

## Original public commit: correction to our local-only inference

The original cited commit **4cf8c5b exists publicly**. It was absent from this local object history, but the direct GitHub page and unauthenticated GitHub commit API both resolve it to `4cf8c5b7aa4aea4a444c3447a9e7c16dcd04641f`, a merge publishing reproducible results/manuscript materials. The exact response is recorded in `original_public_commit_verification.json`.

Thus the original citation was not shown to be wrong. The proposed retraction based on local absence was rejected after the requested external check. The active manuscript restores the original public code/data reference and separately retains the real `ed2d00d` checkpoint for preserved original submitted files. R1-minor-6 now explicitly distinguishes original public code/data from prepared (`f889ec3`) and technically amended submission files (`ed2d00d`). Earlier audit snapshots/findings remain unchanged as historical records. The fixed author-review release will identify the final revised package after commit/tag/push.

## Final editorial improvements

- E1: Figure 9 panel A uses the shorter label “Known-gene percentile”, preventing truncation/collision. The caption describes individual points, box/whisker/mean/outlier conventions and the dashed percentile reference. The cached plotting command was exercised; no training or scores changed.
- E2: Page locations also include the additional sections already named by R1-major-1/2/4/8; the final index has 83 rows for the same 23 substantive comments.
- E3: Main prose uses ≥ and a nonbreaking positive-weight expression. Semantics and numerical outcomes unchanged.
- E4: Small extraction/kerning gaps in inline-code text are a renderer/text-extraction limitation, not extra characters in the source or an altered identifier. Editable DOCX and named source files accompany the PDFs.
- E5: Fixed-tag publication remains an explicit final operational step. Its target and both remote refs/LFS uploads are checked after commitment, without putting an impossible self-referential commit hash inside its own files.

All 45 temporal cases remain pending human eligibility/date/inheritance verification. No clinical decisions or frozen numerical outputs were amended to resolve these editorial findings. All-author approval, final cover-letter declarations/manuscript ID and journal submission remain outstanding.

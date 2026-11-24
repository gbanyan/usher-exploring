# BMC Bioinformatics second revision — public submission files

Submission ID: 97b94353-679a-4ef3-a386-69332e413872. Assembled 24 November 2026 for the second revision. Release tag: `second-revision-20261124`.

## Files

- `Manuscript.docx` / `Manuscript.pdf`: revised manuscript with Figures 1–8 embedded with their legends. The DOCX is the editable upload; the PDF is a local LibreOffice rendering.
- `Supplementary_Methods.docx` / `Supplementary_Methods.pdf`: Supplementary Methods, including Figure S1. Additional file 3 is the plain-text form.
- `figures/`: separate PDF/PNG files for Figures 1–8 (upload each numbered figure once) and retained plot-data files. Former Figure 9 is now Figure S2 (Additional file 14).
- `Additional_file_1` … `Additional_file_14`: as listed under "Additional files" in the manuscript.
  - Additional files 1–2, 4–9 and 11–13 are byte-identical to the first-revision package (`submission/bmc_bioinformatics_major_revision_20261020_v2/`). The code snapshots inside the ZIPs of files 11–13 belong to that release.
  - Additional file 3 is regenerated from the revised Supplementary Methods.
  - Additional file 14 is new.
  - Additional file 10 hashes the delivered files 1–9 and 11–14, excluding itself.
- `package_manifest.json`: hashes of every file here and of the source files used to build them. `*.entries.json` list the exact ZIP contents. Neither is a journal supplement.

## Changes to figures in this revision

- **Figure 1:** stage 4 is relabeled "Reporting & internal checks" (`scripts/fig1_architecture.py`).
- **Figure S2 (former Figure 9):** panel titles are reworded ("Control recovery (35 shared controls)"; "Cached-output metrics (exploratory)"). It is regenerated with `scripts/mantisml_benchmark.py`, and the recomputed metrics CSV is byte-identical to `data/report/mantisml_benchmark.csv`.
- **Figure 4:** the image key now reads "+ SYSCILIA ciliary control", matching the legend and the code that assigns the mark (`scripts/paper_figures.py`). Regenerating with the original key text reproduces the previous PNG byte for byte, and the new PNG differs only in the key line.
- **Figures 2, 3 and 5–8:** unchanged.

## Build

```
scripts/build_second_revision_documents.py --output-dir submission/bmc_bioinformatics_second_revision_20261124 --cache-dir <cache> \
  --figures-dir submission/bmc_bioinformatics_second_revision_20261124/figures --manuscript manuscript/draft.md --supplement manuscript/supplementary_methods.md
soffice --headless --convert-to pdf <docx>
pandoc manuscript/supplementary_methods.md -t plain --wrap=none -o Additional_file_3_Supplementary_Methods.txt
```

No analysis was rerun and no reported number changed.

# Frozen six-layer scheme key correction

The second execution stopped before saving any case summary or enrichment outcome because the implementation guessed the six-layer row key `archived_six`. The actual frozen co-primary scheme key is **`augmented_six`**, paired with `archived_five`. This was verified directly against the existing `case_rankings.tsv`; no alternative scheme was chosen by its performance.

The read-only join now uses the actual two co-primary names and explicitly asserts the availability of all 45 rows in both schemes. A regression test checks the stable join and 41-in-universe / four-outside split against the frozen files. All source values are copied without rescoring. This is a schema/join repair, not a scientific analysis change. The first two attempts generated no category, rank-summary or enrichment output files.

# HIGH-shortlist old-versus-new comparison

This diagnostic compares the pre-rebuild artifact at `17a34653472792228c6e8740d28383b06731ed0a` with the
current scored state. The old-side IDs are retained here only to make retention
and rank changes auditable; they are not production inputs.

| Metric | Old | New |
|---|---:|---:|
| Scored labels | 19557 | 20081 |
| Candidate rows | 18303 | 18387 |
| HIGH rows | 68 | 62 |

- HIGH overlap: 54
- Old HIGH retained in new HIGH: 54/68 (79.4%)
- Old-only HIGH: 14
- New-only HIGH: 8
- Shared-candidate rank Spearman rho: 0.9881 (17944 shared candidates)
- Retained-HIGH rank delta (new minus old): median absolute 4,
  minimum -19,
  maximum 28

The machine-readable row-level comparison is `high_shortlist_old_vs_new.tsv`.

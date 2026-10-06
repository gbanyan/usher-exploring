# Independent pre-outcome design review

Reviewer: existing user-requested gpt-6-astra, high reasoning. Read-only review
of `PROTOCOL_DRAFT.md` and acquisition records, 6 October 2026. No v2 rankings
were calculated or inspected. The expanded design is executable; historical
HCOP votes need not be recovered before proceeding with native ortholog links.

Required corrections before freezing:

1. Make novelty categories exclusive and use one clinical evidence rubric across
   RetNet and PanelApp. Record first report separately from evidence maturation.
2. Track every catalog gene/domain in a complete screening ledger. Older
   functional citations do not establish an older human association; red status
   or absent post-cutoff references do not establish absence of a new association.
3. Fix a primary endpoint, gene deduplication, NULL/outside-universe denominators,
   percentile formula and boundary-tie policy before results.
4. Specify animal unknown-only/partially unknown NULL semantics, ZFIN fields,
   term deduplication and multi-gene/background handling.
5. Preserve the production HIGH evidence-count threshold of >=3. >=4 is a named
   stricter sensitivity. Fix positive-Q75 population/interpolation and scaling.
6. The strictly archived no-literature version must be primary/co-primary, since
   modern text searches are not historical text snapshots. Explicitly handle
   zero-publication division and the full linked-PMID denominator.

Other improvements: unique-native-link sensitivity for ortholog multiplicity
(global scaling does not test ortholog choice); available-GO rescaling sensitivity;
unified source/date/hash manifest. Do not use local modification times as original
source release dates or invented retrieval timestamps.

Follow-up on practical ascertainment: a two-stage full-catalog ledger is defensible.
Reliable pre-cutoff target human clinical evidence excludes novel-target primary
cases without redoing their complete earliest-paper history. All remaining
records receive standardized screening; uncertain/red/no-reference records cannot
be silently closed. Historical green must describe human target disease, not only
animal/function annotation. Already established genes remain eligible for a
separately defined phenotype-expansion/evidence-maturation event analysis. If only
late references nominate these events, call that secondary ascertainment limited,
not comprehensive. Catalog completeness does not mean all disease genes worldwide.

Implementation response: mandatory rules are being incorporated before protocol
and roster freeze; source acquisition and case adjudication continue. The original
conservative Phase4 and restricted pilot are unchanged.

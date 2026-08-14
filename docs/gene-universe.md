# Frozen gene universe

The production gene universe is loaded from the Ensembl release 113 GRCh38
GTF, not from a current MyGene query. The configured cache is:

```text
data/annotation/Homo_sapiens.GRCh38.113.gtf.gz
```

Source URL:

```text
https://ftp.ensembl.org/pub/release-113/gtf/homo_sapiens/Homo_sapiens.GRCh38.113.gtf.gz
```

The expected SHA-256 is:

```text
62f1709b40e083ce9d4cdc64a86b5ffec2c5d5371434bb7095c74dc89079c466
```

The frozen file is 64,141,785 bytes and matches the release directory's
`CHECKSUMS` entry (`sum 44004 62639`). Its `gene` features contain 20,116
records with `gene_biotype "protein_coding"`.

Setup verifies the digest before parsing. It retains an Ensembl ID only when
every `gene` record for that ID has the exact `gene_biotype=protein_coding`
value; gene symbols are never used as a proxy for biotype. The resulting
DuckDB checkpoint includes the biotype and source digest in its description,
along with the release, source filename/path, URL, and expected digest. The
checkpoint is reused only when all of those identity fields match the current
configuration, the configured cache still exists, and a fresh SHA-256 of the
cache matches the expected digest. A missing or modified cache invalidates the
checkpoint; setup rejects reuse and then fails during source validation until a
valid frozen cache is restored. `setup.provenance.json` records the source
path, URL, digest, size, release, feature type, and retained count.

The default path is relative to `data_dir`. For the frozen source used during
remediation, point `data_dir` at the shared local data directory or copy this
file into the configured `data/annotation/` cache before running
`usher-pipeline setup`. Setup does not download a replacement source or
silently fall back to MyGene when the cache is missing.

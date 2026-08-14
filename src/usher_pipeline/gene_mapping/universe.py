"""Load the human protein-coding gene universe from a frozen Ensembl GTF.

The gene universe is intentionally sourced from a release-pinned local GTF.
MyGene is useful for identifier annotation, but its current API response is
not a reproducible substitute for an Ensembl release snapshot.
"""

import gzip
import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO, TypeAlias
from urllib.parse import urlparse

# Type alias for gene universe lists
GeneUniverse: TypeAlias = list[str]

logger = logging.getLogger(__name__)

# Expected range for human protein-coding genes
MIN_EXPECTED_GENES = 19000
MAX_EXPECTED_GENES = 23000
ENSEMBL_GENE_ID_RE = re.compile(r"^ENSG[0-9]+$")
ENSEMBL_GTF_FILENAME_TEMPLATE = "Homo_sapiens.GRCh38.{release}.gtf.gz"


@dataclass
class EnsemblGeneSource:
    """Parsed, release-pinned Ensembl gene source and its provenance."""

    genes: GeneUniverse
    gene_biotypes: dict[str, frozenset[str]]
    metadata: dict[str, object]
    gene_symbols: dict[str, str | None] = field(default_factory=dict)


def sha256_file(path: Path | str) -> str:
    """Return the SHA-256 digest of a local source file."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_gtf(path: Path) -> TextIO:
    """Open a plain-text or gzip-compressed GTF as UTF-8 text."""

    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def _parse_gtf_attributes(attributes: str) -> dict[str, str]:
    """Parse the key/value attributes used by Ensembl GTF records."""

    parsed: dict[str, str] = {}
    for field in attributes.rstrip(";").split(";"):
        key, separator, value = field.strip().partition(" ")
        if not separator:
            continue
        parsed[key] = value.strip().strip('"')
    return parsed


def _validate_source_identity(
    path: Path,
    ensembl_release: int,
    source_url: str,
) -> None:
    """Ensure the local filename and URL both identify the declared release."""

    expected_filename = ENSEMBL_GTF_FILENAME_TEMPLATE.format(
        release=ensembl_release
    )
    if path.name != expected_filename:
        raise ValueError(
            f"Ensembl release {ensembl_release} requires source filename "
            f"{expected_filename}, got {path.name}"
        )

    parsed_url = urlparse(source_url)
    url_filename = Path(parsed_url.path).name
    release_match = re.search(r"/release-(\d+)/", parsed_url.path)
    if (
        parsed_url.scheme not in {"http", "https"}
        or not parsed_url.netloc
        or url_filename != expected_filename
        or release_match is None
        or int(release_match.group(1)) != ensembl_release
    ):
        raise ValueError(
            "Ensembl source URL must identify the same release and filename "
            f"as the local source ({expected_filename}): {source_url}"
        )


def load_frozen_ensembl_gene_source(
    source_path: Path | str,
    *,
    ensembl_release: int,
    expected_sha256: str,
    source_url: str,
) -> EnsemblGeneSource:
    """Load protein-coding Ensembl gene IDs from a local frozen GTF.

    Only ``gene`` feature rows are considered.  A retained ID must have the
    exact ``gene_biotype`` value ``protein_coding`` in every gene row for that
    ID.  This makes the filter independent of gene symbols and prevents an
    ambiguous or stale cross-mapping from entering the universe.

    Args:
        source_path: Local Ensembl GTF or GTF.GZ path.
        ensembl_release: Release represented by the frozen source.
        expected_sha256: Required digest used to enforce source immutability.
        source_url: Canonical download URL recorded and checked as source identity.

    Raises:
        FileNotFoundError: If the frozen local source is absent.
        ValueError: If the source digest does not match or no valid genes are
            present.
    """

    path = Path(source_path).expanduser()
    if not expected_sha256:
        raise ValueError("expected_sha256 is mandatory for a frozen Ensembl source")
    if not source_url:
        raise ValueError("source_url is mandatory for a frozen Ensembl source")
    _validate_source_identity(path, ensembl_release, source_url)

    if not path.is_file():
        raise FileNotFoundError(
            f"Frozen Ensembl release {ensembl_release} source not found: {path}. "
            "Provide the release-pinned GTF locally; setup does not query MyGene."
        )

    actual_sha256 = sha256_file(path)
    normalized_expected = expected_sha256.lower()
    if actual_sha256 != normalized_expected:
        raise ValueError(
            f"SHA-256 mismatch for frozen Ensembl source {path}: "
            f"expected {normalized_expected}, got {actual_sha256}"
        )

    biotypes_by_id: dict[str, set[str]] = defaultdict(set)
    gene_names_by_id: dict[str, set[str]] = defaultdict(set)
    gene_record_count = 0

    with _open_gtf(path) as source:
        for line_number, line in enumerate(source, start=1):
            if line.startswith("#"):
                continue

            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] != "gene":
                continue

            gene_record_count += 1
            attributes = _parse_gtf_attributes(fields[8])
            gene_id = attributes.get("gene_id", "").split(".", 1)[0]
            if not ENSEMBL_GENE_ID_RE.fullmatch(gene_id):
                logger.debug(
                    "Ignoring non-Ensembl gene ID at %s:%d: %s",
                    path,
                    line_number,
                    gene_id,
                )
                continue

            # Missing biotype is recorded as an invalid value rather than
            # silently treated as protein-coding.
            biotypes_by_id[gene_id].add(attributes.get("gene_biotype", ""))
            gene_name = attributes.get("gene_name", "").strip()
            if gene_name:
                gene_names_by_id[gene_id].add(gene_name)

    retained_biotypes = {
        gene_id: frozenset(biotypes)
        for gene_id, biotypes in biotypes_by_id.items()
        if biotypes == {"protein_coding"}
    }
    genes = sorted(retained_biotypes)
    if not genes:
        raise ValueError(
            f"No protein_coding Ensembl gene IDs were found in frozen source {path}"
        )

    gene_symbols = {
        gene_id: (
            next(iter(gene_names_by_id[gene_id]))
            if len(gene_names_by_id[gene_id]) == 1
            else None
        )
        for gene_id in genes
    }
    metadata: dict[str, object] = {
        "source_path": str(path.resolve()),
        "source_filename": path.name,
        "source_url": source_url,
        "source_sha256": actual_sha256,
        "expected_sha256": normalized_expected,
        "source_size_bytes": path.stat().st_size,
        "ensembl_release": ensembl_release,
        "feature_type": "gene",
        "gene_biotype": "protein_coding",
        "gene_record_count": gene_record_count,
        "protein_coding_gene_count": len(genes),
        "ambiguous_or_non_protein_coding_gene_count": (
            len(biotypes_by_id) - len(retained_biotypes)
        ),
        "gtf_gene_name_count": sum(
            1 for gene_id in genes if len(gene_names_by_id[gene_id]) == 1
        ),
        "missing_or_ambiguous_gene_name_count": sum(
            1 for gene_id in genes if len(gene_names_by_id[gene_id]) != 1
        ),
        "ambiguous_gene_name_count": sum(
            1 for gene_id in genes if len(gene_names_by_id[gene_id]) > 1
        ),
    }
    logger.info(
        "Loaded %d protein-coding genes from Ensembl release %d source %s",
        len(genes),
        ensembl_release,
        path,
    )

    return EnsemblGeneSource(
        genes=genes,
        gene_biotypes=retained_biotypes,
        metadata=metadata,
        gene_symbols=gene_symbols,
    )


def fetch_protein_coding_genes(
    source_path: Path | str | int | None = None,
    *,
    ensembl_release: int = 113,
    expected_sha256: str | None = None,
    source_url: str | None = None,
) -> GeneUniverse:
    """Compatibility shim for loading protein-coding IDs from a frozen GTF.

    The historical ``fetch_protein_coding_genes(ensembl_release=113)`` MyGene
    API behavior is removed.  Callers must provide the cached release-pinned
    GTF, its release-matching URL, and its expected SHA-256.
    """

    if source_path is None or isinstance(source_path, int):
        raise TypeError(
            "fetch_protein_coding_genes(ensembl_release=...) is deprecated; "
            "pass source_path, ensembl_release, expected_sha256, and source_url"
        )
    if not expected_sha256:
        raise ValueError("expected_sha256 is mandatory for a frozen Ensembl source")
    if not source_url:
        raise ValueError("source_url is mandatory for a frozen Ensembl source")

    return load_frozen_ensembl_gene_source(
        source_path,
        ensembl_release=ensembl_release,
        expected_sha256=expected_sha256,
        source_url=source_url,
    ).genes

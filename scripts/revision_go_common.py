"""Small, testable ontology and statistics helpers for the post-hoc GO audit."""
import math
from collections import defaultdict
from pathlib import Path

ROOTS = {"GO:0008150", "GO:0003674", "GO:0005575"}
ASPECTS = {"biological_process": "BP", "molecular_function": "MF", "cellular_component": "CC"}
EXPERIMENTAL = {"EXP", "IDA", "IPI", "IMP", "IGI", "IEP", "HTP", "HDA", "HMP", "HGI", "HEP"}


def read_editor(path):
    terms, item = {}, None
    for line in Path(path).open():
        line = line.rstrip("\n")
        if line.startswith("["):
            if item and item.get("id", "").startswith("GO:"):
                terms[item["id"]] = item
            item = {"alts": [], "replacements": [], "subsets": [], "parents": []} if line == "[Term]" else None
        elif item is not None and ": " in line:
            key, value = line.split(": ", 1)
            if key in ("id", "name", "namespace"):
                item[key] = value
            elif key == "alt_id":
                item["alts"].append(value)
            elif key == "is_obsolete":
                item["obsolete"] = value == "true"
            elif key == "replaced_by":
                item["replacements"].append(value.split()[0])
            elif key == "subset":
                item["subsets"].append(value)
            elif key == "is_a" and value.startswith("GO:"):
                item["parents"].append(value.split()[0])
            elif key == "relationship" and value.split()[0] in ("part_of", "BFO:0000050"):
                item["parents"].append(value.split()[1])
    if item and item.get("id", "").startswith("GO:"):
        terms[item["id"]] = item
    return terms


def term_resolver(terms):
    aliases = {alt: key for key, row in terms.items() for alt in row["alts"]}
    def resolve(key, seen=None):
        seen = set() if seen is None else seen
        key = aliases.get(key, key)
        if key in seen or key not in terms:
            return None
        seen.add(key)
        row = terms[key]
        if row.get("obsolete"):
            replacements = row["replacements"]
            return resolve(replacements[0], seen) if len(replacements) == 1 else None
        return key
    return resolve


def bh_fdr(pvalues):
    """Benjamini--Hochberg on the full supplied hypothesis family."""
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in pvalues):
        raise ValueError("Invalid P value")
    n = len(pvalues)
    order = sorted(range(n), key=lambda i: (pvalues[i], i))
    out, running = [1.0] * n, 1.0
    for rank in range(n, 0, -1):
        i = order[rank - 1]
        running = min(running, pvalues[i] * n / rank)
        out[i] = running
    return out


def annotation_index(rows):
    """Index all approved HGNC records, preserving explicit shared RNA products."""
    proteins, rnas, approved, aliases = (defaultdict(set) for _ in range(4))
    records = {}
    for r in rows:
        if r.get("status") != "Approved":
            continue
        key = r["hgnc_id"]
        records[key] = r
        approved[r["symbol"]].add(key)
        for a in r.get("uniprot_ids", "").split("|"):
            if a:
                proteins[a].add(key)
        for a in r.get("rna_central_id", "").split("|"):
            if a:
                rnas[a].add(key)
        for a in (r.get("prev_symbol", "") + "|" + r.get("alias_symbol", "")).split("|"):
            if a:
                aliases[a].add(key)
    return {"proteins": proteins, "rnas": rnas, "approved": approved, "aliases": aliases, "records": records}


def map_product(fields, index):
    database, accession, symbol = fields[:3]
    if database == "RNAcentral":
        keys = index["rnas"].get(accession.removesuffix("_9606"), set())
        if keys:
            return keys, "HGNC RNAcentral xref (shared sequence)" if len(keys) > 1 else "HGNC RNAcentral xref"
    if database == "UniProtKB":
        keys = index["proteins"].get(accession, set())
        route = "HGNC UniProt accession"
        if not keys and "-" in accession:
            keys = index["proteins"].get(accession.split("-")[0], set())
            route = "HGNC UniProt accession (isoform collapsed)"
        if keys:
            return (keys, route) if len(keys) == 1 else (set(), "ambiguous protein accession")
    keys = index["approved"].get(symbol, set())
    if len(keys) == 1:
        return keys, "exact approved symbol"
    keys = index["aliases"].get(symbol, set())
    if len(keys) == 1:
        return keys, "unambiguous HGNC alias"
    return set(), "ambiguous or unmapped symbol"

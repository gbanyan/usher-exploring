"""Reconstruct historical evidence after the v2 source/cohort freeze.

No production database scores or present-day gene annotations are read.
"""
from collections import Counter, defaultdict
import csv
import gzip
import json
import math
from pathlib import Path
import re
import sys

import numpy as np
import polars as pl
from scipy.io import mmread
from scipy.stats import rankdata
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from revision_temporal_analysis import historical_genes, go_counts, zip_table
from revision_phase2 import digest, write_table, clean
from usher_pipeline.evidence.annotation.transform import normalize_annotation_score
from usher_pipeline.evidence.expression.models import HPA_LEVEL_ORDINAL, HPA_TISSUE_KEYS
from usher_pipeline.evidence.expression.transform import calculate_tau_specificity, compute_expression_score
from usher_pipeline.evidence.localization.transform import classify_evidence_type, score_localization
from usher_pipeline.evidence.animal_models.models import SENSORY_MP_KEYWORDS, SENSORY_ZP_KEYWORDS

BASE = ROOT / "revision/major_revision_20261006/temporal_validation_v2"
CACHE = ROOT / "data/cache/temporal-validation-v2-20261006"
OLD = ROOT / "data/cache/temporal-extension-20261006/raw"
LAYERS = ["gnomad", "expression", "annotation", "localization", "animal", "literature"]


def unique_index(rows, column):
    mapping = defaultdict(set)
    for row in rows:
        if row[column]:
            mapping[row[column]].add(row["ensembl_gene_id"])
    return {key: next(iter(ids)) for key, ids in mapping.items() if len(ids) == 1}


def symbol_resolver(genes):
    exact = {g["symbol"]: g["ensembl_gene_id"] for g in genes}
    aliases = defaultdict(set)
    for g in genes:
        for name in (g["prev_symbol"] + "|" + g["alias_symbol"]).split("|"):
            if name:
                aliases[name].add(g["ensembl_gene_id"])

    def resolve(name):
        if name in exact:
            return exact[name], "approved"
        if len(aliases.get(name, set())) == 1:
            return next(iter(aliases[name])), "unique_alias"
        return None, "ambiguous_alias" if aliases.get(name) else "unmapped"
    return resolve


def retinal_metadata(path, expected_cells):
    with gzip.open(path, "rt") as handle:
        header = next(csv.reader(handle, delimiter="\t"))
        rows = list(csv.reader(handle, delimiter="\t"))
    corrected = "Barcode" not in header and "barcode" not in header
    if corrected:
        header = ["barcode"] + header
    if len(rows) != expected_cells or any(len(row) != len(header) for row in rows):
        raise ValueError("Retinal metadata dimensions/row widths disagree with matrix")
    barcode_index = header.index("Barcode") if "Barcode" in header else header.index("barcode")
    if len({row[barcode_index] for row in rows}) != len(rows):
        raise ValueError("Retinal cell barcodes are not unique")
    label_index = header.index("Labels")
    return np.array([row[label_index] in ("Rods", "Cones") for row in rows]), {
        "header_barcode_restored": corrected, "cells": len(rows),
        "labels": dict(Counter(row[label_index] for row in rows))}


def photoreceptors(genes):
    resolve = symbol_resolver(genes)
    sums, denominators, platforms, audits = defaultdict(float), Counter(), {}, {}
    for stem, suffix in [("GSE137537", "tsv"), ("GSE137846_Seq-Well", "txt")]:
        raw = CACHE / "raw"
        with gzip.open(raw / f"{stem}_gene_names.txt.gz", "rt") as handle:
            features = [line.strip().strip('"') for line in handle]
        with threadpool_limits(limits=2):
            matrix = mmread(raw / f"{stem}_counts.mtx.gz").tocsr()
        if matrix.shape[0] != len(features) or np.any(matrix.data < 0):
            raise ValueError("Retinal feature dimensions or nonnegative counts invalid")
        selected, audit = retinal_metadata(raw / f"{stem}_sample_annotations.{suffix}.gz", matrix.shape[1])
        n = int(selected.sum())
        if n == 0:
            raise ValueError("No original rods/cones labels")
        values = np.asarray(matrix[:, selected].sum(axis=1)).ravel()
        totals, mapping = defaultdict(float), Counter()
        for name, value in zip(features, values):
            gid, method = resolve(name)
            mapping[method] += 1
            if gid is not None:
                totals[gid] += float(value)
        platforms[stem] = {gid: value / n for gid, value in totals.items()}
        for gid, value in totals.items():
            sums[gid] += value
            denominators[gid] += n
        audits[stem] = dict(audit, selected_photoreceptors=n, features=len(features),
                            nonzero_entries=int(matrix.nnz), mapped_gene_features=len(totals),
                            feature_mapping=dict(mapping), original_feature_order_used=True)
    pooled = {gid: value / denominators[gid] for gid, value in sums.items()}
    return pooled, platforms, audits


def expression_inputs(frame, genes):
    hpa, hpa_date = zip_table("hpa_v20_normal_tissue.zip", OLD)
    tissues = {k.replace("_", " "): k for k in HPA_TISSUE_KEYS}
    hpa = hpa.filter(pl.col("Tissue").is_in(list(tissues)) &
                     pl.col("Reliability").is_in(["Approved", "Enhanced", "Supported"]))
    hpa = hpa.with_columns(pl.col("Level").replace_strict(
        HPA_LEVEL_ORDINAL, default=None, return_dtype=pl.Int8).alias("level"))
    result = frame
    for tissue, key in tissues.items():
        part = hpa.filter(pl.col("Tissue") == tissue).group_by("Gene").agg(pl.col("level").max()).rename(
            {"Gene": "gene_id", "level": f"hpa_{key}_protein_level"})
        result = result.join(part, on="gene_id", how="left")
    with gzip.open(CACHE / "raw/gtex_v8_gene_median_tpm.gct.gz", "rt") as handle:
        if handle.readline().strip() != "#1.2":
            raise ValueError("Unexpected GTEx GCT version")
        dimensions = list(map(int, handle.readline().split()))
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(rows) != dimensions[0]:
        raise ValueError("Incomplete GTEx GCT")
    gtex = {row["Name"].split(".")[0]: row for row in rows}
    if len(gtex) != len(rows):
        raise ValueError("GTEx duplicate unversioned IDs")
    gtex_columns = []
    for tissue, key in [("Brain - Cerebellum", "cerebellum"), ("Testis", "testis"),
                        ("Fallopian Tube", "fallopian_tube")]:
        column = f"gtex_{key}_tpm"
        gtex_columns.append(column)
        result = result.with_columns(pl.Series(column,
            [float(gtex[gid][tissue]) if gid in gtex else None for gid in frame["gene_id"]], dtype=pl.Float64))
    result = calculate_tau_specificity(result, gtex_columns)
    pooled, platforms, photo_audit = photoreceptors(genes)
    variants = {}
    for name, values in [("pooled", pooled), ("without_photo", {}), *platforms.items()]:
        part = result.with_columns(pl.Series("cellxgene_photoreceptor_expr",
            [values.get(gid) for gid in frame["gene_id"]], dtype=pl.Float64))
        variants[name] = compute_expression_score(part)
    return variants, dict(hpa=hpa_date, gtex_dimensions=dimensions, photo=photo_audit)


def channel_count(term_ids, vocabulary, keywords):
    """Unknown labels cannot establish absence of sensory evidence."""
    known = {vocabulary[tid] for tid in term_ids if tid in vocabulary}
    unknown = set(term_ids) - vocabulary.keys()
    positives = {name for name in known if any(k.lower() in name.lower() for k in keywords)}
    count = len(positives) if positives or not unknown else None
    return count, positives, unknown


def animal_inputs(genes):
    entrez = unique_index(genes, "entrez_id")
    hgnc = unique_index(genes, "hgnc_id")
    vocabulary = {}
    with (OLD / "mgi_vocab_20190129.rpt").open() as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) >= 2:
                vocabulary[row[0]] = row[1]
    mouse_terms, mgi_links, zlinks = defaultdict(set), defaultdict(set), defaultdict(set)
    audit = Counter()
    with gzip.open(CACHE / "raw/impc_release11_phenotypes.csv.gz", "rt") as handle:
        for row in csv.DictReader(handle):
            if row["mp_term_id"] and row["mp_term_name"]:
                vocabulary.setdefault(row["mp_term_id"], row["mp_term_name"])
                mouse_terms[row["marker_accession_id"]].add(row["mp_term_id"])
    with (CACHE / "raw/mgi_human_phenotype_20200202.rpt").open() as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) != 8:
                raise ValueError("Historical MGI HMD schema differs")
            gid, mouse = entrez.get(row[1].strip()), row[5].strip()
            if gid and mouse.startswith("MGI:"):
                mgi_links[gid].add(mouse)
                mouse_terms[mouse].update(re.findall(r"MP:\d+", row[6]))
                audit["mapped_mgi_rows"] += 1
    with (CACHE / "raw/zfin_20201230_orthologs.tsv").open() as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) != 10:
                raise ValueError("Historical ZFIN ortholog schema differs")
            a, b = entrez.get(row[6].strip()), hgnc.get("HGNC:" + row[7].strip())
            if a and b and a != b:
                audit["conflicting_zfin_human_ids"] += 1
                continue
            if a or b:
                zlinks[a or b].add(row[0])
    zterms = defaultdict(set)
    with (CACHE / "raw/zfin_20201230_phenotypes.tsv").open() as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) != 25:
                raise ValueError("Historical ZFIN phenotype schema differs")
            audit["zfin_rows"] += 1
            if row[11] != "abnormal":
                continue
            if not re.fullmatch(r"ZDB-GENE-\d+-\d+", row[2]) or re.search(r"[,;|]", row[1]):
                audit["ambiguous_zfin_gene_rows_excluded"] += 1
                continue
            name = " ".join(row[j] for j in (4, 8, 13, 17, 10) if row[j])
            if not name:
                audit["empty_zfin_term_rows"] += 1
                zterms[row[2]].add((row[7], None))
            else:
                zterms[row[2]].add((row[7], name))
    records = []
    for gene in genes:
        gid = gene["ensembl_gene_id"]
        mids, zids = mgi_links[gid], zlinks[gid]
        terms = set().union(*(mouse_terms[mid] for mid in mids)) if mids else set()
        mc, positive, unknown = channel_count(terms, vocabulary, SENSORY_MP_KEYWORDS)
        if not mids:
            mc = None
        zdata = set().union(*(zterms[zid] for zid in zids)) if zids else set()
        zp = {(structure, name) for structure, name in zdata if name and
              any(k.lower() in name.lower() for k in SENSORY_ZP_KEYWORDS)}
        zunknown = sum(name is None for _, name in zdata)
        zc = len(zp) if zids and (zp or not zunknown) else None
        records.append(dict(gene_id=gid, mouse_ortholog_count=len(mids), zfish_ortholog_count=len(zids),
            mouse_count=mc, zfish_count=zc, mouse_unknown_terms=sorted(unknown),
            mouse_positive_terms=sorted(positive), zfish_unknown_terms=zunknown,
            mouse_term_count_is_lower_bound=bool(unknown and positive)))
    variants = {}
    for name, unique in [("native_union", False), ("unique_native_link", True)]:
        counts = []
        for row in records:
            m = row["mouse_count"] if not unique or row["mouse_ortholog_count"] == 1 else None
            z = row["zfish_count"] if not unique or row["zfish_ortholog_count"] == 1 else None
            counts.append((m, z))
        max_count = max((sum(v for v in pair if v is not None) for pair in counts), default=0)
        denominator = math.log2(max_count + 1) if max_count else 1
        variants[name] = np.array([np.nan if m is None and z is None else
            (.4 * bool(m) + .3 * bool(z)) * math.log2((m or 0) + (z or 0) + 1) / denominator
            for m, z in counts])
    audit.update(mapped_mouse_genes=len(mgi_links), mapped_zfish_genes=len(zlinks))
    return variants, records, dict(audit)


def literature_inputs(genes):
    links = defaultdict(set)
    with gzip.open(CACHE / "raw/gene2pubmed_20200629.gz", "rt") as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            taxon, entrez, pmid = line.strip().split("\t")
            if taxon == "9606":
                links[entrez].add(pmid)
    contexts = {}
    for name in ["cilia", "sensory", "cytoskeleton", "polarity", "hts", "direct_context"]:
        with gzip.open(CACHE / "literature_date_sorted" / f"{name}_pmids.txt.gz", "rt") as handle:
            contexts[name] = {line.strip() for line in handle}
    records, raw = [], []
    for gene in genes:
        pub = links[gene["entrez_id"]] if gene["entrez_id"] else set()
        total = len(pub)
        counts = {name: len(pub & ids) for name, ids in contexts.items()}
        if counts["direct_context"]:
            tier, weight = "direct_experimental", 1.
        elif counts["hts"] and (counts["cilia"] or counts["sensory"]):
            tier, weight = "hts_hit", .3
        elif total >= 3 and (counts["cilia"] or counts["sensory"]):
            tier, weight = "functional_mention", .6
        elif total:
            tier, weight = "incidental", .1
        else:
            tier, weight = "none", 0.
        context = 2 * counts["cilia"] + 2 * counts["sensory"] + counts["cytoskeleton"] + counts["polarity"]
        value = context * weight / math.log2(total + 1) if total else 0.
        raw.append(value if gene["entrez_id"] else np.nan)
        records.append(dict(gene_id=gene["ensembl_gene_id"], total_linked_pmids=total if gene["entrez_id"] else None,
                            evidence_tier=tier, **{f"{key}_count": value for key, value in counts.items()}))
    values = np.array(raw)
    observed = np.isfinite(values)
    score = np.full(len(values), np.nan)
    score[observed] = np.where(values[observed] > 0, rankdata(values[observed], method="average") / observed.sum(), 0.)
    return score, records, links


def reconstruct(genes):
    ids = [g["ensembl_gene_id"] for g in genes]
    frame = pl.DataFrame(dict(gene_id=ids, gene_symbol=[g['symbol'] for g in genes]))
    with gzip.open(OLD / "gnomad_v211.bgz", "rt") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len({r["gene_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate historical constraint IDs")
    constraint = {r["gene_id"]: float(r["oe_lof_upper"]) for r in rows
                  if r["oe_lof_upper"] not in ("", "NA", "NaN", "nan")}
    loeuf = np.array([constraint.get(gid, np.nan) for gid in ids])
    gscore = (np.nanmax(loeuf) - loeuf) / (np.nanmax(loeuf) - np.nanmin(loeuf))
    with gzip.open(OLD / "go_20201208.gaf.gz", "rt") as handle:
        counts, go_audit = go_counts(handle, genes)
    annotation = normalize_annotation_score(frame.with_columns(
        pl.Series("go_term_count", [counts.get(gid) for gid in ids], dtype=pl.Int64),
        pl.lit(None, dtype=pl.Float64).alias("uniprot_annotation_score"),
        pl.lit(None, dtype=pl.Boolean).alias("has_pathway_membership")))
    expression, expression_audit = expression_inputs(frame, genes)
    local, local_date = zip_table("hpa_v20_subcellular.zip", OLD)
    if local["Gene"].n_unique() != local.height:
        raise ValueError("Duplicate HPA localization IDs")
    localization = score_localization(classify_evidence_type(frame.join(local.select(
        pl.col("Gene").alias("gene_id"), pl.col("Reliability").alias("hpa_reliability"),
        pl.col("Main location").alias("hpa_main_location")), on="gene_id", how="left")))
    animal, animal_rows, animal_audit = animal_inputs(genes)
    literature, literature_rows, links = literature_inputs(genes)
    for part in [annotation, localization, *expression.values()]:
        if part['gene_id'].to_list() != ids:
            raise ValueError("Source join changed universe alignment")
    values = np.column_stack([gscore, expression['pooled']['expression_score_normalized'].to_numpy(),
        annotation['annotation_score_normalized'].to_numpy(), localization['localization_score_normalized'].to_numpy(),
        animal['native_union'], literature])
    if np.any(np.isfinite(values) & ((values < 0) | (values > 1))):
        raise ValueError("Historical component outside [0,1]")
    direct_cols = ["compartment_cilia", "compartment_centrosome", "compartment_basal_body",
                   "compartment_transition_zone", "compartment_stereocilia"]
    direct = localization.select(pl.any_horizontal([pl.col(c).fill_null(False) for c in direct_cols])).to_series().to_numpy()
    extras = dict(expression={name: part['expression_score_normalized'].to_numpy() for name, part in expression.items()},
                  animal=animal, direct_gate=direct, loeuf=loeuf, go_counts=counts,
                  expression_frame=expression['pooled'], localization_frame=localization,
                  animal_rows=animal_rows, literature_rows=literature_rows, literature_links=links)
    return values, extras, dict(go=go_audit, expression=expression_audit, animal=animal_audit,
                               localization_archive=local_date)

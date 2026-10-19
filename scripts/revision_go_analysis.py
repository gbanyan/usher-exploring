"""Execute the fixed, post-hoc GO classification/enrichment protocol.

Reads frozen temporal outputs; never writes to production or temporal inputs.
"""
import collections
import csv
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

from scipy.stats import hypergeom

from revision_go_common import ASPECTS, EXPERIMENTAL, ROOTS, annotation_index, bh_fdr, map_product, read_editor, same_aspect_closure, term_resolver

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006/go_classification_20261019"
CACHE = ROOT / "data/cache/go-classification-20261019"
OLD = ROOT / "revision/major_revision_20261006/temporal_validation_v2"
AUTHOR = ROOT / "revision/major_revision_20261006/author_review_20261019"


def read_tsv(path):
    return list(csv.DictReader(Path(path).open(), delimiter="\t"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_table(name, rows, columns=None):
    path = BASE / name
    if columns is None:
        if not rows:
            raise ValueError("Empty table requires explicit columns")
        columns = list(rows[0])
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "" if row.get(k) is None else row[k] for k in columns})


def enrich(name, propagated, aspect_map, query, reference, symbol_by_key):
    """Over-representation, retaining zero-overlap hypotheses in pooled BH FDR."""
    results, coverage = [], []
    if not query <= reference:
        raise ValueError("Query is outside the reference")
    for aspect in ("BP", "MF", "CC"):
        background = {g for g in reference if any(aspect_map[t] == aspect for t in propagated.get(g, set()))}
        selected = query & background
        counts = collections.defaultdict(set)
        for g in background:
            for t in propagated[g]:
                if aspect_map[t] == aspect:
                    counts[t].add(g)
        N, n = len(background), len(selected)
        coverage.append(dict(analysis=name, aspect=aspect, eligible_query=len(query), annotated_query=n,
                             eligible_background=len(reference), annotated_background=N,
                             unannotated_case_symbols="; ".join(sorted(symbol_by_key[g] for g in query-selected))))
        if not n or not N:
            continue
        for term, genes in sorted(counts.items()):
            K = len(genes)
            if K < 5 or N-K < 5:
                continue
            hits = genes & selected
            k = len(hits)
            expected = n * K / N
            results.append(dict(analysis=name, aspect=aspect, go_id=term,
                                query_hits=k, query_annotated=n, background_hits=K, background_annotated=N,
                                expected_hits=expected, fold_enrichment=k/expected,
                                p_value=float(hypergeom.sf(k-1, N, K, n)),
                                case_symbols="; ".join(sorted(symbol_by_key[g] for g in hits))))
    qvalues = bh_fdr([r["p_value"] for r in results])
    for row, q in zip(results, qvalues):
        row["fdr_bh"] = q
        row["fdr_lt_0_05"] = q < 0.05
    return sorted(results, key=lambda x: (x["fdr_bh"], x["p_value"], x["go_id"])), coverage


def main():
    assert (BASE / "PROTOCOL.md").exists() and (BASE / "SOURCE_RESOLUTION.md").exists()
    sources = json.loads((BASE / "source_manifest.json").read_text())
    for r in sources:
        assert sha(ROOT / r["cache_path"]) == r["sha256"]
    om = json.loads((BASE / "ontology_manifest.json").read_text())
    assert om["ontology_version"]["timestamp"] == "2026-09-27"
    assert sha(CACHE / "ontology.json") == om["ontology_cache_sha256"]
    for r in om["requests"]:
        assert sha(ROOT / r["cache_path"]) == r["sha256"]
    universe_rows = read_tsv(OLD / "results/historical_components.tsv")
    universe = {r["hgnc_id"] for r in universe_rows}
    assert len(universe) == len(universe_rows) == 19167
    historical = {r["hgnc_id"]: r for r in universe_rows}
    author_rows = read_tsv(AUTHOR / "returned_author_observations.tsv")
    assert len(author_rows) == len({r["gene_key"] for r in author_rows}) == 45
    cases = {r["gene_key"] for r in author_rows}
    coding = cases & universe
    assert len(coding) == 41 and len(cases-universe) == 4
    assert all(r["human_eligibility_decision_as_returned"] == "PENDING" for r in author_rows)
    records = read_tsv(CACHE / "hgnc_complete_set.tsv")
    index = annotation_index(records)
    assert cases <= set(index["records"]), "A case lacks an approved current HGNC record"
    hgnc = index["records"]
    symbols = {g: hgnc[g]["symbol"] if g in hgnc else historical[g]["symbol"] for g in universe|cases}
    editor = read_editor(CACHE / "go-edit-20260927.obo")
    resolve = term_resolver(editor)
    ontology = json.loads((CACHE / "ontology.json").read_text())
    aspect_map = {g: ASPECTS[r["aspect"]] for g, r in ontology.items() if r.get("aspect") in ASPECTS}
    slim = {g for g, r in editor.items() if "goslim_generic" in r["subsets"] and not r.get("obsolete") and g not in ROOTS}
    assert slim <= set(ontology) and all(not ontology[g]["isObsolete"] for g in slim)
    selected_keys = universe | cases
    direct = collections.defaultdict(lambda: collections.defaultdict(set))
    raw_cases, audit = [], collections.Counter()
    routes = collections.defaultdict(set)
    products = collections.defaultdict(set)
    shared_rna = collections.defaultdict(set)
    mapping_rows = collections.Counter()
    for source_name in ("human_protein.gaf.gz", "human_rna.gaf.gz"):
        with gzip.open(CACHE / source_name, "rt") as handle:
            for line in handle:
                if line.startswith("!"):
                    continue
                f = line.rstrip("\n").split("\t")
                assert len(f) >= 17
                audit["source_rows"] += 1
                if f[12].split("|")[0] != "taxon:9606":
                    audit["nonhuman_excluded"] += 1
                    continue
                if "NOT" in f[3].split("|"):
                    audit["NOT_excluded"] += 1
                    continue
                if f[6] == "ND":
                    audit["ND_excluded"] += 1
                    continue
                term = resolve(f[4])
                if not term or term not in ontology or ontology[term]["isObsolete"]:
                    audit["unresolved_or_obsolete_excluded"] += 1
                    continue
                if term in ROOTS:
                    audit["root_only_excluded"] += 1
                    continue
                assert f[8] == {"BP": "P", "MF": "F", "CC": "C"}[aspect_map[term]]
                if f[13] and f[13] > "20261019":
                    raise ValueError("Future annotation date")
                mapped, route = map_product(f, index)
                mapping_rows[route] += 1
                keys = mapped & selected_keys
                if not keys:
                    audit["unmapped_or_outside_universe_rows"] += 1
                    continue
                audit["usable_source_rows"] += 1
                for key in keys:
                    direct[key][term].add(f[6])
                    routes[key].add(route)
                    products[key].add(f[0]+":"+f[1])
                    if "shared sequence" in route:
                        shared_rna[key].update(mapped)
                    if key in cases:
                        raw_cases.append(dict(gene_key=key, frozen_symbol=next(r["symbol"] for r in author_rows if r["gene_key"]==key),
                            current_symbol=symbols[key], source=source_name, gene_product=f[0]+":"+f[1], mapping_route=route,
                            original_go_id=f[4], go_id=term, term_name=ontology[term]["name"], aspect=aspect_map[term],
                            relation=f[3], evidence_code=f[6], reference=f[5], with_from=f[7],
                            annotation_date=f[13], assigned_by=f[14], annotation_extension=f[15]))
    raw_cases.sort(key=lambda x: (x["frozen_symbol"], x["aspect"], x["go_id"], x["evidence_code"], x["reference"], x["gene_product"]))
    propagated, no_iea = {}, {}
    for g, annotated in direct.items():
        propagated[g], no_iea[g] = set(), set()
        for term, codes in annotated.items():
            closure = same_aspect_closure(term, ontology)
            assert term in closure
            assert all(t in aspect_map and aspect_map[t] == aspect_map[term] for t in closure)
            propagated[g].update(closure)
            if codes - {"IEA"}:
                no_iea[g].update(closure)
    rank_rows = read_tsv(OLD / "results/case_rankings.tsv")
    ranks = {(r["gene_key"], r["scheme"]): r for r in rank_rows if r["scheme"] in ("archived_five", "archived_six")}
    memberships, gene_rows = [], []
    for r in author_rows:
        key = r["gene_key"]
        current = hgnc[key]
        counts = {a: sum(aspect_map[t]==a for t in direct.get(key, {})) for a in ("BP", "MF", "CC")}
        codes = {c for values in direct.get(key, {}).values() for c in values}
        labels = {}
        for aspect in ("BP", "MF", "CC"):
            cats = sorted((propagated.get(key, set()) & slim), key=lambda t: (ontology[t]["name"], t))
            cats = [t for t in cats if aspect_map[t] == aspect]
            labels[aspect] = "; ".join(ontology[t]["name"]+" ["+t+"]" for t in cats)
            for t in cats:
                supporting = sorted(g for g in direct[key] if t in same_aspect_closure(g, ontology))
                memberships.append(dict(gene_key=key, frozen_symbol=r["symbol"], current_symbol=current["symbol"],
                    aspect=aspect, slim_go_id=t, category=ontology[t]["name"], supporting_direct_terms="; ".join(supporting),
                    supported_without_IEA=t in no_iea.get(key,set()), in_historical_universe=key in universe))
        notes = []
        if key not in universe:
            notes.append("Noncoding RNA retained in 45-case description; outside original coding-score/enrichment universe")
        if shared_rna[key]:
            notes.append("Explicit HGNC RNAcentral mapping to a shared sequence; not independent locus-specific functional experiments")
        if not direct.get(key):
            notes.append("No usable positive GO annotation found; do not infer absent biological function")
        elif not codes-{"IEA"}:
            notes.append("All usable direct annotations are electronic (IEA)")
        gene_rows.append(dict(gene_key=key, frozen_symbol=r["symbol"], current_symbol=current["symbol"],
            gene_type=current["locus_group"], in_historical_universe=key in universe,
            usable_direct_go_terms=sum(counts.values()), BP_direct_terms=counts["BP"], MF_direct_terms=counts["MF"], CC_direct_terms=counts["CC"],
            BP_categories=labels["BP"], MF_categories=labels["MF"], CC_categories=labels["CC"],
            evidence_codes="; ".join(sorted(codes)), experimental_direct_terms=sum(bool(c & EXPERIMENTAL) for c in direct.get(key,{}).values()),
            non_IEA_direct_terms=sum(bool(c-{"IEA"}) for c in direct.get(key,{}).values()),
            mapping_routes="; ".join(sorted(routes[key])), annotated_gene_products="; ".join(sorted(products[key])),
            shared_RNAcentral_HGNC_keys="; ".join(sorted(shared_rna[key])),
            frozen_2020_GO_count=int(historical[key]["go_positive_terms"]) if key in historical and historical[key]["go_positive_terms"] else None,
            five_layer_percentile=float(ranks[key,"archived_five"]["percentile"]) if key in universe else None,
            six_layer_percentile=float(ranks[key,"archived_six"]["percentile"]) if key in universe else None,
            author_eligibility_as_returned=r["human_eligibility_decision_as_returned"], notes=". ".join(notes)))
    categories = []
    for term in sorted(slim, key=lambda t: (aspect_map[t], ontology[t]["name"], t)):
        members = {key for key in cases if term in propagated.get(key,set())}
        coded = members & coding
        categories.append(dict(aspect=aspect_map[term], go_id=term, category=ontology[term]["name"],
            genes_of_45=len(members), proportion_of_45=len(members)/45, coding_genes_of_41=len(coded),
            noncoding_genes_of_4=len(members-coding), genes_without_IEA=sum(term in no_iea.get(g,set()) for g in members),
            median_five_percentile=statistics.median(float(ranks[g,"archived_five"]["percentile"]) for g in coded) if coded else None,
            median_six_percentile=statistics.median(float(ranks[g,"archived_six"]["percentile"]) for g in coded) if coded else None,
            genes="; ".join(sorted(symbols[g] for g in members))))
    roster = json.loads((OLD / "cohort_screening/clinical_roster.json").read_text())["records"]
    catalog = {r["gene_key"] for r in roster if any(s.startswith(("RetNet:","panel")) for s in r.get("source_records", []))} & universe
    assert coding <= catalog, sorted(coding-catalog)
    analysis_rows, coverage_rows = [], []
    for name, associations, background in [
        ("Primary: genome background", propagated, universe),
        ("Sensitivity: exclude IEA", no_iea, universe),
        ("Sensitivity: catalog background", propagated, catalog),
    ]:
        result, coverage = enrich(name, associations, aspect_map, coding, background, symbols)
        for row in result:
            row["term_name"] = ontology[row["go_id"]]["name"]
        analysis_rows.extend(result)
        coverage_rows.extend(coverage)
    save_table("gene_summary.tsv", gene_rows)
    save_table("case_direct_annotations.tsv", raw_cases)
    save_table("slim_membership.tsv", memberships)
    save_table("category_summary.tsv", categories)
    save_table("enrichment.tsv", analysis_rows)
    save_table("enrichment_coverage.tsv", coverage_rows)
    save_table("gene_slim_matrix.tsv", [{"gene_key":g["gene_key"],"symbol":g["current_symbol"], **{t:int(t in propagated.get(g["gene_key"],set())) if g["usable_direct_go_terms"] else None for t in sorted(slim)}} for g in gene_rows])
    save_table("background_gene_mapping.tsv", [dict(gene_key=g, frozen_symbol=historical[g]["symbol"], current_symbol=symbols[g],
        has_current_HGNC_record=g in hgnc, has_any_GO=bool(propagated.get(g)),
        has_BP=any(aspect_map[t]=="BP" for t in propagated.get(g,set())),
        has_MF=any(aspect_map[t]=="MF" for t in propagated.get(g,set())),
        has_CC=any(aspect_map[t]=="CC" for t in propagated.get(g,set())),
        in_catalog_reference=g in catalog, mapping_routes="; ".join(sorted(routes[g]))) for g in sorted(universe)])
    # Compact complete association objects make independent numerical replay possible.
    (CACHE / "analysis_associations.json").write_text(json.dumps({
        "all": {g: sorted(t) for g,t in propagated.items()}, "no_IEA": {g: sorted(t) for g,t in no_iea.items()},
        "query": sorted(coding), "genome": sorted(universe), "catalog": sorted(catalog), "aspect_map": aspect_map,
    }, separators=(",", ":")) + "\n")
    summary = dict(case_rows=45, coding_query=41, outside_coding_universe=4,
        current_GO_annotated_cases=sum(g["usable_direct_go_terms"]>0 for g in gene_rows),
        cases_no_usable_GO=[g["current_symbol"] for g in gene_rows if not g["usable_direct_go_terms"]],
        generic_slim_categories=len(slim), categories_with_cases=sum(c["genes_of_45"]>0 for c in categories),
        direct_case_annotation_records=len(raw_cases), gene_category_memberships=len(memberships),
        genome_eligible=19167, catalog_eligible=len(catalog), coverage=coverage_rows,
        enrichment=[dict(analysis=name, tested_terms=sum(r["analysis"]==name for r in analysis_rows),
            fdr_significant=sum(r["analysis"]==name and r["fdr_lt_0_05"] for r in analysis_rows)) for name in dict.fromkeys(r["analysis"] for r in analysis_rows)],
        ontology_version=om["ontology_version"], annotation_audit=dict(audit), mapping_row_routes=dict(mapping_rows),
        protocol_sha256=sha(BASE/"PROTOCOL.md"), source_resolution_sha256=sha(BASE/"SOURCE_RESOLUTION.md"),
        frozen_data_changed=False, original_author_eligibility_preserved=True)
    (BASE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (CACHE / "workbook_data.json").write_text(json.dumps(dict(genes=gene_rows,categories=categories,memberships=memberships,
        annotations=raw_cases,enrichment=analysis_rows,coverage=coverage_rows,summary=summary), separators=(",",":")) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

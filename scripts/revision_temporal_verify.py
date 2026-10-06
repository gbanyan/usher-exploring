"""Independent arithmetic/rank checks plus archival and protected-file checks."""
from collections import Counter
import csv
import gzip
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006/temporal_extension"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    out = BASE / "results"
    components = {r["gene_id"]: r for r in csv.DictReader((out / "historical_components.tsv").open(), delimiter="\t")}
    rows = list(csv.DictReader((out / "historical_rankings.tsv").open(), delimiter="\t"))
    cases = list(csv.DictReader((out / "case_rankings.tsv").open(), delimiter="\t"))
    weights = {"historical_default_available": [.2, .2, .15, .15], "historical_equal_available": [1., 1., 1., 1.]}
    layers = ["gnomad", "expression", "annotation", "localization"]
    max_error = 0
    for row in rows:
        if row["scheme"] not in weights:
            continue
        component = components[row["gene_id"]]
        observed = [(float(component[layer + "_score"]), weight) for layer, weight in zip(layers, weights[row["scheme"]]) if component[layer + "_score"] != ""]
        expected = sum(value * weight for value, weight in observed) / sum(weight for _, weight in observed) if observed else None
        if expected is None:
            assert row["score"] == ""
        else:
            max_error = max(max_error, abs(expected - float(row["score"])))
    assert max_error < 1e-12
    for scheme in {r["scheme"] for r in rows}:
        subset = [r for r in rows if r["scheme"] == scheme and r["score"] != ""]
        descending = sorted(subset, key=lambda r: (-float(r["score"]), r["gene_id"]))
        assert all(int(r["rank_position"]) == i + 1 for i, r in enumerate(descending))
        minimum_positions = {}
        for i, row in enumerate(sorted(subset, key=lambda r: float(r["score"]))):
            minimum_positions.setdefault(float(row["score"]), i)
        assert all(abs(float(r["percentile"]) - 100 * minimum_positions[float(r["score"])] / (len(subset) - 1)) < 1e-10 for r in subset)
        assert all(int(r["rank_denominator"]) == len(subset) for r in subset)
        for r in subset:
            assert all((r[f"top{k}"] == "True") == (int(r["rank_position"]) <= k) for k in (25, 50, 100))
    assert len(rows) == 19167 * 6 and len(cases) == 12 * 6
    taxa, years = Counter(), Counter()
    with gzip.open(ROOT / "data/cache/temporal-extension-20261006/raw/go_20201208.gaf.gz", "rt") as handle:
        for line in handle:
            if line.startswith("!"):
                continue
            fields = line.rstrip("\n").split("\t")
            # GAF's optional second taxon is the interacting organism, not
            # a second gene species. Check the primary gene-product taxon.
            taxa[fields[12].split("|")[0]] += 1
            years[fields[13][:4]] += 1
    assert set(taxa) == {"taxon:9606"} and max(years) <= "2020"
    with (ROOT / "data/cache/temporal-extension-20261006/raw/mgi_20200202.rpt").open() as handle:
        schema = Counter(len(line.rstrip("\n").split("\t")) for line in handle)
    assert set(schema) == {8}
    protected = json.loads((BASE.parent / "input_manifest.json").read_text())["input_sha256"]
    assert all(sha(ROOT / path) == expected for path, expected in protected.items())
    manifest = json.loads((out / "manifest.json").read_text())
    assert all(sha(out / path) == expected for path, expected in manifest["output_sha256"].items())
    assert sha(ROOT / "scripts/revision_temporal_analysis.py") == manifest["script_sha256"]
    result = {"execution_location": "local macOS .venv", "python": sys.version,
              "software": {x: version(x) for x in ["numpy", "polars", "scipy", "duckdb", "pytest"]},
              "all_rank_rows": len(rows), "case_rows": len(cases), "independent_composite_max_abs_error": max_error,
              "independent_all_scheme_position_percentile_topk_checks": True, "gaf_primary_taxa": dict(taxa),
              "gaf_latest_annotation_year": max(years), "historical_mgi_column_counts": dict(schema),
              "protected_hashes_unchanged": True, "output_hashes_match": True,
              "transform_sha256": {str(Path("src/usher_pipeline/evidence") / layer / "transform.py"): sha(ROOT / "src/usher_pipeline/evidence" / layer / "transform.py") for layer in ["expression", "annotation", "localization"]}}
    (BASE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

"""Compare the approved pre-rebuild HIGH shortlist with the current one.

The old artifact is read from local Git history; no external data is fetched.
The comparison output is explicitly diagnostic and does not feed production
scoring or tier assignment.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import subprocess
from pathlib import Path

import duckdb
from scipy.stats import spearmanr


DEFAULT_OLD_COMMIT = "17a34653472792228c6e8740d28383b06731ed0a"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_old_tsv(commit: str, path: str) -> list[dict[str, str]]:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return list(csv.DictReader(io.StringIO(result.stdout), delimiter="\t"))


def rank_map(rows: list[dict[str, str]]) -> dict[str, int]:
    return {row["gene_id"]: index for index, row in enumerate(rows, start=1)}


def parse_old_label_count(commit: str) -> int | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:data/report/reproducibility.md"],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"\| load_scored_genes \| (\d+) \|", result.stdout)
    return int(match.group(1)) if match else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-commit", default=DEFAULT_OLD_COMMIT)
    parser.add_argument("--new-candidates", type=Path, default=Path("data/report/candidates.tsv"))
    parser.add_argument("--db", type=Path, default=Path("data/pipeline.duckdb"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/report/exploration"))
    args = parser.parse_args()

    if not args.new_candidates.is_file():
        raise FileNotFoundError(f"Missing current candidates artifact: {args.new_candidates}")
    if not args.db.is_file():
        raise FileNotFoundError(f"Missing current scored-state database: {args.db}")

    old_rows = read_old_tsv(args.old_commit, "data/report/candidates.tsv")
    new_rows = read_tsv(args.new_candidates)
    old_high = [row for row in old_rows if row.get("confidence_tier") == "HIGH"]
    new_high = [row for row in new_rows if row.get("confidence_tier") == "HIGH"]
    old_high_rank = rank_map(old_high)
    new_high_rank = rank_map(new_high)
    old_rank = rank_map(old_rows)
    new_rank = rank_map(new_rows)

    old_ids = set(old_high_rank)
    new_ids = set(new_high_rank)
    overlap = old_ids & new_ids
    shared_candidates = sorted(set(old_rank) & set(new_rank))
    shared_old_ranks = [old_rank[gene_id] for gene_id in shared_candidates]
    shared_new_ranks = [new_rank[gene_id] for gene_id in shared_candidates]
    rho = float(spearmanr(shared_old_ranks, shared_new_ranks).statistic)
    retained_deltas = [new_high_rank[gene_id] - old_high_rank[gene_id] for gene_id in overlap]

    rows = []
    for gene_id in sorted(old_ids | new_ids):
        old = next((row for row in old_high if row["gene_id"] == gene_id), None)
        new = next((row for row in new_high if row["gene_id"] == gene_id), None)
        rows.append({
            "gene_id": gene_id,
            "gene_symbol_old": old["gene_symbol"] if old else "",
            "gene_symbol_new": new["gene_symbol"] if new else "",
            "status": "retained" if old and new else ("old_only" if old else "new_only"),
            "old_high_rank": old_high_rank.get(gene_id, ""),
            "new_high_rank": new_high_rank.get(gene_id, ""),
            "rank_delta_new_minus_old": (
                new_high_rank[gene_id] - old_high_rank[gene_id] if old and new else ""
            ),
            "old_composite_score": old.get("composite_score", "") if old else "",
            "new_composite_score": new.get("composite_score", "") if new else "",
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    tsv_path = args.output_dir / "high_shortlist_old_vs_new.tsv"
    with tsv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    con = duckdb.connect(str(args.db), read_only=True)
    new_label_count = con.execute("SELECT COUNT(*) FROM scored_genes").fetchone()[0]
    con.close()
    old_label_count = parse_old_label_count(args.old_commit)
    median_abs_delta = (
        sorted(abs(delta) for delta in retained_deltas)[len(retained_deltas) // 2]
        if retained_deltas else None
    )
    report = f"""# HIGH-shortlist old-versus-new comparison

This diagnostic compares the pre-rebuild artifact at `{args.old_commit}` with the
current scored state. The old-side IDs are retained here only to make retention
and rank changes auditable; they are not production inputs.

| Metric | Old | New |
|---|---:|---:|
| Scored labels | {old_label_count if old_label_count is not None else 'unknown'} | {new_label_count} |
| Candidate rows | {len(old_rows)} | {len(new_rows)} |
| HIGH rows | {len(old_high)} | {len(new_high)} |

- HIGH overlap: {len(overlap)}
- Old HIGH retained in new HIGH: {len(overlap)}/{len(old_ids)} ({100 * len(overlap) / len(old_ids):.1f}%)
- Old-only HIGH: {len(old_ids - new_ids)}
- New-only HIGH: {len(new_ids - old_ids)}
- Shared-candidate rank Spearman rho: {rho:.4f} ({len(shared_candidates)} shared candidates)
- Retained-HIGH rank delta (new minus old): median absolute {median_abs_delta},
  minimum {min(retained_deltas) if retained_deltas else 'n/a'},
  maximum {max(retained_deltas) if retained_deltas else 'n/a'}

The machine-readable row-level comparison is `high_shortlist_old_vs_new.tsv`.
"""
    (args.output_dir / "high_shortlist_old_vs_new.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()

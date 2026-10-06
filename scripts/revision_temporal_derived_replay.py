"""Read-only verification of co-primary temporal scores/ranks from derived tables.

This does not regenerate raw evidence, clinical ascertainment, HIGH source flags,
or alternative global expression vectors. It verifies the 38,334 saved primary
rows (including NULL rows) using the delivered historical component table.
"""
from pathlib import Path
import argparse
import json
import numpy as np
import polars as pl
from revision_temporal_v2_evaluate import LAYERS, WEIGHTS, ranking
from revision_phase2 import weighted_mean


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, default=Path('revision/major_revision_20261006/temporal_validation_v2/results'))
    args = parser.parse_args()
    components = pl.read_csv(args.results_dir / 'historical_components.tsv', separator='\t', infer_schema_length=None)
    saved = pl.read_csv(args.results_dir / 'historical_primary_rankings.tsv', separator='\t', infer_schema_length=None)
    ids = components['gene_id'].to_list()
    matrix = np.ascontiguousarray(components.select(LAYERS).to_numpy())
    rows = 0
    for scheme, weights in [('archived_five', WEIGHTS * [1,1,1,1,1,0]), ('augmented_six', WEIGHTS)]:
        scores = weighted_mean(matrix, weights)
        ranks, n = ranking(scores, ids)
        original = saved.filter(pl.col('scheme') == scheme)
        if original['gene_id'].to_list() != ids:
            raise ValueError('Saved row order differs from component IDs')
        np.testing.assert_allclose(scores, original['score'].to_numpy(), rtol=0, atol=0, equal_nan=True)
        counts = (np.isfinite(matrix) & (weights > 0)).sum(axis=1)
        np.testing.assert_array_equal(counts, original['evidence_count'].to_numpy())
        for key, values in ranks.items():
            np.testing.assert_allclose(values, original[key].to_numpy(), rtol=0, atol=0, equal_nan=True)
        rows += len(original)
        print(json.dumps({'scheme': scheme, 'rows': len(original), 'scored': n, 'exact_scores_counts_and_ranks': True}))
    print(json.dumps({'verified_rows': rows, 'raw_source_or_clinical_regeneration': False, 'HIGH_source_flags_reconstructed': False}))


if __name__ == '__main__':
    main()

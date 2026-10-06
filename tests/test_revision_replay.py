"""Replay must preserve scientific missingness and reject changed input bytes."""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import revision_replay as replay
from revision_phase4 import pair_scores


def test_round_trip_distinguishes_null_zero_empty_and_quoted_text(tmp_path):
    source = tmp_path / "source.duckdb"
    with duckdb.connect(str(source)) as con:
        for table in replay.TABLES:
            con.execute(f'CREATE TABLE "{table}" (gene_id VARCHAR, value DOUBLE, label VARCHAR)')
            con.executemany(f'INSERT INTO "{table}" VALUES (?, ?, ?)', [
                ("ENSG3", None, None), ("ENSG1", 0., ""),
                ("ENSG2", .75, 'quoted "text"\twith\nnewline'),
            ])
    bundle = tmp_path / "bundle"
    rebuilt = tmp_path / "rebuilt.duckdb"
    replay.export(source, bundle)
    replay.build(bundle, rebuilt)
    with duckdb.connect(str(rebuilt), read_only=True) as con:
        assert con.execute("SELECT * FROM scored_genes ORDER BY gene_id").fetchall() == [
            ("ENSG1", 0., ""), ("ENSG2", .75, 'quoted "text"\twith\nnewline'),
            ("ENSG3", None, None),
        ]
    with pytest.raises(FileExistsError):
        replay.build(bundle, rebuilt)
    with duckdb.connect(str(rebuilt)) as con:
        con.execute("UPDATE scored_genes SET value=0 WHERE gene_id='ENSG3'")
    with pytest.raises(ValueError, match="differs from frozen input"):
        replay.validate_database(rebuilt, bundle)
    path = bundle / "scored_genes.tsv"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="bundle changed"):
        replay.validate_database(source, bundle)


def test_common_layer_pair_does_not_impute_or_retain_unshared_evidence():
    weights = np.array([.2, .2, .15])
    a = np.array([0., .9, np.nan])
    b = np.array([.4, np.nan, 1.])
    np.testing.assert_allclose(pair_scores(a, b, weights, common=True), [0., .4])
    assert pair_scores(a, b, weights)[0] > 0
    assert np.isnan(pair_scores(np.array([1., np.nan]), np.array([np.nan, .5]), np.ones(2), common=True)).all()

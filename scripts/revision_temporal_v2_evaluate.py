"""Evaluate historical analogues only after a committed input/cohort freeze.

The clinical roster is read before reconstruction. Neither labels nor outcomes
are passed to evidence transforms or used to fit any parameter.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import importlib.metadata
import platform

import numpy as np
import polars as pl
from scipy.stats import rankdata, spearmanr

from revision_temporal_v2_reconstruct import BASE, ROOT, OLD, LAYERS, reconstruct
from revision_temporal_analysis import historical_genes
from revision_phase2 import clean, digest, weighted_mean, write_table
from revision_replay import protected_inputs

WEIGHTS = np.array([.20, .20, .15, .15, .15, .15])
PRIMARY = ('archived_five', 'augmented_six')
TOPK = (25, 50, 100, 500, 1000)


def ranking(scores, ids):
    """Keep deterministic positions distinct from statistical tie ranks."""
    scores = np.asarray(scores, dtype=float)
    observed = np.isfinite(scores)
    n = int(observed.sum())
    result = {name: np.full(len(scores), np.nan) for name in
              ('position', 'tie_min', 'tie_max', 'percentile', 'minimum_percentile')}
    selected = np.flatnonzero(observed)
    ordered = selected[np.lexsort((np.asarray(ids)[selected], -scores[selected]))]
    result['position'][ordered] = np.arange(1, n + 1)
    if n:
        result['tie_min'][selected] = rankdata(-scores[selected], method='min')
        result['tie_max'][selected] = rankdata(-scores[selected], method='max')
        result['percentile'][selected] = (100 * (rankdata(scores[selected]) - 1) / (n - 1)) if n > 1 else 0
        result['minimum_percentile'][selected] = (100 * (rankdata(scores[selected], method='min') - 1) / (n - 1)) if n > 1 else 0
    return result, n


def animal_gate_threshold(values):
    values = np.asarray(values, dtype=float)
    positive = values[np.isfinite(values) & (values > 0)]
    return float(pl.Series(positive).quantile(.75, interpolation='nearest')) if len(positive) else None


def recovery(position, tie_min, tie_max, boundary):
    """NULL/out-of-universe cases always fail every recovery rule."""
    if position is None or not np.isfinite(position):
        return False, False, False
    # All members of a tie strictly above the cutoff are recovered; a tie
    # straddling the cutoff is excluded from the conservative sensitivity.
    return position <= boundary, tie_min <= boundary, tie_max <= boundary


def wilson(successes, total):
    if not total:
        return None, None
    z = 1.959963984540054
    p = successes / total
    center = (p + z*z/(2*total)) / (1 + z*z/total)
    half = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / (1 + z*z/total)
    return center-half, center+half


def schemes(matrix, extras):
    yield 'archived_five', matrix, WEIGHTS * [1, 1, 1, 1, 1, 0]
    yield 'augmented_six', matrix, WEIGHTS.copy()
    yield 'equal_six', matrix, np.ones(6)
    for j, layer in enumerate(LAYERS):
        single = np.zeros(6); single[j] = 1
        omitted = WEIGHTS.copy(); omitted[j] = 0
        yield f'single_{layer}', matrix, single
        yield f'omit_{layer}', matrix, omitted
    yield 'omit_animal_literature', matrix, WEIGHTS * [1, 1, 1, 1, 0, 0]
    for scale in (.7, .4):
        changed = matrix.copy(); changed[:, 4] *= scale
        yield f'animal_uniform_{scale}', changed, WEIGHTS.copy()
    changed = matrix.copy(); changed[:, 4] = extras['animal']['unique_native_link']
    yield 'animal_unique_native_link', changed, WEIGHTS.copy()
    for name, vector in extras['expression'].items():
        if name == 'pooled':
            continue
        changed = matrix.copy(); changed[:, 1] = vector
        yield f'expression_{name}', changed, WEIGHTS.copy()
    changed = matrix.copy(); changed[:, 2] /= .5
    yield 'annotation_available_go_rescale', changed, WEIGHTS.copy()


def verified_freeze(path, commit):
    relative = str(path.resolve().relative_to(ROOT))
    # A working-tree file alone is not evidence that selection preceded outcomes.
    committed = subprocess.check_output(['git', 'show', f'{commit}:{relative}'], cwd=ROOT)
    if committed != path.read_bytes():
        raise ValueError('Freeze manifest differs from its committed version')
    freeze = json.loads(committed)
    if freeze['status'] != 'frozen_before_v2_outcomes':
        raise ValueError('Protocol/source/cohort freeze is incomplete')
    required = {str(p.relative_to(ROOT)) for p in (ROOT/'src/usher_pipeline').rglob('*.py')}
    required.update(f'scripts/{name}.py' for name in
                    ('revision_phase2', 'revision_temporal_analysis', 'revision_replay',
                     'revision_temporal_v2_reconstruct', 'revision_temporal_v2_evaluate'))
    required.update((freeze['clinical_roster_path'], freeze['protocol_path'],
                     freeze['source_inventory_path'], freeze['reference_index_path'],
                     freeze['environment_lock_path'], 'pyproject.toml',
                     'revision/major_revision_20261006/input_manifest.json',
                     'revision/major_revision_20261006/temporal_extension/results/historical_components.tsv'))
    inventory = json.loads((ROOT/freeze['source_inventory_path']).read_text())
    required.update(e['path'] for e in inventory['entries'])
    required.update(e['provenance_manifest'] for e in inventory['entries'])
    references = json.loads((ROOT/freeze['reference_index_path']).read_text())['references']
    for reference in references.values():
        required.update(reference['metadata_source_paths'])
        if reference.get('primary_xml_path'):
            required.add(reference['primary_xml_path'])
    if missing := required - freeze['files'].keys():
        raise ValueError(f'Freeze omits required dependencies: {sorted(missing)}')
    for name, expected in freeze['files'].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f'Frozen input changed: {name}')
        if not name.startswith('data/cache/'):
            content = subprocess.check_output(['git', 'show', f'{commit}:{name}'], cwd=ROOT)
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError(f'Input was not frozen in the specified commit: {name}')
    if platform.python_version() != freeze['python_version']:
        raise ValueError('Python version differs from frozen environment')
    for line in (ROOT/freeze['environment_lock_path']).read_text().splitlines():
        if line and not line.startswith('#'):
            name, version = line.split('==')
            if importlib.metadata.version(name) != version:
                raise ValueError(f'Package version differs from frozen environment: {name}')
    return freeze


def validate_roster(roster):
    """Reject incomplete or development-contaminated principal cohorts."""
    from revision_phase2 import GROUPS
    forbidden = set(GROUPS['usher']) | set(GROUPS['syscilia']) | {'CEP162', 'CFAP20', 'LRRC45'}
    keys = [r['gene_key'] for r in roster]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate clinical gene keys')
    for row in roster:
        if row.get('clinical_status') != 'strong_novel_target':
            continue
        if row['symbol'] in forbidden or row.get('historical_symbol') in forbidden:
            raise ValueError('Previously inspected development/pilot case in primary cohort')
        if row.get('novelty') not in ('A', 'B'):
            raise ValueError('Unresolved novelty in principal cohort')
        if row.get('unrelated_target_families_lower_bound', 0) < 2:
            raise ValueError('Fewer than two documented target families')
        if not row.get('qualifying_functional_evidence') and not row.get('independent_replication_evidence'):
            raise ValueError('Principal case lacks functional/replication support')
        if row.get('target_public_date_interval', ['', ''])[0] <= '2020-12-31':
            raise ValueError('Principal first-target date crosses cutoff')
        if not row.get('postcutoff_association_pmids') or not row.get('reference_keys'):
            raise ValueError('Principal case lacks cited postcutoff clinical evidence')
        if not row.get('observed_human_inheritance_evidence'):
            raise ValueError('Principal case lacks inheritance/segregation evidence')
        if not row.get('domains'):
            raise ValueError('Principal case lacks target domain')
        if row.get('material_human_validity_conflict', False):
            raise ValueError('Contested human association in principal cohort')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze', type=Path, default=BASE / 'freeze.json')
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--output-dir', type=Path, default=BASE / 'results')
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError('Preserve previous outcomes; choose a new replay directory')
    freeze = verified_freeze(args.freeze, args.freeze_commit)
    protected = protected_inputs(ROOT / 'data/pipeline.duckdb')
    roster = json.loads((ROOT / freeze['clinical_roster_path']).read_text())['records']
    validate_roster(roster)
    if any(row.get('selection_decision_status') != 'closed' for row in roster):
        raise ValueError('Clinical roster contains unfinished selection decisions')
    with (OLD / 'hgnc_20201001.tsv').open() as handle:
        genes, excluded = historical_genes(list(csv.DictReader(handle, delimiter='\t')))
    ids = np.array([g['ensembl_gene_id'] for g in genes])
    key_index = {g['hgnc_id']: i for i, g in enumerate(genes)}
    # Only these adjudicated sets receive individual score reports. The full
    # ascertainment ledger, including unresolved cases, remains separately saved.
    cases = [row for row in roster if row['clinical_status'] in
             ('strong_novel_target', 'candidate_novel_target', 'candidate_novelty_unresolved', 'pilot_reference',
              'development_reference', 'phenotype_expansion', 'evidence_maturation',
              'scope_comparison')]
    matrix, extras, audit = reconstruct(genes)
    for case in cases:
        i = key_index.get(case['gene_key'])
        if i is not None:
            linked = extras['literature_links'].get(genes[i]['entrez_id'], set())
            later = set(case.get('postcutoff_association_pmids', []))
            if linked & later:
                raise ValueError(f'Held-out clinical evidence leaked into archived links: {case["symbol"]}')
    components = [dict(gene_id=gid, hgnc_id=genes[i]['hgnc_id'], symbol=genes[i]['symbol'],
        loeuf=extras['loeuf'][i], go_positive_terms=extras['go_counts'].get(gid),
        **{layer: matrix[i,j] for j, layer in enumerate(LAYERS)}) for i, gid in enumerate(ids)]
    coverage = [dict(layer=layer, universe=len(genes), observed=int(np.isfinite(matrix[:,j]).sum()),
        positive=int((matrix[:,j] > 0).sum()), observed_zero=int((matrix[:,j] == 0).sum()),
        missing=int((~np.isfinite(matrix[:,j])).sum())) for j, layer in enumerate(LAYERS)]
    case_rows, summaries, rankings, gate_rows = [], [], [], []
    all_scores, all_ranks, scheme_audit = {}, {}, {}
    for name, values, weights in schemes(matrix, extras):
        scores = weighted_mean(values, weights)
        ranks, n = ranking(scores, ids)
        counts = (np.isfinite(values) & (weights > 0)).sum(axis=1)
        q75 = animal_gate_threshold(values[:,4])
        signal = extras['direct_gate'] | ((values[:,4] >= q75) if q75 is not None else False)
        high = (scores >= .7) & (counts >= 3) & signal
        all_scores[name], all_ranks[name] = scores, ranks
        scheme_audit[name] = dict(weights=weights.tolist(), scored=n, animal_positive_q75=q75,
                                  high=int(high.sum()), score_count_direct_gate=int(extras['direct_gate'].sum()))
        if name in PRIMARY:
            rankings.extend(dict(scheme=name, gene_id=gid, symbol=genes[i]['symbol'], score=scores[i],
                evidence_count=int(counts[i]), high=bool(high[i]),
                **{key: array[i] for key, array in ranks.items()}) for i, gid in enumerate(ids))
        local_cases = []
        for case in cases:
            i = key_index.get(case['gene_key'])
            inside = i is not None
            row = dict(scheme=name, gene_key=case['gene_key'], symbol=case['symbol'],
                clinical_status=case['clinical_status'], novelty=case.get('novelty'),
                control_group=case.get('control_group'),
                domains='|'.join(case.get('domains', [])), mechanism=case.get('mechanism'),
                in_historical_universe=inside, score=scores[i] if inside else None,
                scored=inside and bool(np.isfinite(scores[i])), evidence_count=int(counts[i]) if inside else 0,
                high=inside and bool(high[i]), **{key: array[i] if inside else None for key, array in ranks.items()},
                **{f'{layer}_component': values[i,j] if inside else None for j, layer in enumerate(LAYERS)})
            for label, bound in [(f'top{k}', k) for k in TOPK] + [(f'top{int(p*100)}pct', math.ceil(p*n)) for p in (.01,.05,.10)]:
                deterministic, inclusive, conservative = recovery(row['position'], row['tie_min'], row['tie_max'], bound)
                row[label], row[label+'_tie_inclusive'], row[label+'_whole_tie_above_boundary'] = deterministic, inclusive, conservative
            case_rows.append(row); local_cases.append(row)
            gate_rows.append(dict(scheme=name, gene_key=case['gene_key'], symbol=case['symbol'],
                in_historical_universe=inside, score_pass=inside and bool(scores[i] >= .7),
                count3_pass=inside and bool(counts[i] >= 3), count4_pass=inside and bool(counts[i] >= 4),
                direct_gate=inside and bool(extras['direct_gate'][i]),
                animal_gate=inside and q75 is not None and bool(values[i,4] >= q75),
                animal_q75=q75, high=inside and bool(high[i]),
                high_count4=inside and bool(scores[i] >= .7 and counts[i] >= 4 and signal[i]),
                high_fixed_production_threshold=inside and bool(scores[i] >= .7 and counts[i] >= 3 and
                    (extras['direct_gate'][i] or values[i,4] >= .12765713253595054))))
        groups = {'strong_novel_all': [r for r in local_cases if r['clinical_status'] == 'strong_novel_target']}
        for status in sorted({r['clinical_status'] for r in local_cases}):
            groups[f'status:{status}'] = [r for r in local_cases if r['clinical_status'] == status]
        for control_group in sorted({r['control_group'] for r in local_cases if r['control_group']}):
            groups[f'previously_inspected_control:{control_group}'] = [r for r in local_cases if r['control_group'] == control_group]
        strong = groups['strong_novel_all']
        for field in ('novelty', 'mechanism'):
            for value in sorted({r[field] for r in strong if r[field]}):
                groups[f'{field}:{value}'] = [r for r in strong if r[field] == value]
        for domain in sorted({d for r in strong for d in r['domains'].split('|') if d}):
            groups[f'domain:{domain}'] = [r for r in strong if domain in r['domains'].split('|')]
        for group, members in groups.items():
            for denominator_kind in ('historical_universe', 'all_clinically_eligible', 'scored_subset_descriptive'):
                subset = [r for r in members if denominator_kind == 'all_clinically_eligible' or
                          (r['in_historical_universe'] if denominator_kind == 'historical_universe' else r['scored'])]
                outcomes = ['high'] + [f'top{k}' for k in TOPK] + [f'top{p}pct' for p in (1,5,10)]
                for endpoint in outcomes:
                    variants = [''] if endpoint == 'high' else ['', '_tie_inclusive', '_whole_tie_above_boundary']
                    for suffix in variants:
                        wins = sum(r[endpoint+suffix] for r in subset)
                        lower, upper = wilson(wins, len(subset))
                        summaries.append(dict(scheme=name, stratum=group, denominator_kind=denominator_kind,
                            endpoint=endpoint+suffix, recovered=wins, denominator=len(subset),
                            recall=wins/len(subset) if subset else None, wilson95_lower=lower, wilson95_upper=upper,
                            total_clinically_eligible=len(members), in_universe=sum(r['in_historical_universe'] for r in members),
                            scored=sum(r['scored'] for r in members)))
    comparisons = []
    for reference in PRIMARY:
        for name, scores in all_scores.items():
            shared = np.isfinite(scores) & np.isfinite(all_scores[reference])
            rho = spearmanr(scores[shared], all_scores[reference][shared]).statistic if shared.sum() > 1 else None
            for k in TOPK:
                left = set(ids[all_ranks[reference]['position'] <= k])
                right = set(ids[all_ranks[name]['position'] <= k])
                comparisons.append(dict(reference=reference, scheme=name, shared_scored=int(shared.sum()),
                    reference_scored=int(np.isfinite(all_scores[reference]).sum()),
                    scheme_scored=int(np.isfinite(scores).sum()),
                    spearman_rho=rho, topk=k, shared_topk=len(left & right),
                    reference_topk=len(left), scheme_topk=len(right), union_topk=len(left | right)))
    # Shared unchanged components must reproduce the independently frozen pilot.
    pilot = BASE.parent / 'temporal_extension/results/historical_components.tsv'
    with pilot.open() as handle:
        pilot_rows = {r['gene_id']: r for r in csv.DictReader(handle, delimiter='\t')}
    for i, gid in enumerate(ids):
        for j, layer in [(0, 'gnomad'), (2, 'annotation'), (3, 'localization')]:
            value = pilot_rows[gid][f'{layer}_score']
            expected = float(value) if value not in ('', 'NA', 'None', 'null') else np.nan
            if not np.isclose(matrix[i,j], expected, rtol=1e-12, atol=1e-12, equal_nan=True):
                raise ValueError(f'Unchanged pilot component differs: {gid}/{layer}')
    for path, expected in protected.items():
        if digest(ROOT / path) != expected:
            raise ValueError(f'Protected baseline changed: {path}')
    args.output_dir.mkdir(parents=True)
    tables = dict(historical_components=components, historical_primary_rankings=rankings,
        case_rankings=case_rows, recovery=summaries, case_gate_failures=gate_rows,
        scheme_comparisons=comparisons, source_coverage=coverage,
        animal_source_details=extras['animal_rows'], literature_source_details=extras['literature_rows'])
    for name, rows in tables.items():
        write_table(args.output_dir / f'{name}.tsv', rows)
    manifest = dict(freeze_commit=args.freeze_commit, freeze_sha256=digest(args.freeze), population=len(genes),
        duplicate_historical_identifier_rows_excluded=excluded, source_audit=audit, schemes=scheme_audit,
        protected_unchanged=True, unchanged_pilot_components_reproduced=True,
        postcutoff_case_literature_leakage_checked=True, clinical_specificity_estimated=False,
        output_sha256={p.name:digest(p) for p in sorted(args.output_dir.glob('*.tsv'))},
        code_sha256={str(p.relative_to(ROOT)):digest(p) for p in
            [Path(__file__), ROOT/'scripts/revision_temporal_v2_reconstruct.py']})
    (args.output_dir / 'manifest.json').write_text(json.dumps(clean(manifest), indent=2)+'\n')
    print(json.dumps(clean(manifest), indent=2))


if __name__ == '__main__':
    main()

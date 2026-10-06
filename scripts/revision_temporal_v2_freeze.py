"""Close selection decisions and hash inputs before any v2 outcome calculation.

Run only after reviewing the assembled draft. Selection closure records the
chosen cohort, not proof that every catalog gene has been clinically resolved.
"""
import json
import platform
from pathlib import Path
from revision_phase2 import digest
from revision_temporal_v2_evaluate import validate_roster
from revision_temporal_v2_reconstruct import ROOT, BASE


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')


def main():
    if (BASE/'results').exists() or (BASE/'freeze.json').exists():
        raise FileExistsError('Do not overwrite an existing freeze or outcomes')
    cohort = BASE/'cohort_screening'
    roster = json.loads((cohort/'clinical_roster_draft.json').read_text())
    validate_roster(roster['records'])
    unresolved = ('requires_target_confirmation', 'without_accepted_postcutoff_nomination')
    for row in roster['records']:
        row.pop('adjudication_status', None)
        row['selection_decision_status'] = 'closed'
        row['clinical_evidence_status'] = ('not_fully_adjudicated; retained ascertainment uncertainty'
            if any(s in row['clinical_status'] for s in unresolved) else
            'reviewed selection classification; see cited evidence and uncertainty')
    roster.update(status='frozen_before_v2_outcomes', scores_read=False,
                  scope='Conditional recovery in independently ascertained qualifying cases; not exhaustive discovery or specificity validation.')
    save(cohort/'clinical_roster.json', roster)
    references = json.loads((cohort/'adjudication_reference_index_draft.json').read_text())
    references['status'] = 'frozen_before_v2_outcomes'
    save(cohort/'adjudication_reference_index.json', references)
    inventory = json.loads((BASE/'source_inventory_draft.json').read_text())
    inventory['status'] = 'frozen_before_v2_outcomes'
    save(BASE/'source_inventory.json', inventory)
    protocol = (BASE/'PROTOCOL_DRAFT.md').read_text()
    start = protocol.index('## Question and temporal boundary')
    protocol = ('# Expanded temporal validation protocol — frozen before outcomes\n\n'
        'Status: sources, implementation and selection decisions are frozen before any v2 score/rank/recovery calculation. '
        'The freeze commit records that ordering. The original pilot and conservative Phase4 revision are preserved.\n\n'
        'The adopted ascertainment contains 1,081 catalog keys plus 11 previously inspected reference controls. '
        'The principal cohort is 45 strong later target associations. There are 18 exploratory candidates and '
        'three unresolved-novelty cases; none are promoted after observing results. '
        'The 358 historical curated and 96 historical RetNet records still requiring target confirmation, '
        'and 441 records without an accepted later nomination, retain clinical uncertainty. '
        'Their exclusion is a fixed selection decision, not confirmation of clinical absence. '
        'Broad searches completed for 682 non-historical-green keys (57,153 records), but nomination filters '
        'and unavailable full texts can miss associations. Out-of-catalog cases are not added ad hoc. '
        'Accordingly, recovery is conditional on this ascertained positive cohort, not an exhaustive census '
        'of all later disease genes.\n\n'
        'First-publicity intervals are retained for CREB3 (2024-05-01 to 2025-07-17), '
        'MRPL49 (2022-01-01 to 2024-10-11) and TMEM72 (2021-01-01 to 2022-04-30). '
        'They bound identified post-cutoff evidence without inventing exact thesis or conference release days. '
        'DAP3, LETM1 and TBX2 remain unresolved-novelty cases outside the principal cohort.\n\n'
        + protocol[start:])
    (BASE/'PROTOCOL.md').write_text(protocol)
    files = set((ROOT/'src/usher_pipeline').rglob('*.py'))
    files.update((ROOT/'scripts').glob('revision*.py'))
    files.update(p for p in BASE.rglob('*') if p.is_file() and p.name not in ('freeze.json', 'STATUS.md'))
    files.update((ROOT/'pyproject.toml', ROOT/'revision/major_revision_20261006/input_manifest.json',
                  ROOT/'revision/major_revision_20261006/temporal_extension/results/historical_components.tsv'))
    for e in inventory['entries']:
        files.update((ROOT/e['path'], ROOT/e['provenance_manifest']))
    # Preserve adopted search pages rather than obsolete failed/generic-alias attempts.
    broad = json.loads((cohort/'broad_target_search_manifest.json').read_text())
    files.update(ROOT/p['path'] for request in broad['requests'] for p in request['pages'])
    cache = ROOT/'data/cache/temporal-validation-v2-20261006'
    for folder in ('catalogs', 'clinical_search', 'human_screen', 'precutoff_human_screen', 'clinical_fulltext'):
        files.update(p for p in (cache/folder).rglob('*') if p.is_file() and p.suffix in ('.json', '.xml'))
    for r in references['references'].values():
        files.update(ROOT/p for p in r['metadata_source_paths'])
        if r.get('primary_xml_path'):
            files.add(ROOT/r['primary_xml_path'])
    manifest = dict(status='frozen_before_v2_outcomes', scores_read=False,
        clinical_roster_path=str((cohort/'clinical_roster.json').relative_to(ROOT)),
        reference_index_path=str((cohort/'adjudication_reference_index.json').relative_to(ROOT)),
        protocol_path=str((BASE/'PROTOCOL.md').relative_to(ROOT)),
        source_inventory_path=str((BASE/'source_inventory.json').relative_to(ROOT)),
        environment_lock_path=str((BASE/'requirements.lock.txt').relative_to(ROOT)),
        python_version=platform.python_version(), execution_location='local macOS arm64; single process, sparse retinal matrices',
        raw_storage='Local ignored cache retained with SHA256; Git manifests are not off-machine raw-data backups.',
        files={str(p.relative_to(ROOT)):digest(p) for p in sorted(files)})
    save(BASE/'freeze.json', manifest)
    print(json.dumps(dict(files=len(files), principal=45, clinical_decisions=len(roster['records']), raw_entries=len(inventory['entries']))))


if __name__ == '__main__':
    main()

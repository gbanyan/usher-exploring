"""Package derived revision evidence and verify actual delivered artifact hashes.

Requires completed DOCX/PDF rendering. Does not include live databases, original
raw caches, credentials or virtual environments. ZIP entries use repository paths.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / 'revision/major_revision_20261006'
OUT = ROOT / 'submission/bmc_bioinformatics_major_revision_20261007'
ARCHIVE_DATE = (2026, 10, 7, 0, 0, 0)


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def files_under(paths):
    found = set()
    for path in paths:
        if path.is_file():
            found.add(path)
        elif path.is_dir():
            found.update(p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
        else:
            raise FileNotFoundError(path)
    return sorted(found)


def archive(path, files, readme):
    entries = []
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        contents = [('README.txt', readme.encode())]
        for file in files:
            data = file.read_bytes()
            relative = str(file.relative_to(ROOT))
            contents.append((relative, data))
            entries.append({'path': relative, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
        contents.append(('BUNDLE_MANIFEST.json', (json.dumps(entries, indent=2) + '\n').encode()))
        for name, data in contents:
            info = zipfile.ZipInfo(name, ARCHIVE_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, data)
    write_json(path.with_suffix('.entries.json'), entries)


def verify(out):
    manifest = json.loads((out / 'package_manifest.json').read_text())
    for name, metadata in manifest['artifacts'].items():
        if sha(out / name) != metadata['sha256']:
            raise ValueError(f'Artifact checksum mismatch: {name}')
    additional = json.loads((out / 'Additional_file_10_Checksum_Manifest.json').read_text())
    for name, metadata in additional['files'].items():
        if sha(out / name) != metadata['sha256']:
            raise ValueError(f'Additional-file checksum mismatch: {name}')
    archive_entries = 0
    for path in out.glob('Additional_file_*.zip'):
        with zipfile.ZipFile(path) as bundle:
            if bundle.testzip() is not None:
                raise ValueError(f'ZIP CRC failure: {path}')
            entries = json.loads(bundle.read('BUNDLE_MANIFEST.json'))
            for entry in entries:
                if hashlib.sha256(bundle.read(entry['path'])).hexdigest() != entry['sha256']:
                    raise ValueError(f'ZIP entry checksum mismatch: {entry["path"]}')
                archive_entries += 1
    print(json.dumps({'actual_artifacts_verified': len(manifest['artifacts']),
                      'additional_files_verified': len(additional['files']),
                      'archive_entries_verified': archive_entries,
                      'package_self_hash_excluded': True}, indent=2))


def main():
    global ARCHIVE_DATE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=OUT)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--created-date', default='2026-10-07')
    parser.add_argument('--include-go', action='store_true')
    args = parser.parse_args()
    out = args.output_dir
    ARCHIVE_DATE = (*map(int, args.created_date.split('-')), 0, 0, 0)
    if args.verify_only:
        verify(out)
        return
    shared = files_under([ROOT / 'src', ROOT / 'scripts', ROOT / 'config', ROOT / 'pyproject.toml', ROOT / 'README.md'])
    common_readme = ('Extract at a repository root or preserve these repository-relative paths. '
        'No live database, virtual environment, credentials or large third-party raw archives are distributed. '
        'ZIP BUNDLE_MANIFEST.json lists exact payload bytes; it excludes itself and README.txt.\n')
    guards = json.loads((REV / 'input_manifest.json').read_text())['input_sha256']
    guard_files = [ROOT / name for name in guards if name not in ('data/pipeline.duckdb', 'manuscript/draft.md')]
    diagnostic = files_under([REV / name for name in (
        'analysis_spec.md', 'input_manifest.json', 'baseline', 'results', 'phase2_report.md',
        'phase3_spec.md', 'phase3_roster', 'phase3_results', 'phase3_report.md',
        'phase4_spec.md', 'phase4_results', 'phase4_report.md', 'replay_inputs',
        'reproducibility', 'temporal_extension')])
    archive(out / 'Additional_file_11_Revision_Diagnostics_and_Replay.zip',
        sorted(set(shared + diagnostic + guard_files + [REV / "phase5_claude_review/embedded_compendium_overlap.tsv"])), common_readme +
        '\nStart with revision/major_revision_20261006/reproducibility/README.md. '
        'Production numerical replay builds a task-owned DuckDB from four derived TSVs; '
        '28 numerical TSVs were byte-identical in clean replay. The original source acquisition '
        'and cached mantis-ml training run are not recreated. Phase4 omission diagnostics '
        'are post-outcome sensitivities. The preserved pilot is not the expanded temporal assessment.\n')
    temporal = files_under([REV / 'temporal_validation_v2'])
    pmids = sorted((ROOT / 'data/cache/temporal-validation-v2-20261006/literature_date_sorted').glob('*_pmids.txt.gz'))
    if len(pmids) != 6:
        raise ValueError('Expected six frozen context PMID sets')
    archive(out / 'Additional_file_12_Temporal_Evaluation.zip',
        sorted(set(shared + temporal + pmids + [REV / 'final_review_20261019/HUMAN_REVIEW_SUMMARY.md'])), common_readme +
        '\nStart with temporal_validation_v2/OUTCOME_REPORT.md and PROTOCOL.md under the revision directory. '
        'The six date-bounded context PMID sets are included without paper text. '
        'The full raw reconstruction command requires all recorded raw and clinical cache bytes, '
        'the original Git freeze checkpoints and the pinned analysis environment; this ZIP alone '
        'does not guarantee complete offline raw-source regeneration or clinical re-adjudication. '
        'Clinical search/full-text caches are not bundled.\n'
        'A dated post-analysis human-review summary is included at revision/major_revision_20261006/final_review_20261019/HUMAN_REVIEW_SUMMARY.md. The complete working author-review form is not included.\n'
        'For an archive-only numerical check in the analysis environment, run:\n'
        'python scripts/revision_temporal_derived_replay.py\n'
        'This verifies all 38,334 co-primary score/count/rank rows from derived components, '
        'but not HIGH raw source flags or the alternative global expression vectors. '
        'All 23 scheme case outcomes and endpoint summaries are provided. '
        'Initial 45-case clinical/date ascertainment was AI-assisted. Subsequent human author review covered primary reports and reported family/pedigree evidence for all cases after the frozen analysis. Eligibility concerns involving PDIA6, VWA8 and PLCG1 remain under review; no new human-approved cohort or revised outcome is asserted. Frozen labels are selection categories, not proof of clinical truth. The principal results are weak (top100/HIGH 0/41 and 0/45). '
        'Frozen OUTCOME_REPORT.md and independent_adjudication_20261006.json preserve earlier AI-agent screening wording and are not human adjudication records. '
        'These historical analogues are not prospective independent clinical validation.\n')
    if args.include_go:
        go = files_under([REV / 'go_classification_20261019'])
        outputs = [ROOT / 'outputs/temporal-go-classification-20261019' / name for name in (
            'Temporal_GO_Classification_20261019.xlsx',
            'Temporal_GO_Functional_Overview_20261019.pdf',
            'Temporal_GO_Functional_Overview_20261019.png',
            'Temporal_GO_Functional_Overview_20261019.svg')]
        archive(out / 'Additional_file_13_Temporal_GO_Classification.zip', sorted(set(shared + go + outputs + [ROOT / 'tests/test_revision_go.py'])), common_readme +
            '\nStart with revision/major_revision_20261006/go_classification_20261019/REPORT.md. '
            'Figure S1 is the Temporal_GO_Functional_Overview figure. The XLSX has seven sheets; TSVs provide complete annotations, categories and all 24,597 enrichment tests. '
            'No analysis passes pooled BH FDR < 0.05. This contemporary functional description was added after temporal outcomes and changes no historical score or clinical eligibility. '
            'Raw GOA/QuickGO/HGNC caches are not bundled; source manifests identify them. Source reconstruction requires those bytes. '
            'The full working human clinical-review form is not included.\n')
    additional = {}
    for path in sorted(out.glob('Additional_file_*')):
        if path.suffix == '.json' and path.name.endswith('.entries.json'):
            continue
        if path.name == 'Additional_file_10_Checksum_Manifest.json':
            continue
        additional[path.name] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    if len(additional) != (12 if args.include_go else 11):
        raise ValueError(f'Unexpected additional files: {list(additional)}')
    write_json(out / 'Additional_file_10_Checksum_Manifest.json', {
        'algorithm': 'SHA-256', 'scope': 'Actual delivered additional files 1-9 and 11-' + ('13' if args.include_go else '12'),
        'self_hash_excluded': True, 'files': additional})
    sources = [ROOT / 'manuscript/draft.md', ROOT / 'manuscript/supplementary_methods.md',
               REV / 'rebuttal.md', REV / 'cover_letter_revision.md']
    artifacts = {}
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name not in ('package_manifest.json', 'package_verification.json'):
            artifacts[str(path.relative_to(out))] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    write_json(out / 'package_manifest.json', {
        'algorithm': 'SHA-256', 'created_date': args.created_date,
        'source_base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_base_commit_is_not_a_claim_of_clean_worktree': True,
        'preserved_prior_author_review_release_tag': 'major-revision-author-review-20261007',
        'current_author_review_release_tag': 'major-revision-author-review-' + args.created_date.replace('-', ''),
        'exact_source_hashes': {str(p.relative_to(ROOT)): sha(p) for p in sources},
        'analysis_checkpoint': '736e16f', 'temporal_original_freeze': 'bd6bb2f',
        'temporal_amended_freeze': '53da295',
        'production_database_sha256': sha(ROOT / 'data/pipeline.duckdb'),
        'rendering': 'Pandoc to editable DOCX; python-docx styles; LibreOffice via render_docx.py; local macOS',
        'self_hash_excluded': True, 'artifacts': artifacts})
    verify(out)


if __name__ == '__main__':
    main()

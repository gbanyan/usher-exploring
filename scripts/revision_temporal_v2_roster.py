"""Assemble a reviewable roster from manual adjudication; never inspect scores.

Unnominated catalog genes remain ascertainment limitations, not clinical negatives.
This draft assembly does not itself freeze or approve the scientific decisions.
"""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from revision_temporal_v2_cohort import ROOT, BASE

sys.path.insert(0, str(ROOT / 'src'))
from usher_pipeline.scoring.known_genes import ESTABLISHED_USHER_GENES, SYSCILIA_SCGS_V2_CORE
from usher_pipeline.scoring.negative_controls import HOUSEKEEPING_GENES_CORE

CACHE = ROOT / 'data/cache/temporal-validation-v2-20261006'


def metadata():
    papers, sources = {}, {}
    paths = [*(CACHE/'catalogs').glob('*reference*json'), *(CACHE/'clinical_search').glob('*.json')]
    manifest = json.loads((BASE/'cohort_screening/broad_target_search_manifest.json').read_text())
    paths += [ROOT/page['path'] for request in manifest['requests'] for page in request['pages']]
    for path in sorted(set(paths)):
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            continue
        for paper in data.get('resultList', {}).get('result', []):
            key = (paper['source'], paper['id'])
            papers[key] = paper
            sources.setdefault(key, []).append(str(path.relative_to(ROOT)))
    return papers, sources


def reference(paper, source_paths):
    result = {k: paper.get(k) for k in ('source', 'id', 'pmcid', 'doi', 'title', 'firstPublicationDate', 'electronicPublicationDate', 'firstIndexDate')}
    result['metadata_source_paths'] = source_paths
    path = CACHE/'clinical_fulltext'/f"{paper.get('pmcid')}.xml"
    if path.exists():
        result['primary_xml_path'] = str(path.relative_to(ROOT))
        result['primary_xml_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        dates = []
        for node in ET.parse(path).getroot().findall('./front/article-meta/pub-date'):
            year, month, day = node.findtext('year'), node.findtext('month'), node.findtext('day')
            if year and month and day:
                try:
                    dates.append(f'{int(year):04d}-{int(month):02d}-{int(day):02d}')
                except ValueError:
                    pass
        result['primary_publication_dates'] = sorted(set(dates))
    return result


def main():
    base = BASE/'cohort_screening'
    genes = json.loads((base/'gene_screening_ledger.json').read_text())
    notes = json.loads((base/'adjudication_notes_draft.json').read_text())['records']
    papers, sources = metadata()
    references = {}
    rows = []
    controls = {'usher': ESTABLISHED_USHER_GENES, 'syscilia': SYSCILIA_SCGS_V2_CORE,
                'housekeeping': HOUSEKEEPING_GENES_CORE}
    with (ROOT/'data/cache/temporal-extension-20261006/raw/hgnc_20201001.tsv').open() as handle:
        archived = list(csv.DictReader(handle, delimiter='\t'))
    historical = {g['hgnc_id']: g for g in archived if g['status'] == 'Approved'}
    for gene in genes:
        matching = [n for n in notes if n['symbol'] in gene['symbols'] or n.get('historical_symbol') in gene['symbols']]
        if len(matching) > 1:
            raise ValueError(f"Conflicting manual decisions: {gene['gene_key']}")
        row = dict(gene_key=gene['gene_key'], symbol=gene['symbols'][0] if gene['symbols'] else gene['gene_key'], catalog_symbols=gene['symbols'],
                   source_records=gene['records'], adjudication_status='draft',
                   clinical_status='screened_without_accepted_postcutoff_nomination',
                   decision_reason='No manually established qualifying later association in the adopted screening; not evidence of clinical absence.')
        if gene['precutoff_green_records']:
            row.update(clinical_status='historical_curated_reference_requires_target_confirmation',
                       decision_reason='Archived green human clinical record; target-scope confirmation retained in original ledger, not automatically a clinical negative.')
        elif gene['precutoff_clinical_references']:
            row.update(clinical_status='historical_retnet_reference_requires_target_confirmation',
                       decision_reason='Precutoff curated retinal reference, which may include candidate/risk evidence; excluded from unambiguous first-target nominations.')
        if matching:
            note = matching[0]
            row.update(note)
            row['clinical_status'] = 'candidate_novelty_unresolved'
            proposed = note['proposed_status']
            if proposed.startswith('strong'):
                row['clinical_status'] = 'strong_novel_target'
            elif proposed.startswith('candidate') or proposed == 'clinical_strength_requires_resolution':
                row['clinical_status'] = 'candidate_novel_target'
            elif proposed.startswith('precutoff') or proposed == 'evidence_maturation':
                row['clinical_status'] = 'evidence_maturation'
            elif proposed == 'phenotype_expansion':
                row['clinical_status'] = 'phenotype_expansion'
            elif proposed.startswith('outside_primary_scope'):
                row['clinical_status'] = 'scope_comparison'
            row['novelty'] = note.get('novelty', 'B' if 'prior_other' in proposed else 'A' if proposed.startswith(('strong', 'candidate')) else 'U')
            row['domains'] = note.get('domains') or [d for d in ('hearing', 'retinal', 'optic', 'primary_cilia', 'motile_cilia')
                                                       if d in note.get('domain', '')]
            row['mechanism'] = note.get('mechanism', 'ciliary' if 'cilia' in note.get('domain', '') else 'not_established_as_ciliary')
            # Preserve source-specific counts; a conservative lower bound does
            # not assume all neurological families have the target phenotype.
            row['reported_unrelated_families_all_phenotypes'] = note.get('unrelated_families')
            row['unrelated_target_families_lower_bound'] = note.get('unrelated_target_families_lower_bound',
                2 if row['clinical_status'] == 'strong_novel_target' and note.get('unrelated_families', 0) and note['unrelated_families'] >= 2 else note.get('unrelated_target_families', 0))
            clinical_ids = list(dict.fromkeys(note.get('clinical_pmids', []) + note.get('independent_replication_pmids', []) +
                            ([note['independent_replication_pmid']] if note.get('independent_replication_pmid') else [])))
            row['clinical_pmids'] = clinical_ids
            row['postcutoff_association_pmids'] = [p for p in clinical_ids if papers.get(('MED', p), {}).get('firstPublicationDate', '') > '2020-12-31']
            row['reference_keys'] = []
            for pmid in clinical_ids + note.get('supporting_functional_pmids', []):
                key = ('MED', pmid)
                if key in papers:
                    references[f'MED:{pmid}'] = reference(papers[key], sources[key])
                    row['reference_keys'].append(f'MED:{pmid}')
            date = note.get('first_verified_target_date')
            if not date and row['postcutoff_association_pmids']:
                pub_dates = []
                for pmid in row['postcutoff_association_pmids']:
                    r = references[f'MED:{pmid}']
                    pub_dates += r.get('primary_publication_dates', []) + [r['firstPublicationDate']]
                    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', r.get('electronicPublicationDate') or ''):
                        pub_dates.append(r['electronicPublicationDate'])
                date = min(pub_dates)
            if date:
                # Exact first-publicity cannot be inferred from an issue date.
                # This is a provisional interval, finalized through human review.
                row['earliest_located_publication_date'] = date
                row['target_public_date_interval'] = [date[:4]+'-01-01', date if len(date) == 10 else date[:4]+'-12-31']
            if note.get('target_public_date_interval'):
                row['target_public_date_interval'] = note['target_public_date_interval']
            row['qualifying_functional_evidence'] = note.get('qualifying_functional_evidence')
            row['decision_reason'] = note['evidence_summary']
        for group, symbols in controls.items():
            if set(gene['symbols']) & symbols or historical.get(gene['gene_key'], {}).get('symbol') in symbols:
                row.update(clinical_status='development_reference', control_group=group, novelty=None)
        if set(gene['symbols']) & {'CEP162', 'CFAP20', 'LRRC45'}:
            row.update(clinical_status='pilot_reference', novelty=None,
                       decision_reason='Previously inspected pilot case; never principal independent validation.')
        rows.append(row)
    missing_controls = [(group, s) for group, symbols in controls.items() for s in symbols
                        if not any(r.get('control_group') == group and s in r['catalog_symbols'] for r in rows)]
    for group, symbol in missing_controls:
        match = [g for g in archived if g['status'] == 'Approved' and g['symbol'] == symbol]
        if len(match) != 1:
            raise ValueError(f'Unmapped reference control: {symbol}')
        rows.append(dict(gene_key=match[0]['hgnc_id'], symbol=symbol, catalog_symbols=[symbol], source_records=[],
                         clinical_status='development_reference', control_group=group, novelty=None, domains=[],
                         adjudication_status='draft', decision_reason='Previously inspected production control; outside ascertainment catalog if absent.'))
    # Preserve every catalog key, and explicitly append out-of-catalog controls.
    if len({r['gene_key'] for r in rows}) != len(rows):
        raise ValueError('Duplicate assembled gene keys')
    output = dict(status='draft_for_preoutcome_review', scores_read=False,
                  catalog_gene_keys=len(genes), appended_reference_controls=len(missing_controls),
                  classification_counts=dict(Counter(r['clinical_status'] for r in rows)), records=rows)
    (base/'clinical_roster_draft.json').write_text(json.dumps(output, indent=2)+'\n')
    (base/'adjudication_reference_index_draft.json').write_text(json.dumps(dict(status='draft', references=references), indent=2)+'\n')
    print(json.dumps({k:v for k,v in output.items() if k != 'records'}))


if __name__ == '__main__':
    main()

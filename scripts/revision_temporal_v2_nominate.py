"""Prepare readable nomination dossiers, never accept/exclude cases automatically."""
import json
from pathlib import Path
import re
from revision_temporal_v2_cohort import ROOT, BASE

CACHE = ROOT / 'data/cache/temporal-validation-v2-20261006'


def main():
    base = BASE / 'cohort_screening'
    genes = {g['gene_key']: g for g in json.loads((base/'gene_screening_ledger.json').read_text())}
    requests = {g['gene_key']: g for g in json.loads((base/'standardized_screen_requests.json').read_text())}
    notes = {r['symbol'] for r in json.loads((base/'adjudication_notes_draft.json').read_text())['records']}
    records = {}
    manifest = json.loads((base/'broad_target_search_manifest.json').read_text())
    if not all(r['complete'] for r in manifest['requests']):
        raise ValueError('Broad screening is incomplete')
    for request in manifest['requests']:
      key = request['gene_key']
      for page in request['pages']:
        file = ROOT / page['path']
        if set(genes[key]['symbols']) & notes:
            continue
        spellings = [s for s in requests[key]['symbols'] if s not in {'ALL', 'LARGE', 'GAP', 'AT-1'}]
        pattern = r'(?<![A-Za-z0-9])(?:'+ '|'.join(re.escape(s) for s in spellings) + r')(?![A-Za-z0-9])'
        for paper in json.loads(file.read_text())['resultList']['result']:
            title, abstract = paper.get('title', ''), paper.get('abstractText', '')
            if (paper.get('firstPublicationDate', '') > '2020-12-31' and re.search(pattern, title, re.I)
                and re.search(r'caus|variants|mutations|biallelic|bi-allelic|loss-of-function', title, re.I)
                and re.search(r'famil|patient|proband|individual', abstract, re.I)
                and not re.search(r'review|meta-analysis', title, re.I)):
                records[(key, paper['source'], paper['id'])] = dict(gene_key=key,
                    symbols=genes[key]['symbols'], source=paper['source'], id=paper['id'],
                    title=title, date=paper.get('firstPublicationDate'), abstract=abstract,
                    source_path=str(file.relative_to(ROOT)))
    rows = sorted(records.values(), key=lambda r:(r['symbols'], r['date'], r['id']))
    output = CACHE/'probes/broad_clinical_nomination_draft.json'
    output.write_text(json.dumps(dict(status='nomination only; requires human adjudication',
        gene_title_filter_can_miss_multigene_reports=True, scores_read=False, records=rows), indent=2)+'\n')
    print(json.dumps(dict(records=len(rows), gene_keys=len({r['gene_key'] for r in rows}), output=str(output))))
    print(json.dumps([dict(symbols=r['symbols'], id=r['id'], date=r['date'], title=r['title']) for r in rows], indent=2))


if __name__ == '__main__':
    main()

"""Locate revised sections in the actual PDFs and annotate the 23 responses.

Run in the task-owned document environment after final main/supplement rendering.
This mutates only rebuttal.md and the generated page-location index.
"""
from pathlib import Path
import argparse
import csv
import re
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / 'revision/major_revision_20261006'
OUT = ROOT / 'submission/bmc_bioinformatics_major_revision_20261007'
LOCATIONS = {
    'R1-major-1': (['Abstract', 'Usher syndrome as a specialized sensory ciliopathy', 'Internal control recovery', 'Conclusions'], ['S4. Control traces']),
    'R1-major-2': (['Abstract', 'NULL-aware composite scoring', 'Retrospective evaluation of historical analogues', 'Retrospective temporal evaluation', 'Limitations'], ['S3. Implemented', 'S6. Retrospective']),
    'R1-major-3': (['Internal control recovery'], ['S4. Control traces']),
    'R1-major-4': (['Negative controls', 'Matched unrelated-disease comparators', 'Limitations'], ['S5. Frozen']),
    'R1-major-5': (['NULL-aware composite scoring', 'Sensitivity analysis'], ['S2. Data-driven', 'S4. Control traces']),
    'R1-major-6': (['Impact of missing data handling', 'Sensitivity analysis'], ['S4. Control traces', 'S6. Retrospective']),
    'R1-major-7': (['Evidence layers', 'Sensitivity analysis'], ['S3. Implemented', 'S4. Control traces', 'S5. Frozen']),
    'R1-major-8': (['Sensitivity analysis', 'Retrospective temporal evaluation', 'Comparison with mantis-ml'], ['S4. Control traces', 'S6. Retrospective']),
    'R1-major-9': (['Reproducibility', 'Availability of data and materials', 'Additional files'], ['S7. Numerical replay']),
    'R1-major-10': (['Expression dependence', 'Limitations'], ['S1. Optional', 'S3. Implemented']),
    'R1-minor-1': (['Abstract', 'NULL-aware composite scoring'], ['S3. Implemented']),
    'R1-minor-2': (['NULL-aware composite scoring', 'Internal control recovery'], ['S3. Implemented']),
    'R1-minor-3': (['Gene universe'], ['S1. Optional']),
    'R1-minor-4': (['Internal control recovery'], ['S4. Control traces']),
    'R1-minor-5': (['Figure 5. Internal control recovery'], ['S7. Numerical replay']),
    'R1-minor-6': (['Availability of data and materials'], ['S7. Numerical replay']),
    'R1-minor-7': (['Usher syndrome as a specialized sensory ciliopathy', 'Ciliary and stereociliary biology underlying Usher syndrome'], []),
    'R3-1': (['Usher syndrome as a specialized sensory ciliopathy'], []),
    'R3-2': (['NULL-aware composite scoring', 'Internal control recovery'], ['S3. Implemented', 'S5. Frozen', 'S6. Retrospective']),
    'R3-3': (['Sensitivity analysis'], ['S2. Data-driven', 'S4. Control traces']),
    'R3-4': (['Retrospective evaluation of historical analogues', 'Retrospective temporal evaluation', 'Limitations'], ['S6. Retrospective']),
    'R3-5': (['Expression dependence', 'Limitations'], ['S1. Optional', 'S3. Implemented']),
    'R3-6': (['Negative controls', 'Matched unrelated-disease comparators', 'Sensitivity analysis'], ['S3. Implemented', 'S4. Control traces', 'S5. Frozen']),
}


def page_numbers(name, anchor):
    doc = pymupdf.open(OUT / f'{name}.pdf')
    normal = lambda text: re.sub(r'\s+', ' ', text).strip().replace('’', "'")
    source = ROOT / ('manuscript/draft.md' if name == 'Manuscript' else 'manuscript/supplementary_methods.md')
    headings = []
    for line in source.read_text().splitlines():
        match = re.match(r'^(#{2,6}) (.+)$', line)
        figure = re.match(r'^\*\*(Figure \d+\.[^*]+)\*\*', line)
        if match:
            headings.append((len(match[1]), match[2], False))
        elif figure:
            headings.append((3, figure[1], True))
    lines = [(p+1, normal(''.join(s['text'] for s in line['spans'])))
             for p, page in enumerate(doc) for block in page.get_text('dict')['blocks']
             for line in block.get('lines', [])
             if line['bbox'][0] >= 45 and line['bbox'][1] < 760]
    located = []
    cursor = 0
    for level, heading, figure in headings:
        found = None
        for i in range(cursor, len(lines)):
            for length in (1, 2, 3):
                joined = normal(' '.join(t for _, t in lines[i:i+length]))
                if (joined.startswith(normal(heading)) if figure else joined == normal(heading)):
                    found = i
                    break
            if found is not None:
                break
        if found is None:
            raise ValueError(f'Heading not found in rendered PDF: {name} {heading}')
        located.append((level, heading, found))
        cursor = found + 1
    candidates = [(i, level, pos) for i, (level, heading, pos) in enumerate(located)
                  if heading.rstrip('.') == anchor or heading.startswith(anchor)
                  and anchor.startswith(('S1.', 'S2.', 'S3.', 'S4.', 'S5.', 'S6.', 'S7.'))]
    if not candidates:
        raise ValueError(f'No PDF location: {name} {anchor}')
    # Select the final Conclusions rather than its abstract subheading.
    i, level, pos = candidates[-1]
    end = next((next_pos for next_level, _, next_pos in located[i+1:] if next_level <= level), len(lines))
    start_page, end_page = lines[pos][0], lines[end-1][0]
    return str(start_page) if start_page == end_page else f'{start_page}–{end_page}'


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf-dir', type=Path, default=OUT)
    OUT = parser.parse_args().pdf_dir
    locations = {}
    rows = []
    for comment, groups in LOCATIONS.items():
        parts = []
        for document, anchors in zip(('Manuscript', 'Supplementary_Methods'), groups):
            for anchor in anchors:
                pages = page_numbers(document, anchor)
                rows.append({'comment_id': comment, 'document': document + '.pdf', 'section_anchor': anchor, 'pdf_pages': pages})
                parts.append(f'{document.replace("_", " ")} p. {pages} ({anchor})')
        locations[comment] = '; '.join(parts)
    with (OUT / 'Page_location_index.tsv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=['comment_id', 'document', 'section_anchor', 'pdf_pages'], delimiter='\t', lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    response = REV / 'rebuttal.md'
    text = re.sub(r'\n\*\*Revised PDF locations\.\*\*[^\n]*\n', '\n', response.read_text())
    chunks = re.split(r'(?=^### R[13]-)', text, flags=re.M)
    seen = set()
    for i in range(1, len(chunks)):
        comment = re.match(r'### (R(?:1-(?:major|minor)-\d+|3-\d+))\.', chunks[i]).group(1)
        if comment not in locations:
            raise ValueError(comment)
        seen.add(comment)
        # Append before the next reviewer-section heading, if present in this chunk.
        extra = f'\n\n**Revised PDF locations.** {locations[comment]}.\n\n'
        if '\n## Reviewer' in chunks[i]:
            chunks[i] = chunks[i].replace('\n## Reviewer', extra + '## Reviewer', 1)
        else:
            chunks[i] = chunks[i].rstrip() + extra
    if seen != LOCATIONS.keys():
        raise ValueError(f'Response/index mismatch: {seen ^ LOCATIONS.keys()}')
    response.write_text(re.sub(r'\n{3,}', '\n\n', ''.join(chunks)))
    print(f'Located all {len(seen)} comments in rendered PDFs; index has {len(rows)} section/page rows')


if __name__ == '__main__':
    main()

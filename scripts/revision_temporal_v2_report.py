"""Describe immutable temporal outcomes; never refit or change selection."""
import csv
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'revision/major_revision_20261006/temporal_validation_v2'
PRIMARY = ('archived_five', 'augmented_six')


def rows(name):
    with (BASE/'results'/f'{name}.tsv').open() as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def main():
    manifest = json.loads((BASE/'results/manifest.json').read_text())
    for name, expected in manifest['output_sha256'].items():
        assert hashlib.sha256((BASE/'results'/name).read_bytes()).hexdigest() == expected, name
    outcomes, cases, gates = rows('recovery'), rows('case_rankings'), rows('case_gate_failures')
    def result(scheme, endpoint, denominator='historical_universe', group='strong_novel_all'):
        matches = [r for r in outcomes if (r['scheme'], r['endpoint'], r['denominator_kind'], r['stratum']) ==
                   (scheme, endpoint, denominator, group)]
        assert len(matches) == 1
        return matches[0]
    def fraction(r):
        return f"{r['recovered']}/{r['denominator']} ({100*float(r['recall']):.1f}%)"
    text = ['# Expanded temporal validation: completed outcome report', '',
        'The historical analogues showed limited recovery of later human disease associations. '
        'Neither co-primary version recovered a principal case in the top 100 or HIGH tier. '
        'These results do not support a claim of reliable discovery of genuinely novel disease genes.', '',
        'This is a retrospective temporal stress test with pre-outcome case selection and source/implementation freeze. '
        'It is not a prospectively developed predictor: the original pipeline design and control-calibrated gate '
        'were developed after the historical cutoff. It also does not reproduce every modern production source.', '',
        '## Frozen design and execution', '',
        '- Historical evidence cutoff: 31 December 2020; later clinical ascertainment through 6 October 2026.',
        '- Original pre-outcome freeze: `bd6bb2f`; guarded GTEx identifier repair: `53da295`. '
        'The first attempt stopped before composite scores/ranks/HIGH/recall; '
        '44 canonical/PAR_Y pairs were conflated by version removal. '
        'The repair preserves PAR_Y identity, with no source/cohort/weight/gate changes. '
        'Original manifest and failure record remain available.',
        '- Principal cohort: 45 strong later target associations; 41 are in the 2020 protein-coding universe '
        'and all 41 are scored. RNU4-2, RNU6-2, RNU6-8 and RNU6-9 are outside that universe '
        'and count as nonrecoveries in the 45-case end-to-end denominator.',
        '- Exploratory candidates, unresolved novelty, phenotype expansion/maturation, previously inspected '
        'controls and three pilot cases remain separately labeled. None were promoted after outcomes.',
        '- Universe: 19,167 approved unique historical protein-coding ENSG identifiers. '
        'Five-layer: 19,157 scored, 10 NULL. Six-layer: 19,167 scored. '
        'The added observed literature zero can supply the sole observed family for an otherwise all-NULL gene.',
        '- Two co-primary versions plus 21 prespecified comparisons (23 schemes total). '
        'No control/case-fitted weights or threshold tuning.', '',
        '## Principal recovery', '',
        'Recovery counts use deterministic ENSG tie-breaking; tie-inclusive and whole-tie cutoff '
        'sensitivities are retained in `results/recovery.tsv`. The primary historical-universe '
        'denominator includes any unscored eligible case as a failure; none of these 41 cases were NULL.', '',
        '| Endpoint | Five layers, historical universe | Six layers, historical universe | Five layers, all eligible | Six layers, all eligible |',
        '|---|---:|---:|---:|---:|']
    for endpoint in ('top25','top50','top100','top500','top1000','top1pct','top5pct','top10pct','high'):
        text.append('| '+endpoint+' | '+' | '.join(fraction(result(s, endpoint, d))
                    for d in ('historical_universe', 'all_clinically_eligible') for s in PRIMARY)+' |')
    text.extend(['', 'The score percentile is ascending: a higher percentile indicates higher priority. '
        'The principal-case median percentile is '+
        ' / '.join(f'{statistics.median(float(r["percentile"]) for r in cases if r["scheme"]==s and r["clinical_status"]=="strong_novel_target" and r["scored"]=="True"):.2f}' for s in PRIMARY)+
        ' for five / six layers. This does not show broad high-rank enrichment of the later-case cohort.', '',
        'Top-1,000 cases: five layers TP73 (662) and PLCG1 (879); six layers PLCG1 (474), '
        'TP73 (629) and SAXO6 / historical MDM1 (646). PLCG1 belongs to first-target association '
        'after prior other-phenotype evidence (novelty B), not first-ever human gene-disease association.', '',
        '| Novelty stratum | Five-layer top 1,000 | Six-layer top 1,000 |', '|---|---:|---:|'])
    for group in ('novelty:A','novelty:B'):
        text.append('| '+group+' | '+' | '.join(fraction(result(s,'top1000',group=group)) for s in PRIMARY)+' |')
    text.extend(['', 'A denotes no earlier human causal report located in the adopted audit; '
        'this is not proof that no inaccessible or unindexed earlier report exists. B denotes a '
        'first target-domain association after prior other-phenotype evidence. ', '',
        '## HIGH and source coverage', '',
        'No principal case meets the raw score threshold 0.7 in either co-primary version. '
        'All 41 have at least four observed weighted evidence families. Therefore zero HIGH '
        'recovery cannot be attributed solely to the cilia gate or insufficient family count. '
        'One principal case has the direct HPA gate; three have the historical animal-Q75 gate. '
        'Count>=4 and the fixed original animal-threshold sensitivities also recover zero.', '',
        'Across the entire genome, historical HIGH counts are zero (five layers) and five (six layers). '
        'This scale is affected by partial annotation/localization channels and historical sources, '
        'and cannot be interpreted as a recalibration of the modern production tier.', '',
        '| Evidence family | Observed | Positive | Observed zero | NULL |', '|---|---:|---:|---:|'])
    for r in rows('source_coverage'):
        text.append('| '+' | '.join(r[k] for k in ('layer','observed','positive','observed_zero','missing'))+' |')
    text.extend(['', 'Within the 41 principal in-universe cases, constraint, expression and GO '
        'are all observed and positive. Localization is positive for two, observed zero for 29 '
        'and NULL for ten; animal is positive for 13 and observed zero for 28; literature is '
        'positive for 25 and observed zero for 16. The weak result cannot be described as '
        'all evidence being absent for the later cases.', '',
        'Mapped animal genes with no qualifying recorded sensory terms have observed zero; '
        'this is source evidence absence, not biological absence. Unknown-only terms are NULL. '
        'GO is the available partial annotation channel (maximum family score 0.5); '
        'annotation completeness does not establish disease specificity.', '',
        '## Prespecified sensitivities', '',
        '| Scheme | Top 100 | Top 1,000 | Top 10% | HIGH |', '|---|---:|---:|---:|---:|'])
    for scheme in manifest['schemes']:
        text.append('| '+scheme+' | '+' | '.join(fraction(result(scheme,e)) for e in ('top100','top1000','top10pct','high'))+' |')
    text.extend(['', 'The single-localization and localization-weight-omission schemes each recover '
        'one principal case in deterministic top 100: SAXO6 (position19, tied positions1–77) '
        'and PLCG1 (position90, untied), respectively. Both remain within top100 under the '
        'whole-tie boundary rule. These are prespecified sensitivity outcomes, '
        'not replacements for the co-primary analyses. Single-family ranks have substantial ties; '
        'consult the tie sensitivities before assigning a precise priority.', '',
        'Weight omissions retain both gate routes; the active-family count uses positive score weights. '
        'Animal source/mapping comparisons modify the animal gate input and recompute Q75. '
        'No principal case reaches HIGH under any of the 23 schemes.', '',
        'Five-versus-six-layer Spearman rank correlation is 0.870708 across 19,157 shared scored genes. '
        'Their full-ranking top 100 sets share 57 genes. This shows material ranking dependence on '
        'literature inclusion even when a global rank correlation appears fairly high.', '',
        '## Previously inspected references', '',
        'These groups were used or inspected in pipeline development. They are descriptive references, '
        'not independent new clinical validation or specificity controls.', '',
        '| Reference group | Five-layer top 100 | Six-layer top 100 | Five-layer top 1,000 | Six-layer top 1,000 |',
        '|---|---:|---:|---:|---:|'])
    for group in ('usher','syscilia','housekeeping'):
        text.append('| '+group+' | '+' | '.join(fraction(result(s,e,group='previously_inspected_control:'+group))
                    for e in ('top100','top1000') for s in PRIMARY)+' |')
    text.extend(['', '## Interpretation and remaining limits', '',
        'The expanded study directly addresses later-case recovery and produces a negative/weak result. '
        'The manuscript should state that control recovery supports capture of established biology, '
        'while broad generalization to genuinely novel disease genes remains unvalidated. '
        'These data cannot support clinical specificity, false-positive rate, precision, penetrance '
        'or calibrated disease-probability claims.', '',
        'Historical HCOP support votes and complete UniProt/pathway annotation were not recovered. '
        'Native species links, partial GO, original 2019 raw-UMI retinal matrices/author cell labels, '
        'GTEx v8 and ordinal HPA constitute an explicitly different historical analogue. '
        'The partial-GO rescale, alternative animal mappings/scales and retinal-platform/omission '
        'comparisons quantify selected source differences but do not prove equivalence to production. '
        'Absent direct cochlear hair-cell/developmental data may disadvantage restricted-expression genes.', '',
        'The six-layer literature version uses June2020 gene2pubmed links and public/index date-bounded '
        'PMID context sets, but the queried text is modern and can have later corrections. '
        'The five-layer version avoids that text uncertainty. Neither is a prospective historical deployment.', '',
        'Ascertainment is conditional on adopted RetNet/PanelApp catalogs and searches. '
        '358 historical curated and 96 historical RetNet records still requiring target confirmation, '
        'and 441 records without an accepted nomination, retain clinical uncertainty. '
        'They are not disease-specific negative controls or an exhaustive clinically resolved background. '
        'The 682 broad searches completed (57,153 records), but title/abstract nomination, '
        'missing full text, gene aliases and catalog scope can miss cases. Date intervals and unresolved '
        'DAP3/LETM1/TBX2 classifications are preserved before outcomes. ', '',
        'Wilson95 intervals in the output are descriptive uncertainty summaries within this nonrandom '
        'ascertained cohort, not population-level validation intervals. Domain strata overlap and '
        'must not be summed as independent cases. No post-outcome optimization was performed.', '',
        '## Reproducibility', '',
        'Executed locally on macOS arm64, Python3.13.1, using the exact installed lockfile. '
        'All 3,125 amended dependencies passed checksum/commit verification. '
        'The full test suite passed 354 tests (17 existing warnings). '
        'Shared unchanged constraint/GO/localization components reproduce the restricted pilot; '
        'held-out clinical association PMIDs do not leak into the historical gene links. '
        'Protected baseline/production hashes remain unchanged. A separate clean reconstruction '
        'produced all nine TSVs and the result manifest byte-for-byte identically.', '',
        'The user-requested Astra high independent-agent audit found no critical numerical '
        'or mapping error. Independent raw-source reconstruction reproduced constraint, GO, '
        'localization, animal and literature evidence across the full universe; pooled expression '
        'agreed to maximum absolute difference 2.22e-16. All 4,531 case-scheme rows and 37,950 '
        'recovery rows reproduced. See `astra_outcome_review_20261006.md`. '
        'This is an internal agent audit, not external peer review.', '',
        '```sh',
        'rtk proxy .venv/bin/python scripts/revision_temporal_v2_evaluate.py \\',
        '  --freeze revision/major_revision_20261006/temporal_validation_v2/freeze_amended.json \\',
        '  --freeze-commit 53da295 \\',
        '  --output-dir data/cache/temporal-validation-v2-20261006/new_replay_results',
        'rtk proxy .venv/bin/python scripts/revision_temporal_v2_report.py', '```', '',
        'The replay destination must not already exist. Raw sources remain in the local ignored '
        'cache; Git records hashes/provenance and results, not an off-machine raw-data backup. '
        'Final submission document/PDF packaging is a subsequent task.', ''])
    (BASE/'OUTCOME_REPORT.md').write_text('\n'.join(line.rstrip() for line in text))
    # Standalone scientific figure; denominator is explicitly the 41 in-universe cases.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams['svg.hashsalt'] = 'temporal-v2-20261006'
    endpoints = ('top100','top1000','top10pct','high')
    fig, ax = plt.subplots(figsize=(7.2, 4.0), layout='constrained')
    x = np.arange(len(endpoints))
    for j, s in enumerate(PRIMARY):
        data = [result(s,e) for e in endpoints]
        xpos = x+(j-.5)*.34
        heights = [float(r['recall'])*100 for r in data]
        ax.bar(xpos, heights, width=.32, label=('Five layers','Six layers')[j], color=('#457B9D','#E09F3E')[j])
        for pos, height, r in zip(xpos, heights, data):
            ax.text(pos, height+.5, f"{r['recovered']}/{r['denominator']}", ha='center', fontsize=9)
    ax.set_xticks(x, ['Top 100','Top 1,000','Top 10%','HIGH'])
    ax.set_ylabel('Later-case recovery (%)')
    ax.set_ylim(0,20)
    ax.set_title('Historical analogues: 41 later-case genes in the 2020 universe', fontsize=11)
    ax.spines[['top','right']].set_visible(False)
    ax.legend(frameon=False, loc='upper left')
    folder = BASE/'figures'; folder.mkdir(exist_ok=True)
    for extension in ('pdf','svg','png'):
        metadata = {'CreationDate': None, 'ModDate': None} if extension == 'pdf' else {'Date': None} if extension == 'svg' else None
        path = folder/f'principal_recovery.{extension}'
        fig.savefig(path, dpi=200, metadata=metadata)
        if extension == 'svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    plt.close(fig)
    print('Outcome report and standalone PDF/SVG/PNG recovery figure generated from verified frozen outputs.')


if __name__ == '__main__':
    main()

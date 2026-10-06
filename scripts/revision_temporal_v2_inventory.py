"""Inventory exact historical inputs without calculating evidence or outcomes."""
import json
from pathlib import Path
from revision_temporal_v2_reconstruct import ROOT, BASE, CACHE, OLD
from revision_phase2 import digest


def main():
    sources = [
        (OLD/'hgnc_20201001.tsv', 'universe', '2020-10-01', 'temporal_extension/download_manifest.json'),
        (OLD/'gnomad_v211.bgz', 'constraint', '2019; gnomAD v2.1.1', 'temporal_extension/download_manifest.json'),
        (OLD/'go_20201208.gaf.gz', 'annotation_partial_GO', '2020-12-08', 'temporal_extension/download_manifest.json'),
        (OLD/'hpa_v20_normal_tissue.zip', 'ordinal_expression', 'HPA v20; archived member dated2020', 'temporal_extension/download_manifest.json'),
        (OLD/'hpa_v20_subcellular.zip', 'localization', 'HPA v20; archived member dated2020', 'temporal_extension/download_manifest.json'),
        (OLD/'mgi_vocab_20190129.rpt', 'animal_term_labels', '2019-01-29', 'temporal_extension/download_manifest.json'),
        (CACHE/'raw/gtex_v8_gene_median_tpm.gct.gz', 'quantitative_expression', 'released2019-08-26', 'temporal_validation_v2/gtex_acquisition.json'),
        (CACHE/'raw/mgi_human_phenotype_20200202.rpt', 'animal_native_mouse', '2020-02-02', 'temporal_validation_v2/mgi_human_acquisition.json'),
        (CACHE/'raw/impc_release11_phenotypes.csv.gz', 'animal_mouse_and_term_labels', 'IMPC release11; pre-cutoff', 'temporal_validation_v2/acquisition_initial.json'),
        (CACHE/'raw/zfin_20201230_orthologs.tsv', 'animal_native_zebrafish_links', '2020-12-30; modified2020-12-31', 'temporal_validation_v2/orthology_acquisition.json'),
        (CACHE/'raw/zfin_20201230_phenotypes.tsv', 'animal_zebrafish', '2020-12-30; modified2020-12-31', 'temporal_validation_v2/acquisition_initial.json'),
        (CACHE/'raw/gene2pubmed_20200629.gz', 'literature_historical_links', '2020-06-29', 'temporal_validation_v2/gene2pubmed_acquisition.json'),
    ]
    for stem, suffix, date, record in [('GSE137537','tsv','2019-09-21','retina_10x_acquisition.json'),
                                     ('GSE137846_Seq-Well','txt','2019-09-23','retina_geo_acquisition.json')]:
        for name in [f'{stem}_counts.mtx.gz', f'{stem}_gene_names.txt.gz', f'{stem}_sample_annotations.{suffix}.gz']:
            sources.append((CACHE/'raw'/name, 'photoreceptor_original_counts_labels', date,
                            'temporal_validation_v2/'+record))
    for name in ['cilia','sensory','cytoskeleton','polarity','hts','direct_context']:
        sources.append((CACHE/'literature_date_sorted'/f'{name}_pmids.txt.gz',
            'literature_modern_text_date_bounded', 'FIRST_PDATE and FIRST_IDATE <=2020-12-31; modern text',
            f'temporal_validation_v2/literature_{name}_acquisition.json'))
    entries = [dict(path=str(path.relative_to(ROOT)), role=role, source_date=date,
                    provenance_manifest='revision/major_revision_20261006/'+manifest,
                    bytes=path.stat().st_size, sha256=digest(path)) for path,role,date,manifest in sources]
    output = BASE/'source_inventory_draft.json'
    output.write_text(json.dumps(dict(status='verified-file inventory draft; not outcome/protocol freeze',
        scores_read=False, entries=entries,
        exclusions={'modern_Census':'post-cutoff', 'HPA20_RNA':'no retina/cerebellum target contrast',
            'HCOP_votes':'historical support votes not recovered; native curated links instead',
            'UniProt_annotation_score_pathways':'not recovered; partial GO with named rescale sensitivity',
            'ZFIN_20201231':'server modification2021-01-01 boundary',
            'direct_hair_cells':'no suitable historical production analogue'}), indent=2)+'\n')
    print(json.dumps(dict(files=len(entries), bytes=sum(r['bytes'] for r in entries), output=str(output))))


if __name__ == '__main__':
    main()

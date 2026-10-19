// Run a copy of this builder beside a symlink to the bundled artifact-tool dependencies.
import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const root=process.cwd(),cache=`${root}/data/cache/go-classification-20261019`;
const base=`${root}/revision/major_revision_20261006/go_classification_20261019`;
const output=`${root}/outputs/temporal-go-classification-20261019`;
const data=JSON.parse(await fs.readFile(`${cache}/workbook_data.json`,'utf8'));
const sources=JSON.parse(await fs.readFile(`${base}/source_manifest.json`,'utf8'));
const wb=Workbook.create(),navy='#294C72',ink='#24364B';
const sheets={};for(const name of ['Genes','Categories','Category matrix','Membership','GO enrichment','Annotations','Methods'])sheets[name]=wb.worksheets.add(name);
function col(n){let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;}
function init(s,title,range){s.showGridLines=false;s.getRange(range).format={font:{name:'Arial',size:11,color:ink},verticalAlignment:'top'};s.getRange('A2').values=[[title]];s.getRange('A2').format.font={name:'Arial',size:16,bold:true};s.getRange('A2').format.rowHeight=30;}
function head(s,range,height=72){s.getRange(range).format={fill:navy,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,rowHeight:height};}
function widths(s,cols,last){for(let i=0;i<cols.length;i++)s.getRange(`${col(i)}1:${col(i)}${last}`).format.columnWidth=cols[i];}
function table(s,headers,rows,headerRow,name,widthArray,{height=40,headerHeight=72}={}){
 const last=headerRow+rows.length,end=col(headers.length-1);
 s.getRange(`A${headerRow}:${end}${headerRow}`).values=[headers];
 if(rows.length)s.getRange(`A${headerRow+1}:${end}${last}`).values=rows;
 s.getRange(`A${headerRow+1}:${end}${last}`).format.wrapText=true;
 s.getRange(`A${headerRow+1}:${end}${last}`).format.rowHeight=height;
 s.tables.add(`A${headerRow}:${end}${last}`,true,name);head(s,`A${headerRow}:${end}${headerRow}`,headerHeight);
 widths(s,widthArray,last);s.freezePanes.freezeRows(headerRow);s.freezePanes.freezeColumns(1);
}
const genes=sheets.Genes;init(genes,'GO classification of the 45 temporal cases','A1:R54');genes.tabColor=navy;
genes.getRange('A3').values=[['Contemporary annotation for biological discussion. Frozen temporal scores and author eligibility decisions are preserved.']];
genes.getRange('A4').values=[['GO categories overlap. A missing annotation is not evidence of absent function. Read Methods for sources and definitions.']];
genes.getRange('A5').values=[['Case genes']];genes.getRange('B5').formulas=[['=COUNTA(A9:A53)']];
genes.getRange('D5').values=[['Genes with usable GO']];genes.getRange('E5').formulas=[['=COUNTIFS(C9:C53,"GO found")']];
genes.getRange('A6').values=[['Current functions are not assumed to have been known in 2020. Percentiles are the unchanged five-/six-layer historical results.']];
const clean=t=>t.replace(/ \[GO:\d+\]/g,'');
const gh=['Frozen gene symbol','Current HGNC symbol','GO coverage','Biological process categories','Molecular function categories','Cellular component categories','Frozen 2020 GO term count','Five-layer percentile (0–100)','Six-layer percentile (0–100)','Usable current direct GO terms','Direct terms with non-IEA support','Direct terms with experimental support','Current evidence codes','Gene type','Mapping route','Annotated gene products','Interpretation / mapping limits','Author eligibility as returned'];
const geneValues=data.genes.map(g=>[g.frozen_symbol,g.current_symbol,g.usable_direct_go_terms?'GO found':'No usable GO',clean(g.BP_categories)||'No mapped category',clean(g.MF_categories)||'No mapped category',clean(g.CC_categories)||'No mapped category',g.frozen_2020_GO_count,g.five_layer_percentile,g.six_layer_percentile,g.usable_direct_go_terms,g.non_IEA_direct_terms,g.experimental_direct_terms,g.evidence_codes,g.gene_type,g.mapping_routes,g.annotated_gene_products,g.notes,g.author_eligibility_as_returned]);
table(genes,gh,geneValues,8,'GeneGOClassification',[22,22,22,70,65,65,22,23,23,23,25,26,34,25,56,56,82,25],{height:84,headerHeight:88});
for(let i=0;i<data.genes.length;i++){
 const g=data.genes[i],r=i+9;
 const lines=Math.max(...[clean(g.BP_categories).length/65,clean(g.MF_categories).length/60,clean(g.CC_categories).length/60,g.notes.length/78,g.mapping_routes.length/52,g.annotated_gene_products.length/52].map(Math.ceil));
 genes.getRange(`A${r}:R${r}`).format.rowHeight=Math.max(62,lines*18+14);
}
genes.getRange('H9:I53').setNumberFormat('0.0');genes.getRange('C9:C53').conditionalFormats.add('containsText',{text:'No usable GO',format:{fill:'#FFF2CC',font:{color:'#7F5700',bold:true}}});

const categories=sheets.Categories;init(categories,'Functional categories and historical rank context',`A1:J${data.categories.length+6}`);
categories.getRange('A3').values=[['All active non-root generic GO-slim categories. Membership overlaps. Category medians are descriptive, with no subgroup hypothesis test.']];
table(categories,['Aspect','GO ID','Category','Genes / 45','Proportion of all 45','Coding genes / 41','Noncoding genes / 4','Genes with non-IEA support','Median five-layer percentile','Median six-layer percentile','Current gene symbols'],
 data.categories.map(c=>[c.aspect,c.go_id,c.category,c.genes_of_45,c.proportion_of_45,c.coding_genes_of_41,c.noncoding_genes_of_4,c.genes_without_IEA,c.median_five_percentile,c.median_six_percentile,c.genes]),5,'GOSlimCategories',[14,20,66,17,22,22,24,27,28,28,90],{height:48});
categories.getRange(`E6:E${data.categories.length+5}`).setNumberFormat('0.0%');categories.getRange(`I6:J${data.categories.length+5}`).setNumberFormat('0.0');
for(let i=0;i<data.categories.length;i++)if(data.categories[i].genes.length>160)categories.getRange(`A${i+6}:K${i+6}`).format.rowHeight=Math.ceil(data.categories[i].genes.length/85)*18+12;

const matrix=sheets['Category matrix'];const cats=data.categories.filter(c=>c.genes_of_45>0);const mlast=col(cats.length+1);
init(matrix,'Gene-by-category matrix',`A1:${mlast}51`);matrix.getRange('A3').values=[['1 = observed annotation supports this category. 0 = category not observed. Blank = no usable GO in that aspect. Categories overlap.']];
const membership=new Set(data.memberships.map(r=>`${r.gene_key}:${r.slim_go_id}`));
table(matrix,['Frozen gene symbol','Current gene symbol',...cats.map(c=>`${c.aspect}\n${c.category}\n${c.go_id}`)],data.genes.map(g=>[g.frozen_symbol,g.current_symbol,...cats.map(c=>g[`${c.aspect}_direct_terms`]?Number(membership.has(`${g.gene_key}:${c.go_id}`)):null)]),5,'GeneCategoryMatrix',[22,22,...cats.map(()=>27)],{height:24,headerHeight:132});
matrix.freezePanes.freezeColumns(2);matrix.getRange(`C6:${mlast}50`).conditionalFormats.add('cellIs',{operator:'equal',formula:1,format:{fill:'#BDD7EE',font:{color:navy,bold:true}}});

const member=sheets.Membership;init(member,'Trace each gene to its functional categories',`A1:I${data.memberships.length+6}`);
member.getRange('A3').values=[['Supporting GO terms are direct source annotations. Categories are ancestors through is_a / part_of only. Non-IEA is not always experimental.']];
table(member,['Stable HGNC key','Frozen gene symbol','Current gene symbol','Aspect','GO-slim ID','Category','Supporting direct GO IDs','Supported without IEA','In historical coding universe'],data.memberships.map(r=>[r.gene_key,r.frozen_symbol,r.current_symbol,r.aspect,r.slim_go_id,r.category,r.supporting_direct_terms,r.supported_without_IEA?'Yes':'No',r.in_historical_universe?'Yes':'No']),5,'GOMembership',[22,23,23,14,21,68,100,25,27],{height:42});
for(let i=0;i<data.memberships.length;i++)if(data.memberships[i].supporting_direct_terms.length>180)member.getRange(`A${i+6}:I${i+6}`).format.rowHeight=Math.ceil(data.memberships[i].supporting_direct_terms.length/96)*18+12;

const enrichment=sheets['GO enrichment'];const nr=data.enrichment.length;
init(enrichment,'Exploratory GO over-representation',`A1:N${nr+6}`);
enrichment.getRange('A3').values=[['Primary and two secondary analyses are labelled separately. BH FDR pools all tested BP/MF/CC terms within each analysis, including zero-overlap terms.']];
enrichment.getRange('A4').values=[['Filter Analysis and FDR < 0.05. Complete nonsignificant results are retained. This is functional composition, not independent predictive validation.']];
table(enrichment,['Analysis','Aspect','GO ID','Term','Cases with term (k)','Annotated cases (n)','Background genes with term (K)','Annotated background genes (N)','Expected case count','Fold enrichment','Raw P','BH FDR','FDR < 0.05','Current case gene symbols'],data.enrichment.map(r=>[r.analysis,r.aspect,r.go_id,r.term_name,r.query_hits,r.query_annotated,r.background_hits,r.background_annotated,r.expected_hits,r.fold_enrichment,r.p_value,r.fdr_bh,r.fdr_lt_0_05?'Yes':'No',r.case_symbols]),6,'GOOverRepresentation',[46,13,20,75,23,23,28,30,24,23,22,22,20,95],{height:40,headerHeight:88});
enrichment.getRange(`I7:J${nr+6}`).setNumberFormat('0.00');enrichment.getRange(`K7:L${nr+6}`).setNumberFormat('0.00E+00');
enrichment.getRange(`M7:M${nr+6}`).conditionalFormats.add('containsText',{text:'Yes',format:{fill:'#E2F0D9',font:{color:'#305B23',bold:true}}});
for(let i=0;i<nr;i++)if(data.enrichment[i].case_symbols.length>180)enrichment.getRange(`A${i+7}:N${i+7}`).format.rowHeight=Math.ceil(data.enrichment[i].case_symbols.length/90)*18+12;

const annotations=sheets.Annotations;const na=data.annotations.length;
init(annotations,'Direct case annotations and source evidence',`A1:Q${na+6}`);
annotations.getRange('A3').values=[['Usable positive human GAF records after the stated filters. Repeated GO terms can have different evidence/reference records. Counts in Genes deduplicate terms.']];
table(annotations,['Frozen gene symbol','Current gene symbol','Stable HGNC key','Aspect','GO ID','Term','Evidence code','Reference','Gene-product ID','Mapping route','Source GAF file','Original GO ID','Relation / qualifier','With / from','Annotation date (YYYYMMDD)','Assigned by','Annotation extension'],data.annotations.map(r=>[r.frozen_symbol,r.current_symbol,r.gene_key,r.aspect,r.go_id,r.term_name,r.evidence_code,r.reference,r.gene_product,r.mapping_route,r.source,r.original_go_id,r.relation,r.with_from,r.annotation_date,r.assigned_by,r.annotation_extension]),5,'DirectGOAnnotations',[22,22,22,14,21,76,21,58,52,58,32,22,28,58,28,23,85],{height:44,headerHeight:76});
annotations.getRange(`O6:O${na+5}`).setNumberFormat('@');

const methods=sheets.Methods;init(methods,'Definitions, backgrounds and reproducibility','A1:J50');methods.tabColor='#607D8B';
const summary=data.summary;
const definitions=[
 ['Purpose','Post-hoc functional description of the same 45 provisional temporal cases. No frozen rank, score, cohort label or clinical author decision is changed.'],
 ['GO aspects','BP: biological process. MF: molecular function. CC: cellular component. Generic GO slim groups specific annotations into broader functional categories. A gene can have multiple categories.'],
 ['Mapping','Current approved HGNC stable keys and explicit UniProt/RNAcentral accessions are preferred. Unambiguous approved/previous symbols are fallback routes. Ambiguous aliases/accessions are rejected. Modern and frozen symbols are preserved.'],
 ['RNA handling','Four RNU genes remain in the 45-gene description. Explicit shared RNAcentral sequence mappings are disclosed; they are not independent locus-specific experiments. RNA genes remain outside the original 41-coding-case enrichment/score universe.'],
 ['Annotation filters','Human taxon 9606. Exclude NOT, ND/root-only and unresolved obsolete terms. Keep evidence and references. Counts are unique gene--GO term pairs. An IEA-only annotation is retained in the main description but identified.'],
 ['IEA / non-IEA / experimental','IEA is inferred from electronic annotation. Non-IEA includes curated inference and is not synonymous with experimental evidence. Experimental codes here: EXP, IDA, IPI, IMP, IGI, IEP, HTP, HDA, HMP, HGI, HEP.'],
 ['Ancestry','Authoritative QuickGO ancestors restricted to is_a and part_of within each original GAF aspect. Cross-aspect GO-plus inference is excluded uniformly. No has_part, occurs_in or regulates propagation. Generic GO-slim membership comes from the separately pinned official editor snapshot.'],
 ['Missing values','No annotation is missing evidence, not absent function. Matrix blanks indicate no usable annotation in the aspect. Zero means that category was not observed. Historical score fields are blank for the four out-of-universe RNA genes.'],
 ['2020 GO counts and ranks','The 2020 GO count and five-/six-layer percentiles are copied unchanged from frozen outputs. Current direct GO counts use different dates and filtering, so the counts are not directly comparable. Current category membership is not assumed to have been known in 2020.'],
 ['Primary reference','All 19,167 historical protein-coding genes are eligible. For each aspect, restrict both reference and the 41-case query to genes with a usable annotation in that aspect. Denominators and missing cases appear below.'],
 ['Secondary references','No IEA: remove IEA in both query and genome reference. Catalog background: original catalog-sourced genes intersecting the historical coding universe, with appended reference controls excluded. Catalog genes are not clinically established negatives.'],
 ['Statistical test','One-sided hypergeometric/Fisher over-representation. Test each non-root propagated term with at least 5 annotated background genes in the term and at least 5 outside. Do not filter terms by case hits.'],
 ['Multiple testing','Benjamini--Hochberg FDR pools all tested BP/MF/CC terms separately within each named analysis, including zero-hit terms. FDR < 0.05 is the displayed flag. All results are retained; do not substitute a favorable sensitivity result for the primary result.'],
 ['Interpretation','Enrichment describes this selected cohort and its annotation/background composition. It does not establish disease specificity, independent prospective prediction or a reason for temporal failure. Category rank medians are overlapping post-hoc descriptive summaries.'],
 ['Fixed figure selection','The standalone figure shows up to 12 categories per aspect with the largest gene counts, with GO-ID tie-breaking. Counts use all 45 cases; categories overlap. No pie-chart partition or hand-picked cilia category selection.'],
 ['GOA annotation source',`${sources.find(s=>s.name==='human_protein.gaf.gz').url}\n${sources.find(s=>s.name==='human_rna.gaf.gz').url}\nFiles generated 2026-10-11; full SHA-256 records are retained with the audit.`],
 ['Ontology source',`QuickGO version ${summary.ontology_version.timestamp}: https://www.ebi.ac.uk/QuickGO/services/ontology/go/about\nAncestor request relations=is_a,part_of. All term responses are cached and hashed. Generic slim: official GO editor commit 16154084af7ef6330f815c63fde0b6b6ff08b8f2, 2026-09-27.`],
 ['HGNC mapping source',`${sources.find(s=>s.name==='hgnc_complete_set.tsv').url}\nDownloaded 2026-10-19; source HTTP last-modified is retained in the manifest.`],
 ['Official method references','https://geneontology.org/docs/go-subset-guide/\nhttps://www.geneontology.org/docs/go-enrichment-analysis/\nhttps://www.ebi.ac.uk/QuickGO/api/example.html'],
 ['Clinical status','The human-returned eligibility fields remain PENDING for all 45. Bibliographic dates, functional annotations and clinical eligibility are distinct questions.'],
];
methods.getRange('A4:B4').values=[['Field / rule','Definition']];head(methods,'A4:B4',32);methods.getRange(`A5:B${definitions.length+4}`).values=definitions;methods.getRange(`A5:B${definitions.length+4}`).format.wrapText=true;
widths(methods,[36,126],45);for(let i=0;i<definitions.length;i++)methods.getRange(`A${i+5}:B${i+5}`).format.rowHeight=Math.max(48,Math.ceil(definitions[i][1].length/116)*18+12);
methods.getRange('C1:C30').format.columnWidth=4;
methods.getRange('D2').values=[['Actual aspect-specific query and reference coverage']];methods.getRange('D2').format.font={name:'Arial',size:14,bold:true};
const ch=['Analysis','Aspect','Eligible cases','Annotated cases','Eligible background','Annotated background','Cases without annotation in this aspect'];
methods.getRange('D4:J4').values=[ch];head(methods,'D4:J4',72);
methods.getRange(`D5:J${4+data.coverage.length}`).values=data.coverage.map(r=>[r.analysis,r.aspect,r.eligible_query,r.annotated_query,r.eligible_background,r.annotated_background,r.unannotated_case_symbols]);
methods.getRange(`D5:J${4+data.coverage.length}`).format.wrapText=true;
for(const [c,w] of Object.entries({D:46,E:14,F:22,G:23,H:27,I:29,J:70}))methods.getRange(`${c}4:${c}${4+data.coverage.length}`).format.columnWidth=w;
methods.freezePanes.freezeRows(4);

// Test the formula-linked annotation count and restore the delivered data.
wb.recalculate();const expected=data.genes.filter(g=>g.usable_direct_go_terms>0).length;
if(Number(genes.getRange('B5').values[0][0])!==45 || Number(genes.getRange('E5').values[0][0])!==expected)throw new Error('Summary formulas failed');
const index=data.genes.findIndex(g=>g.usable_direct_go_terms>0),cell=`C${index+9}`;
genes.getRange(cell).values=[['No usable GO']];wb.recalculate();if(Number(genes.getRange('E5').values[0][0])!==expected-1)throw new Error('Input-change count did not update');
genes.getRange(cell).values=[['GO found']];wb.recalculate();if(Number(genes.getRange('E5').values[0][0])!==expected)throw new Error('Count not restored');
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
const views=[['Genes','A2:F11','genes'],['Genes','G8:L12','historical-context'],['Categories','A5:G9','categories'],['Category matrix','A5:H10','matrix'],['Membership','A5:H9','membership'],['GO enrichment','A6:H10','enrichment-counts'],['GO enrichment','I6:N10','enrichment-results'],['Annotations','A5:H9','annotations'],['Methods','A2:B13','methods'],['Methods','D2:J8','coverage']];
for(const [sheetName,range,name] of views){const blob=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(`${cache}/workbook-${name}.png`,new Uint8Array(await blob.arrayBuffer()));}
await fs.mkdir(output,{recursive:true});await (await SpreadsheetFile.exportXlsx(wb)).save(`${output}/Temporal_GO_Classification_20261019.xlsx`);
await fs.writeFile(`${cache}/workbook_checks.json`,JSON.stringify({gene_rows:45,annotated_before:expected,temporary_edit_count:expected-1,restored_count:expected,sheets:7,complete_enrichment_rows:nr,direct_annotation_rows:na,temporary_edit_restored:true},null,2));
console.log(`Saved 45-gene workbook with ${nr} complete enrichment rows and ${na} direct annotation records.`);

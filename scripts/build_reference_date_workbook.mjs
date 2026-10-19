// Run a copy beside the symlink to Codex's bundled artifact-tool dependencies.
import fs from 'node:fs/promises';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const root=process.cwd();
const folder=`${root}/revision/major_revision_20261006/author_review_20261019/date_audit`;
const cache=`${root}/data/cache/author-review-20261019/date-audit`;
const output=`${root}/outputs/temporal-reference-dates-20261019`;
const genes=JSON.parse(await fs.readFile(`${folder}/gene_date_comparison.json`,'utf8'));
const papers=JSON.parse(await fs.readFile(`${folder}/article_dates.json`,'utf8'));
const events=JSON.parse(await fs.readFile(`${folder}/curation.json`,'utf8')).earlier_events;
const wb=Workbook.create();
const main=wb.worksheets.add('Gene dates');
const articles=wb.worksheets.add('Article dates');
const earlier=wb.worksheets.add('Earlier events');
const guide=wb.worksheets.add('Definitions');
const navy='#294C72',ink='#24364B';
const asDate=v=>v && /^\d{4}-\d{2}-\d{2}$/.test(v)?new Date(`${v}T00:00:00Z`):(v||null);
function base(s,range){s.showGridLines=false;s.getRange(range).format={font:{name:'Arial',size:11,color:ink},verticalAlignment:'top'};}
function widths(s,map,last=60){for(const [c,w] of Object.entries(map))s.getRange(`${c}1:${c}${last}`).format.columnWidth=w;}
function header(s,range,height){s.getRange(range).format={fill:navy,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,rowHeight:height};}
function title(s,text){s.getRange('A2').values=[[text]];s.getRange('A2').format.font={name:'Arial',size:16,bold:true};s.getRange('A2').format.rowHeight=30;}
base(main,'A1:P54');base(articles,'A1:R50');base(earlier,'A1:G21');base(guide,'A1:B25');
main.tabColor=navy;guide.tabColor='#607D8B';
title(main,'Reference publication-date audit');
main.getRange('A3').values=[['45 genes. All 46 supplied PDFs reconciled with 43 distinct PMID records. Checked 19 October 2026.']];
main.getRange('A4').values=[['Date suggestions from a source audit. Original author decisions and frozen temporal results remain unchanged.']];
main.getRange('A5').values=[['Genes compared']];main.getRange('B5').formulas=[['=COUNTA(A9:A53)']];
main.getRange('D5').values=[['Exact first-public day unresolved']];main.getRange('E5').formulas=[['=COUNTIFS(J9:J53,"Interval retained")']];
main.getRange('A6').values=[['Blank proposed dates retain uncertainty. Read the explanation in F and the separate publication events in the next two tabs.']];
const mh=['Gene','Why dates differ','Original list date (AI, provisional)','Professor returned date entry (preserved)','Source-supported first PUBLIC target date (blank if exact first day unresolved)','What the different dates mean','Dated public event independently located (may not be earliest)','Type of located public event','Journal-hosted target report first public date','Exact first-public-day status','Frozen uncertainty interval (preserved)','PMIDs in the supplied ZIP','First-target timing source','Professor date decision (preserved)','Professor eligibility decision (preserved)','Stable HGNC gene key'];
main.getRange('A8:P8').values=[mh];header(main,'A8:P8',90);
for(let i=0;i<genes.length;i++){
 const g=genes[i],r=i+9;
 main.getRange(`A${r}:P${r}`).values=[[g.display_symbol,g.category,asDate(g.original_ai_displayed_date),g.professor_returned_exact_date?asDate(g.professor_returned_exact_date):g.professor_returned_date,asDate(g.suggested_exact_first_public_target_date),g.interpretation,asDate(g.independently_located_public_event_date),g.public_event_type,asDate(g.journal_first_public_for_target_report),g.uncertain_first_public_day?'Interval retained':'Located day supported',g.original_frozen_interval.join(' to '),g.supplied_pmids.join('; '),g.first_target_source,g.professor_date_status,g.professor_eligibility,g.gene_key]];
 main.getRange(`A${r}:P${r}`).format.wrapText=true;
 const lines=Math.max(Math.ceil(g.interpretation.length/86),Math.ceil(g.professor_returned_date.length/43)+g.professor_returned_date.split('\n').length-1,Math.ceil(g.category.length/34),Math.ceil(g.first_target_source.length/68));
 main.getRange(`A${r}:P${r}`).format.rowHeight=Math.max(52,lines*18+14);
 main.getRange(`A${r}`).format.font.bold=true;
}
main.tables.add('A8:P53',true,'GenePublicationDates');header(main,'A8:P8',90);
for(const c of ['C','E','G','I'])main.getRange(`${c}9:${c}53`).setNumberFormat('yyyy-mm-dd');
for(let i=0;i<genes.length;i++)if(genes[i].professor_returned_exact_date)main.getRange(`D${i+9}`).setNumberFormat('yyyy-mm-dd');
for(let i=0;i<genes.length;i++)if(!/^\d{4}-\d{2}-\d{2}$/.test(genes[i].independently_located_public_event_date))main.getRange(`G${i+9}`).setNumberFormat('@');
main.getRange('J9:J53').conditionalFormats.add('containsText',{text:'Interval retained',format:{fill:'#FFF2CC',font:{color:'#7F5700',bold:true}}});
main.getRange('B9:B53').conditionalFormats.add('containsText',{text:'unsupported',format:{fill:'#FCE4D6',font:{color:'#9C3500',bold:true}}});
main.freezePanes.freezeRows(8);main.freezePanes.freezeColumns(1);
widths(main,{A:21,B:36,C:21,D:44,E:26,F:92,G:26,H:36,I:24,J:27,K:35,L:26,M:76,N:24,O:25,P:22});

title(articles,'Publication chronology for all supplied articles');
articles.getRange('A3').values=[['43 distinct PMID labels. Editorial dates and each public version are separate. Blank means not recorded in checked sources.']];
articles.getRange('A4').values=[['PubMed issue precision is preserved. YYYY-MM or YYYY stays text. No artificial first day of a month is created.']];
const ah=['Gene labels on ZIP files','PMID','Received / submitted (not public release)','Revised (not public release)','Accepted (not public release)','First public JOURNAL-hosted version','Type of that first public version','Later Version of Record date (only if separately verified)','PubMed Electronic date (retained even when later)','Issue date / period (source precision retained)','Issue date precision','Other public version / correction events','Explanation of source differences','Article title','DOI','Date-history pages in supplied PDF (auto-located)','Publication-date source and PubMed source','ZIP filenames (copies retained)'];
articles.getRange('A6:R6').values=[ah];header(articles,'A6:R6',94);
for(let i=0;i<papers.length;i++){
 const p=papers[i],r=i+7;
 articles.getRange(`A${r}:R${r}`).values=[[p.symbols_on_files.join(', '),p.pmid,asDate(p.received),asDate(p.revised),asDate(p.accepted),asDate(p.journal_first_public),p.journal_first_public_type,asDate(p.version_of_record),asDate(p.pubmed_electronic_date),asDate(p.issue_date),p.issue_date_precision,p.other_public_events,p.note,p.title,p.doi,p.pdf_date_pages.length?p.pdf_date_pages.join(', '):'No date-history panel in supplied extract',`${p.publication_source}\n${p.pubmed_source}`,p.filenames.join('\n')]];
 articles.getRange(`A${r}:R${r}`).format.wrapText=true;
 articles.getRange(`A${r}:R${r}`).format.rowHeight=Math.max(56,Math.ceil(Math.max(p.note.length/88,p.title.length/67,p.filenames.join('\n').length/68))*18+16);
 articles.getRange(`A${r}:B${r}`).format.font.bold=true;
}
articles.tables.add('A6:R49',true,'SuppliedArticleDates');header(articles,'A6:R6',94);
for(const c of ['C','D','E','F','H','I','J'])articles.getRange(`${c}7:${c}49`).setNumberFormat('yyyy-mm-dd');
for(let i=0;i<papers.length;i++)if(papers[i].issue_date_precision!=='day')articles.getRange(`J${i+7}`).setNumberFormat('@');
articles.freezePanes.freezeRows(6);articles.freezePanes.freezeColumns(2);
widths(articles,{A:25,B:14,C:22,D:21,E:22,F:24,G:37,H:26,I:25,J:25,K:18,L:58,M:94,N:72,O:42,P:26,Q:92,R:74});

title(earlier,'Earlier versions, conferences and thesis dates');
earlier.getRange('A3').values=[['15 event records. A thesis award/submission and a scheduled talk do not establish an exact first public-release day.']];
const eh=['Gene(s)','Event date / period','Date precision','Event type','What was verified','Limit / interpretation','Source'];
earlier.getRange('A5:G5').values=[eh];header(earlier,'A5:G5',56);
for(let i=0;i<events.length;i++){
 const e=events[i],r=i+6;
 earlier.getRange(`A${r}:G${r}`).values=[[e.symbols.join(', '),asDate(e.date),e.precision,e.type,e.evidence,e.limitation,e.source]];
 earlier.getRange(`A${r}:G${r}`).format.wrapText=true;
 earlier.getRange(`A${r}:G${r}`).format.rowHeight=Math.max(64,Math.ceil(Math.max(e.evidence.length/78,e.limitation.length/78,e.source.length/78))*18+14);
 earlier.getRange(`A${r}`).format.font.bold=true;
}
earlier.tables.add('A5:G20',true,'EarlierPublicEvents');header(earlier,'A5:G5',56);
earlier.getRange('B6:B20').setNumberFormat('yyyy-mm-dd');
for(let i=0;i<events.length;i++)if(events[i].precision!=='day')earlier.getRange(`B${i+6}`).setNumberFormat('@');
earlier.freezePanes.freezeRows(5);earlier.freezePanes.freezeColumns(1);
widths(earlier,{A:29,B:22,C:17,D:40,E:86,F:86,G:86});

title(guide,'What each date means');
const definitions=[
 ['First PUBLIC target association','Earliest located public proposal of the human retinal/optic, hearing or explicitly supported ciliary disease association. It may be a preprint, public in-press preview or meeting abstract before the final journal paper. It is distinct from the date when the clinical evidence became strong enough for eligibility.'],
 ['Received / submitted','The journal received the manuscript. This is editorial history. It is not evidence that readers could access the paper that day.'],
 ['Revised / accepted','Internal editorial milestones. An accepted manuscript can later be released publicly, but the acceptance decision itself does not establish public availability.'],
 ['First public journal-hosted version','Earliest located public version hosted by the journal. DNAJC30/CTNND1 have in-press previews. PLCG1 has a reviewed preprint before the Version of Record. This column is separate from any earlier external preprint.'],
 ['Version of Record','The final journal version. Filled separately only when the checked source explicitly distinguishes it from an earlier public version. A blank here does not mean there is no final article.'],
 ['Online / advance access / epub','Public online article release. It often precedes the issue date. For PDIA6, publisher first-public January 26 and PubMed Electronic February 17 are both retained. The discrepancy is not silently relabelled as a known version transition.'],
 ['Issue date','The journal volume/issue date. It can be months or a year later than first online. TMEM72 was online in 2025 and appears in the April 2026 issue.'],
 ['Preprint date and DOI','Use the posting date for that version, not the date embedded in the DOI. GPATCH11 DOI August 19 was posted August 21. PKHD1L1 DOI October 8 was posted October 9. Later revisions do not replace the first posting day.'],
 ['Conference / thesis dates','A programme or retrospective report can document an earlier proposal without resolving the exact first public-release date. Thesis award year and submission are not public-deposit dates. Keep source precision and uncertainty.'],
 ['Proposed date left blank','ATP11A, CREB3, MRPL49 and TMEM72 retain first-day uncertainty. The dated public event in G can be securely located without proving it was the first disclosure. Read the original frozen interval and explanation.'],
 ['Original frozen interval','Historical uncertainty bound from the frozen study. Displaying its lower bound as a date in the old Excel did not make that day independently verified. These intervals are preserved here, not silently narrowed or replaced.'],
 ['Target vs non-target disease','VWA8 2021 concerns an earlier neurodevelopmental association; its retinal target report was in 2023. STX3 has an earlier intestinal association. PLCG1 has a 2023 immune report and later sensory reports. Do not substitute the first disease of any kind for the first target association.'],
 ['Scope and missing data','All 46 supplied PDFs were text-inspected and mapped to 43 distinct PMID records. PubMed/Europe PMC metadata were freshly acquired for all 43. Source-specific exceptions and seven preprint records were checked. KCNJ16 is a two-page extract. Blank editorial dates mean not recorded in checked sources.'],
 ['What this audit establishes','It resolves publication-stage differences and identifies unsupported entries. It does not prove that no earlier report exists anywhere or re-adjudicate all clinical families. Fifteen event rows are source chronology, not fifteen independent replications.'],
 ['Cutoff and result impact','Historical cutoff: 2020-12-31. No newly confirmed pre-cutoff public target association was found in this bounded date audit. Receipt/acceptance before 2021 alone does not change eligibility. No frozen cohort label, score or recovery result was changed.'],
 ['Author decisions','All 45 eligibility fields remain PENDING as returned. Their existing date statuses are preserved. This workbook supplies bibliographic suggestions, not inferred human inclusion approval.'],
 ['Sources and reproduction','Publication URLs and source locations sit beside the source records in Article dates and Earlier events. The original workbook, ZIP and frozen data remain intact. Source evidence and hash records were archived with the repository audit.']
];
guide.getRange('A4:B4').values=[['Field / rule','Definition and practical use']];header(guide,'A4:B4',32);
guide.getRange(`A5:B${definitions.length+4}`).values=definitions;
guide.getRange(`A5:B${definitions.length+4}`).format.wrapText=true;
for(let i=0;i<definitions.length;i++)guide.getRange(`A${i+5}:B${i+5}`).format.rowHeight=Math.max(49,Math.ceil(definitions[i][1].length/113)*18+14);
widths(guide,{A:36,B:121});guide.freezePanes.freezeRows(4);

// Check a changed category really updates the displayed unresolved count, then restore it.
wb.recalculate();
if(Number(main.getRange('B5').values[0][0])!==45)throw new Error('Gene count mismatch');
if(Number(main.getRange('E5').values[0][0])!==4)throw new Error('Uncertainty count mismatch');
const changedRow=genes.findIndex(g=>g.uncertain_first_public_day)+9;
main.getRange(`J${changedRow}`).values=[['Located day supported']];wb.recalculate();
if(Number(main.getRange('E5').values[0][0])!==3)throw new Error('Input-change recalculation failed');
main.getRange(`J${changedRow}`).values=[['Interval retained']];wb.recalculate();
if(Number(main.getRange('E5').values[0][0])!==4)throw new Error('Restoration failed');
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10},maxChars:600})).ndjson);
const previews=[['Gene dates','A2:F11','genes-left'],['Gene dates','E20:K24','genes-public-events'],['Article dates','A6:G10','articles-dates'],['Article dates','H6:M9','articles-versions'],['Earlier events','A5:F9','earlier-top'],['Earlier events','A14:F20','earlier-uncertainty'],['Definitions','A2:B13','definitions-top'],['Definitions','A14:B21','definitions-bottom']];
for(const [sheetName,range,name] of previews){
 const img=await wb.render({sheetName,range,scale:1,format:'png'});
 await fs.writeFile(`${cache}/${name}.png`,new Uint8Array(await img.arrayBuffer()));
}
await fs.mkdir(output,{recursive:true});
await (await SpreadsheetFile.exportXlsx(wb)).save(`${output}/Temporal_Reference_Date_Audit_20261019.xlsx`);
await fs.writeFile(`${cache}/workbook_recalculation.json`,JSON.stringify({genes:45,unresolved_before:4,temporary_category_change:3,unresolved_restored:4,original_entries_preserved:true,engine:'artifact-tool; native Excel/LibreOffice not available'},null,2));
console.log('Saved 45 gene comparisons, 43 article chronologies, 15 earlier events and definitions.');

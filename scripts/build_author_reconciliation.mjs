// Run a copy of this builder beside a symlink to the bundled artifact-tool node_modules.
import fs from 'node:fs/promises';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const root=process.cwd();
const folder=`${root}/revision/major_revision_20261006/author_review_20261019`;
const cache=`${root}/data/cache/author-review-20261019`;
const output=`${root}/outputs/temporal-author-reconciliation-20261019`;
const rows=JSON.parse(await fs.readFile(`${folder}/confirmation_items.json`,'utf8'));
const comments=JSON.parse(await fs.readFile(`${folder}/reviewer_comments.json`,'utf8'));
const wb=Workbook.create();
const main=wb.worksheets.add('Confirmations');
const returned=wb.worksheets.add('Author return');
const guide=wb.worksheets.add('Guide');
const navy='#294C72',ink='#24364B',yellow='#FFF2CC';
function base(s,r){s.showGridLines=false;s.getRange(r).format={font:{name:'Arial',size:11,color:ink},verticalAlignment:'top'};}
function header(s,r){s.getRange(r).format={fill:navy,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},wrapText:true,verticalAlignment:'center',horizontalAlignment:'center'};}
function widths(s,map,last=60){for(const [c,w] of Object.entries(map))s.getRange(`${c}1:${c}${last}`).format.columnWidth=w;}
base(main,'A1:N55');base(returned,'A1:K46');base(guide,'A1:B35');
main.tabColor=navy;guide.tabColor='#607D8B';
main.getRange('A2').values=[['Author confirmation after literature review']];main.getRange('A2:N2').format.rowHeight=30;main.getRange('A2').format.font={name:'Arial',size:16,bold:true};
main.getRange('A3').values=[['Read Guide, then answer each question in the yellow cells. Original author observations are preserved in Author return.']];
main.getRange('A4').values=[['Source checks are AI-assisted suggestions. PENDING is retained until an author explicitly decides.']];
main.getRange('A5').values=[['Eligibility pending']];main.getRange('B5').formulas=[['=COUNTIFS(C9:C53,"PENDING")']];main.getRange('B5').format.horizontalAlignment='left';
main.getRange('D5').values=[['A lower pending count is not certification that every date and evidence question is resolved.']];
main.getRange('A6').values=[['An uncertain exact date can stay blank. Record the interval and reason in the reply. Original frozen results are unchanged.']];
const titles=['Gene (frozen name retained)','Question for the author','Final author decision: use this gene as a later-discovered target-disease test case?','Author-confirmed FIRST PUBLIC target-association date','Author reply, supporting PMID and page/table/figure','Author confirming this decision','Date this confirmation was performed','Source check / proposed interpretation (AI-assisted)','Stable HGNC gene key','Date entered in the returned workbook (preserved)','Date decision entered in the returned workbook (preserved)','Earlier frozen AI timing and interval (provisional)','Additional frozen clinical PMIDs NOT supplied in Refs.zip','Suggested date interpretation (AI-assisted; not final)'];
main.getRange('A8:N8').values=[titles];header(main,'A8:N8');main.getRange('A8:N8').format.rowHeight=100;
const authorHeaders=['Gene symbol as returned','Stable HGNC gene key','Eligibility decision as returned','Date decision as returned','Reviewer as returned','Review date as returned','Association-date entry as returned','Notes as returned','Genotype / inheritance notes as returned','AI date displayed in original workbook','AI novelty category displayed in original workbook'];
returned.getRange('A1:K1').values=[authorHeaders];header(returned,'A1:K1');returned.getRange('A1:K1').format.rowHeight=72;
for(let i=0;i<rows.length;i++){
 const r=rows[i],rr=i+9,ar=i+2;
 const label=r.symbol==='EFCAB1'?'CLXN (EFCAB1)':r.symbol;
 const question=r.focus==='Final author sign-off'?r.question:`${r.focus}: ${r.question}`;
 const source=r.source_check;
 main.getRange(`A${rr}:N${rr}`).values=[[label,question,'PENDING',null,null,null,null,source,r.gene_key,r.human_association_exact_date_if_numeric?new Date(`${r.human_association_exact_date_if_numeric}T00:00:00Z`):r.human_association_date_raw,r.human_date_decision_as_returned,`${r.original_ai_association_date}; interval ${r.original_date_interval.join(' to ')}`,r.missing_nominated_pmids.join('; ')||'None nominated beyond the supplied PDFs',r.date_candidate]];
 main.getRange(`A${rr}:N${rr}`).format.wrapText=true;
 main.getRange(`A${rr}:N${rr}`).format.rowHeight=Math.max(116,Math.ceil(Math.max(question.length/52,source.length/68,r.date_candidate.length/52))*17+14);
 main.getRange(`C${rr}:G${rr}`).format.fill=yellow;
 main.getRange(`A${rr}`).format.font.bold=true;
 const g=r.human_association_exact_date_if_numeric?new Date(`${r.human_association_exact_date_if_numeric}T00:00:00Z`):r.human_association_date_raw;
 returned.getRange(`A${ar}:K${ar}`).values=[[r.symbol,r.gene_key,r.human_eligibility_decision_as_returned,r.human_date_decision_as_returned,r.human_reviewer_as_returned,new Date(`${r.human_review_date}T00:00:00Z`),g,r.human_notes_as_returned,r.human_inheritance_genotype_as_returned,new Date(`${r.original_ai_association_date}T00:00:00Z`),r.original_ai_novelty]];
 returned.getRange(`A${ar}:K${ar}`).format.wrapText=true;
 returned.getRange(`A${ar}:K${ar}`).format.rowHeight=Math.max(108,Math.ceil(Math.max(r.human_notes_as_returned.length/55,r.human_inheritance_genotype_as_returned.length/60,r.human_association_date_raw.length/34))*17+10);
 if(r.human_association_exact_date_if_numeric){returned.getRange(`G${ar}`).setNumberFormat('yyyy-mm-dd');main.getRange(`J${rr}`).setNumberFormat('yyyy-mm-dd');}
}
main.tables.add('A8:N53',true,'AuthorConfirmations');header(main,'A8:N8');
main.getRange('C9:C53').dataValidation={rule:{type:'list',values:['PENDING','INCLUDE','EXCLUDE','UNCERTAIN']}};
main.getRange('C9:C53').conditionalFormats.add('containsText',{text:'UNCERTAIN',format:{fill:'#FCE4D6',font:{color:'#9C3500',bold:true}}});
main.getRange('D9:D53').setNumberFormat('yyyy-mm-dd');main.getRange('G9:G53').setNumberFormat('yyyy-mm-dd');
main.freezePanes.freezeRows(8);main.freezePanes.freezeColumns(1);
widths(main,{A:22,B:58,C:28,D:32,E:58,F:24,G:23,H:76,I:20,J:37,K:24,L:48,M:34,N:58});
returned.tables.add('A1:K46',true,'ReturnedAuthorObservations');header(returned,'A1:K1');
returned.getRange('F2:F46').setNumberFormat('yyyy-mm-dd');returned.getRange('J2:J46').setNumberFormat('yyyy-mm-dd');
returned.freezePanes.freezeRows(1);returned.freezePanes.freezeColumns(2);
widths(returned,{A:20,B:22,C:22,D:24,E:20,F:18,G:40,H:62,I:68,J:22,K:22});
const instructions=[
 ['What are we deciding?','For each gene, decide whether it belongs to the test set of later-reported retinal/optic, hearing or explicitly supported ciliary disease genes. This is what the earlier phrase “principal temporal test cohort” meant.'],
 ['What does source location mean?','A PMID plus the place inside that article: PDF page, printed page, figure, table or supplement. Example: PMID 33389130, PDF p.1 abstract. An exact citation helps another author check the same fact.'],
 ['What has already been done?','The returned workbook contains 45 author names, review dates and source/genotype notes. All 45 eligibility decisions still say PENDING. Date decisions are 10 CONFIRMED, 6 REVISED and 29 PENDING. Notes are preserved verbatim in Author return.'],
 ['What should I fill now?','Answer the specific question in Confirmations. Fill decision, earliest public TARGET date (or an interval in the reply), source-backed reply, your name and the date. Yellow cells are new author inputs. Do not overwrite original observations.'],
 ['INCLUDE','Use this gene as a test case only after the phenotype, unrelated-family, inheritance, support and timing rules below are met. INCLUDE means test-set membership, not general clinical certification.'],
 ['EXCLUDE / UNCERTAIN / PENDING','EXCLUDE: a documented rule fails. UNCERTAIN: required evidence or public timing cannot be resolved. PENDING: no final decision yet. Record a reason rather than turning missing evidence into a negative finding.'],
 ['Clinical rules','Relevant human retinal/optic disease, hearing impairment or an explicitly supported ciliopathy; target genotype/phenotype evidence in at least two unrelated families; consistent inheritance/segregation; and functional support OR independent human replication adding a new target-affected family.'],
 ['What does NOT suffice?','Normal expression/localization or computer prediction alone is not functional support. Same-family follow-up is not independent replication. Total neurological or multisystem families are not automatically target sensory families. Use gene-specific counts in multi-gene reports.'],
 ['Timing rules','First public proposal of the HUMAN TARGET association must be after 2020-12-31. Stronger qualifying evidence must have accumulated by 2026-10-06. Include public preprints and in-press versions. Receipt and acceptance dates are not automatically public-release dates.'],
 ['Three different dates','First proposed target association, first date meeting the stronger clinical rubric, and the date the author reviews the evidence are distinct. Example: target preprint 2021-06-10, journal 2022, replication 2024: the first-public target date is 2021-06-10. This is a hypothetical example.'],
 ['Intervals and early theses/conferences','CREB3, MRPL49 and TMEM72 have frozen earliest-publicity intervals. An interval lower bound displayed as a date in the old workbook is not proof of an exact day. Keep the interval if an exact day is unavailable. An interval crossing the cutoff cannot enter primary novelty recovery until resolved.'],
 ['Prior non-target disease','A prior intestinal, immune or developmental association is different from the first retinal/hearing/ciliary target association. Category B preserves an earlier non-target disease and a later first target association (for example STX3 and VWA8).'],
 ['How to use the source checks','Source checks and date candidates are AI-assisted suggestions for author confirmation. Frozen earlier preprint nominations are identified as candidates unless independently rechecked here. No case is automatically included/excluded and no frozen score or outcome is changed.'],
 ['Reference archive','Refs.zip contains 46 PDFs, 43 unique PMID labels and 44 unique file hashes (768 pages across copies). Four RNU-labelled PDFs concern the same PMID, not four independent replications. Some additional references nominated by the frozen evidence are not in this return.'],
 ['Symbol correction','The professor requested CLXN instead of EFCAB1. The current display is CLXN (EFCAB1); HGNC:25678 and the frozen historical gene identity remain unchanged. Official attribution: https://search.clinicalgenome.org/kb/genes/HGNC%3A25678'],
 ['Independent check example','DNAJC30 publisher version history lists the in-press preview on 2021-01-19, before the 2021-03-15 issue: https://www.jci.org/articles/view/138267 . Author confirmation remains pending.'],
 ['Source preservation','The two original returned files are preserved byte-for-byte with SHA-256 records. This workbook is a separate reconciliation aid. The original returned comments are transcribed below; the original file retains its native comment threads.'],
 ['What was not assessed','This intake includes machine extraction of all supplied PDFs and targeted checks, not a complete independent clinical adjudication of all 768 pages, not proof that no earlier report exists, and not a replacement for the author decisions.'],
 ...comments.map(c=>[`Original comment ${c.cell}`,c.text]),
 ['Protocol','Frozen rules: https://github.com/gbanyan/usher-exploring/blob/53da295/revision/major_revision_20261006/temporal_validation_v2/PROTOCOL.md']
];
guide.getRange('A2').values=[['How to finish the author confirmations']];guide.getRange('A2:B2').format.rowHeight=30;guide.getRange('A2').format.font={name:'Arial',size:16,bold:true};
guide.getRange(`A4:B${instructions.length+4}`).values=[['Question / term','Plain-language explanation'],...instructions];header(guide,'A4:B4');guide.getRange('A4:B4').format.rowHeight=30;
widths(guide,{A:34,B:115});guide.getRange(`A5:B${instructions.length+4}`).format.wrapText=true;
for(let i=0;i<instructions.length;i++)guide.getRange(`A${i+5}:B${i+5}`).format.rowHeight=Math.max(44,Math.ceil(instructions[i][1].length/112)*18+12);
guide.freezePanes.freezeRows(4);
// Disposable input change, then restore the delivered state before final checks.
main.getRange('C9').values=[['INCLUDE']];
wb.recalculate();
const changedPending=Number(main.getRange('B5').values[0][0]);
if(changedPending!==44)throw new Error(`Changed pending count: ${changedPending}`);
if(main.getRange('D9').values[0][0])throw new Error('A decision must not fabricate a date');
main.getRange('C9').values=[['PENDING']];
wb.recalculate();
const restoredPending=Number(main.getRange('B5').values[0][0]);
if(restoredPending!==45)throw new Error(`Restored pending count: ${restoredPending}`);
await fs.writeFile(`${cache}/recalculation_check.json`,JSON.stringify({changed_eligibility_pending:changedPending,restored_eligibility_pending:restoredPending,date_stays_blank:true,temporary_edit_restored:true}));
console.log((await wb.inspect({kind:'region',sheetId:'Confirmations',range:'A5:B5',maxChars:600})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10},maxChars:600})).ndjson);
for(const [sheetName,range,name] of [['Confirmations','A8:D12','confirmation-left'],['Confirmations','E8:H10','confirmation-reply'],['Author return','A1:G4','returned-dates'],['Author return','H1:K4','returned-notes'],['Guide','A2:B15','guide-top'],['Guide','A16:B26','guide-bottom']]){
 const p=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(`${cache}/${name}.png`,new Uint8Array(await p.arrayBuffer()));
}
await fs.mkdir(output,{recursive:true});await (await SpreadsheetFile.exportXlsx(wb)).save(`${output}/Temporal_Author_Confirmations_20261019.xlsx`);
console.log('Saved 45 pending author confirmations and 45 verbatim returned observations.');

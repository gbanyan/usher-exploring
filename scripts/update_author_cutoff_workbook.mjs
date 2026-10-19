// Run beside a symlink to the bundled artifact-tool node_modules.
import fs from 'node:fs/promises';
import {FileBlob, SpreadsheetFile} from '@oai/artifact-tool';
const root=process.cwd();
const cache=`${root}/data/cache/author-cutoff-decisions-20261019`;
const source=`${root}/outputs/temporal-author-return-v2-20261019/Temporal_Case_Author_Review_Defined_20261019_V2.xlsx`;
const target=`${root}/outputs/temporal-author-cutoff-decisions-20261019/Temporal_Case_Author_Decisions_Cutoff_20261019.xlsx`;
await fs.mkdir(cache,{recursive:true});
const previewFinal=process.argv.includes('--preview-final');
const previewNames=process.argv.includes('--preview-names');
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(previewFinal||previewNames?target:source));
const review=wb.worksheets.getItem('Review');
const evidence=wb.worksheets.getItem('Evidence');
const definitions=wb.worksheets.getItem('Definitions');
const preview=process.argv.includes('--preview');
if(preview || previewFinal || previewNames){
 const ranges=previewNames?[['Review','A20:D23','names-review'],['Evidence','A216:B220','names-evidence'],['Definitions','B16:D16','names-definition']]:previewFinal?[['Review','A5:D11','final-review'],['Review','G8:I10','final-notes'],['Definitions','B12:D15','final-rules'],['Definitions','B18:D23','final-fields'],['Definitions','B25:D27','final-intervals']]:[['Review','A8:D11','before-review'],['Definitions','B18:D22','before-definitions']];
 for(const [sheetName,range,name] of ranges){
  const blob=await wb.render({sheetName,range,scale:1,format:'png'});
  await fs.writeFile(`${cache}/${name}.png`,new Uint8Array(await blob.arrayBuffer()));
 }
 console.log(previewFinal?'Rendered the preserved final workbook without edits.':'Rendered source workbook before editing.');
 process.exit(0);
}
const audit=JSON.parse(await fs.readFile(`${root}/revision/major_revision_20261006/author_review_20261019/date_audit/gene_date_comparison.json`,'utf8'));
const byKey=new Map(audit.map(r=>[r.gene_key,r]));
const ledger=[];
const currentGeneLabel='CLXN (formerly EFCAB1)';
if(review.getRange('B22').values[0][0]!=='HGNC:25678' || evidence.getRange('B216').values[0][0]!=='HGNC:25678')throw new Error('CLXN stable-ID guard');
review.getRange('A22').values=[[currentGeneLabel]];
evidence.getRange('A216').values=[[currentGeneLabel]];
review.getRange('A3').values=[['Read Definitions: clinical eligibility and post-2020 timing are separate decisions; exact publication day is optional.']];
review.getRange('A6').values=[['A source-supported first-target publicity interval wholly after 2020-12-31 meets timing; clinical evidence must qualify by 2026-10-06.']];
review.getRange('C5').values=[['Timing pending']];
review.getRange('F5').values=[['POST_CUTOFF confirms timing only. Final clinical eligibility is still a separate decision in C.']];
review.getRange('D8').values=[['Timing: first public TARGET association after 2020-12-31?']];
review.getRange('G8').values=[['Professor’s date entry (preserved; see H for public date or interval used for timing)']];
review.getRange('H8').values=[['Source notes and clinical reasons, plus cutoff-window assessment and supporting source']];
review.getRange('D1:D53').format.columnWidth=26;
review.getRange('H1:H53').format.columnWidth=56;
review.getRange('D9:D53').dataValidation={rule:{type:'list',values:['PENDING','POST_CUTOFF','PRE_OR_AT_CUTOFF','UNCERTAIN']}};
for(let row=9;row<=53;row++){
 const key=review.getRange(`B${row}`).values[0][0];
 const r=byKey.get(key);
 if(!r)throw new Error(`Missing audit ${key}`);
 const [lower,upper]=r.original_frozen_interval;
 if(!(lower>'2020-12-31' && upper>=lower && upper<='2026-10-06'))throw new Error(`Invalid cutoff interval ${key}`);
 if(!r.first_target_source || !r.independently_located_public_event_date)throw new Error(`Missing public source ${key}`);
 const originalNotes=review.getRange(`H${row}`).values[0][0]||'';
 const note=`Timing: POST_CUTOFF. Retained first-target publicity interval: ${lower} to ${upper}. Located public target report: ${r.independently_located_public_event_date}. Source: ${r.first_target_source}${r.uncertain_first_public_day?' Exact first-public day remains unresolved; the interval is wholly after the cutoff.':''}`;
 review.getRange(`D${row}`).values=[['POST_CUTOFF']];
 review.getRange(`H${row}`).values=[[`${originalNotes}\n\n${note}`]];
 const noteLines=`${originalNotes}\n\n${note}`.split('\n').reduce((n,line)=>n+Math.max(1,Math.ceil(line.length/53)),0);
 review.getRange(`A${row}:K${row}`).format.rowHeight=Math.max(review.getRange(`A${row}:K${row}`).format.rowHeight||0,noteLines*16+18);
 ledger.push({excel_row:row,gene_key:key,symbol:r.symbol,display_symbol:key==='HGNC:25678'?currentGeneLabel:r.symbol,timing_decision:'POST_CUTOFF',interval:[lower,upper],located_public_event:r.independently_located_public_event_date,source:r.first_target_source,exact_day_uncertain:r.uncertain_first_public_day,eligibility_decision:review.getRange(`C${row}`).values[0][0]});
}
const updates={
 'D16':'CLXN (formerly EFCAB1) is the current display for HGNC:25678. The original TSV and returned files retain their historical symbol. HGNC: https://rest.genenames.org/fetch/hgnc_id/25678',
 'C6':'Choose clinical eligibility and cutoff-window timing separately. Exact-day matching is not required for timing.',
 'D6':'Use the source-supported public date or interval. Preserve the professor’s source notes and record clinical eligibility separately.',
 'D7':'The first proposed human TARGET association must be public after 2020-12-31; a wholly post-cutoff interval suffices. Stronger clinical evidence must exist by 2026-10-06.',
 'C12':'The earliest proposed public human TARGET association must be after 2020-12-31. Use public preprints/online versions or a source-supported interval; the exact day need not be established.',
 'D12':'A pre-2021 target proposal confirmed later is evidence maturation. A prior non-target disease does not itself disqualify. An interval crossing the cutoff stays unresolved.',
 'C14':'EXCLUDE: a documented clinical/timing rule fails. UNCERTAIN: a required clinical fact or the side of the cutoff cannot be resolved.',
 'D14':'An uncertain exact publication day alone does not prevent INCLUDE when a supported first-target interval is wholly post-cutoff. Clinical rules must still be met.',
 'B15':'Cutoff-window example',
 'C15':'Earliest public target report is bounded within 2021–2022; journal publication is in 2022; stronger clinical confirmation arrives in 2024.',
 'D15':'Timing D = POST_CUTOFF. Record the supported interval and source in H; no exact day is required. C = INCLUDE only if the clinical rules are also satisfied. This is hypothetical.',
 'B19':'Human decision on the first-target association’s side of the cutoff',
 'C19':'D assesses whether the earliest proposed public TARGET association is after 2020-12-31, using source-supported dates/intervals and the earlier-publicity review. It no longer checks exact agreement with J.',
 'D19':'POST_CUTOFF = interval wholly after cutoff; PRE_OR_AT_CUTOFF = first target report on/before cutoff; UNCERTAIN = side unresolved/crossing interval; PENDING = not assessed.',
 'D20':'E/F retain the professor’s primary-source reviewer/date. The new timing coding follows the author-approved cutoff-window rule of 2026-10-19 and the existing date audit; it does not assert new professor sign-off.',
 'B22':'Professor’s original association-date entry (preserved)',
 'C22':'G preserves the professor’s returned date text/value. It may be a journal issue, acceptance or other version date; it is not automatically the first public date.',
 'D22':'Use the source-supported public date or interval recorded in H to decide D. Exact-day precision is optional. The original V2 workbook preserves the prior exact-date decisions.',
 'C23':'Preserved source locations plus the timing assessment, first-target publicity interval, located public report and source URL. Clinical reasons/family counts remain separate.',
 'D23':'The appended timing assessment applies the author-approved rule and completed date audit; it does not sign off clinical eligibility. Record any clinical decision, supporting source and deciding author here.',
 'C25':'Original AI-screened located date retained for provenance. A displayed interval lower bound is not necessarily a verified exact first-public day.',
 'D25':'Read only. D now concerns the side of the cutoff, not exact agreement with J. Use H for the supported date/interval and source.',
 'C27':'The original source interval retains uncertainty. Timing can be resolved without establishing the exact earliest day.',
 'D27':'A supported interval wholly after 2020-12-31 is POST_CUTOFF even if the exact day is unknown. Crossing intervals remain UNCERTAIN. A later publication alone does not rule out an earlier target report.',
 'C45':'Original exact-first-public-date check status in the frozen source snapshot; its old meaning is preserved there.',
 'D45':'Read only source snapshot. The working Review D now records cutoff-window timing using the statuses in Definitions row 19.'
};
for(const [cell,value] of Object.entries(updates))definitions.getRange(cell).values=[[value]];
for(const row of [...new Set(Object.keys(updates).map(c=>Number(c.replace(/[A-Z]/g,''))))]){
 const values=definitions.getRange(`B${row}:D${row}`).values[0];
 definitions.getRange(`A${row}:D${row}`).format.rowHeight=Math.max(definitions.getRange(`A${row}:D${row}`).format.rowHeight||0,Math.ceil(Math.max(String(values[0]).length/42,String(values[1]).length/82,String(values[2]).length/73))*18+14);
}
wb.recalculate();
if(Number(review.getRange('B5').values[0][0])!==45 || Number(review.getRange('D5').values[0][0])!==0)throw new Error('Summary mismatch');
review.getRange('D9').values=[['PENDING']];wb.recalculate();
if(Number(review.getRange('D5').values[0][0])!==1 || Number(review.getRange('B5').values[0][0])!==45)throw new Error('Timing edit changed eligibility or failed recalculation');
review.getRange('D9').values=[['UNCERTAIN']];wb.recalculate();
if(review.getRange('C9').values[0][0]!=='PENDING')throw new Error('Timing must not imply clinical inclusion');
review.getRange('D9').values=[['POST_CUTOFF']];wb.recalculate();
if(Number(review.getRange('D5').values[0][0])!==0)throw new Error('Temporary edit not restored');
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10},maxChars:800})).ndjson);
for(const [sheetName,range,name] of [['Review','A5:D12','after-review'],['Review','G8:I10','after-notes'],['Definitions','B12:D15','after-rules'],['Definitions','B18:D23','after-fields'],['Definitions','B25:D27','after-intervals']]){
 const blob=await wb.render({sheetName,range,scale:1,format:'png'});
 await fs.writeFile(`${cache}/${name}.png`,new Uint8Array(await blob.arrayBuffer()));
}
await fs.mkdir(target.slice(0,target.lastIndexOf('/')),{recursive:true});
await(await SpreadsheetFile.exportXlsx(wb)).save(target);
await fs.writeFile(`${cache}/timing_ledger.json`,JSON.stringify(ledger,null,2)+'\n');
await fs.writeFile(`${cache}/edit_plan.json`,JSON.stringify({definition_updates:updates,review_header_cells:['A3','A6','C5','F5','D8','G8','H8'],symbol_updates:[{sheet:'Review',cell:'A22',gene_key:'HGNC:25678',display:currentGeneLabel},{sheet:'Evidence',cell:'A216',gene_key:'HGNC:25678',display:currentGeneLabel}],timing_column:'D9:D53',appended_notes:'H9:H53',column_widths:{D:26,H:56},row_heights_only_for_changed_notes:true,recalculation:{eligibility_pending:45,timing_pending:0,temporary_pending_count:1,temporary_uncertain_did_not_set_eligibility:true,restored:true}},null,2)+'\n');
console.log('Saved separate cutoff-window working copy; 45 POST_CUTOFF, 45 clinical decisions still PENDING.');

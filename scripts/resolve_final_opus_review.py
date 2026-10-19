"""Apply the concrete findings of the dated Opus audit without changing outcomes."""
from pathlib import Path
import re
import json

ROOT=Path(__file__).resolve().parents[1]
REV=ROOT/"revision/major_revision_20261006"


def change(path, old, new):
    text=path.read_text()
    assert text.count(old)==1,(path,old[:90])
    path.write_text(text.replace(old,new))


def main():
    main=ROOT/"manuscript/draft.md"
    supp=ROOT/"manuscript/supplementary_methods.md"
    response=REV/"rebuttal.md"
    cover=REV/"cover_letter_revision.md"
    change(cover,"https://github.com/gbanyan/usher-exploring/tree/revision/major-revision", "https://github.com/gbanyan/usher-exploring/tree/major-revision-author-review-20261019")
    change(cover,"The delivered-file SHA-256 manifest identifies this revision; the earlier fixed tag `major-revision-author-review-20261007` is preserved unchanged.","The fixed tag `major-revision-author-review-20261019` and delivered-file SHA-256 manifest identify this revision; the earlier 7 October tag is preserved unchanged.")
    change(main,"Subsequent human review identified unresolved target-family evidence in flagged cases.","Subsequent human review identified unresolved target-family evidence in three flagged cases.")
    change(main,"family-evidence concerns involving *PDIA6, VWA8* and *PLCG1*, detailed in S6.6", "family-evidence concerns involving *PDIA6* [63], *VWA8* [64] and *PLCG1* [65, 66], detailed in S6.6")
    change(main,"Publication-version checks supported first-target publicity intervals wholly after the cutoff;", "Publication-version checks in a bounded audit supported first-target publicity intervals wholly after the cutoff;")
    change(main,"or either prespecified sensitivity analysis (S8;", "or either protocol-specified secondary analysis (S8;")
    ledger="The frozen screening ledger also cites later PDIA6 reports (PMIDs 35856135, 40974269), recording three families overall and a conservative lower bound of two target families; the VWA8 retinal reports (PMIDs 37012052, 40638000) give a target-family lower bound of two, and PLCG1 has a conservative target-family lower bound of three. These are the retained screening classifications, not new human inclusion decisions."
    change(supp,"These observations therefore require gene–target-specific interpretation; they do not by themselves constitute three exclusions.",ledger+" These observations therefore require gene–target-specific interpretation; they do not by themselves constitute three exclusions.")
    change(response,"Eligibility of the flagged cases remains under review; the original temporal results are retained.",ledger+" The index-paper concerns do not by themselves constitute three exclusions. Eligibility of the flagged cases remains under review; the original temporal results are retained.")
    change(supp,"These intervals lie wholly after the cutoff. DAP3, LETM1 and TBX2", "These intervals lie wholly after the cutoff. The subsequent publication-version audit also retained earliest-day uncertainty for ATP11A (S6.6). DAP3, LETM1 and TBX2")
    change(supp,"the subsequent suite passed 354 tests. Numerical TSV outputs", "the subsequent temporal suite passed 354 tests. Following the GO extension, the current suite passed 362 tests with 17 existing warnings. Numerical TSV outputs")
    change(supp,"and mRNA metabolic process (five). This composition", "and mRNA metabolic process (five, including four RNU genes supported only by IEA). This composition")
    change(REV/"go_classification_20261019/REPORT.md", "independently reproduces all 24,597 test counts/P values/BH values using Fisher's exact test and SciPy BH", "recalculates all 24,597 test counts/P values/BH values from the analysis-derived association cache using separate Fisher-exact/SciPy-BH code; raw annotation mapping/propagation is checked by same-code replay")
    # References are now all cited in the main manuscript. Assign their numbers
    # by actual first appearance, preserving [0,1] score bounds as noncitations.
    text=main.read_text(); body,refs=text.split("## References\n",1)
    blocks=re.split(r"\n\n(?=\[\d+\])",refs.strip())
    by_old={int(re.match(r"\[(\d+)\]",b)[1]):b for b in blocks}
    assert set(by_old)==set(range(1,67))
    pattern=r"\[(\d+(?:,\s*\d+)*)\]"
    order=[]
    for m in re.finditer(pattern,body):
        values=[int(n) for n in re.split(r",\s*",m[1])]
        if not all(n in by_old for n in values): continue
        for n in values:
            if n not in order: order.append(n)
    assert len(order)==66,(len(order),set(by_old)-set(order))
    mapping={old:new for new,old in enumerate(order,1)}
    def renumber(match):
        vals=[int(n) for n in re.split(r",\s*",match[1])]
        if not all(n in mapping for n in vals): return match[0]
        return "["+", ".join(str(mapping[n]) for n in vals)+"]"
    body=re.sub(pattern,renumber,body)
    refs="\n\n".join(re.sub(r"^\[\d+\]",f"[{mapping[n]}]",by_old[n]) for n in order)
    main.write_text(body+"## References\n\n"+refs+"\n")
    for p in (supp,response): p.write_text(re.sub(pattern,renumber,p.read_text()))
    (REV/"final_review_20261019/reference_renumbering.json").write_text(json.dumps({"method":"First main-text citation, excluding numerical score bounds","old_to_new":mapping,"all_66_references_cited_in_main_text":True},indent=2)+"\n")
    # Regenerate the concise distributed summary from the revised section.
    summary=supp.read_text().split("### S6.6 Subsequent human author review\n",1)[1].split("## S7.",1)[0]
    (REV/"final_review_20261019/HUMAN_REVIEW_SUMMARY.md").write_text("# Subsequent human author review\n\n19 October 2026. This summary accompanies the unchanged frozen temporal analysis. References [57–64] are in the revised manuscript; identifiers for later reports remain in the frozen clinical ledger.\n\n"+summary+"\nPrimary index reports: CRLS1 PMID35147173; CTNND1 PMID35700046; DHRSX PMID38821050; RNU PMID41513982; PDIA6 PMID33495992; VWA8 PMID34660594; PLCG1 PMID37422272/40862571.\n")
    print("Resolved cover version, first-citation numbering and cumulative-family context; outcomes unchanged")


if __name__=="__main__": main()

"""Format the supplied primary-report metadata without inventing citations."""
import re
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def main():
    root=ET.parse(ROOT/"data/cache/author-review-20261019/date-audit/pubmed.xml").getroot()
    records={a.findtext("MedlineCitation/PMID"):a for a in root.findall("PubmedArticle")}
    ids=["35147173","35700046","38821050","41513982","33495992","34660594","37422272","40862571"]
    citations=[]
    for number,pmid in enumerate(ids,59):
        a=records[pmid].find("MedlineCitation/Article")
        authors=[]
        for person in a.findall("AuthorList/Author")[:6]:
            authors.append((person.findtext("LastName","")+" "+person.findtext("Initials","")).strip() or person.findtext("CollectiveName",""))
        if len(a.findall("AuthorList/Author"))>6: authors.append("et al")
        title="".join(a.find("ArticleTitle").itertext()).rstrip(".")
        journal=a.findtext("Journal/ISOAbbreviation")
        year=a.findtext("Journal/JournalIssue/PubDate/Year")
        volume=a.findtext("Journal/JournalIssue/Volume","")
        issue=a.findtext("Journal/JournalIssue/Issue","")
        page=a.findtext("Pagination/MedlinePgn") or next((e.text for e in a.findall("ELocationID") if e.get("EIdType")=="pii"),"")
        doi=next(e.text for e in records[pmid].findall("PubmedData/ArticleIdList/ArticleId") if e.get("IdType")=="doi")
        citations.append(f"[{number}] {', '.join(authors)}. {title}. {journal}. {year};{volume}"+(f"({issue})" if issue else "")+(f":{page}" if page else "")+f". doi:{doi}.")
    main=ROOT/"manuscript/draft.md"
    text=main.read_text()
    assert "[59]" not in text
    text += "\n\n"+"\n\n".join(citations)+"\n"
    for number,pmid in enumerate(ids,59):
        text=text.replace(f"(PMID {pmid})",f"[{number}]")
    main.write_text(text)
    supp=ROOT/"manuscript/supplementary_methods.md"
    text=supp.read_text()
    for number,pmid in enumerate(ids,59): text=text.replace(f"(PMID {pmid})",f"[{number}]")
    supp.write_text(text)
    print("Eight numbered primary references formatted from audited PubMed XML")


if __name__ == "__main__": main()

"""Render bounded date panels from all 43 unique supplied PMID-labelled papers."""
import json
import re
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/major_revision_20261006/author_review_20261019/date_audit"
CACHE = ROOT / "data/cache/author-review-20261019"


def main():
    rows = json.loads((BASE / "article_dates.json").read_text())
    panels = []
    locations = []
    pattern = re.compile(r"(?i)(received[: ]|submitted \d|accepted[: ]|published online:|published online \w|published:|advance access publication|accepted for publication|preprint posted|version of record published)")
    for row in rows:
        filename = row["filenames"][0]
        doc = pymupdf.open(CACHE / "references" / filename)
        matches = []
        for i, page in enumerate(doc):
            for block in page.get_text("blocks"):
                text = block[4]
                if pattern.search(text) and re.search(r"20\d{2}", text):
                    matches.append((i, pymupdf.Rect(block[:4]), text))
        canvas = Image.new("RGB", (1400, 270), "white")
        draw = ImageDraw.Draw(canvas)
        title = ", ".join(row["symbols_on_files"]) + "  PMID " + row["pmid"]
        draw.text((12, 7), title, fill="#24364B", font_size=20)
        if matches:
            page_num, rect, text = matches[0]
            page = doc[page_num]
            # Expand to whole page width so adjacent column history labels remain visible.
            crop = pymupdf.Rect(0, max(0, rect.y0 - 5), page.rect.width, min(page.rect.height, max(rect.y0+120, rect.y1 + 15)))
            if crop.height > 150:
                crop.y1 = min(page.rect.height, crop.y0 + 150)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=crop, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.thumbnail((1375, 210))
            canvas.paste(img, (12, 40))
            draw.text((12, 245), f"Supplied PDF p.{page_num+1}; public date may require separate publisher history / PubMed metadata", fill="#52657A", font_size=15)
            locations.append({"pmid": row["pmid"], "preview_page": page_num + 1})
        else:
            draw.text((12, 65), "No complete date-history panel found in supplied extract. Dates checked in PubMed/publisher metadata.", fill="#9C3500", font_size=20)
            locations.append({"pmid": row["pmid"], "preview_page": None})
        panels.append(canvas)
        doc.close()
    out = CACHE / "date-audit"
    for start in range(0, len(panels), 11):
        chunk = panels[start:start+11]
        contact = Image.new("RGB", (1400, 270 * len(chunk)), "#DCE4EC")
        for i, panel in enumerate(chunk):
            contact.paste(panel, (0, i*270))
        contact.save(out / f"date-panels-{start//11+1}.png")
    (out / "preview-locations.json").write_text(json.dumps(locations, indent=2) + "\n")
    print(f"Rendered date panels for {len(panels)} unique supplied PMID labels into four contact sheets.")


if __name__ == "__main__":
    main()

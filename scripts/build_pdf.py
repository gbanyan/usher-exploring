"""Build a review-ready PDF of the manuscript with figures embedded.

Inserts each figure image directly above its legend in the "Figure legends"
section and renders manuscript/draft.md to PDF via pandoc + xelatex. Scientific
Unicode is rewritten to LaTeX so the PDF needs no special fonts or LaTeX
packages beyond a standard install. The source draft.md is left unchanged.

Requires: pandoc and a LaTeX engine (xelatex).

Run:  python scripts/build_pdf.py
Output: manuscript/draft.pdf
"""

import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "manuscript" / "draft.md"
FIGDIR = ROOT / "data" / "report" / "paper_figures"
OUT = ROOT / "manuscript" / "draft.pdf"

# Scientific Unicode -> pandoc-safe LaTeX. \ensuremath works in any position
# (unlike $...$, which pandoc rejects as math when followed by a digit).
UNICODE_MAP = {
    "≥": r"\ensuremath{\geq}", "≤": r"\ensuremath{\leq}", "≠": r"\ensuremath{\neq}",
    "→": r"\ensuremath{\rightarrow}", "×": r"\ensuremath{\times}",
    "±": r"\ensuremath{\pm}", "−": r"\ensuremath{-}",
    "Σ": r"\ensuremath{\Sigma}", "ζ": r"\ensuremath{\zeta}",
    "ρ": r"\ensuremath{\rho}", "τ": r"\ensuremath{\tau}",
    "✓": r"\ensuremath{\checkmark}", "†": r"\ensuremath{\dagger}",
    "⁺": r"\textsuperscript{+}", "₂": r"\textsubscript{2}",
}

HEADER = "\\usepackage{amssymb}\n"


def make_paths_breakable(text: str) -> str:
    """Render path-like inline-code spans with LaTeX's breakable path command."""
    pattern = re.compile(r"`([^`\n]*[/\\][^`\n]*)`")
    return pattern.sub(lambda match: rf"\path{{{match.group(1)}}}", text)


def figure_path(n: int) -> Path | None:
    """Return the PNG for Figure n (fig{n}_*.png), or None if absent."""
    matches = sorted(FIGDIR.glob(f"fig{n}_*.png"))
    return matches[0] if matches else None


def main():
    out_lines = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\*\*Figure (\d+)\.", line)
        if m:
            fp = figure_path(int(m.group(1)))
            if fp:
                out_lines.append(f"![]({fp}){{width=85%}}")
                out_lines.append("")
        out_lines.append(line)

    text = "\n".join(out_lines)
    for uni, tex in UNICODE_MAP.items():
        text = text.replace(uni, tex)
    text = make_paths_breakable(text)
    # Give the narrow first column in Table 2 a legal line-break point.
    text = text.replace("Protein/expression", "Protein/ expression")

    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(text)
        tmp_path = tmp.name

    with tempfile.NamedTemporaryFile(
        "w", suffix=".tex", delete=False, encoding="utf-8"
    ) as hdr:
        hdr.write(HEADER)
        hdr_path = hdr.name

    cmd = [
        "pandoc", tmp_path, "-o", str(OUT),
        "--pdf-engine=xelatex",
        "-V", "geometry:margin=0.85in",
        "-V", "fontsize=11pt",
        "-V", "linkcolor=blue",
        "--include-in-header", hdr_path,
    ]
    subprocess.run(cmd, check=True)
    Path(tmp_path).unlink()
    Path(hdr_path).unlink()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()

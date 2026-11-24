"""Build second-revision DOCX documents from Markdown sources.

Reuses the first-revision formatting (build_revision_submission.format_document).
Run with the document environment that provides python-docx; Pandoc is required.
Sources are passed explicitly so that confidential letters can stay outside the
public package directory.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_revision_submission import format_document  # noqa: E402

FIGURE_S1 = ROOT / "outputs/temporal-go-classification-20261019/Temporal_GO_Functional_Overview_20261019.png"


def stage_manuscript(text: str, figures_dir: Path) -> str:
    lines = []
    for line in text.splitlines():
        if re.fullmatch(r"\[Figure \d+ near here\]", line):
            continue
        match = re.match(r"\*\*Figure (\d+)\.", line)
        if match:
            figures = sorted(figures_dir.glob(f"fig{match[1]}_*.png"))
            if len(figures) != 1:
                raise ValueError(f"Expected one image for figure {match[1]}: {figures}")
            lines.extend([f"![]({figures[0].resolve()}){{width=6.7in}}", ""])
        lines.append(line)
    return "\n".join(lines) + "\n"


def stage_letter(text: str) -> str:
    """Give each quoted line its own paragraph and keep signature line breaks."""
    out = []
    lines = text.splitlines()
    list_item = re.compile(r"^\s*(?:[-*]|\d+\.)\s")
    for i, line in enumerate(lines):
        prev = lines[i - 1] if i else ""
        if list_item.match(line) and prev.strip() and not list_item.match(prev) and not prev.startswith(" "):
            out.append("")
        out.append(line)
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if line.lstrip().startswith("> ") and nxt.lstrip().startswith("> "):
            indent = line[: len(line) - len(line.lstrip())]
            if re.match(r"> (Kind regards,|Ritesh Shelke)$", line.lstrip()):
                out[-1] = line + "\\"
            else:
                out.append(indent + ">")
    return "\n".join(out) + "\n"


def build(name: str, source: Path, output_dir: Path, cache: Path, figures_dir: Path | None) -> Path:
    text = source.read_text()
    reader = "markdown"
    if name == "Manuscript":
        text = stage_manuscript(text, figures_dir)
    elif name == "Supplementary_Methods" and "**Figure S1." in text:
        text = text.replace("**Figure S1.", f"![]({FIGURE_S1.resolve()}){{width=6.5in}}\n\n**Figure S1.", 1)
    elif name in ("Response_to_Reviewers", "Cover_Letter"):
        text = stage_letter(text)
        reader = "markdown-blank_before_blockquote"
    staged = cache / f"{name}.md"
    staged.write_text(text)
    output = output_dir / f"{name}.docx"
    subprocess.run(["pandoc", "-f", reader, str(staged), "--syntax-highlighting=none", "-o", str(output)], check=True)
    format_document(output, name == "Manuscript")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--figures-dir", type=Path)
    parser.add_argument("--manuscript", type=Path)
    parser.add_argument("--supplement", type=Path)
    parser.add_argument("--response", type=Path)
    parser.add_argument("--cover", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    jobs = [("Manuscript", args.manuscript), ("Supplementary_Methods", args.supplement),
            ("Response_to_Reviewers", args.response), ("Cover_Letter", args.cover)]
    for name, source in jobs:
        if source is None:
            continue
        if name == "Manuscript" and args.figures_dir is None:
            raise SystemExit("--figures-dir is required with --manuscript")
        print(build(name, source, args.output_dir, args.cache_dir, args.figures_dir))


if __name__ == "__main__":
    main()

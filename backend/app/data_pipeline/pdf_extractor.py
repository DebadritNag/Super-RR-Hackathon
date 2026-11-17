"""PDF text extraction for the problem statement."""

from __future__ import annotations

import re
from pathlib import Path

try:  # pragma: no cover
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    from PyPDF2 import PdfReader  # type: ignore[no-redef]

HINT_KEYWORDS: dict[str, list[str]] = {
    "deliverables": ["deliverable", "submit", "submission", "top 10", "top 5", "top ten", "rank"],
    "pressure": ["pressure", "required run rate", "wickets in hand", "death", "powerplay"],
    "eligibility": ["minimum", "eligib", "at least", "qualif", "sample"],
    "ipl": ["ipl", "indian premier league"],
    "t20i": ["t20i", "international"],
    "weighting": ["weight", "weightage", "differently", "more importance"],
    "date_window": ["between", "from 20", "since 20", "2022", "2023", "2024", "2025", "2026"],
    "output_format": ["report", "pdf", "word", "csv", "slides", "presentation", "page", "words"],
    "scoring_criteria": ["judg", "criteria", "evaluat", "scor", "marks", "points"],
}


def extract_pdf_text(pdf: Path, out_txt: Path) -> dict:
    reader = PdfReader(str(pdf))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        pages.append(f"--- page {i} ---\n{page.extract_text() or ''}")
    text = "\n\n".join(pages)
    # This PDF stores one token per line separated by whitespace-only lines; rejoin them.
    text = re.sub(r"\n[ \t]+\n", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    with open(out_txt, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return {"pdf": pdf.name, "pages": len(reader.pages), "characters": len(text), "text": text}


def find_requirement_hints(text: str) -> dict:
    """Keyword hits only (line-number evidence). Not a substitute for reading the text."""
    lines = text.splitlines()
    out: dict[str, list[dict]] = {}
    for topic, kws in HINT_KEYWORDS.items():
        hits = []
        for no, line in enumerate(lines, start=1):
            low = line.lower()
            if any(k in low for k in kws):
                hits.append({"line": no, "text": line.strip()[:200]})
        out[topic] = hits[:25]
    return out

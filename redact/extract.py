"""Extract and lightly clean text from a PDF."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_pages(pdf_path: str | Path) -> list[str]:
    """Return one cleaned text string per PDF page (1:1 with page order)."""
    reader = PdfReader(str(pdf_path))
    return [clean_page_text(page.extract_text() or "") for page in reader.pages]


def clean_page_text(text: str) -> str:
    """Join words the PDF splitter broke across lines, then normalise spaces.

    Cover-page emails in this prospectus are stored as
    ``cs.connect@kshinternational.co\\nm``. Removing newlines before
    collapsing whitespace reconstructs them.
    """
    if not text:
        return ""
    joined = text.replace("\r", "\n")
    joined = joined.replace("\n", "")
    joined = " ".join(joined.split())
    # Fix "kshinternational. com" style splits that still have a space.
    joined = joined.replace(". com", ".com").replace(". in", ".in")
    joined = joined.replace(". org", ".org").replace(". co ", ".co ")
    return joined

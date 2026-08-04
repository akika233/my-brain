from __future__ import annotations

from pathlib import Path


def extract_text(pdf_path: Path) -> str:
    """Extract plain text from a PDF. Prefers pdfplumber; falls back to pypdf."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    text = _try_pdfplumber(path)
    if text and text.strip():
        return text

    text = _try_pypdf(path)
    if text and text.strip():
        return text

    raise ValueError(
        f"No extractable text in {path.name}. "
        "If this is a scanned PDF, OCR support is needed."
    )


def _try_pdfplumber(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        return ""

    parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _try_pypdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)

from __future__ import annotations

from pathlib import Path

# Words whose vertical positions differ by less than this (points) are on the same visual row.
_ROW_TOLERANCE = 3.0

# A horizontal gap wider than this (points) is treated as a column break and rendered
# as a double space, so downstream parsing can tell "label   value" from "two words".
_MIN_COLUMN_GAP = 8.0


def extract_text(pdf_path: Path) -> str:
    """Extract text from a PDF, preserving visual row/column structure where possible.

    Order of preference:
      1. pdfplumber word coordinates grouped into visual rows (keeps label/value on one line)
      2. pdfplumber flat text
      3. pypdf flat text
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(path)

    for extractor in (_try_pdfplumber_layout, _try_pdfplumber, _try_pypdf):
        text = extractor(path)
        if text and text.strip():
            return text

    raise ValueError(
        f"No extractable text in {path.name}. "
        "If this is a scanned PDF, OCR support is needed."
    )


def _try_pdfplumber_layout(path: Path) -> str:
    """Rebuild page text from word coordinates instead of pdfplumber's flat reading order.

    Flat extraction collapses a 2D page into a 1D string, which merges unrelated columns
    and separates labels from the values printed beside them. Grouping words by their
    vertical position restores the visual rows a human sees.
    """
    try:
        import pdfplumber
    except ImportError:
        return ""

    parts: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
                if not words:
                    parts.append(page.extract_text() or "")
                    continue
                parts.append(_words_to_rows(words))
    except Exception:  # noqa: BLE001 - fall back to flat extraction
        return ""
    return "\n".join(parts)


def _words_to_rows(words: list[dict]) -> str:
    rows: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(word["top"] - rows[-1][0]["top"]) <= _ROW_TOLERANCE:
            rows[-1].append(word)
        else:
            rows.append([word])

    lines: list[str] = []
    for row in rows:
        row.sort(key=lambda w: w["x0"])
        line = row[0]["text"]
        for prev, cur in zip(row, row[1:]):
            gap = cur["x0"] - prev["x1"]
            line += ("  " if gap > _MIN_COLUMN_GAP else " ") + cur["text"]
        lines.append(line)
    return "\n".join(lines)


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

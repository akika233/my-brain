"""Invoice file -> InvoiceRecord (PDF or image), with rent-aware routing."""
from __future__ import annotations

from pathlib import Path

from .models import InvoiceRecord
from .parse_invoice import parse_invoice_text
from .parse_rent_de import looks_like_german_rent, parse_german_rent_invoice
from .pdf_text import extract_text, ocr_letterhead


def extract_invoice(path: Path, allow_ocr: bool = True) -> InvoiceRecord:
    """Parse one invoice PDF/image.

    German commercial-rent layouts (Mindestmiete / Nebenkosten / Rental income)
    use a dedicated parser. Everything else keeps the existing FR/generic path,
    with letterhead OCR when supplier is missing on a PDF.
    """
    path = Path(path)
    text = extract_text(path)

    if looks_like_german_rent(text):
        return parse_german_rent_invoice(text, source_file=path.name)

    record = parse_invoice_text(text, source_file=path.name)

    if allow_ocr and record.supplier is None and path.suffix.lower() == ".pdf":
        brand = ocr_letterhead(path)
        if brand:
            record = parse_invoice_text(text, source_file=path.name, ocr_supplier=brand)

    return record

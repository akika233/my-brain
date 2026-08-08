"""PDF file -> InvoiceRecord, including the optional OCR retry.

Kept separate from parse_invoice (text -> fields) and pdf_text (PDF -> text) so that
each stage stays independently testable.
"""
from __future__ import annotations

from pathlib import Path

from .models import InvoiceRecord
from .parse_invoice import parse_invoice_text
from .pdf_text import extract_text, ocr_letterhead


def extract_invoice(path: Path, allow_ocr: bool = True) -> InvoiceRecord:
    """Parse one invoice PDF, falling back to letterhead OCR for a missing supplier.

    OCR is deliberately driven by a missing field rather than by an empty text layer:
    invoices exist that carry complete text for every amount yet print the supplier's
    name only inside a logo image, so a page-level "is this scanned?" test never fires.
    """
    path = Path(path)
    text = extract_text(path)
    record = parse_invoice_text(text, source_file=path.name)

    if allow_ocr and record.supplier is None:
        brand = ocr_letterhead(path)
        if brand:
            record = parse_invoice_text(text, source_file=path.name, ocr_supplier=brand)

    return record

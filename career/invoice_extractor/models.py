from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass
class InvoiceRecord:
    source_file: str
    invoice_number: str | None = None
    invoice_date: str | None = None
    supplier: str | None = None
    amount: float | None = None
    vat_rate: float | None = None
    vat_amount: float | None = None
    po_number: str | None = None
    currency: str | None = None
    needs_review: bool = False
    validation: str | None = None
    raw_excerpt: str | None = None
    parse_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def field_names(cls) -> list[str]:
        return [f.name for f in fields(cls)]
